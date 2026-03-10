from django.urls import path
from django.contrib.auth.views import (
    LoginView, 
    LogoutView,
    PasswordResetView,
    PasswordResetDoneView,
    PasswordResetConfirmView,
    PasswordResetCompleteView
)
from .views import (
    RegisterView, UserProfileView, SettingsView, AvatarUpdateView, PasswordUpdateView, 
    DashboardView, SubscriptionHistoryView, CertificateListView, LeaderboardView,
    AttendanceCalendarView, AttendanceManageView,
    NotificationCenterView, NotificationOpenView, NotificationReadAllView, HelpCenterView
)

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(template_name='registration/login.html', redirect_authenticated_user=True), name='login'),
    path('logout/', LogoutView.as_view(next_page='home'), name='logout'),
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('settings/', SettingsView.as_view(), name='settings'),
    path('settings/avatar/', AvatarUpdateView.as_view(), name='update_avatar'),
    path('settings/password/', PasswordUpdateView.as_view(), name='update_password'),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('leaderboard/', LeaderboardView.as_view(), name='leaderboard'),
    path('notifications/', NotificationCenterView.as_view(), name='notifications'),
    path('notifications/<int:notification_id>/open/', NotificationOpenView.as_view(), name='notification_open'),
    path('notifications/read-all/', NotificationReadAllView.as_view(), name='notifications_read_all'),
    path('attendance/', AttendanceCalendarView.as_view(), name='attendance_calendar'),
    path('attendance/manage/', AttendanceManageView.as_view(), name='attendance_manage'),
    path('subscriptions/', SubscriptionHistoryView.as_view(), name='subscriptions'),
    path('certificates/', CertificateListView.as_view(), name='certificates'),
    path('help/', HelpCenterView.as_view(), name='help_center'),
    
    # Password Reset
    path('password-reset/', PasswordResetView.as_view(), name='password_reset'),
    path('password-reset/done/', PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('password-reset-complete/', PasswordResetCompleteView.as_view(), name='password_reset_complete'),
]
