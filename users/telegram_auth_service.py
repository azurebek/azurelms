"""Telegram deep-link orqali kirishning yagona holat mashinasi (PUB1.0d).

Oqim:

1. Brauzer ``POST init`` qiladi (CSRF + PUB1.0c cheklovi). Bitta brauzerda bitta
   faol oqim: oldingisi yopiladi.
2. Bot ``/start auth_<token>`` ni oladi va shu servis orqali
   ``pending → authenticated`` o'tishini qiladi (row lock ostida).
3. Brauzer ``GET status`` bilan holatni so'raydi — bu so'rov **hech narsa
   yozmaydi**: muddat tugagani hisoblanadi, saqlanmaydi.
4. Brauzer ``POST consume`` qiladi — CSRF, brauzer kaliti, row lock, muddat,
   bir martalik belgi va shundan keyingina ``login()``.

Muvaffaqiyatsiz holatlar (token yo'q, boshqa brauzer, kalit yo'q) bir xil
``not_found`` javob beradi: token mavjudligini tashqaridan aniqlab bo'lmaydi.

PUB1.4e: bot havolani ochgan zahoti tasdiqlamaydi — avval kim, nima uchun va
qaysi kod bilan so'ralayotganini ko'rsatib, «Kirishni tasdiqlash» / «Bu men
emas» tugmasini kutadi. Aks holda begona odam o'z brauzerida boshlagan
havolani yuborib, uni bosgan odamning hisobiga kirib olardi. Rad etilgan oqim
``declined`` bo'ladi va brauzer buni darhol ko'radi.
"""

from dataclasses import dataclass
from datetime import timedelta
import secrets

from django.conf import settings
from django.db import transaction
from django.shortcuts import resolve_url
from django.utils import timezone
from django.utils.crypto import constant_time_compare, salted_hmac
from django.utils.http import url_has_allowed_host_and_scheme

from users.models import TelegramAuthSession

SESSION_CLIENT_KEY = 'telegram_auth_client_key'
SESSION_TOKEN_KEY = 'telegram_auth_token'
SESSION_INTENT_KEY = 'telegram_auth_next'

# Klient bilan umumiy transport kontrakti: init javobida yuboriladi, brauzer
# so'rov oralig'ini va to'xtash vaqtini shundan oladi. Token muddati —
# `TelegramAuthSession.TOKEN_TTL` — yagona manba.
POLL_INTERVAL_MS = 2000

# Yopilgan qatorlar shuncha vaqt saqlanadi, keyin o'chiriladi. TTL'dan ancha
# uzun: brauzer "eskirdi/ishlatilgan" javobini ko'ra olishi uchun.
RETENTION = timedelta(days=1)
# Har init'dan keyin o'chiriladigan eng ko'p qator — so'rov sekinlashmaydi.
PURGE_BATCH = 200

STATUS_NOT_FOUND = 'not_found'


@dataclass(frozen=True)
class FlowResult:
    status: str
    user: object = None
    redirect_url: str = ''

    @property
    def ok(self):
        return self.status != STATUS_NOT_FOUND


def effective_status(row):
    """Qatorning haqiqiy holati — bazaga yozmasdan hisoblanadi."""
    if row.status in (
        TelegramAuthSession.STATUS_USED,
        TelegramAuthSession.STATUS_EXPIRED,
        TelegramAuthSession.STATUS_DECLINED,
    ):
        return row.status
    if row.consumed_at is not None:
        return TelegramAuthSession.STATUS_USED
    if row.is_expired():
        return TelegramAuthSession.STATUS_EXPIRED
    if row.status == TelegramAuthSession.STATUS_AUTHENTICATED:
        # Foydalanuvchi o'chirilgan bo'lsa (SET_NULL) oqim yopilgan hisoblanadi.
        return row.status if row.user_id else TelegramAuthSession.STATUS_EXPIRED
    return TelegramAuthSession.STATUS_PENDING


def safe_intent(request, candidate):
    """`next` faqat shu saytning ichki manzili bo'lsa qabul qilinadi."""
    if candidate and url_has_allowed_host_and_scheme(
        candidate,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return candidate
    return ''


def confirmation_code(token):
    """Brauzer va botda bir xil ko'rinadigan 3 xonali kod (bazada saqlanmaydi).

    Maxfiy emas — foydalanuvchi bot so'rayotgan kirish aynan o'z ekranidagi
    oqim ekanini solishtirishi uchun.
    """
    digest = salted_hmac('azurelms.telegram_auth.code', token, algorithm='sha256').hexdigest()
    return f"{int(digest[:8], 16) % 1000:03d}"


def qr_data_uri(link):
    """Bot havolasining QR kodi — SVG `data:` URI (CSP `img-src data:` ruxsat beradi).

    Kompyuterda boshlagan odam telefon kamerasi bilan skanerlaydi va tasdiqni
    telefondagi Telegramda qiladi. Oq fon ataylab: qorong'i mavzuda ham o'qiladi.
    """
    import segno

    return segno.make(link, error='m', micro=False).svg_data_uri(scale=4, border=2, dark='#111827', light='#ffffff')


def bot_link(token):
    bot_username = (getattr(settings, 'BOT_USERNAME', '') or 'azureLMSbot').strip('@')
    return f"https://t.me/{bot_username}?start=auth_{token}"


def _browser_row(request, token, *, lock=False):
    """Shu brauzer boshlagan qator yoki ``None`` (yo'q va begona bir xil)."""
    client_key = request.session.get(SESSION_CLIENT_KEY) or ''
    if not client_key or not token:
        return None
    queryset = TelegramAuthSession.objects.all()
    if lock:
        queryset = queryset.select_for_update()
    row = queryset.filter(token=token).first()
    if row is None or not row.client_key or not constant_time_compare(row.client_key, client_key):
        return None
    return row


def _close_open_row(row):
    """Hali ishlatilmagan qatorni yopadi; ishlatilgani tegilmaydi."""
    if row.status in (TelegramAuthSession.STATUS_PENDING, TelegramAuthSession.STATUS_AUTHENTICATED):
        row.status = TelegramAuthSession.STATUS_EXPIRED
        row.save(update_fields=['status'])


def _close_browser_flow(request):
    previous = request.session.get(SESSION_TOKEN_KEY)
    if not previous:
        return
    with transaction.atomic():
        row = _browser_row(request, previous, lock=True)
        if row is not None:
            _close_open_row(row)


def start_flow(request, next_url=''):
    """Yangi oqim: oldingi oqim yopiladi, token shu brauzerga bog'lanadi."""
    _close_browser_flow(request)
    token = secrets.token_urlsafe(32)
    client_key = secrets.token_urlsafe(32)
    TelegramAuthSession.objects.create(token=token, client_key=client_key)
    request.session[SESSION_CLIENT_KEY] = client_key
    request.session[SESSION_TOKEN_KEY] = token
    request.session[SESSION_INTENT_KEY] = safe_intent(request, next_url)
    purge_expired(limit=PURGE_BATCH)
    return token


def read_status(request, token):
    """Holatni o'qiydi. Bazaga ham, sessiyaga ham yozmaydi."""
    row = _browser_row(request, token)
    if row is None:
        return FlowResult(STATUS_NOT_FOUND)
    return FlowResult(effective_status(row))


def consume(request, token):
    """Tasdiqlangan tokenni bir marta ishlatib, shu brauzerni login qiladi."""
    from django.contrib.auth import login as django_login
    from users.registration_policy import existing_identity_may_continue

    with transaction.atomic():
        row = _browser_row(request, token, lock=True)
        if row is None:
            return FlowResult(STATUS_NOT_FOUND)
        status = effective_status(row)
        if status != TelegramAuthSession.STATUS_AUTHENTICATED:
            # `used` — shu brauzer allaqachon olgan; qayta login yo'q.
            return FlowResult(status)
        user = row.user
        # Bir martalik: login'dan OLDIN yopiladi, parallel so'rov ikkinchi
        # marta ololmaydi.
        row.status = TelegramAuthSession.STATUS_USED
        row.consumed_at = timezone.now()
        row.save(update_fields=['status', 'consumed_at'])

    # Tasdiqdan keyin hisob faolsizlantirilgan bo'lsa ham `login()` buni
    # tekshirmaydi (PUB1.0b).
    if not existing_identity_may_continue(user):
        return FlowResult(STATUS_NOT_FOUND)

    intent = safe_intent(request, request.session.get(SESSION_INTENT_KEY) or '')
    # `login()` sessiya kalitini almashtiradi, ma'lumot esa qoladi: kalit va
    # token shu yerda qoladi, javob yo'qolsa brauzer `status` orqali `used`
    # ni ko'radi va login sahifasi orqali davom etadi.
    django_login(request, user, backend='django.contrib.auth.backends.ModelBackend')
    request.session.pop(SESSION_INTENT_KEY, None)
    return FlowResult(
        TelegramAuthSession.STATUS_AUTHENTICATED,
        user=user,
        redirect_url=intent or resolve_url(settings.LOGIN_REDIRECT_URL),
    )


def cancel(request):
    """Shu brauzer oqimini yopadi. Boshqa brauzer tokeniga tegmaydi."""
    _close_browser_flow(request)
    for key in (SESSION_CLIENT_KEY, SESSION_TOKEN_KEY, SESSION_INTENT_KEY):
        request.session.pop(key, None)


def lock_for_confirmation(token):
    """Bot tasdig'i uchun qatorni bloklaydi. ``transaction.atomic`` ichida chaqiriladi.

    ``(row, status)`` qaytaradi: status `pending` bo'lsagina o'tish mumkin.
    """
    row = TelegramAuthSession.objects.select_for_update().filter(token=token).first()
    if row is None:
        return None, STATUS_NOT_FOUND
    return row, effective_status(row)


def mark_declined(row):
    """Botda rad etildi. Qator bloklangan bo'lishi shart; ishlatilgani tegilmaydi."""
    if effective_status(row) not in (TelegramAuthSession.STATUS_PENDING, TelegramAuthSession.STATUS_AUTHENTICATED):
        return False
    row.status = TelegramAuthSession.STATUS_DECLINED
    row.save(update_fields=['status'])
    return True


def mark_authenticated(row, user):
    """Bot tasdig'i: ``pending → authenticated``. Qator bloklangan bo'lishi shart."""
    if effective_status(row) != TelegramAuthSession.STATUS_PENDING:
        raise ValueError('Faqat kutilayotgan oqim tasdiqlanadi.')
    row.user = user
    row.status = TelegramAuthSession.STATUS_AUTHENTICATED
    row.save(update_fields=['user', 'status'])


def purge_expired(limit=None, now=None):
    """Saqlash muddati o'tgan qatorlarni o'chiradi; o'chirilgan sonini qaytaradi."""
    cutoff = (now or timezone.now()) - RETENTION
    stale = TelegramAuthSession.objects.filter(created_at__lt=cutoff).order_by('created_at')
    if limit is not None:
        ids = list(stale.values_list('pk', flat=True)[:limit])
        if not ids:
            return 0
        stale = TelegramAuthSession.objects.filter(pk__in=ids)
    deleted, _ = stale.delete()
    return deleted
