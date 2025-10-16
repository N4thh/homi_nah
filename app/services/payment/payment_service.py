"""
Payment Service - Business logic cho thanh toán
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import uuid
import time
import json

from app.models.models import db, Payment, PaymentConfig, Booking, Owner, Renter
from app.services.payos_service import PayOSService
from app.utils.payment_validation_middleware import validate_payment_before_payos, PaymentValidationError
from app.utils.booking_locking import booking_locking_service, BookingConflictError, BookingLockingError
from app.utils.notification_service import notification_service


class PaymentService:
    """Service xử lý business logic cho thanh toán"""
    
    def __init__(self):
        self.payos_service = None
    
    def _get_payos_service(self, owner_id: int) -> PayOSService:
        """Lấy PayOS service cho owner"""
        payment_config = PaymentConfig.query.filter_by(
            owner_id=owner_id, 
            is_active=True
        ).first()
        
        if not payment_config:
            raise ValueError("Chủ nhà chưa cấu hình PayOS")
        
        return PayOSService(
            client_id=payment_config.payos_client_id,
            api_key=payment_config.payos_api_key,
            checksum_key=payment_config.payos_checksum_key
        )
    
    def create_payment(self, booking_id: int, user_id: int, 
                      return_url: str = None, cancel_url: str = None) -> Dict[str, Any]:
        """
        Tạo payment cho booking
        """
        try:
            # Kiểm tra booking
            booking = Booking.query.get(booking_id)
            if not booking:
                return {"error": "Booking không tồn tại", "status": 404}
            
            # Kiểm tra quyền truy cập
            if booking.renter_id != user_id:
                return {"error": "Không có quyền truy cập booking này", "status": 403}
            
            # Kiểm tra trạng thái booking
            if booking.payment_status == 'paid':
                return {"error": "Đơn đặt phòng này đã được thanh toán", "status": 400}
            
            if booking.status == 'cancelled':
                return {"error": "Đơn đặt nhà này đã bị hủy", "status": 400}
            
            # Kiểm tra payment pending
            existing_payment = Payment.query.filter_by(
                booking_id=booking.id, 
                status='pending'
            ).first()
            
            if existing_payment and existing_payment.checkout_url:
                return {
                    "success": True,
                    "payment_id": existing_payment.id,
                    "redirect_url": f"/payment/status/{existing_payment.id}",
                    "message": "Đã có giao dịch thanh toán đang chờ"
                }
            
            # Xóa payment cũ không có link
            if existing_payment and not existing_payment.checkout_url:
                db.session.delete(existing_payment)
                db.session.commit()
            
            # Tạo payment record với orderCode số nguyên
            order_code_int = int(f"{booking.id}{int(time.time() % 100000)}")
            
            # Tạo description ngắn gọn
            short_description = f"Booking #{booking.id}"
            
            # Chuẩn bị dữ liệu thanh toán để validate
            payment_data = {
                'amount': booking.total_price,
                'currency': 'VND',
                'order_code': str(order_code_int),
                'payment_code': f"PAY-{uuid.uuid4().hex[:8].upper()}",
                'description': short_description,
                'customer_name': booking.renter.full_name,
                'customer_email': booking.renter.email,
                'customer_phone': booking.renter.phone
            }
            
            # Validate dữ liệu thanh toán
            try:
                validated_data = validate_payment_before_payos(
                    payment_data=payment_data,
                    user_id=user_id,
                    booking_id=booking.id
                )
            except PaymentValidationError as e:
                return {"error": f"Lỗi validation thanh toán: {e.message}", "status": 400}
            
            # Tạo payment record
            payment = Payment(
                payment_code=validated_data['payment_code'],
                order_code=validated_data['order_code'],
                amount=validated_data['amount'],
                currency=validated_data['currency'],
                status='pending',
                description=validated_data['description'],
                customer_name=validated_data['customer_name'],
                customer_email=validated_data['customer_email'],
                customer_phone=validated_data['customer_phone'],
                booking_id=booking.id,
                owner_id=booking.home.owner_id,
                renter_id=user_id
            )
            db.session.add(payment)
            db.session.commit()
            
            # Tạo PayOS service
            payos_service = self._get_payos_service(booking.home.owner_id)
            
            # Tạo payment link
            payment_link_result = payos_service.create_payment_link(
                order_code=order_code_int,
                amount=int(payment.amount),
                description=payment.description,
                return_url=return_url or f"/payment/success/{payment.id}",
                cancel_url=cancel_url or f"/payment/cancelled/{payment.id}",
                items=[{
                    'name': f"Nha {booking.home.title}"[:25],
                    'quantity': 1,
                    'price': int(payment.amount)
                }]
            )
            
            if not payment_link_result.get('success'):
                error_msg = payment_link_result.get('message', 'Không thể tạo link thanh toán')
                # Xóa payment record nếu tạo link thất bại
                db.session.delete(payment)
                db.session.commit()
                return {"error": error_msg, "status": 500}
            
            # Cập nhật payment với thông tin PayOS
            checkout_url = payment_link_result.get('checkout_url') or payment_link_result.get('checkoutUrl')
            qr_code_data = payment_link_result.get('qrCode')
            account_number = payment_link_result.get('accountNumber')
            account_name = payment_link_result.get('accountName')
            bin_code = payment_link_result.get('bin')
            
            if not checkout_url:
                db.session.delete(payment)
                db.session.commit()
                return {"error": "PayOS không trả về checkout URL", "status": 500}
            
            payment.checkout_url = checkout_url
            payment.payos_transaction_id = payment_link_result.get('paymentLinkId')
            
            # Lưu thông tin QR và ngân hàng vào JSON
            payos_data = {
                'qr_code': qr_code_data,
                'account_number': account_number,
                'account_name': account_name,
                'bin': bin_code,
                'bank_name': payos_service.get_bank_name_from_bin(bin_code) if bin_code else None,
                'order_code': payment_link_result.get('orderCode'),
                'amount': payment_link_result.get('amount'),
                'status': payment_link_result.get('status'),
                'currency': payment_link_result.get('currency', 'VND')
            }
            
            # Lưu vào field payos_signature
            if hasattr(payment, 'payos_signature'):
                payment.payos_signature = json.dumps(payos_data, ensure_ascii=False)
            
            db.session.commit()
            
            return {
                "success": True,
                "payment_id": payment.id,
                "payment_code": payment.payment_code,
                "checkout_url": checkout_url,
                "redirect_url": f"/payment/status/{payment.id}",
                "payos_data": payos_data
            }
            
        except Exception as e:
            return {"error": f"Lỗi xử lý thanh toán: {str(e)}", "status": 500}
    
    def get_payment_status(self, payment_id: int, user_id: int) -> Dict[str, Any]:
        """
        Lấy trạng thái payment
        """
        try:
            payment = Payment.query.get(payment_id)
            if not payment:
                return {"error": "Payment không tồn tại", "status": 404}
            
            # Kiểm tra quyền truy cập
            if payment.renter_id != user_id:
                return {"error": "Không có quyền truy cập", "status": 403}
            
            # Parse PayOS data từ JSON
            payos_data = {}
            if hasattr(payment, 'payos_signature') and payment.payos_signature:
                try:
                    payos_data = json.loads(payment.payos_signature)
                except:
                    payos_data = {}
            
            return {
                "success": True,
                "payment": {
                    "id": payment.id,
                    "payment_code": payment.payment_code,
                    "order_code": payment.order_code,
                    "amount": payment.amount,
                    "status": payment.status,
                    "status_text": payment.get_payment_status_text(payment.status),
                    "payment_method": payment.payment_method,
                    "created_at": payment.created_at.isoformat() if payment.created_at else None,
                    "paid_at": payment.paid_at.isoformat() if payment.paid_at else None,
                    "description": payment.description,
                    "checkout_url": payment.checkout_url,
                    "qr_code": payos_data.get('qr_code'),
                    "account_info": {
                        "account_number": payos_data.get('account_number'),
                        "account_name": payos_data.get('account_name'),
                        "bank_name": payos_data.get('bank_name')
                    }
                }
            }
            
        except Exception as e:
            return {"error": f"Lỗi lấy trạng thái payment: {str(e)}", "status": 500}
    
    def refresh_payment_status(self, payment_id: int, user_id: int) -> Dict[str, Any]:
        """
        Refresh trạng thái payment từ PayOS
        """
        try:
            payment = Payment.query.get(payment_id)
            if not payment:
                return {"error": "Payment không tồn tại", "status": 404}
            
            # Kiểm tra quyền truy cập
            if payment.renter_id != user_id:
                return {"error": "Không có quyền truy cập", "status": 403}
            
            # Nếu đã thành công, trả về luôn
            if payment.status == 'success':
                return {
                    "success": True,
                    "status": "success",
                    "message": "Payment completed successfully",
                    "payment_status": payment.status,
                    "redirect": f"/payment/success/{payment.id}"
                }
            elif payment.status == 'failed':
                return {
                    "success": True,
                    "status": "failed",
                    "message": "Payment failed",
                    "payment_status": payment.status,
                    "redirect": f"/payment/failed/{payment.id}"
                }
            elif payment.status == 'cancelled':
                return {
                    "success": True,
                    "status": "cancelled",
                    "message": "Payment cancelled",
                    "payment_status": payment.status,
                    "redirect": f"/payment/cancelled/{payment.id}"
                }
            
            # Nếu vẫn pending, kiểm tra từ PayOS API
            try:
                payos_service = self._get_payos_service(payment.owner_id)
                
                # Lấy thông tin từ PayOS
                order_code = int(payment.order_code)
                payment_info = payos_service.get_payment_info(order_code)
                
                if payment_info.get('success'):
                    data = payment_info.get('data')
                    payos_status = getattr(data, 'status', '') if data else ''
                    
                    # Cập nhật trạng thái payment nếu có thay đổi
                    if payos_service.is_payment_successful(payos_status) and payment.status == 'pending':
                        payment.mark_as_successful()
                        payment.booking.payment_status = 'paid'
                        payment.booking.payment_date = datetime.utcnow()
                        payment.booking.status = 'confirmed'
                        db.session.commit()
                        
                        return {
                            "success": True,
                            "status": "success",
                            "message": "Payment completed successfully",
                            "payment_status": payment.status,
                            "redirect": f"/payment/success/{payment.id}"
                        }
                    elif payos_service.is_payment_failed(payos_status) and payment.status == 'pending':
                        payment.mark_as_failed('Payment failed on PayOS')
                        db.session.commit()
                        
                        return {
                            "success": True,
                            "status": "failed",
                            "message": "Payment failed",
                            "payment_status": payment.status,
                            "redirect": f"/payment/failed/{payment.id}"
                        }
                    else:
                        return {
                            "success": True,
                            "status": "pending",
                            "message": "Payment still pending",
                            "payment_status": payment.status
                        }
                else:
                    return {
                        "success": True,
                        "status": "pending",
                        "message": "Could not check payment status from PayOS, assuming pending",
                        "payment_status": payment.status
                    }
                    
            except Exception as e:
                return {
                    "success": True,
                    "status": "pending",
                    "message": f"Error checking status, assuming pending: {str(e)}",
                    "payment_status": payment.status
                }
                
        except Exception as e:
            return {"error": f"Lỗi refresh trạng thái payment: {str(e)}", "status": 500}
    
    def cancel_payment(self, payment_id: int, user_id: int, reason: str = "Hủy bởi người dùng") -> Dict[str, Any]:
        """
        Hủy payment
        """
        try:
            payment = Payment.query.get(payment_id)
            if not payment:
                return {"error": "Payment không tồn tại", "status": 404}
            
            # Kiểm tra quyền truy cập
            if payment.renter_id != user_id:
                return {"error": "Không có quyền truy cập", "status": 403}
            
            # Chỉ cho phép hủy payment đang pending
            if payment.status != 'pending':
                return {"error": "Chỉ có thể hủy payment đang chờ thanh toán", "status": 400}
            
            # Hủy payment trên PayOS nếu có transaction_id
            if payment.payos_transaction_id:
                try:
                    payos_service = self._get_payos_service(payment.owner_id)
                    cancel_response = payos_service.cancel_payment(
                        payment.payos_transaction_id,
                        reason
                    )
                    
                    if cancel_response.get('error'):
                        # Log warning nhưng vẫn tiếp tục hủy trong database
                        pass
                except Exception as e:
                    # Log warning nhưng vẫn tiếp tục hủy trong database
                    pass
            
            # Cập nhật trạng thái payment
            payment.mark_as_cancelled(reason)
            db.session.commit()
            
            return {
                "success": True,
                "message": "Payment đã được hủy thành công",
                "payment_id": payment.id,
                "status": payment.status
            }
            
        except Exception as e:
            return {"error": f"Lỗi hủy payment: {str(e)}", "status": 500}
    
    def process_payment_success(self, payment_id: int, user_id: int) -> Dict[str, Any]:
        """
        Xử lý payment thành công
        """
        try:
            payment = Payment.query.get(payment_id)
            if not payment:
                return {"error": "Payment không tồn tại", "status": 404}
            
            # Kiểm tra quyền truy cập
            if payment.renter_id != user_id:
                return {"error": "Không có quyền truy cập", "status": 403}
            
            # Cập nhật trạng thái nếu chưa được cập nhật
            if payment.status == 'pending':
                payment.mark_as_successful()
                payment.booking.payment_status = 'paid'
                payment.booking.payment_date = datetime.utcnow()
                payment.booking.payment_method = payment.payment_method or 'PayOS'
                payment.booking.status = 'confirmed'
                db.session.commit()
            
            # Gửi email nếu payment thành công và có email
            if payment.status in ['success', 'completed', 'paid'] and payment.customer_email:
                try:
                    # Gửi email xác nhận cho renter
                    notification_service.send_payment_success_email(payment)
                    
                    # Gửi thông báo cho owner
                    notification_service.send_payment_success_notification_to_owner(payment)
                    
                except Exception as e:
                    # Log error nhưng không fail toàn bộ process
                    pass
            
            return {
                "success": True,
                "payment": payment,
                "booking": payment.booking,
                "message": "Payment processed successfully"
            }
            
        except Exception as e:
            return {"error": f"Lỗi xử lý payment success: {str(e)}", "status": 500}
    
    def get_payment_list(self, user_id: int, user_type: str, 
                        page: int = 1, per_page: int = 10, 
                        status: str = None) -> Dict[str, Any]:
        """
        Lấy danh sách payment của user
        """
        try:
            # Xây dựng query
            if user_type == 'renter':
                query = Payment.query.filter_by(renter_id=user_id)
            elif user_type == 'owner':
                query = Payment.query.filter_by(owner_id=user_id)
            else:
                return {"error": "Không có quyền truy cập", "status": 403}
            
            # Lọc theo status nếu có
            if status:
                query = query.filter_by(status=status)
            
            # Sắp xếp theo thời gian tạo mới nhất
            query = query.order_by(Payment.created_at.desc())
            
            # Phân trang
            pagination = query.paginate(
                page=page, 
                per_page=per_page, 
                error_out=False
            )
            
            payments = []
            for payment in pagination.items:
                payments.append({
                    "id": payment.id,
                    "payment_code": payment.payment_code,
                    "order_code": payment.order_code,
                    "amount": payment.amount,
                    "status": payment.status,
                    "status_text": payment.get_payment_status_text(payment.status),
                    "payment_method": payment.payment_method,
                    "created_at": payment.created_at.isoformat() if payment.created_at else None,
                    "paid_at": payment.paid_at.isoformat() if payment.paid_at else None,
                    "description": payment.description,
                    "booking_id": payment.booking_id
                })
            
            return {
                "success": True,
                "payments": payments,
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total": pagination.total,
                    "pages": pagination.pages,
                    "has_next": pagination.has_next,
                    "has_prev": pagination.has_prev
                }
            }
            
        except Exception as e:
            return {"error": f"Lỗi lấy danh sách payment: {str(e)}", "status": 500}


# Tạo instance global
payment_service = PaymentService()
