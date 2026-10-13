# AzureLMS 🇹🇷

[![CI](https://github.com/azurebek/azurelms/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/azurebek/azurelms/actions/workflows/ci.yml)

**O'zbek tilida turk tili o'rgatuvchi zamonaviy LMS platforma** — AI repetitor, IELTS-uslubidagi imtihon tizimi, real-time messenger va to'liq o'quv jarayoni boshqaruvi bilan.

Django 6 · Channels (WebSocket) · Celery · Google Gemini · SQLite (lokal) · PostgreSQL + pgvector (server profili)

> **[Joriy holat va hujjatlar xaritasi →](nuclear-program/README.md)** Bajarilgan ishlar, ochiq masalalar, backoffice oqimlari va oxirgi qayd etilgan server relizi shu sahifada jamlangan. Lokal tayyorlik, serverga chiqarish va owner qabuli alohida qayd qilinadi.

DigitalOcean adapteri dormant va `AI_ALLOW_DIGITALOCEAN=False` bilan yopiq.
Joriy lokal AI profili Gemini bepul kvotasi chegaralariga rioya qiladi;
provider sozlamalari [AI supply gate](nuclear-program/launch-plan/README.md) bilan boshqariladi.

---

## Nimalar qila oladi

### 🎓 O'quvchi uchun
- **Kurslar va darslar** — modul→dars tuzilmasi, video + konspekt + topshiriq + test tablari; kirish enrollment, dars ochilishi va o'quv ketma-ketligi qoidalari bilan boshqariladi
- **Imtihonlar (5 bo'lim turi)** — Reading/Listening (8 xil boy savol turi: matching, gap-fill, T/F/NG..., avto-baholash), Writing (so'z chegaralari, per-esse o'qituvchi izohi), Speaking (brauzerda yozib yuborish), Grammar test. Fullscreen topshirish UI: taymer avto-submit, autosave, savol xaritasi, listening replay limiti, blur-proctoring
- **Sertifikatlar** — imtihondan o'tgach avtomatik; chop etiladigan sertifikat + ballar ilovasi
- **Gamifikatsiya** — XP, streak, nishonlar, guruh reytingi (podium)
- **Davomat kalendari**, to'lovlar tarixi, bildirishnomalar

### 🤖 Azure AI yordamchisi
- **Suhbat** — samimiy "o'quv-do'st" xarakteri, foydalanuvchi tanlaydigan ohang va model, uzoq muddatli xotira (faktlarni eslab qoladi), dars-kontekstli RAG javoblar
- **Skill routing** — grammatika, quiz, topshiriq va boshqa yordam promptlari tanlanadi. Bu adaptiv o'qitish natijasi isbotlangan degani emas; Gemini free-tier rejimida web-grounding o'chirilgan.
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
- **Kurs va dars tayyorlash** — kurs tuzilmasi, material, topshiriq/quiz muharrirlari va namuna.
- **O'quvchiga yordam** — kirish muammosi, topshiriq/natija va bildirishnoma yetkazilishini tekshirish.
- **Kodsiz dizayn** — qoralama, namuna, nashr va oldingi nashrga qaytish.
- Ish stoli, qidiruv va yaqindagi ishlar; to'lovlar va texnik nazoratga ruxsat doirasida kirish. Yangi oqimlar feature flaglarga bog'liq; qamrov va ochiq chegaralar [joriy holat sahifasida](nuclear-program/README.md).

### 🎓 Study in Turkey (`/sit/`)
- Turkiya universitetlari katalogi, fakultet va dasturlar, kontrakt narxlari, qabul talablari, hujjatlar, e'lonlar va qo'llanmalar
- Shahar, universitet turi, ta'lim tili, daraja, narx va qabul holati bo'yicha server-side filter
- Public qabul/narx ma'lumotlari rasmiy manba va oxirgi tekshirilgan sanasiz nashr qilinmaydi

### 💬 Messenger
- AI / guruh / tutor chatlari — WebSocket real-time, fayl almashish (rasm preview bilan), AI javoblariga feedback + qayta-generatsiya

---

## Tez boshlash (lokal)

```powershell
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
#    GEMINI_GROUNDING_ENABLED=False  (Free tier'da hard-off; env true ham override qilmaydi)
#    GEMINI_FREE_MODEL_ALLOWLIST=gemini-3.1-flash-lite,gemini-3.5-flash-lite
#    GEMINI_PRIMARY_MODEL=gemini-3.1-flash-lite
#    GEMINI_FALLBACK_MODEL=gemini-3.5-flash-lite
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

Ochish: http://127.0.0.1:8000 — bosh sahifa · `/users/register/` — ro'yxat · `/teacher/` va `/backoffice/` — tegishli rol/ruxsat uchun; barcha bo'lim har bir staff hisobiga ochilmaydi. Yuqoridagi model nomlari repo sozlamalaridir, tashqi provider mavjudligi tekshiruvi emas.

> Lokal profil remote xizmatlarsiz ishlashi mumkin. Server profilida broker/cache talablari runtime gate bilan tekshiriladi; memory fallback production kafolati emas. Web, worker, beat va outbox jarayonlari uchun [deploy yo'riqnomasini](deploy/README.md) o'qing.

## Testlar

PowerShell, loyiha virtual muhiti faollashtirilgan holda. Haqiqiy provider
kalitlari yuklanmasligi uchun **testdan oldin** xavfsiz muhitni o'rnating:

```powershell
$env:AZURELMS_SKIP_ENV_FILE='1'
$env:APP_ENV='local'
$env:LOCAL_USE_REMOTE_SERVICES='False'
$env:GEMINI_API_KEY=''
$env:TELEGRAM_BOT_TOKEN=''
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test        # to'liq suite
node --test tests/frontend_v1/*.test.mjs
```

Bu o'zgaruvchilar shu terminalda saqlanadi; odatiy lokal server uchun alohida
terminal oching. Diskdagi SQLite concurrency tekshiruvlari
`AZURELMS_TEST_FILE_DB=1`, PostgreSQL/Valkey testlari esa alohida CI profilini
talab qiladi. Buyruq, natija, sana va skip sabablari [bosqich dalillarida](nuclear-program/README.md)
hamda [marinebookda](nuclear-program/marinebook.md) qayd etiladi; eski test soni
bugungi suite soni deb talqin qilinmaydi.

---

## Loyiha tuzilmasi

| Papka | Vazifasi |
|---|---|
| `users/` | Auth, profil, sozlamalar, dashboard, onboarding |
| `courses/` | Kurslar, darslar, **imtihon dvigateli** (sections/reading engine/attempt lifecycle), sertifikatlar |
| `cohorts/` | Guruhlar, obuna-yozilish (enrollment), davomat, to'lov cheklari |
| `messenger/` | Chat (WebSocket), AI xonalari, Smart Form sessiyalari |
| `ai/` | **AI qatlami**: agent engine, skill routing, prompt builder, RAG, xotira, Gemini va dormant DO adapteri, `documents/` (PDF/rasm/SVG) |
| `subscriptions/`, `blog/`, `gamification/`, `bot/` | Tariflar, blog+studiya, XP/nishonlar, Telegram bot |
| `sit/` | Study in Turkey universitet katalogi, dasturlar, qabul ma'lumotlari va bilim bazasi |
| `core/` | Sozlamalar, backoffice va teacher panel view'lari |
| `aicontrol/`, `core/control_center/` | AI supply/policy, capability registry, audit, health va release holati |
| `library/`, `classbook/` | O'quv resurslari, dars materiallari va jonli mashg'ulot oqimi |
| `frontend/` | Public sahifalar kontenti va sozlamalari |
| `templates/`, `static/` | Yagona dizayn tizimi (shell'lar: public/app/teacher/admin/exam) |

## Hujjatlar (agentlar va hissa qo'shuvchilar uchun)

- **[Joriy holat va hujjatlar xaritasi](nuclear-program/README.md)** — loyiha bo'yicha yagona umumiy kirish.
- **[AGENTS.md](AGENTS.md)** — AI-agentlar birinchi o'qiydigan bootstrap.
- **[Arxitektura wiki](nuclear-program/project-context.md)** — Django applar, oqimlar, data model.
- **[Ish qoidalari](nuclear-program/rules-for-agents.md)** — branch/commit/test tartibi.
- **[Marinebook](nuclear-program/marinebook.md)** — sanali ishlar va dalillar tarixi.

Branch tartibi: `main` — himoyalangan trunk (faqat Azurbek ruxsati bilan); agentlar `claude/`, `codex/`, `antigravity/` prefiksli branchlarda ishlaydi.

---

<p align="center"><sub>AzureLMS · Turk tilini o'zbek tilida, zamonaviy tarzda 🚀</sub></p>
