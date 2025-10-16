"""
Webhook Handler - Unified với Services Architecture
"""

from flask import Blueprint, request, jsonify, current_app
from datetime import datetime
import logging
import traceback
import json

from app.services.payment import (
    payment_service,
    payment_notification_service,
    payment_configuration_service
)
from app.utils.rate_limiter import payos_rate_limit

webhook_bp = Blueprint('webhook', __name__)

# =============================================================================
# PAYOS WEBHOOK HANDLERS
# =============================================================================

@webhook_bp.route('/webhook/payos', methods=['POST'])
@payos_rate_limit
def payos_webhook():
    """
    Webhook endpoint nhận callback từ PayOS
    Không cần authentication vì đây là callback từ bên ngoài
    """
    try:
        # Log webhook request
        current_app.logger.info("Received PayOS webhook")
        
        # Lấy dữ liệu từ webhook
        data = request.get_json()
        if not data:
            current_app.logger.error("Webhook: Không có dữ liệu JSON")
            return jsonify({"error": "Không có dữ liệu"}), 400
        
        # Log dữ liệu webhook (che giấu thông tin nhạy cảm)
        log_data = data.copy()
        if 'signature' in log_data:
            log_data['signature'] = '***'
        current_app.logger.info(f"Webhook data: {log_data}")
        
        # Lấy chữ ký từ header
        received_signature = request.headers.get('x-signature', '')
        if not received_signature:
            current_app.logger.error("Webhook: Không có chữ ký trong header")
            return jsonify({"error": "Không có chữ ký"}), 400
        
        # Lấy order_code từ dữ liệu
        order_code = data.get('orderCode')
        if not order_code:
            current_app.logger.error("Webhook: Không có orderCode")
            return jsonify({"error": "Không có orderCode"}), 400
        
        # Tìm payment record
        from app.models.models import Payment
        payment = Payment.query.filter_by(order_code=order_code).first()
        if not payment:
            current_app.logger.error(f"Webhook: Không tìm thấy payment với order_code {order_code}")
            return jsonify({"error": "Payment không tồn tại"}), 404
        
        # Lấy cấu hình PayOS
        config_result = payment_configuration_service.get_payment_config(payment.owner_id)
        if not config_result["success"]:
            current_app.logger.error(f"Webhook: Không tìm thấy config cho owner {payment.owner_id}")
            return jsonify({"error": "Cấu hình PayOS không tồn tại"}), 400
        
        # Tạo PayOS service và xác thực chữ ký
        from app.services.payos_service import PayOSService
        config = config_result["config"]
        payos = PayOSService(
            config["payos_client_id"],
            config["payos_api_key"],
            config["payos_checksum_key"]
        )
        
        if not payos.verify_webhook_signature(data, received_signature):
            current_app.logger.error(f"Webhook: Chữ ký không hợp lệ cho order_code {order_code}")
            return jsonify({"error": "Chữ ký không hợp lệ"}), 400
        
        # Xử lý trạng thái payment
        payos_status = data.get('status', '').lower()
        trans_id = data.get('transId')
        payment_method = data.get('paymentMethod', 'unknown')
        
        current_app.logger.info(f"Processing payment {order_code} with status: {payos_status}")
        
        if payos.is_payment_successful(payos_status):
            # Thanh toán thành công
            payment.mark_as_successful(
                payos_transaction_id=trans_id,
                payment_method=payment_method
            )
            payment.booking.payment_status = 'paid'
            payment.booking.payment_date = datetime.utcnow()
            payment.booking.status = 'confirmed'
            
            current_app.logger.info(f"Payment {order_code} marked as successful")
            
            # DEBUG: Thêm logging chi tiết
            print(f"🔍 DEBUG WEBHOOK: Payment successful - {order_code}")
            print(f"🔍 DEBUG WEBHOOK: Payment ID: {payment.id}")
            print(f"🔍 DEBUG WEBHOOK: Customer email: {payment.customer_email}")
            print(f"🔍 DEBUG WEBHOOK: Booking ID: {payment.booking_id}")
            
            # Gửi thông báo và email sử dụng service
            try:
                print(f"🔍 DEBUG WEBHOOK: Starting notifications...")
                
                # DEBUG: Kiểm tra payment object
                print(f"🔍 DEBUG WEBHOOK: Payment object check:")
                print(f"  - payment.id: {payment.id}")
                print(f"  - payment.customer_email: {payment.customer_email}")
                print(f"  - payment.customer_name: {payment.customer_name}")
                print(f"  - payment.amount: {payment.amount}")
                print(f"  - payment.booking: {payment.booking}")
                
                if payment.booking:
                    print(f"  - booking.id: {payment.booking.id}")
                    print(f"  - booking.home: {payment.booking.home}")
                    if payment.booking.home:
                        print(f"  - home.title: {payment.booking.home.title}")
                        print(f"  - home.owner: {payment.booking.home.owner}")
                else:
                    print(f"❌ DEBUG WEBHOOK: Payment.booking is None!")
                
                # Sử dụng payment notification service
                notification_result = payment_notification_service.send_payment_success_notification(payment)
                print(f"🔍 DEBUG WEBHOOK: Notification result: {notification_result}")
                
                current_app.logger.info(f"Notifications sent successfully for payment {order_code}")
                print(f"✅ DEBUG WEBHOOK: All notifications completed!")
                
            except Exception as e:
                print(f"💥 DEBUG WEBHOOK: Exception in notifications: {str(e)}")
                print(f"💥 DEBUG WEBHOOK: Exception type: {type(e)}")
                traceback.print_exc()
                current_app.logger.error(f"Error sending notifications for payment {order_code}: {str(e)}")
            
        elif payos.is_payment_failed(payos_status):
            # Thanh toán thất bại
            payment.mark_as_failed(f"PayOS status: {payos_status}")
            payment.booking.payment_status = 'failed'
            current_app.logger.info(f"Payment {order_code} marked as failed")
            
            # Gửi thông báo thất bại
            try:
                notification_result = payment_notification_service.send_payment_failed_notification(
                    payment, f"PayOS status: {payos_status}"
                )
                current_app.logger.info(f"Failed notification sent: {notification_result}")
            except Exception as e:
                current_app.logger.error(f"Error sending failed notification: {str(e)}")
        
        else:
            # Trạng thái khác (pending, etc.)
            payment.status = payos_status
            payment.updated_at = datetime.utcnow()
            current_app.logger.info(f"Payment {order_code} status updated to: {payos_status}")
        
        from app.models.models import db
        db.session.commit()
        
        current_app.logger.info(f"Webhook processed successfully for order_code {order_code}")
        
        return jsonify({
            "success": True,
            "message": "Webhook processed successfully",
            "order_code": order_code,
            "status": payos_status
        })
        
    except Exception as e:
        current_app.logger.error(f"Lỗi khi xử lý webhook: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": "Lỗi server"}), 500

# =============================================================================
# WEBHOOK UTILITY ROUTES
# =============================================================================

@webhook_bp.route('/webhook/test', methods=['POST'])
def test_webhook():
    """
    Webhook test endpoint để kiểm tra webhook có hoạt động không
    """
    try:
        data = request.get_json()
        current_app.logger.info(f"Test webhook received: {data}")
        
        return jsonify({
            "success": True,
            "message": "Test webhook received successfully",
            "data": data
        })
        
    except Exception as e:
        current_app.logger.error(f"Lỗi khi xử lý test webhook: {str(e)}")
        return jsonify({"error": "Lỗi server"}), 500

@webhook_bp.route('/webhook/health', methods=['GET'])
def webhook_health():
    """
    Health check endpoint cho webhook
    """
    return jsonify({
        "status": "healthy",
        "message": "Webhook service is running",
        "timestamp": datetime.utcnow().isoformat()
    })

@webhook_bp.route('/webhook/payment-status/<order_code>', methods=['GET'])
def get_payment_status_by_order_code(order_code):
    """
    API lấy trạng thái payment theo order_code (cho webhook debugging)
    """
    try:
        from app.models.models import Payment
        
        payment = Payment.query.filter_by(order_code=order_code).first()
        if not payment:
            return jsonify({"error": "Payment không tồn tại"}), 404
        
        return jsonify({
            "success": True,
            "payment": {
                "id": payment.id,
                "payment_code": payment.payment_code,
                "order_code": payment.order_code,
                "status": payment.status,
                "amount": payment.amount,
                "customer_email": payment.customer_email,
                "customer_name": payment.customer_name,
                "created_at": payment.created_at.isoformat() if payment.created_at else None,
                "paid_at": payment.paid_at.isoformat() if payment.paid_at else None,
                "booking_id": payment.booking_id,
                "owner_id": payment.owner_id
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Lỗi khi lấy payment status: {str(e)}")
        return jsonify({"error": "Lỗi server"}), 500

# =============================================================================
# WEBHOOK DEBUGGING ROUTES
# =============================================================================

@webhook_bp.route('/webhook/debug/payment/<int:payment_id>', methods=['GET'])
def debug_payment_info(payment_id):
    """
    Debug endpoint để xem thông tin payment chi tiết
    """
    try:
        from app.models.models import Payment
        
        payment = Payment.query.get(payment_id)
        if not payment:
            return jsonify({"error": "Payment không tồn tại"}), 404
        
        # Parse PayOS data
        payos_data = {}
        if hasattr(payment, 'payos_signature') and payment.payos_signature:
            try:
                payos_data = json.loads(payment.payos_signature)
            except:
                payos_data = {}
        
        return jsonify({
            "success": True,
            "payment": {
                "id": payment.id,
                "payment_code": payment.payment_code,
                "order_code": payment.order_code,
                "status": payment.status,
                "amount": payment.amount,
                "customer_email": payment.customer_email,
                "customer_name": payment.customer_name,
                "created_at": payment.created_at.isoformat() if payment.created_at else None,
                "paid_at": payment.paid_at.isoformat() if payment.paid_at else None,
                "booking_id": payment.booking_id,
                "owner_id": payment.owner_id,
                "checkout_url": payment.checkout_url,
                "payos_transaction_id": payment.payos_transaction_id,
                "payos_data": payos_data
            },
            "booking": {
                "id": payment.booking.id if payment.booking else None,
                "status": payment.booking.status if payment.booking else None,
                "payment_status": payment.booking.payment_status if payment.booking else None,
                "home_title": payment.booking.home.title if payment.booking and payment.booking.home else None
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Lỗi khi debug payment: {str(e)}")
        return jsonify({"error": "Lỗi server"}), 500

@webhook_bp.route('/webhook/debug/config/<int:owner_id>', methods=['GET'])
def debug_payment_config(owner_id):
    """
    Debug endpoint để xem cấu hình PayOS của owner
    """
    try:
        result = payment_configuration_service.get_payment_config(owner_id)
        
        if not result["success"]:
            return jsonify({"error": result["error"]}), result.get("status", 500)
        
        config = result["config"]
        
        return jsonify({
            "success": True,
            "config": {
                "id": config["id"],
                "owner_id": config["owner_id"],
                "is_active": config["is_active"],
                "created_at": config["created_at"],
                "updated_at": config["updated_at"],
                "has_client_id": bool(config.get("payos_client_id")),
                "has_api_key": bool(config.get("payos_api_key")),
                "has_checksum_key": bool(config.get("payos_checksum_key"))
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Lỗi khi debug config: {str(e)}")
        return jsonify({"error": "Lỗi server"}), 500
