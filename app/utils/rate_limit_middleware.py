"""
Rate Limit Middleware - Thêm thông tin rate limit vào response headers
"""

from flask import request, g
from app.utils.rate_limiter import get_rate_limit_headers, check_rate_limit_status

def add_rate_limit_headers(response):
    """
    Middleware để thêm rate limit headers vào response
    """
    # Chỉ áp dụng cho PayOS routes
    if request.endpoint and ('payment' in request.endpoint or 'webhook' in request.endpoint):
        try:
            headers = get_rate_limit_headers()
            for key, value in headers.items():
                response.headers[key] = value
        except Exception as e:
            # Log lỗi nhưng không làm crash app
            from flask import current_app
            current_app.logger.error(f"Error adding rate limit headers: {e}")
    
    return response

def before_request_rate_limit():
    """
    Middleware chạy trước mỗi request để kiểm tra rate limit
    """
    # Chỉ áp dụng cho PayOS routes
    if request.endpoint and ('payment' in request.endpoint or 'webhook' in request.endpoint):
        try:
            status = check_rate_limit_status()
            if status and status.get('limit_reached'):
                from flask import jsonify
                return jsonify({
                    'error': 'Rate limit exceeded',
                    'message': 'Bạn đã vượt quá giới hạn 100 request/giờ. Vui lòng thử lại sau.',
                    'retry_after': status.get('reset_time', 3600)
                }), 429
        except Exception as e:
            # Log lỗi nhưng không làm crash app
            from flask import current_app
            current_app.logger.error(f"Error checking rate limit: {e}")
    
    return None
