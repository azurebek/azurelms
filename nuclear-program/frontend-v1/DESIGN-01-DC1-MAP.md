# DESIGN-01 / DC1 — sozlamalar, komponentlar va sahifalar xaritasi

2026-10-10. **DC1 — hujjat inventari tayyor; implementatsiya va vizual qabul emas.**
Tekshirilgan runtime bazasi: `ead7698`. Owner shu suhbatda DESIGN-01ning
birinchi bosqichini boshlashni topshirdi. Bu DC1ni oldingi UX qabulidan
oldin bajarishga ruxsat; [ochiq UX/DATA/RULE bandlari](FINAL-ACCEPTANCE-ISSUES.md)
yopilmadi. DC2–DC6, DB migratsiyasi, prototip paneli va deploy boshlanmadi.

[Asosiy reja](DESIGN-CUSTOMIZATION-PLAN.md) ·
[To‘liq token va URL dalili](DESIGN-01-DC1-SOURCE-INVENTORY.md).

## 1. Admission va o‘lchanadigan natija

| Savol | DC1 javobi |
|---|---|
| Owner muammosi | Rang/shrift/shaklni o‘zgartirish uchun qaysi sahifa va CSSga tegish kerakligi hozir tarqoq; noto‘g‘ri umumiy token boshqa komponentni ham o‘zgartiradi |
| Asosiy KPI | Kelajakdagi har ruxsatli sozlama uchun aniq source → komponent → consumer bog‘lanishi; inventarda egasiz sozlama qolmasligi |
| Canonical state | Hozir hech biri o‘zgarmaydi. Kelajakda yagona design version service; nom/schema DC4 dizaynida tasdiqlanadi |
| Adapterlar | Public, learner, teacher, owner web va Mini App; har biri faqat effective dizaynni iste’mol qiladi |
| Operatsion yuk | DC1 qo‘lda CSS qidirishni kamaytiradigan xarita beradi; keyingi panelda preview/publish/rollback bir oqim bo‘ladi |
| Failure/rollback | Hozir docs-only Git revert; kelajakda existing flag registry, o‘zgarmas versiyalar va statik fallback |
| Admission | **EXPERIMENT — canonical state yozmaydi**, faqat owner ruxsat bergan DC1 inventari. Butun capability uchun launch/post-launch release qarori bu hujjat bilan berilmaydi |

**Belgilar:** `mapped` — source va sozlama roli aniqlangan, lekin hali
dinamik boshqaruv ulanmagan; `constrained` — alohida adapter/refactor yoki
qabul kerak; `not applicable` — shu yuzaning o‘ziga dizayn sozlamasi tatbiq
etilmaydi. Hech biri browser PASS yoki production holatini anglatmaydi.
`S`, `C`, `F`, `X`, `G` IDlari shu DC1 hujjatiga tegishli; existing route,
action yoki component registry IDlarini almashtirmaydi.

## 2. Mavjud manbalar va yagona boshqaruv chegarasi

| Source | Hozirgi fakt | DC1 xulosasi |
|---|---|---|
| `static/frontend_v1/css/tokens.css` | 73 noyob `--az-*` token; light/dark, hujjat print override | Asosiy V1 dizayn poydevori; barcha 73 token ownerga ochilmaydi |
| `static/frontend_v1/css/{base,components,shell}.css` | Font/komponent/shell tokenlarni iste’mol qiladi; border, ayrim leading va opacity literal | Mustaqil komponent rollari chiqariladi; hozirgi ko‘rinish boshlang‘ich default bo‘ladi |
| `static/css/tokens.css`, `static/css/base.css` | Eski `--paper/--ink/--azure` palitrasi; body fonti literal | Legacy adapter va literal audit kerak; V1 tokenini o‘zgartirish yetmaydi |
| `static/css/sit.css`, `static/js/sit-theme.js` | Mustaqil palitra, `--sans/--mono`, `sit-theme` storage kaliti | Legacy SIT alohida constrained consumer |
| `static/css/miniapp.css`, `static/js/miniapp.js` | Eski `--paper/--ink/--azure` tokenlari, literal Inter fonti/geometriya; Telegram `colorScheme/themeChanged`, host header/background | Web palitrasi va Telegram host talablari alohida xaritalanadi |
| `frontend.models.SiteSettings`, `core/brand_forms.py` | Brend nomi, tagline, logo variantlari va favicon allaqachon canonical | Dizayn servisiga qayta ko‘chirilmaydi; existing brend komponenti ishlatiladi |
| `core/landing_forms.py`, `LandingPage`, `AuthPageSettings` | Kontent, media va mavjud sahifa sozlamalari | Matn/media tahriri shu yerda qoladi; global ko‘rinish qiymati ikki manbaga yozilmaydi |
| `core/views.py:backoffice_brand`, `core/audit.py` | Owner permission, reason/confirmation, audit, no-op namunasi | Publish uchun asos; mavjud brand formida to‘liq version/history/rollback bor deb olinmaydi |
| `static/frontend_v1/js/theme.js` | `az-v2-theme`, light/dark/system fallback, boshqa tab bilan sync | Owner palitrasi foydalanuvchi mode tanlovini almashtirmaydi |
| `playground/Eleventh Trial/prototype/` | Lokal sintetik preview; registry `0.84.0-checkout-clarity` | Faqat hujjat metama’lumoti o‘qildi; ignored source/fixture/assets Gitga qo‘shilmadi |

Rejalashtirilgan qiymat tartibi: **published version → mode palette →
component role → ruxsatli component override**. Component override bo‘sh
bo‘lsa umumiy rolga qaytadi. Sahifa ichidagi yashirin theme writer bo‘lmaydi.
Draft alohida owner previewda turadi; oddiy GET publish qilmaydi.

## 3. Sozlamalar katalogi

Quyidagi maydon oilalari **taklif qilingan UI/schema shartnomasi**.
Ular mavjud DB maydonlari emas. Har maydon typed qiymat oladi; tasodifiy
CSS, selector, tashqi URL yoki bajariladigan kod qabul qilinmaydi.
Raqamli min/maxlar bu inventarda yakuniy product qarori sifatida qotirilmaydi:
DC2da control shakli, DC3da dalilli chegaralar belgilanadi.

| ID / ownerga ko‘rinadigan guruh | Hozirgi V1 manba | Taklif etiladigan mustaqil qiymatlar | Consumer / tekshiruv |
|---|---|---|---|
| S01 Fon va yuzalar | `canvas,surface,side,soft,hero` | Har mode uchun sahifa/karta/sidebar/ikkilamchi/hero ranglari | C01,C05,C19; yuzadagi barcha matn juftliklari |
| S02 Matn | `text,muted,faint` | Asosiy/ikkilamchi/yordamchi matn ranglari | Barcha F oilalar; caption ham o‘qiladi |
| S03 Chegara | `border,action-border` | Oddiy/tanlangan control chegarasi | C01,C04,C05,C07,C13 |
| S04 Asosiy amal | `action,action-hover,on-action,action-soft` | Tugma/havola, ustiga olib borish, bosilgan/tanlangan holat, ustidagi matn; yangi active roli | C01,C09,C14,C22; barcha rang juftliklari |
| S05 Semantik holatlar | `success,success-soft,danger,danger-soft,warning` | Success/error/warning foreground/background/border; warning soft/border yetishmaydi | C03,C06,C07,C16; holat faqat rang bilan berilmaydi |
| S06 Fokus va disabled | `focus`; `base.css` focus; komponent opacity `.6`, chat `.5` | Focus rangi; disabled foreground/background/border roli | C01,C04,C09,C10,C14; fokus va disabled ma’nosi saqlanadi |
| S07 Overlay va soyalar | `overlay,shadow` | Modal qoplamasi; karta/dialog/popover uchun cheklangan soya presetlari | C05,C10,C14; matn kontrasti va qatlamlar |
| S08 Shrift oilalari | `font,mono`; heading bodydan meros | Body/heading/code mustaqil katalog tanlovi va fallback | C02,C12,C13,C18; O‘zbek/Turk glyph va yuklanmay qolish |
| S09 Matn iyerarxiyasi | `text-xs…text-2xl,text-title,text-display` | Caption/body/subheading/heading/display o‘lcham rollari | C02,C12,C19; zoom/reflow va uzun kontent |
| S10 Qalinlik va satr | `weight-medium,weight-bold,leading,leading-tight` | Body/heading/label vazni va satr oralig‘i | C01,C02,C04,C13; heading va button literal leading ham ko‘chiriladi |
| S11 Harf oralig‘i | `tracking,tracking-caps`; brand literal | Heading/eyebrow tracking; logo wordmark istisnosi | C02,C19; matn kesilmasligi |
| S12 Tugma | `radius-sm,control,space-2/3/4,button-min` | Button radius/border/height/padding, icon-button o‘lchami | C01; input/nav radiusiga yashirin ta’sir bo‘lmaydi |
| S13 Input va tanlov | `radius-sm,control,space-3`; native control | Field radius/border/padding; select/textarea/checkbox/radio rollari | C04,C16; mobil matn/fokus/touch chegarasi |
| S14 Karta | `radius`, literal `1px` border | Card radius/border/shadow/padding preset | C05; chat bubble bundan mustaqil |
| S15 Dialog va drawer | `radius-lg,dialog,drawer,shadow,space-6` | Dialog radius/border/width/padding; drawer mustaqil cheklangan preset | C10; close/focus/scroll doim yetib boriladi |
| S16 Badge, avatar, jadval | `radius-round,avatar,avatar-sm,space-*` | Badge radius; avatar o‘lcham preset; table density/header/body rollari | C03,C11,C13; avatar crop va table overflow |
| S17 Navigatsiya | `side,action-soft,radius-sm,sidebar,header` | Nav item radius/padding va active ko‘rinish; shell o‘lcham presetlari | C09,C19; menyu tarkibi/ruxsatni o‘zgartirmaydi |
| S18 Chat | `surface,action-soft,radius,reading,control` | Own/other bubble, composer radius/padding; umumiy palitradan meros | C14; history scroll, native keyboard, long content |
| S19 Zichlik va kontent eni | `space-1…16,content,reading,aside` | Ixcham/odatiy/keng preset; o‘qish maydoni va content width preset | C05,C13,C19; responsive va mavjud ish oqimlari |
| S20 Tayyor variant/qoralama/nashr | Hozir design service yo‘q | Nomlangan preset, draft, diff, published version, history, reason, rollback | F20; G01–G06; owner-only mutation |

Token nomlari jadvalda `--az-` prefiksisiz yozilgan; barcha joriy qiymatlar
va CSS consumer fayllari alohida [inventarda](DESIGN-01-DC1-SOURCE-INVENTORY.md).

**Owner uchun oddiy control bo‘lmaydigan tokenlar:** `layer-*` (qatlam
kafolati), `fast/motion` (reduced-motion bilan bog‘liq), `dot/progress/icon`
(komponent geometriyasi), `art-*` (illustratsiya), `empty` (bo‘sh holat eni).
Ular DC1da hisobga olingan; har birini sliderga aylantirish qamrovga kirmaydi.
Breakpoint, timer, baho, quota, permission, nav tartibi va xavfsizlik
chegaralari dizayn maydoniga aylanmaydi. `radius-round`ni global o‘zgartirish
spinner/progress/avatarni buzishi mumkin: semantik rol ajratilgach boshqariladi.

## 4. Komponent xaritasi

`static/frontend_v1/css/` asosiy source; `components.css` bo‘lmasa tegishli
fayl ko‘rsatilgan. Trial registrydagi 20 komponent qoplangan; quyidagi
qo‘shimcha guruhlar shell, rich content va domain komponentlarini ajratadi.

| ID / komponent | Source selector | Sozlama | Holatlar / mustaqillik talabi |
|---|---|---|---|
| C01 Button / icon-button | `.c-button`, `.c-icon-button` | S03,S04,S06,S10,S12 | Primary/secondary/quiet, hover/focus/active/disabled/busy; icon-button touch area |
| C02 Tipografiya | `base.css: html,body,h1,h2,h3`; `.c-eyebrow,.c-caption` | S02,S08–11 | Uzoq matn, heading, body, label, code; heading fonti yangi rol |
| C03 Badge | `.c-badge` | S02,S05,S16 | Success/warning/soft, uzun label; warning hozir soft fonni bo‘lishadi |
| C04 Field | `.c-field`, `.c-field__label`, `[aria-invalid]` | S01–03,S06,S08–10,S13 | Text/number/file/select/textarea, error/read-only/disabled, browser native qismlari |
| C05 Card | `.c-card` | S01,S03,S07,S14,S19 | Default/selected, ichki paddingni page literalidan ajratish |
| C06 Alert | `.c-alert` | S05,S06,S13 | Success/error va unknown/offline; rang bilan birga matn |
| C07 Progress | `.c-progress` | S01,S04,S05 | Native progress va vendor pseudo selectorlar; qiymat formulasi o‘zgarmaydi |
| C08 Tabs | `.c-tabs`, `.c-tabs__item`, `.c-tabs__count` | S02–04,S06,S17 | Current/focus/overflow, hisob va navigatsiya saqlanadi |
| C09 Nav item | `shell.css:.c-nav-item` | S01–04,S06,S17 | Current/hover, collapsed/mobile; role scope o‘zgarmaydi |
| C10 Dialog/drawer | `.c-dialog`, `.c-dialog--drawer`, `::backdrop` | S01–03,S07,S15 | Open/close, native focus, uzun content/short viewport; fixed stacking |
| C11 Avatar | `.c-avatar` | S01,S02,S16 | Image/initials/small; rasmdagi rang qayta bo‘yalmaydi |
| C12 Empty/skeleton | `.c-empty`; `skeleton` faqat Trial component registryda, CSS selector topilmadi | S01,S02,S04,S09,S19 | Empty mavjud; skeleton implemented deb olinmaydi; loading/reduced-motion DC2da xaritalanadi |
| C13 Table | `.c-table-wrap`, `.c-table` | S01–03,S08–10,S16,S19 | Header/body/scroll, ko‘p qator/uzun qiymat, mobile |
| C14 Chat | `messenger.css:.s-mw-bubble,.s-mw-composer,.s-mw-send` | S01–07,S08–10,S18 | Own/other/AI, sending/error/unknown, keyboard/history; card radiusidan ajraladi |
| C15 Step | `.c-step`, `.c-step__number` | S04,S05,S09,S19 | Checkout step va uzun nom; biznes state saqlanadi |
| C16 Choice | `.c-choice`; `classbook.css`, `exam-attempt.css` | S03–06,S13 | Radio/checkbox/matching/order; answer key va grading o‘zgarmaydi |
| C17 Icon | `.c-icon`, `icons.svg` | S02,S04,S05; inherited color | `currentColor` icon; SVG geometriyasi va bitmap redesign alohida |
| C18 Section-title/stat/week | `.c-section-title`; `learning.css:.c-stat*,.c-week*` | S01–05,S08–11,S19 | Stats/count/date/selected; progress va XP hisoblanishi o‘zgarmaydi |
| C19 Shell/brand | `shell.css:.s-*`; `components/brand_logo.html` | S01–04,S08–11,S17,S19 | Learner/teacher/public/auth; existing SiteSettings logo source |
| C20 Rich content | `public.css`, lesson content; legacy CKEditor | S01,S02,S08–11 | Link/list/table/image/code; sanitized kontentdagi format va vendor UI cheklangan |
| C21 Hujjat | `certificates.css`, tokenlarning `@media print` qismi | S08–10; print alohida | Screen light/dark va A4/print alohida qabul; global palette printni bosmaydi |
| C22 Domain actions | `classbook.css`, `study.css`, `exams.css`, `library.css` | C01–16 orqali | Reveal/locked/stale/review, file picker, quota; state ma’nosi saqlanadi |

**Aniq coupling qarzi:** `radius-sm` button, field, nav, table wrapper va
material rowda; `radius` card va chat bubbleda; `control` tugma, input va
composerda ishlatiladi. Hozir bitta qiymatni o‘zgartirish ularning barchasini
o‘zgartiradi. DC2 bu bog‘liqlikni yashirmaydi; component role → eski default
mosligi bilan ajratadi. `fast` tokenining direct consumeri topilmadi;
unga ishlaydigan alohida sozlama bor deb da’vo qilinmaydi.

## 5. Sahifa oilalari va renderer xaritasi

Har real URL, callback va unga tegishli preview IDsi
[to‘liq source inventarida](DESIGN-01-DC1-SOURCE-INVENTORY.md) bor.
Quyidagi flag nomlarida `frontend_v1_` prefiksi tushirilgan. Flagning
**koddagi tanlash yo‘li** o‘rganildi; local DB override yoki AWS holati o‘qilmadi.
Flag OFF renderer ham keyingi regression qamroviga kiradi.

| ID / sahifalar | Amaldagi renderer source va flag | Asosiy komponentlar | Holat / DC2 preview namunasi |
|---|---|---|---|
| F01 Public: home/about/katalog/kurs/pricing/legal/blog/SIT | `frontend/public_v1.py`, `templates/frontend_v1/public/`; `public` | C01–07,C19,C20 | V1 mapped, legacy constrained; home + course detail + uzun maqola |
| F02 Auth: login/register/onboarding/reset | `core/frontend_v1.py`, `users/frontend_v1_auth.py`, V1 auth templates; `auth`, login uchun `learning OR auth` | C01,C02,C04,C06,C19 | Mapped; invalid form va reset link states; native keyboard ochiq |
| F03 Learner dashboard/my-courses | `users/views.py`, V1 dashboard/courses; `learning` | C01,C05,C07,C18,C19 | Mapped; empty/long/progress |
| F04 Dars/material/assignment/quiz | `courses/views.py`, `courses/frontend_v1_practice.py`, V1 lesson/study; `lesson` | C01–07,C10,C16,C20,C22 | Mapped; locked/error/submit; faylning o‘zi X03 |
| F05 Human messenger | `messenger/frontend_v1.py`, V1 messenger; `messenger` | C01,C04,C10,C11,C14 | Mapped; group/tutor, own/other, attachment |
| F06 AI messenger va index alias | Shu adapter, V1 ai_messenger; `ai_messenger` | C01,C04,C10,C14 | Mapped; quota/failure/unknown; UX-01 yopilmagan |
| F07 Profil/hisob | `users/frontend_v1_account.py`; `account` | C01,C04–06,C11 | Mapped; avatar/password/dirty form |
| F08 Maxfiylik/to‘lov/imkoniyatlar | `users/frontend_v1_settings.py`; `settings` | C01,C04,C06,C08,C10 | Mapped; confirm/stale/empty memory |
| F09 Sertifikat ro‘yxati/davomat/obuna/reyting/notification/help | `users/frontend_v1_records.py`; `records` | C01–08,C13,C18 | Mapped; pagination/filter/read/unread/long |
| F10 Sertifikat detail/appendix | `courses/frontend_v1_certificates.py`; `certificates` | C02,C05,C21 | Screen mapped, print constrained X01 |
| F11 Teacher home/release/directory/attendance/review | `core/teacher_views.py`, `core/frontend_v1*.py`; `teacher` | C01–10,C13,C16,C19 | Mapped; readonly/stale/review; dated `attendance_manage` legacy constrained |
| F12 Course/lesson editor | `core/frontend_v1_editors.py`; `editors` | C01,C04–06,C10,C13,C20 | Mapped; create/edit/dirty/error, legacy CKEditor X02 |
| F13 Library/list/create/edit/picker | `library/frontend_v1.py`, `library/backoffice_views.py`; `library` | C01,C04–06,C10,C13 | Mapped; upload/archive/stale; media X03 |
| F14 Checkout/receipt/renewal | `cohorts/frontend_v1.py`, `cohorts/views.py`, `difference_views.py`; `checkout` | C01,C04–06,C10,C15 | Mapped; quote/pending/success/unknown; yangi enrollment va real bank-app qabuli ochiq |
| F15 Exam center/attempt/result/teacher exam review | `courses/views.py`, `exam_attempt_v1.py`, `core/frontend_v1_exam_review.py`; `exams`, `exam_attempt`, `exam_review` | C01–08,C10,C16,C22 | Mapped; attempt/timer/audio/focus; faol attemptga keskin live theme push taklif qilinmaydi |
| F16 Classbook preparation | `classbook/frontend_v1.py`; `classbook_preparation` | C01,C04–06,C10,C13,C16 | Mapped; exercise form/playbook/dirty/long |
| F17 Classbook live/results | `classbook/frontend_v1_live.py`; `classbook_live` | C01–07,C13,C16,C22 | Mapped; reveal/closed/results, audio/media X03 |
| F18 Owner backoffice/control/catalog/exam editor/blog-SIT studio/brand/landing | `core/views.py`, `subscriptions/backoffice_views.py`, `blog/views.py`, `sit/backoffice_views.py`; legacy backoffice shell | C01–06,C10,C13,C19,C20 rollariga kelajakda moslanadi | Constrained; Trialda oila bor, real V1 port bor deb sanalmaydi |
| F19 Mini App entry/home/courses/AI/profile | `bot/views.py`, `templates/bot/miniapp*`, `static/js/miniapp.js` | C01–06,C09,C19 rollari | Constrained; Trialdagi mini shell tokenlari real Telegram adapteri emas |
| F20 Yangi Dizayn paneli | Real route/model yo‘q; [namespace/permission DC2da belgilangan](DESIGN-01-DC2-PREVIEW.md#f20-route-namespace-va-permission-kontrakti), real enforcement DC4da | C01–06,C08,C10,C13 | Lokal DC2 studio alohida katalogda; real port proposed, existing source URL hisobi o‘zgarmaydi |
| F21 403/404/500/maintenance/offline | `core/views.py`, `templates/errors/_base_error.html` | C01,C02,C06,C19 | Constrained; 500 minimal static fallback, haqiqiy offline cache alohida |

## 6. Istisnolar: yashirin to‘liq-qamrov da’vosi bo‘lmasin

| ID / consumer | Tasnif | Qoidasi va dalil |
|---|---|---|
| X01 Print/PDF/sertifikat | constrained | V1 tokenlarda alohida print palitrasi, `certificates.css` oq/qora override bor. Screen nashri printga avtomatik tatbiq etilmaydi; print preset alohida qabul |
| X02 CKEditor/Jazzmin/native controls | constrained | `django_ckeditor_5`, shartli `/admin/`, browser date/select/file UI tashqi renderer. Surrounding app styling xaritalanadi, vendor ichki palitrasi alohida |
| X03 Rasm/video/PDF/audio/download | not applicable (ichki kontent) | Faylni qayta bo‘yash yo‘q; container/control C17/C20/C22. YouTube iframe, certificate bitmap va rasmdagi matn ham shu chegara |
| X04 Telegram host chrome | constrained | `miniapp.js` host header/background va `themeChanged`ni chaqiradi. Ilova ichki palitrasi bilan host mode prioriteti real Telegramda tekshiriladi |
| X05 Legacy SIT | constrained | `sit.css` o‘z root/media/data-theme qiymatlari va `sit-theme` storagega ega. Bu V1 palitrasiga avtomatik ulanmagan |
| X06 Legacy backoffice/auth/public/learner | constrained | `static/css/` va inline template literal qiymatlari. CSS bridge va component roli ajratilishi kerak; har sahifa tekshiriladi |
| X07 Grafik va chizilgan progress | constrained | CSS/native progress mapped; canvas/SVG ichidagi literal rang va JS konfiguratsiya alohida consumer auditi. Chart kutubxonasi bor deb taxmin qilinmaydi |
| X08 Minimal 500 va offline | constrained | 500 context-processorsiz render; design DBga tayanmaydigan default shart. Offline sahifa mavjudligi service worker/cache kafolati emas |
| X09 JSON/action/redirect/webhook/socket/export | not applicable (mustaqil ekran) | Source inventaridagi yordamchi URLlar yangi sahifa deb hisoblanmaydi; ularning UI success/error holati tegishli F oilada tekshiriladi |
| X10 Brand/media ownership | constrained | Existing SiteSettings/LandingPage logotip, matn va media egasi. Publish design bu model qiymatlarini jimgina qayta yozmaydi |

## 7. Keyingi bosqichlarga aniq topshiriq

| ID | Talab | Keyingi dalil |
|---|---|---|
| G01 Rol ajratish | Button/input/card/dialog/chat mustaqil; no-change default avvalgi ko‘rinishga teng | DC2 komponent preview va computed-style comparison |
| G02 Preview kontrakti | S01–20 form, private draft, multi-page light/dark/compact/wide; haqiqiy payment/AI/message mutatsiyasiz | DC2 route/action registry; barcha kerakli holatlar |
| G03 Qabul chegaralari | Kontrast juftliklari, safe font catalog/litsenziya, zoom/long text, touch/focus/reduced motion | DC3 dalilli bounds; supported combinations jadvali, xavfli juftlik rad etilishi |
| G04 Yagona writer | Owner-only service; draft revision + published base revision; atomik publish, reason/confirmation/audit/no-op | DC4 permission, duplicate publish, ikki-tab stale, transaction failure; raw admin writer ham service orqali |
| G05 Yetkazish va qaytish | Versioned effective CSS, eski keshdan yangi HTMLga noto‘g‘ri versiya kelmasligi, private preview cache; unknown→GET readback; rollback tarixni saqlaydi | DC4/5 multi-worker/cache/failure tekshiruvi; flag OFF va DB failure fallback |
| G06 Real qabul | Har mapped F oilasi; legacy rollback, native Mini/iPhone keyboard, print/vendor cheklovlari ownerga ko‘rinadi | DC5/6 regressiya va walkthrough; oldingi UX ochiq bandlari avtomatik yopilmaydi |

**Ochiq design qarorlari:** aniq font katalogi va aktivlar; density/radius/shadow
presetlarining soni va numeric bounds; owner shell accentini global accentdan
mustaqil qilish; print uchun kelajakdagi kengaytma; Mini host/user mode
prioriteti; publish yangi sahifa yuklanishida qo‘llanishi va allaqachon ochiq
sahifaga ko‘rsatma. Hozirgi tavsiya — in-flight exam/chatga avtomatik layout
almashishini yubormaslik; bu yakuniy runtime shartnoma emas.

## 8. DC1 tekshiruv va yakun

- Kod/registr o‘qish, CSS declaration/consumer va URL resolver inventari bajarildi.
- Resolver `.env` yuklanmasdan, Gemini/Telegram kalitlari bo‘sh, Django
  `dummy` DB backend bilan ochildi; request render, user DB so‘rovi, provider
  chaqiruvi va HTTP mutation bajarilmadi.
- `venv/Scripts/python.exe .tools/design-dc1/validate_inventory.py` — PASS:
  73 token identity/value, 120 UI/alias + 77 yordamchi URL, S20/C22/F21/X10/G6
  IDlar, 3 source SHA256 va 112 relative link tekshirildi. Yordamchi script
  ignored local tooling; hujjatdagi statik dalil remote review uchun yetkaziladi.
- `git diff --check` — PASS. Bu docs-only tekshiruv natijasi.
- UI/CSS/JS/model/migration o‘zgarmagani uchun browser va app testlari bu
  bosqichning dalili emas va qayta ishga tushirilmaydi. Native/owner visual
  acceptance **NOT TESTED**. DC1 completion DC2 boshlanishi yoki release GO emas.
