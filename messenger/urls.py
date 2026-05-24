from django.urls import path
from . import views

app_name = 'messenger'

urlpatterns = [
    path('', views.MessengerAIView.as_view(), name='index'),
    path('ai/', views.MessengerAIView.as_view(), name='ai'),
    path('ai/new/', views.create_ai_chat, name='new_ai_chat'),
    path('ai/<int:room_id>/', views.MessengerAIView.as_view(), name='ai_room'),
    path('group/', views.MessengerGroupView.as_view(), name='group'),
    path('tutor/', views.MessengerTutorView.as_view(), name='tutor'),
    path('api/rooms/', views.get_user_rooms, name='get_user_rooms'),
    path('api/rooms/<int:room_id>/pin/', views.toggle_room_pin, name='toggle_room_pin'),
    path('api/messages/<int:room_id>/', views.get_room_messages, name='get_room_messages'),
    path('api/messages/upload/', views.upload_message_attachment, name='upload_message_attachment'),
    path('api/messages/<int:message_id>/edit/', views.edit_message, name='edit_message'),
    path('api/messages/<int:message_id>/delete/', views.delete_message, name='delete_message'),
    path('api/ai-feedback/<int:message_id>/', views.submit_ai_feedback, name='submit_ai_feedback'),
]
