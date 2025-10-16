"""
Notification Helper Functions for Flask Routes
"""

from flask import flash, request, jsonify
import json

def show_notification(type='info', title='', message='', duration=5000):
    """
    Show a notification popup
    
    Args:
        type (str): Notification type ('success', 'error', 'warning', 'info')
        title (str): Notification title
        message (str): Notification message
        duration (int): Duration in milliseconds (default: 5000)
    """
    # For AJAX requests, return JSON response
    if request.headers.get('Content-Type') == 'application/json' or request.is_json:
        return jsonify({
            'success': True,
            'notification': {
                'type': type,
                'title': title,
                'message': message,
                'duration': duration
            }
        })
    
    # For regular requests, use flash messages
    flash(message, type)
    return None

def show_success(title='Thành công', message='', duration=5000):
    """Show success notification"""
    return show_notification('success', title, message, duration)

def show_error(title='Lỗi', message='', duration=5000):
    """Show error notification"""
    return show_notification('error', title, message, duration)

def show_warning(title='Cảnh báo', message='', duration=5000):
    """Show warning notification"""
    return show_notification('warning', title, message, duration)

def show_info(title='Thông báo', message='', duration=5000):
    """Show info notification"""
    return show_notification('info', title, message, duration)

# Convenience functions for common operations
def notify_login_success():
    """Notify successful login"""
    return show_success('Đăng nhập thành công', 'Chào mừng bạn quay trở lại!')

def notify_logout_success():
    """Notify successful logout"""
    return show_success('Đăng xuất thành công', 'Hẹn gặp lại bạn!')

def notify_booking_success():
    """Notify successful booking"""
    return show_success('Đặt phòng thành công', 'Chúng tôi sẽ liên hệ với bạn sớm nhất!')

def notify_payment_success():
    """Notify successful payment"""
    return show_success('Thanh toán thành công', 'Giao dịch đã được xử lý!')

def notify_profile_updated():
    """Notify profile update"""
    return show_success('Cập nhật thành công', 'Thông tin cá nhân đã được lưu!')

def notify_password_changed():
    """Notify password change"""
    return show_success('Đổi mật khẩu thành công', 'Mật khẩu đã được cập nhật!')

def notify_email_sent():
    """Notify email sent"""
    return show_info('Email đã được gửi', 'Vui lòng kiểm tra hộp thư của bạn!')

def notify_operation_failed(message='Có lỗi xảy ra'):
    """Notify operation failed"""
    return show_error('Thao tác thất bại', message)

def notify_validation_error(message='Dữ liệu không hợp lệ'):
    """Notify validation error"""
    return show_error('Lỗi xác thực', message)

def notify_permission_denied():
    """Notify permission denied"""
    return show_error('Không có quyền', 'Bạn không có quyền thực hiện thao tác này!')

def notify_not_found(resource='Tài nguyên'):
    """Notify resource not found"""
    return show_error('Không tìm thấy', f'{resource} không tồn tại!')
