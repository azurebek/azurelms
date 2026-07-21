from django.urls import path
from .views import (
    miniapp_ai,
    miniapp_auth,
    miniapp_courses,
    miniapp_entry,
    miniapp_home,
    miniapp_profile,
    telegram_webhook,
)

app_name = 'bot'

urlpatterns = [
    # The webhook endpoint, typically we should secure it with a token in the URL path
    # like /webhook/SECRET_TOKEN/, but for simplicity we'll use a fixed path here first
    path('webhook/', telegram_webhook, name='telegram_webhook'),
    # Mini App (F5): kirish sahifasi + initData auth-ko'prik
    path('miniapp/', miniapp_entry, name='miniapp_entry'),
    path('miniapp/auth/', miniapp_auth, name='miniapp_auth'),
    path('miniapp/home/', miniapp_home, name='miniapp_home'),
    path('miniapp/courses/', miniapp_courses, name='miniapp_courses'),
    path('miniapp/ai/', miniapp_ai, name='miniapp_ai'),
    path('miniapp/profile/', miniapp_profile, name='miniapp_profile'),
]
