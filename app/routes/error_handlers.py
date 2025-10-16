"""
Common Error Handlers for Routes - Standardize error handling patterns
"""

from flask import jsonify, current_app, render_template, request
from functools import wraps
from sqlalchemy.exc import IntegrityError
from werkzeug.exceptions import BadRequest, NotFound, Forbidden


def handle_api_errors(f):
    """
    Standard error handler for API endpoints
    
    Usage:
        @handle_api_errors
        def api_endpoint():
            pass
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except ValueError as e:
            current_app.logger.warning(f"ValueError in {f.__name__}: {str(e)}")
            return jsonify({
                "success": False, 
                "error": str(e)
            }), 400
        except PermissionError as e:
            current_app.logger.warning(f"PermissionError in {f.__name__}: {str(e)}")
            return jsonify({
                "success": False, 
                "error": "Unauthorized access"
            }), 403
        except NotFound as e:
            current_app.logger.warning(f"NotFound in {f.__name__}: {str(e)}")
            return jsonify({
                "success": False, 
                "error": "Resource not found"
            }), 404
        except IntegrityError as e:
            current_app.logger.error(f"IntegrityError in {f.__name__}: {str(e)}")
            return jsonify({
                "success": False, 
                "error": "Data integrity violation"
            }), 409
        except Exception as e:
            current_app.logger.error(f"Unexpected error in {f.__name__}: {str(e)}")
            return jsonify({
                "success": False, 
                "error": "Internal server error"
            }), 500
    return decorated_function


def handle_web_errors(f):
    """
    Standard error handler for web endpoints
    
    Usage:
        @handle_web_errors
        def web_endpoint():
            pass
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except ValueError as e:
            current_app.logger.warning(f"ValueError in {f.__name__}: {str(e)}")
            from flask import flash
            flash(f"Lỗi dữ liệu: {str(e)}", 'danger')
            return render_template('error.html', error=str(e), status_code=400), 400
        except PermissionError as e:
            current_app.logger.warning(f"PermissionError in {f.__name__}: {str(e)}")
            from flask import flash
            flash("Bạn không có quyền truy cập trang này", 'danger')
            return render_template('error.html', error="Unauthorized", status_code=403), 403
        except NotFound as e:
            current_app.logger.warning(f"NotFound in {f.__name__}: {str(e)}")
            return render_template('error.html', error="Trang không tồn tại", status_code=404), 404
        except IntegrityError as e:
            current_app.logger.error(f"IntegrityError in {f.__name__}: {str(e)}")
            from flask import flash
            flash("Lỗi dữ liệu, vui lòng thử lại", 'danger')
            return render_template('error.html', error="Data error", status_code=409), 409
        except Exception as e:
            current_app.logger.error(f"Unexpected error in {f.__name__}: {str(e)}")
            from flask import flash
            flash("Có lỗi xảy ra, vui lòng thử lại", 'danger')
            try:
                return render_template('error.html', error="Server error", status_code=500), 500
            except:
                # Fallback if error.html doesn't exist
                return f"<h1>Server Error</h1><p>Something went wrong. Please try again later.</p>", 500
    return decorated_function


def handle_database_errors(f):
    """
    Standard error handler for database operations
    
    Usage:
        @handle_database_errors
        def database_operation():
            pass
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except IntegrityError as e:
            current_app.logger.error(f"Database integrity error in {f.__name__}: {str(e)}")
            return jsonify({
                "success": False, 
                "error": "Dữ liệu không hợp lệ hoặc đã tồn tại"
            }), 409
        except Exception as e:
            current_app.logger.error(f"Database error in {f.__name__}: {str(e)}")
            return jsonify({
                "success": False, 
                "error": "Lỗi cơ sở dữ liệu"
            }), 500
    return decorated_function


def handle_file_upload_errors(f):
    """
    Standard error handler for file upload operations
    
    Usage:
        @handle_file_upload_errors
        def upload_file():
            pass
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except ValueError as e:
            current_app.logger.warning(f"File validation error in {f.__name__}: {str(e)}")
            return jsonify({
                "success": False, 
                "error": f"Lỗi file: {str(e)}"
            }), 400
        except PermissionError as e:
            current_app.logger.warning(f"File permission error in {f.__name__}: {str(e)}")
            return jsonify({
                "success": False, 
                "error": "Không có quyền upload file"
            }), 403
        except Exception as e:
            current_app.logger.error(f"File upload error in {f.__name__}: {str(e)}")
            return jsonify({
                "success": False, 
                "error": "Lỗi upload file"
            }), 500
    return decorated_function


def handle_validation_errors(f):
    """
    Standard error handler for validation operations
    
    Usage:
        @handle_validation_errors
        def validate_data():
            pass
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except ValueError as e:
            current_app.logger.warning(f"Validation error in {f.__name__}: {str(e)}")
            return jsonify({
                "success": False, 
                "error": f"Dữ liệu không hợp lệ: {str(e)}"
            }), 400
        except Exception as e:
            current_app.logger.error(f"Validation error in {f.__name__}: {str(e)}")
            return jsonify({
                "success": False, 
                "error": "Lỗi xác thực dữ liệu"
            }), 500
    return decorated_function


def handle_payment_errors(f):
    """
    Standard error handler for payment operations
    
    Usage:
        @handle_payment_errors
        def payment_operation():
            pass
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except ValueError as e:
            current_app.logger.warning(f"Payment validation error in {f.__name__}: {str(e)}")
            return jsonify({
                "success": False, 
                "error": f"Lỗi thanh toán: {str(e)}"
            }), 400
        except PermissionError as e:
            current_app.logger.warning(f"Payment permission error in {f.__name__}: {str(e)}")
            return jsonify({
                "success": False, 
                "error": "Không có quyền thực hiện thanh toán"
            }), 403
        except Exception as e:
            current_app.logger.error(f"Payment error in {f.__name__}: {str(e)}")
            return jsonify({
                "success": False, 
                "error": "Lỗi hệ thống thanh toán"
            }), 500
    return decorated_function


def handle_booking_errors(f):
    """
    Standard error handler for booking operations
    
    Usage:
        @handle_booking_errors
        def booking_operation():
            pass
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except ValueError as e:
            current_app.logger.warning(f"Booking validation error in {f.__name__}: {str(e)}")
            return jsonify({
                "success": False, 
                "error": f"Lỗi đặt phòng: {str(e)}"
            }), 400
        except PermissionError as e:
            current_app.logger.warning(f"Booking permission error in {f.__name__}: {str(e)}")
            return jsonify({
                "success": False, 
                "error": "Không có quyền thực hiện đặt phòng"
            }), 403
        except Exception as e:
            current_app.logger.error(f"Booking error in {f.__name__}: {str(e)}")
            return jsonify({
                "success": False, 
                "error": "Lỗi hệ thống đặt phòng"
            }), 500
    return decorated_function


# Utility functions for error responses
def create_error_response(message, status_code=500, error_type="error"):
    """
    Create standardized error response
    
    Args:
        message (str): Error message
        status_code (int): HTTP status code
        error_type (str): Type of error
    
    Returns:
        tuple: (response, status_code)
    """
    return jsonify({
        "success": False,
        "error": message,
        "error_type": error_type
    }), status_code


def create_success_response(data=None, message="Success"):
    """
    Create standardized success response
    
    Args:
        data: Response data
        message (str): Success message
    
    Returns:
        dict: Success response
    """
    response = {
        "success": True,
        "message": message
    }
    if data is not None:
        response["data"] = data
    return jsonify(response)


def log_error(func_name, error, level="error"):
    """
    Log error with standardized format
    
    Args:
        func_name (str): Function name where error occurred
        error: Error object or message
        level (str): Log level
    """
    if level == "error":
        current_app.logger.error(f"Error in {func_name}: {str(error)}")
    elif level == "warning":
        current_app.logger.warning(f"Warning in {func_name}: {str(error)}")
    else:
        current_app.logger.info(f"Info in {func_name}: {str(error)}")
