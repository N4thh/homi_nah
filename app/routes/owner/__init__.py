"""
Owner Routes Package
Contains all owner-related route modules
"""

from .owner_dashboard import owner_dashboard_bp
from .owner_homes import owner_homes_bp
from .owner_bookings import owner_bookings_bp
from .owner_profile import owner_profile_bp
from .owner_reports import owner_reports_bp

__all__ = [
    'owner_dashboard_bp',
    'owner_homes_bp',
    'owner_bookings_bp', 
    'owner_profile_bp',
    'owner_reports_bp'
]
