"""Auth urinishlarini cheklashning yagona qarori (PUBLIC-01 · PUB1.0c).

Login, ro'yxatdan o'tish, parol tiklash va Telegram orqali kirishda urinishlar
soni cheklanmagan edi: parolni cheksiz taxmin qilish, bazani yangi hisob bilan
to'ldirish va istalgan emailga tiklash xati yuborish mumkin edi. Har view o'z
hisoblagichini yozsa, keyingi endpoint yana unutiladi — shuning uchun qaror va
hisoblagich shu yerda, adapterlar faqat yordamchi funksiyani chaqiradi.

Asosiy qarorlar va nega aynan shunday:

* **Kalit raw emas.** Email, username va IP HMAC bilan digest qilinadi
  (`SECRET_KEY`dan, scope bo'yicha alohida). Jadval yoki log o'g'irlansa ham
  kim, qayerdan kirmoqchi bo'lgani ochilmaydi.
* **Hisob mavjudligi sezilmaydi.** Login va tiklash hisoblagichi kiritilgan
  identifikator bo'yicha yuradi, hisob bor-yo'qligidan qat'i nazar — blok
  holati enumeration uchun signal bo'lmaydi.
* **Doimiy blok yo'q.** Blok faqat joriy oyna oxirigacha. Aks holda hujumchi
  begona hisobni o'z xohishiga ko'ra yopib qo'ya olardi.
* **Ishonchli IP.** `X-Forwarded-For`ning birinchi qiymatiga mijoz istalgan
  narsani yoza oladi; IP faqat `TRUSTED_PROXY_HOPS` sakrashdan olinadi.
* **Saqlash xatosida fail-open.** Hisoblagich jadvali o'qilmasa so'rov o'tadi
  va ogohlantirish logga yoziladi. Aks holda throttle nosozligi hammani,
  jumladan ownerni ham, logindan qoldirardi.
* **Yoqish/o'chirish flagda.** `auth_throttle_enforcement` OFF bo'lsa
  hisoblash davom etadi, lekin hech kim rad etilmaydi (favqulodda holat).
  Limit va oynalar `OperationalSettings`da — owner auditli paneldan o'zgartiradi.
"""

import ipaddress
import logging
import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from datetime import timezone as dt_timezone

from django.conf import settings
from django.db import DatabaseError, transaction
from django.db.models import F
from django.utils import timezone
from django.utils.crypto import salted_hmac

logger = logging.getLogger(__name__)

SCOPE_LOGIN_ACCOUNT = "login_account"
SCOPE_LOGIN_IP = "login_ip"
SCOPE_REGISTER_IP = "register_ip"
SCOPE_RESET_ACCOUNT = "reset_account"
SCOPE_RESET_IP = "reset_ip"
SCOPE_TELEGRAM_INIT_IP = "telegram_init_ip"

#: scope → (limit sozlamasi, oyna sozlamasi) — `core.operational_settings`dagi nomlar.
SCOPE_SETTINGS = {
    SCOPE_LOGIN_ACCOUNT: ("auth_login_account_limit", "auth_login_window_minutes"),
    SCOPE_LOGIN_IP: ("auth_login_ip_limit", "auth_login_window_minutes"),
    SCOPE_REGISTER_IP: ("auth_register_ip_limit", "auth_register_window_minutes"),
    SCOPE_RESET_ACCOUNT: ("auth_reset_account_limit", "auth_reset_window_minutes"),
    SCOPE_RESET_IP: ("auth_reset_ip_limit", "auth_reset_window_minutes"),
    SCOPE_TELEGRAM_INIT_IP: ("auth_telegram_init_ip_limit", "auth_telegram_init_window_minutes"),
}

THROTTLED_MESSAGE = (
    "Juda ko‘p urinish bo‘ldi. Xavfsizlik uchun {minutes} daqiqadan keyin "
    "qayta urinib ko‘ring."
)

_DIGEST_SALT = "azurelms.auth_throttle.v1"
# Har yozuvdan keyin muddati o'tgan qatorlardan shunchasi o'chiriladi — jadval
# beat yoki cron bo'lmasa ham o'smaydi, so'rov esa sekinlashmaydi.
_CLEANUP_BATCH = 200


@dataclass(frozen=True)
class ThrottleDecision:
    allowed: bool
    scope: str = ""
    retry_after: int = 0
    enforced: bool = True

    @property
    def message(self):
        minutes = max(1, math.ceil(self.retry_after / 60))
        return THROTTLED_MESSAGE.format(minutes=minutes)


ALLOWED = ThrottleDecision(allowed=True)


# --------------------------------------------------------------- kalitlar


def client_ip(request):
    """So'rovning ishonchli mijoz IP'si (`TRUSTED_PROXY_HOPS` bo'yicha)."""
    remote = (request.META.get("REMOTE_ADDR") or "").strip()
    hops = int(getattr(settings, "TRUSTED_PROXY_HOPS", 0) or 0)
    candidate = remote
    if hops > 0:
        forwarded = [
            part.strip()
            for part in (request.META.get("HTTP_X_FORWARDED_FOR") or "").split(",")
            if part.strip()
        ]
        # O'ngdan `hops`-chi qiymat — uni bizning proxy qo'ygan. Chapdagilarni
        # mijoz yozishi mumkin, ular hisobga olinmaydi.
        if len(forwarded) >= hops:
            candidate = forwarded[-hops]
    for value in (candidate, remote):
        try:
            return str(ipaddress.ip_address(value))
        except ValueError:
            continue
    return "unknown"


def normalize_identifier(value):
    return str(value or "").strip().lower()[:254]


def _digest(scope, key):
    return salted_hmac(_DIGEST_SALT, f"{scope}\0{key}", algorithm="sha256").hexdigest()


# --------------------------------------------------------------- yadro


def _policy(scope):
    from core.models import OperationalSettings

    thresholds = OperationalSettings.resolved()
    limit_name, window_name = SCOPE_SETTINGS[scope]
    return getattr(thresholds, limit_name), getattr(thresholds, window_name)


def _window(now, minutes):
    seconds = minutes * 60
    epoch = int(now.timestamp())
    start = datetime.fromtimestamp(epoch - (epoch % seconds), tz=dt_timezone.utc)
    return start, start + timedelta(seconds=seconds)


def _enforcing():
    from core.flags import flag_enabled

    return flag_enabled("auth_throttle_enforcement")


def _decide(scope, over_limit, window_end, now):
    if not over_limit:
        return ALLOWED
    retry_after = max(1, math.ceil((window_end - now).total_seconds()))
    enforced = _enforcing()
    return ThrottleDecision(allowed=not enforced, scope=scope, retry_after=retry_after, enforced=enforced)


def _bucket_model():
    from users.models import AuthThrottleBucket

    return AuthThrottleBucket


def peek(scope, key, *, now=None):
    """Hisoblagichni oshirmasdan: shu kalit hozir limitga yetganmi."""
    if not key:
        return ALLOWED
    now = now or timezone.now()
    limit, minutes = _policy(scope)
    start, end = _window(now, minutes)
    try:
        count = (
            _bucket_model().objects
            .filter(scope=scope, key_digest=_digest(scope, key), window_start=start)
            .values_list("count", flat=True)
            .first()
        ) or 0
    except DatabaseError:
        logger.warning("auth throttle o'qib bo'lmadi (scope=%s); so'rov o'tkazildi", scope)
        return ALLOWED
    return _decide(scope, count >= limit, end, now)


def record(scope, key, *, now=None):
    """Hisoblagichni atomik oshiradi; yangi qiymat limitdan oshsa rad."""
    if not key:
        return ALLOWED
    now = now or timezone.now()
    limit, minutes = _policy(scope)
    start, end = _window(now, minutes)
    Bucket = _bucket_model()
    try:
        with transaction.atomic():
            bucket, _ = Bucket.objects.get_or_create(
                scope=scope,
                key_digest=_digest(scope, key),
                window_start=start,
                defaults={"expires_at": end},
            )
            # `F()` bilan oshirish qator darajasida atomik: parallel so'rovlar
            # bir-birining qiymatini yo'qotmaydi.
            Bucket.objects.filter(pk=bucket.pk).update(count=F("count") + 1)
            count = Bucket.objects.filter(pk=bucket.pk).values_list("count", flat=True).get()
            if count >= limit:
                Bucket.objects.filter(pk=bucket.pk, blocked_until__isnull=True).update(blocked_until=end)
        _cleanup_expired(now)
    except DatabaseError:
        logger.warning("auth throttle yozib bo'lmadi (scope=%s); so'rov o'tkazildi", scope)
        return ALLOWED
    return _decide(scope, count > limit, end, now)


def clear(scope, key, *, now=None):
    """Joriy oynadagi hisoblagichni tozalaydi (masalan, muvaffaqiyatli logindan keyin)."""
    if not key:
        return
    now = now or timezone.now()
    _, minutes = _policy(scope)
    start, _ = _window(now, minutes)
    try:
        _bucket_model().objects.filter(scope=scope, key_digest=_digest(scope, key), window_start=start).delete()
    except DatabaseError:
        logger.warning("auth throttle tozalanmadi (scope=%s)", scope)


def _cleanup_expired(now):
    Bucket = _bucket_model()
    stale = list(Bucket.objects.filter(expires_at__lt=now).values_list("pk", flat=True)[:_CLEANUP_BATCH])
    if stale:
        Bucket.objects.filter(pk__in=stale).delete()


def prune_expired(*, now=None):
    """Muddati o'tgan barcha hisoblagichlarni o'chiradi; o'chirilgan qator soni."""
    now = now or timezone.now()
    deleted, _ = _bucket_model().objects.filter(expires_at__lt=now).delete()
    return deleted


def _first_denied(*decisions):
    for decision in decisions:
        if not decision.allowed:
            return decision
    return ALLOWED


# --------------------------------------------------------------- adapterlar uchun


def login_blocked(request, identifier):
    """Login urinishidan oldin: hisob yoki IP limitga yetganmi (hisoblamaydi)."""
    return _first_denied(
        peek(SCOPE_LOGIN_ACCOUNT, normalize_identifier(identifier)),
        peek(SCOPE_LOGIN_IP, client_ip(request)),
    )


def record_login_failure(request, identifier):
    record(SCOPE_LOGIN_ACCOUNT, normalize_identifier(identifier))
    record(SCOPE_LOGIN_IP, client_ip(request))


def record_login_success(request, identifier):
    # IP hisoblagichi saqlanadi: bitta to'g'ri parol boshqa hisoblarni sinashni
    # oqlamaydi.
    clear(SCOPE_LOGIN_ACCOUNT, normalize_identifier(identifier))


def registration_blocked(request):
    return peek(SCOPE_REGISTER_IP, client_ip(request))


def record_registration(request):
    record(SCOPE_REGISTER_IP, client_ip(request))


def consume_password_reset(request, email):
    return _first_denied(
        record(SCOPE_RESET_IP, client_ip(request)),
        record(SCOPE_RESET_ACCOUNT, normalize_identifier(email)),
    )


def consume_telegram_init(request):
    return record(SCOPE_TELEGRAM_INIT_IP, client_ip(request))


def apply_throttle_headers(response, decision):
    """Rad etilgan javobga `429` va `Retry-After` qo'yadi."""
    response.status_code = 429
    response["Retry-After"] = str(decision.retry_after)
    return response
