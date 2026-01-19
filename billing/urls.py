from django.urls import path

from . import views

app_name = "billing"

urlpatterns = [
    path("billing/", views.payment_center_view, name="payment_center"),
]
