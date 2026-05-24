from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from django.conf import settings
from django.conf.urls.static import static

from frontend.views import home_view, about_view, legal_page_view
from core import views as core_views

handler404 = "core.views.page_not_found"
handler403 = "core.views.permission_denied"
handler500 = "core.views.server_error"

urlpatterns = [
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

    # Public blog
    path('blog/', include(('blog.urls', 'blog'), namespace='blog')),
    
    # Cohorts / Checkout
    path('checkout/', include('cohorts.urls', namespace='cohorts')),
    
    # Messenger / Chat
    path('messenger/', include('messenger.urls', namespace='messenger')),
    
    # Bot Webhooks
    path('bot/', include('bot.urls')),
    
    # CKEditor rasm yuklash manzili
    path("ckeditor5/", include('django_ckeditor_5.urls'), name="ck_editor_5_upload_file"),

    # Holat sahifalari (texnik ishlar va offline)
    path('maintenance/', core_views.maintenance, name='maintenance'),
    path('offline/', core_views.offline, name='offline'),
    path('backoffice/', core_views.backoffice_dashboard, name='backoffice_dashboard'),
    path('backoffice/users/', core_views.backoffice_users, name='backoffice_users'),
    path('backoffice/chats/', core_views.backoffice_chats, name='backoffice_chats'),
    path('backoffice/courses/new/', core_views.backoffice_course_editor, name='backoffice_course_create'),
    path('backoffice/courses/<int:course_id>/', core_views.backoffice_course_editor, name='backoffice_course_edit'),
    path('backoffice/lessons/', core_views.backoffice_lesson_editor, name='backoffice_lessons'),
    path('backoffice/lessons/<int:lesson_id>/', core_views.backoffice_lesson_editor, name='backoffice_lesson_edit'),
    path('backoffice/exams/', core_views.backoffice_exam_editor, name='backoffice_exams'),
    path('backoffice/exams/<int:exam_id>/', core_views.backoffice_exam_editor, name='backoffice_exam_edit'),

    # Imtihon (Exam shell)
    path('exam/', include(('users.exam_urls', 'exam'), namespace='exam')),
]

if settings.PROMETHEUS_ENABLED:
    urlpatterns.insert(0, path('', include('django_prometheus.urls')))

if settings.ENABLE_LEGACY_ADMIN:
    urlpatterns.insert(0, path('admin/', admin.site.urls))

# Rivojlanish (Development) vaqtida rasmlarni brauzerda ko'rish uchun:
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
