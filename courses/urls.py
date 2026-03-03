from django.urls import path
from . import views

urlpatterns = [
    path('', views.CourseListView.as_view(), name='courses'),
    path('<int:pk>/', views.CourseDetailView.as_view(), name='course_detail'),
    path('<int:course_id>/study/', views.CourseStudyRedirectView.as_view(), name='course_study'),
    path('<int:course_id>/lesson/<int:lesson_id>/', views.LessonDetailView.as_view(), name='lesson_detail'),
    path('certificate/<str:certificate_id>/', views.CertificateDetailView.as_view(), name='certificate_detail'),
]
