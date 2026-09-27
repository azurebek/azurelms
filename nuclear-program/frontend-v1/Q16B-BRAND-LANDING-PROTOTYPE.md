# Q16b — brend va landing lokal prototipi

2026-09-27, D31 continuation; source base `bebd56c`,
branch `codex/q16b-brand-landing-prototype`. **Faqat lokal prototype**;
haqiqiy public sayt, global logo, DB, provider va AWS o‘zgarmadi.

## Tayyor qamrov

| Band | Canonical URL name | Mahalliy manzil |
|---|---|---|
| U20 | `backoffice_brand` | `/backoffice/control/brand/` |
| U21 | `backoffice_landing` | `/backoffice/landing/` |

Preview: `http://127.0.0.1:8076/backoffice/landing/`.
Registry `0.71.0-brand-landing`: **118 URL /65 page template /97 source
nomi /1050 route-state /189 action**. `?sample=saved` qo‘shimcha canonical
UI emas, shu ikki muharrirning read-only holati.

- Brend:7 source field,4 rasm o‘rni, preserve/replace/clear va fallback.
- Landing:60 source field/9 bo‘lim; bo‘limlar ochilib yopiladi, lekin
  source kabi hammasi bitta tasdiqli forma bilan saqlanadi.
- Qoralama preview yozmaydi; saqlangan sample joriy sintetik qiymatni
  o‘qiydi. Ikkalasi bitta presentation include’dan foydalanadi.
- Mavjud platform/backoffice shell, rang/shrift/breakpoint va ops
  transport reused. Native POST→303→exact receipt, reason/consent,
  before/after/audit/no-op, revision/run/payload replay guards.
-4 raster haqiqiy lokal multipart bilan sinaladi:PNG/JPEG/WebP, source
  5MiB, local4096px/1024px sample/1MiB encoded guard. Original disk/cloudga
  yozilmaydi. Receipt faqat nom/hash saqlaydi, baytlarni ko‘paytirmaydi.
- Matn drafti run/route/revisionga bog‘liq; consent/file/clear tiklanmaydi.
  Error yoki reload’dan keyin fayl qayta tanlanadi, avtomatik resend yo‘q.

## Source xaritasi

`core/views.py:backoffice_brand` + `core/brand_forms.py` →
`frontend/models.py:SiteSettings`; `backoffice_landing` +
`core/landing_forms.py:LANDING_SECTIONS/LandingPageForm` → `LandingPage`.
Static AST extractor label/default/type/required/max_lengthni import yoki
DBsiz oladi; fixture source bilan exact-match testdan o‘tadi.

Canonical mutation sababi/tasdig‘i va no-op talabi saqlandi. Previewdagi
stale/UUID/readback — UI kontrakti; hozirgi real view bu qo‘shimcha
kafolatlarning hammasiga ega degani emas. Integratsiyada alohida tekshiriladi.
`demo_progress` source PositiveSmallInteger0..32767; frontend yangi0..100
siyosatini ixtiro qilmadi. Qoralama matnlariga HTML sifatida ishonilmaydi.

Public sample — kontent tekshiruvi: hero dizayn namunasi va qolgan
source maydonlarning belgilangan proyeksiyasi. Existing `/` yoki legacy
landingning pixel-identical nusxasi emas. Source marketing matnlari
capability/quality da’vosiga dalil bo‘lmaydi. Hero HTML plain-text escaped;
formatlash/sanitizer/real public layout ulanishi alohida portda.
Fon/video, kontent kartalari, navigatsiya CRUD source formga kirmaydi;
bu paket ularga fake boshqaruv qo‘shmadi.

## Tekshiruv

Trial cwd; `AZURELMS_SKIP_ENV_FILE=1`, bo‘sh GEMINI_API_KEY va
TELEGRAM_BOT_TOKEN, LOCAL_USE_REMOTE_SERVICES=0; repository venv.

| Buyruq/dalil | Natija |
|---|---|
| `manage.py check` |0 issue |
| `manage.py test tests --verbosity 1` | **710 PASS,267.037s** |
| Final CSS-only highlight correctiondan keyin `manage.py test tests.test_appearance tests.test_operations --verbosity 1` | **52 PASS,21.967s** |
| `node --test <expanded tests/*.test.mjs>` | **182 PASS** |
| `node --check prototype/static/js/appearance.js` | PASS |
| IAB2 editor +2 saved sample ×5 width ×2 theme | **40 cases, overflow0, control≥44px** |
|320px barcha9 section ochiq,61 field including reason | overflow0, control≥44px |

Browser native brand/landing save→exact receipt→saved sample, image
chooser→blob preview→save→decoded sample, draft reload/unchecked consent,
validation422/input retention, long text PASS. Final error/warn log empty.
Screenshot Windows IAB Chromium; actual phone/Safari/AT NOT TESTED.

Topilgan va yopilgan xatolar:28-field parser full60-field formni rad etdi;
admitted full form uchun80-field/128KiB bounded transport kerak bo‘ldi.
Brand4-file, boshqa yo‘llar1-file handler guardni saqlaydi. Oversize
StopUpload signali dastlab no-opga tushgan —422/no-write regression bilan
yopildi. Native bo‘sh file control text partlari alohida qabul qilinadi.
Hero highlight link typography classi o‘rniga lokal semantic rang classi
ishlatildi; global style o‘zgarmadi. Testlar/gate’lar susaytirilmadi.

## Zaxira va ochiq ishlar

Ignored trial: `playground/Eleventh Trial/checkpoints/packet-71-20260927-043621.zip`.
**529 fayl**, har source/archive entry SHA256 tengligi tekshirilgan.
SHA256 **`1A730FEF86F7B6B455FD7152FF7B2B975AFF1BF3FA3A411D807CED80566911CD`**.
Old Packet70 o‘chirilmagan. Gitga faqat hujjatlar; ignored source/rasmlar
force-add, push yoki upload qilinmadi.

Local dalil `evidence/PACKET-71-RESULTS.md`, screenshots
`q16b-desktop-light.png` / `q16b-mobile-dark.png`. Real RBAC/media/audit/
durable replay, rich-text/public layout, native/owner acceptance va G2/G3
ochiq. **U17/A2-D01 va kengQ14 authoring alohida ochiq.**

Qoldiq **21 UI +3 handler =24 band,6 qadam**. Keyingi **Q17a blog studiyasi,
3 UI**. Real port va AWS release qoldiq prototype hisobidan alohida.
