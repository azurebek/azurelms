"""Maxfiylikka mos ochiq voronka o'lchovi (PUB1.8a) — faqat server tomonida.

Nima sanaladi (PUBLIC-REFORM-PLAN §5.11 ro'yxati):

* ko'rishlar — bosh sahifa, katalog, kurs sahifasi (faqat mehmon, `GET 200`,
  bot/preview emas). Bu sahifa ko'rishlari, noyob odamlar emas: cookie yo'q;
* `purchase_intent_created` — mehmon kurs sahifasidagi xarid tugmasidan kirish
  yoki ro'yxat sahifasiga imzoli niyat bilan keldi; `auth_started` — o'sha
  sahifada forma yubordi; `auth_completed` — kirgandan keyin niyat qaytarildi
  (o'lcham: natija, masalan `checkout`). Uchalasi niyat nonce'i bo'yicha bir
  martadan — yangilash yoki qayta urinish takror sanamaydi;
* `checkout_quote_viewed` — kirgan o'quvchi checkout sahifasini ko'rdi (o'quvchi,
  kurs va kun bo'yicha bir marta); `receipt_created` — chek tranzaksiyasi
  yakunlangandan keyin (chek bo'yicha bir marta);
* `public_unavailable_shown` — kurs sahifasi "hozir yozilib bo'lmaydi" dedi
  (o'lcham: sabab).
* `support_action_used` ro'yxatda, lekin hozir server signali yo'q (aloqa havolasi
  `tel:`/`mailto:`) — sanalmaydi, soxta raqam chiqmaydi.

Nima saqlanmaydi: foydalanuvchi, email, ism, IP, user-agent, qidiruv matni,
forma, token, URL, referrer. Kunlik son (`PublicFunnelDay`) va qisqa umrli takror
kaliti (`PublicFunnelReceipt`, HMAC) — boshqa hech narsa. Flag
`public_telemetry_v1` o'chiq bo'lsa hech narsa yozilmaydi. Yozuv xatosi sahifa
yoki to'lovni hech qachon buzmaydi (savepoint + log).
"""

import hashlib
import hmac
import logging
from datetime import timedelta
from urllib.parse import parse_qs, urlsplit

from django.conf import settings
from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.db.models import F
from django.utils import timezone

FLAG = "public_telemetry_v1"

LANDING = "public_landing_view"
CATALOG = "catalog_results_view"
COURSE = "course_detail_view"
INTENT = "purchase_intent_created"
AUTH_STARTED = "auth_started"
AUTH_COMPLETED = "auth_completed"
QUOTE = "checkout_quote_viewed"
RECEIPT = "receipt_created"
UNAVAILABLE = "public_unavailable_shown"
SUPPORT = "support_action_used"
EVENTS = (LANDING, CATALOG, COURSE, INTENT, AUTH_STARTED, AUTH_COMPLETED, QUOTE, RECEIPT, UNAVAILABLE, SUPPORT)
VIEW_EVENTS = frozenset({LANDING, CATALOG, COURSE})

# O'lcham faqat shu qiymatlardan — erkin matn hech qachon yozilmaydi.
DIMENSIONS = {
    INTENT: frozenset({"login", "register"}),
    AUTH_STARTED: frozenset({"login", "register"}),
    AUTH_COMPLETED: frozenset({"checkout", "checkout_plan", "course_detail", "catalog", "course_gone", "enrolled",
                               "closed", "plan_unavailable"}),
    UNAVAILABLE: frozenset({"not_open", "full", "no_plans"}),
}
AUTH_ROUTES = frozenset({"login", "register"})
CONTINUE_ROUTE = "public_intent_continue"
CHECKOUT_ROUTE = "cohorts:checkout"
logger = logging.getLogger("frontend.public_telemetry")


def enabled():
    from core.flags import flag_enabled

    return flag_enabled(FLAG)


def receipt_key(event, dedupe):
    """Maqsadga bog'langan, qaytarib bo'lmaydigan takror kaliti."""
    message = f"public-telemetry:v1:{event}:{dedupe}".encode()
    return hmac.new(settings.SECRET_KEY.encode(), message, hashlib.sha256).hexdigest()[:40]


def receipt_horizon():
    """Takror kaliti qancha yashaydi: niyat muddati (owner sozlamasi) va bir kunlik kalitlar uchun +1 kun."""
    from core.operational_settings import current_thresholds

    return timedelta(minutes=max(current_thresholds().public_intent_minutes, 24 * 60)) + timedelta(days=1)


def prune_receipts(now=None):
    """Muddati o'tgan takror kalitlarini o'chiradi; o'chirilganlar soni."""
    from frontend.models import PublicFunnelReceipt

    cutoff = (now or timezone.now()) - receipt_horizon()
    deleted, _ = PublicFunnelReceipt.objects.filter(created_at__lt=cutoff).delete()
    return deleted


def _prune_daily(today):
    if cache.add(f"public-telemetry-prune:{today.isoformat()}", 1, timeout=2 * 24 * 3600):
        prune_receipts()


def record(event, *, course_id=None, dimension="", dedupe=None):
    """Hodisani kunlik songa qo'shadi; yozilsa ``True``. Hech qachon istisno chiqarmaydi."""
    if event not in EVENTS:
        raise ValueError(event)
    try:
        from frontend.models import PublicFunnelDay, PublicFunnelReceipt

        dimension = dimension if dimension in DIMENSIONS.get(event, ()) else ""
        course_id = int(course_id or 0)
        today = timezone.localdate()
        # Chaqiruvchilar biznes tranzaksiyasidan tashqarida: middleware (view'dan keyin) va
        # `on_commit` callback'lari. Chek signali tranzaksiya ichida hech narsa o'qimaydi (PR #236).
        if not enabled():
            return False
        # Yozuvlar savepoint ichida: xato faqat o'lchovni bekor qiladi.
        with transaction.atomic():
            if dedupe is not None:
                try:
                    with transaction.atomic():
                        PublicFunnelReceipt.objects.create(key=receipt_key(event, dedupe), event=event)
                except IntegrityError:
                    return False
            row = PublicFunnelDay.objects.filter(day=today, event=event, course_id=course_id, dimension=dimension)
            if not row.update(count=F("count") + 1):
                try:
                    with transaction.atomic():
                        PublicFunnelDay.objects.create(day=today, event=event, course_id=course_id, dimension=dimension, count=1)
                except IntegrityError:
                    row.update(count=F("count") + 1)
            _prune_daily(today)
        return True
    except Exception:  # o'lchov hech qachon sahifa yoki to'lovni buzmaydi
        logger.warning("public_telemetry_failed", extra={"telemetry_event": event}, exc_info=True)
        return False


def _intent_from_next(value):
    from frontend import public_intent

    if not value:
        return None
    parts = urlsplit(value)
    if parts.scheme or parts.netloc:
        return None
    from django.urls import reverse

    if parts.path != reverse(CONTINUE_ROUTE):
        return None
    try:
        return public_intent.read((parse_qs(parts.query).get(public_intent.PARAM) or [""])[0])
    except public_intent.InvalidIntent:
        return None


def _is_bot(request):
    from blog.utils import is_probable_bot

    return is_probable_bot(request.META.get("HTTP_USER_AGENT") or "")


def observe(request, response):
    """Javobdan keyin: shu so'rov voronkaning qaysi qadamiga to'g'ri kelishini aniqlaydi."""
    match = getattr(request, "resolver_match", None)
    if match is None or request.method not in ("GET", "POST"):
        return
    name = match.view_name
    user = getattr(request, "user", None)
    signed_in = bool(user is not None and user.is_authenticated)
    status = response.status_code
    if request.method == "GET" and status == 200 and not signed_in and request.GET.get("preview") != "1":
        from frontend.public_policy import surface_by_name

        policy = surface_by_name().get(name)
        event = getattr(policy, "telemetry_class", None)
        reason = getattr(request, "public_unavailable_reason", "")
        if event in VIEW_EVENTS or reason:
            if not _is_bot(request):
                if event in VIEW_EVENTS:
                    record(event, course_id=match.kwargs.get("pk") if event == COURSE else None)
                if reason:
                    record(UNAVAILABLE, course_id=match.kwargs.get("pk"), dimension=reason)
            return
    if name in AUTH_ROUTES:
        source = request.POST if request.method == "POST" else request.GET
        intent = _intent_from_next(source.get("next", ""))
        if intent is None or not intent.nonce:
            return
        if request.method == "GET" and status == 200:
            record(INTENT, course_id=intent.course_id, dimension=name, dedupe=intent.nonce)
        elif request.method == "POST":
            record(AUTH_STARTED, course_id=intent.course_id, dimension=name, dedupe=intent.nonce)
        return
    if name == CONTINUE_ROUTE and request.method == "GET" and signed_in:
        from frontend import public_intent

        try:
            intent = public_intent.read(request.GET.get(public_intent.PARAM, ""))
        except public_intent.InvalidIntent:
            return
        if intent.nonce:
            record(AUTH_COMPLETED, course_id=intent.course_id, dimension=getattr(request, "public_intent_outcome", ""),
                   dedupe=intent.nonce)
        return
    if name == CHECKOUT_ROUTE and request.method == "GET" and status == 200 and signed_in:
        course_id = match.kwargs.get("course_id")
        record(QUOTE, course_id=course_id, dedupe=f"{user.pk}:{course_id}:{timezone.localdate().isoformat()}")


class PublicFunnelMiddleware:
    """`AuthenticationMiddleware`dan keyin: javob tayyor bo'lgach voronka qadamini sanaydi."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        try:
            observe(request, response)
        except Exception:
            logger.warning("public_telemetry_observe_failed", exc_info=True)
        return response


def on_receipt_saved(sender, instance, created, **kwargs):
    """Yangi to'lov cheki — tranzaksiya muvaffaqiyatli yakunlangandan keyin bir marta.

    Chek tranzaksiyasi ichida hech qanday so'rov yo'q (flag, a'zolik, kurs) — faqat
    commit'dan keyingi callback ro'yxatga olinadi. Ichkarida o'qish xatosi to'lovni
    bekor qilishi mumkin edi (PR #236 review).
    """
    if not created or getattr(instance, "kind", None) != sender.KIND_PERIOD:
        return
    receipt_id, enrollment_id = instance.pk, instance.enrollment_id
    transaction.on_commit(lambda: _record_receipt(receipt_id, enrollment_id))


def _record_receipt(receipt_id, enrollment_id):
    try:
        if not enabled():
            return
        from cohorts.models import Enrollment

        course_id = Enrollment.objects.filter(pk=enrollment_id).values_list("cohort__course_id", flat=True).first()
    except Exception:
        logger.warning("public_telemetry_receipt_failed", exc_info=True)
        return
    record(RECEIPT, course_id=course_id, dedupe=f"receipt:{receipt_id}")


# --- Hisobot -------------------------------------------------------------------------------------

FUNNEL_RATES = (
    ("Kurs sahifasidan xarid niyati", INTENT, COURSE,
     "Xarid tugmasidan kirish/ro'yxatga kelgan niyatlar / mehmon kurs sahifasi ko'rishlari"),
    ("Niyatdan kirishga", AUTH_COMPLETED, INTENT,
     "Kirgandan keyin qaytarilgan niyatlar / niyatlar (bir nonce bir marta)"),
    ("Kirishdan checkout'ga", ("checkout", "checkout_plan"), AUTH_COMPLETED,
     "Kirgach checkout'ga yo'naltirilgan niyatlar / kirgandan keyin qaytarilgan niyatlar"),
    ("Kurs sahifasidan chekka (taxminiy)", RECEIPT, COURSE,
     "Yaratilgan cheklar / mehmon kurs sahifasi ko'rishlari (cheklar kirgan o'quvchilardan ham bo'lishi mumkin)"),
)


def funnel_report(*, days=28, today=None):
    """`{"start", "end", "totals": {event: n}, "rates": [(nom, surat, maxraj, foiz|None, ta'rif)]}`."""
    from django.db.models import Sum

    from frontend.models import PublicFunnelDay

    end = today or timezone.localdate()
    start = end - timedelta(days=days - 1)
    rows = PublicFunnelDay.objects.filter(day__range=(start, end))
    totals = {event: 0 for event in EVENTS}
    for item in rows.values("event").annotate(total=Sum("count")).order_by("event"):
        totals[item["event"]] = item["total"]
    completed_to_checkout = rows.filter(event=AUTH_COMPLETED, dimension__in=("checkout", "checkout_plan")).aggregate(
        total=Sum("count"))["total"] or 0
    rates = []
    for title, numerator, denominator, definition in FUNNEL_RATES:
        top = completed_to_checkout if isinstance(numerator, tuple) else totals[numerator]
        bottom = totals[denominator]
        rates.append((title, top, bottom, round(100 * top / bottom, 1) if bottom else None, definition))
    return {"start": start, "end": end, "totals": totals, "rates": rates}
