"""
Admin Users Routes - User management functionality
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta
from sqlalchemy import func, distinct, extract
import pytz

from app.routes.decorators import admin_required, super_admin_required
from app.routes.error_handlers import handle_api_errors, handle_web_errors, handle_validation_errors
from app.routes.constants import FLASH_MESSAGES, URLS, TIMEZONE, PAGINATION, USER_ROLES
from app.routes.base import BaseRouteHandler

# Import models
from app.models.models import db, Admin, Owner, Renter, Home, Booking, Payment

admin_users_bp = Blueprint('admin_users', __name__, url_prefix='/admin')


class AdminUsersHandler(BaseRouteHandler):
    """Handler for admin user management functionality"""
    
    def __init__(self):
        super().__init__('admin_users')


# =============================================================================
# USER MANAGEMENT ROUTES
# =============================================================================

@admin_users_bp.route('/users')
@admin_required
@handle_web_errors
def users():
    """User management page"""
    # Get query parameters
    user_type = request.args.get('type', 'all')
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    
    # Build query based on user type
    if user_type == 'owners':
        query = Owner.query
        template = 'admin/users.html'
    elif user_type == 'renters':
        query = Renter.query
        template = 'admin/users.html'
    elif user_type == 'admins':
        query = Admin.query
        template = 'admin/users.html'
    else:
        # Show all users - we'll need to combine queries
        return show_all_users(page, search)
    
    # Apply search filter
    if search:
        if user_type == 'owners':
            query = query.filter(Owner.full_name.contains(search) | Owner.email.contains(search))
        elif user_type == 'renters':
            query = query.filter(Renter.full_name.contains(search) | Renter.email.contains(search))
        elif user_type == 'admins':
            query = query.filter(Admin.username.contains(search) | Admin.email.contains(search))
    
    # Paginate
    pagination = query.paginate(
        page=page,
        per_page=PAGINATION['PER_PAGE'],
        error_out=False
    )
    
    return render_template(template, 
                         users=pagination.items,
                         pagination=pagination,
                         user_type=user_type,
                         search=search)


@admin_users_bp.route('/users/owners')
@admin_required
@handle_web_errors
def owners():
    """Owner management page"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    
    query = Owner.query
    
    # Apply search filter
    if search:
        query = query.filter(
            Owner.full_name.contains(search) | 
            Owner.email.contains(search) |
            Owner.phone.contains(search)
        )
    
    # Paginate
    pagination = query.paginate(
        page=page,
        per_page=PAGINATION['PER_PAGE'],
        error_out=False
    )
    
    # Get owner statistics
    owner_stats = get_owner_statistics(pagination.items)
    
    return render_template('admin/owners.html', 
                         owners=pagination.items,
                         pagination=pagination,
                         search=search,
                         stats=owner_stats)


@admin_users_bp.route('/users/renters')
@admin_required
@handle_web_errors
def renters():
    """Renter management page"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    
    query = Renter.query
    
    # Apply search filter
    if search:
        query = query.filter(
            Renter.full_name.contains(search) | 
            Renter.email.contains(search) |
            Renter.phone.contains(search)
        )
    
    # Paginate
    pagination = query.paginate(
        page=page,
        per_page=PAGINATION['PER_PAGE'],
        error_out=False
    )
    
    # Get renter statistics
    renter_stats = get_renter_statistics(pagination.items)
    
    return render_template('admin/renters.html', 
                         renters=pagination.items,
                         pagination=pagination,
                         search=search,
                         stats=renter_stats)


@admin_users_bp.route('/users/admins')
@super_admin_required
@handle_web_errors
def admins():
    """Admin management page (super admin only)"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    
    query = Admin.query
    
    # Apply search filter
    if search:
        query = query.filter(
            Admin.username.contains(search) | 
            Admin.email.contains(search)
        )
    
    # Paginate
    pagination = query.paginate(
        page=page,
        per_page=PAGINATION['PER_PAGE'],
        error_out=False
    )
    
    return render_template('admin/admins.html', 
                         admins=pagination.items,
                         pagination=pagination,
                         search=search)


# =============================================================================
# USER CREATION ROUTES
# =============================================================================

@admin_users_bp.route('/users/create-owner', methods=['GET', 'POST'])
@admin_required
@handle_web_errors
def create_owner():
    """Create new owner"""
    if request.method == 'POST':
        return handle_create_owner_post()

    # GET request - show form
    return render_template('admin/create_owner.html', form_data=build_empty_user_form())


@admin_users_bp.route('/users/create-renter', methods=['GET', 'POST'])
@admin_required
@handle_web_errors
def create_renter():
    """Create new renter"""
    if request.method == 'POST':
        return handle_create_renter_post()

    # GET request - show form
    return render_template('admin/create_renter.html', form_data=build_empty_user_form())


@admin_users_bp.route('/users/create-admin', methods=['GET', 'POST'])
@super_admin_required
@handle_web_errors
def create_admin():
    """Create new admin (super admin only)"""
    if request.method == 'POST':
        return handle_create_admin_post()

    # GET request - show form
    return render_template('admin/create_admin.html', form_data=build_empty_user_form())


# =============================================================================
# USER DETAIL ROUTES
# =============================================================================

@admin_users_bp.route('/users/owner/<int:owner_id>')
@admin_required
@handle_web_errors
def owner_detail(owner_id):
    """View owner details"""
    owner = Owner.query.get_or_404(owner_id)
    
    # Get owner's homes
    homes = Home.query.filter_by(owner_id=owner_id).all()
    
    # Get owner's bookings
    home_ids = [home.id for home in homes]
    bookings = []
    if home_ids:
        bookings = Booking.query.filter(Booking.home_id.in_(home_ids)).order_by(Booking.created_at.desc()).limit(10).all()
    
    # Get owner's payments
    payments = []
    if home_ids:
        payments = Payment.query.join(Booking).filter(
            Booking.home_id.in_(home_ids)
        ).order_by(Payment.created_at.desc()).limit(10).all()
    
    return render_template('admin/owner_detail.html', 
                         owner=owner, 
                         homes=homes,
                         bookings=bookings,
                         payments=payments)


@admin_users_bp.route('/users/renter/<int:renter_id>')
@admin_required
@handle_web_errors
def renter_detail(renter_id):
    """View renter details"""
    renter = Renter.query.get_or_404(renter_id)
    
    # Get renter's bookings
    bookings = Booking.query.filter_by(renter_id=renter_id).order_by(Booking.created_at.desc()).limit(10).all()
    
    # Get renter's payments
    payments = Payment.query.join(Booking).filter(
        Booking.renter_id == renter_id
    ).order_by(Payment.created_at.desc()).limit(10).all()
    
    return render_template('admin/renter_detail.html', 
                         renter=renter,
                         bookings=bookings,
                         payments=payments)


@admin_users_bp.route('/users/admin/<int:admin_id>')
@super_admin_required
@handle_web_errors
def admin_detail(admin_id):
    """View admin details (super admin only)"""
    admin = Admin.query.get_or_404(admin_id)
    
    return render_template('admin/admin_detail.html', admin=admin)


# =============================================================================
# USER ACTIONS ROUTES
# =============================================================================

@admin_users_bp.route('/users/toggle-status/<user_type>/<int:user_id>', methods=['POST'])
@admin_required
@handle_api_errors
def toggle_user_status(user_type, user_id):
    """Toggle user active status"""
    try:
        if user_type == 'owner':
            user = Owner.query.get_or_404(user_id)
        elif user_type == 'renter':
            user = Renter.query.get_or_404(user_id)
        elif user_type == 'admin':
            if not current_user.is_super_admin:
                return jsonify({"error": "Super admin access required"}), 403
            user = Admin.query.get_or_404(user_id)
        else:
            return jsonify({"error": "Invalid user type"}), 400
        
        # Toggle status
        user.is_active = not user.is_active
        db.session.commit()
        
        status = "activated" if user.is_active else "deactivated"
        return jsonify({
            "success": True,
            "message": f"User {status} successfully",
            "is_active": user.is_active
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error toggling user status: {str(e)}")
        return jsonify({"error": "Failed to toggle user status"}), 500


@admin_users_bp.route('/users/delete/<user_type>/<int:user_id>', methods=['POST'])
@admin_required
@handle_api_errors
def delete_user(user_type, user_id):
    """Delete user"""
    try:
        if user_type == 'owner':
            user = Owner.query.get_or_404(user_id)
        elif user_type == 'renter':
            user = Renter.query.get_or_404(user_id)
        elif user_type == 'admin':
            if not current_user.is_super_admin:
                return jsonify({"error": "Super admin access required"}), 403
            user = Admin.query.get_or_404(user_id)
        else:
            return jsonify({"error": "Invalid user type"}), 400
        
        # Check if user has associated data
        if user_type == 'owner':
            homes_count = Home.query.filter_by(owner_id=user_id).count()
            if homes_count > 0:
                return jsonify({"error": "Cannot delete owner with existing homes"}), 400
        
        # Delete user
        db.session.delete(user)
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "User deleted successfully"
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting user: {str(e)}")
        return jsonify({"error": "Failed to delete user"}), 500


# =============================================================================
# API ROUTES
# =============================================================================

@admin_users_bp.route('/api/users/stats')
@admin_required
@handle_api_errors
def get_user_stats():
    """Get user statistics"""
    try:
        # Total counts
        total_owners = Owner.query.count()
        total_renters = Renter.query.count()
        total_admins = Admin.query.count()
        
        # Active counts
        active_owners = Owner.query.filter_by(is_active=True).count()
        active_renters = Renter.query.filter_by(is_active=True).count()
        active_admins = Admin.query.filter_by(is_active=True).count()
        
        # New users this month
        month_start = datetime.utcnow().replace(day=1)
        new_owners = Owner.query.filter(Owner.created_at >= month_start).count()
        new_renters = Renter.query.filter(Renter.created_at >= month_start).count()
        
        stats = {
            'total_owners': total_owners,
            'total_renters': total_renters,
            'total_admins': total_admins,
            'active_owners': active_owners,
            'active_renters': active_renters,
            'active_admins': active_admins,
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


@admin_users_bp.route('/api/users/search')
@admin_required
@handle_api_errors
def search_users():
    """Search users"""
    try:
        query = request.args.get('q', '')
        user_type = request.args.get('type', 'all')
        limit = request.args.get('limit', 10, type=int)
        
        if not query:
            return jsonify({"success": True, "users": []})
        
        users = []
        
        if user_type in ['all', 'owners']:
            owners = Owner.query.filter(
                Owner.full_name.contains(query) | 
                Owner.email.contains(query)
            ).limit(limit).all()
            
            for owner in owners:
                users.append({
                    'id': owner.id,
                    'name': owner.full_name,
                    'email': owner.email,
                    'type': 'owner',
                    'is_active': owner.is_active
                })
        
        if user_type in ['all', 'renters']:
            renters = Renter.query.filter(
                Renter.full_name.contains(query) | 
                Renter.email.contains(query)
            ).limit(limit).all()
            
            for renter in renters:
                users.append({
                    'id': renter.id,
                    'name': renter.full_name,
                    'email': renter.email,
                    'type': 'renter',
                    'is_active': renter.is_active
                })
        
        if user_type in ['all', 'admins'] and current_user.is_super_admin:
            admins = Admin.query.filter(
                Admin.username.contains(query) | 
                Admin.email.contains(query)
            ).limit(limit).all()
            
            for admin in admins:
                users.append({
                    'id': admin.id,
                    'name': admin.username,
                    'email': admin.email,
                    'type': 'admin',
                    'is_active': admin.is_active
                })
        
        return jsonify({
            "success": True,
            "users": users
        })
        
    except Exception as e:
        current_app.logger.error(f"Error searching users: {str(e)}")
        return jsonify({"error": "Failed to search users"}), 500


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def show_all_users(page, search):
    """Show all users combined"""
    # This is a simplified version - in practice, you might want to use a more sophisticated approach
    owners = Owner.query.limit(5).all()
    renters = Renter.query.limit(5).all()
    admins = Admin.query.limit(5).all() if current_user.is_super_admin else []
    
    all_users = []
    
    for owner in owners:
        all_users.append({
            'id': owner.id,
            'name': owner.full_name,
            'email': owner.email,
            'type': 'owner',
            'created_at': owner.created_at,
            'is_active': owner.is_active
        })
    
    for renter in renters:
        all_users.append({
            'id': renter.id,
            'name': renter.full_name,
            'email': renter.email,
            'type': 'renter',
            'created_at': renter.created_at,
            'is_active': renter.is_active
        })
    
    for admin in admins:
        all_users.append({
            'id': admin.id,
            'name': admin.username,
            'email': admin.email,
            'type': 'admin',
            'created_at': admin.created_at,
            'is_active': admin.is_active
        })
    
    # Sort by creation date
    all_users.sort(key=lambda x: x['created_at'], reverse=True)
    
    return render_template('admin/users.html', 
                         users=all_users,
                         user_type='all',
                         search=search)


def handle_create_owner_post():
    """Handle owner creation form submission"""
    form_data = get_user_form_data()

    try:
        required_fields = ['full_name', 'username', 'email', 'phone', 'password']
        normalize_required_fields(form_data, required_fields)
        ensure_owner_uniqueness(form_data)
    except ValueError as exc:
        flash(str(exc), 'danger')
        form_data['password'] = ''
        return render_template('admin/create_owner.html', form_data=form_data), 400

    try:
        owner = Owner(
            username=form_data['username'],
            full_name=form_data['full_name'],
            email=form_data['email'],
            phone=form_data['phone'],
            password_hash=generate_password_hash(form_data['password']),
            is_active=True,
            email_verified=True,
            first_login=True
        )

        db.session.add(owner)
        db.session.commit()

        flash('Owner đã được tạo thành công', 'success')
        return redirect(url_for('admin_users.owner_detail', owner_id=owner.id))

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating owner: {str(e)}")
        flash('Có lỗi xảy ra khi tạo owner', 'danger')
        form_data['password'] = ''
        return render_template('admin/create_owner.html', form_data=form_data), 500


def handle_create_renter_post():
    """Handle renter creation form submission"""
    form_data = get_user_form_data()

    try:
        required_fields = ['full_name', 'email', 'phone', 'password']
        normalize_required_fields(form_data, required_fields)
        ensure_renter_uniqueness(form_data)

        username = form_data.get('username')
        if username:
            if Renter.query.filter_by(username=username).first():
                raise ValueError('Username đã được sử dụng')
        else:
            base_username = derive_username_from_email(form_data['email'])
            form_data['username'] = generate_unique_username(Renter, base_username)

    except ValueError as exc:
        flash(str(exc), 'danger')
        form_data['password'] = ''
        return render_template('admin/create_renter.html', form_data=form_data), 400

    try:
        renter = Renter(
            username=form_data['username'],
            full_name=form_data['full_name'],
            email=form_data['email'],
            phone=form_data['phone'],
            password_hash=generate_password_hash(form_data['password']),
            is_active=True,
            email_verified=True,
            first_login=True
        )

        db.session.add(renter)
        db.session.commit()

        flash('Renter đã được tạo thành công', 'success')
        return redirect(url_for('admin_users.renter_detail', renter_id=renter.id))

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating renter: {str(e)}")
        flash('Có lỗi xảy ra khi tạo renter', 'danger')
        form_data['password'] = ''
        return render_template('admin/create_renter.html', form_data=form_data), 500


def handle_create_admin_post():
    """Handle admin creation form submission"""
    form_data = get_user_form_data()

    try:
        required_fields = ['username', 'email', 'password']
        normalize_required_fields(form_data, required_fields)
        ensure_admin_uniqueness(form_data)
    except ValueError as exc:
        flash(str(exc), 'danger')
        form_data['password'] = ''
        return render_template('admin/create_admin.html', form_data=form_data), 400

    try:
        admin = Admin(
            username=form_data['username'],
            email=form_data['email'],
            password_hash=generate_password_hash(form_data['password']),
            is_active=True,
            is_super_admin=form_data.get('is_super_admin', False)
        )

        db.session.add(admin)
        db.session.commit()

        flash('Admin đã được tạo thành công', 'success')
        return redirect(url_for('admin_users.admin_detail', admin_id=admin.id))

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating admin: {str(e)}")
        flash('Có lỗi xảy ra khi tạo admin', 'danger')
        form_data['password'] = ''
        return render_template('admin/create_admin.html', form_data=form_data), 500


def build_empty_user_form():
    """Return default values for user creation forms."""
    return {
        'full_name': '',
        'username': '',
        'email': '',
        'phone': '',
        'password': '',
        'is_super_admin': False
    }


def normalize_required_fields(form_data, required_fields):
    """Normalize and validate required fields in form data."""
    normalized = {}
    for field in required_fields:
        value = form_data.get(field)
        if isinstance(value, str):
            value = value.strip()
            form_data[field] = value
        normalized[field] = value or None

    BaseRouteHandler.validate_required_fields(normalized, required_fields)
    return normalized


def ensure_owner_uniqueness(form_data):
    """Ensure owner username and email are unique."""
    if Owner.query.filter_by(username=form_data['username']).first():
        raise ValueError('Username đã được sử dụng')

    if Owner.query.filter_by(email=form_data['email']).first():
        raise ValueError('Email đã được sử dụng')


def ensure_renter_uniqueness(form_data):
    """Ensure renter email is unique."""
    email = form_data['email']

    if Renter.query.filter_by(email=email).first():
        raise ValueError('Email đã được sử dụng')


def ensure_admin_uniqueness(form_data):
    """Ensure admin username and email are unique."""
    if Admin.query.filter_by(username=form_data['username']).first():
        raise ValueError('Username đã được sử dụng')

    if Admin.query.filter_by(email=form_data['email']).first():
        raise ValueError('Email đã được sử dụng')


def derive_username_from_email(email):
    """Derive a username from an email address."""
    if not email:
        return ''

    if '@' not in email:
        return email

    return email.split('@')[0]


def generate_unique_username(model, base_username):
    """Generate a unique username for the given model."""
    if not base_username:
        base_username = 'user'

    candidate = base_username
    counter = 1

    while model.query.filter_by(username=candidate).first():
        candidate = f"{base_username}{counter}"
        counter += 1

    return candidate


def get_user_form_data():
    """Get and validate user form data"""
    data = build_empty_user_form()
    data.update({
        'full_name': request.form.get('full_name', '').strip(),
        'email': request.form.get('email', '').strip(),
        'phone': request.form.get('phone', '').strip(),
        'password': request.form.get('password', ''),
        'username': request.form.get('username', '').strip(),
        'is_super_admin': request.form.get('is_super_admin') == 'on'
    })

    return data


def get_owner_statistics(owners):
    """Get statistics for owners"""
    stats = {
        'total_homes': 0,
        'total_revenue': 0,
        'total_bookings': 0
    }
    
    owner_ids = [owner.id for owner in owners]
    
    if owner_ids:
        # Total homes
        stats['total_homes'] = Home.query.filter(Home.owner_id.in_(owner_ids)).count()
        
        # Total revenue
        home_ids = db.session.query(Home.id).filter(Home.owner_id.in_(owner_ids)).all()
        home_ids = [home_id[0] for home_id in home_ids]
        
        if home_ids:
            stats['total_revenue'] = db.session.query(func.sum(Payment.amount)).join(Booking).filter(
                Booking.home_id.in_(home_ids),
                Payment.status == 'success'
            ).scalar() or 0
            
            stats['total_bookings'] = Booking.query.filter(Booking.home_id.in_(home_ids)).count()
    
    return stats


def get_renter_statistics(renters):
    """Get statistics for renters"""
    stats = {
        'total_bookings': 0,
        'total_spent': 0
    }
    
    renter_ids = [renter.id for renter in renters]
    
    if renter_ids:
        # Total bookings
        stats['total_bookings'] = Booking.query.filter(Booking.renter_id.in_(renter_ids)).count()
        
        # Total spent
        stats['total_spent'] = db.session.query(func.sum(Payment.amount)).join(Booking).filter(
            Booking.renter_id.in_(renter_ids),
            Payment.status == 'success'
        ).scalar() or 0
    
    return stats
