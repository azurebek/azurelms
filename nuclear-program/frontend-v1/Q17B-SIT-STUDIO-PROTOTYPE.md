# Q17b — SIT studiyasi, lokal prototip

2026-09-27–28, D31 continuation; base `f7047e6`, branch
`codex/q17b-sit-studio-prototype`. **Packet74: U25–U34, 10 source-shaped
UI manzili qurildi.** Runtime, DB, provider, deploy yoki yangi product
qoidasiga tegilmadi. Admission: EXPERIMENT — canonical state yozmaydi.
KPI: tasdiqsiz nashr va stored/public kontent farqi 0.

## Nima tayyor

Preview: `http://127.0.0.1:8079/backoffice/sit/`.
Registry `0.74.0-sit-studio`: **131 URL /69 page template /110 source
nomi /1167 route-state /198 action**. 10 yangi URL ikki umumiy template
bilan: SIT dashboard, universitet/e’lon/qo‘llanma list/new/edit.
Source: `sit/backoffice_urls.py`, `backoffice_forms.py`, `models.py`,
`backoffice_views.py`, `selectors.py`, `views.py`.

- 24 universitet +8 e’lon +11 qo‘llanma =43 source maydoni. Universitetning
  7 ichki formseti: fakultet, dastur, til tayyorlov, talab, hujjat, yordam,
  media — jami33 child maydoni. Field/choice/default/length AST orqali
  canonical source’dan olinadi; real model yoki settings import qilinmaydi.
- Yangi universitet avval saqlanadi; yangi fakultet keyingi saqlashdan
  so‘ng dastur tanloviga kiradi. Source `can_delete=False`: o‘chirish yo‘q,
  faol holatini o‘zgartirish bor. Faculty/program scope, uniqueness, hidden
  ID va management-count tekshiruvi; hamma formset birga valid bo‘lmasa
  hech narsa yozilmaydi. No-op revision/auditni o‘zgartirmaydi.
- Filtr/pagination → tahrir → preview/save → receipt → o‘sha filtrli
  ro‘yxat. Safe return faqat ayni oilaga; tashqi/buzilgan query rad etiladi.
  Unknown ID, shu jumladan0, boshqa yozuvga almashtirilmaydi.
- Native sabab/tasdiq →303 o‘zgarmas receipt. Run/revision/UUID/digest,
  repeat/stale/no-op va unknown-result reconcile; no automatic resend.
  Normal/empty/long/locked/expired/error/offline/slow/uncertain holatlari.
- Universitet va qo‘llanma nashrida manba/tekshirish sanasi kerak.
  SITdagi kelajak `published_on` blog scheduling bilan aralashtirilmadi:
  source kabi nashrni yashirmaydi. Draft namuna read-only; draftga saqlash
  publicdan yashiradi. 4 mavjud public SIT yo‘li shu storedan o‘qiydi.
- Tab/run/path/revision-scoped qoralama; reload matn/holatni tiklaydi,
  lekin consent, file bytes va clear-image intentni tiklamaydi. Body uchun
  Packet73 CKEditor va yagona sanitizer; SIT media namespace blogdan
  ajratilgan. Format va ichki rasm preview/save/publicda qoladi.
- Universitetning bir nechta rasmlari memory-only normalizer orqali;
  guide inline image xuddi Packet73 upload adapteri bilan. CSRF, auth,
  origin/revision/run, replay va raster bounds saqlanadi. Fixed local caps
  operatsion mahsulot sozlamasi emas:32 entity/child,64 receipt,20k body,
  university34 file/10MiB aggregate,16MiB thumbnail store.

## Brauzer dalili

Computer Use/IAB Chromium orqali native form va keyboard tekshirildi;
actual phone/Safari/AT emas. **120 responsive case**:10 URL ×320/390/768/
1024/1280/1536 ×light/dark, document horizontal overflow0.

1. 390px universitet nomini edit/save →1-versiya; hujjat child qatorini
   qo‘shish → unsaved preview → save →2-versiya; public namuna shu nom,
   yangi hujjat va avvalgi fakultet/dasturni birga ko‘rsatdi.
2. Guide bold Uzbek/Turkish matni + actual synthetic2×2 PNG chooser →
   native save →1-versiya → saved sample: strong matn va same-run image
   `complete=true`, `naturalWidth=2`.
3. Filtrli universitet ro‘yxati → native no-op save → receipt → filtered
   return; Back receiptga qaytganda ham qidiruv/publication saqlangan.
4. New announcement → title/date/university/publish/homepage → reload:
   qoralama tiklandi, consent unchecked → alohida tasdiq/save → public
   SITda ayni yangi sarlavha. Bu haqiqiy e’lon nashri emas.
5. Console final warning/error0; vaqtinchalik viewport reset qilindi.

Browser topgan GET child-form binding xatosi tuzatildi: empty FILES bilan
GET forma bound bo‘lib, saved rows bo‘sh ko‘ringan edi. Alohida regression
endi saved faculty/program/IDni va blank extra row error-free holatini
tekshiradi. Consent yetishmagan native urinish422 deb qayd etildi, success
deb hisoblanmadi; fresh checked holatda qayta yuborishgina saqlandi.

Screenshots lokal `playground/Eleventh Trial/evidence/` ichida:
`packet-74-studio-desktop-light.png`, `packet-74-university-mobile-light.png`,
`packet-74-guide-mobile-dark.png`. Ignored bytes Gitga kiritilmaydi.

## Test va restore

Trial cwd, repo venv. Har run: `AZURELMS_SKIP_ENV_FILE=1`,
`GEMINI_API_KEY=` va `TELEGRAM_BOT_TOKEN=`, `LOCAL_USE_REMOTE_SERVICES=0`.

- Yakuniy full `manage.py test tests --verbosity 1`: **770 PASS**, jumladan
  18 SIT regression. Run27-sentyabr boshlanib28-sentyabr yakunlandi;
  logdagi71220.051s wall-clock oraliq, odatiy ish davomiyligi taxmini emas.
  Oldingi full768 PASS (304.331s); undan keyingi GET child-render va safe
  return/unknown0 tuzatishlari yakuniy770 tarkibida qayta tekshirildi.
- `node --test tests/*.test.mjs`:191 PASS (797.2147ms), shu jumladan
  SIT endpoint va blog/SIT media namespace ajratilishi.
- `node --check prototype/static/js/sit-studio.js`:PASS.
- `manage.py check`:0 issue. Tracked o‘zgarishlar faqat evidence/docs.

Final checkpoint: `playground/Eleventh Trial/checkpoints/packet-74-20260928-024509.zip`,
**569 fayl**, barcha entry SHA256 source bilan tekshirildi. ZIP SHA256:
`FA41C78FF7C1CD1240DA85A97212BEB497137FFF8E0BECCEF6AC1A9895ABEAF7`.
Ignored source/evidence/screenshots force-add yoki upload qilinmadi.

## Ochiq chegaralar

Bu **lokal implementation**, owner/native/G2/G3 yoki real port qabuli
emas. Source owner-only RBAC, DB atomicity/audit, durable revision/replay,
storage/media access va cross-browser nashr real adapterda tekshiriladi.
Har browser alohida fixture universe; shu universe signed-out published
media ochiladi, foreign universe yopiq. Reset/restart synthetic kontent
va faylni yo‘qotadi; bu permanent CMS emas.

Tashqi source/application/video/announcement URL qiymatlari ko‘rsatiladi,
lekin real tashqi xizmat/network amali qilinmaydi. Source public layout,
application-help CTA va oldingi Q03 advanced acceptance bu paketning
studio-field/public-content tekshiruvi bilan yopilmaydi. U17/A2-D01,
keng Q14 authoring ham alohida OPEN. Packet73 checkpoint o‘zgarishsiz
rollback bazasi sifatida saqlanadi; vendor venv dependency ZIPga kirmaydi.

**Qoldiq:8 UI +3 handler =11 yangi band,4 qadam:** Q18 Mini App5,
Q19 system5, Q08 legacy attendance1, yakuniy qabul. Real port alohida.
AWSning oxirgi tasdiqlangan relizi `8bb6b95`,19 renderer flag; bu turn
AWSga ulanilmadi yoki o‘zgartirilmadi.
