# BACKOFFICE-02 / B2.5 — dizayn sozlamalari ichki formalarda

Sana: 2026-10-13. Tayanch: `1107302` (B2.4). Ownerning «davom et»
topshirig‘i bilan mavjud dizayn sozlamalari eski boshqaruv formalariga
ulandi. Admission: [yagona reja §11](BACKOFFICE-REFORM-PLAN.md#backoffice-02).
Holat: **B2.5 lokal texnik tekshiruvdan o‘tdi**. Owner/native/production
qabuli va B2.6 birgalikdagi sifat tekshiruvi alohida qoladi.

## Natija

- Imtihon, kutubxona, tarif, guruh, blog, universitet, e’lon va qo‘llanma
  formalarida mavjud matn, tugma/maydon/karta shakli va oraliq sozlamalari
  qo‘llanadi. Shu sozlamalar yagona yangi boshqaruv qobig‘ida ham, mavjud
  eski qobiqda ham o‘qiladi.
- Oddiy dizayn ustaxonasining **Shakllar** qismida **Maydonlar** tanlovi bor:
  odatdagi, tekis, yumshoq yoki yumaloq. Bu mavjud `field-radius` maydonini
  o‘zgartiradi; alohida yangi sozlama yoki boshqa saqlash manbasi yaratilmagan.
- **Boshqaruv formasi** namunasi imtihon muharririning haqiqiy klasslari va
  bazaviy uslublarini ishlatadi. Matn, maydon, karta, ochiladigan qo‘shimcha
  qism va saqlash tugmasining ko‘rinishi shu yerda tekshiriladi.
- Namuna haqiqiy forma emas: maydonlar o‘qish uchun, tugma `type="button"`,
  mazmun sinov matni. Bosish haqiqiy imtihon yoki boshqa kontentni saqlamaydi.

## Shartnoma

`core/design_catalog.json`dagi mavjud **87 typed sozlama**, `design_schema`
va `design_service` yagona manba bo‘lib qoladi. Published CSS va brauzerdagi
preview bir xil katalogni iste’mol qiladi. Yangi theme engine, erkin CSS,
model, migration, provider yoki kontent writeri qo‘shilmagan.

`static/backoffice/design-runtime.css`dagi adapter faqat `.bo-editor`ning
belgilangan beshta ildiz oilasiga ulanadi:

| Forma | Ildiz / asosiy iste’molchilar |
|---|---|
| Imtihon | `.bo-exam-editor`, `.bo-editor-section`, `.bo-editor-save` |
| Kutubxona | `.lib-editor`, `.bo-card`, `.lib-primary`, `.lib-action` |
| Tarif va guruh | `.catalog-form.bo-editor`, `.brand-input`, `.catalog-save` |
| Blog | `.blog-editor`, `.content-editor-field`, `.content-editor-button` |
| SIT universitet/e’lon/qo‘llanma | `.sit-bo-wrap`, `.sit-bo-form-section`, `.sit-bo-btn` |

Tarif/guruhning karta ildizi `.bo-editor`ning o‘zi; sarlavha esa undan oldingi
`.brand-hero`. Ikkalasi shu formaga chegaralangan selector bilan qamrab olinadi.
Mavjud `--dc-text-*` aliaslari qiymat berilgandagina chiqadi; bo‘sh qiymat
har formaning avvalgi bazaviy o‘lchami va responsive qoidasini saqlaydi.
Bu parity yakuniy brauzer tekshiruvida alohida solishtirildi.

Density bo‘limlar orasidagi bo‘shliqni, card padding esa kartaning ichki
bo‘shlig‘ini boshqaradi. Kutubxonadagi edge-to-edge foydalanish ro‘yxatining
inline `padding:0` qoidasi va maxsus sidebar oralig‘i saqlanadi; asosiy
tahrirlash kartasi hamda ustunlar oralig‘i sozlamalarga ulanadi.

Runtime adapter `@media screen` ichida, unda `!important` yo‘q. Mavjud mobile
qobiqning `!important` matn qoidasini yengish uchun `legacy-workspace.css`da
faqat shu editor oilalariga tegishli screen/mobile override bor; sozlama
bo‘sh bo‘lsa avvalgi `max(1rem,16px)` o‘qish chegarasi qoladi. Checkbox,
radio, range, hidden maydon va `.ck` ichki boshqaruvlari bu mappingdan
chiqarilgan. Print va vendor muharrir ichki UI bu bosqichga kirmaydi.

Preview alohida legacy CSS boshini ishlatadi; boshqa V1 namunasining
selectorlari unga aralashmaydi. Mavjud bo‘sh `sandbox`, CSP va
`no-referrer` saqlangan. Namuna sahifasida script, yuboriladigan form,
nomlangan editable maydon yoki tashqi kontent amali yo‘q.

Design saqlash/nashr/rollback ruxsati, revision, sabab, tasdiq va audit
oqimlari avvalgi `design_service` orqali qoladi. Kontent sahifalaridagi
saqlash handlerlari, baholash, ruxsat va biznes qoidalari o‘zgarmagan.

## Tekshiruv dalili

Muhit: `AZURELMS_SKIP_ENV_FILE=1`, `APP_ENV=local`,
`LOCAL_USE_REMOTE_SERVICES=False`, `GEMINI_API_KEY` va
`TELEGRAM_BOT_TOKEN` bo‘sh.

```powershell
venv/Scripts/python.exe manage.py test core.test_design_views core.test_design_service core.test_design_runtime core.test_frontend_v1_editors core.test_backoffice_catalog_navigation core.test_sidebar_reaches_blog_and_sit --verbosity 1
node --test tests/frontend_v1/*.test.mjs
venv/Scripts/python.exe manage.py check
```

- Django: **112 test / 110 PASS / 2 PostgreSQL skip**, 7.074s, exit 0.
  Mavjud schema/service/runtime va editor/navigation contractlari; yangi
  inert preview testi haqiqiy kontent yuborilmasligini hamda GET hech bir
  design yozuvini yaratmasligini tekshiradi.
- Node: **171/171 PASS**, skip 0. Check: 0 muammo.
- Yakuniy CSS tuzatishidan keyin `venv/Scripts/python.exe manage.py test
  core.test_design_runtime core.test_design_views --verbosity 1`:
  **23/23 PASS**, 5.754s. `git diff --check`: PASS.

IAB synthetic nusxa: `.tools/backoffice-b25/demo.sqlite3`, port **8103**.
Asosiy bazaga sinov kontenti kiritilmaydi. Eski library rendererini
tekshirish uchun fixtureda `frontend_v1_library` OFF; Telegram yuborish OFF.

Sakkiz forma tekshirildi: exam, library, plan, cohort, blog, university,
announcement, guide. Yangi qobiqda 1440px yorug‘, 1280px qorong‘i, 320px
va 200% rendered text holatlari ko‘rildi. Eski qobiqda ham sakkiz formaning
published qiymatlari mos; design flag OFFda sakkiztasida statik ko‘rinish
va runtime CSS havolalarining yo‘qligi tasdiqlandi. CKEditor tugmasining
ichki ko‘rinishi o‘zgarmadi.

Synthetic **nashr 6** computed dalili: maydon matni 18px, burchagi 12px,
padding 14px; tugma burchagi 32px; karta burchagi 16px va padding 24px.
2px chegara browser pixel rounding sabab computed ko‘rinishda 1.6px
bo‘lib qaytgan; bu sozlama yo‘qolishi deb hisoblanmagan.

Mahalliy rasmlar/loglar Gitga kirmaydi: `.tools/backoffice-b25/` ichida
`studio-editor-preview.png`, `exam-light-published.png`,
`sit-mobile-text200.png`, `guide-mobile-form-text200.png`,
`final-focused.log`, `node-tests.log`, `check.log`.

**Yakuniy dalillar:**

- Asl Azure sinov nashri 7 bilan eski `HEAD` runtime CSS va yangi CSS bir
  xil sahifalarda taqqoslandi. Unified 1440/320pxda sakkiz forma bo‘yicha
  **391 element**ning font/family/weight/leading/radius/padding/gap/border/
  shadow qiymatlarida farq 0. Eski qobiq ham solishtirildi; topilgan exam
  va SIT farqlari tuzatilgach ayni elementlarda qayta tasdiqlandi.
  Taqqoslash faqat synthetic GET query orqali eski CSS nusxasini ulaydi;
  mahsulotda bunday endpoint yoki flag yo‘q.
- Review va computed tekshiruvda topilgan sarlavha leading, library
  help/disclosure fallback, exam label/button leading va SIT heading
  weight farqlari tuzatildi. Ownerning explicit qiymatlari ustuvor qoladi.
- Brauzer orqali nashr 7 dan **nashr 5** qiymatlariga rollback yangi
  **nashr 8** sifatida yozildi. Sakkiz formada field computed qiymatlari
  boshlang‘ich bilan teng, button radius17/card radius0 qaytdi. Published
  qiymatlarning to‘liq fingerprinti original bilan teng; qoralama saqlandi.
- Kontent/brend: **82 jadval / 184 qator**, oldin/keyin hash teng.
  Logo va kontent dizayn nashri yoki rollback bilan o‘zgarmadi.
- Yangi namuna 320px tashqi sahifada 243px iframe ichiga sig‘di; overflow0.
  `browser-evidence.json`da bosqichlar bo‘yicha computed dalil saqlangan.
- Primary lokal rollback smoke: dizayn + sakkiz forma + ikki CSS —
  **11 HTTP200**. **149 jadval / 1316 qator** hash teng. Vaqtinchalik
  login/GET initializer/recent yozuvlari rollback ichida; auth, flag yoki
  sinov kontenti saqlanmadi. Dalil: `.tools/backoffice-b25/local-smoke-report.json`.
- Required CI va PR review integratsiya gate’i; yashil bo‘lgach standing
  workflow bo‘yicha merge qilinadi. Native/production qabuli deb hisoblanmaydi.

## Flaglar va chegaralar

Mavjud `backoffice_design_workspace` OFF statik ko‘rinishni qaytaradi.
Versiya rollback’i faqat dizayn nashrini almashtiradi; logo yoki platforma
kontentini tahrirlash bu writerning vazifasi emas. Primary lokal bazadagi
mavjud dizayn nashri saqlanadi; nashr va rollback sinovi synthetic nusxada.

Bu ish belgilangan ichki formalar bilan chegaralangan. Butun saytning
barcha eski sahifalari, vendor toolbar, print, native host yoki yangi
kontent yaratish imkoniyatlari avtomatik qamrab olindi degan claim yo‘q.
200% rendered text native brauzer zoom yoki haqiqiy telefondagi sinov emas.

Owner usability, native telefon/zoom/AT va production qabuli alohida.
**B2.6 — birgalikdagi sifat tekshiruvi** keyingi kesim; ushbu qayd uni
yopmaydi.
