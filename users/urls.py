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
    AIModelUpdateView, AIToneUpdateView, AIWebSearchEffortUpdateView,
    AIMemoryListView, AIMemoryArchiveView, AIMemoryClearAllView, AIMemoryRejectView, AIMemoryToggleView,
    DashboardView, MyCoursesView, SubscriptionHistoryView, CertificateListView, LeaderboardView,
    AttendanceCalendarView, AttendanceManageView,
    NotificationCenterView, NotificationOpenView, NotificationReadAllView, HelpCenterView,
    OnboardingChoiceView, StartSmartOnboardingView
)

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('register/onboarding/', OnboardingChoiceView.as_view(), name='onboarding_choice'),
    path('register/onboarding/ai/', StartSmartOnboardingView.as_view(), name='start_smart_onboarding'),
    path('login/', LoginView.as_view(template_name='registration/login.html', redirect_authenticated_user=True), name='login'),
    path('logout/', LogoutView.as_view(next_page='home'), name='logout'),
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('settings/', SettingsView.as_view(), name='settings'),
    path('settings/avatar/', AvatarUpdateView.as_view(), name='update_avatar'),
    path('settings/password/', PasswordUpdateView.as_view(), name='update_password'),
    path('settings/ai-tone/', AIToneUpdateView.as_view(), name='update_ai_tone'),
    path('settings/ai-model/', AIModelUpdateView.as_view(), name='update_ai_model'),
    path('settings/ai-web-search/', AIWebSearchEffortUpdateView.as_view(), name='update_ai_web_search_effort'),
    path('settings/ai-memory/', AIMemoryListView.as_view(), name='ai_memory'),
    path('settings/ai-memory/toggle/', AIMemoryToggleView.as_view(), name='ai_memory_toggle'),
    path('settings/ai-memory/clear/', AIMemoryClearAllView.as_view(), name='ai_memory_clear'),
    path('settings/ai-memory/<int:fact_id>/archive/', AIMemoryArchiveView.as_view(), name='ai_memory_archive'),
    path('settings/ai-memory/<int:fact_id>/reject/', AIMemoryRejectView.as_view(), name='ai_memory_reject'),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('my-courses/', MyCoursesView.as_view(), name='my_courses'),
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
