"""
Availability API - Cung cấp API để kiểm tra availability và lấy time slots
"""

from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from app.models.models import Home, Booking, db
from app.utils.booking_locking import booking_locking_service
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

availability_api_bp = Blueprint('availability_api', __name__)


@availability_api_bp.route('/api/availability/check', methods=['POST'])
@login_required
def check_availability():
    """
    API kiểm tra availability của một home trong khoảng thời gian
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "Dữ liệu không hợp lệ"}), 400
        
        home_id = data.get('home_id')
        start_time_str = data.get('start_time')
        end_time_str = data.get('end_time')
        
        if not all([home_id, start_time_str, end_time_str]):
            return jsonify({"error": "Thiếu thông tin bắt buộc"}), 400
        
        # Parse datetime
        try:
            start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
            end_time = datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))
        except ValueError:
            return jsonify({"error": "Định dạng thời gian không hợp lệ"}), 400
        
        # Validate time range
        if start_time >= end_time:
            return jsonify({"error": "Thời gian kết thúc phải sau thời gian bắt đầu"}), 400
        
        # Check if home exists
        home = Home.query.get(home_id)
        if not home:
            return jsonify({"error": "Home không tồn tại"}), 404
        
        # Check availability
        is_available = booking_locking_service.is_room_available_atomic(
            home_id=home_id,
            start_time=start_time,
            end_time=end_time
        )
        
        return jsonify({
            "success": True,
            "available": is_available,
            "home_id": home_id,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error checking availability: {e}")
        return jsonify({
            "error": "Lỗi kiểm tra availability",
            "message": str(e)
        }), 500


@availability_api_bp.route('/api/availability/slots/<int:home_id>', methods=['GET'])
@login_required
def get_available_slots(home_id):
    """
    API lấy danh sách time slots có sẵn cho một home
    """
    try:
        # Get query parameters
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        duration_hours = request.args.get('duration_hours', 2, type=int)
        
        # Default to next 7 days if not specified
        if not start_date_str:
            start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            start_date = datetime.fromisoformat(start_date_str)
        
        if not end_date_str:
            end_date = start_date + timedelta(days=7)
        else:
            end_date = datetime.fromisoformat(end_date_str)
        
        # Validate parameters
        if start_date >= end_date:
            return jsonify({"error": "Ngày kết thúc phải sau ngày bắt đầu"}), 400
        
        if duration_hours <= 0:
            return jsonify({"error": "Thời lượng phải lớn hơn 0"}), 400
        
        # Check if home exists
        home = Home.query.get(home_id)
        if not home:
            return jsonify({"error": "Home không tồn tại"}), 404
        
        # Get available slots
        available_slots = booking_locking_service.get_available_time_slots(
            home_id=home_id,
            start_date=start_date,
            end_date=end_date,
            duration_hours=duration_hours
        )
        
        # Format slots for response
        slots = []
        for start_time, end_time in available_slots:
            slots.append({
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "duration_hours": duration_hours
            })
        
        return jsonify({
            "success": True,
            "home_id": home_id,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "duration_hours": duration_hours,
            "available_slots": slots,
            "total_slots": len(slots)
        })
        
    except Exception as e:
        logger.error(f"Error getting available slots: {e}")
        return jsonify({
            "error": "Lỗi lấy danh sách time slots",
            "message": str(e)
        }), 500


@availability_api_bp.route('/api/availability/conflicts/<int:home_id>', methods=['GET'])
@login_required
def get_conflicts(home_id):
    """
    API lấy danh sách bookings có thể conflict với time range
    """
    try:
        start_time_str = request.args.get('start_time')
        end_time_str = request.args.get('end_time')
        
        if not all([start_time_str, end_time_str]):
            return jsonify({"error": "Thiếu thông tin thời gian"}), 400
        
        # Parse datetime
        try:
            start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
            end_time = datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))
        except ValueError:
            return jsonify({"error": "Định dạng thời gian không hợp lệ"}), 400
        
        # Check if home exists
        home = Home.query.get(home_id)
        if not home:
            return jsonify({"error": "Home không tồn tại"}), 404
        
        # Get conflicting bookings
        conflicting_bookings = Booking.query.filter(
            Booking.home_id == home_id,
            Booking.status.in_(['pending', 'confirmed', 'active']),
            Booking.start_time < end_time,
            Booking.end_time > start_time
        ).all()
        
        # Format conflicts for response
        conflicts = []
        for booking in conflicting_bookings:
            conflicts.append({
                "booking_id": booking.id,
                "start_time": booking.start_time.isoformat(),
                "end_time": booking.end_time.isoformat(),
                "status": booking.status,
                "renter_name": booking.renter.full_name if booking.renter else "Unknown"
            })
        
        return jsonify({
            "success": True,
            "home_id": home_id,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "conflicts": conflicts,
            "total_conflicts": len(conflicts)
        })
        
    except Exception as e:
        logger.error(f"Error getting conflicts: {e}")
        return jsonify({
            "error": "Lỗi lấy danh sách conflicts",
            "message": str(e)
        }), 500


@availability_api_bp.route('/api/availability/stats/<int:home_id>', methods=['GET'])
@login_required
def get_availability_stats(home_id):
    """
    API lấy thống kê availability của một home
    """
    try:
        # Get query parameters
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        
        # Default to next 30 days if not specified
        if not start_date_str:
            start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            start_date = datetime.fromisoformat(start_date_str)
        
        if not end_date_str:
            end_date = start_date + timedelta(days=30)
        else:
            end_date = datetime.fromisoformat(end_date_str)
        
        # Check if home exists
        home = Home.query.get(home_id)
        if not home:
            return jsonify({"error": "Home không tồn tại"}), 404
        
        # Get booking statistics
        total_bookings = Booking.query.filter(
            Booking.home_id == home_id,
            Booking.start_time >= start_date,
            Booking.end_time <= end_date
        ).count()
        
        confirmed_bookings = Booking.query.filter(
            Booking.home_id == home_id,
            Booking.status.in_(['confirmed', 'active']),
            Booking.start_time >= start_date,
            Booking.end_time <= end_date
        ).count()
        
        pending_bookings = Booking.query.filter(
            Booking.home_id == home_id,
            Booking.status == 'pending',
            Booking.start_time >= start_date,
            Booking.end_time <= end_date
        ).count()
        
        # Calculate availability percentage
        total_hours = (end_date - start_date).total_seconds() / 3600
        booked_hours = db.session.query(
            db.func.sum(Booking.total_hours)
        ).filter(
            Booking.home_id == home_id,
            Booking.status.in_(['confirmed', 'active']),
            Booking.start_time >= start_date,
            Booking.end_time <= end_date
        ).scalar() or 0
        
        availability_percentage = max(0, (total_hours - booked_hours) / total_hours * 100) if total_hours > 0 else 100
        
        return jsonify({
            "success": True,
            "home_id": home_id,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "stats": {
                "total_bookings": total_bookings,
                "confirmed_bookings": confirmed_bookings,
                "pending_bookings": pending_bookings,
                "total_hours": total_hours,
                "booked_hours": booked_hours,
                "availability_percentage": round(availability_percentage, 2)
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting availability stats: {e}")
        return jsonify({
            "error": "Lỗi lấy thống kê availability",
            "message": str(e)
        }), 500
