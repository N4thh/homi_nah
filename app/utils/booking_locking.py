"""
Booking Locking Utilities - Hybrid locking implementation for booking system
"""

import time
import logging
from datetime import datetime, timedelta
from typing import Optional, Tuple, List
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy import text
from flask import current_app
from app.models.models import db, Booking, Home

logger = logging.getLogger(__name__)


class BookingConflictError(Exception):
    """Raised when booking conflicts with existing bookings"""
    pass


class BookingLockingError(Exception):
    """Raised when booking locking fails"""
    pass


class BookingLockingService:
    """
    Service class for handling booking operations with hybrid locking
    """
    
    def __init__(self, max_retries: int = 3, base_delay: float = 0.1):
        self.max_retries = max_retries
        self.base_delay = base_delay
    
    def is_room_available_atomic(self, home_id: int, start_time: datetime, 
                                end_time: datetime, exclude_booking_id: Optional[int] = None) -> bool:
        """
        Atomically check if room is available for booking
        
        Args:
            home_id: ID of the home
            start_time: Start time of the booking
            end_time: End time of the booking
            exclude_booking_id: ID of booking to exclude from check (for updates)
            
        Returns:
            bool: True if room is available, False otherwise
        """
        try:
            query = Booking.query.filter(
                Booking.home_id == home_id,
                Booking.status.in_(['pending', 'confirmed', 'active']),
                Booking.start_time < end_time,
                Booking.end_time > start_time
            )
            
            if exclude_booking_id:
                query = query.filter(Booking.id != exclude_booking_id)
            
            conflicting_bookings = query.count()
            return conflicting_bookings == 0
            
        except Exception as e:
            logger.error(f"Error checking room availability: {e}")
            return False
    
    def create_booking_with_locking(self, home_id: int, start_time: datetime, 
                                  end_time: datetime, renter_id: int, 
                                  total_hours: int, total_price: float,
                                  booking_type: str = 'hourly') -> Booking:
        """
        Create booking with hybrid locking mechanism
        
        Args:
            home_id: ID of the home
            start_time: Start time of the booking
            end_time: End time of the booking
            renter_id: ID of the renter
            total_hours: Total hours of the booking
            total_price: Total price of the booking
            booking_type: Type of booking ('hourly' or 'daily')
            
        Returns:
            Booking: Created booking object
            
        Raises:
            BookingConflictError: If room is not available
            BookingLockingError: If locking fails after retries
        """
        
        for attempt in range(self.max_retries):
            try:
                with db.session.begin():
                    # 🔒 PESSIMISTIC: Lock home record
                    home = Home.query.filter_by(id=home_id).with_for_update().first()
                    
                    if not home:
                        raise BookingLockingError(f"Home {home_id} not found")
                    
                    # 🚀 OPTIMISTIC: Check availability atomically
                    if not self.is_room_available_atomic(home_id, start_time, end_time):
                        raise BookingConflictError(
                            f"Room {home_id} not available from {start_time} to {end_time}"
                        )
                    
                    # ✅ Create booking
                    booking = Booking(
                        home_id=home_id,
                        renter_id=renter_id,
                        start_time=start_time,
                        end_time=end_time,
                        total_hours=total_hours,
                        total_price=total_price,
                        status='pending',
                        payment_status='pending',
                        booking_type=booking_type
                    )
                    
                    db.session.add(booking)
                    db.session.flush()  # Get the ID without committing
                    
                    logger.info(f"Created booking {booking.id} for home {home_id}")
                    return booking
                    
            except BookingConflictError:
                # Don't retry on conflict - room is genuinely not available
                raise
                
            except (IntegrityError, OperationalError) as e:
                # Database-level conflict - retry with exponential backoff
                if attempt < self.max_retries - 1:
                    delay = self.base_delay * (2 ** attempt)
                    logger.warning(f"Booking conflict on attempt {attempt + 1}, retrying in {delay}s: {e}")
                    time.sleep(delay)
                    continue
                else:
                    raise BookingLockingError(f"Failed to create booking after {self.max_retries} attempts: {e}")
                    
            except Exception as e:
                db.session.rollback()
                logger.error(f"Unexpected error creating booking: {e}")
                raise BookingLockingError(f"Unexpected error: {e}")
        
        raise BookingLockingError(f"Failed to create booking after {self.max_retries} attempts")
    
    def update_booking_with_locking(self, booking_id: int, start_time: datetime, 
                                  end_time: datetime, total_hours: int, 
                                  total_price: float) -> Booking:
        """
        Update booking with hybrid locking mechanism
        
        Args:
            booking_id: ID of the booking to update
            start_time: New start time
            end_time: New end time
            total_hours: New total hours
            total_price: New total price
            
        Returns:
            Booking: Updated booking object
            
        Raises:
            BookingConflictError: If room is not available
            BookingLockingError: If locking fails after retries
        """
        
        for attempt in range(self.max_retries):
            try:
                with db.session.begin():
                    # 🔒 PESSIMISTIC: Lock booking and home records
                    booking = Booking.query.filter_by(id=booking_id).with_for_update().first()
                    
                    if not booking:
                        raise BookingLockingError(f"Booking {booking_id} not found")
                    
                    home = Home.query.filter_by(id=booking.home_id).with_for_update().first()
                    
                    if not home:
                        raise BookingLockingError(f"Home {booking.home_id} not found")
                    
                    # 🚀 OPTIMISTIC: Check availability atomically (excluding current booking)
                    if not self.is_room_available_atomic(
                        booking.home_id, start_time, end_time, exclude_booking_id=booking_id
                    ):
                        raise BookingConflictError(
                            f"Room {booking.home_id} not available from {start_time} to {end_time}"
                        )
                    
                    # ✅ Update booking
                    booking.start_time = start_time
                    booking.end_time = end_time
                    booking.total_hours = total_hours
                    booking.total_price = total_price
                    
                    db.session.flush()
                    
                    logger.info(f"Updated booking {booking_id}")
                    return booking
                    
            except BookingConflictError:
                # Don't retry on conflict
                raise
                
            except (IntegrityError, OperationalError) as e:
                # Database-level conflict - retry with exponential backoff
                if attempt < self.max_retries - 1:
                    delay = self.base_delay * (2 ** attempt)
                    logger.warning(f"Booking update conflict on attempt {attempt + 1}, retrying in {delay}s: {e}")
                    time.sleep(delay)
                    continue
                else:
                    raise BookingLockingError(f"Failed to update booking after {self.max_retries} attempts: {e}")
                    
            except Exception as e:
                db.session.rollback()
                logger.error(f"Unexpected error updating booking: {e}")
                raise BookingLockingError(f"Unexpected error: {e}")
        
        raise BookingLockingError(f"Failed to update booking after {self.max_retries} attempts")
    
    def get_available_time_slots(self, home_id: int, start_date: datetime, 
                                end_date: datetime, duration_hours: int) -> List[Tuple[datetime, datetime]]:
        """
        Get available time slots for a home within a date range
        
        Args:
            home_id: ID of the home
            start_date: Start of search range
            end_date: End of search range
            duration_hours: Duration of booking in hours
            
        Returns:
            List of (start_time, end_time) tuples for available slots
        """
        try:
            # Get all existing bookings for the home in the date range
            existing_bookings = Booking.query.filter(
                Booking.home_id == home_id,
                Booking.status.in_(['pending', 'confirmed', 'active']),
                Booking.start_time < end_date,
                Booking.end_time > start_date
            ).order_by(Booking.start_time).all()
            
            available_slots = []
            current_time = start_date
            
            for booking in existing_bookings:
                # Check if there's a gap before this booking
                if current_time + timedelta(hours=duration_hours) <= booking.start_time:
                    available_slots.append((current_time, current_time + timedelta(hours=duration_hours)))
                
                # Move current_time to after this booking
                current_time = max(current_time, booking.end_time)
            
            # Check if there's time after the last booking
            if current_time + timedelta(hours=duration_hours) <= end_date:
                available_slots.append((current_time, current_time + timedelta(hours=duration_hours)))
            
            return available_slots
            
        except Exception as e:
            logger.error(f"Error getting available time slots: {e}")
            return []


# Global instance for easy import
booking_locking_service = BookingLockingService()
