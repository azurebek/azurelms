import json

from aiogram import types
from asgiref.sync import async_to_sync
from django.conf import settings
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import redirect_to_login
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt

from .aiogram_app import get_bot, get_dispatcher
from .miniapp import safe_next_path, validate_init_data


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


def miniapp_entry(request):
    """Mini App kirish sahifasi (F5).

    Telegram webview shu sahifani ochadi; sahifadagi JS
    window.Telegram.WebApp.initData'ni auth endpoint'ga POST qiladi,
    sessiya ochilgach maqsad sahifaga o'tadi.
    """
    requested_next = request.GET.get("next") or reverse("bot:miniapp_home")
    next_path = safe_next_path(requested_next)

    # Telegram WebView localhost'ni ochmaydi va initData faqat Telegram ichida
    # mavjud. Lokal UI ishlab chiqish uchun oddiy Django login orqali xuddi shu
    # destination'ga o'tamiz. Production'da preview parametri hech narsa qilmaydi.
    if getattr(settings, "IS_LOCAL", False) and request.GET.get("preview") == "1":
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        return redirect(next_path)

    return render(
        request,
        "bot/miniapp_entry.html",
        {"next_path": next_path},
    )


@login_required
def miniapp_home(request):
    """Telegram WebView uchun ixcham platforma markazi."""
    from users.views import build_student_enrollments

    enrollments = build_student_enrollments(request.user)
    active_enrollments = [
        item for item in enrollments if item.dashboard_effective_status == "active"
    ]
    return render(
        request,
        "bot/miniapp_home.html",
        {
            "enrollments": enrollments[:3],
            "active_enrollments": active_enrollments,
            "primary_enrollment": active_enrollments[0] if active_enrollments else None,
            "is_local_preview": getattr(settings, "IS_LOCAL", False),
        },
    )


@csrf_exempt
def miniapp_auth(request):
    """initData'ni tekshirib Django sessiyasini ochadi.

    CSRF o'rniga autentifikatsiya — initData'ning o'zi (bot token bilan
    HMAC imzolangan, 24 soatlik muddat). csrf_exempt shu sababdan xavfsiz.
    """
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "POST kerak."}, status=405)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"status": "error", "message": "Invalid JSON"}, status=400)

    init_data = payload.get("init_data") or ""
    token = (getattr(settings, "TELEGRAM_BOT_TOKEN", "") or "").strip()
    validated = validate_init_data(init_data, token)
    if not validated or not validated.get("user"):
        return JsonResponse(
            {"status": "error", "message": "Telegram ma'lumotini tasdiqlab bo'lmadi."},
            status=403,
        )

    telegram_id = validated["user"].get("id")
    from users.models import CustomUser

    user = CustomUser.objects.filter(telegram_id=telegram_id, is_active=True).first()
    if not user:
        return JsonResponse(
            {
                "status": "error",
                "code": "unlinked",
                "message": "Hisobingiz botga ulanmagan. Botda /start bosib ro'yxatdan o'ting.",
            },
            status=404,
        )

    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    return JsonResponse(
        {"status": "success", "redirect": safe_next_path(payload.get("next"))}
    )
