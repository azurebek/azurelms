# I8b — real imtihon topshirish

**FINAL VALIDATION — 2026-09-26.** I8b review fixlar `6085156`, `425ecc3`da.
Owner library ABA fixni ham tasdiqladi; alohida `453b6dd` commitda
clock-independent edit counter qo‘shildi. Old full failure ostida tarixiy
dalil saqlandi; yangi full **2229 OK skip51 (145.501s)**. Fresh CI/review
acceptance kutilmoqda. AWS yo‘q.
[Library admission va dalil](LIBRARY-ABA.md).

Latest follow-up: head110cfd2 CI36226414409 all3PASS, PostgreSQL2229 OK
skip20 (154.690s). Review4110573482 applied receipt growthni topdi; owner
sozlanadigan himoyaga ruxsat berdi. `842edb4`: audited cap + atomic epoch
rotation before eviction. [Admission va dalil](EXAM-RECEIPT-BOUND.md).
Focused85 OK skip6/Node110 PASS, IAB two-tab recovery va owner audit PASS.
Final provider-free full2236 OK skip52 (168.837s). Fresh CI/review/main
acceptance kerak; hali merge/deploy emas. Long sleep-interrupted run and
rerun evidence are retained in the follow-up document.
Next review4111999822 outer audio rollback fixed in `e39a263`; focused73 OK
skip7 (9.180s), no migration/UI delta. Prior86eaf08 CI all3PASS; fresh
full/CI/review required. [Complete rollback scope](EXAM-RECEIPT-BOUND.md).

### Final local checkpoint — library guard included

- Runtime `453b6dd`: clock-independent, row-locked library save revision;
  owner-approved additive library0002. Focused library/exam112 OK skip6,
  controlled original same-clock test PASS. Final full2229 OK skip51;
  Node109 PASS, check0/drift0. Six domain concurrency tests require PG CI.
- All four existing PR140 review findings have implementation/test replies
  and resolved threads. Fresh head CI/review and main acceptance still open.

### Previous checkpoint — reading config parity and discovered blocker

- Runtime `425ecc3`: canonical multi-select cap validation, V1 checkbox cap,
  disabled review-flag projection/control va canonical save/toggle rejection.
  Model/operatsion limit qo‘shilmadi; mavjud task sozlamalari ishlatiladi.
- `manage.py test courses --noinput`: **265 OK skip6 (26.850s)**;
  `node --test tests/frontend_v1/*.test.mjs`: **109 PASS**. 4 backend/2 Node
  regression qo‘shildi. IAB8068: 2 tanlovdan keyin uchinchisi disabled,
  uncheckdan keyin enabled, 2 tanlov va flagsiz short-answer Save accepted.
  Mobile320 overflow0, console0; `i8b-reading-cap-mobile.png` local proof.
- **Final full2225 FAILED (1 failure, skip50, 147.156s):**
  `library.test_frontend_v1.LibraryV1Tests.test_snapshot_changes_on_aba_tags_and_usage`
  line158. Yakka qayta test1 PASS (0.040s), ammo timestampni bir xil ushlab
  original test/assertion bilan controlled repro1 FAIL (0.032s).
  `library/frontend_v1.py` snapshot `updated_at`ga suyanadi; bir clock tickda
  A→B→A bo‘lsa fingerprint teng. Bu uch library fayli baseline `b8c1604`dan
  o‘zgarmagan (`git diff b8c1604 -- library/...` empty). Shu checkpointda
  library runtime/test o‘zgartirilmagan edi; keyin owner-approved `453b6dd`
  bilan tuzatildi. Assertion susaytirilmadi; yangi full dalili yuqorida.
- Old head12f9c4e CI36225064864 **all3PASS** (SQLite5m47s, PG4m2s,
  security2m0s). Bu eski checkpoint, `425ecc3` uchun CI o‘rnini bosmaydi.

### First review fixes — previous green checkpoint

- Provider-free `venv/Scripts/python.exe manage.py test --noinput`:
  **2221 OK skip50 (143.232s)**; Node **107 PASS**; check0/drift0/diff PASS.
  8 yangi backend / 3 yangi Node regression; 5 PG race testi CI’da.
- Isolated IAB8067, real CSP header: same-origin WAV ended, count1/left0;
  missing404 audio count0/left1, POST yo‘q; external URL unavailable.
  Before-write503 → explicit reconcile → draft qoladi → fresh Save accepted.
  6 breakpoint readback320–1280 overflow0; dark/light mobile inspection.
  Local proof: `playground/frontend-v1-smoke/i8b-review-mobile.png`.
- Strict CSP real response testida V1-only blob preview istisnosi va Mini App
  frame policy bilan birga saqlanishi; legacy/global media policy o‘zgarmagan.
  Native microphone/codec/real-device va haqiqiy audio kontent release hali ochiq.
- Birinchi regression run’da fixture assert JSON `state.plays_used` o‘rniga
  yo‘q model fieldga qaradi va old middleware-cached Client ishlatildi;
  test wiring tuzatilib barcha assertlar saqlandi. Keyingi focused48 OK skip5,
  so‘ng yakuniy full2221 (Mini App assertion bilan) PASS.

### Review-fix admission (runtime tahriridan oldin)

Second review (head12f9c4e) P2/P2: reading multi-select cap va disabled
review-flag. ADMIT — shu I8b config-parity doirasida; yangi feature/sozlama
emas. Canonical reading writer configured maximumni reject qiladi, V1 tanlash
controlida unchecked variantlar capga yetganda yopiladi (checked variantni
olib tashlash mumkin). Disabled flag projection/templatega o‘tadi, canonical
save/toggle forbidden true flagni yozmaydi. Barcha adapter bir writerdan
foydalanadi; current DB/backfill/grades recalculation yo‘q.

ADMIT — launch-critical; mavjud I8b doirasida. P1: V1 listening faqat
same-origin HTTP(S) manbani qabul qiladi, blocked/missing manbani limitdan
oldin rad etadi. Browser audio tayyorligini tekshiradi (xato/bekor qilishda
POST yo‘q); POST aynan tekshirilgan URLni qayta solishtiradi. Tashqi host,
proxy/SSRF yoki global CSP ruxsati qo‘shilmaydi. Faqat V1 attempt HTMLda
`media-src 'self' blob:` local speaking preview uchun tor istisno.

P2: student/exam uchun bitta UUID epoch yozuvi (additive courses0023).
Faqat ruxsatli, flag-ON GET bu slotni bir marta yaratadi; POST yaratmaydi.
Har action server bergan joriy epochni olib keladi. Reconcile applied receiptni
o‘qiydi yoki slotni almashtirib eski epochdagi barcha kechikkan actionlarni
bloklaydi; cancelled receipt INSERT yo‘q. Eski epoch bilan reconcile read-only,
OFFda faqat avval berilgan slot yopiladi. Ikkinchi tab eski epochda fail-closed
409 + fresh state oladi, qoralama qoladi. Applied receiptlar saqlanadi.
Bu protokolning strukturaviy bounded holati; yangi vaqt/retention/quota yoki
owner operatsion sozlamasi emas. Eski data/receiptlar o‘chirilmaydi.

### Oldingi review blockerlar (fixdan oldingi tarix)

- P1: `SECURITY_STRICT` CSP `media-src 'self'`; tashqi section media URL
  bloklanadi, lekin listen count undan oldin yoziladi. Manba mosligini
  limit sarflashdan oldin tekshirish/first-party media yechimi kerak.
  Speaking `blob:` preview ham shu strict-policy device gate’da tekshirilsin.
  CSP manbalari yoki production content avtomatik kengaytirilmadi.
- P2: fresh UUIDli reconcile nullable-attempt cancelled receipt yaratadi,
  hatto flag OFF/no-attempt holatida. Bounded server-issued identity yoki
  canonical throttling/retention kerak; yopilmaguncha yangi kod deploy qilinmaydi.
- Review threadlar **ochiq**, PR merge qilinmadi. Head `a8b35b3`da CI
  PostgreSQL va security/image PASS; SQLite kuzatuv vaqtida pending.
  Runtime final local `manage.py test --noinput`: **2213 OK skip50,
  166.277s**, Node104. 5 yangi SQLite skip — PG-only row-lock testlar.

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
  mavjud receiptni qaytaradi yoki bounded gate epochini almashtiradi.
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

Identity receipt (UUID + epoch-bound request digest) ayni so‘rovni ikki marta bajarmaydi;
o‘sha UUID boshqa payload bilan rad etiladi. Missing GET receipt hali noma’lum;
explicit reconcile applied receipt yoki virtual cancelled acknowledgement qaytaradi.
Cancelled INSERT yo‘q: courses0023 ExamActionGate unique(student,exam) epochini
user lock ostida almashtiradi. Slot faqat flag-ON authorized GETda yaratiladi,
POST hech qachon slot yaratmaydi. Eski epochning har qanday actioni rad etiladi;
eski epochni yana reconcile qilish no-op. Applied receiptlar qoladi, cancel
butun o‘sha epochdagi in-flight actionlarga ta’sir qiladi; boshqa tab fresh state
olib qoralamasini qayta ko‘radi. Kechikkan POST barrier’dan keyin javob yozmaydi.
OFFda faqat state/receipt va avval berilgan slotning identity
reconciliation qoladi. Enrollment revoke bilan global linearizability da’vosi
yo‘q; joriy per-request access policy PR139dagi kabi.

`courses0022_exam_action_revisions` additive: ikki defaultli attempt maydoni,
identity-only `ExamActionReceipt` jadvali, yangi jadvalda unique constraint.
Receipt attempt nullable eski schema bilan moslik uchun qoladi; yangi cancelled
row yaratilmaydi. Answer text/media/grade receiptga kirmaydi. Additive courses0023
faqat yangi bounded gate jadvali, data delete/backfill yo‘q.
Flag OFF bo‘lsa ham yangi kod deployidan **oldin migration kerak**. Eski ball,
answer, publication backfill/delete yo‘q. Rollback: flag OFF, additive schema qoladi.
Listening URL same-origin HTTP(S), exact preloaded source POSTda qayta tekshiriladi.
Preload error/cancel limit sarflamaydi. Playback boshlanganidan keyingi tarmoq/codec
xatosida avtomatik refund yo‘q; listen count play-start authorization hisobidir,
DRM yoki audioni eshitganlik kafolati emas. External media hostlar ochilmagan;
reliz oldidan kontent first-party audio URLga mosligi tekshiriladi.

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

Final lock-order hardening `948878c`: legacy va V1 APIlar bir xil
user → attempt tartibida; legacy submit streak/FK yozuvi bilan aralash
ochilgan eski-yangi oynada lock inversion oldi olindi. Beshinchi PG testi
legacy-submit/V1-save racing invariantini tekshiradi. Final focused
`manage.py test courses.test_exam_attempt_v1 courses.test_exam_api_security
courses.test_frontend_v1_exams users.test_frontend_v1 --noinput`:
**111 OK, skip5, 9.839s**. Besh skip SQLite’da row-lock imkoniyati yo‘qligi;
final full/PG count PR140 CI’da. Oldingi 4-skip sonlar o‘sha checkpoint dalili.

### Ochiq release chegarasi

Native iOS/Android microphone permission/recording/codec/upload va real audio,
uzoq fon rejimi, haqiqiy tarmoq uzilishi, real content hamda AWS migration /
renderer rollback hali release gate. Recording/file writer backendda, mic UI
implemented lekin native device’da hali qabul qilinmagan. Receipt retention
uchun yangi avtomatik purge qo‘shilmadi. I8c ustoz exam review UI, I9 Classbook
va I5 certificate detail/appendix UI qoladi. Frozen trial o‘zgarmadi.
