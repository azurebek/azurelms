from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from django.conf import settings
from django.conf.urls.static import static

from frontend.views import home_view, about_view, legal_page_view

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Bosh sahifa (Home / Landing)
    path('', home_view, name='home'),
    path('about/', about_view, name='about'),
    path('privacy-policy/', legal_page_view, {"page_type": "privacy"}, name='privacy_policy'),
    path('terms-of-service/', legal_page_view, {"page_type": "terms"}, name='terms_of_service'),
    path('faq/', legal_page_view, {"page_type": "faq"}, name='faq_page'),
    
    # Users (Auth)
    path('users/', include('users.urls')),
    
    # Courses
    path('courses/', include('courses.urls')),
    
    # Pricing/Subscriptions
    path('pricing/', include('subscriptions.urls', namespace='subscriptions')),
    
    # Cohorts / Checkout
    path('checkout/', include('cohorts.urls', namespace='cohorts')),
    
    # Messenger / Chat
    path('messenger/', include('messenger.urls', namespace='messenger')),
    
    # Bot Webhooks
    path('bot/', include('bot.urls')),
    
    # CKEditor rasm yuklash manzili
    path("ckeditor5/", include('django_ckeditor_5.urls'), name="ck_editor_5_upload_file"),
]

# Rivojlanish (Development) vaqtida rasmlarni brauzerda ko'rish uchun:
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
