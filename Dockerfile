# AzureLMS production image.
#
# Bitta image — besh process (web, worker, beat, outbox va migratsiya qadami).
# Ular `deploy/docker-compose.prod.yml` da bir xil image ustidan turli
# `command` bilan ko‘tariladi: kod hammasida bir xil bo‘lishi shart, aks holda
# migratsiya bir versiyada, worker boshqasida ishlab qolardi.

FROM python:3.12-slim

# `deploy/docker-compose.prod.yml` dagi PostgreSQL server majori bilan bir xil
# bo'lishi shart. Yangi klient eski serverdan dump ola oladi, ammo restore
# paytida yangi GUC'larni (masalan PG17 `transaction_timeout`) yozib, eski
# serverda tiklashni yiqitishi mumkin.
ARG POSTGRES_MAJOR=16

# `PYTHONUNBUFFERED` — log darhol `docker logs` ga chiqsin; buferlansa
# konteyner o‘lganda oxirgi, ya‘ni eng kerakli satrlar yo‘qolardi.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    APP_ENV=production

WORKDIR /app

# `ffmpeg` — speaking audio uchun; `libpq5` — PostgreSQL klient kutubxonasi.
# `postgresql-client-16` — `manage.py backup_db`/`restore_db` ichida ishlatiladigan
# `pg_dump`/`pg_restore`. Usiz zaxira olishning canonical yo‘li konteynerda
# umuman bo‘lmasdi va operator uni qo‘lda, tekshiruvsiz qilishga majbur edi.
# Build-only `gcc` va `libpq-dev` ataylab olinmadi: `psycopg2-binary` tayyor
# g‘ildirak bo‘lib keladi, kompilyator esa image ichida qolib ketardi.
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        ffmpeg \
    && install -d /usr/share/postgresql-common/pgdg \
    && curl -fsS https://www.postgresql.org/media/keys/ACCC4CF8.asc \
        -o /usr/share/postgresql-common/pgdg/apt.postgresql.org.asc \
    && . /etc/os-release \
    && echo "deb [signed-by=/usr/share/postgresql-common/pgdg/apt.postgresql.org.asc] https://apt.postgresql.org/pub/repos/apt ${VERSION_CODENAME}-pgdg main" \
        > /etc/apt/sources.list.d/pgdg.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        "postgresql-client-${POSTGRES_MAJOR}" \
    && apt-get purge -y --auto-remove curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Statikni build paytida yig‘amiz: runtime‘da qilinsa har bir konteyner uni
# takrorlab, `staticfiles/` manifesti processlarda har xil bo‘lishi mumkin edi.
# `APP_ENV=local` aynan shu qadam uchun — runtime gate non-local profilda
# DB va Redis manzilini talab qiladi, build mashinasida esa ularning hech
# biri yo‘q (`core/runtime_gate.py`).
RUN APP_ENV=local DATABASE_URL=sqlite:///:memory: SECRET_KEY=build-only-not-a-runtime-secret \
    python manage.py collectstatic --noinput

# Root emas: konteyner ichidagi ixtiyoriy kod ijrosi root bo‘lsa, mount
# qilingan `media` va `private-media` volume‘lariga ham to‘liq egalik olardi.
RUN useradd --create-home --uid 10001 azurelms \
    && mkdir -p /app/media /app/private-media \
    && chown -R azurelms:azurelms /app/media /app/private-media /app/staticfiles
USER azurelms

EXPOSE 8080

# Default — web. Qolgan processlar compose‘da `command` bilan almashtiriladi.
CMD ["daphne", "-b", "0.0.0.0", "-p", "8080", "core.asgi:application"]
