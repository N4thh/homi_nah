"""
Renter Dashboard Routes - Dashboard and overview functionality
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from sqlalchemy import func, distinct, extract
import pytz

from app.routes.decorators import renter_email_verified, renter_required
from app.routes.error_handlers import handle_api_errors, handle_web_errors
from app.routes.constants import FLASH_MESSAGES, URLS, TIMEZONE, PAGINATION
from app.routes.base import BaseRouteHandler

# Import models
from app.models.models import db, Renter, Home, Booking, Payment, Review

renter_dashboard_bp = Blueprint('renter_dashboard', __name__, url_prefix='/renter')


class RenterDashboardHandler(BaseRouteHandler):
    """Handler for renter dashboard functionality"""
    
    def __init__(self):
        super().__init__('renter_dashboard')


# =============================================================================
# DASHBOARD ROUTES
# =============================================================================

@renter_dashboard_bp.route('/dashboard')
@renter_email_verified
@handle_web_errors
def dashboard():
    """Renter dashboard with statistics"""
    # Get basic statistics
    stats = get_dashboard_statistics()
    
    # Get recent bookings
    recent_bookings = get_recent_bookings()
    
    # Get recommended homes
    recommended_homes = get_recommended_homes()
    
    return render_template('renter/dashboard.html', 
                         stats=stats, 
                         recent_bookings=recent_bookings,
                         recommended_homes=recommended_homes)


@renter_dashboard_bp.route('/verify-email')
@login_required
@handle_web_errors
def verify_email():
    """Trang verify email cho Renter"""
    if current_user.email_verified:
        flash('Email đã được xác thực', 'info')
        return redirect(url_for('renter_dashboard.dashboard'))
    
    return render_template('renter/verify_email.html')


# =============================================================================
# STATISTICS API ROUTES
# =============================================================================

@renter_dashboard_bp.route('/api/stats/overview')
@renter_required
@handle_api_errors
def get_overview_stats():
    """Get overview statistics"""
    try:
        stats = get_dashboard_statistics()
        return jsonify({
            "success": True,
            "data": stats
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting overview stats: {str(e)}")
        return jsonify({"error": "Failed to get overview statistics"}), 500


@renter_dashboard_bp.route('/api/stats/bookings')
@renter_required
@handle_api_errors
def get_booking_stats():
    """Get booking statistics"""
    try:
        # Total bookings
        total_bookings = Booking.query.filter_by(renter_id=current_user.id).count()
        
        # Bookings by status
        bookings_by_status = db.session.query(
            Booking.status,
            func.count(Booking.id)
        ).filter(Booking.renter_id == current_user.id).group_by(Booking.status).all()
        
        # Total spent
        total_spent = db.session.query(func.sum(Payment.amount)).join(Booking).filter(
            Booking.renter_id == current_user.id,
            Payment.status == 'success'
        ).scalar() or 0
        
        # Average booking amount
        avg_booking = db.session.query(func.avg(Payment.amount)).join(Booking).filter(
            Booking.renter_id == current_user.id,
            Payment.status == 'success'
        ).scalar() or 0
        
        stats = {
            'total_bookings': total_bookings,
            'total_spent': total_spent,
            'avg_booking': round(avg_booking, 2),
            'bookings_by_status': [{'status': status, 'count': count} for status, count in bookings_by_status]
        }
        
        return jsonify({
            "success": True,
            "data": stats
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting booking stats: {str(e)}")
        return jsonify({"error": "Failed to get booking statistics"}), 500


@renter_dashboard_bp.route('/api/stats/spending')
@renter_required
@handle_api_errors
def get_spending_stats():
    """Get spending statistics"""
    try:
        # Monthly spending for last 12 months
        monthly_spending = []
        for i in range(12):
            month_start = datetime.utcnow() - timedelta(days=30 * (i + 1))
            month_end = datetime.utcnow() - timedelta(days=30 * i)
            
            spending = db.session.query(func.sum(Payment.amount)).join(Booking).filter(
                Booking.renter_id == current_user.id,
                Payment.status == 'success',
                Payment.paid_at >= month_start,
                Payment.paid_at < month_end
            ).scalar() or 0
            
            monthly_spending.append({
                'month': month_start.strftime('%Y-%m'),
                'amount': spending
            })
        
        return jsonify({
            "success": True,
            "data": list(reversed(monthly_spending))
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting spending stats: {str(e)}")
        return jsonify({"error": "Failed to get spending statistics"}), 500


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_dashboard_statistics():
    """Get comprehensive dashboard statistics"""
    # Bookings
    total_bookings = Booking.query.filter_by(renter_id=current_user.id).count()
    
    # Spending
    total_spent = db.session.query(func.sum(Payment.amount)).join(Booking).filter(
        Booking.renter_id == current_user.id,
        Payment.status == 'success'
    ).scalar() or 0
    
    # Reviews
    total_reviews = Review.query.join(Booking).filter(
        Booking.renter_id == current_user.id
    ).count()
    
    # Average rating given
    avg_rating_given = db.session.query(func.avg(Review.rating)).join(Booking).filter(
        Booking.renter_id == current_user.id
    ).scalar() or 0
    
    return {
        'total_bookings': total_bookings,
        'total_spent': total_spent,
        'total_reviews': total_reviews,
        'avg_rating_given': round(avg_rating_given, 2)
    }


def get_recent_bookings():
    """Get recent bookings for dashboard"""
    bookings = Booking.query.filter_by(renter_id=current_user.id).order_by(
        Booking.created_at.desc()
    ).limit(5).all()
    
    return [{
        'id': booking.id,
        'home_title': booking.home.title,
        'start_time': booking.start_time.strftime('%Y-%m-%d'),
        'end_time': booking.end_time.strftime('%Y-%m-%d'),
        'status': booking.status,
        'total_amount': booking.total_amount
    } for booking in bookings]


def get_recommended_homes():
    """Get recommended homes for dashboard"""
    # Get homes that user hasn't booked yet
    booked_home_ids = db.session.query(Booking.home_id).filter(
        Booking.renter_id == current_user.id
    ).distinct().all()
    booked_home_ids = [home_id[0] for home_id in booked_home_ids]
    
    # Get recommended homes
    if booked_home_ids:
        homes = Home.query.filter(
            Home.is_active == True,
            ~Home.id.in_(booked_home_ids)
        ).order_by(Home.created_at.desc()).limit(6).all()
    else:
        homes = Home.query.filter_by(is_active=True).order_by(
            Home.created_at.desc()
        ).limit(6).all()
    
    return [{
        'id': home.id,
        'title': home.title,
        'address': home.address,
        'price': home.price,
        'property_type': home.property_type,
        'capacity': home.capacity,
        'images': [img.filename for img in home.images[:3]]  # First 3 images
    } for home in homes]


def get_vietnam_datetime():
    """Get current datetime in Vietnam timezone"""
    vn_tz = pytz.timezone(TIMEZONE['VIETNAM'])
    return datetime.now(vn_tz)


def convert_to_utc(dt):
    """Convert datetime to UTC for database comparison"""
    vn_tz = pytz.timezone(TIMEZONE['VIETNAM'])
    return vn_tz.localize(dt).astimezone(pytz.UTC).replace(tzinfo=None)
