# I5c.1 — Maxfiylik, To‘lov va Imkoniyatlar

## Admission — 2026-09-26, implementatsiyadan oldin

**ADMIT — launch-critical.** Owner tayyor V1 prototiplarini real kodga
ko‘chirishga qaytishni so‘radi. Uch mavjud settings sahifasi bitta paket:
ACC-01 shared tabs, Paket43 privacy, Paket44 billing va preferences form.
Yangi dizayn, AI engine/provider, to‘lov yoki yangi prototip yo‘q.

- Outcome/KPI: uch route bitta barqaror learner/teacher shell; har saqlash
  o‘z sahifasiga qaytadi; begona user/faktga yozish0; stale V1 form no-write;
  320–1280px gorizontal overflow0; required CI3/3.
- Canonical state: `CustomUser` preference maydonlari va mavjud POST views;
  `MemoryRepository` archive/reject/clear, decay/traces/legacy semantics;
  `aicontrol.service.build_usage_panel` hisoblagan quota. JS hisoblamaydi.
- Adapter: `frontend_v1_settings` default-OFF, real URL/CSRF/native POST→GET.
  Account flagdan mustaqil; shared tabs ikkala flag holatini ochiq bildiradi.
- V1 write guard: user/action-bound HMAC snapshot, explicit confirmation
  archive/reject/clear uchun; eski form no-write. Canonical preference writer
  versiya hisoblagichini ham saqlaydi; validation/choice/quota o‘zgarmaydi.
  Bu barcha admin/ORM/AI writerlar uchun global revision yoki durable receipt
  emas. Native form avtomatik qayta yuborilmaydi; noaniq natija GET bilan
  tekshiriladi. Persistent private draft/operation storage yo‘q.
- Owner workload: yangi operatsion jarayon yo‘q; existing audited flag bilan
  rollback. OFF faqat eski renderer; DB yozuvini o‘chirmaydi. V1 yuborilgan
  snapshot flag OFF bo‘lganda ham tekshiriladi.
- Failure: invalid/stale bound preference ko‘rinadi; known-offline/duplicate
  browser guard, dirty exit. Usage unavailable holati nol deb ko‘rsatilmaydi.
  Privacy clear faol faktlarni arxivlaydi VA canonical eski xotirani bo‘shatadi;
  toggle holati o‘zgarmaydi. Ko‘rishning mavjud maintenance ta’siri saqlanadi.
- Verification: offline focused users/memory/flags; full Django va Node;
  synthetic isolated DB browser mobile/desktop/theme/keyboard; native device,
  production rollout va real provider/SMTP bu paketda NOT TESTED.

## Holat

- [x] ~~Runtime, regressiya va lokal browser.~~ `d3c286e`.
- [ ] Required CI/review/main integratsiya.
- [ ] AWS release va haqiqiy qurilma qabuli — alohida.

Oldingi I5b.1 PR131 MERGED `af4ed76`; final CI `36196388190` uchala PASS.
8058 fresh isolated browser: bound409 dirty guard va long-name/bio320px
overflow0; runtime `3d51a61`. Profil/Hisob qayta port qilinmaydi.

## Tekshiruv va aniq chegaralar

Offline env: `AZURELMS_SKIP_ENV_FILE=1`, `GEMINI_API_KEY=''`,
`TELEGRAM_BOT_TOKEN=''`. Provider va production userlar ishlatilmadi.

- `venv/Scripts/python.exe manage.py test users.test_frontend_v1_settings
  users.test_frontend_v1_account users.test_settings_sections core.test_feature_flags
  --noinput --verbosity 1`: **65 OK**, 5.735s; 25 yangi settings regressiyasi.
  Rendered privacy snapshot bilan real POST ham tekshirildi (test-only token emas).
- `venv/Scripts/python.exe manage.py test --noinput --verbosity 0`: **PASS,
  exit0** (review follow-updan OLDIN; yangi full suite qayta boshlangan).
  Lokal output truncation sabab aniq count/time bu yerda da’vo qilinmaydi.
- `node --test tests/frontend_v1/*.test.mjs`: **73 PASS**, 0 fail.
- `manage.py check`: 0 issue; `manage.py makemigrations --check --dry-run`:
  No changes detected; `git diff --check`: PASS. Quyidagi additive migration bor.

IAB, disposable SQLite8059: real native login, preference explicit save/PRG,
ikki tabdagi o‘zgarishdan keyin eski POST409/no-write; bound tanlov va haqiqiy
saved label alohida. Rejected formdan link bilan chiqish bekor bo‘lib tanlov
saqlandi; server xatosiga fokus. Privacy uzun uzilmas matn, native disclosure,
billing canonical token/reset holati ko‘rildi. Har uch route uchun
320/639/640/1023/1024/1280 ×800 readback va overflow0; mobile320×740 va
desktop light/dark ko‘rildi. Drawer Escape → opener focus; console warn/error0.
Dastlab viewport boshqa tabga tushgan o‘lchovlar chiqarib tashlanib,
selected tabning haqiqiy `innerWidth` readback’i bilan qayta tekshirildi.

Privacy toggle/archive/reject/clear, explicit confirmation, foreign fact/user,
stale fact/legacy/new-fact va flag-OFF late POST **Django test client** orqali;
browserda privacy sozlamasi o‘zgartirilmadi. Staff shell, empty/legacy-only,
blocked/unlimited/unavailable usage holatlari backend testida. Full native
device, screen reader va provider/SMTP qabuli **NOT TESTED**; AWS deploy yo‘q.

## Review follow-up — `725d47c`

PR132 ikkita P2 topilmasi tuzatildi. A→B→A o‘zgarishi eski formani qayta
valid qilmasligi uchun `CustomUser.ai_preferences_version` monotonic counter;
`users/preferences.py:save_ai_preference` to‘rt mavjud endpointning V1,
legacy va JSON chaqiruvlari uchun yagona locked writer. No-op increment0;
har haqiqiy o‘zgarish barcha AI preference formalarni konservativ eskirtiradi.
Direct admin/ORM yozuvlari revision-aware deb da’vo qilinmaydi.

`users.0022_customuser_ai_preferences_version` additive migration: bigint0,
editable=False; drop/rename yoki data migration yo‘q. Deploy oldidan migrate
zarur. Renderer rollback schema/counterni o‘chirmaydi; 0022ni unapply qilish
oddiy rollback yo‘li emas. Production bu sessiyada migrate qilinmagan.

Snapshot aynan ko‘rsatilgan faktlardan olinadi; N+1 token query yo‘q.
Confirmed clear `MemoryRepository.archive_all_for_user`da faqat tekshirilgan
fact va legacy row IDlarini o‘zgartiradi. Verification→bulk write orasida
qo‘shilgan fact/legacy saqlanadi (deterministic interleaving regression).
Existing legacy clear-all kontrakti defaults bilan saqlangan.
AI writerlar uchun global revision/durable receipt da’vosi yo‘q. Private
draft storage/automatic resend yo‘q; privacy GET maintenance/decay saqlangan.

Keyingi port: register/reset/onboarding; records/help/notifications.
I6–I9 ochiq, bu paket notifications yoki checkoutni o‘z ichiga olmaydi.
