from django.urls import path

from . import views


app_name = "backoffice"

urlpatterns = [
    path("", views.BackofficeDashboardView.as_view(), name="dashboard"),
    path("students/", views.BackofficeStudentsView.as_view(), name="students"),
    path("users/", views.BackofficeUsersView.as_view(), name="users"),
    path("users/<int:user_id>/", views.BackofficeUserDetailView.as_view(), name="user_detail"),
    path("payments/", views.BackofficePaymentsView.as_view(), name="payments"),
    path("cohorts/", views.BackofficeCohortsView.as_view(), name="cohorts"),
    path("attendance/", views.BackofficeAttendanceView.as_view(), name="attendance"),
    path("notifications/", views.BackofficeNotificationsView.as_view(), name="notifications"),
]
