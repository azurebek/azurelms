from django.urls import path

from . import views


app_name = "backoffice"

urlpatterns = [
    path("", views.BackofficeDashboardView.as_view(), name="dashboard"),
    path("students/", views.BackofficeStudentsView.as_view(), name="students"),
    path("payments/", views.BackofficePaymentsView.as_view(), name="payments"),
    path("cohorts/", views.BackofficeCohortsView.as_view(), name="cohorts"),
    path("attendance/", views.BackofficeAttendanceView.as_view(), name="attendance"),
]
