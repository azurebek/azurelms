# Economic / Standard / Intensive — implementation ledger

Owner admission: 2026-09-04, `writing-block.md` rejasidan keyin «boshla qurishni».
Status: **ADMIT — launch-critical**. Payment foundation va keyingi tuzatishlar
main'da (#67–69). Catalog + delivery **IMPLEMENTED/TESTED — LOCAL REGRESSION
GREEN** (`b5c2068`); required CI/merge dalili [PR #70](https://github.com/azurebek/azurelms/pull/70)da.

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
2. **IMPLEMENTED/TESTED — catalog + delivery.** Yangi uch plan/policy, sotuv availability,
   eski planlarni tarix uchun saqlash; cohort tier/capacity va mos enrollment.
   Sotuvga ochishdan oldin oxirgi joy contention testi. Owner qarorlari va
   eski o'quvchilar uchun rollout chegarasi quyidagi admissionda.
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

Birinchi slice yangi delivery formatini sotuvga chiqarmaydi, eski faol
enrollment tarifini migratsiya bilan almashtirmaydi, proration yoki
guruhlararo avtomatik upgrade/downgrade qilmaydi. Ular keyingi slice'lar.

## Catalog + delivery admission — 2026-09-04

**ADMIT — launch-critical.** Owner «davom et reja bo'yicha»; ikki aniq javob:
joy **faqat to'lov tasdiqlanganda** band; ko'p kursli AI allowance esa
**hozirgidek eng oxirgi faol enrollment** tarifidan, yig'indi/max emas.

- Outcome/KPI: sotilgan guruh sig'imidan ortiq tasdiqlangan a'zolik **0**;
  paketga mos bo'lmagan guruhga xarid **0**.
- Canonical state: Plan catalog/availability, AIPlanPolicy, Cohort plan/capacity,
  Enrollment status. Policy/locklar domain serviceda; web/bot bir xil ishlatadi.
- Checkoutni ochish va chek yuborish joyni band qilmaydi. Tasdiqlashda qayta
  tekshiriladi; joy qolmasa chek pending qoladi, pul/huquq o'zgarmaydi,
  owner boshqa guruh yoki qaytarish masalasini qo'lda hal qiladi.
- Tasdiqlangan enrollment active/expired holatda guruh a'zosi hisoblanadi:
  obuna muddati tugashi pedagogik guruhdan avtomatik chiqarish emas.
  Frozen a'zolik joyni bo'shatadi; qayta ochishda sig'im qayta tekshiriladi.
- Adapterlar: pricing, web/bot checkout, receipt review, transfer/promotion,
  owner catalog/delivery backoffice. AI tanlash algoritmi o'zgarmaydi.
- Owner yuki: narx/sotuv/guruh sozlamasi bitta backofficeda; faqat oxirgi
  joyga parallel chek kelsa mavjud qo'lda ko'rib chiqish oqimi ishlaydi.
- Rollout/rollback: yangi uch paket draft (sotuv yopiq), faqat ishlayotgan
  core imkoniyatlar matni; eski plan/cohort/enrollmentlar o'zgarishsiz.
  Tier belgilanmagan legacy guruh legacy xaridni davom ettiradi, yangi
  paket unga sotilmaydi. Archive eski access/quota/tarixni o'chirmaydi.
  Rollbackda yangi sotuvni yoping; additive ustun/tarixni reverse qilmang.
- Verification: availability web/bot parity; capacity/tier validation;
  pending joy olmaydi; so'nggi joyga parallel approval; archived renewal
  chegarasi; eski tarix va effective-date/delayed-approval regressiyalari;
  migration preservation, SQLite va PostgreSQL CI, backoffice browser QA.
- Scope tashqarisi: avtomatik tier upgrade/ko'chirish, premium workflow,
  proration, kundalik subscription job refaktori, analytics va to'liq marketing.

### Catalog + delivery dalili — 2026-09-04

- Commit `b5c2068`: yangi uch paket + AI policy **draft**, stable code va
  guruh maksimumi; `is_available_for_purchase` archive, legacy paid renewal
  istisnosi. Narx/marketing/sotuv holati owner-only auditli backofficeda.
- `Cohort.plan/capacity` additive; eski guruhlar null/null holda qoladi.
  Default guruh course+plan scope'da. Course → cohort → enrollment →
  plan/receipt lock tartibi, tartiblangan ko'p-guruh transfer qulflari.
  Sig'im statusdan hisoblanadi: active/expired band, pending/frozen band emas.
- `/backoffice/catalog/`: narx/sotuv/marketing, cohort yaratish va tahrir;
  AI limitlari mavjud `/backoffice/ai-control/` orqali. O'qituvchi course'dan.
  Faol mos guruhsiz delivery tarifini backoffice sotuvga ochmaydi.
- Review tuzatishi `916de52`: to'lgan/yopilgan guruhdagi to'lanmagan intent
  uchun GET mos bo'sh guruhni faqat ko'rsatadi; POST/bot course lock ostida
  `relocate_pending_checkout` orqali eski yozuvni muzlatib, yangi pending
  va transition/audit yaratadi. Qarori kutilayotgan chek ko'chirilmaydi;
  rad etilgach qayta checkout mumkin. Paid membership/tier o'zgarmaydi.
- `python manage.py test --noinput`: **1123 OK, skipped=29**.
  `AZURELMS_TEST_FILE_DB=1 python manage.py test cohorts.test_delivery_catalog
  cohorts.test_payment_plan_integrity cohorts.test_single_pending_receipt
  subscriptions.test_catalog --noinput`: **67/67 OK** (review/handoffdan keyingi head).
  Required PostgreSQL CI alohida gate.
- Ikki nazorat yugurishi: `validate_seat` yo'q qilinganda oxirgi joy testi
  **1/1 yiqildi**; tier mosligi guardi yo'q qilinganda legacy guruhga noto'g'ri
  xarid testi **1/1 yiqildi**. Faqat test process monkeypatchi.
- Eski checkout tanlash funksiyasi test processida qaytarilganda yangi bot
  retry regression testi **1/1 yiqildi** (`cohort_full`); tuzatilgani yashil.
  Web retry/approval, bot takrorlash, GET no-write, pending invoice immutability,
  audit rollback va yopiq guruhning same-tier fallback'i qamralgan.
- Handoff required CI eski approve/reject race assertionini topdi: kelasi
  davr uchun approval bugunoq plan almashishini kutgan, #68ga zid. Eski
  assertion `d4099ac`da ham bor. Approve-first nazorat **1/2 yiqildi**,
  reject-first o'tdi; runtime o'zgartirilmay test effective-date contractiga
  moslandi va ikkala winnerga deterministik coverage qo'shildi. Asl unordered
  race ham saqlangan; invoice/deadline/AI quota/audit/notification tekshiriladi.
- `check --fail-level WARNING`: 0 issue; `makemigrations --check --dry-run`:
  drift yo'q; `scan_secrets`: toza. Barcha testlar env faylsiz va provider keys bo'sh.
- Brauzer: haqiqiy DB'dan ajratilgan in-memory QA, test owner/student.
  Narxni saqlash; Standard sig'imi 9 rad etilishi, 7 saqlanishi; 390px
  katalog; 390px checkout Economic → Standard; 1280px dark checkout →
  Intensive. Tarif/guruh/summa birga o'zgardi, horizontal overflow yo'q,
  checkout konsolida JS error yo'q. Topilgan head-script timing xatosi
  `defer` asset bilan tuzatilib qayta real bosish orqali tekshirildi.
- QA server/tab yopildi. Bu real Android/iOS, mikrofon, Telegram yoki
  haqiqiy bank to'lovining sign-off'i emas.

**Rollout hali yopiq:** eski Starter/Pro/Premium o'chirilmagan/arxivlanmagan,
eski a'zolar avtomatik yangi paketga o'tmagan. Owner avval mos yangi guruhni
yaratadi; premium workflow va copy release gate'idan keyin sotuvni ochib,
eski tariflarni yangi sotuvdan yopadi. Mavjud paid a'zolar arxiv tarifini
yangilashi mumkin, yangi o'quvchi arxiv tarifni sotib ololmaydi. Migration
oldindan shu kodli owner planini topsa nom/narx/policy'ni qayta yozmaydi:
bunday collision alohida owner rollout qarorini talab qiladi.

**Keyingi slice:** Standard feedback, Intensive personal assignment/progress
review/priority; keyin pricing/dashboard/analytics. Course detail'dagi eski
«Cheksiz AI repetitor» va «umrbod kirish» copy'si presentation bosqichida
to'lov/quota contractiga moslanishi kerak; yangi seed bunday claim yozmaydi.

Local migration ham bajarildi: `python manage.py backup_db` →
`python manage.py migrate cohorts 0017 --noinput` → `check --fail-level WARNING`.
Backup `backups/db-20260904-070703.sqlite3`, 1.9 MB, integrity ok (gitga kirmaydi).
Read-only SQLite solishtirishda 125 jadvalning barcha oldingi ustun/yozuvlari
saqlandi (migration ledgeridan tashqari): yo'qolgan/o'zgargan eski qator **0**.
Yangi uch paket sotuvga yopiq, eski cohortlar null/null. Haqiqiy learner,
guruh yoki payment holati o'zgartirilmadi.

## Birinchi slice dalili — 2026-09-04

Barcha testlar `AZURELMS_SKIP_ENV_FILE=1 GEMINI_API_KEY= TELEGRAM_BOT_TOKEN=`
bilan, haqiqiy provider chaqiruvisiz yugurdi.

- `python manage.py test --noinput`: **1070 test, OK, skipped=26** (legacy admin review tuzatishi bilan).
- `AZURELMS_TEST_FILE_DB=1 python manage.py test cohorts.test_payment_plan_integrity cohorts.test_payment_plan_migration --noinput`: **22/22 OK**, jumladan parallel approve/approve va approve/reject.
- Shu buyruqqa `cohorts.test_single_pending_receipt` qo'shib qayta yugurish:
  **28/28 OK**, parallel chek yaratish ham tekshirildi.
- Legacy admin review tuzatishidan keyin shu uch modul: **30/30 OK**.
  Invoice inline formasi billing maydonlarini tahrirlashga taklif qilmaydi;
  crafted POST ham ularni o'zgartirmaydi. Standalone changelistdan auditni
  chetlab o'tadigan verification checkboxi olib tashlandi.
- `7c7fff3` uchun required CI uchalasi yashil: PostgreSQL full suite
  **1070 test OK (skipped=20)**. Eng so'nggi head holati PR checklarida.
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

**Alohida, pre-existing Windows test qarzi:** butun suite'ni faylli SQLite
bilan birga yuritish `core.test_backup_restore` restore testida ochiq WAL
handle (`WinError 32`) va keyingi test-DB corruptionga olib keladi. O'zgarishdan
oldingi `f4e348b`ning alohida temp nusxasida ham aynan shu test yiqildi
(`--keepdb --failfast`: 954 yugurdi, 2 error). Backup/restore moduli yakka
holda 15/15 OK; billing focused file suite 30/30 OK. Bu PR backup/restore
kodini o'zgartirmaydi va full file-suite green deb da'vo qilmaydi. Real DB
hamda zaxira `integrity_check=ok`; ochiq connectionlar bilan live restore
qilish xavfsiz deb hisoblanmasin — alohida lifecycle tuzatishi kerak.

## Birinchi slice'dan keyingi tuzatish — 2026-09-04 [Claude]

Poydevor tekshirilganda bitta xulq nuqsoni topildi va tuzatildi: tarif
tasdiqlash paytida emas, **o'zi to'langan davr boshlanganda** kuchga kiradi.

Sabab: yangilash to'lovi joriy muddat tugaganidan boshlanadi, lekin
`PaymentReceipt.save()` faol tarifni darhol almashtirardi. Muddatiga 10 kun
qolgan o'quvchi 30 kunlik pulga 40 kunlik qimmat tarif olardi (arzonga
o'tishda esa to'langan kunlarini yo'qotardi). Bu slice'ning o'z KPI'siga zid:
to'lanmagan kun uchun huquq va AI kvotasi oshmasligi kerak.

Tuzatish schema o'zgartirmaydi:

* `PaymentReceipt.plan_takes_effect_now()` — davri boshlanmagan chek
  `Enrollment.plan`ga tegmaydi;
* `Enrollment.active_plan()` — haqiqat tasdiqlangan chekning davrida, ya'ni
  tarif o'z kunida cronsiz kuchga kiradi;
* `cohorts.enrollment_service.promote_due_plans()` — kunlik obuna buyrug'i
  denormalizatsiyalangan ustunni ko'chiradi (backoffice ro'yxatlari va
  `aicontrol` plan-scope reset uni to'g'ridan-to'g'ri o'qiydi);
* huquq, AI limiti va o'quvchiga ko'rsatiladigan tarif `active_plan()`dan
  o'qiydi.

To'lovning o'zi kutmaydi: status va `next_payment_deadline` tasdiqlash
paytida darhol uzayadi.

Dalil: `python manage.py test --noinput` **1079 OK (skipped=26)**;
`cohorts/test_plan_effective_date.py` 9 test; nazorat yugurishi ikki qism
uchun alohida (5/9 va 2/9 yiqildi, tiklangach yashil).

**Owner qarori ochiq:** agar qimmatroq tarifga o'tish darhol ishlashi kerak
bo'lsa, davr ham o'sha kundan boshlanishi yoki farq hisoblanishi kerak
(proration). Hozirgi tanlov — "to'langan kun = olingan kun".

## Ikkinchi tuzatish — 2026-09-04 [Claude]

Birinchi tuzatishning ko'zgudagi aksi: tizim to'lanmagan kunlarni berardi,
shu bilan birga **to'langan kunlarni olib qolardi**.

To'lov davri chek yuborilgan kuni hisoblanadi, tasdiqlash esa qo'lda. Kirishi
yopiq turgan o'quvchi (birinchi xarid yoki muddati o'tgan obuna) tasdiqlash
kutilgan kunlarni yo'qotardi — o'lchovda 3 kun kutish 30 kunlik pulga 27 kun
berdi. Endi bunday holatda davr uzunligi kirish ochilgan kundan sanaladi
(`PaymentReceipt.granted_deadline()`). Kirishi ochiq turgan o'quvchiga
qo'shimcha kun berilmaydi.

Dalil: `python manage.py test --noinput` **1085 OK (skipped=26)**;
`cohorts/test_approval_delay.py` 6 test; nazorat yugurishi 2/6 yiqildi.
Schema o'zgarmadi.
