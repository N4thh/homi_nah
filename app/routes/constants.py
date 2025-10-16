"""
Centralized Constants for Routes - Consolidate all hardcoded values
"""

# =============================================================================
# MESSAGES
# =============================================================================

# Flash Messages
FLASH_MESSAGES = {
    # Authentication & Authorization
    'UNAUTHORIZED': 'Bạn không có quyền truy cập',
    'LOGIN_REQUIRED': 'Bạn phải đăng nhập để thực hiện thao tác này',
    'EMAIL_VERIFICATION_REQUIRED': 'Vui lòng xác thực email trước khi sử dụng hệ thống',
    'EMAIL_VERIFICATION_BOOKING': 'Vui lòng xác thực email trước khi thực hiện đặt phòng',
    
    # Role-specific messages
    'OWNER_REQUIRED': 'You must be an owner to access this page',
    'RENTER_REQUIRED': 'You must be a renter to access this page',
    'ADMIN_REQUIRED': 'Bạn không có quyền truy cập!',
    'SUPER_ADMIN_REQUIRED': 'Bạn không có quyền truy cập trang này.',
    
    # Success messages
    'SUCCESS': 'Thao tác thành công',
    'SAVE_SUCCESS': 'Lưu thành công',
    'UPDATE_SUCCESS': 'Cập nhật thành công',
    'DELETE_SUCCESS': 'Xóa thành công',
    'UPLOAD_SUCCESS': 'Upload thành công',
    
    # Error messages
    'SERVER_ERROR': 'Lỗi server',
    'DATA_ERROR': 'Lỗi dữ liệu',
    'VALIDATION_ERROR': 'Dữ liệu không hợp lệ',
    'FILE_ERROR': 'Lỗi file',
    'UPLOAD_ERROR': 'Lỗi upload',
    'PAYMENT_ERROR': 'Lỗi thanh toán',
    'BOOKING_ERROR': 'Lỗi đặt phòng',
    
    # Warning messages
    'WARNING': 'Cảnh báo',
    'CONFIRM_ACTION': 'Bạn có chắc chắn muốn thực hiện thao tác này?',
    'DATA_LOSS': 'Dữ liệu có thể bị mất',
}

# API Response Messages
API_MESSAGES = {
    'SUCCESS': 'Success',
    'ERROR': 'Error',
    'UNAUTHORIZED': 'Unauthorized access',
    'FORBIDDEN': 'Access forbidden',
    'NOT_FOUND': 'Resource not found',
    'VALIDATION_ERROR': 'Validation error',
    'SERVER_ERROR': 'Internal server error',
    'EMAIL_VERIFICATION_REQUIRED': 'Email verification required',
    'LOGIN_REQUIRED': 'Login required',
    'ADMIN_REQUIRED': 'Admin access required',
    'SUPER_ADMIN_REQUIRED': 'Super admin access required',
    'PASSWORD_CHANGE_RENTER_ONLY': 'Chỉ Renter mới có thể đổi mật khẩu',
    'BOOKING_EMAIL_VERIFICATION': 'Email verification required for booking',
    'CONTENT_TYPE_JSON': 'Content-Type must be application/json',
}

# =============================================================================
# URLS & ROUTES
# =============================================================================

# Main URLs
URLS = {
    'HOME': 'home',
    'LOGIN': 'auth.login',
    'REGISTER': 'auth.register',
    'LOGOUT': 'auth.logout',
    
    # Owner URLs
    'OWNER_DASHBOARD': 'owner_dashboard.dashboard',
    'OWNER_VERIFY': 'owner_dashboard.verify_email',
    'OWNER_PROFILE': 'owner_profile.profile',
    'OWNER_HOMES': 'owner_dashboard.dashboard',
    'OWNER_BOOKINGS': 'owner_bookings.view_bookings',
    
    # Renter URLs
    'RENTER_DASHBOARD': 'renter.dashboard',
    'RENTER_VERIFY': 'renter.verify_email',
    'RENTER_PROFILE': 'renter.profile',
    'RENTER_BOOKINGS': 'renter.bookings',
    
    # Admin URLs
    'ADMIN_DASHBOARD': 'admin.dashboard',
    'ADMIN_USERS': 'admin.users',
    'ADMIN_HOMES': 'admin.homes',
    'ADMIN_PAYMENTS': 'admin.payments',
    
    # Payment URLs
    'PAYMENT_CHECKOUT': 'payment.checkout',
    'PAYMENT_SUCCESS': 'payment.success',
    'PAYMENT_FAILED': 'payment.failed',
    'PAYMENT_CANCEL': 'payment.cancel',
}

# =============================================================================
# APPLICATION CONSTANTS
# =============================================================================

# Pagination
PAGINATION = {
    'PER_PAGE': 5,
    'PER_PAGE_LARGE': 10,
    'PER_PAGE_SMALL': 3,
    'MAX_PER_PAGE': 50,
}

# Commission & Revenue
COMMISSION = {
    'DEFAULT_PERCENT': 10.0,
    'ADMIN_RATE': 0.05,  # 5%
    'MIN_COMMISSION': 0.0,
    'MAX_COMMISSION': 50.0,
}

# Timezone
TIMEZONE = {
    'VIETNAM': 'Asia/Ho_Chi_Minh',
    'UTC': 'UTC',
}

# File Upload
FILE_UPLOAD = {
    'ALLOWED_EXTENSIONS': {'png', 'jpg', 'jpeg', 'gif', 'webp'},
    'MAX_FILE_SIZE': 16 * 1024 * 1024,  # 16MB
    'UPLOAD_FOLDER': 'uploads',
    'PROFILE_IMAGE_FOLDER': 'profile_images',
    'HOME_IMAGE_FOLDER': 'home_images',
}

# Property Types
PROPERTY_TYPES = {
    'townhouse': 'Nhà phố',
    'apartment': 'Chung cư',
    'villa': 'Villa',
    'penthouse': 'Penthouse',
    'farmstay': 'Farmstay',
    'resort': 'Resort',
    'studio': 'Studio',
    'duplex': 'Duplex',
}

# Property Type Reverse Mapping
PROPERTY_TYPE_REVERSE = {v: k for k, v in PROPERTY_TYPES.items()}

# Booking Status
BOOKING_STATUS = {
    'pending': 'Chờ xác nhận',
    'confirmed': 'Đã xác nhận',
    'active': 'Đang sử dụng',
    'completed': 'Hoàn thành',
    'cancelled': 'Đã hủy',
    'expired': 'Hết hạn',
}

# Payment Status
PAYMENT_STATUS = {
    'pending': 'Chờ thanh toán',
    'success': 'Thanh toán thành công',
    'failed': 'Thanh toán thất bại',
    'cancelled': 'Đã hủy',
    'refunded': 'Đã hoàn tiền',
}

# User Roles
USER_ROLES = {
    'owner': 'Chủ nhà',
    'renter': 'Người thuê',
    'admin': 'Quản trị viên',
    'super_admin': 'Siêu quản trị viên',
}

# =============================================================================
# VALIDATION RULES
# =============================================================================

# Password
PASSWORD_RULES = {
    'MIN_LENGTH': 8,
    'MAX_LENGTH': 128,
    'REQUIRE_UPPERCASE': True,
    'REQUIRE_LOWERCASE': True,
    'REQUIRE_NUMBERS': True,
    'REQUIRE_SPECIAL_CHARS': True,
}

# Email
EMAIL_RULES = {
    'MAX_LENGTH': 254,
    'REQUIRE_VERIFICATION': True,
}

# Phone
PHONE_RULES = {
    'MIN_LENGTH': 10,
    'MAX_LENGTH': 15,
    'PATTERN': r'^[0-9+\-\s()]+$',
}

# Home/Property
HOME_RULES = {
    'TITLE_MIN_LENGTH': 10,
    'TITLE_MAX_LENGTH': 200,
    'DESCRIPTION_MIN_LENGTH': 50,
    'DESCRIPTION_MAX_LENGTH': 2000,
    'PRICE_MIN': 0,
    'PRICE_MAX': 1000000000,  # 1 billion VND
    'CAPACITY_MIN': 1,
    'CAPACITY_MAX': 50,
}

# Booking
BOOKING_RULES = {
    'MIN_DURATION_HOURS': 1,
    'MAX_DURATION_DAYS': 30,
    'ADVANCE_BOOKING_DAYS': 30,
    'CANCELLATION_HOURS': 24,
}

# =============================================================================
# API RESPONSE CODES
# =============================================================================

HTTP_STATUS = {
    'OK': 200,
    'CREATED': 201,
    'BAD_REQUEST': 400,
    'UNAUTHORIZED': 401,
    'FORBIDDEN': 403,
    'NOT_FOUND': 404,
    'CONFLICT': 409,
    'UNPROCESSABLE_ENTITY': 422,
    'INTERNAL_SERVER_ERROR': 500,
    'SERVICE_UNAVAILABLE': 503,
}

# =============================================================================
# CACHE SETTINGS
# =============================================================================

CACHE = {
    'DEFAULT_TIMEOUT': 300,  # 5 minutes
    'SHORT_TIMEOUT': 60,     # 1 minute
    'LONG_TIMEOUT': 3600,    # 1 hour
    'VERY_LONG_TIMEOUT': 86400,  # 24 hours
}

# =============================================================================
# RATE LIMITING
# =============================================================================

RATE_LIMIT = {
    'DEFAULT': '100 per hour',
    'LOGIN': '5 per minute',
    'REGISTER': '3 per minute',
    'PASSWORD_RESET': '3 per hour',
    'EMAIL_VERIFICATION': '5 per hour',
    'PAYMENT': '10 per minute',
    'UPLOAD': '20 per hour',
}

# =============================================================================
# NOTIFICATION TYPES
# =============================================================================

NOTIFICATION_TYPES = {
    'PAYMENT_SUCCESS': 'payment_success',
    'PAYMENT_FAILED': 'payment_failed',
    'BOOKING_CONFIRMED': 'booking_confirmed',
    'BOOKING_CANCELLED': 'booking_cancelled',
    'EMAIL_VERIFICATION': 'email_verification',
    'PASSWORD_CHANGED': 'password_changed',
    'PROFILE_UPDATED': 'profile_updated',
}

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_property_type_name(type_code):
    """Get property type name by code"""
    return PROPERTY_TYPES.get(type_code, 'Không xác định')

def get_booking_status_name(status):
    """Get booking status name"""
    return BOOKING_STATUS.get(status, 'Không xác định')

def get_payment_status_name(status):
    """Get payment status name"""
    return PAYMENT_STATUS.get(status, 'Không xác định')

def get_user_role_name(role):
    """Get user role name"""
    return USER_ROLES.get(role, 'Không xác định')

def is_valid_property_type(type_code):
    """Check if property type is valid"""
    return type_code in PROPERTY_TYPES

def is_valid_booking_status(status):
    """Check if booking status is valid"""
    return status in BOOKING_STATUS

def is_valid_payment_status(status):
    """Check if payment status is valid"""
    return status in PAYMENT_STATUS
