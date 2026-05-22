from django.urls import path
from . import views

app_name = 'cohorts'

urlpatterns = [
    path('course/<int:course_id>/', views.checkout_view, name='checkout'),
    path('course/<int:course_id>/promo-preview/', views.checkout_promo_preview_view, name='checkout_promo_preview'),
    path('receipt/<int:receipt_id>/pending/', views.checkout_pending_view, name='checkout_pending'),
    path('receipt/<int:receipt_id>/success/', views.checkout_success_view, name='checkout_success'),
    path('success/', views.checkout_success_view, name='checkout_success_latest'),
]
