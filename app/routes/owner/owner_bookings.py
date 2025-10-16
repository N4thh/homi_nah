"""
Owner Bookings Routes - Booking management and calendar functionality
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from datetime import datetime, timedelta
import json

from app.routes.decorators import owner_email_verified, owner_required
from app.routes.error_handlers import handle_api_errors, handle_web_errors
from app.routes.constants import FLASH_MESSAGES, URLS, BOOKING_STATUS
from app.routes.base import BaseRouteHandler

# Import models
from app.models.models import db, Home, Booking, Payment, Renter

owner_bookings_bp = Blueprint('owner_bookings', __name__, url_prefix='/owner')


class OwnerBookingsHandler(BaseRouteHandler):
    """Handler for owner bookings functionality"""
    
    def __init__(self):
        super().__init__('owner_bookings')


# =============================================================================
# BOOKING MANAGEMENT ROUTES
# =============================================================================

@owner_bookings_bp.route('/view-bookings')
@owner_bookings_bp.route('/view-bookings/<status>')
@owner_email_verified
@handle_web_errors
def view_bookings(status=None):
    """View all bookings for owner's homes"""
    # Get owner's homes
    homes = Home.query.filter_by(owner_id=current_user.id).all()
    home_ids = [home.id for home in homes]
    
    if not home_ids:
        return render_template('owner/view_bookings.html', bookings=[], status=status)
    
    # Build query
    query = Booking.query.filter(Booking.home_id.in_(home_ids))
    
    # Filter by status if provided
    if status and status in BOOKING_STATUS:
        query = query.filter(Booking.status == status)
    
    # Order by creation date
    bookings = query.order_by(Booking.created_at.desc()).all()
    
    # Update booking status based on current time
    update_booking_status(bookings)
    
    return render_template('owner/view_bookings.html', bookings=bookings, status=status)


@owner_bookings_bp.route('/booking-details/<int:booking_id>')
@owner_email_verified
@handle_web_errors
def booking_details(booking_id):
    """View booking details"""
    booking = Booking.query.get_or_404(booking_id)
    
    # Check ownership
    if booking.home.owner_id != current_user.id:
        flash(FLASH_MESSAGES['UNAUTHORIZED'], 'danger')
        return redirect(url_for('owner_dashboard.dashboard'))
    
    return render_template('owner/booking_details.html', booking=booking)


# =============================================================================
# CALENDAR ROUTES
# =============================================================================

@owner_bookings_bp.route('/calendar')
@owner_email_verified
@handle_web_errors
def calendar():
    """Owner calendar view"""
    # Get owner's homes
    homes = Home.query.filter_by(owner_id=current_user.id).all()
    
    # Convert homes to serializable format
    homes_data = []
    for home in homes:
        homes_data.append({
            'id': home.id,
            'title': home.title,
            'address': home.address,
            'is_active': home.is_active
        })
    
    return render_template('owner/calendar.html', homes=homes_data)


@owner_bookings_bp.route('/calendar/api/bookings/<date>')
@owner_required
@handle_api_errors
def get_bookings_by_date(date):
    """API endpoint to get bookings for a specific date"""
    try:
        # Parse date
        try:
            target_date = datetime.strptime(date, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({"error": "Invalid date format"}), 400
        
        # Get owner's homes
        homes = Home.query.filter_by(owner_id=current_user.id).all()
        home_ids = [home.id for home in homes]
        
        if not home_ids:
            return jsonify({"bookings": []})
        
        # Get bookings for the date
        start_datetime = datetime.combine(target_date, datetime.min.time())
        end_datetime = datetime.combine(target_date, datetime.max.time())
        
        bookings = Booking.query.filter(
            Booking.home_id.in_(home_ids),
            Booking.start_time <= end_datetime,
            Booking.end_time >= start_datetime
        ).all()
        
        # Format booking data
        booking_data = []
        for booking in bookings:
            booking_data.append({
                'id': booking.id,
                'home_title': booking.home.title,
                'renter_name': booking.renter.full_name if booking.renter else 'N/A',
                'start_time': booking.start_time.isoformat(),
                'end_time': booking.end_time.isoformat(),
                'status': booking.status,
                'payment_status': booking.payment_status,
                'total_price': booking.total_price
            })
        
        return jsonify({
            "success": True,
            "bookings": booking_data,
            "date": date
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting bookings by date: {str(e)}")
        return jsonify({"error": "Failed to get bookings"}), 500


@owner_bookings_bp.route('/calendar/api/booking/<int:booking_id>')
@owner_required
@handle_api_errors
def get_booking_details_api(booking_id):
    """API endpoint to get booking details"""
    try:
        booking = Booking.query.get_or_404(booking_id)
        
        # Check ownership
        if booking.home.owner_id != current_user.id:
            return jsonify({"error": "Unauthorized"}), 403
        
        # Format booking data
        booking_data = {
            'id': booking.id,
            'home_title': booking.home.title,
            'renter_name': booking.renter.full_name if booking.renter else 'N/A',
            'renter_email': booking.renter.email if booking.renter else 'N/A',
            'renter_phone': booking.renter.phone if booking.renter else 'N/A',
            'start_time': booking.start_time.isoformat(),
            'end_time': booking.end_time.isoformat(),
            'status': booking.status,
            'payment_status': booking.payment_status,
            'total_price': booking.total_price,
            'created_at': booking.created_at.isoformat(),
            'notes': booking.notes or ''
        }
        
        return jsonify({
            "success": True,
            "booking": booking_data
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting booking details: {str(e)}")
        return jsonify({"error": "Failed to get booking details"}), 500


@owner_bookings_bp.route('/calendar/api/dates-with-bookings/<int:year>/<int:month>')
@owner_required
@handle_api_errors
def get_dates_with_bookings(year, month):
    """API endpoint to get dates with bookings for calendar"""
    try:
        # Validate year and month
        if not (1 <= month <= 12):
            return jsonify({"error": "Invalid month"}), 400
        
        if not (2020 <= year <= 2030):
            return jsonify({"error": "Invalid year"}), 400
        
        # Get owner's homes
        homes = Home.query.filter_by(owner_id=current_user.id).all()
        home_ids = [home.id for home in homes]
        
        if not home_ids:
            return jsonify({"dates": []})
        
        # Calculate date range for the month
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)
        
        # Get bookings for the month
        bookings = Booking.query.filter(
            Booking.home_id.in_(home_ids),
            Booking.start_time < end_date,
            Booking.end_time >= start_date
        ).all()
        
        # Get unique dates with bookings
        dates_with_bookings = set()
        for booking in bookings:
            # Add all dates covered by this booking
            current_date = booking.start_time.date()
            end_date_booking = booking.end_time.date()
            
            while current_date <= end_date_booking:
                if start_date.date() <= current_date < end_date.date():
                    dates_with_bookings.add(current_date.strftime('%Y-%m-%d'))
                current_date += timedelta(days=1)
        
        return jsonify({
            "success": True,
            "dates": list(dates_with_bookings),
            "year": year,
            "month": month
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting dates with bookings: {str(e)}")
        return jsonify({"error": "Failed to get dates with bookings"}), 500


# =============================================================================
# BOOKING ACTIONS
# =============================================================================

@owner_bookings_bp.route('/api/bookings')
@owner_required
@handle_api_errors
def get_bookings_api():
    """API endpoint to get all bookings for owner"""
    try:
        # Get query parameters
        status = request.args.get('status')
        home_id = request.args.get('home_id', type=int)
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        # Get owner's homes
        homes = Home.query.filter_by(owner_id=current_user.id).all()
        home_ids = [home.id for home in homes]
        
        if not home_ids:
            return jsonify({
                "success": True,
                "bookings": [],
                "pagination": {
                    "page": 1,
                    "pages": 0,
                    "per_page": per_page,
                    "total": 0
                }
            })
        
        # Build query
        query = Booking.query.filter(Booking.home_id.in_(home_ids))
        
        # Filter by home if specified
        if home_id and home_id in home_ids:
            query = query.filter(Booking.home_id == home_id)
        
        # Filter by status if specified
        if status and status in BOOKING_STATUS:
            query = query.filter(Booking.status == status)
        
        # Order by creation date
        query = query.order_by(Booking.created_at.desc())
        
        # Paginate
        pagination = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        
        # Format booking data
        bookings_data = []
        for booking in pagination.items:
            bookings_data.append({
                'id': booking.id,
                'home_title': booking.home.title,
                'renter_name': booking.renter.full_name if booking.renter else 'N/A',
                'renter_email': booking.renter.email if booking.renter else 'N/A',
                'start_time': booking.start_time.isoformat(),
                'end_time': booking.end_time.isoformat(),
                'status': booking.status,
                'payment_status': booking.payment_status,
                'total_price': booking.total_price,
                'created_at': booking.created_at.isoformat()
            })
        
        return jsonify({
            "success": True,
            "bookings": bookings_data,
            "pagination": {
                "page": pagination.page,
                "pages": pagination.pages,
                "per_page": pagination.per_page,
                "total": pagination.total,
                "has_next": pagination.has_next,
                "has_prev": pagination.has_prev
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting bookings: {str(e)}")
        return jsonify({"error": "Failed to get bookings"}), 500


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def update_booking_status(bookings):
    """Update booking status based on current time"""
    now = datetime.utcnow()
    updated = False
    
    for booking in bookings:
        # Only update paid bookings
        if booking.payment_status == 'paid':
            # If past end time -> completed
            if now >= booking.end_time and booking.status != 'completed':
                booking.status = 'completed'
                updated = True
            # If within booking time -> active
            elif now >= booking.start_time and now < booking.end_time and booking.status == 'confirmed':
                booking.status = 'active'
                updated = True
    
    if updated:
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating booking status: {str(e)}")


def get_booking_summary(bookings):
    """Get booking summary statistics"""
    total_bookings = len(bookings)
    confirmed_bookings = len([b for b in bookings if b.status == 'confirmed'])
    active_bookings = len([b for b in bookings if b.status == 'active'])
    completed_bookings = len([b for b in bookings if b.status == 'completed'])
    cancelled_bookings = len([b for b in bookings if b.status == 'cancelled'])
    
    total_revenue = sum(b.total_price for b in bookings if b.payment_status == 'paid')
    
    return {
        'total_bookings': total_bookings,
        'confirmed_bookings': confirmed_bookings,
        'active_bookings': active_bookings,
        'completed_bookings': completed_bookings,
        'cancelled_bookings': cancelled_bookings,
        'total_revenue': total_revenue
    }


def get_monthly_booking_stats(year, month):
    """Get monthly booking statistics"""
    # Calculate date range
    start_date = datetime(year, month, 1)
    if month == 12:
        end_date = datetime(year + 1, 1, 1)
    else:
        end_date = datetime(year, month + 1, 1)
    
    # Get owner's homes
    homes = Home.query.filter_by(owner_id=current_user.id).all()
    home_ids = [home.id for home in homes]
    
    if not home_ids:
        return {
            'total_bookings': 0,
            'total_revenue': 0,
            'occupancy_rate': 0
        }
    
    # Get bookings for the month
    bookings = Booking.query.filter(
        Booking.home_id.in_(home_ids),
        Booking.start_time >= start_date,
        Booking.start_time < end_date
    ).all()
    
    # Calculate statistics
    total_bookings = len(bookings)
    total_revenue = sum(b.total_price for b in bookings if b.payment_status == 'paid')
    
    # Calculate occupancy rate
    total_days = (end_date - start_date).days
    total_available_days = len(home_ids) * total_days
    occupied_days = 0
    
    for booking in bookings:
        if booking.payment_status == 'paid':
            booking_days = (booking.end_time - booking.start_time).days
            occupied_days += booking_days
    
    occupancy_rate = (occupied_days / total_available_days * 100) if total_available_days > 0 else 0
    
    return {
        'total_bookings': total_bookings,
        'total_revenue': total_revenue,
        'occupancy_rate': round(occupancy_rate, 2)
    }
