# admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    User, ParkingLocation, ParkingZone, ParkingSlot, Vehicle,
    Reservation, OccupancyLog, SlotPrediction, Payment,
    ParkingReport, Notification, ActivityLog
)

class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'role', 'phone_number', 'is_verified', 'is_staff')
    list_filter = ('role', 'is_verified', 'is_staff', 'is_active')
    fieldsets = UserAdmin.fieldsets + (
        ('Parking Info', {'fields': ('role', 'phone_number', 'profile_image', 'is_verified')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Parking Info', {'fields': ('role', 'phone_number', 'profile_image')}),
    )

admin.site.register(User, CustomUserAdmin)

@admin.register(ParkingLocation)
class ParkingLocationAdmin(admin.ModelAdmin):
    list_display = ('name', 'city', 'location_type', 'manager', 'is_active')
    list_filter = ('location_type', 'is_active', 'city')
    search_fields = ('name', 'city', 'address')
    prepopulated_fields = {'slug': ('name',)}
    raw_id_fields = ('manager',)

@admin.register(ParkingZone)
class ParkingZoneAdmin(admin.ModelAdmin):
    list_display = ('name', 'location', 'floor_number')
    list_filter = ('location', 'floor_number')
    search_fields = ('name', 'location__name')
    raw_id_fields = ('location',)

@admin.register(ParkingSlot)
class ParkingSlotAdmin(admin.ModelAdmin):
    list_display = ('slot_number', 'zone', 'slot_type', 'status', 'hourly_rate', 'is_active')
    list_filter = ('slot_type', 'status', 'has_ev_charger', 'is_active')
    search_fields = ('slot_number', 'zone__name', 'zone__location__name')
    raw_id_fields = ('zone',)
    list_editable = ('status', 'hourly_rate')

@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ('vehicle_number', 'owner', 'vehicle_type', 'brand', 'is_default')
    list_filter = ('vehicle_type', 'is_default')
    search_fields = ('vehicle_number', 'owner__username', 'owner__email')
    raw_id_fields = ('owner',)

@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ('reservation_code', 'user', 'slot', 'start_time', 'end_time', 'status')
    list_filter = ('status', 'start_time')
    search_fields = ('reservation_code', 'user__username', 'slot__slot_number')
    raw_id_fields = ('user', 'vehicle', 'slot')
    readonly_fields = ('reservation_code', 'created_at', 'updated_at')
    list_editable = ('status',)

@admin.register(OccupancyLog)
class OccupancyLogAdmin(admin.ModelAdmin):
    list_display = ('slot', 'previous_status', 'new_status', 'source', 'created_at')
    list_filter = ('source', 'previous_status', 'new_status')
    raw_id_fields = ('slot', 'reservation', 'changed_by')
    readonly_fields = ('created_at',)

@admin.register(SlotPrediction)
class SlotPredictionAdmin(admin.ModelAdmin):
    list_display = ('slot', 'predicted_available_at', 'confidence', 'probability_percent')
    list_filter = ('confidence',)
    raw_id_fields = ('slot',)
    readonly_fields = ('created_at',)

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'reservation', 'amount', 'status', 'provider', 'paid_at')
    list_filter = ('status', 'provider')
    search_fields = ('payment_id', 'reservation__reservation_code')
    raw_id_fields = ('reservation',)
    readonly_fields = ('created_at',)

@admin.register(ParkingReport)
class ParkingReportAdmin(admin.ModelAdmin):
    list_display = ('title', 'location', 'report_type', 'generated_by', 'created_at')
    list_filter = ('report_type', 'location')
    search_fields = ('title', 'location__name')
    raw_id_fields = ('location', 'generated_by')

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'recipient', 'notification_type', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read', 'email_sent', 'sms_sent')
    search_fields = ('title', 'recipient__username', 'recipient__email')
    raw_id_fields = ('recipient', 'reservation')
    readonly_fields = ('created_at', 'read_at')

@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ('action', 'actor', 'object_type', 'created_at')
    list_filter = ('action', 'object_type')
    search_fields = ('action', 'actor__username', 'object_id')
    raw_id_fields = ('actor',)
    readonly_fields = ('created_at',)