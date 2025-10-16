"""
Renter Reviews Routes - Review management functionality
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from sqlalchemy import func, distinct, extract
import pytz

from app.routes.decorators import renter_email_verified, renter_required
from app.routes.error_handlers import handle_api_errors, handle_web_errors, handle_validation_errors
from app.routes.constants import FLASH_MESSAGES, URLS, TIMEZONE, PAGINATION
from app.routes.base import BaseRouteHandler

# Import models
from app.models.models import db, Renter, Home, Booking, Payment, Review

renter_reviews_bp = Blueprint('renter_reviews', __name__, url_prefix='/renter')


class RenterReviewsHandler(BaseRouteHandler):
    """Handler for renter review functionality"""
    
    def __init__(self):
        super().__init__('renter_reviews')


# =============================================================================
# REVIEW MANAGEMENT ROUTES
# =============================================================================

@renter_reviews_bp.route('/reviews')
@renter_email_verified
@handle_web_errors
def reviews():
    """View all reviews by renter"""
    page = request.args.get('page', 1, type=int)
    
    # Get reviews by renter
    query = Review.query.join(Booking).filter(
        Booking.renter_id == current_user.id
    ).order_by(Review.created_at.desc())
    
    # Paginate
    pagination = query.paginate(
        page=page,
        per_page=PAGINATION['PER_PAGE'],
        error_out=False
    )
    
    return render_template('renter/reviews.html', 
                         reviews=pagination.items,
                         pagination=pagination)


@renter_reviews_bp.route('/reviews/<int:review_id>')
@renter_email_verified
@handle_web_errors
def review_detail(review_id):
    """View review details"""
    review = Review.query.get_or_404(review_id)
    
    # Check ownership
    if review.booking.renter_id != current_user.id:
        flash(FLASH_MESSAGES['UNAUTHORIZED'], 'danger')
        return redirect(url_for('renter_dashboard.dashboard'))
    
    return render_template('renter/review_detail.html', review=review)


@renter_reviews_bp.route('/reviews/edit/<int:review_id>', methods=['GET', 'POST'])
@renter_email_verified
@handle_web_errors
def edit_review(review_id):
    """Edit review"""
    review = Review.query.get_or_404(review_id)
    
    # Check ownership
    if review.booking.renter_id != current_user.id:
        flash(FLASH_MESSAGES['UNAUTHORIZED'], 'danger')
        return redirect(url_for('renter_dashboard.dashboard'))
    
    if request.method == 'POST':
        return handle_edit_review_post(review)
    
    # GET request - show edit form
    return render_template('renter/edit_review.html', review=review)


@renter_reviews_bp.route('/reviews/delete/<int:review_id>', methods=['POST'])
@renter_email_verified
@handle_api_errors
def delete_review(review_id):
    """Delete review"""
    try:
        review = Review.query.get_or_404(review_id)
        
        # Check ownership
        if review.booking.renter_id != current_user.id:
            return jsonify({"error": "Unauthorized"}), 403
        
        # Delete review
        db.session.delete(review)
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Review đã được xóa thành công"
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting review: {str(e)}")
        return jsonify({"error": "Có lỗi xảy ra khi xóa review"}), 500


# =============================================================================
# REVIEW CREATION ROUTES
# =============================================================================

@renter_reviews_bp.route('/reviews/create/<int:booking_id>', methods=['GET', 'POST'])
@renter_email_verified
@handle_web_errors
def create_review(booking_id):
    """Create review for booking"""
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
        return redirect(url_for('renter_reviews.edit_review', review_id=existing_review.id))
    
    if request.method == 'POST':
        return handle_create_review_post(booking)
    
    # GET request - show review form
    return render_template('renter/create_review.html', booking=booking)


# =============================================================================
# REVIEW ANALYTICS ROUTES
# =============================================================================

@renter_reviews_bp.route('/reviews/analytics')
@renter_email_verified
@handle_web_errors
def review_analytics():
    """Review analytics page"""
    # Get review analytics
    analytics_data = get_review_analytics()
    
    return render_template('renter/review_analytics.html', 
                         analytics=analytics_data)


# =============================================================================
# API ROUTES
# =============================================================================

@renter_reviews_bp.route('/api/reviews')
@renter_required
@handle_api_errors
def get_reviews_api():
    """Get reviews via API"""
    try:
        # Get query parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        # Build query
        query = Review.query.join(Booking).filter(
            Booking.renter_id == current_user.id
        ).order_by(Review.created_at.desc())
        
        # Paginate
        pagination = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        
        # Format review data
        reviews_data = []
        for review in pagination.items:
            reviews_data.append({
                'id': review.id,
                'home_title': review.booking.home.title,
                'home_address': review.booking.home.address,
                'rating': review.rating,
                'comment': review.comment,
                'created_at': review.created_at.isoformat(),
                'booking_id': review.booking_id
            })
        
        return jsonify({
            "success": True,
            "reviews": reviews_data,
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
        current_app.logger.error(f"Error getting reviews: {str(e)}")
        return jsonify({"error": "Failed to get reviews"}), 500


@renter_reviews_bp.route('/api/reviews/<int:review_id>')
@renter_required
@handle_api_errors
def get_review_detail_api(review_id):
    """Get review details via API"""
    try:
        review = Review.query.get_or_404(review_id)
        
        # Check ownership
        if review.booking.renter_id != current_user.id:
            return jsonify({"error": "Unauthorized"}), 403
        
        # Format review data
        review_data = {
            'id': review.id,
            'booking': {
                'id': review.booking.id,
                'home_title': review.booking.home.title,
                'home_address': review.booking.home.address,
                'start_time': review.booking.start_time.isoformat(),
                'end_time': review.booking.end_time.isoformat()
            },
            'rating': review.rating,
            'comment': review.comment,
            'created_at': review.created_at.isoformat()
        }
        
        return jsonify({
            "success": True,
            "review": review_data
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting review detail: {str(e)}")
        return jsonify({"error": "Failed to get review detail"}), 500


@renter_reviews_bp.route('/api/reviews/stats')
@renter_required
@handle_api_errors
def get_review_stats():
    """Get review statistics"""
    try:
        # Total reviews
        total_reviews = Review.query.join(Booking).filter(
            Booking.renter_id == current_user.id
        ).count()
        
        # Average rating given
        avg_rating = db.session.query(func.avg(Review.rating)).join(Booking).filter(
            Booking.renter_id == current_user.id
        ).scalar() or 0
        
        # Rating distribution
        rating_distribution = db.session.query(
            Review.rating,
            func.count(Review.id)
        ).join(Booking).filter(
            Booking.renter_id == current_user.id
        ).group_by(Review.rating).all()
        
        # Recent reviews
        recent_reviews = Review.query.join(Booking).filter(
            Booking.renter_id == current_user.id
        ).order_by(Review.created_at.desc()).limit(5).all()
        
        stats = {
            'total_reviews': total_reviews,
            'avg_rating': round(avg_rating, 2),
            'rating_distribution': [{'rating': rating, 'count': count} for rating, count in rating_distribution],
            'recent_reviews': [{
                'id': review.id,
                'home_title': review.booking.home.title,
                'rating': review.rating,
                'comment': review.comment[:100] + '...' if len(review.comment) > 100 else review.comment,
                'created_at': review.created_at.strftime('%Y-%m-%d')
            } for review in recent_reviews]
        }
        
        return jsonify({
            "success": True,
            "data": stats
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting review stats: {str(e)}")
        return jsonify({"error": "Failed to get review statistics"}), 500


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def handle_create_review_post(booking):
    """Handle review creation form submission"""
    try:
        # Get form data
        rating = request.form.get('rating', type=int)
        comment = request.form.get('comment', '').strip()
        
        # Validate rating
        if not rating or not (1 <= rating <= 5):
            flash('Vui lòng chọn đánh giá từ 1 đến 5 sao', 'danger')
            return redirect(url_for('renter_reviews.create_review', booking_id=booking.id))
        
        # Create review
        review = Review(
            booking_id=booking.id,
            rating=rating,
            comment=comment
        )
        
        db.session.add(review)
        db.session.commit()
        
        flash('Đánh giá đã được gửi thành công', 'success')
        return redirect(url_for('renter_reviews.review_detail', review_id=review.id))
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating review: {str(e)}")
        flash('Có lỗi xảy ra khi tạo đánh giá', 'danger')
        return redirect(url_for('renter_reviews.create_review', booking_id=booking.id))


def handle_edit_review_post(review):
    """Handle review edit form submission"""
    try:
        # Get form data
        rating = request.form.get('rating', type=int)
        comment = request.form.get('comment', '').strip()
        
        # Validate rating
        if not rating or not (1 <= rating <= 5):
            flash('Vui lòng chọn đánh giá từ 1 đến 5 sao', 'danger')
            return redirect(url_for('renter_reviews.edit_review', review_id=review.id))
        
        # Update review
        review.rating = rating
        review.comment = comment
        review.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        flash('Đánh giá đã được cập nhật thành công', 'success')
        return redirect(url_for('renter_reviews.review_detail', review_id=review.id))
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating review: {str(e)}")
        flash('Có lỗi xảy ra khi cập nhật đánh giá', 'danger')
        return redirect(url_for('renter_reviews.edit_review', review_id=review.id))


def get_review_analytics():
    """Get review analytics data"""
    # Monthly reviews
    monthly_reviews = []
    for i in range(12):
        month_start = datetime.utcnow() - timedelta(days=30 * (i + 1))
        month_end = datetime.utcnow() - timedelta(days=30 * i)
        
        reviews_count = Review.query.join(Booking).filter(
            Booking.renter_id == current_user.id,
            Review.created_at >= month_start,
            Review.created_at < month_end
        ).count()
        
        monthly_reviews.append({
            'month': month_start.strftime('%Y-%m'),
            'count': reviews_count
        })
    
    # Rating distribution
    rating_distribution = db.session.query(
        Review.rating,
        func.count(Review.id)
    ).join(Booking).filter(
        Booking.renter_id == current_user.id
    ).group_by(Review.rating).all()
    
    # Average rating over time
    avg_rating_by_month = []
    for i in range(6):  # Last 6 months
        month_start = datetime.utcnow() - timedelta(days=30 * (i + 1))
        month_end = datetime.utcnow() - timedelta(days=30 * i)
        
        avg_rating = db.session.query(func.avg(Review.rating)).join(Booking).filter(
            Booking.renter_id == current_user.id,
            Review.created_at >= month_start,
            Review.created_at < month_end
        ).scalar() or 0
        
        avg_rating_by_month.append({
            'month': month_start.strftime('%Y-%m'),
            'avg_rating': round(avg_rating, 2) if avg_rating else 0
        })
    
    return {
        'monthly_reviews': list(reversed(monthly_reviews)),
        'rating_distribution': [{'rating': rating, 'count': count} for rating, count in rating_distribution],
        'avg_rating_by_month': list(reversed(avg_rating_by_month))
    }


def get_review_summary(reviews):
    """Get review summary statistics"""
    total_reviews = len(reviews)
    avg_rating = sum(review.rating for review in reviews) / total_reviews if total_reviews > 0 else 0
    
    # Rating distribution
    rating_distribution = {}
    for i in range(1, 6):
        rating_distribution[i] = len([r for r in reviews if r.rating == i])
    
    return {
        'total_reviews': total_reviews,
        'avg_rating': round(avg_rating, 2),
        'rating_distribution': rating_distribution
    }


def can_edit_review(review):
    """Check if review can be edited"""
    # Allow editing within 24 hours of creation
    hours_since_creation = (datetime.utcnow() - review.created_at).total_seconds() / 3600
    return hours_since_creation < 24


def get_review_trends():
    """Get review trends for analytics"""
    # Get reviews for last 12 months
    reviews = Review.query.join(Booking).filter(
        Booking.renter_id == current_user.id,
        Review.created_at >= datetime.utcnow() - timedelta(days=365)
    ).all()
    
    # Group by month
    monthly_data = {}
    for review in reviews:
        month_key = review.created_at.strftime('%Y-%m')
        if month_key not in monthly_data:
            monthly_data[month_key] = {'count': 0, 'total_rating': 0}
        
        monthly_data[month_key]['count'] += 1
        monthly_data[month_key]['total_rating'] += review.rating
    
    # Calculate averages
    trends = []
    for month, data in monthly_data.items():
        avg_rating = data['total_rating'] / data['count'] if data['count'] > 0 else 0
        trends.append({
            'month': month,
            'count': data['count'],
            'avg_rating': round(avg_rating, 2)
        })
    
    return sorted(trends, key=lambda x: x['month'])
