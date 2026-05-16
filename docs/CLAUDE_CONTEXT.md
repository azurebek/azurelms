# Claude uchun loyiha konteksti

Bu fayl yangi Claude Code suhbati boshlanganda o'qish uchun. Loyihaning to'liq kontekstini bir fayldan beradi — qayta-qayta papkalarni o'rganishga hojat yo'q.

> **Yangi suhbatda:** "Avval `docs/CLAUDE_CONTEXT.md` ni o'qib chiq" deb ayting.

---

## 1. Loyiha haqida qisqacha

**AzureLMS** — Django-asosidagi Learning Management System. O'zbek tilidagi turk tili kurslari platformasi.

**Joylashuv:** `C:\Projects\azurelms`
**Ishchi branch:** `young-mantis-version` (asosiy)
**GitHub:** `https://github.com/azurebek/azurelms.git`

---

## 2. Tech Stack

| Qatlam | Texnologiya |
|---|---|
| Backend | Django 6.0.2, Python 3.14 |
| Async / WS | Django Channels 4.3 + Daphne (ASGI) |
| Tasks | Celery 5.6 + Redis/Valkey (lokal: `memory://`, eager) |
| DB | PostgreSQL + pgvector (prod), SQLite (lokal) |
| AI | Google Gemini API (google-genai 1.65) — Flash/Pro fallback |
| Bot | Aiogram 3.26 (Telegram) |
| Storage | DigitalOcean Spaces (S3), Whitenoise (static) |
| Admin | Jazzmin 3.0 + CKEditor5 |

---

## 3. Django apps

- `users` — CustomUser (email + telegram_id + total_xp), Notification
- `courses` — Course, Module, Lesson, Exam (reading/writing/listening/speaking), Quiz, Certificate, LessonProgress
- `cohorts` — Cohort, Enrollment (active/pending/expired/frozen), PaymentReceipt, Attendance
- `messenger` — ChatRoom (group/private/ai), Message, AILongTermMemory, LessonRAGChunk (pgvector), AIFeedback
- `gamification` — Level, Badge (Google Material Icons), EarnedBadge, Certificate
- `subscriptions` — Plan, PlanFeature, PromoCampaign, PromoCode
- `frontend` — LandingPage, AboutPage, Statistic, Testimonial, TeamMember, SiteSettings, AuthPageSettings, LegalPage (Singleton patterns)
- `backoffice` — Yashirin admin panel (URL SHA256 dan generatsiya)
- `blog` — BlogPost, BlogTag, BlogHomeSettings
- `bot` — TelegramLessonSession, TelegramLessonCheckIn

---

## 4. Asosiy oqimlar

1. **Enrollment:** User → Plan → PaymentReceipt → Admin approval → active → ChatRoom join (signals)
2. **AI Chat (RAG):** WebSocket → Message → Celery → pgvector similarity → Gemini API → broadcast
3. **Attendance:** Teacher /start_lesson → students check-in (Telegram) → /close_lesson → Attendance + XP

---

## 5. Environment

- `APP_ENV=local` → SQLite, memory broker, eager Celery, DEBUG
- `APP_ENV=production` → PostgreSQL (SSL), Redis, S3, HTTPS strict, CSP
- `LOCAL_USE_REMOTE_SERVICES=True` → lokal env'dan prod Redis/DB ga ulanish

---

## 6. Design Playground

`design-playground/` — 54 statik HTML prototip (mobile-first), Django templatega ko'chirish uchun manba.

**Manba zanjiri (Source of Truth):**
1. `design-playground/index.html` — barcha flowlar ro'yxati
2. `design-playground/DESIGN_STANDARDS.md` — qoidalar
3. `design-playground/DESIGN_TOKENS.md` — ranglar, typography, spacing
4. `design-playground/COMPONENT_CATALOG.md` — komponentlar
5. `docs/MOBILE_FIRST_READINESS.md` — mobile gate
6. `design-playground/MIGRATION_READINESS.md` — Playground → Django mapping
7. `docs/PROTOTYPE_COVERAGE_MATRIX.md` — flow + page + CSS + komponent + status matrix
8. `docs/PLAYGROUND_READINESS_GATE.md` — final gate

**CSS tizimi:** Bootstrap YO'Q. O'z token tizimi:
- `tokens.css` (design tokens)
- `foundation.css` (reset + primitives)
- shell CSS (har flow uchun: `public.css`, `auth.css`, `app.css`, ...)
- page CSS (sahifa-specific)

---

## 7. Migration jadvali (10 ta shell)

| # | Flow | Holat | Commit |
|---|---|---|---|
| 1 | **Auth & Billing** | ✅ TUGADI | `ca1c337` |
| 2 | **Public Discovery** | ✅ TUGADI | `005b2f5` |
| 3 | Student App | ⏳ Keyingi |  |
| 4 | Blog Reading |  |  |
| 5 | Blog Studio |  |  |
| 6 | Learning |  |  |
| 7 | Exam |  |  |
| 8 | Messenger |  |  |
| 9 | Legal | ✅ Public bilan birga ko'chirildi |  |
| 10 | Error |  |  |

### Auth & Billing (tugadi)

**Static (5):** `tokens.css`, `foundation.css`, `auth.css` (2241 qator), `billing.css` (2063 qator), `auth.js`

**Templates (9):**
- `auth/base.html` — shared shell (parallel-pane: chap form, o'ng visual scene)
- `registration/login.html`
- `registration/register.html`
- `registration/password_reset_form.html`
- `registration/password_reset_done.html`
- `registration/password_reset_confirm.html`
- `registration/password_reset_complete.html`
- `cohorts/checkout.html`
- `cohorts/checkout_success.html`

**Modifierlar:** `auth-shell--login/register/recovery/verify/checkout` (har biri o'z rang aksenti)

### Public Discovery (tugadi)

**Static (8):** `public.css` (3911), `public-shell-polish.css`, `about.css`, `public-course-list.css`, `public-course-detail.css`, `legal.css`, `public-shell.js` (carousel), `public-mobile.js` (mobile menu)

**Templates (7):**
- `base_public.html` — shared shell (utility strip + header + footer)
- `index.html` — billboard carousel (3 slides) + popular courses + how-it-works + testimonials + CTA
- `about.html` — hero + statistics + mission/vision + pillars + team + testimonials
- `legal_page.html` — privacy/terms/faq (LegalPage.content)
- `subscriptions/pricing.html` — plan card + features + process band
- `courses/course_list.html` — filter (level, q) + grid + pagination
- `courses/course_detail.html` — hero + facts + tabs + modules + instructor + CTA

**Logout:** POST form ishlatiladi (Django 5+ talab)

**SiteSettings property qo'shildi:** `contact_phone_href` (probelsiz `tel:` link uchun)

---

## 8. Migration usuli (har shell uchun)

Auth va Public da sinab ko'rilgan ish tartibi:

1. **CSS/JS ko'chirish** — `design-playground/assets/css/*.css` va `*.js` → `static/css/` va `static/js/`
2. **Base shell yaratish** — `templates/<flow>/base.html` yoki `templates/base_<flow>.html`
3. **Child templatelar** — har biri base ni extend qilib `{% block %}` orqali maxsus mazmun
4. **URL nomlarini tekshirish** — `{% url %}` chaqiruvlari mavjudligini Python skript bilan
5. **Template syntax tekshiruvi** — `get_template()` orqali
6. **HTTP test** — `runserver` + `curl` bilan barcha sahifalar 200 OK
7. **Vizual test** — foydalanuvchi brauzer + skrinshot
8. **Commit** — semantik xabar bilan

**Muhim:** Auth shellda `auth-shell--<modifier>` (rang aksenti), Public da `body_class` orqali sahifa-specific scope.

---

## 9. Asosiy URL nomlari

```
home, about, privacy_policy, terms_of_service, faq_page
login, register, logout, dashboard
password_reset, password_reset_done, password_reset_complete
courses (list), course_detail (pk=)
subscriptions:pricing
blog:list, blog:detail (slug=)
cohorts:checkout (course_id=), cohorts:checkout_success
help_center, certificates, subscriptions (user)
```

---

## 10. Branchlar va Git holat

| Branch | Holat |
|---|---|
| `young-mantis-version` ⭐ | Asosiy ishchi |
| `main` | Eski (35+ kun orqada, 11-aprel 2026) |
| `codex/design-system-refresh` | Lokal WIP |

**Remote:** `origin/young-mantis-version` (push qilingan)

Tozalash mumkin bo'lgan remote branchlar (merge bo'lgan):
- `origin/feature/architecture-map-*`
- `origin/production-readiness-blitzkrieg-*`

---

## 11. Muhim eslatmalar

1. **OneDrive dan ko'chirildi:** Loyiha `C:\Users\azure\OneDrive\...` dan `C:\Projects\azurelms` ga ko'chirilgan (SQLite I/O xatolari uchun). venv qayta yaratilgan (Python 3.14 + Django 6.0.2).

2. **Claude Code worktree:** Yangi suhbat boshlasangiz, Claude avtomatik `.claude/worktrees/<random-name>/` yaratadi — bu eski `main` branchga asoslangan **bo'lmaydi**, chunki hozir biz `young-mantis-version` dan ishlashga o'rganib qoldik. Yangi Claude'ga aytishingiz mumkin: "Fayllarni `C:\Projects\azurelms\` dan o'qi, worktree path emas."

3. **`.gitignore`:** `.claude/`, `.tools/`, `.codex/` papkalari ignor qilinadi.

4. **Test ma'lumotlar:** Bazada `Debug 2b3caa`, `Debug 4bcdd1` kabi sodda test kurslar bor. Real ma'lumot uchun admin orqali `Course`, `LandingPage`, `AboutPage`, `Plan` ga matn va rasm qo'shish kerak.

5. **Bootstrap YO'Q:** Auth va Public shellda Bootstrap ishlatilmaydi. Hamma narsa `tokens.css` asosida. Boshqa shellga o'tganda ham shu printsipga rioya qilish kerak.

---

## 12. Keyingi qadam — Student App

`MIGRATION_READINESS.md` → 2-navbat: Student App.

**Manba:** `design-playground/app/app-shell.html` + 9 ta child:
- `app-shell.html` → `templates/dashboard/base.html` (sidebar + topbar)
- `app-course-list.html` → `templates/courses/app_course_list.html` (yoki dashboard versiyasi)
- `app-course-detail.html` → app versiyasi
- `app-attendance.html` → `templates/users/attendance_calendar.html`
- `app-leaderboard.html` → `templates/users/leaderboard.html`
- `notifications.html` → `templates/users/notifications.html`
- `subscriptions.html` → `templates/users/subscriptions.html`
- `app-profile.html` → `templates/users/profile.html`
- `app-settings.html` → `templates/users/settings.html`

**CSS:** `app.css`, `app-course-list.css`, `app-attendance.css`, `app-leaderboard.css`, `app-notifications.css`, `app-subscriptions.css`, `app-account.css`

**Views:** Hammasi `LoginRequiredMixin` bilan, `users/views.py` da `DashboardView`, `LeaderboardView`, `AttendanceCalendarView`, `NotificationCenterView`, `SettingsView`, `UserProfileView`, `SubscriptionHistoryView` bor.

**Kutilgan murakkablik:** Auth dan biroz katta, Public dan biroz kichik. ~12-15 ta fayl.

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

# Git
git status
git log --oneline -5
git push origin young-mantis-version
```

---

*Oxirgi yangilanish: 16-may 2026 (Auth + Public shell migrationdan keyin)*
