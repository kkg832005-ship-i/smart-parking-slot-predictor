# base/views.py - Complete fixed version
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.contrib.auth.views import PasswordChangeView
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView, 
    TemplateView, FormView, View
)
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.db.models import Q, Count, Sum
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponse
from decimal import Decimal
from datetime import datetime, timedelta
import csv

# Import your models
from .models import (
    User, ParkingLocation, ParkingZone, ParkingSlot, Vehicle,
    Reservation, OccupancyLog, Payment, Notification, ActivityLog
)

# Import your forms
from .forms import (
    UserRegistrationForm, UserProfileForm, ParkingLocationForm,
    ParkingZoneForm, ParkingSlotForm, BulkSlotCreationForm,
    VehicleForm, ReservationForm, ReservationCheckInForm,
    ReservationCheckOutForm, ParkingSlotSearchForm
)


# ========== Helper Functions ==========

def get_client_ip(request):
    """Extract client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR', '')
    return ip


def log_activity(user, action, object_type, object_id, request, metadata=None):
    """Helper function to log user activities"""
    if user and user.is_authenticated:
        ActivityLog.objects.create(
            actor=user,
            action=action,
            object_type=object_type,
            object_id=str(object_id),
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:255],
            metadata=metadata or {}
        )


# ========== Authentication Views ==========

class RegisterView(CreateView):
    model = User
    form_class = UserRegistrationForm
    template_name = 'parking/auth/register.html'
    success_url = reverse_lazy('login')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Registration successful! Please log in.")
        return response


class LoginView(FormView):
    template_name = 'parking/auth/login.html'
    success_url = reverse_lazy('dashboard')
    
    def get_form(self):
        from django import forms
        class LoginForm(forms.Form):
            username = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
            password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))
        return LoginForm()
    
    def form_valid(self, form):
        username = form.cleaned_data.get('username')
        password = form.cleaned_data.get('password')
        user = authenticate(self.request, username=username, password=password)
        
        if user is not None:
            login(self.request, user)
            messages.success(self.request, f"Welcome back, {user.get_full_name() or user.username}!")
            return redirect(self.success_url)
        else:
            messages.error(self.request, "Invalid username or password.")
            return self.form_invalid(form)


class LogoutView(View):
    def get(self, request):
        logout(request)
        messages.info(request, "You have been logged out.")
        return redirect('login')


# ========== Dashboard View ==========

@method_decorator(login_required, name='dispatch')
class DashboardView(TemplateView):
    template_name = 'parking/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Statistics
        total_slots = ParkingSlot.objects.filter(is_active=True).count()
        available_slots = ParkingSlot.objects.filter(status='AVAILABLE', is_active=True).count()
        occupied_slots = ParkingSlot.objects.filter(status='OCCUPIED', is_active=True).count()
        
        # Today's revenue
        today = timezone.now().date()
        today_revenue = Payment.objects.filter(
            status='SUCCESS',
            paid_at__date=today
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        # Recent reservations
        recent_reservations = Reservation.objects.filter(user=user).order_by('-created_at')[:5]
        
        # Notifications
        notifications = Notification.objects.filter(recipient=user, is_read=False).order_by('-created_at')[:5]
        
        context.update({
            'total_slots': total_slots,
            'available_slots': available_slots,
            'occupied_slots': occupied_slots,
            'occupancy_percentage': (occupied_slots / total_slots * 100) if total_slots > 0 else 0,
            'today_revenue': today_revenue,
            'recent_reservations': recent_reservations,
            'recent_notifications': notifications,
            'unread_notifications_count': Notification.objects.filter(recipient=user, is_read=False).count(),
        })
        return context


# ========== Profile Views ==========

@method_decorator(login_required, name='dispatch')
class ProfileView(UpdateView):
    model = User
    form_class = UserProfileForm
    template_name = 'parking/profile/profile.html'
    success_url = reverse_lazy('profile')
    
    def get_object(self):
        return self.request.user
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Profile updated successfully!")
        return response


@method_decorator(login_required, name='dispatch')
class ChangePasswordView(SuccessMessageMixin, PasswordChangeView):
    template_name = 'parking/profile/change_password.html'
    success_url = reverse_lazy('profile')
    success_message = "Your password has been changed successfully!"


# ========== Vehicle Views ==========

@method_decorator(login_required, name='dispatch')
class VehicleListView(ListView):
    model = Vehicle
    template_name = 'parking/vehicles/vehicle_list.html'
    context_object_name = 'vehicles'
    
    def get_queryset(self):
        return Vehicle.objects.filter(owner=self.request.user)


@method_decorator(login_required, name='dispatch')
class VehicleCreateView(CreateView):
    model = Vehicle
    form_class = VehicleForm
    template_name = 'parking/vehicles/vehicle_form.html'
    success_url = reverse_lazy('base:vehicle_list')  # Add 'base:' namespace
    
    def form_valid(self, form):
        form.instance.owner = self.request.user
        
        # Set as default if it's the first vehicle or explicitly marked
        if form.cleaned_data.get('is_default') or not Vehicle.objects.filter(owner=self.request.user).exists():
            Vehicle.objects.filter(owner=self.request.user, is_default=True).update(is_default=False)
            form.instance.is_default = True
        
        messages.success(self.request, f"Vehicle '{form.instance.vehicle_number}' added successfully!")
        return super().form_valid(form)


@method_decorator(login_required, name='dispatch')
class VehicleUpdateView(UpdateView):
    model = Vehicle
    form_class = VehicleForm
    template_name = 'parking/vehicles/vehicle_form.html'
    success_url = reverse_lazy('base:vehicle_list')  # Add 'base:' namespace
    
    def get_queryset(self):
        return Vehicle.objects.filter(owner=self.request.user)
    
    def form_valid(self, form):
        if form.cleaned_data.get('is_default'):
            Vehicle.objects.filter(owner=self.request.user, is_default=True).exclude(id=self.object.id).update(is_default=False)
        messages.success(self.request, f"Vehicle updated successfully!")
        return super().form_valid(form)



@method_decorator(login_required, name='dispatch')
class VehicleDeleteView(DeleteView):
    model = Vehicle
    template_name = 'parking/vehicles/vehicle_confirm_delete.html'
    success_url = reverse_lazy('base:vehicle_list')  # Add 'base:' namespace
    
    def get_queryset(self):
        return Vehicle.objects.filter(owner=self.request.user)
    
    def delete(self, request, *args, **kwargs):
        vehicle = self.get_object()
        vehicle_number = vehicle.vehicle_number
        response = super().delete(request, *args, **kwargs)
        messages.success(request, f"Vehicle '{vehicle_number}' deleted successfully!")
        return response


# ========== Reservation Views ==========

@method_decorator(login_required, name='dispatch')
class ReservationListView(ListView):
    model = Reservation
    template_name = 'parking/reservations/reservation_list.html'
    context_object_name = 'reservations'
    paginate_by = 10
    
    def get_queryset(self):
        return Reservation.objects.filter(user=self.request.user).order_by('-created_at')


@method_decorator(login_required, name='dispatch')
# In base/views.py - Update CreateReservationView
class CreateReservationView(FormView):
    template_name = 'parking/reservations/create_reservation.html'
    form_class = ReservationForm
    success_url = reverse_lazy('base:reservation_list')  # Add 'base:' here
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        reservation = form.save(commit=False)
        reservation.user = self.request.user
        reservation.save()
        
        messages.success(self.request, f"Reservation {reservation.reservation_code} created successfully!")
        return super().form_valid(form)


@method_decorator(login_required, name='dispatch')
class CancelReservationView(View):
    def post(self, request, pk):
        reservation = get_object_or_404(Reservation, pk=pk, user=request.user)
        
        if reservation.status in ['PENDING', 'CONFIRMED']:
            reservation.status = 'CANCELLED'
            reservation.save()
            
            # Free up the slot
            if reservation.slot.status == 'RESERVED':
                reservation.slot.status = 'AVAILABLE'
                reservation.slot.save()
            
            messages.success(request, f"Reservation cancelled successfully!")
        else:
            messages.error(request, f"Cannot cancel reservation with status: {reservation.status}")
        
        return redirect('base:reservation_list')


@method_decorator(login_required, name='dispatch')
class CheckInView(FormView):
    template_name = 'parking/reservations/check_in.html'
    form_class = ReservationCheckInForm
    success_url = reverse_lazy('base:reservation_list')
    
    def form_valid(self, form):
        reservation_code = form.cleaned_data['reservation_code']
        reservation = Reservation.objects.get(reservation_code=reservation_code)
        
        reservation.status = 'CHECKED_IN'
        reservation.actual_check_in = timezone.now()
        reservation.save()
        
        # Update slot
        reservation.slot.status = 'OCCUPIED'
        reservation.slot.last_status_changed_at = timezone.now()
        reservation.slot.save()
        
        messages.success(self.request, f"Checked in successfully!")
        return super().form_valid(form)


@method_decorator(login_required, name='dispatch')
class CheckOutView(FormView):
    template_name = 'parking/reservations/check_out.html'
    form_class = ReservationCheckOutForm
    success_url = reverse_lazy('base:reservation_list')
    
    def form_valid(self, form):
        reservation_code = form.cleaned_data['reservation_code']
        reservation = Reservation.objects.get(reservation_code=reservation_code)
        
        # Calculate final amount
        if reservation.actual_check_in:
            hours_parked = (timezone.now() - reservation.actual_check_in).total_seconds() / 3600
            reservation.final_amount = reservation.slot.hourly_rate * Decimal(str(max(0.5, hours_parked)))
        
        reservation.status = 'COMPLETED'
        reservation.actual_check_out = timezone.now()
        reservation.save()
        
        # Free up slot
        reservation.slot.status = 'AVAILABLE'
        reservation.slot.save()
        
        messages.success(self.request, f"Checked out successfully! Final amount: ${reservation.final_amount}")
        return super().form_valid(form)


# ========== Search View ==========

@method_decorator(login_required, name='dispatch')
class SearchAvailableSlotsView(FormView):
    template_name = 'parking/search/search_slots.html'
    form_class = ParkingSlotSearchForm
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        if self.request.GET and self.request.GET.get('location'):
            location_id = self.request.GET.get('location')
            start_time = self.request.GET.get('start_time')
            duration_hours = float(self.request.GET.get('duration_hours', 1))
            
            slots = ParkingSlot.objects.filter(
                zone__location_id=location_id,
                status='AVAILABLE',
                is_active=True
            )
            
            # Calculate estimated price
            for slot in slots:
                slot.estimated_price = slot.hourly_rate * Decimal(str(duration_hours))
            
            context['slots'] = slots
            context['duration_hours'] = duration_hours
        
        return context


# ========== Notification Views ==========

@method_decorator(login_required, name='dispatch')
class NotificationListView(ListView):
    model = Notification
    template_name = 'parking/notifications/notification_list.html'
    context_object_name = 'notifications'
    paginate_by = 20
    
    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user).order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['unread_count'] = self.get_queryset().filter(is_read=False).count()
        return context


@method_decorator(login_required, name='dispatch')
class MarkNotificationReadView(View):
    def post(self, request, pk):
        notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
        notification.mark_as_read()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'success'})
        
        return redirect('notification_list')


@method_decorator(login_required, name='dispatch')
class MarkAllNotificationsReadView(View):
    def post(self, request):
        Notification.objects.filter(recipient=request.user, is_read=False).update(
            is_read=True, read_at=timezone.now()
        )
        messages.success(request, "All notifications marked as read")
        return redirect('notification_list')


# ========== Export Function ==========

@login_required
def export_reservations_csv(request):
    reservations = Reservation.objects.filter(user=request.user)
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="reservations.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Reservation Code', 'Slot', 'Start Time', 'End Time', 'Status', 'Amount'])
    
    for reservation in reservations:
        writer.writerow([
            reservation.reservation_code,
            reservation.slot.slot_number,
            reservation.start_time.strftime('%Y-%m-%d %H:%M'),
            reservation.end_time.strftime('%Y-%m-%d %H:%M'),
            reservation.get_status_display(),
            str(reservation.final_amount or reservation.estimated_amount)
        ])
    
    return response