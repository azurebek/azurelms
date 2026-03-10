# Local And Production Workflow

Bu loyiha endi `APP_ENV` bo'yicha avtomatik sozlanadi:

- `local` -> lokal test (default bot mode: `polling`)
- `production` -> real server (default bot mode: `webhook`)

## 1) Lokal sozlash

1. `.env.local.example` faylidan nusxa oling: `.env.local`.
2. Token va boshqa qiymatlarni to'ldiring.
3. `APP_ENV=local` qoldiring.
4. Ishga tushiring:

```powershell
$env:APP_ENV="local"
python manage.py runserver
```

Telegram botni localda ngroksiz test qilish:

```powershell
$env:APP_ENV="local"
python manage.py runbot
```

## 2) Production sozlash

1. `.env.production.example` faylidan `.env.production` yarating.
2. Barcha secretlarni to'ldiring.
3. Production server env ga `APP_ENV=production` qo'ying.
4. Webhook o'rnating:

```powershell
python manage.py setwebhook https://example.com
```

## Muhim eslatma

- Localda webhook bilan ishlamoqchi bo'lsangiz ham, xavfsizlikni pasaytirish uchun:
  - `TELEGRAM_ALLOW_INSECURE_LOCAL_WEBHOOK=True` faqat localda qo'llang.
- Productionda bu qiymat `False` bo'lsin.

## Rollback (tez ortga qaytish)

Agar yangi o'zgarishlar yoqmasa, git orqali oldingi holatga qaytish mumkin:

```powershell
git checkout -- core/settings.py bot/views.py bot/management/commands/runbot.py bot/management/commands/setwebhook.py .gitignore
git clean -f .env.local.example .env.production.example LOCAL_PROD_SETUP.md
```

Yoki commit qilingandan keyin alohida revert commit qiling:

```powershell
git revert <commit_sha>
```
