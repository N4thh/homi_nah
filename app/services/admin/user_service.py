"""
Admin User Service
Business logic for user management operations
"""

from app.models.models import db, Owner, Renter, Admin, Home, Booking
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from app.mock.config import get_customer_api, is_mock_mode


class AdminUserService:
    """Service for admin user management operations"""
    
    def get_all_users(self) -> List[Dict]:
        """Get all users using mock API or database"""
        if is_mock_mode():
            customer_api = get_customer_api()
            return customer_api.get_all_users()
        else:
            # Use database
            users = []
            
            # Get owners
            owners = Owner.query.all()
            for owner in owners:
                users.append(self._get_owner_data(owner))
            
            # Get renters
            renters = Renter.query.all()
            for renter in renters:
                users.append(self._create_user_dict(renter, 'renter'))
            
            return users
    
    def filter_users(self, users: List[Dict], role_filter: str = 'all', 
                    status_filter: str = 'all', search_query: str = '') -> List[Dict]:
        """Apply filters to users list"""
        if is_mock_mode():
            customer_api = get_customer_api()
            return customer_api.filter_users(users, role_filter, status_filter, search_query)
        else:
            # Use original logic
            filtered_users = users.copy()
            
            # Apply role filter
            if role_filter != 'all' and role_filter in ['owner', 'renter']:
                filtered_users = [user for user in filtered_users if user['role_type'] == role_filter]
            
            # Apply status filter
            if status_filter != 'all':
                if status_filter == 'active':
                    filtered_users = [user for user in filtered_users if user['is_active']]
                elif status_filter == 'inactive':
                    filtered_users = [user for user in filtered_users if not user['is_active']]
            
            # Apply search filter
            if search_query:
                search_term = search_query.lower()
                filtered_users = [
                    user for user in filtered_users
                    if (search_term in user['username'].lower() or
                        search_term in user['email'].lower() or
                        search_term in str(user['phone']).lower() or
                        search_term in str(user['full_name']).lower())
                ]
            
            return filtered_users
    
    def sort_users(self, users: List[Dict], sort_by: str = 'id_asc') -> List[Dict]:
        """Sort users based on sort parameter"""
        if is_mock_mode():
            customer_api = get_customer_api()
            return customer_api.sort_users(users, sort_by)
        else:
            # Use original logic
            sorted_users = users.copy()
            
            if sort_by == 'id_asc':
                sorted_users.sort(key=lambda x: x['id'])
            elif sort_by == 'id_desc':
                sorted_users.sort(key=lambda x: x['id'], reverse=True)
            elif sort_by == 'name_asc':
                sorted_users.sort(key=lambda x: x['full_name'] or x['username'])
            elif sort_by == 'name_desc':
                sorted_users.sort(key=lambda x: x['full_name'] or x['username'], reverse=True)
            elif sort_by == 'date_desc':
                sorted_users.sort(key=lambda x: x['created_at'] or datetime.min, reverse=True)
            elif sort_by == 'date_asc':
                sorted_users.sort(key=lambda x: x['created_at'] or datetime.min)
            
            return sorted_users
    
    def add_owner(self, user_data: Dict) -> Dict:
        """Add new owner"""
        from app.mock.config import get_owner_api
        
        if is_mock_mode():
            owner_api = get_owner_api()
            return owner_api.add_owner_mock_response(user_data)
        else:
            # Real logic - create actual owner
            try:
                new_owner = Owner(
                    username=user_data['username'],
                    email=user_data['email'],
                    phone=user_data['phone'],
                    first_name=user_data['first_name'],
                    last_name=user_data['last_name'],
                    full_name=f"{user_data['first_name']} {user_data['last_name']}",
                    email_verified=False,
                    first_login=True
                )
                new_owner.set_password(user_data['password'])

                # Add and commit to database
                db.session.add(new_owner)
                db.session.commit()

                return {
                    'success': True,
                    'message': 'Tạo tài khoản owner thành công',
                    'data': {
                        'id': new_owner.id,
                        'username': new_owner.username,
                        'email': new_owner.email,
                        'full_name': new_owner.full_name,
                        'phone': new_owner.phone
                    }
                }
            except Exception as e:
                db.session.rollback()
                return {
                    'success': False,
                    'message': f'Lỗi khi tạo tài khoản: {str(e)}'
                }
    
    def calculate_statistics(self) -> Dict:
        """Calculate dashboard statistics"""
        try:
            today = datetime.now().date()
            
            # Get counts
            total_owners = Owner.query.count()
            total_renters = Renter.query.count()
            total_homes = db.session.query(db.func.count(Home.id)).scalar()
            total_bookings = db.session.query(db.func.count(Booking.id)).scalar()
            
            # Today's statistics
            today_owners = Owner.query.filter(db.func.date(Owner.created_at) == today).count()
            today_renters = Renter.query.filter(db.func.date(Renter.created_at) == today).count()
            today_homes = db.session.query(db.func.count(Home.id)).filter(db.func.date(Home.created_at) == today).scalar()
            today_bookings = db.session.query(db.func.count(Booking.id)).filter(db.func.date(Booking.created_at) == today).scalar()
            
            # Active bookings
            active_bookings = Booking.query.filter_by(status='active').count()
            
            # Revenue calculation
            total_revenue = db.session.query(db.func.sum(Booking.total_price)).filter_by(status='completed').scalar() or 0
            
            return {
                'total_owners': total_owners,
                'total_renters': total_renters,
                'total_homes': total_homes,
                'total_bookings': total_bookings,
                'today_owners': today_owners,
                'today_renters': today_renters,
                'today_homes': today_homes,
                'today_bookings': today_bookings,
                'active_bookings': active_bookings,
                'total_revenue': total_revenue
            }
        except Exception as e:
            return {
                'total_owners': 0,
                'total_renters': 0,
                'total_homes': 0,
                'total_bookings': 0,
                'today_owners': 0,
                'today_renters': 0,
                'today_homes': 0,
                'today_bookings': 0,
                'active_bookings': 0,
                'total_revenue': 0
            }
    
    def _get_owner_data(self, owner: Owner) -> Dict:
        """Convert Owner object to dictionary"""
        return {
            'id': owner.id,
            'username': owner.username,
            'email': owner.email,
            'full_name': owner.full_name,
            'phone': owner.phone,
            'role_type': 'owner',
            'is_active': owner.is_active,
            'created_at': owner.created_at,
            'avatar_url': owner.avatar_url or '/static/images/avatars/default.jpg',
            'first_name': owner.first_name,
            'last_name': owner.last_name,
            'email_verified': owner.email_verified,
            'first_login': owner.first_login
        }
    
    def _create_user_dict(self, user, role_type: str) -> Dict:
        """Create user dictionary from user object"""
        return {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'full_name': user.full_name,
            'phone': user.phone,
            'role_type': role_type,
            'is_active': user.is_active,
            'created_at': user.created_at,
            'avatar_url': getattr(user, 'avatar_url', None) or '/static/images/avatars/default.jpg',
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email_verified': getattr(user, 'email_verified', True),
            'first_login': getattr(user, 'first_login', False)
        }


# Global instance
admin_user_service = AdminUserService()
