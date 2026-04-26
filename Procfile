release: python manage.py migrate --noinput
web: daphne -b 0.0.0.0 -p $PORT core.asgi:application
worker: celery -A core worker -l info
beat: celery -A core beat -l info
