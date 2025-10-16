"""
Admin Reports Routes - Reports and analytics functionality
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from sqlalchemy import func, distinct, extract
import pytz

from app.routes.decorators import admin_required, super_admin_required
from app.routes.error_handlers import handle_api_errors, handle_web_errors
from app.routes.constants import FLASH_MESSAGES, URLS, TIMEZONE, PAGINATION
from app.routes.base import BaseRouteHandler

# Import models
from app.models.models import db, Admin, Owner, Renter, Home, Booking, Payment, Review

admin_reports_bp = Blueprint('admin_reports', __name__, url_prefix='/admin')


class AdminReportsHandler(BaseRouteHandler):
    """Handler for admin reports functionality"""
    
    def __init__(self):
        super().__init__('admin_reports')


# =============================================================================
# REPORTS ROUTES
# =============================================================================

@admin_reports_bp.route('/reports')
@admin_required
@handle_web_errors
def reports():
    """Admin reports dashboard"""
    # Get comprehensive reports data
    reports_data = get_comprehensive_reports()
    
    return render_template('admin/reports.html', 
                         reports=reports_data)


@admin_reports_bp.route('/reports/users')
@admin_required
@handle_web_errors
def user_reports():
    """User reports page"""
    # Get user reports data
    user_reports_data = get_user_reports()
    
    return render_template('admin/user_reports.html', 
                         reports=user_reports_data)


@admin_reports_bp.route('/reports/homes')
@admin_required
@handle_web_errors
def home_reports():
    """Home reports page"""
    # Get home reports data
    home_reports_data = get_home_reports()
    
    return render_template('admin/home_reports.html', 
                         reports=home_reports_data)


@admin_reports_bp.route('/reports/bookings')
@admin_required
@handle_web_errors
def booking_reports():
    """Booking reports page"""
    # Get booking reports data
    booking_reports_data = get_booking_reports()
    
    return render_template('admin/booking_reports.html', 
                         reports=booking_reports_data)


@admin_reports_bp.route('/reports/revenue')
@admin_required
@handle_web_errors
def revenue_reports():
    """Revenue reports page"""
    # Get revenue reports data
    revenue_reports_data = get_revenue_reports()
    
    return render_template('admin/revenue_reports.html', 
                         reports=revenue_reports_data)


# =============================================================================
# API ROUTES FOR REPORTS
# =============================================================================

@admin_reports_bp.route('/api/reports/overview')
@admin_required
@handle_api_errors
def get_reports_overview():
    """Get reports overview data"""
    try:
        # Get overview data
        overview_data = get_comprehensive_reports()
        
        return jsonify({
            "success": True,
            "data": overview_data
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting reports overview: {str(e)}")
        return jsonify({"error": "Failed to get reports overview"}), 500


@admin_reports_bp.route('/api/reports/users/<period>')
@admin_required
@handle_api_errors
def get_user_reports_api(period):
    """Get user reports for specific period"""
    try:
        # Validate period
        valid_periods = ['week', 'month', 'quarter', 'year']
        if period not in valid_periods:
            return jsonify({"error": "Invalid period"}), 400
        
        # Calculate date range
        now = datetime.utcnow()
        if period == 'week':
            start_date = now - timedelta(days=7)
        elif period == 'month':
            start_date = now - timedelta(days=30)
        elif period == 'quarter':
            start_date = now - timedelta(days=90)
        elif period == 'year':
            start_date = now - timedelta(days=365)
        
        # Get user data
        user_data = get_user_data_by_period(start_date, now)
        
        return jsonify({
            "success": True,
            "data": user_data,
            "period": period
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting user reports: {str(e)}")
        return jsonify({"error": "Failed to get user reports"}), 500


@admin_reports_bp.route('/api/reports/homes/<period>')
@admin_required
@handle_api_errors
def get_home_reports_api(period):
    """Get home reports for specific period"""
    try:
        # Validate period
        valid_periods = ['week', 'month', 'quarter', 'year']
        if period not in valid_periods:
            return jsonify({"error": "Invalid period"}), 400
        
        # Calculate date range
        now = datetime.utcnow()
        if period == 'week':
            start_date = now - timedelta(days=7)
        elif period == 'month':
            start_date = now - timedelta(days=30)
        elif period == 'quarter':
            start_date = now - timedelta(days=90)
        elif period == 'year':
            start_date = now - timedelta(days=365)
        
        # Get home data
        home_data = get_home_data_by_period(start_date, now)
        
        return jsonify({
            "success": True,
            "data": home_data,
            "period": period
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting home reports: {str(e)}")
        return jsonify({"error": "Failed to get home reports"}), 500


@admin_reports_bp.route('/api/reports/bookings/<period>')
@admin_required
@handle_api_errors
def get_booking_reports_api(period):
    """Get booking reports for specific period"""
    try:
        # Validate period
        valid_periods = ['week', 'month', 'quarter', 'year']
        if period not in valid_periods:
            return jsonify({"error": "Invalid period"}), 400
        
        # Calculate date range
        now = datetime.utcnow()
        if period == 'week':
            start_date = now - timedelta(days=7)
        elif period == 'month':
            start_date = now - timedelta(days=30)
        elif period == 'quarter':
            start_date = now - timedelta(days=90)
        elif period == 'year':
            start_date = now - timedelta(days=365)
        
        # Get booking data
        booking_data = get_booking_data_by_period(start_date, now)
        
        return jsonify({
            "success": True,
            "data": booking_data,
            "period": period
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting booking reports: {str(e)}")
        return jsonify({"error": "Failed to get booking reports"}), 500


@admin_reports_bp.route('/api/reports/revenue/<period>')
@admin_required
@handle_api_errors
def get_revenue_reports_api(period):
    """Get revenue reports for specific period"""
    try:
        # Validate period
        valid_periods = ['week', 'month', 'quarter', 'year']
        if period not in valid_periods:
            return jsonify({"error": "Invalid period"}), 400
        
        # Calculate date range
        now = datetime.utcnow()
        if period == 'week':
            start_date = now - timedelta(days=7)
        elif period == 'month':
            start_date = now - timedelta(days=30)
        elif period == 'quarter':
            start_date = now - timedelta(days=90)
        elif period == 'year':
            start_date = now - timedelta(days=365)
        
        # Get revenue data
        revenue_data = get_revenue_data_by_period(start_date, now)
        
        return jsonify({
            "success": True,
            "data": revenue_data,
            "period": period
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting revenue reports: {str(e)}")
        return jsonify({"error": "Failed to get revenue reports"}), 500


@admin_reports_bp.route('/api/reports/export')
@admin_required
@handle_api_errors
def export_reports():
    """Export reports data"""
    try:
        report_type = request.args.get('type', 'overview')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        # Parse dates
        if start_date:
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d')
            except ValueError:
                return jsonify({"error": "Invalid start date format"}), 400
        
        if end_date:
            try:
                end_date = datetime.strptime(end_date, '%Y-%m-%d')
            except ValueError:
                return jsonify({"error": "Invalid end date format"}), 400
        
        # Get export data based on type
        if report_type == 'overview':
            export_data = get_comprehensive_reports()
        elif report_type == 'users':
            export_data = get_user_reports()
        elif report_type == 'homes':
            export_data = get_home_reports()
        elif report_type == 'bookings':
            export_data = get_booking_reports()
        elif report_type == 'revenue':
            export_data = get_revenue_reports()
        else:
            return jsonify({"error": "Invalid report type"}), 400
        
        return jsonify({
            "success": True,
            "data": export_data,
            "type": report_type,
            "exported_at": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        current_app.logger.error(f"Error exporting reports: {str(e)}")
        return jsonify({"error": "Failed to export reports"}), 500


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_comprehensive_reports():
    """Get comprehensive reports data"""
    # Users
    total_users = Owner.query.count() + Renter.query.count()
    active_users = Owner.query.filter(Owner.last_login >= datetime.utcnow() - timedelta(days=30)).count() + \
                  Renter.query.filter(Renter.last_login >= datetime.utcnow() - timedelta(days=30)).count()
    
    # Homes
    total_homes = Home.query.count()
    active_homes = Home.query.filter_by(is_active=True).count()
    
    # Bookings
    total_bookings = Booking.query.count()
    monthly_bookings = Booking.query.filter(
        Booking.created_at >= datetime.utcnow().replace(day=1)
    ).count()
    
    # Revenue
    total_revenue = db.session.query(func.sum(Payment.amount)).filter(
        Payment.status == 'success'
    ).scalar() or 0
    
    monthly_revenue = db.session.query(func.sum(Payment.amount)).filter(
        Payment.status == 'success',
        Payment.paid_at >= datetime.utcnow().replace(day=1)
    ).scalar() or 0
    
    # Reviews
    total_reviews = Review.query.count()
    avg_rating = db.session.query(func.avg(Review.rating)).scalar() or 0
    
    return {
        'users': {
            'total': total_users,
            'active': active_users,
            'growth': get_user_growth()
        },
        'homes': {
            'total': total_homes,
            'active': active_homes,
            'growth': get_home_growth()
        },
        'bookings': {
            'total': total_bookings,
            'monthly': monthly_bookings,
            'growth': get_booking_growth()
        },
        'revenue': {
            'total': total_revenue,
            'monthly': monthly_revenue,
            'growth': get_revenue_growth()
        },
        'reviews': {
            'total': total_reviews,
            'avg_rating': round(avg_rating, 2)
        }
    }


def get_user_reports():
    """Get user reports data"""
    # Monthly user registration
    monthly_users = []
    for i in range(12):
        month_start = datetime.utcnow() - timedelta(days=30 * (i + 1))
        month_end = datetime.utcnow() - timedelta(days=30 * i)
        
        owners = Owner.query.filter(
            Owner.created_at >= month_start,
            Owner.created_at < month_end
        ).count()
        
        renters = Renter.query.filter(
            Renter.created_at >= month_start,
            Renter.created_at < month_end
        ).count()
        
        monthly_users.append({
            'month': month_start.strftime('%Y-%m'),
            'owners': owners,
            'renters': renters,
            'total': owners + renters
        })
    
    # User activity
    active_users = Owner.query.filter(Owner.last_login >= datetime.utcnow() - timedelta(days=30)).count() + \
                  Renter.query.filter(Renter.last_login >= datetime.utcnow() - timedelta(days=30)).count()
    
    return {
        'monthly_users': list(reversed(monthly_users)),
        'active_users': active_users
    }


def get_home_reports():
    """Get home reports data"""
    # Monthly home creation
    monthly_homes = []
    for i in range(12):
        month_start = datetime.utcnow() - timedelta(days=30 * (i + 1))
        month_end = datetime.utcnow() - timedelta(days=30 * i)
        
        homes_count = Home.query.filter(
            Home.created_at >= month_start,
            Home.created_at < month_end
        ).count()
        
        monthly_homes.append({
            'month': month_start.strftime('%Y-%m'),
            'count': homes_count
        })
    
    # Property type distribution
    property_distribution = db.session.query(
        Home.property_type,
        func.count(Home.id)
    ).group_by(Home.property_type).all()
    
    return {
        'monthly_homes': list(reversed(monthly_homes)),
        'property_distribution': [{'type': prop_type, 'count': count} for prop_type, count in property_distribution]
    }


def get_booking_reports():
    """Get booking reports data"""
    # Monthly bookings
    monthly_bookings = []
    for i in range(12):
        month_start = datetime.utcnow() - timedelta(days=30 * (i + 1))
        month_end = datetime.utcnow() - timedelta(days=30 * i)
        
        bookings_count = Booking.query.filter(
            Booking.created_at >= month_start,
            Booking.created_at < month_end
        ).count()
        
        monthly_bookings.append({
            'month': month_start.strftime('%Y-%m'),
            'count': bookings_count
        })
    
    # Booking status distribution
    status_distribution = db.session.query(
        Booking.status,
        func.count(Booking.id)
    ).group_by(Booking.status).all()
    
    return {
        'monthly_bookings': list(reversed(monthly_bookings)),
        'status_distribution': [{'status': status, 'count': count} for status, count in status_distribution]
    }


def get_revenue_reports():
    """Get revenue reports data"""
    # Monthly revenue
    monthly_revenue = []
    for i in range(12):
        month_start = datetime.utcnow() - timedelta(days=30 * (i + 1))
        month_end = datetime.utcnow() - timedelta(days=30 * i)
        
        revenue = db.session.query(func.sum(Payment.amount)).filter(
            Payment.status == 'success',
            Payment.paid_at >= month_start,
            Payment.paid_at < month_end
        ).scalar() or 0
        
        monthly_revenue.append({
            'month': month_start.strftime('%Y-%m'),
            'revenue': revenue
        })
    
    # Revenue by home
    revenue_by_home = db.session.query(
        Home.title,
        func.sum(Payment.amount)
    ).join(Booking).join(Payment).filter(
        Payment.status == 'success'
    ).group_by(Home.id, Home.title).order_by(
        func.sum(Payment.amount).desc()
    ).limit(10).all()
    
    return {
        'monthly_revenue': list(reversed(monthly_revenue)),
        'revenue_by_home': [{'home': title, 'revenue': revenue} for title, revenue in revenue_by_home]
    }


def get_user_data_by_period(start_date, end_date):
    """Get user data for specific period"""
    # New users
    new_owners = Owner.query.filter(
        Owner.created_at >= start_date,
        Owner.created_at <= end_date
    ).count()
    
    new_renters = Renter.query.filter(
        Renter.created_at >= start_date,
        Renter.created_at <= end_date
    ).count()
    
    # Active users
    active_owners = Owner.query.filter(
        Owner.last_login >= start_date,
        Owner.last_login <= end_date
    ).count()
    
    active_renters = Renter.query.filter(
        Renter.last_login >= start_date,
        Renter.last_login <= end_date
    ).count()
    
    return {
        'new_owners': new_owners,
        'new_renters': new_renters,
        'active_owners': active_owners,
        'active_renters': active_renters
    }


def get_home_data_by_period(start_date, end_date):
    """Get home data for specific period"""
    # New homes
    new_homes = Home.query.filter(
        Home.created_at >= start_date,
        Home.created_at <= end_date
    ).count()
    
    # Active homes
    active_homes = Home.query.filter(
        Home.is_active == True,
        Home.created_at <= end_date
    ).count()
    
    return {
        'new_homes': new_homes,
        'active_homes': active_homes
    }


def get_booking_data_by_period(start_date, end_date):
    """Get booking data for specific period"""
    # New bookings
    new_bookings = Booking.query.filter(
        Booking.created_at >= start_date,
        Booking.created_at <= end_date
    ).count()
    
    # Successful bookings
    successful_bookings = Booking.query.filter(
        Booking.created_at >= start_date,
        Booking.created_at <= end_date,
        Booking.payment_status == 'paid'
    ).count()
    
    return {
        'new_bookings': new_bookings,
        'successful_bookings': successful_bookings
    }


def get_revenue_data_by_period(start_date, end_date):
    """Get revenue data for specific period"""
    # Total revenue
    total_revenue = db.session.query(func.sum(Payment.amount)).filter(
        Payment.status == 'success',
        Payment.paid_at >= start_date,
        Payment.paid_at <= end_date
    ).scalar() or 0
    
    # Average payment
    avg_payment = db.session.query(func.avg(Payment.amount)).filter(
        Payment.status == 'success',
        Payment.paid_at >= start_date,
        Payment.paid_at <= end_date
    ).scalar() or 0
    
    return {
        'total_revenue': total_revenue,
        'avg_payment': round(avg_payment, 2)
    }


def get_user_growth():
    """Calculate user growth rate"""
    current_month = Owner.query.filter(
        Owner.created_at >= datetime.utcnow().replace(day=1)
    ).count() + Renter.query.filter(
        Renter.created_at >= datetime.utcnow().replace(day=1)
    ).count()
    
    last_month_start = (datetime.utcnow().replace(day=1) - timedelta(days=1)).replace(day=1)
    last_month = Owner.query.filter(
        Owner.created_at >= last_month_start,
        Owner.created_at < datetime.utcnow().replace(day=1)
    ).count() + Renter.query.filter(
        Renter.created_at >= last_month_start,
        Renter.created_at < datetime.utcnow().replace(day=1)
    ).count()
    
    if last_month > 0:
        return round(((current_month - last_month) / last_month) * 100, 2)
    return 0


def get_home_growth():
    """Calculate home growth rate"""
    current_month = Home.query.filter(
        Home.created_at >= datetime.utcnow().replace(day=1)
    ).count()
    
    last_month_start = (datetime.utcnow().replace(day=1) - timedelta(days=1)).replace(day=1)
    last_month = Home.query.filter(
        Home.created_at >= last_month_start,
        Home.created_at < datetime.utcnow().replace(day=1)
    ).count()
    
    if last_month > 0:
        return round(((current_month - last_month) / last_month) * 100, 2)
    return 0


def get_booking_growth():
    """Calculate booking growth rate"""
    current_month = Booking.query.filter(
        Booking.created_at >= datetime.utcnow().replace(day=1)
    ).count()
    
    last_month_start = (datetime.utcnow().replace(day=1) - timedelta(days=1)).replace(day=1)
    last_month = Booking.query.filter(
        Booking.created_at >= last_month_start,
        Booking.created_at < datetime.utcnow().replace(day=1)
    ).count()
    
    if last_month > 0:
        return round(((current_month - last_month) / last_month) * 100, 2)
    return 0


def get_revenue_growth():
    """Calculate revenue growth rate"""
    current_month = db.session.query(func.sum(Payment.amount)).filter(
        Payment.status == 'success',
        Payment.paid_at >= datetime.utcnow().replace(day=1)
    ).scalar() or 0
    
    last_month_start = (datetime.utcnow().replace(day=1) - timedelta(days=1)).replace(day=1)
    last_month = db.session.query(func.sum(Payment.amount)).filter(
        Payment.status == 'success',
        Payment.paid_at >= last_month_start,
        Payment.paid_at < datetime.utcnow().replace(day=1)
    ).scalar() or 0
    
    if last_month > 0:
        return round(((current_month - last_month) / last_month) * 100, 2)
    return 0
