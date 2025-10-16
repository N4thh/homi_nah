"""
Common Decorators for Routes - Consolidate duplicate decorator logic
"""

from functools import wraps
from flask import flash, redirect, url_for, jsonify, request
from flask_login import login_required, current_user


def role_required(role_type, redirect_url='home'):
    """
    Generic role-based decorator
    
    Args:
        role_type (str): Type of role ('owner', 'renter', 'admin')
        redirect_url (str): URL to redirect to if unauthorized
    
    Usage:
        @role_required('owner')
        def owner_dashboard():
            pass
    """
    def decorator(f):
        @wraps(f)
        @login_required
        def decorated_function(*args, **kwargs):
            # Check if user has the required role
            if not getattr(current_user, f'is_{role_type}', lambda: False)():
                if request.headers.get('Content-Type') == 'application/json':
                    return jsonify({
                        'success': False, 
                        'message': f'You must be a {role_type} to access this page'
                    }), 403
                
                flash(f'You must be a {role_type} to access this page', 'danger')
                return redirect(url_for(redirect_url))
            
            return f(*args, **kwargs)
        decorated_function.__name__ = f.__name__
        return decorated_function
    return decorator


def email_verification_required(role_type):
    """
    Generic email verification decorator
    
    Args:
        role_type (str): Type of role ('owner', 'renter')
    
    Usage:
        @email_verification_required('owner')
        def owner_action():
            pass
    """
    def decorator(f):
        @wraps(f)
        @role_required(role_type)
        def decorated_function(*args, **kwargs):
            # Check email verification
            if not current_user.email_verified:
                if request.headers.get('Content-Type') == 'application/json':
                    return jsonify({
                        'success': False, 
                        'message': 'Email verification required'
                    }), 403
                
                flash('Vui lòng xác thực email trước khi sử dụng hệ thống', 'warning')
                return redirect(url_for(f'{role_type}_dashboard.verify_email'))
            
            return f(*args, **kwargs)
        decorated_function.__name__ = f.__name__
        return decorated_function
    return decorator


def admin_required(f):
    """
    Decorator to check if user is admin
    
    Usage:
        @admin_required
        def admin_dashboard():
            pass
    """
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        from app.models.models import Admin
        
        if not isinstance(current_user, Admin):
            if request.headers.get('Content-Type') == 'application/json':
                return jsonify({
                    'success': False, 
                    'message': 'Admin access required'
                }), 403
            
            flash("Bạn không có quyền truy cập!", "danger")
            return redirect(url_for('auth.login'))
        
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function


def super_admin_required(f):
    """
    Decorator to check if user is super admin
    
    Usage:
        @super_admin_required
        def super_admin_action():
            pass
    """
    @wraps(f)
    @admin_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_super_admin:
            if request.headers.get('Content-Type') == 'application/json':
                return jsonify({
                    'success': False, 
                    'message': 'Super admin access required'
                }), 403
            
            flash('Bạn không có quyền truy cập trang này.', 'danger')
            return redirect(url_for('admin_dashboard.dashboard'))
        
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function


def api_required(f):
    """
    Decorator for API endpoints that require JSON response
    
    Usage:
        @api_required
        def api_endpoint():
            pass
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Ensure JSON response for API endpoints
        if request.headers.get('Content-Type') != 'application/json':
            return jsonify({
                'success': False, 
                'message': 'Content-Type must be application/json'
            }), 400
        
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function


def password_change_api_required(f):
    """
    Decorator for password change API endpoints
    
    Usage:
        @password_change_api_required
        def change_password():
            pass
    """
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({
                'success': False, 
                'message': 'Bạn phải đăng nhập để thực hiện thao tác này'
            }), 401
        
        if not current_user.is_renter():
            return jsonify({
                'success': False, 
                'message': 'Chỉ Renter mới có thể đổi mật khẩu'
            }), 403
        
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function


def require_email_verification_for_booking(f):
    """
    Decorator to check email verification for booking actions
    
    Usage:
        @require_email_verification_for_booking
        def book_home():
            pass
    """
    @wraps(f)
    @role_required('renter')
    def decorated_function(*args, **kwargs):
        # Check email verification for booking
        if not current_user.email_verified:
            if request.headers.get('Content-Type') == 'application/json':
                return jsonify({
                    'success': False, 
                    'message': 'Email verification required for booking'
                }), 403
            
            flash('Vui lòng xác thực email trước khi thực hiện đặt phòng', 'warning')
            return redirect(url_for('renter_dashboard.verify_email'))
        
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function


# Convenience decorators for common use cases
owner_required = role_required('owner')
renter_required = role_required('renter')
owner_email_verified = email_verification_required('owner')
renter_email_verified = email_verification_required('renter')
