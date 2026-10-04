# PAR-05 — chek, muqobil kirish va material yo‘llari

2026-10-04, Packet82; source base `994494f`. Admitted lokal funksional
implementatsiya yakunlandi. **G3/native/owner qabul yoki real port emas.**
Faqat ignored Eleventh Trial; canonical runtime/DB/AWS o‘zgarmadi.

## Tuzatilgan farqlar

- `cohorts/receipt_service.py` rad etilganda haqiqiy chekni o‘chiradi.
  Preview ham eski ID uchun404 qaytaradi, subscriptions receipt historydan
  olib tashlaydi. Ichki operation tombstone saqlanadi, lekin ochiladigan
  chek va pending/success havolasi emas. Open tab notice bilan yangilanadi,
  avtomatik redirect/focus sakrashi yo‘q. DEBUGda ham mavjud Q19 404,
  obunalarga aniq qaytish; texnik URLconf dump ko‘rsatilmaydi.
- Unknown submit→reload qulfi→explicit GET reconcile keyinroq rad etilgan
  natijani ham topadi. Exact replay yozuvni qayta yaratmaydi. Yangi chek
  yangi ID oladi. Accepted link current snapshotdan; eski objectdan emas.
  Ackdan keyin fayl tanlovi va tasdiq tozalanadi, eski success qolmaydi.
- `cohorts/views.py` pending/success verification redirectlari moslandi.
  `/checkout/success/` own latest verified yoki subscriptions; fixture
  creation order, katta301ID yangi31dan keyin yaratilgan degani emas.
  `/messenger/` source `MessengerAIView` kabi existing AI rendererga kiradi;
  lesson konteksti, login next va Back saqlanadi. GET yozmaydi/POST405.
- Picker3/81/list→detail→filtered Back va resource save qaytishi saqlanadi.
  Strict local return allowlist; foreign/nested/duplicate query va boshqa
  resource target rad. Bu C04 local continuity hardening; real legacy
  editor allaqachon shunday ishlaydi degan da’vo emas. 81-darsdagi eskirgan
  “o‘quvchi yuzasi yo‘q” copy olib tashlandi. New-family handoff regression.

Registry139named UI +**2alias**,77page/118renderer-source +2alias-source,
1223state/213action +3handler. Aliaslar ikki yangi dizayn deb sanalmaydi.
Yangi shell/token/font/dependency/business formula/capability yo‘q.

## Dalil

Trial cwd, `.env.local`siz: `AZURELMS_SKIP_ENV_FILE=1`, `GEMINI_API_KEY=`,
`TELEGRAM_BOT_TOKEN=`. Production/AI/Telegram/payment ulanmagan.

- `../../venv/Scripts/python.exe manage.py test tests --verbosity 0`:
  **869 PASS**,432.246s/check0;11yangi test. Old screen tests200 taxmini
  source lifecycle404/redirect va haqiqiy sintetik fixture setupga moslandi.
- Focused58 PASS11.279s: `tests.test_journey_parity tests.test_payments
  tests.test_payment_difference tests.test_system_pages tests.test_library
  tests.test_library_resources`. Oldfocused36 ichida all-route/state/control
  tekshiruvlari bor; yakuniy869 barchasini qayta qopladi.
- Barcha `tests/*.test.mjs` PowerShellda kengaytirilib `node --test`:
  **227 PASS**,1571.611ms;4yangi payment-state test. JS syntax/check PASS.
- IAB8087:31reject→dead-link yo‘q;32unknown→reload locked→reject→read-only
  reconcile;33new→approve→reload canonical success/latest alias. AI alias
  lesson→Back; keyboard Enter picker/detail return. localhost8088:46attach→
  learner81 visible→detach→hidden. Missing receipt Q19 screen. Tekshirilgan
  nuqtalarda console error/warning0.
- Desktop screenshots mavjud va ko‘rildi; lokal `evidence/packet-82-*jpg`.
  **Compact responsive NOT VERIFIED:** viewport override requested320..1920,
  effective1280/1920 qolgan; mismatched runs PASSga kirmaydi. Native phone,
  UX-01 iPhone Chrome, AT/Firefox/WebKit/owner acceptance ochiq.
- Ikki preview server birhostname/turliport cookie bilan to‘qnashdi; eski
  forma stale guard orqali rad etildi. Browser test localhost8088ga ajratilib
  qayta o‘tdi. Bir hostname uchun bitta faol preview; durable data emas.

## Saqlash va qolgan ish

Source/assets/tests ignored playground’da. Gitga faqat dalil/tracker kiradi;
force-add/upload yo‘q. Verified lokal checkpoint
`playground/Eleventh Trial/checkpoints/packet-82-20261004-133144.zip`:
**659 fayl**, har entry SHA256 asl nusxa bilan tekshirildi.
ZIP SHA256 `FB8C509B89C370766865187B28BDB2C4FECE3748552905C7ED2E52242DA6D5DD`.
Old Packet81 arxiv SHA256 qayta tekshirildi va saqlandi; lokal nusxa
mustaqil offsite disaster-recovery backup emas.

PAR-01..05 admitted lokal implementatsiyalari tugadi. Final UX-01..06,
DATA-01/RULE-01/native/owner qabul→DESIGN-01 qoladi. U17/A2-D01, kengQ14,
human reply/assignment/quiz authoring alohida capability qarorlari; bu
paket ularni yopmaydi. Real port/deploy avtomatik boshlanmaydi.
