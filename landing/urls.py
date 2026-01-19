from django.urls import path
from django.views.generic import TemplateView
from .views import home_view, lead_capture_view

app_name = "landing"

urlpatterns = [
    path("", home_view, name="home"),
    path("lead/", lead_capture_view, name="lead_capture"),
    
    # Legal pages
    path("legal/refund-policy/", TemplateView.as_view(template_name="legal/refund_policy.html"), name="refund_policy"),
    path("legal/privacy-policy/", TemplateView.as_view(template_name="legal/privacy_policy.html"), name="privacy_policy"),
    path("legal/terms-of-service/", TemplateView.as_view(template_name="legal/terms_of_service.html"), name="terms_of_service"),
    path("legal/community-guidelines/", TemplateView.as_view(template_name="legal/community_guidelines.html"), name="community_guidelines"),
]
