# forms.py
from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal
from datetime import datetime, timedelta
import re

from .models import (
    User, ParkingLocation, ParkingZone, ParkingSlot, Vehicle,
    Reservation, OccupancyLog, SlotPrediction, Payment,
    ParkingReport, Notification, ActivityLog
)


# ==================== Custom Form Widgets & Validators ====================

class PhoneNumberValidator:
    """Validate phone number format"""
    def __call__(self, value):
        if value and not re.match(r'^\+?1?\d{9,15}$', value):
            raise ValidationError('Enter a valid phone number (9-15 digits, optional + prefix).')


class FutureDateTimeValidator:
    """Ensure datetime is in the future"""
    def __call__(self, value):
        if value and value <= timezone.now():
            raise ValidationError('Date and time must be in the future.')


# ==================== User Forms ====================

class UserRegistrationForm(forms.ModelForm):
    """Form for new user registration"""
    password = forms.CharField(widget=forms.PasswordInput, min_length=8)
    confirm_password = forms.CharField(widget=forms.PasswordInput)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'confirm_password', 
                  'first_name', 'last_name', 'phone_number', 'role']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'}),
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+1234567890'}),
            'role': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError('A user with this email already exists.')
        return email
    
    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number')
        if phone:
            validator = PhoneNumberValidator()
            validator(phone)
        return phone
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        
        if password and confirm_password and password != confirm_password:
            raise ValidationError('Passwords do not match.')
        
        return cleaned_data
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user


class UserProfileForm(forms.ModelForm):
    """Form for updating user profile"""
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'phone_number', 'profile_image']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'profile_image': forms.FileInput(attrs={'class': 'form-control'}),
        }


# ==================== Parking Location Forms ====================

class ParkingLocationForm(forms.ModelForm):
    """Form for creating/editing parking locations"""
    
    class Meta:
        model = ParkingLocation
        fields = [
            'name', 'slug', 'location_type', 'manager', 'address', 'city', 'state',
            'latitude', 'longitude', 'opening_time', 'closing_time', 'is_24_hours', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., City Center Mall'}),
            'slug': forms.TextInput(attrs={'class': 'form-control', 'help_text': 'URL-friendly name'}),
            'location_type': forms.Select(attrs={'class': 'form-select'}),
            'manager': forms.Select(attrs={'class': 'form-select'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'state': forms.TextInput(attrs={'class': 'form-control'}),
            'latitude': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001'}),
            'longitude': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001'}),
            'opening_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'closing_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'is_24_hours': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        is_24_hours = cleaned_data.get('is_24_hours')
        opening_time = cleaned_data.get('opening_time')
        closing_time = cleaned_data.get('closing_time')
        
        if not is_24_hours:
            if not opening_time or not closing_time:
                raise ValidationError('Opening and closing times are required when not 24/7.')
            if opening_time >= closing_time:
                raise ValidationError('Closing time must be after opening time.')
        
        return cleaned_data


class ParkingZoneForm(forms.ModelForm):
    """Form for creating/editing parking zones"""
    
    class Meta:
        model = ParkingZone
        fields = ['location', 'name', 'floor_number', 'description', 'map_image']
        widgets = {
            'location': forms.Select(attrs={'class': 'form-select'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., North Wing'}),
            'floor_number': forms.NumberInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'map_image': forms.FileInput(attrs={'class': 'form-control'}),
        }


# ==================== Parking Slot Forms ====================

class ParkingSlotForm(forms.ModelForm):
    """Form for creating/editing parking slots"""
    
    class Meta:
        model = ParkingSlot
        fields = [
            'zone', 'slot_number', 'slot_type', 'status', 'hourly_rate',
            'has_ev_charger', 'map_x', 'map_y', 'is_active'
        ]
        widgets = {
            'zone': forms.Select(attrs={'class': 'form-select'}),
            'slot_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., A-101'}),
            'slot_type': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'hourly_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.50', 'min': '0'}),
            'has_ev_charger': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'map_x': forms.NumberInput(attrs={'class': 'form-control'}),
            'map_y': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def clean_hourly_rate(self):
        rate = self.cleaned_data.get('hourly_rate')
        if rate and rate < 0:
            raise ValidationError('Hourly rate cannot be negative.')
        return rate


class BulkSlotCreationForm(forms.Form):
    """Form for creating multiple slots at once"""
    zone = forms.ModelChoiceField(queryset=ParkingZone.objects.all(), widget=forms.Select(attrs={'class': 'form-select'}))
    slot_prefix = forms.CharField(max_length=20, help_text='Prefix for slot numbers (e.g., "A-")')
    start_number = forms.IntegerField(min_value=1)
    end_number = forms.IntegerField(min_value=1)
    slot_type = forms.ChoiceField(choices=ParkingSlot.SlotType.choices, widget=forms.Select(attrs={'class': 'form-select'}))
    hourly_rate = forms.DecimalField(max_digits=8, decimal_places=2, min_value=0)
    has_ev_charger = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    
    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get('start_number')
        end = cleaned_data.get('end_number')
        
        if start and end and start > end:
            raise ValidationError('Start number must be less than or equal to end number.')
        
        return cleaned_data


# ==================== Vehicle Forms ====================

class VehicleForm(forms.ModelForm):
    """Form for registering vehicles"""
    
    class Meta:
        model = Vehicle
        fields = ['vehicle_number', 'vehicle_type', 'brand', 'model', 'color', 'is_default']
        widgets = {
            'vehicle_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., ABC-1234'}),
            'vehicle_type': forms.Select(attrs={'class': 'form-select'}),
            'brand': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Toyota'}),
            'model': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Camry'}),
            'color': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Red'}),
            'is_default': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def clean_vehicle_number(self):
        number = self.cleaned_data.get('vehicle_number').upper()
        if Vehicle.objects.filter(vehicle_number=number).exists():
            raise ValidationError('A vehicle with this number is already registered.')
        return number


# ==================== Reservation Forms ====================

class ReservationForm(forms.ModelForm):
    """Form for creating a parking reservation"""
    duration_hours = forms.DecimalField(
        max_digits=5, decimal_places=1, min_value=0.5, max_value=72,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5'}),
        help_text='Number of hours (minimum 0.5, maximum 72)'
    )
    
    class Meta:
        model = Reservation
        fields = ['vehicle', 'slot', 'start_time', 'duration_hours']
        widgets = {
            'vehicle': forms.Select(attrs={'class': 'form-select'}),
            'slot': forms.Select(attrs={'class': 'form-select'}),
            'start_time': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user:
            self.fields['vehicle'].queryset = Vehicle.objects.filter(owner=user)
        
        # Only show available slots
        self.fields['slot'].queryset = ParkingSlot.objects.filter(
            status=ParkingSlot.Status.AVAILABLE,
            is_active=True
        )
    
    def clean_start_time(self):
        start_time = self.cleaned_data.get('start_time')
        if start_time and start_time < timezone.now():
            raise ValidationError('Start time cannot be in the past.')
        
        if start_time and start_time > timezone.now() + timedelta(days=30):
            raise ValidationError('Reservations can only be made up to 30 days in advance.')
        
        return start_time
    
    def clean(self):
        cleaned_data = super().clean()
        slot = cleaned_data.get('slot')
        start_time = cleaned_data.get('start_time')
        duration_hours = cleaned_data.get('duration_hours')
        
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
                raise ValidationError('This slot is already reserved for the selected time period.')
            
            # Calculate estimated amount
            cleaned_data['end_time'] = end_time
            cleaned_data['estimated_amount'] = slot.hourly_rate * Decimal(str(duration_hours))
        
        return cleaned_data
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.end_time = self.cleaned_data['end_time']
        instance.estimated_amount = self.cleaned_data['estimated_amount']
        
        # Generate unique reservation code
        import uuid
        instance.reservation_code = f"RES-{uuid.uuid4().hex[:8].upper()}"
        
        if commit:
            instance.save()
            # Change slot status to reserved
            instance.slot.status = ParkingSlot.Status.RESERVED
            instance.slot.save()
        
        return instance


class ReservationCheckInForm(forms.Form):
    """Form for checking into a reservation"""
    reservation_code = forms.CharField(max_length=80, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter reservation code'}))
    
    def clean_reservation_code(self):
        code = self.cleaned_data.get('reservation_code')
        try:
            reservation = Reservation.objects.get(reservation_code=code)
            if reservation.status != Reservation.Status.CONFIRMED:
                raise ValidationError(f'Reservation status is {reservation.status}. Cannot check in.')
            if reservation.start_time > timezone.now():
                raise ValidationError('Check-in not yet available. Please wait until your reservation start time.')
            return code
        except Reservation.DoesNotExist:
            raise ValidationError('Invalid reservation code.')


class ReservationCheckOutForm(forms.Form):
    """Form for checking out and calculating final amount"""
    reservation_code = forms.CharField(max_length=80, widget=forms.TextInput(attrs={'class': 'form-control'}))
    
    def clean_reservation_code(self):
        code = self.cleaned_data.get('reservation_code')
        try:
            reservation = Reservation.objects.get(reservation_code=code)
            if reservation.status != Reservation.Status.CHECKED_IN:
                raise ValidationError(f'Cannot check out. Current status: {reservation.status}')
            return code
        except Reservation.DoesNotExist:
            raise ValidationError('Invalid reservation code.')


# ==================== Payment Forms ====================

class PaymentForm(forms.ModelForm):
    """Form for processing payments"""
    
    class Meta:
        model = Payment
        fields = ['provider']
        widgets = {
            'provider': forms.Select(attrs={'class': 'form-select'}),
        }


# ==================== Report Forms ====================

class ParkingReportForm(forms.ModelForm):
    """Form for generating parking reports"""
    date_from = forms.DateTimeField(widget=forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}))
    date_to = forms.DateTimeField(widget=forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}))
    
    class Meta:
        model = ParkingReport
        fields = ['location', 'report_type', 'title']
        widgets = {
            'location': forms.Select(attrs={'class': 'form-select'}),
            'report_type': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        date_from = cleaned_data.get('date_from')
        date_to = cleaned_data.get('date_to')
        
        if date_from and date_to and date_from >= date_to:
            raise ValidationError('End date must be after start date.')
        
        return cleaned_data


# ==================== Notification Forms ====================

class NotificationFilterForm(forms.Form):
    """Form for filtering notifications"""
    notification_type = forms.ChoiceField(
        choices=[('', 'All')] + list(Notification.Type.choices),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    is_read = forms.ChoiceField(
        choices=[('', 'All'), ('True', 'Read'), ('False', 'Unread')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    date_from = forms.DateTimeField(required=False, widget=forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}))
    date_to = forms.DateTimeField(required=False, widget=forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}))


# ==================== Search Forms ====================

class ParkingSlotSearchForm(forms.Form):
    """Form for searching available parking slots"""
    location = forms.ModelChoiceField(
        queryset=ParkingLocation.objects.filter(is_active=True),
        empty_label="Select Location",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    slot_type = forms.ChoiceField(
        choices=[('', 'Any')] + list(ParkingSlot.SlotType.choices),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    requires_ev_charger = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    start_time = forms.DateTimeField(widget=forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}))
    duration_hours = forms.DecimalField(min_value=0.5, max_value=72, initial=1, widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5'}))
    
    def clean_start_time(self):
        start_time = self.cleaned_data.get('start_time')
        if start_time and start_time < timezone.now():
            raise ValidationError('Start time cannot be in the past.')
        return start_time