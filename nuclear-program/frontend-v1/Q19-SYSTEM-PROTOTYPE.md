# Q19 — tizim holatlari, lokal prototip

2026-09-28, D31 continuation; base `d13fecd`, branch
`codex/q19-system-prototype`. **Packet76: U40/U41 va H01–H03 qurildi.**
EXPERIMENT SYS-01: faqat ignored Eleventh Trial. Canonical runtime, DB,
AWS, provider, Telegram va maxfiy sozlamalar o‘zgarmadi.

## Qamrov va xatti-harakat

Preview: `http://127.0.0.1:8081/maintenance/`; pastdagi lokal galereya
besh holatni ochadi. Registry `0.76.0-system`: **138 named URL /76 page
template /117 source nomi /1214 route-state /202 action**. Bundan alohida
**3 handler diagnostic URL /3 template /3 state**; ular canonical named
UI hisobiga qo‘shilmadi. Manba: `core/views.py`, `core/urls.py`,
`templates/errors/{403,404,500,maintenance,offline}.html` va `_base_error.html`.

| Band | Holat | Lokal manzil | HTTP |
|---|---|---|---:|
| U40 | Texnik ishlar | `/maintenance/` |503 |
| U41 | Aloqa uzilishi | `/offline/` |200 |
| H01 | Ruxsat yo‘q | `/_preview/errors/403/` |403 |
| H02 | Topilmadi | `/_preview/errors/404/` |404 |
| H03 | Server xatosi | `/_preview/errors/500/` |500 |

- Mavjud token, tema, button/card/empty/icon asosidagi standalone error
  pattern. Yangi palette, font, breakpoint, global navigatsiya yo‘q.
- Retry — allowlisted **GET havola**. Oldingi POST qayta yuborilmaydi;
  `reload`, raw referrer, `history.back`, yashirin timer/auto-retry yo‘q.
  External, duplicate, nested, self/error, noma’lum va file-download return
  rad etiladi. Haqiqiy handlerlar requestni o‘qimay bosh sahifani taklif qiladi.
- 500 renderer request/user/site-settings/context-processor/state snapshot/
  DB/URL-reverse/app bootstrapga bog‘lanmaydi. Empty context ham render bo‘ladi;
  exception yoki oldingi POST qiymatlari HTMLga chiqmaydi. Faqat lokal assetlar.
- Oldingi write natijasi noma’lum bo‘lsa, avval tekshirish ogohlantiriladi.
  “Saqlandi”, “jamoa xabardor”, tiklanish vaqti yoki offline cache va’dasi yo‘q.
- 403 → login/home; 404 → home/katalog. Login qo‘shimcha ruxsat yaratmaydi.
  Galereya explicit synthetic namuna; haqiqiy outage sifatida ko‘rsatilmaydi.

## Tekshiruv dalili

Trial cwd `playground/Eleventh Trial`, root `venv/Scripts/python.exe`.
`AZURELMS_SKIP_ENV_FILE=1`, `GEMINI_API_KEY=` / `TELEGRAM_BOT_TOKEN=`,
`LOCAL_USE_REMOTE_SERVICES=0`. Real `.env` va provider ishlatilmadi.

| Buyruq / sinov | Natija |
|---|---|
| `python manage.py check` |0 issue |
| `python manage.py test tests --verbosity 0` |**800 PASS**,339.267s |
| `python manage.py test tests.test_system_pages --verbosity 0` |Final **12 PASS**,0.289s |
| `node --test tests/*.test.mjs` |**195 PASS**,0 skipped |
| IAB5 holat ×6width ×2theme |**60 PASS**,overflow0,controls≥44px |

12 focused test status/method, minimal/empty context, actual Django
DEBUG=False handler dispatch, GET/POST exception redaction, broken fixture
middleware→500, no mutation/snapshot, return validation, source mapping,
local asset/icon/action contract va no fabricated successni qamraydi.
Preview normal DEBUG=True; real handler dispatch testda DEBUG=False bilan
tasdiqlandi. Generic route-state test endi503 source statusini kutadi;
minimal ikki route uchun app bootstrap/dialog talab qilinmaydi.

Computer-use: widths320/360/390/768/1024/1440, light/dark. Dastlab topilgan
header alignment va galereya touch-target kamchiligi tuzatilib,60 o‘lchov
qayta o‘tdi. 320px offline→aniq lesson3 materials→Back;403→login va404→catalog;
740×320 horizontal overflow0, ko‘rinadigan keyboard focus/skip→main verified.
Final captured console warn/error0; HTTP403/404/500/503 ataylab qaytariladi.
Viewport reset. Lokal dalil `evidence/PACKET-76-RESULTS.md`, `packet-76-*.log`,
`packet-76-responsive.json`, `packet-76-console.json`, mobile/desktop PNG.

## Ochiq chegaralar va keyingi ish

**Q19 lokal implementation bajarildi; real port yoki owner/native qabul emas.**
Offline sahifa tarmoq uzilganda avtomatik ishlashini kafolatlamaydi: haqiqiy
PWA/service-worker/cache, offline asset delivery va native outage/AT OPEN.
Minimal HTML/GET testlari haqiqiy o‘chirilgan JS/CSS/network browser testi emas.
Canonical500 integration, middleware/proxy outage handling va production
security/header muvofiqligi port bosqichida qayta tekshiriladi.

Endi boshlang‘ich inventardan **1 yangi UI manzili (U42),2 qadam**:
Q08 legacy davomat/paritet → umumiy qabul. Q03 advanced, U17/A2-D01,
broad Q14, real Telegram, oldingi state-parity va owner G2/G3 qarzlari
ochiq; sahifalar soni ularni yopmaydi. AWS oxirgi qayd `8bb6b95`/19flags,
bu ish davomida qayta deploy qilinmadi.

## Lokal saqlash

Ignored prototype Gitga qo‘shilmadi yoki upload qilinmadi. Lokal checkpoint:
`playground/Eleventh Trial/checkpoints/packet-76-20260928-035343.zip`,
**610 fayl**, har ZIP entry SHA256 asl nusxa bilan tekshirildi.

SHA256 `9A6A42E7A0868301BE4B35DD38F2DFD7DDABA06D8F4C5BF39D91F62E7F5F19F9`.

Oldingi Packet75 checkpointi saqlanadi; rollback uchun u mavjud.
Restore canonical source checkout/existing venv talab qiladi;
ZIP venv/DB/secretlarni olmaydi. Tracked PR faqat dalil/reja/jurnal.
