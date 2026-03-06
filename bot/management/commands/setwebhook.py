from django.core.management.base import BaseCommand
from django.conf import settings
from aiogram import Bot
import asyncio

class Command(BaseCommand):
    help = 'Sets the telegram webhook URL'

    def add_arguments(self, parser):
        parser.add_argument('url', type=str, help='The base URL (e.g. https://xyz.ngrok-free.app)')

    def handle(self, *args, **options):
        base_url = options['url'].rstrip('/')
        webhook_url = f"{base_url}/bot/webhook/"
        
        # We need to run aiogram setup in an event loop
        asyncio.run(self.setup_webhook(webhook_url))

    async def setup_webhook(self, webhook_url):
        bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
        
        self.stdout.write(f"Setting webhook to: {webhook_url}")
        
        try:
            # Check current webhook
            webhook_info = await bot.get_webhook_info()
            if webhook_info.url == webhook_url:
                self.stdout.write(self.style.SUCCESS('Webhook is already set to this URL!'))
                return
                
            # Set new webhook
            # We add drop_pending_updates=True to ignore old messages while testing
            await bot.set_webhook(url=webhook_url, drop_pending_updates=True)
            self.stdout.write(self.style.SUCCESS(f'Successfully set webhook to {webhook_url}'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to set webhook: {str(e)}'))
        finally:
            await bot.session.close()
