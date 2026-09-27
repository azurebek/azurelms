# Q17a — boy matn va inline rasm pariteti

2026-09-27, D31 continuation; base `e18fe10`, branch
`codex/q17a-rich-content-parity`. **Paket73 lokal implementation gate’i
bajarildi; Q17a prototip qadami yakunlandi.** Bu real port, owner/native
G3 yoki AWS release qabuli emas. PR151 ko‘rsatgan rich-text bo‘shlig‘i
scope’dan chiqarilmadi: shu paketda qurildi va tekshirildi.

## Natija

Preview: `http://127.0.0.1:8078/blog/studio/`.
121 route /67 page template /100 source nomi /1077 route-state;
registry `0.73.0-blog-rich`,193 action (+rich edit, +inline upload).
Texnik vendor/render/upload/media endpointlari yangi canonical UI emas.

- Mavjud `django-ckeditor-5`0.2.20 bundle (CKEditor47.5.0), Uzbek tarjima
  va `core/settings.py`dagi default toolbar/image/table config AST orqali
  olinadi. Runtime settings/domain app/DB import qilinmaydi; CDN yo‘q.
- Heading, bold/italic/underline/strike, link, bullet/numbered list,
  quote, table, image, undo/redo → draft → namuna → save → public.
  Body uchun yagona Bleach allowlist; serverdan tozalangan fragmentgina
  preview DOMga qo‘yiladi. Initial/restored HTML ham oldin sanitizatsiyadan
  o‘tadi; async hydration paytida body readonly, typing yo‘qolmaydi.
- Source5MiB raster input/Q16b normalizer; faqat session-memory PNG.
  Image upload maqolani nashr qilmaydi. Run/origin/revision/UUID/digest,
  CSRF/auth/scenario checks; exact retry bir URL, o‘zgargan payload409.
  Local cap32 image/8MiB; invalid/oversize/duplicate/cap no-write.
- Alt/caption/alignment va bounded fractional width saqlanadi. Missing,
  foreign, external/data/blob inline image422; matn bound formda qoladi.
  Draft media signed-out va boshqa sessiondan yopiq; live post media
  shu sintetik sessionning public o‘qishida ochiq. Reset URLni bekor qiladi.
- Pending upload/preview/save gate; data change consentni tozalaydi.
  Stale preview qo‘llanmaydi; pagehide upload abort, avtomatik retry yo‘q.
  No-JS HTML textarea save qoladi; toolbar/upload/draft JSga bog‘liq.
- Blog-only `style-src-attr` vendor geometry istisnosi; script-src self.
  Script/event/SVG/iframe faol HTMLga o‘tmaydi; content CSS faqat bounded
  dimension/alignment. Bu production sanitizer siyosati tasdig‘i emas.

## Desktop va mobil

Existing shell/tokens saqlandi. Toolbar itemlari bir xil, compactda44px
wrap; sticky toolbar matnni yopmasligi uchun faqat bu editorda o‘chirildi.
Table10×10 grid o‘z popupida scroll; page horizontal scroll qilmaydi.
Dark editable text/list markers va mobile alt/link popup widths tuzatildi.
Project CSSga !important/global palette yoki yangi breakpoint qo‘shilmadi.

IAB Chromium tekshiruvi, native phone/Safari/AT emas:

- New/edit/public ×320/390/768/1024/1280 ×light/dark =30 case:
  overflow0, editor toolbar visible buttonlari kamida44×44.
- Native bold,2×2 table→Tab bilan cells, undo/redo; actual synthetic image
  chooser→normalized same-run image, alt, image alignment; formatted HTML
  paste (heading/styles/lists/quote/link), editable caption.
- Draft reload format/image saqladi, consent unchecked; create publish,
  edit save, saved sample/public image/caption/table tasdiqlandi.
- Mobile table popup44px/owned scroll, alt popup bounds tekshirildi.
  Link Insert desktop pointer va320px native AX click bilan ishladi;
  Enter ham ishladi. Mobile locator-click ba’zan fokusni yo‘qotgan:
  fresh AX orqali aynan shu tugma bosilib haqiqiy body o‘zgarishi o‘qildi,
  attempted click success deb hisoblanmadi. Actual touch/keyboard G3 ochiq.
- Final console warning/error0; vaqtinchalik viewport reset qilindi.

## Testlar

Trial cwd, repo venv; `AZURELMS_SKIP_ENV_FILE=1`, bo‘sh `GEMINI_API_KEY`
va `TELEGRAM_BOT_TOKEN`, `LOCAL_USE_REMOTE_SERVICES=0`.

- `manage.py test tests --verbosity 1`: **752 PASS (272.372s)**.
- Final focused rich/studio +CSS guards: **44 PASS (7.352s)**.
- `node --test tests/*.test.mjs`: **190 PASS (578.7865ms)**.
- `manage.py check`:0 issue; `node --check prototype/static/js/blog-studio.js`:PASS.
- First full752 run54 vendor-asset subcase’da fail bo‘ldi: eski gate
  faqat `/assets/`ni tanirdi. Admissiondagi installed local assets uchun
  faqat2 blog editor/3 exact filename/existing file tekshiruvi qo‘shildi;
  arbitrary path/remote script ruxsat qilinmadi. Final full yuqorida.
- 17 new Django +4 Node regressiya: rich HTML equality, safety, malformed
  HTML idempotence, CSRF, scope/reset, replay, no publication on upload,
  cap/oversize/duplicate files, fractional dimensions va abort/error lock.

## Restore va ochiq chegaralar

Ignored source/evidence/screenshots Gitga kiritilmaydi. Packet72 final
checkpoint o‘zgarishsiz saqlanadi. Packet73:
`playground/Eleventh Trial/checkpoints/packet-73-20260927-060856.zip`,
**551 fayl**, har entry SHA256 source bilan tekshirildi; ZIP SHA256:
`075F306F6C091095A9A468B9FA7E7F0D40FF13A4DF9DB437E65C16E305ABA737`.
Trial restore shu repo source va o‘rnatilgan dependencies bilan ishlaydi;
venv/vendor bundle ZIP ichiga nusxalanmagan. Assetlar litsenziyasi saqlanadi;
mavjud source kabi GPL config ishlatilgan, yangi license xulosasi emas.

Installed vendor SHA256 (dist ichida):

| Fayl | SHA256 |
|---|---|
| bundle.js | EE3BC20F2734932E11E8AAD9D8BCAFE66C6C3BF993F1914D2E4BAD7785568F69 |
| styles.css | 375248A9576F41FE94921D06CE79D0DEA93988DEF0639B2508E4AD6D59B90D70 |
| translations/uz.js | AB916E53659CA1B987623AF1458D02D29849ED3EACEFC9C9D19B02DE686B10EF |
| bundle.js.LICENSE.txt | D856BF7E08C511B8DCBF807847A4B7AE10D3BEA982DF6A2C3EC8CE06E7C8778D |

Local image bytes process restart/resetda yo‘qoladi; bu permanent storage
emas. Body20000/local caps mahsulot limiti emas. Real staff/superuser
RBAC, durable revision/replay/storage va canonical upload/sanitizer porti
alohida. Q03 public pagination/hero/comment/clap, U17/A2-D01, kengQ14,
owner/native/G2/G3 ochiq; ulardan hech biri bu paketda yopilmadi.

**Qolgan prototip:18 UI+3 handler=21 band,5 navbatdagi qadam:** Q17b SIT10,
Q18 Mini5, Q19 system5, Q08 legacy attendance1, final qabul.
Real runtime/DB/AWS8bb6b95 va19 renderer flag o‘zgarmadi.

API reference: [upload adapter](https://ckeditor.com/docs/ckeditor5/latest/framework/deep-dive/upload-adapter.html),
[CSP](https://ckeditor.com/docs/ckeditor5/latest/getting-started/setup/csp.html),
[Bleach allowlist](https://bleach.readthedocs.io/en/latest/clean.html).
