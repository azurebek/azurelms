import os

from dotenv import load_dotenv
from google import genai


def main():
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key)

    print("\nAPI kalitida ishlaydigan modellar ro'yxati:\n")
    try:
        for model in client.models.list():
            print(f"Model: {model.name}")
    except Exception as exc:
        print(f"XATOLIK: {exc}")


if __name__ == "__main__":
    main()
