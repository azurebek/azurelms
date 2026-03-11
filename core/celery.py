import os
import ssl
from celery import Celery

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


is_local = (os.getenv("APP_ENV", "").strip().lower() == "local") or _env_bool("LOCAL_DEV", False)
local_use_remote_services = _env_bool("LOCAL_USE_REMOTE_SERVICES", False)

explicit_broker = os.getenv("CELERY_BROKER_URL")
remote_redis_url = os.getenv("VALKEY_URL") or os.getenv("REDIS_URL")
local_default_broker = "redis://127.0.0.1:6379/1"

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
app.conf.timezone = 'UTC'
app.conf.task_ignore_result = True

# DigitalOcean Valkey (rediss) uchun TLS sozlamasi
if str(app.conf.broker_url).startswith('rediss://'):
    app.conf.broker_use_ssl = {"ssl_cert_reqs": ssl.CERT_NONE}

if app.conf.result_backend and str(app.conf.result_backend).startswith('rediss://'):
    app.conf.redis_backend_use_ssl = {"ssl_cert_reqs": ssl.CERT_NONE}

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
