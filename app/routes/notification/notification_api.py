"""
Notification API - Xử lý thông báo real-time
"""
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from app.models.models import Payment, Booking, db
from app.utils.notification_service import notification_service
import logging
from datetime import datetime, timedelta

notification_api_bp = Blueprint('notification_api', __name__)

@notification_api_bp.route('/api/notifications/payment-success/<int:payment_id>', methods=['GET'])
@login_required
def get_payment_notification(payment_id):
    """
    Lấy thông báo payment success cho user
    """
    try:
        # Kiểm tra payment có tồn tại không
        payment = Payment.query.get(payment_id)
        if not payment:
            return jsonify({"error": "Payment không tồn tại"}), 404
        
        # Kiểm tra quyền truy cập
        if payment.booking.renter_id != current_user.id and payment.booking.home.owner_id != current_user.id:
            return jsonify({"error": "Không có quyền truy cập"}), 403
        
        # Tạo thông báo
        notification_data = {
            "type": "payment_success",
            "title": "Thanh toán thành công",
            "message": f"Thanh toán {payment.amount:,} VND đã được xử lý thành công",
            "payment_id": payment.id,
            "booking_id": payment.booking_id,
            "amount": payment.amount,
            "timestamp": payment.paid_at.isoformat() if payment.paid_at else datetime.utcnow().isoformat()
        }
        
        return jsonify({
            "success": True,
            "notification": notification_data
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting payment notification: {str(e)}")
        return jsonify({"error": "Lỗi server"}), 500

@notification_api_bp.route('/api/notifications/user/<int:user_id>', methods=['GET'])
@login_required
def get_user_notifications(user_id):
    """
    Lấy tất cả thông báo của user
    """
    try:
        # Kiểm tra quyền truy cập
        if current_user.id != user_id:
            return jsonify({"error": "Không có quyền truy cập"}), 403
        
        # Lấy thông báo từ service
        notifications = notification_service.get_user_notifications(user_id)
        
        return jsonify({
            "success": True,
            "notifications": notifications
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting user notifications: {str(e)}")
        return jsonify({"error": "Lỗi server"}), 500

@notification_api_bp.route('/api/notifications/owner/<int:owner_id>', methods=['GET'])
@login_required
def get_owner_notifications(owner_id):
    """
    Lấy thông báo của owner
    """
    try:
        # Kiểm tra quyền truy cập
        if current_user.id != owner_id or not current_user.is_owner():
            return jsonify({"error": "Không có quyền truy cập"}), 403
        
        # Lấy thông báo từ service
        notifications = notification_service.get_owner_notifications(owner_id)
        
        return jsonify({
            "success": True,
            "notifications": notifications
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting owner notifications: {str(e)}")
        return jsonify({"error": "Lỗi server"}), 500

@notification_api_bp.route('/api/notifications/check-new', methods=['POST'])
@login_required
def check_new_notifications():
    """
    Kiểm tra thông báo mới
    """
    try:
        data = request.get_json()
        last_check = data.get('last_check')
        
        if last_check:
            last_check_dt = datetime.fromisoformat(last_check.replace('Z', '+00:00'))
        else:
            last_check_dt = datetime.utcnow() - timedelta(hours=1)
        
        # Lấy thông báo mới
        new_notifications = notification_service.get_new_notifications(
            current_user.id, 
            last_check_dt
        )
        
        return jsonify({
            "success": True,
            "new_notifications": new_notifications,
            "count": len(new_notifications)
        })
        
    except Exception as e:
        current_app.logger.error(f"Error checking new notifications: {str(e)}")
        return jsonify({"error": "Lỗi server"}), 500

@notification_api_bp.route('/api/notifications/mark-read/<int:notification_id>', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    """
    Đánh dấu thông báo đã đọc
    """
    try:
        # Đánh dấu đã đọc
        success = notification_service.mark_notification_read(
            notification_id, 
            current_user.id
        )
        
        if success:
            return jsonify({"success": True, "message": "Đã đánh dấu đã đọc"})
        else:
            return jsonify({"error": "Không thể đánh dấu đã đọc"}), 400
        
    except Exception as e:
        current_app.logger.error(f"Error marking notification read: {str(e)}")
        return jsonify({"error": "Lỗi server"}), 500

