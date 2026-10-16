# COMMERCE-01 — narxdan ishonchli accessgacha: Payment, Subscription va Checkout islohoti

**Holat:** `REJA — ADMIT, runtime implementatsiyasi boshlanmagan`  
**Audit sanasi:** 2026-10-15  
**Audit tayanchi:** `main`dagi `72e82e0`  
**Birinchi implementatsiya kesimi:** `COM1.0a`  
**Asosiy product contract:** [pricing packages ledgeri](../pricing-packages-plan.md)  
**Oldingi checkout dalili:** [I7 — checkout](I7-CHECKOUT.md)  
**Launch bog‘lanishi:** [A4 — acquisition, payment va entitlement](../launch-plan/03-mahsulot-backlog.md#a4-acquisition-payment-va-entitlement--in-progress-m-contract--l-adapters)

> Bu hujjat kod, DB, flag, real pul, receipt fayli, provider yoki deployni
> o‘zgartirmaydi. U amaldagi yaxshi poydevorni saqlab, Payment, Subscription va
> Checkoutni bitta **Commerce** domeni sifatida xavfsiz va bosqichma-bosqich
> isloh qilish uchun bajariladigan contract va roadmapdir. “Reja tayyor” —
> “muammo tuzatildi” yoki “productionga chiqarildi” degani emas.

---

## 1. Mahsulot qarori

### 1.1 Yakunda nima quriladi?

AzureLMS Commerce foydalanuvchini reklama narxidan boshlab haqiqiy accessgacha
bir izchil va tushunarli yo‘ldan olib boradi:

1. learner kurs va paketni tanlaydi;
2. server ayni offer, muddat, promo va to‘lov manzilidan immutable quote/order
   yaratadi;
3. learner bank/karta o‘tkazmasini amalga oshiradi va xavfsiz dalil yuboradi;
4. vakolatli finance reviewer aynan shu orderni dalili va snapshoti bilan
   ko‘rib, `tasdiqlash`, `qo‘shimcha ma’lumot so‘rash`, `rad etish` yoki
   `qo‘lda hal qilish` qarorini beradi;
5. tasdiqlangan settlement subscription period va entitlement termni atomik
   yaratadi; cohort joyi ham ayni transaction ichida qayta tekshiriladi;
6. learner har payt “nima bo‘ldi, kimdan nima kutilmoqda va keyingi qadam nima”
   ekanini ko‘radi;
7. refund, correction yoki reversal eski tarixni o‘chirmaydi — yangi
   compensating yozuv bilan izohlanadi;
8. Web, Telegram va owner UI bir xil canonical command/read-modeldan
   foydalanadi.

Joriy relizda manual transfer va receipt review asosiy payment usuli bo‘lib
qoladi. COMMERCE-01 Payme, Click, Uzum, Stripe yoki avtomatik card billing
providerini tanlamaydi va integratsiya qilmaydi. Keyinchalik provider qabul
qilinsa ham shu order/payment/subscription contractiga adapter bo‘ladi.

### 1.2 Admission va navbat

**Qaror: `ADMIT — launch-critical contract`.** A4 allaqachon launch-critical;
joriy audit moliyaviy tarix, ruxsat, dalilsiz approval va lifecycle correctness
bo‘yicha runtime containment talablarini topdi. Shuning uchun:

- `COM1.0a–COM1.0b` security/correctness maintenance sifatida yangi katta UXdan
  oldin baholanadi;
- `COM1.1+` additive canonical reform bo‘lib, owner joriy umumiy navbatga
  kiritgandagina implementatsiya qilinadi;
- reja B3, Classbook, Messenger, SIT yoki A8→A9 navbatlarini avtomatik
  almashtirmaydi;
- har slice alohida PR, test, rollback va dalilga ega bo‘ladi.

### 1.3 O‘lchanadigan natijalar

Baseline COM1.0da production PII’siz, synthetic fixture va mavjud rowlar uchun
read-only reconciliation bilan olinadi. Hozir o‘lchanmagan ko‘rsatkich
“yaxshilandi” deb yozilmaydi.

| Outcome | Yakuniy qabul targeti | Dalil |
|---|---:|---|
| Dalilsiz oddiy approval | **0** | service, web va bot permission/evidence matrix |
| Bir commanddan ikki settlement yoki ikki access grant | **0** | idempotency + SQLite/PostgreSQL concurrency testi |
| Noto‘g‘ri user/course/cohort/offer/destinationga bog‘langan payment | **0** | immutable snapshot va cross-object invariant testlari |
| Settlement/allocation bilan fulfilled pul, ammo tegishli entitlement yo‘q | **0** | reconciliation va injected-failure testi |
| `unallocated_inflow` access beradi yoki refund yo‘lisiz qoladi | **0** | ledger/access invariant va no-seat/mismatch E2E |
| Payment yoki explicit owner grant manbasiz entitlement | **0** | source constraint va reconciliation |
| Reject/correction sabab tarixning yo‘qolishi | **0** | append-only decision/event test |
| Refund/reversaldan keyin revenue/access drift | **0** admitted policy bo‘yicha | ledger projection va reconciliation |
| Promo limitining tashlab ketilgan checkoutda abadiy band qolishi | **0** | expiry/release job testi |
| Reviewer SLA buzilishi | owner belgilaydigan threshold bilan o‘lchanadi | queue age histogram + alert |
| Checkout xatosidan keyin tanlovni qayta kiritish | keraksiz redundant entry **0** | no-JS va enhanced browser ssenariy |
| 320 CSS px / 400% reflow | page-level gorizontal scroll **0** | browser + native acceptance |

### 1.4 O‘zgarmaydigan guardraillar

- Economic, Standard va Intensive bir xil core curriculumga ega; farq teacher
  attention va AI quotada. [Owner contract](../pricing-packages-plan.md) bir
  feature PR bilan yashirincha o‘zgarmaydi.
- Cohort joyi checkout ochilganda yoki receipt yuborilganda emas, settlement/
  approval transactionida band qilinadi.
- Narx, discount, currency va muddat clientdan ishonilmaydi; server source of
  truth.
- `pending_plan` yoki tanlangan offer haqiqiy access bermaydi.
- Rejected evidence, payment yoki decision oddiy workflowda hard-delete
  qilinmaydi; prohibited sensitive-auth-data incidenti binary purge exceptioni,
  metadata/decision lineage esa qoladi.
- Evidence’siz cash/manual settlement override COMMERCE-01da admitted emas;
  owner ham oddiy approval yo‘li bilan dalilsiz access bera olmaydi.
- Security va moliyaviy invariant presentation flag ortiga yashirilmaydi.
- Renderer rollback canonical ledgerni rollback qilmaydi.
- Legacy tarixda yo‘q ma’lumot “taxmin” bilan to‘ldirilmaydi.
- “Avtomatik yangilanadi”, “istalgan vaqtda cancel”, “refund kafolatlanadi”,
  “umrbod access”, “cheksiz AI” kabi claimlar owner/legal contractisiz chiqmaydi.

### 1.5 Qamrovga kirmaydigan ishlar

COMMERCE-01:

- yangi payment provider tanlamaydi yoki credentials yaratmaydi;
- kredit karta ma’lumotini platformada yig‘maydi;
- soliq invoice/fiskal chek tizimi yoki accounting ERP qurmaydi;
- price/product qarorini agent nomidan bermaydi;
- legal retention/refund/cancel policy’ni o‘ylab topmaydi;
- cohort pedagogik workflowini yoki course contentni qayta loyihalamaydi;
- eski finance rowlarni destructive migration bilan o‘chirmaydi;
- presentation redesignni canonical writerdan oldinga qo‘ymaydi.

---

## 2. Tadqiqot chegarasi va amaldagi holat

### 2.1 Tekshirilgan ichki yuzalar

Audit quyidagi qatlamlarni source, migration, template, test va mavjud contract
darajasida ko‘rdi:

- [`cohorts/models.py`](../../cohorts/models.py),
  [`checkout_service.py`](../../cohorts/checkout_service.py),
  [`receipt_service.py`](../../cohorts/receipt_service.py),
  [`membership_service.py`](../../cohorts/membership_service.py),
  [`delivery_service.py`](../../cohorts/delivery_service.py),
  [`transition_service.py`](../../cohorts/transition_service.py) va
  [`tasks.py`](../../cohorts/tasks.py);
- [`subscriptions/models.py`](../../subscriptions/models.py),
  [`promo_service.py`](../../subscriptions/promo_service.py), catalog service,
  forms, views va legacy admin;
- [`core/entitlements.py`](../../core/entitlements.py),
  [`core/access.py`](../../core/access.py),
  [`core/private_media_views.py`](../../core/private_media_views.py),
  receipt decision form va backoffice views;
- legacy/V1 pricing, checkout, status, subscription history va owner receipt
  queue templatelari;
- Telegram checkout/review adapterlari va staff middleware;
- I7, A4, pricing packages ledgeri, migrations va mavjud focused testlar.

Safe-env baseline:

```powershell
$env:AZURELMS_SKIP_ENV_FILE='1'
$env:APP_ENV='local'
$env:LOCAL_USE_REMOTE_SERVICES='False'
$env:GEMINI_API_KEY=''
$env:TELEGRAM_BOT_TOKEN=''
.\venv\Scripts\python.exe manage.py test cohorts subscriptions users.test_frontend_v1_records core.test_entitlements core.test_receipt_decisions core.test_private_media --noinput --verbosity 1
```

Natija: **305 test, PASS; 6 skip; system check 0 issue**. Kalitlar ataylab
bo‘sh bo‘lgani uchun mock AI failure loglari ko‘rindi; bu Commerce natijasiga
ta’sir qilmagan. Real provider, production PostgreSQL/Redis, bank o‘tkazmasi,
Telegram va native qurilma tekshirilmagan.

Local DB read-only signal: 6 plan, 2 cohort, 4 enrollment, 3 receipt. Bu
production hajmi yoki data sifati dalili emas va roadmap KPI baseline’i
hisoblanmaydi.

### 2.2 Saqlanadigan yaxshi poydevor

| Mavjud poydevor | Nega saqlanadi | Reform chegarasi |
|---|---|---|
| Checkout GET va write yo‘li ajratilgan | sahifani ochish enrollment/promo yozmaydi | persistent order faqat explicit commandda yaratiladi |
| Course → cohort → enrollment lock tartibi | seat contentionni nazorat qiladi | payment/order lock va conditional expiry bilan kengayadi |
| Bitta enrollment/kind uchun pending receipt partial unique constraint | oddiy duplicate’ni DBda to‘sadi | stable order/idempotency bilan user-course darajasiga ko‘tariladi |
| Signed quote TTL va server-side plan/promo recalc | client narxiga ishonmaydi | quote persistent orderga materialize bo‘ladi |
| Receipt plan/price/discount/period snapshotlari | tarixni qisman saqlaydi | currency, offer, destination, policy va order reference qo‘shiladi |
| `pending_plan` active plandan alohida | unpaid upliftni qisman to‘sadi | source paymentli entitlement termga o‘tadi |
| Private receipt storage, sniffing, `no-store`, unauthorized 404 | dalilni publicdan saqlaydi | validation barcha adapter uchun canonical boundaryga ko‘chadi |
| Web va Telegram bir receipt decision servicedan foydalanadi | adapter driftini kamaytiradi | bot one-click mutation o‘rniga scoped secure handoff |
| Decision/catalog audit mavjud | owner harakatining dalili bor | append-only payment/event ledger bilan bog‘lanadi |
| Typed entitlement service mavjud | capability savolini markazlashtiradi | unknown/null plan fail-closed va source termdan projection |
| V1 native form/no-JS va responsive checkout | resilient UX poydevori | canonical read-model, error recovery va intent continuity |

### 2.3 P0 — yangi Commerce feature’dan oldin yopiladigan holatlar

| # | Aniq topilma | Xavf | Majburiy javob |
|---|---|---|---|
| P0-1 | [`receipt_service.py`](../../cohorts/receipt_service.py), [`private_media_views.py`](../../core/private_media_views.py), backoffice va bot har qanday active `is_staff`ga global receipt qarori/faylini beradi | teacher yoki oddiy staff moliyaviy dalilni ko‘rishi, tasdiqlashi/rad etishi mumkin | named finance capability, scoped queryset, default-deny; web/bot/media bir policy |
| P0-2 | tier-difference receipt [`membership_service.py`](../../cohorts/membership_service.py)da faylsiz yaratiladi, ammo current approve evidence talab qilmaydi | haqiqiy pul dalilisiz entitlement/plan change | `awaiting_evidence` va `ready_for_review`; settlement uchun evidence majburiy; offline cash override COMMERCE-01da admitted emas |
| P0-3 | reject [`receipt_service.py`](../../cohorts/receipt_service.py)da receipt rowni o‘chiradi | reason, status URL, resubmit lineage va finance history yo‘qoladi; blob orphan bo‘lishi mumkin | immutable evidence + append-only rejection/request-info decision; hard delete yo‘q |
| P0-4 | approved payment uchun refund, void, reversal va correction yo‘q | xato approvalni tarixni buzmasdan tuzatib bo‘lmaydi; revenue/access drift | compensating `PaymentTransaction`; owner policy’siz avtomatik access revoke yo‘q |
| P0-5 | transfer/upgrade yangi tierni difference settlementdan oldin berishi mumkin | `unpaid entitlement uplift > 0` | owner qarorigacha default prepaid: `awaiting_settlement`, keyin cutover |
| P0-6 | amount/period invarianti DBda yetarli emas; period yo‘q bo‘lsa 30 kun hard-code bo‘lishi mumkin | null/noto‘g‘ri term yoki parallel renewal overlap | immutable offer term; positive/reconciliation constraints; locked term calculator |
| P0-7 | promo manfiy qiymatni qabul qilishi mumkin | final narx noto‘g‘ri, hatto zero yoki oshgan bo‘lishi mumkin | model/service/DB range constraints va boundary/property test |
| P0-8 | Telegram “eng oxirgi checkout”ga tayanadi, stable order/session ID yo‘q | parallel checkout dalili boshqa kurs/orderga tushishi mumkin | UUID order; bot FSM/order deep link aynan shu IDni olib yuradi |
| P0-9 | expiry job stale ID listdan keyin approval uzaytirgan enrollmentni ham expire qilishi mumkin | to‘langan access race sabab yopiladi | conditional update yoki bir xil lock order; PostgreSQL concurrency testi |
| P0-10 | upload validation web viewlarda; bot service canonical boundaryni chetlashi mumkin | adapterga qarab zararli/noto‘g‘ri fayl qabul qilinadi | bitta evidence commandda size/signature/MIME/hash validation |
| P0-11 | default payment destination realga o‘xshash placeholder; editing legacy admin bilan bog‘liq; destination yo‘q bo‘lsa V1 form ochilishi mumkin | learner noto‘g‘ri hisobga pul yuboradi | versionlangan destination, publish readiness, checkout fail-closed |
| P0-12 | legacy pricing/success copy “bepul”, “umrbod”, “cheksiz”, “access ochildi” kabi current contractga zid claim beradi | pul va access bo‘yicha yolg‘on expectation | barcha rendererda factual copy; security/truth renderer flagga bog‘lanmaydi |
| P0-13 | legacy admin finance/catalog fieldlarni canonical service’siz o‘zgartirishi mumkin | audit/invariant chetlab o‘tiladi | finance field read-only; mutation faqat canonical command orqali |

### 2.4 P1 — canonical islohotning asosiy qarzlari

- `PaymentReceipt` bir paytning o‘zida order, invoice snapshot, upload, decision,
  payment va subscription signalidir; Boolean `is_verified` lifecycle’ni
  ifodalamaydi.
- Finance rowlar Enrollment/User/Cohortga cascade bog‘langan; account cleanup
  pul tarixini o‘chirishi mumkin.
- Receipt snapshotida currency, course/cohort, destination version, policy/
  terms version va stable public order reference yetishmaydi.
- Signed token persistent order emas. Learner pul yuborganidan keyin quote
  expire yoki katalog o‘zgarsa upload `409`da qolishi mumkin.
- Promo reservation abandoned checkoutda expiry’siz qolishi mumkin.
- Subscription sahifasida renewal, pending change, cancel/refund policy,
  support yoki keyingi amal bir joyda yo‘q.
- User history barcha ochiq difference’lardan faqat `.first()`ni chiqaradi.
- Current status va effective access turli model semantikasidan olinib,
  foydalanuvchiga zid ko‘rinishi mumkin.
- Cohort approval paytida to‘lsa receipt “pending” qoladi; “pul keldi, lekin
  joy yo‘q” uchun aniq `manual_resolution` queue yo‘q.
- Revenue `submitted_at` va `is_verified=True`ga tayangan; `settled_at`, refund,
  reversal va currency ledgeri yo‘q.
- Grace 2 kun, term 30 kun hard-coded; owner-operational setting emas.
- Lifecycle Celery taski broad exceptionni yutib, ishlamagan bo‘lsa ham success
  ko‘rinishi mumkin.
- Notification/access side effectlar durable outbox bilan atomik emas.
- Pricing CTA selected course/plan va guest register `next` contextini yo‘qotadi.
- Plan marketing/pricing qatori inplace tahrirlanadi; effective-dated immutable
  revision yo‘q.
- Owner receipt queue pagination, saved filter, age/SLA va keyboard bulk flow
  bermaydi.

### 2.5 P2 — polish va kelajak qarzlari

- daily subscription reminder oqimida N+1 xavfi;
- marketing `PlanFeature` va code entitlement map drift qilishi mumkin;
- actual bank amount/reference hamda evidence hash/dedup to‘liq yo‘q;
- “oy” copy va aniq 30 kun contracti bir-biriga mos emas;
- receipt export, learner-readable timeline va owner workload analytics yo‘q;
- provider webhook/inbox contracti yo‘q — provider hali scope’da emas;
- multi-currency, tax va partial payment product qarorisiz qo‘shilmasligi kerak.

---

## 3. Tashqi tadqiqotdan chiqarilgan majburiy qoidalar

Quyidagi manbalar 2026-10-15da ko‘rildi. Ular payment provider tanlovi yoki
“PCI compliant” da’vosi emas; Commerce contractining minimal xavfsizlik va UX
qoidalarini beradi.

| Manba | Rejaga olingan qoida |
|---|---|
| [OWASP Third Party Payment Gateway Integration](https://cheatsheetseries.owasp.org/cheatsheets/Third_Party_Payment_Gateway_Integration_Cheat_Sheet.html) | amount, currency va product serverda qayta tekshiriladi; browser return URL payment tasdig‘i emas |
| [OWASP Transaction Authorization](https://cheatsheetseries.owasp.org/cheatsheets/Transaction_Authorization_Cheat_Sheet.html) | user nimani tasdiqlayotganini ko‘radi; final action oldidan fresh authorization va TOCTOU himoyasi |
| [Django 6.0 transactions](https://docs.djangoproject.com/en/6.0/topics/db/transactions/) va [`select_for_update`](https://docs.djangoproject.com/en/6.0/ref/models/querysets/#select-for-update) | payment decision, seat, term va outbox bir atomik boundary; parallel test PostgreSQL’da |
| [Django constraints](https://docs.djangoproject.com/en/6.0/ref/models/constraints/) | correctness faqat formga emas, DB check/unique constraintga ham qo‘yiladi |
| [Stripe idempotent requests](https://docs.stripe.com/api/idempotent_requests) | provider tanlovi emas; bir mutation intentiga stable key va bir xil key+boshqa payloadga conflict patterni |
| [Stripe subscription lifecycle](https://docs.stripe.com/api/subscriptions/object), [webhooks](https://docs.stripe.com/billing/subscriptions/webhooks) | provider tanlovi emas; payment, subscription va entitlement holati alohida; eventlar kechikishi/reorder/replayga tayyor |
| [OWASP File Upload](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html), [Django uploads](https://docs.djangoproject.com/en/6.0/topics/http/file-uploads/) va [user-uploaded content](https://docs.djangoproject.com/en/6.0/topics/security/#user-uploaded-content) | allowlist, signature/MIME, random filename, strict size, private storage, quarantine/retention; original HTML/SVG/office/zip qabul qilinmaydi |
| [PCI DSS audience](https://www.pcisecuritystandards.org/standards/pci-dss/), [digital image FAQ](https://www.pcisecuritystandards.org/faqs/1070/), [bank account/PAN FAQ](https://www.pcisecuritystandards.org/faqs/1335/), [encryption FAQ](https://www.pcisecuritystandards.org/faqs/1086/) va [sensitive authentication data FAQ](https://www.pcisecuritystandards.org/faqs/1574/) | receipt rasmida PAN/CVV bo‘lishi mumkin; learnerga crop/redact ko‘rsatmasi, finite retention va no-log. Encryption scope’ni yo‘q qilmaydi; CVV/PIN saqlashga consent yetmaydi; “manual transfer PCI scope emas” yoki “compliantmiz” deyilmaydi |
| [OWASP Authorization](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html) | default-deny, least privilege va har requestda object scope |
| [OWASP Logging](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html) | who/what/when/outcome audit; binary, full PAN, token, raw body va secret loglanmaydi |
| [OWASP Webhook Security](https://cheatsheetseries.owasp.org/cheatsheets/Webhook_Security_Cheat_Sheet.html) | kelajak provideri: signature raw bodyda, replay/dedup, timestamp, async inbox va out-of-order handling |
| [Django CSRF](https://docs.djangoproject.com/en/6.0/ref/csrf/) va [OWASP CSRF](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html) | barcha browser mutation POST+CSRF; GET read-only |
| [WCAG 2.2 error prevention](https://www.w3.org/WAI/WCAG22/Understanding/error-prevention-legal-financial-data.html), [error identification](https://www.w3.org/WAI/WCAG22/Understanding/error-identification), [redundant entry](https://www.w3.org/WAI/WCAG22/Understanding/redundant-entry) va [status messages](https://www.w3.org/WAI/WCAG22/Understanding/status-messages.html) | financial actionda review/correct/confirm, field error, oldingi qiymatni saqlash va focus olmaydigan semantik status |

### 3.1 Bu manbalardan chiqmaydigan da’volar

- Receipt uploadni re-encode qilish barcha malware’ni yo‘q qiladi deyilmaydi.
- Private storage yoki encryption avtomatik PCI compliance bermaydi.
- “Exactly once” transport da’vo qilinmaydi; stable intent + durable receipt
  logical mutationni idempotent qiladi.
- Refund, cancellation, tax va retention muddati legal/owner qarorisiz
  belgilanmaydi.

---

## 4. Foydalanuvchilar va yakuniy tajriba

### 4.1 Rollar

| Rol | Asosiy vazifa | Ko‘rmaydigan/qilmaydigan narsa |
|---|---|---|
| Mehmon | kurs/offer/aniq muddat va to‘lov jarayonini tushunish | receipt, boshqa learner yoki admin data |
| Learner | order ochish, qayerga qancha to‘lashni ko‘rish, evidence yuborish, status/next action, renewal/change/refund so‘rovi | reviewer ichki note, boshqa order |
| Finance reviewer | scoped review queue, evidence va snapshot, request-info/reject/settle | course content yoki global user admin avtomatik emas |
| Support | learnerga statusni tushuntirish va secure handoff | paymentni approve/refund qilish emas |
| Teacher | o‘z cohort occupancy va learnerning access holatini minimum projectionda ko‘rish | receipt rasmi, bank reference, amount breakdown zarur bo‘lmasa |
| Owner | offer/destination/settings publish, exceptional override/refund, health/reconciliation | immutable tarixni edit/delete qilish emas |
| System worker | expiry, outbox, reconciliation, projection | o‘zicha price/refund/access policy yaratmaydi |

Finance reviewer bu target rol; COM-D14 hal bo‘lguncha alohida reviewer grant
yo‘q va barcha review amali owner/superuser-only.

### 4.2 Learner golden path

1. Pricing yoki course detailda kursga tegishli sotuvga ochiq offer ko‘rinadi.
2. CTA guest bo‘lsa internal `next` va serverda saqlangan random, bir martalik
   `commerce_return_id` bilan login/registerga o‘tadi; qaytganda course/offer
   yo‘qolmaydi. URLdagi nonce PII, promo yoki tijoriy payload saqlamaydi.
3. Checkout sahifasi orderni yaratishdan oldin course, cohort policy, offer,
   duration, amount, promo va destinationni serverda tekshiradi.
4. `To‘lov buyurtmasini yaratish` POSTi stable order number beradi. Sahifani
   refresh qilish yangi order yaratmaydi.
5. Orderda amount/currency, recipient, reference, expiry va crop/redact
   ko‘rsatmasi ko‘rinadi. Destination publish-ready bo‘lmasa payment CTA yopiq.
6. Evidence upload progresssiz ham native form bilan ishlaydi. Xatoda tanlov va
   fayldan tashqari xavfsiz qiymatlar saqlanadi.
7. Status timeline: `To‘lov kutilmoqda` → `Dalil yuborildi` → `Tekshiruvda` →
   `Tasdiqlandi`; yoki `Qo‘shimcha ma’lumot kerak`/`Rad etildi`/
   `Qo‘lda hal qilinmoqda`.
8. `needs_info`da learner eski evidence’ni ko‘rmasdan, yangi revision yuboradi;
   reason aniq, deadline esa faqat published policy mavjud bo‘lsa ko‘rsatiladi.
   Eski revision audit uchun qoladi. Terminal `rejected`dan keyingi urinish shu
   orderda emas, explicit `previous_order` lineage’li yangi orderda bo‘ladi.
9. Approvaldan keyin “pul tasdiqlandi” va “access boshlanishi” alohida, aniq
   sana bilan ko‘rinadi.
10. Subscription center active period, next expiry, pending order/change,
    payment history va support actionni bitta joyda beradi.

### 4.3 Exception yo‘llari

- **Pul yuborildi, order expired:** evidence stable orderga qabul qilinadi va
  `manual_resolution`; yangi narxni jim qo‘llamaydi.
- **Cohort to‘ldi:** settlement avtomatik tugamaydi; alternative cohort/refund/
  owner resolution queue. Confirmed cash unallocated ledgerga olinadi va seat
  topilmasa source-bound full refund+cancel bilan tugaydi; learner “pending”da
  izohsiz qolmaydi.
- **Noto‘g‘ri amount/reference:** `needs_info` yoki owner-approved adjustment;
  tolerance owner qarorisiz avtomatik emas. Confirmed mismatch settle
  qilinmasa unallocated ledger va full refund yo‘li majburiy.
- **Duplicate upload/click:** bir xil intent/payload ayni receiptni qaytaradi;
  boshqa payload conflict yoki yangi evidence revision.
- **Reviewer browser timeout:** readback order state orqali qaror natijasi
  aniqlanadi; ko‘r-ko‘rona qayta approve qilinmaydi.
- **Refund/reversal:** oldingi settlement/allocation/unallocated inflow
  o‘zgarmaydi; source-bound compensating transaction va policy-driven
  entitlement/order result timeline’da ko‘rinadi.

### 4.4 Owner golden path

1. Queue default `ready_for_review`, eng eski/SLA xavfi yuqori birinchi.
2. Cardda learner, order ref, course/cohort, offer revision, expected amount,
   destination version va evidence age ko‘rinadi.
3. Reviewer sanitized derivative previewni private endpointdan oladi; original
   binary alohida kuchli permissionda. Preview pixelsini ko‘rgan user uni
   saqlashi mumkinligi yashirilmaydi; farq original metadata/fidelity exposure’ini
   kamaytiradi. Binary audit/logga kirmaydi.
4. Qaror formi current state/versionni ko‘rsatadi; reason va confirm kerak.
5. Settlement command fresh permission, evidence, amount, seat, order version,
   duplicate payment va termni transaction ichida tekshiradi.
6. Natija event/outbox bilan yoziladi; notification failure settlementni
   qaytarmaydi, outbox retry qiladi.
7. Resolution queue cohort full, stale price, amount mismatch, duplicate hash,
   refund va correctionni reason-coded ko‘rsatadi.

### 4.5 Target URL xaritasi

| URL | Maqsad | GET write-free? |
|---|---|---:|
| `/pricing/` | course-aware offer discovery | ha |
| `/courses/<slug>/` | course + offer context | ha |
| `/checkout/<course>/<offer>/` | quote preview | ha |
| `/commerce/orders/<public_id>/` | learner order/status/timeline | ha |
| `/commerce/orders/<public_id>/evidence/` | evidence POST | n/a |
| `/account/subscription/` | active/pending/history/next action | ha |
| `/backoffice/commerce/reviews/` | scoped review queue | ha |
| `/backoffice/commerce/reviews/<id>/` | decision workspace | ha |
| `/backoffice/commerce/catalog/` | offer/destination/settings studio | ha |
| `/backoffice/commerce/health/` | reconciliation/outbox/lifecycle health | ha |

Legacy URLlar cutover davrida canonical selector/commandga adapter bo‘ladi;
redirect yoki olib tashlash alohida deprecation evidence’siz qilinmaydi.

---

## 5. Canonical arxitektura va ownership

### 5.1 Bitta haqiqat zanjiri

```text
Plan (stable identity)
  └─ OfferVersion (immutable price/currency/term/claims)
       └─ CourseOffer (qaysi course/cohortda sotiladi)
            └─ CheckoutOrder (buyer intent + immutable snapshots)
                 ├─ PaymentEvidence revisions (private proof)
                 ├─ PaymentDecision events (human/system review)
                 ├─ PaymentApprovalAttestation rounds (optional four-eyes)
                 └─ PaymentTransaction ledger
                       └─ SubscriptionPeriod
                            └─ EntitlementGrant
                                 └─ Enrollment/DeliveryMembership
```

`Plan` marketing/catalog identity. `CheckoutOrder` nima sotib olinganini,
`PaymentTransaction` nima pul bo‘lganini, `SubscriptionPeriod` qaysi commercial
muddatni, `EntitlementGrant` qaysi capability vaqtini, Enrollment esa learner
qaysi pedagogik delivery/cohortda ekanini ifodalaydi. Ularning biri boshqasining
status maydoniga yashirilmaydi.

### 5.2 Tavsiya etilgan modul chegarasi

Yangi canonical entity va commandlar alohida `commerce/` Django appida bo‘ladi:

```text
commerce/
  models.py                 # ledger va immutable snapshotlar
  enums.py                  # stable states/reason codes
  policy.py                 # authorization va object scope
  selectors.py              # read-only canonical queries
  quote_service.py          # server pricing/offer resolution
  order_service.py          # order/idempotency
  evidence_service.py       # upload validation/lifecycle
  payment_service.py        # review/settle/refund/adjustment
  subscription_service.py   # periods, renew/change
  entitlement_service.py    # grants/revoke projection
  reconciliation.py         # read-only audit va approved repairs
  outbox.py                 # durable events
  errors.py                 # stable public/internal taxonomy
  management/commands/
```

Existing `subscriptions.Plan`, catalog va `cohorts.Enrollment` birdan
ko‘chirilmaydi. Expand/backfill/shadow/cutoverdan keyin legacy writer read-only
bo‘ladi. Cross-app circular importdan qochish uchun Commerce faqat stable FK va
service protocol ishlatadi; `cohorts` Commerce modelini `save()` ichida
chaqirmaydi.

### 5.3 Canonical command oqimi

```text
HTTP / Telegram / Backoffice adapter
  → authenticate + parse only
  → Commerce command (actor, subject, idempotency_key, expected_version)
      → fresh policy
      → transaction.atomic
      → deterministic lock order
      → validate current state + immutable snapshots
      → write domain rows + operation receipt + outbox
  → commit
  → project read model / dispatch outbox
  → adapter-specific response
```

Adapterlar amount hisoblamaydi, enrollment statusni direct o‘zgartirmaydi,
receiptni delete qilmaydi va notificationni transaction ichida remote yubormaydi.

### 5.4 Deterministik lock tartibi

Amaldagi `PaymentReceipt` writeri `Course → Cohort → Enrollment → Receipt`
tartibida lock oladi. Shadow davrda teskari order kiritish deadlock beradi.
Shuning uchun COM1.0bda barcha legacy commandlar quyidagi **global** tartibga
moslashtiriladi, shadow write faqat shundan keyin yoqiladi:

1. canonical domain mutationiga tegishli bo‘lsa singleton
   `CommerceWriterControl`: oddiy/order/money/access/lifecycle writerlar PostgreSQL
   `SELECT ... FOR SHARE`, control stage/abort/config commandlari `FOR UPDATE`;
   keyin target `User` (kerak bo‘lsa, PK bo‘yicha), so‘ng stable
   `subscriptions.Plan → Course → CourseOffer → OfferVersion →
   CommercePolicyVersion` (har model ichida PK bo‘yicha; tegishlisi bo‘lsa).
   Offer revision allocator stable Plan parentini lock qilib `(plan,revision)`ning
   keyingi qiymatini beradi. Quote/create policy rowini shared/read lockda, policy
   publish/retire esa ayni row va overlap candidate’larini exclusive lockda oladi;
2. fresh authorization kerak bo‘lsa `CommerceFinanceAssignment` (PK bo‘yicha);
3. tegishli `CommerceKeyPurpose` control rowlari (`slug` bo‘yicha), so‘ng
   userning `CommerceWriterPilotMember` rowi (mavjud bo‘lsa), keyin
   `(user, course)` `CommerceWriterRoute`, so‘ng tegishli
   `CommerceWriterRouteBatchRun → CommerceWriterRouteBatchItem`;
4. tegishli `Cohort`lar (PK ascending);
5. stable `PaymentDestination` family (PK bo‘yicha), so‘ng tegishli
   `PaymentObservationNamespace` (PK bo‘yicha). Bu locklar `create_order`,
   destination publish/retire/shred, alias insert/materialization, observation-key
   rotate/retire va har `settlement|unallocated_inflow|reversal|adjustment`
   observationida olinadi; immutable DestinationVersion alohida lock qilinmaydi;
6. legacy promo `Campaign → Code → Redemption`, keyin canonical stable
   `PromoRule → PromoReservation` (har model ichida PK ascending; immutable
   `PromoRuleVersion` lock qilinmaydi, stable parent limit serialization locki);
7. `Subscription` (mavjud bo‘lsa);
8. `Enrollment/DeliveryMembership` (PK ascending);
9. `CheckoutOrder`;
10. `PaymentEvidence → PaymentApprovalAttestation → SensitiveEvidenceIncident →
    PaymentResolution → PaymentTransaction` (mavjud transactionlar PK ascending),
    so‘ng `PaymentAllocationSource → PaymentRefundSource → CommerceCashDeficit`;
11. `SubscriptionPeriod`;
12. `EntitlementOverrideDecision → EntitlementGrant`;
13. `CommerceLegalHold` (mavjud active row);
14. `CommerceLifecycleRun`, so‘ng `CommerceReconciliationRun →
    CommerceReconciliationFinding`;
15. retention domain transactionida `CommerceRetentionRun →
    CommerceRetentionClaim`.

Orderni o‘qib IDsni bilish lock emas; immutable parent IDs olinadi, keyin
yuqoridagi tartibda lock qilinib order version/parents yana tekshiriladi. Assignment
revoke ham Course (course-scoped bo‘lsa) → Assignment tartibidan foydalanadi;
global assignment revoke faqat assignmentni lock qiladi. Route migration, key
rotation/retirement, destination shred, promo cleanup, incident purge,
resolution, legal-hold va delivery commandlari shu ro‘yxatdagi
o‘zidan oldingi parentlarni tashlab teskari lock olmaydi. Yangi order hali mavjud
bo‘lmagani uchun avval Course/Route/Cohort/Promo locklari olinadi, keyin
actor+intent idempotency unique insert qilinadi; parallel unique conflict oldingi
operation/order readbackiga aylanadi. `CheckoutOrder`ni birinchi lock qiladigan
alohida yo‘l taqiqlanadi. `CommerceDeliveryTransitionLink` va outbox append-only
insert: ularning mutable parentlari yuqorida lock qilinadi, link/outbox rowning
o‘zi qayta lock/update qilinmaydi. Outer operation-lease claim qisqa alohida
transaction; domain transactiondagi receipt finalizatsiyasi token/version CAS
bo‘lib, bu lock tartibiga teskari explicit row lock qo‘shmaydi.
Reconciliation worker run parametrini lock qilmay snapshot qilib oladi, keyin
subject domain rowlarini yuqoridagi tartibda lock/re-read qiladi va faqat undan
keyin Run→Finding CAS/upsert qiladi. Repair/resolve ham domain→Finding; hech bir
yo‘l Findingni lock qilib keyin order/payment/period/grantga qaytmaydi.
Resolve-vs-rerun PostgreSQL testi duplicate open finding, lost resolution va
deadlock 0ligini isbotlaydi.
Lifecycle worker qisqa outer transactionda faqat Run leaseni claim/reclaim qilib
lockni bo‘shatadi. Har batch domain rowlarini yuqoridagi tartibda mutate qilgach,
ayni domain transaction oxirida Run lease token/versionini lock+CAS qilib cursor/
count/heartbeatni advance qiladi; 0-row stale fence butun domain batchini rollback
qiladi. Uzoq transaction Run lockini ushlab remote ish qilmaydi.

Bir command boshqa tartib ishlatmasligi test va code review checklistiga
kiradi. SQLite test lock semantikasini isbotlamaydi; parallel create/settlement/
expiry/renewal gate PostgreSQL CI’da.

### 5.5 Direct writer policy

Quyidagi obyektlar approved migration/backfill yoki canonical service’dan
tashqari `.save()`, `.update()`, admin edit yoki signal bilan o‘zgarmaydi:

- order state/version/snapshots;
- evidence lifecycle;
- payment decision/transaction;
- subscription period;
- entitlement grant/revocation;
- promo reservation/consumption;
- published offer/destination revision.

Model `save()` moliyaviy side effect bermaydi. Signal business transition
yaratmaydi; ko‘pi bilan transactional outbox dispatcherini uyg‘otadi.

---

## 6. Ma’lumot modeli va invariantlar

Quyidagi field nomlari implementatsiya contractidir. Agent model nomini
o‘zgartirmoqchi bo‘lsa avval plan/ADRni yangilaydi; semantikani jim almashtirmaydi.

### 6.1 `OfferVersion`

Stable `subscriptions.Plan`ning immutable sotuv revisioni.

| Field | Contract |
|---|---|
| `id`, `public_id` | internal PK + unguessable UUID |
| `plan` | `PROTECT`; stable identity |
| `revision` | plan ichida monotonic positive integer; unique `(plan, revision)` |
| `status`, `version` | `draft/published/retired`; positive CAS lifecycle version |
| `display_name`, `description_snapshot` | o‘sha sotuv paytidagi copy |
| `tier_rank` | positive immutable commercial rank; source/target compare shu snapshotda, equal rank upgrade/downgrade emas |
| `currency` | uppercase allowlist; launchda `UZS`, exponent registry’da `0` |
| `amount_minor` | `BigIntegerField`; currency minor birlikda `> 0`; float/Decimal DB value yo‘q |
| `term_unit`, `term_count` | masalan `day/30`; ikkalasi valid pair |
| `capability_snapshot` | versionlangan schema, canonical entitlement map bilan validate |
| `service_claim_snapshot` | faqat ishlaydigan/admitted claimlar |
| `effective_from`, `effective_until` | overlap policy explicit |
| `created_by/at`, `published_by/at`, `retired_by/at` | audit |

Revision allocation owner inputidagi `MAX()+1` emas: create service stable Plan
parentini §5.4 tartibida lock qiladi, current max revisionni transaction ichida
o‘qib next positive value bilan insert qiladi; DB `(plan,revision)` unique final
fence. Concurrent draft create’dan biri keyingi revisionni oladi, duplicate/stale
overwrite yo‘q; PostgreSQL test exact ikki distinct monotonic revisionni isbotlaydi.

Money contracti end-to-end bir xil: barcha saqlanadigan summalar signed 64-bit
integer minor units; fieldlar `*_minor` bilan tugaydi. Promo foizi `Decimal`
oraliq hisobda qo‘llanib, **faqat final discount** configured currency exponentga
`ROUND_HALF_UP` bilan bir marta quantize qilinadi; snapshot input va rounded
resultni saqlaydi. UZS exponent `0`. Configured bo‘lmagan currency rad etiladi.
Legacy Decimal UZS qiymat butun so‘mga exact aylantirilmasa canonical payment
to‘qilmaydi — `LegacyCommerceRecord` findingiga tushadi.

Constraint: published revision uchun currency, positive amount, valid term,
non-empty display va readiness PASS. PostgreSQL partial exclusion constraint
`plan WITH =, tstzrange(effective_from,effective_until,'[)') WITH &&`ni
`status=published`da taqiqlaydi; null end infinity. Overlapga owner bypass yo‘q,
schedule yangi non-overlap revision bilan tuzatiladi.
Publishdan keyin display/price/term/capability/claim/effective interval va plan
identitysi immutable. Faqat `published→retired` status transitioni expected
version+owner reason/idempotency bilan ruxsat va `retired_by/at`, version+1 yozadi;
`effective_until`ni orqaga edit qilmaydi. Qayta sotuv yangi revision.

### 6.2 `CourseOffer`

| Field | Contract |
|---|---|
| `public_id` | unguessable UUID, DB unique va immutable; signed quote/order shu IDni saqlaydi |
| `course`, `cohort` | course required, cohort optional; cohort coursega tegishli |
| `offer_version` | published/retired revisionga `PROTECT` |
| `sale_state` | `draft/open/paused/closed` |
| `opens_at`, `closes_at` | nullable pair va time validation |
| `allowed_order_kinds` | nonempty immutable subset of `initial/renewal/upgrade/downgrade`; unknown/manual kind deny |
| `priority` | deterministic display order |
| `payment_destination` | stable `PaymentDestination` familyga `PROTECT`; draftda nullable, `open` sale’da required |
| `created_by/at`, `updated_by/at`, `version` | CAS/audit |

CourseOffer birinchi marta `open` bo‘lgach `course/cohort/offer_version/
allowed_order_kinds/payment_destination/public_id` identity maydonlari immutable;
commercial bog‘lanish o‘zgarsa yangi CourseOffer ochiladi. Faqat
`sale_state`, oldindan validatsiyalangan `opens_at/closes_at` va `priority`
expected-version CAS bilan o‘zgaradi. Close/pause historical order/quote IDni
qayta ma’nolantirmaydi.

Sale eligibility bitta selector orqali olinadi. Template yoki bot `.filter()`
bilan o‘z talqinini yaratmaydi. Destination global “birinchi active row”dan
tanlanmaydi: selector aynan `CourseOffer.payment_destination` familysi va offer
currency’si bo‘yicha quote vaqtida **bitta** effective published version talab
qiladi. Nol yoki birdan ko‘p natija sale readinessni fail-closed qiladi;
`priority` faqat bir nechta CourseOffer orasidagi display order, destination
tanlovi emas. COMMERCE-01da bitta offerga bir nechta payment method yo‘q; keyin
kerak bo‘lsa alohida versionlangan binding modeli bilan roadmapga kiritiladi.

### 6.3 `PaymentDestination` va `PaymentDestinationVersion`

`PaymentDestination` stable family: unguessable `public_id`, unique immutable
`code`, **canonical immutable** `kind`, `currency`, created audit. Version bu
ikki fieldni takrorlamaydi. Version rowda
alohida unguessable
`version_public_id`, parent `destination`, monotonic positive `revision` va DB
`UNIQUE(destination, revision)` mavjud. Published effective intervallar bitta
destination family ichida PostgreSQL exclusion constraint bilan overlap
qilmaydi; draftlarda overlap mumkin. `public_id` hech qachon version ID ma’nosida
qayta ishlatilmaydi.

Bir xil real recipient/account ikki stable destination family orqali dedupni
ajratib yubormasligi uchun COM1.1a1da `PaymentObservationNamespace` (`public_id`,
created audit, version) va `PaymentDestinationValueAlias` (`namespace`,
`hmac_key_version`, `value_hmac`, canonicalization version, created_at) ham
yaratiladi. Alias DB `UNIQUE(hmac_key_version, value_hmac)`; exact destination
qiymati kindga mos canonicalize qilinib HMAC qilinadi, plaintext saqlanmaydi.
Provision/publish existing alias topsa exact `PaymentDestinationVersion` ayni
namespacega bog‘lanishi shart; boshqa namespace bilan publish fail-closed.
Recipient qiymati yangi revisionda o‘zgarsa u boshqa namespace olishi mumkin;
old order old version/namespace’da qoladi. Shu sabab legacy yoki ataylab alohida
familylar bir real recipientga tegishli bo‘lsa ham cash observation mutex/
fingerprint namespace’i umumiy.

HMAC rotation protokoli qayta tiklab bo‘lmaydigan canonical inputni saqlash yoki
soxta “full backfill”ga tayanmaydi. Destination plaintext va normalized bank
reference DBda saqlanmaydi; crypto-shreddan keyin destinationni yangi key bilan
qayta HMAC qilish imkonsiz. Yangi key `prepared` bo‘lgach provision/observation
commandlari inputni **barcha retained key versionlari** bilan transient HMAC
qilib old alias/observationni qidiradi, keyin yangi write/current-key aliasni faqat
current key bilan yaratadi. Decrypt hali mumkin bo‘lgan destinationlar uchun yangi
alias opportunistik materialize qilinishi mumkin, ammo bu rotation readinessi
emas va shredded row uchun talab qilinmaydi. Rotation, alias insert va namespace
lookup §5.4dagi purpose+namespace mutexlarini oladi; retained-key candidate test,
provider readback va collision reconciliation 0dan keyin prepared→current flip
bo‘ladi. Eski alias/fingerprint va unga kerak HMAC key duplicate-detection/
financial retention tugamaguncha saqlanadi; unga bog‘liq historical row 0
bo‘lmaguncha key retire qilinmaydi. Parallel same-value publishni har retained-key
candidate lookup, current-key unique va namespace mutex birga yopadi. Legacy
bootstrap decrypt qila oladigan duplicate destinationlarni bitta namespacega map
qiladi; decrypt/readback noma’lum bo‘lsa sale publish HOLD, taxminiy yangi
namespace emas.

Key materiali DBga yozilmaydi, ammo rotate/retire bilan transaction o‘rtasidagi
race yashirin qolmasligi uchun COM1.1a2 `CommerceKeyPurpose` va
`CommerceKeyVersion` control registryni yaratadi. `CommerceKeyPurpose`da unique
allowlisted `slug` (`destination_alias_hmac`, `payment_observation_hmac`,
`payment_reference_hmac`, `payment_ip_hmac`, `promo_lookup_hmac`,
`settlement_fingerprint_hmac`, `legal_hold_reference_hmac`,
`retention_fingerprint_hmac`, `legacy_record_fingerprint_hmac`,
`mutation_journal_fingerprint_hmac`, `quote_signing_hmac`, `destination_kek`,
`evidence_kek`), nullable
positive `current_version`, positive CAS `version` va audit bor. Fresh additive
deployda purpose rowlari seeded, current null va Commerce key-health critical;
provisiondan keyin exactly-one current required. `CommerceKeyVersion`da
purpose, positive key version, opaque external-provider key ID,
`prepared|current|retained|retired` state va activation/retirement auditi;
`UNIQUE(purpose, key_version)` hamda purpose uchun exactly-one partial current
constraint bor. Parent `current_version` current childga mosligi service va
reconciliationda tekshiriladi. Business rowlar purpose+versionni saqlaydi;
provider materialni faqat shu reference bilan resolve qiladi.

`rotate_commerce_key` va `retire_commerce_key_version` ayni purpose control rowini
§5.4 tartibida lock qiladi. First/second four-eyes proposal, alias/observation
write va key retirement ham shu mutexni oladi, so‘ng current/retained state’ni
qayta o‘qiydi. Destination-alias va observation keyi retirementdan oldin barcha
retained-key candidate-lookup rehearsal/collision reconciliation 0ni hamda shu
key versioniga bog‘langan retained historical alias/observation 0ni; settlement
fingerprint keyi esa open approval round 0ni talab qiladi. Payment reference/IP
keylari uchun shu versiondagi open round va retention-required transaction/audit
row 0; promo lookup keyi uchun published/yet-effective rule, active reservation
yoki raw-code lookup talab qiladigan pending order 0 bo‘lishi shart.
Quote-signing keyi shu version bilan imzolangan, hali `expires_at`i o‘tmagan token
bo‘lishi mumkin bo‘lgan maksimal quote TTL + clock-skew oynasi tugamaguncha retire
qilinmaydi; verifier current va retained versionni token claimidan exact tanlaydi.
Legal-hold reference keyi shu versiondagi active hold 0 bo‘lmaguncha;
retention-fingerprint keyi shu versionga bog‘langan pending/leased claim 0 va
run audit retentioni tugamaguncha retire bo‘lmaydi. Hold/claim create ham tegishli
purpose mutexini oladi. Legacy-record va mutation-journal fingerprint keylari
shu versiondagi retained lineage rowlari yoki replay windowi bor ekan retire
bo‘lmaydi; backfill/replay tegishli purpose mutexini oladi. Shu bilan
propose-vs-retire yoki observation-vs-key-flip orasida yo‘qolgan key oynasi yo‘q;
PostgreSQL race testlari ikkala tarafdan buni isbotlaydi.

| Field | Contract |
|---|---|
| `version_public_id`, `destination`, `revision`, `status`, `lifecycle_version` | unique family revision; `draft→published→retired` only, positive CAS lifecycle version |
| `observation_namespace` | exact decrypted recipient qiymatidan alias orqali topilgan stable namespace `PROTECT`; pre-secret draftda nullable, publishda required va keyin immutable |
| parent `kind/currency` | stable familydan read-only; `bank_transfer/card_transfer/other_manual`, provider credential emas |
| `recipient_name`, `masked_account`, `ciphertext` | display va exact copy value alohida; logga chiqmaydi |
| `aead_nonce`, `aead_tag`, `cipher_version` | AES-256-GCM metadata; nonce har encryptda 96-bit random, tag 128-bit |
| `wrapped_dek`, `record_key_handle`, `kek_key_id` | random 256-bit DEK record-specific external erasure key bilan wrap; plaintext key DB/repo/logda yo‘q |
| `crypto_version` | positive CAS version; rewrap va key-destroy/tombstone transitionida +1, business revisiondan alohida |
| `value_hmac`, `hmac_key_version` | version readback signali; canonical cross-family identity alohida namespace aliasida, plaintext hash emas |
| `instructions` | exact account/PAN uchun emas; parent currency order currency bilan mos |
| `effective_from/until` | order yaratilganda active bo‘lishi kerak |
| `created/published/retired_by/at`, `reason` | every lifecycle transition audit; no reopen |

Readiness: placeholder denylist, recipient/currency/instruction, encrypt→decrypt
readback, owner confirm va kamida bitta active version. Minimal crypto contract
COM1.1a2ning o‘zida mavjud: AEAD AAD aynan
`PaymentDestinationVersion/version_public_id/revision/destination.kind/
destination.currency`ning immutable, canonical encodingidan quriladi; `kind` va
`currency` versiondagi duplicate field emas, stable parentdan olinadi. Key
provider faqat alias/key ID oladi. Production
`COMMERCE_KEY_PROVIDER` resolved bo‘lmasa yoki registryning tegishli purpose/current
external key IDsi providerda o‘qilmasa butun Django
startup yiqilmaydi: Commerce key-health **critical** bo‘ladi va destination
publish, order creation, exact display/decrypt hamda canary readiness fail-closed;
public non-Commerce sahifalar ishlashi mumkin. Local/test random fake provider
ishlatadi. Productionda birinchi publishdan oldin owner+ops
`commerce_key_provider_ready` gate’i provider resolve, encrypt/decrypt/rewrap va
audit readback evidence’i bilan imzolanadi; bu gate bo‘lmasa COM1.1a2 additive
deploy bo‘lishi mumkin, ammo Commerce mutationi yoqilmaydi.
Publishdan keyin business/secret/effective fields immutable; faqat parent mutex
ostida expected-version `published→retired`, retired actor/time/reason va
lifecycle_version+1 yoziladi. Rewrap/shred faqat crypto projection maydonlari va
`crypto_version`ni o‘zgartiradi, business lifecycle’ni reopen qilmaydi. Yangi
recipient/instruction/schedule yangi revisiondir.
`masked_account` user inputi emas: service decrypted exact qiymatdan kindga mos
deterministic mask yaratadi. `instructions` va `recipient_name` exact account/
PAN/credential patternini qabul qilmaydi; faqat dedicated secret field exact
qiymat oladi. `recipient_name` PII sifatida log/telemetryga chiqmaydi. Exact value
faqat authenticated, object-scoped, `no-store` order viewda va order
`awaiting_payment` bo‘lib haqiqatan pul yuborish talab qilinganda ko‘rinadi.
`evidence_submitted/under_review/needs_info/manual_resolution` hamda barcha
terminal state’da faqat masked; public/listlarda doim masked.

Business revision immutable. Har revision uchun provider app DB backupidan
mustaqil, non-exportable record-erasure key yaratadi; DBdagi
`record_key_handle` faqat shu tashqi obyektga reference. KEK rotation CAS+auditli
`rewrap_destination_dek` commandi orqali yangi record keyni yangi provider KEK
ostida tayyorlaydi, DEKni provider ichida rewrap qiladi, keyin
`wrapped_dek/record_key_handle/kek_key_id`ni CAS bilan almashtiradi; commitdan
keyin eski handle destroy qilinadi, crash reconciliation orphan handleni yopadi.
`ciphertext`, nonce, tag, AAD va business fieldlar o‘zgarmaydi. Crypto-shred
DB rowni tozalashdan **oldin** external providerning authoritative, app backupidan
restore qilinmaydigan destruction registry’sida `record_key_handle`ni irreversible
destroy qiladi. Shundan keyin eski `wrapped_dek` DB backupdan qaytsa ham unwrap
fail-closed; masked snapshot va auditni
qoldiradi. U faqat shu destination revisioniga `awaiting_payment`,
`evidence_submitted`, `under_review`, `needs_info` yoki `manual_resolution`
holatidagi order bog‘lanmagan, retention/legal-hold ruxsat bergan va restore/
  replica re-purge rejasi mavjud bo‘lganda bajariladi. Shred stable destination
  parentini lock qilib blockerlarni qayta o‘qiydi va provider destroy → local
  tombstone/`crypto_version+1` commit tugaguncha lockni ushlab turadi. `create_order`
  ham ayni parent lockidan keyin decrypt-readiness va blocker state’ni qayta
  tekshiradi; shuning uchun checkdan keyin yangi actionable order kirib qolmaydi.
  Crashda provider destroy bo‘lib DB tombstone hali yozilmagan bo‘lsa decrypt
  readback fail-closed va reconciliation roll-forward qiladi. Actionable order borida shred
qat’iy deny. `expired` order ham `expires_at + late_evidence_window_minutes`
o‘tmaguncha yoki unresolved money/evidence findingi borida shred blocker;
windowdan keyin late-payment command deny. Kutilmagan key lossda checkout va exact
display fail-closed. `awaiting_payment` order evidence/submitted timestampini
to‘qib `manual_resolution`ga o‘tkazilmaydi: u state’da qoladi, destination-not-ready
banner/support cancel actioni va critical finding oladi; yangi payment yuborish
ko‘rsatmasi 0. Evidence mavjud orderlargina normal invariantlari bilan
`manual_resolution`ga o‘tishi mumkin. Yangi revision publish qilish eski
ciphertextni tiklamaydi.
Real destination migration, fixture, repo, CLI argument, log yoki screenshotga
kirmaydi. Secret faqat HTTPS owner POST orqali provision qilinadi. Recipient
qiymati PAN bo‘lsa COM-D15siz `card_transfer` publish qilinmaydi. Checkout
destination topolmasa order yaratmaydi; support CTA beradi.

### 6.4 `CheckoutOrder`

| Field | Contract |
|---|---|
| `public_id` | UUID, URL/reference; PK ochilmaydi |
| `order_number` | `AZ-<16 Crockford Base32>-<mod37 checksum>`; 80-bit CSPRNG, PII/sequence emas |
| `user`, `course`, `cohort` | `PROTECT`; selected subject |
| `subscription` | renewal/change lineage uchun nullable FK |
| `source_period`, `source_offer_version`, `source_period_version`, `source_tier_rank`, `source_boundary_at` | renewal/upgrade/downgradeda required immutable paid-source snapshot; initialda null |
| `previous_order` | terminal rejectiondan keyingi yangi urinish lineage’i; nullable self-FK |
| `kind` | `initial/renewal/upgrade/downgrade`; `manual_adjustment` COMMERCE-01 scope’ida yo‘q |
| `offer_version`, `course_offer` | `PROTECT` |
| `destination_version` | `PROTECT`; full destinationni orderda yana nusxalamaydi |
| `base_amount_minor`, `discount_amount_minor`, `amount_due_minor`, `currency` | immutable integer-minor-unit server snapshot |
| `legacy_promo_redemption`, `promo_label_snapshot`, `promo_code_hmac` | legacy linkage/safe snapshot; native reservation FK orderda yo‘q, reverse OneToOne quyida; raw promo code order/token/logda yo‘q |
| `term_start_policy`, `term_count`, `term_unit` | approvalda deterministic calculator |
| `state` | state machine quyida |
| `version` | optimistic CAS, har transitionda +1 |
| `expires_at` | quote/order expiry; evidence kelgach jim expire emas |
| `idempotency_key`, `request_fingerprint` | actor+command scope’da unique |
| `terms_version`, `pricing_policy_version` | ko‘rsatilgan shartlar |
| `legacy_receipt_id` | backfill lineage; nullable unique |
| timestamps | created/submitted/decided/closed kabi semantik timestamps |

`order_number` create paytida CSPRNG bilan yaratiladi, DB `UNIQUE`; collisionda
shu transaction ichida ko‘pi bilan 5 marta qayta generatsiya, keyin fail-loud.
Uni foydalanuvchi yoki adapter bera olmaydi.

DB invariantlari:

- `amount_due_minor > 0` (100% discount/free product alohida owner admission);
- `base_amount_minor = discount_amount_minor + amount_due_minor`;
- amount/currency/offer/destination published snapshotdan keladi;
- bitta `(user_id, course_id)` uchun state
  `awaiting_payment/evidence_submitted/under_review/needs_info/manual_resolution/
  expired`
  bo‘lgan ko‘pi bilan bitta order: PostgreSQL partial `UniqueConstraint`.
  Boshqa cohort/offer/kind istagi oldingi intent cancel/reject/lapsed bo‘lmaguncha
  yangi order emas; boshqa course parallel bo‘lishi mumkin;
- `created_at` va `expires_at` non-null, `expires_at > created_at`;
  `submitted_at` `evidence_submitted/under_review/needs_info/manual_resolution/
  approved/rejected` state’larida non-null; `awaiting_payment/expired/lapsed`da null;
  `cancelled`da nullable, chunki learner evidence’siz cancel qilishi ham,
  evidence yoki money resolutionidan keyin audited cancel bo‘lishi ham mumkin.
  Post-evidence cancel timestampni o‘chirmaydi; evidence/decision mavjudligiga
  moslik service+reconciliation bilan tekshiriladi;
  `decided_at` faqat `approved/rejected`da non-null; `expired_at`
  `expired|lapsed`da non-null va late reopen bo‘lsa ham audit sifatida qoladi;
  late window 0 bo‘lib to‘g‘ridan-to‘g‘ri lapse bo‘lsa `expired_at=closed_at`
  ayni fixed DB as-of/transaction vaqtida yoziladi; `closed_at`
  aynan `approved/rejected/cancelled/lapsed`da non-null, reopenable `expired`da
  null. Transition service va DB
  `CheckConstraint` bir xil state setlardan foydalanadi;
- `course_offer.course_id == order.course_id`; scoped `course_offer.cohort_id`
  null yoki `order.cohort_id`, va `course_offer.offer_version_id ==
  order.offer_version_id`. Order cohorti ayni coursega, delivery planli cohort
  bo‘lsa offerning stable planiga tegishli;
- destination version published va `created_at`da effective, uning stable
  destination familysi aynan `course_offer.payment_destination`, parent
  currency’si order currency bilan teng. Keyin retire bo‘lish order snapshotini
  o‘zgartirmaydi;
- `initial`da subscription null va user-course Subscription hali yo‘q;
  `renewal/upgrade/downgrade`da subscription majburiy va uning
  `(user, course)`i order bilan teng; `initial`da subscription null;
- `upgrade/downgrade` quote’da exactly one locked `active|grace` paid source;
  renewalda exactly one deterministic latest paid non-revoked source (`active|
  grace|expired`) va har uchalasida **zero** non-revoked scheduled successor
  tanlanadi; scheduled-only, mavjud scheduled successor yoki ambiguous source
  deny. Source offer/period
  version/rank va `source_boundary_at=min(ends_at,effective_access_until)` freeze
  qilinadi. Renewal targeti aynan source OfferVersionning stable Plan’i va
  `tier_rank`iga teng; rank/Plan farqi faqat upgrade/downgrade strict yo‘nalishida.
  Initialda source fieldlar null;
- `previous_order` faqat ayni user/course’ning terminal `rejected` orderi;
  self/cycle deny va DB `UNIQUE(previous_order)` bitta bevosita successor beradi;
- `user/course/offer` hard-delete emas.

Cross-table tengliklarning DB `CheckConstraint` bilan ifodalab bo‘lmaydigan
qismi create commandda locked rows ustida, mutationdan oldin tekshiriladi va
reconciliation ayni kodlar bilan qayta isbotlaydi. Mismatch
`CROSS_OBJECT_INVARIANT_FAILED`, row yozilmaydi.

`CommerceWriterControl` COM1.1a3da singleton (`key=primary`) row: `mode=off|
internal|allowlist|canary|on`, `canary_percent=0..100`, nullable opaque external
`canary_salt_id`, monotonic positive `writer_epoch`,
`fallback_backend=legacy|deny`, `resolution_mode=owner_only|normal`, positive CAS `version`, update actor/time/
reason va nullable unique `last_operation_receipt`. Fresh migration aynan `off`,
percent 0, salt null, epoch 1, fallback legacy, owner-only resolution, receipt null bilan system
seed qiladi; keyingi har control mutationida yangi append-only receipt required va
last pointer yangilanadi. Missing/duplicate row
health-critical va write 0. Emergency abort fallbackni `deny` qiladi. Settings
faqat §10.3dagi fail-safe ceiling, DB
controlni permissive qilib override qila olmaydi.

Fence faqat admission emas: `create_order`, evidence/decision, settlement/
unallocated/compensation, subscription/entitlement/delivery lifecycle va ularning
workersi domain transaction boshida controlni PostgreSQL `SELECT ... FOR SHARE`
qilib version/epochni qayta o‘qiydi. **Audience admission faqat yangi intent va
birinchi route yaratishga tegishli.** Mavjud current-epoch route/order mutatsiyasi
persisted backend, flow switch va command authorizationni tekshiradi, lekin pilot
membership muddati yoki keyingi stage audience’ini qayta talab qilmaydi; aks holda
paymentdan keyingi membership expiry orderni strand qilardi. Admission, first route
insert va route migrate/resume ham shu shared lockni oladi; ko‘p writer parallel
qoladi. Stage/abort/salt/control-resume mutationlari `FOR UPDATE` + expected version;
ular barcha old shared writer tugaguncha kutadi. Abort exclusive lockni oldin olsa
keyingi writer yangi fence’ni ko‘rib write 0; writer shared lockni oldin olsa whole
atomic commit abortdan oldin linearize bo‘ladi.

Learner/new-intent mutationda route epoch current bo‘lishi majburiy. Stale-epoch
existing order faqat `resolution_mode=owner_only`, owner fresh reauth, order
abortdan oldin yaratilgan va `commerce_stale_epoch_resolution_v1=ON` bo‘lsa owner
resolution oladi; backend/order ko‘chmaydi. Exact allowlist:
`request_payment_information`, `reject_order`, `cancel_order`,
`record_post_lapse_inflow`, `record_refund`, `record_reversal`,
`record_adjustment`, `resolve_cash_deficit` hamda `settle_payment`. Birinchi sakkiz
command yangi access bermaydi va normal ledger/outbox effektinigina bajaradi;
`settle_payment` esa faqat pre-abort evidence+decision, exact current cash fact,
projection bundle readiness, seat va zero-critical-finding preflight bilan atomik
period/grant yaratishi mumkin. Allowlistdan tashqari learner upload, new order,
renewal/plan-change va route flip deny. Switch default OFF, emergency SAD
erase, reconciliation/readback, outbox delivery va accessni kengaytirmaydigan
expiry/revoke workersi mode OFFda ham ishlaydi, ammo atomik fence uchun control
shared lockini oladi. Quote write-free bo‘lsa ham control version+epochni token
qiladi; create locked current qiymat bilan tenglashtiradi. PostgreSQL
abort-vs-create, abort-vs-settle va abort-vs-worker testlari post-fence partial
write 0ni isbotlaydi.

Canary saltning yagona ID source’i shu DB control rowidir; deploy settingida
ikkinchi salt ID yo‘q. External provider faqat DBdagi opaque ID bo‘yicha materialni
resolve qiladi. `configure_writer_salt(expected_control_version, salt_id,
idempotency, reason)` owner fresh reauth bilan faqat mode `off|internal`, route 0
va batch run 0 paytida IDni CAS qiladi; `canary|on`ga advance’da non-null provider
readback required. **Har qanday birinchi route**, legacy/internal bo‘lsa ham,
non-null salt+provider readback bo‘lmasa fail-closed; bucket placeholder bilan
yaratilmaydi. Birinchi route yaralgach salt ID immutable. Compromise/rotation
bucketlarni jim qayta hisoblamaydi va yangi roadmap/epoch migrationisiz deny.

`CommerceWriterRoute` bir `(user, course)`ni `legacy/canonical` backend,
stable canary bucket, writer epoch va positive CAS versionga unique bog‘laydi. U order emas va access
bermaydi; faqat sticky routing/fence. Create paytida route lock qilinadi,
current audience policy bilan yo‘q bo‘lsa ayni transactionda yaratiladi. Backend
flip faqat pending intent 0, reconciliation green va owner-confirmed migration
`migrate_writer_route(user, course, target_backend, expected_version,
idempotency, reason)` bilan; request ichida yoki renderer flag bilan emas.
No-route create algorithm avval locked offer/course/user/order-kind uchun backendga
bog‘liq bo‘lmagan `base_sale_eligible`ni (published effective offer/destination/
policy, course open, subject allowed, per-kind subscription matrix va capacity)
tekshiradi; false bo‘lsa fallbackga tushmay `SALE_NOT_ELIGIBLE`, route/order 0.
Shundan keyingina control shared locki, User/Course va membershipni olib salt
readbackdan keyin bucketni hisoblaydi: effective canonical admission true
bo‘lsa `backend=canonical`; false va DB `fallback_backend=legacy` bo‘lsa
`backend=legacy`; false va fallback `deny` bo‘lsa `WRITER_ROUTE_FENCED`, order 0.
Route qaysi backend bo‘lsa ayni transactiondagi writer faqat shuni ishlatadi.
Shu sabab seeded `off+legacy` shadowgacha joriy checkoutni uzmaydi, non-admitted
internal/allowlist/canary user ham sticky legacy row oladi, abortdagi `off+deny`
brand-new userga ham legacy bypass bermaydi. Existing route har holda sticky va
epoch checkdan o‘tadi.

Named real-user pilot yashirin setting emas: COM1.1a3
`CommerceWriterPilotMember(user UNIQUE, enabled, expires_at, version,
audience=synthetic|real_pilot, created/updated_by/at, reason,
operation_receipt UNIQUE)`ni yaratadi. Active
predicate aynan `enabled AND transaction_timestamp < expires_at`; expiry
avtomatik route flip qilmaydi. `set_writer_pilot_member` owner fresh reauth,
expected version/idempotency/reason bilan CAS qiladi. Membership faqat yangi
route admissioniga ta’sir qiladi; mavjud legacy route canonical bo‘lishi uchun
yuqoridagi explicit migrate command va pending-intent=0 sharti baribir kerak.
Membership row yo‘q holatdagi create-vs-admissionni ham serializatsiya qilish
uchun set/admission avval ayni Userni, keyin mavjud PilotMemberni, so‘ng Routeni
§5.4 tartibida lock qiladi va active predicate’ni route insertdan darhol oldin
qayta o‘qiydi. Disable/expiry bilan parallel first create shu lockda oldin yutgan
aniq transaction natijasini oladi; stale membership yangi canonical route bermaydi.
`internal` admission faqat active `audience=synthetic`, `allowlist` faqat active
`audience=real_pilot` rowiga tayanadi. `is_staff/is_superuser`, email/domain,
fixture nomi yoki request claimi synthetic marker emas. Audience’ni faqat
`set_writer_pilot_member` owner fresh reauth+reason bilan CAS qiladi; adapter uni
bera olmaydi. Production real account tasodifan internalga kirmasligi negative
permission testida isbotlanadi.

Resumable rollout persistence ham COM1.1a3da oldindan aniq:

- `CommerceWriterRouteBatchRun`: immutable `public_id`,
  `kind=migrate|resume_epoch`, `mode=dry_run|apply`, nullable same-kind
  `source_dry_run PROTECT`, target percent/mode yoki from/to epoch parametrlari,
  expected `CommerceWriterControl` version/epoch, fixed max `Route.pk`
  `snapshot_high_watermark`, nullable exact `last_route_pk`, eligibility digest,
  selected/migrated/resumed/skipped/failed counts, `pending|running|completed|
  failed` status, positive CAS version, actor/timestamps va one-to-one operation
  receipt;
- `CommerceWriterRouteBatchItem`: run, route `PROTECT`, before
  backend/epoch/version, `migrate|resume|skip` action, allowlisted skip reason,
  required after backend/epoch/version va item fingerprint; DB `UNIQUE(run,route)`.

Run shape DB+service XORi exact: `migrate`da `target_mode/target_percent` required,
`from_epoch/to_epoch` null; `resume_epoch`da epochs required va `to_epoch` current,
targetlar null. `dry_run`da source null; `apply`da completed same-kind dry-run
required va kind/params/high-watermark/start-cursor byte-equal. Selector faqat
`Route.pk > last_route_pk AND Route.pk <= snapshot_high_watermark ORDER BY pk`.
`migrate` itemining after’i canonical/current epoch/version+1, `resume`niki same
backend/current epoch/version+1, `skip`niki before bilan aynan teng va route write
0; itemlar insertdan keyin immutable.

Har dry-run batch exact selector snapshotini itemlarga yozib aggregate digest
qiladi. Apply run majburiy completed dry runni reference qiladi va ayni
high-watermark/cursor/paramsni oladi; batch transactionida barcha item route
expected versionlarini lock+compare qiladi. Bitta drift bo‘lsa route mutationi 0,
apply failed va yangi dry run kerak. Mos bo‘lsa route CASlari va apply item/run
counts+digest ayni transactionda yoziladi; dry/apply digest va counts byte-equal.
Keyingi cursor alohida dry/apply batch; retry operation receipt orqali idempotent.
Shu schema bo‘lmasa JSON log yoki command stdout rollout dalili hisoblanmaydi.

### 6.4a `LegacyCommerceRecord`

Canonical `CheckoutOrder` yangi native orderlar uchun strict qoladi. Eski
receiptlarda offer, currency, destination yoki period yo‘q bo‘lsa sentinel
published data yaratish va nullable native order ochish taqiqlanadi. Bunday
row alohida compatibility obyektiga olinadi:

| Field | Contract |
|---|---|
| `legacy_model`, `legacy_pk` | unique source identity |
| `user`, `course`, `enrollment` | faqat source’da aniq bo‘lsa `PROTECT` |
| `known_amount_minor`, `known_currency` | faqat exact representable snapshot |
| `known_period_start/end`, `known_plan_label` | taxmin qilinmaydi |
| `legacy_state` | verified/pending/deleted-audit/unknown |
| `completeness_codes` | qaysi canonical field yo‘qligi typed list |
| `source_fingerprint_hmac`, `hmac_key_version`, `transform_version` | PII/secret-free rerun/catch-up idempotency |
| `linked_order` | keyin owner resolution bilan canonical row yaratilsa |

Bu obyekt yangi settlement/access yaratmaydi. Legacy access shadow readerda
oldingi qoida bilan qoladi; reconciliation ownerga incomplete lineage beradi.
Learner tarixida “eski to‘lov — ayrim tafsilot mavjud emas” deb ko‘rinishi
mumkin, lekin current price/destination/reason bilan to‘ldirilmaydi.

### 6.4b `PromoRuleVersion` va `PromoReservation`

Promo commercial input ham narx kabi revisionlangan:

- `PromoRule`: stable `public_id`, immutable `code_hmac`, `hmac_key_version` va
  DB `UNIQUE(hmac_key_version, code_hmac)`, non-secret suffix/label; raw code
  faqat input vaqtida HMAC qilinadi;
- `PromoRuleVersion`: separate `version_public_id`, parent rule, monotonic
  revision, DB `UNIQUE(rule, revision)`, `draft/published/retired`, positive CAS
  lifecycle version, discount kind va integer-minor
  value, currency, minimum order, total/per-user limits, first-purchase/renewal,
  exact `eligible_order_kinds` subset, course/offer scopes, effective interval va
  create/publish/retire actor/time/reason audit. Published commercial fieldlar
  inplace edit qilinmaydi; faqat expected-version `published→retired`, no reopen,
  effective interval rewrite 0. Bitta rule family published effective intervallari PostgreSQL
  exclusion constraint bilan overlap qilmaydi;
- `PromoReservation`: rule version, user, course, required `order=OneToOneField`
  (`PROTECT`, canonical forward edge), amount snapshots,
  `reserved/locked_for_review/applied/released/rejected/expired`, `expires_at`,
  positive CAS `version`, `reacquisition_count`, idempotency key va transition timestamps. Unique `(rule_version, user,
  idempotency_key)`; OneToOne DB uniqueni beradi, CheckoutOrderda reservation FK
  yoki ikkinchi forward edge yo‘q;
  `reserved/locked_for_review/applied` limit hisobida, qolganlari emas. Order
  yaratilganda order FK ayni transactionda ulanadi. Promo orderning expiry’i
  `min(order_payment_deadline, reservation_deadline)`; shu sabab reserved promo
  orderdan oldin jim expire bo‘lmaydi. Evidence vaqtida reservation
  `locked_for_review`, review/SLA cho‘zilsa avtomatik release emas.

Reservationning har transitioni expected version+1 va operation receipt bilan;
terminaldan faqat explicit `expired→locked_for_review` reacquire ruxsat, qolgan
terminal state reopen yo‘q. Promo faqat quote/order kindi versionning
`eligible_order_kinds`ida bo‘lsa ishlaydi; safe bootstrap `initial`gina.
Renewal/upgrade/downgrade promosi alohida owner-published rule bo‘lmasa deny,
“first purchase”dan taxmin qilinmaydi.

Create transaction avval durable orderni, so‘ng promo ishlatilsa ayni transactionda
reservation→order OneToOneni yozadi; commitda promo snapshot/HMAC bor native
orderga exactly one reservation, promo yo‘q orderga 0. `legacy_promo_redemption`
non-null bo‘lsa native reverse reservation 0; ikkalasi birga deny. Orphan
reservation yoki boshqa orderga cross-link service+reconciliation critical va
PostgreSQL concurrent create testida 0.

Promo lookup raw codeni current va hali retirementga ruxsat berilmagan barcha
lookup-key versionlari bilan transient HMAC qilib `(hmac_key_version, code_hmac)`
juftlari bo‘yicha qidiradi; log/cachega raw code yoki barcha digestlar chiqmaydi.
Yangi rule faqat current key bilan yoziladi, ammo create duplicate checki barcha
retained keylar bo‘yicha ishlaydi. Eski HMAC key faqat shu keyga bog‘langan
published/yet-expired rule, active reservation yoki code orqali qayta topilishi
kerak bo‘lgan pending order **0** bo‘lganda va rehearsal PASS bo‘lganda retire
qilinadi. Historical orderlar rule FK/snapshot bilan o‘qiladi, raw code bilan
emas.

Settlement rule/reservation/orderni global tartibda lock qiladi va faqat
`reserved/locked_for_review → applied`ni transaction/period bilan atomik yozadi.
Terminal mapping **current reservation state-aware**: `reserved|locked_for_review`
holatida rejected order/outcome → `rejected`, cancelled → `released`, expired
order → `expired`, settlement → `applied`. Late-flowda reservation allaqachon
`expired` bo‘lsa keyingi reject/cancel uni `rejected|released`ga o‘tkazmaydi —
`expired` qoladi. Faqat quyidagi explicit muvaffaqiyatli
`expired→locked_for_review` reacquire’dan keyin settlement/reject/cancel tegishli
`applied/rejected/released` transitionini oladi. Har biri outbox bilan atomik;
`needs_info/manual_resolution` holdni saqlaydi. Expired
order late-payment resolutionida eski reservation avtomatik valid bo‘lmaydi:
privileged resolution ayni rowni rule locki ostida `expired →
locked_for_review` explicit `reacquired` transition, incremented
`reacquisition_count`, reason va outbox bilan CAS qiladi. Limitni qayta egallash
muvaffaqiyatli va owner policy original discountni honor qilsa settlement mumkin;
aks holda settlement deny va refund/new full-price order yo‘li.
Limit counter ayni rule row locki ostida; ikki order bitta bo‘sh slotni olmaydi.

COM1.1a1 rule schema, COM1.1a3 reservation schema beradi. COM1.2b existing
`PromoRedemption`ni compatibility adapter orqali o‘qishi mumkin, ammo yangi
native order faqat `PromoReservation` yozadi. COM1.6c schema ixtiro qilmaydi:
u shu ikki modelning lifecycle va owner UI’sini yakunlaydi.

### 6.4c `LegacyMutationJournal`

Shadow/backfilldan oldingi durable journal additive model:

| Field | Contract |
|---|---|
| `sequence`, `event_id` | DB `BigAutoField` ordering + unique UUID event ID |
| `source_model`, `source_pk`, `source_revision`, `source_mutation_id` | exact identity; NOT NULL locked monotonic positive bigint + globally unique UUID; timestamp version emas |
| `mutation_kind` | allowlisted create/approve/promo/access/transition kind |
| `source_fingerprint_hmac`, `hmac_key_version`, `schema_version` | deterministic replay contract; raw secret/PII payload yo‘q |
| `minimal_payload`, `target_type/public_id` | typed, versioned, PII-minimal replay input/output |
| `status`, `attempt_count`, `last_error_code` | pending/applied/failed; bounded safe error |
| `created_at`, `applied_at` | ordered catch-up cursor |

DB `UNIQUE(source_mutation_id)` va `UNIQUE(source_model, source_pk,
source_revision)`. Har qonuniy transition, kind takrorlansa ham, source row va
oxirgi journal rowi lock qilingach `source_revision + 1` oladi; retry ayni
operation receipt orqali ayni mutation UUID/revisionni qayta ishlatadi. Journal row
legacy mutation bilan **ayni DB transactionda** yoziladi; journal insert
bo‘lmasa legacy mutation ham rollback. Consumer sequence bo‘yicha, event ID
idempotent ishlaydi va canonical resultni shu rowga CAS bilan bog‘laydi.
External blobning o‘zi journal JSONiga kirmaydi; faqat private blob ID/hash.

### 6.5 `PaymentEvidence`

Har upload yangi immutable revision.

| Field | Contract |
|---|---|
| `public_id`, `order`, `purpose`, `revision` | purpose `payment_submission|compensation_proof`; unique `(order, purpose, revision)` |
| `version` | positive lifecycle CAS version; revision ordinalining o‘rnini bosmaydi |
| `blob_key` | random private ciphertext object key; original filename emas |
| `original_sha256`, `size_bytes`, `sniffed_mime` | original private blob metadata |
| `preview_blob_key`, `preview_sha256` | encrypted metadata-stripped/re-encoded derivative lineage |
| `original_wrapped_dek/record_key_handle/kek_key_id/crypto_version`, `preview_wrapped_dek/record_key_handle/kek_key_id/crypto_version` | har blob uchun alohida random 256-bit DEK va record-specific external erasure key; independent positive crypto CAS, handle app backupidan mustaqil, plaintext key DB/repo/logda yo‘q |
| `original_nonce/tag`, `preview_nonce/tag` | har blob uchun alohida AES-256-GCM 96-bit nonce/128-bit tag |
| `original_extension` | displayga emas, audit uchun sanitized |
| `derivative_state` | `staged/reviewable/quarantined/restricted_sensitive/superseded/purge_due/purged` |
| `original_state` | `quarantined/available/restricted_sensitive/superseded/purge_due/purged`; `available` faqat clean scan |
| `scan_state` | `not_configured/pending/clean/failed`; scanner bor deb da’vo qilinmaydi |
| `validation_state`, `validation_version`, `validation_failure_code` | `pending/passed/failed`; positive validator schema (masalan `raster-v1`); failureda allowlisted code |
| `uploaded_by/at`, `source`, `handoff_origin` | web/owner/imported_legacy; Telegram faqat web handoff origin, binary source emas |
| `original_retention_due_at/purged_at/purge_reason`, `derivative_retention_due_at/purged_at/purge_reason` | per-blob independent owner/legal policy snapshot va purge audit |

Binary/order/purpose/revision identity immutable, lekin lifecycle projection CAS bilan
o‘zgaradi. `version=1` insertda; derivative finalize, original finalize,
scan, validation, restrict, supersede, purge-due va purge atomik transitionining
har birida expected version shart va successda aynan +1. Bitta command bir nechta
lifecycle fieldini atomik o‘zgartirsa bir marta oshadi. Har system/human command
`CommerceOperationReceipt`/incident auditida expected va resulting evidence
versionni saqlaydi; stale CAS butun blob/DB mutationini rollback qiladi.
`CommerceRetentionClaim.expected_version` claim vaqtidagi shu lifecycle
versiondir, immutable upload `revision` emas. Shu ajratish scan/finalize bilan
flag, purpose ichidagi supersede bilan purge va false-positive bilan auto-erase race’larini
deterministik qiladi. Yangi revision reviewable bo‘lib currentga aylanganda oldingi
current revisionning original va derivative state’i **bitta CAS transactionda**
`superseded` bo‘ladi; blob darhol o‘chirilmaydi, ammo ikkala endpoint ham deny va
faqat retention/SAD purge yo‘li keyin binaryni yo‘q qiladi.

Accepted launch corpus: JPEG, PNG, WebP kabi explicit raster allowlist; max size
operational settingda bounded. SVG, HTML, PDF/office/zip default deny; PDF faqat
alohida risk/admission bilan. Validation service binary signature, decoded image
budget, dimensions va MIME’ni tekshiradi; EXIF strip/re-encode defense-in-depth.

Blob lifecycle: temp/staged upload → DB transaction commitdan keyin finalize.
Rollback/stale stage cleanup jobi bor. Oddiy rejectda evidence o‘chmaydi; access
private va retention policyga bo‘ysunadi. SAD incidenti bundan mustasno.
Derivative malware/PANni “xavfsiz”
qilmaydi; u faqat active content/metadata/fidelity exposure’ini kamaytiradi.

Orphan cleanup taxminiy storage list emas: COM1.1b `CommerceStagedUpload`ni
yaratadi — random `public_id`, actor/session bindingi, intended order+purpose,
private random object key, size/sniffed MIME/SHA-256, immutable
`retention_fingerprint_hmac`+key version, `staged|consumed|purge_due|purged` state,
positive CAS version, `expires_at`, nullable one-to-one consumed evidence va unique
upload operation receipt. Plain filename/path yo‘q. Evidence commit staging rowni
locked `staged→consumed` qilib FKni yozadi; rollback/crash rowni staged qoldiradi.
Cleanup/retention claim `CommerceStagedUpload/staging_object/purge`ni fingerprint+
version bilan oladi, private object verified-missingdan keyin `purged`; consumed
rowni cleanup o‘chirmaydi. DB `consumed` iff evidence non-null va terminal purged
shape checks; expired staged selector PK/high-watermark bilan durable run orqali.

Original va derivative ruxsat/state’i alohida truth-table bilan boshqariladi:

| Validation/scan | Derivative | Original | Review/settlement |
|---|---|---|---|
| validation `pending/failed` | staged/quarantined | quarantined | deny |
| validation PASS, scan `pending` | staged | quarantined | deny |
| validation PASS, scan `failed` | quarantined | quarantined | deny |
| validation PASS, scan `not_configured` | reviewable | quarantined | derivative-only allow |
| validation PASS, scan `clean` | reviewable | available | derivative allow; original separate owner gate |
| either state `restricted_sensitive/superseded/purged` | unavailable | unavailable | deny |

`quarantined` yuqorida har bir blobning o‘z state’i, butun revision uchun
shortcut emas. Settlement faqat shu orderning eng yangi current
`payment_submission` revisioni,
`derivative_state=reviewable`, validation PASS va `scan_state in
{not_configured, clean}` bo‘lsa ishlaydi. Superseded revision audit metadata
bo‘lib qoladi, qarorga asos bo‘lmaydi.

`compensation_proof` shu private upload/validation/encryption/retention
lifecycle’idan foydalanadi, ammo terminal yoki manual-resolution orderning
state’ini evidence_submittedga qaytarmaydi va payment-submission “current”ini
supersede qilmaydi. Har purpose ichida faqat eng yangi non-superseded revision
current. `refund` platform actioni uchun compensation proof va bank reference
null; `reversal|adjustment` uchun owner `submit_compensation_evidence` bilan
current reviewable proof yaratadi va keyingi command aynan shu revisionni link
qiladi. Shunday qilib terminal orderga kelgan bank statementi eski approval
dalilini almashtirmaydi, lekin tashqi correction dalilsiz ledgerga kirmaydi.

Har evidence revision original va derivative’ni **alohida** random DEK+record
handle bilan, alohida nonce va AAD
(`PaymentEvidence/public_id/revision/blob_kind`) ostida shifrlaydi. Shu sabab
original/derivative retention cutoffs mustaqil bajariladi; bir handle shred qilish
ikkinchi blobni muddatidan oldin yo‘qotmaydi. Business lifecycle `version`dan
tashqari har blobning `crypto_version`i rewrap/shredda +1.
Yagona `COMMERCE_KEY_PROVIDER` registryning `evidence_kek` purpose external key
IDlarini app DB backupidan mustaqil non-exportable
record-erasure key va `record_key_handle` yaratadi; shu key DEKni wrap qiladi,
global KEK versioni esa provider hierarchy/auditi uchun. Key provider unavailable
bo‘lsa upload finalize/preview/download/review/settlement fail-closed; order
`needs_info` yoki `manual_resolution`ga reason-coded yo‘naltiriladi, plaintext
bypass yo‘q.

SAD purge avval providerning authoritative, application backup bilan restore
qilinmaydigan destruction registry’sida record handleni irreversible destroy
qiladi, keyin auditli DB transitionda `wrapped_dek`ni clear va active stage/
original/derivative objectlarni verified delete qiladi. Har restore/startupda
destination yoki evidence decryptdan **oldin** erasure registry/provider resolve
gate’i ishlaydi; provider/registry unavailable bo‘lsa decrypt fail-closed.
Incidentdan oldingi DB va ciphertext backup qaytsa ham destroyed handle unwrap
qilmaydi. Tombstone active objectlarni restore’dan keyin yana delete qiladi, ammo
u yagona crypto kafolat emas. Shu sabab confirmed/auto incident erase’dan keyin
recoverable binary copy 0; ciphertext backup retentioni ordinary COM-D1
lifecycle’da qolishi mumkin, ammo DEKsiz ochilmaydi.

CAS+auditli `rewrap_evidence_dek` yangi record keyni yangi KEK ostida tayyorlaydi,
DEKni provider ichida rewrap qiladi, DBdagi wrapper/handle/key IDni CAS bilan
almashtiradi va commitdan keyin eski handleni destroy qiladi; ciphertext/nonces/
tags/AAD o‘zgarmaydi, crash orphan-key reconciliation bilan yopiladi. Eski
destination yoki evidence KEK faqat unga reference qiluvchi live wrapper 0,
pending rewrap 0, destroyed-handle registry saqlangan va restore rehearsal PASS
bo‘lganda retire qilinadi. Destroyed handle rotation bilan qayta yaratilmaydi.

`SensitiveEvidenceIncident` mutable, durable **CAS control row**; auditning o‘zi
append-only `SensitiveEvidenceIncidentEvent`da. Control fieldlari: evidence
revision; `flagged/confirmed_purge/key_destroyed/objects_pending/erased/
failed_retryable/false_positive` state; positive `version`; typed reason;
reporter/owner-security confirmer; initial operation receipt; unique immutable
`erase_request_id`; lease token/expiry, attempt/retry-at; `flagged_at`, non-null
`auto_erase_at`, confirmed/key-destroyed/wrapper-cleared/stage-deleted/
original-deleted/preview-deleted/erased timestamps va safe last-error code. DB
conditional unique bir evidence revisionga bittadan ortiq nonterminal incidentni
taqiqlaydi. Event row: incident, monotonic sequence, from/to state, step, actor/
service identity, operation receipt, expected/resulting version, safe error va
timestamp; `UNIQUE(incident, sequence)` va `UNIQUE(operation_receipt)`.

Erase algoritmi crash-safe va normativ:

1. human confirm yoki overdue worker incidentni lease+expected version bilan
   `confirmed_purge`ga CAS qiladi; `erase_request_id` o‘zgarmaydi;
2. providerga shu request ID bilan idempotent destroy yuboriladi. `destroyed` va
   `already_destroyed` bir xil success; keyin `key_destroyed_at` CAS. Crash oldin
   yoki keyin bo‘lsa retry registrydan ayni natijani oladi;
3. DB transaction evidence wrapper/handle’ni clear, blob state’larini purge_due
   qiladi va `wrapper_cleared_at`, `objects_pending`ni yozadi. Key allaqachon
   yo‘qolgan bo‘lsa bu safe forward recovery;
4. stage/original/preview object delete’lari har object key uchun idempotent;
   har step timestampi alohida. Hammasi verified missing bo‘lgach `erased` CAS;
5. transient xato `failed_retryable`+safe code/retry-at; key/progress timestamplari
   qayta nollanmaydi, worker birinchi tugamagan stepdan davom etadi. Har CAS bilan
   IncidentEvent yoziladi; broad exception “success”ga aylanmaydi.

U binary/OCR text/PANni saqlamaydi. `auto_erase_at = flagged_at +
sensitive_incident_response_minutes`; published policy default 15 daqiqa va hard
max 60 daqiqadan oshmaydi. False-positive faqat deadline’dan oldin, incident
aynan `state=flagged`, `lease_token IS NULL`, `confirmed_at IS NULL` va
`key_destroyed_at IS NULL` bo‘lsa owner/security fresh reauth+reason bilan bitta
expected-version CAS orqali. Workerning lease olish+`confirmed_purge`ga o‘tishi
ham shu locked rowda bitta CAS; oraliq `flagged+leased` holat yo‘q. Kim birinchi
CAS qilsa o‘sha yutadi; worker confirmidan keyin provider call hali boshlanmagan
bo‘lsa ham false-positive deny. Evidence avvalgi state’ga validation/scan gate
qayta PASS bo‘lsagina qaytadi.
Deadline’da owner javob bermasa worker purge’ni boshlaydi. Har purpose’dagi
current **yoki superseded**, hali purged bo‘lmagan evidence revision incidentga
olinadi. Superseded revision erase’i current reviewable revision/order state’iga
tegmaydi. Current `payment_submission` erase’i faqat nonterminal orderni
`needs_info`, money suspected bo‘lsa `manual_resolution`ga olib boradi. Current
`compensation_proof` incidenti approved/terminal order state’ini qayta ochmaydi:
shu proofga tayangan hali commit bo‘lmagan compensationni block qiladi, linked
transaction allaqachon commit bo‘lsa ledgerni o‘zgartirmay critical finding va
owner alert yozadi. Erased incident qaytarilmaydi — kerak bo‘lsa ayni purpose’da
yangi replacement evidence revision yuboriladi.

### 6.6 `PaymentDecision`

Append-only human/system decision event.

| Field | Contract |
|---|---|
| `order`, `sequence` | unique monotonic order sequence |
| `kind` | `submitted/review_started/info_requested/rejected/approval_proposed/approved/manual_resolution/cancelled` |
| `reason_code`, `internal_note` | stable taxonomy; human financial outcome’da reason required, internal max 2000 |
| `learner_message_code`, `learner_message_params` | allowlisted template va bounded safe scalar params; arbitrary free-text emas |
| `actor`, `actor_role`, `source`, `handoff_origin` | web/system/imported_legacy; bot faqat handoff origin |
| `expected_version`, `resulting_version` | stale decision evidence |
| `evidence_revision` | qaror qaysi proofga tayangan |
| `resolution` | nullable unique `PaymentResolution`; resolution-driven order decisionida required canonical edge |
| `created_at`, `request_id`, `ip_hmac`, `hmac_key_version` | minimal audit; raw IP saqlanmaydi |

Row edit/delete qilinmaydi. Service-boundary `reject_secret_like_text` Luhn-valid
PAN, uzun account/reference digitlari, CVV/PIN/credential/token patternlarini
`internal_note` va message paramsda defense-in-depth tekshiradi. Match bo‘lsa text
**saqlanmaydi/redact qilib saqlanmaydi**: command rad etiladi, safe alert yoziladi
va linked evidence bo‘lsa sensitive-incident flag talab qilinadi. Reviewer reason
code/template tanlaydi, dalildagi qiymatni ko‘chirmaydi. Outbox faqat
`learner_message_code` va allowlisted safe paramsni oladi; internal note, rendered
free-text, account/reference log/notificationga kirmaydi. Test full PAN/reference
decision, outbox va logning hech biriga kira olmasligini isbotlaydi; bu validator
manual incident yo‘lining o‘rnini bosmaydi. Shu validator va bounded reason
contracti `PaymentResolution`, `PaymentTransaction`, entitlement override va
assignment internal note’lariga ham service boundaryda qo‘llanadi.

### 6.6a `PaymentApprovalAttestation`

COM-D9 yuqori-summali settlement uchun four-eyes’ni yoqsa yashirin schema
chiqmasligi uchun append-only model COM1.1bdayoq yaratiladi: `order`, current
`evidence_revision`, monotonic `approval_round`, `stage=first|second`, actor,
expected order/evidence versionlari, policy version, one-to-one operation receipt
va PaymentDecision; confirmed `amount_minor/currency`, optional resolved delivery
cohort, bank `occurred_at/source`, transient raw reference’dan olingan
`reference_hmac/key_version`; versionlangan canonical
`settlement_input_fingerprint`, positive `settlement_fingerprint_schema_version`
va `settlement_fingerprint_key_version`; reason code va created_at. Fingerprint aynan
order/evidence/order-version/policy/offer/destination/proposed-resolution
kind+outcome+cohort/amount/
currency/occurred-at/reference-HMAC/promo-reservation hamda ordered
unallocated-source public ID+intended amount+locked cash-outflow total+current
allocation-line totalining canonical encodingidan per-purpose HMAC bilan
olinadi; `PaymentTransaction` immutable bo‘lgani uchun yashirin version field
yo‘q, raw reference/free-text kirmaydi.
DB `UNIQUE(order,
approval_round, stage)`, `UNIQUE(operation_receipt)` va `UNIQUE(decision)`.

Second reviewer reference berilgan bo‘lsa uni “current” reference key bilan emas,
first attestationdagi `reference_hmac_key_version` bilan qayta HMAC qiladi; keyin
fingerprintni ham “current” key bilan emas, first attestationda persist qilingan
`settlement_fingerprint_key_version` bilan qayta hisoblaydi. Reference null bo‘lgan
firstda second reference ham null bo‘lishi shart.
“Open round” alohida mutable status emas, exact derived predicate: order uchun
`MAX(approval_round)`dagi first bor, ayni round second yo‘q, order state
`under_review`, va first saqlagan order/evidence/policy/offer/destination
versionlari current locked qiymatlarga teng. First proposal, second proposal va
key rotate/retire tegishli `CommerceKeyPurpose` rowlarini slug tartibida lock
qiladi. Shu predicate true ekanda fingerprint keyni hamda reference non-null
bo‘lsa uning saqlangan reference keyini retire/destroy qilish readiness gate’i
deny qiladi. Material
version/state o‘zgarishi oldingi roundni derived-stale qiladi; fingerprint
mismatchdan keyingi fresh proposal monotonic yangi `approval_round` yozadi va
eski first endi MAX emas. Append-only rowga closed/status update kerak emas.
Rotation oralig‘ida har ikki HMAC byte-equality deterministic; schema version o‘zgarsa eski
round second qilinmaydi, typed stale bo‘lib yangi first round talab qiladi.

Threshold null bo‘lsa model dormant va oddiy authorized `settle_payment` ishlaydi.
Thresholdga teng/yuqori orderda alohida `propose_payment_approval` commandi first
attestation + `PaymentDecision(kind=approval_proposed)` yozadi, order
`under_review` qoladi va pul/access rowi yozilmaydi. Ikkinchi **boshqa**
fresh-authorized actor ayni evidence/policy/versionni qayta tekshirib, second
attestation yozishdan oldin to‘liq settlement inputini qayta canonicalize qiladi;
fingerprint first bilan byte-equal bo‘lmasa `FOUR_EYES_INPUT_CHANGED`, settlement
0 va yangi first round kerak. Equal bo‘lsa second attestation, approved decision
hamda settlement/projection/outboxni bitta
transactionda yozadi. Actor farqi va cross-row tenglik locked
service+reconciliationda; evidence yoki material order versioni o‘zgarsa round
stale, yangi first proposal keyingi rounddan boshlanadi. COMMERCE-01da four-eyes
faqat settlementga tegishli; refund/key/catalog kabi boshqa action uchun owner
fresh reauth default, ularni ikki kishilik qilish yangi manifest unitisiz taxmin
qilinmaydi.

First stage proposed resolutionning typed payloadini fingerprint qiladi, ammo
`PaymentResolution` rowini **yaratmaydi**: `outcome=settle` rowi dependentsiz
qolishi mumkin emas. Equal second-stage domain transactionda optional
`PaymentResolution` avval insert qilinadi, so‘ng ayni transactionda unga linked
approved decision va `settlement|allocation` yoziladi. Fingerprint mismatch yoki
second-stage rollbackda orphan resolution 0.

### 6.6b `PaymentResolution`

`manual_resolution`ni oddiy status update bilan yopish taqiqlanadi. Append-only
`PaymentResolution` quyidagilarni saqlaydi: order, monotonic `sequence` va
expected version; one-to-one `CommerceOperationReceipt`; DB `UNIQUE(order,
sequence)` va `UNIQUE(operation_receipt)`;
`alternative_cohort/amount_mismatch/duplicate_payment/late_payment/
unallocated_inflow/post_lapse_inflow/cancel_without_money/refund/reversal/
adjustment` typed kind;
nullable original va confirmed amount/currency pairlari; optional same-course
`delivery_cohort`; optional pre-existing source transaction;
`resulting_order_disposition=none|cancel`;
`access_disposition=not_applicable|retain|retain_with_debt|revoke|shorten`;
`outcome`; actor, reason code,
internal note va timestamp. Resolution resulting decision/transaction FKlarini o‘zida
saqlamaydi: canonical forward edge mos ravishda `PaymentDecision.resolution` va
`PaymentTransaction.resolution`. Resolution birinchi, dependents keyin ayni
transactionda insert qilinadi; append-only rowga backfill/update va circular FK
yo‘q.

`outcome` non-null enumi aynan
`hold/settle/needs_info/reject/cancel/compensate`.
DB same-row kind/outcome map:

- `alternative_cohort/amount_mismatch/duplicate_payment/late_payment` →
  `settle|needs_info|reject|cancel`;
- `unallocated_inflow|post_lapse_inflow` → faqat `hold`, confirmed positive
  amount/currency required, source transaction null va
  `resulting_order_disposition=none`; `post_lapse_inflow` faqat terminal `lapsed`
  order uchun va refund-only lineage;
- `cancel_without_money` → faqat `cancel`, confirmed amount/currency va source
  transaction null;
- `refund/reversal/adjustment` → faqat `compensate`, pre-existing
  `source_transaction` required; allowed source kind va disposition quyidagi
  ledger contracti bilan cross-row service+reconciliationda tekshiriladi.

`resulting_order_disposition` compensation-only maydon: DB same-row check bilan
`outcome != compensate` bo‘lsa aynan `none`. `outcome=compensate`da `cancel`
faqat `kind IN (refund,reversal,adjustment)`; cross-row validator esa source
`unallocated_inflow`, orderda allocation/period/grant 0, compensationdan keyin
barcha order cash net 0 va source real balansining to‘liq neutralizatsiyasi
shartlarini talab qiladi. Refundda bu full positive `free_unallocated`; reversal
yoki outflow adjustmentda verified tashqi fakt. Boshqa barcha compensation
`resulting_order_disposition=none`. Shu map `settle+cancel` kabi ma’nosiz rowni
DBdayoq yopadi.

`access_disposition` ham DB same-row mapga kiradi: non-compensation, accessga
tegmaydigan unallocated free-balance refund va `funding_deficit=0` bo‘lgan
unfulfilled reversal/adjustmentda `not_applicable`; fulfilled settlement/allocation
refundi hamda `funding_deficit>0` qiladigan reversal/adjustmentda
`retain|retain_with_debt|revoke|shorten`dan biri required. `retain_with_debt`
faqat verified tashqi reversal/required cash correctionni money-truth ledgerdan
COM-D4 unresolvedligi sabab yashirmaslik uchun safe default; u critical finding
va owner resolution outboxisiz commit qilmaydi.

`alternative_cohort/amount_mismatch/duplicate_payment/late_payment/
cancel_without_money` order-disposition kindlarida ayni resolutionga exactly one
PaymentDecision required: `settle→approved`, `needs_info→info_requested`,
`reject→rejected`, `cancel→cancelled`; kind tengligi service+reconciliationda.
`outcome=settle`da shu resolutionga exactly one `settlement|allocation`
transaction ham required; qolgan uch disposition outcome’da transaction yo‘q.
`outcome=hold`da exactly one `unallocated_inflow` transaction, decision 0 va
order state o‘zgarishi 0 required: oddiy `unallocated_inflow` orderni
`manual_resolution`da, `post_lapse_inflow` esa terminal `lapsed`da qoldiradi;
pul ledgerga olinadi, ammo access berilmaydi. Post-lapse source allocation/
settlementga yaroqsiz, faqat uning to‘liq musbat `free_unallocated` balansiga
source-bound refund mumkin; refund ham orderni `cancelled`ga o‘tkazmaydi.
`refund/reversal/adjustment`da
`outcome=compensate` hamda ayni resolutionga exactly one va kindi mos
compensating `PaymentTransaction` required. Odatdagi approved-order
compensationida `resulting_order_disposition=none` va resolution-linked decision
0. Faqat yuqoridagi unfulfilled/full-neutralization shartlari bajarilib
post-compensation order cash net 0 bo‘lsa `resulting_order_disposition=cancel` va
ayni resolutionga exactly one `PaymentDecision(kind=cancelled)` required;
aks holda cancel deny. Shuning uchun “pulni qaytarib cancel” ham, “approved
order excessini qaytarib accessni saqlash” ham bitta aniq cardinality bilan
ifodalanadi. Reverse cardinality DB unique, required/zero cross-row invariant
service+reconciliation bilan commitdan oldin tekshiriladi. Learner message faqat
order-disposition `PaymentDecision` template’ida qoladi.

`outcome=settle` resolution canonical `settle_payment`ni qayta chaqiradi va uning
fresh permission/evidence/amount/seat/term checks hamda transaction→period→
grant→delivery→outbox atomik yozuvlarining hammasidan o‘tadi. Oldindan ledgerga
olingan `unallocated_inflow` source’lari bo‘lmasa direct `settlement`; bo‘lsa
exact due’ni qoplaydigan bitta neutral `allocation` va uning immutable source
qatorlari yoziladi — cash ikkinchi marta inflow bo‘lmaydi. Alternative cohort
orderning immutable selected-cohort snapshotini o‘zgartirmaydi; typed proposed
resolution payload fingerprintga kiradi, actual resolution rowi second-stage
transactionda yaratiladi; original va alternative cohortlar PK tartibida lock
qilinadi, alternative ayni course/offer delivery tieriga tegishli va seat mavjud
bo‘lishi qayta tekshiriladi. Delivery projection resolution cohortini oladi va
typed link yozadi. COM-D7 explicit admit qilmasa amount
mismatch settle bo‘lmaydi. `reject/cancel` outcome faqat confirmed amount/currency
null va money observation/settlement 0 bo‘lganda; pul tasdiqlangan bo‘lsa faqat
`settle` yoki `needs_info`; settle hozir mumkin bo‘lmasa confirmed cash avval
`record_unallocated_inflow` orqali append-only ledgerga olinadi. Unfulfilled
cashni qaytarish uchun **soxta seat-bypass settlement yozilmaydi**:
`compensate_payment(kind=refund, source=unallocated_inflow)` outflow yozadi va
yuqoridagi zero-balance shartida orderni cancelled qiladi. Keyin seat/policy
ochilsa uning o‘rniga unallocated source’lar `allocation` orqali fulfillmentga
bog‘lanadi. Cross-order money reallocation COMMERCE-01 scope’ida yo‘q va yangi
ADR/manifest unitsiz implement qilinmaydi.

### 6.7 `PaymentTransaction`

Pul haqiqatining append-only ledgeri.

| Field | Contract |
|---|---|
| `public_id`, `order` | lineage |
| `kind` | `settlement/unallocated_inflow/allocation/refund/reversal/adjustment`; provider `void` COMMERCE-01 scope’ida yo‘q |
| `direction` | `inflow/outflow/neutral`; `allocation`gina neutral, adjustment uchun ma’no noaniq qolmaydi |
| `fact_origin` | `bank_observed/platform_action/neutral`; settlement/unallocated/reversal/adjustment bank-observed, refund platform-action, allocation neutral |
| `amount_minor`, `currency` | positive integer minor-unit magnitude; ledger sign `direction`dan olinadi |
| `occurred_at`, `occurred_at_source`, `recorded_at` | bank va platform vaqti alohida; noma’lum vaqt to‘qilmaydi |
| `reference_hmac`, `reference_suffix`, `hmac_key_version`, `evidence` | normalized raw reference transient; full value saqlanmaydi/loglanmaydi. Reversal/adjustmentda evidence aynan current reviewable `compensation_proof` va reference fields required; refundda null |
| `observation_namespace`, `observation_role`, `observation_basis`, `observation_fingerprint`, `observation_key_version` | cross-family external-cash dedup identity; settlement/unallocated/reversal/adjustmentda required, refund/allocationda null; role `cash_inflow|bank_outflow_correction` user-selectable kind emas |
| `source_transaction` | refund/reversal/adjustmentning quyidagi exact matrixdagi ayni order/currency source’i; settlement/unallocated/allocationda null; self/cycle deny |
| `resolution` | unallocated, allocation va compensating kindlarda majburiy; manual-resolution orqali settlementda optional `PaymentResolution` `PROTECT` |
| `actor`, `reason_code`, `internal_note` | audit; learnerga chiqmaydi |
| `idempotency_key`, `request_fingerprint` | unique logical mutation |

Kind/direction contracti qat’iy:

- `settlement = inflow`, source null, order currency; direct cash confirmation va
  fulfillment ayni transactionda bo‘lgandagina ishlaydi;
- `unallocated_inflow = inflow`, source null, `PaymentResolution(outcome=hold)`
  majburiy; real received cashni yozadi, ammo period/grant/delivery yozmaydi;
- `allocation = neutral`, source FK o‘rniga quyidagi `PaymentAllocationSource`
  qatorlari va `PaymentResolution(outcome=settle)` required; cashni qayta
  sanamasdan fulfillmentni oldingi unallocated inflowlarga bog‘laydi;
- `refund = outflow`, source aynan `settlement|allocation|unallocated_inflow`;
  partial fulfilled refund faqat COM-D4 admitted bo‘lsa, unallocated source base
  safety refundi esa uning full remaining balance’i;
- `reversal = outflow`, source aynan real cash inflow bo‘lgan
  `settlement|unallocated_inflow`, hech qachon neutral/multi-source `allocation`
  emas; bir yoki bir nechta verified bank reversalning cumulative summasi source
  gross amountidan oshmaydi, ammo oldingi platform refund sabab current net 0
  bo‘lsa ham real reversal yoziladi. Har reversalga raw bank reference, current
  reviewable `compensation_proof`, external-observation identity va reason required.
  Unallocated source allocationda ishlatilgan bo‘lsa
  dependent allocation/period/grant ham lock qilinib explicit access outcome
  COM-D4/D5ga ko‘ra atomik yoziladi;
- `adjustment = inflow|outflow`, COMMERCE-01da faqat bank-observed required cash
  correction; source aynan
  `settlement|unallocated_inflow` + `PaymentResolution`; neutral allocationni
  cash source qilib ko‘rsatmaydi. Raw bank reference, current reviewable
  `compensation_proof`, external-observation identity va COM-D5 revenue/access
  outcome’i required; ownerning dalilsiz
  bookkeeping entrysi emas, order snapshot rewrite qilinmaydi.

`PaymentAllocationSource` COM1.1bdayoq yaratiladi: `allocation_transaction`,
`unallocated_inflow`, positive `amount_minor`, `currency`, `created_at`; DB
`UNIQUE(allocation_transaction, unallocated_inflow)` va allocation tomoni faqat
`PaymentTransaction(kind=allocation)`, source tomoni faqat
`kind=unallocated_inflow` bo‘lishi locked service+reconciliation bilan
tekshiriladi. Allocation source qatorlari append-only. Ayni order/currencydagi
bir yoki bir nechta unallocated inflow qismlari exact due’ni yig‘ishi mumkin;
allocation line summasi allocation amountiga va order due’ga aynan teng
bo‘lmasa fulfillment yozilmaydi. Allocation cash outflow/“consumption” emas.
Har real-cash source uchun `source_cash_net = inflow + source-bound inflow
adjustment - direct refund - allocation-refund split - reversal - source-bound
outflow adjustment`.
Unallocated source uchun `designated = allocation line sum` va
`free_unallocated = source_cash_net - designated`. Allocation yozilayotgan
paytda har source `source_cash_net >= yangi cumulative designated`, barcha line jami
exact due va order cash net nonnegative bo‘lishi shart. Base-safety refund faqat
musbat `free_unallocated`ning to‘liq summasini qaytaradi; allocated backingni
COM-D4siz refund qilmaydi. Source resolutioni `kind=post_lapse_inflow` bo‘lsa
`designated` doim 0, allocation qat’iy deny va yagona ruxsatli disposition
source-bound full refund + order state o‘zgarmas `lapsed`; uni yangi active
orderga ko‘chirish yoki eski orderni reopen qilish COMMERCE-01 scope’ida yo‘q.

Allocation-backed refund underlying cashni yashirmaydi. COM1.1b
`PaymentRefundSource(refund_transaction, allocation_source,
cash_source_transaction, amount_minor, currency, created_at)` append-only
qatorini ham yaratadi: refund tomoni aynan `kind=refund` va uning
`source_transaction`i allocationga teng; `allocation_source` ayni allocationning
`PaymentAllocationSource` qatori; cash source shu qatorning unallocated inflowi.
DB `UNIQUE(refund_transaction, allocation_source)`; service/reconciliation har
refund line summasi refund amountiga tengligini va har allocation source bo‘yicha
cumulative refund source summasi original line amountidan oshmasligini locked
holda tekshiradi. Direct settlement/unallocated refundda line 0; allocation
refundida kamida 1 va barcha source line exact required.

Split owner inputi emas: service oldingi refund source qatorlarini lock qiladi,
har source `remaining_i = allocation_line_i.amount - cumulative_refunded_i`ni
hisoblaydi, refundni remaining summaga proporsional floor bilan bo‘ladi va qolgan
minor birliklarni fractional remainder descending, tie’da cash-source public ID
ascending tartibida bittadan tarqatadi. Shu deterministic largest-remainder
algoritmi rerun/idempotencyda ayni splitni beradi. Shundan keyin real source
`source_cash_net` direct refundlar bilan birga unga tegishli
`PaymentRefundSource.amount_minor`ni ham ayiradi; multi-source refund funding
backing/deficitni aniq kamaytiradi.

Funding formulasi direct settlementni ham qamraydi va yagona normativ ta’rifga
ega. Fulfillment `settlement` bo‘lsa source uchun `funding_required =
settlement.amount_minor`; `allocation` bo‘lsa har unallocated source uchun
`funding_required = SUM(PaymentAllocationSource.amount_minor)`. Har ikkala
holatda `funding_backing = max(0, source_cash_net)` va source deficit
`max(0, funding_required - funding_backing)`; order `funding_deficit`i barcha
fulfillment source deficitlari yig‘indisi. Keyingi haqiqiy bank reversal
settlement/allocation tarixini o‘chirmaydi va designated summani “ikki marta
sarf” deb hisoblamaydi. Deficit >0 bo‘lsa dependent transaction, period va grant ham
lock qilinadi. Published COM-D4/D5 bo‘lsa explicit revoke/shorten/retain
natijasi; qaror hali unresolved bo‘lsa bank faktini yo‘qotmaslik uchun reversal
ledgeri + `access_disposition=retain_with_debt` + critical reconciliation
finding + owner outbox ayni transactionda yoziladi. Keyingi
`resolve_funding_deficit` append-only entitlement decision bilan findingni
yopadi; eski ledger/resolution update qilinmaydi. Order cash neti verified tashqi
fakt sabab manfiy bo‘lishi mumkin, ammo §6.7adagi exact deficit projectionisiz
emas; bank fakti source lineage’da qoladi va funded-access drift jim emas. Direct
settlement, single va multi-source allocation ayni formuladan foydalanadi.

Bir real bank observationini ikki orderga yoki ikki idempotency key bilan
yozmaslik faqat request idempotencyga tayanmaydi. Har
`settlement|unallocated_inflow|reversal|adjustment` uchun user tanlamaydigan
`observation_role` ishlatiladi: `settlement|unallocated_inflow|inflow adjustment
→ cash_inflow`; `reversal|outflow adjustment → bank_outflow_correction`.
`observation_fingerprint = HMAC(dedup_key_version, canonical(v3,
observation_role, basis, observation_namespace_id,
normalized_bank_reference))`; bank reference yo‘q inflowda input faqat
`canonical(v3, cash_inflow, evidence_fingerprint,
observation_namespace_id)` bo‘ladi. Shuning uchun settlement↔unallocated va
reversal↔outflow-adjustment qayta klassifikatsiyasi bir external factni ikkinchi
marta yozolmaydi, original inflow va keyingi bank outflow esa role bilan ajraladi.
Claim qilingan amount/currency/time identityga kiritilmaydi — ayni bytesni boshqa
raqam/vaqt bilan yuborib dedupni chetlab o‘tib bo‘lmaydi; existing observationga
ular mos kelmasa suspicion finding va manual resolution ochiladi.
`evidence_fingerprint`
validated original bytes digestidan olinadi, digestning o‘zi token/logga
chiqmaydi. `observation_basis=bank_reference|evidence_fingerprint`; compensation
uchun faqat `bank_reference`, referencesiz basis faqat inflowda. DB partial
`UNIQUE(observation_namespace, observation_key_version,
observation_fingerprint)` `kind IN (settlement, unallocated_inflow, reversal,
adjustment)` uchun.
`observation_namespace` `PaymentObservationNamespace`ga `PROTECT`; u orderdagi
immutable destination versionning namespace’iga aynan tengligi locked service
va reconciliationda tekshiriladi. Bir xil real recipientning destination
revisioni yoki alohida familysi alias orqali shu namespace’ga qaytadi.

Command §5.4dagi key-purpose va stable `PaymentObservationNamespace`ni lock
qilib, avval barcha retained dedup-key versionlari bilan candidate HMAClarni
hisoblaydi va existing external observationni qidiradi, keyin current version
bilan insert qiladi. Key rotation/current
flip ham ayni parent lockini oladi; eski key duplicate-detection/financial
retention tugamaguncha retire qilinmaydi. Shu sabab cross-order parallel request
different order locklari ortida yashirinmaydi; same-key race’ni DB unique,
rotation chegarasini parent mutex yopadi. Match topilsa yangi cash row 0;
cash-inflow matchida existing transaction/order immutable qoladi, incoming order
typed `duplicate_payment` manual resolutionga. Ayni role matchi boshqa kind bilan
kelsa `OBSERVATION_CLASSIFICATION_CONFLICT`, yangi money row 0 va owner finding;
ayni compensation kind/request bo‘lsa existing result readback. Reconciliation finding relevant
public IDlarga bog‘lanadi. Bank reference yo‘q inflow observationi COMMERCE-01da direct settlement
bo‘lmaydi: owner fresh reauth bilan avval `unallocated_inflow`, keyin alohida
allocation yoki full refund; bu “high-confidence fingerprint”ni bankning
absolyut haqiqatiga aylantirmaydi. Dedup collision owner tomonidan unique’ni
bypass qilib ikkinchi inflow yaratish bilan emas, bankning boshqa immutable
reference’i yoki reconciliation orqali hal qilinadi.

DB `CheckConstraint` kind/direction/source nullabilityni aynan shu mapga bog‘laydi;
partial `UniqueConstraint(order)` `kind IN (settlement, allocation)` uchun bitta
fulfillment transactionni, `UniqueConstraint(resolution)` unallocated,
allocation va har compensating operation rowining bittaligini beradi.
Reversal/adjustment replayini source unique emas, yuqoridagi external-observation
unique’i yopadi; bir source’da bir nechta distinct bank reversal bo‘lishi mumkin.
Refund/reversal ham typed `PaymentResolution` talab qiladi; FK ortidagi source kind va same
order/currency matritsasini DB CheckConstraint ifodalay olmaydi, shu sabab ayni
versionlangan validator locked service + reconciliationda majburiy.

Source-bound formulalar ham exact. Platform-controlled refund uchun settlement/
allocationda cumulative refund source commercial amountidan oshmaydi;
unallocated base refund esa faqat musbat `free_unallocated`ni to‘liq oladi.
Bank-observed cumulative reversal har `settlement|unallocated_inflow` source’ning
gross amountidan oshmaydi; u oldingi platform refunddan keyin ham kelishi mumkin.
Bank adjustmentning source/direction boundi policy/proof bilan alohida. Har
formula same-currency va same-order locked rows bilan tekshiriladi. Oddiy
platform action order cash netini manfiy qilmaydi; verified tashqi reversal yoki
required outflow correction manfiy qilsa quyidagi CashDeficit atomik yoziladi.

Ledger immutable; compensating command eski rowni update qilmaydi. Har source
bo‘yicha consumption va har currency/order bo‘yicha cash net locked holda
tekshiriladi: cash net = `settlement + unallocated_inflow + inflow adjustment -
refund - reversal - outflow adjustment`; `allocation` cash neutral. Negative
cash net faqat exact `CommerceCashDeficit` projectioni bilan ruxsat. Revenue/
access projection faqat `settlement|allocation`ni hisoblaydi; adjustmentning
revenue/access ta’siri COM-D5 explicit bo‘lmasa 0, cash report esa allocationni
hisoblamaydi — ikki marta revenue/cash yo‘q. Defaultda direct
settlement yoki allocation amounti aynan order due; partial/overpayment/refund
HOLD bo‘lsa `POLICY_NOT_ADMITTED`, lekin policy admit qilmagan real cash
`unallocated_inflow` sifatida qayd etilib to‘liq refund qilinishi mumkin.
`occurred_at` nullable va faqat bank
dalilida exact vaqt borida yoziladi; non-null bo‘lsa `occurred_at_source` aynan
`bank_statement` yoki `reviewer_asserted`, null bo‘lsa source ham null DB check.
`recorded_at` server vaqti doim non-null.
Analytics `effective_at = COALESCE(occurred_at, recorded_at)` ishlatadi, lekin
har row/chartda `bank_reported` yoki `platform_recorded` time-basis labelini
saqlaydi — fallback bank vaqti deb ko‘rsatilmaydi.

`reference_hmac` va `ip_hmac` per-purpose secret key bilan HMAC-SHA-256;
plain/unsalted hash emas. Key ID/rotation va finite retention mavjud. Ular
anonymization emas, pseudonymized data hisoblanadi. Reviewer settlementda
server prefill qilgan expected amountni ko‘radi, ammo dalildagi **actual**
`amount_minor`, currency va mavjud bo‘lsa occurred-at/reference’ni tasdiqlaydi.
Raw reference faqat request davomida normalize→HMAC qilinib tashlanadi. Amount
mismatch COM-D7 hal bo‘lmasa settlement emas, `manual_resolution`.

### 6.7a `CommerceCashDeficit` va eventlari

Verified bank reversal yoki required outflow correction oldingi platform refund
bilan qo‘shilib order cash netini manfiy qilishi mumkin; bank faktini rad etish
yoki soxta inflow yozish taqiqlanadi. COM1.1b shu sabab mutable CAS projection
`CommerceCashDeficit`ni yaratadi: `public_id`, `order PROTECT`, `currency`,
nonnegative `current_deficit_minor`, nonnegative `recognized_loss_minor`,
`state=open|partially_written_off|written_off|recovered`, positive `version`,
created/updated/closed timestamps. DB `UNIQUE(order, currency)`, currency orderga
mos; `recognized_loss_minor <= current_deficit_minor`. Derived
`outstanding_receivable_minor = current_deficit_minor - recognized_loss_minor`.
State map exact: deficit 0/loss 0 → `recovered`; deficit >0/loss 0 → `open`;
0 < loss < deficit → `partially_written_off`; loss=deficit>0 → `written_off`.

Har o‘zgarish append-only `CommerceCashDeficitEvent` bilan isbotlanadi: deficit,
monotonic `sequence`, `kind=external_increase|cash_recovery|write_off|
write_off_reversal`, signed `deficit_delta_minor`, signed
`recognized_loss_delta_minor`, nullable `trigger_transaction PROTECT`, actor yoki
service identity, reason code, one-to-one operation receipt,
`expected_version/resulting_version`, created_at. DB `UNIQUE(deficit, sequence)`,
`UNIQUE(operation_receipt)` va non-null trigger transaction uchun partial
`UNIQUE(trigger_transaction)`. Same-row map:

- `external_increase`: positive deficit delta, zero loss delta, trigger aynan
  verified `reversal|outflow adjustment`;
- `cash_recovery`: negative deficit delta, nonpositive loss delta, trigger aynan
  verified `inflow adjustment`; delta magnitude pre-event deficitdan oshmaydi,
  loss delta esa `recognized_loss <= new deficit`ni saqlash uchun zarur qismini
  avtomatik revers qiladi;
- `write_off`: zero deficit delta, positive loss delta, trigger null;
- `write_off_reversal`: zero deficit delta, negative loss delta, trigger null.

Locked service va reconciliation exact tengliklarni tekshiradi:
`current_deficit_minor = max(0, -order_cash_net)`;
projection maydonlari genesisdan barcha event delta yig‘indisiga teng; event
expected/resulting versioni ketma-ket +1. Verified tashqi transaction netni
birinchi yoki yana chuqurroq manfiy qilsa transaction, event, projection,
resolution/finding/outbox bitta DB transactionda yoziladi. Inflow adjustment netni
tiklasa recovery event ayni transactionda; deficitdan ortiq qismi oddiy positive
cash bo‘lib qoladi. Ownerning `resolve_cash_deficit` write-offi ledgerni
o‘zgartirmaydi, faqat loss/receivable projectioni va outboxni CAS qiladi. Recovered
row o‘chmaydi va keyingi yangi tashqi deficitda qayta ochiladi. Platform action
negative cash yaratolmaydi; bank truth esa CashDeficit yozilmagani uchun rad
etilmaydi.

### 6.8 `Subscription` va `SubscriptionPeriod`

`Subscription` user+course commercial lineage; cohort transferda yangidan
boshlanmaydi.

`Subscription` fieldlari: `public_id`, `user`, `course`, `status_projection`,
`created_at`, `closed_at`, `version`. DB `UNIQUE(user_id, course_id)` — bir umrga
bitta lineage; qayta sotib olish yopilgan rowni yangi period bilan reopen qiladi,
ikkinchi Subscription yaratmaydi. `closed_at` projection, uniqueness sharti emas.

Projection enumi aynan `scheduled|active|grace|closed` va child periodlar bo‘yicha
precedence `active > grace > scheduled > closed`: kamida bitta non-revoked period
shu state’da bo‘lsa yuqori precedence, aks holda barcha period `expired|revoked`
yoki period 0 bo‘lsa `closed`. `closed_at` faqat `closed`da non-null; terminalga
birinchi kirgan transitionning DB transaction vaqti, yangi scheduled period
yaratilganda nullga qaytadi. Har period create/activate/grace/expire/revoke/shorten
commandi Subscriptionni avval lock qiladi, child mutation bilan ayni transactionda
projectionni recompute qilib Subscription `version+1` yozadi; UI/renewal selector
shu projection bilan birga exact child/effective-endni ham tekshiradi, taxminiy
statusga tayanmaydi.

`SubscriptionPeriod` fieldlari:

- subscription, order va source fulfillment transactionga `PROTECT`;
- offer version va `policy_version PROTECT`; positive
  `grace_capability_schema_version` hamda sorted unique `grace_capabilities`
  immutable snapshoti;
- `starts_at`, `ends_at`, optional `grace_ends_at`, non-null
  `effective_access_until`;
- `effective_access_reason=contract_term|grace|renewal_superseded|
  compensation_shorten|revoked`, nullable `effective_access_transaction`,
  nullable `effective_access_resolution`, nullable `superseding_period`;
- `state`: `scheduled/active/grace/expired/revoked`;
- positive `version`; lifecycle/revoke/shorten/renewal endpoint CASida +1;
- `revocation_reason`, actor/time;
- unique source transaction;
- same subscriptionda non-revoked effective access overlap yo‘q. Production
  PostgreSQL migration `btree_gist` va partial `ExclusionConstraint` bilan
  `(subscription_id WITH =, tstzrange(starts_at,
  effective_access_until, '[)') WITH &&)`ni taqiqlaydi. Same-row checks:
  `starts_at < ends_at`, `starts_at <= effective_access_until`, va
  `effective_access_until <= COALESCE(grace_ends_at, ends_at)`. Grace yo‘q yoki
  capability list empty bo‘lsa endpoint=ends_at; grace bor va list non-empty bo‘lsa
  `grace_ends_at > ends_at` hamda initial endpoint=grace_ends_at. Period `active`
  paytida ham bu kelajakdagi maksimal access boundary; `as_of >= ends_at`da worker
  state’ni `grace`ga o‘tkazadi. Early shorten/revoke’da endpoint < ends_at ruxsat va
  compensation transaction+resolution ikkalasi required; renewal-supersededda
  `superseding_period` required va (`grace_ends_at` non-null bo‘lsa
  `ends_at <= endpoint <= grace_ends_at`, null bo‘lsa `endpoint=ends_at`)
  (early renewal exact contractual endga teng bo‘lishi mumkin).
  Source/reason XOR va lineage locked service+reconciliationda.
  Exclusion constraint renewal graph rewrite’i uchun PostgreSQLda `DEFERRABLE
  INITIALLY DEFERRED`; transaction commitida overlap 0 bo‘lishi shart.
  SQLite faqat local/test compatibility: ayni effective interval service lock
  checki bor, ammo release evidence PostgreSQL constraint/race testidan keladi.

Barcha persisted instant UTC-aware; contractual paid term `[starts_at, ends_at)`,
real access esa `[starts_at, effective_access_until)`. Grace faqat endpoint
ends_atdan katta bo‘lsa `[ends_at, effective_access_until)`; early terminationda
contractual `ends_at` tarix uchun o‘zgarmaydi. Display user timezone’da. Precision
DB timestamp precisioni bilan bir xil. Initial/renewal uchun exact formula:
`continuity_anchor = min(latest_non_revoked_paid_period.ends_at,
latest_non_revoked_paid_period.effective_access_until)` va `starts_at =
max(approval_at, continuity_anchor)`; oldingi period bo‘lmasa `approval_at`.
`ends_at` immutable offer term calculatoridan.
Backdated/future manual effective date bu formula ichida yo‘q va alohida owner
override policy bo‘lmasa rad etiladi.

Settlement bitta DB `as_of` instantini oladi. Yangi period uchun
`starts_at <= as_of < effective_access_until` bo‘lsa initial state `active`,
`as_of < starts_at` bo‘lsa `scheduled`; `effective_access_until <= as_of` bo‘lsa
settlement `PERIOD_INTERVAL_INVALID` bilan whole rollback. Har commercial grant
shu period state’ini mirror qilib mos ravishda `active` yoki `scheduled` yaratiladi;
shundan keyin Subscription projection ayni transactionda recompute qilinadi.

Compensation policy `shorten_to_event_time` tanlab, verified event vaqti period/
grant `starts_at`idan oldin yoki aynan teng bo‘lsa actual action **scheduled
revoke**: locked period `scheduled→revoked`, `effective_access_until=starts_at`,
`effective_access_reason=revoked`, period-level source aynan compensating
transaction+PaymentResolution va version+1;
uning barcha scheduled grantlari esa alohida target-grant
`EntitlementOverrideDecision`lari bilan `scheduled→revoked`, same resolution
va version+1 bilan ayni transactionda. Zero-length real-access interval overlap
hisobiga kirmaydi, contractual `ends_at` o‘zgarmaydi. Lifecycle worker faqat
`state=scheduled` + expected versionni conditional update qiladi; revoked rowni
skip etadi va compensation-vs-activation race’da lock/CAS g‘olibi bitta natija
beradi. Event `starts_at < event_time < effective_access_until` bo‘lsa endpoint
event_timegacha shorten; event endpointdan keyin/teng bo‘lsa retain. Bu uchala
boundary PostgreSQL race testida period va barcha grant uchun atomik isbotlanadi.
Event time server transaction vaqtidan kelajak bo‘lsa correction write 0/finding.
Interval ichidagi shorten event timegacha endpoint/har grant endini qisqartirib,
event time ≤ transaction as-of bo‘lgani uchun affected `active|grace` **yoki
worker-lag sabab hali scheduled bo‘lsa ham starts_at < event_time bo‘lgan** period
va grantlarni ayni transactionda `expired` qiladi. Bu scheduled→expired historical
shorten transitioni accessni bir lahza ham activate qilmaydi; `revoked` faqat
event_time≤starts_at pre-start yoki explicit revoke actioniga tegishli.

`grace_ends_at` policy bo‘yicha maksimal imkoniyatni audit uchun saqlaydi;
`effective_access_until` real exclusion/projection endpoint. Renewal oldingi
period grace’i ichida yoki oldindan scheduled bo‘lsa Subscription va oldingi
periodni lock qilib, transactionda avval yangi periodni insert qiladi (deferred
exclusion vaqtinchalik overlapni commitgacha ruxsatlaydi), keyin oldingi
`effective_access_until`ni yangi `starts_at`gacha CAS bilan faqat qisqartirib
`superseding_period` FKni yangi rowga o‘rnatadi va transition audit/outboxini
yozadi. Commitda FK mavjud va exclusion overlap 0 bo‘lmasa whole rollback.
Shuning uchun paid renewal grace’ni
supersede qiladi, ikki grant bir payt active bo‘lmaydi va historical
`grace_ends_at` yo‘qolmaydi; endpoint hech qachon keyinroqqa uzaytirilmaydi.
Oldingi periodning qisqartirilgan endpointi `<=` ayni fixed DB `as_of` bo‘lsa uning
`scheduled|active|grace` state’i atomik `expired`ga o‘tadi; aks holda old state
saqlanadi. Bu period transitioni, barcha grant mirrorlari va Subscription
recompute’i yangi period inserti bilan bitta transaction/deferrable constraintda.

Compensationda period-level `effective_access_resolution` bitta shared source;
periodning har affected commercial grantiga exactly one target-specific
`EntitlementOverrideDecision(source_payment_resolution=same resolution)` yoziladi.
Period bir qarorni “primary” deb tanlamaydi. Required decision count aynan
affected grant countiga teng, hammasi bir xil actual disposition/event boundaryga
ega; transaction+resolution+decisions+period/grants atomik va reconciliation
cardinalityni qayta isbotlaydi.

Period create invariant: subscription `(user, course)`i order bilan teng;
source transaction `kind IN (settlement, allocation)` va ayni order/currencyga
tegishli. `allocation` bo‘lsa uning immutable source-line summasi transaction
amountiga va order due’ga aynan teng, har unallocated source consumption boundi
lock ostida PASS bo‘lmaguncha period/grant/delivery yozilmaydi. Period
order/subscription/transaction lineage’dan bittasi ham adapter inputidan alohida
tanlanmaydi. Unique source fulfillment transaction DBda, cross-table tenglik va
allocation summalari locked service + reconciliationda.

### 6.9 `EntitlementGrant`

Commercial bo‘lmagan grant va funding-deficit access qarori alohida append-only
`EntitlementOverrideDecision`: `public_id`, user/course/capability,
`kind=grant|revoke|retain|shorten`, finite `starts_at/ends_at`, nullable
`target_grant`, nullable `source_payment_resolution`, nullable `source_finding`,
nullable `applied_compensation_rule PROTECT`,
shorten uchun nullable `effective_until`, actor, reason code, internal note,
request/idempotency key va created_at. `source_payment_resolution` COM1.1c1da,
`source_finding` esa `CommerceReconciliationFinding` bilan birga COM1.1c2ning
aniq migrationida qo‘shiladi — yashirin migration emas.

Same-row map va interval ma’nosi exact: manual `grant`da `[starts_at,ends_at)`
yangi grantning finite intervali, target/source/finding/effective-until null;
manual `revoke`da same user/course/capability active grant `PROTECT` target
required, `[starts_at,ends_at)` aynan targetning mutationdan oldingi frozen
interval snapshoti, source/finding/effective-until null. Funding
`revoke|retain|shorten`da target va source resolution required va
`starts_at=target.starts_at`, `ends_at=target.ends_at` pre-action snapshot;
`retain`/`revoke`da effective-until null, `shorten`da
`target.starts_at < effective_until < target.ends_at`. Immediate compensationda orderning frozen rule’i,
deferred `retain_with_debt` findingini yopayotgan qarorda source finding hamda
resolution vaqtidagi published `remediation_allowed` rule required; ayni rule
`applied_compensation_rule`da freeze bo‘ladi. Barcha kindda `starts_at < ends_at`;
target actionda snapshot tengligi locked service/reconciliation, nullability va
shorten boundi DB same-row checks bilan. DB source/finding ikkalasi null yoki valid allowed combination checklari va
partial `UNIQUE(source_payment_resolution, target_grant)`; FK ortidagi
resolution disposition/finding/lineage/interval locked service+reconciliationda.
Faqat owner capability yaratadi; update/delete yo‘q.

| Field | Contract |
|---|---|
| `user`, `course`, `capability` | typed capability |
| `period`, `source_transaction` | commercial grantda ikkalasi ham majburiy |
| `override_decision` | `EntitlementOverrideDecision`; commercial source bilan XOR |
| `starts_at`, `ends_at` | normally `starts_at < ends_at`; only pre-start revoked commercial projectionda zero-length allowed |
| `state` | `scheduled/active/expired/revoked` |
| `version` | positive projection CAS; revoke/shorten/renewalda +1 |
| `revocation_transaction`, `revocation_override_decision` | revoked state uchun compensation yoki explicit override XOR source |
| `revoked_by/at/reason` | source’dan projection qilingan explicit audit |

DB source shape aynan ikkita: commercialda `period` va `source_transaction`
non-null, `override_decision` null; override’da `period/source_transaction` null,
`override_decision` non-null va finite `ends_at`. Shu **same-row nullability XOR**
DB `CheckConstraint` bilan deny qilinadi. FK ortidagi
`override_decision.kind=grant`, uning user/course/capability tengligi va commercial
transactionning shu period/order `settlement|allocation` fulfillmentiga
tegishliligi, allocation source-line sum/consumptioni DB CheckConstraint bilan
ifodalanmaydi; locked service + model validation + reconciliation ayni stable
code bilan tekshiradi, DB buni qila oladi deb da’vo qilinmaydi.
DB partial `UNIQUE(period, capability)` commercial grantni va
`UNIQUE(override_decision)` override grantni takrorlanishdan saqlaydi. Revoke
decision yangi grant manbasi bo‘lmaydi; target grant state’ini atomik projectionda
`revoked` qiladi va `revocation_override_decision` orqali bog‘lanadi. Refund/
reversal/adjustment policy access revoke qilsa ayni compensating
`PaymentTransaction` `revocation_transaction` bo‘ladi. `state=revoked`da shu ikki
revocation source’dan aynan biri non-null; boshqa state’da ikkalasi null. Bu
fieldlar COM1.1c1 schema’sida oldindan mavjud, COM1.5d1 yashirin migration
qo‘shmaydi. Revoke decision/transaction target user/course/capability/period
lineage’i service+reconciliationda tekshiriladi.
Grant interval DB checki exact: non-revoked va barcha override-source grantlarda
`starts_at < ends_at`; `starts_at = ends_at` faqat `state=revoked`, commercial
period/source present, revocation source non-null, period ham revoked va
`period.effective_access_until=period.starts_at=grant.starts_at` bo‘lgan pre-start
compensation projectionida. `starts_at > ends_at` hech qachon yo‘q. Boundary
test scheduled period/grantni zero-access revoke qilib entitlement readini 0
qilishini isbotlaydi.
`retain` access fieldini o‘zgartirmay explicit qarorni/finding resolutionni
yozadi. `shorten` target grant `ends_at`i, uning commercial period
`effective_access_until`i va shu periodning boshqa capability grantlarini ayni
timestampgacha faqat qisqartiruvchi CAS qiladi; intervalni uzaytira olmaydi.
Funding qaroridagi barcha affected grantlar oldindan lock qilinadi va decisionlar,
period/grant projection, finding resolution hamda outbox bitta transactionda;
qisman access outcome yo‘q.
Commercial grant intervali capabilityga bog‘liq: slug periodning frozen
`grace_capabilities`ida bo‘lsa `ends_at=period.effective_access_until`, aks holda
`ends_at=period.ends_at`; shu sabab grace faqat allowlisted subsetga access beradi.
Period endpoint contract enddan oldinga qisqarsa barcha grantlar
`min(old_grant_end, new_endpoint)`gacha qisqaradi. Renewal oldingi period endpointini qisqartirganda uning `scheduled|active`
(period grace’da bo‘lsa ham grant active bo‘lishi mumkin) non-revoked grantlari
ham ayni transaction/expected versionda qisqaradi; endpoint as-ofdan o‘tgan bo‘lsa
`expired`, aks holda old state saqlanadi, version+1 va transition audit/outbox
yoziladi. Grant
overlap scope’i `(user, course, capability)` va interval `[starts_at, ends_at)`.
Commercial, manual va funding-decision source’larining barchasi shu scope’da
bir-birini overlap qilishi **taqiqlanadi**; capability union/stacking yo‘q.
PostgreSQL partial `ExclusionConstraint` non-revoked grantlar uchun
`(user WITH =, course WITH =, capability WITH =, tstzrange(starts_at, ends_at,
'[)') WITH &&)`ni deny qiladi va renewal graph rewrite uchun `DEFERRABLE
INITIALLY DEFERRED`; SQLite service lock checki va PostgreSQL parallel
testi shu semantikani mirror qiladi. Adjacent `[a,b)`/`[b,c)` ruxsat.
Unknown plan/capability fail-closed. `core.entitlements` cutover paytida shu
grant projectionini o‘qiydi; shadow davrda legacydan kamroq access bersa alert,
ko‘proq bersa rollout block. Legacy accessni yashirin kengaytirmaydi.

### 6.9a `CommerceDeliveryTransitionLink`

Commercial access bilan pedagogik cohort membershipni aralashtirmasdan audit
qiladigan append-only bridge schema COM1.1c1da yaratiladi; COM1.2d2ning birinchi
internal delivery projectionidan boshlab majburiy yoziladi, COM1.5d2 lifecycle
adapterlarini shu mavjud contractga kengaytiradi:

| Field | Contract |
|---|---|
| `event_id`, `kind` | unique UUID; allocate/transfer/release/freeze/reactivate |
| `subscription_period`, `order`, `resolution` | period majburiy; order/resolution relevant bo‘lsa `PROTECT` |
| `enrollment_transition` | existing `cohorts.EnrollmentTransition`ga nullable unique FK; allocate/release direct mutationi uchun null |
| `source_enrollment`, `target_enrollment`, `source_cohort`, `target_cohort` | pre/post snapshot FKlari, semantikaga mos nullability |
| `reason_code`, `actor`, `created_at` | allowlisted reason va audit; free-text learnerga chiqmaydi |

Har command uchun operation receipt/event ID unique. Link row enrollment/seat
mutationi bilan ayni transactionda; transitionga tegmagan expiry grantni yopishi
mumkin, lekin membershipni yashirin ko‘chirmaydi yoki joyni jim bo‘shatmaydi.

### 6.10 `CommercePolicyVersion`

Hard-coded operatsion qiymatlar immutable, audited policy revisionga ko‘chadi:

- `status`: `draft/published/retired`; positive monotonic `revision` with DB
  `UNIQUE(revision)`; allocator PostgreSQL `commerce_policy_revision_seq`
  `nextval`idan foydalanadi (gap ruxsat, `MAX+1` va client revision taqiqlanadi;
  SQLite test adapteri process mutex+transaction bilan serialize qiladi); positive
  `aggregate_version`; non-null `effective_from`,
  nullable `effective_until` with end > start;
- `quote_preview_minutes`, `order_payment_window_minutes`,
  `promo_reservation_minutes` — uch xil TTL, bir-birining aliasi emas;
- `late_evidence_window_minutes` — default `0` (late reopen deny); nonzero faqat
  COM-D16 published qarori bilan;
- `review_sla_minutes` (UI va alert; paymentni avtomatik tasdiqlamaydi);
- `sensitive_incident_response_minutes` default `15`, hard max `60`; restriction
  darhol, bu owner/security false-positive yoki manual purge uchun deadline va
  undan keyingi majburiy auto-erasure chegarasi — oddiy review SLA emas;
- nonnegative `grace_days`, positive `grace_capability_schema_version` va
  `grace_capabilities` JSON array: canonical entitlement registrysidagi allowlisted
  sluglarning sorted, unique string snapshoti; empty array grace’da access 0,
  unknown/duplicate/unsorted slug publish deny. Order policy FKni, period esa
  ayni immutable capability snapshotini freeze qiladi; grant projection undan
  tashqari capabilityni taxmin qilmaydi;
- nonnegative `renewal_open_before_end_days`; latest non-revoked effective access
  endidan shuncha kun oldin renewal ochiladi, barcha period terminal bo‘lsa late
  renewal darhol eligible;
- `plan_change_payment_mode=prepaid_only` (current scope’da yagona qiymat) va
  `plan_change_effective_rule=next_paid_boundary` safe default; boshqa boundary
  yoki credit/receivable COM-D2/D5 decision+roadmap amendmentisiz publish deny;
- `evidence_max_bytes`, raster MIME/dimension/pixel limits;
- schema boshidan exact va yashirin migration yo‘q: nullable positive
  `resubmit_limit` (null = va’da yo‘q, abuse rate-limit qoladi), non-negative
  `amount_tolerance_minor` default `0`, `allow_partial_refund` default `False`,
  `proration_policy` enum `none|credit_balance|invoice_adjustment`, default va
  COMMERCE-01da yagona admitted qiymat `none` (boshqalari COM-D2/D5 va yangi
  roadmap unitisiz publish deny), nullable
  `high_value_four_eyes_threshold_minor`;
- safe defaultdan boshqa qiymat tegishli COM-D qaror reference’isiz publish
  validationdan o‘tmaydi; field mavjudligi feature admissioni emas;
- `created/published_by/at`, reason va diff audit.

COM-D4/D5 qarorini runtime taxmin qilmaslik uchun COM1.1a1 shu boshidan dormant
`CommerceCompensationPolicyRule` child jadvalini ham yaratadi: immutable unique
`public_id`, policy version `PROTECT`,
`event_kind=platform_refund|bank_reversal|bank_adjustment_inflow|
bank_adjustment_outflow`, `funding_impact=none|partial|full`,
`access_action=not_applicable|retain|revoke|shorten_to_event_time`,
`revenue_action=cash_only|reverse_source_amount|manual_finding`, boolean
`remediation_allowed` default false, non-null owner
decision reference, reason/audit; DB `UNIQUE(policy_version, event_kind,
funding_impact)`. `shorten_to_event_time`da event effective time grant startidan
oldin/teng bo‘lsa actual revoke, grant oralig‘ida bo‘lsa barcha affected
grant/period endpointlari shu vaqtgacha qisqaradi, enddan keyin/teng bo‘lsa actual
retain; actual disposition resolution/override’da saqlanadi.

Draft parentda rule insert/update/delete faqat locked parentning expected
`aggregate_version`i bilan mumkin va har child mutation parent versionini +1
qiladi. Parent publish complete rule setni ayni lockda validate qilib expected
aggregate version+1 bilan parent/childrenni birga freeze qiladi; retire ham expected
aggregate version+1. Parallel tabning stale child edit/publishi `ORDER_STALE`
semantikasidagi 409 bilan write 0;
published yoki retired parentning childiga insert/update/delete DB trigger va
service guard bilan deny, Django admin read-only. Rule’ning alohida mutable
status/versioni yo‘q: historical identity parent revision+immutable public ID.
Policy o‘zgarishi yangi parent revision va yangi child set bilan; eski order
reference qilgan matrix hech qachon jim o‘zgarmaydi.

Same-row/publish validation: `funding_impact=none` faqat
`access_action=not_applicable`; partial/full impactda `not_applicable` deny;
`revenue_action=reverse_source_amount` source commercial amount/cumulative bounddan
oshmaydi. Safe bootstrap faqat unfulfilled/free unallocated cashni to‘liq
qaytarish kabi `none/not_applicable/cash_only` rule’iga ruxsat beradi; fulfilled
refund yoki boshqa qoida COM-D4/D5 decision reference’isiz publish bo‘lmaydi.
`select_compensation_rule(order_policy, event_kind, funding_impact)` aynan bitta
row talab qiladi. Platform actionda 0/>1 natija `POLICY_NOT_ADMITTED` va money
write 0; verified bank factida money row baribir yozilib
`retain_with_debt`+critical finding fallback ishlaydi. `retain_with_debt`
published final rule emas. `resolve_funding_deficit` orderning eski immutable
policy’sini tahrirlamaydi: resolution vaqtidagi `select_commerce_policy(now)`dan
event kind+funding impactga exactly-one `remediation_allowed=True` rule oladi,
uni override decisionga `PROTECT` qilib freeze qiladi va actual actionini
qo‘llaydi. 0/>1 bo‘lsa finding ochiq qoladi; implementer current policy yoki UI
inputidan o‘zboshimcha disposition tanlamaydi.

Published policy inplace edit qilinmaydi. Order o‘zi foydalangan policy
revisionini snapshot/reference qiladi; yangi revision eski order muddatini jim
o‘zgartirmaydi. COM1.1a1da mavjud
`core.OperationalSettings.checkout_quote_minutes` faqat
`quote_preview_minutes` uchun ownerga ko‘rsatiladigan draftga exact ko‘chiriladi;
owner publish qilgach Commerce policy yagona source bo‘ladi, eski maydon
read-only compatibility projectionga aylanadi. Order/payment window, promo TTL
va review SLA undan taxmin qilinmaydi — owner qiymat bermasa tegishli cutover
fail-closed.

Global published interval overlap qilmaydi: PostgreSQL
`ExclusionConstraint(tstzrange(effective_from, effective_until, '[)') WITH &&)`
`status=published` conditionida; null end infinity. Draftlar overlap qilishi
mumkin. `select_commerce_policy(as_of)` exactly one published effective row
talab qiladi; 0 yoki >1 `COMMERCE_POLICY_UNAVAILABLE`, quote/publish readiness va
tegishli worker mutationi fail-closed, critical health finding.
`quote_checkout`ning normativ `as_of`i transaction-scoped DB
`transaction_timestamp()` va token `issued_at`i aynan shu qiymat. Selector exact
policy rowini shared/read lockda oladi; quote expiry
`min(issued_at + quote_preview_minutes, offer/destination/promo effective_until
bo‘lsa ularning eng ertasi)`dan oshmaydi. Signed token policy public IDsi va
revisionini saqlaydi.

`create_order` **current policyga qayta select qilmaydi**: u token ko‘rsatgan
immutable policy rowini shared/read lockda olib, signature/binding/expiry bilan
birga `issued_at ∈ [effective_from,effective_until)` bo‘lganini tekshiradi va ayni
revision bilan server recalc qiladi. Quote chiqarilganda published bo‘lgan row
token muddati ichida `retired` bo‘lib qolsa ham quote honor qilinadi; retirement
business fieldlarni o‘zgartirmaydi yoki rowni o‘chirmaydi. Favqulodda savdoni
to‘xtatish CourseOffer pause yoki global writer safe-disable bilan qilinadi, valid
token semantikasini jim almashtirish bilan emas. Publish/retire ayni policy row va
overlap candidate’larini global lock tartibida exclusive lock qilgani uchun
quote/create check→commit race’i yo‘q. Token policy ID/revisioni topilmasa yoki
issued-at intervalga kirmasa `COMMERCE_POLICY_UNAVAILABLE`, row 0.
Orderga tegishli keyingi commandlar “current” policyga ko‘chmay, orderdagi
`pricing_policy_version` reference/snapshotni ishlatadi; faqat explicitly
operational incident max kabi global hard safety ceiling eski snapshotni
zaiflashtirmasdan qo‘llanadi.

### 6.11 `CommerceOperationReceipt`, outbox va runlar

`CommerceOperationReceipt`:

- actor/subject/command/idempotency key unique;
- canonical request fingerprint;
- `in_progress/succeeded/failed_retryable/failed_terminal`, `lease_token`,
  `lease_expires_at`, `retry_after_at`, `version`, `attempt_count`;
- result object/type/version va stable error code;
- bir key + boshqa fingerprint → `IDEMPOTENCY_CONFLICT`;
- terminal response replay ayni logical natijani qaytaradi.

Claim algoritmi normativ:

1. Qisqa outer transaction unique operation rowni `in_progress` lease bilan
   insert qiladi. Unique conflictda row lock qilinadi.
2. Fingerprint farq qilsa conflict; `succeeded/failed_terminal` bo‘lsa stored
   result; valid `in_progress` lease bo‘lsa `OPERATION_IN_PROGRESS` + readback/
   bounded Retry-After. Request DB lockni uzoq kutmaydi.
3. Expired lease faqat compare-and-swap (`old lease_token/version`) bilan yangi
   workerga o‘tadi; attempt counter oshadi. `failed_retryable` faqat
   `retry_after_at <= now` bo‘lganda ayni token/version CAS bilan `in_progress`,
   yangi token/lease va incremented attemptga o‘tadi. `failed_terminal` reclaim
   qilinmaydi.
4. Domain transaction global lock tartibida business rowlar bilan birga aynan
   claim qilingan `lease_token/version`ni `succeeded`ga CAS qiladi. CAS 0 row
   bo‘lsa stale worker exceptioni ko‘tarilib **butun domain transaction**, shu
   jumladan business mutation, rollback; commitdan keyingina outbox dispatch.
5. Domain transaction rollback qilsa oldindan yaratilgan claim row qoladi;
   alohida qisqa transactionda safe error class `failed_retryable` yoki
   `failed_terminal` qilinadi, lekin bu update ham o‘sha lease token/versionga
   scoped CAS; stale worker yangi owner natijasini overwrite qilolmaydi. Process
   crash bo‘lsa lease expiry reclaim beradi.
6. Evidence command fingerprinti raw binary emas, staged upload token +
   validated hashni ishlatadi. Boshqa command fingerprinti stable IDs, integer
   amounts, versions va zarur bo‘lsa per-purpose HMACdan quriladi; raw reference,
   promo, account yoki free-text yo‘q. Result payload PII/secret saqlamaydi.

Shu sabab “DB exactly once” deb transport da’vosi qilinmaydi; logical effect
stable operation receipt, constraints va transaction bilan idempotent.

`CommerceEventOutbox`:

- domain event ID/type/schema/version/aggregate/version;
- recipient reference, payloadning PII-minimal projectioni;
- `pending/leased/sent/dead`, `lease_token`, `lease_owner`, `lease_expires_at`,
  positive CAS `version`, cycle/lifetime attempt counts, manual-retry count,
  next-at/error class va sent-at;
- row domain write bilan ayni transactionda;
- consumer/event adapterga event ID idempotency key sifatida uzatiladi.

Outbox fence exact: due `pending` row `SELECT ... FOR UPDATE SKIP LOCKED` bilan
unique random token, expiry, attempt+1 va version+1ga `leased`; expired lease faqat
old token/version CAS bilan reclaim. Worker remote call oldidan token/version va
lease’da kamida configured network-timeout+safety-margin qolganini CAS readback
qiladi. `sent`, retry yoki `dead` finalize faqat ayni token/version CAS; 0 row
stale worker bo‘lib natijani overwrite qilmaydi. Remote provider idempotency keyni
qo‘llasa event ID majburiy; qo‘llamaydigan email/Telegram adapterida crashning
send→CAS oralig‘i sabab at-least-once va bir xil xavfsiz notification duplikati
mumkinligi ochiq contract — “exactly once” da’vosi yo‘q. In-app consumer DB
`UNIQUE(event_id, recipient)` bilan logical duplicate 0. Reclaim-vs-late-finalize,
timeout, crash-after-send va manual retry testlari majburiy.

Retry taxonomy exact: network timeout/connectivity, provider 429 va 5xx
`retryable`; malformed payload/schema, revoked recipient yoki deterministic 4xx
`terminal`; provider auth/config 401/403 terminal row bilan birga health-critical
alert. Retryable backoff `min(30s * 2^(cycle_attempt-1), 1h)` + event-IDdan
deterministic 0–10% jitter. `COMMERCE_OUTBOX_MAX_ATTEMPTS` default 12, hard range
1..50; limitda `dead`. `retry_dead_outbox(event_id, expected_version,
idempotency, reason)` owner fresh reauth bilan payload/recipient/configni qayta
validate qiladi va ayni rowni `dead→pending`, cycle attempts 0, lifetime count
saqlangan, manual-retry count+1, version+1 va next-at=nowga CAS qiladi;
`CommerceOperationReceipt` audit qoladi. Event ID/payload o‘zgarmaydi, clone yo‘q.
Dead rowni bulk/automatic reopen qilish taqiqlanadi. Manual retry uchun yashirin
numeric budget yo‘q: owner-only, fresh-reauth, per-event expected-version,
reason va terminal-cause-now-retryable validationi har urinishda majburiy;
`manual_retry_count` lifetime auditi saqlanadi va 3/10 thresholdlarda warning/
critical alert beradi, ammo haqiqatan tuzatilgan eventni taxminiy hard cap bilan
abadiy yetkazilmas holga tashlamaydi. Rate limit va parallel CAS bir eventga
bir vaqtning o‘zida bitta manual retry beradi.

`CommerceNotificationPreference` COM1.7bda aniq migration bilan yaratiladi:
`user`, `channel` (`email/in_app/telegram`), allowlisted `event_type`, `enabled`,
`version`, timestamps; DB `UNIQUE(user, channel, event_type)`. Security/finance
incidentlari mute qilinmaydi; preference yo‘q bo‘lsa transactional in-app
default ON, marketing emas.

`CommerceLifecycleRun` COM1.1c2da order/period/promo workerlari uchun umumiy,
durable checkpoint model: immutable `public_id`, `kind=order_expiry|
expired_finalize|period_lifecycle|promo_cleanup`, fixed DB `as_of`, target
modelining fixed max-PK `snapshot_high_watermark`, nullable `last_pk`,
`pending|running|completed|failed` status, lease owner/token/expiry, positive CAS
`version`, attempt, nullable `retry_at` va selected/processed/skipped/failed counts, started/heartbeat/
finished timestamps, unique operation receipt va safe error code. Selector faqat
`pk > last_pk AND pk <= snapshot_high_watermark ORDER BY pk`; har batchdan keyin
cursor+counts CAS, expired lease old token/version bilan reclaim, stale finalize 0.
Retryable failure runni `running`da retry-at bilan qoldiradi; terminal schema/
policy mismatch `failed`; cursor rewind va completed run reopen yo‘q. Shu modelni
COM1.5a workerlari reuse qiladi, stdout/heartbeat-only progress emas.
DB shape: `pending`da lease/start/heartbeat/finish/retry null; `running`da
lease owner/token/expiry va started/heartbeat required, finished null; retry_at
faqat running retry waitida; `completed|failed`da lease/retry null va finished
required, failedda safe error code required, completedda null.

`CommerceRetentionPolicyVersion` COM1.8a1da aniq migration bilan yaratiladi:
`public_id`, positive integer `revision` (DB unique; PostgreSQL
`commerce_retention_policy_revision_seq.nextval`, gap ruxsat, `MAX+1`/client
revision yo‘q; SQLite serialized test adapter),
`state=draft|published|retired`, exact nullable-draft fields
`original_evidence_days`, `derivative_evidence_days`, `financial_record_days`,
`audit_event_days` (har biri publishda integer `1..36500`) va
`staging_object_days` (`1..30`), `legal_hold_mode=block_destructive`,
`effective_from`, nullable
`effective_until`, actor/reason/published-at audit. DB check
`effective_until IS NULL OR effective_from < effective_until`; PostgreSQL
exclusion constraint published intervallarning `[effective_from,
effective_until)` oralig‘ida overlapini taqiqlaydi. Published row immutable;
birorta duration null/rangedan tashqari bo‘lsa publish deny. Run cutoffs aynan
`as_of - timedelta(days=<field>)`; evidence original/derivative va staging object
shu nomdagi cutoffga, financial ledger/decision va audit/event export-report
minimumlari mos financial/audit cutoffga maplanadi. COMMERCE-01 financial/auditni
hard-delete qilmaydi.

Har retention revisionida positive lifecycle `version` bor. Draft field edit,
publish va `published→retired` commandlari rowni lock qilib expected versionni
talab qiladi va +1 yozadi; stale edit/publish/retire write 0. Running
`CommerceRetentionRun.policy_version` esa selected immutable published revisionga
`PROTECT` reference bo‘lib, lifecycle CAS tokeni yoki “latest” selector emas.

`select_retention_policy(as_of)` aynan `state=published AND effective_from <=
as_of AND (effective_until IS NULL OR as_of < effective_until)` predikatini
ishlatadi va **exactly one** row talab qiladi. 0 yoki >1 natija
`RETENTION_POLICY_UNAVAILABLE`, purge/export/anonymization/key-retirement
mutationlari fail-closed va critical health finding; “latest revision” fallback
yo‘q.

Legal hold authoritative schema ham COM1.8a1da yaratiladi, “if admitted” degan
yashirin tashqi tizim emas. `CommerceLegalHold`: `public_id`,
`scope=user|order|evidence`, aynan bittasi non-null bo‘lgan `user/order/evidence`
`PROTECT`, bounded reason code, optional case-reference HMAC+key version,
`starts_at` (server transaction time), nullable `released_at`, positive CAS
`version`, create/release actor va one-to-one operation receiptlari. DB
scope/FK XOR checki, `released_at >= starts_at`, create/release receipt unique va
har scope subject uchun `released_at IS NULL` partial unique bitta active holdni
beradi. Future scheduling va row delete yo‘q. User hold uning barcha order,
evidence va identity anonymizationini; order hold order+evidence+financial
lineageni; evidence hold faqat shu revisionning destructive actionini to‘sadi.
Bu ordinary retention/shredga tegishli. Confirmed
`SENSITIVE_AUTH_DATA_INCIDENT`dagi taqiqlangan authentication binarysi legal
holdga qaramay hard deadline’da crypto-erased bo‘ladi; hold metadata-only
incident/event/tombstone, decision va ledger lineageni saqlaydi, PAN/CVV binaryni
saqlashga ruxsat bermaydi. Emergency event `legal_hold_bypassed_for_sad` reasonini
va active hold public IDlarini PII-free auditga yozadi.

`place_legal_hold` va `release_legal_hold` target User→Course, so‘ng optional
case-reference bo‘lsa `CommerceKeyPurpose(slug=legal_hold_reference_hmac)`, keyin
CheckoutOrder→PaymentEvidence→CommerceLegalHold tartibida stable subjectni lock
qiladi; barcha bir turdagi row PK ascending. Owner/legal capability, fresh reauth,
expected version/idempotency/reason majburiy. Retention/shred ham
shu subject lockidan keyin `active_legal_holds(user, order, evidence,
as_of=transaction_timestamp)`ni qayta o‘qiydi. Shuning uchun create-hold-vs-purge
race’da lockni birinchi olgan transition yutadi; hold purge commitidan keyin
retroaktiv emas. Release eski skipped claimni qayta ochmaydi, yangi run kerak.

Mid-run policy almashishi targetni o‘zgartirmasligi uchun COM1.8a1 shu migrationda
yana ikki model yaratadi. `CommerceRetentionRun`: `public_id`, selected
`policy_version PROTECT`, DB transactiondan olingan fixed `as_of`, original/
derivative/staging/financial/audit uchun hisoblangan non-null cutoff timestamplari,
`mode=dry_run|destructive`, `status=pending|running|completed|failed`, actor,
operation receipt, cursor, claimed/done/skipped/failed counts, lease token/
expiry, version, started/finished-at va safe error code; receipt unique, cutofflar
run yaralgach immutable. `CommerceRetentionClaim`: run, allowlisted
`category`, `subject_kind`, `subject_public_id`, `token_kind=cas_version|
immutable_fingerprint`, nullable claimed `expected_version`, nullable
`expected_fingerprint_hmac/fingerprint_key_version`,
`action=purge|crypto_shred|anonymize`,
`status=pending|leased|done|skipped_hold|failed_retryable|failed_terminal`,
positive CAS `version`, lease token/expiry, attempt/retry-at, safe result code,
crypto-shred action uchun immutable unique `erase_request_id` va
`progress_step=not_started|key_destroyed|wrapper_cleared|objects_pending|
verified_done`, step timestamps; DB `UNIQUE(run, category, subject_kind,
subject_public_id)` va token-kind/nullability XOR. Claim rowlar immutable identity/actionga ega, faqat CAS
status/lease/progress maydonlari o‘zgaradi.

Allowlist/token map normativ va cross-product emas:
`PaymentEvidence/evidence_original/crypto_shred` →
`cas_version=PaymentEvidence.original_crypto_version` va
`PaymentEvidence/evidence_derivative/crypto_shred` →
`cas_version=PaymentEvidence.preview_crypto_version`; staged objectning durable rowi
`staging_object/purge` → immutable object fingerprint;
`PaymentDestinationVersion/destination_secret/crypto_shred` →
`cas_version=crypto_version`; `User/account_identity/anonymize` → user
row lock ostida allowlisted mutable identity fieldlarining retention-purpose
HMAC fingerprinti. Financial ledger/decision/audit rowlari COMMERCE-01da
hard-delete claim olmaydi; policy cutoffi export/retention reportida saqlanadi,
account identitysi yuqoridagi user claim orqali anonymize qilinadi. Mapdan tashqari
subject/action publish yoki workerda fail-closed; universal “version bor” taxmini
yo‘q. `erase_request_id` va `progress_step` faqat `crypto_shred`da required;
`purge|anonymize`da ikkalasi null. Crypto-shred terminal success faqat
`verified_done`; purge terminal success object verified-missing, anonymize terminal
success identity-field fingerprintining expected post-transform qiymati bilan
`status=done`da saqlanadi.

Run yaratish transactioni selectorni fixed `as_of` bilan chaqiradi, policy FK va
barcha category cutofflarini bir marta persist qiladi, so‘ng claimlarni faqat shu
snapshotdan quradi. Worker faqat persisted claimni consume qiladi; yangi policy
yoki wall-clock siljishi run targetini kengaytirmaydi. Dry-run ham ayni
run/claim contractini yozadi, lekin destructive operation chaqirmaydi va keyin
destructivega toggle qilinmaydi. Destructive run har claim CASidan so‘ng object
version hamda **joriy** legal holdni yana tekshiradi: yangi hold eski snapshotdan
ustun va claim `skipped_hold`; holdni olib tashlash esa eski runni avtomatik
qayta ochmaydi, yangi run kerak. COM-D1 hal bo‘lmaguncha **ordinary** destructive
worker OFF. Sensitive-auth-data emergency erasure workeri alohida, COM1.2c bilan
majburiy ON/health-critical va bu setting yoki COM-D1 bilan pause qilinmaydi.

Claim leasing `CommerceOperationReceipt`ning §6.11 token/version fence’ini aynan
mirror qiladi: due pending/retryable row leased; expired lease old token/version
CAS bilan reclaim; har step/finalize faqat current token/version, stale worker 0
row va side-effectni advance qilmaydi. Crypto-shredda worker stable subjectni
lock qilib current legal hold/tokenni `not_started→key_destroyed` irreversible
boundarydan darhol oldin tekshiradi. Hold yutsa `skipped_hold`; key destroy yutsa
providerga immutable `erase_request_id` bilan idempotent destroy, keyin wrapper
clear, object deletes va verified-missing checkpointlari faqat oldinga yuradi.
Crashdan keyin provider `already_destroyed` safe success; progress/timestamp
nollanmaydi. Key yo‘qolgach yangi legal hold metadata/tombstoneni ushlab qoladi,
ammo binary cleanupni orqaga qaytarmaydi. Retryable backoff
`min(30s * 2^(attempt-1), 1h)` + claim-IDdan deterministic 0–10% jitter; max 12
attemptdan keyin claim `failed_terminal`. Schema/authorization mismatch darhol
terminal va health finding. Kamida bitta failed-terminal claim bo‘lsa run `failed`;
barcha claim `done|skipped_hold` va retryable/live lease 0 bo‘lsa `completed`;
aks holda terminal emas. Run countlari har claim finalize bilan CAS recompute
qilinadi, `finished_at` faqat completed/failedda, failed run safe error code bilan;
completed/failed run reopen qilinmaydi.

`CommerceReconciliationRun/Finding`:

- Run: immutable `public_id`, `scope=full|money|access|privacy|writer`, fixed DB
  `as_of`, har scanned model uchun `{model:max_pk}` immutable
  `snapshot_high_watermarks` canonical JSON, `cursor_model` va `cursor_pk`,
  `pending|running|completed|failed` status, lease owner/token/expiry, positive CAS
  version/attempt, selected/scanned/opened/refreshed/resolved/error counts,
  started/heartbeat/finished timestamps, unique operation receipt va safe error
  code. Model order allowlisted; har modelda `pk > cursor AND pk <= max_pk ORDER BY
  pk`, expired lease old token/version CAS bilan reclaim, stale finalize 0;
- finding code, stable `subject_kind+subject_digest`, PII-free
  `subject_descriptor_json`, severity,
  detected/resolved timestamps, first/last seen run, occurrence count, positive
  CAS `version` va nullable resolving operation receipt;
- DB partial `UNIQUE(finding_code, subject_kind, subject_digest) WHERE
  resolved_at IS NULL`; rerun ayni open rowni lock qilib `last_seen_run`, count va
  versionni oshiradi, duplicate open finding yaratmaydi. Old finding resolved
  bo‘lgach ayni anomaly qaytsa yangi row ochiladi va old lineage saqlanadi;
- `resolve_funding_deficit`, post-lapse full refund va boshqa repair exact finding
  ID+expected versionni global lock tartibida olib, domain projection bilan ayni
  transactionda `resolved_at/resolving_receipt/version+1` yozadi. 0/>1 active
  match yoki stale version mutationni fail-closed qiladi;
- default read-only; repair alohida owner-confirmed command va audit;
- task broad exceptionni yutmaydi; partial/failure explicit.

Finding subject encoding normativ: descriptor sorted-key canonical JSON, integer
PKlar decimal va UUIDlar lowercase, float/PII/free-text 0;
`subject_digest=SHA-256("azurelms-commerce-finding-subject-v1\0" || descriptor)`.
Matrixdagi composite subjectlar exact keylar bilan yoziladi: order+currency,
transaction+observation_namespace, order+fulfillment_kind, key_purpose_slug+
key_version, period_pk+capability, grant_pk, writer_route_pk va batch_run_public_id.
Single subject public ID bo‘lsa descriptorga o‘sha ID, public ID yo‘q internal
projectionda immutable DB PK yoziladi. Code har bir descriptor schema versionini
test fixture bilan freeze qiladi; key missing/extra bo‘lsa findingning o‘zi
yozilmay `RECONCILIATION_SUBJECT_INVALID` bilan run failed. `reconcile_commerce
--scope <...> [--resume-run <public_id>]` faqat shu persisted runni yuritadi;
stdout cursor yoki wall-clock selector source of truth emas.

### 6.12 Delete va PII policy

- Offer/order/payment/decision/period/grant FKlari `PROTECT` yoki anonymization
  workflow; CASCADE bilan finance lineage yo‘qolmaydi.
- Account deletion identity PII’sini policy bo‘yicha anonymize qiladi, ammo
  ledger summasi/reference hash/audit minimumini owner/legal retention qaroriga
  ko‘ra saqlaydi.
- Evidence binary uchun retention muddati `COM-D1` owner qarori; muddatsiz
  saqlash default emas.
- `SENSITIVE_AUTH_DATA_INCIDENT` binary purge’i ordinary retention yoki legal
  convenience defaultidan mustaqil; minimal tombstone/audit binary o‘rnini bosadi.
- Log/telemetryga evidence, filename, raw instructions, account number, full
  reference, promo code secret, email yoki reason free-text chiqmaydi.

---

## 7. State machine, command va xato contracti

### 7.1 Order state machine

```text
awaiting_payment
  ├─→ evidence_submitted → under_review
  │                         ├─→ approved
  │                         ├─→ needs_info → evidence_submitted
  │                         ├─→ rejected
  │                         └─→ manual_resolution
  ├─→ cancelled
  └─→ expired              # late-evidence window davomida reopenable, active-intent blocker

expired ──late-payment proof──→ manual_resolution
expired ──late window elapsed, payment/evidence 0──→ lapsed
manual_resolution ──owner resolution──→ approved | needs_info | rejected | cancelled
manual_resolution ──confirmed cash, settlement blocked──→ manual_resolution
                                                       # unallocated inflow, access yo‘q
lapsed ──kech aniqlangan tashqi cash──→ lapsed          # refund-only ledger, reopen/access yo‘q
```

`approval_proposed` PaymentDecision/attestation eventidir, order state emas:
four-eyes birinchi bosqichidan keyin order `under_review`da qoladi.

Quote order emas: `quote_checkout` write-free signed preview qaytaradi;
`create_order` durable `awaiting_payment` rowini yaratadi. `approved`,
`rejected`, `cancelled`, `lapsed` terminal. `expired` va `manual_resolution`
terminal emas,
ammo oddiy reviewer uni resolve qila olmaydi. Terminal `rejected` resubmit
qilinmaydi; learner ruxsat bo‘lsa `previous_order`ga linked yangi order ochadi.
Tuzatiladigan dalil `needs_info` ishlatadi. Evidence kelgan order expiry jobi
bilan delete/expire qilinmaydi. `expired → manual_resolution` faqat payment
expiry’dan oldin yuborilganiga dalil bor privileged command bilan. Transitionlar
allowlist; arbitrary status set yo‘q.

Nonzero late windowda `expired` partial active-intent unique ichida qoladi, shu
sabab yangi order yaratilmaydi. `finalize_expired_orders` window o‘tgach va
payment/evidence 0ni locked holda qayta tekshirib `lapsed` qiladi; window 0 bo‘lsa
`expire_orders` to‘g‘ridan-to‘g‘ri `lapsed` va
`expired_at=closed_at=fixed DB as_of` yozadi. `record_late_payment_evidence` ham
User→Course→Order lockini oladi. Create-vs-late-proof va create-vs-lapse race’ni
PostgreSQL unique+lock tartibi deterministik yopadi; ikki active intent yo‘q.

Late window tugagach eski order reopen qilinmaydi. Learner to‘lovni muddatida
yuborganini keyinroq ko‘rsatsa yoki bank fact kech kelib tushsa, owner avval
`submit_compensation_evidence` orqali lapsed orderga current reviewable
`compensation_proof` yaratadi, keyin `record_post_lapse_external_inflow` ishlatadi.
Command User→Course→barcha shu user-course active orderlari→lapsed Order→Evidence→
money locklarini oladi, required immutable bank reference va eski orderning
observation namespace’i bilan retained-key dedupni bajaradi. Ayni transactionda
`PaymentResolution(kind=post_lapse_inflow,outcome=hold)`, `unallocated_inflow`,
critical owner finding va outbox yoziladi; old order `lapsed`, yangi active order
va uning promo/accessi o‘zgarmaydi. Bu source allocation/settlementga yaroqsiz;
faqat to‘liq source-bound refund bilan yopiladi. Har distinct bank reference
alohida source/finding bo‘lishi mumkin; mavjud money faqat oldingi
`post_lapse_inflow` unallocated source’lari va ularning refund lineage’i bo‘lsa
yangi distinct fact rad etilmaydi. Har source mustaqil to‘liq refund qilinadi.
`compensate_payment(refund)` matching open findingni majburiy lock qiladi va full
refund transactioni bilan ayni transactionda resolved qiladi; partial refund yoki
finding’siz close deny. Destination secret allaqachon
crypto-shred bo‘lgan bo‘lsa ham namespace/HMAC lineage saqlanadi va decrypt talab
qilinmaydi. Reference/proof yo‘q yoki dedup noaniq bo‘lsa money row 0 va finding;
cross-order ko‘chirish yoki retroaktiv access uchun yangi ADR/manifest kerak.

“Promo-free preview/token” bu hujjatda **raw-code-free** degani. `quote_checkout`
POSTidagi raw promo code faqat process xotirasida normalize qilinib per-purpose
HMAC lookup bilan exact immutable `PromoRuleVersion`ga topiladi; raw qiymat
log, operation fingerprint, session, token yoki responsega kirmaydi. Imzolangan
quote tokenining versionlangan claimlari aynan: quote nonce, actor yoki anonymous
session bindingi, `order_kind`, course/offer-version/course-offer public IDlari,
positive `course_offer_version`,
destination-version/
pricing-policy-version public IDlari, optional non-secret
`subscription_public_id` (initialda null, renewal/upgrade/downgradeda required),
renewal/upgrade/downgradeda required `source_period_public_id`, source period version,
source offer-version public ID, source/target tier rank va `source_boundary_at`,
optional non-secret `promo_rule_version_public_id`, base/discount/due minor-unit qiymatlari,
optional `previous_rejected_order_public_id` va uning expected versioni,
currency, term snapshot, `writer_control_version`, `writer_epoch`, positive
`quote_signing_key_version`, issued-at va
expires-at. Effective audience predicate yoki PilotMember PII/token ichida yo‘q.
Secret yoki PII claim yo‘q.
Token formati `HS256` emas, application-level `HMAC-SHA-256`:
`HMAC(key, "azurelms-commerce-quote-v1\0" || canonical_json_utf8)`; canonical JSON
UTF-8, sorted ASCII keys, duplicate key 0, integerlar decimal, float 0 va Unicode
NFC stringlar bilan aynan bitta serializationga ega. Key faqat
`CommerceKeyPurpose(slug=quote_signing_hmac)` registrysidagi token version orqali
providerdan olinadi; yangi token current key bilan, verify esa aynan claimed
current/retained key bilan constant-time qilinadi. Unknown/retired key, boshqa
domain separator, non-canonical bytes yoki signature mismatch write 0.
`create_order` token signature/expiry/bindingni tekshiradi, aynan ko‘rsatilgan
CommerceWriterControlni shared lock qilib token version/epochga byte-equal va
effective admission hali true ekanini tekshiradi, so‘ng aynan ko‘rsatilgan
Course→CourseOffer→OfferVersion va destination mutexlarini lock qiladi, keyin
CourseOffer `sale_state=open`, window, `allowed_order_kinds` va token’dagi expected
versionni,
OfferVersion `published`+effective intervalini, destination decrypt readinessni,
subscription user/course/kind lineageni; plan-change’da source periodning
state/version/offer/rank/boundary snapshotini, non-revoked scheduled successor 0ni
hamda promo rule-version
`status=published`+effective interval/eligibility/
usage limitini transaction ichida qayta hisoblaydi. Quote’dan keyingi pause,
close, retire yoki key-shred bo‘lsa `OFFER_NOT_AVAILABLE`/`DESTINATION_NOT_READY`,
row 0. Barcha money/term/destination natijalari token
bilan byte-for-byte teng bo‘lsagina reservation+orderni atomik yaratadi. Order
uchun `promo_code_hmac` rule versionning server-side maydonidan olinadi. Guest
register return-intent bindingi COM1.0cdagi server-side one-time handoff bilan
authenticated actor bindingiga almashtiriladi; client claimni o‘zi ko‘chira
olmaydi. Shu tariqa `create_order`ga raw kodni ikkinchi marta yuborish talab
qilinmaydi, ammo server recalc ham yo‘qolmaydi.

Rejected retry alohida taxminiy selector emas: learner `retry_rejected_order`
entrypointidan predecessor public IDni `quote_checkout`ga uzatadi. Quote/create
predecessorni lock qilib ayni actor/course, terminal `rejected`, successor 0 va
requested kindning predecessor kindiga tengligini tekshiradi; ID+version token
claimiga kiradi. `create_order` ayni lock ostida DB `UNIQUE(previous_order)` bilan
link yozadi. Parallel retrylardan biri order yaratadi, ikkinchisi o‘sha successor
IDni idempotent readback qiladi (boshqa request fingerprint bo‘lsa conflict);
“eng so‘nggi rejected” yoki URLdan olinmagan predecessor inference yo‘q.

Order-kind matrix ham selector/command/test uchun yagona:

| Kind | Required lineage | Quote/create admission | Settlement natijasi |
|---|---|---|---|
| `initial` | subscription null, previous paid/current Subscription 0 | CourseOffer allowed; initial-eligible promo only | yangi lifetime Subscription + first non-overlap period |
| `renewal` | ayni actor/course existing Subscription va frozen paid-source period required | latest effective end − frozen policy `renewal_open_before_end_days`dan boshlab; source stable Plan+tier rank target bilan aynan teng; barcha period terminal bo‘lsa darhol; CourseOffer renewalni allow qiladi | ayni Subscriptionga §6.8 continuity anchorli next period, parallel subscription 0 |
| `upgrade` | ayni actor/course existing Subscription required | target OfferVersion `tier_rank` strictly higher, frozen `prepaid_only+next_paid_boundary`; credit/receivable yo‘q | settlementdan keyingina next paid boundaryda new capability |
| `downgrade` | ayni actor/course existing Subscription required | target `tier_rank` strictly lower va frozen `next_paid_boundary`; proration yo‘q | current paid benefitni erta kamaytirmay next paid boundary projection |

Unknown yoki `manual_adjustment` kind 422/write 0. `CourseOffer.allowed_order_kinds`,
subscription user/course, target rank va policy token/create paytida aynan bir xil
locked selector bilan tekshiriladi; adapter kindni infer qilmaydi.

Plan-change settlement ham source snapshotni taxmin qilmaydi: control→User→Plan/
Course/Offers→Subscription→source Period→Order tartibida lock qilib source period
version/state/offer/rank/boundary order snapshotiga hanuz tengligini tekshiradi.
Renewal, compensation shorten/revoke yoki lifecycle transition versionni
o‘zgartirgan bo‘lsa fulfillment 0; cash hali tasdiqlanmagan bo‘lsa `ORDER_STALE`,
tasdiqlangan bo‘lsa manual resolution/unallocated yo‘l. Target period
`starts_at=max(settlement_db_as_of, source_boundary_at)`, old grace endpointi
kerak bo‘lsa §6.8 deferred graph rewrite bilan shu boundarygacha qisqaradi.
Target future bo‘lsa scheduled va settlement old benefitni erta oshirmaydi;
source period/offer/rank/boundary order yaralgach rewrite qilinmaydi.

### 7.2 Payment va period state

```text
Payment ledger: settlement → [refund | reversal | adjustment]
                unallocated_inflow → allocation → refund
                       └───────────→ [refund | reversal | adjustment]

SubscriptionPeriod:
scheduled → active → grace → expired
    └──────────────→ revoked          # pre-start compensation
                 └────────→ revoked   # active/grace explicit policy/decision
```

Fulfilled `settlement|allocation` refundi accessni avtomatik revoke qiladimi,
period oxirigacha qoladimi yoki partial proration qilinadimi — `COM-D4`.
Qarorgacha shu **fulfilled** refund commandi accessni jim o‘zgartirmaydi,
resolution/compensating transaction yozmaydi va `POLICY_NOT_ADMITTED`
qaytaradi; ownerga PII-minimal reconciliation finding ochilishi mumkin. Qaror
admitted bo‘lgach yangi immutable refund resolution, outflow va explicit access
natijasi approved order terminal state’ini qayta ochmasdan atomik yoziladi.
Ammo `unallocated_inflow`ning full positive `free_unallocated` returni — order hali
unfulfilled bo‘lsin yoki approved orderning excess qismi bo‘lsin — COM-D4 emas,
majburiy base safety path: owner fresh reauth, partial 0 va access mutation 0.
Unfulfilled orderda refunddan keyin barcha unallocated balans 0 bo‘lsa cancelled
decision atomik; fulfilled/excess refundda disposition none va access o‘zgarmaydi.
Bu yo‘lni unresolved proration qarori pulni ushlab qolish uchun bloklamaydi.

Bank isboti bilan kelgan reversal yoki required cash correction platform
tanlaydigan refunddan farq qiladi: money-truth rowi COM-D4/D5 yo‘qligi sabab
rad etilmaydi. Funding/access policy tayyor bo‘lmasa ayni transaction
`retain_with_debt`, critical finding va owner outbox yozadi; access jim revoke
qilinmaydi. Keyingi `resolve_funding_deficit` faqat append-only entitlement
decision/projection bilan yakunlaydi, bank ledgerini qayta yozmaydi.

### 7.3 Canonical commandlar

Create-or-update CASlarda `expected_version=ABSENT` alohida typed sentinel (JSONda
string literal) bo‘lib “row yo‘q bo‘lishi shart” degani; null/omitted qabul
qilinmaydi. Existing row uchun positive version required. Parent User/subject
lockidan keyin absent/existing qayta o‘qiladi; mismatch `ORDER_STALE` 409 va current
safe readback, write 0. `set_writer_pilot_member` first create va
`place_legal_hold` first create aynan shu contractda; release/disable existing
positive version bilan.

| Command | Asosiy input | Fresh check | Natija |
|---|---|---|---|
| `quote_checkout` | actor/session, `order_kind`, course, offer, nullable subscription, transient raw promo, nullable explicit rejected predecessor ID | sale/allowed-kind eligibility; initialda subscription null va existing lineage 0 (valid rejected predecessor retry bundan mustasno), renewal/change’da same-user/course subscription required; predecessor terminal/version/successor 0; destination va HMAC promo lookup | PII/raw-code-free signed version-ID preview, predecessor ID/version freeze; business DB write yo‘q, create’da server recalc |
| `quote_renewal` | actor, subscription, offer, transient raw promo | `quote_checkout(order_kind=renewal)`ning barcha checklari; current lineage va renewal eligibility | renewal kind+subscription IDli ayni signed quote contracti; yashirin inference yo‘q |
| `create_order` | signed quote token, idempotency | signature/expiry/actor binding; locked token-policy issued-at contract, CourseOffer open/window/allowed-kind/version, OfferVersion published/effective, destination readiness, subscription lineage, promo limit va ayni frozen policy bilan byte-equal server recalc | promo reservation + durable awaiting-payment order atomik |
| `submit_evidence` | open order, expected order/current-evidence versions, payment-submission upload, idempotency | owner/access/state/upload | `purpose=payment_submission` revision + evidence_submitted |
| `submit_compensation_evidence` | terminal yoki manual-resolution order, upload, idempotency, reason | owner finance capability+fresh reauth; order scope; same private validation/scan/size policy | current `purpose=compensation_proof` revision; payment-submission currenti va order state o‘zgarmaydi |
| `flag_sensitive_auth_data` | any current/superseded non-purged evidence revision, expected version, idempotency, typed reason | scoped finance capability + revision belongs to scoped order; already erased idempotent | shu revision atomik `restricted_sensitive` + versioned incident + bounded `auto_erase_at` + alert; current bo‘lsagina order action |
| `purge_sensitive_auth_data` | incident, expected version, idempotency, typed reason | human: owner/security + fresh reauth; system: overdue emergency lease | external record-key destroy + wrapper clear + active object delete; order `needs_info` yoki money suspected bo‘lsa `manual_resolution` |
| `start_review` | order, expected order/evidence versions, idempotency | finance scope + current reviewable derivative | under_review/receipt |
| `request_information` | order, expected order/evidence versions, idempotency, reason | scope/current evidence | needs_info + outbox |
| `reject_payment` | order, expected order/evidence versions, idempotency, reason | scope/current evidence | rejected + promo reservation rejected + outbox; no delete |
| `propose_payment_approval` | `settle_payment` bilan ayni full input: order/evidence/expected version/amount/currency/optional typed proposed-resolution payload+cohort+ordered unallocated source allocationlar, optional occurred-at/raw reference, idempotency | COM-D9 threshold active, fresh reviewer, latest evidence/all settle prechecks | safe settlement-input fingerprint + first attestation + `approval_proposed`; PaymentResolution/money/access write 0 |
| `record_unallocated_inflow` | manual-resolution order, evidence, expected version, actual positive amount/currency, occurred-at source, optional raw reference, idempotency, reason | owner capability+fresh reauth; current clean evidence; cross-family observation-namespace lock va barcha retained keys bo‘yicha duplicate 0; settlement prerequisite haqiqatan blocked | reference+observation HMAC + `PaymentResolution(kind=unallocated_inflow,outcome=hold)` + inflow transaction; order manual-resolution, access 0, outbox |
| `record_post_lapse_external_inflow` | lapsed order, current compensation-proof revision, required transient raw immutable bank reference, positive amount/currency, optional exact bank occurred-at, expected order/evidence versions, idempotency, reason | owner capability+fresh reauth; current proof reviewable/clean; User/Course/CheckoutOrderlar PK tartibida locked; old observation namespace va retained-key dedup; fulfillment/allocation/period/grant 0; old money faqat distinct post-lapse-unallocated va ularning refund lineage’i | `PaymentResolution(kind=post_lapse_inflow,outcome=hold)` + unallocated inflow + source-linked critical finding/outbox; old order lapsed va current active order untouched; har source refund-only |
| `settle_payment` | order/evidence, expected order/evidence/source versions, idempotency, actual amount/currency, optional occurred-at/raw reference/typed resolution payload va ordered `(unallocated_source_id, allocation_amount)` | permission, latest reviewable derivative/validation/scan policy, exact/mismatch policy, original+resolved cohort seat, term, promo reservation; source’lar same order/currency, locked cash backing yetarli va total exact due; high-value bo‘lsa current first attestation va boshqa actor | optional resolution first, so‘ng direct settlement yoki neutral allocation+source rows; optional second attestation + period+grant+delivery link+membership+outbox atomik |
| `compensate_payment` | source, kind, direction, positive amount/currency, expected source/order versions, idempotency, reason; post-lapse refundda required `finding_public_id+expected_finding_version`, boshqa kindda finding input null; refundda proof/reference null; reversal/adjustmentda current compensation-proof revision + required transient raw bank reference + optional exact bank occurred-at | owner capability+fresh reauth, proof reviewable/clean policy, same order/currency, observation dedup va locked cash/designation/refund-split bound. Unallocated source full free-balance returni base safety; post-lapse source’da exact matching open finding/version va full balance required; fulfilled platform refundda exactly-one policy rule, user-supplied disposition yo‘q. Verified external fact har holda ledgerga; rule yo‘q funding deficitda retain-with-debt+finding | resolution + matching transaction + allocation refund split/CashDeficit event kerak bo‘lsa + policy-derived access/order disposition yoki durable debt finding + outbox atomik; post-lapse full refundda exact source finding CAS bilan ayni transactionda resolved, order lapsed qoladi |
| `resolve_funding_deficit` | compensate resolution, `finding_public_id`, `expected_finding_version`, expected grant/period versions, idempotency, reason | owner capability+fresh reauth; source resolution retain-with-debt; exact finding/open deficit fresh; current published policyda exactly-one remediation-allowed rule | rule FKsi frozen source-linked `EntitlementOverrideDecision`(lar) + grant/period projection + finding CAS-resolved + outbox atomik; money ledger immutable |
| `resolve_cash_deficit` | deficit, expected version, `write_off|reverse_write_off`, positive amount, idempotency, reason | owner finance capability+fresh reauth; write-off ≤ outstanding receivable, reversal ≤ recognized loss; cash ledger/current deficit exact reconciliation PASS | append-only CashDeficitEvent + loss/state/version projection + outbox; PaymentTransaction yozilmaydi |
| `change_plan` | subscription, target offer, signed `upgrade|downgrade` quote with source period/version/offer/ranks/boundary, idempotency | frozen `prepaid_only+next_paid_boundary`, actor/subscription lineage, exactly-one active|grace paid source, strict rank direction va locked quote recalc; credit/receivable yo‘q | immutable source snapshotli unpaid plan-change order; settlement source versionni yana tekshiradi, capability/quota target period active bo‘lgandagina |
| `cancel_order` | order, expected version, idempotency, reason | actor/state; confirmed payment/evidence yo‘q | cancelled + promo reservation `released` + outbox |
| `expire_orders` | `CommerceLifecycleRun(kind=order_expiry)` public ID, lease token/version | run running/current lease; persisted fixed as-of/cursor; payment deadline, no evidence/payment, conditional version | late window >0 bo‘lsa active-blocking expired; 0 bo‘lsa lapsed va `expired_at=closed_at=as_of`; promo reservation expired + outbox; run cursor/count CAS ayni transactionda |
| `finalize_expired_orders` | `CommerceLifecycleRun(kind=expired_finalize)` public ID, lease token/version | run running/current lease; persisted fixed as-of/cursor; expired, late-evidence deadline elapsed, payment/evidence 0, conditional version | lapsed + closed_at + outbox; yangi intent shundan keyin mumkin; run cursor/count CAS ayni transactionda |
| `record_late_payment_evidence` | expired order, payment-submission upload, expected order/current-evidence versions, idempotency, reason | owner scope+fresh reauth; now ≤ late-evidence deadline; proof payment before expiry; user-course active-intent lock | new payment-submission revision + manual_resolution; expired_at saqlanadi, promo expired qoladi, privileged resolutiongina reacquire qiladi |
| `resolve_manual_resolution` | order, expected order/evidence/source versions, typed resolution input, idempotency, reason | owner capability + relevant D-gate; settle delegates all settle checks; promo limit reacquire if expired; reject/cancel faqat confirmed cash ledgerga olinmaganida | resolution + approved/needs_info/rejected/cancelled; confirmed cash uchun settle, record-unallocated yoki source-bound compensate commandiga explicit delegation |
| `advance_period_lifecycle` | `CommerceLifecycleRun(kind=period_lifecycle)` public ID, lease token/version | run running/current lease; persisted fixed `as_of`/cursor; locked subscription/period expected version; avval non-revoked `effective_access_until≤as_of→expired`; aks holda scheduled+starts_at≤as_of→active; active+ends_at≤as_of va effective end>ends_at→grace; grace+effective end≤as_of→expired; revoked always skip | har due period aynan bitta version+1 transition + per-capability grant/subscription projection/outbox; run cursor/count CAS ayni transactionda, stale worker whole rollback; shorten-vs-activation/expiry CAS atomik, not-due write 0 |
| `place_legal_hold` / `release_legal_hold` | scoped subject, create’da `ABSENT`, release’da expected positive hold version, idempotency, reason/case reference | owner/legal capability+fresh reauth; stable subject lock va active-hold uniqueness | versioned hold/release audit; destructive claim yaratilmaydi/qayta ochilmaydi |
| `rotate_commerce_key` / `retire_commerce_key_version` | purpose, expected purpose version, target version, idempotency, reason | owner/security fresh reauth; purpose-specific retained-key candidate rehearsal, historical-row/open-round/pending-claim/live-wrapper blockers va reconciliation | prepared→current/retained yoki retained→retired CAS audit; non-recomputable history eski keyda qoladi, material external providerda |
| `configure_writer_salt` | expected control version, opaque external salt ID, idempotency, reason | owner rollout capability+fresh reauth; locked control mode off/internal, route/run count 0, provider readback | control salt ID/version+1 audit; material DB/logda yo‘q, first routedan keyin immutable |
| `set_writer_pilot_member` | user, enabled, expiry, first create’da member `ABSENT`, aks holda positive member version, expected control version, idempotency, reason | owner rollout capability+fresh reauth; locked control→User→member; mode allowlist admissionda fresh active predicate | member CAS/audit; mavjud route flip 0 |
| `migrate_writer_routes` | expected control version/epoch, target percent/mode, snapshot cursor/batch, mode, applyda required source dry-run ID, operation key | locked DB control; eligible legacy route selector; User/Course/Route/Order lock; pending intent 0, expected route version, reconciliation green; apply items/digest dry-run bilan exact | durable Run/Itemli resumable reason-coded one-way legacy→canonical CAS; stage threshold request-time reroute’siz kengayadi |
| `resume_writer_epoch` | expected control version/current epoch, from epoch, snapshot cursor/batch, mode, applyda required source dry-run ID, operation key | locked DB control; canonical va legacy backend health green; pending intent 0; expected route version/finding 0; apply items/digest dry-run bilan exact | durable Run/Item, backendni o‘zgartirmay route epoch/version CAS; skip/audit/resume safe |
| `advance_writer_stage` | expected control version, target mode/percent/resolution mode, completed apply-run IDs, idempotency, reason | owner rollout capability+fresh reauth; locked control, gates green, run evidence valid, global eligible legacy route recheck 0; normal resolution faqat allowlist/canary/on va finance gates green | DB control mode/percent/resolution/version+1 + audit; fallback o‘zgarmaydi; env ceilingdan permissive bo‘lsa effective state baribir ceilingda |
| `abort_writer_rollout` | expected control version, idempotency, reason | owner/automated emergency capability; locked current control | mode off, fallback deny, resolution owner-only, epoch+1, version+1 atomik; stale process va brand-new no-route write fenced |
| `resume_writer_rollout` | expected control version, target mode/percent/resolution, completed resume-epoch apply-run IDs, idempotency, reason | owner rollout capability+fresh reauth; locked abort-state control, all routes current epoch, pending stale order HOLD/0, both backend health+salt readback+critical finding/global route checks green | fallback deny→legacy, target controls/version+1 atomik; epoch same; new-intent un-fence faqat shu commandda |
| `retry_dead_outbox` | dead event, expected event version, idempotency, reason | owner operations capability+fresh reauth; terminal error class endi retryable, recipient/payload policy hali valid; per-event rate/CAS, numeric hard cap yo‘q | ayni immutable event `pending`, new lease cycle/version va lifetime manual count+audit; yangi event/payload yo‘q |
| `reconcile_commerce` | mode/cursor | owner/system | findings only by default |

Target codenamelar `commerce.flag_sensitive_payment_evidence` va
`commerce.purge_sensitive_payment_evidence`. Birinchisi assigned finance
reviewerga scoped bo‘lishi mumkin; ikkinchisining human UI’i auto-grantsiz
owner/security-only, overdue worker esa alohida non-human service capability.
Ikkalasi `CommerceOperationReceipt` lease/fingerprint, expected evidence/incident
version va rate/anomaly alertdan foydalanadi. Flag darhol normal view/reviewni
yopadi, ammo false-positive deadline’gacha irreversible erase qilmaydi. Deadline
yarimida va o‘zida critical escalation; deadline’da dedicated emergency worker
owner tasdig‘isiz CAS/idempotent purge’ni boshlaydi. Worker failure `failed_retryable`ni
safe code bilan yozadi, healthni qizil qiladi va bounded backoff bilan uzluksiz
retry/escalate qiladi; owner inactivity, COM-D1, legal convenience yoki
`commerce_retention_purge_v1=OFF` uni to‘xtatmaydi. Owner false-positive’ni faqat
§6.5dagi `flagged`+unleased CAS guardi bilan qaytara oladi.
Confirmed/auto purge’dan keyin restore yo‘q va learnerga bank detailini
takrorlamaydigan replacement-evidence template’i chiqadi.

`start_review`dan tashqari barcha human financial decision/override commandlari
bounded nonblank reasonni **service boundaryda** talab qiladi; form validation
yolg‘iz himoya emas.

### 7.4 Stable public error taxonomy

| Code | HTTP/adapter behavior | Learner/reviewer action |
|---|---|---|
| `ORDER_NOT_FOUND` | 404 without existence leak | account history/support |
| `ORDER_STALE` | 409 + fresh projection | refresh, values preserved |
| `ORDER_EXPIRED_AFTER_PAYMENT` | 409/manual resolution | evidence yuborish/support |
| `OPERATION_IN_PROGRESS` | 409 yoki async adapterda 202 + bounded `Retry-After`; result URL | ayni idempotency key bilan readback/poll, yangi mutation yo‘q |
| `IDEMPOTENCY_CONFLICT` | 409 | yangi intentional action key |
| `EVIDENCE_REQUIRED` | 422 | accepted file yuborish |
| `EVIDENCE_INVALID` | 422 field error | crop/format/size ko‘rsatmasi |
| `EVIDENCE_NOT_REVIEWABLE` | 409 | current validated derivative/scan natijasini kutish yoki qayta upload |
| `EVIDENCE_ORIGINAL_UNAVAILABLE` | object scope’ga ko‘ra 404/423 | original quarantine/scan holati; preview bilan ishlash |
| `SENSITIVE_DATA_RESTRICTED` | 423 + owner incident queue | oddiy review to‘xtaydi, binary ochilmaydi |
| `PAYMENT_REVIEW_FORBIDDEN` | 403/404 by surface | owner role fix |
| `PAYMENT_ALREADY_DECIDED` | 409 + current result | duplicate approve qilmaslik |
| `FOUR_EYES_INPUT_CHANGED` | 409; old attestation immutable, money/access write 0 | fresh input bilan yangi approval round |
| `OBSERVATION_CLASSIFICATION_CONFLICT` | 409 + owner finding, yangi money row 0 | mavjud observationni tekshirish, unique’ni bypass qilmaslik |
| `REJECTION_LEDGER_REQUIRED` | 409; confirmed cashni reject/cancel qilib yashirish 0 | avval unallocated inflow/settlement yoki source-bound refund |
| `LAPSED_ORDER_REFUND_ONLY` | 409; old order/access/current intent o‘zgarmaydi | kech aniqlangan cashni faqat source-bound full refund |
| `COHORT_CAPACITY_UNAVAILABLE` | manual resolution | alternative/refund owner action |
| `OFFER_NOT_AVAILABLE` | 409 | current offer list |
| `DESTINATION_NOT_READY` | 503 factual copy | payment yubormaslik, support |
| `COMMERCE_POLICY_UNAVAILABLE` | 503 + critical health, write 0 | owner policy interval/readinessni tuzatadi |
| `RETENTION_POLICY_UNAVAILABLE` | owner adapterda 503 + critical health, claim/purge write 0 | exactly-one policy selectorni tuzatish; emergency SAD erasure bundan mustaqil |
| `SETTLEMENT_PROJECTION_NOT_READY` | 503 + operation readback, partial commit 0 | same idempotency key bilan retry; health/reconciliation |
| `WRITER_ROUTE_FENCED` | 503 + route/epoch readback, order write 0 | rollout resume/migration commandini kutish |
| `CROSS_OBJECT_INVARIANT_FAILED` | 409/owner adapterda 422, write 0 | stale yoki noto‘g‘ri course/offer/subscription bog‘lanishini tuzatish |
| `POLICY_NOT_ADMITTED` | 409/owner gate | owner decision kerak |
| `TEMPORARY_FAILURE` | 503 + readback-safe retry | same idempotency key bilan retry |

Raw exception, storage key, SQL, token yoki bank data responsega chiqmaydi.

### 7.5 Permission matrix

| Amal | Learner | Teacher | Support | Finance reviewer | Owner |
|---|---:|---:|---:|---:|---:|
| o‘z order/statusini ko‘rish | o‘zi | yo‘q | scoped summary | scoped | ha |
| sanitized derivative preview | o‘z current preview optional/HOLD | yo‘q | yo‘q | scoped | ha |
| original evidence download | yo‘q | yo‘q | yo‘q | default yo‘q | owner-only + reason/audit + clean scan |
| evidence yuborish | o‘z open orderi | yo‘q | secure handoff | optional scoped | ha |
| sensitive evidence flag | yo‘q | yo‘q | yo‘q | assigned scope + named capability | ha |
| sensitive evidence purge/false-positive close | yo‘q | yo‘q | yo‘q | yo‘q | owner/security named capability + fresh reauth |
| request info/reject | yo‘q | yo‘q | yo‘q | scoped capability | ha |
| settle | yo‘q | yo‘q | yo‘q | scoped capability | ha |
| offline evidence override | yo‘q | yo‘q | yo‘q | yo‘q | yo‘q — replacement evidence required |
| refund/reversal | yo‘q | yo‘q | yo‘q | policyga qarab HOLD | explicit capability |
| cash deficit write-off/reversal | yo‘q | yo‘q | yo‘q | yo‘q | explicit finance capability + fresh reauth |
| legal hold place/release | yo‘q | yo‘q | yo‘q | yo‘q | explicit legal capability + fresh reauth |
| offer/destination publish | yo‘q | yo‘q | yo‘q | yo‘q | explicit capability |
| internal health/reconciliation | yo‘q | yo‘q | yo‘q | scoped operational summary | ha |

Boshlang‘ich COM1.0a contracti **owner/superuser-only global review**: oddiy
staff va faqat codename’ga ega non-owner ham qaror/faylga kira olmaydi.
COM-D14 hal qilinib explicit assignment modeli kelmaguncha “course-scoped
finance reviewer” taxmin qilinmaydi. Stable Django codenamelar mavjud
`PaymentReceipt` modeliga bog‘lanadi: `cohorts.review_payment` va
`cohorts.view_payment_evidence`; joriy original file ham faqat ownerga va shu
gate orqali beriladi. COM1.1b target splitda
`commerce.view_payment_evidence_preview` va
`commerce.download_payment_evidence_original` yaratiladi; ikkinchisi auto-grant
qilinmaydi, owner-only default va reason/audit talab qiladi. Eski codenamelar jim
rename qilinmaydi; policy API ichida compatibility mapping qoladi. `is_staff`
capability emas. Superuser break-glass ham reason/audit bilan; bot
Telegram IDni user account+fresh rolega resolve qiladi va ayni policy ishlatadi.

Target assignment schema COM1.4ada `CommerceFinanceAssignment` bilan keladi:
`public_id`, reviewer user, nullable course (`null` = global faqat owner explicit
grant qilsa), non-null `active_from/active_until` (`active_until > active_from`),
granted/revoked by/at, reason code va
version. DB predicate `now()` ishlatmaydi: course-scoped rowlar uchun partial
`UNIQUE(reviewer, course) WHERE revoked_at IS NULL`, global rowlar uchun alohida
`UNIQUE(reviewer) WHERE course IS NULL AND revoked_at IS NULL`. “Fresh active”
service checki `revoked_at IS NULL AND active_from <= now < active_until`.
Expiry worker open muddati o‘tgan rowni system reason `expired` bilan CAS-revoke
qiladi; yangi grant commandi ham ayni global lock tartibida stale open rowni avval
expire qilib, keyin insert qiladi. Shunday qilib immutable bo‘lmagan `now()`
partial-index predicate’i yo‘q, ammo bir scope’da ikkita open assignment ham yo‘q.
Assignmentni faqat owner create/revoke qiladi. Authorization branchi exact:

```text
base = named_capability AND fresh_role AND object_policy
owner_mode = assignment schema hali yo‘q OR commerce_finance_assignment_v1=OFF
allow = base AND (
    (owner_mode AND actor.is_owner_or_superuser)
    OR
    (NOT owner_mode AND fresh_active_assignment_matches_order_course)
)
```

Shu sabab COM1.2c pre-schema va flag OFF davrida assignment talab qilinmaydi,
lekin faqat owner/superuser o‘tadi; oddiy staffga codename yolg‘iz yetmaydi. Flag
ON bo‘lsa owner ham normal queue commandi uchun assignment oladi. Favqulodda
owner/superuser break-glass bu formuladan alohida named capability, fresh reauth,
nonblank reason, qisqa expiry, alert va audit bilan; silent bypass emas. Original
download assignment ON bo‘lsa ham owner-only qo‘shimcha gate’ini saqlaydi.
COM-D14 hal bo‘lmaguncha assignment UI/activation flag OFF va owner-only policy
qoladi; COM1.4a unit schema, owner grant/revoke UI, audit va revoked-role race
testini o‘z ichiga oladi — yashirin “keyingi slice” yo‘q.

---

## 8. UX contractlari

### 8.1 Pricing va course offer

- Page course context bo‘lmasa “qaysi kurs?”ni avval so‘raydi; global plan
  narxini har course uchun sotuvga ochiq deb ko‘rsatmaydi.
- Har card: nom, aniq summa+currency, aniq term (“30 kun”, “oy” emas agar
  calendar month bo‘lmasa), core bir xilligi, haqiqiy service difference,
  cohort availability va `Tanlash`.
- “Tavsiya etiladi” sababi va marketing claim factual.
- CTA login/register orqali tanlovni server-side session/short-lived store’da
  saqlaydi; URL faqat random, one-time `commerce_return_id` oladi. Token PII,
  promo code yoki narxni o‘zida saqlamaydi, referrer/log/historyga tijoriy data
  chiqarmaydi; consume’da session/user binding va internal `next` allowlist.
- Unavailable/paused offer CTA o‘rniga sabab va support/notify action.
- No-JS barcha tanlash/login qaytish uchun ishlaydi.

### 8.2 Checkout

Sahifa tartibi:

1. **Nima olyapsiz:** course, cohort policy, offer, term.
2. **Hisob:** base, promo discount, total, currency. Promo xatosi field yonida.
3. **Qayerga to‘laysiz:** public/list previewda masked; authenticated `no-store`
   order viewda exact recipient faqat `awaiting_payment` state’da ko‘rinadi.
   Evidence yuborilgach, manual-resolution va terminal state’larda masked. Copy
   aynan ko‘rinadigan qiymatni oladi, learner oxirgi raqamlarni vizual tekshira
   oladi; plain text no-JS fallback mavjud.
4. **Muhim reference:** order number va transfer izohi.
5. **Dalil xavfsizligi:** faqat kerakli qismini crop qiling; to‘liq karta/PAN,
   CVV, PIN, balans yoki boshqa tranzaksiyalarni yubormang.
6. **Review:** financial commitdan oldin barcha qiymatni qayta ko‘rish.
7. **Submit:** ikki marta bosish duplicate emas; status message `role=status`.

Destination yo‘q yoki placeholder bo‘lsa “to‘lov yuboring” degan ko‘rsatma
chiqmaydi. Upload errorida browser tanlagan file qayta prefill qilinmaydi, ammo
order saqlanadi va foydalanuvchi faqat faylni qayta tanlaydi.

### 8.3 Order status va timeline

Har holat uchun:

- bitta aniq title;
- 1–2 jumla fakt;
- “Sizdan kutiladi” yoki “Bizdan kutiladi”;
- keyingi action;
- order reference va yangilangan vaqt;
- promised review SLA faqat owner setting bo‘lsa;
- support deep link order ref bilan, evidence/bank detail bilan emas.

Status label va access label alohida:

- `To‘lov tasdiqlandi` — settlement;
- `Access 20-noyabr 18:00gacha faol` — entitlement;
- `Guruh joyi hal qilinmoqda` — delivery resolution.

### 8.4 Subscription center

`/account/subscription/` quyidagi bloklarni beradi:

- active course/plan/term va effective access;
- renewal deadline/next action;
- pending order yoki plan change;
- payment timeline (amount/currency/date/status/reference);
- needs-info/rejected/manual-resolution action;
- admitted bo‘lsa change/cancel/refund request;
- support.

Raw model status yoki Boolean ko‘rsatilmaydi; `CommerceReadModel` quyidagini
qaytaradi: `display_state`, `headline`, `detail`, `next_action`, `deadline`,
`access_state`, `allowed_actions`, `support_context`.

### 8.5 Owner review workbench

- pagination/cursor, oldest-first, status/course/cohort/age/reviewer filter;
- count va SLA-risk badge; PII-minimal search;
- keyboard navigation va focus qaytishi;
- decision detailda order snapshot vs current catalog alohida;
- image zoom/rotate client-side, ammo public blob URL yo‘q;
- approve/reject/request-info bitta tugma emas: review summary → reason → confirm;
- stale versionda values saqlanadi, current result ko‘rsatiladi;
- bulk approve yo‘q; bulk low-risk metadata action alohida admission;
- every decision audit timeline’da.

### 8.6 Catalog/destination studio

- draft → validate → preview → publish;
- published revision inplace edit yo‘q; “yangi revision yaratish”;
- course offer matrix va availability;
- destination readiness checklist, masked preview, confirm;
- promo boundaries va reservation health;
- diff/history/retire; rollback yangi revision orqali;
- dangerous publish reauth/fresh confirm (`COM-D9` step-up policy).

### 8.7 Telegram

- Bot order yaratganda stable `order_public_id` FSMda saqlanadi.
- COMMERCE-01da bot receipt/photo/document binaryni **qabul qilmaydi va
  yuklab olmaydi**. U stable orderga user/session-bound, one-time, short-lived
  authenticated web upload link beradi; link consume bo‘lganda server order va
  actorni qayta tekshiradi. Telegram faqat handoff origin/status metadata oladi.
- Staff botga receipt binary/thumbnail yuborilmaydi. Faqat PII-minimal order
  metadata va authenticated web workbench deep link; one-tap approve/reject
  olib tashlanadi.
- Future Telegram inbound binary alohida privacy/PCI threat model, retention/
  deletion guarantee va owner-approved ADRsiz qayta yoqilmaydi; COM1.7a bunga
  admission emas.
- Telegram callback replay idempotent va fresh permission checked.
- Notification “tasdiqlandi”ni outbox settlement eventidan keyin yuboradi;
  adapter DB statusni o‘zicha talqin qilmaydi.
- Telegram ishlamasa web order/status to‘liq ishlaydi.

---

## 9. Security, privacy, accessibility va operations

### 9.1 Upload va private media

- canonical evidence service barcha adapter uchun yagona gate;
- content sniffing decoded image bilan, pixel/dimension/decompression budget;
- original filename storage key yoki response headerga ishonchsiz qo‘yilmaydi;
- authenticated, object-scoped private stream; `Cache-Control: private,
  no-store`, `X-Content-Type-Options: nosniff`, safe content disposition;
- binary/thumbnail CDN/public bucketda emas;
- sanitized derivative preview va original-download capabilitylari alohida;
  preview olgan user pixelsni saqlashi mumkinligi security boundaryda hisobga
  olinadi; authorized view/download audit body-free;
- original endpoint `scan_state=clean` va `original_state=available` bo‘lmasa
  404/typed deny; `not_configured/pending/failed` originalni ochmaydi;
- target original download GET emas: owner-only `POST` + CSRF + fresh reauth +
  bodydagi allowlisted reason code + expected evidence versiondan keyin ayni
  response private attachment stream qiladi. Reason URL/query/referrer/logga
  tushmaydi; download audit body/binarysiz yoziladi. Derivative preview GET
  read-only qoladi. COM1.0a compatibility file owner-only; COM1.1b shu target
  endpointga o‘tkazadi;
- duplicate hash cross-user existence leak bermaydi;
- staging/orphan/purge reconciliation.

### 9.2 Payment data va PCI ehtiyoti

- AzureLMS learnerning **sender** PAN/card number, CVV/CVC, PIN yoki online
  banking credentialini structured fieldda so‘ramaydi. Recipient destination
  PAN bo‘lsa bu gap uni scope’dan chiqarmaydi; COM-D15 compliance admissioni
  bo‘lmasa `card_transfer` publish fail-closed.
- UI receiptni crop/redact qilishni tushuntiradi.
- Reviewer dalilda PAN/CVV/PIN yoki taqiqlangan sensitive-authentication data
  ko‘rsa `SENSITIVE_AUTH_DATA_INCIDENT` oddiy retention/COM-D1dan mustaqil darhol
  **containment** qiladi: evidence `restricted_sensitive`, review/settlement/
  preview/download yopiladi, owner/security alert oladi va default 15, hard max
  60 daqiqalik `auto_erase_at` boshlanadi. Owner/security deadline’dan oldin
  fresh reauth bilan false-positive yoki manual purge qiladi; javob bo‘lmasa
  emergency worker avtomatik purge qiladi. Erasure external record-key handleni
  backupdan mustaqil registry’da destroy, keyin active stage/original/derivative
  objectlarni verified delete qiladi. Incidentdan oldingi backup ham unwrap
  qilmaydi; restore tombstone active blobni qayta delete qiladi. Confirmed/auto
  erase tugagach recoverable binary/derivative nusxa 0, faqat minimal metadata,
  decision va incident audit qoladi. OCRga tayanilmaydi: manual detection
  majburiy path,
  optional detector faqat qo‘shimcha signal.
- Reviewer note/message service’i full account/reference’ni reject qiladi; outbox
  template code+safe params, log esa typed code saqlaydi.
- Destination va evidence AEAD encryption, record-erasure key,
  key ID/rotation/rewrap/retirement/key-loss/crypto-shred runbookiga ega;
  encryption compliance yoki scope’dan chiqish da’vosi emas.
- Owner/legal `COM-D1` bilan evidence retention, data-subject export/delete va
  accounting minimumini belgilaydi; bu qaror prohibited data purge’ini
  kechiktira olmaydi.

### 9.3 Authorization va audit

- default-deny, named capability, object scope, fresh role check;
- list/detail/file/decision bir xil policy; “list yopiq, direct URL ochiq” yo‘q;
- bot/web/admin bypass yo‘q;
- audit: actor, capability, aggregate/version, action, reason code, outcome,
  request correlation, time; secret/binary/raw payload yo‘q;
- break-glass reason+expiry+notification; silent superuser path yo‘q.

### 9.4 CSRF, replay va rate limit

- browser mutationlar POST+CSRF; GET write-free;
- idempotency key CSRF o‘rnini bosmaydi;
- evidence upload per-user/order/IP coarse rate limit; accessibilityni
  bloklamaydigan recovery;
- reviewer decision per-actor limit va anomaly alert;
- stale expected version fail, current state readback;
- future webhook raw-body signature, timestamp/replay window va inbox dedup.

### 9.5 Accessibility

- semantic headings/landmarks/form labels; field error input bilan bog‘langan;
- financial commit oldidan review/correct/confirm;
- error sabab va yechim, rang bilan yolg‘iz emas;
- asynchronous status `role=status`/`aria-live=polite`, focusni tortmaydi;
- no-JS quote/order/evidence/status/review core;
- keyboard-only, visible focus, 44px preferred targets;
- 320 CSS px va 400% text/reflow, Windows High Contrast;
- native NVDA + desktop keyboard; Android TalkBack va iOS VoiceOver owner
  sign-off final gate.

### 9.6 Performance budgets

Initial targets baseline olingach ratify qilinadi:

- pricing/checkout/status server p95 ≤500 ms local/staging DB profile;
- review list ≤50 row per page, bounded eager loading, query budget test;
- evidence max bytes/dimensions settingda; upload stream disk/object storagega,
  memoryga to‘liq emas;
- order/status no-store private; pricing cache offer publish bilan invalidate;
- outbox backlog age va lifecycle run duration bounded.

### 9.7 Telemetry va alertlar

Metrics (low-cardinality):

- order created/evidence submitted/settled/rejected/needs-info by kind;
- state age histograms, review SLA breach count;
- idempotent replay/conflict, stale decision, duplicate evidence hash;
- settlement→grant latency, settlement-without-grant count;
- grant-without-source, overlapping period, payment sum mismatch;
- capacity manual-resolution count;
- outbox pending/dead/oldest age;
- lifecycle/reconciliation last success and findings;
- upload reject by safe reason class;
- checkout conversion denominator definitions versionlangan.

Critical alerts:

1. settlement bor, grant yo‘q;
2. source’siz active grant;
3. same order duplicate settlement;
4. outbox/lifecycle last success thresholddan eski;
5. destination missing/invalid while sale open;
6. reconciliation severity critical;
7. ordinary staff forbidden decision/file attempts spike.
8. sensitive evidence incident confirm/purge SLOdan oshdi yoki erase failed.

### 9.8 Reconciliation

Read-only command finding kodi, subject turi/public IDsi va severity’sini quyidagi
normativ matritsadan oladi; “mismatch” degan generic finding yo‘q:

| Finding code | Exact predicate | Subject / severity |
|---|---|---|
| `COM_ORDER_SNAPSHOT_INVALID` | amount identity, currency, policy/offer/destination/course/cohort/kind lineage yoki state timestamp contractidan bittasi false | order / critical |
| `COM_EVIDENCE_BLOB_INVALID` | row↔blob/derivative/original/scan, current-per-purpose, restricted tombstone, staged orphan yoki SAD deadline invariantidan bittasi false | evidence yoki incident / security-critical |
| `COM_RESOLUTION_CARDINALITY_INVALID` | §6.6b kind/outcome uchun required decision/transaction 1 emas, forbidden dependent >0 yoki disposition map noto‘g‘ri | resolution / critical |
| `COM_EXTERNAL_OBSERVATION_INVALID` | transaction namespace order destination namespace’iga teng emas, retained-key recompute topmaydi, bir role/fingerprint >1 yoki bir observation boshqa kindda qayta klassifikatsiya qilingan | transaction+namespace / critical |
| `COM_POST_LAPSE_INFLOW_UNRESOLVED` | `post_lapse_inflow` source cash neti >0 bo‘lib exact source-linked open finding yo‘q; yoki full source-bound refunddan keyin cash net 0 bo‘lsa ham finding open; resolved findingda cash net ≠0/required refund-resolution edge yo‘q | post-lapse unallocated transaction / critical |
| `COM_ALLOCATION_BACKING_INVALID` | allocation line sum ≠ allocation amount/order due, wrong kind/order/currency source, designated > source cash net yoki post-lapse source allocationda ishlatilgan | allocation / critical |
| `COM_REFUND_SOURCE_SPLIT_INVALID` | allocation-backed refund line sum ≠ refund, wrong cash source, cumulative line bound oshgan yoki deterministic largest-remainder recompute farq qiladi | refund / critical |
| `COM_FUNDING_DEFICIT_DRIFT` | fulfillment source’lari bo‘yicha `Σ max(0,funding_required-funding_backing)` order projection/findingga teng emas | order+fulfillment / critical |
| `COM_CASH_DEFICIT_DRIFT` | `current_deficit_minor != max(0,-cash_net)` yoki Event delta replay projection/loss/state bilan teng emas | order+currency / critical |
| `COM_OVERRIDE_SOURCE_INVALID` | funding override source resolution/finding/rule FKsi, remediation eligibility, event/funding/action yoki applied disposition bir-biriga mos emas | override / critical |
| `COM_PERIOD_GRANT_LINK_INVALID` | settlement/allocation↔period↔grant↔delivery edge cardinalitysi, half-open interval/effective end, source/overlap, compensation boundary yoki Subscription precedence/status/closed_at/version projectionidan biri false | subscription/period/grant / critical |
| `COM_COHORT_CAPACITY_INVALID` | active delivery membership capacitydan oshgan yoki resolution cohort linki course/offerga mos emas | cohort / critical |
| `COM_PROMO_RESERVATION_DRIFT` | reservation state order state’iga mos emas, hold/TTL/consumption limit noto‘g‘ri yoki late-flow expired reservation noqonuniy qayta ochilgan | reservation / critical |
| `COM_OUTBOX_FENCE_INVALID` | required domain event yo‘q, `(event,recipient)` duplicate, sent/dead lease fence noto‘g‘ri yoki stale token finalize qilgan | event/outbox / critical |
| `COM_KEY_REGISTRY_INVALID` | purpose slug allowlistdan tashqari, parent `current_version` exactly-one current childga mos emas, required external key resolve/readback yo‘q yoki retire blockeri bor version retired | key purpose+version / security-critical |
| `COM_WRITER_ROUTE_INVALID` | route-required lineage (`CheckoutOrder` yoki unresolved legacy pending intent yoxud route-bootstrap high-watermarkdan keyingi writer journal) mavjud scope’da route cardinalitysi ≠1; route-required lineage yo‘q scope’da 0 ruxsat. Shuningdek bucket/control-salt mismatch, backend/epoch fence buzilishi, completed BatchRun/Item digest/count/CAS farqi yoki rollout gate’dan keyin reason-code’siz eligible legacy route qolishi | writer route yoki batch run / critical |
| `COM_LEGACY_SHADOW_DIFF` | versioned transform bo‘yicha current legacy va canonical projection farqi yoki journal high-watermark gap | source record / warning; access/money farqi critical |

Repair default emas. Har repair code, affected IDs, dry-run, owner confirm,
operation receipt va post-repair reconciliation talab qiladi.

---

## 10. Migration va rollout strategiyasi

### 10.1 Expand → journal/shadow → backfill/catch-up → cutover → contract

1. **Expand:** yangi table/link/index; legacy writer xulqi hali o‘zgarmaydi.
2. **Audit:** current data anomaly report; hech narsa avtomatik tuzatilmaydi.
3. **Legacy mutation journal + shadow write:** barcha inventar qilingan create,
   approve, promo va access mutation `LegacyMutationJournal`ga legacy write
   bilan ayni transactionda, keyin canonical schema/eventga yoziladi. Reject
   COM1.0adan beri bloklangan. Global lock order PostgreSQL’da isbotlanmaguncha
   shadow yoqilmaydi. Canonical failure legacy success sifatida yashirilmaydi.
4. **Snapshot/high-watermark:** source PK + updated marker/event sequence qayd.
5. **Backfill:** shu high-watermarkgacha resumable, deterministic batch;
   transform version/fingerprint saqlanadi.
6. **Catch-up:** backfill davomida kelgan journal drain qilinadi, changed-source
   rows fingerprint bilan qayta ishlanadi; ikki ketma-ket zero-diff pass.
7. **Shadow read:** ikkala projection solishtiriladi, userga legacy ko‘rinadi;
   diff metric/log IDs-only.
8. **Internal writer rehearsal:** epoch/fence eski binary yoki queue’ning
   canonical rowdan keyin legacy write qilishini to‘sadi. COM1.2d2 faqat
   owner/internal synthetic web adapter; learner writer flag OFF. Telegram
   binary doim OFF. Minimal outbox ham shu bosqichda isbotlanadi.
9. **Reader cutover:** cohort/entitlement/history canonical read-modelga.
10. **Legacy read-only:** admin/model writer yopiladi; compatibility projection.
11. **Contract:** drop faqat kamida bir release observation, zero diff va
    alohida backup/restore evidence’dan keyin; COMMERCE-01 ichida shart emas.

Learner-facing writer cutover faqat COM1.8cda: COM1.4b2 compensating ledger,
COM1.5d1 access outcome, barcha P0 gate va final rollback rehearsal yopilgach.
COM1.2d2dagi “web adapter” production learner rollout degani emas.

### 10.2 Legacy receipt backfill

| Legacy holat | Canonical mapping |
|---|---|
| verified + image + barcha strict snapshot | approved order; evidence original/derivative state’i validation/scan daliliga mos, settlement/period/grant faqat explicit snapshotdan |
| verified, ammo offer/destination/currency/amount/perioddan biri yo‘q | `LegacyCommerceRecord`; mavjud evidence linki, `legacy_evidence_unavailable` kerak bo‘lsa; canonical settlement/grant to‘qilmaydi |
| unverified + image + strict snapshot | `evidence_submitted`/ready review order |
| unverified yoki difference, strict field yetishmaydi | `LegacyCommerceRecord`; owner finding, current narx/destination bilan to‘ldirilmaydi |
| deleted rejected receipt | audit yetarli bo‘lsa `LegacyCommerceRecord` tombstone; user/amount/reason taxmin qilinmaydi |

Backfill verified receipt amountini current plan price bilan almashtirmaydi;
receipt snapshot bo‘lmasa `unknown`, “hozirgi narx” emas. Period inference faqat
explicit `period_start/end`; yo‘q bo‘lsa `LegacyCommerceRecord` finding.

### 10.3 Feature flaglar

Default OFF presentation/read/adaptor cutover flaglari (writer bundan mustasno,
quyidagi enum mode bilan boshqariladi):

- `commerce_order_reader_v1`;
- `commerce_checkout_renderer_v2`;
- `commerce_subscription_center_v1`;
- `commerce_review_workbench_v1`;
- `commerce_finance_assignment_v1` — OFF bo‘lsa owner-only policy, assignment
  row mavjudligi huquq bermaydi;
- `commerce_health_console_v1`;
- `commerce_catalog_studio_v1`;
- `commerce_telegram_adapter_v1` — metadata/status/web handoff only; binary
  qabul qilish bu flag bilan ham mavjud emas.

Writer uchun `commerce_order_writer_v1` nomli ikkinchi Boolean/registry flag
**mavjud emas**. Yagona authoritative mutable control COM1.1a3dagi DB singleton
`CommerceWriterControl`. Deploy settings faqat undan qat’iyroq fail-safe ceiling:
`COMMERCE_WRITER_MODE_CEILING=off|internal|allowlist|canary|on` (default `off`),
`COMMERCE_CANARY_PERCENT_CEILING=0..100` (default `0`), va
`COMMERCE_CANONICAL_RESOLUTION_MODE_CEILING=owner_only|normal` (default
`owner_only`). Audience mode’lar total-order deb taxmin qilinmaydi. DB predicate
va ceiling predicate har biri alohida hisoblanadi (`off=false`, `internal=active
PilotMember(audience=synthetic)`, `allowlist=active
PilotMember(audience=real_pilot)`, `canary=bucket < o‘z percenti`,
`on=true`) va `effective_admission = DB_predicate AND ceiling_predicate`.
Ikkalasi canary bo‘lsa bu amalda bucket < `min(DB_percent, ceiling_percent)`;
mode’lar turlicha bo‘lsa ularning haqiqiy set intersectioni, enum `min()` emas.
Effective resolution faqat ikkala tomon `normal` bo‘lsa normal, aks holda
owner-only. Setting writer epoch yoki salt ID manbasi emas. Mode/percent/epochni faqat
expected-version owner command DBda o‘zgartiradi, shuning uchun eski process ham
har create’da locked current rowni ko‘rib fail-closed qiladi. COM1.1a3dagi
`CommerceWriterRoute(user, course, backend, bucket, writer_epoch, version, assigned_at)`
DB `UNIQUE(user, course)` bilan sticky source beradi. Bucket
`HMAC(canary_salt, user_public_id || course_public_id) mod 100`; salt rollout
davomida almashtirilmaydi va loglanmaydi. Existing legacy pending intent auditda
`legacy` route oladi; first canonical create route va orderni ayni transactionda
yozadi. Reader har orderni persisted backend/ID bilan ochadi, current foiz bilan
qayta route qilmaydi. Route avtomatik canonical↔legacy flip qilinmaydi.

Canonical admission selector exact: `off` predicate false; `internal`
faqat unexpired active `CommerceWriterPilotMember(audience=synthetic)`;
`allowlist` faqat unexpired active member `audience=real_pilot`; `canary` eligible real userning persisted bucketi
percentdan kichik bo‘lsa; `on` barcha boshqa sale-eligible actor. Har mode’da
mavjud route sticky; stale `writer_epoch` yangi create’da
`WRITER_ROUTE_FENCED`, legacy fallback emas.

Foiz oshishi mavjud legacy routeni request vaqtida qayta bucketlab jim flip
qilmaydi. Har `1→5→25→50→100` advance’da owner avval resumable
`migrate_writer_routes(target_percent, cursor, batch_size, dry_run, operation_key)`
batchini yuritadi. Har batch current `CommerceWriterControl`ni avval lock qilib
run expected control version/epochini tekshiradi. Selector snapshot
high-watermarkgacha faqat `backend=legacy`,
`bucket < target_percent` (final `on`da **barcha** legacy route, joriy offer/sale
eligibilitydan qat’i nazar), current epoch va critical finding 0 routelarni stable
`Route.pk` tartibida, persisted max-PK high-watermark/cursor chegarasida
oladi. Har row User→Course→Route va tegishli orderlarni global tartibda lock
qilib, pending/open intent 0 hamda expected route versionni qayta tekshiradi;
eligible row ayni `migrate_writer_route(..., target_backend=canonical)` CASiga
delegatsiya qilinadi, boshqasi reason-coded skip. Cursor/run/attempt counts,
before/after version va operation receipt saqlanadi; retry idempotent. Dry-run
eligible count apply bilan byte-equal, faqat undan keyin stage admission foizi
oshadi. Threshold stage tugagan deyilishi uchun high-watermark ichidagi eligible
legacy route 0; pending sabab skip qilingan row intent yopilgach keyingi run’da
migratsiya qilinadi. Paused/closed course route’lari ham final batchdan tashqarida
qolmaydi va keyingi eligible intentda legacyga “uyg‘onmaydi”. `100%/on` existing
population uchun ham barcha safe legacy route 0 completion gate’iga ega; pending
intentli skiplar yopilmaguncha stage HOLD. Rollback canonical routeni legacyga
qaytarmaydi.

COM1.8c activation tartibi manual va monotonic: `off → internal` (owner/synthetic)
→ named real-user allowlist → canary `1 → 5 → 25 → 50 → 100` → `on`. Har stage
kamida 24 soat turadi; auto-advance yo‘q. Advance oldidan critical finding,
wrong-route, duplicate/partial write va authorization leak **0**; kamida 20
attempt bo‘lgan 15 daqiqalik windowda command error rate ≤2%; outbox oldest age
≤5 daqiqa; §11 COM1.8b performance thresholds PASS. Kam hajm bu mezonlarni
“green” qilmaydi — owner evidence packda HOLD yoki explicit insufficient-volume
waiverni qayd etadi, ammo zero-tolerance invariantga waiver yo‘q.

Stage advance oddiy setting edit emas: `advance_writer_stage(expected_control_version,
target_mode, target_percent, target_resolution_mode, completed_batch_run_ids,
idempotency, reason)` control
rowini lock qiladi, referenced apply runlar completed/dry-equal ekanini va
**butun joriy DBda** target thresholdga tushadigan safe `backend=legacy` route 0
ekanini yana tekshiradi, so‘ng mode/percent/version+1ni atomik yozadi. First route
insert/migration ham control rowni avval lock qilgani uchun high-watermarkdan keyin
kirgan legacy route bu final recheck bilan ko‘rinadi yoki advance’dan keyingi
request yangi control bo‘yicha canonical bo‘ladi; check→advance oynasi yo‘q.
`target_resolution_mode=normal` faqat target `allowlist|canary|on`, referenced
routes current epoch, finance assignment/four-eyes/compensation/reconciliation
gatelari green va env ceiling normal bo‘lganda ruxsat; `off|internal`da owner-only.
Normal→owner-only safety tightening istalgan stage’da ruxsat, teskarisi yuqoridagi
gate bilan audited CAS.

`command error rate` bitta formula: denominator — auth, structural parse va sticky
route admissionidan o‘tgan commandlarning `succeeded` natijalari **plus** quyidagi
numerator failure’lari (idempotent replay logical attempt sifatida bir marta);
numerator — HTTP 5xx, `failed_retryable`, timeout yoki kutilmagan
`failed_terminal`. Expected validation/policy deny, stale-version/idempotency
conflict va authorization 4xx numeratorga ham denominatorga ham kirmaydi, alohida
code counterda kuzatiladi. Rolling window va dashboard ayni server-side
receipt/metricdan hisoblaydi, browser statusidan emas.

Abort trigger: zero-tolerance finding ≥1, ikki ketma-ket 5 daqiqalik windowda
performance breach, yoki yuqoridagi error/outbox threshold breach. Operator
`abort_writer_rollout(expected_control_version, idempotency, reason)` bilan
locked controlni `mode=off`, `resolution_mode=owner_only`, `writer_epoch+1`,
`fallback_backend=deny`, `version+1` qiladi; env ceilingni OFF qilish
defense-in-depth, fence manbasi emas. Yangi
canonical va legacy fallback order ikkalasi ham sticky-canonical route uchun
bloklanadi. Existing canonical orderlar canonical reader/owner resolutionda,
legacy orderlar legacy compatibility readerda qoladi; pul yuborgan pending
order boshqa backendka ko‘chmaydi. Reconciliation va support status OFF
qilinmaydi.

Resume settingni qayta yoqishning o‘zi emas. Owner avval abort epochidagi
reconciliationni green qiladi, so‘ng resumable
`resume_writer_epoch(from_epoch, to_current_epoch, cursor, dry_run=true)`ni
ishlatadi. Har **canonical va legacy** route User→Course→Route tartibida lock
qilinadi; backendiga mos writer/shadow health green, open/pending intent 0,
critical finding 0 va expected route version mos bo‘lsa backendni o‘zgartirmay
version+1/current epochga CAS; boshqasi reason-coded skip. Dry-run count bilan
apply count byte-equal bo‘lishi kerak. Pending canonical yoki legacy orderlar eski
epochda o‘z backendining owner resolution/readback yo‘li bilan tugatiladi, boshqa
backendka ko‘chmaydi; ular yopilgach keyingi resumable run route’ni ko‘taradi.
Shunday qilib abortdan oldingi legacy route abadiy fenced qolmaydi, ammo epochni
e’tiborsiz ham qoldirmaydi. Abort-vs-create va resume-vs-new-intent PostgreSQL
race testlari birorta post-fence write yoki backend flip qolmasligini isbotlaydi.

Abortdan rolloutni qayta ochadigan yagona transition
`resume_writer_rollout(expected_control_version, target_mode, target_percent,
target_resolution_mode, completed_resume_run_ids, idempotency, reason)`. U controlni
exclusive lock qilib **barcha** route current epoch, pending stale-epoch orderlar 0
yoki owner resolution queue’da explicit HOLD, canonical+legacy health va critical
finding 0, referenced resume apply/dry digests equal, salt provider readback hamda
global route recheckni talab qiladi. Success `fallback_backend=legacy` qiladi,
target mode/percentni yozadi va resolution uchun yuqoridagi stage gate’ni qo‘llab
version+1; epochni yana oshirmaydi. Oddiy `advance_writer_stage` fallback
`deny→legacy` qila olmaydi. Shu command bo‘lmasa abortdan keyin yangi intent
abadiy fenced qoladi, shuning uchun resume-vs-create race release-blocking test.

Flag ortiga qo‘yilmaydi:

- evidence’siz approvalni taqiqlash;
- finance least-privilege;
- destructive rejectni COM1.0ada bloklash va COM1.2cda immutable decisionga
  almashtirish;
- promo/amount/period invariantlari;
- upload canonical validation;
- false payment/access copy containment;
- task failure/health visibility.

### 10.4 Rollback

- Presentation flag OFF enhanced UI’ni yashirishi mumkin, canonical data
  yozishni o‘chirmaydi. Persisted canonical route/order uchun minimal status,
  owner resolution va support readback flag ortida emas; legacy UI canonical
  rowni direct mutate qilmaydi.
- Writer cutoverdan keyin pre-fence binaryga rollback yo‘q; compatibility
  writer faqat yangi schema tushunadigan release orqali.
- Migrations reverse qilib ledger row/drop qilinmaydi.
- Shadow/cutover failure’da new writer pause; existing orderlar read-only
  status va owner queue orqali hal qilinadi.
- Destination/catalog publish rollback eski rowni edit qilish emas, oldingi
  revisiondan yangi published revision.
- Outboxni o‘chirib settlement rollback qilinmaydi; dispatcher pause/retry.
- Emergency runbook exact flag, binary floor, pending queues, reconciliation,
  resume va owner communicationni ko‘rsatadi.

Named pause switchlar va talab qilinadigan rollback testlari:

| Unit/oqim | Default-OFF switch | OFF semantikasi | Majburiy test |
|---|---|---|---|
| Settlement (1.2d) | `commerce_settlement_writer_v1` | yangi settle yo‘q; existing state/owner queue readable | mid-request epoch fence → whole rollback |
| Abort resolution (1.8c) | `commerce_stale_epoch_resolution_v1` | stale-epoch orderga SAD/read-only/revoke-safe pathdan boshqa mutation yo‘q | exact allowlist deny; ONda owner fresh-reauth settlement preflight/ledger atomik |
| Lifecycle (1.5a) | `commerce_lifecycle_workers_v1` | expiry/grace worker claim olmaydi | pause/resume cursor duplicate 0 |
| Renewal (1.5b) | `commerce_renewal_writer_v1` | yangi renewal order yo‘q | pending renewal readable/resumable |
| Plan change (1.5c) | `commerce_plan_change_writer_v1` | yangi upgrade/downgrade order yo‘q | unpaid uplift 0 after pause |
| Promo (1.6c) | `commerce_promo_writer_v1` | yangi reservation yo‘q; existing release/resolve ishlaydi | pause while reserved → no leak |
| Outbox (1.7b) | `commerce_outbox_dispatch_v1` | dispatch pause, rows retained | resume/replay duplicate notification bounded |
| Delivery (1.5d) | `commerce_delivery_projection_v1` | new settlement HOLD/manual resolution, partial access yo‘q | projection unavailable → settlement rollback |
| Purge (1.8a) | `commerce_retention_purge_v1` | faqat ordinary purge claim yo‘q; SAD emergency worker flagga bog‘liq emas va qoladi | ordinary jobni irreversible boundarydan oldin pause; emergency path pause qilinmaydi |
| Analytics (1.7c) | `commerce_analytics_v1` | view hidden, ledger untouched | flag combinations source totalsni o‘zgartirmaydi |

Har tegishli manifest unit switchni settings registry, health readback va yuqoridagi
focused rollback test bilan yetkazadi; “pause” nomi yozilgan bo‘lsa aynan shu
switch nazarda tutiladi.

---

## 11. Roadmap — dependency tartibidagi 40 reviewable PR-unit

31 logical slice katta migrationlarni oldindan bo‘lish natijasida **40 alohida
PR-unit**ga ajratildi. Quyidagi execution manifest normativ: har unitning direct
dependency’si, asosiy fayllari, schema/setting ta’siri, owner gate’i va focused
test moduli bor. Agent baribir `rg` bilan barcha consumer/writerni qayta topadi,
ammo “qayerdan boshlash”ni taxmin qilmaydi. Bir unit 600+ production LOC yoki
ikki mustaqil migrationga chiqsa u yana kichrayadi; ikki unit bitta PRga
qo‘shilmaydi.

### 11.1 Execution manifest va exact DAG

`—` schema yo‘q degani; “gate yo‘q” owner qarori talab qilinmasligini anglatadi.
Test moduli unit ichida shu nom bilan yaratiladi yoki mavjud ko‘rsatilgan modul
kengaytiriladi.

| PR-unit | Direct dependency | Asosiy fayllar | Schema/setting | Owner gate va focused test |
|---|---|---|---|---|
| COM1.0a | — | `core/access.py`, `core/views.py`, private media, receipt service/forms, `cohorts/admin.py`, bot staff/middleware, dashboard/nav/workspace/receipt templates | `PaymentReceipt.Meta.permissions` migration; auto-grant yo‘q | COM-D14 default owner-only; `manage.py test core.test_receipt_decisions core.test_private_media cohorts.test_payment_plan_integrity bot.test_checkout_parity` |
| COM1.0b | COM1.0a | cohort tasks/enrollment/delivery/receipt/transition services, signals, notification service, health view | schema —; conditional update va global lock policy | gate yo‘q; `manage.py test cohorts.test_plan_effective_date cohorts.test_tier_transfer users.test_frontend_v1_records` + PostgreSQL race |
| COM1.0c | — | pricing/course/checkout legacy+V1 templates, public/user auth views, return-intent helper | server-side one-time return record session/cache; DB schema — | gate yo‘q; `manage.py test users.test_frontend_v1_records cohorts.test_frontend_v1_checkout subscriptions.tests` |
| COM1.0d1 | COM1.0a | subscriptions model/promo service/forms, upload validation, receipt service, admins | promo check migration; upload limits existing settings | gate yo‘q; `manage.py test subscriptions cohorts.test_payment_plan_integrity core.test_private_media` |
| COM1.0d2 | COM1.0a | frontend payment settings/form, backoffice payment hub, checkout/transition/membership services, bot checkout/photo routes | schema —; audited current destination readiness | COM-D2 safe prepaid block; `manage.py test cohorts.test_tier_transfer cohorts.test_checkout_shows_where_to_pay bot.test_receipt_target` |
| COM1.1a1 | COM1.0a, COM1.0d2 | new `commerce/apps.py`, enums/models/admin-readonly, settings, migrations | `CommerceOperationReceipt`; Offer/CourseOffer, Destination+Version, PaymentObservationNamespace+PaymentDestinationValueAlias, Policy(+aggregate CAS)+immutable `CommerceCompensationPolicyRule`, PromoRule+Version tables; policy DB sequence, alias unique va published interval exclusions | COM-D11 compatibility; COM-D15 card publish blocked; `manage.py test commerce.tests.test_operations commerce.tests.test_catalog_models commerce.tests.test_compensation_policy_models commerce.tests.test_destination_namespace` + PostgreSQL Plan revision allocation/policy sequence/stale-edit/overlap/same-value cross-family races |
| COM1.1a2 | COM1.1a1 | commerce catalog/policy/destination services/forms/views/urls, `commerce/crypto.py`, key-provider interface/fake, owner template, non-secret draft/key commands | `CommerceKeyPurpose/CommerceKeyVersion` migration + allowlisted purpose seed; opaque external key refs only, material/secret migration yo‘q; app boots but key health/mutations fail-closed | COM-D16 + owner confirm; production publish uchun `commerce_key_provider_ready`; `manage.py test commerce.tests.test_bootstrap commerce.tests.test_destination_crypto commerce.tests.test_key_lifecycle` + PostgreSQL rotate/retire races |
| COM1.1a3 | COM1.1a2 | commerce order/legacy/writer-control/promo reservation/writer-route/pilot-member/route-batch models, migration, factories, minimal `configure_writer_salt` owner service | strict Order (c1 source-period alterigacha initial core), LegacyRecord, PromoReservation(+version), seeded singleton `CommerceWriterControl`, CommerceWriterRoute(+version), `CommerceWriterPilotMember`, `CommerceWriterRouteBatchRun/Item`; OperationReceipt a1dan reuse | COM1.2adan oldin owner salt ID+provider readback required; `manage.py test commerce.tests.test_order_models commerce.tests.test_money commerce.tests.test_promo_models commerce.tests.test_writer_control commerce.tests.test_writer_route commerce.tests.test_writer_pilot commerce.tests.test_writer_route_batch` + PostgreSQL abort/admission race |
| COM1.1b | COM1.1a2, COM1.1a3 | commerce staged-upload/encrypted evidence/decision/approval-attestation/resolution/payment/allocation/refund-source/cash-deficit/SAD models, evidence lifecycle+per-blob crypto CAS, cash-observation fingerprint, private storage + derivative/original endpoints, migration | `CommerceStagedUpload`; Evidence(+purpose/version, independent original/derivative keys+retention metadata)/Decision/ApprovalAttestation/Resolution/Transaction/PaymentAllocationSource/PaymentRefundSource/CommerceCashDeficit/Event/Incident/Event tables; external-observation partial unique; preview/original/flag/purge permissions | COM-D1 ordinary retention nullable; COM-D9 attestation dormant; `manage.py test commerce.tests.test_payment_models commerce.tests.test_staged_uploads commerce.tests.test_payment_allocation commerce.tests.test_refund_sourcing commerce.tests.test_cash_deficit commerce.tests.test_cash_observation_dedup commerce.tests.test_evidence_permissions commerce.tests.test_sensitive_data_incident commerce.tests.test_four_eyes` + PostgreSQL lifecycle/source/dedup/key-retire races |
| COM1.1c1 | COM1.1b | commerce subscription/period/override/grant/delivery-link models, CheckoutOrder paid-source snapshot alter migration, core entitlement adapter skeleton | Subscription/Period(+version/effective-end/policy+grace snapshot sources)/EntitlementOverrideDecision(+funding actions/source resolution/applied compensation rule)/Grant(+version)/CommerceDeliveryTransitionLink; nullable initial-only vs required renewal/change Order source fields; PostgreSQL `btree_gist` exclusions | COM-D3/D4 behavior OFF; `manage.py test commerce.tests.test_subscription_models commerce.tests.test_order_source_snapshot commerce.tests.test_funding_decisions commerce.tests.test_delivery_models` + PostgreSQL period/grant overlap |
| COM1.1c2 | COM1.1a3, COM1.1c1 | commerce outbox/reconciliation/lifecycle-run/operation helpers, funding-decision finding link, migration | `CommerceEventOutbox`, `CommerceLifecycleRun`, `CommerceReconciliationRun/Finding` + lease indexes; nullable `EntitlementOverrideDecision.source_finding` FK and final source/finding checks | gate yo‘q; `manage.py test commerce.tests.test_operations commerce.tests.test_outbox_models commerce.tests.test_lifecycle_runs commerce.tests.test_reconciliation_models commerce.tests.test_funding_decisions` + PostgreSQL lease reclaim/stale-finalize |
| COM1.1d | COM1.1b, COM1.1c2 | `audit_commerce_legacy` command, classifier, fixtures, runbook | schema —, write 0 | owner anomaly review; `manage.py test commerce.tests.test_legacy_audit` |
| COM1.2a | COM1.1d, COM1.0b | legacy writer hooks, `LegacyMutationJournal`, shadow/backfill/catch-up commands, reconciliation | journal table + exact unique/index migration; no drop | owner exception map + WriterControl salt non-null/provider readback; `manage.py test commerce.tests.test_backfill commerce.tests.test_shadow_write commerce.tests.test_mutation_journal commerce.tests.test_writer_control` + PostgreSQL deadlock |
| COM1.2b | COM1.2a, COM1.1a2 | commerce quote/order services/selectors, web internal views/urls, promo reservation adapter, authoritative DB writer-control gate | schema —; DB control seeded OFF, env mode/percent/resolution ceilings default fail-closed; tests/owner synthetic uchun explicit DB `internal` CAS | published policy/offer/destination; `manage.py test commerce.tests.test_quote_order commerce.tests.test_writer_control` + stale-process abort race |
| COM1.2c | COM1.2b | evidence/decision/SAD-incident services, mandatory emergency-erasure worker+heartbeat, private media adapter, compatibility receipt view, cleanup task | schema —; storage staging config; emergency path ordinary retention switchidan mustaqil | COM-D1 ordinary purge OFF; `manage.py test commerce.tests.test_evidence_commands commerce.tests.test_decisions commerce.tests.test_sensitive_data_incident` + pre-incident backup unwrap deny |
| COM1.2d1 | COM1.2c | payment/subscription kernel, money/HMAC helper, idempotency helper | schema —; HMAC key reference; `commerce_settlement_writer_v1=OFF`, no adapter route | hard runtime-disable until d2 bundle; `manage.py test commerce.tests.test_settlement_kernel` + PostgreSQL concurrency |
| COM1.2d2 | COM1.2d1, COM1.1c2 | transaction+period+grant+delivery-link projection, outbox dispatcher, DB-control fence/epoch, internal synthetic web adapter | settlement/delivery/outbox switches OFF; DB writer control remains internal/fail-safe ceiling OFF for learners | public cutover forbidden; `manage.py test commerce.tests.test_fulfillment commerce.tests.test_cutover commerce.tests.test_writer_control` + PostgreSQL last-seat/abort fence |
| COM1.3a | COM1.2d2 | commerce selectors/read model, order/status/account views+urls+templates | reader flag default OFF; schema — | COM-D12 binary self-preview; `manage.py test commerce.tests.test_read_model commerce.tests.test_order_views` |
| COM1.3b | COM1.3a | checkout V2 templates/forms/static/controller/browser tests | `commerce_checkout_renderer_v2` default OFF; schema — | gate yo‘q; `manage.py test commerce.tests.test_checkout_views cohorts.test_checkout_mobile` + browser |
| COM1.3c | COM1.3a | subscription-center view/template/navigation/tests | page flag default OFF; schema — | admitted actions only; `manage.py test commerce.tests.test_subscription_center` |
| COM1.4a | COM1.2c, COM1.3a | review selectors/views/forms/templates/static, finance assignment owner UI, private derivative preview + POST original endpoint | `CommerceFinanceAssignment` migration; `commerce_review_workbench_v1` va `commerce_finance_assignment_v1` default OFF | COM-D14; owner-only original + reason + clean scan; `manage.py test commerce.tests.test_review_workbench commerce.tests.test_finance_assignment commerce.tests.test_evidence_permissions` |
| COM1.4b1 | COM1.4a, COM1.2d2 | resolution service/queue/forms/templates/outbox events | schema —; reason taxonomy data | COM-D6/D7/D9; `manage.py test commerce.tests.test_manual_resolution` |
| COM1.4b2 | COM1.4a, COM1.2d1 | compensation-proof upload, refund/reversal/correction, deterministic refund sourcing, funding/cash-deficit resolution services/forms/projections | schema —; 1.1b deficit/refund-source va c1/c2 funding fields reused | platform refund COM-D4/D5 + owner fresh reauth; proven reversal always recorded; `manage.py test commerce.tests.test_compensation_evidence commerce.tests.test_compensating_transactions commerce.tests.test_refund_sourcing commerce.tests.test_funding_deficit commerce.tests.test_cash_deficit` + PostgreSQL cross-kind observation race |
| COM1.4c | COM1.1c2, COM1.2d2 | health/reconciliation views/templates/commands/repair service | `commerce_health_console_v1` default OFF; schema — | repair owner-confirmed; `manage.py test commerce.tests.test_reconciliation_console` |
| COM1.5a | COM1.2d2, COM1.1a2, COM1.4b2 | policy studio, order expire/lapse, in-window late evidence va post-lapse refund-only external-inflow command, period activate/grace/expire and reservation workers using c2 durable run/lease | schema —, `CommerceLifecycleRun` c2dan reuse; lifecycle switch OFF; legacy quote setting read-only projection | COM-D3/D16; `manage.py test commerce.tests.test_policy_lifecycle commerce.tests.test_order_late_window commerce.tests.test_post_lapse_inflow commerce.tests.test_period_lifecycle commerce.tests.test_lifecycle_runs` + PostgreSQL create-vs-late/lapse/refund/stale-worker race |
| COM1.5b | COM1.5a | renewal command/calculator/promo selector/read model | schema —; renewal switch OFF | COM-D10 transfer only; commercial pause requires roadmap amendment; `manage.py test commerce.tests.test_renewal` + PostgreSQL effective-access overlap |
| COM1.5c | COM1.5b | `CheckoutOrder(kind=upgrade/downgrade)` service/read model, c1 paid-source snapshot fields, entitlement projection | schema —; plan-change switch OFF | COM-D2/D5; `manage.py test commerce.tests.test_plan_change` including scheduled-successor/renewal race and source-version drift |
| COM1.5d1 | COM1.5a, COM1.5b, COM1.4b2 | period/grant expiry/grace/revoke worker and reconciliation | schema —; lifecycle switch reused | COM-D3/D4; `manage.py test commerce.tests.test_period_lifecycle` + race |
| COM1.5d2 | COM1.5c, COM1.5d1 | delivery membership/seat/transfer/freeze adapters using existing commerce delivery link | schema —; delivery switch OFF; COM1.1c1 link reused | COM-D6/D10; `manage.py test commerce.tests.test_delivery_projection cohorts.test_tier_transfer` |
| COM1.6a1 | COM1.1a1 | offer revision/schedule/course-offer services and policy | schema — | COM-D11; `manage.py test commerce.tests.test_offer_service` |
| COM1.6a2 | COM1.6a1 | owner offer studio forms/views/templates/history/preview | studio flag default OFF; schema — | factual claims owner confirm; `manage.py test commerce.tests.test_offer_studio` |
| COM1.6b | COM1.1a2, COM1.2b | full destination studio/history, established crypto service rewrap/rotation operations | schema —; COM1.1a2 key contract reused | COM-D9/D15; `manage.py test commerce.tests.test_destination_studio commerce.tests.test_destination_crypto` |
| COM1.6c | COM1.2b, COM1.5b | existing PromoRuleVersion/PromoReservation lifecycle services, owner UI, cleanup/reconciliation | schema —; promo switch OFF; 1.1a1/a3 models reused | gate yo‘q; `manage.py test commerce.tests.test_promo_lifecycle subscriptions.tests` |
| COM1.7a | COM1.2d2, COM1.3a | bot FSM/status/routes/callbacks, stable-order authenticated web-upload handoff | `commerce_telegram_adapter_v1` default OFF; schema —; inbound binary route removed/denied | no Telegram binary; `manage.py test commerce.tests.test_telegram_adapter bot.test_checkout_parity bot.test_receipt_target` |
| COM1.7b | COM1.2d2 | fenced outbox consumers, notification/email/Telegram adapters, dead-letter UI va owner `retry_dead_outbox` | `CommerceNotificationPreference` exact migration; dispatcher switch OFF | gate yo‘q; `manage.py test commerce.tests.test_notification_outbox commerce.tests.test_outbox_leases` + crash-after-send/stale-finalize |
| COM1.7c | COM1.4b2, COM1.4c, COM1.5d1 | analytics selectors/views/templates/definitions | schema —; analytics switch OFF; materialized view out of scope | multi-currency HOLD; `manage.py test commerce.tests.test_analytics` |
| COM1.8a1 | COM1.7b, COM1.6b | retention/export/anonymization; all §6.3 key-purpose rotation/retirement; legal-hold commands; snapshot run/claim+dry-run rewrap | `CommerceRetentionPolicyVersion`(+lifecycle CAS), `CommerceLegalHold`, `CommerceRetentionRun`, fenced `CommerceRetentionClaim` exact migration; PostgreSQL policy interval/active-hold constraints | COM-D1; `manage.py test commerce.tests.test_retention_policy commerce.tests.test_retention_snapshot commerce.tests.test_legal_hold commerce.tests.test_export commerce.tests.test_key_lifecycle commerce.tests.test_destination_crypto commerce.tests.test_evidence_crypto commerce.tests.test_promo_key_rotation` + PostgreSQL policy stale-edit/hold-vs-purge/propose-vs-retire races |
| COM1.8a2 | COM1.8a1 | purge/crypto-shred/anonymization workers, backup/replica/authoritative-erasure-registry runbook | irreversible ordinary purge switch OFF; no drop migration; SAD emergency path already active | COM-D1 explicit enable; `manage.py test commerce.tests.test_purge` + restore/re-purge + pre-incident backup unwrap deny |
| COM1.8b | COM1.2d2, COM1.3b, COM1.4c, COM1.5d2, COM1.6c, COM1.7a, COM1.7b, COM1.8a2 | load/chaos fixture including generated non-PII encrypted raster + `commerce_release_rehearsal` runner, backup/restore runbook | schema — | COM-D17 thresholds; exact §11 contract + PostgreSQL/Redis/storage/key-provider suites |
| COM1.8c | COM1.8b, COM1.6a2, COM1.6b, COM1.7c, COM1.0c, COM1.0d1, COM1.3c, COM1.4b1 | sticky DB-control rollout, pilot membership, single-route+resumable threshold-batch migrate, dual-backend resume-epoch, stage-advance/abort/resume-rollout CAS commands, stale-epoch owner resolution switch, ceiling flags/runbook/support pack/final evidence | env mode/percent/resolution faqat fail-safe ceiling; Control/Pilot/Route/RouteBatchRun+Item schema already 1.1a3, yangi migration yo‘q | all release-blocking gates + owner canary sign-off; full §12 matrix, threshold final global recheck, audience-expiry/stage-change existing-order completion, stale-process abort/create va legacy+canonical abort/resume/new-intent races |

Bu jadval ASCII “ketma-ketlik” emas: har qatorning `Direct dependency` ustuni
DAG edge’larining yagona manbasi. Parallel unitlar faqat shu direct dependency
yopilganda boshlanadi. Jadvalda “kerak bo‘lsa/if absent/alohida migration” degan
yashirin ish yo‘q. Discovery yangi schema yoki alohida PR talab qilsa avval shu
manifest yangi `.1/.2` ID, direct edge, primary file, migration, test, rollback
va downstream dependency replacementi bilan yangilanadi; undan oldin kod yozish
boshlanmaydi. Shunda “40 reviewable PR-unit” soni ham shu commitda yangilanadi.

### COM1.0 — bugungi xavfni contain qilish

#### COM1.0a — birinchi kesim: finance capability va evidence gate

- **Bog‘liqlik:** yo‘q.
- **O‘zgarish:** stable `cohorts.review_payment`/
  `cohorts.view_payment_evidence` named permissions va Commerce policy;
  COM-D14gacha owner/superuser-only; ordinary staff va faqat codename holder
  deny. Private media, list/detail/decision, dashboard revenue/count, nav badge,
  student workspace, Django admin/inlines va bot context ayni policyda.
  `verify_receipt` faylsiz normal approve’ni typed failure bilan rad etadi;
  offline override yo‘q. Destructive legacy reject barcha adapterda
  `REJECTION_LEDGER_REQUIRED` bilan vaqtincha bloklanadi; Telegram qarori secure
  web handoff.
- **Files:** `core/access.py`, `core/views.py`, `core/private_media_views.py`,
  `cohorts/receipt_service.py`, `core/receipt_forms.py`, bot middleware/router,
  `cohorts/admin.py`, backoffice dashboard/nav/student workspace/receipt
  templatelari va context builderlar, tests.
- **Migration:** `PaymentReceipt.Meta.permissions` schema migrationi aynan ikki
  codename’ni content-type permission sifatida yaratadi; data auto-grant yo‘q.
  Mavjud superuser Django semantics saqlanadi, oddiy staff deny.
- **Test:** learner/teacher/ordinary staff/codename-only staff/owner × list/
  dashboard/count/revenue/workspace/admin/detail/file/approve/reject; difference
  receipt evidence-less deny; reject delete 0; web/bot parity; CSRF/replay.
- **Exit:** ordinary staff financial mutation/file **0**; no-evidence ordinary
  approval **0**; reject hard-delete **0**; existing evidence approval owner
  oqimida regressiya yo‘q. Ordinary staffga revenue/receipt PII chiqmaydi;
  non-sensitive aggregate alohida product admissiongacha owner-only.
- **Rollback:** faqat owner-only roll-forward fallback; global `is_staff`
  policy, destructive reject yoki bot mutation qayta yoqilmaydi. Permission
  migration harmless qoladi.

#### COM1.0b — lifecycle fail-loud va race containment

- **Bog‘liqlik:** COM1.0a.
- **O‘zgarish:** expiry task exceptionni yutmaydi; batch result/heartbeat;
  approval-vs-expiry conditional update; barcha legacy money/access writerlari
  §5.4 global lock orderiga moslashadi; duplicate notificationni idempotent key
  bilan contain; read-only health endpoint/command.
- **Files:** `cohorts/tasks.py`, `enrollment_service.py`, signals,
  notification service, core health/backoffice.
- **Test:** task failure status, retry, approve-vs-expire PostgreSQL test,
  duplicate notification, timezone boundary.
- **Exit:** injected failure successful run deb chiqmaydi; stale expiry active
  paid accessni yopmaydi.
- **Rollback:** health UI OFF; correctness conditional update qoladi.

#### COM1.0c — truthful copy va intent continuity

- **Bog‘liqlik:** yo‘q; COM1.0a bilan parallel alohida PR mumkin.
- **O‘zgarish:** legacy/V1 pricing/course/success/status copy factual;
  success faqat receipt accepted, access emas; pricing/course → login/register
  → checkout selection continuity server-side one-time opaque nonce bilan;
  queryda PII/promo/price yo‘q; open redirect deny.
- **Files:** subscription/course/checkout templates, `users/views.py`, V1
  public views/tests.
- **Test:** all renderer flag combinations, guest login/register roundtrip,
  tampered/expired intent, no-JS, snapshot copy assertions.
- **Exit:** “free/lifetime/unlimited/cancel anytime/access opened” false claim
  supported surfacelarda 0.
- **Rollback:** visual renderer mumkin; factual copy/security token qoladi.

#### COM1.0d — promo/upload va xavfli payment yo‘llari containmenti

- **Bog‘liqlik:** COM1.0a.
- **PR-unit COM1.0d1 — invariant boundary:** promo non-negative/max
  constraints; canonical upload validator web/V1ga; amount/period approval
  guard; legacy admin dangerous finance fieldlari read-only. Telegram photo/
  document writer COMMERCE-01 davomida qabul qilinmaydi.
- **PR-unit COM1.0d2 — destination/tier/bot containment:** current known
  placeholder yoki blank destination barcha legacy/V1/bot checkoutda fail-closed;
  minimal owner-only, audited existing-setting formdan tashqari config yo‘q;
  COM-D15gacha PAN/card recipient bu formdan readiness ololmaydi va payment
  unavailable qoladi.
  Cross-tier `allow_tier_change` va yangi difference request settlementli
  `CheckoutOrder(kind=upgrade|downgrade)` kelguncha bloklanadi; same-tier
  transfer saqlanadi. Existing
  open difference rows read-only `audit_unpaid_tier_uplift` bilan topiladi:
  previous settled plan snapshot aniq bo‘lsa incremental premium capability
  undan oshmaydi; source noma’lum bo‘lsa avtomatik downgrade qilinmaydi, critical
  finding release’ni bloklaydi va owner resolution talab qiladi. Telegram “latest
  checkout” photo upload permanent safe-disabled, web checkout/status link beradi.
- **Files:** `subscriptions/models.py`, promo service/forms/migration,
  receipt/upload service, `cohorts/transition_service.py`, membership service,
  frontend settings/form/backoffice payment hub, web/V1/bot checkout adapters,
  admin va tests.
- **Migration:** d1 promo check constraints; d2 schema yo‘q, mavjud destination
  qiymati migration/fixturega ko‘chirilmaydi.
- **Test:** `-1/0/100/101`, price’dan katta fixed, negative set-price;
  malicious/wrong file corpus web/V1; null/mismatch period/amount; admin deny;
  blank/known-placeholder destination all renderers/botda payment CTA0;
  cross-tier unpaid uplift0; Telegram photo/document deny va web-link handoff.
- **Exit:** adapter bypass/invalid promo/amount/period approval 0; ma’lum
  placeholderga payment instruction 0; yangi unpaid tier uplift 0; mavjud
  uplift findinglari explicit resolved yoki launch-blocking; “latest checkout”
  receipt attachment 0. Umumiy KPI “unpaid uplift 0” findinglar yopilmaguncha
  bajarilgan deb belgilanmaydi.
- **Rollback:** additive constraints drop qilinmaydi; owner-only destination
  readiness, tier block va Telegram safe-disable zaiflashtirilmaydi.

### COM1.1 — canonical additive schema va data audit

#### COM1.1a — Commerce foundation va secret-safe bootstrap

- **Bog‘liqlik:** COM1.0a, COM1.0d2.
- **PR-unit COM1.1a1 — catalog/policy schema:** `commerce` app;
  generic fenced/idempotent `CommerceOperationReceipt` (keyingi sibling service
  commandlari undan foydalanadi),
  `OfferVersion`, `CourseOffer`, `PaymentDestination`+version,
  `PaymentObservationNamespace`, `PaymentDestinationValueAlias`,
  `CommercePolicyVersion`+immutable `CommerceCompensationPolicyRule`,
  `PromoRule`+version; alias unique, published interval exclusions va boshqa
  constraints/indexes. Existing
  `checkout_quote_minutes` faqat draft `quote_preview_minutes`ga ko‘rsatiladi.
- **PR-unit COM1.1a2 — minimal bootstrap/publish:** current Plansdan non-secret
  draft offer yaratadigan idempotent command; owner-only web POSTda policy
  qiymatlarini va exact destination secretni kiritish, validate→preview→confirm→
  publish. Shu unit `commerce/crypto.py`, external KEK/HMAC key-provider
  interface, AES-256-GCM envelope, AAD/readback, per-revision wrapped DEK,
  `CommerceKeyPurpose`/`CommerceKeyVersion` exact migrationi, allowlisted purpose
  seedlari va nullable-current bootstrap/readiness contracti,
  whole-app startupni buzmaydigan critical Commerce health hamda fail-closed
  publish/order/exact-display, key-provider-ready gate va fake-provider testini
  ham beradi. Destination retained-key candidate lookup/current-key write
  readinessi, non-recomputable historical alias/key retirement guardi va same
  plaintext recipientning ikki familyga parallel publishida bitta namespace/
  ikkinchi conflict PostgreSQL testi ham shu unitda. Secret CLI
  arg, migration, repo, fixture, log yoki screenshotda yo‘q. Full studio va
  rotation UI COM1.6da; minimal crypto kechiktirilmaydi.
- **PR-unit COM1.1a3 — order substrate (a2dan keyin):** strict `CheckoutOrder`,
  `LegacyCommerceRecord`, a1dagi `CommerceOperationReceipt`ni reuse qiluvchi
  `PromoReservation`,
  seeded singleton `CommerceWriterControl`, `CommerceWriterRoute`,
  `CommerceWriterPilotMember`,
  `CommerceWriterRouteBatchRun/Item`; integer minor-unit, sticky route/epoch,
  versioned pilot admission, durable rollout dry/apply/cursor evidence va
  native-vs-legacy constraints/indexes. Shu unit minimal owner-only
  `configure_writer_salt` service/POSTi va provider readbackni beradi;
  COM1.2a route/backfill boshlanishidan oldin salt non-null bo‘lishi exit gate.
  Renewal/change `source_period` FKlari bu yerda yaratilmaydi: Period hali yo‘q;
  ular COM1.1c1ning aniq Order alter migrationida qo‘shiladi.
- **Migration:** uchta expand-only migration/PR; current tables untouched;
  automatic published offer/destination/policy yo‘q, checkout canonical writer
  emas.
- **Test:** empty/current DB forward; constraints, money conversion,
  Plan-parent concurrent revision allocation, policy aggregate stale child-edit/
  publish CAS, published immutability, secret non-leak, owner confirm, idempotent
  draft; incomplete legacy row only `LegacyCommerceRecord`ga.
- **Exit:** kamida bitta owner-confirmed policy/offer/destination stagingda
  publish qilina oladi; runtime checkout o‘zgarmaydi.
- **Rollback:** code/UI OFF; tables/draft/published rows retained. Secret
  exposure bo‘lsa incident+rotate, migration reverse emas; namespace/alias
  rows drop yoki destination familylardan ajratilmaydi.

#### COM1.1b — evidence, decision va payment ledger schema

- **Bog‘liqlik:** COM1.1a2 va COM1.1a3.
- **O‘zgarish:** `PaymentEvidence`, `PaymentDecision`,
  `PaymentApprovalAttestation`, `PaymentTransaction`, `PaymentResolution`,
  `PaymentAllocationSource`, `PaymentRefundSource`, `CommerceCashDeficit`+event,
  `SensitiveEvidenceIncident`+event, per-revision record-erasure-key envelope
  encryption va private blob lifecycle metadata;
  derivative preview, original download, sensitive flag/purge uchun alohida
  codenamelar. Direct settlement cash+fulfillment; blocked confirmed cash
  `unallocated_inflow`; keyingi fulfillment neutral allocation+immutable source
  rows bilan double-countsiz bog‘lanadi.
- **Test:** append-only guards, lineage/cycle/currency/amount constraints,
  conditional decision/transaction edge, dormant+enabled four-eyes schema va
  first/second oralig‘ida fingerprint-key rotation/retirement guard,
  mismatch→new MAX round→old-key retirement,
  delete protection, hash scope, original clean-scan gate, preview permission;
  scan/finalize-vs-flag, supersede-vs-purge va false-positive-vs-auto-erase CAS;
  PostgreSQLda ikki worker bir unallocated source’ni allocate/refund qilganda
  jami source amountdan oshmasligi va faqat bitta fulfillment; deterministic
  `PaymentRefundSource` split/cumulative bound; external reversal sabab negative
  cash iff exact CashDeficit/Event; ikki order ayni bank reference yoki ayni
  evidence bytesni different amount/time/kind bilan parallel yozganda bitta
  observation, ikkinchisi typed duplicate/classification-conflict resolution.
- **Exit:** reject/refund/correctionni status overwrite’siz ifodalash mumkin.
- **Rollback:** no read cutover; tables retained.

#### COM1.1c — subscription/access va event substrate

- **Bog‘liqlik:** COM1.1b.
- **PR-unit COM1.1c1:** `Subscription`, versioned `SubscriptionPeriod`,
  contractual enddan alohida effective-access end+reason/source/superseding
  period, `EntitlementOverrideDecision` funding actions/source resolution/
  applied compensation rule,
  versioned `EntitlementGrant`, UTC half-open interval,
  `CommerceDeliveryTransitionLink`, lifetime `(user, course)` unique va
  PostgreSQL `btree_gist` overlap constraint; CheckoutOrderga initialda null,
  renewal/upgrade/downgradeda required source period/offer/version/rank/boundary
  fieldlarini qo‘shadigan alter migration.
- **PR-unit COM1.1c2:** `CommerceEventOutbox`, exact `CommerceLifecycleRun`,
  `CommerceReconciliationRun/Finding` va operation lease helpers;
  OverrideDecision→Finding FK/final checks; minimal
  no-op/internal dispatcher health.
- **Migration:** c1 va c2 alohida expand-only migrations; legacy models/drop
  yo‘q.
- **Test:** source grant, interval/overlap, idempotency lease/fingerprint va
  stale-worker-after-reclaim CAS rollback, outbox uniqueness, PROTECT delete,
  crash/reclaim, retain/revoke/shorten funding decision va partial projection
  rollback.
- **Exit:** payment→access trace model darajasida mumkin.
- **Rollback:** runtime unused; tables retained.

#### COM1.1d — read-only legacy auditor va backfill rehearsal

- **Bog‘liqlik:** COM1.1c2.
- **O‘zgarish:** `audit_commerce_legacy --format json --no-pii`; anomaly
  taxonomy; production-copy rehearsal runbook; no mutation.
- **Test:** verified/unverified/no-image/deleted-history gap/null period/promo/
  overlap/capacity fixtures; deterministic report.
- **Exit:** every existing row classified; unknowns explicit; owner review pack.
- **Rollback:** command removal only; data unchanged.

### COM1.2 — backfill, canonical writer va cutover

#### COM1.2a — mutation journal, shadow write va resumable backfill

- **Bog‘liqlik:** COM1.1d owner review va COM1.0b global lock containmenti.
- **O‘zgarish:** inventoried legacy mutation journal/shadow hooks avval; global
  lock-order test; snapshot high-watermark; keyin batch/cursor/checkpoint/
  versioned transform va catch-up. `LegacyMutationJournal` exact schema/migration
  shu unitda; legacy mutation bilan ayni transaction. Strict row canonical, incomplete row
  `LegacyCommerceRecord`; dry-run default, resume safe.
- **Test:** writer-during-backfill, journal replay, rerun/restart/idempotency,
  mixed legacy fixtures, count/sum reconciliation, no fabricated metadata,
  PostgreSQL deadlock probe.
- **Exit:** shadow yoqilganidan keyin staging copy backfill+catch-up 2× same;
  ikki ketma-ket zero-diff pass; critical finding 0 yoki approved exception map.
- **Rollback:** additive rows retained; reader legacy.

#### COM1.2b — quote/order service, faqat internal shadow pilot

- **Bog‘liqlik:** COM1.2a va COM1.1a2dan owner-confirmed published policy,
  offer va destination readiness.
- **O‘zgarish:** quote/create-order commands, server recalc, persistent order,
  promo reservation expiry, destination snapshot; GET remains write-free.
- **Test:** stale/tampered quote, refresh/double-click, parallel order, missing
  destination fail-closed, expired promo, no-JS.
- **Exit:** internal/synthetic web order stable UUID/reference; current learner
  CTA hali legacy yoki safe-unavailable, canonical evidence/settlement va
  minimal outbox COM1.2d2gacha public rollout **taqiqlangan**.
- **Rollback:** order writer flag OFF; created orders remain visible/read-only.

#### COM1.2c — evidence/decision writer va immutable rejection

- **Bog‘liqlik:** COM1.2b.
- **O‘zgarish:** upload/needs-info/reject/review canonical; staged blob;
  legacy receipt shadow linkage; COM1.0ada bloklangan reject endi immutable
  terminal decision va promo reservation `rejected`+outbox; resubmit faqat `needs_info`,
  rejected retry linked new order. `flag_sensitive_auth_data` original/
  derivative accessni darhol yopib owner/security alert+auto deadline yaratadi;
  `purge_sensitive_auth_data` human confirm yoki overdue emergency service orqali
  external record handleni erase va active bloblarni verified delete qiladi.
  Emergency worker heartbeat/fail-loud, COM-D1 ordinary retentionidan mustaqil.
- **Test:** upload rollback/orphan cleanup, needs-info revisions, reject history,
  rejected→new linked order,
  promo limit immediate release, duplicate hash/replay, latest reviewable
  derivative/scan invariant, original-download permission matrix, false-positive
  before deadline, owner inactivityda auto-erasure, incidentdan oldingi backup
  restore’da unwrap deny, recoverable binary copies 0 va metadata audit saqlanishi.
- **Exit:** all supported adapter rejection metadata lineageni saqlaydi; ordinary
  reject blobni saqlaydi, SAD incident esa binaryni verified purge qiladi.
- **Rollback:** canonical orders stay; compatibility UI reads them.

#### COM1.2d — atomic settlement va projection cutover

- **Bog‘liqlik:** COM1.2c.
- **PR-unit COM1.2d1:** `settle_payment`; actual amount/reference HMAC;
  operation claim; exact lock order; PaymentTransaction + SubscriptionPeriod
  repository/kernel va mismatch/manual-resolution. Runtime
  `commerce_settlement_writer_v1=OFF`: real adapter route yo‘q va projection
  bundle ro‘yxatdan o‘tmagan chaqiriq `SETTLEMENT_PROJECTION_NOT_READY` bilan
  **hech qanday row yozmasdan** rad. Unit test fake bundle bilan bitta transaction
  rollback/constraintni isbotlaydi; d1 alohida deploy settlement yaratmaydi.
- **PR-unit COM1.2d2:** EntitlementGrant + seat/enrollment projection + outbox;
  minimal in-app dispatcher; writer epoch/fence, **internal/synthetic-only** web
  adapter va reconciliation. Shu unit real projection bundle’ni ulab transaction+
  period+grant+delivery-link+membership+outboxni **bitta atomic block**da yoqadi.
  Learner writer flag COM1.8cgacha OFF; COM1.4b2,
  COM1.5d1 va barcha P0 gate yopilmasdan public cutover taqiqlangan. Telegram
  binary COMMERCE-01 davomida safe-disabled.
- **Test:** duplicate/replay/stale; PostgreSQL parallel last seat, renewal,
  approve-vs-expire; injected failure at every write; HTTP legacy/V1 parity;
  old binary/queue fence va no-notification-before-commit.
- **Exit:** one intent→one settlement/period/grant; partial core write 0.
- **Rollback:** canonical writer pause, no ledger deletion; reconciliation.

### COM1.3 — learner uchun ultra qulay Commerce center

#### COM1.3a — canonical read model va order timeline

- **Bog‘liqlik:** COM1.2d2.
- **O‘zgarish:** one selector for display state/next action/access; order URL;
  needs-info/rejected/manual-resolution; existing history compatibility.
- **Test:** every state × access projection, unauthorized 404, cache headers,
  multiple open differences.
- **Exit:** raw Boolean/status template logic 0 supported surfacesda.
- **Rollback:** reader flag OFF; writer unchanged.

#### COM1.3b — checkout v2 responsive/no-JS

- **Bog‘liqlik:** COM1.3a.
- **O‘zgarish:** review/correct/confirm, destination safety, upload recovery,
  semantic status, 320px/400% UX.
- **Test:** browser no-JS+enhanced; keyboard, focus, errors, double submit,
  back/refresh, 320/1440, dark/light.
- **Exit:** golden path va exceptions accessible; no data/business duplication JSda.
- **Rollback:** renderer flag only.

#### COM1.3c — subscription center

- **Bog‘liqlik:** COM1.3a.
- **O‘zgarish:** active period, pending order/change, history, next action,
  support; renewal CTA admitted rules bilan.
- **Test:** no subscription, active/grace/expired/scheduled, multiple course,
  refund/manual resolution, no-JS.
- **Exit:** learner subscription holatini support so‘ramasdan tushunadi.
- **Rollback:** page flag OFF; canonical rows remain.

### COM1.4 — owner operations

#### COM1.4a — review workbench

- **Bog‘liqlik:** COM1.2c/COM1.3a.
- **O‘zgarish:** paginated queue, saved filter, age/SLA, private preview,
  reasoned confirm, stale recovery. Reviewer faqat sanitized derivative ko‘radi;
  original alohida owner-only endpoint, nonblank reason/audit va clean scan bilan.
- **Assignment:** `CommerceFinanceAssignment` exact migration va owner-only
  grant/revoke UI; named codename + fresh course/global scope + object policy.
  COM-D14 hal bo‘lmasa activation OFF, owner-only workbench.
- **Test:** permissions, query budget, pagination stability, keyboard/focus,
  two-reviewer race, grant/revoke/expiry race, scanner absent/pending/failed
  original deny, no binary leak.
- **Exit:** no raw receipt decision legacy page needed for new orders.
- **Rollback:** UI flag OFF; commands remain.

#### COM1.4b — manual resolution va compensating money

- **Bog‘liqlik:** COM1.4a. COM1.4b1 uchun COM-D6/D7/D9; COM1.4b2 uchun
  COM-D4/D5. COM-D2 plan-change slice’da.
- **PR-unit COM1.4b1:** cohort full, actual-amount mismatch, duplicate va stale
  price manual-resolution queue; alternative cohort/contact/cancel actionlari;
  typed `PaymentResolution`; settle doim canonical checks. Darhol settle
  bo‘lmaydigan confirmed cash `unallocated_inflow` ledgeriga yoziladi; keyin
  exact-due `allocation` bilan fulfillment yoki source-bound refund bilan
  accesssiz cancel qilinadi. Seat-bypass soxta settlement va cash double-count
  yo‘q; confirmed cashda bevosita reject/cancel deny. COM-D9 admitted
  bo‘lsa COM1.1bdagi approval-attestation roundini ishlatadi, yangi schema yo‘q.
- **PR-unit COM1.4b2:** refund/reversal/correction commands va compensating
  ledger; compensation-proof evidence, deterministic `PaymentRefundSource`,
  source settlement/allocation/unallocated lineage’i, `CommerceCashDeficit`/
  Event projectioni va access/order natijasi. Platform refundi COM-D4/D5ga qat’iy bog‘liq; proven reversal/
  required correction COM-D4siz ham money-truth + retain-with-debt finding
  yozadi, keyin `resolve_funding_deficit` owner qarori bilan yopadi. Shu unit
  COM1.5a ishlatadigan generic post-lapse unallocated/refund/finding
  primitivelarini beradi; terminal lifecycle commandining o‘zi COM1.5ada.
- **Test:** each reason state, cohort-full+no-alternative confirmed cash full
  refund+cancel **COM-D4 unresolved holatda ham**, under/overpayment full refund,
  partial unallocated refund deny, multiple-source allocation,
  approved-order excess refund, concurrent allocate-vs-refund source bound,
  full allocated single/multi-source underlying reversal → funding deficit+
  explicit access outcome; negative cash bo‘lsa iff exact CashDeficit/Event,
  inflow/outflow adjustment cash-net va COM-D5 revenue/access ajratilishi,
  compensating ledger, access policy, audit, notification.
- **Exit:** exceptional money no longer indefinite generic pending.
- **Rollback:** new cases pause in manual resolution; ledger immutable.

#### COM1.4c — health, outbox va reconciliation console

- **Bog‘liqlik:** COM1.1c2 va COM1.2d2.
- **O‘zgarish:** PII-minimal health, run details, dead outbox retry, dry-run
  repairs and export.
- **Test:** permission, failure visibility, retry idempotency, large cursor.
- **Exit:** owner can see stuck commerce without DB shell.
- **Rollback:** console OFF; scheduled metrics/alerts remain.

### COM1.5 — subscription lifecycle va plan change

#### COM1.5a — audited lifecycle policy va worker

- **Bog‘liqlik:** COM1.2d2, COM1.4b2, COM-D3 va COM-D16.
- **O‘zgarish:** COM1.1a2da bootstrap qilingan policy uchun full
  draft→validate→confirm/history UI; grace/review SLA/order window/reservation
  TTL transitions; fixed-as-of order expire→expired/lapsed va expired finalize;
  in-window late evidence, terminal post-lapse distinct external inflowning
  refund-only source/finding yo‘li; period lifecycle worker heartbeat/run rows.
  Eski OperationalSettings fieldi compatibility read-only.
- **Test:** boundary/timezone, direct lapse timestamp, create-vs-late-vs-lapse
  PostgreSQL race, multi-post-lapse observation/full-refund/finding close, invalid
  setting, task retry/resume, no silent fail.
- **Exit:** magic 2/30-day values canonical pathda 0.
- **Rollback:** last published settings; rows versioned.

#### COM1.5b — renewal semantics

- **Bog‘liqlik:** COM1.5a; transfer continuity COM-D10. Commercial pause current
  40-unit scope’da yo‘q; owner uni tanlasa koddan oldin yangi schema/unit/edge
  bilan manifest qayta tasdiqlanadi.
- **O‘zgarish:** user-course subscription lineage, scheduled period, current
  enddan extension, legacy transfer continuity.
- **Test:** early/on-expiry/late/concurrent renewal, transfer, promo eligibility,
  overlap/gap.
- **Exit:** every renewal deterministic period va source transactionga ega.
- **Rollback:** renewal writer pause; existing periods remain.

#### COM1.5c — upgrade/downgrade

- **Bog‘liqlik:** COM-D2/D5, COM1.5b.
- **O‘zgarish:** default prepaid `CheckoutOrder(kind=upgrade|downgrade)` —
  “plan-change order” alohida model emas; settlementgacha uplift yo‘q;
  effective date/proration faqat admitted matrix.
- **Test:** upgrade/downgrade each timing, unpaid/failed/rejected, concurrent
  change, quota/access projection.
- **Exit:** unpaid uplift 0; each change order+decision lineage.
- **Rollback:** new plan-change creation pause; existing scheduled honored/resolved.

#### COM1.5d — expiry/grace/access va delivery projection

- **Bog‘liqlik:** COM1.5a–c, COM-D4.
- **PR-unit COM1.5d1:** conditional period transitions, grace va typed
  entitlement revoke; refund outcome COM1.4b2 ledgeridan.
- **PR-unit COM1.5d2:** delivery membership/seat explicitly separate;
  existing `EnrollmentTransition`ga period/order/resolution va reasonni bog‘lovchi
  COM1.1c1da allaqachon yaratilgan append-only
  `CommerceDeliveryTransitionLink` contractidan foydalanadi, bu unitda yangi
  schema yo‘q; transfer va pedagogik freeze faqat COM-D6/D10ga mos reason-coded
  transition. Commercial pause bu roadmap scope’ida emas.
- **Test:** expiry-vs-renew/settle/refund, grace access, manual revoke, reactivation,
  cohort seat rules.
- **Exit:** payment/subscription/access/delivery state aralashmasi yo‘q.
- **Rollback:** worker pause + reconciliation; history untouched.

### COM1.6 — catalog, destination va promo governance

#### COM1.6a — offer revision service va studio

- **Bog‘liqlik:** COM1.1a1. B3 koordinatsiyasi execution dependency emas:
  Commerce current navigation extension pointidan foydalanadi va B3 kodiga
  majburiy o‘zgarish kiritmaydi. B3 change zarur topilsa manifest avval yangi
  explicit unit/edge bilan yangilanadi.
- **PR-unit COM1.6a1:** offer draft/validate/publish/retire service, effective
  schedule, course-offer matrix, CAS/idempotency/audit.
- **PR-unit COM1.6a2:** owner studio UI, diff/history/preview va factual claim
  readiness.
- **Test:** immutability, overlapping schedule, current orders unchanged,
  permission/audit, preview isolation.
- **Exit:** published price/term/claims inplace edit 0.
- **Rollback:** publish previous content as new revision.

#### COM1.6b — destination studio

- **Bog‘liqlik:** COM1.1a2; COM1.2b order preview bilan integration test.
- **O‘zgarish:** masked secret-aware editor, placeholder/readiness, effective
  version, safe preview/confirm; COM1.1a2 crypto service ustida KEK rewrap/
  rotation/history operations. Bu unit crypto asosini birinchi marta yaratmaydi.
- **Test:** secret blank preservation, unauthorized mask, no log/render leak,
  missing active destination blocks checkout, rewrap ciphertext/tagni
  o‘zgartirmasligi, actionable-order crypto-shred deny.
- **Exit:** checkout destination has exact audited version.
- **Rollback:** previous destination as new revision; current order snapshot unchanged.

#### COM1.6c — promo lifecycle

- **Bog‘liqlik:** COM1.2b/COM1.5b.
- **O‘zgarish:** COM1.1a1/a3dagi `PromoRuleVersion/PromoReservation` ustida
  versioned rules, reservation TTL/release, user-course renewal eligibility,
  limit reconciliation, owner UI; yangi schema yo‘q.
- **Test:** concurrency, abandon/expire/reuse, transfer bypass, boundary values,
  current order snapshot.
- **Exit:** promo limit leak/drift 0.
- **Rollback:** new redemption pause; existing reservation/order preserved.

### COM1.7 — adapters, notification va analytics

#### COM1.7a — Telegram metadata/status parity va secure web handoff

- **Bog‘liqlik:** COM1.2d/COM1.3a.
- **O‘zgarish:** stable order FSM, status/readback, order-scoped one-time
  authenticated **web** evidence-upload link, secure reviewer handoff, callback
  idempotency/fresh role. Bot photo/document binaryni qabul qilmaydi/yuklamaydi.
- **Test:** two parallel orders, stale/replayed/other-user handoff link va
  callback, photo/document deny, wrong course, revoked staff, web/status parity.
- **Exit:** “latest checkout” heuristic, direct finance mutation va Telegram
  inbound binary 0.
- **Rollback:** bot Commerce entry pause; web remains canonical.

#### COM1.7b — notification outbox

- **Bog‘liqlik:** COM1.2d.
- **O‘zgarish:** email/in-app/Telegram adapters only outbox; user preference;
  dead-letter/retry; no binary/secret.
- **Test:** broker outage/replay/order, mute, stale recipient, content snapshot.
- **Exit:** settlement succeeds independently; notification loss/duplicate bounded.
- **Rollback:** dispatcher pause, queue retained.

#### COM1.7c — trustworthy finance/operations analytics

- **Bog‘liqlik:** COM1.4b2, COM1.4c va COM1.5d1.
- **O‘zgarish:** settled/refunded net, currency segmentation, funnel definitions,
  reviewer workload, renewal/cohort resolution; no `submitted_at` revenue.
- **Test:** settlement/refund/adjustment dates, multi-currency HOLD behavior,
  permission, query budget.
- **Exit:** dashboard metrics each documented source/time semanticsga ega.
- **Rollback:** analytics view OFF; ledger untouched.

### COM1.8 — privacy, scale va release

#### COM1.8a — retention/export, key lifecycle va irreversible purge

- **Bog‘liqlik:** COM-D1, COM1.6b established key lifecycle va canonical cutover.
- **PR-unit COM1.8a1:** retention policy, audit minimum, learner export,
  destination/evidence KEK rewrap+retirement va §6.3dagi barcha exact key-purpose
  HMAC keylari, legal-hold commands hamda account anonymization contract; exact
  `CommerceRetentionPolicyVersion`, `CommerceLegalHold`,
  `CommerceRetentionRun` va fenced `CommerceRetentionClaim`, exactly-one as-of
  selector, immutable cutoff snapshot va legal copy review. Ordinary purge hali
  yo‘q; COM1.6b established key service prerequisite.
- **PR-unit COM1.8a2:** evidence/derivative/backup/replica va backupdan mustaqil
  authoritative erasure-registry limitationsi bilan purge queue, crypto-shred va
  restore’dan keyingi re-purge. Telegram binary nusxasi COMMERCE-01da umuman
  yaratilmaydi.
- **Test:** retention exactly-one selector, published interval overlap, fixed
  as-of/cutoff snapshotga mid-run policy publish ta’sir qilmasligi, fresh legal
  hold claimni skip qilishi, hold-vs-purge va SAD-hard-deadline precedence,
  dry-run mutation 0; retention boundary, rewrap CAS/orphan, barcha allowlisted
  purpose sluglari seed/current/retire guardi, open approval/reference hold,
  pending claim/run va lineage replay blocker testlari, old-KEK retirement guard,
  provider key-loss fail-closed, promo old-key lookup,
  purge retry, pre-incident backup unwrap deny, export authorization va ledger
  totals preserved.
- **Exit:** finite policy implemented and owner-approved; metadata/decision
  lineage binary purge’dan keyin qoladi.
- **Rollback:** ordinary purge job pause; destructive purge qaytarib bo‘lmaydi,
  canary+restore/re-purge rehearsal majburiy. SAD emergency deadline workeri
  pause qilinmaydi. Backup/replica retention purge’ni cheksiz bekor qilmaydi va
  COM-D1 policyga kiradi.

#### COM1.8b — capacity, chaos va restore rehearsal

- **Bog‘liqlik:** COM1.2d2, COM1.3b, COM1.4c, COM1.5d2, COM1.6c,
  COM1.7a, COM1.7b va COM1.8a2.
- **O‘zgarish:** named runner
  `manage.py commerce_release_rehearsal --fixture-size 10000 --concurrency 50
  --duration-seconds 600 --output artifacts/commerce-rehearsal.json`; 10k synthetic
  order/period/evidence-metadata, 50 parallel create/settle, queue/query budgets,
  60s DB connectivity, 300s broker va 120s storage failure injection, backup→
  restore→reconciliation. Real binary/PII/payment data yo‘q, ammo runner o‘zi
  yaratgan deterministic non-PII kichik rasterlardan ikkitasi majburiy: bittasi
  live encrypted preview/RTO readback uchun; ikkinchisi backupdan keyin SAD purge
  qilinib, pre-incident backup restore’ida ham unwrap deny isboti uchun.
- **Test/pass:** 3 repeat run; duplicate/partial core write va critical finding 0;
  p95 read ≤500ms, p95 command DB qismi ≤1500ms, review page ≤25 SQL, checkout
  ≤15 SQL; recoverydan 60s ichida outbox age ≤60s. Disaster rehearsal RPO ≤5
  daqiqa va RTO ≤60 daqiqa. RPO clock: runner har 10 soniyada committed marker
  order+transaction+outbox va private-object manifest yozadi; `T_fail` oxirgi
  acknowledged commitdan keyin qayd etiladi, isolated restore’dagi eng yangi
  fully linked marker `T_recovered`; `RPO = T_fail - T_recovered`. Scope:
  PostgreSQL legacy+canonical/journal/outbox/incident metadata, private evidence
  ciphertext inventory, authoritative destroyed-handle registry va external
  destination/evidence KEK hamda HMAC key references. Key material backupga
  ko‘chirilmaydi; provider+erasure-registry resolve/readback decryptdan oldingi
  restore gate. Redis authoritative emas va rebuild qilinadi.
- **RTO clock:** monitoring runner failure’ni `T_detect` deb qayd qilgan ondan
  isolated restored stack health green, keys resolve, live synthetic fixture
  uchun one scoped preview decrypt, erased fixture uchun unwrap deny,
  canonical+legacy reader va owner queue ishlaydi, reconciliation critical 0,
  pending outbox replaydan oldest age ≤60s bo‘lgan `T_ready`gacha;
  `RTO = T_ready - T_detect`. Missing blob/key yoki orphan money row PASS emas.
  `JSON + Markdown + timestamps + marker IDs + commit + environment` artifact
  CI/stagingda saqlanadi. Named runner: release operator; owner COM-D17 bilan
  limitni qabul qiladi, aks holda rollout HOLD.
- **Exit:** yuqoridagi barcha threshold PASS va owner COM-D17 sign-off.
- **Rollback:** rollout blocked; no production canary.

#### COM1.8c — staged cutover va final evidence

- **Bog‘liqlik:** manifestdagi barcha leaf edge’lar, COM1.8b, all P0 closed,
  relevant owner decisions resolved.
- **O‘zgarish:** internal reviewer → synthetic learner → bounded real canary →
  staged percentage; shu yerdagina learner writer flag ON; legacy read-only;
  runbook/support pack. Har thresholddan oldin exact high-watermark/cursorli
  legacy-route batch migratsiyasi; abortdan keyin legacy va canonical route uchun
  backendni almashtirmaydigan epoch resume majburiy.
- **Test:** E2E matrix, native devices/AT, Telegram, migration/restart/rollback,
  1→5→25→50→100 eligible legacy-route drain va pending skip/resume,
  legacy+canonical abort/resume races, security review, observability readback.
- **Exit:** Definition of Done; owner explicit rollout sign-off.
- **Rollback:** canary stop, writer floor respected, pending orders resolvable.

---

## 12. Test va qabul matrixi

### 12.1 Majburiy avtomatik contractlar

| Soha | Minimal testlar |
|---|---|
| Authorization | learner/teacher/staff/reviewer/owner × list/detail/file/all commands; assignment grant/revoke/expiry; original POST+reauth+reason |
| Quote/order | issued-at policy selection va quote-expiry honor, publish/retire-vs-create lock race, per-kind subscription matrix, server recalc, cross-object lineage, active-intent unique, sticky writer route/epoch, stale/expired destination/promo, double-click/idempotency conflict |
| Evidence | allowlist/signature/MIME/size/pixel, record-key envelope encryption/provider loss/rewrap/retirement, web upload + bot handoff, derivative/original/scan truth-table, staged rollback/orphan, revision/reject, SAD deadline/auto-erasure/pre-incident-backup unwrap deny/retention |
| Decision | request-info/reject/propose/settle, reason, stale version, two reviewer race/four-eyes different actor, secret-like note reject, no delete |
| Money | positive total/currency, one settlement-or-allocation fulfillment/order, exact kind/direction/source/observation-role matrix va cross-kind conflict, cash-observation namespace multi-key dedup, allocation source sums/free balance, deterministic PaymentRefundSource split/cumulative bounds, exact funding deficit, `CashDeficit=max(0,-cash_net)` Event replay/recovery/write-off, immutable ledger, inflow/outflow adjustment cash totals, refund/reversal resolution lineage; multi-source va multi-post-lapse fact/full-refund concurrency |
| Subscription | scheduled/active/grace/expired/revoked, renewal timing, grace supersession/effective-access overlap, timezone |
| Entitlement | source required, unknown fail-closed, settlement projection, refund policy, override expiry |
| Cohort | last seat PostgreSQL concurrency, cohort full manual resolution, transfer/renewal |
| Promo | negative/boundaries, order-coupled reservation TTL, review hold, concurrent settle/expire/reacquire limit, expired late-flow reject/cancel no-reopen, successful reacquire mapping, terminal release, transfer renewal bypass |
| Tasks/outbox | commit-before-dispatch, replay, broker failure, leased-token reclaim/stale-finalize, crash-after-send at-least-once duplicate bound, dead-letter/manual retry, heartbeat/fail-loud |
| Migration | empty/current DB, journal monotonic revision/dedup, writer-during-backfill, dry-run/resume/rerun, counts/sums, sticky-route threshold batch/high-watermark, legacy+canonical epoch resume va rollback floor |
| Privacy | unauthorized 404/no cache, no secret in notes/outbox/log, pre-backup crypto-erasure, PROTECT/anonymization |
| UI | no-JS, keyboard/focus/status, errors preserve context, 320px/400%, renderer parity |
| Reconciliation | every critical invariant finding, dry-run, repair authorization/idempotency |

### 12.2 Yakuniy E2E ssenariylar

1. Guest Standardni course detaildan tanlaydi, register qiladi, ayni tanlovga
   qaytadi, order ochadi, evidence yuboradi, owner settle qiladi, access oladi.
2. JavaScriptsiz shu oqim.
3. Double submit/timeout/retry bitta order/evidence/settlement/grant beradi.
4. Learner ikki kurs/order ochadi; Telegram aynan tanlangan orderning one-time
   authenticated web upload linkini beradi, photo/documentning o‘zini olmaydi.
5. Promo checkout abandon bo‘ladi; TTLdan keyin limit bo‘shaydi.
6. Price/destination/policy orderdan keyin o‘zgaradi; eski order snapshoti
   o‘zgarmaydi. Policy quote bilan create orasida publish/retire bo‘lsa issued-at
   revision token expiry’gacha aynan honor qilinadi yoki invalid token row 0 beradi.
7. `needs_info` yangi evidence revisionni qabul qiladi; terminal rejected
   order status/reason/timeline bilan qoladi va ruxsatli retry yangi
   `previous_order`-linked order yaratadi.
8. Difference order evidence’siz approve bo‘lmaydi.
9. Ordinary staff URL/bot/file/POST orqali qaror yoki evidencega kira olmaydi.
10. Ikki reviewer bir payt approve: oddiy summada bittasi settlement, ikkinchisi
    current result readback; COM-D9 threshold yoqilgan summada first proposal
    pul/access bermaydi va faqat boshqa reviewerning fresh second attestationi
    settlement beradi.
11. Oxirgi seatga ikki settlement: bittasi approved, bittasi manual resolution;
    ikkalasiga ham noaniq pending emas.
12. Oxirgi seatni yutqazgan orderda confirmed cash unallocated inflow sifatida
    bir marta yoziladi; alternative cohort yo‘q va COM-D4 unresolved bo‘lsa ham
    full refund+cancel tugaydi, period/grant/delivery 0. Shu paytda boshqa order
    boshqa destination family, ammo ayni observation namespace orqali ayni
    reference yoki evidence bytesni different amount/time bilan yuborsa
    PostgreSQL race’da ikkinchi inflow 0 va typed duplicate resolution oladi.
    Lapsed eski order uchun keyin topilgan ikki distinct bank transfer esa ikki
    refund-only source/finding bo‘lib yoziladi; har full refund o‘z findingini
    atomik yopadi, yangi active order va accessga tegmaydi.
13. Early renewal periodni overlap qilmay uzaytiradi.
14. Approval va expiry race paid accessni yopmaydi.
15. Upgrade paymentdan oldin capability/quota oshirmaydi.
16. Refund/reversal admitted owner policy bo‘yicha compensating ledger va
    access natijasini beradi; exact-due single/multi-source allocationdan keyin
    bir underlying inflow bank reversal bo‘lsa physical cash net kerak bo‘lsa
    manfiy bo‘ladi, ammo `max(0,-cash_net)` exact CashDeficit/Event projectioniga
    teng; funding deficit va access outcome atomik, silent loss/funded-access
    drift 0. Settlement 100 → platform refund 100 → bank reversal 100 case’i
    cash=-100, deficit=100ni isbotlaydi.
17. DB failure settlement/period/grant/outboxning yarmini qoldirmaydi.
18. Broker/Telegram outage settlementni qaytarmaydi; retry duplicate emas.
19. Evidence storage finalize failure explicit retry/manual resolution,
    orphan reconciliation; PAN/CVV/PIN topilsa immediate restricted incident,
    owner javob bermasa bounded deadline’da auto-erasure, pre-incident backupda
    unwrap deny va metadata-only audit qoladi.
20. Destination invalid bo‘lsa sale CTA payment instructions bermaydi.
21. Account anonymization finance totals/source lineageni saqlaydi, PII policy
    bo‘yicha yo‘qoladi.
22. Backfill rerun current legacy fixtureda row/sum duplikat qilmaydi.
23. Shadow reader canonical accessni legacyga nisbatan yashirin kengaytirmaydi;
    canary 1→5→25→50→100 batchi eligible legacy routelarni cursor/idempotency bilan
    drain qiladi, pendingni skip+resume qiladi; abortdan keyin legacy va canonical
    route epochi backend flip qilmasdan ko‘tariladi va persisted order almashmaydi.
24. 320px/400% reflow, keyboard, NVDA status/error.
25. Android/iOS private web evidence upload va Telegram link-only handoff native
    sign-off; bot inbound binary deny.
26. Disaster runner RPO≤5m/RTO≤60mni exact marker/clock bilan o‘lchaydi;
    restore’dan keyin live synthetic raster decrypt, erased synthetic raster
    unwrap deny, keys/readers/outbox green va reconciliation critical 0.

### 12.3 Safe-env buyruqlari

COM1.0a–d2da `commerce` app hali yo‘q; shu pre-Commerce baseline ishlatiladi:

```powershell
$env:AZURELMS_SKIP_ENV_FILE='1'
$env:APP_ENV='local'
$env:LOCAL_USE_REMOTE_SERVICES='False'
$env:GEMINI_API_KEY=''
$env:TELEGRAM_BOT_TOKEN=''

.\venv\Scripts\python.exe manage.py check
.\venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\venv\Scripts\python.exe manage.py test cohorts subscriptions users.test_frontend_v1_records core.test_entitlements core.test_receipt_decisions core.test_private_media bot.test_checkout_parity bot.test_receipt_target --noinput --verbosity 1
.\venv\Scripts\python.exe .tools\docs-sync\verify_docs.py
git diff --check
```

COM1.1a1dan keyin broader Commerce regression:

```powershell
$env:AZURELMS_SKIP_ENV_FILE='1'
$env:APP_ENV='local'
$env:LOCAL_USE_REMOTE_SERVICES='False'
$env:GEMINI_API_KEY=''
$env:TELEGRAM_BOT_TOKEN=''
.\venv\Scripts\python.exe manage.py check
.\venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\venv\Scripts\python.exe manage.py test commerce cohorts subscriptions core.test_entitlements core.test_receipt_decisions core.test_private_media bot.test_checkout_parity bot.test_receipt_target --noinput --verbosity 1
.\venv\Scripts\python.exe .tools\docs-sync\verify_docs.py
git diff --check
```

PostgreSQL concurrency slice `.github/workflows/ci.yml` required jobida real
PostgreSQL bilan o‘tmaguncha green deb hisoblanmaydi. Frontend o‘zgarsa mavjud
Node suite va targeted browser probes qo‘shiladi. Real key/token test envga
yuklanmaydi.

### 12.4 Manual evidence formati

Har stage evidence hujjati quyidagini yozadi:

- commit/PR/branch va base;
- schema/backfill/row counts before-after;
- aniq commands va pass/skip/fail;
- browser viewport, JS/no-JS, keyboard/AT/native coverage;
- role/account fixture va PII’siz screenshot/video;
- flag/settings oldingi/yangi qiymati;
- reconciliation summary;
- deploy/canary qilindimi yoki qilinmadimi;
- rollback rehearsal va remaining risks.

---

## 13. Keyingi agent uchun bajarish protokoli

### 13.1 Ishni boshlashdan oldin

1. `AGENTS.md`, `rules-for-agents.md`, marinebookning so‘nggi 3–5 yozuvi va
   `nuclear-program/README.md`ni o‘qish.
2. `git status --short --branch`, `git log --oneline --decorate -8`,
   `git branch -a`; clean `main`/`origin/main`dan o‘z `codex/`, `claude/` yoki
   `antigravity/` branchi.
3. Shu hujjatda slice dependency va owner decisionini tekshirish. `HOLD`
   qaror bo‘lsa taxmin bilan implement qilmaslik.
4. Slice tegadigan barcha writer/consumerlarni `rg` bilan topish; faqat roadmap
   file listiga suyanmaslik.
5. Baseline focused testni o‘zgartirishdan oldin yugurtirish.

### 13.2 Har slice tartibi

1. Slice ID va outcome’ni PR title/bodyga yozing.
2. Model/state/policy o‘zgarsa avval contract test.
3. Additive migration; destructive migration alohida owner admission.
4. Canonical service; keyin web, bot, admin adapterlari.
5. Permission, idempotency, concurrency, failure injection va no-JS test.
6. Reconciliation/readback/telemetry.
7. Relevant hujjat, README holati va stage evidence.
8. Safe-env focused + broader regression, docs verifier, `git diff --check`.
9. Logical commit, mandatory co-author trailer, marinebook, push/PR.
10. Required CI, review izohlari va branch freshness qoidalariga amal qilish.

### 13.3 PR hajmi va dependency qoidasi

- Bir PR bir §11.1 PR-unit; 600+ production LOC yoki bir nechta mustaqil
  migration transitioni bo‘lsa shu unitni `.1/.2` qilib yana bo‘ling.
- Schema PR runtime cutover qilmaydi.
- UI PR direct model write qo‘shmaydi.
- Bot PR canonical service’siz business logic yaratmaydi.
- Analytics PR canonical settled timestampdan oldin revenue da’vo qilmaydi.
- Refactor va behavior change bitta diffda aralashtirilmaydi.
- Backfill command dry-run default; production mutation explicit flag+
  backup+owner approval bilan.

### 13.4 Stop/eskalatsiya shartlari

Quyidagida agent commit/pushdan oldin to‘xtab ownerga aniq dalil beradi:

- real payment/receipt data’da noma’lum yoki contradictory lineage;
- destructive migration, hard delete yoki irreversible purge;
- refund, proration, credit, transfer, pause yoki legal retention qarori;
- migration/backfill expected count/sumdan farq;
- production destination/secret kerak bo‘lishi;
- payment provider admission;
- legacy/canonical access diff canonical tomonda kengroq;
- settlement/access reconciliation critical finding;
- boshqa agentning uncommitted o‘zgarishi bilan conflict;
- required security/CI failure.

“Qiyin” yoki test uzoq davom etishi stop sababi emas. Xavfsiz read-only audit,
fixture, test va docs bilan davom etiladi.

### 13.5 Tavsiya etilgan PR navbati

Exact DAG [§11.1 execution manifest](#111-execution-manifest-va-exact-dag)dagi
`Direct dependency` ustunidir; uni soddalashtirgan parallel ASCII graph bilan
almashtirmang. Minimal release critical path:

| Milestone | Required PR-unitlar |
|---|---|
| Bugungi xavfni yopish | COM1.0a, COM1.0b, COM1.0c, COM1.0d1, COM1.0d2 |
| Canonical substrate | COM1.1a1–a3, COM1.1b, COM1.1c1–c2, COM1.1d |
| Internal canonical writer rehearsal | COM1.2a–c, COM1.2d1–d2; learner flag OFF |
| Learner/owner usable pilot | COM1.3a–c, COM1.4a, COM1.4c |
| Policy-dependent money/lifecycle | relevant COM1.4b/COM1.5 units only owner gates resolved bo‘lsa |
| Full adapter/catalog | COM1.6/COM1.7 dependencies manifest bo‘yicha |
| Release | COM1.8a1–a2, COM1.8b, COM1.8c |

COM1.6 catalog studio current UI/navigation extension contractiga joylashadi;
B3 tashqi dependency emas va Commerce invariantlarini rendererga bermaydi.
COM1.7 Telegram
Messenger outbox patternsidan foydalanishi mumkin, lekin payment commandni
Messenger domeniga ko‘chirmaydi.

---

## 14. Ochiq owner qarorlari

| ID | Qaror | Qarorgacha xavfsiz default | Kerak bo‘ladigan slice |
|---|---|---|---|
| COM-D1 | Receipt/evidence binary, finance ledger va audit retention muddatlari | ordinary purge yo‘q, production rollout HOLD; `SENSITIVE_AUTH_DATA_INCIDENT` darhol contain, default 15/hard max 60 daqiqada manual yoki auto crypto-erasure | 1.2c/1.8a1/a2 |
| COM-D2 | Upgrade paymentdan oldin beriladimi? Credit/receivable bormi? | **prepaid**: settlementgacha uplift yo‘q | 1.5c |
| COM-D3 | Grace muddati va qaysi capabilitylar grace’da qoladi | joriy 2 kun compatibility, yangi UI va’da qilmaydi | 1.5a/d1 |
| COM-D4 | Full/partial refund, reversal va access natijasi | avtomatik revoke/refund yo‘q; manual resolution | 1.4b2/1.5d1 |
| COM-D5 | Upgrade/downgrade effective date va proration | proration HOLD; yangi term next boundary yoki explicit quote | 1.5c |
| COM-D6 | Cohort full bo‘lsa alternative/refund SLA va authority | manual resolution, no silent settlement | 1.4b1/1.5d2 |
| COM-D7 | Amount/reference tolerance va partial payment | exact expected amount; mismatch manual resolution | 1.4b1 |
| COM-D8 | Evidence resubmit soni/deadline | bounded setting hali e’lon qilinmaydi; abuse rate limit | 1.3a/1.5a |
| COM-D9 | High-value settlement four-eyes threshold; boshqa dangerous action step-up’i | threshold null/dormant, owner-only + fresh reauth; admitted threshold predeclared attestation flow’ni yoqadi | 1.1b/1.4b1/1.6 |
| COM-D10 | Subscription pause/freeze/transfer commercial policy | yangi commercial pause current scope’da yo‘q; “yes” bo‘lsa implementationdan oldin yangi manifest unit/schema; pedagogik freeze alohida | 1.5b/d2 yoki roadmap amendment |
| COM-D11 | Calendar monthmi yoki aniq 30 kunmi | mavjud contract exact 30 days sifatida ko‘rsatiladi | 1.1a1/1.6a1 |
| COM-D12 | Learner o‘z evidence preview/download qila oladimi | status metadata only; support/reviewer private binary | 1.3a/1.8a1 |
| COM-D13 | Payment provider admission | manual transfer only | future ADR |
| COM-D14 | Finance reviewer roli kimlarga beriladi va course scope bormi | faqat owner/superuser; ordinary staff deny | 1.0a/1.4a |
| COM-D15 | Recipient destination PAN/card bo‘ladimi va uning PCI/compliance validationi qanday? | `card_transfer` publish yopiq; non-PAN admitted destination yoki HOLD | 1.1a2/1.6b |
| COM-D16 | Quote preview, order payment, promo reservation, late-evidence window va manual review SLA nechchi? | joriy quote preview 30 daqiqa compatibility; late window 0, yangi order/promo cutover va SLA va’dasi HOLD | 1.1a2/1.5a |
| COM-D17 | Release capacity va disaster recovery SLOsi qabul qilinadimi? | p95 read 500ms, command DB 1500ms, review 25/checkout 15 SQL, RPO 5m, RTO 60m taklifi; sign-offsiz rollout HOLD | 1.8b/1.8c |

Owner qarori sana, exact rule, oldingi qarorni almashtiradimi, migration va
learner copy ta’siri bilan pricing ledger yoki ADRga yoziladi. Chatdagi noaniq
gap production policy hisoblanmaydi.

Gate klassifikatsiyasi exact: COM-D1 (finite retention/purge authority), COM-D16
(public order/promo/SLA qiymatlari) va COM-D17 (capacity/DR acceptance) production
learner rollout uchun **release-blocking**; ularda HOLD Definition of Done yoki
COM1.8c PASS emas. Qolgan qaror faqat uning feature’i yoqilsa release-blocking:
masalan COM-D4/D5 unresolved bo‘lsa fulfilled partial refund/proration/plan-change
OFF qolishi mumkin, COM-D14 unresolved bo‘lsa owner-only, COM-D15 unresolved
bo‘lsa card destination OFF. Safe-disabled optional slice uchun “scope HOLD” docs/
schema roadmapini tugatishi mumkin, lekin o‘sha feature shipped deb sanalmaydi.

---

## 15. COMMERCE-01 Definition of Done

Commerce reform faqat quyidagilarning **hammasi** yopilganda tugagan:

- [ ] P0 topilmalar runtime’da yopilgan, regression va permission matrix green.
- [ ] Published offer/destination immutable revision va readinessga ega.
- [ ] Har yangi checkout durable order, stable reference va idempotencyga ega.
- [ ] Evidence append-only revision, private lifecycle va finite approved
      retentionga ega.
- [ ] Original evidence faqat clean scan + owner-only named permission/reason
      bilan; reviewer derivative bilan ishlaydi.
- [ ] Prohibited PAN/CVV/PIN incident binarysi COM-D1ni kutmasdan restricted va
      verified purge bo‘ladi; minimal audit qoladi.
- [ ] Ordinary reject/request-info binaryni darhol o‘chirmaydi; SAD incident
      mustasno. Har purge’dan keyin decision/evidence metadata lineage qoladi.
- [ ] Settlement/refund/reversal append-only payment ledgerda.
- [ ] Payment → period → entitlement → delivery lineage query bilan izlanadi.
- [ ] Parallel approval/renewal/expiry/last-seat PostgreSQL’da green.
- [ ] Unpaid entitlement uplift 0; source’siz active grant 0.
- [ ] Web, Telegram, owner UI canonical commands/read-modeldan foydalanadi;
      Telegram binary olmaydi, order-scoped web handoff beradi.
- [ ] Pricing→auth→checkout intent yo‘qolmaydi; no-JS core ishlaydi.
- [ ] Learner order timeline va subscription center next actionni aniq beradi.
- [ ] Owner queue paginated/scoped/audited/SLA-observable.
- [ ] Outbox/lifecycle fail-loud, retryable va owner-visible.
- [ ] Revenue analytics settled/refund time va currency semanticsiga ega.
- [ ] Backfill 2× idempotent; shadow diff critical 0; rollback rehearsal PASS.
- [ ] Sticky writer route, staged canary, abort/fence va pending-order readback
      rehearsal PASS; backend silently almashmaydi.
- [ ] 26 E2E ssenariy, accessibility/native/Telegram gates dalillangan.
- [ ] COM-D1, COM-D16 va COM-D17 resolved/sign-off; boshqa enabled production
      slice qarorlari resolved, faqat safe-disabled optional slice scope HOLD.
- [ ] Required CI green, review izohlari resolve, docs/marinebook/current state
      yangilangan.
- [ ] Production rollout alohida owner sign-off va canary evidence bilan.

---

## 16. Birinchi implementatsiya task kartasi — COM1.0a

### Outcome

COM-D14 hal bo‘lguncha faqat owner/superuser receipt/evidence’ni ko‘radi va
evidence bor paymentni tasdiqlaydi; oddiy staff, teacher yoki faqat permission
codename olgan user kira olmaydi. Evidence’siz tier-difference/oddiy receipt
approvaldan o‘tmaydi. Tarixni o‘chiradigan reject vaqtincha bloklanadi. Telegram
finance mutation uchun secure web workbenchga olib boradi.

### Scope

1. Bitta policy API yarating, masalan:

   ```python
   can_review_payment(user, receipt_or_order) -> bool
   can_view_payment_evidence(user, receipt_or_order) -> bool
   payment_review_queryset(user)
   ```

2. Vaqtinchalik policy exact: `is_active and is_superuser`; `is_staff` yoki
   codename’ning o‘zi deny. COM-D14dan keyingi assignment modeli COM1.4ada.
3. Mavjud `PaymentReceipt` modeliga stable `cohorts.review_payment` va
   `cohorts.view_payment_evidence` permissionlari migration bilan e’lon
   qilinsin; mavjud ordinary staffga auto-grant qilinmasin. Keyingi `commerce`
   app migrationida bu codenamelar rename qilinmaydi.
4. Receipt list/detail/POST va private file bilan birga backoffice dashboard
   pending rows/count/today-week revenue, navigation badge, student workspace,
   context processor, Django admin/list/inline va bot `/cheklar` ayni policyga
   o‘tsin. Ordinary staffga finance amount/revenue aggregate ham chiqmaydi.
5. `verify_receipt` service boundaryda nonblank reason va receipt image/evidence
   talab qiladi. Failure exception emas: existing typed
   `ReceiptDecision(ok=False, code="evidence_required", ...)`; HTTP/bot adapter
   uni public `EVIDENCE_REQUIRED`ga map qiladi. “Offline cash” override yo‘q.
6. Bot approve/reject callback business mutation qilmasin; authorized userga
   expiring, signed, same-origin web review link bersin yoki factual “webda
   ko‘rib chiqing” javobi. Link hech qachon authorization capability bermaydi;
   web fresh login, named permission va object scope’ni yana tekshiradi.
7. `reject_receipt` hech qachon legacy `.delete()`ga yetib bormasin. U barcha
   adapter uchun typed `rejection_ledger_required` failure qaytaradi, denied
   audit yozadi va row/blobni o‘zgartirmaydi. UI reject tugmasi o‘rniga
   “immutable qaror oqimi tayyorlanmoqda” factual statusi beradi. Immutable
   rejection COM1.2cda qayta yoqiladi.

### Explicit non-goals

- yangi `commerce` app/model;
- refund, order, subscription center;
- evidence retention/purge;
- pricing redesign;
- current receipts backfill;
- production role grant.

### Test nomlari/holatlari

- `test_student_cannot_list_view_file_or_decide_receipt`
- `test_teacher_staff_cannot_list_view_file_or_decide_receipt`
- `test_unprivileged_staff_direct_post_is_denied`
- `test_codename_only_staff_is_denied_until_scope_is_admitted`
- `test_owner_can_review_receipt`
- `test_staff_cannot_see_payment_dashboard_counts_revenue_or_nav_badge`
- `test_staff_cannot_see_student_workspace_receipts_or_admin_inline`
- `test_private_media_uses_same_payment_policy`
- `test_inactive_owner_loses_access_immediately`
- `test_receipt_without_evidence_cannot_be_approved`
- `test_difference_receipt_without_evidence_cannot_be_approved`
- `test_receipt_with_valid_evidence_still_approves_once`
- `test_service_rejects_blank_decision_reason`
- `test_reject_is_blocked_without_deleting_row_or_blob`
- `test_web_and_bot_use_same_policy_result`
- `test_bot_callback_replay_does_not_mutate_payment`
- `test_review_get_is_write_free`
- `test_decision_requires_post_csrf_reason_and_confirmation`

Matrix kamida learner, teacher+staff, ordinary staff, codename-only staff,
superuser/owner va inactive owner fixturelarini qamraydi.

### Verification

```powershell
$env:AZURELMS_SKIP_ENV_FILE='1'
$env:APP_ENV='local'
$env:LOCAL_USE_REMOTE_SERVICES='False'
$env:GEMINI_API_KEY=''
$env:TELEGRAM_BOT_TOKEN=''
.\venv\Scripts\python.exe manage.py check
.\venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\venv\Scripts\python.exe manage.py test cohorts core.test_receipt_decisions core.test_private_media bot.test_checkout_parity --noinput --verbosity 1
.\venv\Scripts\python.exe .tools\docs-sync\verify_docs.py
git diff --check
```

### Tugash mezoni

- ordinary staff list/detail/file/direct POST/bot orqali finance data/actionga
  kira olmaydi;
- owner supported existing evidence receiptni ayni service bilan bir marta
  approve qila oladi; reject esa row/blobni o‘chirmasdan bloklanadi;
- no-evidence normal approval barcha adapterda rad;
- ordinary staff dashboard/count/revenue/nav/workspace/admin orqali finance
  data ko‘rmaydi;
- GET mutation yo‘q; raw error/PII leak yo‘q;
- migration existing userga finance permissionni yashirin bermaydi;
- stage evidence, README/marinebook va rollback note yozilgan.

### Rollback

Emergency fallback ham owner-only qoladi. Permission rowni qoldirish mumkin,
ammo xavfsizlikni zaiflashtirib `is_staff`ga global access, destructive reject
yoki Telegram one-tap mutation qayta yoqilmaydi. Existing receipt va evidence
row/fayllariga destructive amal yo‘q.
