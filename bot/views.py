import json

from aiogram import types
from asgiref.sync import async_to_sync
from django.conf import settings
from django.http import HttpResponseForbidden, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .aiogram_app import get_bot, get_dispatcher


@csrf_exempt
def telegram_webhook(request):
    """
    Webhook endpoint for Telegram bot.
    """
    # Simple security check
    if request.headers.get('content-type') != 'application/json':
        return HttpResponseForbidden()

    # Validate the secret token
    secret_token = request.headers.get('X-Telegram-Bot-Api-Secret-Token')
    expected_token = getattr(settings, 'TELEGRAM_WEBHOOK_SECRET', None)

    # Localda webhook test qilinsa, flag orqali vaqtinchalik yumshatish mumkin.
    allow_insecure_local = (
        getattr(settings, "APP_ENV", "production") == "local"
        and getattr(settings, "TELEGRAM_ALLOW_INSECURE_LOCAL_WEBHOOK", False)
    )
    if allow_insecure_local and not secret_token:
        print("Local mode: skipping webhook secret token check.")
    elif not expected_token or secret_token != expected_token:
        print(f"Unauthorized Webhook Access! Token mismatch. Received: {secret_token}")
        return HttpResponseForbidden()

    try:
        update_dict = json.loads(request.body.decode('utf-8'))
        update = types.Update(**update_dict)

        async def process_update():
            await get_dispatcher().feed_update(get_bot(), update)

        async_to_sync(process_update)()

        return JsonResponse({"status": "ok"})
    except Exception as e:
        print(f"Error processing update: {e}")
        return JsonResponse({"error": "Internal server error"}, status=500)
