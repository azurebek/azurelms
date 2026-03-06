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

# 6. Django-ni yoqish (App Platform buni o'zi boshqaradi, lekin bu yerda turishi zarar qilmaydi)
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "core.wsgi:application"]
