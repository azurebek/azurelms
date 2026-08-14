# AzureLMS 🇹🇷

**O'zbek tilida turk tili o'rgatuvchi zamonaviy LMS platforma** — AI repetitor, IELTS-uslubidagi imtihon tizimi, real-time messenger va to'liq o'quv jarayoni boshqaruvi bilan.

Django 6 · Channels (WebSocket) · Celery · Google Gemini (joriy local AI) · SQLite (lokal) · PostgreSQL + pgvector (future prod)

> **2026-08-14 resurs holati:** loyiha LOCAL/PRE-PROD. DigitalOcean hosting, Spaces va inference ishlatilmaydi; adapter kodi keyingi production qarorigacha dormant va `AI_ALLOW_DIGITALOCEAN=False` bilan fail-closed. Gemini bepul kvotasi hard constraint. `A8` global request/token reservation ledgeri, bounded provider attemptlari va cooldown circuit'i **`IMPLEMENTED/TESTED — LOCAL REGRESSION GREEN`**; bu production yoki real-concurrency readiness da'vosi emas.

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
- **Rasm oqimi** 👁 — `image_qa` routing va upload primitive'i bor, ammo joriy Gemini adapteri vision payload qabul qilmaydi; rasmni ko'rish capability'si vision provider qayta admissionigacha `HOLD`
- **Rasm chizadi** 🎨 — flashcard/diagramma so'rasangiz SVG chizib beradi (qat'iy xavfsizlik filtridan o'tadi)
- **Smart onboarding** — ro'yxatdan o'tgach AI bilan qisqa suhbatda maqsad/daraja aniqlanadi (forma o'rniga)
- **Floating widget** — istalgan sahifadan AI'ga tez murojaat

### 👨‍🏫 O'qituvchi paneli (`/teacher/`)
- **Tekshirish navbati** — kutayotgan imtihonlar va uy vazifalari bir joyda; imtihonni bo'limma-bo'lim baholash (per-esse ball+izoh, ballar jonli jamlanadi), tasdiqlash sertifikatgacha olib boradi
- **Davomat olish** — guruh+dars tanlab bir sahifada belgilash
- Guruhlar, o'quvchilar (progress/qidiruv), kontent muharrirlariga ko'prik, blog studiya

### 🛡 Backoffice (`/backoffice/`)
- Platforma holati (KPI, kutilayotgan to'lovlar, AI RAG index holati), foydalanuvchilar, chat monitoring, kurs/dars/imtihon muharrirlari

### 🎓 Study in Turkey (`/sit/`)
- Turkiya universitetlari katalogi, fakultet va dasturlar, kontrakt narxlari, qabul talablari, hujjatlar, e'lonlar va qo'llanmalar
- Shahar, universitet turi, ta'lim tili, daraja, narx va qabul holati bo'yicha server-side filter
- Public qabul/narx ma'lumotlari rasmiy manba va oxirgi tekshirilgan sanasiz nashr qilinmaydi

### 💬 Messenger
- AI / guruh / tutor chatlari — WebSocket real-time, fayl almashish (rasm preview bilan), AI javoblariga feedback + qayta-generatsiya

---

## Tez boshlash (lokal)

```bash
# 1. Klonlash va muhit
git clone https://github.com/azurebek/azurelms.git
cd azurelms
python -m venv venv
.\venv\Scripts\Activate.ps1 # Windows PowerShell (Linux/Mac: source venv/bin/activate)
pip install -r requirements.txt

# 2. Sozlamalar — .env.local fayl yarating:
#    APP_ENV=local
#    LOCAL_USE_REMOTE_SERVICES=False
#    USE_S3=False
#    AI_CHAT_PROVIDER=gemini
#    AI_FREE_TIER_MODE=True
#    GEMINI_FREE_MODEL_ALLOWLIST=gemini-3.1-flash-lite,gemini-2.5-flash-lite
#    GEMINI_PRIMARY_MODEL=gemini-3.1-flash-lite
#    GEMINI_FALLBACK_MODEL=gemini-2.5-flash-lite
#    GEMINI_API_KEY=                 (AI kerak bo'lsa Google AI Studio kaliti)
#    AI_ALLOW_DIGITALOCEAN=False     (owner production admissionigacha o'zgartirmang)
#    DIGITALOCEAN_INFERENCE_API_KEY= (pre-production'da bo'sh qoldiring)

# 3. Baza va admin
$env:APP_ENV='local'         # Linux/Mac: export APP_ENV=local
python manage.py migrate
python manage.py createsuperuser

# 4. Ishga tushirish (WebSocket bilan)
python manage.py runserver   # yoki: daphne core.asgi:application
```

Ochish: http://127.0.0.1:8000 — bosh sahifa · `/users/register/` — ro'yxat · `/teacher/` va `/backoffice/` — staff uchun.

> Celery lokalda shart emas — AI javoblari Celery yo'qligida avtomatik thread-fallback bilan ishlaydi. `Procfile` va `Dockerfile` kelajak deployment baseline'i, ammo yopilmagan security/CI/restore/health/outbox gate'lari sabab production-ready dalili emas.

## Testlar

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test        # to'liq suite
python manage.py test ai.documents courses core.tests.TeacherPanelTests   # nuqtali misollar
```

2026-08-14 post-A8 local evidence: tashqi provider kalitlari yuklanmagan offline rejimda full suite **524/524 OK**, `manage.py check` — 0 issue, migration drift — yo'q, `system_audit` — **10/10 GREEN**. Bu local evidence; production readiness uchun security/CI/restore, real DB-concurrency va alohida production admission gate'lari qoladi.

---

## Loyiha tuzilmasi

| Papka | Vazifasi |
|---|---|
| `users/` | Auth, profil, sozlamalar, dashboard, onboarding |
| `courses/` | Kurslar, darslar, **imtihon dvigateli** (sections/reading engine/attempt lifecycle), sertifikatlar |
| `cohorts/` | Guruhlar, obuna-yozilish (enrollment), davomat, to'lov cheklari |
| `messenger/` | Chat (WebSocket), AI xonalari, Smart Form sessiyalari |
| `ai/` | **AI qatlami**: agent engine, 14 skill, prompt builder, RAG, xotira, joriy Gemini va dormant DO adapteri, `documents/` (PDF/rasm/SVG) |
| `subscriptions/`, `blog/`, `gamification/`, `bot/` | Tariflar, blog+studiya, XP/nishonlar, Telegram bot |
| `sit/` | Study in Turkey universitet katalogi, dasturlar, qabul ma'lumotlari va bilim bazasi |
| `core/` | Sozlamalar, backoffice va teacher panel view'lari |
| `templates/`, `static/` | Yagona dizayn tizimi (shell'lar: public/app/teacher/admin/exam) |

## Hujjatlar (agentlar va hissa qo'shuvchilar uchun)

- **`AGENTS.md`** — AI-agentlar uchun kirish nuqtasi (birinchi shuni o'qing)
- **`nuclear-program/project-context.md`** — arxitektura wiki (Django applar, oqimlar, data model)
- **`nuclear-program/rules-for-agents.md`** — ish qoidalari (branch/commit/test tartibi)
- **`nuclear-program/marinebook.md`** — loyiha kundaligi (har major ish yozib boriladi)

Branch tartibi: `main` — himoyalangan trunk (faqat Azurbek ruxsati bilan); agentlar `claude/`, `codex/`, `antigravity/` prefiksli branchlarda ishlaydi.

---

<p align="center"><sub>AzureLMS · Turk tilini o'zbek tilida, zamonaviy tarzda 🚀</sub></p>
