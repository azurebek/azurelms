# I2b — real topshiriq va quizli dars

2026-09-25, `codex/frontend-v1-lesson-practice`.
Admission: **ADMIT — launch-critical**, V1 portning I2 bog‘liqligi.

- Outcome/KPI: o‘quvchi haqiqiy topshiriq/quizni yuborib, reload’dan keyin
  aynan saqlangan ish/natijani ko‘radi; xatoda javobi yo‘qolmaydi.
- Canonical state: AssignmentSubmission / QuizAttempt / QuizAnswer / XP;
  `courses.submission_service` yozadi, web va bot uning iste’molchisi.
- Owner yuki oshmaydi: ustozning mavjud review navbati saqlanadi, yangi
  editor, baholash formulasi, tashqi provider yoki jadval yaratilmaydi.
- `frontend_v1_lesson` default OFF; OFF eski rendererga qaytaradi. Input,
  atomiklik va XP invariant tuzatishlari renderer flagiga bog‘lanmaydi.
- Native CSRF POST → redirect → GET; JS faqat qoralama, dirty guard va
  double-submit yordamchisi. Soxta API/revision/receipt kafolati yo‘q.
- Scope: learner assignment/quiz tabs, real attachment/private URL, review
  holati, tanlangan cohort, empty/error/retry, latest quiz attempt. I3ning
  teacher review UI/ro‘yxatlar/davomati bu paketga kirmaydi.
- Invariantlar: malformed quiz no-write; quiz best-XP farqi parallel
  yozuvda ham ortmaydi; resubmission bahoni tozalasa eski XP ham mos
  qaytariladi; o‘zgarmagan pending ishning takror POSTi no-op. Service
  optional enrollment oladi, uni student/course/faol scope bilan tekshiradi.
- Tekshiruv: flag ON/OFF, CSRF/auth/foreign IDs/locked cohort, form errors,
  file bytes, native/JSON/bot parity, XP/review/resubmit/duplicate/rollback,
  desktop/compact/theme/keyboard va barcha required CI.

I2a oldingi PR #121 (`5528c74`) main’da. CI `36086594312` uchala PASS;
SQLite 1862 OK (skip=40), PostgreSQL 1862 OK (skip=20), Node 13 PASS.
I2b uchun natijalar quyida faqat haqiqiy tekshiruvdan keyin yoziladi.
Staging, haqiqiy telefon, AWS rollout va owner go/no-go **ochiq**.

## Implementatsiya va dalil

Runtime/test commit: `7e2efb6`. Required CI/merge yakuni shu branchning PRida;
bu yozuv paytida lokal implementatsiya va browser tekshiruvi tugadi.

| Yo‘l | Renderer/controller | Canonical manba |
|---|---|---|
| Lesson `?cohort=…&tab=homework` | `practice_assignments.html`, `practice.js` | Existing assignment/submission, review feedback/status |
| Assignment submit | Native multipart CSRF POST → same tab/cohort GET | `submit_assignment`; invalid input bound 400, locked 403 |
| Submission file | Existing private file endpoint | Auth/access/file validation; raw media URL yo‘q |
| Lesson `?cohort=…&tab=quiz` | `practice_quizzes.html`, `practice.js` | Current questions, latest persisted attempt/answers |
| Quiz submit | Native POST/PRG; legacy JSON saqlangan | `grade_quiz`, best-attempt XP delta, transaction |
| Teacher review | Existing legacy view/navbat | `review_assignment_submission`; stale instance refresh under lock |

### Lokal tekshiruv

Barcha Django buyruqlari: `AZURELMS_SKIP_ENV_FILE=1`, `GEMINI_API_KEY=''`,
`TELEGRAM_BOT_TOKEN=''`; `.env.local` va real provider kvotasi ishlatilmadi.

- `venv\Scripts\python.exe manage.py check`: **0 issue**.
- `venv\Scripts\python.exe manage.py test courses.test_streak_wiring
  courses.test_assignment_review courses.test_locked_lesson_write_gate
  --noinput --verbosity 1`: **23 PASS**.
- `venv\Scripts\python.exe manage.py test courses.test_frontend_v1_practice
  courses.test_frontend_v1_study users.test_frontend_v1 --noinput --verbosity 1`:
  **57 OK (skip=1)**; oxirgi template/controller patchdan keyin qayta PASS.
  PostgreSQL row-lock parallel test SQLite’da capability sabab skip;
  PostgreSQL required CI uni bajarishi kerak.
- `venv\Scripts\python.exe manage.py test --noinput --verbosity 1`:
  **1879 OK (skip=42), 119.225 s**, failure/error 0.
- `node --test tests/frontend_v1/*.test.mjs`: **28 PASS** (15 practice).
- Hashed static asset tekshiruvi focused suite ichida; `git diff --check`: PASS.

Backend testlari: ON/OFF, CSRF/auth/foreign/inactive/locked cohort, empty
assignment no-write, haqiqiy PDF upload/download bytes va outsider 404,
teacher review→learner feedback, resubmit confirmation/XP reset/reapprove,
stale review no double credit, malformed quiz no-write, partial answers,
latest attempt 100→50, JSON/direct-service parity, exception rollback.
Node: text/choice-only draft, session isolation, bound server error,
revision/unknown outcome explicit restore/discard, input block until choice,
pending matching server va unchanged-text no-op, file outcome no false ack,
other-form file warning, offline, double-submit, denied storage, Back reload.

### Browser

Computer-use orqali IAB, alohida vaqtinchalik DB/media va cookieli **haqiqiy
Django** server `127.0.0.1:8050`; production DB/flaglar untouched.
1440px desktop dark, 320px compact dark, 390px light ko‘rildi; horizontal
overflow kuzatilmadi. Actual learner login→empty assignment 400→text POST→
persisted pending; quiz partial 400 tanlovni saqladi→100%/20 XP→retake 50%/
0 added XP→reload latest 50% sinandi. Empty quiz va existing needs-revision
feedback ko‘rindi. Oxirgi patchdan keyin server restart qilinib, yangi login→
text submit→keyboard Enter bilan unchanged resubmit native no-op va server
natijasiga mos qoralama tozalanishi qayta tekshirildi. Console warn/error **0**.
Viewport override olib tashlandi. Real telefon testi emas.

### Chegara va keyingi qadam

- Fayl baytlari draftga kirmaydi; xatoda faylni qayta tanlash kerak. Session
  storage bloklansa matnni nusxalash ogohlantiriladi. DB transaction filesystem
  rollbackini kafolatlamaydi; parallel tabs uchun server CAS/operation receipt
  mavjud deb da’vo qilinmaydi. Duplicate file POST idempotency qo‘shilmadi.
- Grade formulasi o‘zgarmadi. Reset qilingan bahoning eski XPsi user balansida
  qolib ketishi tuzatildi, shunda qayta review ikki marta kredit bermaydi.
- Renderer flag default OFF. OFF legacy UIga qaytaradi, xavfsiz input/atomic
  invariantlarni qaytarmaydi; model/migration yo‘q. Trial/backup o‘zgarmadi.
- I2bning required CI/merge yakuni tekshirilsin. Keyin R1 staging/test
  accounts/haqiqiy qurilma/AWS rollout vakolati va owner go/no-go kerak.
  I3 teacher review/ro‘yxatlar/davomat yangi UI porti alohida ochiq.

## PR #122 review tuzatishi

`d42b200` uchun CI `36088931120` uchala PASS: SQLite1879 skip41,
PostgreSQL1879 skip20, Node28. Reviewda P2 topildi: Telegram adapteri
default `replace_review=True` orqali yangi XP resetini tasdiqsiz bajara olardi.
`82fb6b7` canonical defaultni **False** qildi. Botda avvalgi baho/XP/izoh
tozalanishi aytiladi; alohida `as:r` tugmasi rozilikni user/assignment pending
holatiga bog‘laydi. Submit target/kindni tekshiradi, canonical service faol
accessni yana tekshiradi. Xatoda qayta yuborish kerakligi aniq aytiladi.
Legacy web view o‘z existing opt-in semantikasini explicit uzatishda qoladi;
V1 web checkbox talab qiladi. Quizga bu tuzatish taalluqli emas.

Offline `venv\Scripts\python.exe manage.py test bot.tests.AssignmentAndQuizTests
courses.test_frontend_v1_practice courses.test_assignment_review
courses.test_locked_lesson_write_gate --noinput --verbosity 1`:
**42 OK (skip=1)**, jumladan 3 yangi bot service/callback testi. Birinchi
test fixture’da majburiy dataclass argument yetishmagani tuzatilib, to‘liq
focused command qayta PASS bo‘ldi. Yangi HEAD uchun required CI qayta kerak.

Owner aniqlashtirishi: **alohida staging yo‘q, faqat AWS asosiy server bor**.
Production rollout, flaglar va test yozuvlari uchun vakolat bundan kelib
chiqmaydi. R1 zaxira/rollback/test hisob/device/owner qarori ochiq qoladi.
