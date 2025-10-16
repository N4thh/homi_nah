"""
Base Route Classes - Common functionality for all route handlers
"""

from flask import Blueprint, jsonify, current_app, request, render_template, flash, redirect, url_for
from functools import wraps
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

from app.routes.constants import (
    FLASH_MESSAGES, API_MESSAGES, HTTP_STATUS, 
    PAGINATION, FILE_UPLOAD, HOME_RULES, BOOKING_RULES
)
from app.routes.error_handlers import create_error_response, create_success_response, log_error


class BaseRouteHandler:
    """
    Base class for route handlers with common functionality
    """
    
    def __init__(self, blueprint_name: str, url_prefix: str = None):
        """
        Initialize base route handler
        
        Args:
            blueprint_name (str): Name of the blueprint
            url_prefix (str): URL prefix for the blueprint
        """
        self.blueprint_name = blueprint_name
        self.url_prefix = url_prefix
        self.logger = logging.getLogger(f"{__name__}.{blueprint_name}")
    
    @staticmethod
    def handle_api_response(func):
        """
        Standard API response handler
        
        Usage:
            @BaseRouteHandler.handle_api_response
            def api_endpoint():
                return {"data": "result"}
        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                result = func(*args, **kwargs)
                return create_success_response(result)
            except Exception as e:
                log_error(func.__name__, e)
                return create_error_response("Internal server error", HTTP_STATUS['INTERNAL_SERVER_ERROR'])
        return wrapper
    
    @staticmethod
    def handle_web_response(func):
        """
        Standard web response handler
        
        Usage:
            @BaseRouteHandler.handle_web_response
            def web_endpoint():
                return render_template('page.html')
        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                log_error(func.__name__, e)
                flash(FLASH_MESSAGES['SERVER_ERROR'], 'danger')
                return render_template('error.html', error=str(e)), HTTP_STATUS['INTERNAL_SERVER_ERROR']
        return wrapper
    
    @staticmethod
    def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> bool:
        """
        Validate required fields in request data
        
        Args:
            data: Request data dictionary
            required_fields: List of required field names
            
        Returns:
            bool: True if all required fields are present
            
        Raises:
            ValueError: If required fields are missing
        """
        missing_fields = [field for field in required_fields if field not in data or data[field] is None]
        if missing_fields:
            raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")
        return True
    
    @staticmethod
    def validate_field_length(field_value: str, min_length: int = 0, max_length: int = None, field_name: str = "Field") -> bool:
        """
        Validate field length
        
        Args:
            field_value: Field value to validate
            min_length: Minimum length
            max_length: Maximum length
            field_name: Name of the field for error message
            
        Returns:
            bool: True if validation passes
            
        Raises:
            ValueError: If validation fails
        """
        if not isinstance(field_value, str):
            raise ValueError(f"{field_name} must be a string")
        
        if len(field_value) < min_length:
            raise ValueError(f"{field_name} must be at least {min_length} characters long")
        
        if max_length and len(field_value) > max_length:
            raise ValueError(f"{field_name} must be no more than {max_length} characters long")
        
        return True
    
    @staticmethod
    def validate_numeric_range(value: float, min_value: float = None, max_value: float = None, field_name: str = "Value") -> bool:
        """
        Validate numeric range
        
        Args:
            value: Value to validate
            min_value: Minimum value
            max_value: Maximum value
            field_name: Name of the field for error message
            
        Returns:
            bool: True if validation passes
            
        Raises:
            ValueError: If validation fails
        """
        if not isinstance(value, (int, float)):
            raise ValueError(f"{field_name} must be a number")
        
        if min_value is not None and value < min_value:
            raise ValueError(f"{field_name} must be at least {min_value}")
        
        if max_value is not None and value > max_value:
            raise ValueError(f"{field_name} must be no more than {max_value}")
        
        return True
    
    @staticmethod
    def validate_file_upload(file, allowed_extensions: set = None, max_size: int = None) -> bool:
        """
        Validate file upload
        
        Args:
            file: Uploaded file object
            allowed_extensions: Set of allowed file extensions
            max_size: Maximum file size in bytes
            
        Returns:
            bool: True if validation passes
            
        Raises:
            ValueError: If validation fails
        """
        if not file or not file.filename:
            raise ValueError("No file selected")
        
        if allowed_extensions is None:
            allowed_extensions = FILE_UPLOAD['ALLOWED_EXTENSIONS']
        
        if max_size is None:
            max_size = FILE_UPLOAD['MAX_FILE_SIZE']
        
        # Check file extension
        if '.' not in file.filename:
            raise ValueError("File must have an extension")
        
        file_ext = file.filename.rsplit('.', 1)[1].lower()
        if file_ext not in allowed_extensions:
            raise ValueError(f"File type .{file_ext} is not allowed. Allowed types: {', '.join(allowed_extensions)}")
        
        # Check file size
        file.seek(0, 2)  # Seek to end
        file_size = file.tell()
        file.seek(0)  # Reset to beginning
        
        if file_size > max_size:
            raise ValueError(f"File size ({file_size} bytes) exceeds maximum allowed size ({max_size} bytes)")
        
        return True
    
    @staticmethod
    def paginate_query(query, page: int = 1, per_page: int = None):
        """
        Paginate database query
        
        Args:
            query: SQLAlchemy query object
            page: Page number (1-based)
            per_page: Items per page
            
        Returns:
            Pagination object
        """
        if per_page is None:
            per_page = PAGINATION['PER_PAGE']
        
        return query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
    
    @staticmethod
    def format_pagination_response(pagination):
        """
        Format pagination response for API
        
        Args:
            pagination: SQLAlchemy pagination object
            
        Returns:
            dict: Formatted pagination data
        """
        return {
            'items': [item.to_dict() if hasattr(item, 'to_dict') else item for item in pagination.items],
            'pagination': {
                'page': pagination.page,
                'pages': pagination.pages,
                'per_page': pagination.per_page,
                'total': pagination.total,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev,
                'next_num': pagination.next_num,
                'prev_num': pagination.prev_num
            }
        }
    
    @staticmethod
    def get_current_timestamp():
        """
        Get current timestamp in Vietnam timezone
        
        Returns:
            datetime: Current timestamp
        """
        from app.routes.constants import TIMEZONE
        import pytz
        
        vn_tz = pytz.timezone(TIMEZONE['VIETNAM'])
        return datetime.now(vn_tz)
    
    @staticmethod
    def convert_to_utc(dt: datetime):
        """
        Convert datetime to UTC for database storage
        
        Args:
            dt: Datetime object
            
        Returns:
            datetime: UTC datetime
        """
        from app.routes.constants import TIMEZONE
        import pytz
        
        vn_tz = pytz.timezone(TIMEZONE['VIETNAM'])
        return vn_tz.localize(dt).astimezone(pytz.UTC).replace(tzinfo=None)
    
    @staticmethod
    def validate_booking_dates(start_time: datetime, end_time: datetime) -> bool:
        """
        Validate booking dates
        
        Args:
            start_time: Booking start time
            end_time: Booking end time
            
        Returns:
            bool: True if validation passes
            
        Raises:
            ValueError: If validation fails
        """
        now = datetime.utcnow()
        
        # Check if start time is in the future
        if start_time <= now:
            raise ValueError("Start time must be in the future")
        
        # Check if end time is after start time
        if end_time <= start_time:
            raise ValueError("End time must be after start time")
        
        # Check minimum duration
        duration = end_time - start_time
        min_duration = BOOKING_RULES['MIN_DURATION_HOURS']
        if duration.total_seconds() < min_duration * 3600:
            raise ValueError(f"Booking duration must be at least {min_duration} hours")
        
        # Check maximum duration
        max_duration = BOOKING_RULES['MAX_DURATION_DAYS']
        if duration.days > max_duration:
            raise ValueError(f"Booking duration cannot exceed {max_duration} days")
        
        return True
    
    @staticmethod
    def validate_home_data(data: Dict[str, Any]) -> bool:
        """
        Validate home/property data
        
        Args:
            data: Home data dictionary
            
        Returns:
            bool: True if validation passes
            
        Raises:
            ValueError: If validation fails
        """
        # Validate title
        if 'title' in data:
            BaseRouteHandler.validate_field_length(
                data['title'], 
                HOME_RULES['TITLE_MIN_LENGTH'], 
                HOME_RULES['TITLE_MAX_LENGTH'], 
                'Title'
            )
        
        # Validate description
        if 'description' in data:
            BaseRouteHandler.validate_field_length(
                data['description'], 
                HOME_RULES['DESCRIPTION_MIN_LENGTH'], 
                HOME_RULES['DESCRIPTION_MAX_LENGTH'], 
                'Description'
            )
        
        # Validate price
        if 'price' in data:
            BaseRouteHandler.validate_numeric_range(
                data['price'], 
                HOME_RULES['PRICE_MIN'], 
                HOME_RULES['PRICE_MAX'], 
                'Price'
            )
        
        # Validate capacity
        if 'capacity' in data:
            BaseRouteHandler.validate_numeric_range(
                data['capacity'], 
                HOME_RULES['CAPACITY_MIN'], 
                HOME_RULES['CAPACITY_MAX'], 
                'Capacity'
            )
        
        return True
    
    def log_info(self, message: str):
        """Log info message"""
        self.logger.info(message)
    
    def log_warning(self, message: str):
        """Log warning message"""
        self.logger.warning(message)
    
    def log_error(self, message: str):
        """Log error message"""
        self.logger.error(message)


class APIRouteHandler(BaseRouteHandler):
    """
    Base class for API route handlers
    """
    
    def __init__(self, blueprint_name: str, url_prefix: str = None):
        super().__init__(blueprint_name, url_prefix)
        self.blueprint = Blueprint(blueprint_name, __name__, url_prefix=url_prefix)
    
    def register_route(self, rule: str, methods: List[str] = None, **options):
        """
        Register API route with standard error handling
        
        Args:
            rule: URL rule
            methods: HTTP methods
            options: Additional options
        """
        if methods is None:
            methods = ['GET']
        
        def decorator(f):
            wrapped_func = self.handle_api_response(f)
            self.blueprint.add_url_rule(rule, f.__name__, wrapped_func, methods=methods, **options)
            return wrapped_func
        return decorator


class WebRouteHandler(BaseRouteHandler):
    """
    Base class for web route handlers
    """
    
    def __init__(self, blueprint_name: str, url_prefix: str = None):
        super().__init__(blueprint_name, url_prefix)
        self.blueprint = Blueprint(blueprint_name, __name__, url_prefix=url_prefix)
    
    def register_route(self, rule: str, methods: List[str] = None, **options):
        """
        Register web route with standard error handling
        
        Args:
            rule: URL rule
            methods: HTTP methods
            options: Additional options
        """
        if methods is None:
            methods = ['GET']
        
        def decorator(f):
            wrapped_func = self.handle_web_response(f)
            self.blueprint.add_url_rule(rule, f.__name__, wrapped_func, methods=methods, **options)
            return wrapped_func
        return decorator


class MixedRouteHandler(BaseRouteHandler):
    """
    Base class for mixed route handlers (both API and web)
    """
    
    def __init__(self, blueprint_name: str, url_prefix: str = None):
        super().__init__(blueprint_name, url_prefix)
        self.blueprint = Blueprint(blueprint_name, __name__, url_prefix=url_prefix)
    
    def register_api_route(self, rule: str, methods: List[str] = None, **options):
        """Register API route"""
        if methods is None:
            methods = ['GET']
        
        def decorator(f):
            wrapped_func = self.handle_api_response(f)
            self.blueprint.add_url_rule(rule, f.__name__, wrapped_func, methods=methods, **options)
            return wrapped_func
        return decorator
    
    def register_web_route(self, rule: str, methods: List[str] = None, **options):
        """Register web route"""
        if methods is None:
            methods = ['GET']
        
        def decorator(f):
            wrapped_func = self.handle_web_response(f)
            self.blueprint.add_url_rule(rule, f.__name__, wrapped_func, methods=methods, **options)
            return wrapped_func
        return decorator
