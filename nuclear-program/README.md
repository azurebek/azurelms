# AzureLMS — joriy holat va hujjatlar xaritasi

**Shu yerdan boshlang.** Bu sahifa loyihada nima tayyor, nima ochiq va
tafsilotni qayerdan topishni jamlaydi. AI agentlar avval [AGENTS.md](../AGENTS.md)
va [ish qoidalarini](rules-for-agents.md) o‘qiydi.

Oxirgi solishtirish: **2026-10-16**, kod tayanchi `main`dagi **`8442cd1`**
(PUB1.0a holati shu sanadagi branch ishi bilan qo‘shilgan).
Bu sana va commit quyidagi holat qaydining chegarasi; keyingi ishda Git va
yangi dalillar bilan yangilanadi. Tarixiy rejadagi checkbox yoki eski test
soni o‘z-o‘zidan bugungi ishlar ro‘yxati hisoblanmaydi.

## Hozir qayerdamiz?

| Qism | Tasdiqlangan holat | Tafsilot |
|---|---|---|
| Asosiy platforma | Django LMS: kurs/dars, topshiriq/test/imtihon, o‘qituvchi tekshiruvi, guruh/to‘lov, kutubxona, Classbook, messenger, Telegram va AI qatlamlari kodda mavjud. Har birining ishlashi ruxsat, sozlama va muhitga bog‘liq. | [Arxitektura va kod xaritasi](project-context.md) |
| Backoffice islohoti | Dastlabki olti bosqich, eski muharrirlarni soddalashtirish va **B2.1–B2.6 lokal texnik ishlari bajarilgan**. B2.6 [PR #189](https://github.com/azurebek/azurelms/pull/189) orqali `62dd358`ga qo‘shilgan; [uchta majburiy CI tekshiruvi](https://github.com/azurebek/azurelms/actions/runs/38443075952) muvaffaqiyatli. | [Yagona backoffice rejasi](frontend-v1/BACKOFFICE-REFORM-PLAN.md), [B2.6 dalili](frontend-v1/BACKOFFICE-02-STAGE-6.md) |
| Keyingi backoffice bosqichi | **BACKOFFICE-03 rejalashtirildi, implementatsiya boshlanmagan.** Yetti bosqich: xavfsiz sozlamalar, exam qoralama/nashri, to‘liq exam muharriri, qayta foydalanish, ko‘rinadigan landing kontenti, qolgan dizayn consumerlari va texnik qabul/reliz paketi. Birinchi ish B3.1a; owner shaxsiy testi old shart emas. | [B3 qamrov va tugash mezonlari](frontend-v1/BACKOFFICE-REFORM-PLAN.md#backoffice-03) |
| Classbook islohoti | **CLASSBOOK-01 rejalashtirildi, implementatsiya boshlanmagan.** Sakkiz bosqich: ishonchli session/tarix va kirish, kodsiz 10 tur muharriri, dars rejasi, ustoz boshqaruvi, o‘quvchi xonasi, hisobot/yordam, birgalikdagi sifat, reliz paketi. Keyingi Classbook ishi CB1.1a; B3 alohida saqlanadi. | [Classbook rejasi va audit](frontend-v1/CLASSBOOK-REFORM-PLAN.md) |
| Dashboard islohoti | **DASHBOARD-01 rejalashtirildi, implementatsiya boshlanmagan.** Learner, teacher, Mini App/Bot va existing Backoffice entry auditi global staff PII/chat context/moliya, private cache, GET write, Mini App replay/frame, product-truth va N+1 qarzlarini ochdi. Sakkiz phase/33 kichik kesim; birinchi kesim DASH1.0a. Keng redesign NEXT/post-launch; global users/chats, receipt writer, foreign receipt file va Bot staff scope DASH1.0a affected release uchun existing A0b stop-ship regressioni. | [Dashboard tadqiqoti va roadmap](frontend-v1/DASHBOARD-REFORM-PLAN.md) |
| Blog islohoti | **BLOG-01 rejalashtirildi, implementatsiya boshlanmagan.** Azure Journal uchun xavfsiz rich content va preview, canonical editorial lifecycle/revision, qulay studiya, public discovery/SEO, accessible reader, post glossary/course bridge, moderatsiya, distribution/metrics va rollout to‘qqiz bosqichda yozildi. Owner Blog ishini navbatga qo‘ysa birinchi kesim BLOG1.0a1. | [Blog tadqiqoti va roadmap](frontend-v1/BLOG-REFORM-PLAN.md) |
| Messenger islohoti | **MESSENGER-01 rejalashtirildi, implementatsiya boshlanmagan.** I4a/I4b renderer poydevori saqlanadi; Origin/session/input containment, exact-once send/dual-cursor outbox, canonical membership/unread, unified no-JS Inbox, safe attachment, scoped teacher/support, Telegram outbox, private AI/A9, retention va rollout to‘qqiz bosqich/34 reviewable kesimda yozildi. Birinchi kesim MSG1.0a1. | [Messenger tadqiqoti va roadmap](frontend-v1/MESSENGER-REFORM-PLAN.md) |
| Payment, Subscription va Checkout islohoti | **COMMERCE-01 rejalashtirildi, implementatsiya boshlanmagan.** Mavjud signed quote, server recalc, private evidence, lock va entitlement poydevori saqlanadi; finance least-privilege/evidence containment, immutable order-payment-subscription-access graph, learner center, owner workbench, Telegram/outbox, reconciliation va staged rollout to‘qqiz bosqich/40 reviewable PR-unitda yozildi. Birinchi kesim COM1.0a. | [Commerce tadqiqoti va roadmap](frontend-v1/COMMERCE-REFORM-PLAN.md) |
| SIT islohoti | **SIT-01 rejalashtirildi, implementatsiya boshlanmagan.** Audit current price/filter, freshness/source, preview/rich-content, fee/dead CTA, AI routing/retrieval va canonical inquiry muammolarini topdi. Versionlangan katalog, scoped evidence, S2 inquiry, owner studio, program-first discovery/compare, deterministic AI, SEO/cache/WCAG va rollout to‘qqiz bosqich/27 kichik kesimda yozildi. Birinchi kesim SIT1.0a. | [SIT tadqiqoti va roadmap](frontend-v1/SIT-REFORM-PLAN.md) |
| Public/anonymous islohoti | **PUBLIC-01 rejalashtirildi; PUB1.0, PUB1.1, PUB1.3 bosqichlari, PUB1.2a–b, PUB1.2d, PUB1.4b–c, PUB1.4e, PUB1.5, PUB1.6, PUB1.7 bosqichlari, PUB1.8a va PUB1.8b kodda (2026-10-16/21, lokal); PUB1.4a owner qarori bilan keyinga qoldirilgan, qolgan kesimlar boshlanmagan.** PUB1.0a: legacy va V1 public rich text yagona `PUBLIC_EDITORIAL_V1` profili va navigatsiya/kontent URL siyosatidan o‘tadi, read-only `audit_public_content` bor. PUB1.0b: web, Telegram deep-link va telefon ro‘yxati yagona `registration_policy` qaroridan o‘tadi; faolsizlantirilgan hisob hech bir kanalda kira olmaydi. PUB1.0c: login, ro‘yxat, parol tiklash va Telegram init urinishlari owner sozlaydigan limit bilan cheklanadi (generik 429). PUB1.0d: Telegram orqali kirishda init/consume CSRF’li POST, status hech narsa yozmaydigan GET; login faqat bir martalik consume’da. PUB1.0e: public/auth GET bazaga yozmaydi; yo‘q huquqiy sahifa namuna matn bilan yaratilmaydi — halol 503, Control Center `public_content` qizil. PUB1.0f: parol tiklash xati o‘zbekcha; email sozlanmagan non-local muhitda tiklash ochiq yopiq turadi, `check --deploy` `azurelms.E101` beradi. PUB1.0g: Blog anonim o‘quvchiga cookie qo‘ymaydi va o‘qish/IP/UA yozmaydi; olqish uchun kirish kerak; eski data `purge_blog_read_tracking --apply` bilan tozalanadi. PUB1.1a: 221 route’ning hammasi public/ops/private deb `frontend/public_policy.py`da tasniflangan, yangi route tasniflanmaguncha `check` (`azurelms.E201`) yiqiladi; xulq snapshot’i dalil sifatida. PUB1.1b: har `<head>` bitta metadata blokidan; canonical/og:url `PUBLIC_CANONICAL_ORIGIN`dan (Host emas); auth/sertifikat/holat/private/preview sahifalari `noindex`. PUB1.1c: `/robots.txt` (faqat sitemap ko‘rsatkichi) va `/sitemap.xml` — faqat e’lon qilingan, 200 va canonical’ga teng URL’lar. PUB1.1d: public route sarlavhalari va method’i registrdan bitta middleware’da (sensitive/holat/xato/preview `no-store`, mehmon sahifasi `private, no-cache` + ETag, GET-only sahifaga POST `405`); theme CSS kontent-xeshli immutable URL. PUB1.2a: talaba soni/foiz/reyting kabi statistika faqat owner dalil bilan tasdiqlasa (`backoffice/claims/`), fikrlar faqat rozilik bilan chiqadi; seed raqamlar dalilsiz yashirin. PUB1.2b: bosh sahifa/about deterministik proyeksiya (`frontend/public_content.py`), learner PII o‘qilmaydi, so‘rov budjeti testda. PUB1.2d: legacy va V1 sarlavha/footer bitta owner menyusidan (qotirilgan nav yo‘q), SIT bir marta, footer uchta nomlangan guruh; noto‘g‘ri yo‘naltirilgan “Sertifikatlar”/“Qabul yo‘li” seed qatorlari `0022` migratsiyasida olib tashlandi; ro‘yxat yopiq bo‘lsa ro‘yxatga havola yo‘q, o‘rniga kurslar katalogi; aloqa/ijtimoiy tarmoq faqat sozlangan bo‘lsa (model namunasi chiqmaydi), javob muddati va’dalari olib tashlandi. PUB1.3a: katalog qidiruvi boy HTML’da emas, normallashgan oddiy-matn proyeksiyasida (`Course.search_text`; `o‘/oʻ/o'` bir xil, teg nomlari topilmaydi), `q` 80 belgi/6 so‘z, noma’lum filtr tashlanadi, tartib `id` bilan to‘liq, havolalar URL-kodlangan, so‘rov budjeti testda. PUB1.3b: kurs taklifi (`courses/public_offer.py`) checkout bilan bir qoidadan — sahifa “qabul ochiq” desa checkout ayni guruh/narx/davrni beradi; yopiq bo‘lsa sahifa sababni aytadi, checkout’ga olib borib qaytarmaydi. PUB1.3c: kurs sahifasi va kartasi faqat bazadagi faktlarni (0 yoki bo‘sh fakt yo‘q) va checkout bilan bir manbadagi tariflarni ko‘rsatadi; sertifikat faqat oraliq va yakuniy imtihon bo‘lsa va’da qilinadi; dalilsiz sidebar bandlari olib tashlandi. PUB1.3d: kurs sahifasidan kirgan/ro‘yxatdan o‘tgan mehmon imzoli niyat (`frontend/public_intent.py`) bilan aynan o‘sha kurs (va tanlangan tarif) checkout’iga qaytadi; qaytishda qabul va tarif qayta tekshiriladi; havola muddati owner sozlamasi. PUB1.4b: auth formalarida har xato bir marta, bitta xulosa (maydonlar soni), birinchi xatoga fokus, xato maydon bilan `aria-describedby` orqali bog‘langan, legacy ham o‘zbekcha; CSRF rad etilsa o‘zbekcha sahifa. PUB1.4c: login va parol tiklash javobi (matn, status, javobgacha ish) hisob borligini bildirmaydi, ro‘yxatda band emailni sinab chiqish cheklangan, `/admin/` login va parol o‘zgartirish ham cheklovda, parolni tiklagan egasi darhol kiradi. PUB1.4e: Telegram bot havolani ochganda kirishni o‘zi tasdiqlamaydi — kod va «Kirishni tasdiqlash» / «Bu men emas» tugmasi; rad etilsa brauzer darhol biladi; ikkala renderer bitta panel va skript; kompyuterda QR kod (`segno`). PUB1.5a: maxfiylik va shartlar versiyalanadi (qoralama → tasdiq → nashr, kuchga kirish sanasi, oldingisiga qaytish, audit) — `/backoffice/legal/`; owner nashr qilmaguncha bu sahifalar 503 (umumiy namuna matn tasdiqlanmaydi). PUB1.5b: brauzerda saqlanadigan hamma narsa va tashqi manbalar ro‘yxati (`PUBLIC-COOKIE-INVENTORY.md`, koddan va javobdan test bilan), kuzatuv yo‘q (CSP’dan ham olib tashlandi), rozilik banneri kerak emas; ma’lumot yig‘adigan formalar yonida eslatma. PUB1.5c: sertifikatni 192-bitli tasodifiy kod bilan tekshirish (`/certificates/verify/<kod>/`) — faqat holat, qisqa ism, kurs va sana; noto‘g‘ri kod cheklanadi; flag owner qarorigacha o‘chiq. PUB1.5d: ballar ilovasi faqat egasi va xodimlarga; eski `AZ-…` havola boshqalarga faqat minimal tasdiq (o‘tish davri flagi bilan), mavjud sertifikatlarga kod — `backfill_certificate_tokens`. PUB1.6a: Blog katalog bilan bir so‘rov qoidasida (`frontend/public_query.py`), toza sahifa/teg havolalari va qaytish, ochiq sahifada login emas — ism. PUB1.6b: SIT bitta adapter (`sit/public.py`) orqali katalog/sitemap/meta’ga; toza sahifalash va qaytish; umumiy AI, ustoz va 5 000 so‘m CTA’lari o‘rniga katalog va sozlangan aloqa. PUB1.7a: xato/texnik ishlar/oflayn sahifalari tashqi manbasiz va rost (500 bazaga tegmaydi, “xabardor” yo‘q, POST qayta yuborilmaydi, `Retry-After` faqat owner belgilasa); `/healthz`, `/readyz` begonaga faqat holat. PUB1.7b: shrift/ikonka o‘z serverimizda (Google Fonts, jsDelivr CSP’dan ham olib tashlandi), V1 ochiq sahifa ilova bundle’isiz, asset byudjeti CI’da, `audit_public_media`. PUB1.7c: a11y CI probe (0 topilma), JavaScriptsiz yo‘llar, legacy xira matn kontrasti AA, 320px reflow 0; ekran o‘quvchi/qurilma bandlari OPEN — [dalillar](frontend-v1/PUBLIC-A11Y-EVIDENCE.md). PUB1.8a: shaxsiy ma’lumotsiz server voronkasi (`public_telemetry_v1`, default OFF; kunlik son + qisqa HMAC kalit), `public_funnel_report`. PUB1.8b: reliz tayyorligi darvozasi — bitta selector (owner sahifasi `/backoffice/release/`, Control Center `public_release`, `public_release_gate`); pilot faqat majburiy bandlar (huquqiy matn, sotuvdagi kurs, aloqa, to‘lov rekvizitlari, email, domen, sitemap, media) yashil bo‘lsa, owner tasdig‘i sabab va holat izi bilan auditda. Landing, kurs/pricing, auth/reset/Telegram, legal/cookie, Blog/SIT adapterlari, sertifikat va system state’lar audit qilindi. Renderer-independent rich-content, registration/auth containment, truthful offer/claim/legal contractlari, exact intent, SEO/cache, WCAG/performance va rollout to‘qqiz bosqich/36 reviewable kesimda yozildi. PUB1.2c B3.5 writer’i bilan birga ochiq; PUB1.4a keyinga qoldirilgan (refund/renewal siyosati kutilmoqda); keyingi kesim PUB1.8b2 (aloqa va to‘lov rekvizitlari owner muharriri; checkout/botda namuna karta chiqmaydi), keyin PUB1.8c yoki PUB1.4d (SMTP owner’da). | [Public tadqiqoti va roadmap](frontend-v1/PUBLIC-REFORM-PLAN.md) |
| Public editorial dizayn porti | **PUBLIC-02 rejalashtirildi (2026-10-28), implementatsiya boshlanmagan.** Manba — owner bilan qurilgan lokal prototip `playground/Thirteenth Trial/` (git'ga kirmaydi): 18 ochiq sahifa + o'quv maydoni production V1 tokenlarida, ochiq sahifa → kirish → o'quv maydoni logo/header uzluksizligi ±1px. Ko'rinish va sahifa tuzilishi o'zgaradi, canonical state o'zgarmaydi; flag `public_editorial_v1` (default OFF) ortida o'n bitta kesim (PE0–PE10). Owner qarorlari D1–D5 (to'q footer, logo, tugma rangi, urg'u burchagi, "Savol-javob" yorlig'i) 2026-10-30 da tavsiya bo'yicha qabul qilingan; keyingi kesim PE1. | [Port rejasi](frontend-v1/PUBLIC-EDITORIAL-PORT-PLAN.md) |
| Lokal backoffice | B2.6 yakunida `8092` serverida avval yoqilgan beshta B2 gate ON saqlangan. Registrdagi default qiymatlar OFF. Bu qayd barcha muhitda funksiyalar yoqilganini anglatmaydi. | [Lokal yoqish chegarasi](frontend-v1/BACKOFFICE-LOCAL-ROLLOUT.md), [flag registri](../core/flags.py) |
| AWS | **Oxirgi hujjatlashtirilgan reliz — 2026-09-26 R2, `8bb6b95`**, o‘sha tekshiruvda 19 ta V1 renderer flagi ON. Oktabrdagi B2 ishlarining serverga chiqarilgani shu dalildan kelib chiqmaydi. | [R2 reliz qaydi](frontend-v1/R2-READY-V1-AWS.md), [deploy yo‘riqnomasi](../deploy/README.md) |
| Dizayn prototipi va haqiqiy ilova | DESIGN-01 ustaxonasi va uning dalillari bor; haqiqiy Django backoffice dizayn oqimi alohida qurilgan. Prototip, kodga ko‘chirish, lokal test va owner qabuli turli holatlar. | [Frontend indeksi](frontend-v1/README.md), [ko‘chirish ledgeri](frontend-v1/PORT-LEDGER.md), [DC6 qabuli](frontend-v1/DESIGN-01-DC6-ACCEPTANCE.md) |

Bu hujjat yangilanishida server holati qayta kuzatilmadi, deploy bajarilmadi.

## Uch asosiy ishni qayerdan boshlash kerak?

Yoqilgan lokal backoffice va tegishli ruxsat bilan:

| Ish | Boshlanish joyi | Hozirgi imkoniyat |
|---|---|---|
| Kurs va dars tayyorlash | **Kurslar** — `/backoffice/workspace/courses/` | Kurs/modul/dars, materiallar, topshiriq va quiz tayyorlash, namuna ko‘rish; imtihon va bo‘limni tahrirlashga kontekst bilan o‘tish. |
| O‘quvchi muammosini topish | **O‘quvchilar** — `/backoffice/workspace/students/` | Kurs/darsga kirish sababini, topshiriq va e’lon qilingan natijani, xabar yetkazish holatini ko‘rish; tegishli tekshiruvdan ayni kartaga qaytish. |
| Dizaynni kodsiz sozlash | **Sayt va dizayn → Ko‘rinish** (owner) — `/backoffice/control/design/` | Ruxsat etilgan rang, shrift, o‘lcham va shakllar; qoralama/namuna, nashr qilish va oldingi nashrga qaytish. |

Ish stoli, umumiy qidiruv va yaqindagi ishlar shu oqimlar o‘rtasida yo‘lni
saqlaydi. [B2.1–B2.6 tafsilotlari](frontend-v1/BACKOFFICE-REFORM-PLAN.md#backoffice-02)
har bir imkoniyatning chegarasini ko‘rsatadi.

## Hali ochiq qolganlar

Backoffice bo‘yicha keyingi qamrov [B3 rejasida](frontend-v1/BACKOFFICE-REFORM-PLAN.md#backoffice-03),
jonli dars tayyorlash va olib borish islohoti [CLASSBOOK-01da](frontend-v1/CLASSBOOK-REFORM-PLAN.md),
authenticated ish markazi islohoti [DASHBOARD-01da](frontend-v1/DASHBOARD-REFORM-PLAN.md),
Azure Journal islohoti [BLOG-01da](frontend-v1/BLOG-REFORM-PLAN.md),
human/AI yordam va realtime qatlam islohoti
[MESSENGER-01da](frontend-v1/MESSENGER-REFORM-PLAN.md), narxdan accessgacha
Commerce islohoti [COMMERCE-01da](frontend-v1/COMMERCE-REFORM-PLAN.md), “Turkiyada o‘qish”
portali islohoti [SIT-01da](frontend-v1/SIT-REFORM-PLAN.md), anonim landing,
kurs/pricing/auth/legal/certificate va umumiy public infratuzilma esa
[PUBLIC-01da](frontend-v1/PUBLIC-REFORM-PLAN.md) ajratilgan.
Reja yozilishi ularning bajarilganini anglatmaydi; keng versioning, public UX va
production masalalari o‘z chegaralarida qoladi. BLOG-01, MESSENGER-01 va
PUBLIC-01 joriy queue’ni o‘z-o‘zidan almashtirmaydi. BLOG1.0, SIT1.0, MSG1.0 va
PUB1.0dagi xavfsizlik topilmalari maintenance sifatida alohida baholanadi.

**Current security correction:** 2026-10-15 Dashboard source auditi legacy global
dashboard/users/chats PII/message contexti, receipt decision, foreign private
receipt file va Telegram Bot global admin oqimlarida ordinary active staff
scope’ini topdi. Bu oldingi A0b permission maqsadiga zid;
[DASH1.0a](frontend-v1/DASHBOARD-REFORM-PLAN.md#dash10a--backoffice-capability-va-pii-containment)
tegishli surface release’i uchun stop-ship. Bu reja yozilishi regression
tuzatildi degani emas.

- **Azurbekning shaxsiy foydalanish qabuli** keyinga qoldirilgan. Lokal
  texnik yakun uni bajarilgan deb belgilamaydi.
- **Haqiqiy telefon, brauzerning native zoom’i va screen reader** bilan
  qabul ochiq. Ekran kengligi va 200% render matni sinovlari ularning o‘rnini
  bosmaydi. B2 uchun production rollout ham alohida ish.
- **Barcha kontent uchun to‘liq builder va ishlatilgan kontentni keng
  versiyalash** B2 doirasida tugatilmagan. Imtihonning reading/listening savol
  tuzilmalari, SIT/Mini App dizayn qamrovi va vendor/print cheklovlari tegishli
  ledgerlarda ochiq qoladi.
- **UX, DATA va RULE masalalari** bo‘yicha [qabul muammolari ro‘yxati](frontend-v1/FINAL-ACCEPTANCE-ISSUES.md)
  saqlanadi. “B2 tugadi” ularni avtomatik yopmaydi.
- **A2 AI sozlamalari auditi**: mavjud AI settings yozish yuzalariga sabab,
  tasdiq va `SystemAuditEvent`ni qo‘shish qarzi ochiq. **A9 AI eval, latency va cost release gate**
  va boshqa launch gate’lari [launch-ops](launch-plan/05-launch-ops.md)da;
  ularning holati B2 natijasi bilan o‘zgarmaydi.

## Qaysi hujjat nima uchun?

| Kerakli ma’lumot | Asosiy manba |
|---|---|
| Joriy umumiy holat va ochiq chegaralar | **Shu sahifa** |
| Kod tuzilishi, domenlar va ish oqimlari | [project-context.md](project-context.md) |
| Agentning branch, test, commit va merge tartibi | [rules-for-agents.md](rules-for-agents.md), [AGENTS.md](../AGENTS.md) |
| Qachon nima bajarilgani, commit va test dalili | [marinebook.md](marinebook.md) — sanali tarix |
| Backoffice, dizayn va frontend tafsilotlari | [Frontend indeksi](frontend-v1/README.md), [backoffice rejasi](frontend-v1/BACKOFFICE-REFORM-PLAN.md) |
| Classbookning keyingi islohoti | [CLASSBOOK-01](frontend-v1/CLASSBOOK-REFORM-PLAN.md) — audit, foydalanuvchi yo‘llari, sakkiz bosqich va qabul; [I9a](frontend-v1/I9A-PREPARATION.md)/[I9b](frontend-v1/I9B-LIVE.md) — oldingi port dalillari |
| Authenticated dashboard islohoti | [DASHBOARD-01](frontend-v1/DASHBOARD-REFORM-PLAN.md) — learner/teacher/owner/Mini App auditi, projection va role-router contracti, 33 implementatsiya kesimi, 33 E2E gate va rollback |
| Blog/Azure Journal islohoti | [BLOG-01](frontend-v1/BLOG-REFORM-PLAN.md) — code/UX/security tadqiqoti, canonical schema/service, 17 implementatsiya kesimi, 14 qabul ssenariysi va rollback |
| Messengerning keyingi islohoti | [MESSENGER-01](frontend-v1/MESSENGER-REFORM-PLAN.md) — backend/realtime/UX/AI/security auditi, canonical data/command/event contracti, 34 implementatsiya kesimi, 27 E2E gate va rollback; [I4a](frontend-v1/I4A-HUMAN-MESSENGER.md)/[I4b](frontend-v1/I4B-AI-MESSENGER.md) — oldingi port dalillari |
| Payment, Subscription va Checkoutning keyingi islohoti | [COMMERCE-01](frontend-v1/COMMERCE-REFORM-PLAN.md) — finance/security/data/UX auditi, order→payment→subscription→entitlement contracti, 40 reviewable PR-unit, 26 E2E gate va rollback; [I7](frontend-v1/I7-CHECKOUT.md) — oldingi checkout port dalili; [pricing ledgeri](pricing-packages-plan.md) — owner product contracti |
| SIT/“Turkiyada o‘qish” islohoti | [SIT-01](frontend-v1/SIT-REFORM-PLAN.md) — code/UX/AI/security tadqiqoti, version/source/inquiry contracti, 27 implementatsiya kesimi, qabul matrixi va rollback |
| Anonymous/public sirt islohoti | [PUBLIC-01](frontend-v1/PUBLIC-REFORM-PLAN.md) — route/security/UX/privacy/SEO tadqiqoti, offer/intent/claim/legal/certificate contractlari, 36 implementatsiya kesimi, 28 E2E gate va rollback |
| Public sahifalarning yangi (editorial) dizayni | [PUBLIC-02 port rejasi](frontend-v1/PUBLIC-EDITORIAL-PORT-PLAN.md) — prototip dalili, admission, owner qarorlari, prototip → production xaritasi, PE0–PE10 kesimlar, byudjet va rollback |
| Owner strategiyasi, admission va qolgan launch ishlari | [Launch rejasi](launch-plan/README.md) — eski jadval yangi deadline emas |
| Tarif va to‘lov shartlari | [Pricing ledgeri](pricing-packages-plan.md) |
| Telegram va landing bo‘yicha dastlabki shartlar | [Telegram rejasi](telegram-bot-plan.md), [landing rejasi](landing-editor-plan.md) — sanali qismlarni joriy kod bilan birga o‘qing |
| Serverga chiqarish va qaytarish tartibi | [Deploy yo‘riqnomasi](../deploy/README.md) |

`codex-context.md`, eski handofflar, bosqich hisobotlari va marinebookdagi
yozuvlar o‘z sanasidagi dalilni saqlaydi. Ular shu sahifaga parallel yangi
“joriy vazifalar” navbatini yaratmaydi. Owner qarorlari va domen shartlari
esa keyingi aniq qaror bilan almashtirilmaguncha o‘z kuchida qoladi.

## Tekshiruv dalilini qanday o‘qish kerak?

So‘nggi B2.6 lokal dalili: **10/10 ssenariy**, Django **1784 jami / 1735 PASS /
49 skip**, Node **172/172 PASS**. Bu butun loyihaning bugungi test soni emas;
aniq buyruqlar, skip sabablari va muhit [B2.6 hisobotida](frontend-v1/BACKOFFICE-02-STAGE-6.md).
Testlar haqiqiy Gemini/Telegram kalitlarisiz bajarilgan. Shu hujjatlarni
yangilash paytida ushbu natijalar qayta yugurtirilgan deb ko‘rsatilmaydi.

Holat o‘zgarganda shu sahifa, tegishli batafsil contract va marinebook
bir ish doirasida moslashtiriladi. Tarixiy test soni va sana qayta yozilmaydi;
yangi tekshiruv yangi sanali dalil bo‘ladi. “Kodda bor”, “muhitda yoqilgan”,
“tekshirildi”, “owner qabul qildi” va “serverga chiqarildi” alohida qayd qilinadi.
