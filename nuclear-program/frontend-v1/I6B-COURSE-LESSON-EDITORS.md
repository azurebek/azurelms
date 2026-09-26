# I6b — kurs/dars muharrirlari va dars materiallari

## Admission — runtime tahriridan oldin

**ADMIT — launch-critical.** Frozen V1 course list/create/edit va lesson
index/edit ko‘rinishlarini real kontentga ulash. KPI: besh mavjud URL oilasi
va per-link settings/reorder/detach native CSRF/PRG bilan, scoped access,
bound invalid draft, 320–1280 overflow0 va uch required CI PASS.

- Canonical state: Course, Module, Lesson, LessonMaterial; mavjud
  CourseBackofficeForm/LessonBackofficeForm/LessonMaterialForm va library
  services yozadi. teacher_course_queryset yagona scope. XP, release,
  enrollment, quiz, assignment, narx hisoblash qoidalari o‘zgarmaydi.
- Presentation: default-OFF frontend_v1_editors; teacher shell, explicit
  GET filters va saqlash tasdig‘i. Prototipdagi 4 course input bilan eski
  real formdagi qolgan 10 maydonni yo‘qotmaymiz: jami 14 maydon. Darsda 6.
  Mavjud modul tanlovi — ustozning ruxsatli kurslari; uni yangi biznes
  cheklovi bilan toraytirmaymiz. UI bu scope’ni ochiq bildiradi.
- V1 /lessons/ avtomatik birinchi darsni tahrirlamaydi: scoped tanlov.
  Eski first-lesson create faqat ustozda hech qanday dars bo‘lmaganda
  shu manzilda saqlanadi; mavjud darslar bo‘lsa POST aniq ID talab qiladi.
  Yangi umumiy lesson-create yoki modul/quiz authoring bu paketga kirmaydi.
- User/action/object-bound HMAC saved-value snapshots; stale409 no-write.
  Course/Lesson modelida revision/timestamp yo‘q: bu barcha admin/ORM
  writerlar yoki A→B→A uchun monotonic revision kafolati EMAS. Yangi
  migration/receipt engine yo‘q. Create global idempotency emas; native
  PRG, duplicate UI guard, unknown natijada holatni tekshirish.
- Course/Lesson write atomic plain-row lock; material endpoints lesson →
  resource → link tartibida seriallashadi. Link snapshot resource policy
  va link updated_atni qamraydi; reorder barcha linklarni tekshiradi.
  Resource/file delete qilinmaydi, detach faqat dars bog‘lanishini uzadi.
- Existing library form controller qayta ishlatiladi: dirty exit, cross-form
  discard confirm, no retry/storage. No-JS ham native forms bilan ishlaydi.
- Owner haftalik yangi monitoring vazifasini olmaydi. Flag OFF rendererlarni
  qaytaradi, kontentni emas; in-flight V1 POST guardlari rollbackda qoladi.
  AWS deploy, prototype edit, provider call yoki production data yo‘q.

## Qabul

- [-] Runtime va regressiya.
- [ ] Isolated browser desktop/mobile va asosiy amallar.
- [ ] Required CI/review/main.
- [ ] AWS/native-device release (alohida).

I6a PR135 MERGED `12b0e3c`; final CI36214042911 uchala PASS:
SQLite2063 skip44, PostgreSQL2063 skip20, Node95.
[Final acceptance](https://github.com/azurebek/azurelms/pull/135#issuecomment-5842697120).
