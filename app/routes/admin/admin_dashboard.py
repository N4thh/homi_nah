"""
Admin Dashboard Routes - Admin dashboard and overview functionality
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
from app.utils.cache import cache

# Import models
from app.models.models import db, Admin, Owner, Renter, Home, Booking, Statistics, Review, Payment

admin_dashboard_bp = Blueprint('admin_dashboard', __name__, url_prefix='/admin')


class AdminDashboardHandler(BaseRouteHandler):
    """Handler for admin dashboard functionality"""
    
    def __init__(self):
        super().__init__('admin_dashboard')


# =============================================================================
# DASHBOARD ROUTES
# =============================================================================

@admin_dashboard_bp.route('/dashboard')
@admin_required
@handle_web_errors
def dashboard():
    """Admin dashboard with statistics"""
    try:
        # Get basic statistics with caching
        stats_data = get_dashboard_statistics()
        
        # Format stats for template
        stats = {
            'total_homes': stats_data['total_homes'],
            'total_bookings': stats_data['total_bookings'],
            'active_users': stats_data['active_users'],
            'total_revenue': stats_data['total_revenue'],
            'total_owners': 0,  # Will be updated below
            'total_renters': 0  # Will be updated below
        }
        
        # Get recent activities with caching
        recent_activities = get_recent_activities()
        
        # Get chart data with caching
        chart_data = get_chart_data()
        
        # Get weekly statistics with caching
        weekly_stats = get_weekly_stats()
        
        # Get users data for customer management with optimized query
        page = request.args.get('page', 1, type=int)
        role_filter = request.args.get('role', 'all')
        status_filter = request.args.get('status', 'all')
        search_query = request.args.get('search', '')
        
        # Get users based on filters with optimized query
        users_query = None
        if role_filter == 'owner':
            users_query = Owner.query
        elif role_filter == 'renter':
            users_query = Renter.query
        else:
            # For 'all', we'll need to combine both - this is complex
            # For now, let's just get owners
            users_query = Owner.query
        
        if status_filter == 'active':
            users_query = users_query.filter_by(is_active=True)
        elif status_filter == 'inactive':
            users_query = users_query.filter_by(is_active=False)
        
        if search_query:
            users_query = users_query.filter(
                db.or_(
                    Owner.username.contains(search_query),
                    Owner.email.contains(search_query),
                    Owner.full_name.contains(search_query)
                )
            )
        
        # Optimize query with pagination and limit fields
        users = users_query.with_entities(
            Owner.id, Owner.username, Owner.email, Owner.full_name, 
            Owner.is_active, Owner.created_at
        ).paginate(
            page=page, per_page=10, error_out=False
        )
        
        # Get additional data needed for template
        total_users = Owner.query.count() + Renter.query.count() + Admin.query.count()
        total_homes = Home.query.count()
        total_bookings = Booking.query.count()
        total_revenue = db.session.query(func.sum(Booking.total_price)).scalar() or 0
        
        # User counts by type
        owner_count = Owner.query.count()
        renter_count = Renter.query.count()
        admin_count = Admin.query.count()
        
        # Update stats with actual counts
        stats['total_owners'] = owner_count
        stats['total_renters'] = renter_count
        
        # Popular homes
        popular_homes = Home.query.options(
            db.joinedload(Home.images)
        ).filter_by(is_active=True).limit(5).all()
        
        return render_template('admin/dashboard.html', 
                             stats=stats, 
                             recent_activities=recent_activities,
                             chart_data=chart_data,
                             weekly_stats=weekly_stats,
                             users=users,
                             current_role_filter=role_filter,
                             current_filter=status_filter,
                             search_query=search_query,
                             total_users=total_users,
                             total_homes=total_homes,
                             total_bookings=total_bookings,
                             total_revenue=total_revenue,
                             owner_count=owner_count,
                             renter_count=renter_count,
                             admin_count=admin_count,
                             popular_homes=popular_homes)
    except Exception as e:
        current_app.logger.error(f"Error in dashboard route: {str(e)}")
        flash('Có lỗi xảy ra khi tải dashboard', 'error')
        return render_template('admin/dashboard.html', 
                             stats=[], 
                             recent_activities=[],
                             chart_data={},
                             weekly_stats={},
                             users=None,
                             current_role_filter='all',
                             current_filter='all',
                             search_query='',
                             total_users=0,
                             total_homes=0,
                             total_bookings=0,
                             total_revenue=0,
                             owner_count=0,
                             renter_count=0,
                             admin_count=0,
                             popular_homes=[])


@admin_dashboard_bp.route('/navbar-test')
def navbar_test():
    """Test navbar with logout button"""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Navbar Test</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css" rel="stylesheet">
    </head>
    <body>
        <nav class="navbar navbar-expand-lg navbar-light bg-white shadow-sm fixed-top">
            <div class="container-fluid">
                <span class="navbar-brand fw-bold d-flex align-items-center">
                    <span class="brand-text" style="font-size: 24px">Homi Admin</span>
                </span>
                
                <div class="navbar-nav ms-auto d-flex flex-row align-items-center">
                    <div class="nav-item d-flex align-items-center me-3">
                        <img src="https://via.placeholder.com/32" alt="Avatar" class="rounded-circle me-2" style="width: 32px; height: 32px;">
                        <span class="text-dark fw-bold">admin</span>
                    </div>
                    
                    <div class="nav-item">
                        <a class="btn btn-outline-danger btn-sm" href="{url_for('auth.logout_simple')}" style="border-radius: 20px; padding: 6px 16px;">
                            <i class="fas fa-sign-out-alt me-1"></i>
                            Đăng xuất
                        </a>
                    </div>
                </div>
            </div>
        </nav>
        
        <div style="margin-top: 100px; padding: 20px;">
            <h1>Navbar Test</h1>
            <p>Click vào button "Đăng xuất" ở góc phải navbar để test logout.</p>
            <p>Current user: {current_user}</p>
        </div>
        
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    </body>
    </html>
    """

@admin_dashboard_bp.route('/public-template-test')
def public_template_test():
    """Public template test route - no authentication required"""
    return render_template('pages/simple_test.html')

@admin_dashboard_bp.route('/public-admin-template-test')
def public_admin_template_test():
    """Public admin template test route - no authentication required"""
    return render_template('pages/test_dashboard.html')

@admin_dashboard_bp.route('/public-dashboard-test')
def public_dashboard_test():
    """Public dashboard test route - no authentication required"""
    return render_template('pages/admin_dashboard.html', 
                         stats=[], 
                         recent_activities=[],
                         chart_data={},
                         weekly_stats={},
                         users=None,
                         current_role_filter='all',
                         current_filter='all',
                         search_query='',
                         total_users=0,
                         total_homes=0,
                         total_bookings=0,
                         total_revenue=0,
                         owner_count=0,
                         renter_count=0,
                         admin_count=0,
                         popular_homes=[])

@admin_dashboard_bp.route('/public-dashboard-real-data')
def public_dashboard_real_data():
    """Public dashboard test route with real data - no authentication required"""
    try:
        # Get basic statistics with caching
        stats_data = get_dashboard_statistics()
        
        # Format stats for template
        stats = {
            'total_homes': stats_data['total_homes'],
            'total_bookings': stats_data['total_bookings'],
            'active_users': stats_data['active_users'],
            'total_revenue': stats_data['total_revenue'],
            'total_owners': 0,  # Will be updated below
            'total_renters': 0  # Will be updated below
        }
        
        # Get recent activities with caching
        recent_activities = get_recent_activities()
        
        # Get chart data with caching
        chart_data = get_chart_data()
        
        # Get weekly statistics with caching
        weekly_stats = get_weekly_stats()
        
        # Get additional data needed for template
        total_users = Owner.query.count() + Renter.query.count() + Admin.query.count()
        total_homes = Home.query.count()
        total_bookings = Booking.query.count()
        total_revenue = db.session.query(func.sum(Booking.total_price)).scalar() or 0
        
        # User counts by type
        owner_count = Owner.query.count()
        renter_count = Renter.query.count()
        admin_count = Admin.query.count()
        
        # Update stats with actual counts
        stats['total_owners'] = owner_count
        stats['total_renters'] = renter_count
        
        # Popular homes
        popular_homes = Home.query.options(
            db.joinedload(Home.images)
        ).filter_by(is_active=True).limit(5).all()
        
        return render_template('pages/admin_dashboard.html', 
                             stats=stats, 
                             recent_activities=recent_activities,
                             chart_data=chart_data,
                             weekly_stats=weekly_stats,
                             users=None,
                             current_role_filter='all',
                             current_filter='all',
                             search_query='',
                             total_users=total_users,
                             total_homes=total_homes,
                             total_bookings=total_bookings,
                             total_revenue=total_revenue,
                             owner_count=owner_count,
                             renter_count=renter_count,
                             admin_count=admin_count,
                             popular_homes=popular_homes)
    except Exception as e:
        current_app.logger.error(f"Error in public dashboard test: {str(e)}")
        return f"Error: {str(e)}"

@admin_dashboard_bp.route('/simple-test')
@admin_required
def simple_test():
    """Simple test route"""
    return "Hello World - Admin Dashboard Test"

@admin_dashboard_bp.route('/dashboard-test')
@admin_required
def dashboard_test():
    """Dashboard test route with authentication"""
    try:
        # Get basic statistics with caching
        stats_data = get_dashboard_statistics()
        
        # Format stats for template
        stats = {
            'total_homes': stats_data['total_homes'],
            'total_bookings': stats_data['total_bookings'],
            'active_users': stats_data['active_users'],
            'total_revenue': stats_data['total_revenue'],
            'total_owners': 0,  # Will be updated below
            'total_renters': 0  # Will be updated below
        }
        
        # Get recent activities with caching
        recent_activities = get_recent_activities()
        
        # Get chart data with caching
        chart_data = get_chart_data()
        
        # Get weekly statistics with caching
        weekly_stats = get_weekly_stats()
        
        # Get additional data needed for template
        total_users = Owner.query.count() + Renter.query.count() + Admin.query.count()
        total_homes = Home.query.count()
        total_bookings = Booking.query.count()
        total_revenue = db.session.query(func.sum(Booking.total_price)).scalar() or 0
        
        # User counts by type
        owner_count = Owner.query.count()
        renter_count = Renter.query.count()
        admin_count = Admin.query.count()
        
        # Update stats with actual counts
        stats['total_owners'] = owner_count
        stats['total_renters'] = renter_count
        
        # Popular homes
        popular_homes = Home.query.options(
            db.joinedload(Home.images)
        ).filter_by(is_active=True).limit(5).all()
        
        return render_template('pages/admin_dashboard.html', 
                             stats=stats, 
                             recent_activities=recent_activities,
                             chart_data=chart_data,
                             weekly_stats=weekly_stats,
                             users=None,
                             current_role_filter='all',
                             current_filter='all',
                             search_query='',
                             total_users=total_users,
                             total_homes=total_homes,
                             total_bookings=total_bookings,
                             total_revenue=total_revenue,
                             owner_count=owner_count,
                             renter_count=renter_count,
                             admin_count=admin_count,
                             popular_homes=popular_homes)
    except Exception as e:
        current_app.logger.error(f"Error in dashboard test: {str(e)}")
        return f"Error: {str(e)}"

@admin_dashboard_bp.route('/template-test')
@admin_required
def template_test():
    """Template test route"""
    return render_template('pages/test_dashboard.html')

@admin_dashboard_bp.route('/simple-template-test')
@admin_required
def simple_template_test():
    """Simple template test route"""
    return render_template('pages/simple_test.html')

@admin_dashboard_bp.route('/profile')
@admin_required
@handle_web_errors
def profile():
    """Admin profile page"""
    return render_template('admin/profile.html', admin=current_user)


# =============================================================================
# STATISTICS API ROUTES
# =============================================================================

@admin_dashboard_bp.route('/api/stats/overview')
@admin_required
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


@admin_dashboard_bp.route('/api/stats/users')
@admin_required
@handle_api_errors
def get_user_stats():
    """Get user statistics"""
    try:
        # Total users by type
        total_owners = Owner.query.count()
        total_renters = Renter.query.count()
        total_admins = Admin.query.count()
        
        # Active users (last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        try:
            active_owners = Owner.query.filter(Owner.last_login >= thirty_days_ago).count()
            active_renters = Renter.query.filter(Renter.last_login >= thirty_days_ago).count()
        except AttributeError:
            # Fallback to created_at if last_login doesn't exist
            active_owners = Owner.query.filter(Owner.created_at >= thirty_days_ago).count()
            active_renters = Renter.query.filter(Renter.created_at >= thirty_days_ago).count()
        
        # New users this month
        month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        new_owners = Owner.query.filter(Owner.created_at >= month_start).count()
        new_renters = Renter.query.filter(Renter.created_at >= month_start).count()
        
        stats = {
            'total_owners': total_owners,
            'total_renters': total_renters,
            'total_admins': total_admins,
            'active_owners': active_owners,
            'active_renters': active_renters,
            'new_owners': new_owners,
            'new_renters': new_renters
        }
        
        return jsonify({
            "success": True,
            "data": stats
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting user stats: {str(e)}")
        return jsonify({"error": "Failed to get user statistics"}), 500


@admin_dashboard_bp.route('/api/stats/homes')
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
        month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        new_homes = Home.query.filter(Home.created_at >= month_start).count()
        
        stats = {
            'total_homes': total_homes,
            'active_homes': active_homes,
            'inactive_homes': inactive_homes,
            'new_homes': new_homes,
            'homes_by_type': [{'type': prop_type, 'count': count} for prop_type, count in homes_by_type]
        }
        
        return jsonify({
            "success": True,
            "data": stats
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting home stats: {str(e)}")
        return jsonify({"error": "Failed to get home statistics"}), 500


@admin_dashboard_bp.route('/api/stats/bookings')
@admin_required
@handle_api_errors
def get_booking_stats():
    """Get booking statistics"""
    try:
        # Total bookings
        total_bookings = Booking.query.count()
        
        # Bookings by status
        bookings_by_status = db.session.query(
            Booking.status,
            func.count(Booking.id)
        ).group_by(Booking.status).all()
        
        # Bookings this month
        month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        monthly_bookings = Booking.query.filter(Booking.created_at >= month_start).count()
        
        # Revenue this month
        monthly_revenue = db.session.query(func.sum(Payment.amount)).join(Booking).filter(
            Payment.status == 'success',
            Payment.paid_at >= month_start
        ).scalar() or 0
        
        stats = {
            'total_bookings': total_bookings,
            'monthly_bookings': monthly_bookings,
            'monthly_revenue': monthly_revenue,
            'bookings_by_status': [{'status': status, 'count': count} for status, count in bookings_by_status]
        }
        
        return jsonify({
            "success": True,
            "data": stats
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting booking stats: {str(e)}")
        return jsonify({"error": "Failed to get booking statistics"}), 500


@admin_dashboard_bp.route('/api/stats/revenue')
@admin_required
@handle_api_errors
def get_revenue_stats():
    """Get revenue statistics"""
    try:
        # Total revenue
        total_revenue = db.session.query(func.sum(Payment.amount)).filter(
            Payment.status == 'success'
        ).scalar() or 0
        
        # Revenue this month
        month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        monthly_revenue = db.session.query(func.sum(Payment.amount)).filter(
            Payment.status == 'success',
            Payment.paid_at >= month_start
        ).scalar() or 0
        
        # Revenue last month
        last_month_start = (month_start - timedelta(days=1)).replace(day=1)
        last_month_revenue = db.session.query(func.sum(Payment.amount)).filter(
            Payment.status == 'success',
            Payment.paid_at >= last_month_start,
            Payment.paid_at < month_start
        ).scalar() or 0
        
        # Revenue growth
        revenue_growth = 0
        if last_month_revenue > 0:
            revenue_growth = ((monthly_revenue - last_month_revenue) / last_month_revenue) * 100
        
        stats = {
            'total_revenue': total_revenue,
            'monthly_revenue': monthly_revenue,
            'last_month_revenue': last_month_revenue,
            'revenue_growth': round(revenue_growth, 2)
        }
        
        return jsonify({
            "success": True,
            "data": stats
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting revenue stats: {str(e)}")
        return jsonify({"error": "Failed to get revenue statistics"}), 500


@admin_dashboard_bp.route('/api/charts/monthly-data')
@admin_required
@handle_api_errors
def get_monthly_chart_data():
    """Get monthly chart data for dashboard"""
    try:
        # Get data for last 12 months
        monthly_data = []
        
        for i in range(12):
            month_start = datetime.utcnow() - timedelta(days=30 * (i + 1))
            month_end = datetime.utcnow() - timedelta(days=30 * i)
            
            # Users
            new_users = Owner.query.filter(
                Owner.created_at >= month_start,
                Owner.created_at < month_end
            ).count() + Renter.query.filter(
                Renter.created_at >= month_start,
                Renter.created_at < month_end
            ).count()
            
            # Homes
            new_homes = Home.query.filter(
                Home.created_at >= month_start,
                Home.created_at < month_end
            ).count()
            
            # Bookings
            bookings = Booking.query.filter(
                Booking.created_at >= month_start,
                Booking.created_at < month_end
            ).count()
            
            # Revenue
            revenue = db.session.query(func.sum(Payment.amount)).join(Booking).filter(
                Payment.status == 'success',
                Payment.paid_at >= month_start,
                Payment.paid_at < month_end
            ).scalar() or 0
            
            monthly_data.append({
                'month': month_start.strftime('%Y-%m'),
                'new_users': new_users,
                'new_homes': new_homes,
                'bookings': bookings,
                'revenue': revenue
            })
        
        return jsonify({
            "success": True,
            "data": list(reversed(monthly_data))
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting monthly chart data: {str(e)}")
        return jsonify({"error": "Failed to get monthly chart data"}), 500


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_dashboard_statistics():
    """Get comprehensive dashboard statistics with caching"""
    @cache.memoize(timeout=300)  # Cache for 5 minutes
    def _get_stats():
        try:
            # Get basic counts with optimized queries
            total_homes = Home.query.count()
            total_bookings = Booking.query.count()
            total_payments = Payment.query.count()
            
            # Get active users with fallback for last_login
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            try:
                active_users = Owner.query.filter(Owner.last_login >= thirty_days_ago).count() + \
                              Renter.query.filter(Renter.last_login >= thirty_days_ago).count()
            except AttributeError:
                # Fallback to created_at if last_login doesn't exist
                active_users = Owner.query.filter(Owner.created_at >= thirty_days_ago).count() + \
                              Renter.query.filter(Renter.created_at >= thirty_days_ago).count()
            
            # Get total users
            total_owners = Owner.query.count()
            total_renters = Renter.query.count()
            
            # Get revenue with optimized query
            total_revenue = db.session.query(func.sum(Payment.amount)).filter(
                Payment.status == 'success'
            ).scalar() or 0
            
            # Get pending bookings
            pending_bookings = Booking.query.filter_by(status='pending').count()
            
            return {
                'total_homes': total_homes,
                'total_bookings': total_bookings,
                'total_payments': total_payments,
                'active_users': active_users,
                'total_owners': total_owners,
                'total_renters': total_renters,
                'total_revenue': total_revenue,
                'pending_bookings': pending_bookings
            }
        except Exception as e:
            current_app.logger.error(f"Error getting dashboard statistics: {str(e)}")
            return {
                'total_homes': 0,
                'total_bookings': 0,
                'total_payments': 0,
                'active_users': 0,
                'total_owners': 0,
                'total_renters': 0,
                'total_revenue': 0,
                'pending_bookings': 0
            }
    
    return _get_stats()


def get_recent_activities():
    """Get recent activities for dashboard with caching"""
    @cache.memoize(timeout=180)  # Cache for 3 minutes
    def _get_activities():
        try:
            activities = []
            
            # Recent bookings with optimized query
            recent_bookings = Booking.query.options(
                db.joinedload(Booking.home),
                db.joinedload(Booking.renter)
            ).order_by(Booking.created_at.desc()).limit(5).all()
            
            for booking in recent_bookings:
                activities.append({
                    'type': 'booking',
                    'description': f'New booking for {booking.home.title}',
                    'time': booking.created_at,
                    'user': booking.renter.full_name if booking.renter else 'Unknown'
                })
            
            # Recent homes with optimized query
            recent_homes = Home.query.options(
                db.joinedload(Home.owner)
            ).order_by(Home.created_at.desc()).limit(5).all()
            
            for home in recent_homes:
                activities.append({
                    'type': 'home',
                    'description': f'New home added: {home.title}',
                    'time': home.created_at,
                    'user': home.owner.full_name if home.owner else 'Unknown'
                })
            
            # Recent payments with optimized query
            recent_payments = Payment.query.options(
                db.joinedload(Payment.booking).joinedload(Booking.renter)
            ).filter(
                Payment.status == 'success'
            ).order_by(Payment.paid_at.desc()).limit(5).all()
            
            for payment in recent_payments:
                activities.append({
                    'type': 'payment',
                    'description': f'Payment received: {payment.amount:,.0f} VND',
                    'time': payment.paid_at,
                    'user': payment.booking.renter.full_name if payment.booking and payment.booking.renter else 'Unknown'
                })
            
            # Sort by time and return top 10
            activities.sort(key=lambda x: x['time'], reverse=True)
            return activities[:10]
            
        except Exception as e:
            current_app.logger.error(f"Error getting recent activities: {str(e)}")
            return []
    
    return _get_activities()


def get_chart_data():
    """Get chart data for dashboard with caching"""
    @cache.memoize(timeout=600)  # Cache for 10 minutes
    def _get_chart_data():
        try:
            # Monthly data for last 6 months
            monthly_data = []
            
            for i in range(6):
                month_start = datetime.utcnow() - timedelta(days=30 * (i + 1))
                month_end = datetime.utcnow() - timedelta(days=30 * i)
                
                # Users with optimized query
                new_users = Owner.query.filter(
                    Owner.created_at >= month_start,
                    Owner.created_at < month_end
                ).count() + Renter.query.filter(
                    Renter.created_at >= month_start,
                    Renter.created_at < month_end
                ).count()
                
                # Revenue with optimized query
                revenue = db.session.query(func.sum(Payment.amount)).join(Booking).filter(
                    Payment.status == 'success',
                    Payment.paid_at >= month_start,
                    Payment.paid_at < month_end
                ).scalar() or 0
                
                monthly_data.append({
                    'month': month_start.strftime('%Y-%m'),
                    'users': new_users,
                    'revenue': revenue
                })
            
            return list(reversed(monthly_data))
            
        except Exception as e:
            current_app.logger.error(f"Error getting chart data: {str(e)}")
            return []
    
    return _get_chart_data()


def get_vietnam_datetime():
    """Get current datetime in Vietnam timezone"""
    vn_tz = pytz.timezone(TIMEZONE['VIETNAM'])
    return datetime.now(vn_tz)


def convert_to_utc(dt):
    """Convert datetime to UTC for database comparison"""
    vn_tz = pytz.timezone(TIMEZONE['VIETNAM'])
    return vn_tz.localize(dt).astimezone(pytz.UTC).replace(tzinfo=None)


def get_weekly_stats():
    """Get weekly statistics with caching"""
    @cache.memoize(timeout=300)  # Cache for 5 minutes
    def _get_weekly_stats():
        try:
            vn_tz = pytz.timezone(TIMEZONE['VIETNAM'])
            today_vn = datetime.now(vn_tz).date()
            
            # Get the start of current week (Monday)
            days_since_monday = today_vn.weekday()
            week_start = today_vn - timedelta(days=days_since_monday)
            week_start_datetime = datetime.combine(week_start, datetime.min.time())
            week_start_utc = convert_to_utc(week_start_datetime)
            
            # Calculate new records this week with optimized queries
            new_owners_this_week = Owner.query.filter(Owner.created_at >= week_start_utc).count()
            new_renters_this_week = Renter.query.filter(Renter.created_at >= week_start_utc).count()
            new_homes_this_week = Home.query.filter(Home.created_at >= week_start_utc).count()
            new_bookings_this_week = Booking.query.filter(Booking.created_at >= week_start_utc).count()
            
            # Calculate booking growth rate
            total_bookings = Booking.query.count()
            booking_growth_rate = 0
            if total_bookings > 0:
                booking_growth_rate = round((new_bookings_this_week / total_bookings) * 100, 1)
            
            # Calculate monthly stats
            month_start = today_vn.replace(day=1)
            month_start_datetime = datetime.combine(month_start, datetime.min.time())
            month_start_utc = convert_to_utc(month_start_datetime)
            
            new_owners_this_month = Owner.query.filter(Owner.created_at >= month_start_utc).count()
            new_renters_this_month = Renter.query.filter(Renter.created_at >= month_start_utc).count()
            new_homes_this_month = Home.query.filter(Home.created_at >= month_start_utc).count()
            new_bookings_this_month = Booking.query.filter(Booking.created_at >= month_start_utc).count()
            
            return {
                'new_owners': new_owners_this_week,
                'new_renters': new_renters_this_week,
                'new_homes': new_homes_this_week,
                'new_bookings': new_bookings_this_week,
                'booking_growth_rate': booking_growth_rate,
                'new_owners_month': new_owners_this_month,
                'new_renters_month': new_renters_this_month,
                'new_homes_month': new_homes_this_month,
                'new_bookings_month': new_bookings_this_month
            }
            
        except Exception as e:
            current_app.logger.error(f"Error getting weekly stats: {str(e)}")
            return {
                'new_owners': 0,
                'new_renters': 0,
                'new_homes': 0,
                'new_bookings': 0,
                'booking_growth_rate': 0,
                'new_owners_month': 0,
                'new_renters_month': 0,
                'new_homes_month': 0,
                'new_bookings_month': 0
            }
    
    return _get_weekly_stats()
