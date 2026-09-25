# I5a — public V1 port

Admission: **ADMIT — launch-critical**, 2026-09-25.
Owner navbatni o‘zgartirdi: public avval → mavjud tayyor qismlar bilan
`azurebek.me` AWS release qabuli → I4b va qolgan navbatga qaytish.
Branch: `codex/frontend-v1-public-pages`.

## Outcome va scope

Mehmon platforma/kurs/tarif/kontentni bir tanish V1 shell orqali ko‘radi,
kirish yoki canonical checkoutga o‘tadi. KPI: 14 public route turi desktop
va 320px compactda ochiladi, document horizontal overflow=0; nashr etilmagan
kontent yoki yopiq dars mehmonlarga ochilmaydi.

- Home, about, catalog/detail, pricing, FAQ/terms/privacy, blog list/detail,
  SIT home/university list/detail/guide detail.
- Frozen public.html/public.css va page patterns; yangi palette/framework/
  prototype yo‘q. Demo kontent productionga ko‘chmaydi.
- Canonical sources: frontend model/context processor; CourseList/Detail;
  purchase_plans; BlogPost.published va existing comment/clap/like views;
  SIT selectors va staff preview gates. Tarif/access/grade hisoblanmaydi.
- Public renderer flag `frontend_v1_public` default OFF. OFF eski sahifalar;
  DB/content/permission va existing actions saqlanadi. Migration yo‘q.
- Admin boshqaradigan brend/nav/kontent saqlanadi. Yangi operatsion xizmat
  yoki haftalik owner vazifasi qo‘shilmaydi. Checkout I7, auth qoldig‘i I5b,
  backoffice editorlar va AI chat bu paketda qayta qurilmaydi.
- Native GET filters/pagination, native POST comments, CSRF reaction calls;
  unknown reaction qayta yuborilmaydi. Dynamic titles/empty/long/preview
  va dark/light tekshiriladi. Legal matnlar mavjud DBdan, yangi huquqiy copy yo‘q.

## Gate

Offline Django relevant apps + full suite, Node controller checks, collectstatic,
browser desktop/compact/light/dark; required uch CI va review. AWS deploydan
oldin deployed/target SHA, backup/rollback, flaglar, xavfsiz smoke tekshiriladi.
Hozircha productionga yozish bajarilmadi. Provider/bot kalitlari testda bo‘sh.

## Natija

Runtime commit: `74818ee`. Lokal implementatsiya va tekshiruv PASS;
required CI/integratsiya va R1 production qabuli hali alohida ochiq.

`frontend/public_v1.py` existing class/function viewlarga faqat renderer,
title va xavfsiz family-scoped `return_to` qo‘shadi. Eski queryset, pricing,
access, staff-preview va comment/clap/like endpointlari o‘zgarmagan.
Boy matn existing `sanitize` filtridan o‘tadi; nav tashqi URLlari executable
scheme olmaydi. Public javoblar private/no-store. Flag OFF eski templatega
qaytishi barcha 14 route uchun testlangan.

2026-09-25 owner 320px headerning juda katta va gorizontal scrollbarli
ko‘rinishini rad etdi. Bu qabul qilingan kosmetik qarz emas: header native
ochiladigan menyuga tuzatildi. Yopiq balandlik ~65px; logo/theme/menu bir
qator; sahifa/auth havolalari ochilganda ko‘rinadi. Escape fokusni menyuga
qaytaradi, tashqariga bosish/desktopga o‘tish/Back menyuni yopadi. JavaScriptsiz
ham native disclosure ishlaydi. Frozen trial fayllari o‘zgartirilmagan.

### Dalil

Provider/bot kalitlari bo‘sh va `AZURELMS_SKIP_ENV_FILE=1`:

- `venv/Scripts/python.exe manage.py check`: 0 issue.
- `venv/Scripts/python.exe manage.py test frontend.test_public_v1 --noinput --verbosity 0`:
  14 OK. Publication/preview, expired enrollment, CSRF, empty/long content,
  numeric statistic, safe links/return, native actions va ON/OFF qamralgan.
- `venv/Scripts/python.exe manage.py test --noinput --verbosity 0`:
  **1945 OK, skipped=45**, 123.170s.
- `node --test tests/frontend_v1/*.test.mjs`: **53 PASS**.
- Node syntax va `git diff --check`: PASS. Isolated serverning
  `collectstatic` bosqichi PASS; real local DB/media o‘zgartirilmadi.
- IAB `8054`, temporary SQLite/media, synthetic accounts: catalog explicit
  GET filter→pagination→detail→filtered back; exact login-next; blog
  search/tag→detail→clap→login→native comment/reply→like real server ACK.
- 320px dark header closed/open va Escape/focus: PASS, scrollbar yo‘q;
  long blog/320px light university detail: document overflow yo‘q.
  Universitet filtri `status=all` yopiq universitetni ham ko‘rsatdi.
  University detail 640/1024pxda ham overflow yo‘q; SIT desktop/light va
  guide/source ko‘rildi. About/pricing/FAQ/terms/privacy 320 va 1280pxda
  title/content mavjud, document overflow yo‘q. Console warn/error: 0.
  Tema va vaqtinchalik viewport tekshiruvdan so‘ng qaytarildi.

### Chegara / release

- Bu real backendga port, lekin `8054`dagi yozuvlar faqat sintetik sinov
  kontenti; production matnlari aynan o‘sha kontent emas.
- Native izoh POSTi canonical redirect beradi; cross-reload durable comment
  draft yoki idempotent receipt kiritilmadi. Reaction unknown avtomatik
  qayta yuborilmaydi; reload explicit.
- Eski landing carousel/animatsiya/presetlari V1ga ko‘chirilmagan; asosiy
  kontent/brend/nav/statistika canonical DBdan. Bu yangi biznes va’da emas.
- Checkout, records/help, qolgan auth/preferences hamda AI legacy qoladi.
- Haqiqiy iOS/Android qurilmasi, AWS target/deployed SHA, backup/rollback,
  real-content visual qabul va owner go/no-go **hali bajarilmagan**.
  Owner ko‘rinish bo‘yicha e’tirozidan keyin deploymentga o‘tilmadi.
