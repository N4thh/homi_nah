"""
Cache utility for Flask application
"""

from flask_caching import Cache
from flask import current_app

# Initialize cache instance
cache = Cache()

def init_cache(app):
    """Initialize cache with Flask app"""
    cache.init_app(app, config={
        'CACHE_TYPE': 'simple',  # Use simple cache for development
        'CACHE_DEFAULT_TIMEOUT': 300  # 5 minutes default timeout
    })

def clear_cache():
    """Clear all cache"""
    cache.clear()

def clear_cache_pattern(pattern):
    """Clear cache entries matching pattern"""
    cache.delete_memoized(pattern)
