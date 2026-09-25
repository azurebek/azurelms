# I2 — real dars/material va ustoz release

2026-09-25. Branch: `codex/frontend-v1-lesson-release`.
[PR #121](https://github.com/azurebek/azurelms/pull/121).
Admission: **ADMIT — launch-critical** (ownerning V1 port qarori).

- Outcome/KPI: ustoz aniq guruh darsini ochadi/yopadi; o‘quvchining dars
  va private materialga haqiqiy kirishi shu holatga mos keladi.
- Canonical state: `CohortLessonRelease`; yozuvchi `set_lesson_release`.
  Access `check_lesson_access`, material `student_materials`/private file
  endpoint, completion `progress_service` orqali qoladi. UI qoida egasi emas.
- Web faqat iste’molchi; Telegram/AI/XP, model va migration o‘zgarmaydi.
- Owner yuki: yangi boshqaruv tizimi yo‘q, existing ikki view ko‘rinishi
  almashtiriladi; target va birinchi drip ta’siri tasdiqdan oldin ko‘rinadi.
- `frontend_v1_lesson`, `frontend_v1_teacher` default OFF; oldingi renderer
  flag o‘chirilishi bilan qaytadi. Noto‘g‘ri POST cohort fallbacki flagdan
  qat’i nazar yopiladi: boshqa guruhga yozish rollback yo‘li emas.
- Verification: ON/OFF, auth/scope/CSRF, explicit target, duplicate/no-op,
  teacher open/lock → student read/file/completion; desktop/mobile/theme.

## I2a chegarasi (tarixiy; I2b bilan kengaytirildi)

Ustoz home/release va matn/video/material dars adapteri. Assignment yoki
quizli dars **butunlay existing rendererda qoladi**; hech bir tab olib
tashlanmaydi va yarim yangi dars ko‘rsatilmaydi. Bu README dagi fallback
qoidasidir. I2bda practice controller/form izolyatsiyasi tugamaguncha
**I2 to‘liq PASS emas**. R1 staging/device/AWS gate ham alohida ochiq.

Yangi prototype dizayni, fixture API, fake timer/state/receipt ko‘chirilmaydi.
Release POST/redirect/GET server javobi authoritative; prototype revision
reconciliation va parallel tab conflict kafolati bu adapterda da’vo qilinmaydi.

## Tekshiruv va integratsiya dalillari

### Adapter mapping

| Existing URL | V1 renderer / controller | Canonical manba |
|---|---|---|
| `/teacher/` | `frontend_v1/teacher/dashboard.html` | Existing teacher queryset, pending queue va real counts |
| `/teacher/release/?cohort=…` | `frontend_v1/teacher/release.html`, `release.js` | Scoped cohort/lessons → `set_lesson_release`; PRG |
| `/courses/<course>/lesson/<lesson>/?cohort=…&tab=…` | `frontend_v1/lesson.html`; practice bo‘lsa existing template | Existing `LessonDetailView` access bundle/content/material context |
| `/courses/<course>/lesson/<lesson>/completion/` | Native CSRF POST; allowlisted tab bilan PRG | `mark_lesson_completed`/`unmark_lesson_completed` |
| `/library/material/<id>/file/` | Existing private endpoint | `student_can_open`, private storage; o‘zgarmagan |

Teacher GET confirmation hech nima yozmaydi. Invalid/missing POST cohort,
query/body mismatch, foreign/inactive cohort yozmaydi. Note uzunligi va
target/first-drip checkboxlari serverda tekshiriladi. Form xatosida izoh
HTMLda qaytariladi, checkboxlar qayta tasdiqlanadi. JS faqat native dialog,
cancel/reopen, unsaved-note navigation ogohlantirishi va double-submit guard;
JSsiz ham to‘liq inline confirmation form mavjud. Browser storage ishlatilmaydi.

### Lokal tekshiruv

Barcha Django buyruqlarida `AZURELMS_SKIP_ENV_FILE=1`, `GEMINI_API_KEY=''`,
`TELEGRAM_BOT_TOKEN=''`. Vaqtinchalik test DB/media, current DB untouched.

- `venv\Scripts\python.exe manage.py check`: 0 issue.
- `venv\Scripts\python.exe manage.py test courses core users library
  --noinput --verbosity 1`: **1051 test, OK (skipped=26)**. Keyingi optional
  completion tab va malformed-ID edge testlari fresh run bilan tekshiriladi.
- `node --test tests/frontend_v1/*.test.mjs`: **13 PASS** (8 I1 + 5 release).
- `git diff --check`: PASS.
- `venv\Scripts\python.exe manage.py test --noinput --verbosity 1`:
  **1862 test, OK (skipped=41), 269.381 s**, failure/error 0.
- Final `venv\Scripts\python.exe manage.py test courses.test_frontend_v1_study
  users.test_frontend_v1 --noinput --verbosity 1`: **40 PASS** — 16 I2 + 24 I1;
  updated malformed-ID/allowlisted-tab va hashed `study.css`/`release.js` ham ichida.

Browser: computer-use orqali IAB, isolated real Django server `8049`.
1440px desktop, 390px va 320px compact, light/dark; page-level horizontal
overflow kuzatilmadi. Teacher login→group→confirmation, cancel/reopen’da
note saqlanishi, 320px confirmation submit→real release/izoh; learner login→
shu dars→materials→haqiqiy PDF download→completion sinandi. Topilgan tab
sakrashi tuzatildi va fresh serverda `tab=materials` saqlanishi qayta ko‘rildi.
Console warn/error 0. Viewport override yakunda olib tashlandi.

Haqiqiy telefon, tashqi video playback, AWS/staging tekshiruvi bajarilmadi.
Native PRG parallel tab version/reconciliation kafolati emas. I2b practice
fallback ochiq; shu sababli **I2 va R1 PASS emas**. Flaglar canonical DBda
yoqilmadi, trial runtime/backup o‘zgarmadi. PR required CI alohida tekshiriladi.

### CI regression va tuzatish

Run `36086106798`: SQLite va sir/dependency skani PASS, PostgreSQL suite
1862 testda 4 error (skipped=20). Birinchi xato yangi download testidagi
`FileResponse.close()` bo‘lib, `request_finished` orqali `TestCase`ning
PostgreSQL connectionini yopgan; qolgan uchta error shu classning keyingi
testlarida yopiq connectiondan kelgan. Runtime xatosi deb talqin qilinmadi.

`a2a5907`: download stream Django test client wrapperi orqali iste’mol
qilinadi; PDF baytlari va response yopilgani ham assert qilinadi. Hech bir
permission/DB assertion yoki CI gate olib tashlanmadi. Lokal yuqoridagi
focused command qayta: **40 PASS**. Tuzatilgan HEAD uchun uchala required
CI qayta o‘tishi shart; yakuniy holat PRda, merge/deploy hali da’vo qilinmaydi.

### Yakuniy fresh tekshiruv — 2026-09-25

PR #121 **MERGED**, main commit `5528c74dc5cf1d4f8675e8cda0361769d84836bd`.
Tuzatilgan HEAD uchun CI `36086594312`: uchala required job PASS;
SQLite 1862 OK (skip=40), PostgreSQL 1862 OK (skip=20), Node 13 PASS.
Bu tekshiruv I2b ishining boshida GHdan olindi. Yuqoridagi CI-kutiladi va
practice-fallback holatlari I2a bosqichining tarixiy cheklovi;
[I2b](I2B-PRACTICE.md) practice darsini ham V1ga ulaydi. R1 release ochiq.
