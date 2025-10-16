# Payment System Refactor Guide

## Tổng Quan

Hệ thống thanh toán đã được refactor để tách biệt business logic khỏi routes, tạo ra cấu trúc rõ ràng và dễ bảo trì hơn.

## Cấu Trúc Mới

### 1. Services Layer

```
app/services/payment/
├── __init__.py                      # Export các services
├── payment_service.py               # Service chính xử lý thanh toán
├── payment_validation_service.py    # Service validation
├── payment_notification_service.py  # Service thông báo
└── payment_configuration_service.py # Service cấu hình PayOS
```

### 2. Routes Layer (Refactored)

```
app/routes/
├── payment_refactored.py           # Routes thanh toán chính (mới)
├── payment_api_refactored.py       # API endpoints (mới)
└── webhook_handler_refactored.py   # Webhook handler (mới)
```

## Các Services Chính

### 1. PaymentService

**Chức năng:**

- Tạo payment cho booking
- Lấy trạng thái payment
- Refresh trạng thái từ PayOS
- Hủy payment
- Xử lý payment thành công
- Lấy danh sách payment

**Ví dụ sử dụng:**

```python
from app.services.payment import payment_service

# Tạo payment
result = payment_service.create_payment(
    booking_id=123,
    user_id=456,
    return_url="https://example.com/success",
    cancel_url="https://example.com/cancel"
)

if result.get("success"):
    payment_id = result["payment_id"]
    redirect_url = result["redirect_url"]
```

### 2. PaymentValidationService

**Chức năng:**

- Validate booking trước khi tạo payment
- Validate dữ liệu payment
- Validate việc chỉnh sửa booking
- Validate cấu hình PayOS
- Kiểm tra payment trùng lặp

**Ví dụ sử dụng:**

```python
from app.services.payment import payment_validation_service

# Validate booking
result = payment_validation_service.validate_booking_for_payment(
    booking_id=123,
    user_id=456
)

if result["valid"]:
    booking = result["booking"]
    # Tiếp tục xử lý
else:
    error = result["error"]
    # Xử lý lỗi
```

### 3. PaymentNotificationService

**Chức năng:**

- Gửi thông báo tạo payment
- Gửi thông báo payment thành công
- Gửi thông báo payment thất bại
- Gửi thông báo payment bị hủy
- Gửi thông báo nhắc nhở

**Ví dụ sử dụng:**

```python
from app.services.payment import payment_notification_service

# Gửi thông báo thành công
result = payment_notification_service.send_payment_success_notification(payment)

if result["success"]:
    print("Thông báo đã được gửi")
```

### 4. PaymentConfigurationService

**Chức năng:**

- Tạo/cập nhật cấu hình PayOS
- Lấy cấu hình PayOS
- Kích hoạt/vô hiệu hóa cấu hình
- Test cấu hình PayOS
- Lấy trạng thái thanh toán của owner

**Ví dụ sử dụng:**

```python
from app.services.payment import payment_configuration_service

# Tạo cấu hình PayOS
config_data = {
    "payos_client_id": "client_id",
    "payos_api_key": "api_key",
    "payos_checksum_key": "checksum_key"
}

result = payment_configuration_service.create_payment_config(
    owner_id=123,
    config_data=config_data
)
```

## Routes Refactored

### 1. Payment Routes (`payment_refactored.py`)

**Các route chính:**

- `/checkout/<booking_id>` - Trang checkout
- `/modify-booking/<booking_id>` - Chỉnh sửa booking
- `/process_payment` - Xử lý tạo payment
- `/status/<payment_id>` - Trạng thái payment
- `/success/<payment_id>` - Thanh toán thành công
- `/failed/<payment_id>` - Thanh toán thất bại
- `/cancelled/<payment_id>` - Thanh toán bị hủy

**Đặc điểm:**

- Sử dụng services thay vì business logic trực tiếp
- Xử lý lỗi tập trung
- Code ngắn gọn và dễ đọc

### 2. Payment API Routes (`payment_api_refactored.py`)

**Các API chính:**

- `POST /api/payment/create` - Tạo payment
- `GET /api/payment/<id>/status` - Lấy trạng thái
- `POST /api/payment/webhook` - Webhook PayOS
- `POST /api/payment/<id>/cancel` - Hủy payment
- `GET /api/payment/list` - Danh sách payment
- `POST /api/payment/<id>/auto-cancel` - Tự động hủy

### 3. Webhook Handler (`webhook_handler_refactored.py`)

**Chức năng:**

- Xử lý webhook từ PayOS
- Sử dụng services để xử lý business logic
- Gửi thông báo tự động
- Logging chi tiết

## Lợi Ích Của Cấu Trúc Mới

### 1. Tách Biệt Rõ Ràng

- **Routes**: Chỉ xử lý HTTP request/response
- **Services**: Chứa business logic
- **Models**: Chỉ định nghĩa cấu trúc dữ liệu

### 2. Dễ Test

- Có thể test business logic độc lập
- Mock services dễ dàng
- Test coverage tốt hơn

### 3. Tái Sử Dụng

- Services có thể được gọi từ nhiều routes
- Logic tập trung ở một nơi
- Tránh code trùng lặp

### 4. Dễ Bảo Trì

- Thay đổi business logic chỉ cần sửa services
- Routes không bị ảnh hưởng
- Code dễ đọc và hiểu

### 5. Mở Rộng

- Dễ thêm tính năng mới
- Có thể thêm services mới
- Tích hợp với hệ thống khác dễ dàng

## Migration Guide

### 1. Thay Thế Routes Cũ

**Trước:**

```python
# Trong routes/payment.py
@payment_bp.route('/process_payment', methods=['POST'])
def process_payment():
    # Business logic trực tiếp trong route
    booking = Booking.query.get(booking_id)
    # ... nhiều dòng code xử lý
```

**Sau:**

```python
# Trong routes/payment_refactored.py
@payment_bp.route('/process_payment', methods=['POST'])
def process_payment():
    # Chỉ gọi service
    result = payment_service.create_payment(
        booking_id=int(booking_id),
        user_id=current_user.id
    )

    if result.get("error"):
        flash(result["error"], 'danger')
        return redirect(url_for('payment.checkout', booking_id=booking_id))

    return redirect(result["redirect_url"])
```

### 2. Cập Nhật Imports

**Trước:**

```python
from app.models.models import db, Booking, Payment, PaymentConfig
from app.services.payos_service import PayOSService
# ... nhiều imports khác
```

**Sau:**

```python
from app.services.payment import (
    payment_service,
    payment_validation_service,
    payment_notification_service
)
```

### 3. Xử Lý Lỗi Tập Trung

**Trước:**

```python
try:
    # Business logic
    # ...
except Exception as e:
    flash(f"Lỗi: {str(e)}", 'danger')
    return redirect(...)
```

**Sau:**

```python
result = service.method(params)

if result.get("error"):
    flash(result["error"], 'danger')
    return redirect(...)
```

## Testing

### 1. Unit Tests cho Services

```python
def test_create_payment():
    # Test payment service
    result = payment_service.create_payment(
        booking_id=123,
        user_id=456
    )

    assert result["success"] == True
    assert "payment_id" in result
```

### 2. Integration Tests cho Routes

```python
def test_process_payment_route():
    response = client.post('/payment/process_payment', data={
        'booking_id': 123
    })

    assert response.status_code == 302  # Redirect
    assert '/payment/status/' in response.location
```

## Kết Luận

Cấu trúc mới giúp:

- Code dễ đọc và bảo trì hơn
- Business logic được tách biệt rõ ràng
- Dễ test và debug
- Có thể mở rộng dễ dàng
- Tuân thủ nguyên tắc SOLID

Việc migration từ cấu trúc cũ sang mới có thể được thực hiện từng bước, không cần thay đổi toàn bộ cùng lúc.
