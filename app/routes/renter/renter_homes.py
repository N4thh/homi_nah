"""
Renter Homes Routes - Xem và đặt homestay
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from sqlalchemy import and_, or_, func, desc
import pytz

from app.routes.decorators import renter_email_verified, renter_required
from app.routes.error_handlers import handle_api_errors, handle_web_errors
from app.routes.constants import FLASH_MESSAGES, URLS, TIMEZONE, PAGINATION
from app.routes.base import BaseRouteHandler

# Import models
from app.models.models import db, Renter, Home, Booking, Payment, Review, Owner

renter_homes_bp = Blueprint('renter_homes', __name__, url_prefix='/renter')


class RenterHomesHandler(BaseRouteHandler):
    """Handler for renter homes functionality"""
    
    def __init__(self):
        super().__init__('renter_homes')


# =============================================================================
# HOME VIEWING ROUTES
# =============================================================================

@renter_homes_bp.route('/view-home/<int:home_id>')
@handle_web_errors
def view_home_detail(home_id):
    """
    Xem chi tiết homestay
    """
    try:
        # Lấy thông tin homestay
        home = Home.query.get_or_404(home_id)
        
        # Kiểm tra homestay có active không
        if not home.is_active:
            flash("Homestay này hiện không khả dụng", 'warning')
            return redirect(url_for('renter_search.search'))
        
        # Lấy thông tin owner
        owner = Owner.query.get(home.owner_id)
        
        # Lấy reviews
        reviews = Review.query.filter_by(home_id=home_id)\
            .order_by(Review.created_at.desc()).limit(10).all()
        
        # Lấy thống kê reviews
        review_stats = db.session.query(
            func.avg(Review.rating).label('avg_rating'),
            func.count(Review.id).label('total_reviews')
        ).filter_by(home_id=home_id).first()
        
        # Lấy tham số tìm kiếm từ URL
        search_params = {
            'location': request.args.get('location', ''),
            'check_in': request.args.get('check_in', ''),
            'check_out': request.args.get('check_out', ''),
            'guests': request.args.get('guests', '1'),
            'booking_type': request.args.get('booking_type', 'hourly'),
            'adults': request.args.get('adults', '1'),
            'children': request.args.get('children', '0'),
            'rooms': request.args.get('rooms', '1')
        }
        
        # Xử lý tham số
        try:
            search_params['guests'] = int(search_params['guests']) if search_params['guests'] else 1
            search_params['adults'] = int(search_params['adults']) if search_params['adults'] else 1
            search_params['children'] = int(search_params['children']) if search_params['children'] else 0
            search_params['rooms'] = int(search_params['rooms']) if search_params['rooms'] else 1
        except ValueError:
            search_params['guests'] = 1
            search_params['adults'] = 1
            search_params['children'] = 0
            search_params['rooms'] = 1
        
        # Lấy homestay liên quan
        related_homes_query = Home.query.filter(
            and_(
                Home.id != home_id,
                Home.is_active == True,
                or_(
                    Home.city == home.city,
                    Home.district == home.district
                )
            )
        )

        if hasattr(Home, 'is_approved'):
            related_homes_query = related_homes_query.filter(
                Home.is_approved.is_(True)
            )

        related_homes = related_homes_query.limit(4).all()
        
        return render_template('renter/view_home_detail.html',
                             home=home,
                             owner=owner,
                             reviews=reviews,
                             review_stats=review_stats,
                             search_params=search_params,
                             related_homes=related_homes)
        
    except Exception as e:
        current_app.logger.error(f"Error viewing home detail: {str(e)}")
        flash("Có lỗi xảy ra khi tải thông tin homestay", 'danger')
        return redirect(url_for('renter_search.search'))


@renter_homes_bp.route('/book-home/<int:home_id>')
@login_required
@renter_email_verified
@handle_web_errors
def book_home(home_id):
    """
    Trang đặt homestay
    """
    try:
        # Lấy thông tin homestay
        home = Home.query.get_or_404(home_id)
        
        # Kiểm tra homestay có active không
        if not home.is_active:
            flash("Homestay này hiện không khả dụng", 'warning')
            return redirect(url_for('renter_search.search'))
        
        # Lấy thông tin owner
        owner = Owner.query.get(home.owner_id)
        
        # Lấy tham số từ URL
        booking_type = request.args.get('type', 'hourly')
        checkin = request.args.get('checkin', '')
        checkout = request.args.get('checkout', '')
        duration = request.args.get('duration', '1')
        guests = request.args.get('guests', '1')
        
        # Xử lý tham số
        try:
            duration = int(duration) if duration else 1
            guests = int(guests) if guests else 1
        except ValueError:
            duration = 1
            guests = 1
        
        # Tính toán giá
        if booking_type == 'hourly':
            base_price = home.hourly_price
            total_price = base_price * duration
        else:  # daily
            base_price = home.daily_price
            total_price = base_price * duration
        
        # Tính phí dịch vụ và thuế
        service_fee = total_price * 0.1  # 10% phí dịch vụ
        tax = total_price * 0.1  # 10% thuế
        total_amount = total_price + service_fee + tax
        
        booking_data = {
            'home': home,
            'owner': owner,
            'booking_type': booking_type,
            'checkin': checkin,
            'checkout': checkout,
            'duration': duration,
            'guests': guests,
            'base_price': base_price,
            'total_price': total_price,
            'service_fee': service_fee,
            'tax': tax,
            'total_amount': total_amount
        }
        
        return render_template('renter/book_home.html', **booking_data)
        
    except Exception as e:
        current_app.logger.error(f"Error in book home: {str(e)}")
        flash("Có lỗi xảy ra khi tải trang đặt homestay", 'danger')
        return redirect(url_for('renter_search.search'))


@renter_homes_bp.route('/api/check-availability/<int:home_id>', methods=['POST'])
@login_required
@renter_email_verified
@handle_api_errors
def check_availability(home_id):
    """
    API kiểm tra tính khả dụng của homestay
    """
    try:
        data = request.get_json()
        checkin = data.get('checkin')
        checkout = data.get('checkout')
        booking_type = data.get('booking_type', 'hourly')
        
        if not checkin or not checkout:
            return jsonify({'error': 'Thiếu thông tin ngày check-in/check-out'}), 400
        
        # Parse dates
        try:
            checkin_date = datetime.strptime(checkin, '%Y-%m-%d')
            checkout_date = datetime.strptime(checkout, '%Y-%m-%d')
        except ValueError:
            return jsonify({'error': 'Định dạng ngày không hợp lệ'}), 400
        
        # Kiểm tra booking conflicts
        existing_bookings = Booking.query.filter(
            and_(
                Booking.home_id == home_id,
                Booking.status.in_(['confirmed', 'paid', 'checked_in']),
                or_(
                    and_(
                        Booking.check_in <= checkin_date,
                        Booking.check_out > checkin_date
                    ),
                    and_(
                        Booking.check_in < checkout_date,
                        Booking.check_out >= checkout_date
                    ),
                    and_(
                        Booking.check_in >= checkin_date,
                        Booking.check_out <= checkout_date
                    )
                )
            )
        ).count()
        
        is_available = existing_bookings == 0
        
        return jsonify({
            'available': is_available,
            'message': 'Homestay có sẵn' if is_available else 'Homestay đã được đặt trong khoảng thời gian này'
        })
        
    except Exception as e:
        current_app.logger.error(f"Error checking availability: {str(e)}")
        return jsonify({'error': 'Lỗi server'}), 500


@renter_homes_bp.route('/api/get-home-images/<int:home_id>')
@handle_api_errors
def get_home_images(home_id):
    """
    API lấy danh sách hình ảnh của homestay
    """
    try:
        home = Home.query.get_or_404(home_id)
        
        # Parse images từ JSON string
        images = []
        if home.images:
            try:
                import json
                images = json.loads(home.images) if isinstance(home.images, str) else home.images
            except:
                images = []
        
        return jsonify({
            'images': images,
            'total': len(images)
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting home images: {str(e)}")
        return jsonify({'error': 'Lỗi server'}), 500
