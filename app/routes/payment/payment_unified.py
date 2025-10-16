"""
Payment Routes & API - Unified với Services Architecture
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from datetime import datetime, timedelta
import json

from app.services.payment import (
    payment_service,
    payment_validation_service,
    payment_notification_service,
    payment_configuration_service
)
from app.utils.rate_limiter import payos_rate_limit, enforce_payment_creation_limits
from app.utils.booking_locking import booking_locking_service, BookingConflictError, BookingLockingError

payment_bp = Blueprint('payment', __name__, url_prefix='/payment')

# =============================================================================
# WEB ROUTES (HTML Pages)
# =============================================================================

@payment_bp.route('/checkout/<int:booking_id>')
@login_required
def checkout(booking_id):
    """Hiển thị trang checkout với thông tin booking"""
    # Kiểm tra email verification cho Renter
    if current_user.is_renter() and not current_user.email_verified:
        flash('Vui lòng xác thực email trước khi thực hiện thanh toán', 'warning')
        return redirect(url_for('renter.verify_email'))
    
    # Validate booking
    validation_result = payment_validation_service.validate_booking_for_payment(
        booking_id, current_user.id
    )
    
    if not validation_result["valid"]:
        flash(validation_result["error"], 'danger')
        return redirect(url_for('renter.dashboard'))
    
    booking = validation_result["booking"]
    
    # Calculate minimum date (30 days before booking start time)
    min_date = booking.start_time - timedelta(days=30)

    return render_template('payment/checkout.html', booking=booking, min_date=min_date)

@payment_bp.route('/modify-booking/<int:booking_id>', methods=['POST'])
@login_required
def modify_booking(booking_id):
    """Modify booking details before payment"""
    # Kiểm tra email verification cho Renter
    if current_user.is_renter() and not current_user.email_verified:
        flash('Vui lòng xác thực email trước khi thực hiện thanh toán', 'warning')
        return redirect(url_for('renter.verify_email'))
    
    try:
        # Validate modification data
        modification_data = {
            'booking_type': request.form.get('booking_type', 'daily'),
            'start_date': request.form.get('start_date'),
            'start_date_hourly': request.form.get('start_date_hourly'),
            'start_time': request.form.get('start_time'),
            'duration_daily': request.form.get('duration_daily'),
            'duration_hourly': request.form.get('duration_hourly')
        }
        
        validation_result = payment_validation_service.validate_payment_modification(
            booking_id, current_user.id, modification_data
        )
        
        if not validation_result["valid"]:
            flash(validation_result["error"], 'warning')
            return redirect(url_for('payment.checkout', booking_id=booking_id))
        
        booking = validation_result["booking"]
        start_datetime = validation_result["start_datetime"]
        duration = validation_result["duration"]
        booking_type = validation_result["booking_type"]
        
        # Calculate total price based on booking type
        home = booking.home
        total_price = 0
        
        if booking_type == 'hourly':
            end_datetime = start_datetime + timedelta(hours=duration)
            
            # Check for overnight/daytime pricing
            start_hour = start_datetime.hour
            is_overnight = (start_hour >= 21 or start_hour <= 8) and home.price_overnight
            is_daytime = (start_hour >= 9 and start_hour <= 20) and home.price_daytime
            
            if is_overnight and duration >= 8:
                total_price = home.price_overnight
            elif is_daytime and duration >= 8:
                total_price = home.price_daytime
            elif duration <= 2 and home.price_first_2_hours:
                total_price = home.price_first_2_hours
            elif duration > 2 and home.price_first_2_hours and home.price_per_additional_hour:
                total_price = home.price_first_2_hours + (duration - 2) * home.price_per_additional_hour
            elif home.price_per_hour:
                total_price = duration * home.price_per_hour
            else:
                flash("Nhà này chưa có giá phù hợp với thời gian bạn chọn.", "warning")
                return redirect(url_for('payment.checkout', booking_id=booking_id))
        else:  # daily booking
            end_datetime = start_datetime + timedelta(days=duration)
            price = home.price_per_day if home.price_per_day and home.price_per_day > 0 else home.price_per_night
            if not price or price <= 0:
                flash("Nhà này chưa có thông tin giá. Vui lòng liên hệ chủ nhà để cập nhật giá trước khi đặt.", "warning")
                return redirect(url_for('payment.checkout', booking_id=booking_id))
            
            total_price = price * duration
            duration = duration * 24  # Convert to hours for total_hours field
        
        # Update booking với hybrid locking
        try:
            updated_booking = booking_locking_service.update_booking_with_locking(
                booking_id=booking.id,
                start_time=start_datetime,
                end_time=end_datetime,
                total_hours=duration if booking_type == 'hourly' else duration,
                total_price=total_price
            )
            
            # Update additional fields
            updated_booking.booking_type = booking_type
            from app.models.models import db
            db.session.commit()
            
            flash('Thông tin đặt phòng đã được cập nhật thành công!', 'success')
            return redirect(url_for('payment.checkout', booking_id=booking_id))
            
        except BookingConflictError as e:
            flash('This home is not available during the selected time period.', 'danger')
            current_app.logger.warning(f"Booking modification conflict for booking {booking_id}: {e}")
            return redirect(url_for('payment.checkout', booking_id=booking_id))
            
        except BookingLockingError as e:
            flash('Unable to update booking at this time. Please try again.', 'danger')
            current_app.logger.error(f"Booking modification locking error for booking {booking_id}: {e}")
            return redirect(url_for('payment.checkout', booking_id=booking_id))
            
        except Exception as e:
            flash('An error occurred while updating the booking. Please try again.', 'danger')
            current_app.logger.error(f"Unexpected error updating booking {booking_id}: {e}")
            return redirect(url_for('payment.checkout', booking_id=booking_id))
        
    except Exception as e:
        current_app.logger.error(f"[PAYMENT] Error modifying booking: {str(e)}")
        flash(f"Lỗi cập nhật thông tin đặt phòng: {str(e)}", 'danger')
        return redirect(url_for('payment.checkout', booking_id=booking_id))

@payment_bp.route('/process_payment', methods=['POST'])
@login_required
@payos_rate_limit
@enforce_payment_creation_limits(user_daily_limit=5, ip_minute_limit=20, ip_hour_limit=200)
def process_payment():
    """Xử lý tạo payment"""
    current_app.logger.info(f'[PAYMENT] User {current_user.id} ({current_user.email}) bắt đầu tạo payment cho booking {request.form.get("booking_id")}.')
    
    # Kiểm tra email verification cho Renter
    if current_user.is_renter() and not current_user.email_verified:
        flash('Vui lòng xác thực email trước khi thực hiện thanh toán', 'warning')
        return redirect(url_for('renter.verify_email'))
    
    booking_id = request.form.get('booking_id')
    
    # Sử dụng payment service để tạo payment
    result = payment_service.create_payment(
        booking_id=int(booking_id),
        user_id=current_user.id,
        return_url=url_for('payment.payment_success', payment_id='{payment_id}', _external=True),
        cancel_url=url_for('payment.payment_cancelled', payment_id='{payment_id}', _external=True)
    )
    
    if result.get("error"):
        flash(result["error"], 'danger')
        return redirect(url_for('payment.checkout', booking_id=booking_id))
    
    # Gửi thông báo tạo payment
    from app.models.models import Payment
    payment = Payment.query.get(result["payment_id"])
    if payment:
        payment_notification_service.send_payment_created_notification(payment)
    
    return redirect(result["redirect_url"])

@payment_bp.route('/status/<int:payment_id>')
@login_required
def payment_status(payment_id):
    """Hiển thị trang trạng thái thanh toán với QR Code"""
    result = payment_service.get_payment_status(payment_id, current_user.id)
    
    if result.get("error"):
        flash(result["error"], 'danger')
        return redirect(url_for('renter.dashboard'))
    
    payment_data = result["payment"]
    
    # Chuẩn bị dữ liệu cho template
    template_data = {
        'payment': payment_data,
        'booking': payment_data.get('booking'),
        'payos_data': payment_data.get('payos_data', {}),
        'qr_code': payment_data.get('qr_code'),
        'account_number': payment_data.get('account_info', {}).get('account_number'),
        'account_name': payment_data.get('account_info', {}).get('account_name'),
        'bank_name': payment_data.get('account_info', {}).get('bank_name'),
        'formatted_amount': f"{payment_data['amount']:,.0f} VND"
    }
    
    return render_template('payment/payment_status.html', **template_data)

@payment_bp.route('/success/<int:payment_id>')
@login_required
def payment_success(payment_id):
    """Trang thanh toán thành công"""
    result = payment_service.process_payment_success(payment_id, current_user.id)
    
    if result.get("error"):
        flash(result["error"], 'danger')
        return redirect(url_for('renter.dashboard'))
    
    payment = result["payment"]
    booking = result["booking"]
    
    return render_template('payment/success.html', payment=payment, booking=booking)

@payment_bp.route('/failed/<int:payment_id>')
@login_required
def payment_failed(payment_id):
    """Trang thanh toán thất bại"""
    from app.models.models import Payment
    payment = Payment.query.get_or_404(payment_id)
    booking = payment.booking
    
    # Kiểm tra quyền
    if payment.renter_id != current_user.id:
        flash('Bạn không có quyền truy cập thông tin này.', 'danger')
        return redirect(url_for('renter.dashboard'))
    
    current_app.logger.warning(f'[PAYMENT] Payment {payment.payment_code} thất bại cho booking {booking.id}, user {current_user.id}.')
    return render_template('payment/failed.html', payment=payment, booking=booking)

@payment_bp.route('/cancelled/<int:payment_id>')
@login_required
def payment_cancelled(payment_id):
    """Trang thanh toán bị hủy"""
    result = payment_service.cancel_payment(payment_id, current_user.id, "Người dùng hủy thanh toán")
    
    if result.get("error"):
        flash(result["error"], 'danger')
        return redirect(url_for('renter.dashboard'))
    
    from app.models.models import Payment
    payment = Payment.query.get(payment_id)
    booking = payment.booking
    
    flash('Thanh toán đã bị hủy.', 'warning')
    return redirect(url_for('renter.booking_details', booking_id=booking.id))

@payment_bp.route('/timeout/<int:payment_id>')
@login_required
def payment_timeout(payment_id):
    """Trang thanh toán hết hạn"""
    result = payment_service.cancel_payment(payment_id, current_user.id, "Thanh toán hết hạn")
    
    if result.get("error"):
        flash(result["error"], 'danger')
        return redirect(url_for('renter.dashboard'))
    
    flash('Thời gian thanh toán đã hết hạn.', 'warning')
    return redirect(url_for('payment.payment_failed', payment_id=payment_id))

@payment_bp.route('/retry/<int:payment_id>')
@login_required
def retry_payment(payment_id):
    """Thử lại thanh toán"""
    from app.models.models import Payment
    payment = Payment.query.get_or_404(payment_id)
    booking = payment.booking
    
    # Kiểm tra quyền
    if payment.renter_id != current_user.id:
        flash('Bạn không có quyền thực hiện thao tác này.', 'danger')
        return redirect(url_for('renter.dashboard'))
    
    current_app.logger.info(f'[PAYMENT] User {current_user.id} retry payment cho booking {booking.id}, payment {payment.payment_code}.')
    # Chuyển hướng về trang checkout
    return redirect(url_for('payment.checkout', booking_id=booking.id))

@payment_bp.route('/cancel/<int:payment_id>')
@login_required
def cancel_payment(payment_id):
    """Hủy thanh toán"""
    result = payment_service.cancel_payment(payment_id, current_user.id, "Hủy bởi người dùng")
    
    if result.get("error"):
        flash(result["error"], 'danger')
        return redirect(url_for('renter.dashboard'))
    
    from app.models.models import Payment
    payment = Payment.query.get(payment_id)
    booking = payment.booking
    
    flash('Thanh toán đã được hủy.', 'info')
    return redirect(url_for('renter.booking_details', booking_id=booking.id))

# =============================================================================
# API ROUTES (JSON Responses)
# =============================================================================

@payment_bp.route('/api/create', methods=['POST'])
@login_required
@payos_rate_limit
@enforce_payment_creation_limits(user_daily_limit=5, ip_minute_limit=20, ip_hour_limit=200)
def api_create_payment():
    """
    API tạo link thanh toán cho booking
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "Dữ liệu không hợp lệ"}), 400
        
        booking_id = data.get('booking_id')
        return_url = data.get('return_url')
        cancel_url = data.get('cancel_url')
        
        if not booking_id:
            return jsonify({"error": "Thiếu booking_id"}), 400
        
        # Sử dụng payment service để tạo payment
        result = payment_service.create_payment(
            booking_id=booking_id,
            user_id=current_user.id,
            return_url=return_url,
            cancel_url=cancel_url
        )
        
        if result.get("error"):
            return jsonify({"error": result["error"]}), result.get("status", 500)
        
        # Gửi thông báo tạo payment
        from app.models.models import Payment
        payment = Payment.query.get(result["payment_id"])
        if payment:
            notification_result = payment_notification_service.send_payment_created_notification(payment)
            current_app.logger.info(f'[PAYMENT_API] Notification sent: {notification_result}')
        
        return jsonify({
            "success": True,
            "payment_id": result["payment_id"],
            "payment_code": result["payment_code"],
            "checkout_url": result["checkout_url"],
            "redirect_url": result["redirect_url"],
            "payos_data": result.get("payos_data", {})
        })
        
    except Exception as e:
        current_app.logger.error(f"Lỗi khi tạo payment: {str(e)}")
        return jsonify({"error": "Lỗi server"}), 500

@payment_bp.route('/api/<int:payment_id>/status', methods=['GET'])
@login_required
@payos_rate_limit
def api_get_payment_status(payment_id):
    """
    API lấy trạng thái payment
    """
    try:
        result = payment_service.get_payment_status(payment_id, current_user.id)
        
        if result.get("error"):
            return jsonify({"error": result["error"]}), result.get("status", 500)
        
        payment_data = result["payment"]
        
        return jsonify({
            "payment_id": payment_data["id"],
            "payment_code": payment_data["payment_code"],
            "order_code": payment_data["order_code"],
            "amount": payment_data["amount"],
            "status": payment_data["status"],
            "status_text": payment_data["status_text"],
            "payment_method": payment_data["payment_method"],
            "created_at": payment_data["created_at"],
            "paid_at": payment_data["paid_at"],
            "description": payment_data["description"]
        })
        
    except Exception as e:
        current_app.logger.error(f"Lỗi khi lấy payment status: {str(e)}")
        return jsonify({"error": "Lỗi server"}), 500

@payment_bp.route('/api/<int:payment_id>/cancel', methods=['POST'])
@login_required
@payos_rate_limit
def api_cancel_payment(payment_id):
    """
    API hủy payment
    """
    try:
        result = payment_service.cancel_payment(payment_id, current_user.id, "Hủy bởi người dùng")
        
        if result.get("error"):
            return jsonify({"error": result["error"]}), result.get("status", 500)
        
        # Gửi thông báo hủy
        from app.models.models import Payment
        payment = Payment.query.get(payment_id)
        if payment:
            notification_result = payment_notification_service.send_payment_cancelled_notification(
                payment, "Hủy bởi người dùng"
            )
            current_app.logger.info(f"Cancel notification sent: {notification_result}")
        
        return jsonify({
            "success": True,
            "message": result["message"],
            "payment_id": result["payment_id"],
            "status": result["status"]
        })
        
    except Exception as e:
        current_app.logger.error(f"Lỗi khi hủy payment: {str(e)}")
        return jsonify({"error": "Lỗi server"}), 500

@payment_bp.route('/api/list', methods=['GET'])
@login_required
@payos_rate_limit
def api_list_payments():
    """
    API lấy danh sách payment của user
    """
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        status = request.args.get('status')
        
        # Xác định user type
        user_type = 'renter' if current_user.is_renter() else 'owner' if current_user.is_owner() else None
        if not user_type:
            return jsonify({"error": "Không có quyền truy cập"}), 403
        
        result = payment_service.get_payment_list(
            user_id=current_user.id,
            user_type=user_type,
            page=page,
            per_page=per_page,
            status=status
        )
        
        if result.get("error"):
            return jsonify({"error": result["error"]}), result.get("status", 500)
        
        return jsonify({
            "payments": result["payments"],
            "pagination": result["pagination"]
        })
        
    except Exception as e:
        current_app.logger.error(f"Lỗi khi lấy danh sách payment: {str(e)}")
        return jsonify({"error": "Lỗi server"}), 500

@payment_bp.route('/api/<int:payment_id>/auto-cancel', methods=['POST'])
@payos_rate_limit
def api_auto_cancel_payment(payment_id):
    """
    API tự động hủy payment sau 5 phút
    """
    try:
        from app.models.models import Payment
        payment = Payment.query.get(payment_id)
        if not payment:
            return jsonify({"error": "Payment không tồn tại"}), 404
        
        # Chỉ cho phép hủy payment đang pending
        if payment.status != 'pending':
            return jsonify({
                "success": True,
                "message": "Payment đã không còn pending",
                "payment_id": payment.id,
                "status": payment.status
            })
        
        # Kiểm tra thời gian tạo payment
        time_diff = datetime.utcnow() - payment.created_at
        if time_diff.total_seconds() < 300:  # 5 phút = 300 giây
            return jsonify({
                "success": False,
                "message": "Payment chưa đủ 5 phút để tự động hủy",
                "payment_id": payment.id,
                "time_elapsed": time_diff.total_seconds()
            }), 400
        
        # Sử dụng payment service để hủy
        result = payment_service.cancel_payment(payment_id, payment.renter_id, "Tự động hủy sau 5 phút")
        
        if result.get("error"):
            return jsonify({"error": result["error"]}), result.get("status", 500)
        
        # Gửi thông báo hủy
        notification_result = payment_notification_service.send_payment_cancelled_notification(
            payment, "Tự động hủy sau 5 phút"
        )
        current_app.logger.info(f'AUTO_CANCEL notification sent: {notification_result}')
        
        return jsonify({
            "success": True,
            "message": result["message"],
            "payment_id": result["payment_id"],
            "status": result["status"],
            "time_elapsed": time_diff.total_seconds()
        })
        
    except Exception as e:
        current_app.logger.error(f"Lỗi khi tự động hủy payment: {str(e)}")
        return jsonify({"error": "Lỗi server"}), 500

@payment_bp.route('/api/config', methods=['GET'])
@login_required
def api_get_payment_config():
    """
    API lấy cấu hình PayOS của owner
    """
    try:
        if not current_user.is_owner():
            return jsonify({"error": "Chỉ owner mới có thể truy cập"}), 403
        
        result = payment_configuration_service.get_payment_config(current_user.id)
        
        if result.get("error"):
            return jsonify({"error": result["error"]}), result.get("status", 500)
        
        return jsonify({
            "success": True,
            "config": result["config"]
        })
        
    except Exception as e:
        current_app.logger.error(f"Lỗi khi lấy cấu hình payment: {str(e)}")
        return jsonify({"error": "Lỗi server"}), 500

@payment_bp.route('/api/config', methods=['POST'])
@login_required
def api_create_payment_config():
    """
    API tạo/cập nhật cấu hình PayOS
    """
    try:
        if not current_user.is_owner():
            return jsonify({"error": "Chỉ owner mới có thể tạo cấu hình"}), 403
        
        data = request.get_json()
        if not data:
            return jsonify({"error": "Dữ liệu không hợp lệ"}), 400
        
        result = payment_configuration_service.create_payment_config(current_user.id, data)
        
        if result.get("error"):
            return jsonify({"error": result["error"]}), result.get("status", 500)
        
        return jsonify({
            "success": True,
            "message": result["message"],
            "config": {
                "id": result["config"].id,
                "owner_id": result["config"].owner_id,
                "is_active": result["config"].is_active,
                "created_at": result["config"].created_at.isoformat() if result["config"].created_at else None,
                "updated_at": result["config"].updated_at.isoformat() if result["config"].updated_at else None
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Lỗi khi tạo cấu hình payment: {str(e)}")
        return jsonify({"error": "Lỗi server"}), 500

@payment_bp.route('/api/config/test', methods=['POST'])
@login_required
def api_test_payment_config():
    """
    API test cấu hình PayOS
    """
    try:
        if not current_user.is_owner():
            return jsonify({"error": "Chỉ owner mới có thể test cấu hình"}), 403
        
        result = payment_configuration_service.test_payment_config(current_user.id)
        
        if result.get("error"):
            return jsonify({"error": result["error"]}), result.get("status", 500)
        
        return jsonify({
            "success": True,
            "message": result["message"],
            "config": result["config"]
        })
        
    except Exception as e:
        current_app.logger.error(f"Lỗi khi test cấu hình payment: {str(e)}")
        return jsonify({"error": "Lỗi server"}), 500

# =============================================================================
# UTILITY ROUTES (AJAX/JSON)
# =============================================================================

@payment_bp.route('/check-status/<int:payment_id>')
@login_required
@payos_rate_limit
def check_payment_status(payment_id):
    """API kiểm tra trạng thái thanh toán"""
    result = payment_service.get_payment_status(payment_id, current_user.id)
    
    if result.get("error"):
        return jsonify({'status': 'error', 'message': result["error"]}), result.get("status", 500)
    
    payment_data = result["payment"]
    
    return jsonify({
        'status': payment_data['status'],
        'payment_code': payment_data['payment_code'],
        'amount': payment_data['amount'],
        'formatted_amount': f"{payment_data['amount']:,.0f} VND",
        'created_at': payment_data['created_at'],
        'checkout_url': payment_data['checkout_url'],
        'qr_code': payment_data['qr_code'],
        'account_info': payment_data['account_info']
    })

@payment_bp.route('/refresh-status/<int:payment_id>')
@login_required
@payos_rate_limit
def refresh_payment_status(payment_id):
    """Refresh trạng thái thanh toán từ PayOS hoặc database"""
    result = payment_service.refresh_payment_status(payment_id, current_user.id)
    
    if result.get("error"):
        return jsonify({'status': 'error', 'message': result["error"]}), result.get("status", 500)
    
    return jsonify({
        'status': result['status'],
        'message': result['message'],
        'payment_status': result['payment_status'],
        'redirect': result.get('redirect')
    })

@payment_bp.route('/qr-data/<int:payment_id>')
@login_required
def get_qr_data(payment_id):
    """API trả về QR data để tạo QR code động"""
    result = payment_service.get_payment_status(payment_id, current_user.id)
    
    if result.get("error"):
        return jsonify({'status': 'error', 'message': result["error"]}), result.get("status", 500)
    
    payment_data = result["payment"]
    qr_code = payment_data.get('qr_code')
    
    if not qr_code:
        return jsonify({'status': 'error', 'message': 'QR code not available'})
    
    return jsonify({
        'status': 'success',
        'qr_data': qr_code,
        'payment_info': {
            'account_number': payment_data.get('account_info', {}).get('account_number'),
            'account_name': payment_data.get('account_info', {}).get('account_name'),
            'bank_name': payment_data.get('account_info', {}).get('bank_name'),
            'amount': payment_data['amount'],
            'formatted_amount': f"{payment_data['amount']:,.0f} VND",
            'description': payment_data['description'],
            'order_code': payment_data['order_code']
        }
    })

@payment_bp.route('/get-qr/<int:payment_id>')
@login_required
@payos_rate_limit
def get_qr_direct(payment_id):
    """Lấy QR code trực tiếp từ PayOS API hoặc database"""
    result = payment_service.get_payment_status(payment_id, current_user.id)
    
    if result.get("error"):
        return jsonify({'error': result["error"]}), result.get("status", 500)
    
    payment_data = result["payment"]
    
    # Nếu có QR trong cache, dùng luôn
    if payment_data.get('qr_code'):
        return jsonify({
            'success': True,
            'qr_code': payment_data['qr_code'],
            'account_number': payment_data.get('account_info', {}).get('account_number'),
            'account_name': payment_data.get('account_info', {}).get('account_name'),
            'bank_name': payment_data.get('account_info', {}).get('bank_name', 'Ngân hàng TMCP Quân đội (MB Bank)'),
            'amount': payment_data['amount'],
            'description': payment_data['description'],
            'status': 'PENDING'
        })
    
    # Nếu không có cache, trả về lỗi
    return jsonify({'error': 'QR code not available in cache'})
