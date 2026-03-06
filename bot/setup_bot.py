import os
import sys
import requests
import secrets
from pathlib import Path

# Load settings from .env
env_file = Path('c:/projects/azure_lms/.env')
env_vars = {}
with open(env_file, 'r') as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('#'):
            key, val = line.split('=', 1)
            env_vars[key.strip()] = val.strip()

BOT_TOKEN = env_vars.get('TELEGRAM_BOT_TOKEN')

print("1. Please enter the main NGROK URL you are using (e.g. https://1234abcd.ngrok-free.app):")
ngrok_url = input("> ").strip().rstrip('/')

print("2. Generating a strong random secret token for webhook verification...")
secret = secrets.token_hex(16)

print(f"Generated secret: {secret}")
print("Appending TELEGRAM_WEBHOOK_SECRET to .env file...")

with open(env_file, 'a') as f:
    f.write(f"\nTELEGRAM_WEBHOOK_SECRET={secret}\n")

print("3. Registering Webhook with Telegram servers...")
webhook_url = f"{ngrok_url}/bot/webhook/"

res = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook", json={
    "url": webhook_url,
    "secret_token": secret
})

if res.status_code == 200 and res.json().get('ok'):
    print("✅ Webhook successfully set!")
    print(f"URL: {webhook_url}")
else:
    print("❌ Failed to set webhook:")
    print(res.text)

print("\nIMPORTANT: Please restart your Django server (`python manage.py runserver`) for the new SECRET to take effect.")
