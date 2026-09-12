"""Telegram webhook manzilini o'rnatadi (F10).

    python manage.py setwebhook https://lms.example.com

**Bu buyruq deploy yo'lida turadi va shuning uchun fail-safe bo'lishi kerak.**
2026-09-13 deploy oldi auditi uch nuqson topdi va uchalasi ham bir xil
oqibatga olib borardi: bot **jimgina** ishlamay qoladi, buyruq esa
muvaffaqiyat deb ko'rinadi.

1. **Secret almashsa ham "allaqachon o'rnatilgan" deb chiqib ketardi.**
   Telegram `getWebhookInfo` da secret'ni **qaytarmaydi** — ya'ni URL
   tengligi secret tengligini isbotlamaydi. Owner `.env` da
   `TELEGRAM_WEBHOOK_SECRET` ni almashtirib buyruqni qayta yugurtirsa,
   Telegram eski secret bilan yuborishda davom etardi va `bot/views.py`
   fail-closed bo'lgani uchun **har bir update rad etilardi**. Endi
   `set_webhook` har doim chaqiriladi: u idempotent va secret'ni
   kafolatlashning yagona yo'li.
2. **Xato yutilardi va exit-code `0` bo'lardi.** `except Exception` xabarni
   `stdout` ga yozib qo'yardi — ya'ni deploy skripti yoki CI buyruqni
   muvaffaqiyatli deb hisoblardi. Endi `CommandError` ko'tariladi.
3. **`drop_pending_updates=True` doim yoqilgan edi.** Izohda "while
   testing" deb yozilgan, ammo u productionga ham ketgan: bot to'xtab
   turgan vaqtda o'quvchilar yozgan xabarlar **jimgina o'chirilardi**.
   Endi default `False`, kerak bo'lsa `--drop-pending` bilan ataylab
   so'raladi.
"""

import asyncio

from aiogram import Bot
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

#: Django URLconf'dagi webhook yo'li (`bot/urls.py`).
WEBHOOK_PATH = "/bot/webhook/"


class Command(BaseCommand):
    help = "Telegram webhook manzilini o'rnatadi"

    def add_arguments(self, parser):
        parser.add_argument(
            "url", type=str, help="Sayt manzili (masalan https://lms.example.com)"
        )
        parser.add_argument(
            "--drop-pending",
            action="store_true",
            help=(
                "Telegram navbatidagi kutilayotgan update'larni o'chiradi. "
                "ATAYLAB so'raladi: bot to'xtab turgan vaqtda kelgan "
                "xabarlar butunlay yo'qoladi."
            ),
        )

    def handle(self, *args, **options):
        mode = getattr(settings, "TELEGRAM_MODE", "webhook")
        if mode != "webhook":
            # Ogohlantirish, to'siq emas: staging'da polling bilan turib
            # webhook o'rnatib ko'rish qonuniy holat.
            self.stdout.write(
                self.style.WARNING(
                    f"TELEGRAM_MODE='{mode}' — webhook emas. Bu buyruq "
                    "staging/production uchun mo'ljallangan."
                )
            )

        token = (getattr(settings, "TELEGRAM_BOT_TOKEN", "") or "").strip()
        if not token:
            raise CommandError("TELEGRAM_BOT_TOKEN sozlanmagan.")

        secret = (getattr(settings, "TELEGRAM_WEBHOOK_SECRET", "") or "").strip()
        if not secret:
            # Secret'siz webhook o'rnatilsa `bot/views.py` fail-closed
            # bo'lgani uchun HAMMA update rad etiladi va bot jimgina
            # ishlamay qoladi. Shu sabab oldindan to'xtatamiz.
            raise CommandError(
                "TELEGRAM_WEBHOOK_SECRET sozlanmagan. Secret'siz webhook "
                "o'rnatilsa barcha update rad etiladi. Avval secret bering:\n"
                '  python -c "import secrets; print(secrets.token_urlsafe(32))"'
            )

        base_url = options["url"].rstrip("/")
        if not base_url.startswith("https://"):
            # Telegram HTTPS'siz webhookni qabul qilmaydi; buni bu yerda
            # aytish API xatosidan ko'ra tushunarliroq.
            raise CommandError(
                f"Webhook manzili HTTPS bo'lishi shart: {base_url!r}"
            )

        webhook_url = f"{base_url}{WEBHOOK_PATH}"
        drop_pending = bool(options["drop_pending"])

        result = asyncio.run(
            self._apply(token, webhook_url, secret, drop_pending=drop_pending)
        )
        for line in result:
            self.stdout.write(line)
        self.stdout.write(self.style.SUCCESS(f"Webhook o'rnatildi: {webhook_url}"))

    async def _apply(self, token, webhook_url, secret, *, drop_pending):
        bot = Bot(token=token)
        lines = []
        try:
            try:
                info = await bot.get_webhook_info()
            except Exception as exc:  # noqa: BLE001 — tarmoq/API xatosi
                raise CommandError(f"getWebhookInfo yiqildi: {exc}") from exc

            if info.url == webhook_url:
                # Ataylab chiqib ketmaymiz. `getWebhookInfo` secret'ni
                # qaytarmaydi, ya'ni URL bir xilligi secret ham bir xil
                # ekanini **isbotlamaydi**. Yagona ishonchli yo'l — qayta
                # o'rnatish; `setWebhook` idempotent.
                lines.append(
                    "Manzil o'zgarmagan — secret'ni kafolatlash uchun baribir "
                    "qayta o'rnatilmoqda (Telegram secret'ni qaytarmaydi)."
                )
            else:
                lines.append("Eski manzil: " + (info.url or "(yo'q)"))

            if info.pending_update_count:
                lines.append(
                    f"Navbatda {info.pending_update_count} ta kutilayotgan update — "
                    + (
                        "ular O'CHIRILADI (--drop-pending)."
                        if drop_pending
                        else "ular saqlanadi va yetkaziladi."
                    )
                )

            try:
                await bot.set_webhook(
                    url=webhook_url,
                    secret_token=secret,
                    drop_pending_updates=drop_pending,
                )
            except Exception as exc:  # noqa: BLE001 — tarmoq/API xatosi
                raise CommandError(f"setWebhook yiqildi: {exc}") from exc
        finally:
            await bot.session.close()
        return lines
