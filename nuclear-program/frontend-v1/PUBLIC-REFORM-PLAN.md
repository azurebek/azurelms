# PUBLIC-01 — anonim tashrifni ishonchli va ultra qulay yo‘lga aylantirish

**Holat:** REJA TAYYOR; **PUB1.0 bosqichi (a–g) va PUB1.1a–b kodda (2026-10-16/17, lokal)**,
PUB1.1c va keyingi kesimlar boshlanmagan
**Tadqiqot sanasi:** 2026-10-15
**Kod tayanchi:** `main`dagi `72e82e0`
**Birinchi implementatsiya kesimi:** `PUB1.0a`
**Asosiy mahsulot KPI:** anonim kurs sahifasidan boshlangan niyatning ayni
kurs bo‘yicha canonical checkout quote’iga yetishi. Trafik, click yoki account
soni o‘z-o‘zicha muvaffaqiyat emas.

Bu reja auth qilinmagan foydalanuvchi ko‘ra oladigan butun AzureLMS sirtini
qamraydi: landing, About, kurs katalogi va detaili, pricing, login/register/
reset/Telegram auth, legal/FAQ, public Blog va SIT adapterlari, sertifikat
verifieri, 403/404/500, maintenance va offline holatlari. U amaldagi Django
view/template/model/testlari, launch va frontend contractlari hamda rasmiy
xavfsizlik, accessibility, SEO, performance va maxfiylik manbalari asosida
yozilgan.

Bu dizayn g‘oyalari ro‘yxati emas. Har bosqichda canonical manba, tegiladigan
fayl, test, dependency, rollback va tugash mezoni berilgan. Keyingi agent eng
yuqoridagi tugallanmagan **bitta** kesimdan boshlaydi; “public redesign” nomi
bilan katta aralash PR ochmaydi.

Reja yozilishi runtime, local DB, AWS yoki productionni o‘zgartirmaydi.
`I5A-PUBLIC.md`dagi 14-route V1 porti bajarilgan tarixiy poydevor; PUBLIC-01 uni
“qilinmagan” demaydi. Aksincha, o‘sha renderer ustidagi xavfsizlik, truthful
content, acquisition continuity, SEO/cache va real qabul qarzlarini ajratadi.
Blog domain islohoti [BLOG-01](BLOG-REFORM-PLAN.md)da qoladi: Blog uchun faqat
umumiy public shell, xavfsizlik, maxfiylik, metadata va CTA adapterlari shu scope’da.

---

## 1. Mahsulot qarori

### 1.1 Yakunda nima quriladi?

Public qatlam besh vazifani bitta izchil yo‘lda bajaradi:

1. **Tushunarli kirish eshigi.** Mehmon birinchi ekranda AzureLMS kim uchun,
   nima o‘rgatishi, qanday formatda va keyingi real qadam nima ekanini biladi.
   Isbotsiz award, student soni, reyting, muddat yoki “natija kafolati” yo‘q.
2. **Qaror uchun yetarli offer.** Katalog va kurs detaili canonical `Course`,
   active `Cohort`, sotib olinadigan `Plan` va checkout policy’dan read-only
   projection oladi. Kim uchun, prerequisite, curriculum, workload, jadval,
   mavjudlik, nimalar kirishi va narx faqat manbada bo‘lsa ko‘rsatiladi.
3. **Uzilmaydigan acquisition.** Course → login/register → onboarding → ayni
   checkout yo‘li course/plan niyatini yo‘qotmaydi. Klient yuborgan ID, narx yoki
   availability haqiqat hisoblanmaydi; checkout hammasini qayta resolve qiladi.
4. **Ishonch va nazorat.** Legal matn, cookie/tracking, testimonial, marketing
   claim, sertifikat va auth oqimi kimga nima oshkor qilayotgani aniq. Public
   `GET` incidental canonical/domain yozuv yaratmaydi; Django CSRF/reset kabi
   framework security bookkeeping faqat explicit allowlist va disclosure testi
   bilan qoladi. Sensitive route cache va indexga tushmaydi.
5. **Tez va accessible web.** Server-rendered core flow JSsiz ishlaydi; keyboard,
   screen reader, zoom/reflow, reduced motion va responsive media birinchi
   kundan release gate. Indexable sahifalar deterministic metadata va cache
   policy oladi, auth/preview/token yo‘llari esa qat’iy private qoladi.

### 1.2 Admission va navbat

PUBLIC-01 ikki turdagi ishni ajratadi:

- Butun PUB1.0 fazasi — `PUB1.0a–g`: stored-XSS (a), registration bypass (b),
  auth abuse throttle (c), Telegram state-changing `GET` (d), public GET/legal
  read-write (e), password reset delivery (f) va yashirin Blog tracking (g)
  containmenti — **launch-critical maintenance**. Bular renderer flagi yoki
  redesign navbatini kutmaydi.
- Qolgan acquisition/UX/SEO/performance ishlari — **PLANNED**. Ular ownerning
  active task navbatiga avtomatik kirmaydi va mavjud B3/Classbook/Messenger/SIT
  yo‘nalishlarini o‘z-o‘zidan siqib chiqarmaydi.

Public acquisition launch backlogdagi A4 payment/entitlement contractining
kirish adapteri. U checkout, enrollment, plan yoki entitlement business
qoidalarini qayta yozmaydi. PUBLIC-01 tugasa ham production offer va legal
matn owner tomonidan tasdiqlanmasdan sotuv yoqilmaydi.

### 1.3 Qamrovga kirmaydigan ishlar

- yangi SPA/frontend framework yoki public uchun alohida API-first platforma;
- pricing, refund, subscription, cohort capacity yoki entitlement siyosatini
  agentning o‘zi belgilashi;
- Blog domain redesigni, comment/community/studio versioningi — ular
  [BLOG-01](BLOG-REFORM-PLAN.md)da alohida;
- SIT katalog, source/version, inquiry yoki AI logicini parallel qurish;
- “AI marketing writer”, avtomatik claim, fake testimonial yoki synthetic
  production content;
- A/B test, personalization yoki aggressive popup — baseline va yetarli trafik
  bo‘lmasdan;
- CAPTCHA’ni yagona auth yo‘li qilish yoki password manager/copy-paste’ni
  bloklash;
- native mobil ilova, yangi to‘lov provider, yangi email provider yoki CRM;
- service worker bo‘lmasdan “offline ishlaydi” claimi;
- huquqshunos tasdig‘isiz “KVKK compliant”, “14 kun kafolatli refund” yoki
  bolalar consent yoshi haqida qat’iy matn;
- global CSP’ni birdan almashtirish: public/error/auth inline dependency’lari
  kichik kesimlarda olib tashlanadi, system-wide cutover alohida evidence bilan.

### 1.4 Natija va guardraillar

| O‘lchov | Aniq hisob | Release talabi |
|---|---|---|
| Qualified purchase conversion | Course detaildan boshlangan unique guest journey ichida canonical checkout quote/start’ga yetganlar / eligible course-detail journeys | Avval 2–4 haftalik baseline; owner keyin relative target beradi |
| Intent continuity | Authdan keyin aynan oldingi course/plan destinationga yetganlar / intentli successful auth | 100%; boshqa dashboardga tasodifiy tushish 0 |
| Claim integrity | Public ko‘rsatilgan statistika, testimonial, price, deadline va service claimlar ichida current evidence bor ulush | 100%; dalilsiz claim yashirin |
| Legal integrity | Public response current effective owner/legal-approved revisionni ko‘rsatadi | 100%; generic fallback “tasdiqlangan policy” deb ko‘rsatilmaydi |
| Dead-end rate | Real forward yoki configured support amali yo‘q valid public holatlar / barcha public holatlar | 0 |
| Accessibility | Core journey keyboard-only completion; automated critical/serious issue; horizontal overflow | 100%; 0; 0 |
| Performance | Real-user p75 LCP / INP / CLS, mobile va desktop alohida | `≤2.5s` / `≤200ms` / `≤0.1` |
| Privacy | Telemetryda email, ism, form matni, search body, token, cookie/session secret | 0 |
| Reliability | Public 5xx, typed auth/checkout failure, uncertain-state recovery | Baseline va alert; fake success 0 |
| GET purity | Analytics yoki framework security bookkeeping allowlistiga kirmagan public `GET`dagi canonical/domain mutation | 0 |

Conversion foizi auditdan oldin to‘qilmaydi. Security, privacy, claim va
accessibility invariantlari esa baseline kutmaydi: ular birinchi release’da
0/100% talablardir.

---

## 2. Tadqiqot va amaldagi kod auditi

### 2.1 Tekshirilgan ichki yuzalar

Audit quyidagilarni source darajasida ko‘rdi:

- router va error handlerlar: `core/urls.py`, app `urls.py`lari;
- public adapter: `frontend/public_v1.py`, `frontend/views.py`, context
  processor, public/legacy templates va frontend assetlar;
- landing/About/nav/statistic/testimonial/auth/legal modellari va admin/
  backoffice writerlari;
- course list/detail, pricing, checkout entry, certificate detail/appendix;
- login/register/onboarding/password reset/Telegram auth va bot account claim;
- Blog visitor cookie/IP-hash/read yozuvi, public interaction va preview;
- SIT public adapteri va SIT-01 bilan boundary;
- CSP, security middleware, health/readiness, maintenance/offline/error shell;
- `frontend/test_public_v1.py`, auth/Telegram/certificate/checkout testlari;
- `I5A-PUBLIC.md`, `FINAL-ACCEPTANCE-ISSUES.md`, B3, SIT-01, MESSENGER-01,
  pricing va launch contractlari.

Ushbu audit production data, real Search Console, real RUM, native device yoki
legal sign-off bajarganini anglatmaydi. Ular roadmapning release evidence
bosqichida alohida olinadi.

### 2.2 Public sirt inventari

| Oila | Joriy route | Joriy haqiqat | Target policy |
|---|---|---|---|
| Landing | `/` | Guest render; authenticated user dashboardga redirect; V1/legacy flag | Indexable canonical; guest projection; auth redirect private |
| About | `/about/` | Team/stat/testimonial publication flaglari to‘liq emas | Indexable, published-only, claim-gated |
| Legal | `/privacy-policy/`, `/terms-of-service/`, `/faq/` | Missing row `GET`da yaratiladi; generic/versionless content | Effective revision; write-free GET; canonical |
| Course list | `/courses/` | `q`, level, sort, pagination; unbounded rich-HTML search | Clean base canonical; bounded filters; query policy |
| Course detail | `/courses/<pk>/` | Outline/instructor/CTA; offer va direct-register intent yo‘q | Indexable offer projection; exact intent |
| Pricing | `/pricing/` | Global plan cards; CTA generic register/catalog | Truthful comparison; default course-first flow |
| Blog list/detail | `/blog/`, `/blog/<slug>/` | Published content; detail GET tracking cookie/IP hash yozadi | Shared shell/SEO/privacy only; domain redesign yo‘q |
| SIT | `/sit/...` | Public catalog/guide; generic AI/help handoff | SIT-01 owns domain; shared public policy adapter |
| Login | `/users/login/` | Email/username, password, Telegram entry | Sensitive/noindex/no-store; accessible errors; throttle |
| Register | `/users/register/` | Immediate account/login; flag only web pathni yopadi | Shared registration policy; legal notice; intent |
| Onboarding | `/users/register/onboarding/...` | Authdan keyin optional AI path | Noindex/private; exact intended destination |
| Reset | `/users/password-reset/...` | Anti-enumeration baseline; delivery consolega tushishi mumkin | Uzbek delivery; release capability gate; throttle |
| Telegram auth | `/users/telegram-auth/init/`, `status/...` | `GET` row yaratadi, token consume va login qiladi | POST init/consume; read-only status; cleanup/throttle |
| Certificate | `/courses/certificate/<id>/`, `appendix/` | Exact ID bilan full name/score va attempt detail public | Owner-decided minimal verifier; opaque token; noindex |
| Error/status | 403/404/500, `/maintenance/`, `/offline/` | Remote assets; 500 unsupported alert claim; cache/index policy yo‘q | Self-contained, truthful, noindex, method-safe retry |
| Ops probes | `/healthz`, `/readyz` | Anonymous env/release/check summary | Human UI emas; external response minimal |
| Theme CSS | `/design/theme.css` | Public consumer, doim `no-store` | Revision-keyed immutable cache |
| CKEditor upload | `/ckeditor5/image_upload/` | URL mounted, package default staff POST gate | Public UI emas; staff/upload policy auditi alohida |
| Protected entry | checkout/library/messenger/classbook/lesson/exam | Login redirect orqali public journeyga ta’sir qiladi | Safe return + exact intent; protected state public emas |

`healthz`, `readyz` va upload endpointini sitemap yoki public navigationga
qo‘shish mumkin emas. “Browserdan authsiz ochiladi” va “public product page”
bir xil tushuncha emas.

### 2.3 Saqlanadigan yaxshi poydevor

- V1 base `lang="uz"`, viewport, skip link va semantic `main`ga ega.
- Mobile header native `<details>` bilan JSsiz ochiladi; Escape/outside/breakpoint
  cleanup mavjud.
- Course/login/register/onboarding safe `next` helper tashqi redirectni rad
  etadi; mavjud login orqali exact course return testi bor.
- Password reset known/unknown/inactive/unusable account uchun bir xil receipt
  oqimini testlaydi; reset token bir martalik.
- Telegram token 32-byte URL-safe, browser `client_key`iga bog‘langan, TTLli,
  constant-time match va row-lock bilan bir martalik consume qilinadi.
- Blog va SIT preview published querysetdan ajratilgan; V1 preview `noindex`
  va private/no-store baseline’iga ega.
- Course/plan/checkout canonical modellari va server-side revalidation mavjud;
  public layer ularni qayta ixtiro qilmaydi.
- V1 public testlari 14 route, flag ON/OFF, filter/pagination return, unsafe nav
  URL, preview, CSRF, pricing catalog va empty statesni qamraydi.

Radikal islohot shu poydevorni buzmaydi. Ayniqsa safe `next`, canonical
checkout, CSRF, reset anti-enumeration va Telegram one-time invariantlari
regression test bilan saqlanadi.

### 2.4 P0 — keyingi public feature’dan oldin containment

1. **Default legacy renderer stored XSS yo‘lini ochadi.**
   `frontend_v1_public` default OFF. `templates/index.html`, `about.html`,
   `legal_page.html`, `blog/post_detail.html`, `courses/course_detail.html` va
   `sit/knowledge_detail.html` DB HTMLni raw `|safe` qiladi. V1 `sanitize`
   ishlatadi, lekin umumiy sanitizer `iframe`, global `style/class/id` va keng
   CSSni ruxsatlaydi. CSP esa `unsafe-inline`ni qabul qiladi. Xavfsizlik
   rendererga bog‘langan va flag rollback raw kontentga qaytarishi mumkin.
2. **Registration flag barcha account-creation yo‘lini yopmaydi.** Web register
   `public_registration`ni tekshiradi; `bot/services.py`dagi deep-link Telegram
   auth hamda `register_guest_via_phone` noma’lum identity uchun account yarata
   oladi. Mini App auth esa hozir faqat existing userni topadi, lekin shared
   parity contracti yo‘q. Flag OFF amalda “yangi account yo‘q” degani emas.
3. **Auth abuse qatlami yo‘q.** Login/register/reset va Telegram init/status
   uchun per-feature throttle yo‘q. Telegram init har bir `GET`da DB row va
   session yozadi; status `GET` tokenni consume qilib login qiladi.
4. **Non-local reset console backendga jim tushishi mumkin.** `EMAIL_HOST`
   bo‘lmasa production-like muhit console backend tanlaydi. UI “yuborildi”
   deydi, secret reset URL logga chiqishi va user email olmasligi mumkin;
   readiness email capability’ni critical deb hisoblamaydi.
5. **Privacy/legal tracking haqiqatini qoplamaydi.** Blog detail anonymous
   visitorda bir yillik cookie o‘rnatadi, IP hash/User-Agent saqlaydi; retention,
   purge, opt-out/consent va aniq notice yo‘q. Legal GET esa juda yupqa generic
   matn bilan row yaratadi.

### 2.5 P1 — launch-critical correctness va trust qarzi

1. Public certificate ID `course.id`, `student.id` va 6 hex suffixdan tuzilgan;
   appendix barcha reviewed attempt/section ballarini authsiz ko‘rsatadi. Revoke,
   consent, publish scope va opaque verifier token yo‘q.
2. Course direct-register linki `next`ni yo‘qotadi; pricing CTA course/plan
   niyatini tashimaydi. User authdan keyin generic dashboard/catalogga tushadi.
3. Course detail canonical active cohort, start/schedule, availability, mos
   plan, final price, prerequisite/outcome/workloadni qaror formida bermaydi.
4. Landing va About barcha active testimonialsni memoryga olib random uchta
   tanlaydi; HTML/cache/test deterministic emas. `recent_students` query qilinib
   V1da ishlatilmaydi.
5. Landing defaultlari “2026 yilning eng yaxshi platformasi”, `2400+`, `94%`,
   `4.9`, “10 hafta”, “Doimiy support” va AI xotira kabi dalilsiz claimlarni
   real ko‘rinishda chiqarishi mumkin. Statistic/Testimonial’da provenance,
   consent, verified/expiry yo‘q.
6. `LegalPage` version, effective date, approver, publish/rollback yoki user
   acceptance receiptga ega emas. Registerda just-in-time notice ham yo‘q.
7. Auth/settings/nav/public kontentining katta qismi faqat Django admin writeriga
   ega; B3.5 esa faqat landingning bir qismini qamraydi. Direct writers bitta
   publication/readiness policy’dan o‘tmaydi.
8. SEO substrate yo‘q: sitemap/robots endpointi, global canonical/description,
   OG/Twitter contracti va published-only registry mavjud emas. Filter/search
   kombinatsiyalari index explosion hosil qilishi mumkin.
9. V1dagi barcha public response `private, no-store`; legacy’da esa yagona
   policy yo‘q. Cache xavfsizlik emas, renderer flag xulqi bo‘lib qolgan.
10. Course/Blog `q` qiymati uzunliksiz `icontains`, jumladan rich HTML body’da
    ishlaydi. Query budget, normalized input va clean canonical policy yo‘q.
11. Error shell tashqi Google Fonts/jsDelivrga tayangan. 500 sahifa real error
    reporting receiptisiz “Jamoamiz xabardor qilindi” deydi.
12. `/healthz` va `/readyz` anonymous clientga environment, release va
    capability summaryni beradi; external probe uchun buncha detail zarur emas.

### 2.6 P2 — qulaylik va polish qarzi

- Public base har routega `auth.css` va `learning.css`ni ham yuklaydi.
- Hero/blog/SIT media’da consistent intrinsic size, `srcset/sizes`, poster,
  caption va alt policy yo‘q; LCP/CLS boshqarilmaydi.
- Repeated card linklari “Kursni ko‘rish”, “Maqolani o‘qish” kabi bir xil
  accessible name oladi; paginationda direct page va `aria-current` yo‘q.
- Footer platform/company/legalni bitta tekis navda aralashtiradi, SITni
  hardcode qiladi va mavjud real contact/support sozlamalarini ishlatmaydi.
- Default navda SIT yo‘q, footerda esa hardcoded bor; mahsulot ierarxiyasi
  qarorsiz.
- Empty states ba’zan userni yana bo‘sh katalogga qaytaradi; configured support
  yoki waitlist backend bo‘lmasa fake “xabardor qilamiz” CTA qo‘shib bo‘lmaydi.
- Password reset UI Uzbek, outbound subject/body Django default tilida qolishi
  mumkin; global `LANGUAGE_CODE` `en-us`.
- Current V1 auth errorlari top banner va field `errorlist`da takrorlanishi
  mumkin; UX-04 prototype runtimega to‘liq portlanmagan.
- Legacy authda sana/location va tasdiqlanmagan `94%/4.9` hardcoded.
- `/offline/` oddiy 200 route, service worker yo‘q; “offline app” claimi noto‘g‘ri.

### 2.7 Boshqa rejalarga tegishli ownership

| Masala | Canonical owner | PUBLIC-01 vazifasi |
|---|---|---|
| Landing content writer/media lifecycle | BACKOFFICE-03 `B3.5` | Public read projection, claim readiness va render contracti |
| Course/plan/cohort/payment/entitlement | A4 + pricing plan + checkout services | Truthful offer projection va intent adapteri |
| SIT source/version/inquiry/AI | SIT-01 | Shared shell/meta/cache registryga adapter; domain logic yo‘q |
| Rich content primitive | Birinchi bo‘lib tushadigan `PUB1.0a` yoki `SIT1.0a` | Bitta `core/rich_content_policy.py`; ikkinchi plan reuse qiladi |
| Blog domain/community/studio | Hozir admission yo‘q | Faqat public privacy/security/SEO/shell; rejected plan qaytmaydi |
| Messenger/AI yordam | MESSENGER-01/A8/A9 | Ishlamaydigan yoki overclaim public CTA bermaslik |
| Error state prototipi | Q19 tarixiy poydevor | Haqiqiy runtime, truthful copy va self-contained asset |

Bir xil muammo ikki plan yoki ikki modelda yechilmaydi. Overlap topilsa agent
avval yuqoridagi ownerni tekshiradi va shared primitive uchun bitta PR tanlaydi.

---

## 3. Tashqi tadqiqotdan chiqarilgan majburiy qoidalar

### 3.1 Accessibility

Release nishoni WCAG 2.2 AA. “Compliant” degan marketing claim faqat manual va
automated to‘liq auditdan keyin ishlatiladi.

- Sahifa `lang="uz"`; turkcha ibora yoki parchaga kerak bo‘lsa `lang="tr"`.
- Semantic `header/nav/main/footer`, bitta mazmunli `h1`, izchil heading va skip
  link.
- Keyboard focus mantiqiy va ko‘rinadigan; sticky header/banner/widget fokusni
  butunlay berkitmaydi.
- WCAG 2.2 minimum target 24×24 CSS px yoki yetarli spacing. AzureLMS primary
  CTA/input uchun ichki UX targeti 44×44; bu “WCAG 44px talab qiladi” degani emas.
- Auth password manager, autofill, copy/paste va `autocomplete` tokenlarini
  qo‘llaydi. CAPTCHA bo‘lsa yagona yo‘l emas.
- Fieldda haqiqiy label, inline xato + `aria-describedby`, bitta error summary,
  server response’dan keyin first-invalid focus va to‘g‘ri qiymatlarni saqlash.
- 320 CSS px reflow, 200% va 400% zoom, text spacing, contrast, forced colors,
  reduced motion, screen reader va native keyboard manual gate.

Manba: [WCAG 2.2](https://www.w3.org/TR/WCAG22/),
[Accessible Authentication](https://www.w3.org/WAI/WCAG22/Understanding/accessible-authentication-minimum.html),
[Target Size Minimum](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html),
[Focus Not Obscured](https://www.w3.org/WAI/WCAG22/Understanding/focus-not-obscured-minimum.html),
[WAI form validation](https://www.w3.org/WAI/tutorials/forms/validation/).

### 3.2 Auth va HTTP xavfsizligi

- Safe methodlar canonical/domain side-effect yaratmaydi. Login/register/
  contact/init/consume kabi mutationlar POST + CSRF; status `GET` faqat
  o‘qiydi. Django reset tokenini URLdan sessionga yashirish kabi framework
  security bookkeeping named exception bo‘lib, olib tashlanmaydi.
- Login/reset natijalari account mavjudligini ochib bermaydi. Per-feature
  account/IP/session signaliga tayangan throttle va bounded delay bo‘ladi;
  permanent hard lockout bilan hujumchi boshqani bloklay olmaydi.
- Reset token random, single-use, TTLli; token URLida `Referrer-Policy:
  no-referrer`; email delivery resource abuse’dan himoyalangan.
- `next`/return/callback arbitrary URL emas: named destination yoki parsed
  scheme/host/port allowlist. Purchase token narx/access uchun authority emas.
- Production HTTPS, Secure/HttpOnly/explicit SameSite cookies, aniq
  `ALLOWED_HOSTS`, `check --deploy`, HSTS staged rollout.
- CSP avval report-only o‘lchanadi, so‘ng enforce; `unsafe-inline` permanent
  yechim emas. `frame-ancestors`, `nosniff`, Referrer va Permissions policy
  explicit.

Manba: [Django 6 security](https://docs.djangoproject.com/en/6.0/topics/security/),
[Django CSRF](https://docs.djangoproject.com/en/6.0/ref/csrf/),
[Django CSP](https://docs.djangoproject.com/en/6.0/ref/csp/),
[Django deployment checklist](https://docs.djangoproject.com/en/6.0/howto/deployment/checklist/),
[OWASP Authentication](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html),
[Forgot Password](https://cheatsheetseries.owasp.org/cheatsheets/Forgot_Password_Cheat_Sheet.html),
[Session Management](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html),
[CSRF](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html).

### 3.3 SEO va indeksatsiya

Har public route `intent → index/noindex → canonical → sitemap → structured
data → cache → auth visibility` contractiga ega bo‘ladi.

- Home/About/course base/detail va sifatli published content canonical va
  sitemapga kirishi mumkin.
- Login/register/reset/token/preview/error/checkout va internal search/filter
  kombinatsiyalari sitemapga kirmaydi; odatda `noindex`.
- `robots.txt` maxfiylik yoki auth vositasi emas. `noindex`ni crawler ko‘ra
  olishi kerak.
- Indexable sahifa self-referential canonical oladi; sitemap faqat 200
  qaytaradigan absolute canonical URLlarni beradi.
- Structured data visible content bilan aynan teng. Organization,
  BreadcrumbList va mos bo‘lsa `Course` + `ItemList`; rich result yoki ranking
  kafolatlanmaydi. FAQ rich-result va 2025da olib tashlangan Course Info feature
  roadmap maqsadi emas.
- Content people-first: haqiqiy author/reviewer/source, rost publish/modified
  sana; “freshness” uchun sun’iy sana yangilanmaydi.

Manba: [canonical URL](https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls),
[noindex](https://developers.google.com/search/docs/crawling-indexing/block-indexing),
[sitemap](https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap),
[structured data policy](https://developers.google.com/search/docs/appearance/structured-data/sd-policies),
[Course list](https://developers.google.com/search/docs/appearance/structured-data/course),
[people-first content](https://developers.google.com/search/docs/fundamentals/creating-helpful-content).

### 3.4 Performance

Core Web Vitals real-user p75 targeti `LCP ≤2.5s`, `INP ≤200ms`, `CLS ≤0.1`.
Lighthouse lab natijasi, ayniqsa INP uchun, RUM o‘rnini bosmaydi.

- LCP hero responsive format/size oladi va lazy-load qilinmaydi; below-fold
  media lazy. Har media intrinsic size yoki aspect-ratio rezervatsiyasiga ega.
- Public core meaning server-rendered HTMLda, JSsiz mavjud.
- Route-specific CSS/JS; third-party chat/analytics/video inventari. Qiymatsiz
  script olib tashlanadi, non-essential script consentdan keyin va defer/async.
- Cookie banner layoutni surib CLS yoki fokus obstruction qilmaydi.
- Public cache faqat personalization, CSRF, preview va analytics writedan
  ajratilgan projectionda yoqiladi.

Manba: [Web Vitals](https://web.dev/articles/vitals),
[responsive images](https://web.dev/articles/serve-responsive-images),
[third-party JavaScript](https://web.dev/articles/third-party-javascript).

### 3.5 KVKK, cookie va legal notice

- Ma’lumot yig‘ilayotgan joyda controller, maqsad, recipient/transfer, usul,
  huquqiy asos va user huquqlari haqida qatlamli notice.
- Privacy policy activity-specific notice o‘rnini bosmaydi. Aydınlatma va açık
  rıza alohida jarayon va alohida evidence.
- Zarur bo‘lmagan analytics/marketing cookie default OFF; consent active,
  granular, qaytarib olinadigan va loglangan. Accept/Reject/Settings bir xil
  darajada; “saytdan foydalansangiz rozisiz” yo‘q.
- Cookie nomi, provider, maqsad, first/third party va expiry ko‘rsatiladi.
- Voyaga yetmaganlar modeli va xalqaro data transfer owner + legal qarorisiz
  taxmin qilinmaydi.

Manba: [KVKK cookie qo‘llanmasi](https://www.kvkk.gov.tr/Icerik/7353/Cerez-Uygulamalari-Hakkinda-Rehber),
[Aydınlatma majburiyati](https://www.kvkk.gov.tr/Icerik/2033/Aydinlatma-Yukumlulugu-),
[2022/1358 cookie qarori](https://www.kvkk.gov.tr/Icerik/7595/2022-1358).

### 3.6 Pricing va dark-pattern chegarasi

Public offer checkoutdan oldin asosiy xizmat xususiyati, barcha soliqlar bilan
real narx, billing/contract muddati, renewal, cancellation/refund sharti,
included/excluded narsalar va seller/contactni aniq beradi. AzureLMS offerining
aniq huquqiy klassifikatsiyasi legal review talab qiladi; “har doim 14 kun”
degan universal claim qilinmaydi.

Soxta countdown/scarcity, yashirin fee, preselected pullik addon, isbotsiz
“eng ommabop”, confirmshaming, sun’iy reference price, fake review/student count
va cancellationni signupdan qiyin qilish taqiqlanadi.

Manba: [T.C. Ticaret Bakanlığı abonelik qo‘llanmasi](https://tuketici.ticaret.gov.tr/yayinlar/tuketici-bilgi-rehberi/abonelik-sozlesmeleri-hakkinda-bilgilendirme),
[masofaviy shartnomalar](https://tuketici.ticaret.gov.tr/yayinlar/tuketici-bilgi-rehberi/mesafeli-sozlesmeler-hakkinda-bilgilendirme),
[OECD dark commercial patterns](https://www.oecd.org/en/topics/dark-commercial-patterns.html).

---

## 4. Foydalanuvchilar va axborot arxitekturasi

### 4.1 Asosiy rollar

| Rol | Asosiy savol | Public qatlam javobi |
|---|---|---|
| Birinchi tashrifchi | “Bu menga mosmi?” | Kim uchun, format, real kurs va keyingi qadam |
| Kurs qidiruvchi | “Nimani va qachon o‘rganaman?” | Filter, outcome, prerequisite, curriculum, workload, cohort/offer |
| Narx solishtiruvchi | “Qancha va nimaga to‘layman?” | Total price/billing/included/excluded/cancel truth |
| Qaytgan user | “Kirish yoki parolni tiklashni qanday tugataman?” | Accessible, enumeration-safe auth va real delivery |
| SIT tashrifchisi | “Qaysi dastur va qanday yordam?” | SIT-01 discovery/inquiry; public shared shell |
| Kontent o‘quvchi | “Maqola ishonchlimi va keyin nima qilaman?” | Author/source/date, canonical CTA; yashirin tracking yo‘q |
| Sertifikat tekshiruvchi | “Bu hujjat haqiqiymi?” | Minimal verifier; learner akademik tarixini oshkor qilmaydi |
| Owner/editor | “Nimani nashr qilyapman?” | Preview, evidence/readiness, reason/audit/rollback |

### 4.2 Target public navigatsiya

Desktop va mobile bir xil ma’no va tartibda:

1. Bosh sahifa
2. Kurslar
3. Tariflar
4. Turkiyada o‘qish — owner uni alohida mahsulot kirishi sifatida tasdiqlasa
5. Foydali materiallar — hozirgi Blog labeli owner copy qaroriga bog‘liq
6. Biz haqimizda
7. Kirish / Hisob yaratish yoki authenticated bo‘lsa O‘quv maydoni

Footer uch landmark guruhiga bo‘linadi: **Platforma**, **Kompaniya/yordam**,
**Huquqiy**. Link faqat real route/configuration bo‘lsa chiqadi. “Sertifikatlar”
linki verifier search route bo‘lmasa Aboutga yashirin map qilinmaydi. Support
email/phone/hours bo‘sh bo‘lsa UI service va’da qilmaydi.

### 4.3 Asosiy purchase yo‘li

```text
Landing yoki tashqi search
  → Course catalog
  → Course detail + canonical offer
  → [Kirish | Hisob yaratish]
  → optional onboarding
  → ayni course checkout
  → server qayta tekshirgan quote
  → mavjud payment/receipt oqimi
```

Default — **course-first**. Global pricingdan “sotib olish” userga course tanlamay
turib generic account yaratmaydi; course tanlashga olib boradi. PUB-D1 owner
plan-first flowni aniq admit qilsa, signed intent plan code’ni course tanlash
bosqichigacha saqlaydi, lekin checkout baribir canonical availability va price
qayta resolve qiladi.

Failure holatlari:

- registration OFF: intent saqlanadi; existing login va faqat configured real
  support/waitlist ko‘rsatiladi; user yaratilmaydi;
- cohort/plan auth oralig‘ida yopildi: enrollment/receipt yaratilmaydi; typed
  unavailable holati va real alternative;
- email delivery yo‘q: reset request generic response beradi, operator
  capability red; production “email yuborildi”ni real delivery deb hisoblamaydi;
- JS/network uzildi: server-rendered forms va retry-safe response ishlaydi.

### 4.4 Qaytgan user auth yo‘li

```text
Login
  ├─ email/username + password
  ├─ Telegram explicit start → pending status → POST consume
  └─ Parolni unutdim → generic receipt → email token → new password → login
```

User entered email/passworddan tashqari cognitive puzzle yechmaydi. Password
manager va paste ishlaydi. Telegram yo‘li boshlanishidan oldin nima almashishi,
token muddati va browserga qaytish tushuntiriladi; QR/deep-link desktop/mobilega
mos. Cancel va manual status check bor.

### 4.5 Content discovery yo‘li

- Blog: list/search/tag → detail → source/author/date → course yoki configured
  support CTA. Comment/reaction domain logic o‘zgarmaydi.
- SIT: list/filter/detail/guide → SIT-01 qualified inquiry. Generic AI room
  domain yordam so‘rovi o‘rnini bosmaydi.
- Filter/detail/back query state saqlanadi; external yoki protocol-relative
  `return_to` rad etiladi.

### 4.6 Legal va trust yo‘li

Footer legal link → current effective revision → effective date/controller/
contact → activity-specific notice yoki cookie settings. Registration/checkout
qaysi revision va qanday acknowledgement talab qilishini legal owner belgilaydi.
Agent generic checkboxni “compliance” deb o‘zi qo‘shmaydi.

### 4.7 Certificate verification yo‘li

Target URL: `/certificates/verify/<opaque-token>/`.

- Token kamida 128-bit entropy; sequential user/course ID authority emas.
- Public projection owner/legal qaroridagi minimal maydonlar va current/revoked
  holatni ko‘rsatadi.
- Appendix default authenticated learner/authorized staff; alohida share token
  faqat explicit owner admission bo‘lsa.
- Barcha verifier route `noindex,noarchive`, `no-store`, `no-referrer`; random ID
  404 generic va rate-limited.

Eski certificate URL bir kunda o‘chirilmaydi. Expand/backfill/alias telemetry/
expiry va rollback PUB1.5da aniq migratsiya bilan bajariladi.

### 4.8 System state yo‘li

- 403 foydalanuvchiga login faqat login yordam bera olsa taklif qiladi.
- 404 home, catalog va kerak bo‘lsa searchga real forward path beradi.
- 500 “xabardor qilindi” demaydi; real incident receipt bo‘lsa keyin truthful
  copy ulanadi.
- Maintenance `503` + operator belgilagan `Retry-After`; offline browserning
  network holatini tushuntiradi, service worker capability’sini va’da qilmaydi.
- Retry oldingi POSTni blind resubmit qilmaydi; faqat safe current URL GET yoki
  explicit yangi action.

---

## 5. Canonical arxitektura va contractlar

### 5.1 Asosiy qoidalar

1. **Public view haqiqat egasi emas.** U Course/Cohort/Plan/Enrollment,
   LegalRevision, published content va registration policy’dan projection oladi.
2. **Bitta policy, barcha renderer.** Legacy/V1/preview/metadata/sitemap bir xil
   eligibility, rich-content va claim qarorini iste’mol qiladi.
3. **Safe method canonical/domain state yozmaydi.** Intentional analytics
   alohida service va privacy policy bilan ajratiladi. Django CSRF va password
   reset URL-tokenini session indirection orqali yashirish kabi framework
   security bookkeeping esa named allowlist, minimal scope va disclosure
   regressioni bilan qoladi; agent uni “GET write 0” uchun buzmaydi.
4. **Security flag ortida emas.** Sanitization, registration gate, CSRF,
   method, redirect va token invariantlari OFF rollbackda ham saqlanadi.
5. **UI access bermaydi.** Hidden CTA, signed intent yoki public cache
   enrollment/payment/certificate authorization o‘rnini bosmaydi.
6. **Fail truthful.** Data yoki dependency yo‘q bo‘lsa fake content/success
   emas, typed unavailable va real recovery.

### 5.2 `PublicSurfacePolicy`

Yangi `frontend/public_policy.py` barcha human-facing anonymous route uchun
code-owned registry saqlaydi. Model yoki admin’da arbitrary route policy
yaratilmaydi.

```python
@dataclass(frozen=True)
class PublicSurfacePolicy:
    route_name: str
    methods: frozenset[str]
    audience: Literal["anonymous", "mixed", "sensitive", "ops"]
    index_policy: Literal["index", "noindex", "conditional"]
    canonical_policy: Literal["self", "clean_base", "none", "object"]
    sitemap_policy: Literal["include", "exclude", "object"]
    cache_class: CacheClass
    rich_content_profile: str | None
    telemetry_class: str | None
    claim_gate: bool
```

Registry startup/system checkda quyidagini rad etadi:

- duplicate route, unknown named route yoki method;
- sensitive/token/preview routega `index` yoki shared cache;
- sitemapga canonical’siz route;
- rich content render qiladigan routega policy’siz profile;
- mixed/personalized responsega public shared cache;
- route inventaridagi human-facing path registrydan tashqarida qolishi.

`core/urls.py`dagi health/readiness va CKEditor upload `ops/non-product`
allowlistda turadi. Bu ularni indexable pagega aylantirmaydi.

### 5.3 Index, canonical va cache matrixi

| Surface | Robots | Canonical | Sitemap | Cache class |
|---|---|---|---|---|
| Home/About | index,follow | self | include | `PUBLIC_CONTENT` proofdan keyin |
| Course list clean | index,follow | self | include base | `PUBLIC_CONTENT` |
| Course list `q/sort/level` | noindex,follow | clean base | exclude | `PUBLIC_QUERY` revalidate |
| Unfiltered page 2+ | index qarori owner/SEO evidence bilan; default noindex | self yoki base, bir xil policy | exclude | `PUBLIC_QUERY` |
| Course detail active | index,follow | object URL | include | `PUBLIC_CONTENT` |
| Pricing | index faqat truthful live offer bo‘lsa; aks holda noindex | self | conditional | `PUBLIC_CONTENT` |
| Published Blog/SIT detail | domain eligibility | object URL | object registry | domain projection |
| Preview/draft | noindex,nofollow | none | exclude | `PREVIEW_PRIVATE` |
| Login/register/reset/onboarding | noindex,nofollow | none | exclude | `SENSITIVE_NO_STORE` |
| Certificate/token | noindex,noarchive | none | exclude | `SENSITIVE_NO_STORE` |
| Error/maintenance/offline | noindex,nofollow | none | exclude | `STATUS_NO_STORE` |
| Health/ready/upload | product metadata yo‘q | none | exclude | endpoint-specific |

`CacheClass` contracti:

- `SENSITIVE_NO_STORE`: `private, no-store`, `Pragma: no-cache`, no ETag body
  reuse; auth, reset, token, preview, user-dependent response.
- `STATUS_NO_STORE`: `no-store`; maintenance `Retry-After`; error response
  statusi saqlanadi.
- `PUBLIC_QUERY`: browser revalidation, shared cache OFF; bounded ETag mumkin.
- `PUBLIC_CONTENT`: avval `max-age=0, must-revalidate`; projection cookie,
  CSRF, user header, tracking write va random data’dan ajratilgani testlangach
  revision-keyed short `s-maxage` owner/operator sozlamasi bilan yoqiladi.
- `IMMUTABLE_ASSET`: content hash/revision URL, uzoq immutable cache.

`frontend_v1_public` faqat renderer tanlaydi. U policy, sanitizer yoki cache
xavfsizligini o‘chirmaydi. Shared cache birdan barcha routega yoqilmaydi.

### 5.4 `PublicPageMeta`

`frontend/public_meta.py` typed value object qaytaradi:

```text
title, description, canonical_url, robots,
open_graph(title, description, url, type, image, image_alt, locale),
twitter(card, title, description, image),
breadcrumbs, structured_data, modified_at
```

Qoidalar:

- absolute URL faqat configured `PUBLIC_CANONICAL_ORIGIN`dan; raw `Host`
  authority emas;
- description plain text, bounded va sahifaga xos; rich HTML yoki query body
  metadata’ga kirmaydi;
- preview, search, token, auth va errors explicit noindex; template unutsa
  registry response middleware/testi xato beradi;
- OG image faqat valid public media rendition; private/original upload URL yo‘q;
- JSON-LD visible projection bilan ayni selector’dan quriladi. Hidden price,
  stale statistic yoki unpublished course schema ichiga kirmaydi;
- structured-data validator PASS ranking/rich result kafolati deb yozilmaydi.

`robots.txt` sitemap pointer va zarur crawl guidance beradi, secret path ro‘yxati
emas. `sitemap.xml` `frontend/public_sitemap.py` registridagi published canonical
object selectorlardan tuziladi; preview/filter/token/empty 404 yo‘q.

### 5.5 `PublicOfferProjection`

`courses/public_offer.py` yangi model emas; read-only projection builder:

```text
course: id, slug/route, title, level, outcome, prerequisites,
        duration/workload, curriculum counts, instructor display
availability: active cohort count, next start, schedule summary, seats state
plans: code, display name, current total/billing unit, included/excluded,
       purchase eligibility and truthful unavailable reason
cta: intended destination enum, auth requirement, reason
source_revision: course/cohort/plan fingerprints
```

Projection faqat mavjud canonical selector/service’lardan oladi. `price`
legacy fieldini `Plan` haqiqatiga parallel source sifatida ishlatmaydi.
Seat/plan/price CTA render paytida snapshot, checkout POSTda qayta tekshiriladi.
No active cohort bo‘lsa “joy bor” yoki fake waitlist yo‘q; owner configured real
support bo‘lsa o‘sha, aks holda katalogga qaytish.

Query budget fixturelari 0, 1, 8 va 100 course bilan yoziladi. List card uchun
N+1 yo‘q; detail expensive counts bounded annotation/prefetch bilan.

### 5.6 `PublicIntent`

Purchase niyati client-controlled `next=/checkout/...&plan=1` emas. Yangi
`frontend/public_intent.py` Django signing bilan stateless typed envelope beradi:

```text
version: 1
destination: "course_checkout" | "course_detail" | "catalog"
course_id: integer | null
plan_code: stable string | null
issued_at: unix timestamp
nonce: random correlation id
```

- Client tokenni o‘zgartira olmaydi; `max_age` audited runtime setting.
- Destination enum named routega map bo‘ladi; raw URL saqlanmaydi.
- Tokenda PII, price, seat, entitlement yoki authorization yo‘q.
- Login/register/onboarding tokenni aynan saqlaydi; auth completion resolver
  signature/age/route/course/plan/registration policy’ni qayta tekshiradi.
- Checkout canonical `Course/Cohort/Plan`dan yangi quote oladi. Token faqat
  niyat, hech qachon buyurtma yoki band qilingan joy emas.
- Invalid/expired token generic safe destination va visible explanation beradi;
  open redirect, 500 yoki silent dashboard yo‘q.
- Same nonce’dagi transition telemetry bir marta sanaladi; token URL/referrerda
  yuradigan bo‘lsa faqat non-sensitive IDlar va strict referrer policy.

Generic protected sahifa uchun mavjud `_safe_next` saqlanadi. Public purchase
intent uni almashtirish emas, course/plan typed continuity qo‘shimchasi.

### 5.7 Claim va testimonial readiness

Marketing matnini boshqarish va uni nashrga tayyor deb bilish alohida. B3.5
existing `LandingPage`/`LandingProcessStep` writerini boshqaradi; PUBLIC-01
quyidagi shared evidence gate’ni qo‘shadi.

`frontend/models.py`dagi additive `PublicClaimEvidence`:

| Maydon | Contract |
|---|---|
| `claim_key` | Stable code, unique; masalan `landing.active_students` |
| `content_digest` | Ko‘rsatiladigan normalized text/value SHA-256; matn o‘zgarsa evidence stale |
| `source_url` | Optional public source; scheme allowlist |
| `evidence_note` | Owner uchun bounded izoh; publicga avtomatik chiqmaydi |
| `verified_at`, `expires_at` | Freshness; expiry o‘tganda claim yashirin |
| `approved_by`, `approval_reason` | Owner/publisher va sabab |
| `revision` | Stale-save/CAS va audit |

Statistics, award, rating, student count, success rate, support response time,
course duration guarantee, discount/reference price va AI capability claim gate
orqali chiqadi. Evidence row mavjudligi o‘zi yetmaydi: digest, vaqt va effective
publication mos bo‘ladi.

`Testimonial` additive maydonlari: `display_name`, `consent_scope`,
`consent_confirmed_at`, `consent_revoked_at`, `source_reference`, `order`.
Consent yo‘q/revoked bo‘lsa public emas. Rating aggregate deb talqin qilinmaydi;
sample fikr ekanligi ko‘rinadi. Random sample olib tashlanadi, explicit stable
order ishlaydi.

Defaults va migration seedlari production claim emas. Readiness command
`audit_public_readiness` ularni `unverified/expired/missing-consent` deb chiqaradi;
agent synthetic rowni verified qilmaydi.

### 5.8 Rich content va URL policy

`core/rich_content_policy.py` named profile `PUBLIC_EDITORIAL_V1`ni e’lon qiladi.
`SIT1.0a` birinchi tushsa u yaratadi; `PUB1.0a` reuse qiladi. PUBLIC birinchi
tushsa aksincha. Ikki sanitizer bo‘lmaydi.

Profile minimumi:

- semantic paragraph/heading/list/blockquote/table/code va safe link/image;
- script, event handler, SVG/MathML executable surface, form/input, `object`,
  `embed`, `srcdoc`, `data:`/`javascript:`/malformed URL rad;
- global `style`, arbitrary `id/class` rad; zarur presentation classlari exact
  allowlist;
- iframe default rad. YouTube/Vimeo kerak bo‘lsa raw iframe emas,
  canonical media embed object + exact host/path/query policy;
- external link uchun safe scheme, `rel="noopener noreferrer"`; target policy;
- image src faqat approved storage/rendition; alt required yoki explicit
  decorative marker; width/height;
- sanitizer idempotent va renderer-independent.

Containment ikki qatlam:

1. Render-time sanitization legacy va V1da darhol, flag ON/OFF parity.
2. Publication/save service normalized sanitized snapshotni tekshiradi; unsafe
   diff ownerga ko‘rsatiladi. Existing rows read-only audit command bilan
   quarantine report oladi; migration raw contentni ko‘r-ko‘rona yo‘q qilmaydi.

`frontend/templatetags/bleach_tags.py`ni global birdan o‘zgartirish boshqa private
consumerlarni sindirishi mumkin. Named wrapper bosqichma-bosqich ulanadi;
global filterning mavjud import/output smoke testi saqlanadi.

Navigation URL uchun `frontend/public_url_policy.py`: local named route yoki
`https`, zarur bo‘lsa `mailto/tel`; `javascript/data/file`, protocol-relative,
control/backslash va unapproved host rad. Legacy va V1 bir xil helper ishlatadi.

### 5.9 Auth edge contracti

#### Shared registration policy

`users/registration_policy.py::can_create_account(channel, request, identity)`
web, Telegram bot va Mini App uchun yagona qaror. Avval productiondagi barcha
`CustomUser.create_user` call-site inventar qilinadi; kamida web register,
Telegram deep-link auth va `register_guest_via_phone` shared service orqali
o‘tadi. Mini App hozir existing-user lookup bo‘lsa ham yangi identity uchun
create count `0` parity testi bilan qulflanadi. `public_registration=OFF` bo‘lsa
hech bir adapter yangi `CustomUser` yaratmaydi. Mavjud user login/claim qilishi
mumkin. Telegram synthetic email va unusable-password accounti faqat policy,
notice va owner decision bilan; flagni aylanib o‘tmaydi.

#### Auth abuse service

`users/auth_abuse.py` login/register/reset/Telegram init/status/consume uchun
feature + HMAC-hashed identity + trusted-client-IP/session bo‘yicha decision
qaytaradi. Raw email/IP log yoki modelga yozilmaydi. Exact threshold, window va
retention audited runtime setting; permanent lockout yo‘q. Edge/WAF global
limit application per-feature limit o‘rnini bosmaydi.

Initial schema kerak bo‘lsa `AuthThrottleBucket`:

```text
scope, key_digest, window_start, count, blocked_until, expires_at
UNIQUE(scope, key_digest, window_start)
```

Transaction-safe increment, cleanup command/beat task, max-row health signal va
clock boundary tests majburiy. PUB1.0cda konservativ default qiymatlar bilan
darhol enforce qilinadi; report-only faqat lokal/staging o‘lchovi uchun va P0ni
kechiktirmaydi. Owner/security PUB-D13 orqali qiymatlarni audited setting bilan
sozlaydi. `Retry-After` userga accessible generic copy;
response account mavjudligini oshkor qilmaydi.

#### Telegram method split

Target endpointlar:

- `POST /users/telegram-auth/init/` — CSRF, throttle, bitta browserda bitta
  active session, safe intent;
- `GET /users/telegram-auth/status/<token>/` — effective pending/authenticated/
  expiredni **write qilmasdan** o‘qiydi;
- `POST /users/telegram-auth/consume/<token>/` — CSRF, browser key, row-lock,
  TTL, one-time mark, `django_login`, safe intent resolve;
- bot callback canonical service orqali pending → authenticated; registration
  policy va transaction ichida.

Expired/used rows bounded retention bilan purge. Status polling interval/backoff
va max lifetime client + serverda bir xil contractdan. Cancel browser state’ni
tozalaydi, boshqa user tokenini mutate qilmaydi.

#### Password reset delivery

- Known/unknown/inactive/unusable receipt matni va observable flow teng qoladi.
- Uzbek subject, plain text va HTML template; reset URL no-referrer page.
- Non-local console backend `system_audit`, readiness/release checkda red.
- Send failure userga account existence signal bermaydi; operatorga typed
  delivery failure. Logga token/body chiqmaydi.
- Per-account/IP throttle; token brute-force limit; reused/expired recovery.
- Email verificationni majburiy qilish PUB-D14 qarori; agent o‘zi qo‘shmaydi.

### 5.10 Legal revision contracti

Current mutable `LegalPage` read model bo‘lib qolishi mumkin, lekin target
publication immutable revisionga tayanadi:

```text
LegalDocument: kind, current_revision_id
LegalRevision: document, version_label, title, sanitized_content,
               effective_at, published_at, status,
               created_by, approved_by, reason, content_digest
```

`draft → approved → scheduled/published → superseded/archived`; bir documentga
bitta effective revision. Preview private/noindex/CTA-free. Publish/rollback
append-only audit va CAS; old acceptance receipt qayta yozilmaydi.

Registration/checkout acknowledgement alohida `LegalAcceptance` faqat legal
owner talab qilsa: user, revision, purpose, accepted_at, channel, receipt key.
Marketing consent unga qo‘shilmaydi. Default generic migration contenti
owner/legal approval bo‘lmaguncha “approved” bo‘lmaydi.

Missing effective revision public GETda row yaratmaydi. Safe behavior: `503`
truthful unavailable, noindex/no-store, configured contact; production readiness
red. FAQ legal acceptance document emas va alohida content sifatida yuradi.

### 5.11 Privacy, cookie va telemetry

`nuclear-program/frontend-v1/PUBLIC-COOKIE-INVENTORY.md` PUB1.5da generated
evidence sifatida yaratiladi: cookie/local storage, owner, purpose, legal basis,
first/third party, expiry, code path, essential/optional, disable/purge.

Safe default:

- session/CSRF/theme kabi zarur client state documented;
- anonymous Blog unique-view cookie/IP/User-Agent tracking PUB-D6gacha OFF;
- non-essential analytics/marketing script va cookie OFF;
- consent platform faqat real non-essential purpose admit qilinsa quriladi;
  decorative banner yo‘q;
- telemetry event payloadida PII/form/search text/token/referrer query yo‘q;
- HMAC/opaque journey ID short-lived va purpose-bounded; retention legal/owner
  qarori bilan; refresh/retry same transitionni qayta sanamaydi.

Minimal first-party event allowlist:

```text
public_landing_view, catalog_results_view, course_detail_view,
purchase_intent_created, auth_started, auth_completed,
checkout_quote_viewed, receipt_created,
public_unavailable_shown, support_action_used
```

Eventlar product truthni o‘zgartirmaydi. `receipt_created` canonical receipt
transactionidan keyin; browser click undan oldin conversion emas.

### 5.12 Certificate verifier contracti

Owner PUB-D4/PUB-D15 qaroridan so‘ng additive schema:

```text
Certificate.public_token          unique, random >=128-bit, nullable during backfill
Certificate.public_status         hidden | verifiable | revoked
Certificate.public_name_mode      full | abbreviated | omitted
Certificate.revoked_at/reason     private reason, public truthful status
Certificate.verification_revision monotonic
```

Public selector minimal projectiondan boshqa relationni prefetch qilmaydi.
Appendix `LoginRequiredMixin` + owner/own-certificate authorization; public
share alohida scoped expiring token admit qilinmaguncha yo‘q. Legacy ID alias:

1. expand-only fields;
2. deterministic resumable backfill random token bilan, collision test;
3. dual-read telemetry, new link token route;
4. owner-approved grace;
5. legacy route noindex/no-store, keyda embedded IDsga public detail bermaslik;
6. expiry/redirect yoki 404 owner qarori; rollback fieldsni o‘chirmaydi.

Certificate tokenni topish uchun public “all certificates search” yoki user ID
query yo‘q. Random lookup throttle va generic response; audit raw tokenni log
qilmaydi.

### 5.13 Writer va publication ownership

- B3.5 `LandingPage`/`LandingProcessStep` writer UX, media lifecycle,
  preview/audit/rollbackni quradi.
- PUBLIC claim/readiness service publishdan oldin evidence, unsafe URL/rich
  content va required CTA route’ni tekshiradi.
- About/team/statistic/testimonial/nav/auth copy/legal uchun bitta public content
  workspace keyingi B3/public slice’da existing modellarni service orqali
  boshqaradi; erkin page builder yoki parallel CMS yo‘q.
- Django admin direct writer servicega ulanadi yoki read-only bo‘ladi.
- Blog studio hozirgi admission doirasida qoladi; Blog domain revisioning shu
  reja bahonasida qurilmaydi. Ammo shared sanitizer/URL/claim policy bypass
  qilolmaydi.
- Preview side-effect 0: analytics/read count/cookie/CTA mutation/email yo‘q.

---

## 6. Target UX va dizayn qoidalari

### 6.1 Umumiy sahifa anatomiyasi

Har human public sahifada:

1. skip link;
2. bir xil public header va current location;
3. bitta aniq `h1` va qisqa lead;
4. asosiy content/task;
5. bitta primary keyingi qadam, zarur secondary recovery;
6. consistent help/contact joyi;
7. grouped footer va legal/settings;
8. status/error `role`lari va focus management.

Bir ekran bir vaqtda uchta primary CTA bermaydi. CTA verb + destinationni aytadi:
“A1 kursini ko‘rish”, “Ayni kursga kirish”, “Tariflarni solishtirish”. “Boshlash”
yoki “Batafsil” contextdan tashqarida accessible name bo‘lib qolmaydi.

### 6.2 Landing

First fold:

- kim uchun va asosiy outcome — kafolatsiz, plain language;
- primary `Kurslarni ko‘rish`; secondary faqat real `Tariflar` yoki owner
  configured SIT entry;
- bitta lightweight image/illustration; autoplay hero video default emas;
- dalilsiz badge/stat/award yashirin.

Keyin: qanday ishlaydi → live course cards → offer tushuntirishi → verified
testimonial bo‘lsa → truthful support/FAQ → final CTA. AI, exam, certificate
capability faqat current release/readinessga mos bo‘lsa. Recent students/PII
yo‘q. Empty course holati fake card bermaydi.

### 6.3 Catalog

- Search max length, trim/normalize, HTML body emas searchable plain projection;
- allowed level/sort qiymatlari; unknown query visible validation yoki safe
  default, silent arbitrary DB behavior emas;
- result count va applied filters; individual removable chip/link; “Hammasini
  tozalash”; GET form/no-JS;
- stable sort tie-breaker (`-created_at, -id` kabi);
- pagination query saqlaydi, `aria-current`, previous/next va direct pages;
- card: title, level, truthful duration/workload/start/price/availability faqat
  mavjud bo‘lsa; unique accessible link name;
- zero result filter recovery va configured support, fake waitlist emas.

### 6.4 Course detail

First fold qaror uchun:

- title, level, kim uchun, measurable-but-not-guaranteed outcome;
- next active cohort/start/schedule/timezone va availability;
- “from price” faqat haqiqiy applicable plan setdan; barcha soliqlar/period copy;
- primary exact course CTA; auth statusga mos;
- unavailable reason va real alternative.

Keyin prerequisite, curriculum/sample lesson, instructor credential, workload,
assessment/certificate ma’nosi, included/excluded, support channel/real response
expectation, pricing link. `0 imtihon` badge feature sifatida ko‘rsatilmaydi;
section content mavjud bo‘lsa chiqadi. Course description shared sanitizer va
rich-text typography oladi.

### 6.5 Pricing

Pricing course’dan ajralgan “account generator” emas. Default course-first:

- cards core farq, teacher attention/AI quota va included/excludedni canonical
  policy’dan ko‘rsatadi;
- total, billing period, renewal, cancellation/refund/manual approval truth;
- `is_popular` faqat evidence/owner rationale bilan “Ko‘p tanlangan”; bo‘lmasa
  neutral recommended copy ham yo‘q;
- CTA “Kursni tanlash” yoki course contextida “Ayni tarif bilan davom etish”;
- unavailable plan hidden emas, qaror uchun zarur bo‘lsa typed reason bilan;
- pricing va checkout quote mismatch release blocker.

### 6.6 Auth

- One-column task first; decorative trust panel dalilsiz stat bermaydi.
- Har field label, autocomplete, inputmode, help/error association.
- Error summary count + anchor; xato bir marta; first invalid focus; password
  server response’da echo qilinmaydi.
- Password rules input oldidan; fake strength score yo‘q. Reveal button keyboard
  va accessible name/state bilan.
- Login/register/reset/Telegram o‘rtasida intended course/plan ko‘rinadi:
  “Kirishdan keyin A1 kursi yozilishiga qaytasiz.”
- Registration closed sahifa 200 marketing dead-end emas: exact status,
  existing login, configured help va intent expiry tushuntirishi.
- Legal notice form submit yaqinida, version/current link bilan; checkbox
  faqat legal qaror talab qilsa.

### 6.7 Error, maintenance va offline

- Inline style/script va external CDN dependency olib tashlanadi; local minimal
  CSS/icon/SVG.
- Status code saqlanadi; 500 details/PII/request body ko‘rsatmaydi.
- Retry safe methodni takrorlaydi; POST resultga blind reload yo‘q.
- Focus `h1`ga yoki main boshiga; clear recovery links; light/dark/forced colors.
- Maintenance time taxmin qilinmaydi; real operator ETA bo‘lsa timestamp/timezone.

### 6.8 Responsive media va asset budget

- Public base `tokens + base + components + shell + public` oladi; auth va
  learning CSS faqat tegishli route. JS ham header, form va reaction bo‘yicha.
- Builddagi hashed static contract saqlanadi; inline script/style chiqariladi.
- Image pipeline approved size/format variantlari, `srcset/sizes`, width/height,
  EXIF strip va upload validation.
- Hero LCP asset eager/fetchpriority faqat lab + field evidence bilan; qolgan
  media lazy/async decode.
- Video: poster, controls, transcript/caption kerak bo‘lsa, no autoplay audio;
  reduced-motionda animation/video avtomatik boshlanmaydi.
- Har route uchun compressed CSS/JS/image bytes baseline va regression budget;
  exact budget PUB1.7a o‘lchovidan so‘ng evidence bilan qulflanadi.

### 6.9 Accessibility acceptance

Automated axe/html validator zarur, yetarli emas. Final manual matrix:

- 320/390/640/768/1024/1440 CSS px;
- 200% va 400% zoom, 200% text, custom text spacing;
- keyboard-only, no pointer; focus order/visible/not obscured;
- Windows NVDA + Chrome/Firefox; macOS/iOS VoiceOver + Safari; Android TalkBack
  imkon bo‘lsa; owner qurilmasi alohida;
- light/dark, high contrast/forced colors, reduced motion, Save-Data;
- JS disabled core home/catalog/detail/auth/reset/comment/filter journey;
- long Uzbek copy, Turkish span pronunciation, empty/error/loading/unavailable.

“Axe 0” owner/native/AT acceptance o‘rnini bosmaydi.

---

## 7. Threat model va privacy matrixi

| Xavf | Joriy dalil | Target control | Majburiy test |
|---|---|---|---|
| Stored XSS | Legacy raw `safe`, broad iframe/style policy | Shared named sanitizer, save + render defense, CSP migration | Malicious corpus; ON/OFF parity |
| Unsafe nav URL | Legacy custom `href` raw | One URL policy all renderers/writers | javascript/data/protocol-relative/control chars |
| Registration bypass | Telegram unknown ID creates user | Shared registration policy all adapters | Flag OFF: web/bot/Mini App user count unchanged |
| Auth brute force/flood | Throttle yo‘q | Per-feature hashed identity/IP/session limits | boundary, retry-after, no permanent lockout |
| State-changing GET/CSRF | Telegram init/status writes | POST init/consume + CSRF; read-only status | GET DB/session write 0; CSRF denial |
| Account enumeration | register duplicate; reset abuse risk | Generic auth receipts/timing, rate limit | known/unknown response contract |
| Open redirect | Existing safe-next good, plan context missing | Named signed intent + existing safe-next | external/scheme/backslash/expired signature |
| Cache leak | Policy rendererga bog‘liq | Typed response policy; sensitive no-store | anonymous/auth/preview cross-cache leakage 0 |
| Preview leak | Staff preview varies by domain | Explicit preview permission, 404 guest, CTA/tracking 0 | role matrix + noindex/no-store |
| Certificate enumeration | Embedded IDs + 24-bit suffix | 128-bit token, minimal selector, appendix auth | random/legacy/revoked/noindex/no-store |
| Hidden tracking | 1-year Blog cookie + IP hash | Default off, inventory/legal basis/consent/retention | no-consent cookie/write 0; purge |
| False claim | Seed/default stats and support copy | Digest-bound evidence/readiness | edit invalidates evidence; expired hidden |
| Legal fallback as policy | GET creates generic row | Immutable approved revision, readiness fail | GET write 0; missing revision 503 |
| Host/SEO poisoning | Canonical infrastructure yo‘q | Configured origin, not raw Host | hostile Host canonical unchanged |
| Query resource abuse | Unbounded `icontains` | normalized caps, indexed projection, per-IP budget | max input/query count/timeout |
| Third-party outage/privacy | Fonts/icons/CDN on errors | Self-host critical assets; optional consented third party | blocked network still usable |
| Ops disclosure | healthz/readyz environment va release detail public | Coarse external status; detailed owner auth | ikkala anonymous payload snapshoti |
| Method replay | Offline/refresh | GET-safe retry, POST receipt/idempotency | refresh/double-click no duplicate |

Security logging redaction: password, reset/Telegram/certificate/intent token,
cookie, session, CSRF, email, raw IP, form body va search text logga kirmaydi.
Structured event faqat error code, route policy, hashed short-lived actor bucket
va correlation receiptni oladi.

---

## 8. Tavsiya etilgan modul va fayl chegaralari

| Joy | Vazifa | Yangi haqiqat yaratadimi? |
|---|---|---|
| `frontend/public_policy.py` | Route/index/cache/method registry | Yo‘q; code policy |
| `frontend/public_meta.py` | Canonical metadata/JSON-LD projection | Yo‘q |
| `frontend/public_sitemap.py` | Published canonical URL registry | Yo‘q |
| `frontend/public_response.py` | Header/cache/security policy application | Yo‘q |
| `frontend/public_intent.py` | Signed typed acquisition intent | Yo‘q; token authority emas |
| `frontend/public_claims.py` | Evidence/readiness/digest policy | Evidence modelni o‘qiydi |
| `frontend/public_content.py` | Landing/About/nav/legal read projection | Existing/revision state |
| `core/rich_content_policy.py` | Shared named sanitizer profiles | Yo‘q |
| `frontend/public_url_policy.py` | URL scheme/host/named-route validation | Yo‘q |
| `courses/public_offer.py` | Course/cohort/plan read-only projection | Yo‘q |
| `users/registration_policy.py` | Web/bot/Mini App account-creation gate | Yo‘q |
| `users/auth_abuse.py` | Auth throttle decision/service | Bounded operational buckets |
| `users/telegram_auth_service.py` | Init/status/consume transitions | Existing session state |
| `users/password_delivery.py` | Reset email capability/typed result | Delivery, account truth emas |
| `courses/certificate_public.py` | Minimal verifier selector/policy | Existing certificate + token state |
| `core/public_readiness.py` | Claims/legal/offers/email/media release checks | Yo‘q; Control Center projection |
| `templates/frontend_v1/public/...` | Presentation only | Yo‘q |

View/template/admin/bot ichida duplicate business rule yozilmaydi. Model `save()`
ichida request, permission yoki external delivery logic joylashtirilmaydi.
State mutation service + transaction + audit orqali; template faqat typed
projectionni ko‘rsatadi.

---

## 9. Observability va readiness

### 9.1 Public readiness snapshot

Owner Control Centerda quyidagi coarse holatni ko‘radi:

- effective legal revisionlar: privacy/terms/FAQ;
- verified/expired/missing marketing claims va testimonial consent;
- active courses, sellable course/cohort/plan combinations;
- SMTP/reset delivery capability;
- public registration policy per channel;
- Blog tracking/optional cookie state;
- certificate verifier migration/revoked/legacy alias count;
- sitemap URL count, canonical/meta failures;
- auth throttle bucket health/cleanup lag;
- public asset/media broken reference va cache revision;
- last RUM/lab/a11y evidence age.

Anonymous `/healthz` va `/readyz` bu detailni bermaydi. Owner snapshot
read-only; setting
o‘zgartirish existing audited Control Center patternida reason/confirmation/
revision bilan.

### 9.2 Alert va SLO

Alertlar absolute marketing metric emas, operator actionga bog‘langan:

- 5xx yoki auth failure baseline’dan oshdi;
- reset delivery failed/queue stale;
- throttle denial keskin ko‘paydi yoki bucket cleanup lag;
- legal/claim/offer readiness red;
- sitemap canonical 4xx/5xx;
- p75 CWV budget buzildi;
- checkout quote → receipt keskin uzildi;
- certificate random lookup/abuse spike;
- unexpected non-essential cookie yoki third-party request.

500 copy alert pipeline receipt bermaguncha “jamoa xabardor” demaydi. Alert
delivery failure public response’ni fake successga aylantirmaydi.

---

## 10. Roadmap — dependency tartibidagi 36 reviewable kesim

Har kesim alohida PR chegarasi. Schema + full landing redesign + auth + SEO bir
PRga kirmaydi. Security containment oldinda; keyingi phase oldingisining aniq
DoD’iga suyanadi.

### PUB1.0 — P0 containment va bugungi haqiqat

#### PUB1.0a — birinchi kesim: rich content va public URL parity

**Holat — 2026-10-16: kodda, lokal tekshirilgan** (branch
`claude/pub10a-public-rich-content`). `core/rich_content_policy.py`da
`PUBLIC_EDITORIAL_V1` (ikki bosqichli tozalash: script/style/svg kabi
konteynerlar matni bilan ketadi, keyin semantik teglar, exact atributlar,
`safe_url`, faqat ilova media/static rasmi, iframe → “Videoni ochish” havolasi
yoki yo‘q, rad etilgan havola oddiy matn) va `public_plain_text`.
`frontend/public_url_policy.py` navigatsiya (lokal/https/mailto/tel) va
kontent/manba havolasi (+http) siyosati; nav context processor’da bir marta
filtrlanadi. Legacy 11 ta raw `|safe` va V1 public `|sanitize` o‘rniga
`public_rich`; katalog/kurs/pricing/checkout qisqa matni `public_plain`;
`BlogPost.plain_text` ayni profildan. `audit_public_content [--format=json]`
read-only, faqat ID/topilma turi. Global `bleach_tags.sanitize` va private
dars/imtihon consumerlari o‘zgarmagan. Lokal DB auditi: barcha public maydonda
topilma 0. **Ochiq:** §5.8dagi ikkinchi qatlam (save/publish paytida snapshot
tekshiruvi) writer slicelariga (B3.5, Blog/SIT studio) qoladi; navigatsiya
uchun owner host allowlisti yo‘q (userinfo/scheme/host shakli tekshiriladi);
server/production DB auditi va CSP `unsafe-inline` (PUB1.1d) alohida.

**Ish:**

1. `core/rich_content_policy.py`da `PUBLIC_EDITORIAL_V1` named profile va
   malicious corpus. Agar SIT1.0a avval yaratgan bo‘lsa ayni profile reuse.
2. Landing/About/legal/course/**pricing**/Blog/SIT public rich text legacy va V1da
   bitta wrapper orqali. Pricing aniq kiradi: V1
   `templates/frontend_v1/public/subscriptions/pricing.html` hozir
   `Plan.description` (CKEditor maydoni)ni global `sanitize` filtri bilan
   chiqaradi, u esa `iframe` va ixtiyoriy `style`/`class`/`id`ni o‘tkazadi;
   legacy pricing `striptags` bilan qoladi yoki wrapperga o‘tadi. Raw public
   `|safe` yo‘q; private lesson scope’iga tegilmaydi.
3. `frontend/public_url_policy.py`ni V1 `public_url` va legacy navga ulash.
4. Flag ON/OFF bir xil sanitized semantic output; rollback raw kontentga
   qaytmaydi.
5. Existing DB content read-only audit command; destructive rewrite/migration
   yo‘q. Unsafe row IDs/report, raw payload logga chiqmaydi.

**Tegiladigan joylar:** `core/rich_content_policy.py`,
`frontend/public_url_policy.py`, `frontend/templatetags/`, yuqorida sanalgan
legacy/V1 templates (jumladan V1/legacy pricing), `frontend/test_public_content_policy.py`,
SIT/Blog parity testlari. Existing `bleach_tags.py` public wrapper ortida qoladi.

**Test:** script/event/style/iframe/SVG/data/malformed URL; target/rel; semantic
table/list/code; idempotence; legacy/V1/preview/flag ON/OFF; custom nav scheme;
sanitized metadata plain text. Field matrixda har public rich maydon nomma-nom,
shu jumladan `Plan.description`: `iframe`/inline `style` bilan saqlangan plan
V1 pricing’da `PUBLIC_EDITORIAL_V1` rad etadigan markupni chiqarmaydi.

**Tugashi:** executable public markup 0; unsafe nav URL 0; visible safe content
ma’nosi saqlangan; global private rendererlar o‘zgarmagan. Rollback security
policy’ni chetlab o‘tmaydi.

#### PUB1.0b — barcha kanalda bitta registration gate

**Holat — 2026-10-16: kodda, lokal tekshirilgan** (branch
`claude/pub10b-registration-gate`). Inventar: production’da yangi user
yaratadigan joylar — web `RegisterView` (form), `bot/services.py`dagi
`handle_telegram_auth_token` va `register_guest_via_phone`, hamda faqat lokal
`core/demo_seed.py::seed_demo_data`; Mini App yaratmaydi. Yagona qaror
`users/registration_policy.py::can_create_account(channel, request, identity)`
(kanal jadvali, ro‘yxatda yo‘q kanal fail-closed, sintetik email faqat
Telegram kanallarida) va `existing_identity_may_continue(user)`. Deep-link va
telefon yopiq flagda generik `registration_closed` qaytaradi (deep-link sessiyasi
pending qoladi); mavjud faol identity kirish/ulashni davom ettiradi. Topilgan
qo‘shimcha nuqson ham yopildi: faolsizlantirilgan hisob Telegram deep-link orqali
webga kira olardi (`login()` `is_active`ni tekshirmaydi) — endi bot ham, status
endpoint ham rad etadi. Ayni Telegram ID uchun parallel yaratish ikkinchi akkaunt
yoki “server xatosi” o‘rniga g‘olib akkauntga qaytadi. Mini App ayni identity
qoidasini ishlatadi. Inventar testi yangi `create_user` paydo bo‘lsa qizil bo‘ladi.

**Ish:** avval barcha production `CustomUser.create_user` call-site inventari;
so‘ng `users/registration_policy.py` va shared result code. Web RegisterView,
Telegram deep-link auth va `register_guest_via_phone` unga ulanadi. Mini App
hozir account yaratmasa ham new-identity create count `0` parity contracti bilan
qoplanadi. Flag OFFda existing user login mumkin, yangi account barcha adapterda
rad. Synthetic email creation faqat admitted policy’da. Denial generic va
intentni saqlaydi.

**Tegiladigan joylar:** `users/views.py`, `bot/services.py`, Mini App auth,
`core/flags.py`, focused tests. Botdagi transaction/race saqlanadi.

**Test:** call-site inventory completeness; ON/OFF × web/Telegram deep-link/
phone guest/Mini App × new/existing/deactivated identity; parallel Telegram
claim; user/notification count; Mini App new identity create count `0`; no
external call fixture.

**Tugashi:** registration OFFda yangi `CustomUser` 0; existing login regressiyasi
0; adapter policy duplicate’i 0. Bu presentation flag emas, domain gate.

#### PUB1.0c — auth abuse substrate va P0 enforcement

**Holat — 2026-10-16: kodda, lokal tekshirilgan** (branch
`claude/pub10c-auth-throttle`). `users/auth_abuse.py` — HMAC-digest kalit,
`TRUSTED_PROXY_HOPS` bo‘yicha ishonchli IP (Caddy ortida o‘ngdagi XFF), atomik
fixed-window hisoblagich (`users.AuthThrottleBucket`, users0023), doimiy blok
yo‘q, saqlash xatosida fail-open, har yozuvdan keyin bounded cleanup va
`manage.py prune_auth_throttle`. Login (blok tekshiruvi `authenticate`dan oldin),
ro‘yxat, parol tiklash va Telegram init generik `429`+`Retry-After` bilan
enforce qiladi; login/tiklash hisoblagichi hisob mavjudligidan qat’i nazar.
Limit/oynalar `OperationalSettings`da (core0008, rejadagi konservativ default),
owner `Vaqt va limitlar` panelida sabab/tasdiq/`SystemAuditEvent` bilan
o‘zgartiradi; yoqish/o‘chirish `auth_throttle_enforcement` flagida (OFF — faqat
sanaydi). Control Center `auth_throttle` capability’si (high, `/readyz`ga
kirmaydi). PostgreSQL parallel increment testi CI integration ishida.
**Ochiq:** beat/cron jadvali qo‘shilmadi (bounded cleanup yetarli); fixed window
chegara burst’i va session/CAPTCHA layering PUB1.4c’da.

**Ish:** `users/auth_abuse.py`, hashed key derivation, trusted proxy/IP helper,
bounded bucket schema yoki atomic backend, cleanup va Control Center health.
Login/register/reset/Telegram uchun named scope; permanent lockout yo‘q.
**Shu sliceda** login, register, password reset va Telegram auth init
endpointlari decision API’ni chaqiradi **va enforce qiladi** — P0 nuqsoni
(cheksiz parol taxmini, account/DB/email flood) PUB1.4cgacha ochiq qolmaydi.
Threshold/window/retention audited runtime setting (model `default=` + env
fallback + range validator, o‘zgartirish sabab/tasdiq/`SystemAuditEvent` bilan);
konservativ boshlang‘ich defaultlar: login 5 muvaffaqiyatsiz/account/15 daqiqa
va 20/IP/15 daqiqa, register 5/IP/soat, reset 3/account/soat va 10/IP/soat,
Telegram init 10/IP/10 daqiqa. PUB-D13 bu qiymatlarni sozlaydi, enforcementni
kechiktirmaydi. Test fixture qiymatlari product constant emas.

**Tegiladigan joylar:** `users/models.py`, additive migration, service,
`core/runtime_settings*`, Control Center snapshot, cleanup command/task,
login/register/reset view’lari (`users/views.py`, `users/frontend_v1_auth.py`),
Telegram auth init adapteri, tests.

**Test:** exact boundary, rolling/window reset, account+IP layering, spoofed
XFF, concurrency PostgreSQL, SQLite behavior, cleanup rerun, failure mode,
redaction va generic denial. Har to‘rt endpoint uchun: limitdan keyingi urinish
generic `429` + `Retry-After` va auth/DB/email write 0; window tugagach legitimate
user kira oladi; response account mavjudligini oshkor qilmaydi.

**Tugashi:** to‘rt endpoint decision API’ni enforce qiladi; bucket unbounded
o‘smaydi; audit raw identity saqlamaydi. PUB1.4c faqat layering/delay/CAPTCHA
escalation va enumeration polishini qo‘shadi — asosiy throttle shu yerda yoqiladi.

#### PUB1.0d — Telegram init/status/consume method split

**Holat — 2026-10-16: kodda, lokal tekshirilgan** (branch
`claude/pub10d-telegram-method-split`). `users/telegram_auth_service.py` yagona
holat mashinasi: `POST init` (CSRF + PUB1.0c cheklovi; bir brauzerda bitta faol
oqim — oldingisi `expired`; xavfsiz `next` server sessiyasida; javobda
`poll_ms`/`expires_in`), `GET status` (DB/sessiya yozuvi 0, muddat hisoblanadi;
`never_cache`), `POST consume` (CSRF, brauzer kaliti, row lock, TTL, `used` login
oldidan, faolsizlantirilgan hisob rad), `POST cancel` (faqat shu brauzer oqimi).
Eski `GET init`/`GET consume` → 405, holat o‘zgarmaydi. Bot tasdig‘i qatorni
transaction boshida lock qiladi, registration policy o‘sha transaction ichida.
Tozalash: init’da bounded (200) + `manage.py prune_telegram_auth`, saqlash 1 kun.
V1 `login.js` va legacy login/register (umumiy `static/js/telegram-login.js`)
CSRF, server oralig‘i, 15 so‘rovdan keyin 2× backoff, umr chegarasi, consume,
`used` orqali noaniq javobdan tiklanish va cancel bilan. PostgreSQL parallel
consume testi CI integration ishida. **Ochiq:** `RETENTION`/`POLL_INTERVAL_MS`
kod konstantasi (owner jonli kunda o‘zgartirmaydigan protokol qiymati, TTL bilan
bir xil); legacy sahifada cancel tugmasi yo‘q; status/consume’ga alohida
throttle qo‘yilmadi — status hisoblagich yozsa write-free sharti buziladi,
consume esa brauzer kaliti va 256-bit token bilan himoyalangan.

**Ish:** init va consume POST+CSRF; status read-only GET; bot transition shared
service; bir browserda bitta active flow; expiry calculation write-free; purge;
safe signed intent; current one-time/browser-lock invariant saqlanadi. JS no
double-init, backoff, cancel va uncertain recoveryga moslanadi.

**Tegiladigan joylar:** `users/urls.py`, `users/views.py`, yangi
`users/telegram_auth_service.py`, `bot/services.py`, V1/legacy login JS/template,
Telegram security testlari.

**Test:** wrong method 405; missing/bad CSRF 403; status DB/session write 0;
pending/authenticated/expired/used; other browser indistinguishable; parallel
consume bitta login; rate limit; cleanup; safe intent; JS timeout/cancel.

**Tugashi:** safe GET mutation 0; token replay/login 0; current happy path va
fallback ishlaydi. Old GET mutation route temporary compatibility bo‘lsa 405/
explicit migration, state change emas.

#### PUB1.0e — public GETni write-free qilish

**Holat — 2026-10-17: kodda, lokal tekshirilgan** (branch
`claude/pub10e-public-get-write-free`). Inventar (toza va to‘ldirilgan baza,
legacy+V1): yozuvlar faqat `SiteSettings`/`AuthPageSettings`/`LandingPage`
(context processor), `AboutPage`, `LegalPage` (3 sahifa + yordam markazi) va
`BlogHomeSettings` edi. Endi `SingletonModel.current()` (frontend va blog)
qator yoki saqlanmagan default nusxa qaytaradi — public/auth GET va bot o‘qishi
shunga o‘tdi, `load()` faqat tahrir yo‘llarida. Yo‘q huquqiy sahifa
yaratilmaydi: legacy/V1 halol “hali e’lon qilinmagan”, `503` +
`X-Robots-Tag: noindex` + `no-store`; `LegalPage.defaults_for` olib tashlandi.
`core/public_readiness.py` + Control Center `public_content` (high, `/readyz`ga
kirmaydi): yo‘q huquqiy sahifa qizil, PUB1.0e’gacha avtomatik yaratilgan namuna
matn sariq, sozlama qatori yo‘q sariq. Blog maqola hisoblagichi nomlangan
analytics ruxsati (faqat `blog_blogpostread`/`blog_blogpost`), PUB1.0g’da.
**Qaror:** singleton default’lari uchun data migration qo‘shilmadi — kod
default’lari qator yaratilganda ham aynan shu bo‘lardi, yo‘q qator esa Control
Center’da ko‘rinadi (migration test bazasida `objects.create` bilan to‘qnashardi).
**Ochiq:** lokal baza nusxasida uchala huquqiy sahifa eski avtomatik namuna
matnda — productionda ham shunday bo‘lishi ehtimoli katta, owner haqiqiy matn
yozishi kerak (legal revision kesimlari); `LandingPage` default’laridagi
tasdiqlanmagan da’vo (claim gate kesimlari).

**Ish:** `LegalPage.get_or_create`, singleton `load()` va context processordagi
implicit create yo‘llarini read projectionga almashtirish. Required defaults
explicit data migration/seed/setupda; missing row typed unavailable + readiness
red. Blog view counter bu slice’da “analytics intentional write” deb alohida
qoladi va PUB1.0gda hal bo‘ladi.

**Tegiladigan joylar:** `frontend/models.py`, `frontend/context_processors.py`,
`frontend/views.py`, help centerdagi legal loop, data migration va tests.

**Test:** clean DB va populated DBda har public/auth page GETdan oldin/keyin
relevant table snapshot teng; missing legal/status; migration rerun; no 500.

**Tugashi:** analyticsdan tashqari public GET canonical write 0; missing config
fake default sifatida nashr bo‘lmaydi; existing owner content saqlanadi.

#### PUB1.0f — password reset delivery release gate

**Holat — 2026-10-17: kodda, lokal tekshirilgan** (branch
`claude/pub10f-reset-delivery-gate`). Yagona qaror `core/email_delivery.py`
(jim backendlar: console/dummy/locmem/filebased): Control Center email probe,
`users/checks.py` (`check --deploy`, `azurelms.E101`, CI deploy qadamida soxta
`EMAIL_HOST` bilan) va tiklash sahifasi bir xil hisoblaydi. Non-local jim
backendda tiklash **fail-closed**: forma o‘rniga halol xabar, POST `503`, xat va
console’ga tokenli havola yo‘q; lokal console ruxsat. `UzbekPasswordResetForm`
— o‘zbekcha mavzu/oddiy matn/HTML (tashqi rasm yo‘q, `no-referrer`), Django
`get_users` siyosati (noma’lum/faolsiz/parolsiz — xat yo‘q, javob bir xil); SMTP
xatosi javobni o‘zgartirmaydi, `auth.password_reset.delivery_failed` audit
(foydalanuvchi id + xato turi, email/token/IP yo‘q) va email probe 24 soatda
sariq. Tasdiq sahifasi `Referrer-Policy: no-referrer`; legacy “Havola
yuborildi” da’vosi olib tashlandi. **Ochiq:** so‘nggi qayd etilgan AWS relizi
console backendda — deploydan keyin productionda tiklash yopiq turadi, owner
SMTP’ni `deploy/.env`ga yozishi kerak; email verification PUB-D14.

**Ish:** non-local console backendni release/readiness red; Uzbek subject/plain/
HTML templates; generic receipt; token/referrer/log redaction; delivery typed
failure va operator evidence. Reset endpoint PUB1.0c scope’iga ulanadi.

**Tegiladigan joylar:** `core/settings.py`, capability registry/health,
`users/frontend_v1_auth.py`, email templates, deployment check va tests.

**Test:** local console allowed; non-local console rejected; SMTP configured
readiness; known/unknown/inactive/unusable same response; email Uzbek; raw token
log/eventda yo‘q; send exception enumeration leak bermaydi.

**Tugashi:** production-like console fallback “green” emas; user-visible fake
delivery claim yo‘q; current one-use reset regressiyasi 0.

#### PUB1.0g — Blog anonymous tracking containment

**Holat — 2026-10-17: kodda, lokal tekshirilgan** (branch
`claude/pub10g-blog-tracking`). PUB-D6 qarorigacha xavfsiz default: anonim
maqola o‘qish write 0 va cookie 0; eski `blog_visitor` cookie ko‘rilsa
o‘chiriladi va o‘qilmaydi. Kirgan o‘quvchi o‘qishi bir marta sanaladi — faqat
(maqola, foydalanuvchi), IP xeshi va user-agent yozilmaydi; preview/bot 0.
Anonim olqish **login talab qiladi** (`403 auth_required` JSON yoki login’ga
redirect; legacy va V1’da anonimga forma o‘rniga kirish havolasi). Eski data:
`blog/tracking_cleanup.py` + `manage.py purge_blog_read_tracking` (default faqat
hisobot, `--apply` anonim qatorlarni o‘chiradi va IP/UA’ni bo‘shatadi; jami
`view_count`/`clap_count` o‘zgarmaydi) — data o‘chirish owner buyrug‘i bilan,
avtomatik migration emas. Control Center `public_content` eski kuzatuv qatorini
sariq ko‘rsatadi. PUB1.0e write-free testi anonim maqola o‘qishini ham 0 deb
qulfladi. **Ochiq:** ixtiyoriy (admitted) anonim analytics — PUB-D6 qarori va
PUB1.5b/PUB1.8a; maqola sahifasidagi “N ko‘rish” endi asosan kirgan
o‘quvchilarni sanaydi (aggregate, “unique reader” deb talqin qilinmaydi).

**Ish:** Blog page renderini visitor cookie/IP hash/read mutationidan ajratish.
PUB-D6gacha anonymous unique tracking default OFF; authenticated read ham
retention policy’siz yangi PII surface yaratmaydi. Existing aggregate counter
displayi “unique verified readers” deb talqin qilinmaydi. Anonymous clap POST
ham ayni bir yillik cookie yaratadi: owner qarorigacha login talab qiladi yoki
explicit admitted, short-lived essential state/consent contractiga o‘tadi;
yashirin persistent identifier qolmaydi. Preview/bot writes 0.

**Tegiladigan joylar:** `blog/views.py`, `blog/utils.py`, Blog public tests,
feature policy/readiness. Blog comment/clap/studio redesign qilinmaydi.

**BLOG-01 bilan koordinatsiya:** [BLOG-01](BLOG-REFORM-PLAN.md)dagi BLOG1.0a3
(visitor cookie/identity hardening) va read-tracking privacy qarori ayni
`blog/utils.py`/`BlogPostRead` kod yo‘liga tegadi. Qaysi biri oldin bajarilsa
o‘sha implementatsiya qiladi; ikkinchisi uni reuse qilib faqat o‘z test/qabul
shartini qo‘shadi — ikki parallel cookie/tracking siyosati yozilmaydi.

**Test:** no-consent guest detail va clap cookie 0, `BlogPostRead` write 0;
anonymous clap tanlangan policy bo‘yicha login yoki admitted consent/state
contractiga qat’iy mos; existing session/CSRF unaffected; bot/preview 0;
optional admitted analytics ON contract, purge/expiry va redaction.

**Tugashi:** yashirin bir yillik tracking yo‘q; Blog o‘qish va interaction core
flow ishlaydi; Blog domain reformasi BLOG-01da qoladi, PUB1.0g uni qayta
yozmaydi.

### PUB1.1 — route, metadata va response policy poydevori

#### PUB1.1a — public route registry va method/disclosure contracti

**Holat — 2026-10-17: kodda, lokal tekshirilgan** (branch
`claude/pub11a-public-route-registry`). `frontend/public_policy.py` —
`PublicSurfacePolicy` + `CacheClass` (§5.2/§5.3 maqsad qiymatlari), 221 nomli
route’ning hammasi tasniflangan: public 30, ops 5 (healthz, readyz, runtime
theme CSS, CKEditor upload, Telegram webhook; Prometheus ixtiyoriy), private
186 (namespace + aniq ro‘yxat). System check `azurelms.E201` tasniflanmagan,
noma’lum, takroriy, ikki guruhdagi route va siyosat ziddiyatini (sensitive
index/shared cache, canonical’siz sitemap, noma’lum rich profil, mixed shared
cache) rad etadi — yangi route ongli tasniflanmaguncha `check`/test yiqiladi.
`frontend/public_route_audit.py` har route uchun anonim/kirgan/faolsiz GET,
anonim HEAD/POST natijasini o‘lchaydi; `frontend/public_route_snapshot.json` —
data/disclosure dalili, snapshot testi xulq o‘zgarishini ko‘rsatadi
(`UPDATE_PUBLIC_ROUTE_SNAPSHOT=1` bilan ongli yangilanadi). Invariantlar: mehmon
ocha oladigan har route registrda; private route mehmonga hech qachon 2xx
bermaydi (zanjir login’da tugaydi); faolsizlantirilgan hisob aynan mehmon
ko‘rganini ko‘radi; public sahifada boshqa foydalanuvchi email/telefoni va
private dars matni chiqmaydi. `manage.py audit_public_routes` — statik hisobot.
**Dalil sifatida ochiq farqlar (PUB1.1b–d yopadi):** login/register/reset va
sertifikat, Mini App, maintenance/offline’da `noindex` va (ko‘pida) `no-store`
yo‘q; bosh sahifa, about, legal, SIT, Mini App kirishi, offline/maintenance
GET-only bo‘lsa ham POST’ni qabul qiladi.

**Ish:** `PublicSurfacePolicy` registry, inventory system check va har named
route uchun anonymous/authenticated status, redirect, allowed method, data
disclosure snapshot. Ops/non-product allowlist explicit.

**Test:** URL resolver inventory; unknown/duplicate/missing route; GET/HEAD/POST;
anonymous/auth/deactivated; health/upload classification.

**Tugashi:** human public route 100% registrda; registry runtime business logicni
takrorlamaydi; current behavior differences evidence sifatida ko‘rinadi.

#### PUB1.1b — deterministic metadata va canonical origin

**Holat — 2026-10-17: kodda, lokal tekshirilgan** (branch
`claude/pub11b-public-metadata`). `frontend/public_meta.py` — `PublicPageMeta`
(OpenGraph, Twitter, breadcrumb, JSON-LD) va `{% public_meta_tags %}`; har
`<head>` egasi (legacy/V1 base, legacy SIT, sertifikat, xato, Mini App, imtihon)
shu bitta blokni ishlatadi, V1 blog/SIT va legacy SIT’dagi ad-hoc meta olib
tashlandi. `PUBLIC_CANONICAL_ORIGIN` (env; bo‘sh bo‘lsa `https://APP_DOMAIN`,
lokal `http://localhost:8000`; `azurelms.E202` yo‘l/login/serverda http’ni rad
etadi) — canonical, og:url, JSON-LD va blog ulashish havolasi faqat shundan,
`Host` ta’sir qilmaydi. Robots registrdan: sensitive `noindex, nofollow,
noarchive`; holat/xato/private/preview/e’lon qilinmagan `noindex, nofollow`,
canonical va OG’siz; filtr/qidiruv/sahifa so‘rovi `noindex, follow` + toza
canonical (`utm_*` hisobga olinmaydi). Kurs/blog/SIT/huquqiy/bosh/about —
kontekstdagi obyektdan adapter; tavsif oddiy matn ≤160; OG rasm faqat public
media; JSON-LD Course (narx/taklifsiz), BlogPosting, BreadcrumbList.
**Qaror:** tariflar sahifasi PUB1.2 haqqoniy taklif proyeksiyasigacha
`noindex`. PUB1.1a snapshot’idagi “noindex belgisi yo‘q” farqlari yopildi
(qolgani: `no-store`, POST — PUB1.1d). **Ochiq:** `<title>` hali shablon
bloklarida (og:title bilan bir xil manba emas); Telegram status JSON’ida
`X-Robots-Tag` yo‘q (PUB1.1d).

**Ish:** `PublicPageMeta`, configured canonical origin, base template contract,
route-specific title/description/robots/OG/Twitter/breadcrumbs. Blog/SIT faqat
adapter; preview/query/auth/error noindex. Host header canonicalga ta’sir qilmaydi.

**Test:** hostile Host, slash/query/page variants, preview, empty/unpublished,
escaping, long descriptions, image privacy, visible-data metadata equality.

**Tugashi:** indexable page self/object canonical; sensitive page noindex;
duplicate/conflicting tags 0. Legacy/V1 security parity.

#### PUB1.1c — robots va published-only sitemap

**Ish:** root `robots.txt`, `sitemap.xml`, object registry; published/effective
Course/Blog/SIT/legal policy. No secret-route dump; absolute configured URLs;
pagination/filter/preview/token excluded. SIT1.7a register qiladi, second engine
yaratmaydi.

**Test:** published/unpublished/expired/deactivated, 200 URL guarantee, lastmod
truth, canonical equality, query exclusion, 404 object removal, cache/purge.

**Tugashi:** sitemap entrylarning 100%i canonical 200/effective; sensitive URL
0; robots sitemap pointer to‘g‘ri.

#### PUB1.1d — response/cache/security header matrix

**Ish:** `frontend/public_response.py` registrydan cache, Referrer, frame,
nosniff va Permissions headerlarni qo‘llaydi. Hozirgi all-no-store xavfsiz
baseline; shared cache faqat anonymous-invariant projection testidan keyin.
Theme CSS revision-keyed immutable URL/cache.

**Test:** route × anonymous/auth/preview/query/token header matrix; ETag 304;
CSRF/user/preview leak; publish/rollback invalidation; flag OFF parity.

**Tugashi:** sensitive no-store 100%; shared response user/CSRF/cookiega bog‘liq
emas; stale publish rollback testli. Global CSP weakening yo‘q.

### PUB1.2 — landing, trust va content readiness

#### PUB1.2a — claim evidence va readiness foundation

**Ish:** additive `PublicClaimEvidence`, digest/freshness/approval service,
testimonial consent/order maydonlari, read-only audit command va Control Center
snapshot. Existing seed/default rows verified qilinmaydi; missing/expired claim
publicdan yashirin.

**Test:** edit invalidates digest; expiry boundary; actor/reason; testimonial
consent/revoke; concurrent approval; audit rerun/no mutation; legacy/V1 equality.

**Tugashi:** displayed governed claims evidence coverage 100%; `2400+/94%/4.9`
va award defaulti dalilsiz ko‘rinmaydi. Migration production fakt to‘qimaydi.

#### PUB1.2b — deterministic landing/About selectors

**Ish:** renderer-specific read projection; unused `recent_students` va ortiqcha
queries olib tashlash; testimonials explicit order; published-only team/stats;
stable course cards; fallback claim emas. Query budgets.

**Tegiladigan joylar:** yangi `frontend/public_content.py`, `frontend/views.py`,
About/home templates/tests.

**Test:** 0/1/many content, deterministic repeated GET body, query count,
inactive/unverified exclusion, no user query/PII, flag ON/OFF.

**Tugashi:** same revision same HTML/projection; random sampling 0; unused PII
query 0; empty state truthful.

#### PUB1.2c — B3.5 writer/readiness integratsiyasi

**Ish:** B3.5 existing `LandingPage/LandingProcessStep` writeri claim readiness,
safe URL/rich content va render preview bilan ulanadi. About/team/stat/testimonial/
nav/auth copy uchun minimal public content workspace gaplari inventory qilinadi;
parallel CMS/page builder yo‘q. Direct admin service yoki read-only.

**Test:** draft publicga chiqmaydi; preview write/tracking/CTA 0; reason/
confirmation/audit/CAS; publish/rollback; unsafe claim/media denied; legacy/V1.

**Tugashi:** owner ko‘rgan preview = publish projection; old revision rollback;
other section/shared media o‘zgarmaydi. B3.5 ownership takrorlanmagan.

#### PUB1.2d — public shell va landing task-first UX

**Ish:** owner qaroridagi IA; grouped header/footer; hardcoded/duplicate SIT va
misrouted certificate linklarni tuzatish; configured contact/help. Landing first
fold, how-it-works, live course/offer cards, verified trust va final CTA. No-JS
va empty/degraded states.

**Test:** real/empty content, nav active state, unique accessible names, 320–
1440, long copy, keyboard/menu, footer landmarks, unsafe/missing contact, claim0.

**Tugashi:** landingdan catalogga clear primary route; dead link/dead-end/fake
claim 0; mobile/desktop semantik nav parity.

### PUB1.3 — catalog, course offer va intent continuity

#### PUB1.3a — bounded catalog query contracti

**Ish:** plain searchable projection yoki sanitized text, q length/normalization,
allowed level/sort, stable tie-breaker, filter validation, pagination/accessibility,
SEO clean query policy va optional abuse budget.

**Test:** max/empty/Unicode/control/HTML query; unknown/multiple filters;
stable pages; SQL/query budget; no-JS; canonical/noindex; back URL preservation.

**Tugashi:** unbounded rich-body `icontains` yo‘q; results deterministic; zero
state recovery; query explosion indexga kirmaydi.

#### PUB1.3b — canonical `PublicOfferProjection`

**Ish:** Course + active Cohort + purchase Plans read-only projection, availability
reason taxonomy va source revision. Pricing pack/A4 semantics reuse; new price
model yo‘q. Missing field omitted, guessed value yo‘q.

**Test:** active/inactive/full/future/no cohort; available/unavailable plan;
price/period/included equality with checkout; permissions; query count; timezone.

**Tugashi:** card/detail qaror factlari canonical; checkout mismatch 0 fixture;
offer render GET write 0.

#### PUB1.3c — course detail va card islohoti

**Ish:** first-fold offer, outcome/prerequisite/workload, curriculum/sample,
instructor, assessment/certificate, included/excluded, real support; responsive
media/rich text. `0 exam` va empty facts hidden; CTA typed availability bilan.

**Test:** complete/partial/empty course; 0 counts; long names; unavailable;
rich-content attacks; unique link names; metadata/JSON-LD visible equality.

**Tugashi:** user checkoutdan oldin qaror uchun mavjud barcha canonical factni
ko‘radi; unsupported claim yoki blank badge 0.

#### PUB1.3d — signed intent va exact auth return

**Ish:** typed signed `PublicIntent`; course detail login va direct register,
onboarding, registration closed va checkout resolver. Existing generic safe-next
saqlanadi. Expiry/invalid/replay recovery va telemetry receipt.

**Test:** course → login/register → onboarding → exact checkout; plan optional;
tamper/expired/wrong type/deleted course/external URL/backslash; session rotation;
double click; availability mid-flow close.

**Tugashi:** eligible auth intent loss 0; client token price/access authority 0;
closed offer duplicate enrollment/receipt 0.

### PUB1.4 — pricing va accessible auth

#### PUB1.4a — pricing funnel va truthful comparison

**Dependency/stop gate:** current `subscriptions.Plan` price, description,
availability va featurelarni beradi, lekin renewal/cancellation/refund policy
contracti yo‘q. A4 owneri avval canonical offer/legal-copy schema yoki service
beradi. U yo‘q bo‘lsa PUBLIC yangi business field yoki policy ixtiro qilmaydi,
sotuv/readiness red qoladi va implementation shu qismda to‘xtaydi.

**Ish:** PUB-D1 course-first default; A4 taqdim etgan canonical plan fields,
billing/renewal/cancel/refund/manual approval copy, included/excluded; popular/
discount evidence gate. CTA course contextga mos; empty/unavailable recovery.

**Test:** plans 0/1/3, unavailable, missing legal copy, evidence expiry, guest/
auth, pricing-to-course-to-checkout intent, checkout quote equality.

**Tugashi:** generic register CTA yo‘q; plan/course ambiguity 0; hidden fee yoki
unsupported “popular/discount” 0.

#### PUB1.4b — UX-04 auth error va form clarity porti

**Ish:** login/register/reset forms: single summary, field association, first
invalid focus, preserved safe values, password no echo, autocomplete/inputmode,
44px internal target, legal/context/footer links. Canonical validators qoladi;
fake strength meter yo‘q.

**Test:** required/email/duplicate/mismatch/weak/non-field/CSRF; JS/no-JS;
screen reader DOM; keyboard/mobile zoom; safe intent banner; long Uzbek text.

**Tugashi:** har xato bir marta; first invalid focus; successful recovery;
password/secret render yoki logda 0. UX-04 runtime bandi evidence bilan yangilanadi.

#### PUB1.4c — login/register/reset full throttle va enumeration

**Ish:** PUB1.0cda yoqilgan asosiy throttle ustiga account/IP/session
layering, generic response va bounded delay; PUB1.0c qamramagan qolgan auth
adapterlari ham shu servicega ulanadi. Registration duplicate email copy/
flow email capability va PUB-D14ga mos; CAPTCHA faqat risk escalation va
accessible alternative bilan.

**Test:** known/unknown/duplicate, distributed account attempts, one-IP many
accounts, Retry-After, legitimate recovery, no hard permanent lockout, race,
timing contract tolerant range va redaction.

**Tugashi:** cheap unlimited auth/email/DB flood yo‘q; enumeration-visible
message/status farqi yo‘q; owner thresholds auditli.

#### PUB1.4d — password reset end-to-end delivery

**Ish:** PUB1.0f substrate ustida real delivery receipt/monitoring, Uzbek email,
known/unknown generic UI, expired/reused recovery, optional session revoke policy.
Production smoke fake account/email bilan; real user address ishlatilmaydi.

**Test:** subject/plain/HTML absolute canonical URL; token TTL/use; send error;
worker/provider outage; no-referrer; existing sessions PUB-D14 policy bo‘yicha.

**Tugashi:** production reset mail olinadi va token ishlaydi; delivery evidence
bor; console/log leak 0.

#### PUB1.4e — Telegram auth inclusive UX

**Ish:** method-split backend uchun explicit privacy/context copy, QR/deep-link,
countdown, pending/authenticated/expired/uncertain/cancel, manual check, intended
destination. Password/email alternative doim mavjud.

**Test:** desktop/mobile, popup blocked, Telegram app yo‘q, network loss,
poll backoff, duplicate click, expiry, other browser, reduced motion/AT/no-JS
fallback, registration OFF.

**Tugashi:** duplicate init/login 0; user nima bo‘layotganini biladi; safe intent
saqlanadi; Telegram yagona accessible auth yo‘li emas.

### PUB1.5 — legal, cookie va certificate privacy

#### PUB1.5a — immutable legal revision foundation

**Ish:** expand-only LegalDocument/Revision yoki equivalent, backfill current
rowsni draft/unapproved sifatida, lifecycle service, effective selector, preview,
publish/rollback/audit/CAS. Owner/legal matnni o‘zi beradi/tasdiqlaydi.

**Test:** one effective revision, schedule boundary, concurrent publish,
rollback, missing 503, sanitizer, preview noindex/no-store/write0, backfill
dry-run/rerun/readback.

**Tugashi:** public legal page version/effective source’dan; GET create 0;
generic seed approved bo‘lmagan; old row lost 0.

#### PUB1.5b — activity notice, consent va cookie inventory

**Ish:** register/reset/Telegram/blog/payment activity notice map; generated
cookie inventory; optional-cookie engine faqat PUB-D6 admit qilsa. Accept/Reject/
Settings parity, withdrawal va retention/purge. Theme/session/CSRF essential
classification evidence bilan.

**Test:** first visit, accept/reject/customize/withdraw, no-JS, keyboard/focus,
CLS, third-party blocked pre-consent, revision receipt, expiry/purge, cross-device
claim qilinmasligi.

**Tugashi:** active cookies inventory coverage 100%; non-essential pre-consent
request 0; “KVKK compliant” overclaim yo‘q.

#### PUB1.5c — certificate opaque token va minimal verifier

**Ish:** owner PUB-D4/PUB-D15 qaroriga mos additive fields, random token,
status/revoke, minimal selector/template, new URL, noindex/noarchive/no-referrer/
no-store, throttle. Token logs redacted.

**Test:** entropy/unique collision retry, hidden/verifiable/revoked, minimal
fields, other relations query 0, random/malformed, brute budget, metadata/cache,
print/accessibility.

**Tugashi:** new public URL embedded user/course IDga tayanmaydi; policydan
ortiq PII/academic detail 0; revoke truthful.

#### PUB1.5d — appendix authorization va legacy certificate migration

**Ish:** appendix own learner/authorized staff; scoped share token faqat admitted.
Resumable backfill, legacy alias telemetry/grace/expiry, learner certificate link
update va rollback readback. Data deletion yo‘q.

**Test:** anonymous/owner/other/staff role matrix; legacy valid/random; backfill
resume/rerun/collision; old print link; alias expiry; flag OFF/new fields readback.

**Tugashi:** anonymous appendix exposure policy violation 0; migration counts/
hash; existing learner hujjati yo‘qolmaydi.

### PUB1.6 — Blog va SIT public adapterlari

#### PUB1.6a — Blog shared public contracti, domain redesignsiz

**Ish:** shared meta/canonical/cache/rich-content/URL/privacy, list query bounds,
author/date/source presentation, accessible cards/pagination va truthful CTA.
Comment/clap/studio data model/lifecycle o‘zgarmaydi; rejected plan yo‘q.

**Test:** published/draft/preview, search/tag/page/back, tracking OFF, comment
login return/CSRF, no-JS, metadata/sitemap, unsafe content, query budget.

**Tugashi:** Blog public security/SEO/shell parity; domain feature qo‘shilmagan.

#### PUB1.6b — SIT shared infrastructure adapteri

**Ish:** SIT-01 effective selectors public registry/meta/sitemap/cache/media
contractiga register. PUBLIC SIT source/version/inquiry/AI logicini yozmaydi.
SIT1.7a ikkinchi sitemap/cache engine yaratmaydi.

**Test:** published/stale/unpublished/preview, canonical/source metadata,
filter/detail/back, no duplicate registry entry, public/SIT flag combinations.

**Tugashi:** bitta public infra; SIT domain truth SIT-01da; dead generic help/AI
CTA SIT roadmap gate’iga mos.

### PUB1.7 — system states, performance va accessibility

#### PUB1.7a — truthful self-contained system states

**Ish:** 403/404/500/maintenance/offline runtime port; local critical assets;
noindex/no-store; method-safe retry; status code/Retry-After; 500 fake alert copy
olib tashlash; `/healthz` va `/readyz` external payloadlari coarse, owner detail
private. Orchestrator uchun zarur method/status semantics saqlanadi.

**Test:** each status, dependency failure, external network blocked, GET vs POST
retry, PII/body absence, `/healthz` va `/readyz` anonymous payload/method/cache
snapshotlari, cache/robots, focus/keyboard/light-dark/forced colors.

**Tugashi:** outage page third partyga bog‘liq emas; fake operational claim 0;
blind POST replay 0; probe orchestration contract saqlangan.

#### PUB1.7b — route bundles, media va performance budgets

**Ish:** public/auth/learning CSS/JS route split; inline dependency removal;
self-host critical font/icon; image renditions/dimensions/srcset; video poster/
caption policy; query/asset lab baseline va cache revision.

**Test:** manifest/static resolution, CSP report-only, image fallbacks, LCP not
lazy, CLS reservation, Save-Data/reduced motion, blocked JS/CSS/media, compressed
budget, Lighthouse lab. RUM hali alohida.

**Tugashi:** unused auth/learning bundle publicda 0; broken media dead-end 0;
budget regression CI’da signal; CSPni weakening yo‘q.

#### PUB1.7c — WCAG/no-JS/native acceptance

**Ish:** section 6.9 matrix; current V1 tap-target test; axe/HTML/static probes;
manual evidence template; owner/native qurilma bandlarini truthful holatda qayd.

**Test:** 28 E2E ssenariy ichidagi accessibility subset; NVDA/VoiceOver/TalkBack
evidence imkoniga qarab; keyboard/zoom/reflow/text spacing/forced colors/no-JS.

**Tugashi:** automated critical/serious 0; core keyboard/no-JS 100%; overflow 0;
native/AT bajarilmagan bo‘lsa “PASS” emas, explicit OPEN.

### PUB1.8 — measurement, pilot va production release

#### PUB1.8a — privacy-safe funnel baseline

**Ish:** allowlisted server-side events, idempotent transition receipts, short
opaque journey correlation, retention/redaction; dashboard funnel definitions.
Non-essential client analytics PUB-D6siz yo‘q.

**Test:** payload schema, PII/token/search exclusion, refresh/retry dedupe,
concurrent auth/receipt, retention purge, event failure business transactionni
buzmasligi.

**Tugashi:** KPI numerator/denominator reproducible; telemetry PII 0; 2–4 hafta
baseline olish mumkin. A/B hali yo‘q.

#### PUB1.8b — content/data/release readiness gate

**Ish:** legal, claims, testimonials, course/cohort/plan, support, email,
certificate, sitemap/media va stale evidence snapshot; `system_audit`/Control
Center/management command bir xil selector. Real content owner sign-off.

**Test:** each red/yellow/green fixture, missing data, stale evidence, broken
media, console mail, no live offer; anonymous healthz/readyz detail leak 0.

**Tugashi:** pilot only all required green; red item UI’da yashirishning o‘zi
release proofi emas; owner decision receipt mavjud.

#### PUB1.8c — staged rollout, rollback va final evidence

**Ish:** shadow policy/meta → owner preview → internal/small canary → public;
cache purge/readback, flag combinations, schema backward compatibility, backup/
restore rehearsal, RUM/error/conversion watch va rollback drill.

**Test:** old/new renderer and flags matrix; real browser engines/devices;
production-like `check --deploy`; migrations/backfill; cache/CDN; full Django,
Node/static, broken link/crawl, security scan va dependency gate.

**Tugashi:** owner-approved real journey, rollback tested, evidence document,
required CI green, no unresolved P0/P1, production state separately recorded.

---

## 11. Feature flag, setting va rollback contracti

### 11.1 Flag ortiga yashirilmaydigan himoyalar

Quyidagilar har doim amal qiladi:

- public rich-content/URL sanitizer va renderer parity;
- shared registration gate;
- safe HTTP method + CSRF;
- safe-next/signed-intent verification;
- auth/token/certificate authorization va secret redaction;
- preview permission va sensitive `no-store/noindex`;
- non-local console reset delivery release failure;
- public GET purity;
- claim yo‘q bo‘lsa fake fallback bermaslik.

`frontend_v1_public=OFF` yoki yangi UI rollback bularni qaytarmaydi.

### 11.2 Tavsiya etilgan rollout flaglari

Flaglar faqat presentation/cutover uchun `core/flags.py` registrida default OFF:

| Flag | Nima tanlaydi | OFF fallback |
|---|---|---|
| `public_response_policy_v1` | New metadata/route response adapter | Existing renderer + unconditional safety headers |
| `public_acquisition_v1` | New landing/catalog/course/pricing/intent presentation | Existing V1 presentation, safe registration/sanitizer qoladi |
| `public_legal_revisions_v1` | Immutable effective legal reader | Existing approved content read-only; missing fake create yo‘q |
| `public_certificate_verifier_v1` | Opaque-token minimal verifier | Existing route containment/noindex; owner-approved transition |
| `public_telemetry_v1` | First-party allowlisted funnel events | Events yozilmaydi; product flow ishlaydi |
| `public_optional_cookies_v1` | Admitted non-essential consent engine | Optional cookie/script OFF |

`public_registration` account-creation domain gate bo‘lib qoladi; renderer yoki
waitlist flagi sifatida ishlatilmaydi. SIT/Blog/Messenger domain flaglari o‘z
ownerida.

### 11.3 Audited operational settings

Quyidagilar code constant yoki `.env` bilan yashirin almashtirilmaydi:

- auth scope window/limit/cooldown/retention;
- signed intent TTL;
- anonymous public shared-cache TTL va stale policy;
- legal/claim freshness defaultlari;
- support contact/hours va claimed response expectation;
- optional telemetry retention;
- certificate legacy alias grace;
- maintenance `Retry-After`.

Existing runtime setting service patterni: owner permission, reason,
confirmation, revision/CAS, `SystemAuditEvent`, safe min/max va no-op detection.
Secret/provider credential bu jadvalga plain text kirmaydi.

### 11.4 Rollback tartibi

1. Mutation/event emissionni to‘xtatish: telemetry/optional cookies OFF.
2. Shared cache OFF, purge va `must-revalidate/no-store` conservative policy.
3. New acquisition/metadata renderer OFF; unconditional sanitizer/auth/policy
   saqlanadi.
4. New legal/certificate writer OFF; dual-read safe projection va old data
   readback. Schema/columns darhol o‘chirilmaydi.
5. Failed backfill resume/quarantine; destructive reverse migration yo‘q.
6. Old/new response snapshot, row counts/hash va auth/checkout smoke.
7. Incident/evidence marinebook va stage hujjatida.

Rollback “old raw `safe`ga qaytish”, Telegram GET loginini ochish, registration
flagni botda chetlab o‘tish yoki sensitive cache’ni public qilish emas.

---

## 12. Test va qabul matrixi

### 12.1 Majburiy avtomatik contractlar

- route inventory: anonymous/auth/deactivated status, method, redirect, data;
- public GET canonical/domain write0; intentional analytics va framework
  security bookkeeping named allowlist/disclosure fixture;
- sanitizer/URL malicious corpus, legacy/V1/preview/flag parity;
- registration call-site inventory; ON/OFF web/Telegram deep-link/phone guest/
  Mini App parity;
- auth abuse boundary/concurrency/cleanup/redaction;
- Telegram init/status/consume CSRF/method/TTL/one-use/browser/intent;
- reset enumeration/delivery/language/referrer/reuse/production backend;
- signed intent tamper/expiry/deleted offer/mid-flow change;
- offer projection = checkout canonical price/availability fixture;
- claim digest/freshness/approval/testimonial consent;
- legal lifecycle/effective revision/preview/rollback/acceptance separation;
- certificate role/token/revoke/legacy alias/appendix;
- metadata/canonical/robots/sitemap/structured-data visible equality;
- response/cache/security headers va cross-user leak;
- Blog tracking OFF/detail+clap cookie inventory; SIT shared registry;
- error/status code/copy/local assets/noindex/no-store/safe retry;
- query count/asset bytes/image dimensions/static manifest;
- telemetry schema/idempotency/no-PII/retention;
- flags ON/OFF, migration/backfill rerun va rollback readback.

### 12.2 Browser va end-to-end ssenariylar

| # | Ssenariy | Qabul mezoni |
|---|---|---|
| 1 | Home → filter → course → direct register → onboarding | Ayni course checkoutga qaytadi |
| 2 | Course → existing-user login | Exact intended checkout, safe destination |
| 3 | Pricing → course → plan → auth | Canonical plan/course revalidated; raw ID authority emas |
| 4 | `public_registration=OFF` | Web/Telegram deep-link/phone guest/Mini App user yaratmaydi; login/real help bor |
| 5 | Offer auth oralig‘ida yopiladi | Enrollment/receipt 0; typed unavailable + real alternative |
| 6 | Invalid register/login | Xato bir marta; summary; first invalid focus; password echo 0 |
| 7 | Reset known/unknown/inactive/unusable | Bir xil receipt; Uzbek outbound mail |
| 8 | Reset token reused/expired | Form emas, yangi request recovery |
| 9 | Telegram pending/network uncertain/cancel/expiry | Duplicate init/login 0; intent saqlanadi |
| 10 | Empty course/plan/Blog/SIT | Fake data/loop 0; real forward/help |
| 11 | Legal takroriy GET | DB write 0; effective version/date |
| 12 | Draft/preview | Guest 404; owner private/noindex; tracking/CTA mutation 0 |
| 13 | Blog/SIT filter → detail → back | Query state saqlanadi; unsafe return rad |
| 14 | Certificate valid/random/revoked | Minimal policy; random generic; appendix auth |
| 15 | 403 | Login faqat yordam bersa; aks holda safe forward |
| 16 | 404 | Home/catalog/search recovery; status 404 |
| 17 | 500 | PII/body/fake “xabardor” 0; status 500 |
| 18 | Offline/maintenance | Remote asset 0; GET-safe retry; blind POST replay 0 |
| 19 | 320/390/640/768/1024/1440, light/dark | Overflow 0; primary CTA ko‘rinadi; long copy |
| 20 | 200%/400% zoom va keyboard-only | Focus visible/not obscured; content loss 0 |
| 21 | NVDA/VoiceOver/TalkBack | Unique names, heading/landmark/status tushunarli |
| 22 | JS disabled | Nav/filter/auth/reset/comment core flow ishlaydi |
| 23 | Slow/failed media/assets, Save-Data/reduced-motion | Meaning/CTA qoladi; CLS budget |
| 24 | SEO crawl | Canonical/sitemap faqat published effective; sensitive excluded |
| 25 | Public cache | User/CSRF/preview leak 0; publish purge/readback |
| 26 | Telemetry refresh/retry | Transition bir marta; PII 0 |
| 27 | Owner edit/preview/publish/rollback | Reason/revision, no-write preview, exact restore |
| 28 | Flag OFF rollback va dependency failure | Canonical data saqlanadi; fake success/content 0 |

### 12.3 Performance va accessibility gate

- Field/RUM: p75 mobile va desktop LCP/INP/CLS; segment sample size ko‘rsatiladi.
- Lab: Lighthouse/WebPageTest yoki repo-equivalent cold/warm, throttled profile;
  TBT faqat INP proxy deb label.
- Per-route HTML TTFB, query count/p95, compressed CSS/JS/image bytes.
- Axe critical/serious 0, HTML validation, link/crawl check.
- Manual keyboard, zoom/reflow, screen reader va native device evidence. Evidence
  olinmagan platforma `NOT TESTED`, taxminiy PASS emas.

### 12.4 Test buyruqlari

Har agent safe env bilan:

```powershell
$env:AZURELMS_SKIP_ENV_FILE='1'
$env:APP_ENV='local'
$env:LOCAL_USE_REMOTE_SERVICES='False'
$env:GEMINI_API_KEY=''
$env:TELEGRAM_BOT_TOKEN=''

venv\Scripts\python.exe manage.py check
venv\Scripts\python.exe manage.py makemigrations --check
venv\Scripts\python.exe manage.py test frontend.test_public_v1 users.test_frontend_v1_auth users.test_register_remembers_where_you_were_going users.test_telegram_auth_security courses.test_frontend_v1_certificates cohorts.test_frontend_v1_checkout --noinput
node --test tests/frontend_v1/*.test.mjs
venv\Scripts\python.exe .tools/docs-sync/verify_docs.py
git diff --check
```

Kesimga tegishli yangi focused file va cross-app testlar yuqoridagiga qo‘shiladi.
Concurrency/schema uchun PostgreSQL required CI. Final stage full Django + full
Node/static suite + production-like `check --deploy`; real Gemini/Telegram key,
real user email yoki production mutation test uchun ishlatilmaydi.

---

## 13. Keyingi agent uchun bajarish protokoli

### 13.1 Ishni boshlashdan oldin

1. `AGENTS.md`, `rules-for-agents.md`, marinebook top 3–5 va joriy README’ni
   to‘liq o‘qi; `git status/log/branch`ni tekshir.
2. `PUBLIC-REFORM-PLAN.md`dagi eng yuqoridagi unfinished bitta slice’ni tanla.
3. Cross-plan ownerni tekshir: rich content SIT1.0a bilan, landing writer B3.5
   bilan, offer A4/pricing bilan, SIT adapter SIT-01 bilan.
4. Current behaviorni focused failing regression test yoki read-only auditor
   bilan isbotla. Production data, legal text yoki claim taxmin qilma.
5. Ochiq owner qarori slice’ni materially o‘zgartirsa safe defaultda to‘xta;
   qolgan mustaqil containmentni davom ettir.

### 13.2 Har slice ish tartibi

1. Contract va test first; katta visual patch emas.
2. Schema bo‘lsa expand-only, migration va backfill alohida; dry-run/resume/
   rerun/count/hash/quarantine.
3. Mutation service orqali; view/form/template/admin/bot duplicate rule yozmaydi.
4. GET canonical/domain write-free; framework security bookkeeping faqat named
   allowlistda; preview side-effect0; security rollback-independent.
5. Failure path va typed error happy path bilan bir PRda.
6. Safe env focused + cross-app + check + migration check + diff-check.
7. Browser/AT/native talab bo‘lsa evidence yoki explicit OPEN.
8. Reja statusini faqat haqiqiy dalil bilan yangila; tarixiy testni yangi deb
   ko‘rsatma.
9. Test → commit → marinebook → push → PR → required CI → repo qoidasi bo‘yicha
   merge/cleanup. Begona branch/worktree/main push yo‘q.

### 13.3 Tavsiya etilgan PR navbati

```text
PUB1.0a → PUB1.0b → PUB1.0c → PUB1.0d → PUB1.0e → PUB1.0f → PUB1.0g
  → PUB1.1a → PUB1.1b → PUB1.1c → PUB1.1d
  → PUB1.2a → PUB1.2b → PUB1.2c → PUB1.2d
  → PUB1.3a → PUB1.3b → PUB1.3c → PUB1.3d
  → PUB1.4a → PUB1.4b → PUB1.4c → PUB1.4d → PUB1.4e
  → PUB1.5a → PUB1.5b → PUB1.5c → PUB1.5d
  → PUB1.6a → PUB1.6b
  → PUB1.7a → PUB1.7b → PUB1.7c
  → PUB1.8a → PUB1.8b → PUB1.8c
```

`PUB1.0a` va `SIT1.0a`dan qaysi biri birinchi tushsa shared sanitizer
substrate’iga owner; ikkinchisi ayni profile/test corpusni reuse qiladi.
`PUB1.2c` B3.5 writer bilan bir contractda. `PUB1.6b` SIT1.7a bilan bir public
infra’da: SIT1.7a `PUB1.1a–d`ni reuse qiladi; PUBLIC poydevori hali bo‘lmasa,
alohida SIT engine emas, shared primitive PR birinchi tushadi. Bir sessiyada
bitta canonical slice.

### 13.4 Stop va eskalatsiya shartlari

Agent to‘xtab ownerga aniq dalil bilan xabar beradi, agar:

- destructive migration/data purge yoki existing public URLni birdan o‘chirish;
- legal/privacy/certificate disclosure yoki price/refund business qarori;
- production content/claimni verified qilish uchun manba yo‘q;
- SMTP/analytics/CDN/provider/production mutation authority kerak;
- parallel plan bir xil schema/servicega allaqachon tegayotgan bo‘lsa;
- required CI, dependency/security gate yoki PostgreSQL concurrency yiqilsa;
- rollback old renderer orqali xavfsizlikni pasaytirsa;
- native/AT/owner acceptance o‘rniga synthetic evidence bilan PASS yozish talab
  qilinsa.

Failed security gate `--admin`, allowlist/ack yoki required checkni o‘chirish
bilan aylanib o‘tilmaydi.

### 13.5 Stage evidence formati

Har yakunlangan slice uchun alohida stage hujjat shart emas; ammo major phase
yoki rollout quyidagini yozadi:

```text
Holat va commit/PR
Qamrov va qamrovga kirmaganlar
Oldingi nuqsonni isbotlagan test
Canonical state/service/route o‘zgarishi
Migration/backfill count/hash/quarantine
Focused/cross-app/full test exact command va natija
Browser/viewport/AT/native evidence
Security/privacy/cache/SEO/claim checks
Flag/setting holati va rollback readback
Production o‘zgardimi yoki yo‘qmi
Ochiq risk va keyingi exact slice
```

---

## 14. Ochiq owner va legal qarorlari

| ID | Qaror | Xavfsiz default | Qaysi slice bloklanadi |
|---|---|---|---|
| PUB-D1 | Primary funnel course-firstmi yoki plan-first? | Course-first; global pricing kurs tanlashga olib boradi | PUB1.4a plan-first varianti |
| PUB-D2 | Registration yopiq paytda waitlist/support bormi? | Faqat existing login va configured real contact; lead collection yo‘q | PUB1.2d/PUB1.4 UX copy |
| PUB-D3 | Marketing claimni kim va qancha muddatga tasdiqlaydi? | Evidence/digest/expiry yo‘q claim yashirin | PUB1.2a production publish |
| PUB-D4 | Certificate verifier public qoladimi, qanday minimal fields? | Current route noindex/no-store; new verifier owner qarorisiz rollout yo‘q; appendixni kengaytirish yo‘q | PUB1.5c–d |
| PUB-D5 | Privacy/Terms legal approver, version va effective date? | Generic text approved deb ko‘rsatilmaydi; missing readiness red | PUB1.5a production |
| PUB-D6 | First-party analytics/cookie purpose, legal basis, retention? | Non-essential tracking OFF | PUB1.5b/PUB1.8a optional analytics |
| PUB-D7 | Real support channel, hours va response expectation? | Faqat configured contact; SLA claim yo‘q | Landing/course/error help copy |
| PUB-D8 | Public course’da qaysi schedule/seat/price faktlari chiqadi? | Canonical mavjud factlar; unknown hidden/“aniqlanmoqda” | PUB1.3b–c |
| PUB-D9 | Testimonial identity/consent scope? | Consent/evidence yo‘q bo‘lsa yashirin | PUB1.2a–d |
| PUB-D10 | CDN/shared HTML cache targeti? | Browser revalidate, shared cache OFF | PUB1.1d/PUB1.7b production |
| PUB-D11 | External font/icon/video/analytics providerlar? | Critical asset self-hosted; optional third party OFF | PUB1.7b |
| PUB-D12 | Public tillar: hozir faqat Uzbekmi? | Uzbek UI; Turkish phrase `lang=tr`; hidden locale variant yo‘q | Hreflang/multilingual keyingi admission |
| PUB-D13 | Auth rate windows/limits/retention va trusted proxy? | PUB1.0c konservativ default bilan enforce qiladi; owner/security qiymatni audited setting orqali sozlaydi | Qiymat tuningi; PUB1.0c enforcementni bloklamaydi |
| PUB-D14 | Email verification va password-change session revoke siyosati? | Mandatory verification qo‘shilmaydi; reset delivery fail-closed; Django safe baseline | PUB1.4c–d advanced policy |
| PUB-D15 | Certificate full/abbreviated name, revocation copy va legacy grace? | Minimal disclosure, raw reason private, destructive cutover yo‘q | PUB1.5c–d |
| PUB-D16 | SIT primary navda alohida top-level entrymi? | Existing public access saqlanadi; nav duplication/hardcode yo‘q | PUB1.2d final IA |
| PUB-D17 | Real pricing cancellation/refund/subscription copy? | Agent ixtiro qilmaydi; missing policy visible “owner approval required” readiness red | PUB1.4a production |

PUB-D1/D3/D4/D5/D6/D15/D17 production rolloutni bloklashi mumkin, lekin
PUB1.0a–f kabi independent containmentni to‘xtatmaydi. PUB-D13 faqat throttle
qiymatlarini sozlaydi; PUB1.0c enforcementi uni kutmaydi.

---

## 15. PUBLIC-01 Definition of Done

PUBLIC-01 faqat quyidagilar dalil bilan yopilganda tugagan hisoblanadi:

- public route/method/index/cache/disclosure inventory 100%; ops endpoints aniq;
- legacy/V1/preview/flag yo‘llarida executable stored rich content va unsafe URL 0;
- registration OFF inventardagi barcha production account-creation adapterida,
  jumladan Telegram deep-link va phone guest yo‘lida account yaratmaydi; Mini
  App new identity create count `0`;
- login/register/reset/Telegram abuse bounded, GET canonical/domain side-effect
  free; framework reset/CSRF bookkeeping allowlistli; CSRF va one-time token
  invariantlari yashil;
- non-local reset email real capability gate’idan o‘tgan, Uzbek delivery testli;
- analytics va named framework-security allowlistidan tashqari public GET
  canonical/domain mutation 0; tracking, jumladan Blog detail/clap, notice/
  consent/retention qaroriga mos;
- displayed claim va testimonial evidence/consent/freshness coverage 100%;
- legal pages owner/legal-approved effective revision, preview/audit/rollbackli;
- course/pricing factlari canonical offerdan; auth intent continuity 100%;
- certificate public disclosure owner qaroriga mos, opaque token/revoke va
  appendix authorization testli;
- canonical/meta/robots/sitemap faqat effective published data; sensitive URL 0;
- cache cross-user/preview/CSRF leak 0; publish/rollback purge/readback testli;
- Blog shared public scope yaxshilangan, Blog domain redesigni BLOG-01ga qoldirilgan;
- SIT shared infra ishlatadi, SIT domain truthini duplicate qilmaydi;
- error/maintenance/offline truthful, self-contained, correct status/noindex;
- WCAG/no-JS/responsive/performance gate dalilli; native/AT ochiq bo‘lsa aniq;
- privacy-safe funnel baseline reproducible; telemetryda PII/token 0;
- required CI, docs verifier, rollback rehearsal va owner production decision
  yozilgan.

“Chiroyli landing”, Lighthouse bitta score, automated axe 0 yoki flag ON bu
DoDning o‘rnini bosmaydi.

---

## 16. Birinchi implementatsiya task kartasi — PUB1.0a

### Maqsad

Public DB rich text va custom navigation URL hech bir legacy/V1/preview/flag
yo‘lida executable markup yoki unsafe scheme chiqarmasin. Existing semantic
content yo‘qolmasin; private lesson/editor consumers scope’dan tashqarida qolsin.

### Boshlash tekshiruvi

1. Branch latest `origin/main`dan `codex/public-rich-content-policy`.
2. SIT1.0a yoki boshqa PR `core/rich_content_policy.py`ni yaratganmi tekshir.
3. Current raw pathsni focused failing tests bilan tasdiqla; payloadni log yoki
   marinebookda executable yozma.
4. Existing public content auditini read-only yugurtir; row count/type ber,
   contentni avtomatik rewrite qilma.

### Implementatsiya qadamlari

1. Shared `PUBLIC_EDITORIAL_V1` profile va `sanitize_public_editorial()`.
2. Safe-link attribute callback va public media policy; iframe default deny.
3. `sanitize_public_url()` local/named/https va admitted mailto/tel contracti.
4. Public wrapper/filter V1 `sanitize` o‘rnida; legacy raw `safe` o‘rnida.
5. About bio, landing subtitle, legal, course, pricing `Plan.description`, Blog,
   SIT guide field matrixi.
6. Preview/meta plain-text helpers ayni profile/projectordan.
7. `audit_public_content --format=json` read-only, raw content redacted.
8. Flag ON/OFF regression va safe semantic fixtures.

### Majburiy testlar

- script/event/style/id/class/form/input/object/embed/iframe/srcdoc;
- malformed nested HTML, encoded protocol, backslash/control, protocol-relative;
- `javascript:`, `data:`, SVG/image edge, external link rel;
- headings/list/table/blockquote/code/image alt semantic preservation;
- sanitizer idempotence;
- all listed public fields × legacy/V1 × preview × flag ON/OFF;
- custom nav local/https/mailto/tel/unsafe;
- existing `bleach_tags` imports/private smoke;
- GET write0 va no raw payload logging.

### Tugash mezoni

- focused malicious corpus va existing public suite yashil;
- `git diff --check`, `manage.py check`, migration check;
- runtime data/schema o‘zgarishi yo‘q yoki explicit expand-only evidence;
- rollback old templatega qaytsa ham shared wrapperni chetlab o‘tmaydi;
- SIT1.0a bilan bitta shared primitive, parallel sanitizer yo‘q;
- commit + marinebook + required CI.
