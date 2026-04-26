# 1. Muhitni tayyorlash
FROM python:3.12-slim

# 2. Ishchi papka
WORKDIR /app

# 3. Kerakli tizim paketlari (Postgres va Media fayllar uchun)
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# 4. Kutubxonalarni o'rnatish
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Kodni ko'chirish
COPY . .

# Statik fayllarni yig'ish (Baza ulanishi talab etilmasligi uchun dummy DATABASE_URL beramiz)
RUN DATABASE_URL=sqlite:///:memory: SECRET_KEY=build_pure_secret python manage.py collectstatic --noinput

# 7. ASGI server (WebSocket qo'llab-quvvatlashi uchun)
CMD ["daphne", "-b", "0.0.0.0", "-p", "8080", "core.asgi:application"]
