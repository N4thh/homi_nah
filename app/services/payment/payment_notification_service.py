"""
Payment Notification Service - Xử lý thông báo cho thanh toán
"""

from typing import Dict, Any, Optional
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.models.models import db, Payment, Booking, Owner, Renter
from app.utils.notification_service import notification_service


class PaymentNotificationService:
    """Service xử lý thông báo cho thanh toán"""
    
    def __init__(self):
        pass
    
    def send_payment_created_notification(self, payment: Payment) -> Dict[str, Any]:
        """
        Gửi thông báo khi tạo payment
        """
        try:
            # Gửi email cho renter
            email_result = self._send_payment_created_email(payment)
            
            # Gửi thông báo cho owner
            owner_notification = self._send_payment_created_notification_to_owner(payment)
            
            return {
                "success": True,
                "email_sent": email_result.get("success", False),
                "owner_notification_sent": owner_notification.get("success", False),
                "message": "Thông báo đã được gửi"
            }
            
        except Exception as e:
            return {"success": False, "error": f"Lỗi gửi thông báo: {str(e)}"}
    
    def send_payment_success_notification(self, payment: Payment) -> Dict[str, Any]:
        """
        Gửi thông báo khi payment thành công
        """
        try:
            # Gửi email xác nhận cho renter
            email_result = notification_service.send_payment_success_email(payment)
            
            # Gửi thông báo cho owner
            owner_result = notification_service.send_payment_success_notification_to_owner(payment)
            
            return {
                "success": True,
                "email_sent": email_result,
                "owner_notification_sent": owner_result,
                "message": "Thông báo thanh toán thành công đã được gửi"
            }
            
        except Exception as e:
            return {"success": False, "error": f"Lỗi gửi thông báo thành công: {str(e)}"}
    
    def send_payment_failed_notification(self, payment: Payment, reason: str = "Thanh toán thất bại") -> Dict[str, Any]:
        """
        Gửi thông báo khi payment thất bại
        """
        try:
            # Gửi email thông báo thất bại cho renter
            email_result = self._send_payment_failed_email(payment, reason)
            
            # Gửi thông báo cho owner
            owner_notification = self._send_payment_failed_notification_to_owner(payment, reason)
            
            return {
                "success": True,
                "email_sent": email_result.get("success", False),
                "owner_notification_sent": owner_notification.get("success", False),
                "message": "Thông báo thanh toán thất bại đã được gửi"
            }
            
        except Exception as e:
            return {"success": False, "error": f"Lỗi gửi thông báo thất bại: {str(e)}"}
    
    def send_payment_cancelled_notification(self, payment: Payment, reason: str = "Thanh toán bị hủy") -> Dict[str, Any]:
        """
        Gửi thông báo khi payment bị hủy
        """
        try:
            # Gửi email thông báo hủy cho renter
            email_result = self._send_payment_cancelled_email(payment, reason)
            
            # Gửi thông báo cho owner
            owner_notification = self._send_payment_cancelled_notification_to_owner(payment, reason)
            
            return {
                "success": True,
                "email_sent": email_result.get("success", False),
                "owner_notification_sent": owner_notification.get("success", False),
                "message": "Thông báo hủy thanh toán đã được gửi"
            }
            
        except Exception as e:
            return {"success": False, "error": f"Lỗi gửi thông báo hủy: {str(e)}"}
    
    def send_payment_reminder_notification(self, payment: Payment) -> Dict[str, Any]:
        """
        Gửi thông báo nhắc nhở thanh toán
        """
        try:
            # Kiểm tra payment còn pending không
            if payment.status != 'pending':
                return {"success": False, "error": "Payment không còn pending"}
            
            # Gửi email nhắc nhở cho renter
            email_result = self._send_payment_reminder_email(payment)
            
            return {
                "success": True,
                "email_sent": email_result.get("success", False),
                "message": "Thông báo nhắc nhở đã được gửi"
            }
            
        except Exception as e:
            return {"success": False, "error": f"Lỗi gửi thông báo nhắc nhở: {str(e)}"}
    
    def _send_payment_created_email(self, payment: Payment) -> Dict[str, Any]:
        """
        Gửi email thông báo tạo payment cho renter
        """
        try:
            if not payment.customer_email:
                return {"success": False, "error": "Không có email khách hàng"}
            
            # Tạo nội dung email
            subject = f"Thông báo tạo thanh toán - Booking #{payment.booking_id}"
            
            html_content = f"""
            <html>
            <body>
                <h2>Thông báo tạo thanh toán</h2>
                <p>Xin chào {payment.customer_name},</p>
                <p>Chúng tôi đã tạo thanh toán cho booking của bạn với thông tin sau:</p>
                
                <table border="1" style="border-collapse: collapse; width: 100%;">
                    <tr>
                        <td><strong>Mã thanh toán:</strong></td>
                        <td>{payment.payment_code}</td>
                    </tr>
                    <tr>
                        <td><strong>Mã đơn hàng:</strong></td>
                        <td>{payment.order_code}</td>
                    </tr>
                    <tr>
                        <td><strong>Số tiền:</strong></td>
                        <td>{payment.amount:,.0f} VND</td>
                    </tr>
                    <tr>
                        <td><strong>Mô tả:</strong></td>
                        <td>{payment.description}</td>
                    </tr>
                    <tr>
                        <td><strong>Thời gian tạo:</strong></td>
                        <td>{payment.created_at.strftime('%d/%m/%Y %H:%M') if payment.created_at else 'N/A'}</td>
                    </tr>
                </table>
                
                <p>Vui lòng thực hiện thanh toán trong thời gian sớm nhất.</p>
                <p>Trân trọng,<br>Đội ngũ Homi</p>
            </body>
            </html>
            """
            
            # Gửi email
            result = notification_service.send_email(
                to_email=payment.customer_email,
                subject=subject,
                html_content=html_content
            )
            
            return {"success": result, "message": "Email đã được gửi"}
            
        except Exception as e:
            return {"success": False, "error": f"Lỗi gửi email: {str(e)}"}
    
    def _send_payment_created_notification_to_owner(self, payment: Payment) -> Dict[str, Any]:
        """
        Gửi thông báo tạo payment cho owner
        """
        try:
            owner = Owner.query.get(payment.owner_id)
            if not owner or not owner.email:
                return {"success": False, "error": "Không có email chủ nhà"}
            
            # Tạo nội dung thông báo
            subject = f"Thông báo có thanh toán mới - Booking #{payment.booking_id}"
            
            html_content = f"""
            <html>
            <body>
                <h2>Thông báo có thanh toán mới</h2>
                <p>Xin chào {owner.full_name},</p>
                <p>Có một thanh toán mới được tạo cho nhà của bạn:</p>
                
                <table border="1" style="border-collapse: collapse; width: 100%;">
                    <tr>
                        <td><strong>Mã thanh toán:</strong></td>
                        <td>{payment.payment_code}</td>
                    </tr>
                    <tr>
                        <td><strong>Khách hàng:</strong></td>
                        <td>{payment.customer_name}</td>
                    </tr>
                    <tr>
                        <td><strong>Số tiền:</strong></td>
                        <td>{payment.amount:,.0f} VND</td>
                    </tr>
                    <tr>
                        <td><strong>Thời gian tạo:</strong></td>
                        <td>{payment.created_at.strftime('%d/%m/%Y %H:%M') if payment.created_at else 'N/A'}</td>
                    </tr>
                </table>
                
                <p>Vui lòng theo dõi trạng thái thanh toán.</p>
                <p>Trân trọng,<br>Đội ngũ Homi</p>
            </body>
            </html>
            """
            
            # Gửi email
            result = notification_service.send_email(
                to_email=owner.email,
                subject=subject,
                html_content=html_content
            )
            
            return {"success": result, "message": "Thông báo đã được gửi cho chủ nhà"}
            
        except Exception as e:
            return {"success": False, "error": f"Lỗi gửi thông báo cho chủ nhà: {str(e)}"}
    
    def _send_payment_failed_email(self, payment: Payment, reason: str) -> Dict[str, Any]:
        """
        Gửi email thông báo payment thất bại cho renter
        """
        try:
            if not payment.customer_email:
                return {"success": False, "error": "Không có email khách hàng"}
            
            subject = f"Thông báo thanh toán thất bại - Booking #{payment.booking_id}"
            
            html_content = f"""
            <html>
            <body>
                <h2>Thông báo thanh toán thất bại</h2>
                <p>Xin chào {payment.customer_name},</p>
                <p>Thanh toán của bạn đã thất bại với lý do: <strong>{reason}</strong></p>
                
                <table border="1" style="border-collapse: collapse; width: 100%;">
                    <tr>
                        <td><strong>Mã thanh toán:</strong></td>
                        <td>{payment.payment_code}</td>
                    </tr>
                    <tr>
                        <td><strong>Số tiền:</strong></td>
                        <td>{payment.amount:,.0f} VND</td>
                    </tr>
                    <tr>
                        <td><strong>Thời gian:</strong></td>
                        <td>{payment.created_at.strftime('%d/%m/%Y %H:%M') if payment.created_at else 'N/A'}</td>
                    </tr>
                </table>
                
                <p>Vui lòng thử lại hoặc liên hệ hỗ trợ nếu cần thiết.</p>
                <p>Trân trọng,<br>Đội ngũ Homi</p>
            </body>
            </html>
            """
            
            result = notification_service.send_email(
                to_email=payment.customer_email,
                subject=subject,
                html_content=html_content
            )
            
            return {"success": result, "message": "Email thông báo thất bại đã được gửi"}
            
        except Exception as e:
            return {"success": False, "error": f"Lỗi gửi email thất bại: {str(e)}"}
    
    def _send_payment_failed_notification_to_owner(self, payment: Payment, reason: str) -> Dict[str, Any]:
        """
        Gửi thông báo payment thất bại cho owner
        """
        try:
            owner = Owner.query.get(payment.owner_id)
            if not owner or not owner.email:
                return {"success": False, "error": "Không có email chủ nhà"}
            
            subject = f"Thông báo thanh toán thất bại - Booking #{payment.booking_id}"
            
            html_content = f"""
            <html>
            <body>
                <h2>Thông báo thanh toán thất bại</h2>
                <p>Xin chào {owner.full_name},</p>
                <p>Thanh toán cho nhà của bạn đã thất bại:</p>
                
                <table border="1" style="border-collapse: collapse; width: 100%;">
                    <tr>
                        <td><strong>Mã thanh toán:</strong></td>
                        <td>{payment.payment_code}</td>
                    </tr>
                    <tr>
                        <td><strong>Khách hàng:</strong></td>
                        <td>{payment.customer_name}</td>
                    </tr>
                    <tr>
                        <td><strong>Số tiền:</strong></td>
                        <td>{payment.amount:,.0f} VND</td>
                    </tr>
                    <tr>
                        <td><strong>Lý do:</strong></td>
                        <td>{reason}</td>
                    </tr>
                </table>
                
                <p>Trân trọng,<br>Đội ngũ Homi</p>
            </body>
            </html>
            """
            
            result = notification_service.send_email(
                to_email=owner.email,
                subject=subject,
                html_content=html_content
            )
            
            return {"success": result, "message": "Thông báo thất bại đã được gửi cho chủ nhà"}
            
        except Exception as e:
            return {"success": False, "error": f"Lỗi gửi thông báo thất bại cho chủ nhà: {str(e)}"}
    
    def _send_payment_cancelled_email(self, payment: Payment, reason: str) -> Dict[str, Any]:
        """
        Gửi email thông báo payment bị hủy cho renter
        """
        try:
            if not payment.customer_email:
                return {"success": False, "error": "Không có email khách hàng"}
            
            subject = f"Thông báo hủy thanh toán - Booking #{payment.booking_id}"
            
            html_content = f"""
            <html>
            <body>
                <h2>Thông báo hủy thanh toán</h2>
                <p>Xin chào {payment.customer_name},</p>
                <p>Thanh toán của bạn đã bị hủy với lý do: <strong>{reason}</strong></p>
                
                <table border="1" style="border-collapse: collapse; width: 100%;">
                    <tr>
                        <td><strong>Mã thanh toán:</strong></td>
                        <td>{payment.payment_code}</td>
                    </tr>
                    <tr>
                        <td><strong>Số tiền:</strong></td>
                        <td>{payment.amount:,.0f} VND</td>
                    </tr>
                    <tr>
                        <td><strong>Thời gian:</strong></td>
                        <td>{payment.created_at.strftime('%d/%m/%Y %H:%M') if payment.created_at else 'N/A'}</td>
                    </tr>
                </table>
                
                <p>Nếu bạn muốn tiếp tục đặt phòng, vui lòng tạo booking mới.</p>
                <p>Trân trọng,<br>Đội ngũ Homi</p>
            </body>
            </html>
            """
            
            result = notification_service.send_email(
                to_email=payment.customer_email,
                subject=subject,
                html_content=html_content
            )
            
            return {"success": result, "message": "Email thông báo hủy đã được gửi"}
            
        except Exception as e:
            return {"success": False, "error": f"Lỗi gửi email hủy: {str(e)}"}
    
    def _send_payment_cancelled_notification_to_owner(self, payment: Payment, reason: str) -> Dict[str, Any]:
        """
        Gửi thông báo payment bị hủy cho owner
        """
        try:
            owner = Owner.query.get(payment.owner_id)
            if not owner or not owner.email:
                return {"success": False, "error": "Không có email chủ nhà"}
            
            subject = f"Thông báo hủy thanh toán - Booking #{payment.booking_id}"
            
            html_content = f"""
            <html>
            <body>
                <h2>Thông báo hủy thanh toán</h2>
                <p>Xin chào {owner.full_name},</p>
                <p>Thanh toán cho nhà của bạn đã bị hủy:</p>
                
                <table border="1" style="border-collapse: collapse; width: 100%;">
                    <tr>
                        <td><strong>Mã thanh toán:</strong></td>
                        <td>{payment.payment_code}</td>
                    </tr>
                    <tr>
                        <td><strong>Khách hàng:</strong></td>
                        <td>{payment.customer_name}</td>
                    </tr>
                    <tr>
                        <td><strong>Số tiền:</strong></td>
                        <td>{payment.amount:,.0f} VND</td>
                    </tr>
                    <tr>
                        <td><strong>Lý do:</strong></td>
                        <td>{reason}</td>
                    </tr>
                </table>
                
                <p>Trân trọng,<br>Đội ngũ Homi</p>
            </body>
            </html>
            """
            
            result = notification_service.send_email(
                to_email=owner.email,
                subject=subject,
                html_content=html_content
            )
            
            return {"success": result, "message": "Thông báo hủy đã được gửi cho chủ nhà"}
            
        except Exception as e:
            return {"success": False, "error": f"Lỗi gửi thông báo hủy cho chủ nhà: {str(e)}"}
    
    def _send_payment_reminder_email(self, payment: Payment) -> Dict[str, Any]:
        """
        Gửi email nhắc nhở thanh toán cho renter
        """
        try:
            if not payment.customer_email:
                return {"success": False, "error": "Không có email khách hàng"}
            
            subject = f"Nhắc nhở thanh toán - Booking #{payment.booking_id}"
            
            html_content = f"""
            <html>
            <body>
                <h2>Nhắc nhở thanh toán</h2>
                <p>Xin chào {payment.customer_name},</p>
                <p>Bạn có một thanh toán đang chờ xử lý:</p>
                
                <table border="1" style="border-collapse: collapse; width: 100%;">
                    <tr>
                        <td><strong>Mã thanh toán:</strong></td>
                        <td>{payment.payment_code}</td>
                    </tr>
                    <tr>
                        <td><strong>Số tiền:</strong></td>
                        <td>{payment.amount:,.0f} VND</td>
                    </tr>
                    <tr>
                        <td><strong>Thời gian tạo:</strong></td>
                        <td>{payment.created_at.strftime('%d/%m/%Y %H:%M') if payment.created_at else 'N/A'}</td>
                    </tr>
                </table>
                
                <p>Vui lòng thực hiện thanh toán sớm để đảm bảo booking của bạn được xác nhận.</p>
                <p>Trân trọng,<br>Đội ngũ Homi</p>
            </body>
            </html>
            """
            
            result = notification_service.send_email(
                to_email=payment.customer_email,
                subject=subject,
                html_content=html_content
            )
            
            return {"success": result, "message": "Email nhắc nhở đã được gửi"}
            
        except Exception as e:
            return {"success": False, "error": f"Lỗi gửi email nhắc nhở: {str(e)}"}


# Tạo instance global
payment_notification_service = PaymentNotificationService()
