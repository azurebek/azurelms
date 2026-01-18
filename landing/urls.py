from django.urls import path
from .views import home_view, lead_capture_view

app_name = "landing"

urlpatterns = [
    path("", home_view, name="home"),
    path("lead/", lead_capture_view, name="lead_capture"),
]
