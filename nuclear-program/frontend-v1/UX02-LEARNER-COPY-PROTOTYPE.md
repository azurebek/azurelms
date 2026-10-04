# UX-02 — o‘quvchi matnlari, Packet83

2026-10-04. Base `a442b28`; EXPERIMENT — canonical state yozmaydi.
Faqat ignored Eleventh Trial, real runtime/DB/AWS o‘zgarmadi.

## Bajarilgan qism

8 page template: kurslarim, dars, bildirishnomalar, yordam, profil,
hisob/to‘lov/imkoniyatlar sozlamalari. Platform/Auth footer ham soddalashdi.
Foundation/fixture/backend/RAG/exemption kabi keraksiz ichki izohlar,
takroriy no-effect tushuntirishlari va eskirgan “hali ulanmagan” matni
aniq foydalanuvchi ko‘rsatmasiga almashtirildi yoki olib tashlandi.
Sinov belgisi yo‘qolmadi; real xizmat, hisob yoki AI ishlayotgani aytilmadi.

Saqlash/draft/stale/unknown, qayta yuborish natijasi, fayl/parol chegarasi,
ruxsat va moliyaviy ogohlantirishlar saqlangan. Lab va owner runbooklari
o‘zgarmadi. URL, action, form fields, CSS/JS/fixture/formula o‘zgarmadi.
Packet82 ZIP bilan10template taqqoslandi: a/button/input/form/select/
textarea teglarining atributlari aynan bir xil. Eski nusxa hash mos.

## Tekshiruv

Trial cwd; `AZURELMS_SKIP_ENV_FILE=1`, `GEMINI_API_KEY=`,
`TELEGRAM_BOT_TOKEN=`. Haqiqiy provider chaqirilmadi.

- `../../venv/Scripts/python.exe manage.py test tests.test_learner_copy
  tests.test_support tests.test_profile_entry tests.test_billing
  tests.test_lesson_journey tests.test_auth --verbosity 0`: **74 PASS**,
  6.129s;6 yangi copy/no-write/safety testi.
- Barcha `.test.mjs` fayllari PowerShellda kengaytirilib `node --test`:
  **227 PASS**,1526.4985ms. `manage.py check`:0.
- `../../venv/Scripts/python.exe manage.py test tests --verbosity 0`:
  **875 PASS**,519.899s; check0. All-route/state/control regression ham shu
  yakuniy suite ichida o‘tdi. `git diff --check`: PASS.
- IAB localhost8088:10route×320/390/768/1280px×light/dark = **80 DOM case**;
  8route×empty/offline/long×320/1280 = **48 state case**, dark tema.
  Har case effective width tekshirildi, document horizontal overflow0.
  Bu barcha browser/real-device yoki har uzun matnning pixel qabuli emas.
- 390px profil edit→Enter save→hisobda bir xil matn. Uslub tanlash saved
  labelni o‘zgartirmadi; explicit save→reload yangisini ko‘rsatdi.
  Notification read→lesson link→native Back o‘qilgan holatni saqladi.
  Console warn/error0; mobile/desktop screenshotlar lokal evidence’da.
- Browserda mavjud avatar guard profilni shu oynada saqlaganda ham
  “boshqa oynada” deydi; yangilash orqali ishlaydi. Copy-controller
  muvofiqligi UX-02ning qolgan qismida tekshiriladi; bu yerda tuzatilgani
  da’vo qilinmaydi. Avatar/parol biznes amallari bu paketga kirmaydi.

## Saqlash va ochiq chegara

Source/assets/tests/screenshots ignored playground’da; Gitga faqat docs.
Verified `playground/Eleventh Trial/checkpoints/packet-83-20261004-135738.zip`:
**664 fayl**, har entry SHA256 asl nusxa bilan tekshirildi.
ZIP SHA256 `86609F0CAC7B535547AD176204BD5F466500942DD13BDF4E365E68C4C7FCEB86`.
Packet82 saqlandi, SHA256 mos.
Bir diskdagi checkpoint offsite backup emas.

**UX-02 PARTIAL:** tanlangan o‘quvchi copy qismi bajarildi. Qolgan sahifalar
va dinamik JS/server feedback matnlari, til/apostrof to‘liq auditi hamda
real `templates/frontend_v1/`dagi V1/migratsiya/eski-ko‘rinish yozuvlari
ochiq. Root runtime bu taskda o‘zgartirilmadi. UX-01 native keyboard,
UX-03..06, DATA-01/RULE-01/owner qabul → DESIGN-01 navbati saqlanadi.
Packet82 responsive cheklovi ushbu10route sinovi bilan umumiy yopilmaydi.
