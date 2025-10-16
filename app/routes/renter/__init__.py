"""
Renter Routes Package
Contains all renter-related route modules
"""

from .renter_dashboard import renter_dashboard_bp
from .renter_bookings import renter_bookings_bp
from .renter_profile import renter_profile_bp
from .renter_reviews import renter_reviews_bp
from .renter_search import renter_search_bp
from .renter_homes import renter_homes_bp

__all__ = [
    'renter_dashboard_bp',
    'renter_bookings_bp',
    'renter_profile_bp',
    'renter_reviews_bp',
    'renter_search_bp',
    'renter_homes_bp'
]
