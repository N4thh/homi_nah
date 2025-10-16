"""
Owner Home Service
Business logic for home management operations
"""

from app.models.models import db, Home, Booking, Review, Province, District, Ward, Rule, Amenity, HomeDeletionLog
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import os
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload
from sqlalchemy import func, or_


class OwnerHomeService:
    """Service for owner home management operations"""
    
    def get_owner_homes(self, owner_id: int) -> List[Home]:
        """Get all homes owned by a specific owner"""
        return Home.query.filter_by(owner_id=owner_id).options(
            joinedload(Home.images),
            joinedload(Home.rules),
            joinedload(Home.amenities)
        ).order_by(Home.created_at.desc()).all()
    
    def get_home_by_id(self, home_id: int, owner_id: int) -> Optional[Home]:
        """Get a specific home by ID, ensuring it belongs to the owner"""
        return Home.query.filter_by(id=home_id, owner_id=owner_id).options(
            joinedload(Home.images),
            joinedload(Home.rules),
            joinedload(Home.amenities)
        ).first()
    
    def create_home(self, owner_id: int, home_data: Dict) -> Dict:
        """Create a new home"""
        try:
            location = self._resolve_location(home_data)
            pricing = home_data.get('pricing', {})

            new_home = Home(
                owner_id=owner_id,
                title=home_data['title'],
                home_type=home_data.get('home_type') or home_data.get('property_type') or 'Nhà phố',
                accommodation_type=home_data.get('accommodation_type', 'entire_home'),
                description=home_data.get('description', ''),
                address=home_data.get('address') or self._build_address(home_data, location),
                city=home_data.get('city') or location.get('city', 'Chưa cập nhật'),
                district=home_data.get('district') or location.get('district', 'Chưa cập nhật'),
                home_number=home_data.get('home_number', home_data['title']),
                bed_count=home_data.get('bed_count', home_data.get('bedrooms', 1)),
                bathroom_count=home_data.get('bathroom_count', home_data.get('bathrooms', 1)),
                max_guests=home_data.get('max_guests', home_data.get('capacity', 1)),
                price_first_2_hours=pricing.get('price_first_2_hours'),
                price_per_additional_hour=pricing.get('price_per_additional_hour'),
                price_overnight=pricing.get('price_overnight'),
                price_daytime=pricing.get('price_daytime'),
                price_per_day=pricing.get('price_per_day'),
                price_per_hour=pricing.get('price_per_hour'),
                price_per_night=pricing.get('price_per_night'),
                is_active=home_data.get('is_active', True),
                floor_number=home_data.get('floor_number', 1)
            )

            if new_home.price_per_hour is None and new_home.price_first_2_hours is not None:
                new_home.price_per_hour = new_home.price_first_2_hours
            if new_home.price_per_night is None and new_home.price_per_day is not None:
                new_home.price_per_night = new_home.price_per_day

            db.session.add(new_home)
            db.session.flush()

            if 'amenities' in home_data:
                amenity_ids = self._convert_to_int_list(home_data['amenities'])
                if amenity_ids:
                    amenities = Amenity.query.filter(Amenity.id.in_(amenity_ids)).all()
                    new_home.amenities.extend(amenities)

            if 'rules' in home_data:
                rule_ids = self._convert_to_int_list(home_data['rules'])
                if rule_ids:
                    rules = Rule.query.filter(Rule.id.in_(rule_ids)).all()
                    new_home.rules.extend(rules)

            db.session.commit()

            return {
                'success': True,
                'message': 'Tạo nhà thành công!',
                'home_id': new_home.id
            }

        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'message': f'Lỗi khi tạo nhà: {str(e)}'
            }
    
    def update_home(self, home_id: int, owner_id: int, home_data: Dict) -> Dict:
        """Update an existing home"""
        try:
            home = self.get_home_by_id(home_id, owner_id)
            if not home:
                return {
                    'success': False,
                    'message': 'Không tìm thấy nhà'
                }
            
            location = self._resolve_location(home_data)
            pricing = home_data.get('pricing', {})

            home.title = home_data.get('title', home.title)
            home.home_type = home_data.get('home_type', home.home_type)
            if home_data.get('property_type') and not home_data.get('home_type'):
                home.home_type = home_data['property_type']
            home.accommodation_type = home_data.get('accommodation_type', home.accommodation_type)
            home.description = home_data.get('description', home.description)
            if 'address' in home_data or location:
                home.address = home_data.get('address') or self._build_address(home_data, location, fallback=home.address)
            home.city = home_data.get('city') or location.get('city', home.city)
            home.district = home_data.get('district') or location.get('district', home.district)
            home.home_number = home_data.get('home_number', home.home_number)
            home.bed_count = home_data.get('bed_count', home.bed_count)
            home.bathroom_count = home_data.get('bathroom_count', home.bathroom_count)
            home.max_guests = home_data.get('max_guests', home.max_guests)

            if pricing:
                if 'price_first_2_hours' in pricing:
                    home.price_first_2_hours = pricing.get('price_first_2_hours')
                if 'price_per_additional_hour' in pricing:
                    home.price_per_additional_hour = pricing.get('price_per_additional_hour')
                if 'price_overnight' in pricing:
                    home.price_overnight = pricing.get('price_overnight')
                if 'price_daytime' in pricing:
                    home.price_daytime = pricing.get('price_daytime')
                if 'price_per_day' in pricing:
                    home.price_per_day = pricing.get('price_per_day')
                if 'price_per_hour' in pricing:
                    home.price_per_hour = pricing.get('price_per_hour')
                elif pricing.get('price_first_2_hours') is not None:
                    home.price_per_hour = pricing.get('price_first_2_hours')
                if 'price_per_night' in pricing:
                    home.price_per_night = pricing.get('price_per_night')
                elif pricing.get('price_per_day') is not None:
                    home.price_per_night = pricing.get('price_per_day')

            # Update amenities
            if 'amenities' in home_data:
                home.amenities.clear()
                amenity_ids = self._convert_to_int_list(home_data['amenities'])
                if amenity_ids:
                    amenities = Amenity.query.filter(Amenity.id.in_(amenity_ids)).all()
                    home.amenities.extend(amenities)

            # Update rules
            if 'rules' in home_data:
                home.rules.clear()
                rule_ids = self._convert_to_int_list(home_data['rules'])
                if rule_ids:
                    rules = Rule.query.filter(Rule.id.in_(rule_ids)).all()
                    home.rules.extend(rules)
            
            db.session.commit()
            
            return {
                'success': True,
                'message': 'Cập nhật nhà thành công!'
            }
            
        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'message': f'Lỗi khi cập nhật nhà: {str(e)}'
            }
    
    def delete_home(self, home_id: int, owner_id: int, reason: str) -> Dict:
        """Delete a home with reason logging"""
        try:
            home = self.get_home_by_id(home_id, owner_id)
            if not home:
                return {
                    'success': False,
                    'message': 'Không tìm thấy nhà'
                }
            
            # Check if home has active bookings
            active_bookings = Booking.query.filter(
                Booking.home_id == home_id,
                Booking.status.in_(['confirmed', 'active'])
            ).count()
            
            if active_bookings > 0:
                return {
                    'success': False,
                    'message': 'Không thể xóa nhà có booking đang hoạt động'
                }
            
            # Log deletion reason
            deletion_log = HomeDeletionLog(
                home_id=home_id,
                owner_id=owner_id,
                reason=reason,
                deleted_at=datetime.now()
            )
            db.session.add(deletion_log)
            
            # Delete home images from filesystem
            for image in home.images:
                if image.image_path:
                    file_path = os.path.join('static', image.image_path)
                    if os.path.exists(file_path):
                        os.remove(file_path)
            
            # Delete home
            db.session.delete(home)
            db.session.commit()
            
            return {
                'success': True,
                'message': 'Xóa nhà thành công!'
            }
            
        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'message': f'Lỗi khi xóa nhà: {str(e)}'
            }
    
    def toggle_home_status(self, home_id: int, owner_id: int) -> Dict:
        """Toggle home active status"""
        try:
            home = self.get_home_by_id(home_id, owner_id)
            if not home:
                return {
                    'success': False,
                    'message': 'Không tìm thấy nhà'
                }
            
            home.is_active = not home.is_active
            db.session.commit()
            
            status_text = 'kích hoạt' if home.is_active else 'vô hiệu hóa'
            return {
                'success': True,
                'message': f'{status_text.capitalize()} nhà thành công!',
                'is_active': home.is_active
            }
            
        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'message': f'Lỗi khi thay đổi trạng thái nhà: {str(e)}'
            }
    
    def get_home_statistics(self, owner_id: int) -> Dict:
        """Get statistics for owner's homes"""
        try:
            # Get all homes owned by current user
            owner_homes = Home.query.filter_by(owner_id=owner_id).all()
            home_ids = [home.id for home in owner_homes]
            
            if not home_ids:
                return {
                    'total_profit': 0,
                    'total_hours': 0,
                    'total_bookings': 0,
                    'booking_rate': 0,
                    'common_type': 'N/A',
                    'average_rating': 0,
                    'hourly_revenue': 0,
                    'nightly_revenue': 0,
                    'top_homes': []
                }
            
            # Get all completed and confirmed bookings for owner's homes
            completed_bookings = Booking.query.filter(
                Booking.home_id.in_(home_ids),
                Booking.status.in_(['completed', 'confirmed'])
            ).all()
            
            # Calculate basic statistics
            total_bookings = len(completed_bookings)
            total_profit = sum(booking.total_price for booking in completed_bookings)
            total_hours = sum((b.end_time - b.start_time).total_seconds() / 3600 for b in completed_bookings)
            
            # Count booking types
            hourly_count = sum(1 for b in completed_bookings if b.booking_type == 'hourly')
            nightly_count = total_bookings - hourly_count
            
            # Calculate hourly and nightly revenue
            hourly_revenue = sum(b.total_price for b in completed_bookings if b.booking_type == 'hourly')
            nightly_revenue = sum(b.total_price for b in completed_bookings if b.booking_type == 'daily')
            
            # Calculate booking rate (bookings per home)
            booking_rate = total_bookings / len(owner_homes) if owner_homes else 0
            
            # Get most common property type
            property_types = [home.home_type for home in owner_homes if home.home_type]
            common_type = max(set(property_types), key=property_types.count) if property_types else 'N/A'
            
            # Calculate average rating
            reviews = Review.query.join(Booking).filter(
                Booking.home_id.in_(home_ids)
            ).all()
            average_rating = sum(review.rating for review in reviews) / len(reviews) if reviews else 0
            
            # Get top performing homes
            home_revenues = {}
            for booking in completed_bookings:
                if booking.home_id not in home_revenues:
                    home_revenues[booking.home_id] = 0
                home_revenues[booking.home_id] += booking.total_price
            
            top_homes = []
            for home_id, revenue in sorted(home_revenues.items(), key=lambda x: x[1], reverse=True)[:5]:
                home = next((h for h in owner_homes if h.id == home_id), None)
                if home:
                    top_homes.append({
                        'id': home.id,
                        'title': home.title,
                        'revenue': revenue
                    })
            
            return {
                'total_profit': total_profit,
                'total_hours': total_hours,
                'total_bookings': total_bookings,
                'booking_rate': booking_rate,
                'common_type': common_type,
                'average_rating': average_rating,
                'hourly_revenue': hourly_revenue,
                'nightly_revenue': nightly_revenue,
                'top_homes': top_homes
            }
            
        except Exception as e:
            return {
                'total_profit': 0,
                'total_hours': 0,
                'total_bookings': 0,
                'booking_rate': 0,
                'common_type': 'N/A',
                'average_rating': 0,
                'hourly_revenue': 0,
                'nightly_revenue': 0,
                'top_homes': []
            }

    # ---------------------------------------------------------------------
    # Helper methods
    # ---------------------------------------------------------------------

    def _resolve_location(self, home_data: Dict) -> Dict:
        province_code = home_data.get('province_code') or home_data.get('province')
        district_code = home_data.get('district_code') or home_data.get('district')
        ward_value = home_data.get('ward')

        details = {
            'city': 'Chưa cập nhật',
            'district': 'Chưa cập nhật',
            'ward': ward_value or 'Chưa cập nhật'
        }

        if not province_code:
            return details

        province = Province.query.filter_by(code=province_code).first()
        if province:
            details['city'] = province.name

            district = None
            if district_code:
                district = District.query.filter_by(code=district_code, province_id=province.id).first()
                if district:
                    details['district'] = district.name

            if ward_value and district:
                ward = Ward.query.filter(
                    Ward.district_id == district.id,
                    or_(Ward.name == ward_value, Ward.code == ward_value)
                ).first()
                if ward:
                    details['ward'] = ward.name
                else:
                    details['ward'] = ward_value

        return details

    def _build_address(self, home_data: Dict, location: Dict, fallback: Optional[str] = None) -> str:
        street = home_data.get('street') or home_data.get('address')
        ward_name = location.get('ward') if location else None
        if street and ward_name and ward_name != 'Chưa cập nhật':
            return f"{street}, {ward_name}"
        if street:
            return street
        if ward_name and ward_name != 'Chưa cập nhật':
            return ward_name
        return fallback or 'Chưa cập nhật'

    @staticmethod
    def _convert_to_int_list(values) -> List[int]:
        if values is None:
            return []
        result = []
        for value in values:
            try:
                result.append(int(value))
            except (TypeError, ValueError):
                continue
        return result


# Global instance
owner_home_service = OwnerHomeService()
