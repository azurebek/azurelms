# DESIGN-02 — "sokin" dizayn tizimini production'ga ko'chirish rejasi

**Holat — 2026-11-08: S0 (shu reja, docs-only). Implementatsiya boshlanmagan; flag hali registrda yo'q.**
Owner qarori 2026-11-07: owner bilan qurilgan eskizdagi dizayn tizimi AzureLMS'ning **yangi dizayn tizimi**
bo'ladi — tokenlar, shrift, o'lchamlar, chegaralar, komponentlar, sahifa turlari va ochiq sayt ham. Bu
2026-10-30 dagi `#1257e6` tugma qarorini, PE9 dagi 1200px qarorini va PUBLIC-02 editorial ko'rinishini
almashtiradi ([PUBLIC-02](PUBLIC-EDITORIAL-PORT-PLAN.md) PE9–PE10 to'xtatildi).

**Manba git'dan tashqarida.** Eskiz (79 sahifa, yorug' va qorong'i, telefon va kompyuter) va uning dizayn
qoidalari hujjati owner'ning shaxsiy claude.ai artefaktlari; repo'ga kirmaydi. Shu sabab bu hujjat portga
kerakli normativ qismni — tokenlar xaritasi, komponentlar, menyu, bosqichlar va domen chegaralarini — o'zida
saqlaydi, S1 esa token qoidasini CI testiga aylantiradi. Ko'rinish bo'yicha bahsli joyda yakuniy manba —
owner'ning eskizdagi qabuli.

Bu reja PUBLIC-01, DASHBOARD-01, COMMERCE-01, CLASSBOOK-01 va B3 kontraktlarini o'zgartirmaydi. U **ko'rinish
va sahifa tuzilishi**ni almashtiradi; har sahifa bugungi adapterlardan keladigan ayni kontekstni chizadi.

## 1. Qamrov

**Ko'chiriladi:**

- dizayn tokenlari — ranglar, matn o'lchamlari, burchaklar, balandliklar va chegaralar (D2);
- Figtree shrifti, o'z serverimizda (D1);
- komponentlar — tugma, maydon, holat belgisi, tasdiq paneli, yig'iladigan bo'lim, ro'yxat qatori, tab va
  pastki menyu;
- beshta sahifa turi va rolga qarab menyu (§4.7);
- har sahifa, ochiq sayt va kirish ham, o'zining bo'sh, kutish, xato va muvaffaqiyat holatlari bilan.

**Ko'chirilmaydi:**

- eskizdagi "faqat eskizda" qutilari va namuna raqamlar;
- eskizdagi namuna narxlar — haqiqiy narx admin paneldagi Tariflar sahifasida o'zgaradi va bazadan o'qiladi
  (owner tuzatishi, 2026-11-08);
- eskizda chizilgan, lekin kodda ma'lumoti yo'q funksiyalar — ular o'z dasturida keladi (§7).

**Tayyor degani:**

- eskizdagi har sahifa flag yoqilganda eskizdagidek ko'rinadi;
- flag o'chiq bo'lsa hech bir sahifa baytda o'zgarmaydi;
- uchala majburiy CI ishi yashil;
- 320px'da gorizontal toshish 0;
- har bosqichni owner eskiz bilan yonma-yon ko'rib qabul qilgan.

PUBLIC-02 ning ochiq sayt uchun qilgan ishi yo'qolmaydi: kontekst adapterlari, so'rov byudjetlari, rost da'vo,
SEO va a11y qoidalari yangi ochiq shablonlarga meros o'tadi; faqat ko'rinish almashadi.

## 2. Feature admission

1. **Muammo:** o'quvchi, ustoz va owner har kuni ishlatadigan sahifalar uch xil davrda qurilgan uch ko'rinishda
   (legacy, V1, editorial). O'quvchi menyusida 2 ta asosiy va 10 ta "avvalgi ko'rinishda" band bor
   (`core/frontend_v1.py`), telefonda pastki menyu yo'q, bir xil vazifa sahifadan sahifaga boshqacha chiziladi.
   Owner 2026-11-06 da kirgandan keyingi dizayn "nimasidir noto'g'ri" ekanini aytdi; eskizda butun platforma
   bitta tizimda qurildi.
2. **Asosiy KPI (taklif):** ochiq qismda — PUB1.8a voronkasi (`public_funnel_report`: kurs sahifasidan xarid
   niyatigacha), eski dizaynda baseline bilan. Ichki sahifalar uchun hozir o'lchov manbai yo'q; uni qo'shish
   alohida kesim (shaxsiy ma'lumotsiz, PUB1.8a naqshida) yoki owner KPI'siz qabulni tanlaydi. Bu S10 dan oldin
   hal qilinadi, portni to'xtatmaydi.
3. **Canonical state:** o'zgarmaydi. Yagona yangi yozuvlar DESIGN-01 ustaxonasida: katalogdagi "Sokin" tayyor
   varianti va matn oralig'i (`core/design_catalog.json`), mavjud auditli qoralama → nashr oqimi orqali
   (`core/design_service.py`). Migration yo'q.
4. **Adapterlar (faqat iste'mol qiladi):** V1 ichki shablonlari, ustoz shablonlari, backoffice workspace,
   ochiq/auth shablonlari, shell (`platform.html`, `shell.css`, `shell.js`), Mini App ramkasi. Kontekst bugungi
   view'lar va selectorlardan — yangi selector yoki dublikat hisob yo'q.
5. **Owner yuki:** port davomida har bosqich oxirida eskiz bilan yonma-yon ko'rik; keyin oshmaydi.
6. **Flag va rollback:** `platform_calm_v1` (default OFF). OFF — bugungi V1/editorial/legacy chiqishi baytda bir
   xil. S10 gacha qaytarish bitta harakat: flag o'chiriladi.
7. **Taklif qilingan status: `ADMIT — post-launch`.** Yakuniy status owner qarori.

## 3. Owner qarorlari

**Qaror — 2026-11-07:** eskiz dizayn tizimi real kodning dizayn tizimi bo'ladi; D1–D4 shu bilan yopildi.

| # | Savol | Qaror yoki tavsiya | Ta'siri | Holat |
|---|---|---|---|---|
| D1 | Shrift | **Owner:** Figtree 400/500/600 | O'z serverimizda woff2 (PUB1.7b tashqi shriftni taqiqlaydi). Turkcha (ğ, ş, ı, İ) va o'zbekcha (‘, ʻ) harflar S1 da sinaladi; asset byudjeti qayta o'lchanadi | Qabul qilindi (2026-11-07) |
| D2 | Ranglar va o'lchamlar | **Owner:** eskiz qiymatlari — `#1d57d8`, `#1f1f1f`, oq fon, 16/12px burchak, 15/13px matn | 2026-10-30 dagi `#1257e6` qarori o'rnini bosadi. Qiymat ikki joyda almashadi: `tokens.css` va ustaxona standartlari; ustaxona matn oralig'i kengayadi | Qabul qilindi (2026-11-07) |
| D3 | Telefon chegarasi | **Owner:** 900px dan tor — pastki menyu; 560px dan tor — tugmalar to'liq kenglikda | PE9 dagi 1200px qarori o'rnini bosadi; shell S2 da bir marta qayta quriladi | Qabul qilindi (2026-11-07) |
| D4 | Ochiq sayt | **Owner:** eskizdagi ochiq sahifalar | PUBLIC-02 editorial ko'rinishi almashadi; PE9–PE10 to'xtatildi; editorial kontekst va so'rov ishi meros | Qabul qilindi (2026-11-07) |
| D5 | Navbat | DASH1.0a (stop-ship) dan keyin; PE9 endi kerak emas; B3 va CLASSBOOK-01 bilan fayllar bo'yicha kelishiladi | Hamma bosqichlar | DASH1.0a 2026-11-08 da [PR #252](https://github.com/azurebek/azurelms/pull/252) bilan `main`ga qo'shildi; owner shu kuni "boshla" dedi — S0 boshlandi |
| D6 | Tariflar | Narx ma'lumot, kod emas: admin paneldagi Tariflar (`backoffice_workspace_plans` → `backoffice_plan_edit`) narx, tarkib, sig'im va sotuvni o'zgartiradi; sahifalar bazadan o'qiydi | Port narxlarni kutmaydi | Boshqacha hal qilindi (owner, 2026-11-08) |
| D7 | Mini-ilova | **Owner:** eskizdagidek — Telegram ichida kichik bosh sahifa, bo'limlar saytning o'z sahifalarini menyusiz (`tgmini` ramkasi) ochadi; `templates/bot/miniapp_*.html` keyin olib tashlanadi | S9, DASHBOARD-01 Mini App bosqichi (DASH1.0d) | Qabul qilindi (2026-11-08) |
| D8 | Qorong'i rejim: kodda bor, eskizda avval yo'q edi | O'chirilmaydi. Qorong'i variant eskizga chizildi (har rang token, yorug' qiymatlar o'zgarmagan) | Har sahifa; ustaxonaning qorong'i standartlari | Owner ko'rigini kutmoqda; S1 darvozasi |

Qoidalar hujjatidagi ochiq savollar portni to'xtatmaydi, faqat o'z qismini:

- **Davomat (3 savol):** uch bosqichli davomatni kim boshlaydi, har tekshiruv oynasi qancha, holat o'rniga XP va
  "kelmadi" xabari nimaga bog'lanadi. Faqat uch bosqichli davomat ishini to'xtatadi (CLASSBOOK-01).
- **Jonli dars tugmasi:** `classbook/delivery.py` guruhga inline `web_app` tugma yuboradi, Bot API esa uni faqat
  shaxsiy chatda ruxsat beradi; haqiqiy guruhda sinalmaguncha jonli dars sahifasi eski oqimda qoladi.
- **Ustoz huquqi:** ustoz kurs ma'lumotlarida narx, katalog va ustozni o'zgartira oladimi (bugungi forma hammaga
  ko'rsatadi). S6 dagi ustoz kurs sahifasini to'xtatadi.

## 4. Arxitektura

DESIGN-02 ikki ish qiladi: mavjud V1 tanloviga yangi shablon qatlamini qo'shadi va dizayn tizimining standart
qiymatlarini eskizdagiga almashtiradi. Ruxsat, kontekst, so'rovlar va cache bugungidek qoladi.

1. **Flag.** `platform_calm_v1` `core/flags.py` registriga qo'shiladi, default OFF. Boshqa flaglar bilan bitta
   `flags_enabled(...)` chaqiruvida o'qiladi — so'rovlar soni o'zgarmaydi.
2. **Shablon tanlovi.**
   - Ichki sahifalar: bugungi tanlov nuqtalari (`core/frontend_v1.py::FrontendV1Mixin.get_template_names`,
     `render_teacher_v1`, backoffice workspace) bitta `calm_template_names(t)` funksiyasiga keltiriladi; flag ON
     bo'lsa `["frontend_v1/calm/<t>", "<t>"]`.
   - Ochiq sahifalar: `frontend/public_content.py` renderer bugun uch qiymat oladi (`LEGACY`, `V1`, `EDITORIAL`);
     to'rtinchisi `CALM` qo'shiladi, `frontend/public_v1.py::public_template_names` zanjiri calm → editorial → V1.
   - Ikkala holatda ko'chirilmagan sahifa avtomatik eskisida qoladi.
3. **Tokenlar ikki joyda almashadi:** `static/frontend_v1/css/tokens.css` (statik standart) va
   `core/design_catalog.json` (ustaxona standartlari). Sabab: ustaxona yoqilgan bo'lsa
   (`backoffice_design_workspace`), nashr qilingan ko'rinish har sahifada barcha `--az-*` ranglarni `:root`ga
   yozadi va flagli CSS'dan ustun turadi. Shuning uchun:
   - S1 da eskiz qiymatlari katalogning `presets` ro'yxatiga **"Sokin"** varianti sifatida qo'shiladi (mavjud
     "Asl Azure", "Yumshoq shakllar", "Ixcham ish maydoni", "O'qish uchun" yonida);
   - ishlab chiqish va owner ko'rigi lokal bazada shu variantni nashr qilib o'tkaziladi;
   - S10 da `tokens.css` va katalog standartlari eskiz qiymatlariga o'tadi.
   Owner keyin ham ustaxonada istalgan qiymatni o'zgartira oladi.
4. **Ustaxona katalogi.** Matn oralig'i eskizga moslanadi: `text-md` minimumi 16 → 15px, `text-sm` 14 → 13px
   (`text-2xl` minimumi 24px, eskizning 26px'i allaqachon sig'adi). Eski nashr va qoralamalar ochilishi kerak —
   PUBLIC-02 PE1 dagi `added` qoidasidek. Validatsiya `core/design_schema.py` va
   `static/backoffice/design-model.mjs`da birga o'zgaradi.
5. **Shrift.** Figtree 400/500/600 woff2 `static/` ichida, litsenziya fayli bilan. `tokens.css`dagi `@font-face`,
   `--az-font` ro'yxatida Figtree birinchi; `font-display: swap`.
6. **CSS.** `static/frontend_v1/css/calm.css` faqat flag ON sahifalarda (`<html class="s-calm">`). Unda faqat
   tokenlar; breakpoint ikkita — 560 va 900px. Qoida `tests/frontend_v1/calm.test.mjs`da (CI'dagi Node bosqichi
   `tests/frontend_v1/*.test.mjs`ni allaqachon yuguradi). Asset byudjeti ichki sahifalarga ham qo'yiladi.
7. **Menyu.** Rolga qarab, 6 bandgacha:
   - o'quvchi: Bosh sahifa, Darslarim, Jonli dars, Natijalarim, Xabarlar;
   - ustoz: Bosh sahifa, Jonli dars, Guruhlarim, Tekshiruv, Xabarlar;
   - admin: Ish stoli, Kurslar, O'quvchilar, Xabarlar, To'lovlar, Sozlamalar.
   Telefonda pastki satrda 5 tagacha band. Global bandlar DASH1.0a ruxsat qoidasiga bo'ysunadi
   (`core/backoffice_capabilities.py`): ruxsatsiz xodimga 403 ga olib boradigan band ko'rsatilmaydi.
8. **Komponentlar** `components.css`dagi `c-*` klasslari ustiga: holat belgisi, tasdiq paneli, yig'iladigan bo'lim,
   ro'yxat qatori, pastki menyu, akkaunt va bildirishnoma qalqib chiquvchi oynalari (faqat ≥900px).
9. **Mini rejim.** Mini-ilova sahifani `tgmini` nomli ramkada ochadi; `<html data-mini>` menyuni yashiradi (D7).
10. **Qorong'i rejim.** Tokenlarning qorong'i qiymatlari eskizdagi palitradan (D8); `theme.js` va mavzu tugmasi
    saqlanadi.
11. **Xato sahifalari.** `templates/errors/` bazaga tegmaydi va flagni o'qiy olmaydi — S10 da to'g'ridan-to'g'ri
    almashadi.

## 5. Tokenlar xaritasi

Har eskiz qiymatining production'da tokeni bor; yangi rang tokeni kerak emas. Token nomlari qoladi, qiymatlari
almashadi. Kodda hex emas, token nomi yoziladi. "Hozirgi" ustuni 2026-11-08 dagi `tokens.css` (yorug').

| Eskizda | Token | Yangi qiymat | Hozirgi |
|---|---|---|---|
| Shrift | `--az-font` | Figtree | Segoe UI |
| Asosiy ko'k | `--az-action`, `--az-focus` | `#1d57d8` | `#1257e6` |
| Bosilgan ko'k | `--az-action-hover` | `#17459f` | `#1048bf` |
| Och ko'k fon | `--az-action-soft`, `--az-hero` | `#e8f0fe` | `#edf3ff` |
| Sahifa va karta foni | `--az-canvas`, `--az-surface` | `#ffffff` | `#f6f8fb`, `#ffffff` |
| Yon menyu, yumshoq fon | `--az-side` | `#f7f9fa` | `#ffffff` |
| Neytral belgi foni | `--az-soft` | `#f1f3f4` | `#eef2f7` |
| Matn | `--az-text` | `#1f1f1f` | `#172235` |
| Ikkinchi matn | `--az-muted` | `#444746` | `#5d6a7e` |
| Izoh matni | `--az-faint` | `#5f6368` | `#5f6c82` |
| Chiziq | `--az-border` | `#c4c7c5` | `#e3e8ef` |
| Xato, xato foni | `--az-danger`, `--az-danger-soft` | `#b3261e`, `#fce8e6` | `#b43b44`, `#fceef0` |
| Muvaffaqiyat (davomat doirachasi) | `--az-success` | `#188038` | `#22714f` |
| Ogohlantirish | `--az-warning` | `#b06000` | `#936410` |
| Sahifa sarlavhasi | `--az-text-2xl` | 26px | 28px |
| Asosiy matn, izoh | `--az-text-md`, `--az-text-sm` | 15px, 13px | 16px, 14px |
| Burchak: karta, maydon, tugma | `--az-radius-lg`, `--az-radius`, `--az-radius-round` | 16px, 12px, to'liq | 18px, 14px, to'liq |
| Tugma va maydon balandligi | `--az-control` | 44px | 44px |
| Yon menyu eni | ustaxona "Yon menyu eni" | 232px | shell standarti |

Qorong'i palitra (D8, owner ko'rigini kutadi): fon `#131314`, yumshoq `#1b1c1e`, neytral `#26282b`, chiziq
`#474a4d`/`#2f3134`, matn `#e3e3e3`/`#c4c7c5`/`#9aa0a6`, asosiy `#8ab4f8` (bosilgan `#aecbfa`, ustidagi matn
`#0b1d3f`, och fon `#1e2f4d`), xato `#f28b82`/`#3b1d1b`, muvaffaqiyat `#81c995`, ogohlantirish `#fdd663`/`#3a2f10`.

Eng ko'p ko'zga tashlanadigan o'zgarishlar: ko'rinarli chegaralar, toza oq fon va bir pog'ona kichik matn. 15px
matn a11y probe va haqiqiy telefonda alohida tekshiriladi. `#188038` och yashil fonda matn sifatida 4.5:1 dan past
— u faqat doiracha va belgi uchun; muvaffaqiyat matni uchun to'qroq qiymat S1 da tanlanadi.

## 6. Bosqichlar

O'n bitta bosqich: S0–S1 asos, S2 shell, S3–S9 sahifa guruhlari, S10 yoqish va tozalash. S0–S2 ketma-ket; S3–S9
bir-birini kutmaydi, har biri o'z darvozasi ochilganda boshlanadi; S10 hammasi qabul qilingach.

**Owner qarori — 2026-11-08: bitta branch, oxirida bitta merge.** DESIGN-02 butunlay `claude/design-02-plan`
branchida va [PR #253](https://github.com/azurebek/azurelms/pull/253)da yuradi; har bosqich shu branchda alohida,
testdan o'tgan commit(lar). `main`ga oraliq merge yo'q — PR S10 va owner qabulidan keyin bitta merge bilan
qo'shiladi (rules §9 gate'lari o'sha merge'ga qo'llanadi: uchala check yashil, review thread'lar resolve, branch
`main` bilan yangilangan). Shu sabab:

- har bosqich oxirida owner ko'rigi lokal serverda shu branchdan o'tadi;
- branch `main` bilan har bosqich boshida va konflikt chiqqanda **merge** orqali yangilanadi (rebase va force-push
  yo'q), konflikt rules §13 bo'yicha yechiladi va marinebook'da qayd etiladi;
- har push'da CI to'liq yuguradi — qizil holat keyingi bosqichga o'tishdan oldin tuzatiladi;
- marinebook'ga har bosqich commit hash'i bilan yoziladi, merge natijasi faqat oxirida;
- flag S10 gacha OFF bo'lgani uchun branch istalgan bosqichda production'ni o'zgartirmasdan merge qilinishi mumkin
  edi — oraliq merge kerak bo'lib qolsa (masalan uzoq konflikt), owner bilan alohida kelishiladi.

| Bosqich | Eskiz sahifalari | Real shablonlar | Darvoza | Tekshiruv |
|---|---|---|---|---|
| S0 Reja | — | shu hujjat; [README](../README.md), [PORT-LEDGER](PORT-LEDGER.md), [PUBLIC-02](PUBLIC-EDITORIAL-PORT-PLAN.md) yozuvi | D1–D4 | `git diff --check`; docs-only commit `bd383ec` |
| S1 Poydevor | Tokenlar va komponentlar | `core/flags.py`, `calm_template_names`, `CALM` renderer qiymati, `css/calm.css`, `calm.test.mjs`, Figtree, `design_catalog.json` ("Sokin", matn oralig'i), qorong'i tokenlar | S0, D8 | Flag OFF'da `public_route_snapshot.json` va renderer chiqishi baytda bir xil; ustaxona testlari va eski nashrlar; glif sinovi; `node --test`, `manage.py check` |
| S2 Shell va menyu | Yon menyu, pastki menyu, akkaunt/bildirishnoma oynalari, mini rejim | `platform.html`, `nav.html`, `account.html`, `shell.css`, `shell.js`, `core/frontend_v1.py` menyusi | S1 | `users.test_frontend_v1`, shell Node testi, a11y probe, 320/390px |
| S3 O'quvchining kundalik yo'li | Bosh sahifa, yangi foydalanuvchi, Darslarim, Dars, Mashqlar, Kutubxona, Xabarlar, Azure AI, Bildirishnomalar | `dashboard.html`, `courses.html`, `lesson.html`, `practice_*.html`, `library/`, `messenger.html`, `ai_messenger.html`, `records/notifications.html` | S2 | Renderer testlari flag ON va OFF; so'rov byudjeti |
| S4 Natijalarim | Imtihonlar, Imtihon, Natija, Sertifikatlar, Sertifikat, Ballar ilovasi, Davomat, Reyting | `exams/`, `records/certificates.html`, `certificates/`, `records/attendance.html`, `records/leaderboard.html` | S2 | `exam-attempt`, `certificates`, `records` Node testlari; chop etish |
| S5 Hisob va to'lov | Profil, Sozlamalar, Yordam, To'lovlar, Chek | `profile.html`, `account.html`, `settings_*.html`, `records/help.html`, `records/subscriptions.html`, `checkout/` | S2; checkout — COMMERCE-01 bilan kelishib | `settings.test.mjs`, checkout testlari; imzoli narx va server qayta hisobi o'zgarmaydi |
| S6 Ustoz | Bosh sahifa, Tekshiruv navbati, Tekshirish, Imtihon tekshiruvi, Guruhlarim, Guruh, Davomat, Kurslarim, O'quvchilar, Jonli dars, Mashqlar banki | `teacher/` (dashboard, grading, grade_*, cohorts, attendance, courses, students), `classbook/teacher_*`, `classbook/exercise_*` | S2; jonli dars — CLASSBOOK-01 | `core.tests.TeacherPanelTests`, `core.test_frontend_v1_review`, `classbook-live.test.mjs`; ustoz faqat o'z guruhini ko'radi |
| S7 Boshqaruv | Ish stoli, Qidiruv, Kurs/Dars/Topshiriq/Test/Imtihon muharrirlari, Materiallar, O'quvchilar, O'quvchi kartasi, Guruhlar, Cheklar, Tariflar, Xabarlar, Sozlamalar, AI, Xodimlar, Platforma holati, Sayt, Brend, Dizayn ustaxonasi, Kontent, Turkiyada o'qish muharriri, Da'volar dalili | `backoffice/workspace/` (home, search, course*, materials, students, student*, groups, plans, design), `backoffice/` (receipts, runtime_settings, feature_flags, ai_control, users, control_center, landing_editor, brand_control, legal_*, sit_*, claim_evidence, exam_form) | S2; B3 bilan bir faylga bir vaqtda emas | `backoffice-workspace`, `backoffice-design` Node testlari; `core.test_backoffice_capabilities` va ruxsat testlari o'zgarmaydi |
| S8 Ochiq sayt va kirish | Landing, katalog, kurs, Biz haqimizda, huquqiy hujjatlar, Blog, maqola, Turkiyada o'qish (3), sertifikat tekshiruvi, kirish va ro'yxat, AI tanishuv | `frontend_v1/editorial/` (base, index, about, courses, blog, sit, legal_page), `login.html`, `auth_*.html`, `auth_onboarding.html`, sertifikat tekshiruvi | S2 | `frontend.test_public_*` CALM bilan; so'rov byudjetlari, a11y probe; sitemap, meta va cache o'zgarmaydi |
| S9 Mini-ilova | Telegram mini-ilova | D7 bo'yicha mini rejim; `templates/bot/miniapp_*.html` | D7, DASH1.0d | Telegram ichida haqiqiy qurilmada |
| S10 Yoqish va tozalash | Hammasi | Flag, `tokens.css` va katalog standartlari, `templates/errors/`, eski V1 va editorial shablonlari | S3–S9 owner qabuli | Lokal DB nusxasida hammasi; owner ko'rigi, a11y, byudjet, 320/390px, haqiqiy telefon. Eski shablonlarni olib tashlash bu bosqichga kirmaydi (§8) |

`/backoffice/chats/` S7 ga kirmaydi: DASH1.0a dan beri u Messenger-owned metadata selector (MSG1.0d) kelguncha hamma
uchun 403; eskizdagi "Xabarlar" bo'limi o'sha selector bilan keladi.

S8 da ochiq sahifalar ramkasi (`editorial/base.html`) eskizdagi yuqori menyu va footer bilan almashadi. Tanlov
zanjiri tufayli CALM shabloni tayyor bo'lmagan sahifa editorial ko'rinishda ishlab turadi — ochiq sayt hech qachon
yarim buzilgan bo'lmaydi.

## 7. Eskizdan kelgan domen o'zgarishlari

Eskizdagi 13 taklifdan hech biri portni to'xtatmaydi. Port avval bugungi ma'lumotni yangi ko'rinishda chizadi;
domen o'zgarishi o'z dasturida keladi va yangi shablon uning qismini faqat kontekstda shu ma'lumot bo'lsa
ko'rsatadi. Eskizda chizilgan, lekin kodda yo'q narsa yangi shablonda va'da qilinmaydi — PUBLIC-01 dagi "rost
da'vo" qoidasining ichki sahifalardagi davomi.

| Taklif | Qayerga tushadi | Port bosqichi nima qiladi |
|---|---|---|
| Darsda alohida "So'zlar" jadvali | Yangi model va migration; B3 dars muharriri bilan (owner: kod bosqichi boshlanganda, 2026-11-07) | S3 Dars sahifasi bugungi bitta matn maydoni bilan |
| Uch bosqichli davomat, uchta doiracha | CLASSBOOK-01 sessiya bosqichi; §3 dagi 3 savol hal bo'lgach | S4 va S6 Davomat bugungi bitta belgi bilan |
| Jonli dars mashqi tugmasi guruhda | CLASSBOOK-01; avval haqiqiy guruhda sinov | S6 jonli dars oqimi o'zgarmaydi |
| Mashq javoblarini qatorlar bilan kiritish | CLASSBOOK-01 "kodsiz 10 tur muharriri" | S6 mashq muharriri bugungi matn sintaksisi bilan |
| Imtihonning 2-bo'limi va savollari saytda, qoralama holati | B3 (exam qoralama/nashri, to'liq muharrir) | S7 imtihon sahifasi B3 dan keyin |
| Bo'lim bali javoblar yig'indisidan; baholanmagan yozish e'lon qilinmaydi | B3 exam muharriri bilan alohida kesim | S6 imtihon tekshiruvi bugungi qoidani ko'rsatadi |
| Natija e'lon qilinganda o'quvchiga xabar | MESSENGER-01 bildirishnomalari | O'quvchi sahifalari bu ish qilinmaguncha "xabar keladi" demaydi |
| Rad etilgan chek sababini ko'rsatish | COMMERCE-01 o'quvchi markazi | S5 chek sahifasi sababsiz holatni rost aytadi |
| Hisobni saytda bloklash/ochish | DASHBOARD-01 (xodim huquqlari) | S7 o'quvchi kartasi tugmasiz |
| Telegram guruhini ulash buyrug'i raqami bilan | S7 ichida kichik kesim: raqam bazada bor, faqat ko'rsatiladi | Shu bosqichda bajariladi |
| Mini rejim, Telegram "orqaga" tugmasi | S9 va DASH1.0d | D7 ga bog'liq |
| Promokodlarni saytda boshqarish | COMMERCE-01 | S7 tariflar sahifasi promokodsiz |
| Xodim qo'shish, rol va kurs berish saytda | DASHBOARD-01; bugun ruxsat `manage.py backoffice_capability` bilan beriladi | S7 xodimlar sahifasi faqat ko'rish uchun |

## 8. Sinov va chiqarish

Port bazadagi ma'lumotni o'zgartirmaydi va migration qo'shmaydi. S10 gacha qaytarish bitta harakat: flag
o'chiriladi va hamma sahifa darhol eskisiga qaytadi. S10 dagi standart token almashuvi alohida commit; merge'dan keyin uni revert qilish
va ustaxonada oldingi nashrga qaytish orqaga oladi.

**Har bosqich commitida (CI esa har push'da):**

1. `manage.py check` va o'zgargan app testlari (`.env.local`siz — [AGENTS.md](../../AGENTS.md)).
2. `node --test tests/frontend_v1/*.test.mjs`, shu jumladan `calm.test.mjs`.
3. Mavjud renderer testlari ikki holatda: flag ON va OFF.
4. So'rovlar soni flag bilan o'zgarmaydi — sahifaning so'rov byudjeti testi.
5. a11y probe (`frontend/a11y_probe.py`) va asset byudjeti.
6. 320 va 390px'da gorizontal toshish 0.

**Har bosqich oxirida:** lokal serverda flag yoqiladi va owner sahifalarni eskiz bilan yonma-yon ko'radi.
Qabul qilinmagan izohlar o'sha bosqichda tuzatiladi.

**Yoqish (S10):** lokal DB nusxasida hamma sahifa flag bilan; owner qabuli; haqiqiy telefon va ekran o'quvchi
(PUBLIC-01 dan beri ochiq bandlar). Serverda yoqish alohida reliz ishi, bu rejaga kirmaydi. Eski V1 va editorial
shablonlari, `s-calm` cheklovi va flag bitta merge'dan keyin ham zaxira yo'l bo'lib qoladi: ular yangi ko'rinish
serverda owner qabulidan o'tgach alohida kichik PR bilan olib tashlanadi — aks holda qaytarish yo'li yo'qoladi.

## 9. Riskler

| Risk | Nima bo'ladi | Yechim |
|---|---|---|
| Ustaxona nashri ranglarni `:root`ga yozadi | Flag ON bo'lsa ham sahifa eski ranglarda | S1 "Sokin" varianti; ko'rik shu variant nashri bilan; S10 da standartlar almashadi |
| Katalog oralig'i o'zgaradi (15/13px) | Bazadagi eski nashr yoki qoralama ochilmay qoladi | Validatsiya `design_schema.py` va `design-model.mjs`da birga; eski nashrlar testi |
| Bir shablonga ikki dastur tegadi (B3, CLASSBOOK-01, DASHBOARD-01) | Merge conflict, qayta ish | Har bosqich boshida fayllar ro'yxati marinebook'da e'lon qilinadi; bitta shablonga bir vaqtda bitta PR |
| PUBLIC-02 PE9–PE10 to'xtatildi | Bajarilgan ko'rinish ishi qisman almashadi | Kontekst, so'rov byudjeti va testlar CALM shablonlariga meros; PUBLIC-02 hujjatida qayd etildi |
| Figtree: harflar yoki tezlik | Turkcha/o'zbekcha harf boshqa shriftda; sahifa sekinlashadi | S1 glif sinovi; 3 qalinlik, `font-display: swap`; asset byudjeti |
| 15px matn va ko'rinarli chegaralar | Kichik ekranda o'qish qiyinlashadi | a11y probe, kontrast, haqiqiy telefon; muvaffaqiyat matni uchun to'qroq yashil |
| Uch ko'rinish bir vaqtda: yangi, editorial, V1 | "Boshqa saytga o'tgandek" uzilish | Sahifa guruhlari to'liq bosqich bilan yoqiladi; S10 dan oldin serverda yoqilmaydi |
| Eskizda bor, kodda yo'q funksiya shablonga kirib qoladi | Ishlamaydigan tugma, yolg'on va'da | Shablon faqat kontekstdagi ma'lumotni chizadi; §7 jadvali har PR review'da tekshiriladi |
| Yangi sahifa ko'proq ma'lumot ko'rsatadi | So'rovlar ko'payadi | Har sahifaga so'rov byudjeti testi; yangi maydon faqat mavjud selector orqali |
| S10 gacha har sahifaning 2–3 shabloni | Bitta tuzatish bir necha joyda | Bosqichlar qisqa; S10 tozalashi kechiktirilmaydi |
| Namuna ma'lumot kodga o'tadi | Saytda soxta raqam yoki narx | Shablonda literal raqam va narx yo'q |
| Mini-ilova ramkasi Telegram webview'da ishlamaydi | Mini rejim ochilmaydi | S9 haqiqiy qurilmada; ishlamasa D7 alohida mini sahifalarga qaytadi |
| Owner qabuli kechikadi | Bosqich tugamaydi | Ish flag ortida kutadi; keyingi mustaqil bosqich boshlanaveradi |

## 10. Keyingi qadam

- [x] D1–D4: owner eskiz dizayn tizimini tanladi (2026-11-07).
- [x] DASH1.0a `main`ga qo'shildi (PR #252, `6dff8c4`, 2026-11-08) — D5 darvozasi.
- [x] S0: shu reja, README, PORT-LEDGER, PUBLIC-02 va marinebook yozuvi — branch `claude/design-02-plan`.
- [ ] Owner eskizdagi qorong'i rejimni ko'radi (D8) — S1 darvozasi.
- [ ] S1 — shu branchda (`claude/design-02-plan`): flag, `calm_template_names`, `CALM` renderer qiymati, "Sokin"
  varianti va matn oralig'i, Figtree, `calm.css` va `calm.test.mjs`. Tugash mezoni: flag OFF'da hech bir sahifa
  baytda o'zgarmaydi.
