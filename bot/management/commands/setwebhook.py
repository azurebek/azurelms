from django.core.management.base import BaseCommand
from django.conf import settings
from aiogram import Bot
import asyncio

class Command(BaseCommand):
    help = 'Sets the telegram webhook URL'

    def add_arguments(self, parser):
        parser.add_argument('url', type=str, help='The base URL (e.g. https://xyz.ngrok-free.app)')

    def handle(self, *args, **options):
        if getattr(settings, "TELEGRAM_MODE", "webhook") != "webhook":
            self.stdout.write(
                self.style.WARNING(
                    "TELEGRAM_MODE webhook emas. Bu komandani staging/production uchun ishlating."
                )
            )

        base_url = options['url'].rstrip('/')
        webhook_url = f"{base_url}/bot/webhook/"
        
        # We need to run aiogram setup in an event loop
        asyncio.run(self.setup_webhook(webhook_url))

    async def setup_webhook(self, webhook_url):
        bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
        secret_token = (getattr(settings, 'TELEGRAM_WEBHOOK_SECRET', '') or '').strip()

        # Secret'siz webhook o'rnatilsa, view fail-closed bo'lgani uchun HAMMA
        # update rad etiladi va bot jimgina ishlamay qoladi. Shu sabab
        # oldindan to'xtatamiz.
        if not secret_token:
            self.stderr.write(self.style.ERROR(
                "TELEGRAM_WEBHOOK_SECRET sozlanmagan. Secret'siz webhook o'rnatilsa "
                "barcha update rad etiladi. Avval secret bering."
            ))
            return

        self.stdout.write(f"Setting webhook to: {webhook_url}")
        
        try:
            # Check current webhook
            webhook_info = await bot.get_webhook_info()
            if webhook_info.url == webhook_url:
                self.stdout.write(self.style.SUCCESS('Webhook is already set to this URL!'))
                return
                
            # Set new webhook
            # We add drop_pending_updates=True to ignore old messages while testing
            set_kwargs = {
                "url": webhook_url,
                "drop_pending_updates": True,
                "secret_token": secret_token,
            }

            await bot.set_webhook(**set_kwargs)
            self.stdout.write(self.style.SUCCESS(f'Successfully set webhook to {webhook_url}'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to set webhook: {str(e)}'))
        finally:
            await bot.session.close()
