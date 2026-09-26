# I8 — imtihonlar va ustoz tekshiruvi

## Admission — runtime tahriridan oldin

**ADMIT — launch-critical.** Frozen V1 imtihonlar markazi va keyingi
natija/urinish/review yuzalarini canonical Django holatiga ulash. KPI:
o‘quvchi o‘z faol kursining aynan o‘z urinishini topadi; ko‘rish yangi
urinish yaratmaydi; 320–1280 pxda asosiy amal yo‘qolmaydi.

- Birinchi mustaqil bo‘lak **I8a: imtihonlar markazi va natija** (`exam_center`, `exam_result`).
  `ExamCenterView`, `enrollment_active_access_q` va mavjud latest-attempt
  projectioni haqiqat manbasi. V1 faqat render qiladi; baho, attempt,
  timer, enrollment, review yoki sertifikat yozmaydi. JS hisoblash yo‘q.
- Default-OFF `frontend_v1_exams` hozir faqat shu read-only yuzalarni
  tanlaydi. OFF eski renderer/navga qaytaradi, ma’lumotni o‘zgartirmaydi.
  Detail/review hali eski renderer: urinish havolasida bu ochiq aytiladi.
- Mavjud layout/tokenlar, 640/1024 breakpointlar va umumiy theme/nav.
  Boshlanmagan/jarayonda/kutilmoqda/tasdiqlangan/limit/empty holatlari;
  qoralama ball markazda mavjud canonical qoidadek ko‘rsatilmaydi.
- Ownerning haftalik operatsion yuki oshmaydi. Yangi operatsion sozlama,
  provider chaqiruvi, AWS o‘zgarishi yoki yangi prototype yo‘q.
- **Owner 2026-09-26:** “Ha, faqat tasdiqlangan natija ko‘rinsin”.
  Canonical `ExamAttempt.finalize_review` ball bilan bir transactionda
  `ExamResultPublication`ga oxirgi tasdiqlangan section/answer feedback,
  notes va ball nusxasini yozadi. Oddiy draft save bu nusxani o‘zgartirmaydi;
  qayta tasdiqlash uni yangilaydi. Bitta canonical projection V1, legacy
  result va public certificate appendixda ishlaydi; flag OFF privacy
  himoyasini bekor qilmaydi. Bu to‘liq revision/history yoki certificate
  qayta berish siyosati emas. Eski approved urinishlarda tasdiqlangan
  nusxasi yo‘q tafsilotlar taxminan backfill qilinmaydi; oldingi umumiy
  ball saqlanadi, tafsilotlar qayta tasdiqlanganda paydo bo‘ladi.
  Additive migration: yangi publication jadvali, data-loss/backfill yo‘q.
  Persistent form revision, audio qurilma, timer/submit acceptance I8b/cda ochiq.

## Qabul

- [x] ~~I8a runtime `2fe920f` va regressiya.~~
- [x] ~~I8a mobile/desktop browser.~~
- [x] ~~I8a required CI/review/main.~~ PR138 MERGED `17cfc3a`;
  finalCI36219639823 uchala PASS, final local2159 OK skip45 (139.635s),
  focused33 OK, Node95. [Final acceptance](https://github.com/azurebek/azurelms/pull/138#issuecomment-5843413967).
- [ ] I8b/c: attempt/audio/timer/revision va teacher review UI.
- [ ] I8b oldidan [API ruxsat/privacy tuzatishi](I8-API-SECURITY.md).
- [ ] AWS/native-device release.

Sinov: isolated provider-free `manage.py test courses`, yangi focused
tests, full suite, Node suite, check/migration drift/diff; browserda
list → aniq pending/reviewed result yoki instructions → Back, mobil drawer,
theme va empty/long-content. Ko‘rinish porti butun I8 tayyor degani emas.

## I8a dalil

PR138 review fix `17a9e62`: legacy natija matni va section ranglari endi
snapshotdagi passing thresholdni ishlatadi; tarixiy snapshot yo‘q bo‘lsa
live fallback qoladi, zero threshold yo‘q deb olinmaydi. Provider-free
`manage.py test courses.test_frontend_v1_exams --noinput`: **33 OK, 3.229s**;
3 yangi regression. Yangi full/required CI final acceptance’da yoziladi.

- `AZURELMS_SKIP_ENV_FILE=1 GEMINI_API_KEY= TELEGRAM_BOT_TOKEN=` bilan
  `venv/Scripts/python.exe manage.py test --noinput`: **2156 OK, skip45,
  151.359s** (`playground/frontend-v1-smoke/i8-full.log`). 30 yangi test.
  Dastlab yangi test fixturelarida canonical duplicate-active-enrollment
  cheklovi, qo‘lda seed qilingan certificate IDsi va en-us decimal belgisi
  noto‘g‘ri berilgan edi; fixture/assertlar real contractga moslandi.
  Runtime yoki eski testlar yumshatilmadi; yangi skip yo‘q.
- `node --test tests/frontend_v1/*.test.mjs`: **95 PASS**; yangi JS yo‘q.
  `manage.py check --fail-level WARNING`: 0 issue;
  `manage.py makemigrations --check --dry-run`: no changes;
  `git diff --check`: PASS.
- IAB8065 alohida temporary SQLite/media: login → 7 holatli markaz →
  pending/refresh → published → failed/retake instructions/Back → historical
  → empty-account. Qoralama HTMLda yo‘q; tegishli urinish/course URL saqlandi.
  Markaz, pending, published, failed, historical va empty ×
  320/639/640/1023/1024/1280 = **36 readback, positive overflow0**.
  Light/dark desktop/mobile ko‘rildi, mobile drawer Escape focus qaytardi,
  console warn/error0. Temporary viewport reset; 8065 tab deliverable.
- Haqiqiy grading/draft/finalize, republish, failure transaction rollback,
  CSRF/teacher scope, immutable rubric va appendix disclosure Django
  testlarida. Browserda yangi urinish yoki baholash amalga oshirilmadi.
  Native-device, audio/mic, timer/submit va haqiqiy network loss bu slice’da
  NOT TESTED. Bog‘liq attempt/review UI hali legacy; bu butun I8 qabuli emas.
- `?retake=1` faqat reviewed-failed/remaining holatida eski instructionni
  ko‘rsatadi, GET yozmaydi. Yangi urinish existing start POST bilan;
  `check_exam_entry_policy` yana tekshiradi. Pending/passed/limit bypass yo‘q.
- Tasdiqlash writeri va teacher draft POST attempt lock + transactionda.
  Admin aggregate score/passed/is_reviewed readonly; explicit approve action
  yagona publication yo‘li. Certificate issuance/formula o‘zgarmadi.

## Rollout

**Main/CI ≠ AWS.** `courses0021`ni yangi koddan oldin migrate qilish kerak,
hatto renderer OFF bo‘lsa ham; publication privacy ikkalasiga tegishli.
Migration faqat yangi jadval qo‘shadi, mavjud draft/grade/certificatelarni
ko‘chirmaydi yoki o‘chirmaydi. `frontend_v1_exams=OFF` renderer rollback;
old code rollbacki esa yangi privacy kafolatini olib tashlaydi, shuning
uchun alohida release qarori va backup bilan. Oldingi reviewed urinishlarda
snapshot yo‘q bo‘lsa, live tafsilotlar o‘rniga izohli bo‘sh holat ko‘rsatiladi;
ularni taxminan tasdiqlangan deb backfill qilish taqiqlanadi.
