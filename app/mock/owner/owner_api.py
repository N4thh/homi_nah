"""
Owner Mock API
"""

class OwnerAPI:
    """Mock API for owner operations"""
    
    @staticmethod
    def add_owner_mock_response(user_data):
        """Mock response for adding owner"""
        return {
            'success': True,
            'message': 'Tạo tài khoản owner thành công',
            'data': {
                'id': 999,  # Mock ID
                'username': user_data.get('username'),
                'email': user_data.get('email'),
                'full_name': f"{user_data.get('first_name')} {user_data.get('last_name')}",
                'phone': user_data.get('phone'),
                'role_type': 'owner',
                'is_active': True,
                'created_at': '2024-01-01T00:00:00Z'
            }
        }
    
    @staticmethod
    def validate_owner_data(user_data):
        """Mock validation for owner data"""
        errors = []
        
        # Check required fields
        required_fields = ['first_name', 'last_name', 'username', 'email', 'phone', 'password', 'confirm_password']
        for field in required_fields:
            if not user_data.get(field):
                errors.append(f'Vui lòng điền đầy đủ thông tin bắt buộc')
                break
        
        # Check email format
        email = user_data.get('email', '')
        if email and '@' not in email:
            errors.append('Email không hợp lệ')
        
        # Check phone format
        phone = user_data.get('phone', '')
        if phone and len(phone) < 10:
            errors.append('Số điện thoại không hợp lệ')
        
        # Check password length
        password = user_data.get('password', '')
        if password and len(password) < 6:
            errors.append('Mật khẩu phải có ít nhất 6 ký tự')
        
        # Check password match
        if user_data.get('password') != user_data.get('confirm_password'):
            errors.append('Mật khẩu xác nhận không khớp')
        
        return errors

# Global instance
owner_api = OwnerAPI()
