"""
Authentication Routes Package
Contains all authentication-related route handlers
"""

from .auth import auth_bp
from .email_verification import email_verification_bp

__all__ = ['auth_bp', 'email_verification_bp']
