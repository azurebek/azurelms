# Claude uchun loyiha konteksti

Bu fayl yangi Claude Code suhbati boshlanganda o'qish uchun. Loyihaning to'liq kontekstini bir fayldan beradi — qayta-qayta papkalarni o'rganishga hojat yo'q.

> **Yangi suhbatda:** "Avval `docs/CLAUDE_CONTEXT.md` ni o'qib chiq" deb ayting.

---

## 1. Loyiha haqida qisqacha

**AzureLMS** — Django-asosidagi Learning Management System. O'zbek tilidagi turk tili kurslari platformasi.

**Joylashuv:** `C:\Projects\azurelms`
**Ishchi branch:** `codex/playground-next` (yagona faol branch)
**GitHub:** `https://github.com/azurebek/azurelms.git`

---

## 2. Tech Stack

| Qatlam | Texnologiya |
|---|---|
| Backend | Django 6.0.2, Python 3.14 |
| Async / WS | Django Channels 4.3 + Daphne (ASGI) |
| Tasks | Celery 5.6 + Redis/Valkey (lokal: `memory://`, eager) |
| DB | PostgreSQL + pgvector (prod), SQLite (lokal) |
| AI | Google Gemini API (google-genai 1.65) — 2.5 Flash/Flash-Lite, 3.1 Pro, 3.5 Flash, 3.1 Flash-Lite |
| Embedding | `gemini-embedding-001` (768d), pgvector ivfflat indeks |
| Bot | Aiogram 3.26 (Telegram) |
| Storage | DigitalOcean Spaces (S3), Whitenoise (static) |
| Admin | Jazzmin 3.0 + CKEditor5, plus yashirin backoffice |

---

## 3. Django apps

- `users` — `CustomUser` (email + telegram_id + total_xp + ai_tone + ai_model + ai_memory_enabled), `UserOnboarding`, `Notification`, `NotificationBroadcast`
- `courses` — `Course`, `Module`, `Lesson`, `Assignment`, `AssignmentSubmission`, `Quiz`, `QuizAttempt`, `Exam` (reading/writing/listening/speaking), `Certificate`, `LessonProgress`
- `cohorts` — `Cohort`, `Enrollment` (active/pending/expired/frozen), `PaymentReceipt`, `Attendance`
- `messenger` — chat va AI qatlamining DB qismi (4-bo'limda alohida)
- `gamification` — `Level`, `Badge` (Google Material Icons), `EarnedBadge`, `Certificate`
- `subscriptions` — `Plan`, `PlanFeature`, `PromoCampaign`, `PromoCode`
- `frontend` — `LandingPage`, `AboutPage`, `Statistic`, `Testimonial`, `TeamMember`, `SiteSettings`, `AuthPageSettings`, `LegalPage` (Singleton patterns)
- `backoffice` (`core/views.py`) — yashirin admin panel: dashboard, users, course/lesson/exam editor
- `blog` — `BlogPost`, `BlogTag`, `BlogHomeSettings`
- `bot` — `TelegramLessonSession`, `TelegramLessonCheckIn`
- `ai/` (Python paket, Django app emas) — agent qatlami (4-bo'limda alohida)

---

## 4. AI + Messenger arxitekturasi

### 4.1 Messenger modellari (`messenger/models.py`)

- `ChatRoom` — turlar: `group` (cohort), `private` (1:1), `ai` (AzureAI)
- `Message` — `is_ai_response`, `context_lesson` (sehrli maydon: o'quvchi qaysi darsda turib so'rashi)
- `AILongTermMemory` — legacy unstructured text (yangi `AIMemoryFact` ga ko'chmoqda)
- `AIMemoryFact` — strukturali xotira: category (preference/learning_goal/weak_topic/schedule/profile/do_not_remember/other), status (active/archived/rejected), visibility (user_visible/internal), confidence, fingerprint (SHA256), embedding
- `AIMemoryTrace` — har bir xotira eventi (retrieved/saved/skipped/archived) + reason + score + metadata
- `AIConversationSummary` — har chat xona uchun rolling summary (eski xabarlarni siqib boradi)
- `AIResponseRun` — telemetry: status (pending/running/succeeded/fallback/failed), skill_slug, model_name, duration_ms, metadata (used_tools, rag_sources)
- `AIFeedback` — AI xabarlariga thumbs up/down (per student)
- `LessonRAGChunk` — pgvector + JSON embedding fallback

**Migration:** 0001–0010, oxirgisi `0010_airesponserun`.

### 4.2 AI agent qatlami (`ai/`)

```
ai/
├── agent/
│   ├── engine.py         AIEngine.generate_reply(AIRequest) → AIResponse
│   └── types.py          AIRequest, AIResponse, ProviderResponse
├── skills/
│   ├── registry.py       9 ta skill: keyword + priority + context_lesson boost orqali tanlash
│   ├── general_chat/SKILL.md
│   ├── lesson_explainer/SKILL.md
│   ├── quiz_generator/SKILL.md
│   ├── homework_checker/SKILL.md
│   ├── grammar_corrector/SKILL.md
│   ├── speaking_coach/SKILL.md
│   ├── writing_feedback/SKILL.md
│   ├── course_navigator/SKILL.md
│   └── student_progress_coach/SKILL.md
├── tools/
│   └── context.py        ToolContextService — backenddan deterministik snapshot:
│                         lesson_context, homework_context, quiz_context,
│                         student_progress, course_navigator
├── memory/
│   ├── types.py          MemoryCandidate, MemoryExtraction, SavedMemory,
│   │                     ScoredMemoryFact, ConversationContext
│   ├── policy.py         MemoryPolicy: skip rules, sensitive filter, category infer
│   ├── extractor.py      <SAVE_MEMORY>...</SAVE_MEMORY> tag parser
│   ├── repository.py     DB I/O, dedupe fingerprint, decay/archive maintenance
│   │                     (DECAY_START_DAYS=30, ARCHIVE_STALE_DAYS=180)
│   ├── evaluation.py     MemoryQualityEvaluator (trace metadata uchun)
│   ├── semantic.py       SemanticMemoryScorer: lexical + alias + vector cosine
│   │                     (env AI_MEMORY_USE_VECTOR_RETRIEVAL) + category prior
│   ├── retriever.py      relevant facts → prompt, last_used_at marker, trace emit
│   ├── summarizer.py     ConversationSummarizer: incremental "Oldingi suhbat..."
│   └── service.py        Facade: yuqoridagilarni biriktiradi
├── prompts/
│   └── builder.py        PromptBuilder.build(...) — system + skill + tone +
│                         RAG + memory + tool ctx + xavfsizlik blok
├── providers/
│   └── gemini.py         GeminiProvider + Flash/Pro fallback
└── rag/
    └── context.py        RAGContextService → (lesson_context, rag_context,
                          chunks, sources, access_note)
```

### 4.3 Engine oqimi (`ai/agent/engine.py`)

`AIEngine.generate_reply(AIRequest)`:
1. `skill_registry.select_for_request` — keyword + priority + lesson boost (yoki `requested_skill_slug` orqali user tanlovi)
2. `tool_context_service.build(request, skill)` — skill `tool_slugs` ga qarab backend snapshotlari
3. `memory_service.sanitize_user_question` — `<SAVE_MEMORY>` taglarini inputdan tozalash
4. `memory_service.get_conversation_context` — oxirgi 8 ta xabar + eski qismlar uchun rolling summary
5. `memory_service.render_relevant_memory` — top-7 fakt (lexical/semantic/vector)
6. `rag_service.build` — `messenger.rag.retrieve_relevant_chunks` (pgvector → fallback dot-product)
7. `prompt_builder.build` — system + tone + skill instr + memory + summary + lesson ctx + RAG + tool ctx + user message
8. `provider.generate` — Gemini call (user `ai_model` first, fallback chain)
9. `memory_service.extract_from_reply` — `<SAVE_MEMORY>` taglarni ajratish
10. `memory_service.save_candidates` — `AIMemoryFact` ga saqlash (dedupe + trace)
11. `AIResponse(text, model_name, skill_slug, metadata={rag_sources, used_tools, summarized_messages, ...})`

### 4.4 RAG (`messenger/rag.py`)

- `gemini-embedding-001` (768 dim), 180 word chunks, 40 word overlap
- pgvector ishlatilsa `is_pgvector_ready()` → SQL `<=>` (cosine) + ivfflat indeks
- Aks holda Python `_cosine_similarity` fallback
- `context_lesson` bo'lsa: 0.08–0.12 boost
- `_active_course_ids_for_user(user)` orqali enrollment scope (staff/superuser → cheksiz)
- Management: `python manage.py reindex_rag --course-id <id> --force`
- Cache: embedding 7 kun (Django cache)

### 4.5 Chat oqimi

```
client (websocket)
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

---

## 5. Asosiy oqimlar (foydalanuvchi tomondan)

1. **Enrollment:** User → Plan → PaymentReceipt → Admin approval → active → ChatRoom join (signals)
2. **AI Chat:** WebSocket → Message → Celery → memory + RAG + skill + tool ctx + Gemini → broadcast
3. **Attendance:** Teacher `/start_lesson` → studentlar Telegramda check-in → `/close_lesson` → Attendance + XP
4. **AI Memory boshqaruvi:** `/users/settings/ai-memory/` — list, archive, reject, clear-all, toggle (`ai_memory_enabled`)

---

## 6. Environment

- `APP_ENV=local` → SQLite, memory broker, eager Celery, DEBUG
- `APP_ENV=production` → PostgreSQL (SSL), Redis, S3, HTTPS strict, CSP
- `LOCAL_USE_REMOTE_SERVICES=True` → lokal env'dan prod Redis/DB ga ulanish
- `RAG_USE_PGVECTOR=True` (default), `RAG_EMBEDDING_MODEL`, `RAG_TOP_K`, `RAG_MIN_SIMILARITY`
- `AI_MEMORY_USE_VECTOR_RETRIEVAL=True` (default) — semantic memory uchun

---

## 7. Design Playground va frontend

`design-playground/` — 54 statik HTML prototip (mobile-first), Django templatega ko'chirish uchun manba.

**Manba zanjiri:**
1. `design-playground/index.html` — barcha flowlar
2. `design-playground/DESIGN_STANDARDS.md`, `DESIGN_TOKENS.md`, `COMPONENT_CATALOG.md`
3. `design-playground/MIGRATION_READINESS.md` — Playground → Django mapping
4. `docs/MOBILE_FIRST_READINESS.md`, `docs/PROTOTYPE_COVERAGE_MATRIX.md`, `docs/PLAYGROUND_READINESS_GATE.md`

**CSS tizimi (Bootstrap YO'Q):**
- `tokens.css` (design tokens) + `foundation.css` (reset + primitives)
- har flow uchun shell CSS (`public.css`, `auth.css`, `app-shell.css`, `messenger-shell.css`, `exam-shell.css`, `backoffice-shell.css`, `blog-shell.css`, `blog-studio-shell.css`)
- sahifa-specific CSS (`public-index.css`, `app-course-detail.css`, `exam-listening.css`, ...)
- jami 45 ta CSS fayl

---

## 8. Migration jadvali (10 ta shell)

| # | Flow | Holat | Shell CSS |
|---|---|---|---|
| 1 | **Auth & Billing** | ✅ TUGADI | `auth.css`, `billing.css`, `billing-status.css` |
| 2 | **Public Discovery** | ✅ TUGADI | `public.css` + page CSS lar |
| 3 | **Student App (Dashboard)** | ✅ TUGADI | `app.css`, `app-shell.css` + app-*.css |
| 4 | Blog Reading | ✅ TUGADI | `blog-shell.css`, `blog-article.css`, `blog-tags.css`, `blog-django-bridge.css` |
| 5 | Blog Studio | ✅ TUGADI | `blog-studio-shell.css`, `blog-studio-new-post.css`, `blog-studio-analytics.css` |
| 6 | Learning (Course detail, Lesson) | ✅ TUGADI | `public-course-detail.css`, `app-course-detail.css` + `lesson_detail.html` |
| 7 | Exam | ✅ TUGADI | `exam-shell.css`, `exam-listening.css`, `exam-speaking.css`, `exam-writing.css`, `exam-review.css` |
| 8 | **Messenger** | ✅ TUGADI | `messenger-shell.css` + `ai.html`/`group.html`/`tutor.html` |
| 9 | Legal | ✅ TUGADI | `public-legal.css` |
| 10 | Error | ✅ TUGADI | `error-403/404/500/maintenance/offline.css` |

Backoffice ham mavjud (`backoffice-shell.css` + course/lesson/exam/users editor).

---

## 9. URL nomlari (eng muhimlari)

```
home, about, privacy_policy, terms_of_service, faq_page
login, register, logout
dashboard, profile, settings, leaderboard, notifications, help_center, certificates
update_avatar, update_password, update_ai_tone, update_ai_model
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

## 10. Branchlar va Git holat (snapshot 2026-05-24)

| Branch | Holat |
|---|---|
| `codex/playground-next` ⭐ | Faol ishchi — `origin/codex/playground-next` dan 18 commit oldinda |
| `main` | Juda eski (40+ kun orqada) |
| `playground` | Lokal arxiv |

**Remote:** `origin/main`, `origin/codex/playground-next`, `origin/playground`.

`young-mantis-version` endi mavjud emas — barcha so'nggi ish `codex/playground-next` ga ko'chgan.

---

## 11. Muhim eslatmalar

1. **OneDrive dan ko'chirildi:** Loyiha `C:\Users\azure\OneDrive\...` dan `C:\Projects\azurelms` ga ko'chirilgan (SQLite I/O xatolari uchun). venv qayta yaratilgan (Python 3.14 + Django 6.0.2).

2. **Claude Code worktree:** Yangi suhbat boshlasangiz, Claude avtomatik `.claude/worktrees/<random-name>/` yaratadi. Fayllarni `C:\Projects\azurelms\` dan o'qishi kerak, worktree path emas. Yangi Claude'ga shuni eslatib qo'ying.

3. **`.gitignore`:** `.claude/`, `.tools/`, `.codex/`, `__pycache__/`, `*.pyc`, `db.sqlite3`, `media/`, `venv/`.

4. **Test ma'lumotlar:** Bazada `Debug 2b3caa`, `Debug 4bcdd1` kabi sodda test kurslar bor. Real ma'lumot uchun admin orqali `Course`, `LandingPage`, `AboutPage`, `Plan` ga matn va rasm qo'shish kerak.

5. **Bootstrap YO'Q:** Barcha shellda `tokens.css` + custom CSS. Yangi sahifa qo'shganda shu printsipga rioya qilish.

6. **AI memory toggling:** Foydalanuvchi `ai_memory_enabled=False` qilsa, `MemoryService` to'liq disable bo'ladi (extract ham, retrieve ham). Test yozayotganda shuni hisobga oling.

7. **`<SAVE_MEMORY>` tag:** AI javobida `<SAVE_MEMORY>category: fakt</SAVE_MEMORY>` ko'rinishida chiqsa, extractor ajratib oladi va `AIMemoryFact` ga yozadi. Category faqat: `preference`, `learning_goal`, `weak_topic`, `schedule`, `profile`, `do_not_remember`, `other`.

8. **`@azure` mention:** AI bo'lmagan xonada xabarda `@azure` so'zi bo'lsa, AI ham javob beradi (group/tutor chatlarda yordamchi sifatida).

---

## 12. AI skills (qisqacha xarita)

| Slug | Trigger keywords (qisqartirilgan) | Tools | Priority |
|---|---|---|---|
| `general_chat` | (default) | student_progress, course_navigator | 0 |
| `lesson_explainer` | tushuntir, izohlab ber, dars, mavzu | lesson_context, course_navigator | 20 |
| `quiz_generator` | quiz, test, savol tuz, mashq tuz | lesson_context, quiz_context | 80 |
| `homework_checker` | homework, vazifa, tekshir, baholab ber | lesson_context, homework_context, student_progress | 70 |
| `grammar_corrector` | grammar, grammatika, xato, tuzat, zamon | lesson_context | 65 |
| `speaking_coach` | speaking, gapirish, talaffuz, og'zaki | lesson_context, student_progress | 60 |
| `writing_feedback` | writing, essay, insho, paragraph | lesson_context, homework_context | 60 |
| `course_navigator` | qaysi dars, keyingi dars, roadmap | course_navigator, student_progress | 50 |
| `student_progress_coach` | progress, natija, kuchsiz joy, reja tuz | student_progress, course_navigator | 55 |

Skill auto bo'lsa `context_lesson` bo'lsa `lesson_explainer` ga +2 boost. Foydalanuvchi UI dan `requested_skill_slug` orqali majburiy tanlay oladi.

---

## 13. Foydali buyruqlar

```bash
# Venv
cd C:\Projects\azurelms
venv\Scripts\activate           # PowerShell
source venv/Scripts/activate    # Git Bash

# Server
python manage.py runserver

# Tekshiruvlar
python manage.py check
python manage.py migrate

# RAG indeks
python manage.py reindex_rag --force
python manage.py reindex_rag --course-id 5 --force

# Test (messenger AI flow uchun)
python manage.py test messenger.tests

# Git
git status
git log --oneline -10
git push origin codex/playground-next
```

---

*Oxirgi yangilanish: 24-may 2026 (AI agent + memory + skills + tool context + RAG course retrieval bosqichidan keyin)*
