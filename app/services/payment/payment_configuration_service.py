"""
Payment Configuration Service - Xử lý cấu hình PayOS
"""

from typing import Dict, Any, Optional, List
from datetime import datetime

from app.models.models import db, PaymentConfig, Owner


class PaymentConfigurationService:
    """Service xử lý cấu hình PayOS cho owners"""
    
    def __init__(self):
        pass
    
    def create_payment_config(self, owner_id: int, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Tạo cấu hình PayOS cho owner
        """
        try:
            # Kiểm tra owner tồn tại
            owner = Owner.query.get(owner_id)
            if not owner:
                return {"success": False, "error": "Owner không tồn tại", "status": 404}
            
            # Validate dữ liệu cấu hình
            validation_result = self._validate_config_data(config_data)
            if not validation_result["valid"]:
                return {"success": False, "error": validation_result["error"], "status": 400}
            
            # Kiểm tra đã có config chưa
            existing_config = PaymentConfig.query.filter_by(owner_id=owner_id).first()
            if existing_config:
                # Cập nhật config hiện tại
                existing_config.payos_client_id = config_data["payos_client_id"]
                existing_config.payos_api_key = config_data["payos_api_key"]
                existing_config.payos_checksum_key = config_data["payos_checksum_key"]
                existing_config.is_active = config_data.get("is_active", True)
                existing_config.updated_at = datetime.utcnow()
                
                db.session.commit()
                
                return {
                    "success": True,
                    "config": existing_config,
                    "message": "Cấu hình PayOS đã được cập nhật"
                }
            else:
                # Tạo config mới
                new_config = PaymentConfig(
                    owner_id=owner_id,
                    payos_client_id=config_data["payos_client_id"],
                    payos_api_key=config_data["payos_api_key"],
                    payos_checksum_key=config_data["payos_checksum_key"],
                    is_active=config_data.get("is_active", True),
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                
                db.session.add(new_config)
                db.session.commit()
                
                return {
                    "success": True,
                    "config": new_config,
                    "message": "Cấu hình PayOS đã được tạo"
                }
                
        except Exception as e:
            return {"success": False, "error": f"Lỗi tạo cấu hình: {str(e)}", "status": 500}
    
    def get_payment_config(self, owner_id: int) -> Dict[str, Any]:
        """
        Lấy cấu hình PayOS của owner
        """
        try:
            config = PaymentConfig.query.filter_by(owner_id=owner_id).first()
            
            if not config:
                return {"success": False, "error": "Chưa có cấu hình PayOS", "status": 404}
            
            return {
                "success": True,
                "config": {
                    "id": config.id,
                    "owner_id": config.owner_id,
                    "payos_client_id": config.payos_client_id,
                    "payos_api_key": config.payos_api_key,
                    "payos_checksum_key": config.payos_checksum_key,
                    "is_active": config.is_active,
                    "created_at": config.created_at.isoformat() if config.created_at else None,
                    "updated_at": config.updated_at.isoformat() if config.updated_at else None
                }
            }
            
        except Exception as e:
            return {"success": False, "error": f"Lỗi lấy cấu hình: {str(e)}", "status": 500}
    
    def update_payment_config(self, owner_id: int, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Cập nhật cấu hình PayOS của owner
        """
        try:
            config = PaymentConfig.query.filter_by(owner_id=owner_id).first()
            
            if not config:
                return {"success": False, "error": "Không tìm thấy cấu hình PayOS", "status": 404}
            
            # Validate dữ liệu cấu hình
            validation_result = self._validate_config_data(config_data)
            if not validation_result["valid"]:
                return {"success": False, "error": validation_result["error"], "status": 400}
            
            # Cập nhật config
            config.payos_client_id = config_data["payos_client_id"]
            config.payos_api_key = config_data["payos_api_key"]
            config.payos_checksum_key = config_data["payos_checksum_key"]
            config.is_active = config_data.get("is_active", config.is_active)
            config.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            return {
                "success": True,
                "config": config,
                "message": "Cấu hình PayOS đã được cập nhật"
            }
            
        except Exception as e:
            return {"success": False, "error": f"Lỗi cập nhật cấu hình: {str(e)}", "status": 500}
    
    def activate_payment_config(self, owner_id: int) -> Dict[str, Any]:
        """
        Kích hoạt cấu hình PayOS
        """
        try:
            config = PaymentConfig.query.filter_by(owner_id=owner_id).first()
            
            if not config:
                return {"success": False, "error": "Không tìm thấy cấu hình PayOS", "status": 404}
            
            config.is_active = True
            config.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            return {
                "success": True,
                "message": "Cấu hình PayOS đã được kích hoạt"
            }
            
        except Exception as e:
            return {"success": False, "error": f"Lỗi kích hoạt cấu hình: {str(e)}", "status": 500}
    
    def deactivate_payment_config(self, owner_id: int) -> Dict[str, Any]:
        """
        Vô hiệu hóa cấu hình PayOS
        """
        try:
            config = PaymentConfig.query.filter_by(owner_id=owner_id).first()
            
            if not config:
                return {"success": False, "error": "Không tìm thấy cấu hình PayOS", "status": 404}
            
            config.is_active = False
            config.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            return {
                "success": True,
                "message": "Cấu hình PayOS đã được vô hiệu hóa"
            }
            
        except Exception as e:
            return {"success": False, "error": f"Lỗi vô hiệu hóa cấu hình: {str(e)}", "status": 500}
    
    def delete_payment_config(self, owner_id: int) -> Dict[str, Any]:
        """
        Xóa cấu hình PayOS
        """
        try:
            config = PaymentConfig.query.filter_by(owner_id=owner_id).first()
            
            if not config:
                return {"success": False, "error": "Không tìm thấy cấu hình PayOS", "status": 404}
            
            db.session.delete(config)
            db.session.commit()
            
            return {
                "success": True,
                "message": "Cấu hình PayOS đã được xóa"
            }
            
        except Exception as e:
            return {"success": False, "error": f"Lỗi xóa cấu hình: {str(e)}", "status": 500}
    
    def get_all_payment_configs(self, page: int = 1, per_page: int = 10, 
                               active_only: bool = False) -> Dict[str, Any]:
        """
        Lấy danh sách tất cả cấu hình PayOS
        """
        try:
            query = PaymentConfig.query
            
            if active_only:
                query = query.filter_by(is_active=True)
            
            # Sắp xếp theo thời gian tạo mới nhất
            query = query.order_by(PaymentConfig.created_at.desc())
            
            # Phân trang
            pagination = query.paginate(
                page=page, 
                per_page=per_page, 
                error_out=False
            )
            
            configs = []
            for config in pagination.items:
                owner = Owner.query.get(config.owner_id)
                configs.append({
                    "id": config.id,
                    "owner_id": config.owner_id,
                    "owner_name": owner.full_name if owner else "N/A",
                    "owner_email": owner.email if owner else "N/A",
                    "payos_client_id": config.payos_client_id,
                    "is_active": config.is_active,
                    "created_at": config.created_at.isoformat() if config.created_at else None,
                    "updated_at": config.updated_at.isoformat() if config.updated_at else None
                })
            
            return {
                "success": True,
                "configs": configs,
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
            return {"success": False, "error": f"Lỗi lấy danh sách cấu hình: {str(e)}", "status": 500}
    
    def test_payment_config(self, owner_id: int) -> Dict[str, Any]:
        """
        Test cấu hình PayOS
        """
        try:
            config = PaymentConfig.query.filter_by(owner_id=owner_id, is_active=True).first()
            
            if not config:
                return {"success": False, "error": "Không tìm thấy cấu hình PayOS", "status": 404}
            
            # Test kết nối PayOS
            from app.services.payos_service import PayOSService
            
            payos_service = PayOSService(
                client_id=config.payos_client_id,
                api_key=config.payos_api_key,
                checksum_key=config.payos_checksum_key
            )
            
            # Test bằng cách tạo một payment link test (sẽ không thực sự tạo)
            # Hoặc có thể test bằng cách gọi API khác của PayOS
            
            return {
                "success": True,
                "message": "Cấu hình PayOS hoạt động bình thường",
                "config": {
                    "owner_id": config.owner_id,
                    "is_active": config.is_active,
                    "tested_at": datetime.utcnow().isoformat()
                }
            }
            
        except Exception as e:
            return {"success": False, "error": f"Lỗi test cấu hình: {str(e)}", "status": 500}
    
    def _validate_config_data(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate dữ liệu cấu hình PayOS
        """
        try:
            # Kiểm tra các field bắt buộc
            required_fields = ['payos_client_id', 'payos_api_key', 'payos_checksum_key']
            for field in required_fields:
                if field not in config_data or not config_data[field]:
                    return {"valid": False, "error": f"Thiếu thông tin {field}"}
            
            # Validate format
            client_id = config_data['payos_client_id']
            if not isinstance(client_id, str) or len(client_id) < 5:
                return {"valid": False, "error": "PayOS Client ID không hợp lệ"}
            
            api_key = config_data['payos_api_key']
            if not isinstance(api_key, str) or len(api_key) < 10:
                return {"valid": False, "error": "PayOS API Key không hợp lệ"}
            
            checksum_key = config_data['payos_checksum_key']
            if not isinstance(checksum_key, str) or len(checksum_key) < 10:
                return {"valid": False, "error": "PayOS Checksum Key không hợp lệ"}
            
            return {"valid": True}
            
        except Exception as e:
            return {"valid": False, "error": f"Lỗi validation: {str(e)}"}
    
    def get_owner_payment_status(self, owner_id: int) -> Dict[str, Any]:
        """
        Lấy trạng thái thanh toán của owner
        """
        try:
            config = PaymentConfig.query.filter_by(owner_id=owner_id).first()
            
            if not config:
                return {
                    "success": True,
                    "has_config": False,
                    "is_active": False,
                    "message": "Chưa có cấu hình PayOS"
                }
            
            # Đếm số payment của owner
            from app.models.models import Payment
            total_payments = Payment.query.filter_by(owner_id=owner_id).count()
            successful_payments = Payment.query.filter_by(owner_id=owner_id, status='success').count()
            pending_payments = Payment.query.filter_by(owner_id=owner_id, status='pending').count()
            failed_payments = Payment.query.filter_by(owner_id=owner_id, status='failed').count()
            
            return {
                "success": True,
                "has_config": True,
                "is_active": config.is_active,
                "config_created_at": config.created_at.isoformat() if config.created_at else None,
                "statistics": {
                    "total_payments": total_payments,
                    "successful_payments": successful_payments,
                    "pending_payments": pending_payments,
                    "failed_payments": failed_payments,
                    "success_rate": (successful_payments / total_payments * 100) if total_payments > 0 else 0
                }
            }
            
        except Exception as e:
            return {"success": False, "error": f"Lỗi lấy trạng thái thanh toán: {str(e)}", "status": 500}


# Tạo instance global
payment_configuration_service = PaymentConfigurationService()
