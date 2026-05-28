# AzureLMS — loyiha konteksti

Bu hujjat loyihaning yashash kitobi. Yangi feature qo'shilsa shu yerda batafsil tushuntiriladi. Yangi agent kelgan zahoti **birinchi shu faylni o'qiydi**, keyin `rules-for-agents.md` ni, keyin `marinebook.md` ning so'nggi 2-3 ta yozuvini.

---

## 1. Loyiha nimani qiladi

**AzureLMS** — o'zbek tilida turk tilini o'rgatuvchi Learning Management System. Foydalanuvchi sayt orqali kirib kurs tinglaydi, mashqlar bajaradi, AI yordamchi bilan suhbatlashadi, va Telegram bot orqali davomatda qatnashadi. Kelajakda butun tajriba Telegram bot orqali ham ishlashi kerak (hozir qisman).

**Joylashuv:** `C:\Projects\azurelms` (Windows 11)
**Asosiy branch:** `main` (yagona, integratsiya trunk'i)
**GitHub:** https://github.com/azurebek/azurelms.git

---

## 2. Tech stack

| Qatlam | Texnologiya |
|---|---|
| Backend | Django 6.0.2 + Python 3.14 |
| Async / WS | Django Channels 4.3 + Daphne (ASGI) |
| Tasks | Celery 5.6 + Redis/Valkey (lokal: `memory://` + eager) |
| DB | PostgreSQL + pgvector (prod), SQLite (lokal) |
| AI | Google Gemini (google-genai 1.65) — 2.5 Flash, 3.1 Pro, 3.5 Flash, va boshqalar |
| Embedding | `gemini-embedding-001` (768d), pgvector ivfflat indeks |
| Bot | Aiogram 3.26 (Telegram) |
| Storage | DigitalOcean Spaces (S3), Whitenoise (static) |
| Admin | Jazzmin 3.0 + CKEditor5 + yashirin backoffice (`/backoffice/`) |

---

## 3. Django apps

- **`users`** — `CustomUser` (email + telegram_id + total_xp + ai_tone + ai_model + ai_memory_enabled + ai_web_search_effort), `UserOnboarding`, `Notification`, `NotificationBroadcast`
- **`courses`** — `Course`, `Module`, `Lesson`, `Assignment`, `AssignmentSubmission`, `Quiz`, `QuizAttempt`, `Exam` (reading/writing/listening/speaking), `Certificate`, `LessonProgress`
- **`cohorts`** — `Cohort`, `Enrollment` (active/pending/expired/frozen), `PaymentReceipt`, `Attendance`
- **`messenger`** — chat va AI qatlamining DB qismi (5-bo'limda alohida)
- **`gamification`** — `Level`, `Badge`, `EarnedBadge`, `Certificate`
- **`subscriptions`** — `Plan`, `PlanFeature`, `PromoCampaign`, `PromoCode`
- **`frontend`** — `LandingPage`, `AboutPage`, `Statistic`, `Testimonial`, `TeamMember`, `SiteSettings`, `AuthPageSettings`, `LegalPage` (Singleton patterns)
- **`backoffice` (`core/views.py`)** — yashirin admin panel: dashboard, users, course/lesson/exam editor
- **`blog`** — `BlogPost`, `BlogTag`, `BlogHomeSettings`
- **`bot`** — `TelegramLessonSession`, `TelegramLessonCheckIn`
- **`ai/`** (Python paket, Django app emas) — agent qatlami (5-bo'limda)

---

## 4. Asosiy foydalanuvchi oqimlari

1. **Enrollment:** User → Plan → PaymentReceipt → Admin tasdiqlaydi → active → ChatRoom signal orqali avto-join
2. **AI Chat:** WebSocket → Message → Celery → memory + RAG + skill + tool ctx + Gemini → broadcast
3. **Attendance:** O'qituvchi `/start_lesson` (Telegram) → talabalar check-in → `/close_lesson` → Attendance + XP
4. **AI memory boshqaruvi:** `/users/settings/ai-memory/` — list, archive, reject, clear-all, toggle (`ai_memory_enabled`)
5. **Tariff yangilash:** `/pricing/` → "Boshlash" → checkout → admin approval → access ochilishi

---

## 5. AI + Messenger arxitekturasi

### 5.1 Messenger DB modellari (`messenger/models.py`)

- **`ChatRoom`** — `room_type`: `group` (cohort), `private` (1:1 tutor), `ai` (AzureAI)
- **`Message`** — `is_ai_response`, `context_lesson` (talaba qaysi darsda turib so'rashi)
- **`AILongTermMemory`** — legacy unstructured text (yangi `AIMemoryFact` ga ko'chmoqda)
- **`AIMemoryFact`** — strukturali xotira (category, status, visibility, confidence, fingerprint SHA256, embedding)
- **`AIMemoryTrace`** — har xotira eventi (retrieved/saved/skipped/archived + reason + score + metadata)
- **`AIConversationSummary`** — har chat xona uchun rolling summary
- **`AIResponseRun`** — telemetry: status, skill_slug, model_name, duration_ms, metadata (used_tools, rag_sources, web_search_*)
- **`AIFeedback`** — AI xabarlariga thumbs up/down
- **`LessonRAGChunk`** — pgvector + JSON embedding fallback

### 5.2 AI agent qatlami (`ai/`)

```
ai/
├── agent/
│   ├── engine.py         AIEngine.generate_reply(AIRequest) → AIResponse
│   └── types.py          AIRequest, AIResponse, ProviderResponse
├── skills/
│   ├── registry.py       9 ta skill + pair-detection + effort tier hook
│   ├── general_chat/SKILL.md
│   ├── lesson_explainer/SKILL.md
│   ├── quiz_generator/SKILL.md
│   ├── homework_checker/SKILL.md
│   ├── grammar_corrector/SKILL.md
│   ├── speaking_coach/SKILL.md
│   ├── writing_feedback/SKILL.md
│   ├── course_navigator/SKILL.md
│   ├── student_progress_coach/SKILL.md
│   └── web_search/SKILL.md
├── tools/
│   └── context.py        ToolContextService — backend snapshot:
│                         lesson_context, homework_context, quiz_context,
│                         student_progress, course_navigator, web_search
├── memory/
│   ├── types.py          MemoryCandidate, MemoryExtraction, SavedMemory,
│   │                     ScoredMemoryFact, ConversationContext
│   ├── policy.py         skip rules, sensitive filter, category infer
│   ├── extractor.py      <SAVE_MEMORY> tag parser
│   ├── repository.py     DB I/O, dedupe fingerprint, decay/archive maintenance
│   ├── evaluation.py     MemoryQualityEvaluator
│   ├── semantic.py       SemanticMemoryScorer — lexical + alias + vector cosine
│   ├── retriever.py      relevant facts → prompt + trace
│   ├── summarizer.py     ConversationSummarizer rolling summary
│   └── service.py        Facade
├── prompts/
│   └── builder.py        PromptBuilder.build(..., is_first_message)
├── providers/
│   └── gemini.py         GeminiProvider + grounding (google_search tool)
└── rag/
    └── context.py        RAGContextService → lesson_context, rag_context,
                          chunks, sources, access_note
```

### 5.3 Engine oqimi (`ai/agent/engine.py`)

`AIEngine.generate_reply(AIRequest)`:
1. `skill_registry.select_for_request` — keyword + priority + lesson boost + medium/heavy effort'da pair detection
2. `tool_context_service.build(request, skill)` — backend snapshot
3. `memory_service.sanitize_user_question` — `<SAVE_MEMORY>` taglarni inputdan tozalash
4. `memory_service.get_conversation_context` — oxirgi 8 ta xabar + eski qismlar uchun rolling summary
5. `memory_service.render_relevant_memory` — top-7 fakt (lexical/semantic/vector)
6. `rag_service.build` — pgvector → fallback dot-product
7. `prompt_builder.build` — system + tone + skill instr + memory + summary + lesson + RAG + tool + user message; `is_first_message` flag salomlashish qoidasi uchun
8. `provider.generate(prompt, selected_model, enable_web_search)` — Gemini, ehtimoliy grounding bilan
9. `memory_service.extract_from_reply` — `<SAVE_MEMORY>` taglarni ajratish
10. `memory_service.save_candidates` — `AIMemoryFact` ga saqlash (dedupe + trace)
11. `_sanitize_reply` — markdown belgilar + inline `(Manba N)` + trailing `Manbalar:` strip; follow-up'da leading salom strip
12. `AIResponse(text, model_name, skill_slug, metadata={rag_sources, used_tools, web_search_queries, web_search_sources, ...})`

### 5.4 Web search effort tiers

Foydalanuvchi `/users/settings/` da tanlaydi (`CustomUser.ai_web_search_effort`):

| Tier | Xulq |
|---|---|
| `light` (default) | Faqat aniq keyword'lar (qidir, bugungi, kursi qancha, ob-havo...) trigger qiladi |
| `medium` | Light + **pair detection**: time word (`hozir`/`bugun`/`kechagi`...) + info word (`narx`/`kim`/`natija`...) birga uchrasa majburiy web_search |
| `heavy` | Har savolda Gemini'ga `google_search` tool yoqilgan — model o'zi qaror qiladi qidirishni |

Manbalar `AIResponseRun.metadata.web_search_sources` ga saqlanadi (URL + title), javob matnida ko'rsatilmaydi.

### 5.5 RAG (`messenger/rag.py`)

- `gemini-embedding-001` (768 dim), 180 word chunks, 40 word overlap
- pgvector mavjud bo'lsa: SQL `<=>` (cosine) + ivfflat indeks; aks holda Python `_cosine_similarity` fallback
- `context_lesson` mavjud bo'lsa: 0.08–0.12 boost
- `_active_course_ids_for_user(user)` orqali enrollment scope (staff/superuser cheksiz)
- Reindex: `python manage.py reindex_rag --force` yoki `--course-id <id> --force`
- Embedding cache: 7 kun

### 5.6 Chat oqimi

```
client (WebSocket)
  ↓ {action, message, context_lesson_id, ai_skill, client_message_id}
ChatConsumer.receive  (messenger/consumers.py)
  ↓ save_message (Message.create + maybe_name_ai_room_from_first_prompt)
  ↓ group_send 'chat_message' (echo)
  ↓ if ai room OR '@azure' in text:
     generate_ai_response.delay(...)  (Celery task)
        ↓ AIResponseRun.create(status=RUNNING)
        ↓ broadcast ai_status RUNNING
        ↓ AIEngine.generate_reply(...)
        ↓ Message.create(is_ai_response=True)
        ↓ AIResponseRun.save(status=SUCCEEDED/FALLBACK, metadata)
        ↓ broadcast 'chat_message' (AI reply) + ai_status SUCCEEDED
```

### 5.7 Skills xaritasi

| Slug | Trigger keywords (qisqartirilgan) | Tools | Priority |
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

Skill auto bo'lsa `context_lesson` bor `lesson_explainer` ga +2 boost. Foydalanuvchi UI dan `requested_skill_slug` orqali majburiy tanlay oladi.

---

## 6. Frontend / Design tizimi

`design-playground/` — 54 statik HTML prototip (mobile-first), Django templatega ko'chirish manbasi. Migration tugagan.

**CSS tizimi (Bootstrap YO'Q):**
- `tokens.css` (design tokens) + `foundation.css` (reset + primitives) + `components.css`
- Har flow uchun shell CSS: `public.css`, `auth.css`, `app-shell.css`, `messenger-shell.css`, `exam-shell.css`, `backoffice-shell.css`, `blog-shell.css`, `blog-studio-shell.css`
- Sahifa-specific CSS: `public-index.css`, `app-course-detail.css`, `exam-listening.css`, va h.k.
- Jami 45 ta CSS fayl

**Migration jadvali (hammasi tugagan):**

| # | Flow | Shell CSS |
|---|---|---|
| 1 | Auth & Billing | `auth.css`, `billing.css`, `billing-status.css` |
| 2 | Public Discovery | `public.css` + page CSS lar |
| 3 | Student App (Dashboard) | `app.css`, `app-shell.css` + app-*.css |
| 4 | Blog Reading | `blog-shell.css`, `blog-article.css`, `blog-tags.css`, `blog-django-bridge.css` |
| 5 | Blog Studio | `blog-studio-shell.css`, `blog-studio-new-post.css`, `blog-studio-analytics.css` |
| 6 | Learning (Course detail, Lesson) | `public-course-detail.css`, `app-course-detail.css` + `lesson_detail.html` |
| 7 | Exam | `exam-shell.css`, `exam-listening.css`, `exam-speaking.css`, `exam-writing.css`, `exam-review.css` |
| 8 | Messenger | `messenger-shell.css` + `ai.html`/`group.html`/`tutor.html` |
| 9 | Legal | `public-legal.css` |
| 10 | Error | `error-403/404/500/maintenance/offline.css` |

Backoffice ham mavjud (`backoffice-shell.css` + course/lesson/exam/users editor).

---

## 7. Asosiy URL nomlari

```
home, about, privacy_policy, terms_of_service, faq_page
login, register, logout
dashboard, profile, settings, leaderboard, notifications, help_center, certificates
update_avatar, update_password, update_ai_tone, update_ai_model, update_ai_web_search_effort
ai_memory, ai_memory_toggle, ai_memory_clear, ai_memory_archive, ai_memory_reject
attendance_calendar, attendance_manage, subscriptions
courses (list), course_detail (pk=)
subscriptions:pricing
blog:list, blog:detail (slug=)
cohorts:checkout (course_id=), cohorts:checkout_success, cohorts:checkout_pending
messenger:ai, messenger:group, messenger:tutor, messenger:ai_room (room_id=)
messenger:new_ai_chat, messenger:get_user_rooms, messenger:get_room_messages
messenger:submit_ai_feedback (message_id=)
exam:center, exam:history, exam:listening, exam:speaking, exam:writing, exam:review
backoffice_dashboard, backoffice_users, backoffice_course_create/edit,
backoffice_lessons, backoffice_lesson_edit, backoffice_exams, backoffice_exam_edit
maintenance, offline
```

---

## 8. Environment

- `APP_ENV=local` (default) → SQLite, memory broker, eager Celery, DEBUG
- `APP_ENV=production` → PostgreSQL (SSL), Redis, S3, HTTPS strict, CSP
- `LOCAL_USE_REMOTE_SERVICES=True` → lokal env'dan prod Redis/DB ga ulanish
- `RAG_USE_PGVECTOR=True` (default), `RAG_EMBEDDING_MODEL`, `RAG_TOP_K`, `RAG_MIN_SIMILARITY`
- `AI_MEMORY_USE_VECTOR_RETRIEVAL=True` (default)

`.env.local` (gitga kirmaydi) namunasi:
```dotenv
APP_ENV=local
DEBUG=True
SECURITY_STRICT=False
LOCAL_USE_REMOTE_SERVICES=False
USE_S3=False
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```

---

## 9. Foydali buyruqlar

```powershell
# Venv
cd C:\Projects\azurelms
venv\Scripts\activate

# Server
python manage.py runserver

# Telegram bot polling (alohida)
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

## 10. Foydalanuvchi sozlamalari (CustomUser)

| Maydon | Tanlovlar |
|---|---|
| `ai_tone` | friendly (default), formal, brief, detailed |
| `ai_model` | gemini-2.5-flash (default), 2.5-flash-lite, 3.1-pro-preview, 3.5-flash, 3.1-flash-lite |
| `ai_memory_enabled` | true (default) / false — xotira to'liq o'chirish |
| `ai_web_search_effort` | light (default) / medium / heavy |

---

## 11. Muhim eslatmalar

1. **Loyiha OneDrive dan ko'chirildi:** `C:\Users\azure\OneDrive\...` dan `C:\Projects\azurelms` ga (SQLite I/O xatolari uchun). venv qayta yaratilgan (Python 3.14 + Django 6.0.2).
2. **Bootstrap YO'Q:** barcha shellda `tokens.css` + custom CSS. Yangi sahifa qo'shganda shu printsipga rioya qilish.
3. **`<SAVE_MEMORY>` tag:** AI javobida `<SAVE_MEMORY>category: fakt</SAVE_MEMORY>` ko'rinishida chiqsa, extractor ajratib olib `AIMemoryFact` ga yozadi. Category faqat: `preference`, `learning_goal`, `weak_topic`, `schedule`, `profile`, `do_not_remember`, `other`.
4. **`@azure` mention:** AI bo'lmagan xonada xabarda `@azure` so'zi bo'lsa, AI ham javob beradi.
5. **AI memory toggling:** Foydalanuvchi `ai_memory_enabled=False` qilsa, `MemoryService` to'liq disable bo'ladi (extract ham, retrieve ham).
6. **`.gitignore`:** `.claude/`, `.tools/`, `.codex/`, `__pycache__/`, `*.pyc`, `db.sqlite3`, `media/`, `venv/`.

---

*Bu hujjat har major feature qo'shilganda yangilanib turishi kerak. Yangilash protokoli `rules-for-agents.md` da.*
