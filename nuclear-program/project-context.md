# AzureLMS — Loyiha konteksti

Bu hujjat loyihaning yashash kitobi (wiki). Yangi feature qo'shilsa shu yerda batafsil tushuntiriladi. Yangi agent kelishi bilan o'qiy boshlaydigan birinchi joy.

Source of truth har doim **kod** (model/view/task/URL/test). Bu fayl kodga moslab yangilab turiladi.

> **Holat qoidasi:** “Joriy holat” faqat kodda hozir mavjud va tekshirilgan narsani bildiradi. “Maqsad arxitektura” alohida belgilangan reja bo'lib, implementatsiya va test tugamaguncha mavjud capability sifatida talqin qilinmaydi.

---

## 1. Mahsulot xulosasi

**AzureLMS** — o'zbek tilida turk tili o'rgatishga qaratilgan Learning Management System. Klassik kurs/dars oqimini real-time messenger, AI tutor, RAG, memory, exam, subscription, Telegram integratsiyasi, Study in Turkey (SIT) portali va yashirin backoffice boshqaruvi bilan birlashtiradi.

**Joriy workspace:** `C:\Users\AZUREBEK\Documents\Codex\2026-08-13\new-chat\azurelms` (Windows)
**Asosiy branch:** `main` (yagona integratsiya trunk'i)
**GitHub:** https://github.com/azurebek/azurelms.git

### Foydalanuvchi rollari

| Rol | Platformadagi vazifasi |
|---|---|
| Anonymous visitor | landing, kurslar, pricing, blog, legal sahifalarni ko'radi |
| Student | kursga yoziladi, dars o'qiydi, AI bilan chat qiladi, assignment/quiz/exam ishlaydi |
| Teacher / staff | attendance, student monitoring, assignment/exam review, tutor chatlarda qatnashish |
| Admin / superuser | backoffice, Jazzmin admin, course/cohort/payment/user/chat/exam boshqaruvi |
| Azure AI | talaba savollariga javob beradi, lesson/RAG/memory/tool contextdan foydalanadi |
| Telegram bot | account linking, attendance, o'qish/topshirish, checkout/admin notification va Mini App oqimlarini platformaga bog'laydi |

### Asosiy oqim (8 qadam)

1. Talaba ro'yxatdan o'tadi.
2. Kurs yoki tarif tanlaydi.
3. Checkout orqali ariza/to'lov receipt yuboradi.
4. Admin tasdiqlaydi.
5. Talaba cohort/guruhga ulanadi (signal orqali).
6. Dashboard, darslar, quiz/assignment/exam, messenger va AI yordamchidan foydalanadi.
7. O'qituvchi/admin backoffice orqali kontent, foydalanuvchi, exam va chatlarni boshqaradi.
8. Telegram bot account linking, attendance, o'qish/topshirish, checkout/admin xabarlari va Mini App oqimlarini platformaga bog'laydi.

---

## 2. Tech stack

### Backend

| Qism | Texnologiya |
|---|---|
| Web framework | Django 6.0.2 |
| Local Python | venv Python 3.12.13 |
| Docker Python | `python:3.12-slim` (major/minor mos) |
| ASGI | Daphne 4.2.1 |
| WebSocket | Django Channels 4.3.2 |
| Tasks | Celery 5.6.2 |
| Local task mode | `memory://` broker + eager tasks |
| Cache / channel future prod | Redis/Valkey via `REDIS_URL`, `VALKEY_URL` yoki component vars |
| DB local | SQLite `db.sqlite3` |
| DB future prod | PostgreSQL, SSL required |
| Vector search | pgvector in prod, JSON/cosine fallback in code |
| Rich text | django-ckeditor-5 |
| Admin | Jazzmin + optional legacy `/admin/` (faqat `ENABLE_LEGACY_ADMIN=True` bo'lsa) |
| Storage | joriy local filesystem; S3-compatible adapter mavjud, pre-production'da o'chiq |
| Static | Whitenoise compressed static |

### AI

| Qism | Texnologiya |
|---|---|
| Joriy chat provider | `AI_CHAT_PROVIDER=gemini`; oddiy chat Gemini'ga boradi, Free tier API grounding hard-off |
| Qo'llab-quvvatlanadigan adapter | DigitalOcean Serverless Inference adapteri kodda bor, ammo `AI_ALLOW_DIGITALOCEAN=False` defaulti bilan owner admissionigacha provider factoryda fail-closed HOLD |
| Chat models | Primary `gemini-3.1-flash-lite`; temporary fallback `gemini-2.5-flash-lite`; free allowlist shu 2 ta, logical request maksimum 2 physical attempt |
| Embedding | `gemini-embedding-001`, 768 dimensions |
| Web search | Free tier'da Gemini `google_search` qat'iy o'chiq: explicit/medium so'rov ham bitta plain 3.1 Lite chat request bo'ladi va “live tekshira olmayman” qoidasi ishlaydi. Grounding faqat `AI_FREE_TIER_MODE=False` + explicit admission bilan qaytadi |
| Global supply | `AISupplyEvent` reservation/reconciliation + `AISupplyState` 429 cooldown; daily/minute request va daily token internal hard budget |
| Memory | structured `AIMemoryFact`, traces, summaries, semantic scoring |
| RAG | `LessonRAGChunk`, course/lesson scoped retrieval |

### Deployment

**2026-08-14 owner qarori:** joriy bosqich LOCAL/PRE-PROD. DigitalOcean hosting, Spaces va Serverless Inference ishlatilmaydi; production platforma/provider tanlovi HOLD. Local profil SQLite + filesystem + LocMem/InMemory + eager tasks bilan ishlaydi; Telegram mode `polling`, bot esa alohida `python manage.py runbot` process'i bilan boshlanadi. Quyidagi Procfile/Dockerfile faqat kelajak production baseline'i, production readiness isboti emas.

**Procfile:**

```procfile
release: python manage.py migrate --noinput
web: daphne -b 0.0.0.0 -p $PORT core.asgi:application
worker: celery -A core worker -l info
beat: celery -A core beat -l info
```

**Joriy cheklov:** Procfile'da `telegram_outbox --loop` process'i yo'q. Webhook production'da notification DM'lari uchun bu alohida process kerak; maqsad gate `launch-plan/05-launch-ops.md`da.

**Dockerfile:**
- Base image: `python:3.12-slim`
- Installs `libpq-dev`, `gcc`, `ffmpeg`
- Runs `collectstatic` with in-memory SQLite URL
- Starts Daphne on port 8080

---

## 3. Django apps va mas'uliyat

### `users`

**Mas'uliyat:** Auth, profile, settings, dashboard, notifications, attendance views, exam shell URL'lari (`users/exam_urls.py`), certificates.

**Asosiy modellar:**
- `CustomUser` — email + telegram_id + total_xp + AI sozlamalari
- `UserOnboarding` — registration wizard javoblari
- `Notification`, `NotificationBroadcast`

**`CustomUser` AI sozlamalari:**

| Field | Choices |
|---|---|
| `ai_tone` | `friendly` (default), `formal`, `brief`, `detailed` |
| `ai_model` | Gemini model sluglari |
| `ai_memory_enabled` | memory retrieve/extract to'liq on/off |
| `ai_web_search_effort` | `light` (default), `medium`, `heavy` |

### `courses`

**Mas'uliyat:** Course catalog, lesson detail, assignment/quiz/exam lifecycle, certificate generation va gradient covers.

**Asosiy modellar:**
- `Course`, `Module`, `Lesson`
- `Assignment`, `AssignmentSubmission`
- `CohortLessonRelease`, `LessonProgress`
- `Quiz`, `Question`, `Choice`, `QuizAttempt`, `QuizAnswer`
- `Exam`, `ExamSection`, `ExamAttempt`, `ExamSectionAttemptState`, `ExamSectionReview`
- Reading engine: `ReadingPassage`, `ReadingTask`, `ReadingItem`, `ReadingOption`, `ReadingAcceptedAnswer`, `ReadingResponse`
- `StudentAnswer`, `Certificate`

**Muhim qoidalar:**
- `LessonProgress` enrollment'ga bog'lanadi
- `CohortLessonRelease` cohort bo'yicha dars ochilgan/yopilganini boshqaradi
- `Course` certificate requirements (assignment approvals, lesson completion %, attendance %)
- `Lesson.video_url` YouTube embed URL'ga aylantiriladi (⚠️ owner embed bloklasa platforma majburlab ocholmaydi)

### `cohorts`

**Mas'uliyat:** Cohort va guruhlar, enrollment status va payment lifecycle, checkout, attendance.

**Asosiy modellar:**
- `Cohort`, `Enrollment`, `EnrollmentTransition`
- `PaymentReceipt`, `Attendance`

**Enrollment status:**

| Status | Ma'no |
|---|---|
| `pending` | to'lov/ariza kutilmoqda |
| `active` | faol access |
| `expired` | to'lov muddati o'tgan |
| `frozen` | vaqtincha muzlatilgan |

**Access grace:** `ENROLLMENT_ACCESS_GRACE_DAYS = 2` — active enrollment'ning next payment deadline'i grace'dan oldin bo'lsa effective status `expired`'ga tushadi.

### `messenger`

**Mas'uliyat:** Chat rooms (AI/group/tutor), WebSocket real-time messaging, room list, pin/unread state, attachments, edit/delete, AI feedback, AI response run telemetry, memory DB models, RAG chunks.

**Asosiy modellar:**
- `ChatRoom`, `Message`, `ChatRoomUserState`
- `AILongTermMemory` (legacy), `AIMemoryFact`, `AIMemoryTrace`, `AIConversationSummary`
- `AIResponseRun`, `LessonRAGChunk`, `AIFeedback`

**Room types:**

| Type | Behavior |
|---|---|
| `ai` | 1 user + Azure AI, AI har user xabariga javob beradi |
| `group` | cohort chat, `@azure` mention bo'lsa AI ham javob beradi |
| `private` | tutor/student 1:1 chat |

### `ai/` (package, Django app emas)

AI stack'ning asosiy package'i. To'liq batafsil 5-bo'limda.

```text
ai/
├── agent/    engine.py, types.py
├── memory/   evaluation, extractor, policy, repository, retriever, semantic, service, summarizer, types
├── prompts/  builder.py
├── providers/ gemini.py, digitalocean.py, provider factory
├── rag/      context.py
├── skills/   registry.py + 14 ta SKILL.md
└── tools/    context.py
```

### `aicontrol`

**Joriy mas'uliyat:** per-user AI token allowance va project-wide remote supply siyosati/admin amallari. `AISettings` per-user defaultlar bilan birga global supply enforcement, daily/minute request, daily token, cooldown, guest/heavy switchlarini saqlaydi. `AIPlanPolicy`, `AIUserAllowance`, `AIUsageResetEvent` product allowance/auditini; `AISupplyEvent` har logical remote call reservation/reconciliation'sini; `AISupplyState` global provider circuit'ini saqlaydi.

**Joriy UI:** `/backoffice/ai-control/` token usage, global/plan limit va reset/bonusni boshqaradi; blocked userlar sonini ko'rsatadi, lekin shu sahifada per-user block mutation'i yo'q. Per-user blok amali bot yoki admin orqali. `default_model` va `default_effort` modelda saqlanadi, ammo runtime provider ularni o'qimaydi va template ularni edit input sifatida render qilmaydi.

**Joriy Control Center foundation (2026-08-14):** owner-only `/backoffice/control/` `core/control_center/`dagi bitta read-only capability registry va snapshot servisidan foydalanadi. DB, cache, Channels, Celery config, Telegram outbox, media, AI provider/effective token policy, RAG, security va release identity GREEN/AMBER/RED sabab bilan ko'rinadi. AI probe free-tier/DO admission, supply enforcement, daily request/token va minute request used/limit/remaining, attempt/event holati va cooldownni ham ko'rsatadi. Shu snapshot terminalda `python manage.py system_audit [--json] [--fail-on red|amber|never]` orqali ishlaydi; web va CLI alohida health mantiq yozmaydi.

**Joriy chegarasi:** Control Center foundation mutation qilmaydi. Supply policy `AISettingsAdmin` orqali edit qilinadi, `AISupplyEvent`/`AISupplyState` adminlari read-only. Append-only umumiy `SystemAuditEvent`, system-wide feature flag/kill switch, active worker/beat heartbeat, `ReleaseRecord`, backup/email/memory probe, money cost ledger va AI quality release gate hali mavjud emas. `/backoffice/ai-control/` compatibility control path sifatida Control Center'dan ochiladi, lekin hozircha alohida sahifa.

**2026-08-14 A8 holati:** **`IMPLEMENTED/TESTED — LOCAL REGRESSION GREEN`**. Supply/provider/caller target testlari va provider credential/env-file loading o'chirilgan full suite 527/527 o'tgan; local `system_audit` 10/10 GREEN. Bu production readiness yoki SQLite/PostgreSQL true concurrent contention proof emas. Shu sanadagi `AzureAI` Free-tier AI Studio snapshoti: 3.1 Flash Lite `15 RPM / 250K input TPM / 500 RPD`; 3.7 Flash `5 RPM / 250K input TPM / 20 RPD`. Tashqi quota account/project holatiga bog'liq va dynamic.

### `subscriptions`

**Mas'uliyat:** Pricing plans, plan features, promo campaigns, promo codes, redemptions.

**Asosiy modellar:** `Plan`, `PlanFeature`, `PromoCampaign`, `PromoCode`, `PromoRedemption`

**Promo qo'llab-quvvatlaydi:**
- percent/fixed/set-price discounts
- campaign status, max redemption limits
- assigned user-specific codes
- first purchase / renewal behavior
- plan/course/cohort scoping

### `frontend`

**Mas'uliyat:** Landing/about page content, site settings, navigation items, legal pages, auth page settings.

**Singleton pattern:** `LandingPage`, `AboutPage`, `SiteSettings`, `AuthPageSettings`, `LegalPage`.

**Landing to'liq admin nazorati (2026-07-27):** `templates/index.html` (bosh sahifa) endi kontentini to'liq admin modellaridan oladi — ilgari v2 redizayn deyarli hammasini hardcode qilgan edi. Manbalar: `LandingPage` singleton (rail, hero, demo dashboard, daraja yo'li/AI/imtihon/sertifikat sarlavha va demo matnlari, pastki CTA/footer — ~50 maydon), child modellar `LandingLevelStage` (daraja bosqichlari), `LandingAIFeature` (AI xususiyatlari), `LandingExamSkill` (imtihon kartalari), `Statistic` (animatsiyali `numeric_value`/`suffix`/`decimals`), footer ustunlari `LandingNavItem` (`footer_*_links`), brend `SiteSettings`. Migratsiya `0020` joriy nusxani seed qiladi. Faqat demo dashboard sidebar navi va PATH jadval sarlavhalari ataylab statik (strukturaviy chrome).

**Brend assetlari (2026-07-22):** `SiteSettings` to'rtta rasm maydonini saqlaydi — `logo_image` (yorug' fon wordmark), `logo_dark_image` (qorong'i fon wordmark), `logo_mark_image` (ixcham kvadrat belgi), `favicon_image`. Rasm bo'lmasa `logo_mark_text` + `brand_name` matnli fallback ishlaydi. Barcha logo yuzalari `templates/components/brand_logo.html` canonical adapteri orqali o'qiydi (`use_wordmark`, `dark`, `mark_only`, `mark_class`, `name_class`, `image_class` parametrlari); favicon uchun `templates/components/brand_favicon.html`. Qiymatlar global `frontend.context_processors.site_settings_context` orqali `site_settings` nomida yetkaziladi. `core.test_brand_control.BrandSurfaceContractTests` yangi shell canonical komponentni chetlab o'tsa testni yiqitadi.

### `blog`

**Mas'uliyat:** Public blog list/detail, staff-only blog studio, tags, views/read tracking, claps, comments va likes.

**Asosiy modellar:** `BlogHomeSettings`, `BlogTag`, `BlogPost`, `BlogPostRead`, `BlogPostClap`, `BlogComment`, `BlogCommentLike`

### `sit`

**Mas'uliyat:** Study in Turkey public portali — Turkiya universitetlari katalogi, fakultet/dastur/kontrakt ma'lumotlari, qabul holati, hujjatlar, e'lonlar va bilim bazasi.

**Asosiy modellar:**
- `University` — universitet identity, shahar/tur, qabul holati, kontrakt minimumi, nashr va source verification
- `UniversityFaculty` → `UniversityProgram` — fakultet, daraja, ta'lim tili, davomiylik va kontrakt
- `UniversityPreparationCourse`, `UniversityRequirement`, `UniversityDocument`, `UniversityServiceItem`, `UniversityMedia`
- `Announcement`, `KnowledgeArticle`

**Public contract:** faqat `is_published=True` universitet va qo'llanmalar ko'rinadi. Nashr qilish uchun rasmiy `source_url` va `last_verified_on` majburiy; bu vaqtga sezgir qabul/narx ma'lumotini manbasiz chiqarishni bloklaydi. Katalog `q`, universitet turi, shahar, til, daraja, narx va qabul holati bo'yicha server-side filter qiladi. Prototip `playground/SIT/`da referens sifatida qoladi; runtime `templates/sit/`, `static/css/sit.css`, `static/js/sit-theme.js`.

### `bot`

**Mas'uliyat:** Telegram webhook/polling, account linking, student workspace, attendance, lesson/assignment/quiz oqimlari, payment receipt, notification outbox, AI va Mini App adapterlari.

**Asosiy modellar:** `TelegramLessonSession`, `TelegramLessonCheckIn`, `TelegramOutbox`, `BotPendingAction`, `BotGuest`, broadcast/payment yordamchi holatlari.

**Commands:**
- `python manage.py runbot` (polling)
- `python manage.py setwebhook` (production)
- `python manage.py telegram_outbox --loop` (notification DM worker; hozir Procfile'ga ulanmagan)

### `gamification`

**Mas'uliyat:** Levels, badges, earned badges, certificate-like gamification records.

**Asosiy modellar:** `Level`, `Badge`, `EarnedBadge`, `Certificate`

**O'quv seriyasi (streak) — 2026-07-23:** `users.LearnerStreak` (OneToOne) o'quvchining kunlik faollik seriyasini saqlaydi. Seriya DAVOMATDAN emas, o'quvchining o'z tashabbusi bilan qilgan **kunlik malakali o'quv harakatidan** oshadi (dars tugatish, quiz/vazifa topshirish, imtihon urinishi, present/partial davomat). Yagona canonical yozuv nuqtasi — `users.streak.record_activity`; adapterlar faqat shuni chaqiradi. Kun asosida idempotent; freeze bir kunlik bo'shliqni qoplaydi. `CustomUser.streak_days` property jonli qiymat beradi (buzilgan bo'lsa 0). Undash: `users.streak_nudge` mascot bildirishnomalari (holat × kun vaqti xabar banki `users.streak_messages`), Celery beat `users.tasks.run_streak_nudges` (kechqurun, `ENABLE_STREAK_NUDGE_BEAT`). Kunlik bitta streak bildirishnomasi event-bound: harakatdan keyin joyida tabrikка aylanadi va ro'yxat tepasiga chiqadi. `Notification.CATEGORY_STREAK` shu turdagi bildirishnomalar uchun.

### `core/` (project settings + backoffice)

**Mas'uliyat:** Django project settings, URLs, ASGI/WSGI, Celery config, **yashirin backoffice views**.

**Asosiy fayllar:** `settings.py`, `urls.py`, `asgi.py`, `wsgi.py`, `celery.py`, `views.py` (backoffice), `custom_storage.py`.

---

## 4. Foydalanuvchi oqimlari

### 4.1 Visitor → Student

1. Visitor landing/course/pricing/blog sahifalarni ko'radi.
2. `users/register/` orqali ro'yxatdan o'tadi.
3. `UserOnboarding` javoblari saqlanishi mumkin.
4. Login bo'lgach `dashboard`'ga yo'naltiriladi.

### 4.2 Checkout / Enrollment

1. User pricing yoki course detail'dan checkout'ga o'tadi.
2. `cohorts.checkout_view` course uchun default yoki tanlangan cohortni topadi.
3. Plan/promo tanlanadi.
4. `PaymentReceipt` yaratiladi.
5. Admin receipt'ni tasdiqlaydi.
6. `Enrollment` active bo'ladi.
7. `messenger.signals.setup_student_chats` orqali student chat access sync qilinadi.
8. Student group/tutor/AI room'larda ko'rina boshlaydi.

### 4.3 Learning

1. Student course detail'dan `course_study`'ga kiradi.
2. Birinchi accessible lesson topiladi.
3. `LessonDetailView.dispatch` active enrollment'ni tekshiradi.
4. Lesson release map orqali locked/unlocked state chiqadi.
5. Lesson'ga kirish `LessonProgress`'ni completed qilishi mumkin.
6. Student: video, lesson content, assignment, quiz, AI savol.

### 4.4 Assignment

1. Student lesson ichida assignment answer/attachment yuboradi.
2. `AssignmentSubmission` unique `(assignment, student)`.
3. Teacher/admin review qiladi.
4. Status: `pending`, `approved`, `needs_revision`.
5. `awarded_xp` orqali XP berilishi mumkin.

### 4.5 Quiz

1. Lesson quizlari `Quiz`, `Question`, `Choice` orqali tuziladi.
2. Student javoblarni submit qiladi.
3. `QuizAttempt` va `QuizAnswer` saqlanadi.
4. Score/XP hisoblanadi.

### 4.6 Exam (IELTS-like)

Bo'limlar: listening, reading, writing, speaking.

1. Student exam detail'ga kiradi.
2. `StartExamView` attempt yaratadi yoki davom ettiradi.
3. Section state endpoint'lari timer/section progress'ni beradi.
4. Javoblar `SaveExamAnswerView` orqali saqlanadi.
5. Review flag toggle bo'lishi mumkin.
6. Blur warning loglanadi.
7. Submit exam yakunlaydi.
8. Result/review/certificate views ishlaydi.

### 4.7 Messenger

Uch asosiy tajriba: AI suhbat, group chat, tutor/private chat.

**HTTP endpoints:** room list, messages fetch, pin/unpin, upload attachment, edit/delete, feedback.

**WebSocket endpoint:** `ws/chat/<room_id>/`

**Client send payload:**

```json
{
  "action": "message",
  "message": "Savol matni",
  "context_lesson_id": 123,
  "ai_skill": "lesson_explainer",
  "client_message_id": "client-generated-id"
}
```

**AI retry payload:**

```json
{
  "action": "retry_ai_response",
  "user_message_id": 456
}
```

**Server event types:**

| Event | Maqsad |
|---|---|
| `message` | yangi chat message |
| `message_update` | edit/delete/update |
| `ai_status` | AI running/succeeded/failed state |

### 4.8 AI Chat

```text
WebSocket receive
  → Message create
  → room group echo
  → if room_type == ai or text contains @azure
  → generate_ai_response Celery task
  → AIResponseRun idempotency check/create
  → main provider supply pre-reservation
  → AIEngine.generate_reply
      → memory/RAG auxiliary calls (supply-gated, fail-soft)
      → reserved provider call + reconciliation
  → Message create is_ai_response=True
  → AIResponseRun succeeded/fallback/failed
  → broadcast AI message + status
```

AI room nomi birinchi prompt'dan avtomatik o'zgarishi mumkin (`maybe_name_ai_room_from_first_prompt`).

### 4.9 Telegram bot integratsiyasi

- F0–F9 va Mini App foundation kod/testlarda mavjud: account linking, role-aware menyu, attendance, course/lesson/assignment/quiz oqimlari, checkout/admin bildirishnomalari, broadcast va AI boshqaruvlari.
- Local'da polling default. Production webhook, unique secret, doimiy outbox process va prod bot admission'i production qayta ochilguncha HOLD.
- Teacher `/start_lesson` qiladi → `TelegramLessonSession` yaratiladi; talabalar check-in qiladi → `TelegramLessonCheckIn`; natija LMS `Attendance`ga bog'lanadi.
- Multi-step assignment/quiz holati DB'dagi `BotPendingAction` orqali restart-safe saqlanadi.
- Guest AI demo `AISettings.guest_demo_enabled=False` bilan default-off va 5 savol counteriga ega. Owner yoqsa runtime call `AISupplyEvent.CALL_BOT_GUEST` orqali global pre-reservation/reconciliation'dan o'tadi; injected provider faqat test seam'i. Counter update'i uchun to'liq concurrent lock/lease hali yo'q.

### 4.10 Backoffice

Custom yashirin admin URL'lari:

```
/backoffice/
/backoffice/control/                 # faqat active superuser
/backoffice/control/ai-kill-switch/  # faqat owner; AI remote chaqiruvlarini to'xtatish
/backoffice/control/brand/           # faqat active superuser; markaziy brend/logo
/backoffice/landing/                 # faqat owner; landing phase-1 editor
/backoffice/users/
/backoffice/chats/
/backoffice/courses/new/
/backoffice/courses/<id>/
/backoffice/lessons/
/backoffice/lessons/<id>/
/backoffice/exams/
/backoffice/exams/<id>/
/backoffice/sit/
/backoffice/sit/universities/
/backoffice/sit/universities/<id>/
/backoffice/sit/announcements/
/backoffice/sit/guides/
```

Access helper: `core.views._is_backoffice_user`. Legacy `/admin/` faqat `ENABLE_LEGACY_ADMIN=True`.

**Joriy permission cheklovi:** `_is_backoffice_user` `is_staff` yoki `is_superuser`ni qabul qiladi; AI global control ham shu gate ortida. `/backoffice/control/` esa alohida `_is_control_center_owner` orqali faqat active `is_superuser`ga ochiladi va hozir read-only. Teacher scope 2026-08-15 dan default-deny: `core.access.teacher_course_queryset()` / `teacher_cohort_queryset()` yagona manba — superuser hammasini, qolgan har kim faqat `Course.instructor` sifatida biriktirilgan kurslarini ko'radi, anonim yoki nofaol foydalanuvchi hech nima ko'rmaydi. Web teacher paneli (8 view), Telegram bot (`/guruhlarim`, `/baholash`) va `AttendanceManageView` shu scope'ni iste'mol qiladi; adapterlarda alohida nusxa yo'q.

### 4.11 Study in Turkey (SIT)

1. Visitor `/sit/`da real published universitetlar, e'lonlar va qo'llanmalarni ko'radi.
2. `/sit/universities/` katalogi GET filterlari bilan universitetlarni server-side saralaydi; default qabul holati `open`.
3. `/sit/universities/<slug>/` universitet, fakultet/dastur, tayyorlov kursi, talab/hujjat/xizmat va media bloklarini bitta detailda beradi.
4. Har public universitet va qo'llanmada rasmiy manba hamda oxirgi tekshirilgan sana ko'rinadi.
5. Hujjat topshirish CTA login qilingan userni tutor messengerga, AI CTA esa mavjud Azure AI messengerga olib boradi. `sit_advisor` published SIT katalog tool'i bilan mavjud; canonical inquiry/payment/help lifecycle (S2) keyingi slice.
6. Owner-only `/backoffice/sit/` universitetlar va ularning fakultet/dastur/talab/hujjat/xizmat/media qismlari, e'lonlar va qo'llanmalarni audit sabab bilan boshqaradi. 90 kundan eski public universitet ma'lumoti dashboardda tekshiruv signali oladi.
7. SIT bosh sahifasidagi e'lonlar faqat `is_published=True` va `show_on_home=True` bo'lsa chiqadi; oddiy publish yozuvni avtomatik featured qilmaydi.

### 4.12 Maqsad operatsion arxitektura — foundation mavjud, control plane tugamagan

Owner-only Azure Control Center'ning read-only registry/snapshot qatlami joriy URL xaritasiga qo'shildi. Mutation/audit/flag/release qatlamlari, canonical lesson/enrollment state machine'lari, private media, broker fail-fast va CI/release gates rejasi `launch-plan/02-yol-xarita.md`, `03-mahsulot-backlog.md` va `05-launch-ops.md`da qoladi. Ular kod, migration, test va browser/production evidence tugamaguncha mavjud capability hisoblanmaydi.

---

## 5. AI agent arxitekturasi

### 5.1 `AIEngine.generate_reply` oqimi (`ai/agent/engine.py`)

1. **Skill tanlash:** `SkillRegistry.select_for_request` — keyword + priority + lesson boost + medium/heavy effort'da pair detection
2. **Tool context build:** `ToolContextService.build` — backend snapshot
3. **User question sanitize:** `<SAVE_MEMORY>` injection'dan tozalash
4. **Conversation context:** recent dialogue (last 8) + rolling summary
5. **Relevant memory:** top-7 fakt (lexical/semantic/vector scoring)
6. **RAG context:** pgvector → fallback dot-product
7. **Prompt build:** system + tone + skill instr + memory + summary + lesson + RAG + tool + user question. `is_first_message` flag salomlashish qoidasi uchun
8. **Provider call:** task yaratgan main supply reservation routingdan keyin `chat` yoki `web_search`ga aniqlashtiriladi, so'ng `execute_reserved_provider_call(...)` providerga chiqadi va usage/attempt bilan reconcile qiladi. Direct engine test/custom caller bo'lsa `execute_provider_call(...)` o'zi reserve qiladi. Joriy `AI_CHAT_PROVIDER=gemini` sabab oddiy chat ham Gemini'ni ishlatadi; “Gemini faqat web search” farazi joriy runtime uchun to'g'ri emas.
9. **Memory extraction:** AI reply ichidagi `<SAVE_MEMORY>` taglar
10. **Memory save:** `AIMemoryFact` dedupe + trace
11. **Reply sanitize:** markdown/source/greeting cleanup (`_sanitize_reply` — `(Manba N)` strip, trailing `Manbalar:` strip, follow-up'da leading salom strip)
12. **`AIResponse` return:** text, model, skill slug, metadata

### 5.2 Skills (14 ta)

| Slug | Trigger keywords | Tools | Priority |
|---|---|---|---|
| `smart_form` | structured conversational form | — | 100 |
| `general_chat` | (default) | student_progress, course_navigator | 0 |
| `sit_advisor` | universitet, qabul, kontrakt narxi/to'lovi, viza | sit_catalog | 95 |
| `lesson_explainer` | tushuntir, dars, mavzu, izohlab ber | lesson_context, course_navigator | 20 |
| `quiz_generator` | quiz, test, savol tuz, mashq tuz | lesson_context, quiz_context | 80 |
| `homework_checker` | homework, vazifa, tekshir, baholab ber | lesson_context, homework_context, student_progress | 70 |
| `grammar_corrector` | grammar, grammatika, xato, tuzat, zamon | lesson_context | 65 |
| `speaking_coach` | speaking, gapirish, talaffuz, og'zaki | lesson_context, student_progress | 60 |
| `writing_feedback` | writing, essay, insho, paragraph | lesson_context, homework_context | 60 |
| `course_navigator` | qaysi dars, keyingi dars, roadmap | course_navigator, student_progress | 50 |
| `student_progress_coach` | progress, natija, kuchsiz joy, reja tuz | student_progress, course_navigator | 55 |
| `image_qa` | rasm, surat, skrinshot, chiz | lesson_context | 76 |
| `document_qa` | PDF, hujjat, fayl, xulosa | lesson_context | 75 |
| `web_search` | qidir, bugungi, kursi qancha, ob-havo, yangiliklar | web_search | 90 |

`image_qa` tanlanishi vision mavjud degani emas. Joriy `GeminiProvider.supports_vision=False`, shuning uchun upload qilingan rasm payloadi providerga uzatilmaydi; rasmni ko'rish dormant vision provider yoki yangi adapter admissionigacha `HOLD`. Matndan SVG chizish so'rovi alohida document-safety oqimi.

**Tanlash mantig'i:**
- Explicit `requested_skill_slug` bo'lsa shu olinadi
- Aks holda keyword scoring + priority
- Medium/heavy web search effort time-sensitive query'ni `web_search`'ga yo'naltiradi
- Lesson context bor bo'lsa `lesson_explainer`'ga +2 boost

### 5.3 Memory subsystem

| Fayl | Vazifa |
|---|---|
| `ai/memory/policy.py` | skip rules, sensitive filter, category infer |
| `ai/memory/extractor.py` | `<SAVE_MEMORY>` parser |
| `ai/memory/repository.py` | DB I/O, dedupe fingerprint, decay/archive maintenance |
| `ai/memory/semantic.py` | lexical + alias + vector score |
| `ai/memory/retriever.py` | relevant facts render + traces |
| `ai/memory/summarizer.py` | rolling conversation summary |
| `ai/memory/evaluation.py` | quality/eval report |
| `ai/memory/service.py` | facade |

**DB:** `AIMemoryFact`, `AIMemoryTrace`, `AIConversationSummary`

**User controls (`/users/settings/ai-memory/`):**
- Toggle enabled/disabled
- Archive fact
- Reject fact (negative signal)
- Clear all

### 5.4 RAG (`messenger/rag.py`)

**DB:** `LessonRAGChunk`

**Index:**
- Chunk size: ~180 words
- Overlap: 40 words
- Embedding: `gemini-embedding-001`, 768d
- pgvector mavjud: SQL `<=>` (cosine) + ivfflat indeks
- Aks holda: JSON embedding + Python cosine fallback

**Scope:**
- User active enrollment course ID'lari bilan cheklanadi
- Staff/superuser kengroq access
- `context_lesson` bo'lsa: 0.08–0.12 boost

**Commands:**

```powershell
python manage.py setup_rag_pgvector
python manage.py reindex_rag --force
python manage.py reindex_rag --course-id <id> --force
python manage.py reindex_ai_memory --force
```

Embedding cache: 7 kun.

Cache miss bo'lsa `embed_texts` bitta remote batchdan oldin supply reservation qiladi, SDK retry'siz chaqiradi va usage metadata bo'lmasa konservativ token reservationni charge qiladi. RAG query `rag_embedding`, memory query/write `memory_embedding`, lesson/manual reindex esa `reindex` call type'ida. Cache hit remote request va supply yozuvi sarflamaydi. Supply denial/provider xatosida query cache/lexical/no-vector yo'liga yumshoq degradatsiya qiladi; memory write fakti vektorsiz saqlanadi. Lesson reindex eski chunklarni yangi embedding tayyor bo'lmaguncha o'chirmaydi, ammo parallel lesson batch'lari uchun to'liq lease/claim hali yo'q.

### 5.5 Web search effort tiers

Foydalanuvchi `/users/settings/` da tanlaydi (`CustomUser.ai_web_search_effort`):

| Tier | Behavior |
|---|---|
| `light` (default) | Faqat aniq keyword (qidir, bugungi, kursi qancha, ob-havo) |
| `medium` | Light + **pair detection**: vaqt belgisi (`hozir`/`bugun`/`kechagi`) + ma'lumot belgisi (`narx`/`kim`/`natija`) birga uchrasa majburiy web_search |
| `heavy` | Free-tier mode'da UI va mutation endpointdan chiqarilgan, runtime policy ham default-off; faqat owner `heavy_search_enabled`ni va non-free policy'ni ataylab admission qilsa ishlaydi |

Manbalar javob matnida ko'rsatilmaydi. Telemetry'da saqlanadi:
- `web_search_enabled`
- `web_search_queries`
- `web_search_sources` (URL + title)

### 5.6 Tone, model, telemetry

- **Tone:** `friendly` / `formal` / `brief` / `detailed` — prompt builder ohangni o'zgartiradi
- **Provider:** joriy local profil `AI_CHAT_PROVIDER=gemini`. DigitalOcean adapteri kodda saqlanadi, ammo pre-production'da kalitsiz/HOLD; `AI_ALLOW_DIGITALOCEAN=False` bo'lsa factory provider yaratmasdan rad etadi. Noma'lum provider ham fail-closed
- **Model:** free allowlist `gemini-3.1-flash-lite` primary + temporary `gemini-2.5-flash-lite` fallback. Userdagi eski/Pro/preview tanlov runtime va settings UI'da allowlistga clamp qilinadi. Google hozir 2.5 Flash-Lite shutdown sanasini e'lon qilmagan; 2026-10-16 ichki review deadline'ida fallback remove/migrate uchun qayta baholanadi
- **Provider bound:** SDK retry off; 429/quota/billing `1` attemptda fail-fast+circuit; boshqa xatoda jami `≤2`; output `640`, prompt `12,000` belgi, timeout `8s`, deadline `20s`
- **Telemetry:** `AIResponseRun` main messenger javobining status/model/skill/duration/token/context va idempotency'sini saqlaydi. Alohida `AISupplyEvent` chat/search/SmartForm/guest/RAG-memory embedding/reindexning reserved/actual request-token, failure va user/call-type accountingini saqlaydi; `AISupplyState` cooldown circuit holati. Control Center aggregate snapshot beradi

---

## 6. Data model relationship map

```text
CustomUser
  ├─ Enrollment → Cohort → Course → Module → Lesson
  ├─ AssignmentSubmission → Assignment → Lesson
  ├─ LessonProgress → Enrollment + Lesson
  ├─ ChatRoom participants
  ├─ AIMemoryFact / AIMemoryTrace / AIResponseRun
  └─ Notification

Course
  ├─ Module → Lesson
  ├─ Cohort
  ├─ Exam
  ├─ LessonRAGChunk
  └─ PromoCampaign scope

Cohort
  ├─ Enrollment
  ├─ ChatRoom (room_type=group)
  ├─ PaymentReceipt
  ├─ Attendance
  └─ Telegram group fields

ChatRoom
  ├─ Message
  ├─ ChatRoomUserState
  ├─ AIConversationSummary
  └─ AIResponseRun

Message
  ├─ context_lesson
  ├─ AIFeedback
  └─ AIResponseRun (as user_message / ai_message)
```

---

## 7. Frontend / Design system

### CSS printsipi (Bootstrap YO'Q)

- `tokens.css` (design tokens) + `foundation.css` (reset + primitives) + `components.css`
- Har flow uchun shell CSS
- Sahifa-specific CSS

### Shell / Page CSS inventory

| CSS | Flow |
|---|---|
| `public.css` + `public-*.css` | public layout va landing/pricing/about/courses |
| `auth.css`, `billing.css` | auth + checkout |
| `app.css`, `app-shell.css`, `app-*.css` | student app shell + course detail |
| `messenger-shell.css` | messenger |
| `exam-shell.css`, `exam-*.css` | exam |
| `backoffice-shell.css`, `backoffice-*.css` | backoffice |
| `blog-shell.css`, `blog-article.css`, `blog-studio-*.css` | blog + studio |
| `error-*.css` | error/maintenance/offline |

### JS inventory

| JS | Flow |
|---|---|
| `messenger-chat.js` | WebSocket messenger client, AI state, feedback, edit/delete/upload |
| `prototype-ui.js` | migrated prototype UI interactions |
| `public-home.js`, `public-pages.js` | landing va public sahifalar |
| `blog-runtime.js` | blog runtime |
| `billing.js` | checkout |

### Template katalogi

`templates/auth/`, `registration/`, `users/`, `courses/`, `cohorts/`, `subscriptions/`, `messenger/`, `exam/`, `backoffice/`, `blog/`, `errors/`.

`playground/` — static prototype/reference HTML'lar (Fourth Trial va alternative-student-journey). Production runtime uchun manba emas — current implementation Django templates va static CSS/JS.

---

## 8. URL map

### Public / Core

| URL | Name |
|---|---|
| `/` | `home` |
| `/about/` | `about` |
| `/privacy-policy/` | `privacy_policy` |
| `/terms-of-service/` | `terms_of_service` |
| `/faq/` | `faq_page` |
| `/healthz` | `healthz` (liveness — DB'ga tegmaydi) |
| `/readyz` | `readyz` (readiness — critical capability'lar, `503` bera oladi) |
| `/maintenance/` | `maintenance` |
| `/offline/` | `offline` |

### Auth / User

| URL | Name |
|---|---|
| `/users/register/` | `register` |
| `/users/login/` | `login` |
| `/users/logout/` | `logout` |
| `/users/dashboard/` | `dashboard` |
| `/users/profile/` | `profile` |
| `/users/settings/` | `settings` |
| `/users/settings/ai-tone/` | `update_ai_tone` |
| `/users/settings/ai-model/` | `update_ai_model` |
| `/users/settings/ai-web-search/` | `update_ai_web_search_effort` |
| `/users/settings/ai-memory/` | `ai_memory` |
| `/users/leaderboard/` | `leaderboard` |
| `/users/notifications/` | `notifications` |
| `/users/attendance/` | `attendance_calendar` |
| `/users/attendance/manage/` | `attendance_manage` |
| `/users/subscriptions/` | `subscriptions` |
| `/users/certificates/` | `certificates` |
| `/users/help/` | `help_center` |

### Courses

| URL | Name |
|---|---|
| `/courses/` | `courses` |
| `/courses/<pk>/` | `course_detail` |
| `/courses/<course_id>/study/` | `course_study` |
| `/courses/<course_id>/lesson/<lesson_id>/` | `lesson_detail` |
| `/courses/<course_id>/exam/<exam_id>/` | `exam_detail` |
| `/courses/<course_id>/exam/<exam_id>/result/` | `exam_result` |
| `/courses/certificate/<certificate_id>/` | `certificate_detail` |

### Checkout / Pricing

| URL | Name |
|---|---|
| `/pricing/` | `subscriptions:pricing` |
| `/checkout/course/<course_id>/` | `cohorts:checkout` |
| `/checkout/receipt/<receipt_id>/pending/` | `cohorts:checkout_pending` |
| `/checkout/receipt/<receipt_id>/success/` | `cohorts:checkout_success` |

### Messenger

| URL | Name |
|---|---|
| `/messenger/` | `messenger:index` |
| `/messenger/ai/` | `messenger:ai` |
| `/messenger/ai/new/` | `messenger:new_ai_chat` |
| `/messenger/ai/<room_id>/` | `messenger:ai_room` |
| `/messenger/group/` | `messenger:group` |
| `/messenger/tutor/` | `messenger:tutor` |
| `/messenger/api/rooms/` | `messenger:get_user_rooms` |
| `/messenger/api/messages/<room_id>/` | `messenger:get_room_messages` |

### Telegram Mini App

| URL | Name |
|---|---|
| `/bot/miniapp/` | `bot:miniapp_entry` |
| `/bot/miniapp/auth/` | `bot:miniapp_auth` |
| `/bot/miniapp/home/` | `bot:miniapp_home` |
| `/bot/miniapp/courses/` | `bot:miniapp_courses` |
| `/bot/miniapp/ai/` | `bot:miniapp_ai` |
| `/bot/miniapp/profile/` | `bot:miniapp_profile` |

Mini App sahifalari `templates/bot/miniapp_base.html` mobil shellini ulashadi. Telegram `initData` orqali ochilgan sessiya va lokal `?preview=1` oqimi shu alohida shellga kiradi; katta platforma sahifalari faqat chuqur amallar uchun havola sifatida qoladi.

### Blog

| URL | Name |
|---|---|
| `/blog/` | `blog:list` |
| `/blog/studio/` | `blog:studio` |
| `/blog/studio/new/` | `blog:studio_create` |
| `/blog/studio/<slug>/edit/` | `blog:studio_edit` |
| `/blog/<slug>/` | `blog:detail` |

### Study in Turkey

| URL | Name |
|---|---|
| `/sit/` | `sit:home` |
| `/sit/universities/` | `sit:university_list` |
| `/sit/universities/<slug>/` | `sit:university_detail` |
| `/sit/guides/<slug>/` | `sit:knowledge_detail` |

### Study in Turkey backoffice

| URL | Name |
|---|---|
| `/backoffice/sit/` | `sit_backoffice:dashboard` |
| `/backoffice/sit/universities/` | `sit_backoffice:universities` |
| `/backoffice/sit/universities/new/` | `sit_backoffice:university_create` |
| `/backoffice/sit/universities/<id>/` | `sit_backoffice:university_edit` |
| `/backoffice/sit/announcements/` | `sit_backoffice:announcements` |
| `/backoffice/sit/announcements/new/` | `sit_backoffice:announcement_create` |
| `/backoffice/sit/announcements/<id>/` | `sit_backoffice:announcement_edit` |
| `/backoffice/sit/guides/` | `sit_backoffice:guides` |
| `/backoffice/sit/guides/new/` | `sit_backoffice:guide_create` |
| `/backoffice/sit/guides/<id>/` | `sit_backoffice:guide_edit` |

### Backoffice + Exam shell

| URL | Name |
|---|---|
| `/backoffice/` va child URL'lar | `backoffice_dashboard`, `_users`, `_chats`, `_course_create/edit`, `_lessons`, `_lesson_edit`, `_exams`, `_exam_edit` |
| `/exam/center/, /history/, /listening/, /writing/, /speaking/, /review/` | `exam:center`, `:history`, `:listening`, `:writing`, `:speaking`, `:review` |

---

## 9. Background jobs va commands

### Celery tasks

| Task | Vazifa |
|---|---|
| `messenger.tasks.generate_ai_response` | AI reply generation |
| `messenger.tasks.reindex_lesson_rag` | lesson RAG reindex |
| `messenger.tasks.reindex_course_rag` | course RAG reindex |
| `messenger.tasks.send_telegram_notification` | chat notification to Telegram |
| `cohorts.tasks.run_subscription_lifecycle` | subscription expiration/lifecycle |

### Celery beat

- `subscription-lifecycle-daily` — prod-like default
- Local'da odatda off/eager

### Management commands

| Command | App | Maqsad |
|---|---|---|
| `runbot` | bot | Telegram polling botni ishga tushirish |
| `setwebhook` | bot | Telegram webhook sozlash |
| `telegram_outbox --loop` | bot | notification outbox'ni 25 tadan 15 soniyalik siklda yuborish; 3 urinishdan keyin failed |
| `expire_overdue_enrollments` | cohorts | overdue active enrollments → expired |
| `reindex_rag` | messenger | lesson/course RAG chunk + embeddings |
| `setup_rag_pgvector` | messenger | pgvector extension/index setup |
| `reindex_ai_memory` | messenger | memory facts embeddings reindex |
| `generate_subscription_notifications` | users | subscription notification generation |

---

## 10. Environment va settings

### Loading chain

1. `.env` yuklanadi
2. `APP_ENV` aniqlanadi (`local` default)
3. `.env.<APP_ENV>` mavjud bo'lsa override qiladi
4. `LOCAL_USE_REMOTE_SERVICES=True` bo'lsa local'dan remote DB/Redis/S3 ishlatish mumkin

### Muhim env vars

| Env | Vazifasi |
|---|---|
| `APP_ENV` | `local` (default) yoki production-like nom |
| `AZURELMS_SKIP_ENV_FILE` | `.env.<APP_ENV>` yuklanmaydi. Test yugurtirishda **majburiy**: aks holda `.env.local`dagi haqiqiy `GEMINI_API_KEY` yuklanib, testlar bepul kvotani sarflashi mumkin |
| `PRIVATE_MEDIA_ROOT` | Private fayllar ildizi; default `BASE_DIR/private-media`. `MEDIA_ROOT` dan tashqarida bo'lishi shart |
| `AZURELMS_TEST_FILE_DB` | Test bazasini diskdagi SQLite fayliga o'tkazadi. Concurrency proof testlari uchun kerak; default in-memory (tezroq), ammo uning qulflash semantikasi real bazadan farq qiladi |
| `DEBUG` | Django debug |
| `SECRET_KEY` | prod uchun majburiy |
| `APP_DOMAIN` | prod domain, CSP va trusted origins |
| `ALLOWED_HOSTS` | host allowlist |
| `CSRF_TRUSTED_ORIGINS` | CSRF trusted origins |
| `SECURITY_STRICT` | HTTPS, secure cookies, CSP, HSTS |
| `DATABASE_URL` / `DB_*` | PostgreSQL config |
| `LOCAL_USE_REMOTE_SERVICES` | local'dan remote services'ga ulanish |
| `VALKEY_URL` / `REDIS_URL` | cache, channels, celery broker |
| `CELERY_BROKER_URL` | explicit broker override |
| `CELERY_TASK_ALWAYS_EAGER` | local eager task override |
| `GEMINI_API_KEY` | Joriy chat va embeddings; grounding faqat paid/admitted rejimda, secret qiymat git'ga kirmaydi |
| `AI_CHAT_PROVIDER` | Joriy local qiymat `gemini`; `digitalocean` adapteri supported, ammo HOLD |
| `AI_FREE_TIER_MODE` | Default `True`; admitted model va qimmat search UI/runtime siyosatini toraytiradi |
| `GEMINI_GROUNDING_ENABLED` | Free tier'da majburan `False`; env `True` ham hard-offni chetlab o'tmaydi. Faqat non-free admitted rejimda ishlaydi |
| `GEMINI_FREE_MODEL_ALLOWLIST` | `gemini-3.1-flash-lite,gemini-2.5-flash-lite`; boshqa user model tanlovi clamp qilinadi |
| `GEMINI_PRIMARY_MODEL` | Default `gemini-3.1-flash-lite` |
| `GEMINI_FALLBACK_MODEL` | Temporary `gemini-2.5-flash-lite`; announced shutdown yo'q, 2026-10-16 internal review |
| `GEMINI_MAX_OUTPUT_TOKENS` / `GEMINI_MAX_PROMPT_CHARS` | Default `640` / `12000` |
| `GEMINI_REQUEST_TIMEOUT_MS` / `GEMINI_DEADLINE_MS` | Default `8000` / `20000` |
| `GEMINI_EMBEDDING_TIMEOUT_MS` | Default `8000`; embedding SDK retry off |
| `GEMINI_EMBEDDING_MAX_INPUTS` / `GEMINI_EMBEDDING_MAX_INPUT_CHARS` / `GEMINI_EMBEDDING_MAX_BATCH_CHARS` | Default `64` / `8000` / `64000` |
| `AI_ALLOW_DIGITALOCEAN` | Default `False`; explicit owner production admissionisiz factory DO provider bermaydi |
| `DIGITALOCEAN_INFERENCE_API_KEY` | Pre-production'da bo'sh; production qayta ochilganda qayta baholanadi |
| `DIGITALOCEAN_INFERENCE_MODEL` | Dormant DigitalOcean chat modeli, default `router:general` |
| `DIGITALOCEAN_INFERENCE_MODEL_FALLBACKS` | Dormant DigitalOcean chat model fallbacklari |
| `TELEGRAM_BOT_TOKEN` | Telegram bot |
| `BOT_USERNAME` | Telegram bot username |
| `TELEGRAM_MODE` | `polling` (local default), `webhook` (prod) |
| `USE_S3` | Joriy `False`; future S3-compatible media storage adapterini yoqadi |
| `PROMETHEUS_ENABLED` | optional prometheus (package yo'q bo'lsa soft-disabled) |
| `RAG_USE_PGVECTOR`, `RAG_EMBEDDING_MODEL`, `RAG_TOP_K`, `RAG_MIN_SIMILARITY` | RAG sozlamalari |
| `AI_MEMORY_USE_VECTOR_RETRIEVAL` | semantic memory uchun |

### `SECURITY_STRICT=True` joriy ta'siri va cheklovi

- HTTPS redirect
- Secure session/CSRF cookies
- HSTS
- Default sahifalarda `X_FRAME_OPTIONS = DENY`; Telegram-authenticated Mini App view'lari ataylab exempt bo'lib, middleware `frame-ancestors`ni qo'shadi
- `django-csp` v4 formatiga ko'chirildi (2026-08-15, A0b/5): siyosat `core/csp_policy.build_csp_policy()` da quriladi va `CONTENT_SECURITY_POLICY` orqali beriladi; header real javobda tekshirilgan
- `script-src` ga Mini App yuklaydigan `https://telegram.org` qo'shildi; Mini App sessiyasi `frame-ancestors` ni per-response `_csp_replace` bilan kengaytiradi, ya'ni to'liq siyosat saqlanadi

### 2026-08-14 da tasdiqlangan release cheklovlari

- Production-like muhitda broker env yo'q bo'lsa Celery hozir `memory://`ga fallback qilishi mumkin; Channels ham konfiguratsiya bo'lmasa in-memory qatlamga tushadi.
- ~~Default S3 media storage `public-read` va unsigned URL ishlatadi; protected upload klasslari hozir alohida private storage'ga ajratilmagan.~~ **Yopildi 2026-08-15 (A0b/3):** to'lov cheki, vazifa fayli, chat biriktirmasi va speaking yozuvi `PRIVATE_MEDIA_ROOT` ichida — `MEDIA_ROOT` dan tashqarida — saqlanadi va faqat ruxsat tekshiradigan view orqali beriladi. Private storage public URL bermaydi. Future S3 uchun bu view signed URL'ga redirect qiladigan qilib kengaytiriladi.
- `.github/workflows` hozir yo'q. `/healthz` (liveness) va `/readyz` (readiness) 2026-08-15 da qo'shildi: tekshiruv mantig'i Control Center capability registry/probe'laridan olinadi, readiness faqat `critical` capability'larni yugurtiradi va birortasi `red` bo'lsa `503` qaytaradi.
- `TelegramOutbox` modeli/command'i bor, lekin Procfile'da doimiy process yo'q. Worker 2026-08-15 dan **atomik claim/lease** ishlatadi (shartli `UPDATE` + `LEASE_SECONDS` muddati; o'lgan worker qatori navbatga qaytadi), ya'ni bir necha replica bir xil qatorni olmaydi. Kafolat baribir at-least-once: yuborish muvaffaqiyatli bo'lib DB yangilanishidan oldin process o'lsa xabar takrorlanadi. Exponential backoff va dead-letter hali yo'q.
- `AIResponseRun` status, model, skill, token, duration, metadata, error va idempotency keyni saqlaydi; pul qiymati va quality release gate saqlanmaydi.
- Read-only capability registry/snapshot AI supply daily request/token, minute request va cooldown stoplightini ham ko'rsatadi; umumiy append-only `SystemAuditEvent`, active service heartbeat va `ReleaseRecord` hozir yo'q.
- Gemini provider allowlistdagi 1 primary + max 1 fallback bilan bounded; SDK retry off, `429` bir attemptda fail-fast/circuit. Prompt/output/timeout/deadline caplari implement/test qilingan; post-A8 local full regression 527/527.
- Free tier'da API grounding defense-in-depth o'chiq: engine specialist/search call yaratmaydi, provider direct caller `enable_web_search=True` bersa ham `GoogleSearch()` va config tools `0`; intent `requested/blocked/actual` telemetryda ajraladi.
- Per-user allowance upstream supply emas. Alohida `AISupplyEvent` global daily+minute request va daily token hard budgetini pre-reserve qiladi, staff va auxiliary calllarni ham qamraydi; ledger DB xatosida remote call fail-closed.
- SQLite parallel reservation contention proofi 2026-08-15 da yozildi va kamchilikni ochdi: `select_for_update()` SQLite'da no-op (`has_select_for_update=False`), `BEGIN DEFERRED` esa write-upgrade paytida busy_timeout'ni kutmaydi. Local SQLite endi `transaction_mode=IMMEDIATE`, `timeout=15` va WAL bilan ishlaydi; contention testlari `AZURELMS_TEST_FILE_DB=1` bilan fayl bazasida bajariladi. PostgreSQL proofi va alohida OS processlari bilan takrorlash hali pending. SmartForm/guest counterlari hamda lesson reindex batch'lari uchun to'liq concurrency lease/claim yo'q.
- Ichki minute request cap tashqi quota o'rnini bosmaydi. 2026-08-14 AI Studio snapshotida 3.1 Flash Lite `15 RPM / 250K TPM / 500 RPD`, 3.7 Flash `5 RPM / 250K TPM / 20 RPD`; shu sabab 3.7 allowlistga admit qilinmagan. `gemini-2.5-flash-lite` fallbacki 2026-10-16 ichki review deadline'ida qayta baholanadi. Joriy Gemini vision unavailable.
- CSP config django-csp v4 formatiga ko'chirilmagan; middleware order sabab Mini App middleware yaratgan `frame-ancestors` headeri keyingi full policy'ni chetlab o'tishi ham mumkin. Normal sahifa, Mini App entry va authenticated Mini App'da full response-header test, Telegram script/frame allowlist va browser smoke A0b release blocker'i.

### `.env.local` namunasi (git'ga kirmaydi)

```dotenv
APP_ENV=local
DEBUG=True
SECURITY_STRICT=False
LOCAL_USE_REMOTE_SERVICES=False
USE_S3=False
AI_CHAT_PROVIDER=gemini
AI_FREE_TIER_MODE=True
GEMINI_GROUNDING_ENABLED=False
GEMINI_FREE_MODEL_ALLOWLIST=gemini-3.1-flash-lite,gemini-2.5-flash-lite
GEMINI_PRIMARY_MODEL=gemini-3.1-flash-lite
GEMINI_FALLBACK_MODEL=gemini-2.5-flash-lite
GEMINI_MAX_OUTPUT_TOKENS=640
GEMINI_MAX_PROMPT_CHARS=12000
GEMINI_REQUEST_TIMEOUT_MS=8000
GEMINI_DEADLINE_MS=20000
GEMINI_API_KEY=
AI_ALLOW_DIGITALOCEAN=False
DIGITALOCEAN_INFERENCE_API_KEY=
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```

---

## 11. Security va access qoidalari

### Course / lesson access

- Lesson detail active enrollment talab qiladi
- Enrollment active access grace deadline bilan tekshiriladi
- Cohort lesson release map dars locked/unlocked holatini beradi
- `user_can_use_lesson_context` AI lesson context abuse oldini oladi

### Messenger access

- WebSocket `connect` authentication va room authorization tekshiradi
- `sender_id` client'dan olinmaydi, `scope.user`'dan olinadi
- AI context lesson ID client'dan kelsa ham permission'dan o'tadi
- Chat rooms `sync_student_chat_access` bilan enrollment state'ga moslanadi

### AI safety

- User savolidagi `<SAVE_MEMORY>` taglar sanitize qilinadi
- Memory policy sensitive yoki noto'g'ri faktlarni skip qiladi
- AI reply'dagi memory taglar user'ga ko'rsatilmay, extractor orqali ajratiladi
- Web search sources telemetry'da saqlanadi, javob matnida ko'rsatilmaydi
- Inline `(Manba N)` va trailing `Manbalar:` `_sanitize_reply` orqali strip qilinadi

### Production safety

- Local mode remote DB/Redis/S3'ga tasodifan ulanmaydi (`LOCAL_USE_REMOTE_SERVICES=True` bo'lmasa)
- `SECRET_KEY` prod uchun majburiy
- `SECURITY_STRICT` prod'ga yaqin muhitlarda yoqilishi kerak

### 2026-07-22 auditida ochiq qolgan access gaplari

- ~~`TelegramAuthSession` authenticated tokeni status endpointda bir martalik consume/expiry qilinmaydi; replay login xavfi bor.~~ **Yopildi 2026-07-23** (`e7cd4a6`): token bir martalik (`consumed_at`), brauzerga bog'langan (`client_key`), `authenticated` holat TTL'ga bo'ysunadi.
- ~~Telegram webhook secret uchun taniqli default mavjud; mismatch request yuborgan `received` token logga yoziladi.~~ **Yopildi 2026-07-23** (`5bea4a5`): default bo'sh + fail-closed webhook; mos kelmagan token logga yozilmaydi; `constant_time_compare`.
- O'chirilgan (deaktivatsiya qilingan) staff bot admini hisoblanardi. **Yopildi 2026-07-23** (`5bea4a5`): `is_active_staff()` va `resolve_identity` orqali `is_active` tekshiriladi.
- ~~WebSocket room authorization connect vaqtida tekshiriladi; ochiq socket uchun enrollment/access o'zgarishini qayta tekshirish yo'q.~~ **Yopildi 2026-08-15 (A0b/4):** ruxsat har `receive()` da qayta hisoblanadi (foydalanuvchi holati ham DB'dan qayta o'qiladi); yo'qolgan bo'lsa socket `4403` bilan yopiladi.
- ~~Model validatorlari oddiy `save/create`da avtomatik ishlamagani sabab uploadlar real MIME/magic-byte gate'dan to'liq o'tmaydi.~~ **Yopildi 2026-08-15 (A0b/2):** `core/upload_validation.py` faylning boshidagi baytlaridan turini aniqlaydi (`image`/`document`/`audio` profillari, hajm capi va kengaytma izchilligi). Gate view/servis darajasida — chat biriktirmasi, to'lov cheki, vazifa fayli, imtihon audiosi va avatar. Klient yuboradigan `content_type` va fayl nomiga ishonilmaydi.
- ~~Private uploadlar joriy default S3 storage sabab public-read bo'lishi mumkin.~~ **Yopildi 2026-08-15 (A0b/3)** — yuqoriga qarang. Avatar ataylab public qoldi: uni boshqa foydalanuvchilar chat va reytingda ko'radi, `05-launch-ops.md` bo'yicha bu alohida owner qarori.

Ochiq bandlar joriy capability emas, backlog `A0b` release gate'i. Yopilgan har band kod/test evidence bilan shu ro'yxatdan olib tashlanadi.

---

## 12. Task → fayl xaritasi

| Task | Boshlash nuqtasi |
|---|---|
| AI javob sifati | `ai/agent/engine.py`, `ai/prompts/builder.py`, `ai/providers/` |
| Skill qo'shish | `ai/skills/registry.py`, `ai/skills/<slug>/SKILL.md`, `messenger/tests.py` |
| Memory | `ai/memory/service.py`, `repository.py`, `retriever.py`, `messenger/models.py` |
| RAG | `ai/rag/context.py`, `messenger/rag.py`, `LessonRAGChunk`, `reindex_rag` |
| Messenger UI | `templates/messenger/*.html`, `static/css/messenger-shell.css`, `static/js/messenger-chat.js` |
| WebSocket bug | `messenger/consumers.py`, `messenger/routing.py`, browser console |
| AI async/task bug | `messenger/tasks.py`, `AIResponseRun`, Celery settings |
| Course/lesson | `courses/models.py`, `courses/views.py`, `templates/courses/`, `app-course-detail.css` |
| Checkout | `cohorts/views.py`, `cohorts/models.py`, `subscriptions/models.py` |
| Dashboard | `users/views.py`, `templates/users/dashboard.html`, `app.css`/`app-shell.css` |
| Backoffice | `core/views.py`, `templates/backoffice/`, `backoffice-*.css` |
| Blog | `blog/models.py`, `blog/views.py`, `templates/blog/`, blog CSS |
| Study in Turkey | `sit/models.py`, `sit/selectors.py`, `sit/views.py`, `templates/sit/`, `static/css/sit.css` |
| Telegram | `bot/`, `messenger/tasks.send_telegram_notification`, `cohorts.Attendance` |
| Deployment | `core/settings.py`, `core/celery.py`, `Dockerfile`, `Procfile` |

---

## 13. Foydali buyruqlar

```powershell
# Venv
cd C:\Users\AZUREBEK\Documents\Codex\2026-08-13\new-chat\azurelms
.\venv\Scripts\activate

# Server
python manage.py runserver

# Telegram bot polling (alohida terminal)
python manage.py runbot

# Tekshiruvlar
python manage.py migrate
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py system_audit --json --fail-on never
python manage.py backup_db                    # izchil zaxira (WAL-safe)
python manage.py restore_db --input <fayl> --yes

# RAG/memory indeks — Gemini credential va supply budget ataylab ochiq bo'lsa
python manage.py reindex_rag --force
python manage.py reindex_rag --course-id 5 --force
python manage.py reindex_ai_memory --force

# Test — DIQQAT: kvota xavfsizligi uchun har doim `.env.local`siz yugurtiring,
# aks holda haqiqiy GEMINI_API_KEY yuklanadi va testlar bepul kvotani sarflaydi.
$env:AZURELMS_SKIP_ENV_FILE='1'; $env:GEMINI_API_KEY=''; $env:TELEGRAM_BOT_TOKEN=''
python manage.py test
python manage.py test ai.providers.tests aicontrol.tests messenger.test_embedding_supply
python manage.py test messenger
python manage.py test users.tests.DashboardProgressTests

# A8 concurrency proof — fayl bazasini talab qiladi (default in-memory'da skip bo'ladi)
$env:AZURELMS_TEST_FILE_DB='1'; python manage.py test aicontrol.test_supply_concurrency
```

---

## 14. Muhim eslatmalar

1. **Joriy clone:** `C:\Users\AZUREBEK\Documents\Codex\2026-08-13\new-chat\azurelms`; venv Python 3.12.13 + Django 6.0.2. Eski OneDrive/`C:\Projects` yo'llari historical sessiyalarda uchrashi mumkin — buyruqdan oldin `git worktree list` source of truth.
2. **Bootstrap YO'Q:** barcha shell'da `tokens.css` + custom CSS. Yangi sahifa qo'shganda shu printsipga rioya qilish.
3. **`<SAVE_MEMORY>` tag:** AI javobida `<SAVE_MEMORY>category: fakt</SAVE_MEMORY>` ko'rinishida chiqsa, extractor ajratib `AIMemoryFact`'ga yozadi. Category: `preference`, `learning_goal`, `weak_topic`, `schedule`, `profile`, `do_not_remember`, `other`.
4. **`@azure` mention:** AI bo'lmagan xonada xabarda `@azure` so'zi bo'lsa, AI ham javob beradi.
5. **AI memory toggling:** Foydalanuvchi `ai_memory_enabled=False` qilsa, `MemoryService` to'liq disable (extract ham, retrieve ham).
6. **YouTube embed:** owner embed bloklasa platforma majburlab ocholmaydi — fallback UX kelajakda kerak bo'lishi mumkin.
7. **SIT data gate:** qabul, narx va viza kabi vaqtga sezgir public ma'lumot `source_url` va `last_verified_on`siz nashr qilinmaydi. `playground/SIT/` runtime emas.
8. **`.gitignore`:** `.claude/`, `.tools/`, `.codex/`, `__pycache__/`, `*.pyc`, `db.sqlite3`, `media/`, `venv/`, `.env` va `.env.local`.
9. **2026-08-14 resurs/A8 qarori:** production va DigitalOcean integration'i HOLD; local ish davom etadi. A8 supply guard **`IMPLEMENTED/TESTED — LOCAL REGRESSION GREEN`** (527/527; audit 10/10); SQLite/PostgreSQL true concurrency proofdan oldin yangi AI behavior yoki ommaviy rollout yo'q.
10. **Joriy vision chegarasi:** `image_qa` skill mavjud, lekin Gemini adapteri vision'ni qo'llamaydi; rasm tahlili current capability emas.
11. **Schema:** `aicontrol/0002_ai_supply_budget`, `messenger/0014_ai_response_idempotency`, `users/0015_free_tier_model_default` va `users/0016_alter_notification_options` local SQLite'ga apply qilingan.
12. **Model lifecycle:** primary `gemini-3.1-flash-lite`; temporary `gemini-2.5-flash-lite` uchun announced shutdown yo'q, ammo 2026-10-16 internal reviewda remove yoki yangi admitted modelga migrate qarori olinadi. 3.7 Flash joriy project snapshotidagi 20 RPD sabab hozir admit qilinmagan.

---

*Bu hujjat har major feature qo'shilganda yangilanib turishi kerak. Yangilash protokoli `rules-for-agents.md` da.*
