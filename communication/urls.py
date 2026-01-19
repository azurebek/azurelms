from django.urls import path
from . import views

app_name = 'communication'

urlpatterns = [
    path('', views.inbox, name='inbox'),
    path('send/<int:room_id>/', views.send_message, name='send_message'),
    path('poll/<int:room_id>/', views.check_new_messages, name='poll_messages'),
]
