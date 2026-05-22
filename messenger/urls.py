from django.urls import path
from . import views

app_name = 'messenger'

urlpatterns = [
    path('', views.MessengerShellView.as_view(), name='index'),
    path('api/rooms/', views.get_user_rooms, name='get_user_rooms'),
    path('api/messages/<int:room_id>/', views.get_room_messages, name='get_room_messages'),
    path('api/ai-feedback/<int:message_id>/', views.submit_ai_feedback, name='submit_ai_feedback'),
]
