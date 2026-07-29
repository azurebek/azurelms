from django.urls import path

from . import backoffice_views


app_name = "sit_backoffice"

urlpatterns = [
    path("", backoffice_views.dashboard, name="dashboard"),
    path("universities/", backoffice_views.university_list, name="universities"),
    path(
        "universities/new/",
        backoffice_views.university_editor,
        name="university_create",
    ),
    path(
        "universities/<int:university_id>/",
        backoffice_views.university_editor,
        name="university_edit",
    ),
    path("announcements/", backoffice_views.announcement_list, name="announcements"),
    path(
        "announcements/new/",
        backoffice_views.announcement_editor,
        name="announcement_create",
    ),
    path(
        "announcements/<int:announcement_id>/",
        backoffice_views.announcement_editor,
        name="announcement_edit",
    ),
    path("guides/", backoffice_views.guide_list, name="guides"),
    path("guides/new/", backoffice_views.guide_editor, name="guide_create"),
    path(
        "guides/<int:guide_id>/",
        backoffice_views.guide_editor,
        name="guide_edit",
    ),
]
