# DASHBOARD-01 — aniq, ishonchli va ultra qulay ish markazi

**Holat: REJA TAYYOR, IMPLEMENTATSIYA BOSHLANMAGAN.**
2026-10-15; source audit tayanchi `main`dagi **`72e82e0`**.

Owner topshirig‘i: AzureLMSning authenticated dashboard qismini radikal
isloh qilish, takomillashtirish va o‘quvchi, o‘qituvchi hamda owner uchun
ultra qulay qilish. Ushbu hujjat DASHBOARD-01 uchun yagona product, data,
security, UX, performance, test va rollout rejasidir.

Dashboard bu rejada bitta universal sahifa emas. Reja to‘rtta surface oilasini
qamraydi:

1. o‘quvchining web bosh sahifasi;
2. o‘qituvchining web bosh sahifasi va assigned-course Backoffice workspace’i;
3. Telegram Mini App va Botdagi ixcham o‘quvchi ko‘rinishi;
4. owner/global ops va finance’ning mavjud Backoffice yuzalariga capability
   bo‘yicha xavfsiz kirish.

Mavjud [I1 learner shell](I1-LEARNING-SHELL.md),
[I2 teacher home](I2-LESSON-RELEASE.md) va
[BACKOFFICE-02](BACKOFFICE-REFORM-PLAN.md#backoffice-02) ishlari bekor
qilinmaydi. Ular renderer, URL, empty state va navigatsiya poydevorini berdi.
DASHBOARD-01 shu poydevor ustidagi hisoblash, ruxsat, rolga yo‘naltirish,
GET side-effect, Mini App session va foydalanish qulayligi qarzlarini yopadi.

Bu reja yozilishi topilgan runtime muammolari tuzatildi, yangi flag yoqildi,
production yangilandi yoki owner qabul qildi degani emas. Birinchi
implementatsiya kesimi **DASH1.0a**. Roadmap sakkiz phase va **33 reviewable
slice**dan iborat; odatiy PR bitta slice’dan katta bo‘lmaydi.

---

## 1. Mahsulot qarori

### 1.1 Yakunda nima quriladi?

Dashboard vanity statistic yoki barcha moduldan bittadan widget yig‘iladigan
portal emas. U foydalanuvchining hozirgi ruxsatli holatidan **bitta eng to‘g‘ri
keyingi amalni** chiqaradigan read-only ish markazi bo‘ladi.

O‘quvchi uchun:

- birinchi ekranda aynan bitta **Keyingi qadam**;
- A7gacha alohida nomlangan, shaxsiylashtirilmagan operational/recovery amallari;
  A7 qabul qilingach uning aynan uch vazifali typed **Daily Coach** paketi;
- faol kurslar, kirish muammosi bor kurslar va yakunlangan natija bir-biridan
  ajratiladi;
- dars progressi, davomat, streak, XP, imtihon va sertifikat bir-birining
  sinonimi qilib ko‘rsatilmaydi;
- to‘lov, release yoki access muammosi dead-end emas, aniq recovery amaliga
  olib boradi;
- web, Mini App va Bot bir xil canonical proyeksiyadan foydalanadi.

O‘qituvchi uchun:

- mavjud bo‘lsa ayni faol Classbook sessiyasi birinchi turadi;
- imtihon va topshiriq ishlari ikki tasodifiy ro‘yxat emas, bitta typed navbat;
- scope faqat biriktirilgan kurs/cohort bilan chegaralanadi;
- nol backlog “favqulodda ogohlantirish” ko‘rinishida chiqmaydi;
- har karta aynan tekshiriladigan ishga yoki domain-owned workflowga olib boradi.

Owner uchun:

- yangi parallel admin dashboard qurilmaydi;
- mavjud course-scoped Backoffice Ish stoli assigned teacher va owner uchun
  saqlanadi; global ops/finance bloklari alohida capability bilan;
- moliya, PII va global operational metric oddiy staffga avtomatik ochilmaydi;
- health signal har requestdagi og‘ir scan yoki dead hardcoded seriesdan emas,
  Control Centerdagi persisted/cached snapshotdan keladi.

### 1.2 Admission va navbat

**Umumiy natija: keng redesign `NEXT — post-launch`, owner execution admissionini
kutadi; security containment tegishli release’dan oldingi gate.** Keng Dashboard
redesigni joriy
core/B3/CLASSBOOK/A4/A6/A7/A9 navbatini o‘z-o‘zidan almashtirmaydi.

Quyidagilar esa yangi feature emas, **security/correctness maintenance** va
birinchi navbatdagi containment hisoblanadi:

1. ordinary staff uchun Backoffice PII/moliya ko‘rinishini default-deny qilish;
2. barcha authenticated HTML/API javoblariga izchil private-cache policy;
3. dashboard GET vaqtida model yaratish yoki biznes holatini yozishni to‘xtatish;
4. Mini App replay, privileged-session va frame boundarysini toraytirish;
5. progress, study hour, tavsiya, streak va locale bo‘yicha noto‘g‘ri product
   claimlarni test bilan contain qilish.

DASH1.0a source’dagi legacy global dashboard/users/chats PII/message context va
receipt decision/foreign file/Bot staff regressiyasi sabab tegishli Backoffice/
payment/Bot yuzalari yoqiladigan har qanday release uchun
**stop-ship A0b regression**. DASH1.0d Mini App yoqiladigan release uchun
security gate. Qolgan DASH1.0 correctness/private-cache containmenti ham katta
UI redesignidan oldin bajariladi. `DASH1.0a` — birinchi xavfsiz kesim.

### 1.3 Admission gate javoblari

| Savol | DASHBOARD-01 javobi |
|---|---|
| Qaysi learner outcome yechiladi? | Foydalanuvchi holatni taxmin qilmasdan ruxsatli keyingi ishni topadi va boshlaydi. |
| Bitta asosiy KPI nima? | `dashboard_valid_next_action_success_rate`. Ta’rifi §12da. |
| Qaysi canonical state o‘zgaradi? | Dashboardning o‘zi canonical learning/payment/message state yozmaydi. U typed read projection va explicit navigation receiptgina beradi. |
| Adapterlar qaysi? | Learner web, teacher web, Mini App, Bot summary va authenticated home router. Existing course-scoped Backoffice workspace teacher/owner uchun saqlanadi; global ops/finance yuzalari capability bilan. |
| Owner yuki nima bo‘ladi? | Kundalik qidirish va noto‘g‘ri staff access kamayadi; yangi manual dashboard curation kiritilmaydi. |
| Flag/rollback bormi? | Renderer/projection/router uchun default-OFF flaglar; security, privacy va data invariant tuzatishlari rollbackda yechilmaydi. |
| Faza? | Keng reform `NEXT — post-launch`, owner execution admissionini kutadi; DASH1.0a affected release uchun existing A0b stop-ship regression, DASH1.0d Mini App release security gate, qolgan DASH1.0 correctness/security maintenance. |

### 1.4 Qamrovga kirmaydigan ishlar

DASHBOARD-01:

- yangi LMS, calendar, video platforma yoki universal search engine qurmaydi;
- dars completion, exam result, certificate, entitlement, unread yoki
  Classbook sessionning parallel system-of-recordini yaratmaydi;
- AI bilan yashirin ranking yoki “eng yaxshi kurs” tavsiyasi bermaydi;
- mastery, learning time yoki risk score mavjud dalilsiz hisoblamaydi;
- raw message body, notification feed yoki AI promptni dashboardga ko‘chirmaydi;
- mavjud Backoffice reformining owner UI scope’ini egallamaydi;
- A4 pricing/payment, A6 Outcome Ledger, A7 Daily Coach, A9 AI gate,
  Classbook yoki Messenger roadmapidagi canonical ishlarni qayta yozmaydi;
- schema drop, eski URLni birdan olib tashlash yoki production data backfillni
  bitta katta releasega jamlamaydi;
- “dashboard ko‘rildi”ni “o‘qidi”, “o‘rgandi” yoki “natijaga erishdi” deb
  da’vo qilmaydi.

---

## 2. Tadqiqot chegarasi va mavjud poydevor

### 2.1 Tekshirilgan ichki yuzalar

Audit source, template, test, URL va model darajasida quyidagilarni ko‘rdi:

- learner [`DashboardView`](../../users/views.py),
  [`LessonProgress`](../../users/models.py), enrollment va attendance
  aggregatsiyalari;
- learner legacy va V1 templatelari, shell/context processorlari,
  notification open/read oqimi;
- [`courses/resume_service.py`](../../courses/resume_service.py), course study,
  My Courses va academic completion/certificate kontraktlari;
- teacher [`core/teacher_views.py`](../../core/teacher_views.py), canonical
  teacher scope, exam/assignment review queue va legacy/V1 templatelari;
- legacy [`core/views.py`](../../core/views.py) Backoffice dashboardi hamda
  mavjud [workspace Ish stoli](../../templates/backoffice/workspace/home.html);
- Mini App [`bot/views.py`](../../bot/views.py), HMAC/session middleware,
  Bot summary va Mini App templates/CSS;
- frontend feature flaglari, authenticated `/` va login/Telegram redirectlari;
- I1/I2/B2/launch evidence va relevant regression testlar.

Ikki local audit faqat query-shape signali uchun ishlatildi. Mavjud developer
DBdagi bitta enrollmentli render legacy learnerda 29, V1 learnerda 26 query
ko‘rsatdi. Izolyatsiyalangan vaqtinchalik test DBning **warm empty** fixture’ida
esa learner V1 36, teacher V1 31, Mini App home 16 va legacy Backoffice 46 SQL
bo‘ldi. Setup/context farqi sabab bu sonlar bir-biriga benchmark sifatida
solishtirilmaydi.

Fresh singleton holatidagi ayni temp auditda birinchi GET learner uchun 5 ta,
teacher/legacy Backoffice/Mini App uchun 3 tadan `INSERT` qildi. Learner V1
active enrollmentlari 0→1→5→20 bo‘lganda jami SQL 36→40→44→59, payment receipt
querylari esa 0→1→5→20 bo‘ldi. Bu `active_plan()` loopidagi aniq N+1 signalidir.
Production hajmi yoki latency da’vosi emas; DASH1.0c va DASH1.1d bu signallarni
reproducible hard gatega aylantiradi.

### 2.2 Saqlanadigan yaxshi poydevor

| Mavjud tayanch | Nega saqlanadi | Reform chegarasi |
|---|---|---|
| Effective enrollment status builder web, Mini App va Botda ishlatiladi | surface’lar orasidagi status driftini kamaytiradi | viewdan domain projection moduliga ko‘chadi; hisoblash aniq nomlanadi |
| `courses/resume_service.py` exact cohortda last-touched incomplete yoki next open lessonni topadi | lesson deep link uchun yaxshi canonical tayanch | kursni tanlash ham meaningful activityga tayanadi |
| `teacher_course_queryset()` non-owner uchun assigned course’ga default-deny | teacher least-privilege asosi | queue va barcha linked selectorlar ayni scope’dan chiqmaydi |
| V1 learner empty/inactive/active holatlari | soxta progresssiz state ajratilgan | pending/frozen/expired/no-release recovery to‘liq qilinadi |
| V1 skip-link, native dialog, Escape/focus return va no-JS nav | accessible shell foundation | legacy va Mini Appga teng contract beriladi |
| Existing cross-user/exact-cohort tests | eng muhim access regressiyalarini tutadi | rol, replay, query va write0 matrixi bilan kengayadi |
| Mini App deep-action parity testlari | adapter URL parity poydevori | reason/action projection paritygacha ko‘tariladi |
| Raw notification/Telegram feed dashboardda yo‘qligi | privacy va attention uchun to‘g‘ri qaror | typed notice/task faqat domain summarydan keladi |
| Backoffice workspace wrapper active staff + flag + no-store ishlatadi | yangi owner dashboard kerak emas | legacy entry va capability shu xavfsiz yuzaga ulanadi |
| Recent work actor-bound, max-3 va permission revalidated | qulay “qaytish” elementi | analytics yoki source-of-truthga aylantirilmaydi |

### 2.3 Terminlar

| Termin | Ushbu rejadagi aniq ma’no |
|---|---|
| Dashboard | role-scoped read projection va uning renderer/adaptersi |
| Primary action | ayni holat uchun bitta deterministic, ruxsatli keyingi amal |
| Task | canonical domain holatidan kelgan, exact destinationli amaliy ish |
| Lesson completion | eligible lesson uchun `LessonProgress.is_completed`; owner boshqa policy tanlamaguncha attendance emas |
| Attendance | alohida dars qatnashuvi; completion yoki mastery sinonimi emas |
| Streak | `LearnerStreak` contractidagi qualified learning days; “davomat” emas |
| Mastery | A6 validated evidence paydo bo‘lmaguncha dashboardda mavjud emas |
| Academic completion | exam/certificate/outcome policyga bog‘liq canonical state; 100% lesson progress emas |
| Partial projection | optional source ishlamadi, qolgan xavfsiz qismlar render bo‘ldi |
| Write-free GET | request davomida domain va config jadvallariga INSERT/UPDATE/DELETE yo‘q |

---

## 3. P0 topilmalar — yangi UI’dan oldin containment

### 3.1 P0 katalogi

| ID | Source dalili va muammo | Xavf | Majburiy javob |
|---|---|---|---|
| P0-1 | Legacy `/backoffice/`, `/backoffice/users/` va `/backoffice/chats/` `is_staff OR is_superuser`ga global student/teacher PII, chat room/participant/last-message contexti, revenue/signups va pending receipts beradi. Chat route message body hamda participant emaili bo‘yicha qidiradi. Xuddi shu keng staff qarori canonical receipt decide service, boshqa user receipt fayli va Telegram admin stats/receipt adapterida ham bor | ordinary staff global moliya, PII/message body konteksti, boshqa learner chek faylini olishi yoki pul qarorini mutatsiya qilishi mumkin; learnerning o‘z receipt fayliga qonuniy kirishi esa saqlanishi shart | DASH1.0a: barcha reader/writer/adapterda explicit capability, default-deny; `/backoffice/chats` fail-closed va faqat Messenger-owned scoped metadata contractini consume qiladi; body/snippet/email search MSG1.0d/MSG-D13siz hech kimga, jumladan superuserga ham ochilmaydi; own-file ownership alohida allow path; teacher faqat course workspace scope’i; mavjud staffga avtomatik global/finance grant yo‘q |
| P0-2 | V1 learner/teacher va workspace no-store, ammo legacy learner/teacher/backoffice va Mini App bir xil policyga ega emas | shared device/proxy/browser private HTMLni saqlashi mumkin | DASH1.0b: auth-route response helper, `private, no-store`, `Vary: Cookie`; barcha success/error/redirect test |
| P0-3 | Dashboard GET `AISettings.load()`/allowance `get_or_create` va frontend singleton context processorlari orqali cold DBda yozishi mumkin | reload/crawler/two tab business/config state yaratadi, race va audit buziladi | DASH1.0c: read-only default objects va explicit provisioning; authenticated GET write0 gate |
| P0-4 | Mini App HMAC 24h age bilan cheklanadi, future skew/replay digest yo‘q; linked staff/superuser shu `CustomUser` bilan kirsa barcha Django privilege’i faol qoladi; session marker normal webni ham frameable qiladi | replay, privileged session, clickjacking/frame scope va session fixation | DASH1.0d: shared atomic one-time digest, TTL/skew, rate/body schema; privileged account bootstrap assurance gate tayyor bo‘lguncha reject; cycle key va route-exact CSP/frame policy |
| P0-5 | `completed=max(attendance, LessonProgress)` disjoint setda unionni ham, completionni ham bermaydi; global total ham shunday | foydalanuvchiga yolg‘on progress va noto‘g‘ri action | DASH1.0e: owner policy + failing fixtures; safe default LessonProgress-only, attendance separate |
| P0-6 | `average_progress=passed_lessons_count`; study hour `passed*2`; popularity top-3 “Tavsiya”; shell unknown levelni A1 qiladi | o‘lchanmagan yoki noto‘g‘ri product claim | DASH1.0e: uydirma metrikani olib tashlash/rost nomlash; unknown aniq unknown |
| P0-7 | Backoffice `today_revenue`ni render qiladi, dormant `weekly_revenue`ni ham hisoblaydi va verified receiptni `submitted_at` bilan vaqtlaydi; verification vaqti yo‘q | upload vaqtini payment verification yoki accounting revenue deb ko‘rsatadi | DASH1.0e: rendered `today_revenue`ni hide/unavailable va dormant weekly contextni delete; A4 prerequisite haqiqiy immutable verification vaqtini yaratadi; DASH1.4b faqat “tasdiqlangan to‘lovlar/cheklar” selectorini iste’mol qiladi. A4 accounting policy bo‘lmaguncha revenue claim yo‘q |
| P0-8 | Backoffice requestda `get_rag_index_status()` to‘liq content scan qiladi; hardcoded sparkline esa templatega uzatilmaydigan dead context | har refresh O(content), keraksiz hardcoded context esa source truthni loyqalatadi | DASH1.0e: request-time scanni uzish va dead sparkline contextni o‘chirish; healthni unavailable qilish; A2/Control Center prerequisite snapshot tayyorlagach DASH1.4c uni consume qiladi |
| P0-9 | Outcome evaluation `PROMOTION_READY` beradi; keyingi cohortga promotion transitionigina oldingi source enrollmentni `COMPLETED` qilib muzlatadi. Legacy Backoffice “completion rate” aynan `COMPLETED`ni sanaydi | label akademik/certificate completionni emas, promotion qilingan source enrollmentlarni o‘lchaydi; promotion qilinmagan yakunlar ko‘rinmaydi | DASH1.0e: metricni “promoted source enrollments” deb aniq nomlash yoki olib tashlash; course/A6 outcome ownerining alohida academic/certificate projectionisiz “completion rate” claim yo‘q |

P0 tuzatishlari presentation flag ortiga yashirilmaydi. Renderer rollbacki
authorization, private cache, replay yoki data-truth invariantini ochib yubormaydi.

### 3.2 Progress integrity xavfi

`LessonProgress` enrollment+lesson va `Attendance` enrollment+lesson+date
unikalligiga ega, lekin database enrollmentning kursi bilan lessonning kursi
bir xil ekanini kafolatlamaydi. Corrupt yoki eski adapter yozuvi denominatorni
oshirib, foizni 100dan yuqori qilishi mumkin.

Target:

1. projection query enrollment course/eligible curriculum bilan qat’iy scope
   qiladi;
2. writer service foreign-course lessonni rad etadi;
3. management audit invalid rowlarni sanaydi, lekin avtomatik taxminiy tuzatmaydi;
4. UI `min(100, value)` bilan anomaly’ni jim yashirmaydi;
5. reconciliation/backfill faqat explicit owner-approved rule bilan va receipt
   bilan bajariladi.

### 3.3 Private GET side-effect katalogi

Write-free gate faqat `DashboardView`ga emas, render zanjiriga tegishli:

- `AISettings.load()` va `AIUserAllowance.get_or_create`;
- `SiteSettings.load()`, `AuthPageSettings.load()`, `LandingPage.load()`;
- notification/context plan lookup;
- Mini App session/bootstrap;
- notification “open” GETidagi `mark_read()`.

Dashboard projection GET hech qanday read receipt ham yozmaydi. Notification
read explicit CSRF-protected POST yoki o‘sha domainning versionlangan commandi
bo‘ladi. Sessionning framework-level expiry/cookie rotationi alohida kuzatiladi;
business-write0 asserti domain/config jadvallariga qaratiladi.

---

## 4. P1 audit — product va UX qarzlari

### 4.1 Learner

| Topilma | Hozirgi natija | Target |
|---|---|---|
| Resume course birinchi active enrollment/joined date bo‘yicha | oxirgi ishlangan kurs o‘rniga boshqa kurs chiqishi mumkin | recent meaningful accessible activity; yo‘q bo‘lsa deterministic enrollment date+PK |
| `active_courses_count` aslida active enrollment/group | label haqiqatdan siljiydi | “Faol guruhlar” yoki owner-approved aniq birlik |
| 100% lesson progress “Tugatilgan” | exam/certificate hali ochiq bo‘lishi mumkin | “Darslar bajarildi”; academic state alohida |
| `PROMOTION_READY`, promotiondan keyingi source `COMPLETED` va certificate semantics bir xil emas | learner va owner dashboardlari boshqa “yakun”ni sanashi mumkin | har metric typed va rost nomli; umumiy academic completion faqat outcome owneri projectionidan, ungacha unavailable |
| V1 ko‘rsatmaydigan badges/certificates/leaderboard/AI context ham hisoblanadi | query overfetch va cohort-sizega bog‘liq Python loop | field-selective projection; renderer so‘ramagan blok query qilinmaydi |
| leaderboard barcha peers/progress/attendance’ni Python’da yig‘adi | O(cohort) va ranking semantics noaniq | dashboarddan chiqarish; admitted domain ranking bo‘lsa alohida projection |
| streak kartasi attendance’ga olib boradi | ikki tushuncha birlashadi | streak izohi va tegishli activity/history target |
| “Tavsiya etilgan” top-3 popularity | personalization claim yolg‘on | “Mashhur kurslar” deb rost nomlash yoki olib tashlash |
| legacy mobile nav faqat JS bilan ochiladi | JSsiz asosiy yo‘llar ko‘rinmaydi | semantic links/noscript fallback, V1 shell patterni |
| `{% now "l" %}` `en-us` locale bilan | o‘zbek UI ichida inglizcha kun/oy | explicit Uzbek formatter/i18n test |

### 4.2 Teacher

| Topilma | Hozirgi natija | Target |
|---|---|---|
| `_base_context` va dashboard querylari ayrim count/listlarni takrorlaydi | ortiqcha query va drift | bitta `TeacherHomeProjection` |
| Exam va assignment top-5 alohida | eski muhim ish yangi boshqa tur ortida qolishi mumkin | typed unified queue, deterministic `submitted_at/event_at + kind + PK` |
| nol ishda ham alarm card | foydalanuvchini asossiz xavotirga soladi | `empty` state; urgency faqat canonical signalda |
| no-course/no-student state’da next step yo‘q | dead-end | owner/admin contact yoki content/Classbook recovery |
| “Muallif” va “O‘qituvchi” aralash | rol mental modeli buziladi | bitta owner-approved label |
| legacy/V1 nav guruhlari flag bilan ko‘chadi | renderer almashtirilsa mental model ham o‘zgaradi | stable IA; flag faqat renderer tanlaydi |
| role switch learner/teacher/backoffice orasida zid | dual-role user noto‘g‘ri uyga tushadi | pure `WorkspaceHomeResolver` va explicit role switch |

### 4.2a Global context va query overfetch

Private sahifalar ham global context processorlar orqali public nav/footer,
uchta singleton, beshta navigation placement, notification list/unread va plan
querylarini yuklaydi. V1 shell asosan brand va unread countga muhtoj;
`sidebar_current_plan` template consumerga ega emas. Backoffice navigation
flaglari ham bir requestda alohida querylar bilan o‘qiladi.

Target:

- private shell uchun read-only `brand_context` va unread-only notification
  projection;
- recent notification list faqat o‘z sahifasida;
- public nav/footer faqat public layoutda;
- flaglar request-scope bitta bulk snapshotda, cross-request cache’siz;
- learner plan/entitlement learner projectionda bir marta batch qilinadi;
- leaderboard, AI usage, certificate va recommendation faqat so‘ralgan section
  yoki o‘z sahifasida.

### 4.3 Mini App va Bot

| Topilma | Hozirgi natija | Target |
|---|---|---|
| `_miniapp_context` har home/courses/AI/profile requestda full learner aggregation qiladi | har tab ortiqcha query | field-selective shared projection |
| barcha enrollment cardlari `course_study`ga link | inactive holat denial/dead-end | state-specific recovery action |
| AI doim tab/quick action va “doim yoningizda” claimi | A9, quota, kill-switch va entitlementdan oldin va’da | capability projection; unavailable bo‘lsa rost state; tab qarori DASH-D7 |
| bottom nav `aria-current`/skip-link yo‘q, matn 8–10.5px | WebView accessibility past | semantic nav, readable type, safe-area/keyboard tests |
| Bot summary ayni flawed progress helperdan foydalanadi | xato barcha adapterga tarqaladi | same typed learner projection, format-only adapter |

### 4.4 Routing va shell

Authenticated `/`, `LOGIN_REDIRECT_URL` va Telegram web auth hozir learner
dashboardiga moyil. Staff/owner learner querylarini to‘laydi va noto‘g‘ri ish
maydoniga tushadi.

Shu drift register URLni authenticated user ochganda, public V1 headerdagi
authenticated CTA’da va default login success’da ham bor. Mini App alohida
home’da qolishi kerak va webdagi teacher/Backoffice preference’ga sakramaydi.

Target `WorkspaceHomeResolver`:

```text
safe explicit next
  └─ bo‘lsa va allowlistdan o‘tsa → o‘sha destination
aks holda explicit chosen mode
  └─ sessiondagi allowlisted preference bo‘lsa → o‘sha rol
aks holda capability precedence
  ├─ learner-only → learner home
  ├─ teacher-only → teacher home
  ├─ owner/global ops → existing Backoffice Ish stoli
  └─ dual-role → DASH-D2 bo‘yicha deterministic default
```

Resolver pure va read-only bo‘ladi. GET preference yozmaydi. Role switch
kerak bo‘lsa explicit CSRF POST, allowlisted role va session `cycle_key` bilan
amalga oshadi. `/users/dashboard/` dual-role user uchun learner mode direct
URL sifatida saqlanadi.

---

## 5. Canonical dashboard arxitekturasi

### 5.1 Asosiy qoida

Dashboard **system-of-record emas**. U quyidagi qatlamlar orasidagi typed,
immutable, read-only projectiondir:

```text
Enrollment / LessonProgress / Attendance / Exam / Certificate
Payment / Entitlement / Classbook / Messenger / AI capability
                          │
                 domain selectors/policies
                          │
           typed DashboardProjection + reason codes
                          │
     Web learner · Web teacher · Mini App · Bot · home router
```

Adapter progress yoki priority hisoblamaydi, raw URL yasamaydi va GETda
domain state yozmaydi. Destination view har doim ruxsatni qayta tekshiradi.

### 5.2 Tavsiya etilgan modul chegaralari

| Modul | Mas’uliyat | Mas’ul emas |
|---|---|---|
| `core/dashboard_contracts.py` | immutable DTO, enum/reason vocabulary, serialization boundary | ORM query, template, business mutation |
| A0/platform-owned `core/private_response.py` | barcha authenticated route oilasi uchun yagona private/no-store/Vary/referrer/CSP helper | Dashboardga xos role yoki domain policy; Messenger/Classbook alohida nusxa yaratmaydi |
| `core/workspace_home.py` | pure role/capability resolver va safe destination mapping | session preference write, template render |
| `courses/progress_projection.py` | lesson progress truth, denominator, anomalies, recent activity | academic completion yoki certificate write |
| `users/dashboard_service.py` | learner sections va deterministic primary action composition | payment/AI/Classbook state mutation |
| `core/teacher_dashboard_service.py` | scoped teacher queue va teacher action composition | grading/release/Classbook mutation |
| existing Backoffice workspace | owner operational UI | learner/teacher dashboard logic |
| `bot/views.py`/Bot service | projectionni field-select va format qilish | o‘z progress/ranking qoidasi |

Modul nomlari implementatsiya vaqtida repository style bilan aniqlashtirilishi
mumkin, lekin ownership aralashmaydi. Bir qoida ikki adapterda takrorlansa PR
qabul qilinmaydi.

### 5.3 Minimal DTO kontrakti

```python
WidgetState = Literal["ok", "empty", "stale", "unavailable", "denied"]
T = TypeVar("T")

@dataclass(frozen=True)
class ProjectionSection(Generic[T]):
    state: WidgetState
    as_of: datetime | None
    reason_code: str | None
    data: T | None

@dataclass(frozen=True)
class MetricDefinition:
    code: str
    label: str
    value: int | Decimal | None
    unit: str | None
    numerator: int | None
    denominator: int | None
    source: str
    explanation: str

@dataclass(frozen=True)
class RouteParam:
    name: str
    value: int | str

@dataclass(frozen=True)
class DashboardRouteTarget:
    route_key: str
    kwargs: tuple[RouteParam, ...]
    query: tuple[RouteParam, ...]

@dataclass(frozen=True)
class DashboardAction:
    kind: str
    source_ref: str | None
    reason_code: str
    title: str
    description: str
    target: DashboardRouteTarget
    enabled: bool

@dataclass(frozen=True)
class CourseProgressSnapshot:
    enrollment_id: int
    course_id: int
    cohort_id: int
    eligible_count: int
    completed_count: int
    percent: Decimal | None
    last_activity_at: datetime | None
    evidence_policy: str
    anomalies: tuple[str, ...]

@dataclass(frozen=True)
class CourseCard:
    enrollment_id: int
    course_id: int
    cohort_id: int
    course_title: str
    cohort_name: str
    access_state: str
    progress: ProjectionSection[CourseProgressSnapshot]
    primary_action: DashboardAction | None

@dataclass(frozen=True)
class DashboardNotice:
    code: str
    severity: Literal["info", "success", "warning", "error"]
    title: str
    description: str
    action: DashboardAction | None

@dataclass(frozen=True)
class DailyCoachBundle:
    plan_version: str
    generated_at: datetime
    items: tuple[DashboardAction, DashboardAction, DashboardAction]

@dataclass(frozen=True)
class LearnerHomeProjection:
    actor_id: int
    generated_at: datetime
    projection_version: str
    primary: ProjectionSection[DashboardAction]
    operational_actions: ProjectionSection[tuple[DashboardAction, ...]]
    daily_coach: ProjectionSection[DailyCoachBundle]
    courses: ProjectionSection[tuple[CourseCard, ...]]
    activity: ProjectionSection[tuple[MetricDefinition, ...]]
    notices: ProjectionSection[tuple[DashboardNotice, ...]]

@dataclass(frozen=True)
class TeacherWorkItem:
    kind: str
    source_ref: str
    event_at: datetime
    course_id: int
    cohort_id: int | None
    priority_reason: str
    action: DashboardAction

@dataclass(frozen=True)
class TeacherGroupSummary:
    course_id: int
    cohort_id: int
    label: str
    learner_count: int | None
    state: WidgetState
    reason_code: str | None
    action: DashboardAction | None

@dataclass(frozen=True)
class TeacherHomeProjection:
    actor_id: int
    generated_at: datetime
    projection_version: str
    primary: ProjectionSection[DashboardAction]
    queue: ProjectionSection[tuple[TeacherWorkItem, ...]]
    groups: ProjectionSection[tuple[TeacherGroupSummary, ...]]
    quick_actions: ProjectionSection[tuple[DashboardAction, ...]]
    metrics: ProjectionSection[tuple[MetricDefinition, ...]]
    notices: ProjectionSection[tuple[DashboardNotice, ...]]
```

DTO database model emas. `source_ref` adapter reconciliation va idempotent UI
identity uchun opaque typed reference; telemetry label/logiga yozilmaydi va xom
user text yoki URL emas. `DailyCoachBundle` A7ning versionlangan, aynan uch
itemli immutable kontrakti; Dashboard uning itemlarini qayta rank, truncate yoki
aralashtirmaydi. `DashboardRouteTarget` oddiy frozen dataclass bo‘lgani bilan
kifoyalanmaydi: uni faqat `build_route_target()` factorysi yaratadi. Route
registry har `route_key` uchun Django route name, exact kwargs/query keylari,
scalar turi, slug regexi, maksimal string uzunligi va multiplicityni belgilaydi;
factory input mapping/listni defensively copy qilib tuplega muzlatadi. Unknown
route/key, duplicate param, bool-as-int, haddan uzun string va arbitrary URL
rad etiladi. Renderer faqat registry orqali `reverse()` qiladi. Shu sabab ichki
mutable `Mapping` yoki caller keyin o‘zgartira oladigan collection DTOga kirmaydi.
`ProjectionSection` `WidgetState`ni amalda majburiy qiladi:
`unavailable/denied` holatda `as_of` va `data` bo‘sh bo‘lishi mumkin, sabab esa
typed `reason_code`da keladi; renderer o‘zicha fake zero yaratmaydi. Partial
sections shu state’lardan hosila bo‘ladi. `DashboardNotice` faqat trusted
projection copy’si; raw Notification/Messenger body DTOga ko‘chirilmaydi.

### 5.4 Reason code lug‘ati

Boshlang‘ich stable vocabulary:

- `no_enrollment`;
- `pending_payment`;
- `frozen_access`;
- `expired_access`;
- `no_released_lesson`;
- `resume_incomplete_lesson`;
- `start_next_lesson`;
- `lesson_requirements_complete`;
- `exam_or_outcome_next`;
- `certificate_available`;
- `active_classbook_session`;
- `multiple_active_classbook_sessions`;
- `pending_exam_review`;
- `pending_assignment_review`;
- `source_unavailable`;
- `permission_denied`;
- `data_integrity_anomaly`.

Reason code tarjima matni emas va keyinchalik matnni o‘zgartirishga to‘sqinlik
qilmaydi. Har code unit testda exact source conditionga bog‘lanadi.

### 5.5 Failure contracti

- Enrollment/access yoki actor identity aniqlanmasa — fail-safe, primary action
  berilmaydi va private generic error ko‘rsatiladi.
- Optional XP/streak/notification/AI source ishlamasa — qolgan dashboard
  render bo‘ladi, section `unavailable`; **0** deb ko‘rsatilmaydi.
- Stale snapshot bo‘lsa `as_of` va `stale` state ko‘rsatiladi.
- Destination permission dashboarddan keyin ham qayta tekshiriladi.
- Projection exceptioni raw model, SQL, token yoki PII bilan log qilinmaydi.
- Fallback renderer eski noto‘g‘ri hisobni qayta ishlatmaydi; security/truth
  service shared qoladi.

---

## 6. Product truth va action policy

### 6.1 Progress policy

Owner DASH-D3 bilan boshqacha qaror qilmaguncha xavfsiz default:

```text
lesson completion = distinct eligible LessonProgress(is_completed=True)
attendance        = alohida distinct attended lesson/date metric
streak            = LearnerStreak qualified learning-day contracti
academic outcome  = exam/certificate/outcome domain state
mastery           = unavailable (A6 validated evidencegacha)
study hours       = unavailable (real duration eventgacha)
```

Denominator “currently open lesson”ga ko‘r-ko‘rona teng emas. Yakunlangan,
keyin cohort release’i yopilgan dars progressdan jim yo‘qolmasligi kerak;
boshqa course/cohortga tegishli dars esa qo‘shilmasligi kerak. Joriy `Lesson`
modelida draft/published/archive lifecycle yo‘q: reja bunday holatni mavjud deb
taxmin qilmaydi. Exact eligible curriculum definitioni DASH-D4 owner/domain
qarori va joriy `Course.is_active`, cohort holati hamda
`CohortLessonRelease`ning implicit/explicit release semanticsiga mos fixture
bilan yopiladi. Dars lifecycle kerak bo‘lsa u Course/Classbook ownerida alohida
admission qilinadi. Yana bir qat’iy chegara: `LessonProgress.lesson` hozir
`CASCADE`; Lesson hard-delete qilinsa tarixiy progress ham o‘chadi. Dashboard
querysi buni saqlab qola olmaydi. DASH-D4 faqat joriy curriculum va release-lock
semantikasini yopadi; tarixiy evidence/versioning Course/Backoffice yoki A6
ownerida explicit prerequisite bo‘lmasa “old progress always preserved” claimi
qilinmaydi.

### 6.2 Learner primary action policy

Priority taxminiy AI rank emas, deterministic business policy:

1. canonical faol Classbook session mavjud va learner ayni cohortga ruxsatli
   bo‘lsa — bitta sessionda exact `active_classbook_session`; bir nechta open
   sessionda `.first()` emas, barcha sessionni deterministic `-started_at, -pk`
   tartibda saqlaydigan Classbook live-home/list actioni;
2. meaningful activity bo‘lgan active course’dagi last touched accessible
   incomplete lesson — `resume_incomplete_lesson`;
3. shu course’dagi keyingi accessible lesson — `start_next_lesson`;
4. active course’da released lesson yo‘q — blocked state va yordam/notification;
5. active learning yo‘li yo‘q bo‘lsa pending/frozen/expired recovery;
6. enrollment yo‘q bo‘lsa catalog yoki incomplete onboarding;
7. lesson requirements tugasa canonical exam/outcome/certificate service
   qaytargan amal;
8. haqiqiy keyingi amal yo‘q bo‘lsa disabled “hammasi tayyor” emas — honest
   empty state.

Bir kursdagi payment muammosi boshqa faol kursdagi o‘qishni to‘smasligi kerak.
Ko‘p active course’da recent meaningful activity birinchi; hech biri touched
bo‘lmasa enrollment effective date, so‘ng PK bilan deterministic order.
Pin/favorite faqat DASH-D5 owner qaroridan keyin explicit user mutation bo‘ladi.

### 6.3 A7gacha operational amallar, A7dan keyin Daily Coach

Dashboard A7ga parallel “Bugungi ishlar” plannerini qurmaydi.

**A7gacha:** alohida **“Holat va tiklash”** blokida ko‘pi bilan uchta
shaxsiylashtirilmagan operational/recovery amal ko‘rsatilishi mumkin: payment
recovery, released lesson yo‘qligi uchun help yoki exact pending workflow.
Bu blok “Daily Coach”, “Bugungi reja” yoki personalized tavsiya deb atalmaydi;
due/schedule o‘ylab topmaydi, notification bodyni taskga aylantirmaydi va primary
actionni takrorlamaydi. Order typed reason, canonical event time, kind va source
PK bo‘yicha deterministic.

**A7 qabul qilingach:** Dashboard A7ning versionlangan, deterministic aynan uch
vazifali `DailyCoachBundle`ini o‘zgartirmay ko‘rsatadi. Uni qayta rank qilish,
uchdan kesish, ichiga Dashboard task qo‘shish yoki AI suggestion bilan almashtirish
taqiqlanadi. Primary CTA Coach paketidan alohida qoladi. Primary va A7 orasidagi
cross-domain safe default — `primary_separate_no_preemption`: Dashboard primaryni
A7 paketi sabab o‘zgartirmaydi. A7 selectoriga primary target identitysi context
sifatida beriladi; A7 uch item ichidagi va primary bilan dedupe uchun javobgar.
A7 duplicate yoki uchdan boshqa bundle qaytarsa butun Coach section
`unavailable`, primary esa saqlanadi — Dashboard item kesib “tuzatmaydi”.
Kelajakda preemption kerak bo‘lsa faqat owner tasdiqlagan, versionlangan
`WorkspaceNextActionPolicy` ADRsi bilan; renderer yoki adapterda yashirin
precedence yozilmaydi.

### 6.4 Teacher primary action va queue

1. canonical active Classbook session bo‘lsa birinchi; bitta bo‘lsa exact,
   ko‘p bo‘lsa deterministic session-list actioni va qolgan sessionlar
   secondary task/listda saqlanadi;
2. aks holda bitta unified `TeacherWorkItem` queue’dagi eng old/yuqori
   canonical ish;
3. exam va assignment itemlari typed bo‘ladi, lekin order yagona;
4. SLA, “kechikdi” yoki risk claimi owner setting va canonical timestamp
   bo‘lmaguncha ko‘rsatilmaydi;
5. queue item destinationi teacher scope’ni qayta tekshiradi;
6. zero backlog — success/empty state, alarm emas.

### 6.5 Backoffice boundary

DASHBOARD-01 existing Backoffice Ish stolining layout, qidiruv yoki workflow
roadmapini qayta qurmaydi. U faqat:

- authenticated home resolverdan to‘g‘ri kirish;
- capability/PII/moliya containment;
- truthli finance timestamp dependency;
- cached health signal;
- role-switch parity;
- private response policy

chegaralarini integratsiya qiladi. Keyingi owner UI ishlari
[BACKOFFICE-03](BACKOFFICE-REFORM-PLAN.md#backoffice-03)ga tegishli.

Bu yerda ikki xil scope aralashtirilmaydi:

- existing course-centered workspace assigned teacher uchun
  `teacher_course_queryset()` bilan ruxsatli va saqlanadi;
- global learner counts/recent PII, revenue, receipt decision/file va platform
  stats faqat tegishli ops/finance/PII capability bilan.

Finance-only actor generic “cheklangan Ish stoli”ga emas, ruxsatli bo‘lsa exact
finance queue’ga tushadi. Teacherga course authoringni saqlash global moliya yoki
learner PII grant qilish degani emas.

### 6.6 Cross-domain ownership jadvali

| Ma’lumot/amal | Canonical owner | Dashboard nima qiladi |
|---|---|---|
| enrollment/access/payment | A4 + enrollment/entitlement service | effective state va recovery actionni o‘qiydi |
| lesson progress | Course/LessonProgress service | exact snapshotni o‘qiydi |
| mastery/outcome | A6 Outcome Ledger | faqat admitted evidence keyin metric oladi |
| personalized Daily Coach | A7 | exact versionlangan uch-item bundle; dashboard rerank/truncate qilmaydi |
| active live lesson | Classbook | exact session summary/actionni oladi |
| unread/help | Messenger/Notification | count/typed notice; body/snippetni ko‘chirmaydi |
| Backoffice chat support | Messenger MSG1.0d/MSG-D13 | route’ni fail-closed qiladi; faqat Messenger-owned scoped metadata selectorini oladi; body/snippet/email search capability ixtiro qilmaydi |
| AI availability/quota | AI Control/A8/A9 | capability state; va’da yoki provider call qilmaydi |
| SIT inquiry | SIT domain | admitted bo‘lsa typed owner/learner action |
| health | Control Center | cached/persisted snapshotni ko‘rsatadi |
| Mini App theme | B3.6 | projectionga tegmaydigan presentation adapteri |

DASH1.2 va DASH1.3 domain port/interface, deterministic fallback va fake-based
state testlarini quradi. Classbook/A4/Messenger/A6/A7/SIT/AI production
selectorini vaqtincha dashboard ichida yozmaydi. Real wiring faqat DASH1.6dagi
tegishli owner contracti tayyor bo‘lganda; ungacha section/action
`unavailable` yoki mavjud xavfsiz core flow bilan qoladi.

---

## 7. Information architecture va ekran holatlari

### 7.1 O‘quvchi web bosh sahifasi

Tavsiya etilgan tartib:

1. **Sahifa nomi va qisqa holat** — salomlashish ikkilamchi; user-facing nom
   DASH-D1 qaroridan keyin “Bosh sahifa” yoki “O‘quv markazi”.
2. **Keyingi qadam** — bitta primary card, sabab va destination bilan.
3. **Daily Coach yoki operational recovery** — A7 tayyor bo‘lsa uning exact uch
   itemli paketi; aks holda aniq boshqa nomdagi 0–3 operational amal. Ikkisi
   bitta “personalized” ro‘yxatga aralashtirilmaydi.
4. **Kurslarim** — faol kurslar compact; kirish holati muammolari alohida.
5. **Faollik** — faqat ta’riflangan streak, attendance va XP; har biri izohli.
6. **Yordam** — blocking state ichida contextual help; raw feed emas.
7. **Hisob va rol** — profil, sozlama, to‘lov va ruxsatli role switch.

Desktopda content haddan tashqari keng ikki-uch kolonka bo‘lmaydi: primary
reading/action column ustun, ikkilamchi bloklar yon yoki pastda. Mobilda source
order yuqoridagi semantik tartibni saqlaydi.

### 7.2 Learner state matrixi

| Holat | Primary title | Izoh | Destination | Taqiqlangan claim |
|---|---|---|---|---|
| enrollment yo‘q | Kursni tanlang | o‘qish hali boshlanmagan | catalog/onboarding | “0% muvaffaqiyat” |
| pending | To‘lov holatini ko‘ring | tekshiruv kutilmoqda | canonical receipt/status | “kurs bloklandi” sababsiz |
| active, untouched | Birinchi darsni boshlang | ruxsatli birinchi lesson | exact course+cohort study | random popular course |
| active, partial | Davom eting | last meaningful incomplete | exact lesson | joined date asosidagi boshqa course |
| active, no release | Yangi dars kutilmoqda | ustoz hali ochmagan | notification/help | mavjud bo‘lmagan vaqt |
| frozen | Kirishni tiklang | canonical reason bo‘lsa ko‘rsatiladi | A4 recovery | course study denial loop |
| expired | Davom ettirish variantini ko‘ring | access tugagan | renewal/plan | auto-renew va’dasi |
| lesson req complete | Keyingi natijaga o‘ting | exam/certificate policy | canonical outcome action | “kurs tugadi” avtomatik |
| certificate ready | Sertifikatni oching | canonical issued state | certificate detail/download | self-marked progressga certificate |
| source unavailable | Hozir ko‘rsatib bo‘lmadi | keyin urinib ko‘ring/help | safe retry/help | `0` qiymat |

### 7.3 O‘qituvchi bosh sahifasi

Tartib:

1. **Hozir** — active Classbook session bo‘lsa start/return; bo‘lmasa navbatdagi
   aniq ish.
2. **Tekshiruv navbati** — unified exam/assignment list, source type va age.
3. **Guruhlar** — faqat scoped, actionable signal; vanity count ikkilamchi.
4. **Tezkor ishlar** — Classbook, tekshirish, release, kontent.
5. **Yordam va rol** — stable shell, learner/owner mode faqat ruxsat bo‘lsa.

Teacher state’lari: no assigned course; course bor/group yo‘q; group bor/student
yo‘q; zero backlog; mixed queue; active session; partial source failure; access
revoked. Har biri test fixture va exact recoveryga ega bo‘ladi.

### 7.4 Mini App

Tavsiya etilgan stable tablar — DASH-D7 tasdiqlashi kerak:

- **Bosh sahifa**;
- **Darslar**;
- **Xabarlar**;
- **Profil**.

Azure AI A9/capabilityga qarab Xabarlar ichidagi imkoniyat bo‘lishi mumkin;
doimiy asosiy tab bo‘lishi shart emas. Mini App web dashboardning kichraytirilgan
HTML nusxasi emas: u ayni `LearnerHomeProjection`dan zarur fieldlarni oladigan
touch/WebView adapteridir.

Mini App maxsus qabul shartlari:

- Telegram safe-area va virtual keyboard primary actionni yopmaydi;
- 320pxda content loss/gorizontal page scroll yo‘q;
- active tab `aria-current="page"`;
- semantic heading va skip target;
- body text product minimumidan pastga tushmaydi;
- WebView unavailable bo‘lsa webga aniq handoff;
- inactive course course-study denialiga emas, recoveryga olib boradi;
- launch initData/session errori private va qayta urinish mumkin bo‘lgan holat.

### 7.5 Empty, error va degraded holat yozish qoidasi

Har blok quyidagilardan bittasini beradi:

1. nima ma’lum;
2. nima sababdan keyingi amal yo‘q;
3. foydalanuvchi hozir nima qila oladi;
4. tizim o‘zi kutayotgan bo‘lsa, foydalanuvchi qayta yubormasligi kerakmi;
5. help destination.

“Ma’lumot topilmadi”, `0`, spinner yoki qizil alarmning o‘zi yetarli emas.
Optional source exceptioni butun dashboardni 500 qilmaydi. Access/identity
noaniq bo‘lsa esa fail-open emas.

### 7.6 Til va copy

- “V1”, “avvalgi ko‘rinish”, “migratsiya”, “adapter” user-facing matnda yo‘q;
- `Muallif/O‘qituvchi` bitta product atamasiga birlashtiriladi;
- “Tavsiya” faqat haqiqiy recommendation policy bo‘lsa;
- “Tugallandi” lesson checklist va academic outcome uchun alohida matn;
- noma’lum level `A1` qilib to‘ldirilmaydi;
- sana o‘zbek locale/format bilan, timezone actor/product policy bo‘yicha;
- “doim”, “shaxsiylashtirilgan”, “real vaqt”, “o‘rgandingiz” kabi claimlar
  faqat tegishli contract va evidence bo‘lsa.

---

## 8. Tashqi tadqiqotdan olinadigan majburiy prinsiplar

Ushbu reja trend bloglariga emas, rasmiy standart va design-system
yo‘riqnomalariga tayandi.

### 8.1 Accessibility

- [WCAG 2.2 Understanding](https://www.w3.org/WAI/WCAG22/Understanding/)
  umumiy acceptance manbasi.
- [Reflow](https://www.w3.org/WAI/WCAG22/Understanding/reflow.html): 320 CSS px
  ekvivalentda ikki o‘lchamli data talab qilmaydigan content yo‘qolmaydi va
  gorizontal page scroll talab qilmaydi.
- [Target Size Minimum](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html):
  WCAG AA minimum 24×24 CSS px yoki spacing istisnosi; AzureLMS product targeti
  touch primary/control uchun **44px**, lekin bu WCAGning o‘zi deb yozilmaydi.
- [Focus Not Obscured](https://www.w3.org/WAI/WCAG22/Understanding/focus-not-obscured-minimum.html):
  sticky header, bottom nav va keyboard fokuslangan elementni to‘liq yashirmaydi.
- [Status Messages](https://www.w3.org/WAI/WCAG22/Understanding/status-messages.html):
  loading/success/error dinamik holati focusni o‘g‘irlamasdan assistive
  technologyga bildiriladi.
- Agar chart saqlansa, W3Cning
  [complex images](https://www.w3.org/WAI/tutorials/images/complex/) talabi
  bo‘yicha qisqa xulosa va data table/alternative beriladi. Aks holda chart
  vanity bo‘lsa olib tashlanadi.

### 8.2 Task va status dizayni

- GOV.UK
  [complete multiple tasks](https://design-system.service.gov.uk/patterns/complete-multiple-tasks/)
  patterni statusni amaliy task bilan bog‘lashni ko‘rsatadi; AzureLMSda
  list ko‘pi bilan 3 keyingi ish bilan chegaralanadi.
- GOV.UK [tag](https://design-system.service.gov.uk/components/tag/) status
  uchun, interaktiv control sifatida emas; rang ma’noning yagona tashuvchisi
  bo‘lmaydi.
- GOV.UK
  [notification banner](https://design-system.service.gov.uk/components/notification-banner/)
  favqulodda bo‘lmagan ma’lumotni alarmga aylantirmaslik uchun reference.
- GOV.UK [headings](https://design-system.service.gov.uk/styles/headings/)
  vizual kattalik va semantik heading hierarchy bir xil tartibni anglatishini
  eslatadi.
- USWDS
  [summary box](https://designsystem.digital.gov/components/summary-box/)
  foydalanuvchi contextida muhim keyingi qadamni ajratish uchun reference;
  dashboardni ko‘p rangli card gridga aylantirish uchun emas.

### 8.3 Performance va cache

- [Core Web Vitals](https://web.dev/articles/vitals) bo‘yicha field p75 target:
  LCP ≤2.5 s, INP ≤200 ms, CLS ≤0.1; mobile va desktop alohida.
- Django
  [database optimization](https://docs.djangoproject.com/en/6.0/topics/db/optimization/)
  tavsiyalari asosida `select_related`, bounded `prefetch_related`, aggregation
  va `QuerySet.explain()` dalil bilan tanlanadi.
- Django [cache framework](https://docs.djangoproject.com/en/6.0/topics/cache/)
  URL cache user/cookie scope’ini o‘z-o‘zidan xavfsiz qilmaydi. Private
  authenticated HTML shared cachega berilmaydi; expensive global health
  snapshot esa user-independent key va explicit invalidation bilan cachelanadi.

### 8.4 Security

- OWASP
  [Authorization Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html):
  deny-by-default va har requestda permission validation; `is_staff` global
  finance/PII capability degani emas.
- OWASP
  [Session Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html):
  privilege/auth transitionda session rotation, narrow lifetime va cookie
  himoyasi Mini App bootstrapga tatbiq qilinadi.
- OWASP
  [Logging Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html):
  telemetryda secret, session ID, raw PII, message va prompt yo‘q.
- OWASP
  [Business Logic Abuse](https://owasp.org/www-community/attacks/Business_logic_vulnerability):
  replay, double-submit, privilege path va impossible state’lar oddiy input
  validation bilan yopilmaydi; stateful invariant test kerak.
- Telegramning rasmiy
  [Mini App initData validation](https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app)
  contracti HMAC source-of-truthidir. HMAC Telegram actorini tekshiradi, lekin
  browser sessionni o‘zi bog‘lamaydi; AzureLMS shu sabab same-site pre-auth
  CSRF/session nonce va atomic replay consume’ni alohida qo‘shadi.

Tashqi patternlar AzureLMS business policy o‘rnini bosmaydi. Ular accessibility,
security va interaction acceptance mezonini beradi; completion/priority/role
qarori owner va canonical domainlarda qoladi.

---

## 9. Data, migration va concurrency contracti

### 9.1 Boshlang‘ich schema qarori

Projection foundation (`DASH1.1a–d`) yangi dashboard model talab qilmaydi.
Avval mavjud canonical modellardan read-only DTO chiqariladi. Faqat aniq
invariant yoki audit uchun schema qo‘shiladi.

### 9.2 Ehtimoliy additive schema

| O‘zgarish | Qachon | Qoidalar |
|---|---|---|
| `PaymentReceipt.verified_at` | **A4-owned prerequisite**, DASH1.4bdan oldin | nullable, indexed; faqat verified transitionda bir marta; immutable; `verified_by`/audit bilan atomik. Dashboard schema/writerga egalik qilmaydi |
| Mini App launch digest/nonce store | DASH1.0d | DB unique atomic create+bounded purge yoki shared Redis `SET ... NX EX`; digest, pre-auth session hash, nonce, actor, destination va expiry; consume’dan keyingi crashda retry deny/fresh relaunch; raw initData saqlanmaydi; store unavailable bo‘lsa deny, process-local memory/cache fail-open taqiqlanadi |
| explicit role preference | faqat DASH-D2 tasdiqlasa | session-first; model kerak bo‘lsa allowlisted role, actor unique, auditli POST; GET writer emas |
| dashboard product event | faqat DASH-D11 privacy qaroridan keyin | pseudonymous visit ID, event enum, action reason/version, expiry; raw URL/title/PII yo‘q |
| health snapshot | **A2/Control Center-owned prerequisite**, DASH1.4cdan oldin | Dashboard scheduler/model yaratmaydi; versionlangan selector `status/as_of/stale/source/error_code` beradi |

### 9.3 A4 prerequisite — `verified_at` va approved-payment selector contracti

Bu Dashboard migrationi emas. A4 owneri alohida PRda schema, yagona writer va
versionlangan approved-payment selectorini merge qilib qabul dalilini beradi;
DASH1.4b shundan keyin faqat selectorni o‘qiydi. Oldingi verified receiptlar
uchun verification vaqti ma’lum emas. A4 migration/writer contracti:

- `submitted_at`ni `verified_at`ga ko‘chirmaydi;
- tarixiy satrni bugungi/haftalik tasdiqlangan to‘lovga yashirin qo‘shmaydi;
- UI “verification vaqti noma’lum” yoki alohida legacy total ko‘rsatadi;
- current invariant owner — enrollment+receiptni lock qiladigan
  `PaymentReceipt.save()`dagi false→true transition yoki undan ajratilgan yagona
  low-level transition helper. U barcha supported service/admin/Bot/web/direct
  model-save yo‘lida `verified_at=now()`ni bir marta yozadi va `update_fields`ga
  maydonni qo‘shadi;
- business authorization/audit baribir `receipt_service`da; production adapter
  direct `is_verified=True; save()` qilmaydi. `QuerySet.update(is_verified=...)`
  inventoryda taqiqlanadi/guard qilinadi, chunki model invariantini chetlab o‘tadi;
- reject→resubmit yoki status reversal business policy A4 ownerida qoladi;
- timezone boundary test ownerning reporting timezone’i bilan yoziladi;
- rollout ikki bosqich: additive column+writer birinchi, payment widget OFF;
  barcha old binary/writerlar drain bo‘lib, cutoverdan keyingi verified-null 0
  ekaniga reconciliation dalil bergach widget ON. Old tarixiy null alohida qoladi.

`verified_at` faqat tekshiruv qarori vaqtini isbotlaydi. U accounting revenue
recognition vaqti, cash settlement yoki earned revenue degani emas. A4 alohida
accounting policy bermaguncha Dashboard faqat “tasdiqlangan to‘lovlar/cheklar”
deb nomlaydi, daromad/revenue deb emas.

### 9.4 Progress integrity audit

Management command yoki read-only auditor quyidagilarni beradi:

- LessonProgress/Attendance lesson course != enrollment course;
- completed distinct count > eligible denominator;
- orphan enrollment/course/cohort relation;
- duplicate semantik event (DB unique yetarli bo‘lmagan joy);
- academic state va lesson progressning imkonsiz kombinatsiyasi.

Yangi corrupt relationni faqat auditor topib qolmasligi kerak. Guard ikkala
canonical writerda majburiy: `courses/progress_service.py` va
`cohorts/attendance_service.py::upsert_attendance_and_xp`. Enrollment/course/
cohort/lesson mosligi har qanday Attendance/LessonProgress write, XP, streak,
notification yoki boshqa side effectdan **oldin** tekshiriladi. Admin, import,
Bot va direct model-save bypass inventory qilinadi; supported writer canonical
servicega yo‘naltiriladi yoki ayni invariantni buzolmaydi.

Command defaultda report-only, PII-minimized va exit code bilan. `--fix`
birinchi iterationga kirmaydi. Fix kerak bo‘lsa alohida owner-approved mapping,
dry-run, backup, receipt va reversible migration bilan.

### 9.5 Concurrency va transaction mezoni

- `verified_at` ikki verifierda faqat bitta transition receipt yaratadi;
- Mini App ayni initData/digest parallel ishlatilsa shared atomic store orqali
  ko‘pi bilan bitta session bootstrap; consume’dan keyingi har qanday retry deny
  va fresh relaunch talab qiladi; replay store unavailable bo‘lsa fail-closed;
- butun DB+cache+remote adapterlar uchun soxta “global snapshot” va’da qilinmaydi.
  Core DB projection bir version contractida o‘qiladi: zarur bo‘lsa PostgreSQL
  transaction snapshot, aks holda selectorlar `source_version/as_of` qaytaradi
  va composer mos kelmaydigan versiyani `stale/unavailable` qiladi. Har optional
  DB/cache adapter o‘z `as_of/stale` holatiga ega; eski optional signal yangi core
  action bilan fakt sifatida qo‘shilmaydi;
- role switch ikki tabda allowlisted final mode beradi, privilege qo‘shmaydi;
- destination permission projectiondan keyin revoke bo‘lsa destination rad etadi;
- SQLite unit testi yetarli emas: row-lock/unique race PostgreSQL integrationda.

Consistency integration testi selectorlar orasida enrollment/accessni mutatsiya
qiladi: transaction snapshot tanlansa butun core bir old versionni beradi;
version/as-of tanlansa mismatch aniqlanib section `stale/unavailable` bo‘ladi.
Hech qaysi holda eski access bilan yangi lesson actioni “valid” kompozitsiya
bo‘lmaydi. Optional cache snapshot mutatsiyasi o‘z sectionini partial qiladi,
core primaryni jim qayta yozmaydi.

### 9.6 Retention va privacy

Projectionning o‘zi persist qilinmaydi. Agar DASH-D11 telemetryni admit qilsa:

- visit/action ID random va qisqa retentionli;
- user ID analytics qatlamida kerak bo‘lmasa olinmaydi;
- course/message/prompt/title/name/raw URL query yozilmaydi;
- IP/user-agent product event payloadida saqlanmaydi;
- operational error log va product analytics alohida;
- deletion/retention owner policy va privacy notice bilan;
- `SystemAuditEvent` impression/click ombori sifatida ishlatilmaydi.

---

## 10. Feature flag, shadow va rollback

### 10.1 Flaglar

Tavsiya etilgan default-OFF presentation/orchestration flaglari:

- `dashboard_projection_v2` — DTOni shadow hisoblash/compare;
- `learner_home_v2` — learner renderer;
- `teacher_home_v2` — teacher renderer;
- `miniapp_home_v2` — Mini App adapter;
- `authenticated_home_router_v2` — role-aware `/` va post-login route.

Existing `frontend_v1_learning` va `frontend_v1_teacher` juda keng va
navigation/rendererga bog‘langan; yangi business truthni ular boshqarmaydi.
Flag nomi implementatsiyada registry collisionga tekshiriladi.

### 10.2 Flag ortiga yashirilmaydigan tuzatishlar

- capability/default-deny;
- private/no-store va route-exact frame/CSP;
- GET write0;
- Mini App HMAC/replay/session containment;
- foreign-course progress writer validation;
- noto‘g‘ri/fabricated metricni olib tashlash;
- immutable `verified_at` invariant.

### 10.3 Shadow contract

Shadow mode responsega yangi qiymatni ko‘rsatmaydi va state yozmaydi. U faqat
PII-free mismatch counter chiqaradi:

```text
projection_version
surface + role
reason_code_old / reason_code_new
course_count_bucket
partial_section_code
duration_ms + query_count
```

Raw course/user ID loglanmaydi. Eski qiymat noto‘g‘ri ekani ma’lum joyda
“parity” maqsad emas; expected delta fixture bilan belgilanadi.

### 10.4 Rollback

1. renderer flag OFF — eski template, yangi shared security/truth service qoladi;
2. adapter flag OFF — old URL saqlanadi, canonical projection schema drop yo‘q;
3. home-router flag OFF — explicit role URLlar saqlanadi;
4. new nullable column qoladi; old binary uni e’tiborsiz qila olishi migration
   compatibility test bilan isbotlanadi;
5. security/invariant fix hech qachon routine rollbackda bekor qilinmaydi;
6. release oldidan rollback drill old/new session, Back, reload va multi-tab
   holatida o‘tkaziladi.

---

## 11. Roadmap — 33 ta reviewable implementatsiya kesimi

### Ishlash qoidasi

Har kesimda agent quyidagi tartibni buzmaydi:

1. shu kesimning owner decision/dependencylarini tekshiradi;
2. avval failing regression yoki characterization test yozadi;
3. minimal canonical service/invariantni quradi;
4. adapterlarni birma-bir ulaydi;
5. query/write/security dalilini qayta oladi;
6. flag OFF rollbackni tekshiradi;
7. commit, marinebook va PR evidence yozadi.

Bir PR keyingi kesimga tegishli UI yoki schema “qulay bo‘lib qoldi” deb olib
kirmaydi. Exact fayl nomi implementatsiyada tabiiy ravishda o‘zgarishi mumkin;
mas’uliyat va exit mezoni o‘zgarmaydi.

### 11.0 Admission queue va qat’iy tartib

Bu jadval 2026-08-15dagi A0 foundation dalilini o‘chirmaydi. DASH1.0a — o‘sha
A0b permission contractida hozir topilgan tor regression; “yangi A0 admission”
emas. Keng product redesign bir vaqtning o‘zida ADMIT qilingan yangi launch
epic emas.

| Tartib | Kesim | Queue/status | Qachon bajariladi |
|---:|---|---|---|
| 1 | DASH1.0a | **ADMIT — existing A0b regression / stop-ship** | affected legacy dashboard/users/chats, receipt decision/foreign file yoki Bot staff release’dan oldin |
| 2 | DASH1.0b | **ADMIT — private-route maintenance** | keyingi Dashboard/private surface rolloutidan oldin; A0 platform policy sifatida |
| 3 | DASH1.0c | **ADMIT — zero-write maintenance** | Dashboard redesign va yangi authenticated GETlardan oldin |
| 4 | DASH1.0d | **ADMIT — Mini App release security gate** | Mini App yoqiladigan yoki kengayadigan release’dan oldin |
| 5 | DASH1.0e | **ADMIT — correctness containment** | yangi Dashboard renderer oldidan; noto‘g‘ri claimlar darhol yopiladi |
| 6 | DASH1.1–1.7 | **NEXT — post-launch, owner execution admissionini kutadi** | DASH1.0 ketma-ket yopilib, joriy ADMIT ishlar va owner navbati ruxsat bergach |
| — | owner contracti yo‘q domain adapteri | **HOLD** | Classbook/A4/A2/Messenger/A6/A7/SIT/A9 owner prerequisite merge+acceptancegacha |
| — | parallel canonical state/fake claim/broad staff fallback | **CUT** | qurilmaydi |

Majburiy containment tartibi: **DASH1.0a → 1.0b → 1.0c → 1.0d → 1.0e**.
Bir checkout qoidasi sabab kodlash ham shu tartibda. 1.1+ ishlarini “reja tayyor”
degan sabab bilan o‘zicha boshlash mumkin emas.

### Phase DASH1.0 — security va product-truth containment

#### DASH1.0a — Backoffice capability va PII containment

**Maqsad:** ordinary `is_staff` global learner PII, finance va receipt queue’ni
ko‘rmaydi; teacher faqat o‘z course scope’idagi ruxsatli ishga kiradi.

- **Tegadigan joylar:** `core/views.py`, `core/backoffice_sections.py`,
  `core/access.py` yoki yangi `core/backoffice_capabilities.py`,
  `cohorts/receipt_service.py`, `core/private_media_views.py`,
  `bot/middleware.py`, butun `bot/routers/staff.py` admin surface’i va uning
  `bot/services.py` selectorlari, legacy Backoffice URL/template va tests.
- **Route inventory:** test root URLConfni walk qilib `/backoffice/` ostidagi
  barcha direct va nested route’ni method/read/write/file capabilityga map qiladi:
  dashboard, receipts list+POST decision, users, chats, legacy course/lesson/exam
  editorlari, catalog/plan/cohort/member, workspace search/payments/plans/site/
  settings/groups/students/student detail/courses/course/practice writerlari,
  Control Center va uning AI/flag/runtime/dead-letter/brand/design/landing
  mutationlari, SIT va Library nested route’lari, private file/download/export
  endpointlari. `/checkout/receipt/<id>/file/`, canonical receipt service va Bot
  staff command/callbacklar ham shu matrixga kiradi. Protected route yoki method
  **unclassified=0**; broad `_is_backoffice_user` global surface uchun yakuniy
  authorization bo‘la olmaydi.
- **Contract:** alohida capabilities kamida `ops_global_view`,
  `finance_receipt_review`, `finance_cross_user_receipt_file_view`,
  `platform_stats_view`,
  `learner_pii_view`, `course_scoped_teaching`.
  Superuser/owner mapping explicit; oddiy staffga implicit global grant yo‘q.
  Receipt owner o‘z faylini ownership check bilan ko‘radi; bu finance capability
  emas va foreign receiptga yoyilmaydi.
  `ops_global_view` va `learner_pii_view` Messenger body/snippet yoki participant
  email searchini **bermaydi**. `/backoffice/chats` uchun Messenger-owned
  `support_metadata_view` policy/selector mavjud bo‘lmasa route fail-closed.
  MSG-D13 admit qilinmaguncha ordinary staff, ops, PII, finance va superuser uchun
  transcript/body/snippet/email-search access 0; Dashboard break-glass yaratmaydi.
  Capability faqat UI decoratorida emas, canonical receipt writer, private
  media reader va Bot identity/command boundaryda ham tekshiriladi.
- **Schema:** dastlab Django Permission/Group bilan; yangi custom role model
  faqat mavjud mapping yetmasa alohida ADR/migrationda.
- **Test:** anonymous, learner, assigned teacher, unassigned teacher, ordinary
  staff, finance group, ops group, superuser; list/detail/direct URL, canonical
  `verify/reject` service, receipt file, Bot `/stat`, `/cheklar`, callbacklar va
  qolgan admin handler inventorysi; learner own receipt file allow, foreign file
  deny; `/backoffice/chats`da ordinary staff/ops/PII/finance/superuser uchun
  D13siz body/snippet/email-search 0, teacher foreign room metadata 0; HTML/Bot
  outputda ruxsatsiz PII substring yo‘qligi.
- **Exit:** assigned teacher course workspace’ni saqlaydi, ammo plain staff
  global counts/revenue/recent users/receipt image yoki decisionni olmaydi;
  Messenger selectorisiz chat route deny, MSG-D13siz body/search 0;
  authorized capability exact scope’da ishlaydi; denial 403/404 yoki
  tushunarli safe recovery, login loop emas. Launch ops permission matrixi bilan
  reader/writer/Bot parity 100%.
- **Rollback:** eski keng accessga qaytilmaydi. Mapping xatosi bo‘lsa capability
  grant explicit operational change bilan; audit yoziladi.
- **Dependency:** owner DASH-D8 capability nomlari va initial assignee ro‘yxati.
  Chat metadata UI MSG1.0d selectoriga bog‘liq, ammo containment uni kutmaydi:
  selector/MSG-D13 yo‘q bo‘lsa deny/body access0.

#### DASH1.0b — authenticated private response va frame boundary

**Maqsad:** barcha learner/teacher/backoffice/Mini App private response variantlari
shared-cache va cross-route framingdan himoyalangan.

- **Tegadigan joylar:** A0/platform-owned yagona `core/private_response.py`,
  relevant decorators/middleware, `users/views.py`, `core/teacher_views.py`,
  legacy Backoffice, `bot/views.py`, Mini App security middleware. Ushbu slice
  faqat Dashboard route oilalari uchun regression matrixni yopadi; Messenger va
  Classbook o‘z roadmapida ayni helperni iste’mol qiladi, parallel policy/helper
  yaratmaydi.
- **Headers:** HTML/API success/error uchun `Cache-Control: private, no-store`;
  cookie-sensitive javob `Vary: Cookie`; sensitive redirectning landing response’i
  ham protected. Referrer policy va CSP existing global policy bilan mos.
- **Frame:** faqat exact Mini App route namespace Telegram/WebView origin policy
  bo‘yicha frameable; shu session bilan `/users/dashboard/`, auth, payment yoki
  Backoffice frameable emas.
- **Handoff:** current Mini App course/lesson/payment kabi normal web deep
  actionlariga iframe ichida navigate qilib qolmaydi. Avval Mini-App-native exact
  route mavjud bo‘lsa o‘sha ishlatiladi. Aks holda shu containment PRning o‘zida
  allowlisted named-route → external-browser handoff beriladi: Telegram
  `openLink`/supported API yoki `target="_blank" rel="noopener"` fallback;
  arbitrary URL yo‘q. External browser WebView cookie’sini ulashadi deb taxmin
  qilinmaydi: normal web session mavjud bo‘lsa destination ochiladi, cookie yo‘q
  bo‘lsa regular login + allowlisted `next` va “brauzerda qayta kirish talab
  qilinishi mumkin” degan aniq copy. URLga initData, Mini App session/digest,
  auth token, user ID yoki boshqa bearer secret qo‘shilmaydi. Seamless one-time
  browser handoff kerak bo‘lsa alohida security design/admission; DASH1.0b uni
  yashirin qurmaydi. DASH1.5 UXni kutib dead-end qoldirish mumkin emas.
- **Schema:** yo‘q.
- **Test:** legacy/V1 flag ON/OFF, 200/302/403/404/500 handler, conditional GET,
  HEAD, Mini App exact/non-exact path; har current primary/course/payment/help
  deep actioni iframe navigate emas, safe top-level handoff; JS/API unavailable
  fallback; Android/iOS/Desktop WebViewda external browser existing-cookie va
  fresh/no-cookie holati; no-cookie regular login+safe `next`, URL secret0;
  header duplication yo‘q.
- **Exit:** private route matrix 100% expected header; normal web frame deny;
  barcha supported Mini App actionlari exact Mini App route yoki safe top-level
  handoff bilan ishlaydi; route security renderer flagga bog‘liq emas.
- **Rollback:** helperni o‘chirish mumkin emas; faqat overly strict product CSP
  exact allowlist bilan tuzatiladi.
- **Dependency:** A0/platform `core/private_response.py` yagona owneri; boshqa
  product dependency yo‘q, DASH1.0a yopilgach ketma-ket bajariladi.

#### DASH1.0c — authenticated GET write0

**Maqsad:** dashboard render/reload/two-tab domain/config row yaratmaydi yoki
yangilamaydi.

- **Tegadigan joylar:** `aicontrol` settings/allowance selectorlari, frontend
  context processorlari, Site/Auth/Landing singleton loaderlari, notification
  open/read route, learner/teacher/Mini App views.
- **Pattern:** `get_or_create()`li read loader o‘rniga unsaved immutable/default
  value object; provisioning faqat explicit POST/use command yoki migrationda.
- **Schema:** yo‘q; kerak bo‘lsa data migration explicit provisioning uchun
  alohida kesim, GET fallback emas.
- **Test:** cold database, warm database, concurrent GET, reload, HEAD va two-tab;
  target table row counts va SQL write capture before/after; notification GET
  read receipt yozmaydi.
- **Exit:** domain/config `INSERT/UPDATE/DELETE=0`; response mavjud fallback bilan
  render; mutation endpoint CSRF va permission bilan.
- **Rollback:** read-only loader saqlanadi; missing config UIda unavailable yoki
  default, GET writerga qaytilmaydi.
- **Dependency:** DASH1.0b private response foundation; boshqa domain admission
  yo‘q.

#### DASH1.0d — Mini App bootstrap, replay va privileged session containment

**Maqsad:** Telegram initData faqat yangi, haqiqiy, bir martalik va mos
destinationli low-privilege session ochadi.

- **Tegadigan joylar:** `bot/views.py`, Mini App auth/service/middleware,
  settings/control surface, rate-limit helper va tests.
- **Protocol:** Telegramning rasmiy HMAC algoritmi o‘zgarmaydi; constant-time
  verify; fixed 16 KiB request-body ceiling; content-type/schema allowlist;
  one-time digest; actor binding; explicit safe destination allowlist.
- **Security envelope:** `init_data_ttl_seconds` runtime settingi 60–900 s
  (default 300), `future_skew_seconds` 0–60 s (default 30), per-account launch
  1–10/min (default 5). Runtime faqat shu hard-coded xavfsiz oraliqda o‘zgaradi;
  replay record retention kamida `TTL + skew`. Owner qiymatni auditli DB setting
  bilan toraytiradi/kengaytiradi, env fallback; algoritm/body ceiling/hard maxni
  settings yuzasi oshira olmaydi.
- **Navigation:** destination allowlist authdan keyingi top-level handoff uchun;
  u privilege guard emas va normal web route’ni iframeable qilmaydi.
- **Session:** successful learner authda `cycle_key()`. Mini App session absolute
  expiry 900–28,800 s (default 7,200), idle expiry 300–3,600 s (default 900) va
  har doim `idle < absolute`; `set_expiry()` qolgan ikkala limitning minimumiga
  qo‘yiladi. Session `miniapp_issued_at`, absolute deadline va last-seenni
  server-side saqlaydi. Mini App session markeri bor **har qanday requestda**
  absolute/idle expiry tekshiriladi va uzaytirilmaydi; faqat exact Mini App route
  activitysi last-seenni bounded intervalda yangilaydi. Normal-web top-level
  handoff frame exemption yoki idle refresh olmaydi. Bu security-session write,
  domain/config mutation emas.
  Shu middleware destination viewdan oldin fresh actor/link assurance ham
  tekshiradi: user authenticated+active, Telegram link hanuz ayni actor→user va
  `is_staff/is_superuser` hamda ops/finance/PII kabi privileged capabilitylar
  yo‘q. Learner session berilgandan keyin promotion/grant/deactivation/unlink/
  relink bo‘lsa marked session darhol `flush()` va deny; bootstrapdagi eski
  qarorga tayanilmaydi. Typed universal assurance alohida qabul qilinmaguncha bu
  fail-closed recheck Mini App va normal-web handoff requestlarining barchasida.
  Expiry/logout `flush()` qiladi; qayta kirish uchun fresh pre-auth nonce + fresh
  initData kerak, consumed digest ishlamaydi. Runtime qiymat hard envelope ichida
  auditli DB setting + env fallback; browser close persistence owner settingi
  bilan emas, yuqoridagi absolute limit bilan cheklangan. Ayni
  `CustomUser` bilan “past privilege session” yasashning o‘zi yetarli emas:
  `is_staff/is_superuser` barcha direct route’da faol qoladi. Shu sabab linked
  privileged account Mini App bootstrap’i defaultda **authdan oldin reject**.
  Kelajakdagi step-up faqat har privileged route tekshiradigan typed session
  assurance contracti alohida admitted/implemented bo‘lsa ochiladi; destination
  allowlist buning o‘rnini bosmaydi.
- **Login-CSRF/session binding:** `csrf_exempt` olib tashlanadi. Mini App landing
  GET private/no-store pre-auth session nonce va normal same-site CSRF cookie
  yaratadi; auth POST CSRF + nonce + initData talab qiladi. Atomic consume row/
  Redis value digestni pre-auth session-key hash, nonce, actor va intended
  destinationga bog‘laydi, so‘ng `cycle_key()`. Hujumchining valid initData’sini
  boshqa browser/sessionda yuborish session swap bermaydi.
- **Replay:** DB unique+atomic digest create yoki shared Redis `SET key value NX
  EX <retention>`; process-local memory va non-atomic get/set yo‘q. Atomic create
  o‘zi consume hisoblanadi va pre-auth session-key hash+nonce+actor+destinationni
  saqlaydi. Shu nuqtadan keyin session rotation/save yiqilsa ayni digest retry
  **deny**; xavfsiz recovery — fresh Mini App relaunch, fresh initData va fresh
  nonce. “Immediate idempotent success” va’dasi yo‘q. DB rowlar expiry bo‘yicha
  bounded batchda purge qilinadi, ammo `TTL+skew`dan oldin emas; Redis expiry ham
  kamida shu retention. Store xatosi/unavailable holati deny.
- **Rate:** actor/digest/IP signalining privacy-safe combinationi; yuqoridagi
  hard envelope ichida DB sozlamasi + env fallback, auditli mutation.
- **Schema:** faqat DB unique atomic-consume row (`digest`, bound session hash/
  nonce/actor/destination, `expires_at`, timestamps) yoki dedicated shared Redis
  `SET ... NX EX`; generic Django cache/process memory yo‘q. Raw initData/token
  yo‘q; DB purge runbook/metric mavjud.
- **Test:** valid, bad HMAC, expired, future, duplicate sequential/parallel,
  multi-process/PostgreSQL yoki shared Redis race, store unavailable, oversized/
  wrong content type, missing/bad CSRF yoki nonce, attacker initData’sini boshqa
  browser/sessionda swap qilish, active staff/superuser reject, safe/unsafe
  next, session rotation, frozen-clock idle/absolute boundary, logout, expiry
  keyin fresh relaunch, consume→cycle/save orasidagi faultlarda old digest reject
  va fresh digest success, DB purge boundary; learner bootstrapdan keyin
  staff/superuser promotion, ops/finance capability grant, deactivate, unlink/
  boshqa userga relink → keyingi Mini App ham normal-web handoffda flush+deny;
  exact route framing va privileged direct URL.
- **Exit:** replay yangi session/privilege bermaydi; normal learner flow ishlaydi;
  real Telegram WebView smoke evidence release oldidan.
- **Rollback:** Mini App launchni kill-switch bilan to‘xtatish mumkin; HMAC/replay/
  privileged deny yumshatilmaydi.
- **Dependency:** DASH-D9 TTL/skew/rate va privileged-account policy.

#### DASH1.0e — progress, streak, level, time va recommendation truth

**Maqsad:** mavjud rendererlar redesignni kutmasdan yolg‘on yoki noaniq metric
claim qilmaydi.

- **Tegadigan joylar:** `users/views.py`, `bot/views.py`/Bot summary, learner
  templates, My Courses copy, shell profile level, Backoffice revenue/health
  context, focused tests.
- **Changes:** `max(attendance, progress)`ga failing disjoint fixture;
  LessonProgress-only safe display yoki owner-approved policy; attendance/streak
  separate; `passed*2` hours removed; `average_progress` rost nomlanadi yoki
  removed; popular courses rost nomlanadi; unknown level A1 emas; hardcoded
  templatega uzatilmaydigan hardcoded sparkline dead contexti o‘chiriladi.
  A4-owned verification timestamp/selector yo‘qligida rendered `today_revenue`
  hide/unavailable, dormant `weekly_revenue` contexti delete; “revenue” labeli
  qayta ishlatilmaydi. Request-time `get_rag_index_status()` dashboarddan
  uziladi va health widget A2 snapshot tayyor bo‘lmaguncha unavailable. Bu kesim
  yangi payment/accounting yoki health qiymatini hisoblamaydi.
- **Schema:** yo‘q.
- **Test:** disjoint/overlap/duplicate attendance, no level, zero enrollment,
  partial/all lesson, academic incomplete, web/Mini App/Bot copy parity;
  Backoffice GETda rendered `today_revenue` yo‘q, dormant weekly/sparkline
  context yo‘q, RAG full-scan helper chaqirilmaydi.
- **Exit:** har ko‘rsatilgan qiymat formula/source/labelga ega; unavailable 0ga
  aylanmaydi; legacy va V1 bir xil truthdan foydalanadi; DASH1.4b/1.4cgacha
  noto‘g‘ri payment/revenue va health widgetlari yopiq, request-time content
  scan 0.
- **Rollback:** copy/layout rollback mumkin, noto‘g‘ri formula qaytmaydi.
- **Dependency:** DASH-D3/D4; qaror kechiksa unsafe metric olib tashlanadi.

### Phase DASH1.1 — projection foundation va role router

#### DASH1.1a — data integrity auditor va progress policy freeze

**Maqsad:** projection qurilishidan oldin real data anomaly sinfi o‘lchanadi va
eligible denominator contracti fixture bilan muzlatiladi.

- **Tegadigan joylar:** yangi `courses/progress_projection.py`, read-only
  management command, `courses/progress_service.py`,
  `cohorts/attendance_service.py::upsert_attendance_and_xp`, admin/import/direct
  write inventory, enrollment/progress/attendance/XP tests va runbook.
- **Command:** default report-only; counts + opaque IDs optional secure output;
  JSON summary CI/staging uchun; production fix yo‘q.
- **Fixtures:** active/inactive course va cohort, release qatori yo‘q (current
  implicit policy), explicit released/locked, boshqa cohort/course, completed
  keyin lock, module/lesson order, duplicate-date attendance va corrupt FK
  semantic relation. Mavjud bo‘lmagan lesson draft/archive holati yaratilmaydi.
- **Schema:** writer-level check yetarli bo‘lsa yo‘q; cross-table DB invariant
  trigger kerak bo‘lsa alohida ADR va PostgreSQL proof.
- **Writer gate:** foreign course/cohort/lesson avval reject; undan oldin yoki
  keyin Attendance/LessonProgress, XP, streak, audit-success yoki notification
  side effect bo‘lmaydi. Valid writer yo‘llari oldingi behaviorni saqlaydi.
- **Test:** har ikki canonical writer va barcha supported adapterda foreign
  relation reject, row/XP/streak/notification delta 0; admin/import/direct bypass
  characterization; valid idempotent path; concurrent PostgreSQL case.
- **Exit:** DASH-D3/D4 resolved; expected denominator/completion har fixtureda
  aniq; anomaly UIda jim clamp qilinmaydi.
- **Rollback:** command read-only; writer validation compatibility flag faqat
  old corrupt data readini saqlashi mumkin, yangi corrupt write’ni emas.
- **Dependency:** DASH1.0e containment va DASH-D3/D4 policy; yangi corrupt write
  guardi owner javobini kutib ochiq qolmaydi.

#### DASH1.1b — immutable DTO va reason vocabulary

**Maqsad:** barcha adapter uchun frameworkdan mustaqil, versionlangan projection
contract yaratish.

- **Tegadigan joylar:** `core/dashboard_contracts.py`, serialization tests,
  reason registry/documentation.
- **Schema:** yo‘q.
- **Test:** frozen dataclass/immutability, enum exhaustiveness, JSON-safe selected
  fields, caller input mapping/list keyin o‘zgartirilganda DTO o‘zgarmasligi,
  unknown route/key, duplicate/bool-as-int/bad slug/oversize/arbitrary URL/query/
  text rejection, timezone-aware timestamps va partial-state serialization.
- **Exit:** learner/teacher projection interfaces §5.3ga mos; templates ORM
  objectni to‘g‘ridan-to‘g‘ri olmaydi; version va `generated_at` mavjud.
- **Rollback:** contract version `v1` saqlanadi; field removal o‘rniga additive
  version/deprecation.
- **Dependency:** DASH1.0 containment contractlari va route registry reviewi;
  production domain adapteriga dependency yo‘q.

#### DASH1.1c — `WorkspaceHomeResolver` va capability matrix

**Maqsad:** login/root/Telegram auth foydalanuvchini to‘g‘ri workspace’ga
yo‘naltiradi, dual-role direct URLlar saqlanadi.

- **Tegadigan joylar:** `core/workspace_home.py`, frontend root view,
  `LOGIN_REDIRECT_URL` integration, auth/Telegram callback, account role switch,
  URL tests.
- **Schema:** defaultda yo‘q; role preference faqat DASH-D2 bilan explicit POST
  sessionda.
- **Test:** anonymous safe next, learner, teacher, owner, teacher+learner,
  owner+learner, revoked capability, unsafe next, query/anchor injection,
  direct learner URL, two-tab role switch.
- **Exit:** pure resolver DB mutation0; every returned route allowlisted;
  destination reauthorizes; no redirect cycle.
- **Rollback:** router flag OFF post-login legacy targetga qaytadi; explicit role
  URLs va capability fix qoladi.
- **Dependency:** DASH-D1/D2/D8.

#### DASH1.1d — query baseline, budget va fail-soft harness

**Maqsad:** projection hajm bilan linearly query ko‘paytirmaydi va optional
source failureini boshqaradi.

- **Tegadigan joylar:** learner/teacher service test harness, query capture,
  fault-injection fakes, optional dashboard observability.
- **Fixtures:** learner enrollment 0/1/10/100; teacher course/queue 0/1/10/100;
  notification/AI/XP source success/timeout/exception.
- **Test:** full rendered request query capture, SQL fingerprint, optional timeout/
  exception fakes, access-source fail-safe, PostgreSQL explain va cardinality
  comparison; budget raqami faqat shu dalildan keyin freeze.
- **Budget:** exact raqam auditdan keyin freeze; asosiy talab **O(1) query
  family**. Query count 1dan 100ga ko‘payganda enrollment/item soniga teng
  ko‘paymaydi. TTFB/load target stagingda.
- **Schema:** yo‘q.
- **Exit:** checked budget, no N+1, optional failure explicit partial state,
  access source fail-safe.
- **Rollback:** expensive optional widget kill-switch bilan olib tashlanadi;
  query regressionli renderer rollout qilinmaydi.
- **Dependency:** DASH1.1b DTO/section contracti va audit fixturelari; real domain
  adapterlar emas, fakes ishlatiladi.

### Phase DASH1.2 — learner home

#### DASH1.2a — canonical progress, course selection va primary action

**Maqsad:** learner uchun aynan bitta truthli, exact cohortli keyingi amal.

- **Tegadigan joylar:** `courses/progress_projection.py`, existing
  `resume_service.py`, `users/dashboard_service.py`, destination allowlist.
- **Logic:** meaningful activity → deterministic course; resume service exact
  lesson; active learning boshqa inactive payment issue’dan ustun. Outcome
  keyingi amali typed portdan keladi; production outcome adapteri DASH1.6d
  kelmaguncha unavailable, provisional query yozilmaydi.
- **Schema:** odatda yo‘q; meaningful activity uchun existing timestamps yetmasa
  DASH-D5 bilan explicit event dependency, taxminiy `updated_at` emas.
- **Test:** untouched/partial/multiple active, other course corrupt progress,
  no released lesson, access revoke between projection and click, same-state
  deterministic output.
- **Exit:** one primary action; destination 403/dead-end synthetic matrixda 0;
  web/Mini App/Botga bir xil reason/action ID.
- **Rollback:** `learner_home_v2` OFF; canonical corrected progress service qoladi.
- **Dependency:** DASH1.1a–d, DASH-D3/D4; pin/favorite uchun DASH-D5, ammo safe
  deterministic default uni kutmaydi.

#### DASH1.2b — learner state matrix va recovery

**Maqsad:** empty/pending/frozen/expired/no-release/complete/unavailable holatlar
dead-end bo‘lmaydi.

- **Tegadigan joylar:** learner service policy, A4/outcome port interfaces va
  fakes, projection tests. Production A4/outcome selector wiring bu kesimga
  kirmaydi.
- **Schema:** yo‘q.
- **Test:** §7.2ning har qatori, mixed states, missing optional plan,
  unknown reason, stale source, no permission.
- **Exit:** har blocking state reason code + rost description + safe action yoki
  aniq no-action; course-study denial loop 0.
- **Rollback:** unsupported adapter `unavailable` bo‘ladi; fallbackda boshqa
  domain state yozilmaydi.
- **Dependency:** DASH-D6 safe precedence fake fixtureda freeze qilinadi; runtime
  payment/outcome holatlari DASH1.6b/1.6d merge bo‘lmaguncha `unavailable`.
  Direct provisional selector taqiqlanadi.

#### DASH1.2c — task-first SSR learner UI

**Maqsad:** semantic, no-JS ishlaydigan, 320px va keyboardda qulay learner home.

- **Tegadigan joylar:** `templates/frontend_v1/dashboard.html`, shared learner
  components, scoped CSS/JS; legacy redirect/render compatibility.
- **UI:** §7.1 source order, one H1, one prominent CTA, A7gacha rost nomlangan
  ≤3 operational/recovery amal yoki A7dan keyin exact Daily Coach bundle, compact
  course rows, explicit statuses, progressive enhancement.
- **Schema:** yo‘q.
- **Test:** Django template/DOM, Node behavior, JS-off navigation, keyboard,
  focus/status semantics, 320/400% reflow, long Uzbek text, dark/forced colors.
- **Exit:** primary action ≤2 interactions va owner walkthroughda ≤30s product
  target; gorizontal content loss 0; no-JS core path ishlaydi.
- **Rollback:** renderer flag OFF; URLs/actions bir xil.
- **Dependency:** DASH1.2a/1.2b va DASH-D1; A7 yo‘q bo‘lsa §6.3 operational mode.

#### DASH1.2d — stable shell, role switch, notice va help

**Maqsad:** renderer flagi navigatsiya mental modelini o‘zgartirmaydi; dual-role
user safe switch qiladi.

- **Tegadigan joylar:** V1/legacy nav builders, account page, user menu,
  notification summary, help destinations, locale formatter.
- **Rules:** nav group stable; explicit role label; unread count only; raw feed
  yo‘q; notification read explicit POST; contextual help blocking cardda.
- **Schema:** yo‘q, preference admitted bo‘lmasa.
- **Test:** learner/teacher/owner combinations, flag ON/OFF same nav order,
  notification GET write0, Uzbek dates, JS-off drawer/noscript.
- **Exit:** visible unauthorized link 0; authorized mode one clear control;
  migration jargon user-facing DOMda 0.
- **Rollback:** shell renderer rollback mumkin; role/capability contract qoladi.
- **Dependency:** DASH1.1c va DASH1.2b; unread production wiring faqat DASH1.6c.

### Phase DASH1.3 — teacher home

#### DASH1.3a — unified typed teacher review queue

**Maqsad:** exam va assignmentni bitta scoped, deterministic ish navbatiga
birlashtirish.

- **Tegadigan joylar:** `core/teacher_dashboard_service.py`, exam/assignment
  selectors, teacher tests.
- **Order:** canonical urgency bo‘lsa explicit; aks holda event/submission time,
  kind, PK. Har kinddagi top-5ni keyin qo‘shish taqiqlanadi.
- **Schema:** yo‘q; common SQL union/pagination kerak bo‘lsa repository-compatible
  query design va explain evidence.
- **Test:** mixed old/new, equal timestamps, 100+ item pagination/bound,
  assigned/unassigned course, re-review, already resolved, revoke.
- **Exit:** global oldest/priority omission 0; query O(1); every item exact link.
- **Rollback:** teacher renderer eski listga qaytishi mumkin, scope fix qoladi;
  rollout shadow order mismatch counter bilan.
- **Dependency:** DASH1.1b/1.1d va DASH-D12; assigned-course scope DASH1.0ada
  yopilgan bo‘lishi shart.

#### DASH1.3b — active session va teacher primary action

**Maqsad:** active-session porti va teacher primary-action fallbackini qotirish;
Classbook canonical adapteri ulanganidan keyin session bo‘lsa “Hozir”da,
aks holda queue’dagi keyingi ish.

- **Tegadigan joylar:** Classbook read port/interface va fake, teacher service,
  action tests. Production Classbook query bu kesimda yozilmaydi.
- **Schema:** Dashboardda yo‘q; missing session contract bo‘lsa CB roadmapga
  dependency ochiladi, vaqt taxmin qilinmaydi.
- **Test:** fake contractda active/finished/future/no session, bir nechta open
  session va deterministic list, wrong teacher/cohort, concurrent finish/revoke
  response va queue fallback; adapter absent `unavailable`.
- **Exit:** stale session action destinationda safe denial/recovery; one primary
  action; hidden schedule claim yo‘q.
- **Rollback:** Classbook adapter unavailable bo‘lsa queue ishlaydi.
- **Dependency:** runtime session wiring faqat DASH1.6a va Classbook canonical
  selectoridan keyin; oldin interface+fake, duplicate selector yo‘q.

#### DASH1.3c — scoped teacher SSR UI va states

**Maqsad:** no-course/no-student/zero-backlog/mixed/partial holatlarda qulay,
alarmdan xoli teacher home.

- **Tegadigan joylar:** V1 teacher dashboard, legacy compatibility, shared shell,
  CSS/JS/tests.
- **Schema:** yo‘q.
- **Test:** §7.3 state’lari, no-JS, 320/400%, keyboard, long course/cohort names,
  role switch, private headers; `groups` va `quick_actions` faqat typed DTOdan,
  scoped empty/unavailable states va ORM object leakage 0.
- **Exit:** zero backlog alarm yo‘q; empty state exact next step; unauthorized
  count/name leak 0; owner walkthrough task open ≤30s target.
- **Rollback:** `teacher_home_v2` OFF; service/scope fixes qoladi.
- **Dependency:** DASH1.3a/1.3b va DASH1.1c; Classbook production signal bo‘lmasa
  typed unavailable/queue fallback.

### Phase DASH1.4 — existing owner workspace va finance truth

#### DASH1.4a — authenticated home’dan mavjud Ish stoliga integratsiya

**Maqsad:** assigned teacher course-scoped workspace’ni saqlaydi, owner/global
ops existing Ish stoliga, finance-only esa exact finance queue’ga tushadi;
parallel dashboard yo‘q.

- **Tegadigan joylar:** `WorkspaceHomeResolver`, workspace entry wrapper,
  account role switch, Backoffice links/tests.
- **Schema:** yo‘q.
- **Test:** owner, ops, finance-only, assigned teacher+staff, unassigned ordinary
  staff, revoked group, workspace flag OFF, direct legacy `/backoffice/` va
  course workspace deep link.
- **Exit:** assigned teacher scoped course authoringga kira oladi; authorized
  owner/ops existing Ish stoliga; finance-only exact finance queue’ga va boshqa
  PII’siz; flag redirect unrelated course-authoring flagga bog‘liq emas.
- **Rollback:** router OFF; direct workspace URL saqlanadi; capability qoladi.
- **Dependency:** DASH1.0a va BACKOFFICE-03 ownershipi.

#### DASH1.4b — A4 approved-payment selectorini integratsiya qilish

**Maqsad:** DASH1.0eda yashirilgan noto‘g‘ri `today_revenue` o‘rniga, A4 qabul
qilgan versionlangan selector orqali verification vaqtiga tayangan
“tasdiqlangan to‘lovlar/cheklar” signalini xavfsiz ko‘rsatish. Revenue/accounting
claimi bu slice scope’iga kirmaydi.

- **A4 prerequisite (bu slice’dan tashqari):** §9.3dagi nullable immutable
  `verified_at`, barcha service/admin/Bot/web/direct writer fence’i, old binary
  drain, concurrency/reconciliation va versionlangan approved-payment selector
  alohida A4 PRda merge qilingan va owner tomonidan qabul qilingan bo‘ladi.
- **Tegadigan joylar:** Dashboard A4 adapteri, Backoffice projection/template va
  selector contract/fault/copy tests. PaymentReceipt model, migration va writer
  bu PRda o‘zgarmaydi.
- **Schema:** Dashboardda yo‘q.
- **Test:** selector fresh/stale/unavailable, historical-null alohida, timezone
  day/week edge, permission, A4 contract version mismatch va no guessed backfill;
  DOMda “revenue/daromad” claimi yo‘q.
- **Exit:** faqat A4 selector bergan cutoverdan keyingi verification count/summa;
  historical unknown alohida; `submitted_at` ishlatilmaydi; prerequisite
  acceptance bo‘lmasa widget OFF/unavailable.
- **Rollback:** adapter/widget hide; A4 invariant va schema saqlanadi, eski
  formula qaytmaydi.
- **Dependency:** A4 prerequisite merge+acceptance va DASH-D10 historical/
  accounting label qarori.

#### DASH1.4c — A2/Control Center health selectorini integratsiya qilish

**Maqsad:** owner dashboard refresh RAG/contentni to‘liq scan qilmasdan,
DASH1.0eda yashirilgan health widgetini persisted snapshot bilan restore qilish;
dead hardcoded context qaytmaydi.

- **A2 prerequisite (bu slice’dan tashqari):** Control Center owneri scheduled/
  explicit refresh, lease, retention va persisted/cached snapshotni yaratadi;
  versionlangan selector `status/as_of/stale/source/error_code` qaytaradi. A2 PR
  merge va acceptance’siz Dashboard healthni restore qilmaydi.
- **Tegadigan joylar:** Dashboard A2 selector adapteri, Backoffice projection/
  template, legacy dead context removal va contract/fault tests. Dashboard yangi
  health model, scheduler yoki refresh lease yaratmaydi.
- **Schema:** Dashboardda yo‘q.
- **Test:** fresh/stale/missing/failed snapshot, request query/CPU budget,
  contract version mismatch, permission va unavailable copy.
- **Exit:** dashboard request O(1) snapshot read; no full RAG scan; no hardcoded
  dead sparkline context; `as_of` ko‘rinadi.
- **Rollback:** health widget unavailable/hidden; request-time scan qaytmaydi.
- **Dependency:** A2/Control Center prerequisite merge+acceptance.

### Phase DASH1.5 — Mini App va Bot parity

#### DASH1.5a — field-selective shared learner projection

**Maqsad:** Mini App home/courses/profile faqat kerakli projection sectionini
oladi; web bilan action/reason bir xil.

- **Tegadigan joylar:** `users/dashboard_service.py`, field/section selector,
  `bot/views.py`, Mini App templates.
- **Schema:** yo‘q.
- **Test:** each tab query budget; active/pending/frozen/expired; identical
  action kind/reason/source across web/Mini App; hidden section query qilinmaydi.
- **Exit:** `_miniapp_context` web view helper import qilmaydi; adapter business
  formula yo‘q; no dead inactive link.
- **Rollback:** Mini App renderer flag OFF; corrected shared service qoladi.
- **Dependency:** DASH1.0d security, DASH1.1b DTO va DASH1.2 learner service.

#### DASH1.5b — WebView UX, recovery va accessibility

**Maqsad:** Telegram WebView ichida readable, touch-safe, keyboard/safe-area
barqaror Mini App.

- **Tegadigan joylar:** Mini App base/home/course/profile templates, scoped CSS/
  JS, web fallback handoff.
- **Schema:** yo‘q.
- **Test:** Android/iOS imkon doirasida Telegram WebView, 320/360/390 widths,
  font scaling, keyboard open/close/rotate, offline/static failure, `aria-current`,
  focus/status, back navigation.
- **Exit:** primary CTA yopilmaydi; body text readable; active tab semantic;
  recovery web URL safe; native smoke evidence artifact.
- **Rollback:** enhanced JS/CSS rollback; semantic server HTML qoladi.
- **Dependency:** DASH-D7 tab/AI qarori va B3.6 theme ownershipi.

#### DASH1.5c — Bot summary parity

**Maqsad:** Bot dashboard summary projectionni format qiladi, o‘z progress yoki
priority qoidasini ishlatmaydi.

- **Tegadigan joylar:** Bot learner overview service/handlers, shared DTO
  serializer, callback/deep-link tests.
- **Schema:** yo‘q.
- **Test:** web/Mini App/Bot golden matrix, Telegram text/callback limits,
  revoked enrollment, stale callback, unavailable optional source.
- **Exit:** reason/action parity 100%; callback destination reauthorizes;
  no user/title/raw query telemetry.
- **Rollback:** Bot summary old commandga fallback qilishi mumkin, corrected
  progress formula qaytmaydi.
- **Dependency:** DASH1.0a Bot capability containment, DASH1.5a va supported
  callback/deep-link security contracti.

### Phase DASH1.6 — domain-owned adapterlar

Bu phase foundationni kutadi. Bir dependency tayyor bo‘lmasa item
`unavailable` qoladi; dashboard parallel state yasamaydi.

#### DASH1.6a — Classbook exact session adapteri

- **Maqsad:** learner/teacher active session actioni canonical Classbook state.
- **Tegadigan joylar:** Classbook read contract, dashboard adapters/tests.
- **Schema:** Dashboardda yo‘q.
- **Test:** actor/cohort/teacher scope, 0/1/2+ open session (turli chat/cohort),
  deterministic list/no omission, start/finish race, expired session,
  destination revoke, absent adapter.
- **Exit:** session vaqt/holati to‘qilmaydi; bitta bo‘lsa exact action, ko‘p
  bo‘lsa barcha ruxsatli session saqlangan list actioni; both role parity.
- **Rollback:** adapter kill-switch/unavailable; Classbook state tegmaydi.
- **Dependency:** Classbook ownerning scoped versionlangan read selectori
  merge+acceptance va DASH1.3b port contracti.

#### DASH1.6b — A4 payment/access recovery adapteri

- **Maqsad:** pending/frozen/expired holat canonical entitlement/payment
  service’dan reason va action oladi.
- **Tegadigan joylar:** A4 selector/DTO, learner service, payment routes/tests.
- **Schema:** Dashboardda yo‘q.
- **Test:** first purchase/renewal, pending receipt, rejected, frozen, expired,
  another active course, price/plan unavailable.
- **Exit:** dashboard payment status yozmaydi; active learning unrelated blocker
  bilan to‘silmaydi; exact recovery.
- **Rollback:** payment adapter unavailable; unsafe direct mutation yo‘q.
- **Dependency:** A4 ownerning entitlement/recovery selector acceptance’i,
  DASH1.2b state porti, DASH-D6 va kerakli payment truth uchun DASH1.4b
  prerequisite.

#### DASH1.6c — Messenger/notification summary adapteri

- **Maqsad:** unread/help signali canonical unread contractdan; raw body yo‘q.
- **Tegadigan joylar:** Messenger/notification read selector, dashboard header/
  help adapter, tests.
- **Schema:** Dashboardda yo‘q; Messenger roadmapdagi receipt/unread modelga
  dependency.
- **Test:** unread count, hidden/unauthorized room, read GET write0, explicit
  read command, body/name absence, source unavailable.
- **Exit:** count/typed action only; snippet/body/prompt leak 0; dashboard visit
  unreadni tozalamaydi.
- **Rollback:** count unavailable/hidden; Messenger state tegmaydi.
- **Dependency:** Messenger ownerning canonical unread selector acceptance’i va
  DASH1.2d typed notice/help contracti.

#### DASH1.6d — A6 Outcome Ledger adapteri

- **Maqsad:** faqat admitted A6 outcome/mastery evidence’ini typed optional
  section va canonical keyingi amal sifatida ulash.
- **Tegadigan joylar:** A6 public read selector/version contracti, Dashboard A6
  adapteri, learner composition registry va contract tests.
- **Schema:** Dashboardda yo‘q.
- **Test:** adapter absent/disabled/denied/stale/success, actor/course scope,
  evidence version mismatch, destination revoke va partial failure.
- **Exit:** A6siz mastery/completion/certificate claim yo‘q; A6 qaytargan label,
  evidence va action qayta hisoblanmaydi.
- **Rollback:** A6 adapteri OFF/unavailable; core learner flow qoladi.
- **Dependency:** A6 owner admission, versionlangan selector merge+acceptance.

#### DASH1.6e — A7 Daily Coach adapteri

- **Maqsad:** A7ning exact versionlangan uch-item `DailyCoachBundle`ini Dashboardga
  o‘zgartirmasdan ulash.
- **Tegadigan joylar:** A7 public plan selector, `WorkspaceNextActionPolicy`,
  Dashboard A7 adapteri/renderer va parity tests.
- **Schema:** Dashboardda yo‘q.
- **Test:** absent/disabled/stale/denied/success, aynan 3 item, stable order,
  duplicate primary/item contract violation → Coach unavailable va primary
  saqlanishi, destination revoke, A7 kill-switch va web/Mini App parity.
- **Exit:** Dashboard rerank/truncate/append qilmaydi; A7siz personalized “Bugungi
  reja” yo‘q; safe default primaryni alohida saqlaydi; preemption faqat keyingi
  owner-approved versionlangan policy bilan.
- **Rollback:** A7 section OFF/unavailable; pre-A7 operational blok rost nomda
  qoladi, core primary ishlaydi.
- **Dependency:** A7 owner admission va primary identity/dedupe’ni qabul qiladigan
  Daily Coach selector acceptance. Safe defaultdan boshqa policy alohida ADR.

#### DASH1.6f — SIT inquiry adapteri

- **Maqsad:** faqat SIT canonical inquiry lifecycle’idan kelgan ruxsatli learner/
  owner actionni typed optional section sifatida ko‘rsatish.
- **Tegadigan joylar:** SIT public read selector/version contracti, Dashboard SIT
  adapteri, role/scope va destination tests.
- **Schema:** Dashboardda yo‘q.
- **Test:** absent/disabled/denied/stale/success, learner ownership, owner scope,
  closed/reopened inquiry, foreign inquiry, destination revoke va partial fail.
- **Exit:** SIT lifecycle’siz fake task/deadline yo‘q; raw inquiry text yoki PII
  Dashboard DTO/telemetryga kirmaydi.
- **Rollback:** SIT adapter OFF/unavailable; SIT state tegmaydi.
- **Dependency:** SIT roadmap admission va versionlangan selector acceptance.

#### DASH1.6g — AI capability adapteri

- **Maqsad:** AI availabilityni va’da yoki provider chaqiruvisiz, A8/A9/AI
  Control bergan typed capability sifatida ulash.
- **Tegadigan joylar:** AI capability selector/version contracti, Dashboard AI
  adapteri, entitlement/quota/kill-switch copy va tests.
- **Schema:** Dashboardda yo‘q.
- **Test:** unavailable/kill/quota/entitlement deny/allow/stale, provider down,
  selector timeout, privacy va destination reauthorization.
- **Exit:** A9siz premium AI claim yo‘q; Dashboard GET providerga so‘rov yubormaydi
  yoki allowance yaratmaydi; denied/unavailable fake zero emas.
- **Rollback:** AI adapter OFF/unavailable; core learning action qoladi.
- **Dependency:** A8 budget gate, A9/AI Control owner admission va selector
  merge+acceptance.

### Phase DASH1.7 — quality, staged release va cleanup

#### DASH1.7a — performance, fault va operational telemetry gate

- **Maqsad:** query/latency/fault budgetlarini representative dalil bilan
  muzlatish va PII-free operational kuzatuvni ishga tayyorlash.
- **Tegadigan joylar:** query/fault harness, observability adapteri, effective
  operational threshold config, PostgreSQL CI va performance runbook.
- **Schema:** defaultda yo‘q; product event schema DASH-D11siz yo‘q.
- **Test:** §12.4 va §13 fault matrixi, 0/1/10/100 cardinality, timeout/cache/flag/
  telemetry outage, PostgreSQL `EXPLAIN`, label allowlist va load profile.
- **Exit:** DASH1.1dda freeze qilingan budgetlar PASS; O(1) family; PII label 0;
  security source fail-safe, optional source fail-soft; alert dry-run evidence.
- **Rollback:** optional telemetry exporter OFF; security checks qoladi;
  presentation legacyga qaytishi mumkin.
- **Dependency:** DASH1.1d va DASH-D11 (faqat product events uchun).

#### DASH1.7b — accessibility, browser, native va usability qabul

- **Maqsad:** learner/teacher/Mini App/Bot yuzalarini real keyboard, AT, browser
  va Telegram WebViewda product vazifalari bilan qabul qilish.
- **Tegadigan joylar:** semantic templates/CSS/JS fixes, E2E/browser/native test
  artifacts, accessibility va owner walkthrough checklistlari.
- **Schema:** yo‘q.
- **Test:** §13.1–13.5ning securitydan tashqari UI ssenariylari, 320–1440px,
  200/400%, JS-off, keyboard, NVDA/VoiceOver imkon doirasida, WebView, long Uzbek
  copy va five-persona ≤2 interaction/≤30s product target.
- **Exit:** critical accessibility 0, content loss 0, core no-JS path ishlaydi,
  native/AT dalil va owner usability qabul yozuvi mavjud.
- **Rollback:** faqat enhanced presentation; semantic server fallback va
  corrected contract qoladi.
- **Dependency:** DASH1.2c, 1.3c, 1.5b va barcha ishlatiladigan adapterlar.

#### DASH1.7c — staged rollout va rollback drill

- **Maqsad:** yangi Dashboardni shadowdan default ONga kuzatiladigan, qaytariladigan
  bosqichlarda olib chiqish.
- **Tegadigan joylar:** feature registry, release/rollback runbook, cohort config,
  support playbook va release evidence.
- **Schema:** yo‘q; cohort assignment existing flag infrastructure orqali.
- **Bosqichlar:** local fixtures → CI SQLite/PostgreSQL → shadow staff → owner
  account → internal learner/teacher cohort → bounded percent → default ON.
- **Test:** flag ON/OFF, mixed old/new session, Back/reload/two-tab, threshold
  breach, rollback receipt, destination compatibility va security invariants.
- **Exit:** stop-ship 0; DASH-D13 cohort/stable threshold tasdiqlangan; owner
  go/no-go, support runbook va muvaffaqiyatli rollback drill.
- **Rollback:** last safe renderer/router; authorization/cache/data invariant
  ochilmaydi; cause va receipt auditda.
- **Dependency:** DASH1.7a/1.7b va owner DASH-D13.

#### DASH1.7d — stable-window legacy cleanup

- **Maqsad:** faqat qabul qilingan stable windowdan keyin ishlatilmaydigan legacy
  Dashboard renderer/context/flaglarni kichik PRda olib tashlash.
- **Tegadigan joylar:** deprecation ledger, unused template/view/context/flag,
  route coverage va docs. Canonical domain schema bu PRga kirmaydi.
- **Schema:** yo‘q; eski schema drop alohida owner-approved release.
- **Test:** `rg` reference inventory, old bookmark/deep-link compatibility,
  route/flag matrix, full suite va migration compatibility.
- **Exit:** fallback traffic 0, support-window incident 0, owner cleanup sign-off;
  kerakli compatibility redirectlari saqlangan.
- **Rollback:** cleanup commit revert yoki renderer artifact restore; security va
  data invariantga tegilmaydi.
- **Dependency:** DASH1.7c default ONdan keyingi DASH-D13 stable window.

### 11.1 Phase dependency grafigi

```text
DASH1.0a ─┐
DASH1.0b ─┼─> DASH1.1 contracts/router/budget ─┬─> DASH1.2 learner ─┐
DASH1.0c ─┤                                    ├─> DASH1.3 teacher ├─> DASH1.5 Mini App/Bot ─┐
DASH1.0d ─┤                                    └─> DASH1.4 owner   ┘                         │
DASH1.0e ─┘                                                                                 ├─> DASH1.7a perf
          owner prerequisites: Classbook/A4/A2/Messenger/A6/A7/SIT/A9 ─> DASH1.6 adapters ─┘
                                                                                            ↓
                                                              DASH1.7b UX/AT → 1.7c rollout → 1.7d cleanup
```

Security kesimlari o‘zaro kichik PRlarda parallel audit qilinishi mumkin, lekin
bitta checkout qoidasi sabab branch/implementation ketma-ket. DASH1.2–1.4
shared contract merge bo‘lmasdan boshlanmaydi. DASH1.5 ham, DASH1.6 ham tegishli
adapter/UI acceptance bilan DASH1.7ga kiradi; biri ikkinchisini almashtirmaydi.

---

## 12. KPI, telemetry va performance budget

### 12.1 Bitta asosiy KPI

`dashboard_valid_next_action_success_rate`

- **Denominator:** dashboard projection canonical primary action bergan eligible
  visitlar.
- **Numerator:** foydalanuvchi primary actionni ochib, 10 daqiqa ichida
  authorized destination yoki domain-owned success receiptga yetgan visitlar.
- **Success emas:** karta ko‘rildi, oddiy click, sahifada qolish vaqti yoki
  destination 403/404.
- **Segment:** role, surface (web/Mini App/Bot), enrollment/action reason;
  kichik guruh privacy threshold ostida alohida ko‘rsatilmaydi.
- **Target:** avval baseline olinadi; owner baseline ko‘rmasdan foiz o‘ylab
  topilmaydi.

DASH-D11 consent/retention/provider qarori yopilmaguncha bu KPI production
foydalanuvchi eventlaridan hisoblanmaydi. Ungacha numerator/dead-end faqat
synthetic E2E reportida; productionda “success” yoki click trail yig‘ilmaydi.

### 12.2 Guardrail metriclar

| Guardrail | Target |
|---|---|
| cross-user/cross-role data leak | **0** |
| authenticated GET business/config write | **0** |
| primary CTA access-denied/dead-end | synthetic matrixda **0** |
| identical state → identical primary action | **100%** |
| web/Mini App/Bot reason/action parity | **100%** supported statesda |
| optional source failure fake `0` ko‘rsatishi | **0** |
| teacher unified queue oldest/priority omission | **0** |
| Mini App replay yangi session/privilege berishi | **0** |
| private response without expected cache/frame policy | **0** |
| raw name/course/message/prompt/token/full URL query telemetryda | **0** |
| LCP field p75 | ≤2.5 s mobile va desktop alohida |
| INP field p75 | ≤200 ms |
| CLS field p75 | ≤0.1 |

Usability product targeti: besh persona vazifasida primary next actionni
**≤2 interaction va ≤30 soniya**da topish. Bu WCAG talabi emas va owner/native
walkthroughsiz PASS deb belgilanmaydi.

### 12.3 Operational telemetry

Product consent/retention qaroridan oldin faqat quyidagi aggregate operational
signals ruxsat:

- `dashboard_projection_duration_ms{surface,role,version}` histogram;
- `dashboard_query_count{surface,role,section}` histogram;
- `dashboard_partial_total{section,reason}` counter;
- `dashboard_projection_error_total{surface,error_class}` counter;
- `dashboard_cache_policy_violation_total{route_family}`;
- `miniapp_launch_denied_total{reason}` security counter.

`dashboard_action_deadend_total` va `workspace_route_total` DASH-D11gacha faqat
synthetic CI/load reportida mavjud; ular production user behavior eventiga
aylantirilmaydi. D11 qabul qilinsa ham payload allowlist, retention va privacy
threshold alohida testlanadi.

Labelda user/course/enrollment/message ID, email, name, title, prompt, token,
full path/query yo‘q. High-cardinality exception text labelga kiritilmaydi.

### 12.4 Query budgetni muzlatish usuli

Auditdagi lokal sonlar production benchmark emas. DASH1.1d quyidagi controlled
test bilan budgetni isbotlaydi:

1. fresh temp DB va warm singleton variantlari ajratiladi;
2. 0/1/10/100 active enrollment va teacher queue fixturelari;
3. har surface uchun requested sections aniq;
4. session/auth/context processor querylari alohida ko‘rsatiladi;
5. SQL fingerprintlar N+1 family bo‘yicha sanaladi;
6. SQLite correctness va PostgreSQL execution/explain alohida;
7. `force_login()`dan keyingi to‘liq GET va template render birga o‘lchanadi.

Quyidagi raqamlar **PROVISIONAL** — ular DASH1.1d baseline/explain dalilidan
keyin tech review bilan freeze qilinmaguncha release gate yoki koddagi doimiy
constant emas:

| Route | Maksimal SQL | Hajm invariant |
|---|---:|---|
| role-aware default redirect | 3 | role soniga bog‘liq emas |
| learner home | 16 | 1 va 50 enrollmentda bir xil |
| teacher home | 14 | 1 va 100 queue rowda bir xil |
| Mini App home | 12 | 1 va 50 enrollmentda bir xil |
| existing Backoffice workspace home | 18 | Dashboard reform regressiya qilmaydi |

Bu provisional targetga xavfsizlik yoki to‘g‘ri ma’lumotni chetlab o‘tib
erishilmaydi.
Canonical selector sabab target o‘zgarishi kerak bo‘lsa exact SQL fingerprint,
`EXPLAIN`, alternativ va owner/tech review bilan hujjatlashtiriladi; testni jim
bo‘shatish mumkin emas.

Majburiy invariant: 1dan 100 itemga o‘tganda query count item soni bilan
linearly o‘smaydi. Bounded two-step prefetch acceptable; per-enrollment
`active_plan()` yoki per-peer aggregation acceptable emas.

Server uchun boshlang‘ich **PROVISIONAL** target: projection/request p95 ≤500 ms,
p99 ≤1 s, field p75 TTFB ≤800 ms, 5xx <0.5%; boshlang‘ich alert p95 >500 ms
15 daqiqa, 5xx >1% 5 daqiqa, partial projection >2% yoki har qanday redirect
loop. DASH1.7a representative baseline olgach owner/ops effective qiymatni
tasdiqlaydi. Operational threshold code-hardcoded bo‘lmaydi: audited DB setting
+ env fallback + validator; safety envelope p95 200–2000 ms, p99 500–5000 ms,
5xx 0.1–5%, partial 0.5–20%, window 1–60 daqiqa. Effective config Control
Centerda ko‘rinadi. CWVdagi LCP/INP/CLS esa §12.2dagi tashqi standard targeti,
bu operational tuning bilan yumshatilmaydi.

### 12.5 Frontend budget

- initial dashboard core action server-rendered, JSga qaram emas;
- dashboard-specific JS compressed target DASH1.2c baseline’dan keyin freeze;
- above-the-fold image hero kerak emas; avatar/media lazy va dimensioned;
- font/layout shift CLS targetni buzmaydi;
- optional widget core action LCP/TTFBni kutmaydi;
- third-party script dashboard release scope’iga kirmaydi.

Full uncompressed HTML limitlari: learner/teacher **≤64 KiB**, Mini App home
**≤32 KiB**. Auditdagi empty HTML learner V1 22,824, teacher V1 18,593,
legacy Backoffice 14,430 va Mini App 8,315 bayt edi; bu faqat starting signal,
real multi-item/long-text fixture ham limitdan o‘tadi. Secondary course/queue
listi bounded va pagination/handoffga ega.

---

## 13. Majburiy test va qabul matrixi

### 13.1 End-to-end product ssenariylari

| # | Ssenariy | Kutilgan dalil |
|---:|---|---|
| 1 | anonymous protected dashboardga kiradi | safe login `next`; open redirect yo‘q |
| 2 | enrollmenti yo‘q learner | catalog/onboarding; fake progress yo‘q |
| 3 | active, untouched learner | first eligible lesson exact cohort |
| 4 | active, partial learner | last meaningful incomplete lesson |
| 5 | bir nechta active course | deterministic recent actionable primary; barcha course bounded list/pagination orqali reachable, bir DOMga cheksiz render qilinmaydi |
| 6 | active, released lesson yo‘q | honest blocked/help; denial loop yo‘q |
| 7 | pending payment | receipt/status recovery, boshqa active course to‘silmaydi |
| 8 | frozen access | canonical reason/recovery |
| 9 | expired access | renewal/plan recovery |
| 10 | lesson requirements complete | canonical exam/outcome/certificate next |
| 11 | attendance va LessonProgress disjoint | owner policy bo‘yicha exact, alohida metrics |
| 12 | streak va attendance turli | copy/action bir-birini almashtirmaydi |
| 13 | unread notification mavjud | dashboard GET read yozmaydi; body feed yo‘q |
| 14 | AI kill/quota/entitlement deny | unconditional AI claim/tab/action yo‘q |
| 15 | teacherga course biriktirilmagan | safe no-course next step |
| 16 | teacher groupi bor, student yo‘q | empty group state, alarm yo‘q |
| 17 | exam+assignment mixed queue | global deterministic order, exact link |
| 18 | teacher backlog 0 | success/empty state, warning banner yo‘q |
| 19 | dual-role staff/teacher/learner | safe role switch, no redirect cycle |
| 20 | learner/ordinary staff/ops/PII/finance direct global Backoffice va chats | unauthorized PII 0; MSG-D13siz body/snippet/email search0; comprehensible 403/404/recovery |
| 21 | same learner web/Mini App/Bot | reason/action/source parity |
| 22 | GET/reload/HEAD/two tab | domain/config write0 |
| 23 | optional source unavailable | explicit unavailable, core action ishlaydi |
| 24 | flag OFF rollback | old URL/data/session saqlanadi, security qoladi |
| 25 | Mini App replay/future/expired initData yoki expired/logout session | deny; old digest privilege/session yaratmaydi; fresh relaunchgina ishlaydi |
| 26 | linked staff/superuser bootstrap yoki learner sessiondan keyingi promotion/capability grant/deactivate/relink | bootstrap reject yoki keyingi marked requestda flush+deny; normal-web handoff ham privilege ishlatmaydi |
| 27 | Mini Appdan normal web deep action: existing-cookie va fresh/no-cookie external browser; ayni cookie bilan iframe urinish | normal page frameable emas; native route afzal; external browser session bo‘lsa exact destination, bo‘lmasa regular login+safe `next`; URL token/initData0 |
| 28 | historical verified receipt | tasdiqlangan-to‘lov davriga guessed timestamp bilan kirmaydi; revenue claim yo‘q |
| 29 | concurrent double verification | bitta immutable `verified_at`/receipt |
| 30 | foreign-course progress anomaly | audit signal; percent clamp bilan yashirilmaydi |
| 31 | 0/1/10/100 enrollment/queue | query family O(1), budget PASS |
| 32 | projectiondan keyin permission revoke | destination fresh check bilan deny |
| 33 | learner/teacher uchun bir nechta open Classbook session | `.first()` emas; deterministic session list actioni, hech biri yo‘qolmaydi |

### 13.2 Permission matrix

Har protected route family uchun quyidagi actorlar sinov qilinadi:

| Actor | Learner home | Teacher home | Course workspace | Global ops home | Own receipt file | Finance queue / foreign file / decision | Other course |
|---|---:|---:|---:|---:|---:|---:|---:|
| anonymous | login | login | login | login | login | login | login |
| learner | own | deny | deny | deny | own only | deny | deny |
| assigned teacher | explicit learner mode bo‘lsa own | assigned | assigned course | deny | own only | deny | deny |
| unassigned ordinary staff | own bo‘lsa | deny | deny | deny | own only | deny | deny |
| finance capability | own bo‘lsa | faqat alohida assignment bilan | faqat alohida assignment bilan | deny | own only | allow | deny |
| ops/global owner capability | own mode | policy bo‘yicha | policy bo‘yicha | allow | own only | faqat finance capability bo‘lsa | policy bo‘yicha |
| superuser | allow | allow | allow | allow | allow, audited | allow, audited | allow, audited |
| inactive user | deny | deny | deny | deny | deny | deny | deny |

“Link ko‘rinmaydi” permission testi emas; direct URL, crafted PK, changed query,
stale projection va concurrent revoke ham sinaladi.
Own-file allow `receipt.enrollment.student_id == actor.id` ownershipiga tayanadi;
u cross-user finance capability emas. Har actor uchun own receipt va foreign
receipt alohida fixture bo‘ladi.
“Global ops home allow” Messenger transcript/body/snippet/email searchini
anglatmaydi. MSG-D13 yo‘q holatda ordinary staff, ops, PII, finance va superuser
uchun body access0; chat metadata ham Messenger-owned scope selectoridan.

### 13.3 Response/security matrix

Route family × status × renderer bo‘yicha:

- GET/HEAD 200;
- login 302;
- forbidden 403;
- object hidden 404;
- form/launch bad request 400;
- rate 429;
- controlled error 500.

Tekshiriladi: cache-control, `Vary`, CSP/frame, content type, bodyda secret/PII,
CSRF mutation, safe `next`, session rotation va referrer policy.

### 13.4 Browser, device va assistive technology matrixi

- widths: 320, 360, 390, 768, 1024, 1280, 1440 CSS px;
- desktop: current Chrome, Firefox, Edge;
- mobile: Android Chrome, iOS Safari imkon bo‘lsa;
- Telegram Android/iOS WebView imkon bo‘lsa;
- keyboard-only; JS disabled;
- 200% text va 400% browser zoom/reflow;
- NVDA + Firefox/Edge; VoiceOver imkon bo‘lsa;
- light/dark; reduced motion; forced colors/high contrast;
- slow network, offline static asset, Back/reload/multi-tab;
- long Uzbek names, no avatar, 0/1/100 item;
- mobile keyboard open/close/rotate va safe-area.

### 13.5 Accessibility assertions

- exactly one meaningful H1;
- logical heading hierarchy;
- skip link working target;
- landmark/nav accessible name;
- active route `aria-current`;
- dialog/drawer Escape, focus trap va openerga return;
- status live region only when needed, duplicate announcement yo‘q;
- 24×24 WCAG target minimum/spacing; primary touch target product 44px;
- color-only status yo‘q;
- 320px reflow/content loss 0;
- visible focus sticky header/bottom nav ortida qolmaydi;
- chart bo‘lsa text/table alternative; vanity chart removed.

#### Besh persona usability fixture’i

“Besh persona” erkin demo emas; har qabulda ayni vazifa va start state ishlatiladi:

| Persona | Boshlang‘ich holat | Topshiriq | PASS |
|---|---|---|---|
| yangi learner | enrollment yo‘q, web | o‘qishni boshlash yo‘lini topish | catalog/onboarding exact entry ≤2 interaction, ≤30s; fake 0% yo‘q |
| multi-course learner | ikki active course, faqat bittasida recent activity | to‘xtagan joyidan davom etish | ayni course/cohort/lesson ≤2 interaction, ≤30s |
| blocked Mini App learner | pending yoki frozen access, boshqa active course ham bor | muammoni tushunish va xavfsiz recovery | blocker faqat tegishli pathda; active course dead-end emas; top-level handoff ishlaydi |
| assigned teacher | active Classbook + mixed exam/assignment queue | live sessionga qaytish, keyin eng eski ruxsatli ishni ochish | exact scoped destinations; foreign learner/course leak 0 |
| multi-role finance actor | learner + assigned teacher + finance capability, global ops yo‘q | learner→teacher mode’ga o‘tish, keyin exact finance queue/foreign receipt workflow’ni ochish | ikkala role switch ishlaydi; finance queue/file/decision allow; global ops va unrelated course deny; redirect loop 0 |

Moderator task wordingida destination nomini aytmaydi. Interaction va vaqt bilan
birga xato klik, 403/404, yordam so‘rash va foydalanuvchi izohi yoziladi; owner/
native walkthroughsiz PASS qo‘yilmaydi.

### 13.6 Fault injection

Har optional selector uchun timeout, exception, empty va stale; core selector
uchun database/access failure. Qo‘shimcha:

- Redis/cache unavailable;
- telemetry sink unavailable;
- notification/AI/Classbook adapter exception;
- session store race;
- duplicate Mini App launch;
- payment verify transaction rollback;
- feature flag service unavailable.

Optional source fail-soft, access/identity fail-safe. Telemetryning ishlamasligi
dashboardni yiqitmaydi va requestni qayta yozishga majbur qilmaydi. Flag registry/
DB override unavailable bo‘lsa presentation/orchestration flaglari declared-safe
OFF/legacy rendererga tushadi; capability, private-cache, replay va boshqa
unconditional security guardlar esa ON/fail-safe qoladi. Outage securityni
legacy keng accessga qaytarmaydi.

### 13.7 Minimal avtomatlashtirilgan command set

Har slice o‘z focused testini qo‘shadi. Release candidate kamida:

```powershell
$env:AZURELMS_SKIP_ENV_FILE='1'
$env:APP_ENV='local'
$env:LOCAL_USE_REMOTE_SERVICES='False'
$env:GEMINI_API_KEY=''
$env:TELEGRAM_BOT_TOKEN=''
.\venv\Scripts\python.exe manage.py check
.\venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\venv\Scripts\python.exe manage.py test --noinput
node --test tests/frontend_v1/*.test.mjs
.\venv\Scripts\python.exe .tools/docs-sync/verify_docs.py
git diff --check
```

PostgreSQL CI permission/concurrency/query suite va browser/native acceptance
bu local commandlarning o‘rnini bosmaydi, ular ham buning o‘rnini bosmaydi.

---

## 14. Owner qarorlari registri

Agent owner javobisiz unsafe default ixtiro qilmaydi. Quyidagi qarorlar ayni
slice oldidan yopiladi; foundationning mustaqil xavfsiz ishlari kutmaydi.

| ID | Savol | Tavsiya etilgan xavfsiz default | Qachon kerak |
|---|---|---|---|
| DASH-D1 | User-facing nom “Bosh sahifa”mi yoki “O‘quv markazi”mi? | **Bosh sahifa** | DASH1.2c |
| DASH-D2 | Dual-role default va role precedence qanday? | explicit safe next; keyin explicit chosen mode; bo‘lmasa learner-only→learner, teacher-only→teacher, global owner→Ish stoli; mixed roleda tanlov screen yoki oldingi explicit mode | DASH1.1c |
| DASH-D3 | Lesson completionga attendance kiradimi? | **Yo‘q**; LessonProgress-only, attendance alohida | DASH1.0e/1.1a |
| DASH-D4 | Eligible lesson denominatori course/cohort activity va implicit/explicit release holatlarida nima? Hard-delete tarixi kerakmi? | canonical current assigned curriculum; foreign course/cohort yo‘q; release lock mavjud evidence’ni denominator’dan jim chiqarmaydi. Lesson hard-delete CASCADE tarixi Dashboard scope’ida kafolatlanmaydi; versioning kerak bo‘lsa Course/Backoffice/A6 prerequisite | DASH1.1a |
| DASH-D5 | Ko‘p kursda user pin/favorite bo‘ladimi? | avval deterministic recent activity; yangi mutation yo‘q | DASH1.2a |
| DASH-D6 | Payment blocker active learningdan qachon ustun? | faqat o‘sha learning path haqiqatan yopiq bo‘lsa | DASH1.2b/1.6b |
| DASH-D7 | Mini App tablari va AI prominence? | Home, Darslar, Xabarlar, Profil; AI capability ichida | DASH1.5b |
| DASH-D8 | Course teaching, global ops, finance/receipt va learner PII capability guruhlari kimlar? | assigned teacher course workspace’ni saqlaydi; global ops/finance/PII default-deny va superuserdan tashqari explicit group; bu guruhlarning hech biri Messenger body/snippet/email searchini bermaydi — u MSG1.0d/MSG-D13 ownerida | DASH1.0a |
| DASH-D9 | Mini App TTL/skew/rate hard envelope ichidagi qiymat va privileged-account kelajagi? | 300s TTL/30s skew/5 account-min default; privileged bootstrap universal assurance gategacha reject | DASH1.0d |
| DASH-D10 | Historical `verified_at` null va payment metric label/accounting treatmenti? | old timestamp unknown; faqat “tasdiqlangan to‘lovlar”, revenue claim A4 accounting policygacha yo‘q | A4 prerequisite + DASH1.4b |
| DASH-D11 | Product event consent, retention va analytics provider? | qarorgacha product events OFF; operational aggregate only | DASH1.7a |
| DASH-D12 | Teacher queue tur priority/SLA bormi? | yo‘q; event time deterministic | DASH1.3a |
| DASH-D13 | Rollout cohort va stable-window threshold? | owner/internal → bounded cohort → default; kamida bitta to‘liq support cycle | DASH1.7c |

Har qaror sanasi, owner matni, affected slice va chosen value bilan shu hujjat
yoki linked ADRga yoziladi. “Tavsiya etilgan default” owner qarori deb
ko‘rsatilmaydi.

---

## 15. Risk registri

| Risk | Ehtimol/ta’sir | Erta signal | Mitigation | Stop/rollback trigger |
|---|---|---|---|---|
| Progress policy mavjud copy/test bilan zid | yuqori/yuqori | web/Mini/Bot mismatch | DASH1.0e fixture + owner D3/D4 | canonical count noma’lum |
| Capability tightening haqiqiy opsni bloklaydi | o‘rta/yuqori | authorized staff 403 | initial mapping inventory, shadow permission report | owner workflow to‘xtadi; explicit grant, broad rollback emas |
| Mini App CSP Telegram clientni buzadi | o‘rta/yuqori | real WebView blank | route-exact staged native smoke | supported client launch fail |
| Role router redirect loop | o‘rta/yuqori | repeated 302 | pure resolver table test, hop cap | any actor loop |
| Optional adapters core TTFBni oshiradi | yuqori/o‘rta | p75/query regression | field selection, timeout, lazy section | budget fail |
| N+1 plan/progress query | yuqori/o‘rta | 1→100 linear SQL | bulk selector, fingerprint gate | query scaling fail |
| Finance backfill tarixni soxtalashtiradi | o‘rta/yuqori | old rows periodda paydo bo‘ladi | nullable unknown, no guessed backfill | any guessed timestamp |
| GET write qaytadi | o‘rta/yuqori | row-count delta | write-capture CI test | any business/config write |
| New UI ownerga chiroyli, learnerga chalkash | o‘rta/yuqori | task time/click dead-end | 5 persona walkthrough, one primary action | acceptance target fail |
| Telemetry privacy leak | past/o‘ta yuqori | high-cardinality/raw label | schema allowlist, payload tests | any PII/secret payload |
| Legacy fallback eski securityni qaytaradi | o‘rta/o‘ta yuqori | flag OFF header/access fail | security shared below renderer | any flag-dependent security |
| Cross-domain scope creep | yuqori/o‘rta | dashboard writer/model ko‘payadi | ownership table va dependency gate | parallel canonical state |

---

## 16. Kuchsizroq agent uchun bajarish qo‘llanmasi

### 16.1 Har slice boshida

1. `AGENTS.md`, `rules-for-agents.md`, marinebookning so‘nggi yozuvlari va shu
   hujjatning tegishli slice’ini o‘qing.
2. `git status --short --branch`, `git log -8`, `git branch -a` bajaring.
3. `origin/main`dan `codex/<slice>` kabi o‘z prefiks branchini oching; worktree
   yaratmang.
4. Slice dependency va owner qarori yopilganini tekshiring.
5. “Tegadigan joylar”dagi haqiqiy source/testni qayta o‘qing; reja line numberi
   emas, joriy kod haqiqat.
6. Avval regression/characterization test. Test muammoni ko‘rsatmasdan katta
   refactor boshlamang.

### 16.2 Implementatsiya paytida

- domain qoidasini template/view/Bot ichida ko‘paytirmang;
- arbitrary URL saqlamang; route name + typed args;
- GET ichida `get_or_create`, `.save()`, `update()`, read receipt yo‘q;
- optional source exceptionini fake zero bilan yashirmang;
- permission faqat link visibility emas, destinationda fresh check;
- `min(100, progress)` bilan data anomaly yashirmang;
- user-facing copyda V1/migration/internal reason ko‘rsatmang;
- new setting operational bo‘lsa DB setting + env fallback + validator +
  audited mutation; enabled/disabled esa flag registry;
- foreign uncommitted changega tegmang;
- schema bo‘lsa additive migration, old/new binary compatibility va rollback.

### 16.3 Review checklist

PR description quyidagiga aniq javob beradi:

- qaysi DASH slice;
- qaysi problem fixture avval fail qildi;
- canonical owner kim;
- schema/data migration bormi;
- GET write0 dalili;
- permission matrixdagi qaysi actorlar sinaldi;
- query budget oldin/keyin;
- flag OFF va rollback natijasi;
- browser/native tekshiruv nima, nima emas;
- yangi risk yoki owner qarori bormi.

### 16.4 Taqiqlangan shortcutlar

- `is_staff`ni “admin” deb qabul qilish;
- attendance, lesson progress, mastery va completionni bitta foiz qilish;
- `submitted_at`ni verification vaqti deb olish;
- random/top-popular courseni personalized tavsiya deb yozish;
- dashboard GETda config/user allowance yaratish;
- Mini App sessionini barcha routega frame exemption qilish;
- error bo‘lsa barcha optional metricni `0` ko‘rsatish;
- client-side only permission yoki redirect;
- feature flag bilan security fixni o‘chirish;
- owner qarorisiz SLA, deadline, streak, study hours yoki risk score yaratish;
- bir PRda projection, uchta renderer, schema va legacy deletionni jamlash.

---

## 17. Definition of Done

### 17.1 Har slice uchun

- [ ] dependency/owner decision yopilgan yoki safe default hujjatlashtirilgan;
- [ ] failing regression avval dalillangan;
- [ ] canonical service bir joyda;
- [ ] permission va direct-URL tests;
- [ ] GET write0 tegishli bo‘lsa;
- [ ] query budget/fingerprint tegishli bo‘lsa;
- [ ] migration old/new compatibility va rollback tegishli bo‘lsa;
- [ ] flag OFF behavior;
- [ ] Uzbek copy va empty/error state;
- [ ] focused tests + `check` + migration check + diff check;
- [ ] docs/marinebook/status yangilangan;
- [ ] own branch push, required CI, review comments resolved.

### 17.2 DASHBOARD-01 to‘liq yakunlanishi uchun

- [ ] DASH1.0 P0larning barchasi productionga mos dalil bilan yopilgan;
- [ ] learner/teacher/web/Mini App/Bot typed projectionda;
- [ ] owner existing Backoffice workspacega xavfsiz ulanadi;
- [ ] all 33 E2E scenarios PASS;
- [ ] PostgreSQL concurrency/permission/query suite PASS;
- [ ] browser/device/AT matrix evidence;
- [ ] field CWV yoki productionga chiqishdan oldingi lab budget va keyin field
      collection plan;
- [ ] KPI baseline, privacy/retention qarori va owner target;
- [ ] staged rollout/rollback drill;
- [ ] owner go/no-go va native walkthrough;
- [ ] stable windowdan keyin legacy cleanup alohida review.

### 17.3 “Tugadi” degani emas

Quyidagilardan bittasi o‘zi yetarli emas:

- reja yozildi;
- template chiroyli bo‘ldi;
- local testlar yashil;
- flag ON qilindi;
- PR merge bo‘ldi;
- bitta owner account ishladi;
- productionga deploy qilindi.

Kod, migration, test, CI, rollout, native/AT, KPI baseline va owner qabul alohida
dalil. Bittasi boshqasini avtomatik yopmaydi.

---

## 18. Birinchi implementatsiya paketi

Owner “boshlang” desa birinchi PR **DASH1.0a** bo‘ladi:

1. root URLConfdan barcha `/backoffice/` direct+nested read/write/file route va
   methodni capability matrixga chiqarish; unclassified protected route 0;
2. actor matrixni characterization testda qotirish;
3. `/backoffice/chats`ni fail-closed qilish; MSG1.0d selectorisiz metadata deny,
   MSG-D13siz ordinary/ops/PII/finance/superuser uchun body/snippet/email search 0;
4. `cohorts/receipt_service.py` canonical verify/reject writerni broad staffdan
   finance capabilityga o‘tkazish va service-direct test;
5. `core/private_media_views.py::receipt_file`da learner own-file allow’ni
   saqlab, ordinary staff/foreign-file deny va finance cross-user allow testlari;
6. `bot/middleware.py` hamda butun `bot/routers/staff.py`dagi `/stat`, `/cheklar`,
   callback va boshqa admin handlerlarni capability bilan map/test qilish;
7. global PII/finance uchun explicit permission guard;
8. assigned teacher course scope’ini saqlash;
9. assigned teacher course workspace allow, ordinary unassigned staff global/
   finance deny va authorized capability allow;
10. direct route/list/detail/POST/file regressiyasi;
11. no renderer redesign, no unrelated model;
12. migration kerak bo‘lsa faqat Django permission seeding va reversible;
13. ownerga initial assignee mapping/runbook;
14. focused test, full relevant suite, CI va rollback evidence: chats body/search,
    canonical service,
    own/foreign receipt fayli va Bot command/callback matrixi alohida PASS.

Nega birinchi: bu auditdagi eng katta hozirgi maxfiylik/ruxsat xavfi va boshqa
dashboard UI’dan mustaqil yopiladi. DASH1.0b–e undan keyin; katta learner/
teacher redesign foundation merge bo‘lmasdan boshlanmaydi.

---

## 19. Reja verifikatsiyasi va joriy chegara

Ushbu planning task quyidagilarni o‘zgartirmaydi:

- runtime Python/HTML/CSS/JS behavior;
- database schema yoki data;
- feature flag qiymati;
- Gemini/Telegram/provider configuration;
- production server;
- Backoffice, Classbook, Messenger, SIT, A4, A6, A7 yoki A9 admission statusi.

Rejani tekshirish uchun:

```powershell
.\venv\Scripts\python.exe .tools/docs-sync/verify_docs.py
git diff --check
```

Docs-only taskda focused runtime smoke testlar joriy source baseline buzilmaganini
ko‘rsatadi; ular rejalashtirilgan DASH1.x runtime acceptance bajarildi degani
emas.

---

## 20. Qisqa handoff

- **Holat:** DASHBOARD-01 rejalashtirildi; runtime implementatsiya yo‘q.
- **Admission:** keng reform `NEXT — post-launch`, owner execution admissionini
  kutadi; DASH1.0a→b→c→d→e security/correctness maintenance tartibi alohida.
- **Birinchi kesim:** DASH1.0a — Backoffice capability va PII containment.
- **Canonical tamoyil:** dashboard write model emas, typed read projection.
- **Asosiy KPI:** valid primary actiondan haqiqiy authorized outcome’ga yetish.
- **Eng katta xavflar:** ordinary staff global users/chats PII/message va moliya,
  GET writes, Mini App replay/session/frame scope, noto‘g‘ri progress/payment
  claim va O(N) querylar.
- **Saqlanadi:** existing V1 shell/URLs, resume service, teacher scope, Backoffice
  Ish stoli, no-JS/accessibility poydevori.
- **Qurilmaydi:** parallel mastery/payment/message/session state, fake AI ranking,
  yangi owner dashboard.
- **Owner qarorlari:** DASH-D1–D13 tegishli slice oldida.
- **Roadmap:** 8 phase, 33 slice, 33 E2E; har slice goal/files/schema/test/exit/
  rollback/dependency bilan.
- **Merge/release:** har slice kichik PR, required CI, staged flag, security fix
  rollbackda ochilmaydi.
