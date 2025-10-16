"""
Payment Validation Service - Xử lý validation cho thanh toán
"""

from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import re

from app.models.models import db, Payment, Booking, Owner, Renter


class PaymentValidationService:
    """Service xử lý validation cho thanh toán"""
    
    def __init__(self):
        pass
    
    def validate_booking_for_payment(self, booking_id: int, user_id: int) -> Dict[str, Any]:
        """
        Validate booking trước khi tạo payment
        """
        try:
            # Kiểm tra booking tồn tại
            booking = Booking.query.get(booking_id)
            if not booking:
                return {"valid": False, "error": "Booking không tồn tại"}
            
            # Kiểm tra quyền truy cập
            if booking.renter_id != user_id:
                return {"valid": False, "error": "Không có quyền truy cập booking này"}
            
            # Kiểm tra trạng thái booking
            if booking.payment_status == 'paid':
                return {"valid": False, "error": "Đơn đặt phòng này đã được thanh toán"}
            
            if booking.status == 'cancelled':
                return {"valid": False, "error": "Đơn đặt nhà này đã bị hủy"}
            
            # Kiểm tra thời gian booking
            if booking.start_time < datetime.utcnow():
                return {"valid": False, "error": "Không thể thanh toán cho booking đã qua"}
            
            # Kiểm tra giá booking
            if not booking.total_price or booking.total_price <= 0:
                return {"valid": False, "error": "Giá booking không hợp lệ"}
            
            # Kiểm tra thông tin renter
            if not booking.renter.email_verified:
                return {"valid": False, "error": "Vui lòng xác thực email trước khi thanh toán"}
            
            return {"valid": True, "booking": booking}
            
        except Exception as e:
            return {"valid": False, "error": f"Lỗi validation booking: {str(e)}"}
    
    def validate_payment_data(self, payment_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate dữ liệu payment
        """
        try:
            # Kiểm tra các field bắt buộc
            required_fields = ['amount', 'currency', 'order_code', 'payment_code', 'description']
            for field in required_fields:
                if field not in payment_data or not payment_data[field]:
                    return {"valid": False, "error": f"Thiếu thông tin {field}"}
            
            # Validate amount
            amount = payment_data.get('amount')
            if not isinstance(amount, (int, float)) or amount <= 0:
                return {"valid": False, "error": "Số tiền không hợp lệ"}
            
            if amount < 1000:  # Tối thiểu 1000 VND
                return {"valid": False, "error": "Số tiền tối thiểu là 1,000 VND"}
            
            if amount > 100000000:  # Tối đa 100 triệu VND
                return {"valid": False, "error": "Số tiền tối đa là 100,000,000 VND"}
            
            # Validate currency
            currency = payment_data.get('currency')
            if currency != 'VND':
                return {"valid": False, "error": "Chỉ hỗ trợ thanh toán VND"}
            
            # Validate order_code
            order_code = payment_data.get('order_code')
            if not isinstance(order_code, (str, int)):
                return {"valid": False, "error": "Order code không hợp lệ"}
            
            # Validate payment_code
            payment_code = payment_data.get('payment_code')
            if not isinstance(payment_code, str) or len(payment_code) < 5:
                return {"valid": False, "error": "Payment code không hợp lệ"}
            
            # Validate description
            description = payment_data.get('description')
            if not isinstance(description, str) or len(description) < 3:
                return {"valid": False, "error": "Mô tả không hợp lệ"}
            
            if len(description) > 100:
                return {"valid": False, "error": "Mô tả quá dài (tối đa 100 ký tự)"}
            
            # Validate customer info nếu có
            customer_name = payment_data.get('customer_name')
            if customer_name and len(customer_name) > 100:
                return {"valid": False, "error": "Tên khách hàng quá dài"}
            
            customer_email = payment_data.get('customer_email')
            if customer_email and not self._validate_email(customer_email):
                return {"valid": False, "error": "Email không hợp lệ"}
            
            customer_phone = payment_data.get('customer_phone')
            if customer_phone and not self._validate_phone(customer_phone):
                return {"valid": False, "error": "Số điện thoại không hợp lệ"}
            
            return {"valid": True, "data": payment_data}
            
        except Exception as e:
            return {"valid": False, "error": f"Lỗi validation payment data: {str(e)}"}
    
    def validate_payment_modification(self, booking_id: int, user_id: int, 
                                    new_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate việc chỉnh sửa booking trước khi thanh toán
        """
        try:
            # Kiểm tra booking
            booking = Booking.query.get(booking_id)
            if not booking:
                return {"valid": False, "error": "Booking không tồn tại"}
            
            # Kiểm tra quyền
            if booking.renter_id != user_id:
                return {"valid": False, "error": "Không có quyền chỉnh sửa booking này"}
            
            # Kiểm tra trạng thái booking
            if booking.payment_status == 'paid':
                return {"valid": False, "error": "Không thể chỉnh sửa booking đã thanh toán"}
            
            if booking.status == 'cancelled':
                return {"valid": False, "error": "Không thể chỉnh sửa booking đã hủy"}
            
            # Validate booking type
            booking_type = new_data.get('booking_type')
            if booking_type not in ['daily', 'hourly']:
                return {"valid": False, "error": "Loại booking không hợp lệ"}
            
            # Validate thời gian
            start_date = new_data.get('start_date') or new_data.get('start_date_hourly')
            if not start_date:
                return {"valid": False, "error": "Thiếu ngày bắt đầu"}
            
            try:
                start_datetime = datetime.strptime(f"{start_date} 15:00", "%Y-%m-%d %H:%M")
            except ValueError:
                try:
                    start_time = new_data.get('start_time', '15:00')
                    start_datetime = datetime.strptime(f"{start_date} {start_time}", "%Y-%m-%d %H:%M")
                except ValueError:
                    return {"valid": False, "error": "Định dạng ngày/giờ không hợp lệ"}
            
            # Kiểm tra thời gian không được trong quá khứ
            if start_datetime < datetime.utcnow():
                return {"valid": False, "error": "Không thể đặt phòng trong quá khứ"}
            
            # Validate duration
            duration_str = new_data.get('duration_daily') or new_data.get('duration_hourly')
            if not duration_str:
                return {"valid": False, "error": "Thiếu thời gian thuê"}
            
            try:
                duration = int(duration_str)
            except ValueError:
                return {"valid": False, "error": "Thời gian thuê không hợp lệ"}
            
            if booking_type == 'hourly':
                if duration < 2:
                    return {"valid": False, "error": "Số giờ thuê tối thiểu là 2"}
                if duration > 24:
                    return {"valid": False, "error": "Số giờ thuê tối đa là 24"}
            else:  # daily
                if duration < 1:
                    return {"valid": False, "error": "Số đêm thuê tối thiểu là 1"}
                if duration > 30:
                    return {"valid": False, "error": "Số đêm thuê tối đa là 30"}
            
            return {
                "valid": True, 
                "booking": booking,
                "start_datetime": start_datetime,
                "duration": duration,
                "booking_type": booking_type
            }
            
        except Exception as e:
            return {"valid": False, "error": f"Lỗi validation modification: {str(e)}"}
    
    def validate_payment_config(self, owner_id: int) -> Dict[str, Any]:
        """
        Validate cấu hình PayOS của owner
        """
        try:
            from app.models.models import PaymentConfig
            
            config = PaymentConfig.query.filter_by(
                owner_id=owner_id, 
                is_active=True
            ).first()
            
            if not config:
                return {"valid": False, "error": "Chủ nhà chưa cấu hình PayOS"}
            
            # Kiểm tra các field bắt buộc
            if not config.payos_client_id:
                return {"valid": False, "error": "Thiếu PayOS Client ID"}
            
            if not config.payos_api_key:
                return {"valid": False, "error": "Thiếu PayOS API Key"}
            
            if not config.payos_checksum_key:
                return {"valid": False, "error": "Thiếu PayOS Checksum Key"}
            
            return {"valid": True, "config": config}
            
        except Exception as e:
            return {"valid": False, "error": f"Lỗi validation config: {str(e)}"}
    
    def _validate_email(self, email: str) -> bool:
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def _validate_phone(self, phone: str) -> bool:
        """Validate phone format"""
        # Loại bỏ khoảng trắng và ký tự đặc biệt
        clean_phone = re.sub(r'[^\d+]', '', phone)
        
        # Kiểm tra format số điện thoại Việt Nam
        if clean_phone.startswith('+84'):
            clean_phone = '0' + clean_phone[3:]
        
        if clean_phone.startswith('0') and len(clean_phone) == 10:
            return True
        
        return False
    
    def check_duplicate_payment(self, booking_id: int) -> Dict[str, Any]:
        """
        Kiểm tra payment trùng lặp
        """
        try:
            # Kiểm tra payment pending
            existing_payment = Payment.query.filter_by(
                booking_id=booking_id, 
                status='pending'
            ).first()
            
            if existing_payment:
                if existing_payment.checkout_url:
                    return {
                        "duplicate": True,
                        "payment_id": existing_payment.id,
                        "message": "Đã có giao dịch thanh toán đang chờ"
                    }
                else:
                    # Payment không có checkout_url, có thể xóa
                    return {
                        "duplicate": True,
                        "can_delete": True,
                        "payment_id": existing_payment.id,
                        "message": "Có payment cũ không hợp lệ"
                    }
            
            return {"duplicate": False}
            
        except Exception as e:
            return {"duplicate": False, "error": f"Lỗi kiểm tra duplicate: {str(e)}"}


# Tạo instance global
payment_validation_service = PaymentValidationService()
