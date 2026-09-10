"""Production runtime gate — lokal fallbacklar serverda jim ishlab ketmasin.

`core/settings.py` cache/channel layer topolmasa `LocMemCache` va
`InMemoryChannelLayer` ga, `core/celery.py` esa `memory://` brokerga tushadi.
Lokalda bu ataylab shunday: bitta process, hech qanday tashqi xizmat kerak emas.

Serverda **aynan shu fallback eng jim buziladigan nosozlik**. Daphne, Celery
worker, beat va Telegram outbox alohida processlar; har biri o'z xotirasidagi
cache va channel layerni ko'taradi. Natijada hech narsa yiqilmaydi, log toza
qoladi, `/healthz` yashil turadi — lekin messenger WebSocketi bir processdagi
xabarni ikkinchisiga yetkazmaydi, `cache.set()` qo'shni processga ko'rinmaydi
va `memory://` brokerga yuborilgan har bir Celery taski processi bilan birga
yo'qoladi. Ya'ni `VALKEY_URL` ni yozishni unutish sahifani buzmaydi, faqat
mahsulotni sekin va sababsiz noto'g'ri qiladi.

Shuning uchun gate **konfiguratsiya darajasida** va **startup paytida** ishlaydi:
`APP_ENV != local` bo'lsa xizmat manzillari majburiy, aks holda process
`ImproperlyConfigured` bilan ko'tarilmaydi. Ulanish yetib borishini tekshirmaydi
— buni `/readyz` va Control Center probe'lari qiladi; bu yerda tekshirilsa
har bir `manage.py` chaqiruvi tarmoqqa bog'lanib qolardi va CI ham,
`collectstatic` ham real Valkey talab qilib qolardi.

Mantiq settings ichida emas, shu modulda: settings modul darajasida ishlagani
uchun uni testdan turli kirish qiymatlari bilan chaqirib bo'lmaydi.
"""

from django.core.exceptions import ImproperlyConfigured

LOCAL_ENV = "local"

# Celery brokerining "hech qayerga ulanmaslik" qiymati. Celery buni xato deb
# hisoblamaydi — task qabul qilinadi va shu process xotirasida qoladi.
IN_MEMORY_BROKER = "memory://"

_CACHE_HINT = (
    "VALKEY_URL yoki REDIS_URL bering (yoki REDIS_USER/REDIS_PASSWORD/"
    "REDIS_HOST/REDIS_PORT to'plamini)."
)
_BROKER_HINT = (
    "CELERY_BROKER_URL bering, yoki VALKEY_URL/REDIS_URL orqali umumiy "
    "Redis manzilini bering."
)


def is_local_profile(app_env):
    """`APP_ENV` lokal profilnimi.

    `LOCAL_USE_REMOTE_SERVICES` bu yerda qatnashmaydi: u lokal profilga real
    xizmatlarni **qo'shadi**, gate'ni esa o'chirmaydi. CI'ning PostgreSQL+Valkey
    ishi aynan shu holatda yuguradi.
    """
    return (app_env or LOCAL_ENV).strip().lower() == LOCAL_ENV


def collect_service_problems(*, app_env, cache_url, broker_url):
    """Non-local profilda yetishmayotgan xizmatlar ro'yxatini qaytaradi.

    Ro'yxat qaytaradi, birinchi xatoda tashlamaydi — server sozlayotgan odam
    `VALKEY_URL` ni qo'shib qayta urinib, keyin `CELERY_BROKER_URL` haqida
    ikkinchi xatoni ko'rishi ortiqcha aylanish bo'lardi.
    """
    if is_local_profile(app_env):
        return []

    problems = []
    if not (cache_url or "").strip():
        problems.append(
            f"Cache/channel layer manzili yo'q, in-memory fallback ishlatilar edi. {_CACHE_HINT}"
        )

    broker = (broker_url or "").strip()
    if not broker or broker == IN_MEMORY_BROKER:
        shown = broker or "bo‘sh"
        problems.append(
            f"Celery broker `{shown}` — tasklar processdan tashqariga chiqmaydi. {_BROKER_HINT}"
        )
    return problems


def enforce_remote_services(*, app_env, cache_url, broker_url):
    """Muammo bo'lsa `ImproperlyConfigured` tashlaydi; aks holda jim qaytadi."""
    problems = collect_service_problems(
        app_env=app_env, cache_url=cache_url, broker_url=broker_url
    )
    if not problems:
        return
    listed = "\n  - ".join(problems)
    raise ImproperlyConfigured(
        f"APP_ENV={app_env!r} lokal emas, lekin majburiy xizmatlar sozlanmagan:\n  - {listed}\n"
        "Lokal ishlash uchun APP_ENV=local qo'ying."
    )


def resolve_broker_url(*, app_env, explicit_broker, remote_redis_url, local_use_remote_services):
    """Celery broker manzilini tanlaydi.

    `core/celery.py` dagi tanlov shu yerga ko'chirildi, chunki gate brokerni
    settings ichida ham bilishi kerak: aks holda `manage.py` toza ko'tarilib,
    nosozlik faqat worker ishga tushganda — ya'ni deploy tugagach — chiqardi.
    """
    if (explicit_broker or "").strip():
        return explicit_broker.strip()
    if is_local_profile(app_env) and not local_use_remote_services:
        return IN_MEMORY_BROKER
    return (remote_redis_url or "").strip() or IN_MEMORY_BROKER
