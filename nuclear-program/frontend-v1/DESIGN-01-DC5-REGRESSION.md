# DESIGN-01 DC5 — consumer regressiyasi

**Tarixiy snapshot:** quyidagi hashlar Packet89ga tegishli. Joriy source
va qabul holati [DC6 hisobotida](DESIGN-01-DC6-ACCEPTANCE.md).

2026-10-10. Owner beshinchi bosqichni boshlashni topshirdi.
Lokal consumer preview va regressiya qurildi. Bu production renderer,
native device yoki butun sayt WCAG qabuli emas.

## Admission

EXPERIMENT — production canonical state yozmaydi. Outcome: owner dizaynni
mavjud sahifa renderlarida taqqoslaydi; faqat7sintetik namunaga tayanmaydi.
KPI: xaritadagi har lokal route uchun snapshot yoki aniq istisno; tekshirilgan
viewportlarda tashqi overflow0. Writer DC4 release service bo‘lib qoladi.
DC5 faqat inert, build vaqtida olingan sintetik renderlarni iste’mol qiladi.
Script/form/navigation olib tashlanadi, parent iframe sandbox saqlanadi.
Failure: unknown snapshot404, statik default; Packet88 recovery saqlanadi.
Owner yuki: bitta ustaxonada sahifa tanlash va before/after. Real auth/DB,
flag/cache, native/AT, production legacy/Mini host va AWS alohida ochiq.

## Mavjud sahifalarni tekshirish

Studio tanlovida7komponent namunasi yoniga142inert nusxa qo‘shildi:
existing139route va3diagnostic error. Ulardan137ta ko‘rinish dizaynni oladi;
5tizim/xato sahifasi statik qoladi.137consumer75template identity’ni,
statiklar bilan jami80template identity’ni qamraydi. Existing registry
139route/77page/213action o‘zgarmadi. F20 studio shu registrydan tashqarida.

`tools/build_design_snapshots.py` alohida processda preview.settings va
sintetik fixturelarni ishlatadi. Real server sessioniga ulanmaydi. Kutubxona
48–50 va receipt31 yozuvlari existing local create/submit/verify oqimlari
orqali yaratiladi: normal/pending/success render olinadi. Dastlabki missing
record404 nusxalari final qamrovga normal sahifa sifatida qo‘shilmagan;
yozuv yaratilgach shu5route qayta tekshirilgan.

Runtime `GET /_preview/design/consumer/<key>/` faqat manifestdagi statik
HTMLni o‘qiydi. Yangi writer/domain dispatch yo‘q; POST405, unknown404,
no-store va existing iframe sandbox `allow-same-origin` saqlangan.
Script, form, iframe, event handler, inline style, redirect va tashqi
asset URLlar olib tashlanadi. Anchor styling qoladi, href yo‘q. Hidden
CSRF input va password value chiqarilmaydi. Snapshot native controlning
ko‘rinishini saqlaydi; hech qanday to‘lov/message/AI yuborish bajarmaydi.

`design_snapshots/manifest.json` har HTMLning SHA256ini, `provenance.json`
renderer Python/template/fixture/registry manbalarining normalizatsiyalangan
hashini saqlaydi. Input o‘zgarsa provenance testi yiqiladi; qayta build kerak.
Dynamic timestamp/ID fixture dalili, production foydalanuvchi ma’lumoti emas.

## DC1 oilalari qamrovi

| Oila | Nusxa soni | Qabul chegarasi |
|---|---:|---|
| F01 Public/blog/SIT |15| Lokal render; real legacy SIT alohida |
| F02 Auth |7| Static invalid/ready markup; haqiqiy login/native keyboard emas |
| F03 Dashboard/kurslar |2| Learner shell va karta/progress |
| F04 Dars/material |2| Render; fayl ichki kontenti bo‘yalmaydi |
| F05 Human chat |2| Bubble/composer; live message va keyboard emas |
| F06 AI chat |2| Sintetik javob; provider chaqirilmaydi |
| F07 Profil/hisob |2| Forma/avatar konteyneri |
| F08 Settings |3| Tab/field/confirmation markup |
| F09 Records/help |6| Jadval, list va bo‘sh joylashuv |
| F10 Certificate |2| Screen; print stylesheet saqlanadi, print dialogi ochiq |
| F11 Teacher/davomat/review |9| Teacher shell; real legacy davomat porti ochiq |
| F12 Course/lesson editor |9| Surrounding forma; vendor editor JS o‘chirilgan |
| F13 Library |12| Created48–50 ham; file ichki ko‘rinishi istisno |
| F14 Checkout/receipt |4| Receipt31 pending va verified sintetik render |
| F15 Exam |4| Exam-focus shell; timer/real attempt yozmaydi |
| F16 Classbook preparation |7| Forma/playbook |
| F17 Classbook live/results |8| Live-session shell; socket/reveal bajarilmaydi |
| F18 Owner/blog/SIT/control |36| Lokal backoffice; real legacy port emas |
| F19 Mini App |5| Lokal mini shell; Telegram chrome/SDK ishlamaydi |
| F20 Design studio |Alohida| Qoralama o‘z boshqaruv panelini qayta bo‘yamaydi |
| F21 Tizim/error |5| Maintenance/offline/403/404/500; statik default |

Har route/path/template/source hash: lokal `evidence/dc5-coverage.json`.

## Komponentlar va tuzatishlar

DC2/DC3dagi C01–C22 rol xaritasi saqlangan. Umumiy button/field/card/
dialog/badge/avatar/table/text rang va geometriyasi existing classlarda
ishlaydi. DC5 adapter nav/sidebar/header, actual chat bubble/composer,
content/reading width va dialog/drawer widthni actual snapshot classlariga
bog‘laydi. Shared tokens/base/components/shell CSS o‘zgartirilmagan.

- Blank card padding/density asl sahifa paddingini saqlaydi. Explicit
  qiymat umumiy cardga beriladi; chatning tashqi karta ramkasi0paddingda,
  bubble/composer o‘z rollarida qoladi.
- Blank dialog/drawer eni existing layoutni saqlaydi; explicit dialog
  eni viewportdan oshmaydigan max-width bilan olinadi.
- 200% text/spacingda chat header va send tugmasi qatorga sig‘adi;
  compact composer padding bounded. Mini header actionlari yangi qatorga o‘tadi.
- Native input (auth)10px, button24px, card28px, dialog32px,
  chat bubble20px mustaqil computed-style dalili bor. Chat composer8px
  bo‘lib qoladi: oddiy field radiusi composer rolini almashtirmaydi.

C08 nav/tabs, C13table va C20rich contentda ichki scroll bo‘lishi mumkin;
root overflow0 ichki scrolling yoki barcha hidden dialog holatlari PASS
degani emas. C17 SVG geometriyasi o‘zgarmaydi; currentColor meros olinadi.
C12loading/skeleton live transitioni bu statik nusxada ishlamaydi.

## Print, vendor va fallback

Typed override consumer uchun CSSOMdagi `@media screen { :root {} }`ga
yoziladi; root inline palette printni bosmaydi. Adapter CSS screen-only.
Existing certificate print rules va statik print palette saqlangan.
Bu **source contract testi**, OS print dialogi/PDF paginatsiyasi PASS emas.

X01 print/PDF, X02 CKEditor/Jazzmin/native picker, X04 Telegram host,
X05/X06 production legacy rendererlar — constrained, real qabul ochiq.
X03bitmap/audio/video/download va X09JSON/action/socket — ichki kontentga
design tatbiq etilmaydi. X07canvas/JS chizmalar snapshotda ishlamaydi;
CSS progress va SVG currentColor ko‘rinadi. X08minimal500/offline statik
default; offline cache kafolati yo‘q. X10brend/media egasi existing
SiteSettings/LandingPage bo‘lib qoladi; snapshot logosini almashtirmaydi.

## Dalil va qolgan ish

Eleventh Trialda env-file off, Gemini/Telegram keys bo‘sh:
`../../venv/Scripts/python.exe manage.py test --verbosity 0` — **907 PASS**,
368.243s; `manage.py check`0issue. Dastlabki906suite421.994s ham PASS;
228renderer input provenance testi qo‘shilgach yakuniy907suite yugurdi.
Focused14test4.410s PASS. PowerShell-expanded `tests/*.test.mjs` →
`node --test`: **281 PASS**,1156.8773ms. Studio `node --check` PASS.

Browser matritsasi:142nusxa × light/dark ×320/1280 =568case;
3preset ×9asosiy surface × light/dark ×390/768 =108case;
reading preset +200% root text/spacing ×9surface ×2mode ×320/1280 =36case.
Bu tanlangan kombinatsiyalar; barcha87field kombinatsiyalari yoki
production runtime dinamik holatlari exhaustive PASS deyilmaydi.
Native full-page zoom root text scale bilan tenglashtirilmaydi.

Yakuniy712frame holatida root scrollWidth≤clientWidth; expected viewport,
mode va barcha available `.c-button`24px radiusi baseline matritsada mos.
Editor320/390/768/1280 ham overflow0. Desktop/mobile screenshotlar ko‘rildi.
Browser jurnalida source URL/stack’siz bir xil MutationObserver xabari
32 marta qayd etilgan. Preview source ichida MutationObserver yo‘q; xabarning
manbasi aniqlanmagan. Console xatolari nol deb hisoblanmaydi. Dalil `evidence/dc5-browser.json`,
`dc5-desktop.jpg`, `dc5-mobile.jpg` va test loglarida.

Alohida design katalogi25action/20state/5URLpattern/2template +142snapshot.
Snapshotlar real route registriga yangi product sahifa sifatida qo‘shilmaydi.

DC5 lokal qamrov tugaydi; production mapped consumer regressioni DC4
real portdan keyin qaytarilishi shart. DC6 owner walkthrough/native/AT,
oldingi UX/DATA/RULE bandlari va real release gate ochiq.

## Lokal source fingerprintlar

CRLF → LF SHA256; Eleventh Trialga nisbiy. Manifest142HTML hashini, provenance228renderer input hashini saqlaydi.

| Fayl | SHA256 |
|---|---|
| `prototype/contracts/design_catalog.json` | `c74daef167ff4bd2465eb438d20d100268acc512b9e67b18966f5bb63c3542a9` |
| `prototype/preview/design.py` | `133564b1f925006be693ae705d361e05b2c056b184832fd79568a1a9f50fccff` |
| `prototype/preview/urls.py` | `5ff8c8b002ba5ee08fdfc390e6689818b521b9196a7404bb42b74e3d76aefeda` |
| `prototype/templates/design/studio.html` | `c8a8d6d5cfa1fb12f0f2fc494ea941d22dbb9b8ad7de56b4992f0a83d2a134bf` |
| `prototype/templates/design/frame.html` | `5bf290245092f4f366d71ee6d1f67e3851aeaed5a263f80049632a4316455c53` |
| `prototype/static/js/design_model.mjs` | `29a15e2c4f365ee137a22f4cf5950289790b85d572262a16ca3d638b9ea24f67` |
| `prototype/static/js/design_studio.mjs` | `08476fe0540580590e91e19d7589569b96815ccf072e336e173e1bdfaa359f28` |
| `prototype/static/css/design_studio.css` | `5fcab1e4e3c560cdb8b06ac2f4890408519701a5ed77e77e46e9ff6273e113c6` |
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
| `prototype/design_snapshots/manifest.json` | `87c4b16bbc71c0b67e290ee66aaf4f0533a4337f7e5b8923a8bc5b36cdb44c6a` |
| `prototype/design_snapshots/provenance.json` | `0305de791c4be5972c5147be047df30647f84471f7e5faa3f9819768e1d550b0` |

## Tiklash checkpointi

`playground/Eleventh Trial/checkpoints/packet-89-20261010-103457.zip` — **872 fayl**;
har entry SHA256 tekshirildi. ZIP SHA256 `F4BC1258883A9577065D2FFCC7F7D2163C05C2CE51A9189827E9F23756B49939`.
Packet88 saqlandi/hash matched;19oldingi source hash archive ichida tekshirildi.
26joriy source hash live/archive uchun,142HTML manifest va228input provenance
alohida tekshirildi. Shared token/base/components/shell CSS va registry baytlari
o‘zgarmagan. Env/cache/checkpoints va DC2–DC5 server loglari arxivga kirmaydi.
Source/arxiv ignored, force-add/upload yo‘q; same-disk recovery/offsite emas.
Remote CI ignored implementationni bajarmaydi; local dalil alohida.
