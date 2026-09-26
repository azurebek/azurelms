# I5b.2 — ro‘yxatdan o‘tish, tiklash va onboarding

## Admission — 2026-09-26, runtime tahriridan oldin

**ADMIT — launch-critical.** Owner tayyor frozen V1 prototiplarini real
kodga ulashni davom ettirishni so‘radi. Olti mavjud route: register,
onboarding choice, reset request/done/confirm/complete; register-closed va
invalid/expired token holatlari ham shu paketda. Yangi prototip yo‘q.

- Outcome/KPI: guest → register → optional onboarding → safe-next yo‘li,
  reset token/validation/session qoidalarini buzmasdan; 6 route ON/OFF,
  320–1280 overflow0, canonical backend regressiyasi va CI3/3.
- Canonical state: CustomUserCreationForm/RegisterView, `_safe_next`, Django
  PasswordReset views/token generator + UzbekSetPasswordForm; existing
  StartSmartOnboardingView/SmartFormSession. Yangi auth/provider/XP qoida yo‘q.
- Adapter: alohida default-OFF `frontend_v1_auth`, V1 templates/native forms;
  login avvalgi V1 rendererini learning YOKI auth flag bilan tanlaydi.
  Public registration kill switch GET va POSTda saqlanadi. Legacy OFF fallback.
- UX: bound oddiy maydonlar/error focus; parol serverda qayta render qilinmaydi,
  browser draft storage yo‘q; explicit submit/duplicate/known-offline/dirty-exit
  guard; page lifecycle’da parol tozalanadi. Preview receipt yoki retry yo‘q.
- Reset xati yetkazilganini UI kafolatlamaydi, email mavjudligi oshkor qilinmaydi.
  Success sahifasiga direct GET haqiqiy password change deb ko‘rsatilmaydi.
  SMTP/provider/AWS qabuli alohida; lokal email faqat locmem test backendda.
- Onboarding majburiy emas; skip canonical safe-next; AI boshlash mavjud POSTga,
  darslar avtomatik moslashadi degan yangi claim yo‘q. Real AI/Telegram yo‘q.
- Owner yuki: yangi qo‘lda boshqarish yo‘q. Rollback renderer flag OFF; hisob,
  parol, token va session yozuvlari o‘chmaydi. Model/migration rejalashtirilmagan.
- Verification: users + focused auth/flag; full Django/Node; isolated browser
  desktop/mobile/theme/keyboard/validation. Credential creation/reset final
  writes backend test clientda; UI orqali real hisob/parol o‘zgartirilmaydi.

## Holat

- [x] ~~Runtime, regressiya va lokal browser.~~ `ec0ff27`.
- [ ] Required CI/review/main.
- PR: [#133](https://github.com/azurebek/azurelms/pull/133).
  Merge holati va final CI run/SHA uchun PRdagi yakuniy acceptance comment
  authoritative; quyidagi lokal yozuv o‘sha remote natijani oldindan da’vo qilmaydi.
- [ ] AWS/SMTP/native-device qabuli — alohida.

Oldingi I5c.1 PR132 MERGED `dd198b7`; final CI36206802175 all3PASS:
SQLite2000 skip44, PostgreSQL2000 skip20, Node73. AWS’da hali yoqilmagan.

## Implementatsiya va tekshiruv

Canonical URLlar: `/users/register/`, `/users/register/onboarding/`,
`/users/password-reset/`, `/users/password-reset/done/`,
`/users/password-reset-confirm/<uidb64>/<token>/`, `/users/password-reset-complete/`.
`users/frontend_v1_auth.py` faqat renderer/form presentation adapteri;
real register va onboarding writerlari `users/views.py`da qoladi.
Parol tiklashda Django tokenni sessionga oladi va URLni `set-password`ga
almashtiradi; token bir martalik. Complete sahifasidagi bir martalik session
bool faqat UI notice, auth credential/durable receipt emas. Email yuborish
xatosini Django log qiladi; anti-enumeration generic javob saqlanadi.

- Offline env: `AZURELMS_SKIP_ENV_FILE=1`, `GEMINI_API_KEY=''`,
  `TELEGRAM_BOT_TOKEN=''`; email locmem, real AI/Telegram/SMTP yo‘q.
- `venv/Scripts/python.exe manage.py test users.test_frontend_v1_auth
  users.test_frontend_v1 users.test_register_remembers_where_you_were_going
  users.test_password_speaks_uzbek users.test_onboarding_can_be_skipped
  users.test_onboarding_context core.test_feature_flags --noinput --verbosity 1`:
  **100 OK**, final focused run 8.906s.
- `manage.py test users.test_frontend_v1_auth --noinput --verbosity 1`:
  **19 OK**, 1.819s (register va valid reset izohi o‘zbekcha ekanligi ham).
- `manage.py test --noinput --verbosity 0`: **2019 OK, skipped45**, 122.653s.
  To‘liq lokal run oxirgi help-text tarjimasi/assertiondan oldin; undan keyin
  focused qayta PASS. Final HEAD to‘liq CI alohida tekshiriladi.
- `node --test tests/frontend_v1/*.test.mjs`: **79 PASS**, 0 fail.
- `manage.py check`: issue0; `manage.py makemigrations --check --dry-run`:
  No changes detected. Bu paket model/migration qo‘shmaydi. `git diff --check` PASS.

IAB8060 disposable SQLite: 6 route + confirm-valid varianti,
320/639/640/1023/1024/1280 ×800, **42 haqiqiy innerWidth readback, overflow0**.
320×740 va 1280×800 light/dark screenshot ko‘rildi. Empty register native
validation birinchi required maydonga fokuslaydi; ikki password toggle
mustaqil. Synthetic native login → onboarding → keyboard skip → dashboard.
Reset draft bilan linkdan chiqish bekor bo‘lib matn saqlandi; maydon
tozalangach shu link login’ga o‘tdi. Console warn/error0. Viewport reset.
Browserdagi valid reset formasi faqat ko‘rildi, parol kiritilib o‘zgartirilmadi.

Backend client: real account yaratish, safe-next/CSRF/kill switch,
duplicate email/weak/mismatch, reset known/unknown/inactive/unusable email,
SMTP exception generic response, invalid/expired/foreign-session/reused token,
actual reset va one-use completion; flag-OFF fallback va late reset POST.
Onboarding start ketma-ket POST reuse tekshirildi; bu parallel global
idempotency kafolati emas. Browser offline/duplicate/lifecycle guard Node
unit testda; real network loss yoki provider qabuli deb da’vo qilinmaydi.

## Rollback va ochiq chegaralar

- `frontend_v1_auth` OFF: olti route legacy; login learning flag ON bo‘lsa
  V1da qoladi. Foydalanuvchi/parol/token yozuvi o‘chmaydi.
- AWS deploy/SMTP delivery va Android/iOS/screen-reader qabuli **NOT TESTED**.
  Auth flagni production’da yoqishdan oldin shu release gate bajariladi.
- Keyingi I5: records/help/notifications. I6–I9 alohida ochiq.

## Review follow-up — `ac2d13b`

PR133 P2: register draft/autofill va Telegram transport bir sahifada
ishlaganda authenticated/used javobidan keyingi canonical login redirect
beforeunload guardga tushishi mumkin edi. Faqat shu ikki canonical holat
uchun `frontend-v1:auth-redirect` UI event guardni chiqaradi; LoginView
session va safe-nextni avvalgidek qayta tekshiradi. Event auth credential
yoki login muvaffaqiyatining server dalili emas.

Pending/expired/network-error/cancel guardni o‘chirmaydi; pageshow himoyani
qayta tiklaydi. Ikkala production scriptni bir contextda yugurtiruvchi
3 yangi Node regression bilan **82 PASS**, 314.8868ms. Real Telegram bot
yoki production account ishlatilmadi. Final HEAD required CI qayta kutiladi.

## Yakun — keyingi paket boshida fresh tasdiqlangan

PR133 MERGED `75bba33754470d0c6c377ac6ae38d7551b20efdf`.
Final CI36208937362 uch required job PASS: SQLite2019 skip44,
PostgreSQL2019 skip20, Node82. Final lokal full2019 OK, skip45,117.077s.
Review thread resolved, final head `a6923c4` reviewida yangi topilma yo‘q.
[Acceptance comment](https://github.com/azurebek/azurelms/pull/133#issuecomment-5842048014).
Yuqoridagi pending-CI qaydlari tarixiy; AWS/SMTP/device hali ochiq.
