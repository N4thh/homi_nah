"""
Owner Booking Service
Business logic for booking management operations
"""

from app.models.models import db, Booking, Home, Renter
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from app.utils.booking_locking import booking_locking_service, BookingConflictError, BookingLockingError


class OwnerBookingService:
    """Service for owner booking management operations"""
    
    def get_owner_bookings(self, owner_id: int, page: int = 1, per_page: int = 20, 
                          status_filter: str = '', search_term: str = '') -> Dict:
        """Get bookings for owner's homes with pagination and filtering"""
        try:
            # Get all homes owned by current user
            owner_homes = Home.query.filter_by(owner_id=owner_id).all()
            home_ids = [home.id for home in owner_homes]
            
            if not home_ids:
                return {
                    'bookings': [],
                    'pagination': {
                        'page': 1,
                        'per_page': per_page,
                        'total': 0,
                        'total_pages': 0,
                        'has_prev': False,
                        'has_next': False
                    }
                }
            
            # Update booking statuses before filtering
            now = datetime.now()
            updated = False
            
            # Get all bookings for owner's homes that might need status updates
            all_bookings = Booking.query.filter(Booking.home_id.in_(home_ids)).all()
            
            for booking in all_bookings:
                # Only update confirmed bookings that have been paid and are now active
                if booking.status == 'confirmed' and booking.payment_status == 'paid' and booking.start_time <= now:
                    booking.status = 'active'
                    updated = True
                elif booking.status == 'active' and booking.end_time <= now:
                    booking.status = 'completed'
                    updated = True
            
            if updated:
                db.session.commit()
            
            # Build query
            query = Booking.query.join(Home).join(Renter).filter(
                Booking.home_id.in_(home_ids)
            )
            
            # Apply status filter
            if status_filter:
                query = query.filter(Booking.status == status_filter)
            
            # Apply search filter
            if search_term:
                search_term = search_term.lower()
                query = query.filter(
                    db.or_(
                        Home.title.ilike(f'%{search_term}%'),
                        Renter.full_name.ilike(f'%{search_term}%'),
                        Renter.email.ilike(f'%{search_term}%'),
                        Booking.id.ilike(f'%{search_term}%')
                    )
                )
            
            # Get total count
            total = query.count()
            
            # Apply pagination
            bookings = query.order_by(Booking.created_at.desc()).offset(
                (page - 1) * per_page
            ).limit(per_page).all()
            
            # Format bookings data
            bookings_data = []
            for booking in bookings:
                bookings_data.append({
                    'id': booking.id,
                    'home_title': booking.home.title,
                    'renter_name': booking.renter.full_name,
                    'renter_email': booking.renter.email,
                    'start_time': booking.start_time.isoformat(),
                    'end_time': booking.end_time.isoformat(),
                    'status': booking.status,
                    'payment_status': booking.payment_status,
                    'total_price': booking.total_price,
                    'booking_type': booking.booking_type,
                    'created_at': booking.created_at.isoformat()
                })
            
            # Calculate pagination info
            total_pages = (total + per_page - 1) // per_page
            
            return {
                'bookings': bookings_data,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total,
                    'total_pages': total_pages,
                    'has_prev': page > 1,
                    'has_next': page < total_pages
                }
            }
            
        except Exception as e:
            return {
                'bookings': [],
                'pagination': {
                    'page': 1,
                    'per_page': per_page,
                    'total': 0,
                    'total_pages': 0,
                    'has_prev': False,
                    'has_next': False
                }
            }
    
    def create_booking(self, home_id: int, owner_id: int, booking_data: Dict) -> Dict:
        """Create a new booking for owner's home"""
        try:
            # Verify home belongs to owner
            home = Home.query.filter_by(id=home_id, owner_id=owner_id).first()
            if not home:
                return {
                    'success': False,
                    'message': 'Không tìm thấy nhà'
                }
            
            # Parse booking data
            start_datetime = datetime.fromisoformat(booking_data['start_time'])
            end_datetime = datetime.fromisoformat(booking_data['end_time'])
            duration = (end_datetime - start_datetime).days
            
            # Calculate total price using the home's price per night
            total_price = home.price_per_day * duration
            
            # Create booking with hybrid locking
            new_booking = booking_locking_service.create_booking_with_locking(
                home_id=home.id,
                start_time=start_datetime,
                end_time=end_datetime,
                renter_id=owner_id,  # Owner booking their own home
                total_hours=duration * 24,  # Convert days to hours
                total_price=total_price,
                booking_type='daily'
            )
            
            return {
                'success': True,
                'message': 'Booking request submitted successfully!',
                'booking_id': new_booking.id
            }
            
        except BookingConflictError as e:
            return {
                'success': False,
                'message': 'This home is not available during the selected time period.'
            }
            
        except BookingLockingError as e:
            return {
                'success': False,
                'message': 'Unable to create booking at this time. Please try again.'
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'An error occurred while creating the booking: {str(e)}'
            }
    
    def get_booking_chart_data(self, owner_id: int, start_date: str, end_date: str) -> Dict:
        """Get booking chart data for owner's homes"""
        try:
            # Get all homes owned by current user
            owner_homes = Home.query.filter_by(owner_id=owner_id).all()
            home_ids = [home.id for home in owner_homes]
            
            if not home_ids:
                return {'hourly': [], 'daily': []}
            
            # Parse dates
            start_dt = datetime.fromisoformat(start_date)
            end_dt = datetime.fromisoformat(end_date)
            
            # Get bookings in date range
            bookings = Booking.query.filter(
                Booking.home_id.in_(home_ids),
                Booking.status.in_(['completed', 'confirmed']),
                Booking.start_time >= start_dt,
                Booking.start_time <= end_dt
            ).all()
            
            # Group by date and type
            hourly_data = {}
            daily_data = {}
            
            for booking in bookings:
                date_key = booking.start_time.date().isoformat()
                
                if booking.booking_type == 'hourly':
                    if date_key not in hourly_data:
                        hourly_data[date_key] = {'date': date_key, 'revenue': 0, 'bookings': 0}
                    hourly_data[date_key]['revenue'] += booking.total_price
                    hourly_data[date_key]['bookings'] += 1
                else:
                    if date_key not in daily_data:
                        daily_data[date_key] = {'date': date_key, 'revenue': 0, 'bookings': 0}
                    daily_data[date_key]['revenue'] += booking.total_price
                    daily_data[date_key]['bookings'] += 1
            
            return {
                'hourly': list(hourly_data.values()),
                'daily': list(daily_data.values())
            }
            
        except Exception as e:
            return {'hourly': [], 'daily': []}
    
    def update_booking_status(self, booking_id: int, owner_id: int, new_status: str) -> Dict:
        """Update booking status"""
        try:
            # Get booking and verify it belongs to owner's home
            booking = Booking.query.join(Home).filter(
                Booking.id == booking_id,
                Home.owner_id == owner_id
            ).first()
            
            if not booking:
                return {
                    'success': False,
                    'message': 'Không tìm thấy booking'
                }
            
            booking.status = new_status
            db.session.commit()
            
            return {
                'success': True,
                'message': 'Cập nhật trạng thái booking thành công!'
            }
            
        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'message': f'Lỗi khi cập nhật booking: {str(e)}'
            }


# Global instance
owner_booking_service = OwnerBookingService()
