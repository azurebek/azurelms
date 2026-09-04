# Economic / Standard / Intensive — implementation ledger

Owner admission: 2026-09-04, `writing-block.md` rejasidan keyin «boshla qurishni».
Status: **ADMIT — launch-critical**, birinchi slice **IMPLEMENTED/TESTED — LOCAL REGRESSION GREEN**; required CI/merge dalili [PR #67](https://github.com/azurebek/azurelms/pull/67)da.

## Product contract

Barcha tariflar bir xil core curriculum, material, live dars, assignment,
quiz, exam, certificate va AzureAI oladi. Farq — teacher time va xizmat
intensivligi; Economic sun'iy kontent chekloviga aylanmaydi.

| Code | Boshlang'ich UZS/oy | Guruh default/max | AI 5h / rolling 7 kun |
|---|---:|---:|---:|
| economic | 89000 | 60 | 50000 / 300000 |
| standard | 259000 | 8 | 100000 / 800000 |
| intensive | 399000 | 3 | 200000 / 1500000 |

Narx va AI quota DB/backoffice orqali boshqariladi; kodga narx bo'yicha
ruxsat yozilmaydi. Standard tavsiya etiladi. Teacher Economic talabaga
ixtiyoriy individual yordam berishi mumkin: premium capability yordamni
taqiqlash emas, kafolatlangan xizmat darajasi.

## Ketma-ketlik va scope

1. **IMPLEMENTED/TESTED — payment foundation (ushbu PR).** `Enrollment.plan` faol
   tarif; `pending_plan` faqat niyat. Chekda tanlangan plan va narx/davr
   snapshoti. Tasdiqlashgina faol tarifni o'zgartiradi; rad etish niyatni
   tozalaydi. Web/Telegram bir canonical yozuv yo'lidan foydalanadi.
   Eski tasdiqlangan cheklarga hozirgi enrollmentdan tarix to'qilmaydi;
   legacy metadata yo'qligi ochiq ko'rsatiladi.
2. **PLANNED — catalog + delivery.** Yangi uch plan/policy, sotuv availability,
   eski planlarni tarix uchun saqlash; cohort tier/capacity va mos enrollment.
   Sotuvga ochishdan oldin oxirgi joy contention testi. Pending joy bandi
   muddati, bir nechta kursdagi AI allowance va eski o'quvchilarni ko'chirish
   alohida product qarorlari sifatida aniqlashtiriladi.
3. **PLANNED — service workflows.** Standard individual feedback;
   Intensive personal assignment, progress review, priority queue. Marketing
   hali ishlamaydigan xizmatni va'da qilmaydi. Mavjud core ruxsatlar saqlanadi.
4. **PLANNED — presentation + analytics.** Pricing, checkout, dashboard,
   backoffice; occupancy/revenue/usage/review workload/renewal metrikalari.

## Birinchi slice admission

- Outcome: to'lamagan tarif yangi AI quota yoki huquq bermaydi; operator
  chekdagi aynan qaysi tarif uchun pul kelganini biladi.
- KPI: unpaid plan-change sababli entitlement/AI-limit oshishi **0**.
- Canonical state: `Enrollment.plan/pending_plan`, `PaymentReceipt`; canonical
  yozuvlar `cohorts.checkout_service`, `subscriptions.promo_service`,
  `cohorts.receipt_service` va modelning invariant guardlari.
- Adapterlar: web checkout, Telegram checkout, web/bot receipt review,
  payment-history UI. Provider chaqiruvi yo'q.
- Owner workload: mavjud tasdiqlash oqimi saqlanadi, qo'shimcha qo'lda hisob yo'q.
- Rollback: yangi kod sotuv matritsasi/quotalarni yoqmaydi. Additive schema;
  code rollbackdan oldin pending cheklar va yangi snapshotlar saqlanadi,
  migrationni ortga yugurtirib tarix ustunlari o'chirilmaydi.
- Verification: unpaid/failed/rejected/approved/repeated/stale/concurrent
  qarorlar; snapshot rename/price/plan-change'dan mustaqil; web/bot parity;
  legacy migration; SQLite va required PostgreSQL CI; UI render/browser.

## Ochiq chegaralar

Ushbu slice yangi delivery formatini sotuvga chiqarmaydi, eski faol
enrollment tarifini migratsiya bilan almashtirmaydi, proration yoki
guruhlararo avtomatik upgrade/downgrade qilmaydi. Ular keyingi slice'lar.

## Birinchi slice dalili — 2026-09-04

Barcha testlar `AZURELMS_SKIP_ENV_FILE=1 GEMINI_API_KEY= TELEGRAM_BOT_TOKEN=`
bilan, haqiqiy provider chaqiruvisiz yugurdi.

- `python manage.py test --noinput`: **1068 test, OK, skipped=26**.
- `AZURELMS_TEST_FILE_DB=1 python manage.py test cohorts.test_payment_plan_integrity cohorts.test_payment_plan_migration --noinput`: **22/22 OK**, jumladan parallel approve/approve va approve/reject.
- Shu buyruqqa `cohorts.test_single_pending_receipt` qo'shib qayta yugurish:
  **28/28 OK**, parallel chek yaratish ham tekshirildi.
- `python manage.py check --fail-level WARNING`: 0 issue;
  `python manage.py makemigrations --check --dry-run`: drift yo'q.
- Nazorat yugurishi: eski `Enrollment.plan`ga niyat yozish qaytarilganda
  2/2 test yiqildi; tarix uchun jonli enrollment nomi qaytarilganda 2/2
  test yiqildi. Monkeypatch faqat test processida, fayllar o'zgarmadi.
- Brauzer: izolyatsiyalangan in-memory DB va test akkauntlari bilan
  pending sahifa, owner receipt ro'yxati va approve amali tekshirildi.
  Sotib olinayotgan tarif ko'rindi, tasdiqlash muvaffaqiyatli o'tdi.
  Real to'lov/student yozuvlariga tegilmadi; mobile sign-off bu dalil emas.

`cohorts.0016` additive migration: ochiq niyat va pending invoice planini
legacy belgisi bilan saqlaydi; eski tasdiqlangan cheklarga nom/narx taxmin
qilib yozmaydi. Eski kod oldin faol tarifni almashtirib ulgurgan bo'lsa,
avvalgi haqiqiy tarifni dalilsiz tiklamaydi. Deployda avval DB backup,
keyin migration; tarix ustunlarini reverse migration bilan o'chirmaslik kerak.

Local migration bajarildi: `python manage.py backup_db` integrity-ok nusxa
yozdi, `python manage.py migrate cohorts 0016 --noinput` o'tdi. Read-only
SQLite solishtirishda 125 jadvaldagi avvalgi ustun qiymatlari saqlandi
(kutilgan checkout timestamp cleanup va migration ledgeridan tashqari).
Backup repoga commit qilinmagan; local fayl:
`backups/db-20260904-052621.sqlite3`.
