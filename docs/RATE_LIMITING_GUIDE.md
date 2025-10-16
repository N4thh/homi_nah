# Rate Limiting Guide - PayOS

## Tổng quan

Hệ thống rate limiting đã được tích hợp để bảo vệ tất cả các PayOS endpoints khỏi việc bị spam hoặc tấn công DDoS. Rate limiting được cấu hình với giới hạn **100 request/giờ** cho mỗi user hoặc IP.

## Cấu hình Rate Limiting

### Giới hạn
- **100 requests per hour** - Tổng cộng 100 request/giờ
- **10 requests per minute** - Tối đa 10 request/phút để tránh spam
- **3 requests per 10 seconds** - Tối đa 3 request/10 giây cho các thao tác nhanh

### Chiến lược
- **Fixed Window** - Sử dụng cửa sổ thời gian cố định
- **Key Method** - Ưu tiên User ID nếu đã đăng nhập, fallback về IP address
- **Storage** - Sử dụng memory storage (có thể cấu hình Redis)

## Endpoints được bảo vệ

### Payment Routes (`/payment/`)
- `POST /payment/process_payment` - Tạo thanh toán
- `GET /payment/check-status/<payment_id>` - Kiểm tra trạng thái
- `GET /payment/refresh-status/<payment_id>` - Refresh trạng thái
- `GET /payment/get-qr/<payment_id>` - Lấy QR code

### Payment API Routes (`/api/payment/`)
- `POST /api/payment/create` - Tạo link thanh toán
- `GET /api/payment/<payment_id>/status` - Lấy trạng thái payment
- `POST /api/payment/webhook` - Webhook PayOS
- `POST /api/payment/<payment_id>/cancel` - Hủy payment
- `GET /api/payment/list` - Danh sách payment
- `POST /api/payment/<payment_id>/auto-cancel` - Tự động hủy

### Webhook Routes (`/webhook/`)
- `POST /webhook/payos` - Webhook PayOS chính

## API Rate Limit

### Kiểm tra trạng thái rate limit
```http
GET /api/rate-limit/status
Authorization: Bearer <token>
```

**Response:**
```json
{
  "success": true,
  "rate_limit": {
    "remaining": 95,
    "reset_time": 1640995200,
    "limit_reached": false,
    "user_key": "user:123:renter"
  }
}
```

### Lấy thông tin cấu hình
```http
GET /api/rate-limit/info
```

**Response:**
```json
{
  "success": true,
  "rate_limit_config": {
    "limits": [
      "100 requests per hour",
      "10 requests per minute", 
      "3 requests per 10 seconds"
    ],
    "strategy": "fixed-window",
    "key_method": "user_id_or_ip",
    "description": "Rate limiting áp dụng cho tất cả PayOS endpoints"
  }
}
```

## Response Headers

Khi rate limiting được áp dụng, các headers sau sẽ được thêm vào response:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640995200
Retry-After: 3600
```

## Xử lý Rate Limit Exceeded

Khi vượt quá giới hạn rate limit, server sẽ trả về:

**Status Code:** `429 Too Many Requests`

**Response:**
```json
{
  "error": "Rate limit exceeded",
  "message": "Bạn đã vượt quá giới hạn 100 request/giờ. Vui lòng thử lại sau.",
  "retry_after": 3600
}
```

## Cấu hình nâng cao

### Sử dụng Redis Storage
Để sử dụng Redis thay vì memory storage, set biến môi trường:

```bash
export REDIS_URL="redis://localhost:6379/0"
```

### Tùy chỉnh giới hạn
Chỉnh sửa trong `app/utils/rate_limiter.py`:

```python
payos_limits = [
    "100 per hour",  # Tổng cộng 100 request/giờ
    "10 per minute",  # Tối đa 10 request/phút
    "3 per 10 seconds"  # Tối đa 3 request/10 giây
]
```

## Monitoring và Debugging

### Logs
Rate limiting được log trong application logs:
```
[INFO] Rate limit applied for user:123:renter
[WARNING] Rate limit exceeded for user:123:renter
```

### Kiểm tra trạng thái
Sử dụng API endpoint `/api/rate-limit/status` để kiểm tra trạng thái hiện tại.

### Test Rate Limiting
Chạy script test:
```bash
python test_rate_limiting.py
```

## Lưu ý quan trọng

1. **Webhook PayOS**: Webhook từ PayOS cũng bị rate limit, cần đảm bảo PayOS không gửi quá nhiều webhook cùng lúc.

2. **User Experience**: Khi rate limit bị vượt quá, hiển thị thông báo rõ ràng cho user.

3. **Monitoring**: Theo dõi logs để phát hiện các pattern bất thường.

4. **Scaling**: Khi scale ứng dụng, cần sử dụng Redis storage để đồng bộ rate limit giữa các instances.

## Troubleshooting

### Rate limiter không hoạt động
1. Kiểm tra Flask-Limiter đã được cài đặt
2. Kiểm tra `init_rate_limiter()` được gọi trong `app.py`
3. Kiểm tra decorator `@payos_rate_limit` được áp dụng đúng

### False positive
1. Kiểm tra key generation logic
2. Kiểm tra timezone settings
3. Kiểm tra storage backend

### Performance issues
1. Sử dụng Redis thay vì memory storage
2. Tối ưu hóa key generation
3. Giảm frequency của rate limit checks
