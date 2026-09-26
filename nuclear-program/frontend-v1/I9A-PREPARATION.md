# I9a — Classbook tayyorlovi

ADMIT — launch-critical. Owner tasdiqlagan frozen V1ni canonical Classbookga
ulash; yangi prototype yoki mahsulot qoidasi emas. Asosiy KPI: ustozning
guruh → mashq → playbookni saqlash oqimi xatosiz tugashi. Owner yuki oshmaydi.

Qamrov: teacher_home, exercise_list/create/edit, playbook_edit/add/remove/move
va mavjud session_start servisiga tasdiqlangan o'tish. Jonli session,
learner javobi va natija rendererlarining I9b porti alohida qoladi.

Canonical: ExerciseForm/Exercise, LessonPlaybookForm/LessonPlaybook,
PlaybookExercise; start_class_session o'zgarmaydi. Web adapteri ball/access/
Telegram/davomat qoidalarini ko'chirmaydi. GET yangi playbook yaratmaydi.
POST native CSRF/PRG; old/stale/duplicate forma rad etiladi. File/media real
formada qoladi. Yangi formaning yaratilish kaliti bitta Exercise qatorida,
cheksiz receipt jadvali yo'q. Model save revisioni soatga qaram emas.

Default-OFF frontend_v1_classbook_preparation; OFF eski UI, in-flight V1
POST no-write. Additive classbook0003 kerak; rollback schema/data o'chirmaydi.
DB snapshot va qatnashuvchi web writer locklari stale himoyasi; ixtiyoriy
QuerySet.update/bulk/admin child ABA uchun global transaction kafolati yo'q.
Draft shu DOMda: xato matni qoladi, faylni qayta tanlash kerak. Private javob
kaliti browser storagega yozilmaydi. Network unknown avtomatik resend emas.

Tekshiruv rejasi: provider-free classbook regression, yangi V1 scope/CSRF/
GET-no-write/stale/replay/rollback/forms/snapshot testlari, Node controllers,
check/migration drift, synthetic local browser desktop/mobile va required CI.
AWS, haqiqiy Telegram, real qurilma va owner content acceptance bu paket emas.

## Lokal dalil — 2026-09-26

- Runtime `eacce59`; 5 URL yuzasi/4 template oilasi V1ga ulandi.
- Provider-free `venv/Scripts/python.exe manage.py test classbook --noinput --failfast`:
  **64 OK, skipped3, 11.430s**. Yangi 21 test, biri PostgreSQL parallel-add.
- `venv/Scripts/python.exe manage.py test --noinput`: **2286 OK,
  skipped55, 255.780s** (final label/legacy-error-status va CSS follow-updan oldingi run).
- `node --test tests/frontend_v1/*.test.mjs`: **111 PASS**. Yangi JS writer yo'q;
  shared library native-submit/dirty/offline guard va canonical kind help qayta ishlatildi.
- `manage.py check --fail-level WARNING`: 0 issue; `makemigrations --check --dry-run`: no changes.
- IAB8073: native save → boshqa tab stale409/unsaved text retained.
  IAB8074 fresh code: login → short_answer create → bank → empty playbook
  create → exercise attach. Keyboard Enter/Space orqali; IAB click/setChecked
  o'zgarishni qo'llamadi, klaviatura yo'li ishladi. Console warning/error0.
- 5 route × 320/639/640/1023/1024/1280 = **30 readback, positive overflow0**.
  Desktop dark/mobile light screenshot ko'rildi; CSS grid content-stretch tuzatildi.
  Ignored local dalil: `playground/frontend-v1-smoke/i9a-desktop.png`, `i9a-mobile.png`.
  Viewport override reset. Native touch/device test emas.
- Dastlab widget template loader/attrs yo'li testda topilib tuzatildi.
  Ten-kind testi eski ExerciseForm muammosini ko'rsatdi: kind yangi, model clean
  eski config/keyni o'qirdi. Parsed definition endi model validationdan oldin
  instancega ulanadi; canonical parser/grader va validatorlar susaytirilmagan.
- Private-media URL chiqmaydi; keep/clear native widget saqlandi. Uploadning
  real qurilma browser drilli bu paketda o'tkazilmadi.
- Bo'sh legacy-nav sarlavhasi endi render qilinmaydi; preview serverning cached
  template screenshotida eski sarlavha qolishi mumkin. Runtime CI final headni tekshiradi.
- CI/review/main acceptance PRda qayd etiladi. AWS/current DB/prototype o'zgarmadi.
