# Clean Code - Admin Module

## Tổng quan
File `admin.py` đã được refactor để cải thiện khả năng đọc, bảo trì và tổ chức code. Tất cả chức năng và giao diện được giữ nguyên.

## Những cải tiến chính

### 1. Cấu trúc và Tổ chức
- **Constants**: Định nghĩa các hằng số ở đầu file
- **Decorators**: Tách riêng các decorator kiểm tra quyền
- **Helper Functions**: Tách logic phức tạp thành các hàm helper
- **Sections**: Chia code thành các phần rõ ràng với comments

### 2. Constants được định nghĩa
```python
PER_PAGE = 5
DEFAULT_COMMISSION_PERCENT = 10.0
ADMIN_COMMISSION_RATE = 0.05  # 5%
VIETNAM_TIMEZONE = 'Asia/Ho_Chi_Minh'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
```

### 3. Decorators được tách riêng
- `@admin_required`: Kiểm tra user là admin
- `@super_admin_required`: Kiểm tra user là super admin

### 4. Helper Functions được tạo
- `get_vietnam_datetime()`: Lấy datetime theo múi giờ Việt Nam
- `convert_to_utc()`: Chuyển đổi datetime sang UTC
- `create_user_dict()`: Tạo dictionary user chuẩn
- `get_owner_data()`: Lấy dữ liệu owner với commission
- `get_all_users()`: Lấy tất cả users
- `filter_users()`: Lọc users theo điều kiện
- `sort_users()`: Sắp xếp users
- `paginate_users()`: Phân trang users
- `calculate_statistics()`: Tính toán thống kê
- `calculate_weekly_statistics()`: Thống kê tuần
- `calculate_monthly_statistics()`: Thống kê tháng
- `validate_admin_input()`: Validate input admin
- `validate_owner_input()`: Validate input owner
- `handle_avatar_upload()`: Xử lý upload avatar

### 5. Cải thiện Routes
- Thêm docstrings cho tất cả routes
- Sử dụng decorators thay vì kiểm tra thủ công
- Tách logic phức tạp ra helper functions
- Cải thiện error handling
- Code ngắn gọn và dễ đọc hơn

### 6. Cải thiện Error Handling
- Sử dụng try-catch blocks nhất quán
- Rollback database khi có lỗi
- Trả về error messages rõ ràng

### 7. Cải thiện Database Queries
- Sử dụng subqueries để tránh JOIN phức tạp
- Tối ưu hóa queries với proper indexing
- Sử dụng constants cho commission rates

## Cấu trúc file mới

```
# =============================================================================
# IMPORTS
# =============================================================================

# =============================================================================
# CONSTANTS
# =============================================================================

# =============================================================================
# BLUEPRINT SETUP
# =============================================================================

# =============================================================================
# DECORATORS
# =============================================================================

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

# =============================================================================
# ROUTES
# =============================================================================
```

## Lợi ích

### 1. Khả năng đọc
- Code được tổ chức rõ ràng theo chức năng
- Docstrings cho tất cả functions
- Comments giải thích logic phức tạp

### 2. Khả năng bảo trì
- Logic được tách thành các hàm nhỏ
- Dễ dàng thay đổi constants
- Dễ dàng thêm/sửa/xóa routes

### 3. Tái sử dụng
- Helper functions có thể được sử dụng ở nhiều nơi
- Decorators có thể được áp dụng cho routes khác
- Constants có thể được import từ module khác

### 4. Hiệu suất
- Tối ưu hóa database queries
- Giảm code duplication
- Cải thiện error handling

### 5. Bảo mật
- Decorators kiểm tra quyền nhất quán
- Validation input được tách riêng
- Error messages không tiết lộ thông tin nhạy cảm

## Kết luận
File `admin.py` đã được clean code thành công, giữ nguyên toàn bộ chức năng và giao diện nhưng cải thiện đáng kể về khả năng đọc, bảo trì và mở rộng. 