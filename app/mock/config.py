"""
Mock API Configuration
Controls whether to use mock data or real database
"""

import os

# Environment variable to control API mode
# Set USE_MOCK_API=true to use mock data, false or unset for real data
USE_MOCK_API = os.getenv('USE_MOCK_API', 'true').lower() == 'true'

# API mode configuration
API_MODE = 'mock' if USE_MOCK_API else 'real'

def get_customer_api():
    """Get the mock customer API if enabled"""
    if API_MODE == 'mock':
        from app.mock.customer.customer_api import mock_customer_api
        return mock_customer_api
    else:
        # Return None to use original logic in routes
        return None

def get_pagination_api():
    """Get the mock pagination API if enabled"""
    if API_MODE == 'mock':
        from app.mock.pagination.pagination_api import pagination_api
        return pagination_api
    else:
        # Return None to use original logic in routes
        return None

def get_owner_api():
    """Get the mock owner API if enabled"""
    if API_MODE == 'mock':
        from app.mock.owner.owner_api import owner_api
        return owner_api
    else:
        # Return None to use original logic in routes
        return None

def is_mock_mode():
    """Check if currently in mock mode"""
    return API_MODE == 'mock'

def is_real_mode():
    """Check if currently in real mode"""
    return API_MODE == 'real'
