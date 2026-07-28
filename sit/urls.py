from django.urls import path

from . import views


app_name = "sit"

urlpatterns = [
    path("", views.home, name="home"),
    path("universities/", views.university_list, name="university_list"),
    path("universities/<slug:slug>/", views.university_detail, name="university_detail"),
    path("guides/<slug:slug>/", views.knowledge_detail, name="knowledge_detail"),
]
