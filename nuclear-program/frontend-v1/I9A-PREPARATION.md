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
