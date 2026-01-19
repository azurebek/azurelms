from django.urls import path
from . import views

app_name = "education"

urlpatterns = [
    path("lessons/<int:lesson_id>/", views.lesson_detail, name="lesson_detail"),
]
