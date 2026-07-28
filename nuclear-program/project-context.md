# AzureLMS — Loyiha konteksti

Bu hujjat loyihaning yashash kitobi (wiki). Yangi feature qo'shilsa shu yerda batafsil tushuntiriladi. Yangi agent kelishi bilan o'qiy boshlaydigan birinchi joy.

Source of truth har doim **kod** (model/view/task/URL/test). Bu fayl kodga moslab yangilab turiladi.

> **Holat qoidasi:** “Joriy holat” faqat kodda hozir mavjud va tekshirilgan narsani bildiradi. “Maqsad arxitektura” alohida belgilangan reja bo'lib, implementatsiya va test tugamaguncha mavjud capability sifatida talqin qilinmaydi.

---

## 1. Mahsulot xulosasi

**AzureLMS** — o'zbek tilida turk tili o'rgatishga qaratilgan Learning Management System. Klassik kurs/dars oqimini real-time messenger, AI tutor, RAG, memory, exam, subscription, Telegram attendance, Study in Turkey (SIT) portali va yashirin backoffice boshqaruvi bilan birlashtiradi.

**Joriy workspace:** `C:\Users\azurb\azurelms` (Windows)
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
8. Telegram bot attendance va kelajakdagi o'quv oqimlari uchun ishlatiladi.

---

## 2. Tech stack

### Backend

| Qism | Texnologiya |
|---|---|
| Web framework | Django 6.0.2 |
| Local Python | venv Python 3.14 |
| Docker Python | `python:3.12-slim` (⚠️ version drift — Dockerfile'ni 3.14'ga yangilash kerak) |
| ASGI | Daphne 4.2.1 |
| WebSocket | Django Channels 4.3.2 |
| Tasks | Celery 5.6.2 |
| Local task mode | `memory://` broker + eager tasks |
| Cache / channel prod | Redis/Valkey via `REDIS_URL`, `VALKEY_URL` yoki component vars |
| DB local | SQLite `db.sqlite3` |
| DB prod | PostgreSQL, SSL required |
| Vector search | pgvector in prod, JSON/cosine fallback in code |
| Rich text | django-ckeditor-5 |
| Admin | Jazzmin + optional legacy `/admin/` (faqat `ENABLE_LEGACY_ADMIN=True` bo'lsa) |
| Storage | local filesystem yoki DigitalOcean Spaces/S3 |
| Static | Whitenoise compressed static |

### AI

| Qism | Texnologiya |
|---|---|
| Chat provider | `AI_CHAT_PROVIDER`: Google Gemini yoki DigitalOcean Serverless Inference |
| Chat models | Gemini user tanlovi; DigitalOcean uchun `DIGITALOCEAN_INFERENCE_MODEL` + fallbacklar |
| Embedding | `gemini-embedding-001`, 768 dimensions |
| Web search | Gemini grounding / `google_search` tool; DigitalOcean adapterida hozircha o'chirilgan |
| Memory | structured `AIMemoryFact`, traces, summaries, semantic scoring |
| RAG | `LessonRAGChunk`, course/lesson scoped retrieval |

### Deployment

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
├── skills/   registry.py + 10 ta SKILL.md
└── tools/    context.py
```

### `aicontrol`

**Joriy mas'uliyat:** AI token usage siyosati va admin amallari. `AISettings` global enforcement/default limitlarni, `AIPlanPolicy` tarif limitlarini, `AIUserAllowance` user override/reset/bonus/blok holatini, `AIUsageResetEvent` esa reset/bonus auditini saqlaydi.

**Joriy UI:** `/backoffice/ai-control/` token usage, global/plan limit va reset/bonusni boshqaradi; blocked userlar sonini ko'rsatadi, lekin shu sahifada per-user block mutation'i yo'q. Per-user blok amali bot yoki admin orqali. `default_model` va `default_effort` modelda saqlanadi, ammo runtime provider ularni o'qimaydi va template ularni edit input sifatida render qilmaydi.

**Joriy Control Center foundation (2026-07-22):** owner-only `/backoffice/control/` `core/control_center/`dagi bitta read-only capability registry va snapshot servisidan foydalanadi. DB, cache, Channels, Celery config, Telegram outbox, media, AI provider/effective token policy, RAG, security va release identity GREEN/AMBER/RED sabab bilan ko'rinadi. Shu snapshot terminalda `python manage.py system_audit [--json] [--fail-on red|amber|never]` orqali ham ishlaydi; web va CLI alohida health mantiq yozmaydi.

**Joriy chegarasi:** bu foundation mutation qilmaydi. Append-only `SystemAuditEvent`, system-wide feature flag/kill switch, active worker/beat heartbeat, `ReleaseRecord`, backup/email/memory probe, cost ledger va AI quality release gate hali mavjud emas. `/backoffice/ai-control/` compatibility control path sifatida Control Center'dan ochiladi, lekin hozircha alohida sahifa.

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
  → AIResponseRun running
  → AIEngine.generate_reply
  → Message create is_ai_response=True
  → AIResponseRun succeeded/fallback/failed
  → broadcast AI message + status
```

AI room nomi birinchi prompt'dan avtomatik o'zgarishi mumkin (`maybe_name_ai_room_from_first_prompt`).

### 4.9 Telegram attendance

- Local'da polling default; prod/remote uchun webhook.
- Teacher `/start_lesson` qiladi → `TelegramLessonSession` yaratiladi.
- Talabalar check-in qiladi → `TelegramLessonCheckIn` records.
- `Attendance` LMS'ga bog'lanadi.

### 4.10 Backoffice

Custom yashirin admin URL'lari:

```
/backoffice/
/backoffice/control/                 # faqat active superuser
/backoffice/control/brand/           # faqat active superuser; markaziy brend/logo
/backoffice/users/
/backoffice/chats/
/backoffice/courses/new/
/backoffice/courses/<id>/
/backoffice/lessons/
/backoffice/lessons/<id>/
/backoffice/exams/
/backoffice/exams/<id>/
```

Access helper: `core.views._is_backoffice_user`. Legacy `/admin/` faqat `ENABLE_LEGACY_ADMIN=True`.

**Joriy permission cheklovi:** `_is_backoffice_user` `is_staff` yoki `is_superuser`ni qabul qiladi; AI global control ham shu gate ortida. `/backoffice/control/` esa alohida `_is_control_center_owner` orqali faqat active `is_superuser`ga ochiladi va hozir read-only. Teacher'ga explicit course biriktirilmagan bo'lsa teacher query hozir barcha kurslarni qaytarishi mumkin; default-deny teacher scope hali maqsad.

### 4.11 Study in Turkey (SIT)

1. Visitor `/sit/`da real published universitetlar, e'lonlar va qo'llanmalarni ko'radi.
2. `/sit/universities/` katalogi GET filterlari bilan universitetlarni server-side saralaydi; default qabul holati `open`.
3. `/sit/universities/<slug>/` universitet, fakultet/dastur, tayyorlov kursi, talab/hujjat/xizmat va media bloklarini bitta detailda beradi.
4. Har public universitet va qo'llanmada rasmiy manba hamda oxirgi tekshirilgan sana ko'rinadi.
5. Hujjat topshirish CTA login qilingan userni tutor messengerga, AI CTA esa mavjud Azure AI messengerga olib boradi. Alohida SIT AI retrieval va payment/help lifecycle keyingi slice.

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
8. **Provider call:** `provider.generate(prompt, selected_model, enable_web_search)`
9. **Memory extraction:** AI reply ichidagi `<SAVE_MEMORY>` taglar
10. **Memory save:** `AIMemoryFact` dedupe + trace
11. **Reply sanitize:** markdown/source/greeting cleanup (`_sanitize_reply` — `(Manba N)` strip, trailing `Manbalar:` strip, follow-up'da leading salom strip)
12. **`AIResponse` return:** text, model, skill slug, metadata

### 5.2 Skills (10 ta)

| Slug | Trigger keywords | Tools | Priority |
|---|---|---|---|
| `general_chat` | (default) | student_progress, course_navigator | 0 |
| `lesson_explainer` | tushuntir, dars, mavzu, izohlab ber | lesson_context, course_navigator | 20 |
| `quiz_generator` | quiz, test, savol tuz, mashq tuz | lesson_context, quiz_context | 80 |
| `homework_checker` | homework, vazifa, tekshir, baholab ber | lesson_context, homework_context, student_progress | 70 |
| `grammar_corrector` | grammar, grammatika, xato, tuzat, zamon | lesson_context | 65 |
| `speaking_coach` | speaking, gapirish, talaffuz, og'zaki | lesson_context, student_progress | 60 |
| `writing_feedback` | writing, essay, insho, paragraph | lesson_context, homework_context | 60 |
| `course_navigator` | qaysi dars, keyingi dars, roadmap | course_navigator, student_progress | 50 |
| `student_progress_coach` | progress, natija, kuchsiz joy, reja tuz | student_progress, course_navigator | 55 |
| `web_search` | qidir, bugungi, kursi qancha, ob-havo, yangiliklar | web_search | 90 |

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

### 5.5 Web search effort tiers

Foydalanuvchi `/users/settings/` da tanlaydi (`CustomUser.ai_web_search_effort`):

| Tier | Behavior |
|---|---|
| `light` (default) | Faqat aniq keyword (qidir, bugungi, kursi qancha, ob-havo) |
| `medium` | Light + **pair detection**: vaqt belgisi (`hozir`/`bugun`/`kechagi`) + ma'lumot belgisi (`narx`/`kim`/`natija`) birga uchrasa majburiy web_search |
| `heavy` | Gemini provider'da har savolda `google_search` tool yoqilgan — model o'zi qaror qiladi. DigitalOcean adapterida hozircha web search o'chirilgan |

Manbalar javob matnida ko'rsatilmaydi. Telemetry'da saqlanadi:
- `web_search_enabled`
- `web_search_queries`
- `web_search_sources` (URL + title)

### 5.6 Tone, model, telemetry

- **Tone:** `friendly` / `formal` / `brief` / `detailed` — prompt builder ohangni o'zgartiradi
- **Provider:** `AI_CHAT_PROVIDER=gemini|digitalocean`. DigitalOcean adapteri OpenAI-compatible `/v1/chat/completions` endpoint'ini ishlatadi
- **Model:** Gemini'da user setting `ai_model`; DigitalOcean'da `DIGITALOCEAN_INFERENCE_MODEL` va fallbacklar. Provider ishlamasa user'ga yumshoq fallback javob qaytadi
- **Telemetry:** `AIResponseRun` har AI javobning metadata'sini saqlaydi: status, model, skill, duration_ms, tools, rag_sources, memory counts, web_search_*

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
| `GEMINI_API_KEY` | Gemini chat provider va embeddings |
| `AI_CHAT_PROVIDER` | `gemini` (default) yoki `digitalocean` |
| `DIGITALOCEAN_INFERENCE_API_KEY` | DigitalOcean Serverless Inference Model Access Key |
| `DIGITALOCEAN_INFERENCE_MODEL` | DigitalOcean chat modeli, default `router:general` |
| `DIGITALOCEAN_INFERENCE_MODEL_FALLBACKS` | DigitalOcean chat model fallbacklari |
| `TELEGRAM_BOT_TOKEN` | Telegram bot |
| `BOT_USERNAME` | Telegram bot username |
| `TELEGRAM_MODE` | `polling` (local default), `webhook` (prod) |
| `USE_S3` | DigitalOcean Spaces/S3 media storage |
| `PROMETHEUS_ENABLED` | optional prometheus (package yo'q bo'lsa soft-disabled) |
| `RAG_USE_PGVECTOR`, `RAG_EMBEDDING_MODEL`, `RAG_TOP_K`, `RAG_MIN_SIMILARITY` | RAG sozlamalari |
| `AI_MEMORY_USE_VECTOR_RETRIEVAL` | semantic memory uchun |

### `SECURITY_STRICT=True` ta'siri

- HTTPS redirect
- Secure session/CSRF cookies
- HSTS
- `X_FRAME_OPTIONS = DENY`
- `django-csp` mavjud bo'lsa CSP middleware
- CSP frame-source YouTube/Vimeo uchun ruxsat beradi

### 2026-07-22 auditida tasdiqlangan production cheklovlari

- Production-like muhitda broker env yo'q bo'lsa Celery hozir `memory://`ga fallback qilishi mumkin; Channels ham konfiguratsiya bo'lmasa in-memory qatlamga tushadi.
- Default S3 media storage `public-read` va unsigned URL ishlatadi; protected upload klasslari hozir alohida private storage'ga ajratilmagan.
- `.github/workflows` va `/healthz` endpoint hozir yo'q.
- `TelegramOutbox` modeli/command'i bor, lekin Procfile'da doimiy process yo'q; worker atomic claim/lease qilmaydi, shuning uchun hozir aynan 1 replica xavfsizroq.
- `AIResponseRun` status, model, skill, token, duration, metadata va errorni saqlaydi; pul qiymati va quality release gate saqlanmaydi.
- Read-only capability registry/snapshot bor; umumiy append-only `SystemAuditEvent`, active service heartbeat va `ReleaseRecord` hozir yo'q.

### `.env.local` namunasi (git'ga kirmaydi)

```dotenv
APP_ENV=local
DEBUG=True
SECURITY_STRICT=False
LOCAL_USE_REMOTE_SERVICES=False
USE_S3=False
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
- WebSocket room authorization connect vaqtida tekshiriladi; ochiq socket uchun enrollment/access o'zgarishini qayta tekshirish yo'q.
- Model validatorlari oddiy `save/create`da avtomatik ishlamagani sabab uploadlar real MIME/magic-byte gate'dan to'liq o'tmaydi.
- Private uploadlar joriy default S3 storage sabab public-read bo'lishi mumkin.

Bu bandlar joriy capability emas, P0 stop-ship backlog. Yopilgan har band kod/test evidence bilan shu ro'yxatdan olib tashlanadi.

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
cd C:\Users\azurb\azurelms
.\venv\Scripts\activate

# Server
python manage.py runserver

# Telegram bot polling (alohida terminal)
python manage.py runbot

# Tekshiruvlar
python manage.py check
python manage.py migrate

# RAG indeks
python manage.py reindex_rag --force
python manage.py reindex_rag --course-id 5 --force

# Test
python manage.py test
python manage.py test messenger
python manage.py test users.tests.DashboardProgressTests
```

---

## 14. Muhim eslatmalar

1. **Joriy clone:** `C:\Users\azurb\azurelms`; venv Python 3.14 + Django 6.0.2. Eski OneDrive/`C:\Projects` yo'llari historical sessiyalarda uchrashi mumkin — buyruqdan oldin `git worktree list` source of truth.
2. **Bootstrap YO'Q:** barcha shell'da `tokens.css` + custom CSS. Yangi sahifa qo'shganda shu printsipga rioya qilish.
3. **`<SAVE_MEMORY>` tag:** AI javobida `<SAVE_MEMORY>category: fakt</SAVE_MEMORY>` ko'rinishida chiqsa, extractor ajratib `AIMemoryFact`'ga yozadi. Category: `preference`, `learning_goal`, `weak_topic`, `schedule`, `profile`, `do_not_remember`, `other`.
4. **`@azure` mention:** AI bo'lmagan xonada xabarda `@azure` so'zi bo'lsa, AI ham javob beradi.
5. **AI memory toggling:** Foydalanuvchi `ai_memory_enabled=False` qilsa, `MemoryService` to'liq disable (extract ham, retrieve ham).
6. **YouTube embed:** owner embed bloklasa platforma majburlab ocholmaydi — fallback UX kelajakda kerak bo'lishi mumkin.
7. **SIT data gate:** qabul, narx va viza kabi vaqtga sezgir public ma'lumot `source_url` va `last_verified_on`siz nashr qilinmaydi. `playground/SIT/` runtime emas.
8. **`.gitignore`:** `.claude/`, `.tools/`, `.codex/`, `__pycache__/`, `*.pyc`, `db.sqlite3`, `media/`, `venv/`, `.env`.

---

*Bu hujjat har major feature qo'shilganda yangilanib turishi kerak. Yangilash protokoli `rules-for-agents.md` da.*
