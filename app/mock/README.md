# Mock API Structure

## Tổng quan

Thư mục này chứa các Mock API được tổ chức theo tính năng để dễ testing và phát triển mà không cần database thật.

## Cấu trúc thư mục

```
app/mock/
├── config.py          # Cấu hình chọn mock hoặc real data
├── customer/          # Customer management mock APIs
│   ├── __init__.py
│   └── customer_api.py
├── pagination/        # Pagination mock APIs
│   ├── __init__.py
│   └── pagination_api.py
├── owner/            # Owner management mock APIs
│   ├── __init__.py
│   └── owner_api.py
├── __init__.py
└── README.md          # File này
```

## Cách sử dụng

### 1. Chế độ Mock (Mặc định)

Để sử dụng mock data, set environment variable:

```bash
export USE_MOCK_API=true
# hoặc
set USE_MOCK_API=true  # Windows
```

### 2. Chế độ Real (Database thật)

Để sử dụng database thật:

```bash
export USE_MOCK_API=false
# hoặc
set USE_MOCK_API=false  # Windows
```

### 3. Trong code

```python
from app.mock.config import is_mock_mode, get_customer_api, get_pagination_api, get_owner_api

if is_mock_mode():
    # Sử dụng mock APIs
    customer_api = get_customer_api()
    pagination_api = get_pagination_api()
    owner_api = get_owner_api()

    users = customer_api.get_all_users()
    paginated = pagination_api.paginate_users(users)
    response = owner_api.add_owner_mock_response(data)
else:
    # Sử dụng logic cũ với database thật
    users = Owner.query.all()
```

## Mock API Features

### Customer API (`app/mock/customer/customer_api.py`)

- `get_all_users()` - Lấy danh sách users mock
- `filter_users()` - Lọc users theo role, status, search
- `sort_users()` - Sắp xếp users
- `paginate_users()` - Phân trang users
- `add_user()` - Thêm user mới (mock response)
- `get_user_stats()` - Thống kê users

### Pagination API (`app/mock/pagination/pagination_api.py`)

- `paginate_users()` - Phân trang danh sách users
- `paginate_items()` - Phân trang generic cho bất kỳ list nào
- `PaginationMock` class - Mock pagination object

### Owner API (`app/mock/owner/owner_api.py`)

- `add_owner_mock_response()` - Mock response cho việc thêm owner
- `validate_owner_data()` - Mock validation cho dữ liệu owner

## Lợi ích

1. **Tổ chức rõ ràng**: Mỗi tính năng có folder riêng biệt
2. **Dễ bảo trì**: Mock data được tách biệt khỏi routes
3. **Dễ testing**: Có thể test từng tính năng độc lập
4. **Linh hoạt**: Có thể chuyển đổi giữa mock và real data dễ dàng
5. **Bảo toàn logic cũ**: API thật vẫn hoạt động như cũ khi không dùng mock

## Mở rộng

Để thêm mock API mới:

1. Tạo folder mới trong `app/mock/` (ví dụ: `booking/`)
2. Tạo `__init__.py` và file API trong folder đó
3. Cập nhật `app/mock/config.py` để include API mới
4. Cập nhật routes để sử dụng API mới
