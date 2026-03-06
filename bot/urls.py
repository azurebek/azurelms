from django.urls import path
from .views import telegram_webhook

app_name = 'bot'

urlpatterns = [
    # The webhook endpoint, typically we should secure it with a token in the URL path
    # like /webhook/SECRET_TOKEN/, but for simplicity we'll use a fixed path here first
    path('webhook/', telegram_webhook, name='telegram_webhook'),
]
