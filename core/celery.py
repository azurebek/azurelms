import os
import ssl
from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

app = Celery('core')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Broker tanlovi:
# - Localda default tarzda production Redis/Valkeyga ulanmaymiz.
# - Agar ataylab kerak bo'lsa LOCAL_USE_REMOTE_SERVICES=true qo'yiladi.
def _env_bool(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name, default):
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


is_local = (os.getenv("APP_ENV", "").strip().lower() or "local") == "local"
local_use_remote_services = _env_bool("LOCAL_USE_REMOTE_SERVICES", False)

explicit_broker = os.getenv("CELERY_BROKER_URL")
remote_redis_url = os.getenv("VALKEY_URL") or os.getenv("REDIS_URL")
local_default_broker = "memory://"

if explicit_broker:
    app.conf.broker_url = explicit_broker
elif is_local and not local_use_remote_services:
    app.conf.broker_url = local_default_broker
else:
    app.conf.broker_url = remote_redis_url or local_default_broker

app.conf.result_backend = os.getenv('CELERY_RESULT_BACKEND') or None
app.conf.accept_content = ['application/json']
app.conf.task_serializer = 'json'
app.conf.result_serializer = 'json'
app.conf.timezone = os.getenv("TIME_ZONE", "Asia/Tashkent").strip() or "Asia/Tashkent"
app.conf.task_ignore_result = True
app.conf.task_always_eager = _env_bool("CELERY_TASK_ALWAYS_EAGER", is_local and not local_use_remote_services)
app.conf.task_eager_propagates = _env_bool("CELERY_TASK_EAGER_PROPAGATES", False)

# DigitalOcean Valkey (rediss) uchun TLS sozlamasi
if str(app.conf.broker_url).startswith('rediss://'):
    app.conf.broker_use_ssl = {"ssl_cert_reqs": ssl.CERT_NONE}

if app.conf.result_backend and str(app.conf.result_backend).startswith('rediss://'):
    app.conf.redis_backend_use_ssl = {"ssl_cert_reqs": ssl.CERT_NONE}

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

subscription_lifecycle_beat_enabled = _env_bool("ENABLE_SUBSCRIPTION_LIFECYCLE_BEAT", not is_local)
beat_schedule = dict(getattr(app.conf, "beat_schedule", {}) or {})
if subscription_lifecycle_beat_enabled:
    beat_schedule["subscription-lifecycle-daily"] = {
        "task": "cohorts.tasks.run_subscription_lifecycle",
        "schedule": crontab(
            hour=_env_int("SUBSCRIPTION_LIFECYCLE_HOUR", 3),
            minute=_env_int("SUBSCRIPTION_LIFECYCLE_MINUTE", 5),
        ),
    }

# Seriya undash — kechqurun bir marta. Bugun harakat qilmagan, seriyasi
# xavf ostidagi o'quvchi yarim tunga qadar ulgursin deb aynan shu vaqt.
streak_nudge_beat_enabled = _env_bool("ENABLE_STREAK_NUDGE_BEAT", not is_local)
if streak_nudge_beat_enabled:
    beat_schedule["streak-nudge-evening"] = {
        "task": "users.tasks.run_streak_nudges",
        "schedule": crontab(
            hour=_env_int("STREAK_NUDGE_HOUR", 19),
            minute=_env_int("STREAK_NUDGE_MINUTE", 0),
        ),
    }
app.conf.beat_schedule = beat_schedule

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
