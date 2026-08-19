from django.urls import path
from django.contrib.auth.views import (
    LoginView,
    LogoutView,
    PasswordResetView,
    PasswordResetDoneView,
    PasswordResetConfirmView,
    PasswordResetCompleteView
)
from django.views.generic import RedirectView
from .views import (
    RegisterView, UserProfileView, AvatarUpdateView, PasswordUpdateView,
    SettingsAccountView, SettingsBillingView, SettingsCapabilitiesView,
    AIModelUpdateView, AISkillUpdateView, AIToneUpdateView, AIWebSearchEffortUpdateView,
    AIMemoryListView, AIMemoryArchiveView, AIMemoryClearAllView, AIMemoryRejectView, AIMemoryToggleView,
    DashboardView, MyCoursesView, SubscriptionHistoryView, CertificateListView, LeaderboardView,
    AttendanceCalendarView, AttendanceManageView,
    NotificationCenterView, NotificationOpenView, NotificationReadAllView, HelpCenterView,
    OnboardingChoiceView, StartSmartOnboardingView,
    telegram_auth_init, telegram_auth_status
)

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('register/onboarding/', OnboardingChoiceView.as_view(), name='onboarding_choice'),
    path('register/onboarding/ai/', StartSmartOnboardingView.as_view(), name='start_smart_onboarding'),
    path('login/', LoginView.as_view(template_name='registration/login.html', redirect_authenticated_user=True), name='login'),
    path('telegram-auth/init/', telegram_auth_init, name='telegram_auth_init'),
    path('telegram-auth/status/<str:token>/', telegram_auth_status, name='telegram_auth_status'),
    path('logout/', LogoutView.as_view(next_page='home'), name='logout'),
    path('profile/', UserProfileView.as_view(), name='profile'),
    # Sozlamalar 4 bo'limga ajratilgan. `settings` — umumiy kirish nuqtasi
    # bo'lib qoladi (ko'p shablon shunga havola qiladi) va Hisobga yo'naltiradi.
    path('settings/', RedirectView.as_view(pattern_name='settings_account'), name='settings'),
    path('settings/hisob/', SettingsAccountView.as_view(), name='settings_account'),
    path('settings/maxfiylik/', AIMemoryListView.as_view(), name='settings_privacy'),
    path('settings/tolov/', SettingsBillingView.as_view(), name='settings_billing'),
    path('settings/imkoniyatlar/', SettingsCapabilitiesView.as_view(), name='settings_capabilities'),

    path('settings/avatar/', AvatarUpdateView.as_view(), name='update_avatar'),
    path('settings/password/', PasswordUpdateView.as_view(), name='update_password'),
    path('settings/ai-tone/', AIToneUpdateView.as_view(), name='update_ai_tone'),
    path('settings/ai-model/', AIModelUpdateView.as_view(), name='update_ai_model'),
    path('settings/ai-skill/', AISkillUpdateView.as_view(), name='update_ai_skill'),
    path('settings/ai-web-search/', AIWebSearchEffortUpdateView.as_view(), name='update_ai_web_search_effort'),
    # Eski xotira sahifasi Maxfiylik bo'limiga ko'chdi; havola ishlashda qoladi.
    path('settings/ai-memory/', RedirectView.as_view(pattern_name='settings_privacy'), name='ai_memory'),
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
