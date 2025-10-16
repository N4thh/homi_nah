"""
Payment validation middleware for PayOS integration
"""

from typing import Dict, Any
from flask import current_app


class PaymentValidationError(Exception):
    """Custom exception for payment validation errors"""
    pass


def validate_payment_before_payos(
    booking_id: int,
    amount: int,
    owner_id: int,
    renter_id: int,
    payment_method: str = "payos"
) -> Dict[str, Any]:
    """
    Validate payment data before processing with PayOS
    
    Args:
        booking_id: ID of the booking
        amount: Payment amount in VND
        owner_id: ID of the owner
        renter_id: ID of the renter
        payment_method: Payment method (default: payos)
    
    Returns:
        Dict containing validated payment data
    
    Raises:
        PaymentValidationError: If validation fails
    """
    try:
        # Basic validation
        if not booking_id or booking_id <= 0:
            raise PaymentValidationError("Invalid booking ID")
        
        if not amount or amount <= 0:
            raise PaymentValidationError("Invalid payment amount")
        
        if not owner_id or owner_id <= 0:
            raise PaymentValidationError("Invalid owner ID")
        
        if not renter_id or renter_id <= 0:
            raise PaymentValidationError("Invalid renter ID")
        
        # Validate amount range (minimum 1000 VND, maximum 100M VND)
        if amount < 1000:
            raise PaymentValidationError("Payment amount too small (minimum 1000 VND)")
        
        if amount > 100000000:
            raise PaymentValidationError("Payment amount too large (maximum 100M VND)")
        
        # Return validated data
        return {
            'booking_id': booking_id,
            'amount': amount,
            'owner_id': owner_id,
            'renter_id': renter_id,
            'payment_method': payment_method,
            'validated': True
        }
        
    except Exception as e:
        if isinstance(e, PaymentValidationError):
            raise
        else:
            current_app.logger.error(f"Payment validation error: {str(e)}")
            raise PaymentValidationError(f"Payment validation failed: {str(e)}")


def validate_payment_config(owner_id: int) -> bool:
    """
    Validate if owner has valid payment configuration
    
    Args:
        owner_id: ID of the owner
    
    Returns:
        True if valid, False otherwise
    """
    try:
        from app.models.models import PaymentConfig
        
        config = PaymentConfig.query.filter_by(
            owner_id=owner_id,
            is_active=True
        ).first()
        
        if not config:
            return False
        
        # Check if required fields are present
        required_fields = ['payos_client_id', 'payos_api_key', 'payos_checksum_key']
        for field in required_fields:
            if not getattr(config, field, None):
                return False
        
        return True
        
    except Exception as e:
        current_app.logger.error(f"Payment config validation error: {str(e)}")
        return False


def validate_booking_status(booking_id: int) -> bool:
    """
    Validate if booking is in correct status for payment
    
    Args:
        booking_id: ID of the booking
    
    Returns:
        True if valid, False otherwise
    """
    try:
        from app.models.models import Booking
        
        booking = Booking.query.get(booking_id)
        if not booking:
            return False
        
        # Check if booking is in pending status
        if booking.status != 'pending':
            return False
        
        # Check if booking is not expired
        from datetime import datetime
        if booking.check_in_date < datetime.now().date():
            return False
        
        return True
        
    except Exception as e:
        current_app.logger.error(f"Booking status validation error: {str(e)}")
        return False
