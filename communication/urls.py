from django.urls import path
from . import views

app_name = 'communication'

urlpatterns = [
    path('', views.inbox, name='inbox'),
<<<<<<< ours
    path("stream/", views.message_stream, name="message_stream"),
=======
    path('room/<int:room_uuid>/', views.chat_detail, name='chat_detail'),
    path('room/<int:room_uuid>/send/', views.send_message, name='send_message'),
    path('direct/<int:user_id>/', views.start_direct_chat, name='start_direct_chat'),
>>>>>>> theirs
]
