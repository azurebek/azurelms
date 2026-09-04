from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from django.conf import settings
from django.conf.urls.static import static

from frontend.views import home_view, about_view, legal_page_view
from core import health_views
from core import views as core_views
from core import teacher_views
from subscriptions import backoffice_views as catalog_views

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

    # Study in Turkey portal
    path('sit/', include(('sit.urls', 'sit'), namespace='sit')),
    
    # Cohorts / Checkout
    path('checkout/', include('cohorts.urls', namespace='cohorts')),
    
    # Messenger / Chat
    path('messenger/', include('messenger.urls', namespace='messenger')),
    
    # Bot Webhooks
    path('bot/', include('bot.urls')),
    
    # CKEditor rasm yuklash manzili
    path("ckeditor5/", include('django_ckeditor_5.urls'), name="ck_editor_5_upload_file"),

    # Liveness/readiness — auth talab qilmaydi, orkestrator uchun (A1a).
    path('healthz', health_views.healthz, name='healthz'),
    path('readyz', health_views.readyz, name='readyz'),

    # Holat sahifalari (texnik ishlar va offline)
    path('maintenance/', core_views.maintenance, name='maintenance'),
    path('offline/', core_views.offline, name='offline'),
    path('backoffice/sit/', include(('sit.backoffice_urls', 'sit_backoffice'), namespace='sit_backoffice')),
    path('backoffice/control/ai-kill-switch/', core_views.backoffice_ai_kill_switch, name='backoffice_ai_kill_switch'),
    path('backoffice/control/ai-circuit-reset/', core_views.backoffice_ai_circuit_reset, name='backoffice_ai_circuit_reset'),
    path('backoffice/control/flags/', core_views.backoffice_feature_flags, name='backoffice_feature_flags'),
    path('backoffice/control/ai-cost/', core_views.backoffice_ai_cost, name='backoffice_ai_cost'),
    path('backoffice/control/brand/', core_views.backoffice_brand, name='backoffice_brand'),
    path('backoffice/landing/', core_views.backoffice_landing, name='backoffice_landing'),
    path('backoffice/receipts/', core_views.backoffice_receipts, name='backoffice_receipts'),
    path('backoffice/catalog/', catalog_views.catalog, name='backoffice_catalog'),
    path('backoffice/catalog/plans/<int:plan_id>/', catalog_views.plan_editor, name='backoffice_plan_edit'),
    path('backoffice/catalog/cohorts/new/', catalog_views.cohort_editor, name='backoffice_cohort_create'),
    path('backoffice/catalog/cohorts/<int:cohort_id>/', catalog_views.cohort_editor, name='backoffice_cohort_edit'),
    path('backoffice/control/', core_views.backoffice_control, name='backoffice_control'),
    path('backoffice/', core_views.backoffice_dashboard, name='backoffice_dashboard'),
    path('backoffice/users/', core_views.backoffice_users, name='backoffice_users'),
    path('backoffice/chats/', core_views.backoffice_chats, name='backoffice_chats'),
    path('backoffice/courses/new/', core_views.backoffice_course_editor, name='backoffice_course_create'),
    path('backoffice/courses/<int:course_id>/', core_views.backoffice_course_editor, name='backoffice_course_edit'),
    path('backoffice/lessons/', core_views.backoffice_lesson_editor, name='backoffice_lessons'),
    path('backoffice/lessons/<int:lesson_id>/', core_views.backoffice_lesson_editor, name='backoffice_lesson_edit'),
    path('backoffice/exams/', core_views.backoffice_exam_editor, name='backoffice_exams'),
    path('backoffice/exams/<int:exam_id>/', core_views.backoffice_exam_editor, name='backoffice_exam_edit'),
    path('backoffice/ai-control/', core_views.backoffice_ai_control, name='backoffice_ai_control'),

    # TeacherShell — o'qituvchi paneli
    path('teacher/', teacher_views.teacher_dashboard, name='teacher_dashboard'),
    path('teacher/cohorts/', teacher_views.teacher_cohorts, name='teacher_cohorts'),
    path('teacher/students/', teacher_views.teacher_students, name='teacher_students'),
    path('teacher/courses/', teacher_views.teacher_courses_view, name='teacher_courses'),
    path('teacher/grading/', teacher_views.teacher_grading, name='teacher_grading'),
    path('teacher/grading/exam/<int:attempt_id>/', teacher_views.teacher_grade_exam, name='teacher_grade_exam'),
    path('teacher/grading/assignment/<int:submission_id>/', teacher_views.teacher_grade_assignment, name='teacher_grade_assignment'),
    path('teacher/attendance/', teacher_views.teacher_attendance, name='teacher_attendance'),
    path('teacher/release/', teacher_views.teacher_release, name='teacher_release'),
]

if settings.PROMETHEUS_ENABLED:
    urlpatterns.insert(0, path('', include('django_prometheus.urls')))

if settings.ENABLE_LEGACY_ADMIN:
    urlpatterns.insert(0, path('admin/', admin.site.urls))

# Rivojlanish (Development) vaqtida rasmlarni brauzerda ko'rish uchun:
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
