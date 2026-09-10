from django.urls import re_path

from .consumers import ClassbookConsumer


websocket_urlpatterns = [
    re_path(r"ws/classbook/(?P<session_id>\d+)/$", ClassbookConsumer.as_asgi()),
]
