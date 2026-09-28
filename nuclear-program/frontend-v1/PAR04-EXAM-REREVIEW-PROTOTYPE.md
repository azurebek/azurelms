# Packet78 — imtihonni qayta tekshirish pariteti

2026-09-28 · EXPERIMENT/local-only. Owner prototip rejasini davom ettirdi.
Final qabulning PAR-04 bandi lokal yopildi; runtime, DB va AWS o‘zgarmadi.

## Tasdiqlangan source va natija

`core.teacher_views.teacher_grade_exam` completed urinishni, shu jumladan
reviewedni tahrirlaydi. `courses.models.ExamAttempt.finalize_review` explicit
publication yaratadi; `courses.exam_publication.learner_result` faqat shu
publicationdan o‘qiydi. [I8c contract](I8C-REVIEW.md) shu xulqni saqlaydi.

Old preview faqat pending urinishni tekshirardi. Endi reviewed urinish
qoralamasi ham editable; yangi saqlangan ball/izohlar learnerga chiqmaydi,
oldingi approved natija ko‘rinib turadi. Explicit tasdiq uni almashtiradi.
Draft queue/status/learner answers/progressni o‘zgartirmaydi.

Review+attempt revision saqlanadi; dirty refresh/reload inputni yo‘qotmaydi,
stale alohida rebase talab qiladi. Old Packet77 draft matni saqlanadi,
yetishmagan attempt baseline taxmin qilinmaydi. Modal eskirsa consent
tozalanadi. Noma’lum save/publish read-only receipt bilan aniqlanadi;
avtomatik resend yo‘q. Bular synthetic adapter invariantlari, production
idempotency/permission yoki grade/certificate kafolati emas.

## Sonlar va testlar

139 named route /77 page template /118 source URL nomi /1223 state /
206 action va3 handler diagnostic o‘zgarmadi; registry0.78.0-exam-rereview.

Trial cwd `playground/Eleventh Trial`, `AZURELMS_SKIP_ENV_FILE=1`,
`GEMINI_API_KEY`/`TELEGRAM_BOT_TOKEN` bo‘sh:

- `../../venv/Scripts/python.exe manage.py test tests --verbosity 1`:
  **832 PASS (317.259s)**.
- `../../venv/Scripts/python.exe manage.py test tests.test_exam_review
  tests.test_exams --verbosity 1`: **53 PASS (5.579s)**.
- `../../venv/Scripts/python.exe manage.py check`:0 issue.
- Root PowerShell `$trialTests = @(Get-ChildItem -LiteralPath
  'playground/Eleventh Trial/tests' -Filter '*.test.mjs' | ForEach-Object
  FullName); node --test @trialTests`: **203 PASS**.
- `node --check 'playground/Eleventh Trial/prototype/static/js/exam_review.js'`:PASS.

9 yangi Django/6 Node regressiyasi: publication privacy/replacement,
stale/replay/no-write, wrong scope/run, fault/unknown, lab result separation,
draft codec/legacy recovery va availability guard.

## IAB brauzer

Isolated8083, synthetic only: first save17.25→publish→re-save19.50,
learner hali17.25→explicit republish→learner19.50. Two-tab stale va
reload/rebase draftni saqladi; checked modal paytida peer save eski
publicationni blokladi va consentni tozaladi. Unknown save/reload va unknown
publish GET reconcile bilan topildi; qayta POST qilinmadi.

**48 responsive case:** teacher+learner ×320/390/639/640/768/1023/1024/1280
×light/dark ×800height=32;2000-belgili izohli modal shu8width×2theme
×568height=16. Horizontal overflow0; modal viewport ichida;
tekshirilgan buttons/text inputs/textareas/consent-label≥44px. Inline
text links bu o‘lchovga kiritilmadi. Escape triggerga focus qaytardi,
reopen consent unchecked; final console0. Viewport reset, peer closed.

Driver readinessni kutmagan bitta400 va submit feedbackning yangilangan
matniga oid bitta locator timeout PASS deb olinmadi; fresh ready DOMdan
qayta tekshirildi. Invalid POST publicationni o‘zgartirmadi.
Lokal dalil: `playground/Eleventh Trial/evidence/PACKET-78-RESULTS.md`,
`packet-78-rereview.png`. Native iPhone Chrome/AT qabuli emas.

## Checkpoint va ochiq qamrov

`playground/Eleventh Trial/checkpoints/packet-78-20260928-055741.zip`:
**623 fayl**, har entry SHA256 asl fayl bilan tekshirildi.
ZIP SHA256 `12FE314FAB697967466EE2618A31A7B7B9E4860EC379E815703B696AD270ACC0`.
Old Packet77 va avvalgi nusxalar saqlanadi.
Ignored trial/assets/arxiv masofaga yuborilmaydi; bu PR faqat hujjatlar.

PAR-04 **lokal UI/state parity CLOSED**; G2/G3 yoki real reliz emas.
PAR-01/02/03/05, UX-01–06, DATA-01, RULE-01 hamon ochiq. Ayniqsa
ownerning iPhone Chrome keyboard nuqsoni tuzatilgani da’vo qilinmaydi.
Rejaning11-qadami ishda;12-DESIGN-01 hozircha navbatda.
