# I3b — ustoz ro‘yxatlari va davomat

2026-09-25. Admission: **ADMIT — launch-critical**, approved V1 port.
Branch: `codex/frontend-v1-teacher-directory`, base `4e48416`.
Runtime/test commit: `77cc15b`.

- Outcome/KPI: ustoz o‘z kurs/guruh/o‘quvchisini topib, aynan tanlangan
  guruh va dars davomatini bir marta saqlaydi; learner XP canonical natija.
  Yangi owner boshqaruvi, prototype, framework yoki migration yo‘q.
- Source: frozen teacher_courses, teacher_cohorts, teacher_students,
  teacher_attendance markup + teacher_directory.css; existing V1 shell/tokens.
- Read: existing scoped teacher querysets/counts/search/pagination. Write:
  `cohorts.attendance_service.upsert_attendance_and_xp`; batch wrapper shu
  servisga ulanadi, yangi XP/progress formulasi bo‘lmaydi.
- Davomat va darsni ochish V1da alohida: approved prototype singari existing
  teacher_release sahifasiga link. Davomat XP/streakga ta’siri ochiq yoziladi;
  prototype’dagi “XP ulanmagan” copy productionga ko‘chmaydi.
- Explicit POST target + query/body mosligi; noma’lum/begona/inactive target
  boshqa guruh/darsga fallback qilmaydi (OFF ham). Blank mark eski qaydni
  o‘chirmaydi. Invalid status/roster/confirmation barcha yozuvdan oldin qaytadi.
- Snapshot current roster/record revision bilan tekshiriladi, canonical
  attendance writers cohort lock orqali serialize qilinadi; eski varaq 409.
  Native CSRF/PRG, bound inputs, scoped session draft; automatic retry yo‘q.
- `frontend_v1_teacher` default OFF; OFF legacy renderer, data saqlanadi.
  Eski V1 POST rollbackdan so‘ng no-write. Legacy attendance→optional release
  kontrakti saqlanadi; V1 release alohida mavjud tasdiq yo‘liga yo‘naltiradi.
- Test: ON/OFF, owner/staff/learner/foreign IDs; empty/long/multi/page/filter,
  date/XP/streak/duplicate/stale/invalid/all-or-nothing, draft/reload/offline,
  desktop/mobile/light/dark/keyboard va uch required CI.
- R1 AWS vakolati yo‘q, faqat disposable local DB/media bilan browser.
  I3a fresh PR #123 MERGED `4e48416`; CI `36092407070` uchala PASS
  (SQLite1898 skip42, PostgreSQL1898 skip20, Node31).

## Mapping va cheklovlar

| Real route | V1 read / write |
|---|---|
| `/teacher/courses/` | Existing teacher course scope, lesson/exam/active-membership counts, cohort links; editors existing backoffice |
| `/teacher/cohorts/` | Existing scoped groups, active/pending/total membership, active group attendance/release links |
| `/teacher/students/?cohort=&q=&page=` | Scoped membership, real name/email/effective status/progress/XP; 25-row SQL pagination, preserved search |
| `/teacher/attendance/?cohort=&lesson=` | Explicit native GET selectors; CSRF + required confirmation + revision POST; canonical service batch → PRG |

Current server status/date/XP and editable draft are separate. Row helper
retains attendance XP and streak formulas; batch is one transaction so any
invalid row/error rolls back the whole sheet. Shared user writes have stable
user-ID order across cohorts. Canonical writers and admin save participate
in the cohort lock; existing admin XP semantics are not redesigned here.
Historical multiple records remain; latest date/PK is edited, not deleted.

Revision is an optimistic snapshot, not a durable operation receipt. The
native redirect flash acknowledges only the exact committed snapshot/input,
bounded to one sheet in the session; uncertain sends are never auto-retried.
Flag OFF keeps legacy optional attendance→release behavior; explicit bad
POST targets never fall through to another group, in either renderer.
No model/migration, provider call, prototype runtime, new dependencies or AWS writes.

## Local evidence — 2026-09-25

All Python checks with `AZURELMS_SKIP_ENV_FILE=1`, `GEMINI_API_KEY=''`,
`TELEGRAM_BOT_TOKEN=''`; temporary test DB/media, no canonical DB seed/migrate.

- `venv\Scripts\python.exe manage.py check`: 0 issues.
- `venv\Scripts\python.exe manage.py test --noinput --verbosity 1`:
  **1912 OK (skip=44)**, 353.475 s. This full run preceded the final
  localized-error copy / error-stack CSS / sorted shared-user-write correction;
  latest focused results and required CI below cover the final code.
- `node --test tests/frontend_v1/*.test.mjs`: **34 PASS** including attendance
  bulk draft-only, stale draft blocks bulk, exact native all-blank no-op ack;
  existing quiz/review/offline/Back/duplicate/storage guards retained.
- Final `venv\Scripts\python.exe manage.py test core.test_frontend_v1_directory
  core.tests core.test_attendance_parity core.test_attendance_releases_lesson
  --noinput --verbosity 1`: **57 OK (skip=1)**. Includes stable user-write-order
  regression; PostgreSQL sheet concurrency test is intentionally skipped locally.
- `git diff --check`: PASS. Isolated `collectstatic` completed on browser server.
- Computer-use/IAB real Django8052, isolated synthetic users/cohorts/media:
  desktop1440 (courses dark, students/attendance light), mobile320 (all four
  pages light, attendance dark). Long name/email/course, empty search and
  cohort-preserving clear tested; document width305 at viewport320, no overflow.
  Selector alone did not navigate; bulk selection left server status unchanged.
  Enter/native save present + partial showed server10/3 XP and explicit unchanged
  lesson release. Second tab's stale POST returned409 with current server state,
  retained draft, unchecked confirmation; mobile native save also succeeded.
  Browser found side-by-side narrow error paragraphs: stacked locally and error
  copy localized, server restarted and same stale path rechecked. Console warn/error
  0 on final verification tab. Real phone/network interruption remains R1, not
  claimed by viewport simulation; draft/offline cases are Node regression coverage.

Required CI/merge evidence is completed in the branch PR. R1 remains OPEN:
only AWS primary exists, backup/rollback/test account/device/go-no-go need
agreement; default OFF and deploy0. I4 human Messenger B is the next port,
separate from its AI adapter. Frozen trial and backup unchanged.
