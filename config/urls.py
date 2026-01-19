from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("ckeditor5/", include("django_ckeditor_5.urls")),
    path("admin/", admin.site.urls),
    path("", include("landing.urls", namespace="landing")),
    path("", include("users.urls", namespace="users")),
    path("courses/", include("courses.urls", namespace="courses")),
    path("messenger/", include("communication.urls", namespace="communication")),
    path("", include("education.urls", namespace="education")),
    path("", include("billing.urls", namespace="billing")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
