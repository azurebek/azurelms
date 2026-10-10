# DESIGN-01 DC6 — yakuniy ko‘rib chiqish va tiklash

2026-10-10. **Qabulga tayyor; owner qarori kutiladi.** Ustaxonaga 8 qadamli
yo‘riqnoma qo‘shildi, agent asosiy oqimni sinadi va yangi checkpointni alohida
papkaga tiklab tekshirdi. Bu DESIGN-01 yoki production release yakunlandi degani emas.

## Qamrov

EXPERIMENT — canonical state yozmaydi. Outcome: owner dizaynni bitta
ketma-ket yo‘l bilan ko‘rib chiqadi. KPI: har bir 8 qadamda amal va kutilgan
natija aniq. F20 studio; existing feedback, keyboard va documentation
patternlari. `review.toggle` faqat native detailsni ochib/yopadi;
`review-open` / `review-closed` qabul statusi emas. Yangi yozuvchi, DB,
endpoint, migration, network provider yoki runtime theme qo‘shilmadi.

`studio.html` yo‘riqnomasi va scoped `design_studio.css` yangilandi.
Design catalog: **26 action / 22 state**, existing 87 field / 118 value,
5 URL pattern, 2 template va 142 inert consumer snapshot. Shared
`tokens/base/components/shell.css` va real route registry baytlari saqlandi.

## Owner bilan ko‘rib chiqish

Lokal URL: `http://127.0.0.1:8088/_preview/design/`.
Yuqoridagi **Yakuniy tekshiruv · 8 qadam** bo‘limini oching. Mavjud
qoralamani almashtirishdan oldin nomli variant qilib saqlang; bu ham tabga
bog‘liq va doimiy server backupi emas.

1. **Variant:** Yumshoq shakllarni qo‘llab, kerakli almashtirish tasdig‘ini bering.
   Qoralama o‘zgaradi, joriy versiya nashrgacha o‘zgarmaydi.
2. **Mustaqil shakl:** tugma, karta, input va dialog radiusini bittadan o‘zgartiring.
   Bir rol boshqasini almashtirmasligi kerak; bo‘sh qiymat meros oladi.
3. **Rang va matn:** ikkala rejimni ko‘ring. Kontrast xatosi, maydonga qaytish,
   xatoni tuzatish va qayta saqlashni tekshiring.
4. **Sahifalar:** dashboard, auth, chat, exam, Mini va statik xato namunasini
   tanlang; telefon/kompyuter enida solishtiring. Inert nusxada amallar ishlamaydi.
5. **Saqlash:** qoralamani saqlab, shu tabni yangilang; qiymatlar qaytishi kerak.
6. **Lokal nashr:** tayyorlash → farq → sabab → tasdiq → nashr. Versiya va tarixni ko‘ring.
7. **Qaytish:** tarixdan oldingi versiyani sabab/tasdiq bilan qaytaring.
   Yangi tarix yozuvi hosil bo‘ladi; qoralama alohida saqlanadi.
8. **Qurilma:** quyidagi native matritsani haqiqiy qurilma va adapterda yakunlang.

## Qabul qaydi

| Band | Agent dalili | Owner/native holati |
|---|---|---|
| Yo‘riqnoma tushunarliligi, variant va vizual tanlov | 8 qadam ko‘rinadi; lokal smoke bor | PENDING — tanlangan variant va owner izohi kerak |
| Draft/reload, sabab/tasdiq, tarix/rollback | Lokal IAB oqimi PASS | PENDING — owner walkthrough |
| Telefon klaviaturasi va touch | 320/390 CSS viewport tekshirildi | NOT TESTED — haqiqiy telefon/OS/keyboard nomi bilan |
| 200% brauzer zoomi | DC5 root text sinovi tarixiy dalil | NOT TESTED — native full-page zoom |
| Ekran o‘quvchi, focus va xato e’loni | Native details Enter/Space, Tab chiqishi PASS | NOT TESTED — NVDA/VoiceOver, browser va natija |
| Sertifikat print/PDF | DC5 screen-only override kontrakti | NOT TESTED — print dialogi, sahifa bo‘linishi, rang |
| Telegram host va vendor editor | Inert nusxa faqat tashqi ko‘rinish | NOT TESTED — real adapter/host |
| Production owner/auth/DB/flag/cache va consumerlar | Lokal service/fixture dalili | OPEN — DC4/DC5 real port |

Qabul yozuvi uchun: sana, owner, variant/qiymatlar, qurilma/OS/browser,
ko‘rilgan sahifa, natija va kerakli tuzatish. Hozir owner nomidan hech bir
band yopilmagan. Native automation bu sessiyada mavjud emas; viewport
emulyatsiyasi qurilma qabuli sifatida belgilanmadi. Oldingi UX/DATA/RULE va
G3/G4/release bandlari saqlanadi.

## Ushbu bosqich tekshiruvlari

Trial ichida env-file off, Gemini/Telegram keys bo‘sh:

- `../../venv/Scripts/python.exe manage.py check`: **0 issue**.
- `../../venv/Scripts/python.exe manage.py test tests.test_design tests.test_design_consumers tests.test_design_release --verbosity 0`:
  **26 PASS**, 1.041s.
- PowerShell orqali `tests/design*.test.mjs` kengaytirilib `node --test`:
  **35 PASS**, 168.2463ms.

Bu kichik template/CSS va katalog o‘zgarishi uchun tegishli suite.
DC5dagi **907 Django / 281 Node** full natijalari tarixiy; bu bosqichda
full suite qayta yugurtirildi deb hisoblanmaydi.

Alohida loopback `8089` serverda: Enter/Space yo‘riqnomani ochib/yopdi,
Tab keyingi presetga o‘tdi. 24px draft reload bilan saqlandi; v0 → publish v1
→ rollback v2 oqimida draft o‘zgarmadi. Soft preset tasdig‘idan keyin
button16/card24/dialog24. Oq matn 8 ta kontrast xatosini keltirdi va save
bloklandi; tuzatishdan so‘ng 68 qoida o‘tdi. Bu agent sinovi, owner qabuli emas.

6 consumer × 2 mode × 2 width = **24 oldin/keyin juftlik (48 frame)**;
actual 320/1280, mode mos, root overflow 0. Yo‘riqnoma ochiq holda
320/390/768/1280 editor: overflow 0, 8 qadam, summary 44px.
Desktop/mobile screenshotlar ko‘rildi; vaqtinchalik viewport qaytarildi.

DC6 test tabining captured console error/warn soni **0**. DC5dagi 32 ta
source URL/stack’siz MutationObserver xabarining manbasi hali aniqlanmagan;
yangi tabda takrorlanmasligi eski muammo tuzatildi degani emas.

`evidence/dc6-browser.json`, `dc6-coverage.json`, `dc6-desktop.jpg`,
`dc6-mobile.jpg`, `dc6-design-tests.log`, `dc6-node-tests.log` lokal saqlanadi.
Manifestdagi 142 HTML va provenance’dagi 228 input hash tekshiriladi.
Snapshot rebuild fixture vaqt/IDlarini yangilashi mumkin; eski DC5 dalili
va Packet89 o‘zgartirilmadi.

## Tiklash tartibi va amaliy sinov

`playground/Eleventh Trial/checkpoints/packet-90-20261010-105837.zip` — **880 fayl**, har ZIP entry va tiklangan fayl
baytlari tekshirildi. SHA256 **`BED668B61AE8FBBDC45656DA3513A4C3545098E9B318658FAB739B1FABDEDE5E`**.

1. Arxiv SHA256ini tekshiring. Repo checkout va mavjud Python venv kerak;
   bu mustaqil distributiv yoki offsite backup emas. Asosiy repo tayanchi: `1623f4a`.
2. Bo‘sh katalogni repo ichida ikki daraja chuqurlikda yarating, masalan
   `.tools/design-dc6-recovery` yoki `playground/Recovery90`. Mavjud trialni
   ustidan yozmang. Env/cache/checkpoints/server loglari ZIP ichida yo‘q.
3. ZIPni shu katalogga ochib, barcha entry hashlarini solishtiring.
4. Shu katalogdan repo `venv/Scripts/python.exe` bilan yuqoridagi design
   testlarini kalitlar bo‘sh holatda yugurting. Zarur bo‘lsa alohida localhost
   portda ko‘ring; haqiqiy preview sessiyasini qayta ishga tushirmang.

Dastlab `.tools/design-dc6/restore-packet-90` chuqurligi bilan sinov
`core/settings.py` topilmagani uchun to‘xtadi. Mavjud `blog_rich.py` repo
ildizini ota katalogdan hisoblaydi; environment/kalit yuklanmadi.
Mos chuqurlikdagi `.tools/design-dc6-recovery`ga tiklangach **26 test PASS,
1.092s**, system check 0. Source kodi yoki test yumshatilmadi. Bu tiklash
shu repo/venvga bog‘liqligini aniq ko‘rsatadi. Log: `.tools/design-dc6/restore-tests.log`.

Packet89 saqlandi, ZIP va 26 oldingi source hash tekshirildi. Source va
checkpoint Git-ignored, force-add/upload yo‘q; tracked PR faqat dalil va
reja. Remote CI ignored implementationni ishga tushirmaydi.

## Source fingerprintlar

CRLF → LF SHA256; Eleventh Trialga nisbiy. Qabuldan keyingi source o‘zgarishi
tegishli sinov va yangi checkpoint talab qiladi.

| Fayl | SHA256 |
|---|---|
| `prototype/contracts/design_catalog.json` | `cfc28ae8513b5b4d6835b1b9392d4c849f1912452022de519258f24bd7f7d74e` |
| `prototype/preview/design.py` | `133564b1f925006be693ae705d361e05b2c056b184832fd79568a1a9f50fccff` |
| `prototype/preview/urls.py` | `5ff8c8b002ba5ee08fdfc390e6689818b521b9196a7404bb42b74e3d76aefeda` |
| `prototype/templates/design/studio.html` | `518a126b395eb0428312d73753e8c0c1969e4e9f4a62f3738cc08317ebd5372e` |
| `prototype/templates/design/frame.html` | `5bf290245092f4f366d71ee6d1f67e3851aeaed5a263f80049632a4316455c53` |
| `prototype/static/js/design_model.mjs` | `29a15e2c4f365ee137a22f4cf5950289790b85d572262a16ca3d638b9ea24f67` |
| `prototype/static/js/design_studio.mjs` | `08476fe0540580590e91e19d7589569b96815ccf072e336e173e1bdfaa359f28` |
| `prototype/static/css/design_studio.css` | `32a3f78972027543492cc7fe491c2ad720e0339c5979e7f3781a33f58e02b7e7` |
| `prototype/static/css/design_preview.css` | `d7ae8e0b87c83eb0d27b561d673cf3a7607a097b75040079fe27f174acd82566` |
| `tests/test_design.py` | `1d7b9f576a4dcb9d3ef7983edb34512105a38eaa0196e80b9965bd5f084d1c18` |
| `tests/design_model.test.mjs` | `14271502d613dc97a738f66ce6e8c788951b45472850574470c094a964b5ae02` |
| `tests/design_validation.test.mjs` | `e5c5c8c890bdd04f1987df6c27554ed0b04471b025a5f5729ee2f7433b3a2755` |
| `prototype/preview/state.py` | `5200a46b667283bc48141af3664788d76430cdb7397d882bea11aff6be6275b4` |
| `prototype/preview/design_release.py` | `d203fc3b8f857d2f8965ca0c02f6c66536898424a1a25f366884da394a3eb15c` |
| `prototype/preview/design_validation.py` | `7b57842b32b8aee8523d8480157ea92b3e5a5d01c8964a630475841027a69fb1` |
| `prototype/static/js/design_release.mjs` | `c487f199704861082801282a799247e06d3e5b5d7103f663397d7ae5d9f4bd58` |
| `prototype/static/js/design_release_ui.mjs` | `281708239d131583d9c4d90fccdf738a26e009f2075cdd47d3a0968a16a7ca16` |
| `tests/test_design_release.py` | `8d7a19f5b55baaedc1211da70b10c2e7ec3c65cf0b13cd82bd9960d0a89ced64` |
| `tests/design_release.test.mjs` | `9c8105f5bd8098193e4b017a9963c1312daec5f8d8a54bd3b0d4d5797096b77a` |
| `prototype/preview/design_consumers.py` | `29df35ffcaf9c2257016401b43d2dc28c3ed0db4330676a098fe1de9c2f49355` |
| `prototype/static/css/design_consumers.css` | `ee97de53eadc9c2cf48ce35e6605fceedf29fb05c6ee492445e0cd218b989d40` |
| `prototype/static/css/design_runtime.css` | `31e371418f80aace2f2a2d6c6ee7ac47550dac6e0026cf43ae7f5065f6e58491` |
| `tests/test_design_consumers.py` | `bdd5e2389c2f37e115d9eff7b7a4ef50f16c017e31397712215489248380a17e` |
| `tools/build_design_snapshots.py` | `f526194e40c7865e79485831df616c9c451dabdca639f2fce9cf8f98c12edf2a` |
| `prototype/design_snapshots/manifest.json` | `e8f6f6b7f685b0fbe72aa48b99fbbc7d3cd6fa373c556d2e8f32b2b3b9187b84` |
| `prototype/design_snapshots/provenance.json` | `54ef251977da31039c419c3cfc7869c3db8a0428b503eb4b12bdc59a74777988` |
