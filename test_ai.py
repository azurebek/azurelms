import os
from dotenv import load_dotenv
from google import genai

load_dotenv()
api_key = os.getenv('GEMINI_API_KEY')
client = genai.Client(api_key=api_key)

print("\n🔍 API kalitingizda ishlaydigan modellar ro'yxatini qidiryapman...\n")
try:
    for m in client.models.list():
        print(f"✅ Model nomi: {m.name}")
except Exception as e:
    print("❌ XATOLIK:", e)