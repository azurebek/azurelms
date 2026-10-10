# DESIGN-01 DC2 — dizayn formasi, qoralama va preview

2026-10-10. Owner shu suhbatda ikkinchi bosqichni boshlashni topshirdi.
**Lokal Eleventh Trial implementatsiyasi; real design service yoki deploy emas.**
DC1dagi S01–S20 uchun forma, mustaqil komponent rollari, preset/qoralama va
yetti sintetik namunaning light/dark, desktop/mobile preview'i qurildi.
DC3 kontrast/typography qabuli, DC4 publish/history/rollback, DC5 barcha
consumerlar regressiyasi va DC6 owner/native qabul alohida ochiq.

[Asosiy reja](DESIGN-CUSTOMIZATION-PLAN.md) · [DC1 xaritasi](DESIGN-01-DC1-MAP.md)
· [Source inventari](DESIGN-01-DC1-SOURCE-INVENTORY.md).

## Admission va chegara

| Savol | DC2 qarori |
|---|---|
| Owner muammosi | Rang/font/shaklni qo‘lda CSS tahririsiz sinab, ta’sirini oldindan ko‘rish |
| Asosiy KPI | S01–S19dagi 87 maydon ta’rifi (31 rang × 2 mode + 56 umumiy = 118 qiymat) forma orqali o‘zgaradi; S20 qoralama/preset amallari; canonical write 0 |
| Admission | **EXPERIMENT — canonical state yozmaydi**; owner DC2ni oldingi yakuniy qabuldan oldin alohida boshlashni buyurdi |
| State va yagona writer | Faqat shu tabdagi typed design draft va sessionStorage; real Django model/service, existing brend/landing yoki global theme store yozilmaydi |
| Adapter | Lokal forma → typed compiler → sandbox ichidagi namuna; boshqa sahifalar iste’molchi bo‘lib ulanmagan |
| Operatsion yuk | Oldin/keyin solishtirish, nomlangan nusxa va bir amal bilan restore; production operatoriga yangi majburiyat yo‘q |
| Failure/rollback | Invalid qiymat oxirgi valid preview'ni saqlaydi; storage xatosi saqlandi deb ko‘rsatilmaydi; discard/reset tasdiqli. Tab/route yopish experimentni tark etadi; oldingi checkpoint saqlanadi |
| Flag/release | Real capability yoqilmagan, yangi enabled DB manbasi yo‘q. Real portdagi feature flag va owner-only writer DC4 kontraktiga tegishli |

Eski UX/DATA/RULE/native/owner bandlari yopilmaydi. Browserdagi sinov muhiti
belgisi haqiqiy owner authentication yoki production permission kafolati emas.
Preview server faqat loopbackda ishlaydi; `preview.settings` DBsiz va production
settings/env'dan mustaqil. Ishga tushirish: `playground/Eleventh Trial` ichida
`../../venv/Scripts/python.exe manage.py runserver 127.0.0.1:8088 --noreload`.
Ustaxona: `http://127.0.0.1:8088/_preview/design/`.

## Forma va qoralama kontrakti

Ranglar light/dark uchun alohida. Yangi semantik yoki komponent rangi uchun
**Umumiy rangdan olish** tanlovi mavjud: null override umumiy palitraga qaytadi.
Masalan, chat-own → action-soft, nav-active-bg → action-soft, warning-soft →
soft. Mustaqil rang tanlash shu rolni ajratadi; umumiy palitrani qayta yozmaydi.
Bo‘sh son va font/shadow uchun `inherit` asl token/CSS qiymatini saqlaydi.
Hozirgi doimiy z-index, breakpoint, reduced-motion va biznes qoidalari formaga
kiritilmagan. Yangi rol tokenlari faqat preview'da `--dc-*` namespace'da.

To‘rtta boshlang‘ich variant: Asl Azure, Yumshoq shakllar, Ixcham ish maydoni,
O‘qish uchun. Ular DC3 contrast-approved presetlar deb hisoblanmaydi.
Owner 1–60 belgili nom bilan tabda 8 tagacha shaxsiy nusxa saqlaydi; band nom
jimgina ustidan yozilmaydi, to‘lgan katalog eski variantni avtomatik o‘chirmaydi.
Bu limitlar lokal saqlash hajmi uchun experiment guard'i; production product
limiti sifatida qabul qilinmaydi.

- Tahrir faqat draftni o‘zgartiradi; saved snapshot va nomlangan preset nusxalari mustaqil.
- **Qoralamani saqlash** shu tabdagi sessionStorage'ga explicit yozadi; reload saved snapshotni tiklaydi. Unsaved draft avtomatik persist qilinmaydi.
- **Variant sifatida saqlash** joriy valid draft nusxasini saqlaydi, draftning saved holatini o‘zgartirmaydi.
- Apply/reset/restore/delete oldidan inline confirmation bor; cancel qiymatlarni saqlaydi.
- Saqlanmagan yoki invalid draft bilan sahifani tark etishda browser beforeunload guard'i bor. Browser bu dialogni har holatda ko‘rsatadi deb kafolat berilmaydi.
- Broken schema/JSON, nonfinite/off-step/bounds son, noma’lum field/choice yoki CSS/URL payload qabul qilinmaydi. Xato serverga yuborilmaydi.
- Saqlash kvotasi/ruxsati yetmasa draft xotirada qoladi va failure xabari chiqadi; saved snapshot oldinga surilmaydi.
- SessionStorage shu tab uchun; tab duplication browser tomonidan dastlabki nusxani ko‘chirishi mumkin. Real identity/RBAC, qurilmalararo saqlash va concurrent server draft emas.
- Publish, audit reason/confirmation, stale published revision, unknown publish readback, history va rollback endpointlari bu bosqichda mavjud emas.

## Preview va consumerlar

GET `/_preview/design/frame/<page>/` faqat quyidagi yetti allowlist qiymatini
oladi; noma’lum page 404, studio/frame POST 405. Frame'larda script, form,
tashqi asset yoki mutation havolasi yo‘q. Parent iframe sandbox'i faqat
`allow-same-origin`: script/form/popup vakolati berilmagan. Parent typed CSS
propertylarni frame ildiziga qo‘yadi; erkin CSS/HTML interpolation yo‘q.
Existing CSP o‘zgartirilmadi; barcha javoblar `no-store`.

| Namuna | Preview qamrovi | DC1 oilalari bilan munosabat |
|---|---|---|
| components | Button/field/choice/card/nav/badge/avatar/tabs/step/status, chat, dialog/drawer, shadow, loading va empty namunalari | C01–C19ning vakillik namunalari; real domain harakati emas |
| public | Hero, display, kurs kartasi, CTA, matn/form | F01 uchun vakillik namuna; real landing kontenti emas |
| learner | Dars kartasi, progress, CTA va o‘qish maydoni | F03/F04 uchun vakillik namuna |
| teacher | Stat kartalari, jadval, badge va amallar | Teacher guruhlari uchun vakillik namuna |
| owner | Boshqaruv statistikasi va navbat jadvali | F20 uchun vakillik namuna |
| chat | Own/other bubble va composer, matn/form | Messenger komponentlari; haqiqiy history/AI/message oqimi yo‘q |
| mini | Kurs/progress/formning kichik ekran namunasi | Mini uchun cheklangan vakillik; Telegram SDK/host shell yoki native keyboard qabuli emas |

Preview mode formdagi color edit mode'dan mustaqil. Kengliklar 320/390/768/1280;
ikkala frame bir xil width/mode oladi. Katta namuna tor panelda ataylab ichki
scroll maydonida ko‘rinadi; sahifaning o‘zi kengaymaydi. Before asl qiymatlarni,
after joriy draftni ko‘rsatadi; oddiy forma sahifasi o‘z rangini o‘zgartirmaydi.
DC5dagi barcha F oilalari, haqiqiy shell/route regressiyasi, print/PDF/vendor,
minimal 500 va Telegram host/user tema prioriteti hali tekshirilmagan.

## Fayllar va registr

Lokal, ignored `playground/Eleventh Trial/` ichida:

- `prototype/contracts/design_catalog.json`: yagona form/schema, defaults, preset, page va action katalogi.
- `prototype/preview/design.py`, `preview/urls.py`: ikki read-only URL pattern.
- `prototype/templates/design/{studio,frame}.html`: editor va inert specimen.
- `prototype/static/js/{design_model,design_studio}.mjs`: typed draft, saqlash va preview.
- `prototype/static/css/design_{studio,preview}.css`: editor va faqat frame uchun role adapter.
- `tests/test_design.py`, `tests/design_model.test.mjs`: chegara/invariant testlari.

Eski registry 0.84, 139 route/77 page/118 source nomi/213 action o‘zgarmaydi.
DESIGN-01 alohida kengaytma: 1 studio, 7 parametrli namuna, jami 2 yangi named
URL pattern va 2 template; real platforma source URL'iga mos deb yozilmagan.
Shared 73-token fayli va boshqa preview sahifalarining CSS/JS'i o‘zgarmadi.
Source Gitga force-add qilinmaydi; repo'da ushbu port kontrakti va dalil qoladi.

## Maydonlar kontrakti

Quyidagi numeric bounds DC2 preview guardlaridir; DC3 kontrast/font/zoom
qabulining o‘rnini bosmaydi. `null`/`inherit` asl qiymatga qaytadi. Ranglarda
`L` — light, `D` — dark. `--dc-*` faqat lokal specimen adapteriga tegishli.

| Guruh | Maydon | Turi / ruxsatli qiymat | Default / meros | CSS property |
|---|---|---|---|---|
| S01 | `canvas` — Sahifa foni | HEX #RRGGBB; L/D | L `#f6f8fb`; D `#111722` | `--az-canvas` |
| S01 | `surface` — Karta foni | HEX #RRGGBB; L/D | L `#ffffff`; D `#192231` | `--az-surface` |
| S01 | `side` — Yon menyu | HEX #RRGGBB; L/D | L `#ffffff`; D `#151d2a` | `--az-side` |
| S01 | `soft` — Ikkilamchi yuza | HEX #RRGGBB; L/D | L `#eef2f7`; D `#222e40` | `--az-soft` |
| S01 | `hero` — Katta kirish bloki | HEX #RRGGBB; L/D | L `#edf3ff`; D `#1c2b44` | `--az-hero` |
| S02 | `text` — Asosiy matn | HEX #RRGGBB; L/D | L `#172235`; D `#eef2f8` | `--az-text` |
| S02 | `muted` — Ikkilamchi matn | HEX #RRGGBB; L/D | L `#5d6a7e`; D `#aab7ca` | `--az-muted` |
| S02 | `faint` — Yordamchi matn | HEX #RRGGBB; L/D | L `#5f6c82`; D `#97a6bc` | `--az-faint` |
| S03 | `border` — Oddiy chegara | HEX #RRGGBB; L/D | L `#e3e8ef`; D `#2c394d` | `--az-border` |
| S03 | `action-border` — Tanlangan chegara | HEX #RRGGBB; L/D | L `#cfdefc`; D `#3b527c` | `--az-action-border` |
| S04 | `action` — Tugma va havola | HEX #RRGGBB; L/D | L `#1257e6`; D `#9bb8ff` | `--az-action` |
| S04 | `action-hover` — Ustiga olib borilganda | HEX #RRGGBB; L/D | L `#1048bf`; D `#b2c8ff` | `--az-action-hover` |
| S04 | `action-active` — Bosilganda | HEX #RRGGBB; L/D | null → `action-hover` | `--dc-action-active` |
| S04 | `on-action` — Tugma ustidagi matn | HEX #RRGGBB; L/D | L `#ffffff`; D `#12203c` | `--az-on-action` |
| S04 | `action-soft` — Tanlangan yumshoq fon | HEX #RRGGBB; L/D | L `#edf3ff`; D `#233552` | `--az-action-soft` |
| S05 | `success` — Muvaffaqiyat matni | HEX #RRGGBB; L/D | L `#22714f`; D `#93d7b4` | `--az-success` |
| S05 | `success-soft` — Muvaffaqiyat foni | HEX #RRGGBB; L/D | L `#eaf6ef`; D `#203c32` | `--az-success-soft` |
| S05 | `success-border` — Muvaffaqiyat chegarasi | HEX #RRGGBB; L/D | null → `success` | `--dc-success-border` |
| S05 | `danger` — Xato matni | HEX #RRGGBB; L/D | L `#b43b44`; D `#ffb2ba` | `--az-danger` |
| S05 | `danger-soft` — Xato foni | HEX #RRGGBB; L/D | L `#fceef0`; D `#432b34` | `--az-danger-soft` |
| S05 | `danger-border` — Xato chegarasi | HEX #RRGGBB; L/D | null → `danger` | `--dc-danger-border` |
| S05 | `warning` — Ogohlantirish matni | HEX #RRGGBB; L/D | L `#936410`; D `#eac488` | `--az-warning` |
| S05 | `warning-soft` — Ogohlantirish foni | HEX #RRGGBB; L/D | null → `soft` | `--dc-warning-soft` |
| S05 | `warning-border` — Ogohlantirish chegarasi | HEX #RRGGBB; L/D | null → `warning` | `--dc-warning-border` |
| S06 | `focus` — Fokus halqasi | HEX #RRGGBB; L/D | L `#1257e6`; D `#b2c8ff` | `--az-focus` |
| S06 | `disabled-text` — Faol bo‘lmagan matn | HEX #RRGGBB; L/D | null → `muted` | `--dc-disabled-text` |
| S06 | `disabled-bg` — Faol bo‘lmagan fon | HEX #RRGGBB; L/D | null → `soft` | `--dc-disabled-bg` |
| S06 | `disabled-border` — Faol bo‘lmagan chegara | HEX #RRGGBB; L/D | null → `border` | `--dc-disabled-border` |
| S07 | `overlay` — Qoplama qorayishi | 0…80 %; qadam 5 | null → original CSS | `--dc-overlay` |
| S07 | `card-shadow` — Karta soyasi | `inherit`, `none`, `soft`, `raised` | `inherit` → original CSS | `--dc-card-shadow` |
| S07 | `dialog-shadow` — Dialog soyasi | `inherit`, `none`, `soft`, `raised` | `inherit` → original CSS | `--dc-dialog-shadow` |
| S07 | `popover-shadow` — Suzuvchi panel soyasi | `inherit`, `none`, `soft`, `raised` | `inherit` → original CSS | `--dc-popover-shadow` |
| S08 | `body-font` — Asosiy matn | `inherit`, `system`, `humanist`, `serif`, `mono` | `inherit` → original CSS | `--az-font` |
| S08 | `heading-font` — Sarlavha | `inherit`, `system`, `humanist`, `serif`, `mono` | `inherit` → original CSS | `--dc-heading-font` |
| S08 | `code-font` — Kod | `inherit`, `system`, `humanist`, `serif`, `mono` | `inherit` → original CSS | `--az-mono` |
| S09 | `text-xs` — Izoh | 12…18 px; qadam 1 | null → original CSS | `--az-text-xs` |
| S09 | `text-sm` — Yorliq | 14…20 px; qadam 1 | null → original CSS | `--az-text-sm` |
| S09 | `text-md` — Asosiy | 16…22 px; qadam 1 | null → original CSS | `--az-text-md` |
| S09 | `text-lg` — Kichik sarlavha | 18…28 px; qadam 1 | null → original CSS | `--az-text-lg` |
| S09 | `text-xl` — Sarlavha | 20…36 px; qadam 1 | null → original CSS | `--az-text-xl` |
| S09 | `text-2xl` — Katta sarlavha | 24…44 px; qadam 1 | null → original CSS | `--az-text-2xl` |
| S09 | `text-title` — Sahifa nomi | 28…52 px; qadam 1 | null → original CSS | `--az-text-title` |
| S09 | `text-display` — Kirish sarlavhasi | 32…64 px; qadam 1 | null → original CSS | `--az-text-display` |
| S10 | `body-weight` — Matn qalinligi | 400…750 ; qadam 50 | null → original CSS | `--dc-body-weight` |
| S10 | `body-leading` — Matn satr oralig‘i | 1.2…2 ; qadam 0.05 | null → original CSS | `--dc-body-leading` |
| S10 | `heading-weight` — Sarlavha qalinligi | 400…750 ; qadam 50 | null → original CSS | `--dc-heading-weight` |
| S10 | `heading-leading` — Sarlavha satr oralig‘i | 1.2…2 ; qadam 0.05 | null → original CSS | `--dc-heading-leading` |
| S10 | `label-weight` — Yorliq qalinligi | 400…750 ; qadam 50 | null → original CSS | `--dc-label-weight` |
| S10 | `label-leading` — Yorliq satr oralig‘i | 1.2…2 ; qadam 0.05 | null → original CSS | `--dc-label-leading` |
| S11 | `tracking` — Sarlavha harf oralig‘i | -0.03…0.08 em; qadam 0.005 | null → original CSS | `--az-tracking` |
| S11 | `tracking-caps` — Kichik katta harflar | 0…0.16 em; qadam 0.01 | null → original CSS | `--az-tracking-caps` |
| S12 | `button-radius` — Burchak | 0…32 px; qadam 1 | null → original CSS | `--dc-button-radius` |
| S12 | `button-border` — Chegara | 1…3 px; qadam 1 | null → original CSS | `--dc-button-border` |
| S12 | `button-height` — Minimal balandlik | 44…64 px; qadam 1 | null → original CSS | `--dc-button-height` |
| S12 | `button-pad-x` — Yon ichki bo‘shliq | 8…32 px; qadam 1 | null → original CSS | `--dc-button-pad-x` |
| S12 | `button-pad-y` — Vertikal ichki bo‘shliq | 8…20 px; qadam 1 | null → original CSS | `--dc-button-pad-y` |
| S12 | `icon-size` — Icon tugma maydoni | 44…64 px; qadam 1 | null → original CSS | `--dc-icon-size` |
| S13 | `field-radius` — Input burchagi | 0…24 px; qadam 1 | null → original CSS | `--dc-field-radius` |
| S13 | `field-border` — Input chegarasi | 1…3 px; qadam 1 | null → original CSS | `--dc-field-border` |
| S13 | `field-pad` — Input ichki bo‘shlig‘i | 8…20 px; qadam 1 | null → original CSS | `--dc-field-pad` |
| S13 | `field-height` — Input minimal balandligi | 44…64 px; qadam 1 | null → original CSS | `--dc-field-height` |
| S13 | `choice-radius` — Tanlov burchagi | 0…24 px; qadam 1 | null → original CSS | `--dc-choice-radius` |
| S14 | `card-radius` — Burchak | 0…32 px; qadam 1 | null → original CSS | `--dc-card-radius` |
| S14 | `card-border` — Chegara | 1…3 px; qadam 1 | null → original CSS | `--dc-card-border` |
| S14 | `card-pad` — Ichki bo‘shliq | 12…40 px; qadam 1 | null → original CSS | `--dc-card-pad` |
| S15 | `dialog-radius` — Dialog burchagi | 0…32 px; qadam 1 | null → original CSS | `--dc-dialog-radius` |
| S15 | `dialog-border` — Dialog chegarasi | 1…3 px; qadam 1 | null → original CSS | `--dc-dialog-border` |
| S15 | `dialog-pad` — Dialog ichki bo‘shlig‘i | 16…40 px; qadam 1 | null → original CSS | `--dc-dialog-pad` |
| S15 | `dialog-width` — Dialog eni | 280…800 px; qadam 1 | null → original CSS | `--dc-dialog-width` |
| S15 | `drawer-width` — Yon panel eni | 240…420 px; qadam 1 | null → original CSS | `--dc-drawer-width` |
| S16 | `badge-radius` — Badge burchagi | 0…32 px; qadam 1 | null → original CSS | `--dc-badge-radius` |
| S16 | `avatar-size` — Avatar o‘lchami | 32…64 px; qadam 1 | null → original CSS | `--dc-avatar-size` |
| S16 | `table-pad` — Jadval vertikal bo‘shlig‘i | 8…24 px; qadam 1 | null → original CSS | `--dc-table-pad` |
| S17 | `nav-active-bg` — Faol bo‘lim foni | HEX #RRGGBB; L/D | null → `action-soft` | `--dc-nav-active-bg` |
| S17 | `nav-radius` — Bo‘lim burchagi | 0…24 px; qadam 1 | null → original CSS | `--dc-nav-radius` |
| S17 | `nav-pad` — Bo‘lim ichki bo‘shlig‘i | 8…20 px; qadam 1 | null → original CSS | `--dc-nav-pad` |
| S17 | `sidebar-width` — Yon menyu eni | 224…320 px; qadam 1 | null → original CSS | `--dc-sidebar-width` |
| S17 | `header-height` — Sarlavha minimal balandligi | 64…96 px; qadam 1 | null → original CSS | `--dc-header-height` |
| S18 | `chat-own` — O‘z xabari | HEX #RRGGBB; L/D | null → `action-soft` | `--dc-chat-own` |
| S18 | `chat-other` — Boshqa xabar | HEX #RRGGBB; L/D | null → `surface` | `--dc-chat-other` |
| S18 | `bubble-radius` — Xabar burchagi | 0…32 px; qadam 1 | null → original CSS | `--dc-bubble-radius` |
| S18 | `bubble-pad` — Xabar ichki bo‘shlig‘i | 8…24 px; qadam 1 | null → original CSS | `--dc-bubble-pad` |
| S18 | `composer-radius` — Yozish maydoni burchagi | 0…24 px; qadam 1 | null → original CSS | `--dc-composer-radius` |
| S18 | `composer-pad` — Yozish maydoni ichki bo‘shlig‘i | 8…20 px; qadam 1 | null → original CSS | `--dc-composer-pad` |
| S19 | `density` — Zichlik | `inherit`, `compact`, `comfortable`, `spacious` | `inherit` → original CSS | `--dc-density` |
| S19 | `content-width` — Kontent maksimal eni | 720…1440 px; qadam 1 | null → original CSS | `--dc-content-width` |
| S19 | `reading-width` — O‘qish maksimal eni | 480…880 px; qadam 1 | null → original CSS | `--dc-reading-width` |

S20 qiymat maydoni emas: yuqorida bayon qilingan draft/preset saqlash,
qo‘llash, qaytarish va o‘chirish amallari. Publish amali hali yo‘q.

## Tekshiruv

Buyruqlar `playground/Eleventh Trial` ichida; `AZURELMS_SKIP_ENV_FILE=1`,
`GEMINI_API_KEY=''`, `TELEGRAM_BOT_TOKEN=''`; real DB/provider chaqirilmaydi.

- `../../venv/Scripts/python.exe manage.py check`: 0 issue.
- `../../venv/Scripts/python.exe manage.py test tests --verbosity 0`:
  **888 PASS**, 347.001s. Birinchi yugurishda 2 yangi CSS compatibility testi
  yiqildi; raw overlay rangi existing tokenga qaytarildi va yangi rollar
  `--dc-*` bilan ajratildi. Tegishli 9 test 2.808s PASS, keyin to‘liq suite qayta PASS.
- `$tests = @(Get-ChildItem tests/*.test.mjs | ForEach-Object FullName); node --test @tests`:
  **261 PASS**, 1341.1079ms. Yangi 15 model testi inheritance, mode isolation,
  immutable preset, invalid payload, storage corruption/quota va duplicate/capni tekshiradi.
- `node --check prototype/static/js/design_studio.mjs`: PASS.
- Catalog/document comparison: 87 maydon hujjatda bor; har bir CSS property
  original foundation yoki yangi preview CSSda consumerga ega; relative linklar PASS.
- IAB: **56 frame case** (7 page × light/dark × 320/390/768/1280), haqiqiy
  page ID, mode va effective width tekshirildi; root overflow va duplicate ID 0.
  **4 editor viewport** ham overflow0. Keng canvas ichki scroll'i ataylab qoladi.
- Browser: button 24px bo‘lganda input/nav 8px, card/chat 14px qoladi;
  card 0px bo‘lganda chat 14px qoladi. Existing profilning button/input/card
  defaultlari 8/8/14px. Yangi tab 8px defaultni oladi, boshqa tab draftini olmaydi.
- Save→reload, named preset save, apply/cancel, restore/reset, delete/cancel,
  Enter bilan yashirin save yo‘qligi, invalid20px→correct48px/error clearing,
  dark/light ajralishi, heading fontining bodydan ajralishi browserda tekshirildi.
- Global action-soft→chat own inheritance, explicit own override, inheritga
  qaytish ranglari computed-style orqali tekshirildi. Parent editor va existing
  profile theme tanlovi saqlanadi; global theme storage'ga writer yo‘q.
- Screenshotlar: lokal `evidence/dc2-desktop.jpg`, `dc2-mobile-preview.jpg`;
  ikkisi ham ko‘rildi. `dc2-responsive.json` o‘lchovlarni saqlaydi.
- IAB console capture'da source URL/stack berilmagan 4 ta `MutationObserver.observe`
  xabari saqlandi (`dc2-browser-console.json`). DC2 modullarida observer yo‘q;
  kelib chiqishi aniqlanmagan, shuning uchun “console 0” da’vo qilinmaydi.
  Functional oqimlarda app xatosi/CSP rad etilishi kuzatilmadi. Native/AT va
  boshqa browser engine qabuli hali OPEN.

DC2 lokal bosqichi tayyor; real publish yoki umumiy DESIGN-01 completion emas.

## Lokal source fingerprintlar

CRLF → LF normalizatsiyasidan keyingi SHA256; yo‘llar Eleventh Trialga nisbiy.

| Fayl | SHA256 |
|---|---|
| `prototype/contracts/design_catalog.json` | `ad4c7d327fcc23ac32f8d86f36b226e8abe65508a959e930f453f23372f3dfb5` |
| `prototype/preview/design.py` | `70ac826e848f7e1366a32f6a92bd7369f6a0ea8b69ed7863190d9dacbd227985` |
| `prototype/preview/urls.py` | `6cc3c6017c3fb22e95b32f27993dcd0403bbb53b81062dfa59ba8cef86b05382` |
| `prototype/templates/design/studio.html` | `a7a4b5bf502af33ef29f28a352cea4cfbeb1b53a09f03ec1d6c64c3283202a5c` |
| `prototype/templates/design/frame.html` | `d139349fdb89893c358af32631c07ac93422559e55b5422f1d3905ba822816ab` |
| `prototype/static/js/design_model.mjs` | `326b819c23be2f0e7f0401b50c9d45600c79ac1e65ed4fd27be90df29c3afcba` |
| `prototype/static/js/design_studio.mjs` | `c1698b25309330d0214495c195c2b6bdaac06b9ad4880501c4ee3f9ec5467c8c` |
| `prototype/static/css/design_studio.css` | `d6714b17d5d5278eb8a38390a751fccd9813fefe9070619c5e866ba34b9f1acc` |
| `prototype/static/css/design_preview.css` | `bd5043a418889db13968ea37241ba6a8089e9db17f02bbd0d8e9e465180406e0` |
| `tests/test_design.py` | `1d7b9f576a4dcb9d3ef7983edb34512105a38eaa0196e80b9965bd5f084d1c18` |
| `tests/design_model.test.mjs` | `14271502d613dc97a738f66ce6e8c788951b45472850574470c094a964b5ae02` |

## Tiklash checkpointi

`playground/Eleventh Trial/checkpoints/packet-86-20261010-084702.zip` — **696 fayl**, har entry
asl nusxaga SHA256 bilan tekshirildi. ZIP SHA256:
`6CDC33773378F9E8AF7F802411F63FEA276D1805FDCFBB318F863CA321245A23`.
Packet85 saqlandi va oldingi SHA256 bilan mosligi tekshirildi. Faqat existing
`preview/urls.py` va lokal README yangilandi; qolgan implementatsiya yangi
design fayllarida. Archive server log/cache/checkpoint papkasi va indeksni
olmaydi. Bu bir diskdagi recovery; offsite backup emas. Source/arxiv upload
qilinmadi; CI repo hujjatlarini va existing runtime'ni tekshiradi, ignored
lokal DC2 implementatsiyasini qayta ishga tushirmaydi.
