# I3a — ustoz tekshiruv navbati va yozma ishni baholash

2026-09-25, `codex/frontend-v1-teacher-review`.
Admission: **ADMIT — launch-critical**, approved V1 port, TCH-02 / J02.

- Outcome/KPI: ustoz o‘z kursidagi ishni topadi, ko‘rib qaror/izoh/XPni
  saqlaydi; o‘quvchi aynan serverdagi natijani ko‘radi. Navbatdan qaytish va
  xatoda izoh yo‘qolmasin. Owner uchun yangi boshqaruv yuzasi yaratilmaydi.
- Source: frozen `pages/grading.html`, `pages/assignment_review.html` va
  mavjud V1 shell/tokenlar. Runtime URL: `teacher_grading`,
  `teacher_grade_assignment`, `submission_file`. Yangi trial/redesign yo‘q.
- Canonical scope: `teacher_course_queryset`; canonical writer:
  `review_assignment_submission`, XP/audit/notification o‘sha servisda.
  Web faqat form/renderer, bot mavjud optional kontrakt iste’molchisi.
- I3a: queue pending/reviewed/all, scoped kurs filtri/pagination, assignment
  detail, bound validation va CSRF POST/PRG. Exam detail I8da, ro‘yxatlar/
  davomat I3bda; ular eski ishlaydigan sahifaga aniq belgi bilan o‘tadi.
- V1 reviewda explicit qaror/tasdiq, integer XP existing max ichida.
  Noma’lum action yoki yaroqsiz XP yozmaydi. Ko‘rilgan `updated_at` canonical
  user lock ostida solishtiriladi; ish/review yangilangan bo‘lsa 409 va
  fresh ish + bound izoh qaytadi, tasdiq qayta talab qilinadi. Migration yo‘q.
- Draft yordamchisi umumiy `practice.js`: faqat izoh/qaror/XP maydon
  kiritmalari (tasdiq/CSRF/fayl emas), user/session/record scope. Bu saqlangan
  baho emas. Reload/unknown natija avtomatik qayta yuborilmaydi.
- `frontend_v1_teacher` default OFF, OFF legacy renderer; all variantsda
  noma’lum action no-write. Default baholash formulasi o‘zgarmaydi.
- Verification: ON/OFF, role/course/private file, empty/multi-record/long,
  native POST/CSRF/invalid/stale/duplicate, XP/audit/notification/learner
  projection, session draft, desktop/mobile/theme/keyboard; required CI.
- AWS/staging vakolati yo‘q; faqat synthetic isolated local sinov.

I2 fresh proof: PR #122 MERGED `c8c3864`, CI `36089727327` uch required
job PASS (SQLite1882 skip41, PostgreSQL1882 skip20, Node28). I2 tugagan;
R1 release hali ochiq. Owner: alohida staging yo‘q, faqat AWS asosiy server.

## Implementatsiya va verifikatsiya

Runtime/test commit: `4348242`. Required CI va merge yakuni branch PRida;
AWS release yoki umumiy I3 PASS emas.

- `core/frontend_v1_review.py`: real scoped queue va Django form;
  har tur 25 yozuvdan pagination, status/course/query saqlanadi.
- `core/teacher_views.py`, `courses/submission_service.py`: native CSRF/PRG,
  canonical user-lock ostida revision check; bound 400/409 tasdiqni tozalaydi.
  Flag o‘chirilgach eski V1 form POSTi 400/no-write. Legacy valid contract qoladi.
- `templates/frontend_v1/teacher/{grading,grade_assignment}.html` va `study.css`:
  approved markup/tokenlar. Read-only student answer escaped; fayl existing
  private endpointda. Mobil blockquote default yon chekinishi olib tashlandi.
- Existing `practice.js` qayta ishlatildi, yangi paket/controller yo‘q.
  Server normalizatsiyasi (revision XP=0 yoki `015` → 15) uchun native
  POST/redirect session flash exact accepted inputni bir marta beradi. U faqat
  shu submission va saqlangan revisionda, yangi revision + matching pending
  draftni reconciliate qiladi. Persisted result alohida serverdan ko‘rsatiladi.
  Bu durable receipt emas: flash yo‘qolsa/iste’mol qilinsa conservative
  conflict + explicit restore/discard qoladi; avtomatik retry bo‘lmaydi.
- `core/test_frontend_v1_review.py`: role/course, owner, malformed IDs,
  private PDF bytes, pagination, invalid XP/action/confirm/CSRF, flag rollback,
  stale student resubmit/other review, XP delta/audit/notification/learner,
  one-shot/revision-scoped flash va PostgreSQL-only concurrent same-revision.
- Offline focused command:
  `venv\Scripts\python.exe manage.py test core.test_frontend_v1_review courses.test_assignment_review courses.test_frontend_v1_practice core.tests --noinput --verbosity 1`
  → **65 OK (skip=2)**; SQLite row-lock tests skipped, PostgreSQL CI kerak.
  `node --test tests/frontend_v1/*.test.mjs` → **31 PASS**.
  `venv\Scripts\python.exe manage.py test --noinput --verbosity 1`
  → **1897 OK (skip=43)**, 112.500s.
  `manage.py check` → 0 issue; `git diff --check` PASS.
  Barcha Python sinovlarida `AZURELMS_SKIP_ENV_FILE=1`, `GEMINI_API_KEY=''`,
  `TELEGRAM_BOT_TOKEN=''`; external provider/bot chaqirilmaydi.
- Computer-use/IAB: disposable real Django DB/media + separate cookies, 8051.
  Desktop1440 dark review, mobile320 dark native Enter submit, mobile390 light
  queue/long course filter. No horizontal overflow (320 viewport client/scroll
  305/305); answer width231px. Revision with XP15 → persisted0 va flash;
  approve15 → teacher result → real learner dashboard15 + homework feedback.
  Reload, return-to-queue, empty queue, course selection ham tekshirildi.
  Console warn/error 0; viewport override reset.
- Chegara: haqiqiy telefon, AWS/static/private-media production smoke va
  deploy/rollback hali tekshirilmagan. Source trial/backup/canonical DB untouched.
  I3 umumiy yopilmaydi: ro‘yxatlar/davomat keyingi bo‘lak. Exam detail I8.
