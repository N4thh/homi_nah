"""
Renter Booking Service
Business logic for renter booking operations
"""

from app.models.models import db, Booking, Home, Owner, Review
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from app.utils.booking_locking import booking_locking_service, BookingConflictError, BookingLockingError


class RenterBookingService:
    """Service for renter booking operations"""
    
    def get_renter_bookings(self, renter_id: int, page: int = 1, per_page: int = 20, 
                           status_filter: str = '', search_term: str = '') -> Dict:
        """Get bookings for a specific renter with pagination and filtering"""
        try:
            # Update booking statuses before filtering
            now = datetime.now()
            updated = False
            
            # Get all bookings for renter that might need status updates
            all_bookings = Booking.query.filter_by(renter_id=renter_id).all()
            
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
            query = Booking.query.join(Home).join(Owner).filter(
                Booking.renter_id == renter_id
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
                        Owner.full_name.ilike(f'%{search_term}%'),
                        Owner.email.ilike(f'%{search_term}%'),
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
                    'home_address': booking.home.address,
                    'owner_name': booking.home.owner.full_name,
                    'owner_email': booking.home.owner.email,
                    'start_time': booking.start_time.isoformat(),
                    'end_time': booking.end_time.isoformat(),
                    'status': booking.status,
                    'payment_status': booking.payment_status,
                    'total_price': booking.total_price,
                    'booking_type': booking.booking_type,
                    'created_at': booking.created_at.isoformat(),
                    'can_review': booking.status == 'completed' and not self._has_review(booking.id)
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
    
    def create_booking(self, home_id: int, renter_id: int, booking_data: Dict) -> Dict:
        """Create a new booking"""
        try:
            # Get home
            home = Home.query.get(home_id)
            if not home:
                return {
                    'success': False,
                    'message': 'Không tìm thấy nhà'
                }
            
            # Parse booking data
            start_datetime = datetime.fromisoformat(booking_data['start_time'])
            end_datetime = datetime.fromisoformat(booking_data['end_time'])
            
            # Calculate duration and price based on booking type
            if booking_data.get('booking_type') == 'hourly':
                duration_hours = (end_datetime - start_datetime).total_seconds() / 3600
                total_price = home.price_per_hour * duration_hours
                booking_type = 'hourly'
            else:
                duration_days = (end_datetime - start_datetime).days
                total_price = home.price_per_day * duration_days
                booking_type = 'daily'
            
            # Create booking with hybrid locking
            new_booking = booking_locking_service.create_booking_with_locking(
                home_id=home.id,
                start_time=start_datetime,
                end_time=end_datetime,
                renter_id=renter_id,
                total_hours=duration_hours if booking_type == 'hourly' else duration_days * 24,
                total_price=total_price,
                booking_type=booking_type
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
    
    def cancel_booking(self, booking_id: int, renter_id: int, reason: str = '') -> Dict:
        """Cancel a booking"""
        try:
            # Get booking and verify it belongs to renter
            booking = Booking.query.filter_by(id=booking_id, renter_id=renter_id).first()
            
            if not booking:
                return {
                    'success': False,
                    'message': 'Không tìm thấy booking'
                }
            
            # Check if booking can be cancelled
            if booking.status in ['completed', 'cancelled']:
                return {
                    'success': False,
                    'message': 'Không thể hủy booking này'
                }
            
            # Update booking status
            booking.status = 'cancelled'
            booking.cancellation_reason = reason
            booking.cancelled_at = datetime.now()
            
            db.session.commit()
            
            return {
                'success': True,
                'message': 'Hủy booking thành công!'
            }
            
        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'message': f'Lỗi khi hủy booking: {str(e)}'
            }
    
    def create_review(self, booking_id: int, renter_id: int, review_data: Dict) -> Dict:
        """Create a review for a completed booking"""
        try:
            # Get booking and verify it belongs to renter
            booking = Booking.query.filter_by(id=booking_id, renter_id=renter_id).first()
            
            if not booking:
                return {
                    'success': False,
                    'message': 'Không tìm thấy booking'
                }
            
            # Check if booking is completed
            if booking.status != 'completed':
                return {
                    'success': False,
                    'message': 'Chỉ có thể đánh giá booking đã hoàn thành'
                }
            
            # Check if review already exists
            if self._has_review(booking_id):
                return {
                    'success': False,
                    'message': 'Bạn đã đánh giá booking này rồi'
                }
            
            # Create review
            review = Review(
                booking_id=booking_id,
                renter_id=renter_id,
                home_id=booking.home_id,
                owner_id=booking.home.owner_id,
                rating=review_data['rating'],
                comment=review_data.get('comment', ''),
                created_at=datetime.now()
            )
            
            db.session.add(review)
            db.session.commit()
            
            return {
                'success': True,
                'message': 'Đánh giá thành công!'
            }
            
        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'message': f'Lỗi khi tạo đánh giá: {str(e)}'
            }
    
    def _has_review(self, booking_id: int) -> bool:
        """Check if a booking already has a review"""
        return Review.query.filter_by(booking_id=booking_id).first() is not None
    
    def get_renter_statistics(self, renter_id: int) -> Dict:
        """Get statistics for renter's bookings"""
        try:
            # Get all bookings for renter
            bookings = Booking.query.filter_by(renter_id=renter_id).all()
            
            # Calculate statistics
            total_bookings = len(bookings)
            completed_bookings = len([b for b in bookings if b.status == 'completed'])
            total_spent = sum(b.total_price for b in bookings if b.status == 'completed')
            
            # Get most booked property type
            property_types = [b.home.property_type for b in bookings if b.status == 'completed']
            favorite_type = max(set(property_types), key=property_types.count) if property_types else 'N/A'
            
            # Get average rating given
            reviews = Review.query.filter_by(renter_id=renter_id).all()
            average_rating_given = sum(r.rating for r in reviews) / len(reviews) if reviews else 0
            
            return {
                'total_bookings': total_bookings,
                'completed_bookings': completed_bookings,
                'total_spent': total_spent,
                'favorite_type': favorite_type,
                'average_rating_given': average_rating_given,
                'total_reviews': len(reviews)
            }
            
        except Exception as e:
            return {
                'total_bookings': 0,
                'completed_bookings': 0,
                'total_spent': 0,
                'favorite_type': 'N/A',
                'average_rating_given': 0,
                'total_reviews': 0
            }


# Global instance
renter_booking_service = RenterBookingService()
