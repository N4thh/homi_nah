# Payment System - Unified Structure

## Tổng Quan

Thay vì tách thành nhiều file với tên tương tự gây nhầm lẫn, hệ thống thanh toán đã được gộp lại thành **2 file chính** với cấu trúc rõ ràng và dễ quản lý.

## Cấu Trúc Mới

### 1. File Chính

```
app/routes/
├── payment_unified.py    # ✅ Tất cả routes thanh toán (Web + API)
└── webhook_unified.py    # ✅ Tất cả webhook handlers
```

### 2. Services Layer (Không thay đổi)

```
app/services/payment/
├── __init__.py                      # Export services
├── payment_service.py               # Service chính xử lý thanh toán
├── payment_validation_service.py    # Service validation
├── payment_notification_service.py  # Service thông báo
└── payment_configuration_service.py # Service cấu hình PayOS
```

## Chi Tiết Cấu Trúc

### 1. `payment_unified.py`

**Chứa tất cả routes liên quan đến thanh toán:**

#### A. Web Routes (HTML Pages)

- `/checkout/<booking_id>` - Trang checkout
- `/modify-booking/<booking_id>` - Chỉnh sửa booking
- `/process_payment` - Xử lý tạo payment
- `/status/<payment_id>` - Trạng thái payment
- `/success/<payment_id>` - Thanh toán thành công
- `/failed/<payment_id>` - Thanh toán thất bại
- `/cancelled/<payment_id>` - Thanh toán bị hủy
- `/timeout/<payment_id>` - Thanh toán hết hạn
- `/retry/<payment_id>` - Thử lại thanh toán
- `/cancel/<payment_id>` - Hủy thanh toán

#### B. API Routes (JSON Responses)

- `/api/create` - Tạo payment
- `/api/<payment_id>/status` - Lấy trạng thái
- `/api/<payment_id>/cancel` - Hủy payment
- `/api/list` - Danh sách payment
- `/api/<payment_id>/auto-cancel` - Tự động hủy
- `/api/config` - Cấu hình PayOS
- `/api/config/test` - Test cấu hình

#### C. Utility Routes (AJAX/JSON)

- `/check-status/<payment_id>` - Kiểm tra trạng thái
- `/refresh-status/<payment_id>` - Refresh trạng thái
- `/qr-data/<payment_id>` - Lấy QR data
- `/get-qr/<payment_id>` - Lấy QR trực tiếp

### 2. `webhook_unified.py`

**Chứa tất cả webhook handlers:**

#### A. PayOS Webhook Handlers

- `/webhook/payos` - Webhook chính từ PayOS

#### B. Webhook Utility Routes

- `/webhook/test` - Test webhook
- `/webhook/health` - Health check
- `/webhook/payment-status/<order_code>` - Lấy trạng thái theo order_code

#### C. Webhook Debugging Routes

- `/webhook/debug/payment/<payment_id>` - Debug payment info
- `/webhook/debug/config/<owner_id>` - Debug payment config

## Lợi Ích Của Cấu Trúc Mới

### 1. **Đơn Giản Hóa**

- Chỉ 2 file thay vì 6 file
- Không còn nhầm lẫn giữa các file tương tự
- Dễ tìm và quản lý

### 2. **Tổ Chức Rõ Ràng**

- Phân chia theo chức năng: Web routes, API routes, Utility routes
- Comments rõ ràng cho từng section
- Cấu trúc logic và dễ đọc

### 3. **Dễ Bảo Trì**

- Tất cả logic thanh toán ở một nơi
- Dễ debug và troubleshoot
- Thay đổi chỉ cần sửa 1 file

### 4. **Tương Thích Ngược**

- Giữ nguyên tất cả endpoints
- Không cần thay đổi frontend
- Migration dễ dàng

## So Sánh Cấu Trúc

### Trước (Phức Tạp)

```
app/routes/
├── payment.py                    # Routes cũ
├── payment_refactored.py         # Routes mới
├── payment_api.py                 # API cũ
├── payment_api_refactored.py      # API mới
├── webhook_handler.py             # Webhook cũ
└── webhook_handler_refactored.py  # Webhook mới
```

### Sau (Đơn Giản)

```
app/routes/
├── payment_unified.py    # ✅ Tất cả payment routes
└── webhook_unified.py    # ✅ Tất cả webhook handlers
```

## Cách Sử Dụng

### 1. Import trong `__init__.py`

```python
# app/__init__.py
from app.routes.payment_unified import payment_bp
from app.routes.webhook_unified import webhook_bp

app.register_blueprint(payment_bp)
app.register_blueprint(webhook_bp)
```

### 2. URL Patterns

**Web Routes:**

```
/payment/checkout/123
/payment/status/456
/payment/success/456
```

**API Routes:**

```
/payment/api/create
/payment/api/456/status
/payment/api/list
```

**Webhook Routes:**

```
/webhook/payos
/webhook/test
/webhook/health
```

### 3. Services Usage

Tất cả routes đều sử dụng services:

```python
# Tạo payment
result = payment_service.create_payment(booking_id, user_id)

# Validate booking
validation = payment_validation_service.validate_booking_for_payment(booking_id, user_id)

# Gửi thông báo
notification = payment_notification_service.send_payment_success_notification(payment)
```

## Migration Guide

### 1. Thay Thế Imports

**Trước:**

```python
from app.routes.payment import payment_bp
from app.routes.payment_api import payment_api
from app.routes.webhook_handler import webhook_bp
```

**Sau:**

```python
from app.routes.payment_unified import payment_bp
from app.routes.webhook_unified import webhook_bp
```

### 2. Cập Nhật Blueprint Registration

**Trước:**

```python
app.register_blueprint(payment_bp)
app.register_blueprint(payment_api)
app.register_blueprint(webhook_bp)
```

**Sau:**

```python
app.register_blueprint(payment_bp)  # payment_unified.py
app.register_blueprint(webhook_bp)  # webhook_unified.py
```

### 3. Xóa File Cũ

```bash
# Xóa các file không cần thiết
rm app/routes/payment.py
rm app/routes/payment_api.py
rm app/routes/webhook_handler.py
```

## Testing

### 1. Test Web Routes

```bash
curl http://localhost:5000/payment/checkout/123
```

### 2. Test API Routes

```bash
curl -X POST http://localhost:5000/payment/api/create \
  -H "Content-Type: application/json" \
  -d '{"booking_id": 123}'
```

### 3. Test Webhook Routes

```bash
curl -X POST http://localhost:5000/webhook/payos \
  -H "Content-Type: application/json" \
  -d '{"orderCode": "123", "status": "PAID"}'
```

## Kết Luận

Cấu trúc mới giúp:

- **Giảm complexity**: Từ 6 file xuống 2 file
- **Tăng maintainability**: Dễ bảo trì và debug
- **Cải thiện organization**: Cấu trúc rõ ràng và logic
- **Giữ nguyên functionality**: Không mất tính năng nào
- **Dễ migration**: Thay đổi tối thiểu

Hệ thống giờ đây đơn giản, rõ ràng và dễ quản lý hơn rất nhiều so với cấu trúc cũ.
