# I8b — real imtihon topshirish

## Admission — runtime tahriridan oldin

**ADMIT — launch-critical.** KPI: ruxsatli learner start → savolni explicit
saqlash → tasdiqlab topshirish → pending result oqimini 320–1280pxda
bajaradi; stale/unknown javob qoralamani yo‘qotmaydi yoki ko‘r-ko‘rona
takrorlanmaydi. Frozen LRN-04 / exam-focus shell, savollar xaritasi,
per-question form va submit dialog olinadi; yangi dizayn/prototype yo‘q.

- Canonical state: ExamAttempt, StudentAnswer, ReadingResponse; mavjud
  start, question/reading writer, private upload, listen-limit va submit
  servicelari ishlatiladi. UI grade/access/expiry hisoblamaydi.
- Adapter: alohida default-OFF `frontend_v1_exam_attempt`, real detail
  renderer va state/action JSON; eski UI rollback uchun qoladi. I8a center/
  result mustaqil. Ustoz review UI I8cda qoladi.
- Per-attempt lock ostida monotonic attempt/question revisions va
  user/exam/operation-bound receipt: ikki tab stale409 no-write; noaniq
  mutation GET receipt orqali tekshiriladi. Receipt yo‘qligi kechikkan
  so‘rov yo‘qligini isbotlamaydi: explicit reconcile POST user lock ostida
  mavjud receiptni qaytaradi yoki identity-only cancelled barrier yozadi.
  Kechikkan original so‘rov bundan keyin yozolmaydi; javob qayta yuborilmaydi.
  Bu real transport adaptatsiyasi; baho/access yangi biznes qoidasi emas.
  Legacy answer writerlari ham
  revisionni oshiradi. DBga additive schema kerak, baholar backfill emas.
- Text draft session/user/exam/attempt/question doirasida shu tabda;
  file/mic bytes sahifa xotirasida, reload yo‘qotishi ochiq aytiladi.
  Dirty/stale/unknown holda finish blok. Rebase saqlamaydi; Save alohida.
- Deadline backenddan; oxirgi server tekshiruvidagi remaining ko‘rsatiladi,
  browser soati submit qilmaydi. Refresh expiry mavjud canonical istisno.
  Audio permission/upload/limit alohida holatlar, raw key yo‘q.
- Ownerga yangi qo‘lda ish, provider xarajati yoki operatsion vaqt/limit
  qo‘shilmaydi. Failure fail-closed; OFF eski renderer, schema additive
  qoladi. Bu local port, AWS yoki native-device acceptance emas.

## Tekshirish / qabul

- [x] ~~Runtime va backend stale/duplicate/access/publication tests.~~
  PostgreSQL overlapping transaction tests required CI’da alohida gate.
- [x] ~~Controller dirty/unknown/rebase/clock va fault-recovery tests.~~
- [x] ~~Isolated real Django flow, desktop/mobile, theme va console.~~
- [ ] Full tests, required CI/review/main.
- [ ] AWS/native-device microphone va audio playback release.

I8 API security PR139 avval yakunlangan: main `b8c1604`, final
CI36221144145 all3PASS, Python2183/Node95. Qayta qurilmaydi.

## Runtime va tekshiruv — 2026-09-26

Branch `codex/frontend-v1-exam-attempt`; runtime `fc80c7f`, handoff copy /
scope / logout testlari `deef10c`. `courses/<course>/exam/<exam>/` flag ONda
platform shell + instructions, question map, radio/multi/select/short/writing,
speaking file/mic va explicit submit dialog. OFF legacy renderer. GET start
qilmaydi; active attemptni tiklaydi. Center/result mustaqil flag bilan ishlaydi.

`api/v1/` GET current snapshot/optional receipt, POST start/save/listen/submit
hamda explicit reconcile. User/exam scope + current membership + CSRF/private
no-store. Question writers `ExamAttempt` row lock ostida `answer_versions` va
`input_revision`ni oshiradi; legacy write ham shu counterga kiradi. V1 expected
version eski bo‘lsa 409 va no-write. Form rebase faqat baseline’ni yangilaydi.
Listen counter attempt answer revisionini o‘zgartirmaydi. Start first-attempt
race uchun stable user row lock; max_attempts=0 endi birinchi startni ham rad
etadi (centerning mavjud yopiq holatiga mos). Ball/publication formulasi o‘sha.

Identity receipt (UUID + request digest) ayni so‘rovni ikki marta bajarmaydi;
o‘sha UUID boshqa payload bilan rad etiladi. Missing GET receipt hali noma’lum;
explicit reconcile applied receipt yoki cancelled barrier qaytaradi. Kechikkan
POST barrier’dan keyin javob yozmaydi. OFFda faqat state/receipt va shu identity
reconciliation qoladi. Enrollment revoke bilan global linearizability da’vosi
yo‘q; joriy per-request access policy PR139dagi kabi.

`courses0022_exam_action_revisions` additive: ikki defaultli attempt maydoni,
identity-only `ExamActionReceipt` jadvali, yangi jadvalda unique constraint.
Cancelled start uchun attempt nullable; answer text/media/grade receiptga kirmaydi.
Flag OFF bo‘lsa ham yangi kod deployidan **oldin migration kerak**. Eski ball,
answer, publication backfill/delete yo‘q. Rollback: flag OFF, additive schema qoladi.
Storage faylni SQL rollback bilan atomik o‘chira olmaydi; writer ichida rad
etilgan yangi upload tozalanadi, oldingi learner fayllari o‘chirilmaydi.

Session draft user+session+exam HMAC va attempt/question scope’da, field allowlist.
Credentials/CSRF/file bytes yozilmaydi; logout V1 exam keylarini tozalaydi.
Operation identity storage yozilmasa mutation yuborilmaydi. Reload audio
yo‘qolganini ochiq aytadi, yangi fayl yoki explicit discardgacha save/finish yopiq.
Serverda oxirgi tekshirilgan vaqt ko‘rsatiladi; lokal countdown/auto-submit yo‘q.

### Dalil

Provider-free `AZURELMS_SKIP_ENV_FILE=1 GEMINI_API_KEY= TELEGRAM_BOT_TOKEN=`:

- `venv/Scripts/python.exe manage.py test courses --noinput`: **250 OK,
  skip5, 18.813s**. 23 yangi oddiy test va 4 PostgreSQL race testi;
  local SQLite row-lock testlarini bajara olmaydi (4 yangi skip shundan).
- `manage.py test courses users.test_frontend_v1 --noinput`: **274 OK,
  skip5, 24.133s**; static hashed asset yig‘ish ham tekshirildi.
- `manage.py test --noinput`: **2210 OK, skip49, 150.345s** (runtime commit).
  So‘ng handoff-copy va session-scope ikki testi qo‘shildi: final focused
  `courses.test_exam_attempt_v1 courses.test_frontend_v1_exams
  users.test_frontend_v1`: **86 OK, skip4, 8.761s**. Final full count CI’da.
- `node --test tests/frontend_v1/*.test.mjs`: **104 PASS**; 9 yangi invariant /
  storage isolation/logout test. Syntax/check/drift/diff tekshiruvlari ham bajarildi.
- Birinchi full run 2210 ichida bitta failure: asset storage allowlisti yangi
  controllerga ruxsat bermagan. I2bdagi admitted draft istisnosi I8bga tor
  kengaytirildi, credential/file allowlist va logout regression bilan kuchaydi.
  Test o‘chirilmadi yoki umumiy taqiq olib tashlanmadi. Test baseline countga
  importlangan fixture TestCase dublikatlari kiritilmagan.

IAB8066 isolated temp SQLite/media/private, sun’iy akkauntlar; current DB/AWSga
tegilmadi. Start → choice/writing/reading single/multi/short, matching → save;
two-tab stale409 → preserved draft → rebase (no save) → explicit save;
mobile confirm → pending publication. Keyin synthetically lost-ack-after-commit
GET receipt bilan tiklandi, rejected-before-write explicit reconcile bilan
yopildi, qoralama reload’da tiklanib yangi Save bilan saqlandi. Bu real fetch/DB
oqimi, ISP/router nosozligi sinovi emas. 0.1s silent WAV listening ended va
server limit1→0 tekshirildi; limitdan keyin play disabled.

320/639/640/1023/1024/1280px — ikki haqiqiy oltilik **12 readback overflow0**.
Avval noto‘g‘ri tabga tatbiq etilgan override o‘lchovlari dalilga sanalmadi.
Dark/light, mobile dialog, Escape→opener focus, drawer, desktop screenshot.
Final local proof: ignored `playground/frontend-v1-smoke/i8b-{desktop,mobile}.png`.
Oddiy oqimda console0; synthetic 503 va stale409 faultlari kutilgan transport
xatolari. Dastlabki QA matching fixture noto‘g‘ri task_type ishlatgan edi;
modelning `matching` qiymatiga tuzatilib real matching save qayta o‘tdi.

### Ochiq release chegarasi

Native iOS/Android microphone permission/recording/codec/upload va real audio,
uzoq fon rejimi, haqiqiy tarmoq uzilishi, real content hamda AWS migration /
renderer rollback hali release gate. Recording/file writer backendda, mic UI
implemented lekin native device’da hali qabul qilinmagan. Receipt retention
uchun yangi avtomatik purge qo‘shilmadi. I8c ustoz exam review UI, I9 Classbook
va I5 certificate detail/appendix UI qoladi. Frozen trial o‘zgarmadi.
