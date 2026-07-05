# AzureLMS 🇹🇷

**O'zbek tilida turk tili o'rgatuvchi zamonaviy LMS platforma** — AI repetitor, IELTS-uslubidagi imtihon tizimi, real-time messenger va to'liq o'quv jarayoni boshqaruvi bilan.

Django 6 · Channels (WebSocket) · Celery · DigitalOcean Gradient AI (llama-4-maverick) · SQLite (lokal) / PostgreSQL + pgvector (prod)

---

## Nimalar qila oladi

### 🎓 O'quvchi uchun
- **Kurslar va darslar** — modul→dars tuzilmasi, video + konspekt + topshiriq + test tablari, drip-release (o'qituvchi ochgan sari), oldingi vazifa tasdiqlanmaguncha keyingi dars yopiq
- **Imtihonlar (5 bo'lim turi)** — Reading/Listening (8 xil boy savol turi: matching, gap-fill, T/F/NG..., avto-baholash), Writing (so'z chegaralari, per-esse o'qituvchi izohi), Speaking (brauzerda yozib yuborish), Grammar test. Fullscreen topshirish UI: taymer avto-submit, autosave, savol xaritasi, listening replay limiti, blur-proctoring
- **Sertifikatlar** — imtihondan o'tgach avtomatik; chop etiladigan sertifikat + ballar ilovasi
- **Gamifikatsiya** — XP, streak, nishonlar, guruh reytingi (podium)
- **Davomat kalendari**, to'lovlar tarixi, bildirishnomalar

### 🤖 Azure AI (shaxsiyatli repetitor)
- **Suhbat** — samimiy "o'quv-do'st" xarakteri, foydalanuvchi tanlaydigan ohang va model, uzoq muddatli xotira (faktlarni eslab qoladi), dars-kontekstli RAG javoblar
- **Skill'lar avtomatik tanlanadi** — grammatika tuzatish, quiz tuzish, vazifa tekshirish, speaking coach, progress tahlili, web-qidiruv va h.k.
- **PDF bilan ishlaydi** 📄 — yuklangan PDF'ni o'qib savollarga javob beradi; "PDF qilib ber" desangiz haqiqiy hujjat yasab beradi (jadval/ro'yxatlar bilan, yuklab olinadi)
- **Rasmlarni ko'radi** 👁 — foto/skrinshot/qo'lyozmadagi turkcha matnni o'qiydi, tarjima qiladi, xatolarni ko'rsatadi
- **Rasm chizadi** 🎨 — flashcard/diagramma so'rasangiz SVG chizib beradi (qat'iy xavfsizlik filtridan o'tadi)
- **Smart onboarding** — ro'yxatdan o'tgach AI bilan qisqa suhbatda maqsad/daraja aniqlanadi (forma o'rniga)
- **Floating widget** — istalgan sahifadan AI'ga tez murojaat

### 👨‍🏫 O'qituvchi paneli (`/teacher/`)
- **Tekshirish navbati** — kutayotgan imtihonlar va uy vazifalari bir joyda; imtihonni bo'limma-bo'lim baholash (per-esse ball+izoh, ballar jonli jamlanadi), tasdiqlash sertifikatgacha olib boradi
- **Davomat olish** — guruh+dars tanlab bir sahifada belgilash
- Guruhlar, o'quvchilar (progress/qidiruv), kontent muharrirlariga ko'prik, blog studiya

### 🛡 Backoffice (`/backoffice/`)
- Platforma holati (KPI, kutilayotgan to'lovlar, AI RAG index holati), foydalanuvchilar, chat monitoring, kurs/dars/imtihon muharrirlari

### 💬 Messenger
- AI / guruh / tutor chatlari — WebSocket real-time, fayl almashish (rasm preview bilan), AI javoblariga feedback + qayta-generatsiya

---

## Tez boshlash (lokal)

```bash
# 1. Klonlash va muhit
git clone https://github.com/azurebek/azurelms.git
cd azurelms
python -m venv venv
venv\Scripts\activate        # Windows  (Linux/Mac: source venv/bin/activate)
pip install -r requirements.txt

# 2. Sozlamalar — .env.local fayl yarating:
#    APP_ENV=local rejimida SQLite ishlatiladi, minimal kerakli kalitlar:
#    DIGITALOCEAN_INFERENCE_API_KEY=...   (AI uchun; bo'sh bo'lsa AI fallback javob beradi)
#    AI_CHAT_PROVIDER=digitalocean

# 3. Baza va admin
set APP_ENV=local            # Linux/Mac: export APP_ENV=local
python manage.py migrate
python manage.py createsuperuser

# 4. Ishga tushirish (WebSocket bilan)
python manage.py runserver   # yoki: daphne core.asgi:application
```

Ochish: http://127.0.0.1:8000 — bosh sahifa · `/users/register/` — ro'yxat · `/teacher/` va `/backoffice/` — staff uchun.

> Celery lokalda shart emas — AI javoblari Celery yo'qligida avtomatik thread-fallback bilan ishlaydi. Prod uchun: `Procfile` (Daphne + Celery worker) va `Dockerfile` tayyor.

## Testlar

```bash
python manage.py test        # to'liq suite (210+ test)
python manage.py test ai.documents courses core.tests.TeacherPanelTests   # nuqtali misollar
```

---

## Loyiha tuzilmasi

| Papka | Vazifasi |
|---|---|
| `users/` | Auth, profil, sozlamalar, dashboard, onboarding |
| `courses/` | Kurslar, darslar, **imtihon dvigateli** (sections/reading engine/attempt lifecycle), sertifikatlar |
| `cohorts/` | Guruhlar, obuna-yozilish (enrollment), davomat, to'lov cheklari |
| `messenger/` | Chat (WebSocket), AI xonalari, Smart Form sessiyalari |
| `ai/` | **AI qatlami**: agent engine, skill registry, prompt builder, RAG, xotira, provayderlar (DO/Gemini), `documents/` (PDF/rasm/SVG) |
| `subscriptions/`, `blog/`, `gamification/`, `bot/` | Tariflar, blog+studiya, XP/nishonlar, Telegram bot |
| `core/` | Sozlamalar, backoffice va teacher panel view'lari |
| `templates/`, `static/` | Yagona dizayn tizimi (shell'lar: public/app/teacher/admin/exam) |

## Hujjatlar (agentlar va hissa qo'shuvchilar uchun)

- **`AGENTS.md`** — AI-agentlar uchun kirish nuqtasi (birinchi shuni o'qing)
- **`nuclear-program/project-context.md`** — arxitektura wiki (10 app, oqimlar, data model)
- **`nuclear-program/rules-for-agents.md`** — ish qoidalari (branch/commit/test tartibi)
- **`nuclear-program/marinebook.md`** — loyiha kundaligi (har major ish yozib boriladi)

Branch tartibi: `main` — himoyalangan trunk (faqat Azurbek ruxsati bilan); agentlar `claude/`, `codex/`, `antigravity/` prefiksli branchlarda ishlaydi.

---

<p align="center"><sub>AzureLMS · Turk tilini o'zbek tilida, zamonaviy tarzda 🚀</sub></p>
