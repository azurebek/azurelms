from django.urls import path

from . import backoffice_views


app_name = "library_backoffice"

urlpatterns = [
    path("", backoffice_views.resource_list, name="resources"),
    path("new/", backoffice_views.resource_editor, name="resource_create"),
    path("<int:resource_id>/", backoffice_views.resource_editor, name="resource_edit"),
    path("<int:resource_id>/file/", backoffice_views.resource_file, name="resource_file"),
    path("<int:resource_id>/archive/", backoffice_views.resource_archive, name="resource_archive"),
    path("<int:resource_id>/delete/", backoffice_views.resource_delete, name="resource_delete"),
    # Dars muharriri bilan integratsiya.
    path("lessons/<int:lesson_id>/pick/", backoffice_views.lesson_picker, name="lesson_picker"),
    path("lessons/<int:lesson_id>/attach/", backoffice_views.material_attach, name="material_attach"),
    path(
        "lessons/<int:lesson_id>/reorder/",
        backoffice_views.material_reorder,
        name="material_reorder",
    ),
    path(
        "materials/<int:material_id>/update/",
        backoffice_views.material_update,
        name="material_update",
    ),
    path(
        "materials/<int:material_id>/detach/",
        backoffice_views.material_detach,
        name="material_detach",
    ),
]
