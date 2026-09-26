# I7 — checkout va chek holati

## Admission — runtime tahriridan oldin

**ADMIT — launch-critical.** Frozen V1 checkout, pending va success
ko‘rinishlarini haqiqiy narx/chek/access bilan ulash. KPI: uch URL oilasi
(latest-success alias bilan), explicit tarif/promo tekshirish, bir marta
chek yaratish, owner qaroridan oldin access bermaslik, 320–1280 responsive
va required SQLite/PostgreSQL/security CI.

- Canonical state: Course/Plan/Cohort/Enrollment/PaymentReceipt va promo
  reservation. `purchase_plans`, `find/resolve_checkout_enrollment`,
  `checkout_period`, `build_promo_quote`, `create_checkout_receipt_with_promo`
  hisoblaydi/yozadi. Tasdiq/rad qarori `receipt_service`da qoladi.
- Adapter faqat renderer va native form orchestration: default-OFF
  `frontend_v1_checkout`, explicit GET quote, CSRF multipart POST → PRG.
  JS summa/access hisoblamaydi; yangi payment engine yoki migration yo‘q.
- User/course/plan/cohort/period/promo/amount-bound 30 daqiqalik signed
  quote; POST canonical Course → Cohort → Enrollment → Plan → Promo
  lock tartibida qayta hisoblab solishtiradi. Eskirgan quote409, transaction
  rollback; yangi enrollment ham qolmaydi. Bu bank transferi yoki global
  idempotency kafolati emas. Pending receipt canonical gate saqlanadi.
- Flag OFF renderer rollback; eski V1 POST yozmaydi, qayta ochish so‘raydi.
  GET hech qanday enrollment/receipt yaratmaydi. Unknown/repeated plan
  parametrlari boshqa tarifga jim almashtirilmaydi.
- Chek yuborish ≠ to‘lov tasdig‘i. Tasdiq ≠ doim hozirgi access: real
  `has_active_access` ko‘rsatiladi. Difference to‘lovi accessni uzaytirmaydi;
  uning uploadi mavjud Obunalar endpointida: V1 image gate + enrollment →
  receipt lock; ikkinchi upload birinchi dalilni almashtirmaydi, owner
  qaroridan keyin yozilmaydi. V1 PRG pendingga qaytadi. Rad etish canonical servisda
  receiptni o‘chiradi: yo‘q ID uchun soxta persistent rejected holat yo‘q.
- Mavjud native form dirty/duplicate/offline controller qayta ishlatiladi.
  Fayl browserda xatodan keyin qayta tanlanadi; localStorage/retry yo‘q.
- Ownerga yangi doimiy monitoring vazifasi yo‘q. AWS, real pul, real karta,
  provider chaqiruvi va frozen prototype tahriri bu ishga kirmaydi.

## Qabul

- [x] ~~Runtime `3621e9c` va backend/browser regression.~~
- [ ] Required CI/review/main.
- [ ] AWS/native-device release (alohida).

## Implementatsiya va dalil

`cohorts/frontend_v1.py` presentation/native form adapteri. Uch URL oilasi
va latest-success alias existing views orqali ishlaydi. Browserda pul hisobi,
yangi provider yoki owner decision writer yo‘q. `cohorts/difference_views.py`
V1da first-file-wins lock va image validator bilan mavjud receiptni yozadi.
Obunalar tarixida flag ON bo‘lsa aniq receipt status havolasi chiqadi.

Offline buyruqlar: `AZURELMS_SKIP_ENV_FILE=1 GEMINI_API_KEY= TELEGRAM_BOT_TOKEN=`.

| Buyruq | Natija |
|---|---|
| `venv/Scripts/python.exe manage.py test cohorts subscriptions users.test_frontend_v1_records --noinput` | 262 OK, skip6 (19.304s); 28 yangi checkout test |
| `venv/Scripts/python.exe manage.py test --noinput` | 2119 OK, skip45 (125.505s) |
| `node --test tests/frontend_v1/*.test.mjs` | 95 PASS; mavjud native library controller qayta ishlatiladi |
| `manage.py check --fail-level WARNING` | 0 issue |
| `manage.py makemigrations --check --dry-run` | no changes |
| `git diff --check` | PASS |

IAB8064 temporary SQLite/private files: login → explicit tarif/promo quote
(tanlashning o‘zi eski hisobni o‘zgartirmadi), noto‘g‘ri promo/bound input,
error focus, Obunalar → aniq chek → refresh; pending/success/difference
missing-file to‘g‘ri ajratildi. To‘rt holat × 320/639/640/1023/1024/1280 =
24 readback, positive overflow0. Dark desktop/mobile screenshot ko‘rildi,
console error/warn0. Browserda upload yoki pul o‘tkazish bo‘lmadi: upload,
owner verify/reject, no-access-until-approval, duplicate/stale/rollback,
private ownership va difference overwrite rad etish Django testlarida.

Chegaralar: real bank transfer, provider/Telegram, native iOS/Android,
haqiqiy network loss va light-theme browser qabuli bajarilmagan. Browser
error headingining oxirgi matn tahriri backend regression bilan tekshirildi;
preview loader eski headingni keshda saqlagan, qolgan readback yuqorida.
Snapshot saved-value confirmation, monotonic revision/ABA kafolati emas.
Rejected receipt canonical servisda o‘chadi: oldingi URL404; yangi rejection
ledger yoki qaytarilgan pul lifecycle bu portga kirmaydi. Legacy difference
endpoint renderer OFF paytda eski xulqini saqlaydi; V1 markerli in-flight
POST rollbackda bloklanadi. Flag OFF saqlangan receipt/accessni bekor qilmaydi.

Keyingi yirik portlar I8 exam/review va I9 Classbook; I5 certificate
detail/appendix legacy. Main/CI va AWS/device release alohida hisoblanadi.
