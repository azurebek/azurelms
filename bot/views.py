import json
from urllib.parse import urlencode

from aiogram import types
from asgiref.sync import async_to_sync
from django.conf import settings
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import redirect_to_login
from django.db.models import Count, F, Max
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.clickjacking import xframe_options_exempt
from django.utils.crypto import constant_time_compare

from core.flags import flag_enabled
from core.frontend_v1 import PLATFORM_CALM_FLAG, calm_template_names

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
    expected_token = (getattr(settings, 'TELEGRAM_WEBHOOK_SECRET', '') or '').strip()

    # Localda webhook test qilinsa, flag orqali vaqtinchalik yumshatish mumkin.
    allow_insecure_local = (
        getattr(settings, "APP_ENV", "production") == "local"
        and getattr(settings, "TELEGRAM_ALLOW_INSECURE_LOCAL_WEBHOOK", False)
    )
    if allow_insecure_local and not secret_token:
        pass  # faqat lokal test rejimida secret talab qilinmaydi
    elif not expected_token:
        # Secret sozlanmagan — fail-closed. Known-default bilan ochiq qolmaydi.
        print("Webhook rad etildi: TELEGRAM_WEBHOOK_SECRET sozlanmagan.")
        return HttpResponseForbidden()
    elif not secret_token or not constant_time_compare(secret_token, expected_token):
        # Kelgan tokenni logga yozmaymiz — hujumchi qiymati logga tushmasin.
        print("Webhook rad etildi: secret token mos kelmadi.")
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


@xframe_options_exempt
def miniapp_entry(request):
    """Mini App kirish sahifasi (F5).

    Telegram webview shu sahifani ochadi; sahifadagi JS
    window.Telegram.WebApp.initData'ni auth endpoint'ga POST qiladi,
    sessiya ochilgach maqsad sahifaga o'tadi.
    """
    requested_next = request.GET.get("next") or reverse("bot:miniapp_home")
    next_path = safe_next_path(requested_next)
    calm_enabled = flag_enabled(PLATFORM_CALM_FLAG)
    if calm_enabled:
        next_path = _calm_miniapp_destination(next_path)

    # Telegram WebView localhost'ni ochmaydi va initData faqat Telegram ichida
    # mavjud. Lokal UI ishlab chiqish uchun oddiy Django login orqali xuddi shu
    # destination'ga o'tamiz. Production'da preview parametri hech narsa qilmaydi.
    if getattr(settings, "IS_LOCAL", False) and request.GET.get("preview") == "1":
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        if calm_enabled:
            # Production auth buni HMAC tekshiruvidan keyin yozadi. Lokal preview
            # ham canonical sahifalarni tgmini iframe'ida ko'rsatishi uchun ayni
            # frame/CSP sessiya kontrakti kerak; localdan tashqarida bu yo'l yo'q.
            request.session["telegram_miniapp"] = True
        return redirect(next_path)

    return render(
        request,
        calm_template_names("bot/miniapp_entry.html", enabled=calm_enabled),
        {"next_path": next_path, "platform_calm_v1": calm_enabled},
    )


def _calm_miniapp_destination(next_path):
    """CALM Mini App'da canonical sahifani bitta `tgmini` ramkasiga joylang."""
    miniapp_pages = {
        reverse("bot:miniapp_home"),
        reverse("bot:miniapp_courses"),
        reverse("bot:miniapp_ai"),
        reverse("bot:miniapp_profile"),
    }
    if next_path.split("?", 1)[0] in miniapp_pages:
        return next_path
    return f'{reverse("bot:miniapp_home")}?{urlencode({"target": next_path})}'


def _miniapp_context(request, active_tab, *, calm_enabled=None, initial_url=""):
    """Mini App sahifalari ulashadigan mobil kontekst."""
    from users.views import build_student_enrollments

    if calm_enabled is None:
        calm_enabled = flag_enabled(PLATFORM_CALM_FLAG)
    enrollments = build_student_enrollments(request.user)
    active_enrollments = [
        item for item in enrollments if item.dashboard_effective_status == "active"
    ]
    return {
        "active_tab": active_tab,
        "enrollments": enrollments,
        "active_enrollments": active_enrollments,
        "primary_enrollment": active_enrollments[0] if active_enrollments else None,
        "is_local_preview": getattr(settings, "IS_LOCAL", False),
        "platform_calm_v1": calm_enabled,
        "miniapp_initial_url": initial_url,
    }


def _render_miniapp(request, legacy_template, context):
    """Flag ON'da yagona CALM shell, OFF'da ayni eski maxsus sahifa."""
    template = (
        "frontend_v1/calm/bot/miniapp_home.html"
        if context["platform_calm_v1"]
        else legacy_template
    )
    return render(request, template, context)


@xframe_options_exempt
@login_required
def miniapp_home(request):
    """Telegram WebView uchun ixcham platforma markazi."""
    calm_enabled = flag_enabled(PLATFORM_CALM_FLAG)
    initial_url = ""
    if calm_enabled and request.GET.get("target"):
        candidate = safe_next_path(request.GET["target"])
        if not candidate.startswith("/bot/miniapp/"):
            initial_url = candidate
    return _render_miniapp(
        request,
        "bot/miniapp_home.html",
        _miniapp_context(
            request,
            "" if initial_url else "home",
            calm_enabled=calm_enabled,
            initial_url=initial_url,
        ),
    )


@xframe_options_exempt
@login_required
def miniapp_courses(request):
    """Mini App ichidagi kurslar va o'qishni davom ettirish sahifasi."""
    calm_enabled = flag_enabled(PLATFORM_CALM_FLAG)
    return _render_miniapp(
        request,
        "bot/miniapp_courses.html",
        _miniapp_context(
            request,
            "courses",
            calm_enabled=calm_enabled,
            initial_url=reverse("my_courses") if calm_enabled else "",
        ),
    )


@xframe_options_exempt
@login_required
def miniapp_ai(request):
    """Azure AI uchun Mini App markazi va so'nggi suhbatlar."""
    calm_enabled = flag_enabled(PLATFORM_CALM_FLAG)
    context = _miniapp_context(
        request,
        "ai",
        calm_enabled=calm_enabled,
        initial_url=reverse("messenger:ai") if calm_enabled else "",
    )
    if calm_enabled:
        return _render_miniapp(request, "bot/miniapp_ai.html", context)
    context["ai_rooms"] = list(
        request.user.chat_rooms.filter(room_type="ai")
        .annotate(message_count=Count("messages"), last_message_at=Max("messages__created_at"))
        .order_by(F("last_message_at").desc(nulls_last=True), "-created_at")[:4]
    )
    return _render_miniapp(request, "bot/miniapp_ai.html", context)


@xframe_options_exempt
@login_required
def miniapp_profile(request):
    """Mini App uchun profil, AI sozlamalari va tezkor havolalar."""
    calm_enabled = flag_enabled(PLATFORM_CALM_FLAG)
    context = _miniapp_context(
        request,
        "menu" if calm_enabled else "profile",
        calm_enabled=calm_enabled,
        initial_url=reverse("profile") if calm_enabled else "",
    )
    if calm_enabled:
        return _render_miniapp(request, "bot/miniapp_profile.html", context)
    onboarding = getattr(request.user, "onboarding", None)
    context.update(
        {
            "level_label": (
                onboarding.get_current_level_display()
                if onboarding and onboarding.current_level
                else "Daraja belgilanmagan"
            ),
            "ai_tone_label": request.user.get_ai_tone_display(),
            "ai_model_label": request.user.get_ai_model_display(),
        }
    )
    return _render_miniapp(request, "bot/miniapp_profile.html", context)


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
    from users.registration_policy import existing_identity_may_continue

    # Mini App hech qachon akkaunt yaratmaydi (`registration_policy` jadvalida
    # `may_create=False`); faqat mavjud, faol identity sessiya oladi.
    user = CustomUser.objects.filter(telegram_id=telegram_id).first()
    if not existing_identity_may_continue(user):
        return JsonResponse(
            {
                "status": "error",
                "code": "unlinked",
                "message": "Hisobingiz botga ulanmagan. Botda /start bosib ro'yxatdan o'ting.",
            },
            status=404,
        )

    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    request.session["telegram_miniapp"] = True
    next_path = safe_next_path(payload.get("next"))
    if flag_enabled(PLATFORM_CALM_FLAG):
        next_path = _calm_miniapp_destination(next_path)
    return JsonResponse(
        {"status": "success", "redirect": next_path}
    )
