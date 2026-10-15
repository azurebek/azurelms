# SIT-01 — “Turkiyada o‘qish”ni ishonchli qaror va yordam markaziga aylantirish

**Holat:** REJA TAYYOR, implementatsiya boshlanmagan
**Tadqiqot sanasi:** 2026-10-15
**Kod tayanchi:** `main`dagi `2dfac13`
**Birinchi implementatsiya kesimi:** `SIT1.0a`
**Asosiy mahsulot KPI:** belgilangan SLA ichida ko‘rilgan **kvalifikatsiyalangan
yordam so‘rovlari**, trafik yoki katalogdagi universitet soni emas.

Bu hujjat amaldagi Django kodi, template va testlar; launch contractlari;
owner workflow; rasmiy tashqi manbalar; xavfsizlik, accessibility va SEO
yo‘riqnomalari asosida yozilgan. U dizayn prototipi yoki “g‘oyalar ro‘yxati”
emas. Har bir bosqichda canonical state, yozuvchi service, fayllar, test,
rollback va tugash mezoni bor. Shuning uchun keyingi agent faqat shu hujjatni
o‘qib taxmin bilan katta PR ochmasligi, eng yuqoridagi tugallanmagan kichik
kesimdan davom etishi kerak.

Reja yozilishi runtime, local DB, AWS yoki productionni o‘zgartirmaydi. Eski
`Q17B-SIT-STUDIO-PROTOTYPE.md` — tarixiy UI prototipi; undagi sintetik holat,
komponent yoki test haqiqiy publication/version/inquiry contracti sifatida
qabul qilinmaydi. BACKOFFICE-03dagi `B3.6` umumiy legacy dizayn consumerlarini
portlaydi; SIT-01 uning rang/token ishini takrorlamaydi.

---

## 1. Mahsulot qarori

### 1.1 Yakunda nima quriladi?

SIT quyidagi uch vazifani bitta izchil oqimda bajaradi:

1. **Ishonchli katalog.** Foydalanuvchi universitet emas, aynan o‘ziga mos
   akademik yil + dastur + ta’lim tili + asl valyutadagi kontrakt + qabul
   oynasini topadi. Har vaqtga sezgir faktning qayerdan va qachon
   tekshirilgani ko‘rinadi.
2. **Qaror vositasi.** Bir xil mezonga mos 2–4 variantni taqqoslaydi, nima
   mos kelgani va nima hali noma’lumligini ko‘radi, rasmiy manbaga o‘tadi.
   Katalog “reyting”, “kafolat” yoki yashirin valyuta konvertori bo‘lmaydi.
3. **Kuzatiladigan yordam.** Aniq universitet/dastur kontekstidagi CTA
   canonical `SITInquiry` yaratadi. Messenger — aloqa adapteri; holat DM
   xotirasida qolmaydi. Owner “yangi → bog‘lanildi → kvalifikatsiyalandi →
   jarayonda → yakunlandi/bekor qilindi” navbatini ko‘radi.

AI bu tizimning kirish eshigi yoki haqiqat manbasi emas. Deterministik katalog
avval mos variantlarni topadi; AI faqat shu natijani oddiy tilda tushuntiradi,
yetishmayotganini tan oladi va explicit CTAga olib keladi.

### 1.2 Qamrovga kirmaydigan ishlar

- universitet nomidan ariza yuborish, qabul qilish yoki “kafolat” berish;
- avtomatik web scraping va inson tasdig‘isiz publish;
- viza, denklik, rezidentlik yoki huquqiy masalada yakuniy maslahat;
- “eng yaxshi universitet” reytingi yoki manbasiz scholarship claim;
- avtomatik valyuta konvertatsiyasi; v1 filtri asl valyuta ichida ishlaydi;
- 5 000 so‘mlik jiddiylik to‘lovi: avtomatik payment contracti owner tomonidan
  alohida admit qilinmaguncha UI, inquiry va AI’da claim qilinmaydi;
- pasport, diplom, transkript yoki boshqa hujjat uploadi;
- ko‘p agentli CRM, native mobil ilova, boshqa interfeys tillari;
- AI tomonidan inquiry yaratish, holatini o‘zgartirish yoki rasmiy qaror berish.

### 1.3 Natija va guardraillar

| O‘lchov | Aniq ma’no | Release talabi |
|---|---|---|
| Qualified inquiry | Owner “kvalifikatsiyalandi”ga o‘tkazgan, universitet va maqsad konteksti bor unique so‘rov | Asosiy KPI; duplicate retry alohida lead hisoblanmaydi |
| First response SLA | `created_at`dan birinchi audited `contacted` transitionigacha | Owner sozlagan muddatdan oshganlar navbatda ko‘rinadi |
| Fresh claim coverage | Public ko‘rsatilgan exact narx/muddat/dastur claimlarining amaldagi scoped source’i bor ulushi | 100%; stale exact claim public/AIga chiqmaydi |
| CTA completion | Detaildagi inquiry boshlanishidan canonical row yaratilishigacha | Xato va login-return alohida o‘lchanadi; hidden dark pattern yo‘q |
| Retrieval correctness | Tanlangan barcha filterlar aynan bitta offeringda bajarilgan natija | False-positive fixturelarda 0 |
| Critical AI error | Katalogda yo‘q proper noun, narx, sana yoki rasmiy claim | 0; A9 gate’i ham alohida o‘tadi |
| Owner workload | stale/source/inquiry queue yoshi va soni | Dashboardda ko‘rinadi; avtomatlashtirish haqiqatni publish qilmaydi |

Education outcome, qabul bo‘lish ehtimoli yoki “talaba muvaffaqiyati” bu
relizning KPI’si emas. Bunday claim uchun keyin alohida dalil va admission
kerak.

---

## 2. Tadqiqot va amaldagi kod auditi

### 2.1 Ko‘rilgan ichki yuzalar

- domen: `sit/models.py`, `sit/selectors.py`, `sit/views.py`, `sit/urls.py`;
- owner: `sit/backoffice_forms.py`, `sit/backoffice_views.py`,
  `sit/backoffice_urls.py`, `sit/admin.py` va `templates/backoffice/sit_*`;
- public legacy va V1: `templates/sit/**`,
  `templates/frontend_v1/public/sit/**`, `static/css/sit.css`,
  `static/js/sit-theme.js`, `frontend/public_v1.py`;
- AI: `ai/skills/sit_advisor/SKILL.md`, `ai/skills/registry.py`,
  `ai/tools/context.py`, provider/agent/messenger handoff;
- contractlar: `nuclear-program/launch-plan/**`, BACKOFFICE-03, tarixiy Q17b;
- mavjud testlar: `sit/tests.py`, `sit/test_backoffice.py`,
  `sit/test_ai_advisor.py`, public V1 va messenger testlari.

Safe env’da baseline:

```powershell
$env:AZURELMS_SKIP_ENV_FILE='1'
$env:APP_ENV='local'
$env:LOCAL_USE_REMOTE_SERVICES='False'
$env:GEMINI_API_KEY=''
$env:TELEGRAM_BOT_TOKEN=''
venv\Scripts\python.exe manage.py test sit --noinput --verbosity 1
```

Natija: **28/28 PASS**, system check 0. Bu topilmalarni inkor qilmaydi:
mavjud testlar noto‘g‘ri valyuta semantikasi, bir-offering filteri, stale claim,
misleading CTA va real AI promptlarining routingini to‘liq qoplamaydi.

Xuddi shu safe local profilda read-only sanashda `University 0/0`,
`KnowledgeArticle 0/0` va active published program `0` chiqdi. Bu production
inventari haqida dalil emas; `.env.local` ataylab yuklanmagan. Lekin joriy
checkoutda real katalog bilan public/AI acceptance evidence’i yo‘qligini
anglatadi. Synthetic testning yashilligi real source coverage yoki A9
factuality sign-off o‘rnini bosmaydi.

### 2.2 P0 — keyingi feature’dan oldin tuzatiladigan holatlar

| # | Dalil | Ta’sir |
|---|---|---|
| P0-1 | `sit/selectors.py` til va darajani alohida reverse-join filterlaydi. English bachelor + Turkish master bor universitet “English master” so‘roviga tushishi mumkin. | Foydalanuvchiga mavjud bo‘lmagan kombinatsiya mos deb ko‘rsatiladi. |
| P0-2 | Price bucket `tuition_from` raqamini valyutasiz taqqoslaydi; model USD/EUR/TRY/UZSni saqlaydi. Legacy label bucketlarni `$` deb ataydi, V1 currency mezonini ko‘rsatmaydi. | TRY 2 000 va USD 2 000 bir qiymatdek talqin qilinadi; public va AI budget javobi noto‘g‘ri. |
| P0-3 | `University` darajasidagi bitta `source_url/last_verified_on` barcha dastur, narx, deadline va talabga yoyiladi. 90 kunlik stale faqat owner warning; public va AI stale rowni ishlatadi. | “Tekshirilgan” label dalil qamrovini va dolzarblikni ortiqcha da’vo qiladi. |
| P0-4 | Legacy guide `article.body|safe`, V1 esa keng `sanitize` filteridan foydalanadi; allowlist raw iframe, `style/id/class` kabi keng atributlarni qabul qiladi. | Exploit isbotlanmagan, lekin privileged stored-content XSS/tracking riski va renderer drift mavjud. |
| P0-5 | Public preview istalgan authenticated `is_staff`ga ochiq; dedicated studio owner-only. Legacy preview’da private/no-store/noindex parity yo‘q. | Slugni bilgan oddiy staff qoralamani ko‘ra oladi; cache/index leak riski. |
| P0-6 | `application_help_enabled=True` va 5 000 UZS default public detailda ko‘rinadi, holbuki owner contractida to‘lov bloklangan. CTA universitet kontekstisiz `messenger:tutor`ga boradi. | Prospective user faol enrollmentga ega bo‘lmasa “Tutor chati yopiq” dead-end; lead yaratilmaydi va bloklangan fee claim qilinadi. |
| P0-7 | SIT landingdagi real misollar — “1300 dollar, ingliz tilida muhandislik”, “Turkiyada magistratura”, `TÖMER` va yolg‘iz budget savoli — amaldagi routerda `general_chat`ga tushadi. | SIT advisor mavjud ko‘rinsa ham asosiy intent unga yetib bormaydi. |
| P0-8 | AI tool user mezonini selector’ga bermaydi: doim status/order bo‘yicha birinchi 25 universitet va har biridan 8 dastur. | Exact mos variant #26 yoki program #9 bo‘lsa model uni ko‘rmay, noto‘g‘ri “yo‘q” deya oladi. |
| P0-9 | Gemini requestida alohida haqiqiy system-role contracti yo‘q; instruction va data flat prompt ichida ketadi. SIT source matni ham promptda untrusted blok sifatida qat’iy ajratilmagan. | Admissions/legal kabi sezgir oqim uchun instruction hierarchy va prompt-injection himoyasi yetarli emas. |
| P0-10 | Launch contractida keyingi capability `SITInquiry`, lekin model/service/route/queue yo‘q. | Asosiy KPI’ni hisoblab bo‘lmaydi; messenger canonical state vazifasini bajara olmaydi. |
| P0-11 | Skill visa, scholarship va hujjatlarni qamrashini aytadi, lekin tool guide body/source, requirement/document yoki structured scholarship factini bermaydi. | AI o‘ziga berilmagan evidence doirasida yordam va’da qiladi; v2gacha scope katalog taqqoslash bilan cheklanadi. |
| P0-12 | AI memory default ON; raw chat va AI run savol nusxasi saqlanadi, attachment oqimi SITga xos retention/disclosurega ega emas. | Talabgor passport/transkript yuborishi mumkin; point-of-collection warning va retention qarorisiz SIT advisor attachment/memory bilan ship qilinmaydi. |

`SIT1.0a–d` tugamasdan redesign, compare yoki AI advisor v2 release qilinmaydi.
Fee claim va dead-end CTA containmenti eng kichik xavfsiz PRga kiradi.

### 2.3 P1 — radikal islohotning asosiy qarzlari

- published rowning o‘zi draft ham live ham: tahrir live/AIga darhol chiqadi;
  “save draft” esa oldin live bo‘lgan rowni unpublish qiladi;
- published snapshot, revision, diff, rollback, schedule operation, CAS,
  idempotency receipt va immutable before/after audit yo‘q;
- ikki tabdagi edit last-write-wins; `select_for_update` va expected revision yo‘q;
- Django admin `list_editable` va inline’lari reason/audit/service’ni aylanadi;
- `LogEntry` matni canonical append-only audit ledger emas;
- future announcement `published_on`ga qaramay hozir chiqadi; guide publish sanasi
  availabilityga ta’sir qilmaydi;
- `clean()` `QuerySet.update()`/bulk writerdan himoya qilmaydi; future
  verification, negative amount va deadline/status DB invariantlari yo‘q;
- university delete childlarni `CASCADE` qiladi, tarix va inquiry reference’i yo‘q;
- faqat home/list/detail/guide-detail bor; guide archive, announcement archive va
  announcement detail yo‘q, featured bo‘lmagan guide topilmay qoladi;
- qidiruv universitet nomi/shahar bilan cheklangan; program/faculty bo‘yicha
  qidiruv va aynan nima match bo‘lganini ko‘rsatish yo‘q;
- legacy mobil nav `820px` ostida butunlay yashirinadi; replacement yo‘q;
- legacy skip-link yo‘q, focus outline olib tashlangan, ayrim kichik matn
  kontrasti AA minimumidan past; form label placeholderga suyangan;
- canonical, OG, sitemap, structured data yo‘q; V1 barcha public response’ni
  `private, no-store` qiladi;
- cover/media width/height/srcset/meaningful alt yo‘q; legacy public Google
  Fonts va jsDelivrga render-critical bog‘langan;
- global staff preview, direct admin va AI/public selectorlari bir xil policy
  objectidan foydalanmaydi;
- child dastur, talab, hujjat va guide body uchun scoped provenance yo‘q;
- AI guide’dan faqat title oladi, source/freshness/body bermaydi; UI SIT
  source citationlarini ko‘rsatmaydi;
- audit boshidagi launch hujjatidagi `S3 EVIDENCE READY` labeli foundationni
  release evidence deb ortiqcha talqin qilgan: A9 teacher-authored grounded eval
  hali PLANNED va current public CTA mavjud; status shu plan bilan tuzatildi.

### 2.4 P2 — alohida kichik qarzlar

- parallel bir xil slug create `exists()` race’dan `IntegrityError` berishi mumkin;
- university create’ning birinchi POSTida child formset yo‘q; oldin parent,
  keyin faculty, keyin program saqlashga majbur;
- hard-coded `STALE_AFTER_DAYS=90` deploysiz o‘zgarmaydi;
- duplicate child text va teng order uchun barcha joyda deterministic constraint
  yo‘q;
- image extension/size bor, lekin magic-byte va dimension canonical gate emas;
- media replacement orphan blob cleanup/reference trackingga ega emas;
- SIT obyektlari umumiy backoffice search/recent oqimiga to‘liq kirmaydi.

---

## 3. Tashqi tadqiqotdan chiqarilgan product qoidalari

Bu ro‘yxat raqobatchi UI’ni ko‘chirish emas; authoritative manba va ochiq
standartlardan chiqarilgan contractdir.

1. YÖK’ning xalqaro qabul sahifasi xalqaro talabgor universitet belgilagan
   mezon va talab qilingan hujjatlar bilan to‘g‘ridan-to‘g‘ri universitetga
   murojaat qilishini aytadi. Demak AzureLMS umumiy “bitta universal qabul
   qoidasi” yaratmaydi; universitet/cycle-scoped source saqlaydi:
   [YÖK xalqaro qabul mezonlari](https://www.yok.gov.tr/ogrenci/yurt-disinda-kabul-edilecek-ogrenci-kontenjanlari).
2. TR-YÖS sana va qo‘llanmalari uchun canonical manba universitet blogi yoki
   AI xotirasi emas, ÖSYMning yil bo‘yicha rasmiy oqimi:
   [ÖSYM TR-YÖS](https://www.osym.gov.tr/SinavGrubu/Index/13).
3. YÖK Atlas o‘zini qarorni almashtiradigan “tercih robotu” emas, reference
   platforma sifatida tutadi; SIT ham “mos variant”ni tushuntiradi, qabul
   kafolati bermaydi:
   [YÖK Atlas](https://yokatlas.yok.gov.tr/lisans-panel.php?m=1&p=1010&y=105610828).
4. KVKK tamoyillari personal data’ni aniq maqsad, minimal/proportsional hajm,
   dolzarblik va kerakli muddat bilan cheklashni talab qiladi. Inquiry v1
   passport/grade/document yig‘maydi va retention/anonymization contractisiz
   yangi PII qo‘shmaydi:
   [KVKK umumiy tamoyillari](https://www.kvkk.gov.tr/Icerik/6606/General-Principles-in-Processing-of-Personal-Data).
5. W3C WCAG 2.2 AA reflow, keyboard, visible focus, input assistance,
   24×24 minimum target va programmatic statusni qamraydi. Mahsulot primary
   controllar uchun 44px ichki target oladi, lekin normative minimumni to‘g‘ri
   nomlaydi:
   [WCAG 2.2 Understanding](https://www.w3.org/WAI/WCAG22/Understanding/),
   [Reflow](https://www.w3.org/WAI/WCAG22/Understanding/reflow.html),
   [Target Size Minimum](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum).
6. OWASP author HTML kerak bo‘lsa contextga mos encoding va allowlist
   sanitization zarurligini, URL/protocol ham alohida validatsiya qilinishini
   qayd etadi. Raw `safe` yoki CSP sanitizer o‘rnini bosmaydi:
   [OWASP XSS Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet).
7. Google paginated sahifalarda har page uchun crawlable `<a href>`, unique
   URL va self-canonical; filter/sort variantlarini indekslamaslikni tavsiya
   qiladi. Canonical, redirect va sitemap signallari bir-biriga zid bo‘lmasligi
   kerak:
   [pagination guidance](https://developers.google.com/search/docs/specialty/ecommerce/pagination-and-incremental-page-loading),
   [canonical guidance](https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls).
8. Structured data faqat visible contentni aks ettiradi; yashirin yoki
   chalg‘ituvchi claim markupga qo‘shilmaydi. `CollegeOrUniversity` va
   `EducationalOccupationalProgram` vocabulary bo‘lishi mumkin, lekin Google
   rich resultini kafolatlamaydi:
   [Google structured-data policy](https://developers.google.com/search/docs/appearance/structured-data/sd-policies),
   [Schema.org program turi](https://schema.org/EducationalOccupationalProgram).

### 3.1 Manbalar ierarxiyasi

| Fakt | Birlamchi manba | Fallback | Taqiqlangan canonical manba |
|---|---|---|---|
| Universitet identiteti/statusi | YÖK yoki universitetning rasmiy domeni | owner tasdiqlagan boshqa davlat registri | aggregator, social post |
| Program, til, tuition, deadline, hujjat | universitetning aynan xalqaro qabul/program sahifasi yoki rasmiy PDF | YÖKdagi mos scoped hujjat | marketing agentligi, screenshotning o‘zi |
| TR-YÖS | ÖSYM | yo‘q; source unavailable bo‘lsa fakt yashiriladi | blog/AI javobi |
| Scholarship | Türkiye Bursları yoki universitetning rasmiy sahifasi | tegishli davlat tashkiloti | “100% grant” reklama claimi |
| Viza/rezidentlik/denklik | vakolatli davlat tashkiloti/elchixona/YÖK | owner tasdiqlagan rasmiy guidance | forum, influencer, model xotirasi |
| AzureLMS yordami | AzureLMS service contracti | yo‘q | universitet nomidan va’da |

HTTP 200 — “fakt tekshirildi” degani emas. Owner scoped faktni ko‘rib,
source snapshot yaratadi; avtomatik link checker faqat “reachable/broken”
signalini beradi.

---

## 4. Foydalanuvchilar va axborot arxitekturasi

### 4.1 Rollar

| Rol | Huquq | Chegara |
|---|---|---|
| Anonymous visitor | katalog, guide/e’lon, filter, compare | inquiry/advisor uchun login; qoralama ko‘rmaydi |
| Authenticated prospect | yuqoridagilar + o‘z inquiry’ini yaratish/ko‘rish + SIT advisor | boshqa foydalanuvchi inquiry’i va owner note’ini ko‘rmaydi |
| Ordinary staff/teacher | odatiy LMS huquqlari | SIT draft/preview/write huquqi avtomatik berilmaydi |
| SIT editor | draft va source tayyorlaydi, preview faqat ruxsatli item | publish/inquiry PII yo‘q, agar alohida permission berilmasa |
| SIT publisher/owner | review/publish/rollback, source va inquiry queue | barcha action reason+confirmation+audit; superuser bypass yozuvsiz bo‘lmaydi |
| System worker | due publish, reminder, reconciliation | ayni service/idempotency contracti; yangi haqiqat yaratmaydi |

Solo-owner startida editor va publisher bitta odam bo‘lishi mumkin. Shunga
qaramay permission/service ajratiladi: keyin staff qo‘shilganda `is_staff`
fallback xavfsizlik chegarasini buzmasin.

### 4.2 Public yo‘l

1. `/sit/` foydalanuvchini “dastur topish”, “qabulni tushunish” va
   “yordam so‘rash” intentlariga ajratadi.
2. `/sit/programs/` asosiy intent-first katalog bo‘ladi; `/sit/universities/`
   esa institution browse sifatida qoladi. Qidiruv program/university/city
   bo‘yicha; daraja,
   til, status, cycle va **aniq valyuta** filtri bilan server-rendered ishlaydi.
3. Natija kartasi “nima match bo‘ldi”ni: program, daraja, til, original
   amount/period/cycle va freshnessni ko‘rsatadi. Universitet aggregate’i
   matching offering o‘rniga ko‘rsatilmaydi.
4. 2–4 variant `/sit/compare/`da bir xil qatorlarda taqqoslanadi. Missing
   fakt `—` emas, “ma’lumot tasdiqlanmagan” deb tushuntiriladi.
5. Detailda universitet profili, cycle, matching programs, requirements,
   official sources, verification state va disclaimer bor.
6. “Yordam so‘rash” login bo‘lmasa ayni detailga qaytadigan `next` bilan
   autentifikatsiyaga yuboradi; login bo‘lsa explicit confirm form ochadi.
7. Successful POST canonical inquiry ID va status sahifasini beradi; keyin
   messenger shu ID bilan ochilishi mumkin. Browser refresh duplicate lead
   yaratmaydi.

Core katalog, compare va official-source link JSsiz ishlaydi. Enhanced filter
chips yoki client-side compare core funksiyaning yagona yo‘li bo‘lmaydi.

### 4.3 Owner yo‘l

1. Dashboard to‘rtta queue beradi: `Kuzatish kerak`, `Manba yetishmaydi`,
   `Nashrga tayyor qoralamalar`, `Javob kutilayotgan so‘rovlar`.
2. Owner mavjud effective versiondan yangi draft clone qiladi. Live snapshot
   tahrir davomida o‘zgarmaydi.
3. “Asosiy”, “Qabul cycle”, “Dasturlar/narx”, “Talab/hujjat”, “Media”,
   “Manba va tekshiruv” qadamlarida har bo‘lim alohida saqlanadi.
4. Readiness panel qaysi exact claimga source/freshness yetishmasligini
   ko‘rsatadi. Source URL borligi o‘zi yetarli emas.
5. Preview effective vs draft diff, desktop/mobile va official linklarni
   ko‘rsatadi; analytics va public cachega kirmaydi.
6. Submit/review/publish bir service orqali expected revision va operation key
   bilan bajariladi. Stale tab `409`-equivalent form conflict beradi.
7. Rollback eski immutable versionni yangi publication operation bilan current
   qiladi; tarixiy rowni joyida o‘zgartirmaydi.
8. Inquiry queue’da owner assignee, age/SLA, university, maqsad, next action va
   audited transitionni ko‘radi; DMdan qaytganda ham canonical row yangilanadi.

### 4.4 Target URL xaritasi

| URL | Audience/index | Vazifa |
|---|---|---|
| `/sit/` | public/index | intent landing, fresh catalog summary, guide/e’lon |
| `/sit/programs/` | public; clean pagination index, arbitrary filter noindex | asosiy program/offering search va matched cards |
| `/sit/universities/` | public; clean pagination index, arbitrary filter noindex | search/filter/result |
| `/sit/universities/<slug>/` | public/index | effective university snapshot |
| `/sit/compare/?offering=<uuid>&offering=<uuid>` | public/noindex | 2–4 stable offering variant compare; PII yo‘q |
| `/sit/guides/` | public/index | barcha effective guide |
| `/sit/guides/<slug>/` | public/index | source-backed guide |
| `/sit/announcements/` | SIT-D3 `ADMIT` bo‘lsa public/index | current/scheduled-to-now announcement archive |
| `/sit/announcements/<slug>/` | SIT-D3 `ADMIT` bo‘lsa public/index | announcement detail/source |
| `/sit/advisor/` | auth/private | forced SIT mode va starter form |
| `/sit/inquiries/new/` | auth/private | explicit confirm POST |
| `/sit/inquiries/<uuid>/` | owner yoki row egasi/private | status va safe next step |
| `/backoffice/sit/freshness/` | permitted staff/private | source/freshness queue |
| `/sitemap.xml` | public/indexing infrastructure | faqat effective canonical URLlar va haqiqiy `lastmod` |
| `/robots.txt` | public/indexing infrastructure | sitemap pointer; `noindex` o‘rnini bosmaydi |
| `/backoffice/sit/inquiries/` | permission/private | owner lead queue |
| `/backoffice/sit/universities/<id>/history/` | permission/private | diff/audit/rollback |

Eski to‘rtta URL saqlanadi. Slug o‘zgarsa `301` faqat explicit
`SITSlugRedirect`dan; unknown eski slug soft match qilinmaydi.

---

## 5. Canonical data va policy contracti

### 5.1 Asosiy qoida

`University` identitet, `UniversityVersion` esa public haqiqatdir. Public,
AI, sitemap, compare va inquiry contexti faqat bitta `effective_version`
projectionidan foydalanadi. Draft row hech qachon `is_published` booleanini
flip qilib live rowning o‘ziga aylanmaydi.

Yangi schema avval additive bo‘ladi. Legacy field/jadvallar cutover va rollback
oynasida saqlanadi; o‘sha deployda column drop yoki destructive data migration
yo‘q.

### 5.2 Model yo‘nalishi

#### `SITSettings`

Singleton, `state_revision` bilan:

- `admission_fresh_days` — initial 14;
- `offering_fresh_days` — initial 30;
- `requirements_fresh_days` — initial 30;
- `profile_fresh_days` — initial 180;
- `guide_fresh_days` — initial 90;
- `source_review_grace_days` — initial 7;
- `inquiry_duplicate_hours` — initial 24;
- `inquiry_first_response_hours` — initial 24;
- `inquiry_retention_days` — owner/legal reviewdan keyin beriladi;
- `comparison_limit` — initial 4.

Bu qiymatlar operational threshold, permission yoki feature enable emas.
Enable/disable faqat `core/flags.py`dagi flag. Retention qarori kelmaguncha
purge worker yoqilmaydi va yangi ortiqcha PII yig‘ilmaydi.

Settings mutationi ham raw Django admin edit emas: `update_sit_settings()`
`expected_revision`, reason, explicit confirmation va `SystemAuditEvent` bilan
ishlaydi. Yuqoridagi freshness sonlari product truth emas, xavfsiz boshlang‘ich
engineering defaultlaridir; production pilotdan oldin owner source cadence va
capacity bo‘yicha ularni tasdiqlaydi.

Bounds: scope freshness `1..3650` kun, review grace `0..90` kun, duplicate va
first-response `1..168` soat, comparison `2..4`; retention aynan `NULL`
(qaror yo‘q, purge taqiqlangan) yoki owner/legal qaroridan keyin `1..3650` kun.
Normalized no-op revisionni oshirmaydi va audit event yaratmaydi, lekin typed
unchanged receipt qaytaradi; haqiqiy o‘zgarish reason+confirmation talab qiladi.

#### `University`

Stable identity:

- mavjud primary key va canonical slug saqlanadi;
- `lifecycle_status = active|archived`;
- nullable `effective_version`, `scheduled_version`;
- `state_revision`, `archived_at/by`;
- official identity uchun kerak bo‘lsa YÖK/owner-approved identifier;
- legacy fieldlar backfill/cutover davomida read-only compatibility sifatida.

`effective_version` `PROTECT`; university hard-delete yo‘q. Slug tarixini
`SITSlugRedirect(old_slug unique, university, created_at, reason)` saqlaydi.

#### `UniversityVersion`

- `(university, version_number)` unique;
- `state = draft|in_review|approved|scheduled|effective|retired`;
- `based_on`, `created_by/at`, `updated_by/at`, `submitted_at`, `approved_by/at`,
  `scheduled_for`, `published_by/at`, `retired_at`;
- name/short name/city/location/type/profile/cover/order/featured kabi mutable
  public fieldlar;
- sanitizer/policy version va readiness fingerprint;
- bir university uchun ko‘pi bilan bitta mutable draft conditional constraint;
- `in_review`dan boshlab row va child graph service tashqarisida immutable.

Owner solo bo‘lsa `submit_and_publish` kompozit UI actioni mumkin, lekin service
ichida review/publish invariantlari, reason, confirmation va audit bekor
qilinmaydi.

#### Stable child identitet va version rowlar

- `SITFaculty(university, stable_key, lifecycle_status)`;
- `SITProgram(university, stable_key, lifecycle_status)`;
- `SITOffering(program, stable_key UUID, lifecycle_status)` — til/cycle kabi
  exact variantning revisionlararo public identiteti;
- `SITFacultyVersion(university_version, faculty, name, order)`;
- `SITAdmissionCycleVersion(university_version, stable_key, academic_year,
  term, opens_on, deadline, status_override, source_snapshot)`;
- `SITProgramOfferingVersion(university_version, offering, program, faculty_version,
  admission_cycle, name, degree_level, language, duration_value,
  duration_unit, tuition_amount, tuition_currency, fee_period,
  program_source_snapshot, tuition_source_snapshot, is_available, order)`;
- version-scoped preparation, requirement, required-document, service-item va
  structured media rowlari.

`duration` va fee period erkin matn emas: duration `value+unit`, tuition
`amount+ISO currency+per academic_year|term|program` bo‘ladi. Public label
projectionda yaratiladi. Existing `UniversityFaculty/UniversityProgram` IDlari
dedicated `SITLegacyFacultyMap`/`SITLegacyProgramMap` (`legacy_id` unique,
stable faculty yoki program+offering `OneToOne(PROTECT)`, backfill receipt)
orqali saqlanadi; heuristik name/slug remap yo‘q, inquiry va redirect identiteti
uzilmaydi.

`SITProgram.stable_key` va `SITOffering.stable_key` guess qilinmaydigan UUID;
compare URLda exact offering UUID ishlatiladi. Brauzer labeli, universitet
slug’i yoki ichki ketma-ket PK offering identiteti sifatida authoritative emas.

Cross-parent invariantlar majburiy: university pointer faqat o‘z versioniga;
faculty/program faqat o‘z universitetining version childiga; offering, cycle va
source link ayni version graphga; inquiry university/program/version/offering
ham ayni universitet va snapshotga tegishli. Service transactionda tekshiradi,
PostgreSQLda `DEFERRABLE` constraint triggerlari cross-table invariantni direct
ORM/bulk writerga qarshi ham saqlaydi. SQLite compatibility testi service
guardni, PostgreSQL adversarial testi esa mismatched parent insert/update va
deferred valid transactionni isbotlaydi.

#### `SITSourceSnapshot`

- immutable `url`, normalized host va `source_kind`;
- `fact_scope = profile|admission|program|tuition|requirements|preparation|document|service|media|guide|announcement`;
- `verified_at` timezone-aware, `verified_by`, `valid_until`;
- qisqa owner note, optional ETag/Last-Modified va content fingerprint;
- snapshot yaratilgan paytdagi `verification_status`;
- qaysi version/faktni isbotlashi explicit FK/through relationda.

Scope → field mapping ixtiyoriy generic label emas:

| Scope | Exact target |
|---|---|
| `profile` | `UniversityVersion` name/type/city/location/about |
| `admission` | bitta `SITAdmissionCycleVersion` opens/deadline/status |
| `program` | bitta offering name/degree/language/duration/availability |
| `tuition` | bitta offering amount/currency/fee period |
| `requirements` | bitta requirement/exam threshold row |
| `preparation` | bitta preparation language/duration/fee row |
| `document` | bitta required-document row |
| `service` | bitta service item; commercial public gate alohida |
| `media` | bitta media asset provenance/rights/alt recordi; academic claim emas |
| `guide` | `KnowledgeArticleVersion`dagi citation block |
| `announcement` | `AnnouncementVersion`dagi dated claim/source block |

Offering program va tuition uchun ikkita scoped FK saqlaydi; bitta umumiy
university source’i ikkala scope readinessini jim o‘tkazmaydi. Generic
`ContentType + object_id` evidence link ishlatilmaydi.

Keyingi reachability natijasi immutable snapshotni edit qilmaydi.
`SITSourceCheck(source_snapshot, checked_at, status, final_url_digest,
response_metadata)` append-only event bo‘ladi; policy eng so‘nggi eligible checkni
o‘qiydi. Link checker SSRF-safe: faqat `http/https` va approved portlar; har DNS
resolve va redirect hopda loopback/private/link-local/multicast/metadata/
reserved IPv4/IPv6 rad; credential/cookie yo‘q; DNS-rebindingga qarshi resolved
IP connectiongacha qayta tekshiriladi; URL userinfo rad; redirect soni,
connect/read timeout, response byte va content-type qat’iy bounded. Checker
HTMLni execute qilmaydi. Shu guardlar va adversarial testlar bo‘lmasa automated
fetch ship qilinmaydi; owner linkni brauzerda qo‘lda tekshiradi.

Reachability fact verification emas: timeout/4xx/5xx faqat queue signalini va
kamida `review_due` holatini beradi; fingerprint o‘zgarishi yangi publishni
`quarantined` qiladi. Checker effective versionni edit/unpublish qilmaydi va
`verified_at`ni surmaydi. Faqat owner tekshirgan yangi immutable snapshot state’ni
yangilaydi; hard expiry exact critical factni baribir yashiradi.

To‘liq third-party page nusxasi saqlanmaydi. Zarur excerpt minimal va license/
policyga mos bo‘ladi. `verified_at > now` invalid. Host allowlistning o‘zi
faktni to‘g‘ri qilmaydi; scope mismatch readinessni o‘tkazmaydi.

#### Guide va announcement

`KnowledgeArticle` domain sifatida hozircha SITda qoladi: uning source/freshness
semantikasi umumiy Journaldan farq qiladi. BLOG-01 bilan raw model merge
qilinmaydi. Ikkalasi bitta strict rich-content policy engine’dan foydalanadi.

- mavjud `KnowledgeArticle` stable identity bo‘lib qoladi; unga nullable
  effective/scheduled pointerlar va immutable `KnowledgeArticleVersion`
  qo‘shiladi;
- raw author source, canonical sanitized `rendered_body`, `policy_version`;
- source snapshot, effective/scheduled state, cover/alt;
- mavjud `Announcement` stable identity bo‘lib qoladi; immutable
  `AnnouncementVersion` body/excerpt/source/effective window va detail slugni
  saqlaydi;
- future schedule GET vaqtida DB write qilmaydi; due promotion worker/service
  idempotent, visibility esa time-aware selector bilan to‘g‘ri qoladi.

BLOG1.0a1 yoki SIT1.0a qaysi biri oldin implement qilinsa,
`core/rich_content_policy.py`ni o‘sha PR yaratadi; ikkinchi domen yupqa wrapper
bilan reuse qiladi. Canonical ownership `core`; ikki allowlist fork qilinmaydi.

### 5.3 Freshness va public eligibility

`sit/policy.py` yagona qaror beradi:

```text
fact_state = current | review_due | expired | missing_source | quarantined
public_value = exact value | “qayta tekshirilmoqda” | hidden
```

- `review_due_at = min(verified_at + scope_fresh_days, valid_until)` agar
  `valid_until` bor; bo‘lmasa `verified_at + scope_fresh_days`;
- explicit `valid_until` bo‘lsa `expired_at = valid_until`: u hard expiry bo‘lib
  computed grace’dan ustun turadi; u bo‘lmasa
  `expired_at = review_due_at + source_review_grace_days`;
- `now < review_due_at` current; `review_due_at <= now < expired_at`
  review_due; `now >= expired_at` expired. Exact boundary timezone-aware testda;
- deadline/admission status, tuition, offering va requirements expired bo‘lsa
  exact qiymat public va AI’dan olib tashlanadi/yashiriladi; universitet
  identity/detail sahifasi qolishi mumkin;
- `review_due` ko‘rinadi, lekin aniq “tekshirilgan sana” va warning bilan;
- passed deadline + manual `open` contradictionida effective status `closed`;
  owner queue’da `verification_required` violation ochiladi, “open” chiqmaydi;
- future `opens_on` avtomatik `soon`, open window `open`, deadline o‘tganida
  `closed`; override faqat source+reason bilan;
- official source unreachable bo‘lsa exact fakt darhol avtomatik unpublish
  qilinmaydi, lekin queuega signal; oldindan expired bo‘lsa hidden qoladi;
- selector GET hech qachon warning/repair row yaratmaydi.

Public, AI, sitemap va compare ayni policy projectionini ishlatadi. “AI uchun
alohida yumshoq freshness” yo‘q.

### 5.4 Currency va filter contracti

V1 qoida: **konvertatsiya yo‘q**.

- filterda currency majburiy; min/max faqat shu ISO currencydagi matching
  offeringga qo‘llanadi;
- original amount, currency, fee period va academic cycle birga ko‘rinadi;
- university `tuition_from` manually trusted fact emas; current offeringlardan
  currency kesimida derived summary;
- til + degree + currency + price + cycle bitta
  `Exists(SITProgramOfferingVersion...)` subquery/alias ichida qo‘llanadi;
- inactive faculty/program, non-effective version va expired tuition match
  bermaydi;
- search program/faculty/university/cityga boradi, lekin card aynan matched
  offeringlarni qaytaradi.

Query parser contracti ham canonical:

- `q` Unicode-normalized, trim va 120 belgigacha; `İ/I`, apostrof va
  owner-approved `YÖS/YOS`, `TÖMER/TOMER` aliaslari testli;
- enum/currency/page singleton parametri ikki marta yoki unknown qiymat bilan
  kelsa silent coercion emas, accessible `400` recovery formi;
- valid filterda zero result `200 noindex` va filter relaxation linklari;
- `page=1` clean URLga normalize, mavjud bo‘lmagan positive page `404`;
- stable ordering har doim unique PK/stable key tie-breaker bilan;
- pagination helper eski `page` parametrini qayta append qilmaydi.

Keyin approximate conversion admit qilinsa alohida versionlangan FX source,
rate timestamp, original amount va “taxminiy” label shart. Uning yo‘qligida
AI ham valyutalarni solishtirmaydi.

### 5.5 Publication transitionlari

| From | Action | To | Kim | Invariant |
|---|---|---|---|---|
| none/effective | clone draft | draft | editor | live pointer o‘zgarmaydi |
| draft | save | draft | draft owner/editor | expected revision + operation key |
| draft | submit | in_review | editor | readiness complete |
| in_review | request changes | draft | publisher | reason/audit |
| in_review | approve | approved | publisher | source/freshness/security valid |
| approved | publish now | effective | publisher | atomic pointer swap |
| approved | schedule | scheduled | publisher | future datetime, single scheduled pointer |
| scheduled | reschedule/cancel | scheduled/approved | publisher | stale operation rejected |
| effective | unpublish/archive | retired | publisher | reason, safe public result |
| retired/old effective | rollback | new effective operation | publisher | old immutable row edited emas |

Har mutation `select_for_update`, `expected_state_revision`, unique
`operation_id`, normalized fingerprint va `SystemAuditEvent` before/after
bilan bir transactionda. Ayni key+payload retry oldingi receiptni qaytaradi;
ayni key+boshqa payload conflict. Audit yozilmasa mutation ham commit bo‘lmaydi.

`effective_version(university, as_of)` workerga qaramaydi: scheduled pointer
bor va `scheduled_for <= as_of` bo‘lsa due versionni read-only tarzda effective
deb qaytaradi, aks holda current pointer. `promote_due` worker ayni service va
operation receipt bilan pointerlarni housekeeping uchun atomik almashtiradi;
kech ishlashi visible `published_at`ni surmaydi. GET pointer promote, audit yoki
repair queue yozmaydi. Cancel/reschedule/publish race row lock va expected
revision bilan bitta winnerga ega.

### 5.6 Inquiry contracti

#### `SITInquiry`

- UUID public ID; internal bigint bo‘lsa URLda chiqmaydi;
- nullable `user` (`SET_NULL`), university, optional stable program/offering; user
  deletion/retention service avval goal/contact va requesterga bog‘liq event
  detailini anonymize qiladi, keyin FK unlink bo‘ladi;
- `university_version` va optional offering snapshot FK — CTA paytidagi haqiqat;
- `source_surface`, `return_url`ning server-resolved safe identiteti;
- `goal` max 800 plain text; passport/grade/document/medical PII yo‘q;
- `preferred_contact_channel` faqat mavjud verified account kanallaridan;
- `status`, `state_revision`, optional assignee;
- `first_contacted_at`, `qualified_at`, `next_action_at`, `closed_at`;
- `privacy_notice_version`, `notice_acknowledged_at`; bu avtomatik tarzda
  KVKK/GDPR legal consenti deb nomlanmaydi — alohida consent kerak bo‘lsa
  purpose, lawful basis va withdrawal contracti owner/legal tomonidan beriladi;
- `client_request_id`/idempotency receipt, timestamps;
- cancellation/spam/terminal reason controlled vocabulary + owner note alohida.

State machine:

```text
new -> contacted | cancelled | spam
contacted -> qualified | cancelled | spam
qualified -> in_progress | completed | cancelled
in_progress -> completed | cancelled
cancelled -> contacted       # faqat explicit reopen action + reason
completed | spam             # terminal; transition yo‘q
```

User `new|contacted|qualified|in_progress` holatida withdraw POST bilan
`cancelled(reason=user_withdrawn)` qila oladi; bu action userga owner internal
note maydonini yozishga ruxsat bermaydi.
Cancelled inquiry’ni faqat owner `contacted`ga explicit reason bilan qayta
ochadi. Completed/spam qayta ochilmaydi; yangi intent yangi inquiry bo‘ladi.

Create auth+CSRF POST. Service transaction ichida bir user+university+program
uchun configured duplicate windowdagi open inquiry’ni lock qilib topadi;
same intent duplicate bo‘lsa existing receipt qaytadi. Cache rate limit defense
in depth, DB idempotency o‘rnini bosmaydi. Exact limit `SITSettings`da;
anonymous IP tracking canonical PIIga aylanmaydi.

“Same intent” server kaliti: `(user, university, stable_offering_or_null,
admission_cycle_or_null)` va open holatlar `{new, contacted, qualified,
in_progress}`. Free-text goal dedupe kalitiga kirmaydi. Ayni contextda yangi
maqsad kerak bo‘lsa user mavjud receipt/status sahifasidan “yangi so‘rov”ni
explicit boshlaydi; bu action alohida operation receipt oladi.

Parallel birinchi submitlarda hali lock qilinadigan inquiry row bo‘lmasligi
mumkin. Shu sabab service avval actorning `User` rowini `select_for_update()`
bilan serialize qiladi, keyin duplicate window queryni bajaradi; qo‘shimcha
ravishda `(user, client_request_id)` unique constraint bor. Nullable programga
tayanadigan partial unique constraintning o‘zi duplicate-window contracti emas.
PostgreSQL parallel transaction testi aynan shu race’ni isbotlaydi.

`SITInquiryEvent` append-only: from/to, nullable actor + role snapshot,
controlled `reason_code`, operation id va timestamp; unda free text yo‘q.
Retention-bounded owner/user note kerak bo‘lsa u alohida `SITInquiryNote`da,
audited access bilan va anonymizationda o‘chadi. User status copy reason codeda
deterministik; owner internal note’ini ko‘rmaydi. Messenger message metadata’da
inquiry UUID bo‘ladi, ammo message delete/room access inquiry state’ni
o‘zgartirmaydi.

Canonical Notification/outbox intent inquiry bilan **bitta transactionda**
yoziladi; faqat broker/providerga tashqi dispatch `on_commit`dan keyin. Provider
failure leadni yoki delivery intentini yo‘qotmaydi; owner queue
`notification_failed` signalini ko‘radi. Inquiry yaratish paymentga bog‘lanmaydi.

---

## 6. Yozuvchi va o‘quvchi arxitekturasi

### 6.1 Tavsiya etilgan modul chegaralari

```text
sit/
  policy.py                 permission, freshness, visibility, preview
  selectors.py              read-only effective projections
  editorial_service.py      draft/review/publish/schedule/rollback
  inquiry_service.py        create/transition/assign/reopen
  source_service.py         source snapshot va readiness
  presentation.py           labels, JSON-LD-safe projection
  management/commands/
    backfill_sit_versions.py
    reconcile_sit_catalog.py
    purge_sit_inquiries.py   # retention qaroridan keyin
```

View/form/admin model `.save()`, `.update()` yoki pointer flip qilmaydi.
Service typed command qabul qiladi va typed result/receipt qaytaradi.

Minimal service signatures:

```python
save_university_draft(*, actor, university_id, expected_revision,
                      operation_id, payload, reason) -> EditorialReceipt
submit_university_version(...)
publish_university_version(...)
schedule_university_version(...)
rollback_university(...)
update_sit_settings(*, actor, expected_revision, operation_id,
                    payload, reason) -> SettingsReceipt

create_inquiry(*, actor, university_id, program_id, offering_id, version_id,
               client_request_id, payload) -> InquiryReceipt
transition_inquiry(*, actor, inquiry_id, expected_revision,
                   operation_id, target, reason) -> InquiryReceipt
```

Payload server-side allowlist bilan normalized; browser bergan price/source/
version label authoritative emas. `operation_id` UUID format/length bilan
tekshiriladi.

### 6.2 Direct writer policy

- Django admin katalog/version/source/inquiry uchun avval read-only diagnostic;
- allowed action service formga olib boradi, `list_editable` olib tashlanadi;
- bulk publish/unpublish yo‘q; keyingi bulk verify har rowni service orqali
  validation/audit bilan o‘tkazmasa ship qilinmaydi;
- ordinary staff fallback yo‘q; custom permissions va owner mapping preflight;
- DB constraint model `clean()`ni aylanadigan writerlarga qarshi minimal
  invariantni saqlaydi;
- program/version/inquiry referencelar `PROTECT`; hard-delete o‘rniga archive.

### 6.3 Preview contracti

- `can_preview_sit_version(user, version)` yagona policy;
- ordinary staff: 404; editor: ruxsatli item; publisher/owner: barcha;
- opaque preview token qo‘shilsa short-lived, signed, single scope; URL slugning
  o‘zi capability emas;
- response `private, no-store`, `noindex,nofollow`, `X-Robots-Tag` parity;
- preview analytics, inquiry CTA, share/canonical sitemap, AI index va repair
  write’larini yaratmaydi;
- legacy va V1 ayni safe projection; flag OFF raw sourcega qaytarmaydi.

---

## 7. Public tajriba va owner studiyasi

### 7.1 Katalog natijasi

Desktop sidebar va mobile disclosure ayni GET formdan foydalanadi. Har fieldda
visible label, hint va reset bor. Applied filterlar removable link/chip; “hammasini
tozalash” clean URLga olib boradi. Result count `role=status`/`aria-live=polite`
bilan progressive enhancementda yangilanadi, server response’da oddiy heading
bo‘lib qoladi.

Card tarkibi:

- universitet + shahar/tur;
- ayni filterga mos ko‘pi bilan 3 offering, qolgan soni;
- degree, language, duration, academic cycle;
- original tuition + ISO currency + fee period;
- admission effective status/deadline;
- `Tekshirildi`, `Ko‘rib chiqish kerak` yoki `Aniq fakt vaqtincha yashirilgan`;
- official source va detail;
- compare checkbox/link, lekin entire card nested interactive bo‘lmaydi.

Empty state qaysi constraint natijani yo‘q qilganini taxmin qilmaydi. Bir bosqich
bo‘shatish taklifi (masalan, price’ni olib tashlash) deterministic; random
universitet yoki AI hallucination bermaydi.

### 7.2 University detail

Headingdan keyin “fact bar”: cycle, verified state, official website/source va
“AzureLMS mustaqil yordam platformasi; yakuniy shartni rasmiy manbadan tekshiring.”

Bo‘limlar:

1. mos programlar;
2. boshqa current offeringlar;
3. qabul oynasi va scoped talablar;
4. kerakli hujjatlar;
5. tayyorlov/dormitory kabi faqat source-backed xizmatlar;
6. structured media;
7. source va verification tafsiloti;
8. yordam CTA.

Passed deadline ustidan “Qabul ochiq” yozilmaydi. Tuition “yiliga” deb faqat
`fee_period=academic_year` bo‘lsa chiqadi. Missing source’da `0`, `bepul` yoki
“aniqlanmoqda”ni narxdek ko‘rsatmaydi.

### 7.3 Compare

- min 2, max settingsdagi 4;
- URLda faqat stable offering UUIDlar; unknown yoki unpublished UUID foydali
  recovery bilan `404`; duplicate UUIDlar bitta variantga collapse qilinadi va
  accessible message ko‘rsatiladi;
- qatorlar: cycle, degree/languagedagi matched offering, tuition/period,
  deadline, required exams/docs, preparation va evidence age;
- “g‘olib” avtomatik tanlanmaydi; user mezoniga mos farqlar ko‘rsatiladi;
- no-JS GET form ishlaydi, print view semantik table/stackga aylanadi;
- noindex; analytics raw query va comparison contentini PII sifatida saqlamaydi.

Persistent shortlist bu roadmapning sharti emas. Avval shareable compare URL;
keyin account shortlist admit qilinsa retention/privacy alohida qaror.

### 7.4 Guide va announcement

- `/guides/` category/source freshness bo‘yicha browse; featured bo‘lmagan
  effective article ham topiladi;
- SIT-D3 `ADMIT` bo‘lsa `/announcements/` current/future-to-now semantics,
  category va university; aks holda home-only va archive CTA yo‘q;
- external link bo‘lsa detail avval source/contextni tushuntiradi, birdan
  noma’lum saytga redirect qilmaydi;
- rich body canonical sanitizer’dan, raw iframe yo‘q; video alohida structured
  block, approved host, sandbox/title/privacy URL, caption/transcript gate;
- meaningful image alt majburiy, decorative aniq bo‘sh alt;
- BLOG bilan content model merge emas, sanitizer/media policy reuse.

### 7.5 Owner studiyasi

Editor bir ekranda 7 formsetni ko‘tarib yurmaydi. Har qadam server-side draft
save qiladi; nav boshida completion/error count, pastda sticky bo‘lmagan action
bar. Browser-local draft source-of-truth emas.

Required UX:

- existing effective versiondan clone;
- birinchi save’dayoq faculty/program qo‘sha olish;
- row add/duplicate/archive, stable focus va inline error;
- currency/period/cycle bir qatorda;
- source picker va fact-scope coverage;
- “nashrga tayyor emas” sabablarini linkli checklist;
- effective↔draft field/child diff;
- two-tab stale conflictda ikkala qiymat, reload/copy yo‘li;
- preview, submit, publish, schedule, unpublish, rollback alohida action;
- destructive action typed confirmation emas, aniq target + consequence +
  reason va CSRF POST;
- audit tarixida actor/time/reason/before-after va operation receipt.

CSV import keyingi `SIT1.4c`: dry-run → row-level error report → explicit apply.
URL scraper emas. Batch size/resume/idempotency shart; mavjud rowni slug/name
taxmini bilan jim overwrite qilmaydi.

---

## 8. SIT AI advisor v2 contracti

### 8.1 Deterministik qism birinchi

`/sit/advisor/` starter formi degree, language, city, currency, max amount va
cycle’ni structured qilib beradi. Natural-language savol uchun bounded
deterministic extractor shu controlled vocabulary’ni topadi. Selector barcha
published itemni promptga dump qilmaydi:

```text
structured intent -> currency-aware effective offering query
                  -> exact shortlist + evidence/freshness metadata
                  -> optional LLM explanation
```

Provider ishlamasa ham shortlist va official links ishlaydi. Exact match
catalogdagi 26-universitet yoki 9-program bo‘lsa pagination limitidan oldin
filterlanib topiladi. “Top 25 keyin filter” taqiqlanadi.

### 8.2 Routing va conversation mode

- SIT CTA generic `/messenger/ai/`ga tashlamaydi; dedicated entry serverda
  `requested_skill_slug=sit_advisor` contextini o‘rnatadi;
- bu userning global saved AI skillini yashirincha almashtirmaydi;
- room/message’da visible `SIT maslahatchi` mode va catalog version ko‘rinadi;
- manual unrelated persisted skill SIT entrydan ustun kelmaydi;
- conversationdan chiqish va oddiy AIga qaytish aniq;
- AI inquiry yaratmaydi: faqat explicit server-rendered CTA taklif qiladi.

### 8.3 Prompt va source xavfsizligi

- provider haqiqiy `system_instruction`/system-role bilan product+safety
  qoidalarini user content va catalog data’dan ajratadi;
- bu contract barcha enabled provider adapterlari uchun bir xil; haqiqiy system
  role’ni bera olmaydigan dormant/fallback adapter SIT mode uchun eligible emas
  va flat prompt fallback taqiqlanadi;
- catalog/source text `<untrusted_catalog_data>` kabi data boundaryda;
- source ichidagi “oldingi ko‘rsatmani unut” instruction sifatida bajarilmaydi;
- exact proper noun/amount/date faqat returned row + source metadata bilan;
- stale/expired exact fakt promptga kirmaydi;
- viza/denklik/residence umumiy yo‘nalish + official source + human handoff;
- source citation response metadata orqali UIga chiqadi; `rag_sources` bilan
  aralashtirib “web qidirildi” deb da’vo qilmaydi;
- exact university/program nomi, summa, valyuta va sana LLM HTML/textidan emas,
  serverning deterministic shortlist kartasidan render qilinadi. Explanation
  structured program IDlarga bog‘lanadi; runtime claim validator allowlistdagi
  evidence’dan tashqari proper noun/amount/date topsa butun prose’ni rad etib
  deterministic fallback beradi. “Critical xato 0” faqat promptga yuklanmaydi;
- guide title emas, faqat sanitized relevant excerpt va scoped source; retrieval
  bo‘lmasa body promptga kirmaydi;
- SIT mode’da memory extraction default OFF, attachment/document input OFF va
  composerda “passport, ID yoki transkript yubormang” point-of-collection
  disclosure; keyingi enable faqat retention/delete contracti va user control
  bilan;
- free Gemini budget A8 hard gate; yangi provider yoki web-grounding yoqilmaydi.

### 8.4 A9 eval to‘plami

Kamida 50 teacher/owner-authored case:

- 10 exact degree/language/city match;
- 8 no-match va honest fallback;
- 6 stale/future/deadline contradiction;
- 6 mixed-currency/budget;
- 6 visa/denklik/legal boundary;
- 6 source/prompt-injection payload;
- 4 Uzbek apostrof/Turkish character va typo;
- 4 CTA/routing/context persistence.

Gate:

- routing fixtures 100%;
- stale exact fact exposure 0;
- katalogda yo‘q proper noun/amount/date 0;
- source-required exact claim citation coverage 100%;
- critical safety/official-guarantee xato 0;
- non-critical helpfulness owner rubricda kamida 90%;
- A9 latency, quota, cost va provider failure gate’i alohida yashil.

Shu evalsiz S3 statusi “foundation implemented/tested”, **release evidence
ready** emas.

---

## 9. Security, privacy, SEO, cache va accessibility

### 9.1 Rich content va media

- raw source hech qachon `|safe` bilan render qilinmaydi;
- save service `rendered_body + policy_version` yaratadi;
- old policy snapshot runtime’da current strict policy bilan safe projection
  beradi; failure plain-text fallback, GET write qilmaydi;
- script/event/style/arbitrary id, executable/data/protocol-relative URL va raw
  iframe taqiqlanadi;
- links http/https allowlist, `rel`/target server normalization;
- images magic-byte, MIME, size, dimensions; SVG v1’da rad etiladi, keyingi
  dedicated sanitizer alohida security admission talab qiladi;
- original immutable revisionda saqlanadi; repair dry-run/report + owner apply;
  jiddiy unsafe row avtomatik publish/unpublish qilinmaydi.

### 9.2 Privacy/abuse

- inquiry form accountdagi mavjud identitetdan foydalanadi; passport, grades,
  documents yoki free-form sensitive profile so‘ramaydi;
- privacy notice version va purpose form oldida;
- per-user DB idempotency + bounded rate limit; CAPTCHA default requirement
  emas, abuse evidence bo‘lsa alohida admit;
- owner export/download capability v1 scope’da yo‘q; keyin audit+retention bilan;
- logs goal/body/source contentni plaintext debugga chiqarib yubormaydi;
- user o‘z inquiry statusini ko‘radi, boshqa user UUIDsi 404;
- retention qarori chiqqach terminal inquiry PII anonymization commandi dry-run,
  batch/resume/audit bilan: goal/contact va requesterga bog‘liq erkin event note
  o‘chadi, user/assignee FK unlink bo‘ladi, faqat controlled state/timestamp va
  shaxssiz aggregate KPI qoladi. User account delete ham ayni service’dan o‘tadi;
  raw `SET_NULL`ning o‘zi privacy cleanup hisoblanmaydi.

### 9.3 Cache va indeks matrixi

| Holat | Cache | Robots/canonical | Yon ta’sir |
|---|---|---|---|
| Anonymous home/detail/guide/announcement | personalized data ajratilgach bounded public cache | index, self-canonical, sitemap | GET write-free |
| Clean university pagination | bounded public cache | har page self-canonical; crawlable links | duplicate `page` yo‘q |
| Arbitrary search/filter | short/private policy | `noindex,follow`; tracking params stripped | raw query minimallashtiriladi |
| Compare | short/private | `noindex,follow` | PII va persistent shortlist yo‘q |
| Auth published view | private | public canonical URL | user state GETda yozilmaydi |
| Draft/preview | private,no-store | noindex,nofollow + X-Robots | analytics/inquiry0 |
| Inquiry/advisor/backoffice | private,no-store | noindex,nofollow | auth/CSRF |

`frontend/public_v1.py`dagi global `private,no-store` birdan olib tashlanmaydi.
Helper explicit response policy qabul qiladigan qilib refactor qilinadi, Blog,
courses, legal va SIT flag ON/OFF regressionlari o‘tadi; keyin faqat side-effect
free anonymous SIT sahifalar public cachega o‘tadi.

SEO:

- absolute self-canonical, page-aware pagination, UTM cleanup;
- only effective URL sitemap, `lastmod` effective publicationdan;
- OG/Twitter title/description/image, no stale price in meta;
- Breadcrumb JSON-LD; universityda visible `CollegeOrUniversity`, programda
  visible/source-backed `EducationalOccupationalProgram`, guide’da Article;
- hidden field, rating/review, scholarship yoki offer claim markupga qo‘shilmaydi;
- Rich Results/Schema validator va rendered source snapshot dalili.

### 9.4 WCAG 2.2 AA va no-JS gate

- semantic landmarks, skip-link, visible current nav va mobile menu;
- keyboard-only filter/compare/inquiry/studio; focus visible va modal trap/return;
- visible labels, instructions, `autocomplete`, error summaryga focus,
  `aria-invalid/describedby`;
- status/error/loading programmatically announced, rang yagona signal emas;
- 320 CSS px/400% reflow, 200% text resize, WCAG text-spacing override;
- 24×24 normative minimum; primary button/filter control product target 44px;
- contrast: normal text 4.5:1, large 3:1, focus/non-text 3:1;
- meaningful cover/logo alt; decorative bo‘sh; media caption/transcript gate;
- compare semantik table bo‘lsa mobile alternate stacked view ham bir xil data;
- `prefers-reduced-motion`; essential action hover-only emas;
- no-JS: list/filter/pagination/detail/compare/inquiry POST/owner core action;
- native browser zoom va kamida NVDA/Windows screen reader owner acceptance
  avtomatik axe test o‘rnini bosmaydi.

### 9.5 Performance

- 12 va 100 result fixtureda query soni item soni bilan o‘smaydi;
- selector matched offeringsni prefetched/annotated projectionda qaytaradi;
- list HTMLda barcha program graph dump qilinmaydi;
- cover `width/height`, responsive `srcset/sizes`, lazy below fold;
- external Google Fonts/jsDelivr SIT legacy critical pathdan olinadi: system
  font stack va repo-local icon/assets ishlatiladi; CSP/availability parity;
- UI bosqichidan oldin home/list/detail 0/1/100/1000 fixture baseline: query,
  response size, server time. Release’da query regression +2dan ko‘p emas,
  N+1 0; performance budget sanali dalilga freeze qilinadi.

Staged/public release targeti bir xil documented profileda p75
**LCP ≤2.5s, INP ≤200ms, CLS ≤0.1**; bu target real-user evidence bo‘lmasa
synthetic deb aniq yoziladi:
[Core Web Vitals](https://web.dev/articles/vitals).

---

## 10. Roadmap — review qilinadigan aniq kesimlar

Har kesim alohida PR/commit chegarasi. “Model + full redesign + AI” bitta PRga
kirmaydi. Keyingi band oldingisining DoD’iga suyanadi.

### SIT1.0 — containment va yagona policy

#### SIT1.0a — birinchi kesim: claim, rich content va preview containment

**Ish:**

1. Public 5 000 UZS/payment claimini va enrollment-only tutor dead-endini olib
   tashlash; S2 ON bo‘lmaguncha halol unavailable/existing verified contact
   fallback. `application_help_fee` DBdan hali o‘chirilmaydi.
2. Current generic AI marketing CTA/sample promptni de-advertise qilish:
   A9-gated dedicated mode chiqmaguncha blok deterministic
   `/sit/universities/` katalog qidiruvi CTA’siga almashtiriladi; generic AI
   roomga yashirin fallback va ishlamaydigan “beta” tugmasi bo‘lmaydi.
3. Strict shared rich-content policy + malicious corpus; legacy/V1 safe parity.
4. Preview `sit.policy.can_preview` orqali; ordinary staff 404, owner 200;
   private/no-store/noindex parity.
5. Flag OFF eski raw `safe`ga qaytmasligini testlash.

**Tegiladigan joylar:** `sit/policy.py`, guide model/presentation bridge,
`templates/sit/knowledge_detail.html`, V1 detail, university CTA templates,
`core/rich_content_policy.py`; mavjud `frontend/templatetags/bleach_tags.py`
faqat shu core policy’ga compatibility wrapper bo‘ladi, views/tests.

**Test:** script/event/style/iframe/SVG/data URL/malformed HTML; ordinary
staff/owner/anonymous preview; legacy/V1; flag ON/OFF; fee/tutor/AI CTA text va
destination snapshot; AI provider call `0`.

**Tugashi:** executable markup0; draft leak0; blocked payment claim0; unsafe
generic SIT AI claim/entry0; current published guide semantic text saqlanadi.
Rollback renderer flagi raw bodyga qaytarmaydi.

#### SIT1.0b — filter, freshness va model invariantlari

**Ish:**

- expand-only minimal safety substrate: `SITSettings` singleton/revision va
  existing rowlarda zarur DB constraintlar; migration legacy read/writeni
  o‘zgartirmaydi; default row data migration bilan seed, SIT1.0c writerigacha
  UI/admin orqali mutable emas;
- same-offering `Exists` filter;
- currency-select + same-currency min/max; eski min/max valyutasiz kelsa price
  qo‘llanmaydi, `200 noindex`da visible “valyutani tanlang” xatosi va saqlangan
  input qaytadi — silent coercion yoki USD taxmini yo‘q;
- inactive faculty/program exclusion;
- future verified date, nonnegative amount, deadline/status consistency;
- hard-coded stale qiymatini settings policyga compatibility bridge;
- public va AI ayni `public_fact_projection`dan.

**Test:** cross-program false positive, four currencies, boundary amount,
inactive faculty, exact freshness threshold ±1 second/day, future verified,
passed deadline, `QuerySet.update`ga qarshi DB constraint mavjud bo‘lgan joylar.

**Tugashi:** bir offering barcha filterga javob beradi; conversion0; stale exact
price/deadline public/AIga chiqmaydi.

#### SIT1.0c — writer substrate, service, CAS, idempotency va audit

**Ish:** expand-only `state_revision`, custom permission va operation receipt
schema; `sit/editorial_service.py`, `select_for_update`, `SystemAuditEvent`;
current mutable model uchun compatibility service. Backoffice mutationlar
servicega; admin read-only/list_editable off.

**Test:** same-key same payload retry; same-key different payload conflict;
two-tab stale; audit failure rollback; no-op audit0; unauthorized; PostgreSQL
parallel writer.

**Tugashi:** UI/admin/direct supported path service’ni aylanmaydi; stale edit
jim overwrite qilmaydi; rollback eski viewga qaytsa ham writer invariant qoladi.

#### SIT1.0d — default mobile/no-JS containment

Legacy renderer mavjud ekan, `<=820px` navni yo‘qotmaydigan native menu,
skip-link, visible focus, labeled search, AA contrast va reduced-motion qo‘shiladi.
V1 componenti nusxalanmaydi; shared semantic contract saqlanadi.

**Test:** 320/360/390px, 400% zoom, 200% text, JS disabled, keyboard,
light/dark/forced-colors smoke; home → program search → detail → safe CTA.

**Tugashi:** default flag OFF holatida ham barcha asosiy SIT yo‘li reachable;
mobil accessibility katta redesign yoki B3.6ni kutmaydi.

### SIT1.1 — versionlangan katalog va source evidence

#### SIT1.1a — expand-only schema

SIT1.0b–c dagi minimal substrate ustiga source, stable child va version child
jadvallari avval yaratiladi; nullable pointer hamda slug redirect keyingi
expand migrationda qo‘shiladi. Circular FK bitta migrationda qurilmaydi.
Version graph index/constraintlari va cross-parent PostgreSQL deferred triggerlar
qo‘shiladi; legacy read/write o‘zgarmaydi. Migration kichik bo‘laklar; empty va
legacy DB test.

**Tugashi:** `makemigrations --check` clean; SQLite/PostgreSQL migrate;
mismatched pointer/program/faculty/cycle/source/inquiry snapshot PostgreSQLda
rad; column drop0; existing URL/data count o‘zgarmaydi.

#### SIT1.1b — resumable backfill va reconciliation

`backfill_sit_versions --dry-run --batch-size --resume-token`:

- har existing university va active child graphdan version1;
- published/draft mapping;
- current program ID → stable identity mapping;
- current source faqat isbotlay oladigan scope’ga; ambiguity quarantine;
- source/date yo‘q, future yoki contradictory row jim publish qilinmaydi;
- rerun idempotent; counts/hash va old/new projection diff.

Katta data `RunPython` transactioniga kiritilmaydi. Dry-run report owner review,
backup va explicit apply’dan oldin. Rollback pointer flagini legacyga qaytaradi;
yangi rowlar saqlanadi.

#### SIT1.1c — lifecycle va shadow-read cutover

Draft/review/approve/publish/schedule/cancel/unpublish/archive/rollback service,
due worker va time-aware GET selector. Avval shadow old/new diff, keyin
`sit_catalog_revision_reads` default-OFF flag ON pilot.

**Test:** transition table, immutable effective graph, exact schedule boundary,
worker/manual race, GET write0, slug redirect, old/new parity.

**Tugashi:** public va AI faqat effective pointer; draft live’ni o‘zgartirmaydi;
OFF legacy projection safe; eski fields shu release’da drop emas.

### SIT1.2 — source/freshness owner queue

#### SIT1.2a — readiness va queue

Profile/admission/program/tuition/requirements/preparation/document/service/
media/guide/announcement scope coverage, expiry, source reachability va
contradiction queues. Dashboard deep-link exact draft/fieldga. Reminder deduped;
GET write emas.

#### SIT1.2b — studio source workflow

Source snapshot form, official-host hint, verified-at, scope, note; effective
vs draft diff/readiness. Link checker “reachable”ni “verified”ga aylantirmaydi.
SSRF corpus: loopback/private/link-local/metadata/reserved IPv4+IPv6, encoded
host, userinfo, redirect-to-private, DNS rebind, non-approved port, timeout va
oversize body; guardlar yo‘q bo‘lsa checker OFF/manual-only.

**Tugashi:** owner bir qarashda qaysi public exact claim qachon expire bo‘lishini
ko‘radi; missing evidence bilan publish service rad etadi.

### SIT1.3 — canonical inquiry (launch contractidagi S2)

#### SIT1.3a — schema, service va privacy

`SITInquiry`, event/receipt, state transition, permissions, dedupe, rate limit,
SLA, notice acknowledgment/version, terminal reason, anonymize/unlink. Auth+CSRF;
payment va document upload yo‘q.

**Test:** owner/user/other/staff matrix, duplicate window boundary, parallel
create, retry/conflict, transitions/reopen, goal length/unsafe text, notification
failure, retention dry-run skeleton.

#### SIT1.3b — public CTA va status

University/program/effective version contextli confirm page; login return;
POST/Redirect/GET; refresh duplicate0; success/status/withdraw if allowed.
`sit_inquiry_intake` default OFF; OFF halol unavailable, generic tutor dead-end
emas.

#### SIT1.3c — owner queue va messenger adapter

Filter by state/SLA/university/assignee, transition/next-action, inquiry-linked
messenger handoff va transactional outbox. Messenger room unavailable bo‘lsa
inquiry saqlanadi va ownerda visible failure.

**Tugashi:** detail → inquiry → owner contacted → qualified → completed full
browser flow; canonical status DMdan mustaqil; KPI query documented.

### SIT1.4 — ultra qulay studio

#### SIT1.4a — progressive university editor

Qadamli draft, same-first-save children, row add/clone/archive, server draft,
error/focus, readiness va stale conflict UI.

#### SIT1.4b — preview/diff/history/rollback

Responsive preview, field/child diff, source coverage, schedule/history,
operation receipt va accessible confirmation.

#### SIT1.4c — import va bulk hygiene

Faqat real owner ehtiyoji tasdiqlansa: documented CSV schema, dry-run, row
errors, batch/resume/idempotent apply. Scrape/autopublish yo‘q.

**Tugashi:** owner docsiz bitta universitetni draftdan publishgacha yurgiza
oladi; ikki tab va invalid source data yo‘qotmaydi; Q17b faqat visual reference.

### SIT1.5 — public discovery va decision workspace

#### SIT1.5a — search/result cards

Primary `/sit/programs/`, institution `/sit/universities/`, program/faculty
search va alias normalization, exact matched offerings, typed query errors,
filter chips, empty states, correct pagination/querystring, no-JS. Existing
URLs saqlanadi. V1 global headerga owner-configurable/default SIT entry kiradi;
flag ON portalni footerdagina qoldirmaydi.

#### SIT1.5b — detail va compare

Fact bar, cycle/scoped sources, status derivation, 2–4 compare, share/print,
missing-data semantics. Persistent shortlist yo‘q.

#### SIT1.5c — guide va announcement archives

Guide index/detail/category, schedule, source/freshness va discoverability
majburiy. Announcement archive/detail **SIT-D3 owner qarori bu kesimdan oldin
explicit `ADMIT` bo‘lsagina** quriladi. Qaror bo‘lmasa announcement home-only
qoladi va “Barcha e’lonlar” va’dasi yashiriladi; agent default tavsiyani qaror
deb qabul qilmaydi.

**Tugashi:** 320–1440, no-JS, keyboard, 0/1/100/1000 fixture; exact match
card/detail/compare bir projection; orphan effective content0.

### SIT1.6 — AI advisor v2

#### SIT1.6a — dedicated entry va deterministic retrieval

Forced SIT mode, structured starter form/extractor, all-catalog filter-before-
limit, currency/freshness policy, provider-independent shortlist.

#### SIT1.6b — system/data boundary va citations

True system instruction, untrusted catalog delimiter, source metadata, UI
citation, provider failure fallback. Global provider change AI regressionlari
bilan alohida review qilinadi.

#### SIT1.6c — A9 eval va rollout

50-case corpus, latency/quota/cost, prompt injection, stale/no-match, routing.
`sit_ai_explanation` default OFF; owner pilot; old generic CTAga silent rollback
emas — deterministic shortlist qoladi, explanation unavailable bo‘ladi.

### SIT1.7 — SEO, cache, media va accessibility

#### SIT1.7a — metadata/sitemap/cache policy

Explicit `render_public` policy, canonical/robots/OG/Breadcrumb/JSON-LD,
page-aware sitemap, anonymous cache. Global public surfaces regression.

#### SIT1.7b — responsive media/performance

Image validation/projection, width/height/srcset, local critical assets,
query/response budgets, orphan cleanup command dry-run.

#### SIT1.7c — WCAG/no-JS/native acceptance

Automated axe/HTML checks + keyboard, 320px/400%, 200%, text spacing,
reduced motion, NVDA, light/dark, slow network, no-JS. B3.6 token porti bilan
koordinatsiya; behavior/data contract SITniki qoladi.

`html lang`, Django `LANGUAGE_CODE`, Uzbek UI va Turkish proper-name fragmentlari
audit qilinadi. Turkish fragment zarur joyda `lang="tr"`; keyingi to‘liq
multilingual content/hreflang alohida admission, hard-coded yarim tarjima emas.

### SIT1.8 — production migration va release paketi

#### SIT1.8a — data rehearsal

Production-like backup nusxada dry-run/apply/rerun, count/hash/quarantine,
SQLite/PostgreSQL, old/new shadow diff, restore drill. Real production write
ownerning alohida deploy qarori bilan.

#### SIT1.8b — staged flags

1. invariant/security fixlar unflagged;
2. version writes + shadow reads;
3. owner studio pilot;
4. revision public reads;
5. inquiry intake small pilot;
6. decision tools;
7. AI explanation;
8. cache/SEO rollout.

Har qadam health/metrics/rollback readback bilan. OFF data/historyni
o‘chirmaydi. Eski schema cleanup kamida bitta stable release va owner sign-offdan
keyin alohida `SIT2.0 cleanup` admissioni; SIT1.8ga kirmaydi.

#### SIT1.8c — final evidence

DoD matrix, migration/rollback log, browser/device/a11y evidence, source
coverage, inquiry SLA drill, AI eval, privacy/retention qarori, runbook va owner
acceptance status. “Code merged”, “flag ON”, “production deployed” va “owner
qabul qildi” alohida yoziladi.

---

## 11. Feature flag va rollback

| Flag | Default | ON | OFF/rollback |
|---|---:|---|---|
| `sit_catalog_version_writes` | OFF | owner draft/review/publish canonical version service’da | yangi editlar read-only; legacy direct writer qayta ochilmaydi, mavjud version/projection saqlanadi |
| `sit_catalog_revision_reads` | OFF | public/AI effective version projection | safe legacy projection; strict policy/freshness/filter invariant qoladi |
| `sit_inquiry_intake` | OFF | canonical create/status/queue | read-only existing inquiries saqlanadi; CTA unavailable, tutor dead-end emas |
| `sit_public_decision_tools` | OFF | matched cards/compare/archive UX | existing safe list/detail; schema/history qoladi |
| `sit_ai_explanation` | OFF | source-bound LLM explanation deterministic shortlist ustida | public decision-tools form/resulti deterministik qoladi; provider call 0 |

`frontend_v1_public` mavjud presentation flagi bo‘lib qoladi; SIT data,
permission, sanitizer va freshness xavfsizligini boshqarmaydi. Security fix,
DB constraint, ownership va stale exact-fact omission flag ortiga yashirilmaydi.

Flaglar `core/flags.py` registry’da, default OFF va runbook bilan. Owner-live
boolean `SITSettings`ga qo‘yilmaydi. Rollback migration down yoki row delete
emas; read/entry adapter switch. Har flag kombinatsiyasi kamida legacy/V1,
anonymous/auth/owner va existing-data readbackda testlanadi.

Version writer ON bo‘lgach canonical source version graphdir; service legacy
rollback projectionini transactionda materialize qiladi. Writer flag OFF
owner editini vaqtincha read-only qiladi — eski mutable direct writerga qaytib
ikki haqiqat yaratmaydi. Read rollback projectionning hash/parity dalilisiz ON
qilinmaydi.

Writer cutover `SITCatalogCutover(completed_at, actor, operation_receipt)` nomli
bir marta yaratiladigan, delete/update qilinmaydigan audited row bilan qayd
etiladi: cutovergacha OFF compatibility service writerini, cutoverdan keyin esa
read-only holatni anglatadi. Oddiy flag toggle bu receiptni bekor qilmaydi va
eski direct writerni qayta ochmaydi.

---

## 12. Test va qabul matrixi

### 12.1 Majburiy avtomatik contractlar

- model/DB: money, date, status, unique mutable draft, pointer, PROTECT;
- permissions: anonymous/user/other/staff/editor/publisher/owner;
- preview/cache/index side-effect0;
- sanitizer corpus va legacy/V1 parity;
- same-offering + currency + inactive/freshness filters;
- lifecycle transition table, CAS, idempotency, audit failure rollback;
- schedule boundary/worker race/GET write0;
- backfill dry-run/resume/rerun/quarantine/count/hash;
- inquiry duplicate/rate/transition/privacy/outbox failure;
- AI #26/#9 exact match, stale omission, no-match, injection, citation;
- flag ON/OFF va rollback data readback;
- pagination canonical/querystring; JSON-LD visible-data equality;
- query count 12/100 results va media fallback.

### 12.2 Browser ssenariylari

1. Anonymous English master + USD range qidiradi; faqat ayni offering match.
2. TRY row USD filterga kirmaydi; original currency ko‘rinadi.
3. Stale tuition yashiriladi, university sahifasi va source warning qoladi.
4. 26-o‘rindagi exact program public va deterministic advisor’da topiladi.
5. 320px/no-JS filter → page2 → detail → Back filter holatini saqlaydi.
6. 2–4 compare; duplicate/unknown/max-limit accessible xabar.
7. Anonymous CTA login → ayni university/program confirmga qaytadi.
8. Double click/refresh bitta inquiry; notification fail bo‘lsa owner queue bor.
9. Other user inquiry UUIDsi 404; owner statusni CAS bilan o‘zgartiradi.
10. Ordinary staff draft preview 404; owner preview no-store/noindex va CTA0.
11. Published item edit/save draft live sahifani o‘zgartirmaydi.
12. Two-tab edit stale formni bosmaydi, diff/recovery beradi.
13. Scheduled publish exact boundaryda bir marta; retry receipt qaytaradi.
14. Rollback eski versionni yangi audited operation bilan effective qiladi.
15. Unsafe legacy guide ikkala rendererda executable node0, text safe fallback.
16. Advisor generic persisted skillga qaramay SIT mode’da; source va disclaimer.
17. Provider/quota fail: deterministic shortlist + official link saqlanadi.
18. Keyboard-only filter/compare/inquiry/studio; error summary va focus.
19. 400%/320px, 200% text, text spacing, dark/light, reduced motion.
20. Migration rehearsal va flag OFFda old data/slug/inquiry readback.

### 12.3 Test buyruqlari

Har agent avval safe env:

```powershell
$env:AZURELMS_SKIP_ENV_FILE='1'
$env:APP_ENV='local'
$env:LOCAL_USE_REMOTE_SERVICES='False'
$env:GEMINI_API_KEY=''
$env:TELEGRAM_BOT_TOKEN=''

venv\Scripts\python.exe manage.py check
venv\Scripts\python.exe manage.py makemigrations --check
venv\Scripts\python.exe manage.py test sit frontend.test_public_v1 --noinput
```

Kesimga qarab AI/messenger/core flag testlari va PostgreSQL CI qo‘shiladi.
Final stage full Django + repository Node suite + `git diff --check`. Real
Gemini key, Telegram token yoki production URL test uchun ishlatilmaydi.

---

## 13. Keyingi agent uchun bajarish protokoli

1. `AGENTS.md`, `rules-for-agents.md`, marinebook top 3–5 va joriy README’ni
   qayta o‘qi; `git status/log/branch`ni tekshir.
2. Shu roadmapdagi eng yuqoridagi unfinished **bitta** kesimni tanla. Bir PRda
   keyingi bosqichni “qulay bo‘lsin” deb qo‘shma.
3. Kesim boshida current behaviorni failing regression test bilan isbotla.
   Security payloadni log/finalga executable ko‘rinishda tarqatma.
4. Schema bo‘lsa expand-only; production data taxmin qilma. Dry-run/backfill
   command migrationdan alohida.
5. Barcha mutation service orqali; view/form/admin duplicate business logic
   yozma. GET write-free.
6. Existing uncommitted/begona ishni o‘zgartirma. B3.6 yoki BLOG sanitizer
   dependency’si bilan overlap bo‘lsa egasini aniqlab, bitta shared primitive.
7. Safe env’da focused test, relevant cross-app test, `check`, migration check,
   `git diff --check`. Concurrency uchun PostgreSQL testni CIga qo‘y.
8. Commitdan oldin ushbu hujjatda faqat haqiqatan tugagan slice holatini,
   test/evidence linkini yangila; reja matnini “done” deb umumiy almashtirma.
9. Test → commit → marinebook → push → PR → required CI. Repo qoidalaridagi own
   prefix/merge/branch cleanup tartibini aynan bajar.
10. Production flag/data/deploy, retention huquqiy qarori, payment, new PII,
    scraping yoki external notification kanali yangi authority talab qiladi;
    taxmin bilan yoqma.

### Tavsiya etilgan PR navbati

```text
SIT1.0a
 -> SIT1.0b
 -> SIT1.0c
 -> SIT1.0d
 -> SIT1.1a
 -> SIT1.1b
 -> SIT1.1c
 -> SIT1.2a
 -> SIT1.2b
 -> SIT1.3a
 -> SIT1.3b
 -> SIT1.3c
 -> SIT1.4a
 -> SIT1.4b
 -> (SIT1.4c faqat real import ehtiyoji bo‘lsa)
 -> SIT1.5a
 -> SIT1.5b
 -> SIT1.5c
 -> SIT1.6a
 -> SIT1.6b
 -> SIT1.6c
 -> SIT1.7a
 -> SIT1.7b
 -> SIT1.7c
 -> SIT1.8a
 -> SIT1.8b
 -> SIT1.8c
```

SIT core launch lane’ga parallel, lekin har sessiyada bir canonical slice.
`SIT1.0a` xavfsizlik containmenti maintenance sifatida alohida ustuvor;
qolgan navbat ownerning active task qarorini o‘zi o‘zgartirmaydi.

---

## 14. Ochiq owner qarorlari

| ID | Qaror | Rejadagi xavfsiz default |
|---|---|---|
| SIT-D1 | Guide Journalga merge qilinadimi? | Hozircha SIT stable item/revision; shared sanitizer/media policy. Raw model merge yo‘q. |
| SIT-D2 | 5 000 UZS seriousness fee? | UI/AI/inquirydan olib tashlanadi; automated payment alohida admit bo‘lmaguncha OFF. |
| SIT-D3 | Announcement archive/detail? | Ochiq owner gate. SIT1.5c’dan oldin explicit `ADMIT` bo‘lmasa qurilmaydi; home-only va archive CTA yo‘q. |
| SIT-D4 | Inquiry retention muddati va preferred contact kanallari? | Minimal account data; purge yoqilmaydi, export/upload yo‘q; owner/legal aniq muddat beradi. |
| SIT-D5 | SIT editor/publisher ownerdan boshqa kim? | Custom permission schema, lekin initial assignment faqat owner; `is_staff` fallback yo‘q. |
| SIT-D6 | Production pilot qaysi universitet/cycle bilan? | Source coverage 100% bo‘lgan kichik owner-approved cohort; barcha legacy rowni birdan publish emas. |

Bu qarorlar `SIT1.0a–d` containment va correctness ishlarini to‘xtatmaydi.
SIT-D3 announcement qismini, SIT-D4 `SIT1.3` production rolloutini, SIT-D5
writer switchni, SIT-D6 public cutoverni bloklaydi.

---

## 15. SIT-01 Definition of Done

SIT-01 faqat quyidagilar dalil bilan yopilganda tugagan hisoblanadi:

- public, AI va owner ayni effective version/freshness policy’dan o‘qiydi;
- draft/live/schedule/rollback immutable va audited;
- exact program filter bitta offeringga, narx ayni valyutaga bog‘langan;
- stale/manbasiz exact claim public, AI, meta va JSON-LDga chiqmaydi;
- raw rich content hech bir flag/render path’da executable bo‘lmaydi;
- ordinary staff preview qilmaydi; owner preview private/noindex/side-effect0;
- qualified inquiry canonical, idempotent, privacy-bounded va owner SLA queue’li;
- payment claim admissiongacha yo‘q;
- compare/search/detail/guide core flow, va SIT-D3 admitted bo‘lsa announcement
  flow, JSsiz va WCAG 2.2 AA;
- AI deterministic shortlist ustida, source citationli, A8/A9 gate’i yashil;
- old data/slugs preserved, migration resumable, rollback sinalgan, column drop0;
- SQLite va PostgreSQL testlari, full regression, Node/browser/native evidence;
- runbook, flags, metrics, retention decision va owner acceptance statusi yozilgan;
- code merged, flag ON, production deploy va owner qabul holatlari alohida
  qayd etilgan.

Ungacha hujjat holati **REJA / qisman implementatsiya**, “SIT islohoti tugadi”
emas.
