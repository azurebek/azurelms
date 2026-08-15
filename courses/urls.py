from django.urls import path

from core import private_media_views
from . import views

urlpatterns = [
    path('', views.CourseListView.as_view(), name='courses'),
    path('exams/', views.ExamCenterView.as_view(), name='exam_center'),
    path('<int:pk>/', views.CourseDetailView.as_view(), name='course_detail'),
    path('<int:course_id>/study/', views.CourseStudyRedirectView.as_view(), name='course_study'),
    path('<int:course_id>/lesson/<int:lesson_id>/', views.LessonDetailView.as_view(), name='lesson_detail'),
    path(
        '<int:course_id>/lesson/<int:lesson_id>/assignment/<int:assignment_id>/submit/',
        views.SubmitAssignmentView.as_view(),
        name='assignment_submit',
    ),
    
    # Quiz API Endpoint
    path('<int:course_id>/lesson/<int:lesson_id>/quiz/<int:quiz_id>/submit/', views.SubmitQuizView.as_view(), name='api_quiz_submit'),
    
    path('<int:course_id>/exam/<int:exam_id>/', views.ExamDetailView.as_view(), name='exam_detail'),
    path('<int:course_id>/exam/<int:exam_id>/result/', views.ExamResultView.as_view(), name='exam_result'),
    
    # Exam API Endpoints
    path('<int:course_id>/exam/<int:exam_id>/api/start/', views.StartExamView.as_view(), name='api_exam_start'),
    path(
        '<int:course_id>/exam/<int:exam_id>/api/section/<int:section_id>/state/',
        views.ExamSectionStateView.as_view(),
        name='api_exam_section_state',
    ),
    path('<int:course_id>/exam/<int:exam_id>/api/save/', views.SaveExamAnswerView.as_view(), name='api_exam_save'),
    path('<int:course_id>/exam/<int:exam_id>/api/audio/', views.UploadExamAudioView.as_view(), name='api_exam_audio_upload'),
    path('<int:course_id>/exam/<int:exam_id>/api/audio-play/', views.RegisterAudioPlayView.as_view(), name='api_exam_audio_play'),
    path('<int:course_id>/exam/<int:exam_id>/api/review-flag/', views.ToggleExamReviewFlagView.as_view(), name='api_exam_review_flag'),
    path('<int:course_id>/exam/<int:exam_id>/api/blur/', views.LogBlurWarningView.as_view(), name='api_exam_blur'),
    path('<int:course_id>/exam/<int:exam_id>/api/submit/', views.SubmitExamView.as_view(), name='api_exam_submit'),
    
    # Private: o'quvchi ishi va speaking yozuvi.
    path('submission/<int:submission_id>/file/', private_media_views.submission_file, name='submission_file'),
    path('exam/answer/<int:answer_id>/audio/', private_media_views.exam_answer_audio, name='exam_answer_audio'),

    path('certificate/<str:certificate_id>/', views.CertificateDetailView.as_view(), name='certificate_detail'),
    path('certificate/<str:certificate_id>/appendix/', views.CertificateAppendixView.as_view(), name='certificate_appendix'),
]
