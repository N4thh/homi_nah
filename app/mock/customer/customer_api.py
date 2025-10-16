"""
Mock Customer API
Provides mock data for customer management testing
"""

from datetime import datetime, timedelta
import random
from typing import List, Dict, Optional, Tuple


class MockCustomerAPI:
    """Mock API for customer management operations"""
    
    def __init__(self):
        self.mock_users = self._generate_mock_users()
        self.next_id = 51  # Next available ID
    
    def _generate_mock_users(self) -> List[Dict]:
        """Generate mock user data"""
        mock_users = []
        
        # Mock owners
        owner_names = [
            "Nguyễn Văn An", "Trần Thị Bình", "Lê Văn Cường", "Phạm Thị Dung", "Hoàng Văn Em",
            "Vũ Thị Phương", "Đặng Văn Giang", "Bùi Thị Hoa", "Phan Văn Ích", "Ngô Thị Kim",
            "Dương Văn Long", "Lý Thị Mai", "Võ Văn Nam", "Đinh Thị Oanh", "Tôn Văn Phúc",
            "Hồ Thị Quỳnh", "Lưu Văn Rồng", "Chu Thị Sương", "Đỗ Văn Tài", "Cao Thị Uyên",
            "Vương Văn Việt", "Lâm Thị Xuân", "Nguyễn Văn Yên", "Trần Thị Zara", "Lê Văn Alpha"
        ]
        
        for i, name in enumerate(owner_names, 1):
            mock_users.append({
                'id': i,
                'username': f'owner{i}',
                'email': f'owner{i}@example.com',
                'full_name': name,
                'phone': f'0987{i:06d}',
                'role_type': 'owner',
                'is_active': i % 4 != 0,  # Some inactive users
                'created_at': datetime.now() - timedelta(days=random.randint(1, 365)),
                'avatar_url': f'/static/images/avatars/owner_{i}.jpg',
                'first_name': name.split()[0],
                'last_name': name.split()[-1],
                'email_verified': True,
                'first_login': False
            })
        
        # Mock renters
        renter_names = [
            "Nguyễn Thị Lan", "Trần Văn Minh", "Lê Thị Nga", "Phạm Văn Oanh", "Hoàng Thị Phương",
            "Vũ Văn Quang", "Đặng Thị Rồng", "Bùi Văn Sơn", "Phan Thị Tuyết", "Ngô Văn Uyên",
            "Dương Thị Vân", "Lý Văn Xuân", "Võ Thị Yến", "Đinh Văn Zara", "Tôn Thị Alpha",
            "Hồ Văn Beta", "Lưu Thị Gamma", "Chu Văn Delta", "Đỗ Thị Epsilon", "Cao Văn Zeta",
            "Vương Thị Eta", "Lâm Văn Theta", "Nguyễn Thị Iota", "Trần Văn Kappa", "Lê Thị Lambda"
        ]
        
        for i, name in enumerate(renter_names, 26):
            mock_users.append({
                'id': i,
                'username': f'renter{i}',
                'email': f'renter{i}@example.com',
                'full_name': name,
                'phone': f'0987{i:06d}',
                'role_type': 'renter',
                'is_active': i % 3 != 0,  # Some inactive users
                'created_at': datetime.now() - timedelta(days=random.randint(1, 365)),
                'avatar_url': f'/static/images/avatars/renter_{i}.jpg',
                'first_name': name.split()[0],
                'last_name': name.split()[-1],
                'email_verified': True,
                'first_login': False
            })
        
        return mock_users
    
    def get_all_users(self) -> List[Dict]:
        """Get all users"""
        return self.mock_users.copy()
    
    def filter_users(self, users: List[Dict], role_filter: str = 'all', 
                    status_filter: str = 'all', search_query: str = '') -> List[Dict]:
        """Apply filters to users list"""
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
        sorted_users = users.copy()
        
        if sort_by == 'id_asc':
            sorted_users.sort(key=lambda x: x['id'])
        elif sort_by == 'id_desc':
            sorted_users.sort(key=lambda x: x['id'], reverse=True)
        elif sort_by == 'name_asc':
            sorted_users.sort(key=lambda x: x['full_name'])
        elif sort_by == 'name_desc':
            sorted_users.sort(key=lambda x: x['full_name'], reverse=True)
        elif sort_by == 'email_asc':
            sorted_users.sort(key=lambda x: x['email'])
        elif sort_by == 'email_desc':
            sorted_users.sort(key=lambda x: x['email'], reverse=True)
        elif sort_by == 'created_asc':
            sorted_users.sort(key=lambda x: x['created_at'])
        elif sort_by == 'created_desc':
            sorted_users.sort(key=lambda x: x['created_at'], reverse=True)
        
        return sorted_users
    
    def paginate_users(self, users: List[Dict], page: int = 1, per_page: int = 10) -> Tuple[List[Dict], Dict]:
        """Paginate users list"""
        total = len(users)
        start = (page - 1) * per_page
        end = start + per_page
        
        paginated_users = users[start:end]
        
        # Create pagination info
        pagination_info = {
            'page': page,
            'per_page': per_page,
            'total': total,
            'pages': (total + per_page - 1) // per_page,
            'has_prev': page > 1,
            'has_next': page < (total + per_page - 1) // per_page,
            'prev_num': page - 1 if page > 1 else None,
            'next_num': page + 1 if page < (total + per_page - 1) // per_page else None
        }
        
        return paginated_users, pagination_info
    
    def add_user(self, user_data: Dict) -> Dict:
        """Add new user to mock data"""
        # Generate new ID
        new_id = self.next_id
        self.next_id += 1
        
        # Create new user
        new_user = {
            'id': new_id,
            'username': user_data['username'],
            'email': user_data['email'],
            'full_name': f"{user_data['first_name']} {user_data['last_name']}",
            'phone': user_data['phone'],
            'role_type': 'owner',  # Default to owner for add_owner function
            'is_active': True,
            'created_at': datetime.now(),
            'avatar_url': f'/static/images/avatars/default.jpg',
            'first_name': user_data['first_name'],
            'last_name': user_data['last_name'],
            'email_verified': False,
            'first_login': True
        }
        
        # Add to mock data
        self.mock_users.append(new_user)
        
        return {
            'success': True,
            'message': 'Thêm owner thành công!',
            'user': new_user
        }
    
    def check_email_exists(self, email: str) -> bool:
        """Check if email already exists"""
        return any(user['email'] == email for user in self.mock_users)
    
    def check_username_exists(self, username: str) -> bool:
        """Check if username already exists"""
        return any(user['username'] == username for user in self.mock_users)
    
    def check_phone_exists(self, phone: str) -> bool:
        """Check if phone already exists"""
        return any(user['phone'] == phone for user in self.mock_users)
    
    def get_user_stats(self) -> Dict:
        """Get user statistics"""
        total_users = len(self.mock_users)
        total_owners = len([u for u in self.mock_users if u['role_type'] == 'owner'])
        total_renters = len([u for u in self.mock_users if u['role_type'] == 'renter'])
        active_users = len([u for u in self.mock_users if u['is_active']])
        inactive_users = total_users - active_users
        
        return {
            'total_users': total_users,
            'total_owners': total_owners,
            'total_renters': total_renters,
            'active_users': active_users,
            'inactive_users': inactive_users
        }


# Global instance for easy access
mock_customer_api = MockCustomerAPI()
