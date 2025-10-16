"""
Owner Dashboard Routes - Dashboard, statistics, and overview functionality
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from datetime import datetime, timedelta
import json

from app.routes.decorators import owner_email_verified, owner_required
from app.routes.error_handlers import handle_api_errors, handle_web_errors
from app.routes.constants import FLASH_MESSAGES, URLS
from app.routes.base import BaseRouteHandler
from app.utils.cache import cache

# Import models
from app.models.models import db, Home, Booking, Payment, Review

owner_dashboard_bp = Blueprint('owner_dashboard', __name__, url_prefix='/owner')


class OwnerDashboardHandler(BaseRouteHandler):
    """Handler for owner dashboard functionality"""
    
    def __init__(self):
        super().__init__('owner_dashboard')


# =============================================================================
# DASHBOARD ROUTES
# =============================================================================

@owner_dashboard_bp.route('/dashboard')
@owner_email_verified
@handle_web_errors
def dashboard():
    """Owner dashboard using home service with caching"""
    try:
        owner_id = getattr(current_user, 'id', None)
        if owner_id is None:
            return redirect(url_for('auth.login'))

        # Get homes with error handling
        from app.services.owner.home_service import owner_home_service
        homes = owner_home_service.get_owner_homes(owner_id)
        
        return render_template('owner/dashboard.html', homes=homes)
    except Exception as e:
        current_app.logger.error(f"Error in dashboard: {str(e)}")
        # Fallback to empty homes list
        return render_template('owner/dashboard.html', homes=[])


@owner_dashboard_bp.route('/verify-email')
@login_required
@handle_web_errors
def verify_email():
    """Trang verify email cho Owner"""
    if current_user.email_verified:
        flash('Email đã được xác thực', 'info')
        return redirect(url_for('owner_dashboard.dashboard'))
    
    return render_template('owner/verify_email.html')


@owner_dashboard_bp.route('/settings')
@owner_email_verified
@handle_web_errors
def settings():
    """Owner settings page"""
    return render_template('owner/settings.html')


# =============================================================================
# STATISTICS ROUTES
# =============================================================================

@owner_dashboard_bp.route('/statistics')
@owner_required
@handle_web_errors
def statistics():
    """Owner statistics page using home service"""
    # Kiểm tra email verification cho Owner
    if current_user.is_owner() and not current_user.email_verified and current_user.first_login:
        return redirect(url_for('owner_dashboard.verify_email'))
    
    from app.services.owner.home_service import owner_home_service
    stats = owner_home_service.get_home_statistics(current_user.id)
    return render_template('owner/statistics.html', stats=stats)


@owner_dashboard_bp.route('/api/chart-data/<period>')
@owner_dashboard_bp.route('/api/chart-data/<period>/<chart_type>')
@owner_required
@handle_api_errors
def get_chart_data(period, chart_type='revenue'):
    """API endpoint để lấy dữ liệu chart"""
    try:
        # Validate period
        valid_periods = ['week', 'month', 'quarter', 'year']
        if period not in valid_periods:
            return jsonify({"error": "Invalid period"}), 400
        
        # Validate chart_type
        valid_chart_types = ['revenue', 'bookings', 'occupancy']
        if chart_type not in valid_chart_types:
            return jsonify({"error": "Invalid chart type"}), 400
        
        # Get data based on period and chart type
        data = get_chart_data_by_type(period, chart_type)
        
        return jsonify({
            "success": True,
            "data": data,
            "period": period,
            "chart_type": chart_type
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting chart data: {str(e)}")
        return jsonify({"error": "Failed to get chart data"}), 500


@owner_dashboard_bp.route('/api/stats-data/<period>')
@owner_dashboard_bp.route('/api/stats-data/<period>/<chart_type>')
@owner_required
@handle_api_errors
def get_stats_data(period, chart_type='revenue'):
    """API endpoint để lấy dữ liệu statistics"""
    try:
        # Validate period
        valid_periods = ['week', 'month', 'quarter', 'year']
        if period not in valid_periods:
            return jsonify({"error": "Invalid period"}), 400
        
        # Validate chart_type
        valid_chart_types = ['revenue', 'bookings', 'occupancy', 'reviews']
        if chart_type not in valid_chart_types:
            return jsonify({"error": "Invalid chart type"}), 400
        
        # Get data based on period and chart type
        data = get_stats_data_by_type(period, chart_type)
        
        return jsonify({
            "success": True,
            "data": data,
            "period": period,
            "chart_type": chart_type
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting stats data: {str(e)}")
        return jsonify({"error": "Failed to get stats data"}), 500


@owner_dashboard_bp.route('/api/stats-data/custom')
@owner_dashboard_bp.route('/api/stats-data/custom/<chart_type>')
@owner_required
@handle_api_errors
def get_custom_stats_data(chart_type='revenue'):
    """API endpoint để lấy dữ liệu statistics custom date range"""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        if not start_date or not end_date:
            return jsonify({"error": "Start date and end date are required"}), 400
        
        # Validate chart_type
        valid_chart_types = ['revenue', 'bookings', 'occupancy', 'reviews']
        if chart_type not in valid_chart_types:
            return jsonify({"error": "Invalid chart type"}), 400
        
        # Parse dates
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
            end_date = datetime.strptime(end_date, '%Y-%m-%d')
        except ValueError:
            return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400
        
        # Get data based on custom date range
        data = get_custom_stats_data_by_type(start_date, end_date, chart_type)
        
        return jsonify({
            "success": True,
            "data": data,
            "start_date": start_date.strftime('%Y-%m-%d'),
            "end_date": end_date.strftime('%Y-%m-%d'),
            "chart_type": chart_type
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting custom stats data: {str(e)}")
        return jsonify({"error": "Failed to get custom stats data"}), 500


@owner_dashboard_bp.route('/api/chart-data/custom')
@owner_required
@handle_api_errors
def get_custom_chart_data():
    """API endpoint để lấy dữ liệu chart custom date range"""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        chart_type = request.args.get('chart_type', 'revenue')
        
        if not start_date or not end_date:
            return jsonify({"error": "Start date and end date are required"}), 400
        
        # Validate chart_type
        valid_chart_types = ['revenue', 'bookings', 'occupancy']
        if chart_type not in valid_chart_types:
            return jsonify({"error": "Invalid chart type"}), 400
        
        # Parse dates
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
            end_date = datetime.strptime(end_date, '%Y-%m-%d')
        except ValueError:
            return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400
        
        # Get data based on custom date range
        data = get_custom_chart_data_by_type(start_date, end_date, chart_type)
        
        return jsonify({
            "success": True,
            "data": data,
            "start_date": start_date.strftime('%Y-%m-%d'),
            "end_date": end_date.strftime('%Y-%m-%d'),
            "chart_type": chart_type
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting custom chart data: {str(e)}")
        return jsonify({"error": "Failed to get custom chart data"}), 500


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_chart_data_by_type(period, chart_type):
    """Get chart data based on period and type"""
    # Get owner's homes
    homes = Home.query.filter_by(owner_id=current_user.id).all()
    home_ids = [home.id for home in homes]
    
    if not home_ids:
        return []
    
    # Calculate date range based on period
    now = datetime.utcnow()
    if period == 'week':
        start_date = now - timedelta(days=7)
    elif period == 'month':
        start_date = now - timedelta(days=30)
    elif period == 'quarter':
        start_date = now - timedelta(days=90)
    elif period == 'year':
        start_date = now - timedelta(days=365)
    
    if chart_type == 'revenue':
        return get_revenue_data(home_ids, start_date, now)
    elif chart_type == 'bookings':
        return get_bookings_data(home_ids, start_date, now)
    elif chart_type == 'occupancy':
        return get_occupancy_data(home_ids, start_date, now)
    
    return []


def get_stats_data_by_type(period, chart_type):
    """Get statistics data based on period and type"""
    # Get owner's homes
    homes = Home.query.filter_by(owner_id=current_user.id).all()
    home_ids = [home.id for home in homes]
    
    if not home_ids:
        return {}
    
    # Calculate date range based on period
    now = datetime.utcnow()
    if period == 'week':
        start_date = now - timedelta(days=7)
    elif period == 'month':
        start_date = now - timedelta(days=30)
    elif period == 'quarter':
        start_date = now - timedelta(days=90)
    elif period == 'year':
        start_date = now - timedelta(days=365)
    
    if chart_type == 'revenue':
        return get_revenue_stats(home_ids, start_date, now)
    elif chart_type == 'bookings':
        return get_bookings_stats(home_ids, start_date, now)
    elif chart_type == 'occupancy':
        return get_occupancy_stats(home_ids, start_date, now)
    elif chart_type == 'reviews':
        return get_reviews_stats(home_ids, start_date, now)
    
    return {}


def get_custom_stats_data_by_type(start_date, end_date, chart_type):
    """Get custom statistics data based on date range and type"""
    # Get owner's homes
    homes = Home.query.filter_by(owner_id=current_user.id).all()
    home_ids = [home.id for home in homes]
    
    if not home_ids:
        return {}
    
    if chart_type == 'revenue':
        return get_revenue_stats(home_ids, start_date, end_date)
    elif chart_type == 'bookings':
        return get_bookings_stats(home_ids, start_date, end_date)
    elif chart_type == 'occupancy':
        return get_occupancy_stats(home_ids, start_date, end_date)
    elif chart_type == 'reviews':
        return get_reviews_stats(home_ids, start_date, end_date)
    
    return {}


def get_custom_chart_data_by_type(start_date, end_date, chart_type):
    """Get custom chart data based on date range and type"""
    # Get owner's homes
    homes = Home.query.filter_by(owner_id=current_user.id).all()
    home_ids = [home.id for home in homes]
    
    if not home_ids:
        return []
    
    if chart_type == 'revenue':
        return get_revenue_data(home_ids, start_date, end_date)
    elif chart_type == 'bookings':
        return get_bookings_data(home_ids, start_date, end_date)
    elif chart_type == 'occupancy':
        return get_occupancy_data(home_ids, start_date, end_date)
    
    return []


def get_revenue_data(home_ids, start_date, end_date):
    """Get revenue data for chart with optimized query"""
    @cache.memoize(timeout=180)  # Cache for 3 minutes
    def _get_revenue_data():
        payments = Payment.query.join(Booking).filter(
            Booking.home_id.in_(home_ids),
            Payment.status == 'success',
            Payment.paid_at >= start_date,
            Payment.paid_at <= end_date
        ).with_entities(
            Payment.paid_at,
            Payment.amount
        ).order_by(Payment.paid_at).all()
        
        # Group by date
        revenue_by_date = {}
        for payment in payments:
            date_key = payment.paid_at.strftime('%Y-%m-%d')
            if date_key not in revenue_by_date:
                revenue_by_date[date_key] = 0
            revenue_by_date[date_key] += payment.amount
        
        # Convert to list format
        data = []
        current_date = start_date
        while current_date <= end_date:
            date_key = current_date.strftime('%Y-%m-%d')
            amount = revenue_by_date.get(date_key, 0)
            data.append({
                'date': date_key,
                'amount': amount
            })
            current_date += timedelta(days=1)
        
        return data
    
    return _get_revenue_data()


def get_bookings_data(home_ids, start_date, end_date):
    """Get bookings data for chart with optimized query"""
    @cache.memoize(timeout=180)  # Cache for 3 minutes
    def _get_bookings_data():
        bookings = Booking.query.filter(
            Booking.home_id.in_(home_ids),
            Booking.created_at >= start_date,
            Booking.created_at <= end_date
        ).with_entities(Booking.created_at).order_by(Booking.created_at).all()
        
        # Group by date
        bookings_by_date = {}
        for booking in bookings:
            date_key = booking.created_at.strftime('%Y-%m-%d')
            if date_key not in bookings_by_date:
                bookings_by_date[date_key] = 0
            bookings_by_date[date_key] += 1
        
        # Convert to list format
        data = []
        current_date = start_date
        while current_date <= end_date:
            date_key = current_date.strftime('%Y-%m-%d')
            count = bookings_by_date.get(date_key, 0)
            data.append({
                'date': date_key,
                'count': count
            })
            current_date += timedelta(days=1)
        
        return data
    
    return _get_bookings_data()


def get_occupancy_data(home_ids, start_date, end_date):
    """Get occupancy data for chart"""
    bookings = Booking.query.filter(
        Booking.home_id.in_(home_ids),
        Booking.status.in_(['confirmed', 'active']),
        Booking.start_time <= end_date,
        Booking.end_time >= start_date
    ).all()
    
    # Calculate occupancy by date
    occupancy_by_date = {}
    current_date = start_date
    while current_date <= end_date:
        date_key = current_date.strftime('%Y-%m-%d')
        occupancy_by_date[date_key] = 0
        
        for booking in bookings:
            if booking.start_time <= current_date <= booking.end_time:
                occupancy_by_date[date_key] += 1
        
        current_date += timedelta(days=1)
    
    # Convert to list format
    data = []
    for date_key, count in occupancy_by_date.items():
        data.append({
            'date': date_key,
            'count': count
        })
    
    return data


def get_revenue_stats(home_ids, start_date, end_date):
    """Get revenue statistics"""
    payments = Payment.query.join(Booking).filter(
        Booking.home_id.in_(home_ids),
        Payment.status == 'success',
        Payment.paid_at >= start_date,
        Payment.paid_at <= end_date
    ).all()
    
    total_revenue = sum(payment.amount for payment in payments)
    total_bookings = len(payments)
    average_revenue = total_revenue / total_bookings if total_bookings > 0 else 0
    
    return {
        'total_revenue': total_revenue,
        'total_bookings': total_bookings,
        'average_revenue': average_revenue
    }


def get_bookings_stats(home_ids, start_date, end_date):
    """Get bookings statistics"""
    bookings = Booking.query.filter(
        Booking.home_id.in_(home_ids),
        Booking.created_at >= start_date,
        Booking.created_at <= end_date
    ).all()
    
    confirmed_bookings = len([b for b in bookings if b.status == 'confirmed'])
    cancelled_bookings = len([b for b in bookings if b.status == 'cancelled'])
    completed_bookings = len([b for b in bookings if b.status == 'completed'])
    
    return {
        'total_bookings': len(bookings),
        'confirmed_bookings': confirmed_bookings,
        'cancelled_bookings': cancelled_bookings,
        'completed_bookings': completed_bookings
    }


def get_occupancy_stats(home_ids, start_date, end_date):
    """Get occupancy statistics"""
    bookings = Booking.query.filter(
        Booking.home_id.in_(home_ids),
        Booking.status.in_(['confirmed', 'active']),
        Booking.start_time <= end_date,
        Booking.end_time >= start_date
    ).all()
    
    total_nights = sum((booking.end_time - booking.start_time).days for booking in bookings)
    average_occupancy = total_nights / len(home_ids) if home_ids else 0
    
    return {
        'total_nights': total_nights,
        'average_occupancy': average_occupancy,
        'active_bookings': len(bookings)
    }


def get_reviews_stats(home_ids, start_date, end_date):
    """Get reviews statistics"""
    reviews = Review.query.join(Booking).filter(
        Booking.home_id.in_(home_ids),
        Review.created_at >= start_date,
        Review.created_at <= end_date
    ).all()
    
    if not reviews:
        return {
            'total_reviews': 0,
            'average_rating': 0,
            'rating_distribution': {}
        }
    
    total_reviews = len(reviews)
    average_rating = sum(review.rating for review in reviews) / total_reviews
    
    # Rating distribution
    rating_distribution = {}
    for i in range(1, 6):
        rating_distribution[i] = len([r for r in reviews if r.rating == i])
    
    return {
        'total_reviews': total_reviews,
        'average_rating': round(average_rating, 2),
        'rating_distribution': rating_distribution
    }
