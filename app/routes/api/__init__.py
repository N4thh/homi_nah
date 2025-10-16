"""
API Routes Package
Contains all API-related route handlers
"""

from .api import api_bp
from .availability_api import availability_api_bp
from .rate_limit_api import rate_limit_api

__all__ = ['api_bp', 'availability_api_bp', 'rate_limit_api']
