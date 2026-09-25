# I4b — AI Messenger B adapteri

2026-09-26. **ADMIT — launch-critical.** Ownerning V1 port navbatidagi I4b.
Maqsad: o‘quvchi AI bilan keng, mobil composer ko‘rinadigan suhbatda ishlaydi;
tanlov yoki tarmoq xatosi promptni yo‘qotmaydi va provider qayta chaqirilmaydi.
Asosiy KPI: tekshirilgan yuborish/reconnect/retry yo‘llarida avtomatik
takroriy AI so‘rovi = 0. Ownerga yangi operatsion vazifa qo‘shilmaydi.

## Chegara va yagona haqiqat

- Tasdiqlangan D29 B layout, mavjud V1 token/shell va human chat transporti.
- `MessengerAIView`, room membership, `user_can_use_lesson_context`,
  `ChatConsumer`, upload, feedback va users preference viewlari canonical.
- `AIResponseRun` read-only status projection tarixni qayta ochganda ham
  pending/failed/fallbackni ko‘rsatadi; raw error, prompt yoki telemetry yo‘q.
- Model/skill choice backenddan; quota, supply budget, memory, RAG, provider,
  Telegram, AI engine va retry policy qayta yozilmaydi. Migration yo‘q.
- Yangi chat POST+CSRF; exact room; dars konteksti tekshirilgan holatda
  saqlanadi. Feedback, copy, explicit retry va file amallari saqlanadi.
- Uslub, web-search va memory mavjud settings sahifasiga ochiq link orqali.
- `frontend_v1_ai_messenger` default OFF; human flag mustaqil.
  OFF eski AI template/controllerni qaytaradi, xabar/preference o‘chmaydi.
- Shu ish davomida ownerning aniq tuzatishi: transcriptda faqat ism/xabar;
  doimiy feedback/copy/edit/retry qatorlari yo‘q. Amallar native dialogda:
  touch/pen long-press (scroll/tap bekor qiladi), desktop right-click yoki
  `⋯`, klaviatura Shift+F10. Human chat ko‘rinishi o‘zgartirilmaydi.
- AWS flag yoki live provider testi bu ishda bajarilmaydi. Frozen trialga
  tegilmaydi; demo javob production bundlega kirmaydi.

## Qabul

- [x] ~~Flag ON/OFF, auth/foreign room, lesson context, canonical choices.~~
- [x] ~~History/status privacy, feedback/retry va offline regressiya.~~
- [x] ~~Reconnect/no-resend, room/session/lesson draft, keyboard va no implicit save.~~
- [x] ~~Local ASGI + mocked AI: desktop/mobile, dark/light, asosiy amallar.~~
- [x] Required CI/review/integratsiya: PR130 `a25cf4b`, final CI `36192585672`
  all3PASS. Production release alohida gate.

## Lokal dalil

- Offline `manage.py test --noinput --verbosity 0`: **1961 OK, skip45**
  (121.459s); `.env` o‘qilmagan, provider/bot kalitlari bo‘sh.
- `manage.py test messenger.test_frontend_v1_ai messenger.test_frontend_v1
  core.test_feature_flags --noinput --verbosity 1`: **41 OK** (3.431s).
  `manage.py check`: 0 issue. `node --test tests/frontend_v1/*.test.mjs`:
  **61 PASS**, shu jumladan real controller no-resend, long-press cancellation
  va klaviatura fokusidagi row matn/fayl nomi bilan farqlanishi.
- Birinchi test fixtureda unique email yetishmagan, bitta komanda noto‘g‘ri
  `core.test_flags` nomi bilan yugurgan; ikkalasi aniqlanib tuzatildi.
  Node test harness import aliasi tuzatildi; testlar susaytirilmagan.
- IAB disposable DB8055, haqiqiy ASGI/socket/CSRF + **fake provider dispatch**:
  login, prompt/ack/answer, failed→cancel→confirmed retry→success,
  fallback/limit, feedback→reload, model/skill save, room draft/Back,
  Enter newline/Ctrl+Enter. Hech qanday haqiqiy AI yoki Telegram call yo‘q.
- Owner compact tuzatishidan so‘ng: transcript tugmalari faqat `⋯`;
  right-click va Shift+F10 menyu, feedback, clipboard exact text va
  retry tasdiq/cancel tekshirildi. Oldingi doimiy vaqt/action/status
  qatorlari yo‘q. Human chat layouti saqlandi.
- 320×568 document overflow0, history305px; 1280×800 overflow0,
  history521px, composer pastda. Light/dark ko‘rildi. Qayta dizayn emas,
  owner so‘ragan AI transcript ixchamligi.
- Qo‘shimcha 320/639/640/1023/1024/1280 ×800: overflow0, composer bottom800.
  Eski 8055 development asset keshi lesson draft tekshiruvida shubha berdi;
  fresh-origin8056 bilan context→none bo‘sh draft, Back→original draft PASS.
  Production dynamic module URLlari static manifest hashidan keladi.
- PR #130 dastlabki CI `36191990829` uchala PASS. Review P2: row accessible
  name ichiga xabar/fayl matni kiritildi; bir senderning ikki xabari endi
  klaviatura fokusida farqlanadi. Fix `1910aed`; final CI `36192585672`
  uchala PASS. Review thread resolved; PR130 MERGED `a25cf4b`.

## Ochiq cheklovlar

- Native Android/iOS long-press, virtual keyboard va screen reader qabuli
  **NOT TESTED**. Pointer/scroll cancellation Node’da; real browserda
  right-click/keyboard/menu yo‘li tekshirildi. `⋯` touch uchun ham fallback.
- Production deploy/flag ON va live provider/quota smoke bajarilmadi.
- Upload controller/canonical endpoint o‘zgarmaydi; AI attachmentda mavjud
  backend behavior saqlanadi. Lesson context text socket promptga tegishli;
  upload endpointi lesson scope qabul qilmaydi. Yangi file-context da’vosi yo‘q.
- User message uchun durable server send receipt yo‘q; unknown auto-resend
  qilinmaydi. Retry unknown bo‘lsa yangi canonical run ko‘rinmaguncha
  holatni GET bilan tekshirish kerak. Exactly-once da’vosi yo‘q.
