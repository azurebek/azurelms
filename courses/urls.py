from django.urls import path
from . import views

urlpatterns = [
    path('', views.CourseListView.as_view(), name='courses'),
    path('<int:pk>/', views.CourseDetailView.as_view(), name='course_detail'),
    path('<int:course_id>/study/', views.CourseStudyRedirectView.as_view(), name='course_study'),
    path('<int:course_id>/lesson/<int:lesson_id>/', views.LessonDetailView.as_view(), name='lesson_detail'),
    
    # Quiz API Endpoint
    path('<int:course_id>/lesson/<int:lesson_id>/quiz/<int:quiz_id>/submit/', views.SubmitQuizView.as_view(), name='api_quiz_submit'),
    
    path('<int:course_id>/exam/<int:exam_id>/', views.ExamDetailView.as_view(), name='exam_detail'),
    path('<int:course_id>/exam/<int:exam_id>/result/', views.ExamResultView.as_view(), name='exam_result'),
    
    # Exam API Endpoints
    path('<int:course_id>/exam/<int:exam_id>/api/start/', views.StartExamView.as_view(), name='api_exam_start'),
    path('<int:course_id>/exam/<int:exam_id>/api/save/', views.SaveExamAnswerView.as_view(), name='api_exam_save'),
    path('<int:course_id>/exam/<int:exam_id>/api/blur/', views.LogBlurWarningView.as_view(), name='api_exam_blur'),
    path('<int:course_id>/exam/<int:exam_id>/api/submit/', views.SubmitExamView.as_view(), name='api_exam_submit'),
    
    path('certificate/<str:certificate_id>/', views.CertificateDetailView.as_view(), name='certificate_detail'),
]
