"""
Admin Routes Package
Contains all admin-related route modules
"""

from .admin_dashboard import admin_dashboard_bp
from .admin_users import admin_users_bp
from .admin_homes import admin_homes_bp
from .admin_payments import admin_payments_bp
from .admin_reports import admin_reports_bp

__all__ = [
    'admin_dashboard_bp',
    'admin_users_bp', 
    'admin_homes_bp',
    'admin_payments_bp',
    'admin_reports_bp'
]
