"""
Template Caching Utilities
Provides template caching functionality for improved performance
"""

from flask import current_app
from functools import wraps
import hashlib
import json
from datetime import datetime, timedelta

# Template cache storage
_template_cache = {}
_cache_stats = {
    'hits': 0,
    'misses': 0,
    'sets': 0,
    'evictions': 0
}

def get_cache_key(template_name, **kwargs):
    """Generate cache key for template with parameters"""
    # Sort kwargs to ensure consistent keys
    sorted_kwargs = sorted(kwargs.items())
    key_data = f"{template_name}:{json.dumps(sorted_kwargs, default=str)}"
    return hashlib.md5(key_data.encode()).hexdigest()

def cache_template(ttl=300):  # 5 minutes default TTL
    """
    Decorator to cache template rendering
    
    Args:
        ttl: Time to live in seconds
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Extract template name from function name or kwargs
            template_name = kwargs.get('template_name', func.__name__)
            
            # Generate cache key
            cache_key = get_cache_key(template_name, **kwargs)
            
            # Check cache
            if cache_key in _template_cache:
                cached_data = _template_cache[cache_key]
                
                # Check if cache is still valid
                if datetime.now() < cached_data['expires_at']:
                    _cache_stats['hits'] += 1
                    current_app.logger.debug(f"Template cache hit: {template_name}")
                    return cached_data['content']
                else:
                    # Cache expired, remove it
                    del _template_cache[cache_key]
                    _cache_stats['evictions'] += 1
            
            # Cache miss, render template
            _cache_stats['misses'] += 1
            content = func(*args, **kwargs)
            
            # Store in cache
            _template_cache[cache_key] = {
                'content': content,
                'expires_at': datetime.now() + timedelta(seconds=ttl),
                'created_at': datetime.now(),
                'template_name': template_name
            }
            _cache_stats['sets'] += 1
            
            current_app.logger.debug(f"Template cached: {template_name}")
            return content
            
        return wrapper
    return decorator

def invalidate_template_cache(template_name=None, pattern=None):
    """
    Invalidate template cache
    
    Args:
        template_name: Specific template to invalidate
        pattern: Pattern to match template names
    """
    keys_to_remove = []
    
    for cache_key, cached_data in _template_cache.items():
        cached_template = cached_data['template_name']
        
        if template_name and cached_template == template_name:
            keys_to_remove.append(cache_key)
        elif pattern and pattern in cached_template:
            keys_to_remove.append(cache_key)
    
    for key in keys_to_remove:
        del _template_cache[key]
        _cache_stats['evictions'] += 1
    
    current_app.logger.info(f"Invalidated {len(keys_to_remove)} template cache entries")

def clear_template_cache():
    """Clear all template cache"""
    global _template_cache
    _template_cache.clear()
    _cache_stats['evictions'] += len(_template_cache)
    current_app.logger.info("Template cache cleared")

def get_cache_stats():
    """Get cache statistics"""
    total_requests = _cache_stats['hits'] + _cache_stats['misses']
    hit_rate = (_cache_stats['hits'] / total_requests * 100) if total_requests > 0 else 0
    
    return {
        'hits': _cache_stats['hits'],
        'misses': _cache_stats['misses'],
        'sets': _cache_stats['sets'],
        'evictions': _cache_stats['evictions'],
        'hit_rate': round(hit_rate, 2),
        'cache_size': len(_template_cache),
        'total_requests': total_requests
    }

def get_cache_info():
    """Get detailed cache information"""
    cache_info = []
    
    for cache_key, cached_data in _template_cache.items():
        cache_info.append({
            'key': cache_key[:8] + '...',  # Truncated key
            'template_name': cached_data['template_name'],
            'created_at': cached_data['created_at'].isoformat(),
            'expires_at': cached_data['expires_at'].isoformat(),
            'age_seconds': (datetime.now() - cached_data['created_at']).total_seconds(),
            'ttl_seconds': (cached_data['expires_at'] - datetime.now()).total_seconds()
        })
    
    return cache_info

# Template caching context manager
class TemplateCacheContext:
    """Context manager for template caching"""
    
    def __init__(self, ttl=300):
        self.ttl = ttl
        self.original_cache = {}
    
    def __enter__(self):
        # Store original cache
        self.original_cache = _template_cache.copy()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Restore original cache
        global _template_cache
        _template_cache = self.original_cache

# Utility functions for common caching patterns
def cache_component(component_name, ttl=600):  # 10 minutes for components
    """Cache a reusable component"""
    return cache_template(ttl=ttl)

def cache_page(page_name, ttl=300):  # 5 minutes for pages
    """Cache a full page"""
    return cache_template(ttl=ttl)

def cache_fragment(fragment_name, ttl=1800):  # 30 minutes for fragments
    """Cache a page fragment"""
    return cache_template(ttl=ttl)

# Auto-cleanup expired cache entries
def cleanup_expired_cache():
    """Remove expired cache entries"""
    current_time = datetime.now()
    expired_keys = []
    
    for cache_key, cached_data in _template_cache.items():
        if current_time >= cached_data['expires_at']:
            expired_keys.append(cache_key)
    
    for key in expired_keys:
        del _template_cache[key]
        _cache_stats['evictions'] += 1
    
    if expired_keys:
        current_app.logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")
    
    return len(expired_keys)
