# AzureLMS — Codex ishchi konteksti

Bu fayl Codex sessiyalari uchun **tezkor ishchi xarita**. U
[`project-context.md`](project-context.md) o'rnini bosmaydi: loyiha wiki'si keng
inventar va tarixni saqlaydi, bu hujjat esa kodga qayerdan kirish, qaysi qatlam
haqiqatni boshqarishi va o'zgarishni qanday xavfsiz tekshirishni qisqa tutadi.

**Snapshot:** 2026-09-14, `origin/main` = `ef99cb2`. Raqamlar va operatsion
holat vaqtinchalik; har sessiyada Git, marinebook va kod qayta tekshiriladi.

---

## 1. Avval qaysi haqiqatga ishonish kerak

Ish boshlash tartibi:

1. `AGENTS.md` va [`rules-for-agents.md`](rules-for-agents.md)
2. `git status --short --branch`, `git log --oneline --decorate -8`,
   `git branch -a`
3. [`marinebook.md`](marinebook.md) ning eng yangi 3–5 yozuvi
4. [`launch-plan/README.md`](launch-plan/README.md) va task tegadigan backlog
5. Task tegadigan model, canonical service/policy, adapter va testlar
6. [`project-context.md`](project-context.md) — keng arxitektura wiki'si

Product qarorida authority: Azurbekning yozilgan qarori → launch admission →
canonical service/policy/state machine → model/migration → adapter contract →
UI/copy → eski hujjat yoki chat. Kod va testga zid tarixiy matn joriy
capability hisoblanmaydi.

Ikki ma'lum dokument drift'i:

- `Procfile` hozir `outbox: python manage.py telegram_outbox --loop` processini
  o'z ichiga oladi; eski “Procfile'da outbox yo'q” qaydi joriy kodga mos emas.
- 2026-09-13 marinebook yozuvlari birinchi production deploy ishga tushganini
  aytadi. Launch-plan ichidagi “hali deploy qilinmagan” snapshotlari tarixiy.
  Bu avtomatik `PRODUCTION GO` degani emas: real server, restore, release SHA,
  webhook va readiness dalili task paytida yangidan tekshiriladi.

---

## 2. Mahsulotning to'g'ri mental modeli

AzureLMS mustaqil “AI til o'rgatuvchi SaaS” emas. U Azurbekning jonli onlayn
turk tili kursi uchun operatsion tizim:

```text
qabul → checkout/to'lov → enrollment/access → dars release
      → o'qish/mashq/vazifa → ustoz review → mock/progress/sertifikat
```

Joriy launch tezisi — 50 kishigacha boshqariladigan guruhni Classbook orqali
yuritish. Azurbek product, curriculum, pricing va `GO/HOLD/NO-GO` qarorining
yagona egasi. Web, Telegram, Mini App, Messenger, Celery va AI providerlar
alohida biznes haqiqatini yaratmaydi; ular canonical Django state va
service'larning adapterlari.

Asosiy arxitektura qoidasini har o'zgarishda tekshirish kerak:

```text
Owner / Azure Control Center
  policy · health · audit · cost · release
    canonical domain services va state machine'lar
      Web · Telegram · Mini App · WebSocket · Celery · AI provider
```

Bir qoida ikki surface'da kerak bo'lsa, adapterlarga nusxa yozilmaydi.
Canonical service chiqariladi va parity testi bilan ikkala adapter unga
ulanganligi isbotlanadi.

---

## 3. Repo va runtime snapshoti

### Stack

- Python 3.12.10, Django 6.0.8
- ASGI: Daphne 4.2.3; WebSocket: Channels 4.3.2
- Celery 5.6.2
- Local DB: SQLite, `transaction_mode=IMMEDIATE`, 15 soniya timeout, WAL
- Production DB target: PostgreSQL 16 + pgvector
- Shared runtime target: Valkey 8 / Redis-compatible cache, channel layer va
  broker
- Joriy AI: Gemini (`google-genai` 1.65.0); DigitalOcean adapteri dormant
- Telegram: Aiogram 3.30.0
- Frontend: Django template + custom CSS/JS; Bootstrap runtime yo'q

### Hajm, faqat orientir uchun

2026-09-14 snapshotida 794 tracked fayl, taxminan 75 ming qator Python, 126
template, 19 CSS va 16 JS fayl bor. Custom Django qatlamida 12 product app +
`core`; `ai/` oddiy Python package, Django app emas.

### Tekshirilgan local holat

- `manage.py check`: 0 issue
- `makemigrations --check --dry-run`: drift yo'q
- `system_audit --json --fail-on never`: 16 capability, 9 GREEN, 7 AMBER,
  0 RED
- AMBER'lar local uchun izohli: Telegram token/dispatcher yo'q, Gemini kaliti
  yo'q, RAG indekslanmagan, outbox worker belgisi yo'q, DB zaxirasi eskirgan,
  media zaxirasi yo'q
- `core.test_golden_flow_e2e` + `classbook.tests`: 24/24 OK

Local `SOURCE_VERSION` bo'lmasa release `unknown` ko'rinishi normal, lekin
productionda bu release identity nuqsoni.

---

## 4. Qatlamlar va ownership

| Qatlam | Asosiy joylar | Nima boshqaradi |
|---|---|---|
| Governance/control | `core/`, `aicontrol/` | access scope, flags, audited settings, health, supply, cost, release |
| Acquisition/billing | `subscriptions/`, `cohorts/` | plan/promo, checkout intent, receipt, enrollment, seat, attendance |
| Learning | `courses/` | course/module/lesson, release, progress, assignment, quiz, exam, certificate |
| Live lesson | `classbook/` + `bot.TelegramLessonSession` | playbook, activity snapshot, response, grading, leaderboard, finish |
| Communication | `messenger/`, `bot/`, `users.Notification` | chat, AI task, Telegram/Mini App, outbox, user-facing notifications |
| AI | `ai/`, `aicontrol/`, AI modellar `messenger/`da | skill, prompt, memory, RAG, provider, quota/supply, telemetry |
| Public content | `frontend/`, `blog/`, `sit/` | landing/brend/legal, blog, Study in Turkey katalogi |
| Presentation | `templates/`, `static/` | public/app/teacher/admin/messenger/exam/Mini App shell'lari |

`gamification/` badge/level yozuvlarini saqlaydi, lekin asosiy XP write path
`users/xp.py::award_xp()` orqali o'tadi. Sertifikatning o'quv oqimidagi
canonical modeli `courses.Certificate`; `gamification.Certificate`ni unga
avtomatik teng deb taxmin qilmaslik kerak.

---

## 5. Canonical write xaritasi

| Savol yoki mutation | Canonical joy | Adapterlar |
|---|---|---|
| O'qituvchi nimani ko'ra oladi? | `core/access.py` | teacher web, bot, attendance, Classbook |
| O'quvchi nimaga haqli? | `Enrollment.has_active_access()`, `core/entitlements.py` | web, bot, AI context |
| Checkout qaysi guruh/tarifga? | `cohorts/checkout_service.py`, `delivery_service.py` | web checkout, bot |
| Promo va invoice yaratish | `subscriptions/promo_service.py` | checkout adapterlari |
| Chekni tasdiqlash/rad etish | `cohorts/receipt_service.py` | backoffice, bot |
| A'zoni ko'chirish/promotion | `cohorts/transition_service.py`, `membership_service.py` | owner yuzalari |
| Davomat va XP | `cohorts/attendance_service.py` | teacher web, bot, Classbook |
| Dars ochish/yopish | `courses/release_service.py` | teacher, bot, Classbook |
| Darsga real kirish | `courses/access_service.py` | lesson view, bot/Mini App, AI lesson context |
| Dars progressi | `courses/progress_service.py` | web va bot |
| Vazifa/quiz submit va review | `courses/submission_service.py` | learner web/bot, teacher web |
| Exam lifecycle | `exam_service.py`, `exam_section_service.py`, `reading_service.py`, `policy_service.py`, `completion_service.py` | exam shell, teacher review |
| Jonli dars | `classbook/services.py` | teacher web, learner web, bot commands |
| Bildirishnoma | `users/notification_service.py` | web; signal orqali Telegram outbox |
| AI remote call | `aicontrol/supply.py` + `ai/agent/engine.py` | messenger, widget, bot, SmartForm, RAG/memory |
| Feature on/off | `core/flags.py` | barcha iste'molchilar |
| Vaqt/limit/threshold | singleton settings modellar + audited runtime settings surface | Control Center, worker/probe |
| Owner audit | `core/audit.py` → `SystemAuditEvent` | web, bot, worker, release |

Adapter ichida `Enrollment.objects.update(...)`, mustaqil XP hisobi, alohida
release qoidasi yoki provider oldidan supply gate'ni chetlab o'tuvchi network
call ko'rinsa, avval canonical service bor-yo'qligini tekshirish kerak.

---

## 6. Eng muhim invariantlar

### Enrollment, to'lov va entitlement

- Enrollment holati: `pending`, `active`, `expired`, `frozen`.
- Active access payment deadline'dan keyingi 2 kunlik grace'ni hisobga oladi;
  raw `status == active` yetarli tekshiruv emas.
- `pending_plan` va `checkout_started_at` — niyat, entitlement emas.
- `Enrollment.active_plan()` tasdiqlangan receipt davrini hisobga oladi;
  kelajak davr uchun oldindan to'langan tarif erta kuchga kirmaydi.
- Active va expired membership seat egallaydi; pending checkout egallamaydi.
- Bir kursga ikki effective-active enrollment ochilmaydi.
- Verified receipt, promo reservation, deadline va notification qarori
  service ichidagi transaction/lock tartibidan o'tishi kerak.

### Learning

- Darsga kirish bir vaqtning o'zida enrollment, cohort release va oldingi
  prerequisite'larni hisobga oladi. `check_lesson_access()` yoki bundle'dan
  foydalaniladi.
- Lessonni ochish uni tugatish emas; completion alohida user action/service.
- Assignment `(assignment, student)` bo'yicha yagona; review XP va
  notificationni idempotent boshqaradi.
- Exam attempt raqami student+exam uchun unique; timeout/start/save/review va
  certificate alohida service/policy'lardan o'tadi.

### Classbook

- `Exercise` reusable ta'rif, `ActivityRun.snapshot` esa dars boshlangan
  paytdagi immutable nusxa.
- Bir sessionda bir vaqtda faqat bitta `open` activity; bir learnerga bir
  activity uchun bitta `StudentResponse`.
- Answer key public payloaddan olinadi; reveal oldidan score/key chiqmaydi.
- `finish_class_session()` davomat, XP, release, homework va notificationni
  bitta canonical transaction oqimida yopadi.
- Realtime tezkor adapter; HTTP polling mobil/network fallback.

### Audit, media va outbox

- `SystemAuditEvent` append-only. Owner mutationida sabab + tasdiq + audit +
  no-op yo'l kerak.
- Public media `MEDIA_ROOT`; receipt, submission, chat attachment, speaking
  audio va Classbook media `PRIVATE_MEDIA_ROOT`da. Private faylga faqat
  `core/private_media_views.py`dagi permission view orqali kiriladi.
- Uploadda klient `content_type`i yoki kengaytmasiga ishonilmaydi;
  `core/upload_validation.py` magic-byte, profil va hajmni tekshiradi.
- `Notification` Telegram ID bo'lsa signal orqali `TelegramOutbox`ga tushadi.
  DM va Classbook group outbox lease + retry/backoff + dead-letter ishlatadi.
  Kafolat at-least-once; yuborilgandan keyin DB write oldidan worker o'lsa
  takroriy xabar ehtimoli qoladi.

---

## 7. AI oqimi va qattiq chegaralar

```text
Message / widget / bot
  → idempotency va AIResponseRun
  → AISupplyEvent pre-reservation
  → AIEngine
      skill → tool context → memory → RAG → prompt
      → bounded provider call
      → memory extraction/sanitize
  → supply reconciliation
  → AI Message + telemetry
```

Joriy contract:

- Chat provider Gemini; primary `gemini-3.1-flash-lite`, temporary fallback
  `gemini-3.5-flash-lite`.
- `gemini-2.5-flash-lite` retired va runtime'da rad etiladi.
- Logical request odatda ko'pi bilan 1 primary + 1 fallback physical attempt;
  429/quota/billing xatosi fan-out qilmay circuit ochadi.
- Free-tier mode'da API web grounding hard-off. `web_search` skill routingi
  mavjud bo'lsa ham network grounding ishlagan deb da'vo qilinmaydi.
- 14 skill bor; `image_qa` routing mavjud, ammo joriy Gemini adapteri
  `supports_vision=False`. Rasm tahlili current capability emas.
- Memory toggle off bo'lsa retrieve ham, extract/save ham o'chadi.
- RAG active enrollment course scope'idan tashqariga chiqmasligi kerak.
- RAG, memory embedding, SmartForm va guest calllari ham supply ledgerdan
  o'tadi; `AIResponseRun` faqat asosiy messenger reply telemetrysi.
- DigitalOcean adapteri kodda, lekin `AI_ALLOW_DIGITALOCEAN=False` bilan
  explicit owner admissionigacha fail-closed.

Test yoki auditda `.env.local` yuklanishi Gemini free quota'ni yeyishi mumkin.
Har doim:

```powershell
$env:AZURELMS_SKIP_ENV_FILE='1'
$env:GEMINI_API_KEY=''
$env:TELEGRAM_BOT_TOKEN=''
.\venv\Scripts\python.exe manage.py test <target>
```

`reindex_rag --force` va `reindex_ai_memory --force` remote embedding ishlatadi;
credential va budget ataylab ochilmagan bo'lsa ularni smoke sifatida
yugurtirmaslik kerak.

---

## 8. Surface va route xaritasi

- Public va aggregator: `core/urls.py`
- Student/auth/settings/dashboard: `/users/`, `users/urls.py`
- Learning/exam/certificate: `/courses/`, `courses/urls.py`
- Pricing/checkout: `/pricing/`, `/checkout/`
- Messenger: `/messenger/`; WebSocket `ws/chat/<room_id>/`
- Classbook: `/classbook/teacher/` va `/classbook/live/`; WebSocket
  `ws/classbook/<session_id>/`
- Telegram: `/bot/webhook/` va `/bot/miniapp/`
- Teacher: `/teacher/`
- Owner backoffice: `/backoffice/`; Control Center `/backoffice/control/`
- SIT: `/sit/` va `/backoffice/sit/`

ASGI `core/asgi.py`da HTTP Django app va messenger+Classbook WebSocket
routingini birlashtiradi. Har ikki consumer connectdan keyin ham accessni
qayta tekshiradi; socket ochilganini doimiy ruxsat deb qabul qilmaslik kerak.

Frontend shell'lari:

- public: `base_public.html` + `public-shell.css`
- student: `users/base_app.html` + `app-shell.css`
- teacher: `base_teacher.html` + `teacher-shell.css`
- owner: `backoffice/base.html` + `admin-shell.css`
- messenger: `messenger/ai.html` + `messenger.css`
- Mini App: `bot/miniapp_base.html` + `miniapp.css`
- exam: `courses/exam_detail.html` + `exam-shell.css`

Global token/reset qatlami `tokens.css` + `base.css` + `brand.css`. Yangi
surface Bootstrap import qilmasligi va mavjud shell/brand komponentini
chetlab o'tmasligi kerak.

---

## 9. Local va production profillari

### Local

`APP_ENV=local`, `LOCAL_USE_REMOTE_SERVICES=False` holatida:

- SQLite + filesystem
- LocMem cache + InMemory ChannelLayer
- `memory://` broker + eager Celery
- Telegram polling
- `SECURITY_STRICT=False`

Bu bitta-process development uchun ataylab yashil. Real concurrency yoki
multi-process delivery dalili emas.

### Non-local / production

`core/runtime_gate.py` non-local profilda shared cache/channel va broker
yo'q bo'lsa startupni `ImproperlyConfigured` bilan to'xtatadi. Production
compose stack:

- PostgreSQL 16 + pgvector
- Valkey 8
- one-shot migrate
- Daphne web
- Celery worker va beat
- Telegram outbox worker
- Caddy TLS/reverse proxy

Media/private-media named volume'larda; zaxiralar `deploy/backups` bind mountida.
Caddy public `/media/`ni beradi, private-media unga umuman mount qilinmaydi.
`SOURCE_VERSION` release identity uchun har deploy/update/rollbackda uzatiladi.
Docker image root emas, uid 10001 bilan ishlaydi; backup papkasi ownershipi
runbookdagi kabi tayyorlanadi.

Liveness `/healthz` tashqi service'ga tegmaydi. Readiness `/readyz` faqat
critical capability probe'larini yugurtiradi va RED bo'lsa 503 beradi. To'liq
operatsion holat `system_audit`/Control Centerda 16 capability bilan ko'rinadi.

---

## 10. Test va release xaritasi

Minimal local bazaviy tekshiruv:

```powershell
$env:AZURELMS_SKIP_ENV_FILE='1'
$env:GEMINI_API_KEY=''
$env:TELEGRAM_BOT_TOKEN=''
.\venv\Scripts\python.exe manage.py check
.\venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\venv\Scripts\python.exe manage.py test <changed-app-or-module>
git diff --check
```

Yuqori signal testlari:

- `core.test_golden_flow_e2e` — release → lesson → assignment → review → quiz
  va web/bot parity
- `core.test_attendance_parity`, `core.test_receipt_decisions` — adapter
  parity
- `classbook.tests`, `classbook.test_realtime`, `classbook.test_load` — live
  state, permission, realtime va 50 learner
- `core.test_private_media`, `core.test_upload_validation`,
  `messenger.test_socket_access_recheck` — security boundary
- `aicontrol.tests`, `aicontrol.test_supply_concurrency` — AI quota/supply;
  SQLite contention proofi uchun `AZURELMS_TEST_FILE_DB=1`

CI'dagi uch required job nomini o'zgartirish branch protectionni ham bir
vaqtda yangilashni talab qiladi:

1. `Checks va to'liq test suite (SQLite)`
2. `PostgreSQL+pgvector va Valkey smoke`
3. `Sir va bog'liqlik zaifligi skani`

`main` PR-only. O'z `codex/` branchi → test → commit (`Co-Authored-By`
majburiy) → marinebook → push → PR checks → manual merge tartibi saqlanadi.

---

## 11. Collision va regressiya xavfi yuqori joylar

- `nuclear-program/*.md`, `core/settings.py`, `core/urls.py`, `core/views.py`
- `courses/models.py`, `courses/views.py`, `cohorts/models.py`
- `messenger/models.py`, `messenger/tasks.py`, `messenger/consumers.py`
- `bot/services.py`, `bot/outbox.py`, `classbook/services.py`
- `static/js/messenger-chat.js` va asosiy shell CSS'lari

Faylga tegishdan oldin dirty diff va boshqa agent ownershipi tekshiriladi.
Bitta checkout ishlatiladi; worktree va stash ishlatilmaydi.

Yana muhim ehtiyotlar:

- Model `save()` va signal side-effectlarini o'qimasdan bulk/update yo'liga
  o'tmaslik.
- Transaction lock tartibini o'zgartirishdan oldin SQLite va PostgreSQL
  semantikasini alohida tekshirish.
- Operatsion vaqt/limit/thresholdni kodga qotirmaslik: DB settings; on/off
  uchun `core/flags.py`. Protokol limiti va safety floor istisno.
- Owner mutationida mavjud audited form/surface naqshini ishlatish;
  `AISettingsAdmin`ni audit namunasi deb ko'chirmaslik.
- “Ko'rib qoldim” refactori qilmaslik; mavjud takror/unreachable kod task
  bo'lmasa alohida qayd qilinadi, joriy diffga aralashtirilmaydi.
- Frontend o'zgarishida desktop + mobil + real interaction + console tekshiruvi
  kerak; template renderning o'zi yetarli emas.

---

## 12. Ochiq chegaralar — capability deb da'vo qilinmaydi

2026-09-14 rebaseline va koddan ko'rinadigan asosiy ochiq joylar:

- Production deploy bo'lganligi marinebookda qayd etilgan, ammo production
  `GO` — alohida owner qarori; server smoke, restore/rollback, webhook,
  release record va offsite backup dalili yangidan tekshiriladi.
- Offsite backup hali yo'q; local/EC2 diskidagi backup yagona falokat domeni.
- A4 premium service workflow/rollout tugamagan.
- A5 texnik mobil bandlari bor, real Android/iOS/desktop owner sign-off qolgan.
- A6 Learner Outcome Ledger, A7 Daily Coach/structured practice va A9 AI
  quality/cost release gate reja holatida.
- A10 AI persona va cross-room continuity reja holatida.
- SIT S1/S3/S4 foundation bor; S2 canonical inquiry lifecycle yo'q.
- AI `image_qa` vision emas; Gemini grounding free-tierda ishlamaydi.
- Alohida OS-process AI supply contention proofi va guest/SmartForm/reindex
  lease/claim K11 qarzi qolgan.
- Outbox at-least-once; exactly-once delivery da'vosi yo'q.

Backlog holati tez o'zgaradi. Yangi feature oldidan admission savollari va
eng yangi marinebook yozuvi qayta o'qiladi.

---

## 13. Taskni qayerdan boshlash

| Task | Birinchi ochiladigan joylar |
|---|---|
| Auth/profile/settings | `users/models.py`, `users/views.py`, `users/urls.py` |
| Checkout/payment | `cohorts/checkout_service.py`, `receipt_service.py`, `subscriptions/promo_service.py` |
| Enrollment/seat | `cohorts/models.py`, `delivery_service.py`, `transition_service.py` |
| Lesson/access/progress | `courses/access_service.py`, `release_service.py`, `progress_service.py` |
| Assignment/quiz | `courses/submission_service.py`, learner va teacher adapterlari |
| Exam | `courses/exam_service.py`, `exam_section_service.py`, `reading_service.py`, `policy_service.py` |
| Classbook | `classbook/models.py`, `services.py`, `access.py`, `consumers.py` |
| Messenger | `messenger/consumers.py`, `tasks.py`, `access.py`, `static/js/messenger-chat.js` |
| AI behavior | `ai/agent/engine.py`, `prompts/builder.py`, `skills/registry.py`, `aicontrol/supply.py` |
| RAG/memory | `messenger/rag.py`, `ai/rag/context.py`, `ai/memory/`, AI DB modellar |
| Telegram | `bot/services.py`, `bot/routers/`, `outbox.py`, `views.py` |
| Owner control | `core/views.py`, `core/control_center/`, `core/audit.py`, `core/flags.py` |
| Public/SIT/content | `frontend/`, `blog/`, `sit/`, tegishli template va CSS |
| Deploy/ops | `core/settings.py`, `runtime_gate.py`, `deploy/`, `Dockerfile`, CI |

Har taskda kamida model → canonical service → adapter → test zanjiri ko'riladi.
Faqat view yoki template'ni o'qib biznes qoidasi haqida xulosa qilinmaydi.

---

## 14. Bu faylni yangilash qoidasi

Quyidagilardan biri o'zgarsa fayl yangilanadi:

- canonical write owner yoki state machine
- yangi app/surface/provider
- runtime/deploy topology
- xavfsizlik, media, audit yoki supply boundary
- launch admissionning material o'zgarishi

Oddiy bugfix, CSS polish yoki test soni uchun bu fayl churn qilinmaydi.
Snapshot raqamlari yangilansa command va commit dalili bilan yoziladi.
