"""
Owner Reports Routes - Reports and analytics functionality
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from sqlalchemy import func, extract
import json

from app.routes.decorators import owner_required
from app.routes.error_handlers import handle_api_errors, handle_web_errors
from app.routes.constants import FLASH_MESSAGES, URLS, BOOKING_STATUS, PAYMENT_STATUS
from app.routes.base import BaseRouteHandler

# Import models
from app.models.models import db, Home, Booking, Payment, Review

owner_reports_bp = Blueprint('owner_reports', __name__, url_prefix='/owner')


class OwnerReportsHandler(BaseRouteHandler):
    """Handler for owner reports functionality"""
    
    def __init__(self):
        super().__init__('owner_reports')


# =============================================================================
# REPORTS ROUTES
# =============================================================================

@owner_reports_bp.route('/reports')
@owner_required
@handle_web_errors
def reports():
    """Owner reports dashboard"""
    # Get owner's homes
    homes = Home.query.filter_by(owner_id=current_user.id).all()
    home_ids = [home.id for home in homes]
    
    if not home_ids:
        return render_template('owner/reports.html', 
                             homes=[], 
                             stats={}, 
                             recent_bookings=[], 
                             recent_payments=[])
    
    # Get basic statistics
    stats = get_basic_stats(home_ids)
    
    # Get recent bookings
    recent_bookings = get_recent_bookings(home_ids, limit=5)
    
    # Get recent payments
    recent_payments = get_recent_payments(home_ids, limit=5)
    
    return render_template('owner/reports.html', 
                         homes=homes,
                         stats=stats, 
                         recent_bookings=recent_bookings, 
                         recent_payments=recent_payments)


@owner_reports_bp.route('/reports/revenue')
@owner_required
@handle_web_errors
def revenue_report():
    """Revenue report page"""
    # Get owner's homes
    homes = Home.query.filter_by(owner_id=current_user.id).all()
    home_ids = [home.id for home in homes]
    
    if not home_ids:
        return render_template('owner/revenue_report.html', 
                             homes=[], 
                             revenue_data={})
    
    # Get revenue data
    revenue_data = get_revenue_report_data(home_ids)
    
    return render_template('owner/revenue_report.html', 
                         homes=homes,
                         revenue_data=revenue_data)


@owner_reports_bp.route('/reports/bookings')
@owner_required
@handle_web_errors
def bookings_report():
    """Bookings report page"""
    # Get owner's homes
    homes = Home.query.filter_by(owner_id=current_user.id).all()
    home_ids = [home.id for home in homes]
    
    if not home_ids:
        return render_template('owner/bookings_report.html', 
                             homes=[], 
                             bookings_data={})
    
    # Get bookings data
    bookings_data = get_bookings_report_data(home_ids)
    
    return render_template('owner/bookings_report.html', 
                         homes=homes,
                         bookings_data=bookings_data)


@owner_reports_bp.route('/reports/occupancy')
@owner_required
@handle_web_errors
def occupancy_report():
    """Occupancy report page"""
    # Get owner's homes
    homes = Home.query.filter_by(owner_id=current_user.id).all()
    home_ids = [home.id for home in homes]
    
    if not home_ids:
        return render_template('owner/occupancy_report.html', 
                             homes=[], 
                             occupancy_data={})
    
    # Get occupancy data
    occupancy_data = get_occupancy_report_data(home_ids)
    
    return render_template('owner/occupancy_report.html', 
                         homes=homes,
                         occupancy_data=occupancy_data)


# =============================================================================
# API ROUTES FOR REPORTS
# =============================================================================

@owner_reports_bp.route('/api/reports/summary')
@owner_required
@handle_api_errors
def get_reports_summary():
    """Get reports summary data"""
    try:
        # Get owner's homes
        homes = Home.query.filter_by(owner_id=current_user.id).all()
        home_ids = [home.id for home in homes]
        
        if not home_ids:
            return jsonify({
                "success": True,
                "data": {
                    "total_homes": 0,
                    "total_bookings": 0,
                    "total_revenue": 0,
                    "occupancy_rate": 0
                }
            })
        
        # Get summary data
        summary_data = get_basic_stats(home_ids)
        
        return jsonify({
            "success": True,
            "data": summary_data
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting reports summary: {str(e)}")
        return jsonify({"error": "Failed to get reports summary"}), 500


@owner_reports_bp.route('/api/reports/revenue/<period>')
@owner_required
@handle_api_errors
def get_revenue_data(period):
    """Get revenue data for specific period"""
    try:
        # Validate period
        valid_periods = ['week', 'month', 'quarter', 'year']
        if period not in valid_periods:
            return jsonify({"error": "Invalid period"}), 400
        
        # Get owner's homes
        homes = Home.query.filter_by(owner_id=current_user.id).all()
        home_ids = [home.id for home in homes]
        
        if not home_ids:
            return jsonify({"success": True, "data": []})
        
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
        revenue_data = get_revenue_data_by_period(home_ids, start_date, now)
        
        return jsonify({
            "success": True,
            "data": revenue_data,
            "period": period
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting revenue data: {str(e)}")
        return jsonify({"error": "Failed to get revenue data"}), 500


@owner_reports_bp.route('/api/reports/bookings/<period>')
@owner_required
@handle_api_errors
def get_bookings_data(period):
    """Get bookings data for specific period"""
    try:
        # Validate period
        valid_periods = ['week', 'month', 'quarter', 'year']
        if period not in valid_periods:
            return jsonify({"error": "Invalid period"}), 400
        
        # Get owner's homes
        homes = Home.query.filter_by(owner_id=current_user.id).all()
        home_ids = [home.id for home in homes]
        
        if not home_ids:
            return jsonify({"success": True, "data": []})
        
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
        
        # Get bookings data
        bookings_data = get_bookings_data_by_period(home_ids, start_date, now)
        
        return jsonify({
            "success": True,
            "data": bookings_data,
            "period": period
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting bookings data: {str(e)}")
        return jsonify({"error": "Failed to get bookings data"}), 500


@owner_reports_bp.route('/api/reports/occupancy/<period>')
@owner_required
@handle_api_errors
def get_occupancy_data(period):
    """Get occupancy data for specific period"""
    try:
        # Validate period
        valid_periods = ['week', 'month', 'quarter', 'year']
        if period not in valid_periods:
            return jsonify({"error": "Invalid period"}), 400
        
        # Get owner's homes
        homes = Home.query.filter_by(owner_id=current_user.id).all()
        home_ids = [home.id for home in homes]
        
        if not home_ids:
            return jsonify({"success": True, "data": []})
        
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
        
        # Get occupancy data
        occupancy_data = get_occupancy_data_by_period(home_ids, start_date, now)
        
        return jsonify({
            "success": True,
            "data": occupancy_data,
            "period": period
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting occupancy data: {str(e)}")
        return jsonify({"error": "Failed to get occupancy data"}), 500


@owner_reports_bp.route('/api/reports/custom')
@owner_required
@handle_api_errors
def get_custom_report_data():
    """Get custom report data based on date range"""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        report_type = request.args.get('type', 'revenue')
        
        if not start_date or not end_date:
            return jsonify({"error": "Start date and end date are required"}), 400
        
        # Parse dates
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
            end_date = datetime.strptime(end_date, '%Y-%m-%d')
        except ValueError:
            return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400
        
        # Get owner's homes
        homes = Home.query.filter_by(owner_id=current_user.id).all()
        home_ids = [home.id for home in homes]
        
        if not home_ids:
            return jsonify({"success": True, "data": []})
        
        # Get data based on report type
        if report_type == 'revenue':
            data = get_revenue_data_by_period(home_ids, start_date, end_date)
        elif report_type == 'bookings':
            data = get_bookings_data_by_period(home_ids, start_date, end_date)
        elif report_type == 'occupancy':
            data = get_occupancy_data_by_period(home_ids, start_date, end_date)
        else:
            return jsonify({"error": "Invalid report type"}), 400
        
        return jsonify({
            "success": True,
            "data": data,
            "start_date": start_date.strftime('%Y-%m-%d'),
            "end_date": end_date.strftime('%Y-%m-%d'),
            "type": report_type
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting custom report data: {str(e)}")
        return jsonify({"error": "Failed to get custom report data"}), 500


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_basic_stats(home_ids):
    """Get basic statistics for owner's homes"""
    # Total homes
    total_homes = len(home_ids)
    
    # Total bookings
    total_bookings = Booking.query.filter(Booking.home_id.in_(home_ids)).count()
    
    # Total revenue
    total_revenue = db.session.query(func.sum(Payment.amount)).join(Booking).filter(
        Booking.home_id.in_(home_ids),
        Payment.status == 'success'
    ).scalar() or 0
    
    # Occupancy rate (simplified)
    total_nights = db.session.query(func.sum(
        func.extract('day', Booking.end_time - Booking.start_time)
    )).filter(
        Booking.home_id.in_(home_ids),
        Booking.payment_status == 'paid'
    ).scalar() or 0
    
    # Calculate occupancy rate
    days_in_period = 365  # Last year
    max_possible_nights = total_homes * days_in_period
    occupancy_rate = (total_nights / max_possible_nights * 100) if max_possible_nights > 0 else 0
    
    return {
        'total_homes': total_homes,
        'total_bookings': total_bookings,
        'total_revenue': total_revenue,
        'occupancy_rate': round(occupancy_rate, 2)
    }


def get_recent_bookings(home_ids, limit=5):
    """Get recent bookings"""
    bookings = Booking.query.filter(
        Booking.home_id.in_(home_ids)
    ).order_by(Booking.created_at.desc()).limit(limit).all()
    
    return [{
        'id': booking.id,
        'home_title': booking.home.title,
        'renter_name': booking.renter.full_name if booking.renter else 'N/A',
        'start_time': booking.start_time.strftime('%Y-%m-%d'),
        'end_time': booking.end_time.strftime('%Y-%m-%d'),
        'status': booking.status,
        'total_price': booking.total_price
    } for booking in bookings]


def get_recent_payments(home_ids, limit=5):
    """Get recent payments"""
    payments = Payment.query.join(Booking).filter(
        Booking.home_id.in_(home_ids),
        Payment.status == 'success'
    ).order_by(Payment.paid_at.desc()).limit(limit).all()
    
    return [{
        'id': payment.id,
        'home_title': payment.booking.home.title,
        'renter_name': payment.booking.renter.full_name if payment.booking.renter else 'N/A',
        'amount': payment.amount,
        'paid_at': payment.paid_at.strftime('%Y-%m-%d %H:%M') if payment.paid_at else 'N/A',
        'payment_code': payment.payment_code
    } for payment in payments]


def get_revenue_report_data(home_ids):
    """Get revenue report data"""
    # Monthly revenue for last 12 months
    monthly_revenue = []
    for i in range(12):
        month_start = datetime.utcnow() - timedelta(days=30 * (i + 1))
        month_end = datetime.utcnow() - timedelta(days=30 * i)
        
        revenue = db.session.query(func.sum(Payment.amount)).join(Booking).filter(
            Booking.home_id.in_(home_ids),
            Payment.status == 'success',
            Payment.paid_at >= month_start,
            Payment.paid_at < month_end
        ).scalar() or 0
        
        monthly_revenue.append({
            'month': month_start.strftime('%Y-%m'),
            'revenue': revenue
        })
    
    # Revenue by home
    home_revenue = db.session.query(
        Home.title,
        func.sum(Payment.amount)
    ).join(Booking).join(Payment).filter(
        Booking.home_id.in_(home_ids),
        Payment.status == 'success'
    ).group_by(Home.id, Home.title).all()
    
    return {
        'monthly_revenue': list(reversed(monthly_revenue)),
        'home_revenue': [{'home': title, 'revenue': revenue} for title, revenue in home_revenue]
    }


def get_bookings_report_data(home_ids):
    """Get bookings report data"""
    # Monthly bookings for last 12 months
    monthly_bookings = []
    for i in range(12):
        month_start = datetime.utcnow() - timedelta(days=30 * (i + 1))
        month_end = datetime.utcnow() - timedelta(days=30 * i)
        
        bookings_count = Booking.query.filter(
            Booking.home_id.in_(home_ids),
            Booking.created_at >= month_start,
            Booking.created_at < month_end
        ).count()
        
        monthly_bookings.append({
            'month': month_start.strftime('%Y-%m'),
            'bookings': bookings_count
        })
    
    # Bookings by status
    status_bookings = db.session.query(
        Booking.status,
        func.count(Booking.id)
    ).filter(
        Booking.home_id.in_(home_ids)
    ).group_by(Booking.status).all()
    
    return {
        'monthly_bookings': list(reversed(monthly_bookings)),
        'status_bookings': [{'status': status, 'count': count} for status, count in status_bookings]
    }


def get_occupancy_report_data(home_ids):
    """Get occupancy report data"""
    # Monthly occupancy for last 12 months
    monthly_occupancy = []
    for i in range(12):
        month_start = datetime.utcnow() - timedelta(days=30 * (i + 1))
        month_end = datetime.utcnow() - timedelta(days=30 * i)
        
        # Calculate occupied nights for this month
        occupied_nights = db.session.query(func.sum(
            func.extract('day', Booking.end_time - Booking.start_time)
        )).filter(
            Booking.home_id.in_(home_ids),
            Booking.payment_status == 'paid',
            Booking.start_time < month_end,
            Booking.end_time >= month_start
        ).scalar() or 0
        
        # Calculate occupancy rate
        total_homes = len(home_ids)
        days_in_month = 30
        max_possible_nights = total_homes * days_in_month
        occupancy_rate = (occupied_nights / max_possible_nights * 100) if max_possible_nights > 0 else 0
        
        monthly_occupancy.append({
            'month': month_start.strftime('%Y-%m'),
            'occupancy_rate': round(occupancy_rate, 2),
            'occupied_nights': occupied_nights
        })
    
    return {
        'monthly_occupancy': list(reversed(monthly_occupancy))
    }


def get_revenue_data_by_period(home_ids, start_date, end_date):
    """Get revenue data for specific period"""
    # Group by date
    revenue_by_date = {}
    current_date = start_date
    
    while current_date <= end_date:
        date_key = current_date.strftime('%Y-%m-%d')
        revenue_by_date[date_key] = 0
        
        # Get revenue for this date
        revenue = db.session.query(func.sum(Payment.amount)).join(Booking).filter(
            Booking.home_id.in_(home_ids),
            Payment.status == 'success',
            func.date(Payment.paid_at) == current_date.date()
        ).scalar() or 0
        
        revenue_by_date[date_key] = revenue
        current_date += timedelta(days=1)
    
    # Convert to list format
    data = []
    for date_key, amount in revenue_by_date.items():
        data.append({
            'date': date_key,
            'amount': amount
        })
    
    return data


def get_bookings_data_by_period(home_ids, start_date, end_date):
    """Get bookings data for specific period"""
    # Group by date
    bookings_by_date = {}
    current_date = start_date
    
    while current_date <= end_date:
        date_key = current_date.strftime('%Y-%m-%d')
        bookings_by_date[date_key] = 0
        
        # Get bookings for this date
        bookings_count = Booking.query.filter(
            Booking.home_id.in_(home_ids),
            func.date(Booking.created_at) == current_date.date()
        ).count()
        
        bookings_by_date[date_key] = bookings_count
        current_date += timedelta(days=1)
    
    # Convert to list format
    data = []
    for date_key, count in bookings_by_date.items():
        data.append({
            'date': date_key,
            'count': count
        })
    
    return data


def get_occupancy_data_by_period(home_ids, start_date, end_date):
    """Get occupancy data for specific period"""
    # Group by date
    occupancy_by_date = {}
    current_date = start_date
    
    while current_date <= end_date:
        date_key = current_date.strftime('%Y-%m-%d')
        occupancy_by_date[date_key] = 0
        
        # Count occupied homes for this date
        occupied_count = Booking.query.filter(
            Booking.home_id.in_(home_ids),
            Booking.payment_status == 'paid',
            Booking.start_time <= current_date,
            Booking.end_time >= current_date
        ).count()
        
        occupancy_by_date[date_key] = occupied_count
        current_date += timedelta(days=1)
    
    # Convert to list format
    data = []
    for date_key, count in occupancy_by_date.items():
        data.append({
            'date': date_key,
            'count': count
        })
    
    return data
