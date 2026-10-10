# Backoffice islohoti — kodsiz dizayn boshqaruvi

2026-10-10. Owner to‘rtinchi bosqichni amalda qurishni topshirdi.
Tayanch: main `260c71e`, [asosiy reja](BACKOFFICE-REFORM-PLAN.md),
DESIGN-01 typed katalog va DC3/DC4 validatsiya/state-machine tajribasi.

## Admission

**ADMIT — launch-critical.** Owner rang, matn va shaklni texnik yordamsiz
moslay olmaydi. KPI: ko‘rinishni tanlash → moslash → solishtirish → qoralamani
saqlash → tatbiq → oldingi ko‘rinishga qaytishni yordamsiz bajarish; vaqtli
usability natijasi hali yo‘q.

- Yagona design service: typed snapshot, owner-private durable draft/preset,
  immutable publication history, revision/base-version CAS, operation receipt
  va atomic audit. Brand/logo SiteSettings writerida qoladi, ikkinchi brend
  manbasi yoki arbitrary CSS/HTML/URL maydoni qo‘shilmaydi.
- Oddiy rang/shrift/shakl/oraliq tanlovlari mavjud typed schema qiymatlariga
  moslanadi. Custom qiymat «Moslashtirilgan» bo‘lib saqlanadi; oddiy rejimga
  o‘tish yoki preview tanlovi uni qayta yozmaydi. Kengaytirilgan bo‘lim yopiq.
- HTTP/UI service adapterlari: mavjud active superuser gate, CSRF va flag;
  GET design state yaratmaydi. Preview synthetic matnli, learner GET writerini
  chaqirmaydi. Published CSS faqat valid typed qiymatdan olinadi.
- `backoffice_design_workspace` default OFF. OFF editor yozishini va theme
  projectionni o‘chiradi; tarix o‘chmaydi. Tatbiq doirasi V1 va mapped legacy
  common tokens; print/vendor editor/rasm/Telegram tashqi qobig‘i istisno.
  Consumerlar va aniq cheklovlar implementatsiya dalili bilan yangilanadi.
- Canonical holat yangi additive jadvallarda; mavjud user/content/brand data
  qayta yozilmaydi. Default o‘qish factory fallback, migration/destructive
  rollback yo‘q. Owner DB’ga migration yoki test yozuvi qo‘llanmaydi; alohida
  demo DB orqali namoyish. Production deploy, provider va tashqi xizmat yo‘q.
- Saqlash server tasdig‘idan keyin; stale input va yo‘qolgan javob saqlanadi,
  avtomatik POST retry yo‘q. Current pointer DB’dan o‘qiladi, multi-worker stale
  cache ishlatilmaydi. Published CSS screen-only; user theme tanlovi saqlanadi.
- Haftalik ish kamayadi: bir joyda sozlash/ko‘rish/tatbiq/qaytish. Yangi doimiy
  operator navbati, background job yoki monitor yo‘q.

## Tekshiruv shartnomasi

Owner/staff/anonymous/disabled actor; CSRF/flag OFF/in-flight POST; typed bounds,
unsafe CSS/NaN/unknown keys, contrast+hierarchy; draft/preset isolation; no-op,
atomic audit failure, concurrent/stale submit, durable operation replay/readback;
publish/rollback yangi version va draft saqlanishi; public CSS’da private payload
yo‘qligi; real consumer tokens/legacy aliases/print; reload/custom/unknown
response; desktop/mobile/light/dark/keyboard. App, focused Node va PostgreSQL CI.

Holat: runtime kesimi qurildi. Owner usability va real rollout qabuli ochiq.

## Runtime chegarasi

- `/backoffice/control/design/`: active owner uchun besh sodda bo‘lim,
  yopiq aniq sozlamalar, rang/telefon tanlovi va qoralama–joriy namuna.
  Namuna sandbox iframe ichidagi synthetic kurs/dars/suhbat/boshqaruvdir.
- `core/design_schema.py` va `design_catalog.json`: 87 typed maydon, ikki
  palitra, kontrast va matn iyerarxiyasi. CSS, HTML yoki tashqi shrift URL
  kiritish yo‘li yo‘q. JS preview shu katalogning presentation adapteridir;
  server har bir yozishni mustaqil tekshiradi.
- `core/design_service.py`: yagona writer. `DesignDraft` va `DesignPreset`
  ownerga tegishli; `DesignVersion`, `DesignState`, `DesignOperation` nashr,
  joriy pointer va durable receiptni saqlaydi. `core0007` faqat yangi jadvallar.
  Model save/queryset update/delete nashr/receiptni o‘zgartirishni rad etadi;
  raw SQL darajasida database trigger kafolati da’vo qilinmaydi.
- Saqlash revision va base-versionni tekshiradi; tatbiq serverdagi saqlangan
  qoralamadan olinadi. Bir amal belgisi + ayni normalized payload eski receiptni
  qaytaradi; boshqa payload rad etiladi. No-op nashr yangi versiya yaratmaydi.
  Rollback eski snapshotdan yangi versiya yaratadi, shaxsiy qoralamani o‘chirmaydi.
- Nashr va rollback sabab/tasdiq talab qiladi. O‘zgarish, audit va receipt bitta
  transactionda. PostgreSQL actor/current-pointer locklari parallel amallarni
  tartiblaydi; SQLite lock xatosida brauzer natijani qayta o‘qiydi.
- `/design/theme.css` faqat nashrdagi typed qiymatlarni beradi, private metadata
  chiqarmaydi, `no-store`. Joriy pointer har safar DB’dan; worker-local theme
  cache yo‘q. Flag OFF yoki saqlash o‘qilmasa static default ko‘rinish qoladi.
- Frontend V1 va workspace’da rang, matn va aniq komponent rollari ulanadi.
  `templates/base.html` orqali legacy umumiy palitrasi moslanadi; legacy
  geometriyasi to‘liq port qilingan deyilmaydi. Mustaqil Mini App/SIT qobiqlari,
  vendor editor, video/rasmlar va print alohida. `az-v2-theme` tanlovi saqlanadi.
- Preview va private readback GET design row yaratmaydi; mavjud umumiy
  SiteSettings loaderining tarixiy GET xatti-harakati bu claimga kirmaydi.
  Hech bir dars/progress/to‘lov writeri ishga tushmaydi.

## Lokal dalil

Barcha Python testlarda `AZURELMS_SKIP_ENV_FILE=1`, `GEMINI_API_KEY=''`,
`TELEGRAM_BOT_TOKEN=''`.

- `venv/Scripts/python.exe manage.py check`: 0 issue.
  `venv/Scripts/python.exe manage.py makemigrations --check --dry-run`:
  No changes detected. Diff whitespace tekshiruvi PASS.
- `venv/Scripts/python.exe manage.py test core frontend --verbosity 1`:
  **912 test / 881 PASS / 31 skip**, 69.199s. Keyingi input va runtime
  tuzatishlar quyidagi yakuniy focused suite bilan tekshirildi.
- `venv/Scripts/python.exe manage.py test core.test_design_service core.test_design_views core.test_design_runtime --verbosity 1`:
  **59 test / 57 PASS / 2 PostgreSQL-only skip**, 2.022s, check0.
  Ikki parallel owner va ayni operation race PostgreSQL CI’da ishlaydi.
- `node --test tests/frontend_v1/*.test.mjs`: **140/140 PASS**.
  Shundan `backoffice-design.test.mjs` **12/12**: unsafe input, custom/reset,
  durable receipt, key order/hex normalization va recovery/reconcile.
  Ikkala yangi MJS uchun `node --check` PASS.
- Dastlabki HTTP fixture bo‘sh unique email sabab yiqildi; har bir synthetic
  userga alohida email berilib tuzatildi. Review topgan lone-surrogate va
  chuqur nested JSON endi 400 bilan, yozishsiz rad etiladi.
- IAB + faqat `.tools/backoffice-stage2/demo.sqlite3`: avval SQLite backup,
  additive core0007 va yangi flag ON. Save → reload → publish → haqiqiy
  workspace → rollback → private draft retention → explicit rebase PASS.
  Ikki tab: yangi draft saqlangach eski tab POST409, uning tanlovi qoladi,
  explicit rebase muvaffaqiyatli. Hech qanday yashirin POST retry yo‘q.
- 17px custom tugma «Moslashtirilgan» bo‘ladi; Matn reseti unga tegmaydi;
  save/reload saqlaydi. Shaxsiy uslub DB’da saqlandi. Haqiqiy workspace’da
  nashrdan keyin action `#146c4b`, tugma `17px`, matn `18px`, sarlavha `36px`;
  dark palitrada action `#93d7b4`. 1440px va 320px horizontal overflow yo‘q;
  mobile Enter/Escape menyu ishlaydi; yakuniy console error/warn0.
- Readbackning eski receipt + yangi server holati original amal snapshoti
  deb qabul qilinmaydi. Reload’dan oldingi yangi local edit ham server readback
  bilan o‘chmaydi. Rollback ochiq private qoralamani almashtirmaydi.

Native zoom/AT/print/real-device, barcha legacy sahifalarning to‘liq geometry
porti va owner vaqtli usability qabuli ochiq. Card padding faqat qo‘llab-
quvvatlangan panellar/kartalar; kichik avatar varianti va literal workspace
letter-spacing o‘z shartnomasida. UI bu chegaralarni ko‘rsatadi. DESIGN-01 DC6
avtomatik qabul qilinmadi. Production deploy yo‘q; keyingi kesim qolgan
backoffice yuzalarini shu navigatsiyaga ulash.

## PR178 review tuzatishi

State/mutation/readback endi eng so‘nggi 20 nashrni qaytaradi; `history_before`
cursor bilan eski immutable snapshotlar bosqichma-bosqich olinadi. Ro‘yxat
o‘sishi oddiy save javobini cheksiz kattalashtirmaydi. UI sahifa yuklashda faqat
tarixni kengaytiradi; boshqa oynadan kelgan draft/published/receiptni o‘zlashtirmaydi.
Cursor parent chegarasi strict; GET private/no-store va yozishsiz qoladi.

Yakuniy shu focused Python command: **64 test / 62 PASS / 2 SQLite skip**,
2.375s, check0. Design Node **14/14 PASS**. Alohida nusxa8093’da 27 nashr:
avval20, «Oldingi nashrlarni ko‘rish»dan so‘ng27 va Asl Azure versiyasi mavjud;
cursor tugaydi, qoralama o‘zgarmaydi. Vaqtinchalik tab/server yopildi, asosiy
demo8092 tarixi bu sinov bilan ko‘paytirilmadi. Birinchi PR CI uchalasi yashil;
review tuzatishining yangi commit CI’i alohida tekshiriladi.
