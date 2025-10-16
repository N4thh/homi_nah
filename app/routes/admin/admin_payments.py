"""
Admin Payments Routes - Payment management and monitoring functionality
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from sqlalchemy import func, distinct, extract
import pytz

from app.routes.decorators import admin_required, super_admin_required
from app.routes.error_handlers import handle_api_errors, handle_web_errors, handle_validation_errors
from app.routes.constants import FLASH_MESSAGES, URLS, TIMEZONE, PAGINATION, PAYMENT_STATUS
from app.routes.base import BaseRouteHandler

# Import models
from app.models.models import db, Admin, Owner, Renter, Home, Booking, Payment

admin_payments_bp = Blueprint('admin_payments', __name__, url_prefix='/admin')


class AdminPaymentsHandler(BaseRouteHandler):
    """Handler for admin payment management functionality"""
    
    def __init__(self):
        super().__init__('admin_payments')


# =============================================================================
# PAYMENT MANAGEMENT ROUTES
# =============================================================================

@admin_payments_bp.route('/payments')
@admin_required
@handle_web_errors
def payments():
    """Payment management page"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    status = request.args.get('status', '')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    
    query = Payment.query
    
    # Apply filters
    if search:
        query = query.filter(
            Payment.payment_code.contains(search) |
            Payment.customer_name.contains(search) |
            Payment.customer_email.contains(search)
        )
    
    if status and status in PAYMENT_STATUS:
        query = query.filter(Payment.status == status)
    
    if start_date:
        try:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(Payment.created_at >= start_date_obj)
        except ValueError:
            pass
    
    if end_date:
        try:
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
            query = query.filter(Payment.created_at <= end_date_obj)
        except ValueError:
            pass
    
    # Paginate
    pagination = query.paginate(
        page=page,
        per_page=PAGINATION['PER_PAGE'],
        error_out=False
    )
    
    # Get payment statistics
    payment_stats = get_payment_statistics()
    
    return render_template('admin/payments.html', 
                         payments=pagination.items,
                         pagination=pagination,
                         search=search,
                         status=status,
                         start_date=start_date,
                         end_date=end_date,
                         stats=payment_stats)


@admin_payments_bp.route('/payments/<int:payment_id>')
@admin_required
@handle_web_errors
def payment_detail(payment_id):
    """View payment details"""
    payment = Payment.query.get_or_404(payment_id)
    
    return render_template('admin/payment_detail.html', payment=payment)


@admin_payments_bp.route('/payments/refund/<int:payment_id>', methods=['POST'])
@admin_required
@handle_api_errors
def refund_payment(payment_id):
    """Refund payment"""
    try:
        payment = Payment.query.get_or_404(payment_id)
        
        # Check if payment can be refunded
        if payment.status != 'success':
            return jsonify({"error": "Only successful payments can be refunded"}), 400
        
        # Update payment status
        payment.status = 'refunded'
        payment.refunded_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Payment refunded successfully"
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error refunding payment: {str(e)}")
        return jsonify({"error": "Failed to refund payment"}), 500


# =============================================================================
# PAYMENT ANALYTICS ROUTES
# =============================================================================

@admin_payments_bp.route('/payments/analytics')
@admin_required
@handle_web_errors
def payment_analytics():
    """Payment analytics page"""
    # Get analytics data
    analytics_data = get_payment_analytics()
    
    return render_template('admin/payment_analytics.html', 
                         analytics=analytics_data)


@admin_payments_bp.route('/payments/reports')
@admin_required
@handle_web_errors
def payment_reports():
    """Payment reports page"""
    # Get report data
    report_data = get_payment_reports()
    
    return render_template('admin/payment_reports.html', 
                         reports=report_data)


# =============================================================================
# API ROUTES
# =============================================================================

@admin_payments_bp.route('/api/payments/stats')
@admin_required
@handle_api_errors
def get_payment_stats():
    """Get payment statistics"""
    try:
        # Total payments
        total_payments = Payment.query.count()
        
        # Payments by status
        payments_by_status = db.session.query(
            Payment.status,
            func.count(Payment.id)
        ).group_by(Payment.status).all()
        
        # Total revenue
        total_revenue = db.session.query(func.sum(Payment.amount)).filter(
            Payment.status == 'success'
        ).scalar() or 0
        
        # Monthly revenue
        month_start = datetime.utcnow().replace(day=1)
        monthly_revenue = db.session.query(func.sum(Payment.amount)).filter(
            Payment.status == 'success',
            Payment.paid_at >= month_start
        ).scalar() or 0
        
        # Average payment amount
        avg_payment = db.session.query(func.avg(Payment.amount)).filter(
            Payment.status == 'success'
        ).scalar() or 0
        
        # Success rate
        success_count = db.session.query(func.count(Payment.id)).filter(
            Payment.status == 'success'
        ).scalar()
        success_rate = (success_count / total_payments * 100) if total_payments > 0 else 0
        
        stats = {
            'total_payments': total_payments,
            'total_revenue': total_revenue,
            'monthly_revenue': monthly_revenue,
            'avg_payment': round(avg_payment, 2),
            'success_rate': round(success_rate, 2),
            'payments_by_status': [{'status': status, 'count': count} for status, count in payments_by_status]
        }
        
        return jsonify({
            "success": True,
            "data": stats
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting payment stats: {str(e)}")
        return jsonify({"error": "Failed to get payment statistics"}), 500


@admin_payments_bp.route('/api/payments/revenue/<period>')
@admin_required
@handle_api_errors
def get_revenue_data(period):
    """Get revenue data for specific period"""
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
        current_app.logger.error(f"Error getting revenue data: {str(e)}")
        return jsonify({"error": "Failed to get revenue data"}), 500


@admin_payments_bp.route('/api/payments/search')
@admin_required
@handle_api_errors
def search_payments():
    """Search payments"""
    try:
        query = request.args.get('q', '')
        limit = request.args.get('limit', 10, type=int)
        
        if not query:
            return jsonify({"success": True, "payments": []})
        
        payments = Payment.query.filter(
            Payment.payment_code.contains(query) |
            Payment.customer_name.contains(query) |
            Payment.customer_email.contains(query)
        ).limit(limit).all()
        
        payments_data = []
        for payment in payments:
            payments_data.append({
                'id': payment.id,
                'payment_code': payment.payment_code,
                'customer_name': payment.customer_name,
                'amount': payment.amount,
                'status': payment.status,
                'created_at': payment.created_at.strftime('%Y-%m-%d %H:%M')
            })
        
        return jsonify({
            "success": True,
            "payments": payments_data
        })
        
    except Exception as e:
        current_app.logger.error(f"Error searching payments: {str(e)}")
        return jsonify({"error": "Failed to search payments"}), 500


@admin_payments_bp.route('/api/payments/export')
@admin_required
@handle_api_errors
def export_payments():
    """Export payments data"""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        status = request.args.get('status', '')
        
        query = Payment.query
        
        # Apply filters
        if start_date:
            try:
                start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
                query = query.filter(Payment.created_at >= start_date_obj)
            except ValueError:
                pass
        
        if end_date:
            try:
                end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
                query = query.filter(Payment.created_at <= end_date_obj)
            except ValueError:
                pass
        
        if status and status in PAYMENT_STATUS:
            query = query.filter(Payment.status == status)
        
        # Get payments
        payments = query.order_by(Payment.created_at.desc()).all()
        
        # Format data for export
        export_data = []
        for payment in payments:
            export_data.append({
                'id': payment.id,
                'payment_code': payment.payment_code,
                'order_code': payment.order_code,
                'customer_name': payment.customer_name,
                'customer_email': payment.customer_email,
                'customer_phone': payment.customer_phone,
                'amount': payment.amount,
                'status': payment.status,
                'created_at': payment.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'paid_at': payment.paid_at.strftime('%Y-%m-%d %H:%M:%S') if payment.paid_at else None,
                'booking_id': payment.booking_id,
                'home_title': payment.booking.home.title if payment.booking else 'N/A',
                'owner_name': payment.booking.home.owner.full_name if payment.booking and payment.booking.home and payment.booking.home.owner else 'N/A'
            })
        
        return jsonify({
            "success": True,
            "data": export_data,
            "count": len(export_data)
        })
        
    except Exception as e:
        current_app.logger.error(f"Error exporting payments: {str(e)}")
        return jsonify({"error": "Failed to export payments"}), 500


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_payment_statistics():
    """Get comprehensive payment statistics"""
    # Basic counts
    total_payments = Payment.query.count()
    
    # Payments by status
    payments_by_status = db.session.query(
        Payment.status,
        func.count(Payment.id)
    ).group_by(Payment.status).all()
    
    # Revenue statistics
    total_revenue = db.session.query(func.sum(Payment.amount)).filter(
        Payment.status == 'success'
    ).scalar() or 0
    
    # Monthly revenue
    month_start = datetime.utcnow().replace(day=1)
    monthly_revenue = db.session.query(func.sum(Payment.amount)).filter(
        Payment.status == 'success',
        Payment.paid_at >= month_start
    ).scalar() or 0
    
    # Average payment amount
    avg_payment = db.session.query(func.avg(Payment.amount)).filter(
        Payment.status == 'success'
    ).scalar() or 0
    
    # Success rate
    success_count = db.session.query(func.count(Payment.id)).filter(
        Payment.status == 'success'
    ).scalar()
    success_rate = (success_count / total_payments * 100) if total_payments > 0 else 0
    
    # Recent payments
    recent_payments = Payment.query.order_by(Payment.created_at.desc()).limit(5).all()
    
    return {
        'total_payments': total_payments,
        'total_revenue': total_revenue,
        'monthly_revenue': monthly_revenue,
        'avg_payment': round(avg_payment, 2),
        'success_rate': round(success_rate, 2),
        'payments_by_status': [{'status': status, 'count': count} for status, count in payments_by_status],
        'recent_payments': [{
            'id': payment.id,
            'payment_code': payment.payment_code,
            'customer_name': payment.customer_name,
            'amount': payment.amount,
            'status': payment.status,
            'created_at': payment.created_at.strftime('%Y-%m-%d %H:%M')
        } for payment in recent_payments]
    }


def get_payment_analytics():
    """Get payment analytics data"""
    # Monthly revenue for last 12 months
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
    
    # Payment status distribution
    status_distribution = db.session.query(
        Payment.status,
        func.count(Payment.id)
    ).group_by(Payment.status).all()
    
    # Payment method distribution (if available)
    method_distribution = db.session.query(
        Payment.payment_method,
        func.count(Payment.id)
    ).group_by(Payment.payment_method).all()
    
    # Top paying customers
    top_customers = db.session.query(
        Payment.customer_name,
        Payment.customer_email,
        func.count(Payment.id).label('payment_count'),
        func.sum(Payment.amount).label('total_amount')
    ).filter(
        Payment.status == 'success'
    ).group_by(
        Payment.customer_name,
        Payment.customer_email
    ).order_by(
        func.sum(Payment.amount).desc()
    ).limit(10).all()
    
    return {
        'monthly_revenue': list(reversed(monthly_revenue)),
        'status_distribution': [{'status': status, 'count': count} for status, count in status_distribution],
        'method_distribution': [{'method': method, 'count': count} for method, count in method_distribution],
        'top_customers': [{
            'name': customer.customer_name,
            'email': customer.customer_email,
            'payment_count': customer.payment_count,
            'total_amount': customer.total_amount
        } for customer in top_customers]
    }


def get_payment_reports():
    """Get payment reports data"""
    # Daily revenue for last 30 days
    daily_revenue = []
    for i in range(30):
        day_start = datetime.utcnow() - timedelta(days=i + 1)
        day_end = datetime.utcnow() - timedelta(days=i)
        
        revenue = db.session.query(func.sum(Payment.amount)).filter(
            Payment.status == 'success',
            Payment.paid_at >= day_start,
            Payment.paid_at < day_end
        ).scalar() or 0
        
        daily_revenue.append({
            'date': day_start.strftime('%Y-%m-%d'),
            'revenue': revenue
        })
    
    # Payment trends
    payment_trends = db.session.query(
        func.date(Payment.created_at).label('date'),
        func.count(Payment.id).label('count'),
        func.sum(Payment.amount).label('amount')
    ).filter(
        Payment.created_at >= datetime.utcnow() - timedelta(days=30)
    ).group_by(
        func.date(Payment.created_at)
    ).order_by(
        func.date(Payment.created_at)
    ).all()
    
    return {
        'daily_revenue': list(reversed(daily_revenue)),
        'payment_trends': [{
            'date': trend.date.strftime('%Y-%m-%d'),
            'count': trend.count,
            'amount': trend.amount or 0
        } for trend in payment_trends]
    }


def get_revenue_data_by_period(start_date, end_date):
    """Get revenue data for specific period"""
    # Group by date
    revenue_by_date = {}
    current_date = start_date
    
    while current_date <= end_date:
        date_key = current_date.strftime('%Y-%m-%d')
        revenue_by_date[date_key] = 0
        
        # Get revenue for this date
        revenue = db.session.query(func.sum(Payment.amount)).filter(
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
