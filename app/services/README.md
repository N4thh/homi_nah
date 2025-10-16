# Services Structure

## Tổng quan

Thư mục `services/` chứa business logic và xử lý dữ liệu, tách biệt khỏi routes để có cấu trúc rõ ràng.

## Nguyên tắc

- **`routes/`** - Chỉ định nghĩa URL endpoints và gọi services
- **`services/`** - Chứa business logic, xử lý dữ liệu, gọi database

## Cấu trúc thư mục

```
app/services/
├── admin/             # Admin business logic
│   ├── __init__.py
│   └── user_service.py
├── owner/             # Owner business logic
│   └── __init__.py
├── renter/            # Renter business logic
│   └── __init__.py
├── payment/           # Payment business logic
│   └── __init__.py
├── payos_service.py   # PayOS integration
└── README.md          # File này
```

## Ví dụ sử dụng

### Trước (trong routes):

```python
@admin_bp.route('/users')
def get_users():
    # Business logic trực tiếp trong route
    users = Owner.query.all()
    filtered_users = [user for user in users if user.is_active]
    return jsonify(filtered_users)
```

### Sau (sử dụng services):

```python
@admin_bp.route('/users')
def get_users():
    # Route chỉ gọi service
    from app.services.admin.user_service import admin_user_service
    users = admin_user_service.get_all_users()
    return jsonify(users)
```

## Lợi ích

1. **Tách biệt rõ ràng**: Routes chỉ xử lý HTTP, Services xử lý business logic
2. **Dễ test**: Có thể test business logic độc lập
3. **Tái sử dụng**: Services có thể được gọi từ nhiều routes
4. **Dễ bảo trì**: Logic tập trung ở một nơi
5. **Mở rộng**: Dễ thêm tính năng mới

## Quy tắc

- Services không được import Flask objects (request, session, etc.)
- Services nhận data qua parameters và return kết quả
- Routes xử lý HTTP request/response và gọi services
- Mỗi service có một responsibility cụ thể
