"""Holat sahifalari javobi: 403/404/500, texnik ishlar, oflayn, CSRF (PUB1.7a).

Qoidalar:

* **O'zi yetarli.** Shablon faqat lokal `css/system-states.css`ni oladi; tashqi
  shrift/ikonka/CDN, inline skript yo'q. Javob so'rov kontekst
  protsessorlarisiz chiziladi — 500 bazaga umuman tegmaydi (baza yiqilgan
  bo'lishi mumkin), qolganlari brend uchun faqat o'qiydi va xato bo'lsa
  standart nomga tushadi.
* **Rost.** "Jamoa xabardor qilindi", qaytish vaqti kabi da'volar faqat
  haqiqiy manbasi bo'lsa: kutish vaqtini owner belgilaydi
  (`OperationalSettings.maintenance_retry_after_minutes`), bo'lmasa aytilmaydi.
* **Qayta urinish xavfsiz.** Faqat GET/HEAD so'rovni qayta ochish havolasi
  beriladi; POST natijasi hech qachon ko'r-ko'rona qayta yuborilmaydi.
* **Indekslanmaydi, saqlanmaydi.** `no-store` va `noindex` har holat javobida
  (registrdan tashqari manzillardagi 404 ham).
"""

from urllib.parse import quote

from django.http import HttpResponse
from django.template import loader
from django.urls import reverse

SAFE_METHODS = ("GET", "HEAD")
DEFAULT_BRAND = "AzureLMS"
STATE_HEADERS = {"Cache-Control": "no-store, max-age=0", "X-Robots-Tag": "noindex, nofollow"}
# Shablon ham chizilmasa (masalan, static manifest buzilgan) — oxirgi, mutlaqo mustaqil javob.
BARE_500 = (
    '<!DOCTYPE html><html lang="uz"><head><meta charset="utf-8"><meta name="robots" content="noindex, nofollow">'
    "<title>Server xatosi</title></head><body><main><h1>Serverda xatolik</h1>"
    "<p>So‘rovingizni bajarishda kutilmagan xatolik yuz berdi. Bu sizning xatoingiz emas.</p>"
    '<p><a href="/">Bosh sahifaga</a></p></main></body></html>'
)


def _site_settings():
    try:
        from frontend.models import SiteSettings

        return SiteSettings.current()
    except Exception:
        return None


def retry_url(request):
    """Qayta ochish havolasi faqat xavfsiz so'rov uchun; aks holda ``""``."""
    if request is None or request.method not in SAFE_METHODS:
        return ""
    return request.get_full_path()


def login_url_for(request):
    """Mehmonga kirish havolasi (kirgandan keyin shu sahifaga); kirgan odamga ``""``."""
    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated:
        return ""
    return f"{reverse('login')}?next={quote(retry_url(request) or '/')}"


def maintenance_retry_after_minutes():
    """Owner belgilagan kutish (daqiqa); belgilanmagan yoki baza yetmasa — 0."""
    try:
        from core.operational_settings import current_thresholds

        return current_thresholds().maintenance_retry_after_minutes
    except Exception:
        return 0


def render_state(template, *, status, state, allow_db=True, context=None, headers=None):
    site_settings = _site_settings() if allow_db else None
    data = {
        "state": state,
        "site_settings": site_settings,
        "brand_name": (getattr(site_settings, "brand_name", "") or DEFAULT_BRAND),
    }
    data.update(context or {})
    try:
        body = loader.render_to_string(template, data)
    except Exception:
        if status < 500:
            raise
        body = BARE_500
    response = HttpResponse(body, status=status)
    for name, value in {**STATE_HEADERS, **(headers or {})}.items():
        response[name] = value
    return response
