"""
Renter Bookings Routes - Booking management functionality
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from sqlalchemy import func, distinct, extract
import pytz

from app.routes.decorators import renter_email_verified, renter_required
from app.routes.error_handlers import handle_api_errors, handle_web_errors, handle_validation_errors
from app.routes.constants import FLASH_MESSAGES, URLS, TIMEZONE, PAGINATION, BOOKING_STATUS
from app.routes.base import BaseRouteHandler

# Import models
from app.models.models import db, Renter, Home, Booking, Payment, Review

renter_bookings_bp = Blueprint('renter_bookings', __name__, url_prefix='/renter')


class RenterBookingsHandler(BaseRouteHandler):
    """Handler for renter booking functionality"""
    
    def __init__(self):
        super().__init__('renter_bookings')


# =============================================================================
# BOOKING MANAGEMENT ROUTES
# =============================================================================

@renter_bookings_bp.route('/bookings')
@renter_bookings_bp.route('/bookings/<status>')
@renter_email_verified
@handle_web_errors
def bookings(status=None):
    """View all bookings for renter"""
    page = request.args.get('page', 1, type=int)
    
    # Build query
    query = Booking.query.filter_by(renter_id=current_user.id)
    
    # Filter by status if provided
    if status and status in BOOKING_STATUS:
        query = query.filter(Booking.status == status)
    
    # Order by creation date
    query = query.order_by(Booking.created_at.desc())
    
    # Paginate
    pagination = query.paginate(
        page=page,
        per_page=PAGINATION['PER_PAGE'],
        error_out=False
    )
    
    # Update booking status based on current time
    update_booking_status(pagination.items)
    
    return render_template('renter/bookings.html', 
                         bookings=pagination.items,
                         pagination=pagination,
                         status=status)


@renter_bookings_bp.route('/bookings/<int:booking_id>')
@renter_email_verified
@handle_web_errors
def booking_detail(booking_id):
    """View booking details"""
    booking = Booking.query.get_or_404(booking_id)
    
    # Check ownership
    if booking.renter_id != current_user.id:
        flash(FLASH_MESSAGES['UNAUTHORIZED'], 'danger')
        return redirect(url_for('renter_dashboard.dashboard'))
    
    return render_template('renter/booking_detail.html', booking=booking)


@renter_bookings_bp.route('/bookings/cancel/<int:booking_id>', methods=['POST'])
@renter_email_verified
@handle_api_errors
def cancel_booking(booking_id):
    """Cancel booking"""
    try:
        booking = Booking.query.get_or_404(booking_id)
        
        # Check ownership
        if booking.renter_id != current_user.id:
            return jsonify({"error": "Unauthorized"}), 403
        
        # Check if booking can be cancelled
        if booking.status not in ['confirmed', 'pending']:
            return jsonify({"error": "Booking cannot be cancelled"}), 400
        
        # Check cancellation policy
        if not can_cancel_booking(booking):
            return jsonify({"error": "Booking cannot be cancelled due to policy"}), 400
        
        # Update booking status
        booking.status = 'cancelled'
        booking.cancelled_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Booking cancelled successfully"
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error cancelling booking: {str(e)}")
        return jsonify({"error": "Failed to cancel booking"}), 500


# =============================================================================
# BOOKING CREATION ROUTES
# =============================================================================

@renter_bookings_bp.route('/book-home/<int:home_id>', methods=['GET', 'POST'])
@renter_email_verified
@handle_web_errors
def book_home(home_id):
    """Book a home"""
    home = Home.query.get_or_404(home_id)
    
    if request.method == 'POST':
        return handle_book_home_post(home)
    
    # GET request - show booking form
    return render_template('renter/book_home.html', home=home)


@renter_bookings_bp.route('/book-home', methods=['GET', 'POST'])
@renter_email_verified
@handle_web_errors
def book_home_general():
    """Book a home (general form)"""
    if request.method == 'POST':
        return handle_book_home_general_post()
    
    # GET request - show general booking form
    return render_template('renter/book_home_general.html')


# =============================================================================
# BOOKING ACTIONS
# =============================================================================

@renter_bookings_bp.route('/bookings/<int:booking_id>/review', methods=['GET', 'POST'])
@renter_email_verified
@handle_web_errors
def review_booking(booking_id):
    """Review a booking"""
    booking = Booking.query.get_or_404(booking_id)
    
    # Check ownership
    if booking.renter_id != current_user.id:
        flash(FLASH_MESSAGES['UNAUTHORIZED'], 'danger')
        return redirect(url_for('renter_dashboard.dashboard'))
    
    # Check if booking can be reviewed
    if booking.status != 'completed':
        flash('Chỉ có thể đánh giá booking đã hoàn thành', 'warning')
        return redirect(url_for('renter_bookings.booking_detail', booking_id=booking_id))
    
    # Check if already reviewed
    existing_review = Review.query.filter_by(booking_id=booking_id).first()
    if existing_review:
        flash('Bạn đã đánh giá booking này rồi', 'info')
        return redirect(url_for('renter_bookings.booking_detail', booking_id=booking_id))
    
    if request.method == 'POST':
        return handle_review_post(booking)
    
    # GET request - show review form
    return render_template('renter/review_booking.html', booking=booking)


@renter_bookings_bp.route('/bookings/<int:booking_id>/payment', methods=['GET', 'POST'])
@renter_email_verified
@handle_web_errors
def booking_payment(booking_id):
    """Handle booking payment"""
    booking = Booking.query.get_or_404(booking_id)
    
    # Check ownership
    if booking.renter_id != current_user.id:
        flash(FLASH_MESSAGES['UNAUTHORIZED'], 'danger')
        return redirect(url_for('renter_dashboard.dashboard'))
    
    # Check if payment is needed
    if booking.payment_status == 'paid':
        flash('Booking đã được thanh toán', 'info')
        return redirect(url_for('renter_bookings.booking_detail', booking_id=booking_id))
    
    if request.method == 'POST':
        return handle_payment_post(booking)
    
    # GET request - show payment form
    return render_template('renter/booking_payment.html', booking=booking)


# =============================================================================
# API ROUTES
# =============================================================================

@renter_bookings_bp.route('/api/bookings')
@renter_required
@handle_api_errors
def get_bookings_api():
    """Get bookings via API"""
    try:
        # Get query parameters
        status = request.args.get('status')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        # Build query
        query = Booking.query.filter_by(renter_id=current_user.id)
        
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
                'home_address': booking.home.address,
                'start_time': booking.start_time.isoformat(),
                'end_time': booking.end_time.isoformat(),
                'status': booking.status,
                'payment_status': booking.payment_status,
                'total_amount': booking.total_amount,
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


@renter_bookings_bp.route('/api/bookings/<int:booking_id>')
@renter_required
@handle_api_errors
def get_booking_detail_api(booking_id):
    """Get booking details via API"""
    try:
        booking = Booking.query.get_or_404(booking_id)
        
        # Check ownership
        if booking.renter_id != current_user.id:
            return jsonify({"error": "Unauthorized"}), 403
        
        # Format booking data
        booking_data = {
            'id': booking.id,
            'home': {
                'id': booking.home.id,
                'title': booking.home.title,
                'address': booking.home.address,
                'price': booking.home.price,
                'property_type': booking.home.property_type,
                'capacity': booking.home.capacity
            },
            'start_time': booking.start_time.isoformat(),
            'end_time': booking.end_time.isoformat(),
            'status': booking.status,
            'payment_status': booking.payment_status,
            'total_amount': booking.total_amount,
            'created_at': booking.created_at.isoformat(),
            'notes': booking.notes or ''
        }
        
        return jsonify({
            "success": True,
            "booking": booking_data
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting booking detail: {str(e)}")
        return jsonify({"error": "Failed to get booking detail"}), 500


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def handle_book_home_post(home):
    """Handle booking form submission for specific home"""
    try:
        # Get form data
        form_data = get_booking_form_data()
        
        # Validate required fields
        required_fields = ['start_time', 'end_time']
        self.validate_required_fields(form_data, required_fields)
        
        # Parse dates
        start_time = datetime.strptime(form_data['start_time'], '%Y-%m-%d')
        end_time = datetime.strptime(form_data['end_time'], '%Y-%m-%d')
        
        # Validate dates
        if start_time >= end_time:
            flash('Ngày kết thúc phải sau ngày bắt đầu', 'danger')
            return redirect(url_for('renter_bookings.book_home', home_id=home.id))
        
        if start_time < datetime.utcnow().date():
            flash('Không thể đặt phòng cho ngày trong quá khứ', 'danger')
            return redirect(url_for('renter_bookings.book_home', home_id=home.id))
        
        # Check availability
        if not is_home_available(home.id, start_time, end_time):
            flash('Nhà không khả dụng trong khoảng thời gian này', 'danger')
            return redirect(url_for('renter_bookings.book_home', home_id=home.id))
        
        # Calculate total amount
        nights = (end_time - start_time).days
        total_amount = home.price * nights
        
        # Create booking
        booking = Booking(
            home_id=home.id,
            renter_id=current_user.id,
            start_time=start_time,
            end_time=end_time,
            total_amount=total_amount,
            status='pending',
            payment_status='unpaid',
            notes=form_data.get('notes', '')
        )
        
        db.session.add(booking)
        db.session.commit()
        
        flash('Đặt phòng thành công! Vui lòng thanh toán để xác nhận.', 'success')
        return redirect(url_for('renter_bookings.booking_payment', booking_id=booking.id))
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error booking home: {str(e)}")
        flash('Có lỗi xảy ra khi đặt phòng', 'danger')
        return redirect(url_for('renter_bookings.book_home', home_id=home.id))


def handle_book_home_general_post():
    """Handle general booking form submission"""
    try:
        # Get form data
        form_data = get_booking_form_data()
        
        # Validate required fields
        required_fields = ['home_id', 'start_time', 'end_time']
        self.validate_required_fields(form_data, required_fields)
        
        # Get home
        home = Home.query.get_or_404(form_data['home_id'])
        
        # Parse dates
        start_time = datetime.strptime(form_data['start_time'], '%Y-%m-%d')
        end_time = datetime.strptime(form_data['end_time'], '%Y-%m-%d')
        
        # Validate dates
        if start_time >= end_time:
            flash('Ngày kết thúc phải sau ngày bắt đầu', 'danger')
            return redirect(url_for('renter_bookings.book_home_general'))
        
        if start_time < datetime.utcnow().date():
            flash('Không thể đặt phòng cho ngày trong quá khứ', 'danger')
            return redirect(url_for('renter_bookings.book_home_general'))
        
        # Check availability
        if not is_home_available(home.id, start_time, end_time):
            flash('Nhà không khả dụng trong khoảng thời gian này', 'danger')
            return redirect(url_for('renter_bookings.book_home_general'))
        
        # Calculate total amount
        nights = (end_time - start_time).days
        total_amount = home.price * nights
        
        # Create booking
        booking = Booking(
            home_id=home.id,
            renter_id=current_user.id,
            start_time=start_time,
            end_time=end_time,
            total_amount=total_amount,
            status='pending',
            payment_status='unpaid',
            notes=form_data.get('notes', '')
        )
        
        db.session.add(booking)
        db.session.commit()
        
        flash('Đặt phòng thành công! Vui lòng thanh toán để xác nhận.', 'success')
        return redirect(url_for('renter_bookings.booking_payment', booking_id=booking.id))
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error booking home: {str(e)}")
        flash('Có lỗi xảy ra khi đặt phòng', 'danger')
        return redirect(url_for('renter_bookings.book_home_general'))


def handle_review_post(booking):
    """Handle review form submission"""
    try:
        # Get form data
        rating = request.form.get('rating', type=int)
        comment = request.form.get('comment', '').strip()
        
        # Validate rating
        if not rating or not (1 <= rating <= 5):
            flash('Vui lòng chọn đánh giá từ 1 đến 5 sao', 'danger')
            return redirect(url_for('renter_bookings.review_booking', booking_id=booking.id))
        
        # Create review
        review = Review(
            booking_id=booking.id,
            rating=rating,
            comment=comment
        )
        
        db.session.add(review)
        db.session.commit()
        
        flash('Đánh giá đã được gửi thành công', 'success')
        return redirect(url_for('renter_bookings.booking_detail', booking_id=booking.id))
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error submitting review: {str(e)}")
        flash('Có lỗi xảy ra khi gửi đánh giá', 'danger')
        return redirect(url_for('renter_bookings.review_booking', booking_id=booking.id))


def handle_payment_post(booking):
    """Handle payment form submission"""
    try:
        # This would integrate with payment service
        # For now, just redirect to payment page
        
        flash('Chuyển hướng đến trang thanh toán...', 'info')
        return redirect(url_for('payment_unified.checkout', booking_id=booking.id))
        
    except Exception as e:
        current_app.logger.error(f"Error processing payment: {str(e)}")
        flash('Có lỗi xảy ra khi xử lý thanh toán', 'danger')
        return redirect(url_for('renter_bookings.booking_payment', booking_id=booking.id))


def get_booking_form_data():
    """Get and validate booking form data"""
    data = {
        'home_id': request.form.get('home_id', type=int),
        'start_time': request.form.get('start_time', '').strip(),
        'end_time': request.form.get('end_time', '').strip(),
        'notes': request.form.get('notes', '').strip()
    }
    
    return data


def is_home_available(home_id, start_time, end_time):
    """Check if home is available for booking"""
    # Check for conflicting bookings
    conflicting_bookings = Booking.query.filter(
        Booking.home_id == home_id,
        Booking.status.in_(['confirmed', 'active']),
        Booking.start_time < end_time,
        Booking.end_time > start_time
    ).count()
    
    return conflicting_bookings == 0


def can_cancel_booking(booking):
    """Check if booking can be cancelled"""
    # Check cancellation policy (e.g., 24 hours before check-in)
    hours_before_checkin = 24
    cancellation_deadline = booking.start_time - timedelta(hours=hours_before_checkin)
    
    return datetime.utcnow() < cancellation_deadline


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
    
    total_spent = sum(b.total_amount for b in bookings if b.payment_status == 'paid')
    
    return {
        'total_bookings': total_bookings,
        'confirmed_bookings': confirmed_bookings,
        'active_bookings': active_bookings,
        'completed_bookings': completed_bookings,
        'cancelled_bookings': cancelled_bookings,
        'total_spent': total_spent
    }
