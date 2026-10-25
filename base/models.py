import uuid
from decimal import Decimal

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


class UUIDTimeStampedModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class User(AbstractUser):
    class Role(models.TextChoices):
        DRIVER = "DRIVER", "Driver"
        PARKING_MANAGER = "PARKING_MANAGER", "Parking Manager"
        SECURITY_STAFF = "SECURITY_STAFF", "Security Staff"
        ADMIN = "ADMIN", "Admin"

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=40, choices=Role.choices, default=Role.DRIVER)
    phone_number = models.CharField(max_length=20, blank=True)
    profile_image = models.ImageField(upload_to="users/profile_images/", blank=True, null=True)
    is_verified = models.BooleanField(default=False)

    def __str__(self):
        return self.get_full_name() or self.username


class ParkingLocation(UUIDTimeStampedModel):
    class LocationType(models.TextChoices):
        MALL = "MALL", "Shopping Mall"
        COLLEGE = "COLLEGE", "College"
        HOSPITAL = "HOSPITAL", "Hospital"
        AIRPORT = "AIRPORT", "Airport"
        OFFICE = "OFFICE", "Office"
        SMART_CITY = "SMART_CITY", "Smart City"
        OTHER = "OTHER", "Other"

    name = models.CharField(max_length=180)
    slug = models.SlugField(max_length=200, unique=True)
    location_type = models.CharField(max_length=30, choices=LocationType.choices, default=LocationType.OTHER)
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="managed_parking_locations",
    )
    address = models.TextField()
    city = models.CharField(max_length=120, db_index=True)
    state = models.CharField(max_length=120, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    opening_time = models.TimeField(null=True, blank=True)
    closing_time = models.TimeField(null=True, blank=True)
    is_24_hours = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        indexes = [models.Index(fields=["city", "is_active"])]

    def __str__(self):
        return self.name


class ParkingZone(UUIDTimeStampedModel):
    location = models.ForeignKey(ParkingLocation, on_delete=models.CASCADE, related_name="zones")
    name = models.CharField(max_length=120)
    floor_number = models.IntegerField(default=0)
    description = models.TextField(blank=True)
    map_image = models.ImageField(upload_to="parking/maps/", blank=True, null=True)

    class Meta:
        ordering = ["location", "floor_number", "name"]
        constraints = [
            models.UniqueConstraint(fields=["location", "name"], name="unique_zone_per_location")
        ]

    def __str__(self):
        return f"{self.location} - {self.name}"


class ParkingSlot(UUIDTimeStampedModel):
    class SlotType(models.TextChoices):
        CAR = "CAR", "Car"
        BIKE = "BIKE", "Bike"
        EV = "EV", "Electric Vehicle"
        DISABLED = "DISABLED", "Accessible"
        VIP = "VIP", "VIP"

    class Status(models.TextChoices):
        AVAILABLE = "AVAILABLE", "Available"
        OCCUPIED = "OCCUPIED", "Occupied"
        RESERVED = "RESERVED", "Reserved"
        MAINTENANCE = "MAINTENANCE", "Maintenance"
        BLOCKED = "BLOCKED", "Blocked"

    zone = models.ForeignKey(ParkingZone, on_delete=models.CASCADE, related_name="slots")
    slot_number = models.CharField(max_length=50)
    slot_type = models.CharField(max_length=20, choices=SlotType.choices, default=SlotType.CAR)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.AVAILABLE)
    hourly_rate = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("0.00"))
    has_ev_charger = models.BooleanField(default=False)
    map_x = models.PositiveIntegerField(null=True, blank=True)
    map_y = models.PositiveIntegerField(null=True, blank=True)
    last_status_changed_at = models.DateTimeField(default=timezone.now)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["zone", "slot_number"]
        constraints = [
            models.UniqueConstraint(fields=["zone", "slot_number"], name="unique_slot_per_zone")
        ]
        indexes = [
            models.Index(fields=["zone", "status"]),
            models.Index(fields=["slot_type", "status"]),
        ]

    def __str__(self):
        return f"{self.zone} - {self.slot_number}"


class Vehicle(UUIDTimeStampedModel):
    class VehicleType(models.TextChoices):
        CAR = "CAR", "Car"
        BIKE = "BIKE", "Bike"
        EV = "EV", "Electric Vehicle"
        OTHER = "OTHER", "Other"

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="vehicles")
    vehicle_number = models.CharField(max_length=30, unique=True)
    vehicle_type = models.CharField(max_length=20, choices=VehicleType.choices, default=VehicleType.CAR)
    brand = models.CharField(max_length=80, blank=True)
    model = models.CharField(max_length=80, blank=True)
    color = models.CharField(max_length=50, blank=True)
    is_default = models.BooleanField(default=False)

    def __str__(self):
        return self.vehicle_number


class Reservation(UUIDTimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        CONFIRMED = "CONFIRMED", "Confirmed"
        CHECKED_IN = "CHECKED_IN", "Checked In"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"
        NO_SHOW = "NO_SHOW", "No Show"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="parking_reservations")
    vehicle = models.ForeignKey(Vehicle, on_delete=models.SET_NULL, null=True, blank=True, related_name="reservations")
    slot = models.ForeignKey(ParkingSlot, on_delete=models.PROTECT, related_name="reservations")
    reservation_code = models.CharField(max_length=80, unique=True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    actual_check_in = models.DateTimeField(null=True, blank=True)
    actual_check_out = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    estimated_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    final_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    qr_code = models.ImageField(upload_to="parking/qr_codes/", blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["slot", "start_time", "end_time"]),
            models.Index(fields=["reservation_code"]),
        ]

    def __str__(self):
        return self.reservation_code


class OccupancyLog(UUIDTimeStampedModel):
    class Source(models.TextChoices):
        MANUAL = "MANUAL", "Manual"
        SENSOR = "SENSOR", "Sensor"
        RESERVATION = "RESERVATION", "Reservation"
        SECURITY_SCAN = "SECURITY_SCAN", "Security Scan"

    slot = models.ForeignKey(ParkingSlot, on_delete=models.CASCADE, related_name="occupancy_logs")
    reservation = models.ForeignKey(Reservation, on_delete=models.SET_NULL, null=True, blank=True, related_name="occupancy_logs")
    previous_status = models.CharField(max_length=20, choices=ParkingSlot.Status.choices)
    new_status = models.CharField(max_length=20, choices=ParkingSlot.Status.choices)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    source = models.CharField(max_length=30, choices=Source.choices, default=Source.MANUAL)
    note = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["slot", "created_at"])]

    def __str__(self):
        return f"{self.slot} {self.previous_status} -> {self.new_status}"


class SlotPrediction(UUIDTimeStampedModel):
    class Confidence(models.TextChoices):
        LOW = "LOW", "Low"
        MEDIUM = "MEDIUM", "Medium"
        HIGH = "HIGH", "High"

    slot = models.ForeignKey(ParkingSlot, on_delete=models.CASCADE, related_name="predictions")
    predicted_available_at = models.DateTimeField()
    confidence = models.CharField(max_length=20, choices=Confidence.choices, default=Confidence.MEDIUM)
    probability_percent = models.PositiveSmallIntegerField(default=50, validators=[MinValueValidator(0), MaxValueValidator(100)])
    based_on_logs_count = models.PositiveIntegerField(default=0)
    prediction_notes = models.TextField(blank=True)

    class Meta:
        ordering = ["predicted_available_at"]
        indexes = [
            models.Index(fields=["slot", "predicted_available_at"]),
            models.Index(fields=["confidence"]),
        ]

    def __str__(self):
        return f"{self.slot} predicted at {self.predicted_available_at}"


class Payment(UUIDTimeStampedModel):
    class Status(models.TextChoices):
        INITIATED = "INITIATED", "Initiated"
        SUCCESS = "SUCCESS", "Success"
        FAILED = "FAILED", "Failed"
        REFUNDED = "REFUNDED", "Refunded"

    reservation = models.OneToOneField(Reservation, on_delete=models.CASCADE, related_name="payment")
    provider = models.CharField(max_length=80, default="Razorpay")
    payment_id = models.CharField(max_length=160, blank=True, db_index=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.INITIATED)
    paid_at = models.DateTimeField(null=True, blank=True)
    gateway_response = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"Payment for {self.reservation}"


class ParkingReport(UUIDTimeStampedModel):
    class ReportType(models.TextChoices):
        OCCUPANCY = "OCCUPANCY", "Occupancy"
        REVENUE = "REVENUE", "Revenue"
        RESERVATION = "RESERVATION", "Reservation"
        PREDICTION = "PREDICTION", "Prediction"

    location = models.ForeignKey(ParkingLocation, on_delete=models.CASCADE, related_name="reports")
    generated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="parking_reports")
    report_type = models.CharField(max_length=30, choices=ReportType.choices)
    title = models.CharField(max_length=180)
    data = models.JSONField(default=dict, blank=True)
    report_file = models.FileField(upload_to="parking/reports/", blank=True, null=True)

    def __str__(self):
        return self.title


class Notification(UUIDTimeStampedModel):
    class Type(models.TextChoices):
        RESERVATION_CONFIRMED = "RESERVATION_CONFIRMED", "Reservation Confirmed"
        RESERVATION_REMINDER = "RESERVATION_REMINDER", "Reservation Reminder"
        CHECK_IN_SUCCESS = "CHECK_IN_SUCCESS", "Check-in Success"
        CHECK_OUT_SUCCESS = "CHECK_OUT_SUCCESS", "Check-out Success"
        SLOT_AVAILABLE = "SLOT_AVAILABLE", "Slot Available"
        PAYMENT_UPDATE = "PAYMENT_UPDATE", "Payment Update"

    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    notification_type = models.CharField(max_length=50, choices=Type.choices)
    reservation = models.ForeignKey(Reservation, on_delete=models.CASCADE, null=True, blank=True, related_name="notifications")
    title = models.CharField(max_length=180)
    message = models.TextField(blank=True)
    is_read = models.BooleanField(default=False)
    email_sent = models.BooleanField(default=False)
    sms_sent = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["recipient", "is_read"])]

    def mark_as_read(self):
        self.is_read = True
        self.read_at = timezone.now()
        self.save(update_fields=["is_read", "read_at", "updated_at"])

    def __str__(self):
        return self.title


class ActivityLog(UUIDTimeStampedModel):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="activity_logs")
    action = models.CharField(max_length=120, db_index=True)
    object_type = models.CharField(max_length=120, blank=True)
    object_id = models.CharField(max_length=120, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.action 
