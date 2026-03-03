from django.urls import path
from django.contrib.auth.views import (
    LoginView, 
    LogoutView,
    PasswordResetView,
    PasswordResetDoneView,
    PasswordResetConfirmView,
    PasswordResetCompleteView
)
from .views import RegisterView, ProfileView, DashboardView, SubscriptionHistoryView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(template_name='registration/login.html', redirect_authenticated_user=True), name='login'),
    path('logout/', LogoutView.as_view(next_page='home'), name='logout'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('subscriptions/', SubscriptionHistoryView.as_view(), name='subscriptions'),
    
    # Password Reset
    path('password-reset/', PasswordResetView.as_view(), name='password_reset'),
    path('password-reset/done/', PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('password-reset-complete/', PasswordResetCompleteView.as_view(), name='password_reset_complete'),
]
