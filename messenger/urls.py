from django.urls import path
from . import views

app_name = 'messenger'

urlpatterns = [
    path('api/rooms/', views.get_user_rooms, name='get_user_rooms'),
    path('api/messages/<int:room_id>/', views.get_room_messages, name='get_room_messages'),
]
