# DESIGN-01 DC3 — kontrast va o‘qish chegaralari

**Tarixiy snapshot:** quyidagi12source hash Packet87ga tegishli.
Joriy lokal source [DC4](DESIGN-01-DC4-RELEASE.md)da; umumiy validation policy
shu bosqichda catalogga chiqarilgan. DC3 archive hashlar alohida tekshiriladi.

2026-10-10. Owner uchinchi bosqichni boshlashni topshirdi.
DC2ning lokal Eleventh Trial ustaxonasi kengaytiriladi; real service emas.

## Admission

| Savol | Qaror |
|---|---|
| Outcome / KPI | O‘qilmaydigan rang juftligi yoki buzilgan shrift iyerarxiyasi saqlanmaydi; tekshirilgan namunalarda tashqi gorizontal overflow 0 |
| Admission | EXPERIMENT, ownerning DC3 topshirig‘i; oldingi yakuniy qabulni yopmaydi |
| Canonical state / adapter | DC2 typed tab draft → inert iframe; DB, brend, global tema va domain writer o‘zgarmaydi |
| Owner yuki | Muammo, sabab, ranglar va kerakli nisbat forma yonida; ixtiyoriy matn stress rejimi |
| Failure / rollback | Xato draft faqat previewda; saqlash/preset guard; buzilgan eski store ustidan avtomatik yozish yo‘q; Packet86 saqlanadi |
| Release | Lokal source ignored; real enforcement DC4, barcha consumerlar DC5, native/owner DC6 |

## Tekshiruv asosi

Matn uchun konservativ 4.5:1 (sarlavha ham), funksional chegara/focus/progress
uchun 3:1. Qaror yaxlitlanmagan nisbatdan olinadi. Disabled va dekorativ
chegaralar alohida istisno; ularni PASS matn sifatida sanamaymiz.
[W3C kontrast](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html),
[W3C non-text](https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html).

200% matn kattalashishi, 320 CSS px reflow, uzun o‘zbek/turk matni va birga
qo‘llangan satr 1.5 / paragraf 2em / harf .12em / so‘z .16em sinovlari.
[W3C resize](https://www.w3.org/WAI/WCAG22/Understanding/resize-text.html),
[W3C spacing](https://www.w3.org/WAI/WCAG22/Understanding/text-spacing.html).
Bu lokal namuna tekshiruvi; butun platformaning WCAG sertifikati emas.

## Deterministik gate

`design_model.mjs` bitta sRGB luminance hisobidan foydalanadi; 0.04045
linearizatsiya chegarasi, (yorug‘+.05)/(qorong‘i+.05). Nisbat ekranda pastga
ikki kasrgacha qisqartiriladi, PASS uchun yaxlitlanmaydi. 30 juftlik × 2 tema
+ 7 shrift iyerarxiyasi + 1 satr oralig‘i = **68 qoida**. Aktiv preview temasi
boshqa bo‘lsa ham ikkala palitra tekshiriladi. Null override merosi yechiladi.

| Matn / fon | Minimal nisbat |
|---|---|
| text / canvas, surface, side, soft, hero, action-soft, chat-own, chat-other | 4.5 |
| muted / canvas, surface, soft, hero; faint / surface | 4.5 |
| action / surface, action-soft, nav-active-bg | 4.5 |
| on-action / action, action-hover, action-active | 4.5 |
| success / success-soft; danger / danger-soft; warning / warning-soft | 4.5 |
| muted / surface (input, tanlov va secondary button chegarasi); danger / surface (invalid input); action / soft (progress) | 3 |
| focus / canvas, surface, hero, action-soft, nav-active-bg | 3 |

Input, secondary button va tanlov chegarasi `muted`dan olinadi; checked
tanlov `action`dan, invalid input `danger`dan. Umumiy `border` karta/jadval
uchun dekorativ qoladi. DC2dagi inputning xira dekorativ chegara merosi
shu lokal adapterda tuzatildi; global CSS/tokenlar o‘zgarmadi.
Statusda ikon/belgi va matn bor; status dekorativ border override’lari
gate’da emas. Disabled opacity/ranglar ham WCAG incidental istisnosi;
ularning ko‘rinishi avtomatik tasdiqlangan deb aytilmaydi. Native select/choice
popup va OS ranglari bu CSS projectionni to‘liq olishi kafolatlanmaydi.

Schema-valid, lekin kontrasti/hierarchy’i noto‘g‘ri draft tahrir va previewda
qoladi. **Draft save va named preset save yopiladi**; har muammodan tegishli
tema/maydonga o‘tish tugmasi bor. Strict schema-invalid input avvalgidek
oxirgi valid previewni saqlaydi. `assertSafe` faqat UI disable emas:
`savePreset`, `writeStore` va `parseStore`da ham ishlaydi. Unsafe eski saved
yoki preset bo‘lsa store qabul qilinmaydi; ochiq xabar bilan factory default
ochiladi, eski raw storage avtomatik o‘chirilmaydi. Keyingi explicit save
uni almashtiradi. Real server authorization/mutation DC4 kontraktida qoladi.

## Typography, font va xavfsiz chegaralar

DC2ning **87 maydon / 118 qiymat** scheması saqlandi. 49 sonli maydonning
min/max/step diapazonlari DC2 field jadvalidagi kabi; endi kombinatsiya gate’i
ham bor. Guard’lar product sozlamasini yashirmaydi, xavfsizlik chegarasidir.

| Chegara | Dalil / qoida |
|---|---|
| Caption → label → body → h3 → h2 → katta sarlavha → title → display | O‘suvchi yoki teng o‘lcham; bo‘sh tokenlar ham effective qiymat bilan tekshiriladi |
| Bo‘sh typography | 12,14,16,18,22,28; title 28–36, display 36–48 px (16px rootdagi token diapazoni) |
| Matn o‘lchami | Formada 16px rootga nisbiy px ekvivalenti; compiler `/16 rem` chiqaradi, root/font resizega ergashadi |
| Body leading | Syntax 1.2–2 eski draftni tahrir qilish uchun; saqlash ≥1.5. Bu loyiha o‘qish siyosati, WCAGning default leading majburiyati deb yozilmaydi |
| Control height / icon target | Kamida44; bundan past raqam schema’da rad etiladi; min profil browserda ham ≥44 |
| Spacing/width/radius/border | DC2 bounds + min/max kombinatsiya sinovi; sidebar 30%dan oshmaydi, kontent siqilmaydi; dialog tabiiy balandlikda |
| Overflow | Button, badge, nav, uzun so‘z va composer wrap; jadvalda o‘z scroll konteyneri; bir qator inputning ichki scroll’i odatiy |

Tizim sans, Segoe UI, Georgia/Times New Roman, Consolas/Courier New va
inherited stack — **faqat qurilmada o‘rnatilgan font nomlari**, generic
fallback bilan. Font fayli ko‘chirilmaydi/tarqatilmaydi, tashqi URL,
`@font-face`, font CDN/cache/CSP istisnosi va download hajmi **0**.
Bu proprietary fontni self-host qilish litsenziyasi bor degani emas;
kelajakda font asset qo‘shilsa litsenziya/manba/hajm alohida gate bo‘ladi.
Qurilma/font versiyasiga qarab glyph/metrikalar farqlanadi. Generic fallback
toggle tarmoq fonti failure’ini emas, system fallback layoutini sinaydi.

## Lokal sinov matritsasi

| Profil | Sinov |
|---|---|
| Factory normal | 7 sahifa × 2 tema × 320/390/768/1280 =56 |
| Factory stress | 200% root text + uzun matn + barcha spacing + generic fallback + reduced-motion =56 |
| Barcha49 sonli maydon max | Shu stress sharoitida56 |
| Barcha49 sonli maydon min, body-leading1.5 | Shu stress sharoitida56;1.2 alohida rad etilgani tekshirildi |
| Font oilalari | 5 stack × body/heading/code,320px/200%/spacing/uzun matn:5 profil |
| Editor | 320/390/768/1280:4 viewport |

**224 frame holati + 5 font profil + 4 editor viewport**: tashqi overflow0.
Stress profillarda matn/button/card/badge/dialog/popover ichki overflow0;
normal profil root width tekshiruvi. Min/max — qo‘llab-quvvatlangan endpoint
kombinatsiyalari dalili; barcha mumkin bo‘lgan rang/font kombinatsiyalari
to‘liq vizual sinovdan o‘tdi deyilmaydi. Unit test har declared rang juftligi
va raqam endpointini alohida tekshiradi; ixtiyoriy draftni owner previewda
ham ko‘radi. 768px/200%da topilgan sidebar siqilishi va badge/popover wrap
nuqsoni tuzatilib, butun matritsa qayta o‘tdi.

32px bodyda real computed spacing: line48px, letter3.84px, word5.12px,
paragraph margin64px. Keyboard Tab bilan select `:focus-visible`ga o‘tdi;
outline/focus token bor. Reduced-motion fixture spinnerni `none` qildi;
existing OS `prefers-reduced-motion` qoidasi saqlangan. Haqiqiy OS toggle
yoki assistive technology walkthrough bu sessiyada bajarilmagan.

Oq fondagi oq text va yashirin dark palitradagi xato save’ni yopdi;
error-link to‘g‘ri edit-mode/maydonga fokus berdi, tuzatish save’ni ochdi.
Stress boshqaruvi draft/presetga kirmaydi va ikkala frame’ga bir xil ishlaydi.
Eski user tabi o‘zgartirilmay, sinov alohida tabda bajarildi.

Browser `evidence/dc3-browser.json`, `dc3-desktop.jpg`, `dc3-mobile.jpg`.
Yangi tabda URL/stack’siz 2 ta `MutationObserver.observe` xabari qayd etildi;
DC2da ham shunday kuzatilgan. Design modullarida observer yo‘q, lekin kelib
chiqishi isbotlanmagan: **console0 deb da’vo qilinmaydi**.

## Qabul chegarasi va keyingi bosqich

200% root text sinovi browserning native full-page zoomi emas. 320 CSS px
reflow tekshirildi; native 200/400% zoom, haqiqiy iPhone/Android, AT,
Telegram host, font glyph/performance va owner walkthrough DC6da tekshiriladi.
DC5 butun mapped consumerlar, print/PDF/vendor/minimal fallbackni qamraydi.
Publish/history/rollback va real canonical enforcement DC4da qoladi.
Mavjud73 shared token, global runtime va AWS o‘zgarmadi.

Existing registry0.84/139route/77page/213action o‘zgarmadi. Alohida DESIGN
katalogi:2 URL pattern,2template,**17action/11state**. Yangi6 local action:
scale, long-text, spacing, fallback, reduced-motion, validation.locate.
Yangi2 holat: unsafe-combination, stress-preview. DB/service migration0.

## Test natijalari

Eleventh Trial ichida `AZURELMS_SKIP_ENV_FILE=1`, `GEMINI_API_KEY=` va
`TELEGRAM_BOT_TOKEN=` bilan:

- `../../venv/Scripts/python.exe manage.py test --verbosity 0` — **888 PASS**,335.762s.
- `../../venv/Scripts/python.exe manage.py check` —0 issue.
- `tests/*.test.mjs` PowerShell array’ga kengaytirilib `node --test` — **272 PASS**,963.3623ms.
- Yangi `tests/design_validation.test.mjs`:11 test — luminance reference,
  har pairning equal-color failure’i, inherited rang, ikkala tema, save/read
  boundary, correction, hierarchy, rem, sonli endpoint, font allowlist va
  disabled/decorative istisnolari. Oldingi15 design model testi ham PASS.
- Ikki module `node --check` PASS. Focused9 Django PASS; birinchi CSS check
  repo ruxsat bermagan `!important` sabab fail bo‘ldi, selector specificity
  bilan tuzatilib focused va keyin full suite PASS.

Loglar: `evidence/dc3-django-tests.log`, `dc3-node-tests.log`.
Ignored local source/arxiv force-add yoki upload qilinmaydi. Remote CI
tracked repo hujjatlari va existing runtime’ni tekshiradi; u lokal DC3
implementatsiyasini ishga tushirmaydi. Quyidagi hash/checkpointlar shu
farqni aniq saqlaydi. DC2ning tarixiy11 source hash’i Packet86 ichida qayta
tekshirildi; ish boshlashdan oldin current fayllar ham aynan mos edi.

## Lokal source fingerprintlar

CRLF → LF normalizatsiyasidan keyingi SHA256; Eleventh Trialga nisbiy.

| Fayl | SHA256 |
|---|---|
| `prototype/contracts/design_catalog.json` | `65783c9953e5797754c65814f17d0dbdd840baa9b17823d18a11736bd11e56b9` |
| `prototype/preview/design.py` | `70ac826e848f7e1366a32f6a92bd7369f6a0ea8b69ed7863190d9dacbd227985` |
| `prototype/preview/urls.py` | `6cc3c6017c3fb22e95b32f27993dcd0403bbb53b81062dfa59ba8cef86b05382` |
| `prototype/templates/design/studio.html` | `2cc552778b30f9d592ec169f406a125f653a8aeb81dca1a498fa0390bc5df410` |
| `prototype/templates/design/frame.html` | `5bf290245092f4f366d71ee6d1f67e3851aeaed5a263f80049632a4316455c53` |
| `prototype/static/js/design_model.mjs` | `5fda2b5ec1f385d524a5ed4a0466c807b5cff498435f36942e230a73682fe94d` |
| `prototype/static/js/design_studio.mjs` | `16d39d611757a0f2c8d6362de34886222a82c9c22641ac90e1830ac5467c7428` |
| `prototype/static/css/design_studio.css` | `8846ccc36cd72e460f32f72fe405036dec48da5b0f896cf8d4bb276c93ccaedf` |
| `prototype/static/css/design_preview.css` | `d7ae8e0b87c83eb0d27b561d673cf3a7607a097b75040079fe27f174acd82566` |
| `tests/test_design.py` | `1d7b9f576a4dcb9d3ef7983edb34512105a38eaa0196e80b9965bd5f084d1c18` |
| `tests/design_model.test.mjs` | `14271502d613dc97a738f66ce6e8c788951b45472850574470c094a964b5ae02` |
| `tests/design_validation.test.mjs` | `cccd3cbe946c97ef3e8e82a600a2f88b0d2319cbe704e33168a1639cbaffc069` |

## Tiklash checkpointi

`playground/Eleventh Trial/checkpoints/packet-87-20261010-091817.zip` — **703 fayl**, har entry
SHA256 bilan asl nusxaga tekshirildi. ZIP SHA256:
`15D9D7EA66E6F75BEEACC5E930CC2B52C41FE34F7B9F7103378BEF8C40F69F1A`.
Packet86 saqlandi va hash mosligi tekshirildi. Shared tokens/base/components/
shell CSS va eski registry baytlari Packet86 bilan bir xil.
Archive env, cache, checkpoint papkasi/index va DC2/DC3 server loglarini
olmaydi. Source/arxiv ignored va upload qilinmagan; bu bir diskdagi recovery,
offsite backup emas. DC2 tarixiy11 hash va yangi DC3 12hash ajratilgan.
