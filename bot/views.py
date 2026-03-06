import json
from django.conf import settings
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from asgiref.sync import async_to_sync
from aiogram import types
from .aiogram_app import bot, dp

@csrf_exempt
def telegram_webhook(request):
    """
    Webhook endpoint for Telegram bot.
    """
    # Simple security check to make sure the request comes from Telegram
    if request.headers.get('content-type') != 'application/json':
        return HttpResponseForbidden()
        
    # Validate the secret token
    secret_token = request.headers.get('X-Telegram-Bot-Api-Secret-Token')
    expected_token = getattr(settings, 'TELEGRAM_WEBHOOK_SECRET', None)
    
    if not expected_token or secret_token != expected_token:
        print(f"Unauthorized Webhook Access! Token mismatch. Received: {secret_token}")
        return HttpResponseForbidden()
        
    try:
        # Get the update from request
        update_dict = json.loads(request.body.decode('utf-8'))
        update = types.Update(**update_dict)
        
        # Process the update asynchronously using async_to_sync
        async def process_update():
            await dp.feed_update(bot, update)
            
        async_to_sync(process_update)()
        
        return JsonResponse({"status": "ok"})
    except Exception as e:
        print(f"Error processing update: {e}")
        # Security: Do not expose detailed internal stack traces/errors to clients.
        return JsonResponse({"error": "Internal server error"}, status=500)
