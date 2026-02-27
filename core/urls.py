from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Bosh sahifa
    path('', TemplateView.as_view(template_name='index.html'), name='home'),
    
    # Users (Auth)
    path('users/', include('users.urls')),
    
    # CKEditor rasm yuklash manzili
    path("ckeditor5/", include('django_ckeditor_5.urls'), name="ck_editor_5_upload_file"),
]

# Rivojlanish (Development) vaqtida rasmlarni brauzerda ko'rish uchun:
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)