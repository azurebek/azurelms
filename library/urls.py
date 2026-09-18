from django.urls import path

from . import views


app_name = "library"

urlpatterns = [
    # O'quvchiga ochiq yagona manzil: darsga biriktirilgan bitta material.
    path("material/<int:material_id>/file/", views.material_file, name="material_file"),
]
