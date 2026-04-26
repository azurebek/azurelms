from django.urls import path
from . import views

app_name = 'subscriptions'

urlpatterns = [
    path('', views.PricingView.as_view(), name='pricing'),
]
