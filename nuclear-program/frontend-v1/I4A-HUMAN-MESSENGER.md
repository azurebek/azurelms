# I4a — haqiqiy guruh va ustoz suhbati

Admission: **ADMIT — launch-critical** V1 port, 2026-09-25.
Branch `codex/frontend-v1-human-messenger`.
Owner D29 Messenger B joylashuvi; D30 yangi prototip/redesignsiz real port.
Outcome: learner/ustoz keng tarix va ko‘rinadigan composer orqali haqiqiy
xabar yuboradi. KPI: 320×568 / 1120×680 oddiy holatda tarix >=240px,
document overflow=0; noto‘g‘ri xona, yashirin qayta yuborish, yo‘qolgan matn=0.
Owner operatsion yuki: yangi xizmat, migration yoki provider yo‘q.
I1+I2 relizi bu bo‘lakni kutmaydi. AWS/device qabuli alohida R1.

## Scope / contract

- MSG-02: mavjud `messenger:group` / `messenger:tutor`; explicit `?room=ID`
  faqat canonical ruxsatli shu turdagi xonani tanlaydi. Invalid/foreign/duplicate
  parametr 404; boshqa suhbatga jim fallback yo‘q. AI I4bda, legacy qoladi.
- Source: frozen `messenger-wide/index.html`, `layout.css`, `REVIEW.md`.
  Faqat tasdiqlangan viewport grid, shared token/shell/theme. Demo model,
  sample controller, fixture va storage productionga kirmaydi.
- Canonical: `messenger.access`, `ChatConsumer`, `get_room_messages`,
  `edit_message`, `delete_message`, `upload_message_attachment`, private media.
  Backend permission/validator saqlanadi; yangi reply/audio/AI engine yo‘q.
- Actions: native xona link/search/mobile list/detail/Back; history GET va
  eski xabarlar cursor GET; socket send/echo; CSRF edit/delete/upload;
  native dialog confirm; latest-scroll; shared menu/theme/POST logout.
- Aloqa: cheklangan reconnect + history refresh, hech qachon automatic resend.
  Mavjud human socket client IDni faqat echo qiladi, DB idempotency receipt
  saqlamaydi. Unknown send/uploadda matn+marker qoladi, yuborish bloklanadi;
  foydalanuvchi tarixni tekshirib alohida tasdiqlamaguncha qayta yozilmaydi.
  Bu exactly-once kafolati emas. Binary fayl reload orqali tiklanmaydi.
- Draft: authenticated session/user/room bo‘yicha tab xotirasi; logoutda
  tozalanadi. Enter yangi qator, Ctrl/Cmd+Enter submit; IME submit emas.
- States: initial/empty/long/loading/offline/reconnecting/unknown/forbidden/
  history or upload validation failure/storage denied. Xabar untrusted text.
- `frontend_v1_messenger` default OFF. OFF legacy template/controller;
  xabarlar va fayllar saqlanadi. Canonical access fix rollbackdan mustaqil.

## Backend adapter farqlari

- Human room GET `?room=ID` canonical ruxsatli ro‘yxatda exact tanlanadi.
  Staff membership student enrollment sync tomonidan olib tashlanmaydi.
- History oldingi latest-100 contractini saqlaydi; optional `?before=ID`
  stable created_at/PK cursor, `has_more/before`. `?message=ID` shu xona
  ichidagi xabarni authoritative boshqarish uchun o‘qiydi. No-store saqlanadi.
- Edit/delete optional signed `revision`: transaction + row lock, stale409.
  Legacy revision yubormasa oldingi contract; empty native delete POST saqlangan.
  Broadcast faqat commitdan keyin. Model/migration yo‘q.
- Ochiq socketdan faqat o‘qiyotgan hisobning ham ruxsati broadcastdan oldin
  qayta tekshiriladi. Revocation → 4403; private matn/attachment berilmaydi.
- `@azure` canonical yo‘li o‘zgarmaydi; kelgan matn/status ko‘rsatiladi.
  To‘liq AI controls/feedback/provider UI I4bda, legacy AI havolasi ochiq.

## Verification — 2026-09-25

Kalitlar bo‘sh, `AZURELMS_SKIP_ENV_FILE=1`; vaqtinchalik DB/media.

- `venv/Scripts/python.exe manage.py check`: 0 issue.
- `venv/Scripts/python.exe manage.py test messenger --noinput --verbosity 0`:
  159 test OK. Keyingi teacher-menu testi bilan focused
  `manage.py test messenger.test_frontend_v1 --noinput --verbosity 1`: 15 OK.
- `venv/Scripts/python.exe manage.py test --noinput --verbosity 0`:
  1928 OK, skipped45, 246.009s (oxirgi qo‘shimcha teacher-menu testi focused
  tarzda o‘tdi; final CI butun yakuniy holatni qaytaradi).
- `node --test tests/frontend_v1/*.test.mjs`: 45 PASS. Jumladan real
  controller startup no-write, double-send, reconnect no-resend, exact echo,
  foreign session cleanup, storage denied, unknown reload va revoked socket.
- `node --check static/frontend_v1/js/messenger.mjs` va state module: PASS.
- IAB / Windows, synthetic real Django ASGI server8053: real group send→echo,
  edit→reload, file upload→private URL, checkbox-confirmed soft delete,
  100→108 history pagination, group/tutor draft→Back, Enter newline va
  Ctrl+Enter send, mobile list/detail, search no-results tekshirildi.
- 1120×680: history420 / composer bottom680. 320×568: history324 /
  composer bottom568. 639/640/1023/1024/1120 ×680: document horizontal
  overflow0 va composer bottom680. Light/dark screenshots ko‘rildi.
  Uzun guruh nomi sabab implicit grid minimum overflow topilib, chatga
  `minmax(0,1fr)` explicit column qo‘yildi; qayta o‘lchov yuqorida.
- Haqiqiy synthetic PDF validator/private-download/deleted-file gate,
  CSRF/foreign room/expired membership/teacher membership va sender identity
  tests. Hech qanday AI/Telegram providerga jonli call yuborilmadi.
- Final updated serverda teacher menu o‘z maydonida qoldi, staff ham
  real group send/echo qildi. Console warn/error0. Runtime `a3af24f`.
- Rollback review `d48256c`: flag OFF ham mavjud explicit `?room=ID`
  manzilini boshqa guruhga burmaydi; foreign/type mismatch404. Final
  `manage.py test messenger.test_frontend_v1 --noinput --verbosity 1`:
  16 OK. Browserda tutor pin→server saved, native info dialog ham sinaldi.

## Release / cheklovlar

Required CI va merge yakuni PRda tekshiriladi; hozir lokal dalil yuqorida.
Default OFF; AWS o‘zgarmagan. Real-device virtual keyboard/AT, Firefox/
WebKit, live AI/Telegram va AWS rollout NOT TESTED, R1 ochiq. Canonical
human transportda durable client receipt yo‘q: unknownni serverdagi exact
nonce bilan reload orqali avtomatik reconcile qilish da’vo qilinmaydi.
Input/marker saqlanadi, yangi yozish faqat tarixni ko‘rib explicit discarddan
keyin. I4a I4b AI qabulining o‘rnini bosmaydi.
