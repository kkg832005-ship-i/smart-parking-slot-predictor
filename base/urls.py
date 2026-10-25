# base/urls.py
from django.urls import path
from django.contrib.auth.views import LogoutView
from . import views

app_name = 'base'

urlpatterns = [
    # Authentication
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),
    
    # Profile
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('profile/change-password/', views.ChangePasswordView.as_view(), name='change_password'),
    
    # Vehicles
     path('vehicles/', views.VehicleListView.as_view(), name='vehicle_list'),
    path('vehicles/create/', views.VehicleCreateView.as_view(), name='vehicle_create'),
    path('vehicles/<uuid:pk>/update/', views.VehicleUpdateView.as_view(), name='vehicle_update'),  # Changed to uuid
    path('vehicles/<uuid:pk>/delete/', views.VehicleDeleteView.as_view(), name='vehicle_delete'),
    
    # Reservations
    path('reservations/', views.ReservationListView.as_view(), name='reservation_list'),
    #path('reservations/<uuid:pk>/', views.ReservationDetailView.as_view(), name='reservation_detail'),
    path('reservations/create/', views.CreateReservationView.as_view(), name='reservation_create'),
    path('reservations/<uuid:pk>/cancel/', views.CancelReservationView.as_view(), name='reservation_cancel'),
    path('reservations/check-in/', views.CheckInView.as_view(), name='check_in'),
    path('reservations/check-out/', views.CheckOutView.as_view(), name='check_out'),
    
    # Search
    path('search/', views.SearchAvailableSlotsView.as_view(), name='search_slots'),
    
    # Notifications
    path('notifications/', views.NotificationListView.as_view(), name='notification_list'),
    path('notifications/<uuid:pk>/mark-read/', views.MarkNotificationReadView.as_view(), name='mark_notification_read'),
    path('notifications/mark-all-read/', views.MarkAllNotificationsReadView.as_view(), name='mark_all_notifications_read'),
    
    # Exports
    path('export/reservations/', views.export_reservations_csv, name='export_reservations'),
]