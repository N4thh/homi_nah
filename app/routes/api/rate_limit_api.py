"""
Rate Limit API - Cung cấp thông tin về rate limiting
"""

from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app.utils.rate_limiter import check_rate_limit_status, get_rate_limit_headers

rate_limit_api = Blueprint('rate_limit_api', __name__)

@rate_limit_api.route('/api/rate-limit/status', methods=['GET'])
@login_required
def get_rate_limit_status():
    """
    API lấy trạng thái rate limit hiện tại của user
    """
    try:
        status = check_rate_limit_status()
        
        if not status:
            return jsonify({
                'error': 'Rate limiter not available',
                'message': 'Rate limiter chưa được khởi tạo'
            }), 500
        
        return jsonify({
            'success': True,
            'rate_limit': {
                'remaining': status.get('remaining', 0),
                'reset_time': status.get('reset_time', 0),
                'limit_reached': status.get('limit_reached', False),
                'user_key': f"user:{current_user.id}:{current_user.__class__.__name__.lower()}" if current_user.is_authenticated else f"ip:{request.remote_addr}"
            }
        })
        
    except Exception as e:
        return jsonify({
            'error': 'Internal server error',
            'message': str(e)
        }), 500

@rate_limit_api.route('/api/rate-limit/info', methods=['GET'])
def get_rate_limit_info():
    """
    API lấy thông tin về cấu hình rate limiting
    """
    return jsonify({
        'success': True,
        'rate_limit_config': {
            'limits': [
                '100 requests per hour',
                '10 requests per minute', 
                '3 requests per 10 seconds'
            ],
            'strategy': 'fixed-window',
            'key_method': 'user_id_or_ip',
            'description': 'Rate limiting áp dụng cho tất cả PayOS endpoints'
        }
    })
