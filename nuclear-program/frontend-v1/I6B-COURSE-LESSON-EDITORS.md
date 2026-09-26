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

- [x] ~~Runtime va regressiya — `c72c1fd`.~~
- [x] ~~Isolated browser desktop/mobile va asosiy amallar.~~
- [x] ~~Required CI/review/main: PR136 MERGED `0278331`.~~
- [ ] AWS/native-device release (alohida).

I6a PR135 MERGED `12b0e3c`; final CI36214042911 uchala PASS:
SQLite2063 skip44, PostgreSQL2063 skip20, Node95.
[Final acceptance](https://github.com/azurebek/azurelms/pull/135#issuecomment-5842697120).

## Implementatsiya va dalil

`core/frontend_v1_editors.py` — presentation/snapshot adapteri. Mavjud
`core/views.py` va `library/backoffice_views.py` canonical form/servicesga
yozadi; yangi writer engine yo‘q. Ustoz nav va library picker havolasi
flag holatini ko‘rsatadi. Link form IDlari noyob; barcha order inputlar o‘z
native formasi ichida, dirty guard ularni ham qamraydi. Material xato
javobida bound qoralama qaytariladi; qayta GET bo‘lmagan mutation URLiga
emas, saqlangan darsga qaytish havolasi bor. Non-field validation errors
legacy yo‘lda ham KeyErrorga aylanmaydi.

Offline barcha buyruqlar `AZURELMS_SKIP_ENV_FILE=1 GEMINI_API_KEY= TELEGRAM_BOT_TOKEN=`:

| Buyruq | Natija |
|---|---|
| `venv/Scripts/python.exe manage.py test core.test_frontend_v1_editors library core.test_backoffice_courses core.test_backoffice_lessons --noinput` | final111 OK (11.479s), 28 yangi editor test |
| `venv/Scripts/python.exe manage.py test --noinput` | final2091 OK, skip45 (124.588s) |
| `node --test tests/frontend_v1/*.test.mjs` | 95 PASS; mavjud library controller qayta ishlatiladi |
| `manage.py check --fail-level WARNING` | 0 issue |
| `manage.py makemigrations --check --dry-run` | no changes |
| `git diff --check` | PASS |

Final required CI36215540990 uchala PASS: SQLite2091 skip44,
PostgreSQL2091 skip20, Node95; security/image/dependency PASS.
Review findings/threads0. [Final acceptance](https://github.com/azurebek/azurelms/pull/136#issuecomment-5842893063).
Temporary SQLite/private files IAB8063: explicit course filter → course
edit PRG → explicit lesson index → lesson save → per-link metadata →
reorder PRG; second-tab stale409, old draft retained, Save disabled.
Besh route × 320/639/640/1023/1024/1280 = 30 readback, positive overflow0.
Dark screenshot ko‘zdan kechirildi. Browserda resource/detach delete yo‘q;
ular backend testda. Real network loss, light theme/native iOS/Android va
AWS release NOT TESTED. Previewdagi hamma ma’lumot sintetik.

## Qolgan chegara

I6 runtime besh editor oilasi + I6a kutubxona bilan qamraladi; CI/integratsiya
va AWS/device release alohida gate. Yangi lesson-create route, modul yoki
quiz authoring va yangi prototip qurilmadi. Keyingi katta portlar: I7
checkout/receipt, I8 exam/review, I9 Classbook; I5 certificate detail/appendix
hanuz legacy. No-op/ABA/global idempotency yuqoridagi cheklovlar bilan.
