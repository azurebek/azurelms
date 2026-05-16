# Local-First Development Workflow

Loyiha hozir default tarzda lokal ishlashga moslangan. `.env` yoki production
environment sozlanmagan holatda ham Django `APP_ENV=local` deb olinadi.

## Lokal defaultlar

- Database: `db.sqlite3`
- Cache: Django `LocMemCache`
- Channels: in-memory layer
- Celery: eager mode + `memory://` broker
- Media: `media/` papkasi
- Email: console backend
- Telegram: `polling`
- S3, remote Postgres, Redis/Valkey: o'chirilgan

## Ishga tushirish

```powershell
.\venv\Scripts\python.exe manage.py migrate
.\venv\Scripts\python.exe manage.py runserver
```

Telegram botni localda alohida polling rejimida tekshirish:

```powershell
.\venv\Scripts\python.exe manage.py runbot
```

## Optional `.env.local`

`.env.local` fayli gitga kirmaydi. Secret yoki local override kerak bo'lsa,
shu faylda saqlanadi:

```dotenv
APP_ENV=local
DEBUG=True
SECURITY_STRICT=False
LOCAL_USE_REMOTE_SERVICES=False
USE_S3=False
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```

## Remote servislarni ataylab yoqish

Local rejimda remote DB, Redis/Valkey yoki S3 ishlatish faqat quyidagicha
ataylab yoqiladi:

```dotenv
APP_ENV=local
LOCAL_USE_REMOTE_SERVICES=True
DATABASE_URL=postgres://...
REDIS_URL=redis://...
USE_S3=True
```

Bu flag qo'yilmasa, project remote production infraga ulanmaydi.

## Production sozlamalari

Production kodlari saqlangan, lekin default yo'l emas. Production rejim faqat
`APP_ENV=production` berilganda ishga tushadi va majburiy secret/database
sozlamalarini talab qiladi.
