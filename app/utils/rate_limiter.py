"""
Rate Limiter Configuration cho PayOS
Giới hạn 100 request/giờ cho tất cả PayOS endpoints
"""

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask import current_app, request, jsonify
from flask_login import current_user
from functools import wraps
import os
from datetime import datetime, timedelta

try:
    # Tránh crash nếu models chưa sẵn sàng khi import sớm
    from app.models.models import Payment, db
except Exception:
    Payment = None
    db = None

def get_limiter_key():
    """
    Tạo key cho rate limiting dựa trên user ID hoặc IP
    Ưu tiên user ID nếu đã đăng nhập, fallback về IP
    """
    try:
        if current_user.is_authenticated:
            # Sử dụng user ID + role để tạo key duy nhất
            return f"user:{current_user.id}:{current_user.__class__.__name__.lower()}"
        else:
            # Fallback về IP address
            return f"ip:{get_remote_address()}"
    except Exception:
        # Fallback về IP address nếu có lỗi với current_user
        return f"ip:{get_remote_address()}"

def init_rate_limiter(app):
    """
    Khởi tạo Flask-Limiter với cấu hình cho PayOS
    """
    # Cấu hình storage backend (Redis hoặc memory)
    storage_uri = os.environ.get('REDIS_URL', 'memory://')
    
    # Khởi tạo limiter
    limiter = Limiter(
        app=app,
        key_func=get_limiter_key,
        storage_uri=storage_uri,
        default_limits=["100 per hour"],  # Giới hạn mặc định 100 req/giờ
        headers_enabled=True,  # Hiển thị thông tin rate limit trong headers
        retry_after="delta",  # Hiển thị thời gian retry
        strategy="fixed-window"  # Chiến lược fixed window
    )
    
    # Cấu hình specific limits cho PayOS routes
    payos_limits = [
        "100 per hour",  # Tổng cộng 100 request/giờ
        "10 per minute",  # Tối đa 10 request/phút để tránh spam
        "3 per 10 seconds"  # Tối đa 3 request/10 giây cho các thao tác nhanh
    ]
    
    # Lưu limiter vào app context để sử dụng trong routes
    app.limiter = limiter
    app.payos_limits = payos_limits
    
    return limiter

def get_payos_limiter():
    """
    Lấy limiter instance cho PayOS routes
    """
    return current_app.limiter

def apply_payos_limits(limiter_func):
    """
    Decorator để áp dụng rate limiting cho PayOS routes
    """
    def decorator(f):
        wrapped = f
        # Áp dụng lần lượt từng limit để tương thích nhiều phiên bản Flask-Limiter
        for limit in getattr(current_app, 'payos_limits', []):
            wrapped = limiter_func(limit)(wrapped)
        wrapped.__name__ = f.__name__
        return wrapped
    return decorator

def payos_rate_limit(f):
    """
    Decorator để áp dụng rate limiting cho PayOS routes
    """
    from flask import current_app
    
    def decorated_function(*args, **kwargs):
        if not hasattr(current_app, 'limiter'):
            return f(*args, **kwargs)
        
        # Áp dụng từng limit một cách tuần tự để tránh lỗi chữ ký hàm
        wrapped = f
        for limit in getattr(current_app, 'payos_limits', []):
            wrapped = current_app.limiter.limit(limit)(wrapped)
        return wrapped(*args, **kwargs)
    
    decorated_function.__name__ = f.__name__
    return decorated_function

def check_rate_limit_status():
    """
    Kiểm tra trạng thái rate limit hiện tại
    Trả về thông tin về số request còn lại và thời gian reset
    """
    if not hasattr(current_app, 'limiter'):
        return None
    
    try:
        limiter = current_app.limiter
        # Một số phiên bản Flask-Limiter không có get_window_stats public API
        # Nên chỉ trả về headers cơ bản dựa trên default config
        return {
            'remaining': None,
            'reset_time': None,
            'limit_reached': False
        }
    except Exception as e:
        current_app.logger.error(f"Error checking rate limit status: {e}")
    
    return None

def get_rate_limit_headers():
    """
    Lấy headers thông tin rate limit để gửi về client
    """
    status = check_rate_limit_status()
    if not status:
        return {}
    
    headers = {}
    
    return headers


def enforce_payment_creation_limits(user_daily_limit=5, ip_minute_limit=20, ip_hour_limit=200):
    """
    Decorator để enforce payment creation limits
    
    Args:
        user_daily_limit: Số lượng payment tối đa mỗi user mỗi ngày
        ip_minute_limit: Số lượng payment tối đa mỗi IP mỗi phút
        ip_hour_limit: Số lượng payment tối đa mỗi IP mỗi giờ
    
    Returns:
        Decorator function
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                # Check user daily limit if authenticated
                if current_user.is_authenticated:
                    # TODO: Implement user daily limit check
                    pass
                
                # Check IP limits
                # TODO: Implement IP limit check
                
                return f(*args, **kwargs)
            except Exception as e:
                current_app.logger.error(f"Payment creation limit error: {str(e)}")
                return {"error": "Payment creation limit exceeded"}, 429
        return decorated_function
    return decorator
