# serializers.py
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta
import uuid

from .models import (
    User, ParkingLocation, ParkingZone, ParkingSlot, Vehicle,
    Reservation, OccupancyLog, SlotPrediction, Payment,
    ParkingReport, Notification, ActivityLog
)


# ==================== User Serializers ====================

class UserSerializer(serializers.ModelSerializer):
    """Basic user serializer"""
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'full_name',
            'role', 'phone_number', 'profile_image', 'is_verified', 'date_joined'
        ]
        read_only_fields = ['id', 'date_joined', 'is_verified']
    
    def get_full_name(self, obj):
        return obj.get_full_name()


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration"""
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    confirm_password = serializers.CharField(write_only=True, required=True)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'confirm_password', 'first_name', 'last_name', 'phone_number', 'role']
    
    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value
    
    def validate(self, attrs):
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Password fields didn't match."})
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('confirm_password')
        user = User.objects.create_user(**validated_data)
        return user


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user profile"""
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'phone_number', 'profile_image']


# ==================== Parking Location Serializers ====================

class ParkingLocationSerializer(serializers.ModelSerializer):
    """Serializer for parking locations"""
    manager_name = serializers.CharField(source='manager.get_full_name', read_only=True)
    zones_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ParkingLocation
        fields = [
            'id', 'name', 'slug', 'location_type', 'manager', 'manager_name',
            'address', 'city', 'state', 'latitude', 'longitude', 'opening_time',
            'closing_time', 'is_24_hours', 'is_active', 'zones_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_zones_count(self, obj):
        return obj.zones.count()


class ParkingZoneSerializer(serializers.ModelSerializer):
    """Serializer for parking zones"""
    location_name = serializers.CharField(source='location.name', read_only=True)
    slots_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ParkingZone
        fields = [
            'id', 'location', 'location_name', 'name', 'floor_number',
            'description', 'map_image', 'slots_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_slots_count(self, obj):
        return obj.slots.count()


class ParkingSlotSerializer(serializers.ModelSerializer):
    """Serializer for parking slots"""
    zone_name = serializers.CharField(source='zone.name', read_only=True)
    location_name = serializers.CharField(source='zone.location.name', read_only=True)
    is_available = serializers.SerializerMethodField()
    
    class Meta:
        model = ParkingSlot
        fields = [
            'id', 'zone', 'zone_name', 'location_name', 'slot_number', 'slot_type',
            'status', 'hourly_rate', 'has_ev_charger', 'map_x', 'map_y',
            'is_available', 'is_active', 'last_status_changed_at', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'last_status_changed_at', 'created_at', 'updated_at']
    
    def get_is_available(self, obj):
        return obj.status == ParkingSlot.Status.AVAILABLE


class AvailableSlotSerializer(serializers.Serializer):
    """Serializer for available slot search results"""
    slot = ParkingSlotSerializer()
    location = ParkingLocationSerializer()
    distance = serializers.FloatField(required=False)
    estimated_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)


# ==================== Vehicle Serializers ====================

class VehicleSerializer(serializers.ModelSerializer):
    """Serializer for vehicles"""
    owner_name = serializers.CharField(source='owner.get_full_name', read_only=True)
    
    class Meta:
        model = Vehicle
        fields = [
            'id', 'owner', 'owner_name', 'vehicle_number', 'vehicle_type',
            'brand', 'model', 'color', 'is_default', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'owner']
    
    def validate_vehicle_number(self, value):
        value = value.upper()
        if self.instance is None and Vehicle.objects.filter(vehicle_number=value).exists():
            raise serializers.ValidationError("A vehicle with this number already exists.")
        return value


# ==================== Reservation Serializers ====================

class ReservationSerializer(serializers.ModelSerializer):
    """Serializer for reservations"""
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    vehicle_number = serializers.CharField(source='vehicle.vehicle_number', read_only=True)
    slot_number = serializers.CharField(source='slot.slot_number', read_only=True)
    location_name = serializers.CharField(source='slot.zone.location.name', read_only=True)
    duration_hours = serializers.SerializerMethodField()
    is_active = serializers.SerializerMethodField()
    
    class Meta:
        model = Reservation
        fields = [
            'id', 'reservation_code', 'user', 'user_name', 'vehicle', 'vehicle_number',
            'slot', 'slot_number', 'location_name', 'start_time', 'end_time',
            'duration_hours', 'actual_check_in', 'actual_check_out', 'status',
            'estimated_amount', 'final_amount', 'qr_code', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'reservation_code', 'estimated_amount', 'final_amount',
            'qr_code', 'created_at', 'updated_at'
        ]
    
    def get_duration_hours(self, obj):
        if obj.start_time and obj.end_time:
            delta = obj.end_time - obj.start_time
            return round(delta.total_seconds() / 3600, 1)
        return None
    
    def get_is_active(self, obj):
        return obj.status not in [Reservation.Status.COMPLETED, Reservation.Status.CANCELLED, Reservation.Status.NO_SHOW]


class CreateReservationSerializer(serializers.ModelSerializer):
    """Serializer for creating a new reservation"""
    duration_hours = serializers.DecimalField(max_digits=5, decimal_places=1, min_value=0.5, max_value=72)
    
    class Meta:
        model = Reservation
        fields = ['vehicle', 'slot', 'start_time', 'duration_hours']
    
    def validate_slot(self, value):
        if value.status != ParkingSlot.Status.AVAILABLE:
            raise serializers.ValidationError(f"Slot is not available. Current status: {value.status}")
        if not value.is_active:
            raise serializers.ValidationError("This slot is not active.")
        return value
    
    def validate_start_time(self, value):
        if value < timezone.now():
            raise serializers.ValidationError("Start time cannot be in the past.")
        if value > timezone.now() + timedelta(days=30):
            raise serializers.ValidationError("Reservations can only be made up to 30 days in advance.")
        return value
    
    def validate(self, attrs):
        slot = attrs.get('slot')
        start_time = attrs.get('start_time')
        duration_hours = attrs.get('duration_hours')
        
        if slot and start_time and duration_hours:
            end_time = start_time + timedelta(hours=float(duration_hours))
            
            # Check for overlapping reservations
            overlapping = Reservation.objects.filter(
                slot=slot,
                status__in=[Reservation.Status.CONFIRMED, Reservation.Status.PENDING],
                start_time__lt=end_time,
                end_time__gt=start_time
            ).exists()
            
            if overlapping:
                raise serializers.ValidationError(
                    "This slot is already reserved for the selected time period."
                )
            
            attrs['end_time'] = end_time
            attrs['estimated_amount'] = slot.hourly_rate * Decimal(str(duration_hours))
        
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('duration_hours')
        user = self.context['request'].user
        validated_data['user'] = user
        validated_data['reservation_code'] = f"RES-{uuid.uuid4().hex[:8].upper()}"
        validated_data['status'] = Reservation.Status.CONFIRMED
        
        # Update slot status
        slot = validated_data['slot']
        slot.status = ParkingSlot.Status.RESERVED
        slot.save()
        
        return super().create(validated_data)


class UpdateReservationStatusSerializer(serializers.ModelSerializer):
    """Serializer for updating reservation status"""
    
    class Meta:
        model = Reservation
        fields = ['status']
    
    def validate_status(self, value):
        valid_transitions = {
            Reservation.Status.PENDING: [Reservation.Status.CONFIRMED, Reservation.Status.CANCELLED],
            Reservation.Status.CONFIRMED: [Reservation.Status.CHECKED_IN, Reservation.Status.CANCELLED],
            Reservation.Status.CHECKED_IN: [Reservation.Status.COMPLETED],
            Reservation.Status.COMPLETED: [],
            Reservation.Status.CANCELLED: [],
        }
        
        current_status = self.instance.status
        allowed = valid_transitions.get(current_status, [])
        
        if value not in allowed:
            raise serializers.ValidationError(
                f"Cannot transition from {current_status} to {value}."
            )
        
        return value
    
    def update(self, instance, validated_data):
        new_status = validated_data['status']
        old_status = instance.status
        now = timezone.now()
        
        # Handle status-specific logic
        if new_status == Reservation.Status.CHECKED_IN:
            validated_data['actual_check_in'] = now
            # Update slot status
            instance.slot.status = ParkingSlot.Status.OCCUPIED
            instance.slot.last_status_changed_at = now
            instance.slot.save()
        
        elif new_status == Reservation.Status.COMPLETED:
            validated_data['actual_check_out'] = now
            # Calculate final amount if not set
            if not instance.final_amount and instance.actual_check_in:
                hours_parked = (now - instance.actual_check_in).total_seconds() / 3600
                instance.final_amount = instance.slot.hourly_rate * Decimal(str(max(0.5, hours_parked)))
            # Free up the slot
            instance.slot.status = ParkingSlot.Status.AVAILABLE
            instance.slot.last_status_changed_at = now
            instance.slot.save()
        
        elif new_status == Reservation.Status.CANCELLED:
            # Free up the slot
            if instance.slot.status == ParkingSlot.Status.RESERVED:
                instance.slot.status = ParkingSlot.Status.AVAILABLE
                instance.slot.save()
        
        return super().update(instance, validated_data)


# ==================== Occupancy Log Serializers ====================

class OccupancyLogSerializer(serializers.ModelSerializer):
    """Serializer for occupancy logs"""
    slot_number = serializers.CharField(source='slot.slot_number', read_only=True)
    changed_by_name = serializers.CharField(source='changed_by.get_full_name', read_only=True)
    
    class Meta:
        model = OccupancyLog
        fields = [
            'id', 'slot', 'slot_number', 'reservation', 'previous_status',
            'new_status', 'changed_by', 'changed_by_name', 'source', 'note',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']


# ==================== Slot Prediction Serializers ====================

class SlotPredictionSerializer(serializers.ModelSerializer):
    """Serializer for slot availability predictions"""
    slot_number = serializers.CharField(source='slot.slot_number', read_only=True)
    
    class Meta:
        model = SlotPrediction
        fields = [
            'id', 'slot', 'slot_number', 'predicted_available_at',
            'confidence', 'probability_percent', 'based_on_logs_count',
            'prediction_notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


# ==================== Payment Serializers ====================

class PaymentSerializer(serializers.ModelSerializer):
    """Serializer for payments"""
    reservation_code = serializers.CharField(source='reservation.reservation_code', read_only=True)
    
    class Meta:
        model = Payment
        fields = [
            'id', 'reservation', 'reservation_code', 'provider', 'payment_id',
            'amount', 'status', 'paid_at', 'gateway_response', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'payment_id', 'status', 'paid_at', 'created_at', 'updated_at']


class InitiatePaymentSerializer(serializers.Serializer):
    """Serializer for initiating a payment"""
    reservation_id = serializers.UUIDField()
    provider = serializers.CharField(default='Razorpay')
    
    def validate_reservation_id(self, value):
        try:
            reservation = Reservation.objects.get(id=value)
            if reservation.status != Reservation.Status.CONFIRMED:
                raise serializers.ValidationError("Payment can only be initiated for confirmed reservations.")
            if hasattr(reservation, 'payment') and reservation.payment.status == Payment.Status.SUCCESS:
                raise serializers.ValidationError("Payment already completed for this reservation.")
            return value
        except Reservation.DoesNotExist:
            raise serializers.ValidationError("Reservation not found.")


# ==================== Report Serializers ====================

class ParkingReportSerializer(serializers.ModelSerializer):
    """Serializer for parking reports"""
    location_name = serializers.CharField(source='location.name', read_only=True)
    generated_by_name = serializers.CharField(source='generated_by.get_full_name', read_only=True)
    
    class Meta:
        model = ParkingReport
        fields = [
            'id', 'location', 'location_name', 'generated_by', 'generated_by_name',
            'report_type', 'title', 'data', 'report_file', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class GenerateReportSerializer(serializers.Serializer):
    """Serializer for generating reports"""
    location = serializers.UUIDField()
    report_type = serializers.ChoiceField(choices=ParkingReport.ReportType.choices)
    title = serializers.CharField(max_length=180)
    date_from = serializers.DateTimeField()
    date_to = serializers.DateTimeField()
    
    def validate(self, attrs):
        if attrs['date_from'] >= attrs['date_to']:
            raise serializers.ValidationError("End date must be after start date.")
        
        if attrs['date_to'] > timezone.now():
            raise serializers.ValidationError("End date cannot be in the future.")
        
        return attrs


# ==================== Notification Serializers ====================

class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for notifications"""
    recipient_name = serializers.CharField(source='recipient.get_full_name', read_only=True)
    
    class Meta:
        model = Notification
        fields = [
            'id', 'recipient', 'recipient_name', 'notification_type',
            'reservation', 'title', 'message', 'is_read', 'email_sent',
            'sms_sent', 'metadata', 'read_at', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'read_at']


class MarkNotificationReadSerializer(serializers.Serializer):
    """Serializer for marking notifications as read"""
    notification_ids = serializers.ListField(child=serializers.UUIDField())
    
    def validate_notification_ids(self, value):
        if not value:
            raise serializers.ValidationError("At least one notification ID is required.")
        return value


# ==================== Activity Log Serializers ====================

class ActivityLogSerializer(serializers.ModelSerializer):
    """Serializer for activity logs"""
    actor_name = serializers.CharField(source='actor.get_full_name', read_only=True)
    
    class Meta:
        model = ActivityLog
        fields = [
            'id', 'actor', 'actor_name', 'action', 'object_type',
            'object_id', 'ip_address', 'user_agent', 'metadata',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']


# ==================== Dashboard Statistics Serializers ====================

class DashboardStatisticsSerializer(serializers.Serializer):
    """Serializer for dashboard statistics"""
    total_slots = serializers.IntegerField()
    available_slots = serializers.IntegerField()
    occupied_slots = serializers.IntegerField()
    reserved_slots = serializers.IntegerField()
    occupancy_percentage = serializers.FloatField()
    today_reservations = serializers.IntegerField()
    today_revenue = serializers.DecimalField(max_digits=10, decimal_places=2)
    active_users = serializers.IntegerField()


class RevenueReportSerializer(serializers.Serializer):
    """Serializer for revenue reports"""
    period = serializers.CharField()
    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_reservations = serializers.IntegerField()
    average_revenue_per_reservation = serializers.DecimalField(max_digits=10, decimal_places=2)
    payment_success_rate = serializers.FloatField()


# ==================== Search & Filter Serializers ====================

class ParkingSearchSerializer(serializers.Serializer):
    """Serializer for searching parking slots"""
    location_id = serializers.UUIDField(required=False)
    city = serializers.CharField(required=False, max_length=120)
    slot_type = serializers.ChoiceField(choices=ParkingSlot.SlotType.choices, required=False)
    requires_ev_charger = serializers.BooleanField(required=False)
    start_time = serializers.DateTimeField(required=True)
    duration_hours = serializers.DecimalField(max_digits=5, decimal_places=1, min_value=0.5)
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=False)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=False)
    radius_km = serializers.IntegerField(min_value=1, max_value=50, required=False)
    
    def validate(self, attrs):
        if not attrs.get('location_id') and not attrs.get('city') and not (attrs.get('latitude') and attrs.get('longitude')):
            raise serializers.ValidationError(
                "Either location_id, city, or latitude/longitude must be provided."
            )
        
        start_time = attrs.get('start_time')
        if start_time and start_time < timezone.now():
            raise serializers.ValidationError({"start_time": "Start time cannot be in the past."})
        
        return attrs