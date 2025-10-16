"""
Owner Homes Routes - Home management functionality
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app, session
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import os
import json
from PIL import Image
from sqlalchemy import or_, func

from app.routes.decorators import owner_email_verified, owner_required
from app.routes.error_handlers import handle_api_errors, handle_web_errors, handle_file_upload_errors
from app.routes.constants import FLASH_MESSAGES, URLS, PROPERTY_TYPES, PROPERTY_TYPE_REVERSE, FILE_UPLOAD
from app.routes.base import BaseRouteHandler

# Import models
from app.models.models import db, Home, HomeImage, Province, District, Ward, Rule, Amenity

owner_homes_bp = Blueprint('owner_homes', __name__, url_prefix='/owner')


class OwnerHomesHandler(BaseRouteHandler):
    """Handler for owner homes functionality"""
    
    def __init__(self):
        super().__init__('owner_homes')


# =============================================================================
# HOME MANAGEMENT ROUTES
# =============================================================================

@owner_homes_bp.route('/add-home', methods=['GET', 'POST'])
@owner_homes_bp.route('/add-home/<int:home_id>', methods=['GET', 'POST'])
@owner_email_verified
@handle_web_errors
def add_home(home_id=None):
    """Add or edit home"""
    if request.method == 'POST':
        return handle_add_home_post(home_id)
    
    # GET request - show form
    return handle_add_home_get(home_id)


@owner_homes_bp.route('/edit-home/<int:home_id>', methods=['GET', 'POST'])
@owner_email_verified
@handle_web_errors
def edit_home(home_id):
    """Edit existing home"""
    home = Home.query.get_or_404(home_id)
    
    # Check ownership
    if home.owner_id != current_user.id:
        flash(FLASH_MESSAGES['UNAUTHORIZED'], 'danger')
        return redirect(url_for('owner_dashboard.dashboard'))
    
    if request.method == 'POST':
        return handle_edit_home_post(home)
    
    # GET request - show edit form
    return handle_edit_home_get(home)


@owner_homes_bp.route('/delete-home/<int:home_id>', methods=['POST'])
@owner_email_verified
@handle_web_errors
def delete_home(home_id):
    """Delete home"""
    home = Home.query.get_or_404(home_id)
    
    # Check ownership
    if home.owner_id != current_user.id:
        flash(FLASH_MESSAGES['UNAUTHORIZED'], 'danger')
        return redirect(url_for('owner_dashboard.dashboard'))
    
    try:
        # Delete home images
        for image in home.images:
            delete_home_image_file(image.image_path)
            db.session.delete(image)
        
        # Delete home
        db.session.delete(home)
        db.session.commit()
        
        from app.utils.notification_helpers import show_success
        show_success('Xóa nhà thành công', 'Nhà đã được xóa khỏi hệ thống')
        return redirect(url_for('owner_dashboard.dashboard'))
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting home: {str(e)}")
        flash('Có lỗi xảy ra khi xóa nhà', 'danger')
        return redirect(url_for('owner_dashboard.dashboard'))


@owner_homes_bp.route('/home-detail/<int:home_id>')
@login_required
@handle_web_errors
def home_detail(home_id):
    """View home details"""
    home = Home.query.get_or_404(home_id)
    
    # Check ownership
    if home.owner_id != current_user.id:
        flash(FLASH_MESSAGES['UNAUTHORIZED'], 'danger')
        return redirect(url_for('owner_dashboard.dashboard'))
    
    featured_image, gallery_images = split_home_images(home)
    pricing_details = build_home_pricing_details(home)
    amenity_names = extract_sorted_relationship_names(home.amenities)
    rule_names = extract_sorted_relationship_names(home.rules)

    return render_template(
        'owner/home_detail.html',
        home=home,
        featured_image=featured_image,
        gallery_images=gallery_images,
        pricing_details=pricing_details,
        amenity_names=amenity_names,
        rule_names=rule_names
    )


@owner_homes_bp.route('/toggle-home-status/<int:home_id>', methods=['GET', 'POST'])
@login_required
@handle_web_errors
def toggle_home_status(home_id):
    """Toggle home active status"""
    home = Home.query.get_or_404(home_id)
    
    # Check ownership
    if home.owner_id != current_user.id:
        flash(FLASH_MESSAGES['UNAUTHORIZED'], 'danger')
        return redirect(url_for('owner_dashboard.dashboard'))
    
    try:
        home.is_active = not home.is_active
        db.session.commit()
        
        status = "kích hoạt" if home.is_active else "tạm dừng"
        flash(f'Nhà đã được {status} thành công', 'success')
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error toggling home status: {str(e)}")
        flash('Có lỗi xảy ra khi thay đổi trạng thái nhà', 'danger')
    
    return redirect(url_for('owner_dashboard.dashboard'))


# =============================================================================
# HOME PREVIEW & SESSION MANAGEMENT
# =============================================================================

@owner_homes_bp.route('/home-preview')
@owner_email_verified
@handle_web_errors
def home_preview():
    """Preview home before saving"""
    home_data = session.get('home_data', {})
    
    if not home_data:
        flash('Không có dữ liệu nhà để xem trước', 'warning')
        return redirect(url_for('owner_homes.add_home'))
    
    return render_template('owner/home_preview.html', home_data=home_data)


@owner_homes_bp.route('/save-current-step', methods=['POST'])
@owner_email_verified
@handle_api_errors
def save_current_step():
    """Save current step data to session"""
    try:
        data = request.get_json()
        step = data.get('step')
        form_data = data.get('form_data', {})
        
        # Get existing home data from session
        home_data = session.get('home_data', {})
        
        # Update with new step data
        home_data[step] = form_data
        
        # Save to session
        session['home_data'] = home_data
        
        return jsonify({
            "success": True,
            "message": "Dữ liệu đã được lưu tạm thời"
        })
        
    except Exception as e:
        current_app.logger.error(f"Error saving step: {str(e)}")
        return jsonify({"error": "Lỗi lưu dữ liệu"}), 500


@owner_homes_bp.route('/back-to-edit')
@login_required
@handle_web_errors
def back_to_edit():
    """Go back to edit from preview"""
    home_data = session.get('home_data', {})
    
    if not home_data:
        flash('Không có dữ liệu nhà để chỉnh sửa', 'warning')
        return redirect(url_for('owner_homes.add_home'))
    
    return redirect(url_for('owner_homes.add_home'))


@owner_homes_bp.route('/clear-home-data')
@login_required
@handle_web_errors
def clear_home_data():
    """Clear home data from session"""
    session.pop('home_data', None)
    flash('Dữ liệu nhà đã được xóa', 'info')
    return redirect(url_for('owner_homes.add_home'))


@owner_homes_bp.route('/clear-home-session', methods=['POST'])
@login_required
@handle_api_errors
def clear_home_session():
    """Clear home session data via API"""
    try:
        session.pop('home_data', None)
        return jsonify({
            "success": True,
            "message": "Dữ liệu session đã được xóa"
        })
        
    except Exception as e:
        current_app.logger.error(f"Error clearing session: {str(e)}")
        return jsonify({"error": "Lỗi xóa session"}), 500


@owner_homes_bp.route('/confirm-home', methods=['POST'])
@login_required
@handle_api_errors
def confirm_home():
    """Confirm and save home from session data"""
    try:
        home_data = session.get('home_data', {})
        
        if not home_data:
            return jsonify({"error": "Không có dữ liệu nhà để lưu"}), 400
        
        # Create home from session data
        home = create_home_from_session_data(home_data)
        
        # Clear session data
        session.pop('home_data', None)
        
        return jsonify({
            "success": True,
            "message": "Nhà đã được tạo thành công",
            "home_id": home.id
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error confirming home: {str(e)}")
        return jsonify({"error": "Lỗi tạo nhà"}), 500


# =============================================================================
# HOME IMAGES MANAGEMENT
# =============================================================================

@owner_homes_bp.route('/home/<int:home_id>/add-images', methods=['GET', 'POST'])
@owner_required
@handle_file_upload_errors
def add_home_images(home_id):
    """Add images to home"""
    home = Home.query.get_or_404(home_id)
    
    # Check ownership
    if home.owner_id != current_user.id:
        flash(FLASH_MESSAGES['UNAUTHORIZED'], 'danger')
        return redirect(url_for('owner_dashboard.dashboard'))
    
    if request.method == 'POST':
        return handle_add_images_post(home)
    
    # GET request - show form
    return render_template('owner/add_images.html', home=home)


@owner_homes_bp.route('/set-featured-image/<int:image_id>', methods=['GET'])
@login_required
@handle_web_errors
def set_featured_image(image_id):
    """Set featured image for home"""
    image = HomeImage.query.get_or_404(image_id)
    home = image.home
    
    # Check ownership
    if home.owner_id != current_user.id:
        flash(FLASH_MESSAGES['UNAUTHORIZED'], 'danger')
        return redirect(url_for('owner_dashboard.dashboard'))
    
    try:
        # Remove featured status from other images
        HomeImage.query.filter_by(home_id=home.id, is_featured=True).update({'is_featured': False})
        
        # Set this image as featured
        image.is_featured = True
        db.session.commit()
        
        flash('Ảnh đại diện đã được cập nhật', 'success')
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error setting featured image: {str(e)}")
        flash('Có lỗi xảy ra khi cập nhật ảnh đại diện', 'danger')
    
    return redirect(url_for('owner_homes.add_home_images', home_id=home.id))


@owner_homes_bp.route('/home-image/<int:image_id>/delete', methods=['GET', 'POST'])
@owner_required
@handle_web_errors
def delete_home_image(image_id):
    """Delete home image"""
    image = HomeImage.query.get_or_404(image_id)
    home = image.home
    
    # Check ownership
    if home.owner_id != current_user.id:
        flash(FLASH_MESSAGES['UNAUTHORIZED'], 'danger')
        return redirect(url_for('owner_dashboard.dashboard'))
    
    try:
        # Delete image file
        delete_home_image_file(image.image_path)
        
        # Delete image record
        db.session.delete(image)
        db.session.commit()
        
        flash('Ảnh đã được xóa thành công', 'success')
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting image: {str(e)}")
        flash('Có lỗi xảy ra khi xóa ảnh', 'danger')
    
    return redirect(url_for('owner_homes.add_home_images', home_id=home.id))


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def serialize_home_for_form(home):
    """Convert a Home model into the structure expected by the add/edit form"""
    street, ward_hint = extract_address_components(home.address)
    province_code, district_code, ward_code, ward_name = resolve_location_codes(home, ward_hint)

    selected_rental_type = determine_rental_type(home)

    selected_amenities = [
        {
            'id': amenity.id,
            'name': amenity.name,
            'icon': amenity.icon,
            'category_id': amenity.category_id,
            'category_name': getattr(getattr(amenity, 'amenity_category', None), 'name', None)
        }
        for amenity in sorted(home.amenities or [], key=lambda a: (getattr(a, 'category_id', 0) or 0, (a.name or '').lower()))
    ]

    selected_rules = [
        {
            'id': rule.id,
            'name': rule.name,
            'icon': rule.icon,
            'category': rule.category,
            'type': rule.type
        }
        for rule in sorted(home.rules or [], key=lambda r: ((r.category or '').lower(), (r.name or '').lower()))
    ]

    images = list(home.images or [])
    images.sort(key=lambda img: (0 if getattr(img, 'is_featured', False) else 1, getattr(img, 'id', 0) or 0))

    uploaded_images = []
    for index, image in enumerate(images):
        image_path = getattr(image, 'image_path', None)
        if not image_path:
            continue

        uploaded_images.append({
            'id': image.id,
            'index': index,
            'src': url_for('static', filename=image_path),
            'is_featured': bool(getattr(image, 'is_featured', False)),
            'filename': os.path.basename(image_path)
        })

    property_type_key = map_property_type_key(home.home_type)

    return {
        'home_id': home.id,
        'home_title': home.title,
        'home_description': home.description,
        'accommodation_type': home.accommodation_type,
        'property_type': property_type_key,
        'province': province_code or '',
        'district': district_code or '',
        'ward': ward_code or (ward_name or ''),
        'province_name': home.city,
        'district_name': home.district,
        'ward_name': ward_name,
        'street': street or '',
        'bathroom_count': home.bathroom_count,
        'bed_count': home.bed_count,
        'guest_count': home.max_guests,
        'selected_rental_type': selected_rental_type,
        'price_first_2_hours': normalize_price_for_form(home.price_first_2_hours),
        'price_per_additional_hour': normalize_price_for_form(home.price_per_additional_hour),
        'price_overnight': normalize_price_for_form(home.price_overnight),
        'price_daytime': normalize_price_for_form(home.price_daytime),
        'price_per_day': normalize_price_for_form(home.price_per_day),
        'hourly_price': normalize_price_for_form(home.price_per_hour),
        'daily_price': normalize_price_for_form(home.price_per_night),
        'amenities': [amenity['id'] for amenity in selected_amenities],
        'rules': [rule['id'] for rule in selected_rules],
        'selectedAmenities': selected_amenities,
        'selectedRules': selected_rules,
        'uploadedImages': uploaded_images,
        'featured_image_id': next((image.id for image in images if getattr(image, 'is_featured', False)), None),
        'has_existing_images': bool(uploaded_images)
    }


def extract_address_components(address):
    """Split the stored address into street and ward components"""
    if not address:
        return None, None

    parts = [part.strip() for part in address.split(',') if part and part.strip()]
    if not parts:
        return None, None

    street = parts[0]
    ward = parts[-1] if len(parts) > 1 else None
    return street, ward


def resolve_location_codes(home, ward_hint):
    """Resolve stored location names back to their codes for the form"""
    province_code = ''
    district_code = ''
    ward_code = ''
    ward_name = ward_hint or ''

    province_name = (home.city or '').strip()
    if province_name:
        province = Province.query.filter(Province.name.ilike(f"%{province_name}%")).first()
        if not province:
            province = Province.query.filter(Province.name.ilike(f"%{province_name}%")).first()

        if province:
            province_code = province.code

            district_name = (home.district or '').strip()
            if district_name:
                district = District.query.filter(
                    District.province_id == province.id,
                    District.name.ilike(f"%{district_name}%")
                ).first()

                if not district:
                    district = District.query.filter(
                        District.province_id == province.id,
                        District.name.ilike(f"%{district_name}%")
                    ).first()

                if district:
                    district_code = district.code

                    if ward_hint:
                        ward = Ward.query.filter(
                            Ward.district_id == district.id,
                            or_(
                                Ward.name.ilike(f"%{ward_hint}%"),
                                Ward.code == ward_hint
                            )
                        ).first()

                        if ward:
                            ward_code = ward.code
                            ward_name = ward.name

    return province_code, district_code, ward_code, ward_name


def determine_rental_type(home):
    """Infer the rental type from stored pricing values"""
    has_hourly = any(has_price_value(value) for value in [
        home.price_first_2_hours,
        home.price_per_additional_hour,
        home.price_overnight,
        home.price_daytime,
        home.price_per_hour
    ])

    has_daily = any(has_price_value(value) for value in [
        home.price_per_day,
        home.price_per_night
    ])

    if has_hourly and has_daily:
        return 'both'
    if has_hourly:
        return 'hourly'
    return 'daily'


def has_price_value(value):
    """Check if a numeric price value is meaningful"""
    try:
        return value is not None and float(value) > 0
    except (TypeError, ValueError):
        return False


def normalize_price_for_form(value):
    """Normalize stored numeric prices for pre-filling the form"""
    if value is None:
        return None

    try:
        numeric = float(value)
        if numeric.is_integer():
            return int(numeric)
        return numeric
    except (TypeError, ValueError):
        return value


def map_property_type_key(home_type):
    """Map stored property type labels back to their form keys"""
    if not home_type:
        return 'townhouse'

    direct = PROPERTY_TYPE_REVERSE.get(home_type)
    if direct:
        return direct

    normalized = home_type.strip().lower()
    for key, label in PROPERTY_TYPES.items():
        if label.strip().lower() == normalized:
            return key

    return 'townhouse'


def handle_add_home_get(home_id):
    """Handle GET request for add home"""
    if home_id:
        home = Home.query.get_or_404(home_id)
        if home.owner_id != current_user.id:
            flash(FLASH_MESSAGES['UNAUTHORIZED'], 'danger')
            return redirect(url_for('owner_dashboard.dashboard'))
        home_data = serialize_home_for_form(home)
        return render_template('owner/add_home.html', home=home, home_data=home_data, is_edit=True)
    
    # Get session data if exists
    home_data = session.get('home_data', {})
    return render_template('owner/add_home.html', home_data=home_data, is_edit=False)


def handle_add_home_post(home_id):
    """Handle POST request for add home"""
    try:
        # Get form data
        form_data = get_home_form_data()
        
        if home_id:
            # Edit existing home
            home = Home.query.get_or_404(home_id)
            if home.owner_id != current_user.id:
                flash(FLASH_MESSAGES['UNAUTHORIZED'], 'danger')
                return redirect(url_for('owner_dashboard.dashboard'))
            
            update_home_from_form_data(home, form_data)
            flash('Nhà đã được cập nhật thành công', 'success')
        else:
            # Create new home
            home = create_home_from_form_data(form_data)
            flash('Nhà đã được tạo thành công', 'success')
        
        db.session.commit()
        return redirect(url_for('owner_homes.home_detail', home_id=home.id))
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error saving home: {str(e)}")
        flash('Có lỗi xảy ra khi lưu nhà', 'danger')
        return redirect(url_for('owner_homes.add_home'))


def handle_edit_home_get(home):
    """Handle GET request for edit home"""
    home_data = serialize_home_for_form(home)
    return render_template('owner/add_home.html', home=home, home_data=home_data, is_edit=True)


def handle_edit_home_post(home):
    """Handle POST request for edit home"""
    try:
        # Get form data
        form_data = get_home_form_data()
        
        # Update home
        update_home_from_form_data(home, form_data)
        db.session.commit()
        
        flash('Nhà đã được cập nhật thành công', 'success')
        return redirect(url_for('owner_homes.home_detail', home_id=home.id))
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating home: {str(e)}")
        flash('Có lỗi xảy ra khi cập nhật nhà', 'danger')
        return redirect(url_for('owner_homes.edit_home', home_id=home.id))


def handle_add_images_post(home):
    """Handle POST request for adding images"""
    try:
        files = request.files.getlist('images')
        
        if not files or all(file.filename == '' for file in files):
            flash('Vui lòng chọn ít nhất một ảnh', 'warning')
            return redirect(url_for('owner_homes.add_home_images', home_id=home.id))
        
        uploaded_count = 0
        for file in files:
            if file and file.filename:
                if upload_home_image(file, home):
                    uploaded_count += 1
        
        if uploaded_count > 0:
            flash(f'Đã upload thành công {uploaded_count} ảnh', 'success')
        else:
            flash('Không có ảnh nào được upload thành công', 'warning')
        
        return redirect(url_for('owner_homes.add_home_images', home_id=home.id))
        
    except Exception as e:
        current_app.logger.error(f"Error uploading images: {str(e)}")
        flash('Có lỗi xảy ra khi upload ảnh', 'danger')
        return redirect(url_for('owner_homes.add_home_images', home_id=home.id))


def get_home_form_data():
    """Collect and validate data from the add/edit home form"""
    home_title = request.form.get('home_title', '').strip()
    home_description = request.form.get('home_description', '').strip()
    accommodation_type = request.form.get('accommodation_type', 'entire_home')
    property_type_key = request.form.get('property_type', '').strip()
    province_code = (request.form.get('province') or '').strip()
    district_code = (request.form.get('district') or '').strip()
    ward_value = (request.form.get('ward') or '').strip()
    street = request.form.get('street', '').strip()
    selected_rental_type = (request.form.get('selected_rental_type') or 'hourly').strip() or 'hourly'

    if not home_title:
        raise ValueError('Tên homestay là bắt buộc')
    if not home_description:
        raise ValueError('Mô tả homestay là bắt buộc')
    if not property_type_key:
        raise ValueError('Vui lòng chọn mô hình homestay')

    bathroom_count = parse_int(request.form.get('bathroom_count'), default=2, field_name='Số phòng tắm')
    bed_count = parse_int(request.form.get('bed_count'), default=1, field_name='Số giường ngủ')
    guest_count = parse_int(request.form.get('guest_count'), default=1, field_name='Số khách tối đa')

    pricing = prepare_pricing_data(request.form, selected_rental_type)

    rules = request.form.getlist('rules[]') or request.form.getlist('rules')
    amenities = request.form.getlist('amenities[]') or request.form.getlist('amenities')
    images = request.files.getlist('images')
    main_image = request.files.get('main_image')

    return {
        'home_title': home_title,
        'home_description': home_description,
        'accommodation_type': accommodation_type,
        'property_type': property_type_key,
        'province': province_code,
        'district': district_code,
        'ward': ward_value,
        'street': street,
        'bathroom_count': bathroom_count,
        'bed_count': bed_count,
        'guest_count': guest_count,
        'selected_rental_type': selected_rental_type,
        'pricing': pricing,
        'rules': rules,
        'amenities': amenities,
        'images': images,
        'main_image': main_image
    }


def create_home_from_form_data(form_data):
    """Create a new Home record using validated form data"""
    location_details = build_location_details(
        form_data.get('province'),
        form_data.get('district'),
        form_data.get('ward')
    )

    property_type_vn = PROPERTY_TYPES.get(form_data['property_type'], PROPERTY_TYPES.get('townhouse', 'Nhà phố'))
    address = build_full_address(form_data.get('street'), location_details['ward_name'])

    home = Home(
        title=form_data['home_title'],
        home_type=property_type_vn,
        accommodation_type=form_data.get('accommodation_type', 'entire_home'),
        address=address,
        city=location_details['province_name'],
        district=location_details['district_name'],
        home_number=form_data['home_title'],
        bed_count=form_data['bed_count'],
        bathroom_count=form_data['bathroom_count'],
        max_guests=form_data['guest_count'],
        description=form_data['home_description'],
        owner_id=current_user.id,
        is_active=True,
        floor_number=1
    )

    apply_pricing_to_home(home, form_data['pricing'])

    db.session.add(home)
    db.session.flush()

    update_home_relationships(home, form_data['amenities'], form_data['rules'])
    handle_home_images(home, form_data.get('images'), form_data.get('main_image'))

    return home


def create_home_from_session_data(home_data):
    """Create a home from data stored across session steps"""
    combined_data = {}
    for step_data in home_data.values():
        combined_data.update(step_data)

    form_data = {
        'home_title': combined_data.get('home_title', '').strip(),
        'home_description': combined_data.get('home_description', '').strip(),
        'accommodation_type': combined_data.get('accommodation_type', 'entire_home'),
        'property_type': combined_data.get('property_type', 'townhouse'),
        'province': combined_data.get('province'),
        'district': combined_data.get('district'),
        'ward': combined_data.get('ward'),
        'street': combined_data.get('street', ''),
        'bathroom_count': int(combined_data.get('bathroom_count', 2)),
        'bed_count': int(combined_data.get('bed_count', 1)),
        'guest_count': int(combined_data.get('guest_count', 1)),
        'selected_rental_type': combined_data.get('selected_rental_type', 'hourly'),
        'pricing': {
            'price_first_2_hours': safe_price_convert(combined_data.get('price_first_2_hours')),
            'price_per_additional_hour': safe_price_convert(combined_data.get('price_per_additional_hour')),
            'price_overnight': safe_price_convert(combined_data.get('price_overnight')),
            'price_daytime': safe_price_convert(combined_data.get('price_daytime')),
            'price_per_day': safe_price_convert(combined_data.get('price_per_day')),
            'price_per_hour': safe_price_convert(combined_data.get('hourly_price')),
            'price_per_night': safe_price_convert(combined_data.get('daily_price'))
        },
        'amenities': combined_data.get('amenities', []),
        'rules': combined_data.get('rules', []),
        'images': [],
        'main_image': None
    }

    return create_home_from_form_data(form_data)


def update_home_from_form_data(home, form_data):
    """Update an existing home using validated form data"""
    location_details = build_location_details(
        form_data.get('province'),
        form_data.get('district'),
        form_data.get('ward')
    )

    property_type_vn = PROPERTY_TYPES.get(form_data['property_type'], home.home_type)
    home.title = form_data['home_title']
    home.description = form_data['home_description']
    home.home_type = property_type_vn
    home.accommodation_type = form_data.get('accommodation_type', home.accommodation_type)
    home.address = build_full_address(form_data.get('street'), location_details['ward_name'])
    home.city = location_details['province_name']
    home.district = location_details['district_name']
    home.home_number = form_data['home_title']
    home.bed_count = form_data['bed_count']
    home.bathroom_count = form_data['bathroom_count']
    home.max_guests = form_data['guest_count']

    apply_pricing_to_home(home, form_data['pricing'])
    update_home_relationships(home, form_data['amenities'], form_data['rules'])

    if form_data.get('images') and any(img.filename for img in form_data['images']):
        handle_home_images(home, form_data.get('images'), form_data.get('main_image'))


def handle_home_images(home, images, main_image=None):
    """Upload images from the form and attach to the home"""
    files_to_process = []
    if main_image and main_image.filename:
        files_to_process.append((main_image, True))

    for image_file in images or []:
        if image_file and image_file.filename:
            files_to_process.append((image_file, False))

    for image_file, force_featured in files_to_process:
        upload_home_image(image_file, home, featured=force_featured)


def upload_home_image(file, home, featured=False):
    """Upload a single image and create its database record"""
    try:
        if not file or not file.filename:
            return False

        if not allowed_file(file.filename):
            flash(f'File {file.filename} không được hỗ trợ', 'warning')
            return False

        filename = generate_unique_filename(file.filename)
        relative_folder = os.path.join('uploads', FILE_UPLOAD['HOME_IMAGE_FOLDER'])
        upload_path = os.path.join('static', relative_folder)
        os.makedirs(upload_path, exist_ok=True)

        file_path = os.path.join(upload_path, filename)
        file.save(file_path)
        fix_image_orientation(file_path)

        image_record = HomeImage(
            home_id=home.id,
            image_path=os.path.join(relative_folder, filename),
            is_featured=False
        )

        if featured or not home.images:
            image_record.is_featured = True

        db.session.add(image_record)
        return True

    except Exception as e:
        current_app.logger.error(f"Error uploading image: {str(e)}")
        return False


def delete_home_image_file(image_path):
    """Delete a stored home image from the filesystem"""
    try:
        if not image_path:
            return

        file_path = os.path.join('static', image_path)
        if os.path.exists(file_path):
            os.remove(file_path)

    except Exception as e:
        current_app.logger.error(f"Error deleting image file: {str(e)}")


def parse_int(value, default=0, field_name='Giá trị'):
    """Safely parse integers from form input"""
    if value in (None, ''):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field_name} không hợp lệ")


def safe_price_convert(value):
    """Convert price strings to float values"""
    if value in (None, ''):
        return None
    try:
        if isinstance(value, (int, float)):
            return float(value)
        cleaned = str(value).replace(',', '').strip()
        if cleaned == '':
            return None
        return float(cleaned)
    except (TypeError, ValueError):
        return None


def prepare_pricing_data(form, rental_type):
    """Extract pricing data based on selected rental type"""
    pricing = {
        'price_first_2_hours': None,
        'price_per_additional_hour': None,
        'price_overnight': None,
        'price_daytime': None,
        'price_per_day': None,
        'price_per_hour': None,
        'price_per_night': None
    }

    if rental_type == 'hourly':
        pricing['price_first_2_hours'] = safe_price_convert(form.get('price_first_2_hours'))
        pricing['price_per_additional_hour'] = safe_price_convert(form.get('price_per_additional_hour'))
        pricing['price_overnight'] = safe_price_convert(form.get('price_overnight'))
        pricing['price_daytime'] = safe_price_convert(form.get('price_daytime'))
        pricing['price_per_hour'] = pricing['price_first_2_hours']
        pricing['price_per_night'] = safe_price_convert(form.get('daily_price'))
    elif rental_type == 'daily':
        price_per_day = safe_price_convert(form.get('price_per_day'))
        pricing['price_per_day'] = price_per_day
        pricing['price_per_night'] = price_per_day or safe_price_convert(form.get('daily_price'))
        pricing['price_per_hour'] = safe_price_convert(form.get('hourly_price'))
    else:  # both
        pricing['price_first_2_hours'] = safe_price_convert(form.get('price_first_2_hours_both'))
        pricing['price_per_additional_hour'] = safe_price_convert(form.get('price_per_additional_hour_both'))
        pricing['price_overnight'] = safe_price_convert(form.get('price_overnight_both'))
        pricing['price_daytime'] = safe_price_convert(form.get('price_daytime_both'))
        pricing['price_per_day'] = safe_price_convert(form.get('price_per_day_both'))
        pricing['price_per_hour'] = pricing['price_first_2_hours'] or safe_price_convert(form.get('hourly_price'))
        pricing['price_per_night'] = pricing['price_per_day'] or safe_price_convert(form.get('daily_price'))

    # Fallbacks for legacy fields
    if pricing['price_per_day'] is None:
        pricing['price_per_day'] = safe_price_convert(form.get('price_per_day'))
    if pricing['price_per_night'] is None:
        pricing['price_per_night'] = pricing['price_per_day']
    if pricing['price_per_hour'] is None:
        pricing['price_per_hour'] = safe_price_convert(form.get('price_first_2_hours'))

    return pricing


def build_full_address(street, ward_name):
    """Construct a user-friendly address string"""
    if street and ward_name and ward_name != 'Chưa cập nhật':
        return f"{street}, {ward_name}"
    if street:
        return street
    if ward_name and ward_name != 'Chưa cập nhật':
        return ward_name
    return "Chưa cập nhật"


def build_location_details(province_code, district_code, ward_value):
    """Resolve province/district/ward codes to names"""
    details = {
        'province_name': 'Chưa cập nhật',
        'district_name': 'Chưa cập nhật',
        'ward_name': 'Chưa cập nhật'
    }

    if not province_code:
        if ward_value:
            details['ward_name'] = ward_value
        return details

    province = Province.query.filter_by(code=province_code).first()
    if province:
        details['province_name'] = province.name

        district = None
        if district_code:
            district = District.query.filter_by(code=district_code, province_id=province.id).first()
            if district:
                details['district_name'] = district.name

        if ward_value and district:
            ward = Ward.query.filter(
                Ward.district_id == district.id,
                or_(Ward.name == ward_value, Ward.code == ward_value)
            ).first()
            if ward:
                details['ward_name'] = ward.name
            else:
                details['ward_name'] = ward_value
        elif ward_value:
            details['ward_name'] = ward_value

    return details


def split_home_images(home):
    """Return featured and gallery images for a home"""
    images = list(home.images or [])
    featured = next((img for img in images if getattr(img, 'is_featured', False)), None)

    if not featured and images:
        featured = images[0]

    gallery = [img for img in images if img is not featured]
    return featured, gallery


def build_home_pricing_details(home):
    """Build a list of pricing labels and values for display"""
    pricing_pairs = [
        ('Giá 2 giờ đầu', home.price_first_2_hours),
        ('Giá mỗi giờ thêm', home.price_per_additional_hour),
        ('Giá qua đêm', home.price_overnight),
        ('Giá ban ngày', home.price_daytime),
        ('Giá theo ngày', home.price_per_day),
        ('Giá theo giờ', home.price_per_hour),
        ('Giá theo đêm', home.price_per_night)
    ]

    details = [
        {'label': label, 'value': value}
        for label, value in pricing_pairs
        if value is not None
    ]

    if not details:
        details.append({'label': 'Giá', 'value': None})

    return details


def extract_sorted_relationship_names(items):
    """Extract and deduplicate relationship names while preserving order"""
    seen = set()
    names = []

    for item in items or []:
        name = getattr(item, 'name', None)
        if not name:
            continue

        cleaned = name.strip()
        if not cleaned:
            continue

        key = cleaned.lower()
        if key in seen:
            continue

        seen.add(key)
        names.append(cleaned)

    return names


def apply_pricing_to_home(home, pricing):
    """Apply pricing dictionary to a Home model"""
    home.price_first_2_hours = pricing.get('price_first_2_hours')
    home.price_per_additional_hour = pricing.get('price_per_additional_hour')
    home.price_overnight = pricing.get('price_overnight')
    home.price_daytime = pricing.get('price_daytime')
    home.price_per_day = pricing.get('price_per_day')

    if pricing.get('price_per_hour') is not None:
        home.price_per_hour = pricing['price_per_hour']
    elif pricing.get('price_first_2_hours') is not None:
        home.price_per_hour = pricing['price_first_2_hours']
    else:
        home.price_per_hour = None

    if pricing.get('price_per_night') is not None:
        home.price_per_night = pricing['price_per_night']
    elif pricing.get('price_per_day') is not None:
        home.price_per_night = pricing['price_per_day']
    else:
        home.price_per_night = None


def update_home_relationships(home, amenity_ids, rule_ids):
    """Update amenities and rules relationships for a home"""
    if amenity_ids is not None:
        home.amenities.clear()
        amenity_id_list = convert_to_int_list(amenity_ids)
        if amenity_id_list:
            amenities = Amenity.query.filter(Amenity.id.in_(amenity_id_list)).all()
            home.amenities.extend(amenities)

    if rule_ids is not None:
        home.rules.clear()
        rule_id_list = convert_to_int_list(rule_ids)
        if rule_id_list:
            rules = Rule.query.filter(Rule.id.in_(rule_id_list)).all()
            home.rules.extend(rules)


def convert_to_int_list(values):
    """Convert iterable values to list of integers"""
    result = []
    for value in values or []:
        try:
            result.append(int(value))
        except (TypeError, ValueError):
            continue
    return result


def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in FILE_UPLOAD['ALLOWED_EXTENSIONS']


def generate_unique_filename(filename):
    """Generate unique filename"""
    from app.utils.utils import generate_unique_filename as utils_generate_unique_filename
    return utils_generate_unique_filename(filename)


def fix_image_orientation(file_path):
    """Fix image orientation"""
    from app.utils.utils import fix_image_orientation as utils_fix_image_orientation
    utils_fix_image_orientation(file_path)
