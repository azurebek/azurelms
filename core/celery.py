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

# Base settings for Redis
default_redis_url = os.getenv('VALKEY_URL') or os.getenv('REDIS_URL') or 'redis://127.0.0.1:6379/1'
app.conf.broker_url = os.getenv('CELERY_BROKER_URL', default_redis_url)
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
