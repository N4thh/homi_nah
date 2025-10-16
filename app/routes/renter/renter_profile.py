"""
Renter Profile Routes - Profile management and settings functionality
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

from app.routes.decorators import renter_email_verified, renter_required
from app.routes.error_handlers import handle_api_errors, handle_web_errors, handle_validation_errors
from app.routes.constants import FLASH_MESSAGES, URLS, PASSWORD_RULES, EMAIL_RULES
from app.routes.base import BaseRouteHandler

# Import models
from app.models.models import db, Renter

renter_profile_bp = Blueprint('renter_profile', __name__, url_prefix='/renter')


class RenterProfileHandler(BaseRouteHandler):
    """Handler for renter profile functionality"""
    
    def __init__(self):
        super().__init__('renter_profile')


# =============================================================================
# PROFILE MANAGEMENT ROUTES
# =============================================================================

@renter_profile_bp.route('/profile', methods=['GET', 'POST'])
@renter_email_verified
@handle_web_errors
def profile():
    """Renter profile management"""
    if request.method == 'POST':
        return handle_profile_update()
    
    # GET request - show profile form
    return render_template('renter/profile.html', renter=current_user)


@renter_profile_bp.route('/update_profile', methods=['POST'])
@login_required
@handle_validation_errors
def update_profile():
    """Update renter profile via API"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['full_name', 'email', 'phone']
        self.validate_required_fields(data, required_fields)
        
        # Validate email format
        from app.utils.email_validator import process_email
        email_result = process_email(data['email'])
        if not email_result['valid']:
            return jsonify({"error": email_result['message']}), 400
        
        # Check if email is already used by another user
        existing_renter = Renter.query.filter(
            Renter.email == data['email'],
            Renter.id != current_user.id
        ).first()
        
        if existing_renter:
            return jsonify({"error": "Email đã được sử dụng bởi tài khoản khác"}), 400
        
        # Update profile
        current_user.full_name = data['full_name'].strip()
        current_user.email = data['email'].strip()
        current_user.phone = data['phone'].strip()
        
        # Update additional fields if provided
        if 'bio' in data:
            current_user.bio = data['bio'].strip()
        
        if 'address' in data:
            current_user.address = data['address'].strip()
        
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Thông tin cá nhân đã được cập nhật thành công"
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating profile: {str(e)}")
        return jsonify({"error": "Có lỗi xảy ra khi cập nhật thông tin"}), 500


@renter_profile_bp.route('/change_password', methods=['POST'])
@login_required
@renter_required
@handle_validation_errors
def change_password():
    """Change renter password"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['current_password', 'new_password', 'confirm_password']
        self.validate_required_fields(data, required_fields)
        
        # Validate current password
        if not check_password_hash(current_user.password_hash, data['current_password']):
            return jsonify({"error": "Mật khẩu hiện tại không đúng"}), 400
        
        # Validate new password
        new_password = data['new_password']
        confirm_password = data['confirm_password']
        
        if new_password != confirm_password:
            return jsonify({"error": "Mật khẩu mới và xác nhận mật khẩu không khớp"}), 400
        
        # Validate password strength
        from app.utils.password_validator import PasswordValidator
        validator = PasswordValidator()
        validation_result = validator.validate_password(new_password)
        
        if not validation_result['valid']:
            return jsonify({"error": validation_result['message']}), 400
        
        # Update password
        current_user.password_hash = generate_password_hash(new_password)
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Mật khẩu đã được thay đổi thành công"
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error changing password: {str(e)}")
        return jsonify({"error": "Có lỗi xảy ra khi thay đổi mật khẩu"}), 500


# =============================================================================
# PROFILE IMAGE MANAGEMENT
# =============================================================================

@renter_profile_bp.route('/upload-avatar', methods=['POST'])
@login_required
@renter_required
@handle_validation_errors
def upload_avatar():
    """Upload renter avatar"""
    try:
        if 'avatar' not in request.files:
            return jsonify({"error": "Không có file được chọn"}), 400
        
        file = request.files['avatar']
        
        if file.filename == '':
            return jsonify({"error": "Không có file được chọn"}), 400
        
        # Validate file
        self.validate_file_upload(file)
        
        # Generate unique filename
        from app.utils.utils import generate_unique_filename
        filename = generate_unique_filename(file.filename)
        
        # Create upload path
        upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'profile_images')
        os.makedirs(upload_path, exist_ok=True)
        
        file_path = os.path.join(upload_path, filename)
        
        # Save file
        file.save(file_path)
        
        # Fix image orientation
        from app.utils.utils import fix_image_orientation
        fix_image_orientation(file_path)
        
        # Delete old avatar if exists
        if current_user.avatar:
            old_avatar_path = os.path.join(upload_path, current_user.avatar)
            if os.path.exists(old_avatar_path):
                os.remove(old_avatar_path)
        
        # Update user avatar
        current_user.avatar = filename
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Ảnh đại diện đã được cập nhật thành công",
            "avatar_url": f"/uploads/profile_images/{filename}"
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error uploading avatar: {str(e)}")
        return jsonify({"error": "Có lỗi xảy ra khi upload ảnh đại diện"}), 500


@renter_profile_bp.route('/remove-avatar', methods=['POST'])
@login_required
@renter_required
@handle_api_errors
def remove_avatar():
    """Remove renter avatar"""
    try:
        if current_user.avatar:
            # Delete avatar file
            upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'profile_images')
            avatar_path = os.path.join(upload_path, current_user.avatar)
            
            if os.path.exists(avatar_path):
                os.remove(avatar_path)
            
            # Update user record
            current_user.avatar = None
            db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Ảnh đại diện đã được xóa thành công"
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error removing avatar: {str(e)}")
        return jsonify({"error": "Có lỗi xảy ra khi xóa ảnh đại diện"}), 500


# =============================================================================
# VALIDATION ROUTES
# =============================================================================

@renter_profile_bp.route('/check-email', methods=['POST'])
@login_required
@handle_api_errors
def check_email():
    """Check if email is available"""
    try:
        data = request.get_json()
        email = data.get('email', '').strip()
        
        if not email:
            return jsonify({"error": "Email không được để trống"}), 400
        
        # Validate email format
        from app.utils.email_validator import process_email
        email_result = process_email(email)
        if not email_result['valid']:
            return jsonify({"error": email_result['message']}), 400
        
        # Check if email is already used
        existing_renter = Renter.query.filter(
            Renter.email == email,
            Renter.id != current_user.id
        ).first()
        
        if existing_renter:
            return jsonify({
                "available": False,
                "message": "Email đã được sử dụng"
            })
        
        return jsonify({
            "available": True,
            "message": "Email có thể sử dụng"
        })
        
    except Exception as e:
        current_app.logger.error(f"Error checking email: {str(e)}")
        return jsonify({"error": "Có lỗi xảy ra khi kiểm tra email"}), 500


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def handle_profile_update():
    """Handle profile update form submission"""
    try:
        # Get form data
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        bio = request.form.get('bio', '').strip()
        address = request.form.get('address', '').strip()
        
        # Validate required fields
        if not full_name:
            flash('Họ tên không được để trống', 'danger')
            return redirect(url_for('renter_profile.profile'))
        
        if not email:
            flash('Email không được để trống', 'danger')
            return redirect(url_for('renter_profile.profile'))
        
        if not phone:
            flash('Số điện thoại không được để trống', 'danger')
            return redirect(url_for('renter_profile.profile'))
        
        # Validate email format
        from app.utils.email_validator import process_email
        email_result = process_email(email)
        if not email_result['valid']:
            flash(email_result['message'], 'danger')
            return redirect(url_for('renter_profile.profile'))
        
        # Check if email is already used
        existing_renter = Renter.query.filter(
            Renter.email == email,
            Renter.id != current_user.id
        ).first()
        
        if existing_renter:
            flash('Email đã được sử dụng bởi tài khoản khác', 'danger')
            return redirect(url_for('renter_profile.profile'))
        
        # Update profile
        current_user.full_name = full_name
        current_user.email = email
        current_user.phone = phone
        current_user.bio = bio
        current_user.address = address
        
        db.session.commit()
        
        flash('Thông tin cá nhân đã được cập nhật thành công', 'success')
        return redirect(url_for('renter_profile.profile'))
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating profile: {str(e)}")
        flash('Có lỗi xảy ra khi cập nhật thông tin', 'danger')
        return redirect(url_for('renter_profile.profile'))


def validate_profile_data(data):
    """Validate profile data"""
    errors = []
    
    # Validate full name
    if not data.get('full_name', '').strip():
        errors.append('Họ tên không được để trống')
    
    # Validate email
    email = data.get('email', '').strip()
    if not email:
        errors.append('Email không được để trống')
    else:
        from app.utils.email_validator import process_email
        email_result = process_email(email)
        if not email_result['valid']:
            errors.append(email_result['message'])
    
    # Validate phone
    phone = data.get('phone', '').strip()
    if not phone:
        errors.append('Số điện thoại không được để trống')
    elif len(phone) < 10:
        errors.append('Số điện thoại phải có ít nhất 10 số')
    
    return errors


def get_profile_stats():
    """Get profile statistics"""
    # Get renter's bookings
    from app.models.models import Booking, Payment
    bookings = Booking.query.filter_by(renter_id=current_user.id).all()
    
    # Get booking statistics
    total_bookings = len(bookings)
    total_spent = sum(b.total_amount for b in bookings if b.payment_status == 'paid')
    
    # Get reviews
    from app.models.models import Review
    reviews = Review.query.join(Booking).filter(Booking.renter_id == current_user.id).all()
    total_reviews = len(reviews)
    avg_rating_given = sum(r.rating for r in reviews) / total_reviews if total_reviews > 0 else 0
    
    return {
        'total_bookings': total_bookings,
        'total_spent': total_spent,
        'total_reviews': total_reviews,
        'avg_rating_given': round(avg_rating_given, 2),
        'member_since': current_user.created_at.strftime('%B %Y') if current_user.created_at else 'N/A'
    }
