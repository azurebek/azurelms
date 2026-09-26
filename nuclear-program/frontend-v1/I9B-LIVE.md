# I9b — Classbook jonli dars va natijalar

ADMIT — launch-critical. Frozen V1ning qolgan 6 rendereri: teacher_session,
teacher_activity_result, live_home/session/activity/result. KPI: ustoz mashqni
ochishi → learner bir javob yuborishi → explicit reveal → natijani ko'rish.
Owner operatsion yuki oshmaydi; yangi mahsulot/baholash qoidasi yo'q.

Canonical state/service: ActivityRun, StudentResponse, TelegramLessonSession;
open_activity / submit_response / close_activity / finish_class_session.
Web shu servicelarni iste'mol qiladi. Telegram, davomat, XP, access va grading
shu domain qatlamida qoladi. Default-OFF frontend_v1_classbook_live; OFF eski
renderer, in-flight V1 write no-write. Schema migration rejalashtirilmagan.

Transport: explicit native teacher confirmation + scoped state fingerprint;
learner JSON submit/GET reconcile, bir javob unique constraint. Hech qanday
auto POST retry, avtomatik navigatsiya yoki javobni browser storagega yozish
yo'q. Unknown holatda draft DOMda qoladi, GET tekshiruv yozuv qilmaydi.
Mashq ID aliaslari serverda canonical IDga qaytadi; answer key reveal oldidan
clientga chiqmaydi. Ball clientda hisoblanmaydi.

Tekshiruv: provider-free classbook + full suites, PG race, Node state tests,
6 renderer desktop/mobile, open→submit→reveal→finish synthetic browser.
Haqiqiy AWS/Telegram/native device release alohida. Frozen prototype va
current DB o'zgarmaydi. Natijalar tekshiruvdan keyin shu yerga yoziladi.

## Dalil — 2026-09-26

- Runtime `7c3c906`: 6 renderer V1ga ulandi. [PR143](https://github.com/azurebek/azurelms/pull/143)
  required CI, review va main acceptance uchun authoritative manba.
- Provider-free `venv/Scripts/python.exe manage.py test --noinput`:
  **2301 OK skip57 (197.702s)**, oxirgi strict JSON/reveal-copy/reyting
  follow-up va qo'shimcha PG testdan oldin.
- Focused `manage.py test classbook --noinput --failfast`:
  **80 OK skip5 (9.530s)**, oxirgi PG submit/finish regressiondan oldin.
- Final `manage.py test classbook.test_frontend_v1_live --noinput --failfast`:
  **15 OK skip2 (2.747s)**; PG same-page open va submit/finish race CI’da.
- `node --test tests/frontend_v1/*.test.mjs`: **122 PASS**;
  oxirgi JS follow-updan keyin classbook-live subset **11 PASS**.
- `manage.py check --fail-level WARNING`: 0 issue; migration drift: no changes.
- IAB8075 disposable DB: teacher login → open → learner short answer submit
  → accepted → teacher reveal → explicit learner result → teacher result →
  finish. Canonical score109.88/110 va davomat1/1 UI’da ko'rildi.
- 6 renderer × 320/639/640/1023/1024/1280 = **36 actual width readback**, positive
  overflow0. Hidden teacher tabga viewport qo'llanmagan dastlabki6 o'lchov
  hisoblanmadi; yangi tabda haqiqiy kengliklar qayta tasdiqlandi.
- Desktop dark/mobile320 light screenshotlar ko'rildi; lokal ignored dalil:
  `playground/frontend-v1-smoke/i9b-result-desktop.png`, `i9b-result-mobile.png`.
  Yakuniy teacher/learner tab console warn/error0; viewport reset.
- IAB bitta tabda debugger timeout berdi; server200 javob berishda davom etdi.
  Yangi tabda tekshiruv yakunlandi. Eski tabdagi timeout app xatosi deb talqin
  qilinmadi. UI amallari klaviatura Enter/Space bilan bajarildi.

## Contract va release chegarasi

- Parent-first cohort→session→activity lock tartibi live servislarida ham
  start/finish tartibiga mos. Grade/access/XP qoidalari o'zgarmadi.
- Teacher snapshot faqat lifecycle/definition/playbook sozlamasiga bog'liq;
  javob sonining oshishi ustoz formasini eskirtirmaydi. Eski amal409/no-write.
- Matching/order/categorization IDlari HMAC alias; V1 permutation secret
  seed bilan. Raw sequential ID yoki public deterministic shuffle'dan javobni
  tiklash yo'q. Canonical snapshot/grader o'zgarmaydi; flagOFF legacy transport
  saqlanadi, bu global legacy hardening deb da'vo qilinmaydi.
- Learner first accepted response o'zgarmaydi. Reconcile faqat "serverda
  javob mavjud"ni tasdiqlaydi — boshqa tabning javobi bo'lishi ham mumkin;
  yuborilgan aynan shu bytes uchun durable operation receipt yo'q.
- Unknown holatda shu DOMdagi javob o'chmaydi va qayta POST qilinmaydi.
  Reload/tab close oldidan ogohlantirish bor; reload/crashdan keyin draftni
  tiklash yoki prototype'dagi durable receipt bilan to'liq parity da'vosi yo'q.
- API access/reveal gate, 10 tur canonical grading va DOM collect shape testlari;
  haqiqiy device'da barcha10tur, media playback, Wi-Fi uzilishi/reconnect,
  50 foydalanuvchi real load va tashqi Telegram yetkazish qabuli hali ochiq.
- AWS/current DB/frozen trial o'zgarmadi. Flaglar defaultOFF; main integratsiya
  deployed yoki production acceptance degani emas.
