from django.urls import path
from . import views

app_name = "users"

urlpatterns = [
    path("signup/", views.signup_view, name="signup"),
    path("signup/check-email/", views.check_email_view, name="check_email"),
    path("login/", views.login_view, name="login"),
    path("forgot-password/", views.forgot_password_view, name="forgot_password"),
    path("logout/", views.logout_view, name="logout"),
    path("onboarding/", views.onboarding_view, name="onboarding"),
    path("dashboard/", views.dashboard_view, name="dashboard"),
]
