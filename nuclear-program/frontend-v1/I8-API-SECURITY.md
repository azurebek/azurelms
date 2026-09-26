# I8 — attempt API ruxsat va publication chegarasi

## Admission (runtime tahriridan oldin, 2026-09-26)

**ADMIT — launch-critical.** Owner oldingi izolyatsiyalangan testda
tasdiqlangan ikki xavfsizlik topilmasini avval yopishga `ha` dedi.
KPI: ruxsati yo‘q learnerning barcha attempt API so‘rovlari no-write;
tasdiqlanmagan ball/feedback learner runtime JSONida umuman yo‘q.

- Canonical access: `Enrollment.objects.with_active_access()` asosidagi
  exam access policy; start va barcha active-attempt adapterlari shu
  policyga ulanadi. URLdagi course/exam va tanlangan section/question/item
  aynan bitta examga tegishli bo‘lishi kerak. Quiz savoli examga kirmaydi.
- State/writer: mavjud ExamAttempt, StudentAnswer, ReadingResponse va
  audio/review/submit servislar; grading formulasi, vaqt/limit va final
  publication writer o‘zgarmaydi. API javobi saqlangan javob/flag/countni
  beradi, grade/correctness/draft feedbackni emas. Tasdiqlangan natija
  mavjud `learner_result` projectioni orqali result sahifasida qoladi.
- Adapterlar: legacy va kelajak V1 attempt start/state/save/flag/audio/
  blur/submit. Xavfsizlik renderer flagiga bog‘liq emas; shaxsiy API
  javoblari `private, no-store`. Ownerga yangi operatsion sozlama/yuk yo‘q.
- Payloaddan xususiy audio storage kaliti qabul qilinmaydi: faqat mavjud
  tekshirilgan upload writeri uni belgilaydi. Mavjud service hisoblagan
  baho DBda qoladi; eski API-score testlari DB-grade + JSONda disclosure
  yo‘qligini birgalikda tekshiradigan testlarga almashtiriladi.
- Schema/data migration va AWS deploy yo‘q. Ruxsatsiz so‘rov fail-closed;
  eski kodga rollback xavfsizlik bo‘shlig‘ini qaytaradi. Renderer OFF
  himoyani olib tashlamaydi. Attempt revision/race, audio device va yangi
  I8b UI bu cheklangan security paketining qabuli emas.

## Tekshirish rejasi

- Barcha APIlar: anonymous, active/frozen/expired/pending/missing access,
  noto‘g‘ri course/exam, begona attempt/section/question/item; no-write va
  private/no-store. Ruxsatli save/flag/audio-play/submit ishlashi saqlanadi.
- Generic MCQ/text va rich-reading save/state hech qanday unpublished
  grading maydonini chiqarmaydi, lekin DB scoring o‘zgarmaydi. Approved
  publication regressionlari ham qayta ishlaydi.
- Provider-free focused/full Django, Node, check, migration drift,
  diff; required CI va review → manual merge. Productionga tegilmaydi.

## Dalil

- Runtime commit: `40c6ba6`, branch `codex/exam-api-access-privacy`.
- `AZURELMS_SKIP_ENV_FILE=1 GEMINI_API_KEY= TELEGRAM_BOT_TOKEN=` bilan
  `venv/Scripts/python.exe manage.py test courses --noinput`: **223 OK,
  skip1, 17.853s**; `manage.py test --noinput`: **2183 OK, skip45,
  130.929s**. 24 yangi security regressiya. Dastlab yangi fixtureda
  unique-email maydoni bo‘sh qoldirilgani uchun setup xatosi bo‘ldi;
  sintetik hisob emaili to‘g‘rilandi, eski testlar/skiplar yumshatilmadi.
- Dastlabki targeted `courses.test_exam_api_security courses.tests
  courses.test_frontend_v1_exams courses.test_blur_warning_isolation`:
  **90 OK (7.801s)**; keyin ikkita upload test qo‘shilib courses/fullga kirdi.
- `node --test tests/frontend_v1/*.test.mjs`: **95 PASS**.
  `manage.py check --fail-level WARNING`: 0 issue;
  `manage.py makemigrations --check --dry-run`: no changes;
  `git diff --check`: PASS.
- No-write: status active/overdue, frozen/pending/expired/missing, course
  mismatch, foreign/quiz question va foreign reading/section; anonymous,
  CSRF, staff rolini bypass qilmaslik, boshqa learner/completed attempt.
  Rad etilgan expired attempt avtomatik yakunlanmaydi; access avval.
- Ichki MCQ/reading ball va DBdagi grader feedback tashqi JSONda yo‘q;
  result publication regressiyasi saqlandi. Ruxsatli start/save/flag/
  audio-play/blur/submit hamda real private-storage upload ishlaydi.
  JSON orqali audio_key yozish va noto‘g‘ri fayl baytlari rad etiladi.
- UI/template/JS o‘zgarmadi, yangi browser/device qabuli da’vo qilinmaydi.
  Existing controller grading-response maydonlarini iste’mol qilmaydi.
  Yangi prototype, provider yoki AWS deploy yo‘q. Required CI/review/main
  final dalili PR acceptance commentida; bu lokal test dalili.

## Qolgan chegara

Bu access tekshiruvi har so‘rov boshida joriy policyga qaraydi; parallel
enrollment revoke/write uchun yangi global lock yoki revision protokoli
emas. Attempt autosave/submit revision, duplicate/unknown reconciliation,
timer va native audio qabuli I8bda qoladi. Ruxsatli expired-attempt
so‘rovining mavjud avtomatik submit semantikasi o‘zgarmagan. Tarixiy
o‘z audio faylini o‘qishning existing private-media owner/teacher policy
alohida va o‘zgarmagan. I8a courses0021 release talabi hamon saqlanadi;
shu security paketining o‘zi yangi migration qo‘shmaydi.
