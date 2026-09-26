# I5d — o‘quv yozuvlari va yordam

## Admission — 2026-09-26, runtime tahriridan oldin

**ADMIT — launch-critical.** Frozen V1ning 6 mavjud yuzasi: sertifikatlar
ro‘yxati, learner davomat, obunalar/cheklar, guruh reytingi, bildirishnomalar,
yordam. KPI: haqiqiy scoped ma’lumot va canonical amallar bilan 6 route
ON/OFF, 320–1280 overflow0, regressiya va required CI3/3.

- Canonical: mavjud users view querysetlari, get_cohort_leaderboard_context,
  Enrollment.has_active_access/active_plan, PaymentReceipt snapshot/private
  file/difference-upload, Notification.mark_read/read-all, LegalPage kontenti.
  XP, access, narx, sertifikat berish yoki payment qoidasi nusxalanmaydi.
- Adapter: mustaqil default-OFF frontend_v1_records; shared learner/teacher
  shell, explicit GET filter, read-only projection. Invalid/begona filtr
  canonical fallbackni yashirmaydi; joriy qo‘llangan tanlov ochiq ko‘rsatiladi.
- Bildirishnomalar: stable newest-first, targetni ochish va read POST alohida;
  mavjud legacy GET open/read kontrakti saqlanadi. All-read faqat current
  userning barcha unread yozuvlari, bu scope copyda aniq. No external unsafe
  target. Native POST/CSRF/PRG, offline/duplicate guard; durable receipt yo‘q.
- Mavjud tarif-farqi upload formasi saqlanadi. UI qayta yuborishni avtomatik
  qilmaydi; noma’lum natija sahifani qayta ko‘rish bilan tekshiriladi. File
  draft storage yo‘q. Checkout/receipt dizayni I7, certificate detail/appendix
  hali eski rendererda; bu paket I5ning barcha gate’larini yopmaydi.
- FAQ canonical LegalPage rich content, sanitizer bilan; demo savollar va
  tasdiqlanmagan support javob muddati ko‘chmaydi. Native disclosure.
- Owner haftalik yangi operatsion yuki yo‘q. Rollback flag OFF — eski UI;
  DBdagi read belgisi/fayl/yozuv o‘chmaydi. Model/migration rejalashtirilmagan.
- Verify: offline users/cohorts relevant regressiyasi, full Django/Node,
  disposable browser. AWS, real to‘lov, real upload/Telegram/AI yo‘q.

## Holat

- [x] ~~Runtime, regressiya va lokal browser.~~ `d3aa3dc`.
- [ ] Required CI/review/main.
- [ ] AWS va haqiqiy qurilma qabuli.

Oldingi auth I5b.2 PR133 MERGED 75bba33; CI36208937362 all3PASS:
SQLite2019 skip44, PostgreSQL2019 skip20, Node82; final local2019 skip45.
Dalil: https://github.com/azurebek/azurelms/pull/133#issuecomment-5842048014.

## Tekshirilgan runtime va dalil

`users/frontend_v1_records.py` faqat presentation adapteri. Olti view
canonical queryset/contextini saqlaydi; templates/frontend_v1/records va
records.css/js demo controller yoki fixture ishlatmaydi. Login/CSRF,
private/no-store, teacher shell va flag-OFF eski rendererlar tekshirildi.
Default OFF flag — yangi production release avtomatik yoqilmaydi.

- `/users/notifications/<id>/open/` mavjud GET kontraktiga CSRF POST
  qo‘shildi: faqat o‘z xabari, read belgilab list/page/anchor PRG.
  V1 target-link alohida GET, o‘qilgan deb belgilamaydi. GET legacy
  same-site redirectni saqlaydi, tashqi/executable URL listga qaytadi.
  List barcha statuslar bilan `-created_at,-id`, 20/sahifa; read qilganda
  o‘rnidan ko‘chmaydi. Read-all boshqa pagelardagi unreadlarni ham qamraydi.
- Davomat 1-yanvar / 9999-dekabr prev/next chegaralari va juda katta yil
  fallbacki 500 bermaydi. Canonical kunlik priority/count o‘zgarmadi.
- Sertifikat berish, XP, access, billing model/service o‘zgarmadi.
  Tarif `active_plan()`, receipt historical snapshot va private endpoint;
  chekning pending/verified holati accessdan alohida. Native difference
  upload saqlandi; global upload idempotency claim yo‘q.
- FAQ canonical sanitizer va native details; sozlangan Telegram URL
  HTTP(S) bo‘lsa qoladi, tasdiqlanmagan javob muddati va demo FAQ yo‘q.

Offline env har safar `AZURELMS_SKIP_ENV_FILE=1`, `GEMINI_API_KEY=''`,
`TELEGRAM_BOT_TOKEN=''`; real provider va amaldagi DB ishlatilmadi.

| Command | Natija |
|---|---|
| `venv/Scripts/python.exe manage.py test users.test_frontend_v1_records --noinput --verbosity 1` | 21 OK, final 2.402s |
| `venv/Scripts/python.exe manage.py test users cohorts subscriptions --noinput --verbosity 0` | 508 OK, skipped6, 30.929s |
| `venv/Scripts/python.exe manage.py test --noinput --verbosity 0` | 2040 OK, skipped45, 114.098s |
| `node --test tests/frontend_v1/*.test.mjs` | 87 PASS, 0 fail |
| `manage.py check`; `manage.py makemigrations --check --dry-run`; `git diff --check` | issue0; no changes; PASS |

Full run juda katta integer yil guardidan oldin; undan keyin final focused21
qayta PASS. Boshlang‘ich fixture bitta kursga ikki active enrollment bermadi:
domain himoyasi saqlandi, testning ikkinchi kursi alohida qilindi. Skip
qo‘shilmadi. Final HEAD SQLite/PostgreSQL required CI alohida gate.

IAB8061 temporary DB: ikki kurs/guruh, synthetic certificate/badge,
25 notification, difference receipt va FAQ. Dark6routes×6width
(320/639/640/1023/1024/1280) + light6×2(320/1280): **48 readback overflow0**.
Filtr change faqat pendinghint; Qo‘llash→canonical GET, month→samecohort,
Back→oldfilter; FAQ disclosure; menu Escape→opener focus. Notification
direct-link/read POST alohida, individual→samepage/anchor, page2 read-all
→samepage/disabled/0unread. Console warn/error0; viewport reset.
Screenshot lokal ignored `playground/frontend-v1-smoke/records-mobile.png`.
Browserda real fayl/payment/provider mutationi yo‘q; upload/ownership/CSRF
va existing canonical writer app testlarida. Known-offline/duplicate/draft
guards Node VMda; actual network loss/native iOS/Android qabuli emas.

## Ochiq chegara va keyingi ish

PR134 MERGED `337a73c`; final CI36211060029 all3PASS: SQLite2040 skip44,
PostgreSQL2040 skip20, Node87; final local2040 skip45. Review open finding0.
[Acceptance](https://github.com/azurebek/azurelms/pull/134#issuecomment-5842321154).
AWS deploy va haqiqiy qurilma qabuli **NOT TESTED**. OFF faqat
renderer rollback, read belgisi yoki yuklangan faylni o‘chirmaydi.
Sertifikat detail/appendix legacy; I6 library/editor, I7 checkout/receipt,
I8 exam, I9 Classbook ochiq. Yangi prototiplar hanuz pauzada.
