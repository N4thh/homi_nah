"""
Renter Search Routes - Tìm kiếm homestay
"""
from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from sqlalchemy import and_, or_, func, desc
import pytz

from app.routes.decorators import renter_email_verified, renter_required
from app.routes.error_handlers import handle_api_errors, handle_web_errors
from app.routes.constants import FLASH_MESSAGES, URLS, TIMEZONE, PAGINATION
from app.routes.base import BaseRouteHandler
from app.utils.cache import cache

# Import models
from app.models.models import db, Renter, Home, Booking, Payment, Review, Owner

renter_search_bp = Blueprint('renter_search', __name__, url_prefix='/renter')


class RenterSearchHandler(BaseRouteHandler):
    """Handler for renter search functionality"""
    
    def __init__(self):
        super().__init__('renter_search')


# =============================================================================
# SEARCH ROUTES
# =============================================================================

@renter_search_bp.route('/search')
@handle_web_errors
def search():
    """
    Tìm kiếm homestay theo các tiêu chí với caching và tối ưu hóa
    """
    try:
        # Lấy tham số tìm kiếm
        search_params = {
            'location': request.args.get('location', '').strip(),
            'check_in': request.args.get('check_in', ''),
            'check_out': request.args.get('check_out', ''),
            'guests': request.args.get('guests', '1'),
            'booking_type': request.args.get('booking_type', 'hourly'),
            'price_min': request.args.get('price_min', ''),
            'price_max': request.args.get('price_max', ''),
            'amenities': request.args.getlist('amenities'),
            'sort_by': request.args.get('sort_by', 'relevance'),
            'page': request.args.get('page', 1, type=int)
        }
        
        # Xử lý tham số
        try:
            search_params['guests'] = int(search_params['guests']) if search_params['guests'] else 1
        except ValueError:
            search_params['guests'] = 1
            
        try:
            search_params['price_min'] = float(search_params['price_min']) if search_params['price_min'] else None
        except ValueError:
            search_params['price_min'] = None
            
        try:
            search_params['price_max'] = float(search_params['price_max']) if search_params['price_max'] else None
        except ValueError:
            search_params['price_max'] = None
        
        # Tạo cache key dựa trên search parameters
        cache_key = f"search_{hash(str(sorted(search_params.items())))}"
        
        @cache.memoize(timeout=300)  # Cache for 5 minutes
        def _get_search_results():
            # Xây dựng query với tối ưu hóa
            query = Home.query.filter_by(is_active=True).options(
                db.joinedload(Home.owner),
                db.joinedload(Home.images),
                db.joinedload(Home.reviews)
            )
            
            # Lọc theo địa điểm với tối ưu hóa
            if search_params['location']:
                query = query.filter(
                    or_(
                        Home.address.contains(search_params['location']),
                        Home.city.contains(search_params['location']),
                        Home.district.contains(search_params['location']),
                        Home.title.contains(search_params['location'])
                    )
                )
            
            # Lọc theo số khách
            if search_params['booking_type'] == 'hourly':
                query = query.filter(Home.max_guests >= search_params['guests'])
            else:  # daily/overnight
                query = query.filter(Home.max_guests >= search_params['guests'])
            
            # Lọc theo giá với tối ưu hóa
            if search_params['booking_type'] == 'hourly':
                if search_params['price_min']:
                    query = query.filter(Home.price_per_hour >= search_params['price_min'])
                if search_params['price_max']:
                    query = query.filter(Home.price_per_hour <= search_params['price_max'])
            else:
                if search_params['price_min']:
                    query = query.filter(Home.price_per_night >= search_params['price_min'])
                if search_params['price_max']:
                    query = query.filter(Home.price_per_night <= search_params['price_max'])
            
            # Sắp xếp với tối ưu hóa
            if search_params['sort_by'] == 'price_low':
                if search_params['booking_type'] == 'hourly':
                    query = query.order_by(Home.price_per_hour.asc())
                else:
                    query = query.order_by(Home.price_per_night.asc())
            elif search_params['sort_by'] == 'price_high':
                if search_params['booking_type'] == 'hourly':
                    query = query.order_by(Home.price_per_hour.desc())
                else:
                    query = query.order_by(Home.price_per_night.desc())
            elif search_params['sort_by'] == 'rating':
                query = query.order_by(Home.created_at.desc())  # Fallback to created_at
            else:  # relevance
                query = query.order_by(Home.created_at.desc())
            
            # Phân trang
            pagination = query.paginate(
                page=search_params['page'],
                per_page=PAGINATION['PER_PAGE'],
                error_out=False
            )
            
            # Lấy thông tin bổ sung cho mỗi homestay với tối ưu hóa
            homes_with_details = []
            for home in pagination.items:
                # Lấy reviews gần nhất với tối ưu hóa
                recent_reviews = Review.query.filter_by(home_id=home.id)\
                    .order_by(Review.created_at.desc()).limit(3).all()
                
                # Lấy số booking gần đây với tối ưu hóa
                recent_bookings_count = Booking.query.filter_by(home_id=home.id)\
                    .filter(Booking.created_at >= datetime.utcnow() - timedelta(days=30)).count()
                
                home_data = {
                    'home': home,
                    'owner': home.owner,  # Already loaded via joinedload
                    'recent_reviews': recent_reviews,
                    'recent_bookings_count': recent_bookings_count
                }
                homes_with_details.append(home_data)
            
            return pagination, homes_with_details
        
        pagination, homes_with_details = _get_search_results()
        
        # Thống kê tìm kiếm
        search_stats = {
            'total_results': pagination.total,
            'current_page': pagination.page,
            'total_pages': pagination.pages,
            'has_prev': pagination.has_prev,
            'has_next': pagination.has_next
        }
        
        return render_template('renter/search.html',
                             homes_with_details=homes_with_details,
                             search_params=search_params,
                             search_stats=search_stats,
                             pagination=pagination)
        
    except Exception as e:
        current_app.logger.error(f"Error in search: {str(e)}")
        return render_template('renter/search.html',
                             homes_with_details=[],
                             search_params=search_params,
                             search_stats={'total_results': 0},
                             error_message="Có lỗi xảy ra khi tìm kiếm")


@renter_search_bp.route('/api/search/suggestions')
@handle_api_errors
def search_suggestions():
    """
    API để lấy gợi ý tìm kiếm với caching
    """
    try:
        query = request.args.get('q', '').strip()
        if len(query) < 2:
            return jsonify({'suggestions': []})
        
        @cache.memoize(timeout=600)  # Cache for 10 minutes
        def _get_suggestions():
            # Tìm kiếm homestay theo tên và địa chỉ với tối ưu hóa
            homes = Home.query.filter(
                and_(
                    Home.is_active == True,
                    or_(
                        Home.title.contains(query),
                        Home.address.contains(query),
                        Home.city.contains(query),
                        Home.district.contains(query)
                    )
                )
            ).with_entities(
                Home.id, Home.title, Home.address, Home.city, Home.district
            ).limit(10).all()
            
            suggestions = []
            for home in homes:
                suggestions.append({
                    'id': home.id,
                    'name': home.title,
                    'address': home.address,
                    'city': home.city,
                    'district': home.district,
                    'type': 'homestay'
                })
            
            # Tìm kiếm địa điểm phổ biến với tối ưu hóa
            locations = db.session.query(Home.city, Home.district)\
                .filter(
                    and_(
                        Home.is_active == True,
                        or_(
                            Home.city.contains(query),
                            Home.district.contains(query)
                        )
                    )
                )\
                .distinct().limit(5).all()
            
            for city, district in locations:
                suggestions.append({
                    'name': f"{district}, {city}",
                    'city': city,
                    'district': district,
                    'type': 'location'
                })
            
            return suggestions
        
        suggestions = _get_suggestions()
        return jsonify({'suggestions': suggestions})
        
    except Exception as e:
        current_app.logger.error(f"Error in search suggestions: {str(e)}")
        return jsonify({'error': 'Lỗi server'}), 500


@renter_search_bp.route('/api/search/filters')
@handle_api_errors
def search_filters():
    """
    API để lấy các bộ lọc có sẵn với caching
    """
    try:
        @cache.memoize(timeout=1800)  # Cache for 30 minutes
        def _get_filters():
            # Lấy khoảng giá với tối ưu hóa
            price_stats = db.session.query(
                func.min(Home.price_per_hour).label('min_hourly'),
                func.max(Home.price_per_hour).label('max_hourly'),
                func.min(Home.price_per_night).label('min_daily'),
                func.max(Home.price_per_night).label('max_daily')
            ).filter(Home.is_active == True).first()
            
            filters = {
                'amenities': [],  # Simplified for now
                'price_ranges': {
                    'hourly': {
                        'min': float(price_stats.min_hourly) if price_stats.min_hourly else 0,
                        'max': float(price_stats.max_hourly) if price_stats.max_hourly else 1000000
                    },
                    'daily': {
                        'min': float(price_stats.min_daily) if price_stats.min_daily else 0,
                        'max': float(price_stats.max_daily) if price_stats.max_daily else 10000000
                    }
                }
            }
            
            return filters
        
        filters = _get_filters()
        return jsonify(filters)
        
    except Exception as e:
        current_app.logger.error(f"Error in search filters: {str(e)}")
        return jsonify({'error': 'Lỗi server'}), 500
