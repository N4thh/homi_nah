"""
Admin Homes Routes - Home management and monitoring functionality
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from sqlalchemy import func, distinct, extract
import pytz

from app.routes.decorators import admin_required, super_admin_required
from app.routes.error_handlers import handle_api_errors, handle_web_errors, handle_validation_errors
from app.routes.constants import FLASH_MESSAGES, URLS, TIMEZONE, PAGINATION, PROPERTY_TYPES
from app.routes.base import BaseRouteHandler

# Import models
from app.models.models import db, Admin, Owner, Renter, Home, Booking, Payment, Review, HomeImage

admin_homes_bp = Blueprint('admin_homes', __name__, url_prefix='/admin')


class AdminHomesHandler(BaseRouteHandler):
    """Handler for admin home management functionality"""
    
    def __init__(self):
        super().__init__('admin_homes')


# =============================================================================
# HOME MANAGEMENT ROUTES
# =============================================================================

@admin_homes_bp.route('/homes')
@admin_required
@handle_web_errors
def homes():
    """Home management page"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    property_type = request.args.get('type', '')
    status = request.args.get('status', '')
    
    query = Home.query
    
    # Apply filters
    if search:
        query = query.filter(
            Home.title.contains(search) | 
            Home.address.contains(search) |
            Home.description.contains(search)
        )
    
    if property_type and property_type in PROPERTY_TYPES:
        query = query.filter(Home.property_type == property_type)
    
    if status == 'active':
        query = query.filter(Home.is_active == True)
    elif status == 'inactive':
        query = query.filter(Home.is_active == False)
    
    # Paginate
    pagination = query.paginate(
        page=page,
        per_page=PAGINATION['PER_PAGE'],
        error_out=False
    )
    
    # Get home statistics
    home_stats = get_home_statistics()
    
    return render_template('admin/homes.html', 
                         homes=pagination.items,
                         pagination=pagination,
                         search=search,
                         property_type=property_type,
                         status=status,
                         stats=home_stats)


@admin_homes_bp.route('/homes/<int:home_id>')
@admin_required
@handle_web_errors
def home_detail(home_id):
    """View home details"""
    home = Home.query.get_or_404(home_id)
    
    # Get home's bookings
    bookings = Booking.query.filter_by(home_id=home_id).order_by(Booking.created_at.desc()).limit(10).all()
    
    # Get home's payments
    payments = Payment.query.join(Booking).filter(
        Booking.home_id == home_id
    ).order_by(Payment.created_at.desc()).limit(10).all()
    
    # Get home's reviews
    reviews = Review.query.join(Booking).filter(
        Booking.home_id == home_id
    ).order_by(Review.created_at.desc()).limit(10).all()
    
    # Get home's images
    images = HomeImage.query.filter_by(home_id=home_id).all()
    
    return render_template('admin/home_detail.html', 
                         home=home,
                         bookings=bookings,
                         payments=payments,
                         reviews=reviews,
                         images=images)


@admin_homes_bp.route('/homes/toggle-status/<int:home_id>', methods=['POST'])
@admin_required
@handle_api_errors
def toggle_home_status(home_id):
    """Toggle home active status"""
    try:
        home = Home.query.get_or_404(home_id)
        
        # Toggle status
        home.is_active = not home.is_active
        db.session.commit()
        
        status = "activated" if home.is_active else "deactivated"
        return jsonify({
            "success": True,
            "message": f"Home {status} successfully",
            "is_active": home.is_active
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error toggling home status: {str(e)}")
        return jsonify({"error": "Failed to toggle home status"}), 500


@admin_homes_bp.route('/homes/delete/<int:home_id>', methods=['POST'])
@admin_required
@handle_api_errors
def delete_home(home_id):
    """Delete home"""
    try:
        home = Home.query.get_or_404(home_id)
        
        # Check if home has bookings
        bookings_count = Booking.query.filter_by(home_id=home_id).count()
        if bookings_count > 0:
            return jsonify({"error": "Cannot delete home with existing bookings"}), 400
        
        # Delete home images
        for image in home.images:
            db.session.delete(image)
        
        # Delete home
        db.session.delete(home)
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Home deleted successfully"
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting home: {str(e)}")
        return jsonify({"error": "Failed to delete home"}), 500


# =============================================================================
# HOME ANALYTICS ROUTES
# =============================================================================

@admin_homes_bp.route('/homes/analytics')
@admin_required
@handle_web_errors
def home_analytics():
    """Home analytics page"""
    # Get analytics data
    analytics_data = get_home_analytics()
    
    return render_template('admin/home_analytics.html', 
                         analytics=analytics_data)


@admin_homes_bp.route('/homes/analytics/<int:home_id>')
@admin_required
@handle_web_errors
def home_analytics_detail(home_id):
    """Individual home analytics"""
    home = Home.query.get_or_404(home_id)
    
    # Get home-specific analytics
    analytics_data = get_home_analytics_detail(home_id)
    
    return render_template('admin/home_analytics_detail.html', 
                         home=home,
                         analytics=analytics_data)


# =============================================================================
# API ROUTES
# =============================================================================

@admin_homes_bp.route('/api/homes/stats')
@admin_required
@handle_api_errors
def get_home_stats():
    """Get home statistics"""
    try:
        # Total homes
        total_homes = Home.query.count()
        active_homes = Home.query.filter_by(is_active=True).count()
        inactive_homes = total_homes - active_homes
        
        # Homes by property type
        homes_by_type = db.session.query(
            Home.property_type,
            func.count(Home.id)
        ).group_by(Home.property_type).all()
        
        # New homes this month
        month_start = datetime.utcnow().replace(day=1)
        new_homes = Home.query.filter(Home.created_at >= month_start).count()
        
        # Homes with bookings
        homes_with_bookings = db.session.query(func.count(func.distinct(Booking.home_id))).scalar()
        
        # Average price
        avg_price = db.session.query(func.avg(Home.price)).scalar() or 0
        
        stats = {
            'total_homes': total_homes,
            'active_homes': active_homes,
            'inactive_homes': inactive_homes,
            'new_homes': new_homes,
            'homes_with_bookings': homes_with_bookings,
            'avg_price': round(avg_price, 2),
            'homes_by_type': [{'type': prop_type, 'count': count} for prop_type, count in homes_by_type]
        }
        
        return jsonify({
            "success": True,
            "data": stats
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting home stats: {str(e)}")
        return jsonify({"error": "Failed to get home statistics"}), 500


@admin_homes_bp.route('/api/homes/search')
@admin_required
@handle_api_errors
def search_homes():
    """Search homes"""
    try:
        query = request.args.get('q', '')
        limit = request.args.get('limit', 10, type=int)
        
        if not query:
            return jsonify({"success": True, "homes": []})
        
        homes = Home.query.filter(
            Home.title.contains(query) | 
            Home.address.contains(query) |
            Home.description.contains(query)
        ).limit(limit).all()
        
        homes_data = []
        for home in homes:
            homes_data.append({
                'id': home.id,
                'title': home.title,
                'address': home.address,
                'price': home.price,
                'property_type': home.property_type,
                'is_active': home.is_active,
                'owner_name': home.owner.full_name if home.owner else 'Unknown'
            })
        
        return jsonify({
            "success": True,
            "homes": homes_data
        })
        
    except Exception as e:
        current_app.logger.error(f"Error searching homes: {str(e)}")
        return jsonify({"error": "Failed to search homes"}), 500


@admin_homes_bp.route('/api/homes/analytics/<int:home_id>')
@admin_required
@handle_api_errors
def get_home_analytics_api(home_id):
    """Get home analytics data"""
    try:
        home = Home.query.get_or_404(home_id)
        
        # Get analytics data
        analytics_data = get_home_analytics_detail(home_id)
        
        return jsonify({
            "success": True,
            "data": analytics_data
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting home analytics: {str(e)}")
        return jsonify({"error": "Failed to get home analytics"}), 500


@admin_homes_bp.route('/api/homes/performance')
@admin_required
@handle_api_errors
def get_home_performance():
    """Get home performance data"""
    try:
        # Get top performing homes
        top_homes = db.session.query(
            Home.id,
            Home.title,
            Home.price,
            func.count(Booking.id).label('booking_count'),
            func.sum(Payment.amount).label('total_revenue')
        ).join(Booking, isouter=True).join(Payment, isouter=True).filter(
            Payment.status == 'success'
        ).group_by(Home.id, Home.title, Home.price).order_by(
            func.sum(Payment.amount).desc()
        ).limit(10).all()
        
        performance_data = []
        for home in top_homes:
            performance_data.append({
                'id': home.id,
                'title': home.title,
                'price': home.price,
                'booking_count': home.booking_count or 0,
                'total_revenue': home.total_revenue or 0
            })
        
        return jsonify({
            "success": True,
            "data": performance_data
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting home performance: {str(e)}")
        return jsonify({"error": "Failed to get home performance"}), 500


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_home_statistics():
    """Get comprehensive home statistics"""
    # Basic counts
    total_homes = Home.query.count()
    active_homes = Home.query.filter_by(is_active=True).count()
    inactive_homes = total_homes - active_homes
    
    # Homes by property type
    homes_by_type = db.session.query(
        Home.property_type,
        func.count(Home.id)
    ).group_by(Home.property_type).all()
    
    # Price statistics
    price_stats = db.session.query(
        func.min(Home.price).label('min_price'),
        func.max(Home.price).label('max_price'),
        func.avg(Home.price).label('avg_price')
    ).first()
    
    # Homes with bookings
    homes_with_bookings = db.session.query(func.count(func.distinct(Booking.home_id))).scalar()
    
    # New homes this month
    month_start = datetime.utcnow().replace(day=1)
    new_homes = Home.query.filter(Home.created_at >= month_start).count()
    
    return {
        'total_homes': total_homes,
        'active_homes': active_homes,
        'inactive_homes': inactive_homes,
        'new_homes': new_homes,
        'homes_with_bookings': homes_with_bookings,
        'homes_by_type': [{'type': prop_type, 'count': count} for prop_type, count in homes_by_type],
        'price_stats': {
            'min_price': price_stats.min_price or 0,
            'max_price': price_stats.max_price or 0,
            'avg_price': round(price_stats.avg_price or 0, 2)
        }
    }


def get_home_analytics():
    """Get overall home analytics"""
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
    
    # Price range distribution
    price_ranges = [
        (0, 500000, 'Under 500K'),
        (500000, 1000000, '500K - 1M'),
        (1000000, 2000000, '1M - 2M'),
        (2000000, 5000000, '2M - 5M'),
        (5000000, float('inf'), 'Over 5M')
    ]
    
    price_distribution = []
    for min_price, max_price, label in price_ranges:
        if max_price == float('inf'):
            count = Home.query.filter(Home.price >= min_price).count()
        else:
            count = Home.query.filter(
                Home.price >= min_price,
                Home.price < max_price
            ).count()
        
        price_distribution.append({
            'range': label,
            'count': count
        })
    
    return {
        'monthly_homes': list(reversed(monthly_homes)),
        'property_distribution': [{'type': prop_type, 'count': count} for prop_type, count in property_distribution],
        'price_distribution': price_distribution
    }


def get_home_analytics_detail(home_id):
    """Get detailed analytics for a specific home"""
    home = Home.query.get_or_404(home_id)
    
    # Booking statistics
    total_bookings = Booking.query.filter_by(home_id=home_id).count()
    
    # Revenue statistics
    total_revenue = db.session.query(func.sum(Payment.amount)).join(Booking).filter(
        Booking.home_id == home_id,
        Payment.status == 'success'
    ).scalar() or 0
    
    # Average booking duration
    avg_duration = db.session.query(func.avg(
        func.extract('day', Booking.end_time - Booking.start_time)
    )).filter(Booking.home_id == home_id).scalar() or 0
    
    # Occupancy rate (last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    occupied_nights = db.session.query(func.sum(
        func.extract('day', Booking.end_time - Booking.start_time)
    )).filter(
        Booking.home_id == home_id,
        Booking.payment_status == 'paid',
        Booking.start_time >= thirty_days_ago
    ).scalar() or 0
    
    occupancy_rate = (occupied_nights / 30) * 100 if occupied_nights > 0 else 0
    
    # Recent bookings
    recent_bookings = Booking.query.filter_by(home_id=home_id).order_by(
        Booking.created_at.desc()
    ).limit(5).all()
    
    # Recent reviews
    recent_reviews = Review.query.join(Booking).filter(
        Booking.home_id == home_id
    ).order_by(Review.created_at.desc()).limit(5).all()
    
    return {
        'home': {
            'id': home.id,
            'title': home.title,
            'address': home.address,
            'price': home.price,
            'property_type': home.property_type,
            'is_active': home.is_active
        },
        'statistics': {
            'total_bookings': total_bookings,
            'total_revenue': total_revenue,
            'avg_duration': round(avg_duration, 2),
            'occupancy_rate': round(occupancy_rate, 2)
        },
        'recent_bookings': [{
            'id': booking.id,
            'renter_name': booking.renter.full_name if booking.renter else 'Unknown',
            'start_time': booking.start_time.strftime('%Y-%m-%d'),
            'end_time': booking.end_time.strftime('%Y-%m-%d'),
            'status': booking.status,
            'total_amount': booking.total_amount
        } for booking in recent_bookings],
        'recent_reviews': [{
            'id': review.id,
            'renter_name': review.booking.renter.full_name if review.booking and review.booking.renter else 'Unknown',
            'rating': review.rating,
            'comment': review.comment,
            'created_at': review.created_at.strftime('%Y-%m-%d')
        } for review in recent_reviews]
    }
