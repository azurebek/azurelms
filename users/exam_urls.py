from django.urls import path

from .exam_views import (
    ExamCenterView,
    ExamHistoryView,
    ExamListeningView,
    ExamReviewView,
    ExamSpeakingView,
    ExamWritingView,
)

app_name = "exam"

urlpatterns = [
    path("", ExamCenterView.as_view(), name="center"),
    path("history/", ExamHistoryView.as_view(), name="history"),
    path("listening/", ExamListeningView.as_view(), name="listening"),
    path("writing/", ExamWritingView.as_view(), name="writing"),
    path("speaking/", ExamSpeakingView.as_view(), name="speaking"),
    path("review/", ExamReviewView.as_view(), name="review"),
]
