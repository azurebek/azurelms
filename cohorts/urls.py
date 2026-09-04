from django.urls import path

from core import private_media_views
from . import difference_views, views

app_name = 'cohorts'

urlpatterns = [
    path('course/<int:course_id>/', views.checkout_view, name='checkout'),
    path('course/<int:course_id>/promo-preview/', views.checkout_promo_preview_view, name='checkout_promo_preview'),
    path('receipt/<int:receipt_id>/pending/', views.checkout_pending_view, name='checkout_pending'),
    path('receipt/<int:receipt_id>/success/', views.checkout_success_view, name='checkout_success'),
    path('success/', views.checkout_success_view, name='checkout_success_latest'),
    # Private: chek rasmi faqat egasi va staff/owner uchun.
    path('receipt/<int:receipt_id>/file/', private_media_views.receipt_file, name='receipt_file'),
    path('difference/<int:receipt_id>/upload/', difference_views.upload_difference_receipt, name='difference_upload'),
]
