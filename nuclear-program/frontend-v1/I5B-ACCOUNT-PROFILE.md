# I5b.1 — Profil va Hisob porti

2026-09-26; **ADMIT — launch-critical**. Admission implementatsiyadan oldin. Branch:
`codex/frontend-v1-account-profile`; source `a25cf4b`.

## Qabul qilingan chegaralar

- Outcome: `/users/profile/` va `/users/settings/hisob/` frozen ACC-01
  layoutida haqiqiy profil, avatar va parol amallari bilan ishlaydi.
- KPI: ikki route ON/OFF; learner/staff navigatsiyasi; valid/invalid/stale
  profil save; CSRF/own-user/immutable identity; avatar bayt validatsiyasi;
  parol validatsiyasi va sessiya saqlanishi; 320/1280 overflow0.
- Canonical: `ProfileFieldsForm` (faqat ism/familiya/telefon/bio), existing
  `UserProfileView` context, `AvatarUpdateView` va `PasswordUpdateView`.
  XP/access/tarif/AI/email/username siyosati o‘zgarmaydi.
- Adapter: V1 template/form class/nav; profilning ikki V1 formasida
  user-scoped HMAC revision + user row lock bilan stale POST 409/no-write.
  Yangi DB model, migration yoki mustaqil biznes hisobi yo‘q.
- Owner load: yangi qo‘lda boshqarish talab qilinmaydi; native POST/PRG,
  server xatolari va explicit save. AI/Telegram/provider chaqirilmaydi.
- Rollback: alohida `frontend_v1_account` default OFF; OFF legacy template.
  Flag ma’lumotni o‘chirmaydi; eski V1 formadagi revision OFFda ham tekshiriladi.
- Launch category: existing-flow renderer port, alohida CI/release qabuli.
  AWS flag/deploy va production hisoblarini o‘zgartirish bu paketda yo‘q.

## Frozen → real farqi

Native disclosure, lokal settings tabs, shared form/avatar va mavjud tema
controlleri olinadi. Fixture run/receipt, sample avatar, demo parol, storage
va controller olinmaydi. Real sahifada email read-only; canonical XP,
nishon/tarif/Telegram holati saqlanadi. Teacher workspace uzilmaydi.

Profil qoralamasi faqat ochiq formadagi DOMda: shaxsiy ma’lumot browser
storagega yozilmaydi. Chiqishda dirty warning; invalid POSTda bound qiymatlar
saqlanadi. Parol/fayl hech qachon draft storagega yozilmaydi; parol
pagehide/pageshowda tozalanadi. Native POST noaniq tugasa avtomatik qayta
yuborish/success yoki durable receipt da’vosi yo‘q.

Ro‘yxatdan o‘tish/password reset/onboarding, qolgan settings, records/help
bu ikki-route paketga kirmaydi; I5ning ochiq qoldig‘i sifatida kuzatiladi.
Production SMTP yo‘q: email reset delivery tayyor deb aytilmaydi.

## Tekshiruv va dalil

- [x] Focused offline regression va Node controller testlari.
- [x] Izolyatsiyalangan local DB, desktop/mobile/light/dark/keyboard.
- [x] Full regression: **1975 OK, skipped45**, 371.752s.
- [ ] Required CI, review va main integratsiyasi.
- [ ] AWS release va real-device/owner qabuli (alohida).

Offline (`AZURELMS_SKIP_ENV_FILE=1`, `GEMINI_API_KEY=''`,
`TELEGRAM_BOT_TOKEN=''`):

- `venv/Scripts/python.exe manage.py test users.test_frontend_v1_account
  users.test_profile_inline_edit users.test_settings_sections core.test_feature_flags
  --noinput --verbosity 1`: **48 OK**, 12.261s.
- `node --test tests/frontend_v1/*.test.mjs`: **68 PASS**.
  Duplicate/dirty exit/other-form consent/password lifecycle/known offline.
- `venv/Scripts/python.exe manage.py check`: **0 issue**.
- Full `venv/Scripts/python.exe manage.py test --noinput --verbosity 0`:
  **1975 OK, skipped45**, 371.752s. Mocked failure loglari kutilgan;
  live provider yoki bot token ishlatilmagan.

Runtime commit: `1a4d6a3`. Follow-up: rejected bound form ham yangi
keystrokesiz unsaved deb olinadi; cached markupda offline notice yo‘qligi
native submitni buzmaydi. `manage.py test users.test_frontend_v1_account
--noinput --verbosity 1`: **14 OK**, 1.308s. Follow-up `3d51a61`.
PR131 MERGED `af4ed76`; final CI `36196388190` uchala PASS.
AWS rollout va haqiqiy qurilma qabuli alohida ochiq.

IAB + disposable SQLite8057: native login → profile save → account bir xil
ma’lumot; ikkinchi tabdagi profile save → eski account POST409, bound matn
saqlandi, error focus; qayta GET yangilangan ma’lumot. Dirty link navigatsiyasi
bekor bo‘lib formadagi matn saqlandi. Mobile drawer Escape → opener focus.
Learner/staff alohida local login; teacher workspace va home saqlandi.
Ikkala route 320/639/640/1023/1024/1280 ×800: overflow0; 320×568 ham ko‘rildi.
Light/dark desktop/mobile ko‘rildi. Viewport tekshiruvida dastlab boshqa
tabga override tushgani width readback bilan aniqlanib, haqiqiy o‘lchamlar
bilan qayta o‘lchandi; eski o‘lchov PASSga kiritilmagan.

Avatar valid/invalid upload va parol validator/session test-client orqali;
browserda credential almashtirish bajarilmagan (user handoff chegarasi).
Native telefon, screen reader, browser file picker/virtual keyboard va
AWS release **NOT TESTED**. Parol/rasm noaniq POST uchun durable receipt
yo‘q; takroriy yuborish avtomatik bajarilmaydi. Sensitive draft faqat DOM;
to‘liq browser yopilganda/reload’da recovery kafolati yo‘q.
