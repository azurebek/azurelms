# PUBLIC-02 — editorial public dizaynini production'ga ko'chirish rejasi

**Holat — 2026-10-28: reja yozildi, implementatsiya boshlanmagan.** Manba — owner bilan qurilgan lokal
prototip `playground/Thirteenth Trial/` (2026-10-21…28). `playground/` git'ga kirmaydi: prototip faqat shu
kompyuterda. Shu sabab birinchi kod kesimi (PE1) uning normativ qismini (CSS qoidalari va tekshiruvi) repo'ga
olib kiradi; ungacha `playground/Thirteenth Trial/` o'chirilmaydi.

Bu reja PUBLIC-01 ([PUBLIC-REFORM-PLAN.md](PUBLIC-REFORM-PLAN.md)) xavfsizlik, rostlik va registratsiya
kontraktlarini o'zgartirmaydi. U faqat **ko'rinish va sahifa tuzilishi**ni almashtiradi; har sahifa hozirgi
V1 adapterlaridan keladigan ayni kontekstni chizadi.

## 1. Prototip nimani isbotladi

| Isbotlangan | Dalil (prototipda) |
|---|---|
| 18 ochiq sahifa + o'quv maydoni bitta tizimda: bosh sahifa, kurslar, kurs, tariflar, Azure Journal, maqola, SIT (bosh, ro'yxat, universitet, qo'llanma), biz haqimizda, shartlar, maxfiylik, savol-javob, kirish, ro'yxat, parolni tiklash (2 bosqich) | `src/`, `tools/build.py`, `routes.json` |
| Yangi narsa faqat production tokenlaridan: xom rang, literal o'lcham, yangi shrift, yangi breakpoint, production klassini tashqaridan o'zgartirish yo'q | `verify.mjs` (8 test; ~34 ataylab buzish bilan sinalgan) |
| Ochiq sahifa → kirish → o'quv maydoni: logo x/y/balandlik va header chizig'i ±1px, 1920 → 320px; mavzu tanlovi o'tadi | `tools/continuity.mjs`, CONTRACT.md §5 |
| 21 manzil × 320/390px gorizontal toshish 0; yorug'/qorong'i mavzu | `tools/shot.mjs` |
| Burchaklar owner sozlamasiga ergashadi (DESIGN-01 "Karta → Burchak"; karta burchagi 0 bo'lsa hammasi tekis) | `preview-radius.png` |

**Isbotlanmagan:** haqiqiy ma'lumot (matn, raqam, narx namuna), formalar (prototip POST'ga 501 beradi),
legacy renderer, ekran o'quvchi va haqiqiy qurilma. Sinab ko'rilib rad etilgan: o'quv maydoniga "ko'prik"
media (2026-10-28, owner: keragi yo'q) — o'quv maydoni o'z ko'rinishida qoladi.

## 2. Feature admission

1. **Muammo:** ochiq sahifalar bir xil to'rtburchak kartalardan iborat, kirish sahifasi butunlay boshqa
   ramkada — sayt va o'quv maydoni orasida "boshqa saytga o'tgandek" uzilish bor.
2. **Asosiy KPI:** kurs sahifasidan xarid niyatigacha o'tish ulushi (`public_funnel_report`, PUB1.8a).
   Taqqoslash uchun `public_telemetry_v1` yoqilib, eski dizaynda kamida 2 hafta baseline yig'iladi.
3. **Canonical state:** o'zgarmaydi. Yagona yangi yozuv — DESIGN-01 ustaxonasidagi bitta ixtiyoriy maydon
   (`--dc-shape-radius`), mavjud auditli qoralama → nashr oqimi orqali (`core/design_service.py`).
4. **Adapterlar (faqat iste'mol qiladi):** V1 public shablonlari, V1 auth shablonlari, o'quv maydoni shell'i
   (`platform.html`, `shell.css`, `shell.js`). Kontekst `frontend/public_content.py`, `courses/public_offer.py`,
   `frontend/public_claims.py`, `sit/public.py`, `blog/listing.py`, `frontend/legal_revisions.py`dan — yangi
   selector yoki dublikat hisob yo'q.
5. **Owner yuki:** oshmaydi. Rasm yuklash ixtiyoriy — rasm bo'lmasa token-asosli fon chiziladi.
6. **Flag va rollback:** `public_editorial_v1` (default OFF). OFF — hozirgi V1 public, auth va shell aynan
   bugungidek. Kontent, tarif, kirish va ma'lumotga tegilmaydi.
7. **Taklif qilingan status: `ADMIT — post-launch`.** Owner pilotdan oldin xohlasa, minimal to'plam: PE1–PE3 va PE8.
   Yakuniy status owner qarori.

## 3. Owner qarorlari (PE1 dan oldin)

| # | Savol | Tavsiya (agent) | Ta'siri |
|---|---|---|---|
| D1 | To'q footer va to'q bandlar (`--az-inverse` oilasi) qabul qilinadimi? | Ha — prototipning hamma sahifasida sinalgan, kontrast AA | Footer, tanlash bandi, kirish yon paneli |
| D2 | Logo balandligi | `2.5rem` (header 4rem ichida). Brend kiti gorizontal logo uchun ≥160px kenglik tavsiya qiladi, bu yerda ~112px — kattaroq kerak bo'lsa header ham kattalashadi | Uchala ramka |
| D3 | Asosiy tugma rangi `#1257e6` qoladimi yoki kitdagi `#0078D4`? | `#1257e6` qolsin: oq fonda 5.95:1, `#0078D4` esa 4.53:1 (AA chegarasida) | Butun sayt va ilova |
| D4 | DESIGN-01 "Karta" guruhiga "Urg'u burchagi" maydoni | Ha, bo'sh standart (karta burchagi × 2) | Ochiq sahifa shakllari |
| D5 | Huquqiy yorliq "FAQ" → "Savol-javob" | Ha — footer va sarlavha bilan bir xil | Matn |

Owner'ning menyu sozlamasi (kod emas): footer'ga "Tariflar" havolasini `LandingNavItem` orqali qo'shish.

## 4. Arxitektura

- **Shablon tanlovi bitta joyda.** Hozir ikki nuqta bor: `frontend/public_v1.py::render_public` va
  `PublicFrontendV1Mixin.get_template_names`. PE2 ularni bitta `public_template_names(template)` funksiyasiga
  keltiradi: flag ON bo'lsa `["frontend_v1/editorial/<t>", "frontend_v1/public/<t>"]` — ko'chirilmagan sahifa
  avtomatik hozirgi V1'da qoladi, kesimlar sahifama-sahifa yopiladi. Kontekst (`public_context`) va cache
  sarlavhalari (`patch_cache_control`, PUB1.1d middleware) o'zgarmaydi.
- **Kontekst pariteti.** Editorial shablon hozirgi V1 shablon chizadigan hamma narsani chizadi: preview
  banneri, `messages`, bo'sh holatlar, PUB1.3d niyat izohi, PUB1.5b faoliyat eslatmalari, blog izoh va
  olqish, Telegram paneli, forma xatolari xulosasi, `auth_register_closed`. Har kesimda mavjud renderer testlari
  editorial bilan ham yuguradi (flag ON).
- **CSS.** Prototipning `public-patterns.css` → `static/frontend_v1/css/public-editorial.css` (faqat flag ON
  sahifalarda yuklanadi — byudjet faqat shu sahifalarga). Taklif tokenlari → `tokens.css`. Uzluksizlik taklifi
  (`production-proposed.css`) → `public.css`, `shell.css`, `shell.js`, `platform.html`, flag ON'da `<html>`dagi
  `data-editorial` atributi bilan cheklangan; tozalash kesimida (PE10) cheklov olib tashlanadi.
- **Tizim qoidasi CI'da.** `verify.mjs`dagi token qoidalari `tests/frontend_v1/public-editorial.test.mjs`ga
  ko'chadi (CI'dagi Node bosqichi allaqachon `tests/frontend_v1/*.test.mjs`ni yuguradi).
- **Legacy renderer** (`frontend_v1_public` OFF) o'zgarmaydi.

## 5. Prototip → production xaritasi

| Prototip | Production | Kesim |
|---|---|---|
| `css/tokens-proposed.css` (`--az-inverse*`, `--az-logo`, `--az-radius-tile`, `--az-radius-shape`) | `static/frontend_v1/css/tokens.css`; `core/design_catalog.json` S14'ga `--dc-shape-radius` | PE1 |
| `css/public-patterns.css` (holatlar sahifasiga xos `p-public-catalog-*` ko'chmaydi) | `static/frontend_v1/css/public-editorial.css` | PE1 |
| `verify.mjs` token/breakpoint/selector qoidalari | `tests/frontend_v1/public-editorial.test.mjs` | PE1 |
| `tools/build.py` header/footer/logo | `templates/frontend_v1/editorial/base.html`, `components/brand_logo.html` (gorizontal, mavzu bo'yicha) | PE2 |
| `src/home.html`, `src/about.html` | `editorial/index.html`, `editorial/about.html` | PE3 |
| `src/courses.html`, `src/course.html`, `src/pricing.html` | `editorial/courses/course_list.html`, `course_card.html`, `course_detail.html`, `subscriptions/pricing.html` | PE4 |
| `src/journal.html`, `src/article.html` | `editorial/blog/post_list.html`, `card.html`, `post_detail.html` (izoh/olqish bilan) | PE5 |
| `src/sit.html`, `universities.html`, `university.html`, `guide.html` | `editorial/sit/home.html`, `university_list.html`, `card.html`, `university_detail.html`, `knowledge_detail.html` | PE6 |
| `src/terms.html`, `privacy.html`, `faq.html` (`p-public-doc` mundarija) | `editorial/legal_page.html` + mundarija selectori | PE7 |
| `src/login.html`, `register.html`, `reset.html`, `reset-done.html` | `frontend_v1/login.html`, `auth_base.html` va 6 auth shabloni — ochiq sahifa ramkasida | PE8 |
| `production-proposed.css` (sidebar logo qatori, topbar logosi, 1024 → 1200px) | `shell.css`, `shell.js`, `platform.html`, `public.css` | PE9 |

## 6. Kesimlar

Har kesim alohida `claude/` branch va PR; CI uchala job yashil bo'lmaguncha merge yo'q. Flag butun ish davomida
OFF — production ko'rinishi PE10 gacha o'zgarmaydi.

**PE0 — shu reja** (docs-only).

**PE1 — poydevor.** Tokenlar (D1–D3 qaroriga ko'ra), DESIGN-01 maydoni (D4; katalog, sxema validatsiyasi,
preview), `public-editorial.css`, `public_editorial_v1` flagi (registr + runbook), Node qoida testi.
*Test:* `core` dizayn testlari, `node --test tests/frontend_v1/*.test.mjs`, `manage.py check`.
*Tugashi:* flag OFF'da hech bir sahifa baytda o'zgarmaydi (snapshot); ustaxonada yangi maydon qoralama → nashr
→ qaytarish bilan ishlaydi.

**PE2 — umumiy ramka.** `public_template_names`, `editorial/base.html` (to'liq kenglikdagi header, inverse
footer bandi, gorizontal logo komponenti), PUB1.2d owner menyusi o'zgarmaydi.
*Test:* `frontend.test_public_shell`, `test_public_responsive`, `test_public_v1`, `core.test_brand_control`,
`core.test_public_shell_tap_targets`, `test_public_a11y`, `public-header.test.mjs`; flag ON/OFF matritsasi.

**PE3 — bosh sahifa va "Biz haqimizda".** Hero, yangiliklar qatori, raqamlar (faqat PUB1.2a dalili bilan; dalil
yo'q bo'lsa band chiqmaydi) + tanlash bandi, Journal spotlight, SIT bandi; about: maqsad/qarash, jamoa.
*Test:* `test_public_content` so'rov byudjetlari, da'vo/fikr rostlik testlari, a11y probe.

**PE4 — katalog, kurs, tariflar.** Kurs kartasi muqovasi, kurs sahifasi (telefonda birinchi ekran taklifi
saqlanadi), tariflar: kurs tanlashga olib boradi (PUB-D1), "Ommabop" PUB1.4a gacha yo'q, qaytarish/uzaytirish
matni yo'q, davr taklifdagi `period_days` bilan.
*Test:* `courses` public offer/intent testlari, PUB1.3 byudjetlari, `subscriptions`.

**PE5 — Azure Journal.** Ro'yxat (spotlight + qator), maqola (muallif qatori, muqova, izoh va olqish).
*Test:* `blog` testlari, PUB1.6a so'rov qoidasi.

**PE6 — Turkiyada o'qish.** Bosh, universitetlar ro'yxati (`p-public-facets` — yetti filtr), universitet
(telefonda qabul xulosasi), qo'llanma (`p-public-doc` mundarija bilan).
*Test:* `sit` testlari, PUB1.6b adapter qoidasi.

**PE7 — huquqiy sahifalar.** `p-public-doc`: mundarija owner matnidagi h2'lardan **server tomonida**,
sanitizatsiyadan keyin (`PUBLIC_EDITORIAL_V1` profili o'zgarmaydi; id'lar xavfsiz slug, takrorlanmaydi).
Nashr qilinmagan holat (503) mundarijasiz. Yorliq D5.
*Test:* mundarija selectori unit testlari (bo'sh, takror sarlavha, injection), `frontend` legal testlari.

**PE8 — kirish, ro'yxat, parolni tiklash ochiq sahifa ramkasida.** `login.html` va `auth_base.html` editorial
ramkada; yon panel `data-surface="inverse"`. Formalar, CSRF, PUB1.4b xato modeli, Telegram paneli, faoliyat
eslatmalari va `reset_unavailable` (PUB1.0f) o'zgarmaydi.
*Test:* `users` auth testlari, `test_form_origin`, `login.test.mjs`, `auth-validation.test.mjs`, auth byudjeti.

**PE9 — o'quv maydoni uzluksizligi.** Sidebar logo qatori header balandligida, tor ekranda logo topbar'da,
sidebar 1024 → 1200px (`shell.css` + `shell.js` `matchMedia`) — owner qarori 2026-10-25 (b-variant).
*Test:* yangi `tests/frontend_v1/shell.test.mjs` (breakpoint), `users.test_frontend_v1`; uzluksizlik o'lchovi
(Chrome bilan, lokal dalil) 1440/1199/1024/390px.

**PE10 — rollout va tozalash.** Lokal DB nusxasida flag ON: owner ko'rib chiqishi, a11y probe, byudjet qayta
o'lchovi, 320/390px toshish, haqiqiy telefon. Serverda flag ON va kuzatuv (KPI baseline bilan). Owner qabulidan
keyin alohida PR: eski V1 public shablonlari, `data-editorial` cheklovi va flag olib tashlanadi.

## 7. Byudjet va riskler

- **CSS byudjeti:** prototip fayllari gzip'da ~4.3 KB qo'shadi (V1 ochiq sahifa 6.8 → ~11.1 KB; byudjet 9.1 KB).
  PE1 `public-editorial.css`ni faqat flag ON sahifalarga yuklaydi; PE10'da qayta o'lchab byudjet yangilanadi
  (`frontend/public_budgets.py`, o'lchov + 10%).
- **Ikki V1 shablon to'plami vaqtinchalik.** Shu davrda PUB1.8b2, BLOG-01, SIT-01 kabi ishlar V1 public
  shablonlariga tegsa, editorial nusxasi ham shu PR'da yangilanadi; renderer testlari flag ON'da ham yuguradi.
- **Prototip faqat lokal.** PE1 gacha `playground/Thirteenth Trial/` o'chirilmaydi.
- **Uzluksizlik o'lchovi CI'da yo'q** (Chrome kerak): PE9/PE10 dalili lokal; CI'da breakpoint va markup statik
  testlar bilan qulflanadi.

## 8. Production'da topilgan, rejadan mustaqil xatolar

Bular hozirgi V1'da bor; editorial'ni kutmasdan kichik tuzatish sifatida chiqarilishi mumkin:

1. Yopiq `details.p-public-info-card` pastda ~12px ortiqcha joy qoldiradi (Chrome yashirin `::details-content`
   flex elementi, `gap` qo'shiladi) — kurs dasturi. `public.css`.
2. `p-public-info-card` / `p-public-price-card` ichidagi `c-badge` flex kartada butun kenglikka cho'ziladi —
   `sit/card.html`, `subscriptions/pricing.html`.
3. `.f-study-art` (learning.css) — CSS bor, markup yo'q (o'lik CSS).
4. Tariflar sahifasi davrni "/ oy" deydi, kurs taklifi esa `period_days` (30 kun) bilan.
5. Ro'yxat formasida faoliyat eslatmasi tugmaga oraliqsiz yopishadi (tugmadan keyin turadi).
