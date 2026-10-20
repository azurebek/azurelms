# PUBLIC-01 — qulaylik (a11y) qabuli: dalillar va ochiq bandlar

**Holat:** PUB1.7c (2026-10-20). Bu hujjat [PUBLIC-REFORM-PLAN §6.9](PUBLIC-REFORM-PLAN.md) matritsasining
rost holati. Qoidasi: avtomatik yoki agent brauzerida tekshirilgan band **PASS** (qachon, nima bilan);
qurilma, ekran o'quvchi yoki owner talab qiladigan band bajarilmaguncha **OPEN** — "axe 0" uning o'rnini
bosmaydi.

## 1. Avtomatik (CI) — har PR'da

| Tekshiruv | Qamrov | Natija | Qulf |
|---|---|---|---|
| Statik a11y qoidalari (axe critical/serious'ning HTML'dan aniqlanadiganlari: `html-has-lang`, `document-title`, `meta-viewport`, bitta `h1`, bitta `main`, aktiv `duplicate-id`, `label`/`label-for`, `image-alt`, `link-name`, `button-name`, `aria-valid-ref`, musbat `tabindex`, `aria-hidden-focus`, `nested-interactive`, `javascript:` havola) | 21 sahifa × legacy/V1 × mehmon/kirgan: bosh, about, katalog, kurs, tariflar, Blog ro'yxati/maqola (izoh bilan), SIT bosh/katalog/universitet/qo'llanma, maxfiylik, shartlar, sertifikat tekshiruvi, kirish, ro'yxat, parol tiklash (+ yuborildi), texnik ishlar, oflayn, 404 | **0 topilma** | `frontend/test_public_a11y.py::ProbeTests`; probe o'zi ham sinovda (`ProbeSelfTests`) |
| Ichki `#…` havolalar maqsadi | ayni sahifalar | **0 o'lik havola** | `ProbeTests` |
| JavaScriptsiz asosiy yo'llar (sahifadagi formaning o'zi bilan) | katalog qidiruvi → kurs; Blog qidiruvi → maqola (izohlar ko'rinadi); SIT shahar filtri; kirish; parol tiklash; izoh yozish (CSRF bilan) | **PASS** legacy va V1 | `NoScriptJourneyTests` |
| Xira matn kontrasti (dizayn mavzusi nashr qilinmagan holat) | legacy `--ink-3/--ink-4`, SIT, design runtime zaxira ranglari | yorug' `#626b79` ≥4.76:1, qorong'i `#868e9d` ≥4.84:1 | `CssContractTests` |
| Fokus ko'rinishi, harakatni kamaytirish, forced-colors qoidalari CSS'da | V1 base, legacy public, SIT, holat sahifalari | **PASS** | `CssContractTests` |
| Telefon nishon o'lchami (WCAG 2.5.8) | legacy public shell | **PASS** (avvaldan) | `core/test_public_shell_tap_targets.py` |
| Asset/CDN | — | tashqi shrift/ikonka 0 | `frontend/test_public_budgets.py` (PUB1.7b) |

## 2. Agent brauzerida (DB nusxasi, 2026-10-20) — axe-core 4.10.3

axe-core preview serverda vaqtincha berildi (repo'ga kirmadi); qoidalar: `wcag2a, wcag2aa, wcag21a,
wcag21aa, wcag22aa, best-practice`, haqiqiy maket bilan (rang kontrasti ham).

| Holat | Sahifalar | critical/serious | moderate |
|---|---|---|---|
| V1, qorong'i | bosh, about, katalog, kurs, tariflar, Blog, maqola, SIT bosh/katalog, maxfiylik, FAQ, kirish, ro'yxat, parol tiklash, texnik ishlar | **0** | kurs: `aside` boshqa landmark ichida → **tuzatildi** (nomlangan `section`, kurs va SIT sahifasida); maqola va FAQ: matndagi sarlavha darajasi sakraydi (kontent) |
| V1, yorug' | bosh, kurs, maqola, kirish, tariflar, texnik ishlar | **0** | yuqoridagi bilan bir xil |
| Legacy, yorug' | bosh, about, katalog, kurs, tariflar, Blog, maqola, SIT bosh/katalog, maxfiylik, FAQ | **SIT: 15 + 4 rang kontrasti** (`#8a92a0` ≈ 3.05:1) → **tuzatildi**, qayta yugurishda 0 | `heading-order` (about kartalari, katalog kartasi, SIT qadamlari, FAQ, maqola) |
| Legacy, dizayn mavzusisiz (production taxmini) | Blog, bosh, kurs, tariflar, kirish | **0** (tuzatishdan keyin) | — |
| Legacy, qorong'i | SIT bosh/katalog, Blog | **0** (tuzatishdan keyin) | `heading-order` |

**Reflow 320 CSS px** (gorizontal siljish): legacy katalog **338px edi** (karta setkasi
`minmax(320px,1fr)`) → barcha legacy setkalar `minmax(min(Npx,100%),1fr)` → **0**. Tekshirilgan:
legacy bosh, about, katalog, kurs, tariflar, Blog, maqola, SIT bosh/katalog, maxfiylik, FAQ, kirish,
ro'yxat, texnik ishlar; V1 bosh, about, katalog, kurs, tariflar, Blog, maqola, SIT katalog, kirish,
ro'yxat, FAQ — hammasi `scrollWidth = 320`.

**Klaviatura (namuna):** V1 katalogda birinchi Tab — "Asosiy mazmunga o'tish" (`#main`), ko'rinadigan
fokus (outline); keyingi elementlar ham outline bilan.

## 3. Ochiq bandlar (OPEN — bajarilmagan, PASS deb hisoblanmaydi)

| Band | Nega ochiq | Kim/qanday |
|---|---|---|
| NVDA + Chrome/Firefox (Windows) | ekran o'quvchi bilan qo'lda o'tilmagan | owner yoki tester; asosiy yo'llar: katalog → kurs → kirish, Blog → izoh, parol tiklash |
| VoiceOver + Safari (macOS/iOS) | qurilma yo'q | owner qurilmasi |
| TalkBack (Android) | qurilma yo'q | owner qurilmasi |
| 200%/400% zoom, 200% matn, maxsus matn oralig'i (WCAG 1.4.12) | faqat 320px reflow tekshirildi | brauzer zoom bilan qo'lda |
| To'liq klaviatura yo'li (har sahifa, fokus tartibi va yashirinmasligi) | faqat namuna | qo'lda, har asosiy yo'l |
| Windows yuqori kontrast / forced colors | faqat CSS qoidasi bor, ko'rib chiqilmagan | Windows sozlamasi bilan |
| Save-Data | avtoplay media yo'q; alohida xatti-harakat yo'q | PUB1.8 o'lchovi |
| Uzun o'zbekcha matn, turkcha so'z talaffuzi (`lang="tr"` qismlar) | kontentga bog'liq | kontent muharrirlari bilan |
| `heading-order` (moderate) | legacy kartalari va kontent sarlavhalari | legacy/kontent kesimlarida |
| Haqiqiy foydalanuvchi qurilmalari (owner telefoni) | — | owner |

## 4. Qayta yugurish

- CI: `python manage.py test frontend.test_public_a11y frontend.test_public_budgets`.
- Brauzer: axe-core'ni sahifaga yuklab `axe.run(document, {runOnly: {type: 'tag', values: [...]}})`;
  320px uchun `document.documentElement.scrollWidth` ≤ 320. Natijani shu hujjatga sana bilan yozing.
