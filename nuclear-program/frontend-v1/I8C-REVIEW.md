# I8c — real ustoz imtihon tekshiruvi

ADMIT — launch-critical. Frozen teacher_exam_review layoutini mavjud
teacher_grade_exam writeriga ulash. KPI: scoped ustoz qoralamani saqlaydi,
alohida tasdiq bilan faqat saqlangan natijani e’lon qiladi; stale sahifa
yangiroq tekshiruvni bosmaydi. Yangi prototype/provider/AWS ishi yo‘q.

- Canonical baho/publication/certificate: teacher_grade_exam va
  ExamAttempt.finalize_review; frontend formulasi yo‘q.
- Mustaqil default-OFF frontend_v1_exam_review; OFF eski renderer,
  in-flight V1 POST fail-closed. Additive review_revision saqlanadi.
- Native CSRF/POST/redirect, alohida save/publish; har safar explicit
  tasdiq. Stale409 current saved state + bound draft, tasdiq tozalanadi.
  Private draft storagega yozilmaydi; dirty/offline/double-submit guard.
- Reviewed attemptni qayta baholash mavjud real capability sifatida
  saqlanadi; yangi qoralama oldingi publicationni almashtirmaydi.
- Owner yuki oshmaydi, navbat/scoped access o‘zgarmaydi.
- Check: focused review/publication + courses/core tests, Node, full
  provider-free suite, migration drift, desktop/mobile browser, CI/review.

## Lokal dalil va chegaralar

- Provider-free `manage.py test core.test_frontend_v1_exam_review courses.test_frontend_v1_exams --noinput`:
  **49 OK skip1 (10.304s)**. Yangi16 test; skip SQLite row-lock yo‘qligi,
  PostgreSQL CI bir snapshotdan parallel POST → 302/409ni tekshiradi.
- `node --test tests/frontend_v1/*.test.mjs`: **110 PASS**. Existing native
  dirty/offline/duplicate guard qayta ishlatildi. Check0, migration drift0.
- IAB8070 synthetic temporary DB: draft5→8.25, stale second-tab409 bilan
  matn qoldi; explicit publish →60.83%. 320/639/640/1023/1024/1280 readback
  positive overflow0; light/dark mobile va desktop ko‘rildi; console0.
  Dastlab viewport boshqa tabga tushgan1280 readbacklar mobil dalil emas;
  keyingi selected peer tab haqiqiy width bilan tekshirildi.
- GET/HEAD section review yaratmaydi; missing review faqat valid save yoki
  canonical finalize ichida yaratiladi. Invalid/stale POST yozmaydi.
- POST review_revision attempt row lock ostida oshadi; legacy draft va
  admin finalize ham hisoblanadi. Direct ORM/bulk yoki alohida admin child
  writerlar uchun global transaction/revision kafolati emas. Snapshot
  rubric/answer/section saved-value o‘zgarishlarini ham tekshiradi.
- Prototip receipt/reconcile mocki ko‘chirilmagan: native PRG tasdiq,
  connection-unknown holatda avtomatik resend yo‘q, yangi GETda saqlangan
  holatni ko‘rish kerak. Private draft faqat DOMda, reloadga persistence yo‘q.
- Full suite va required CI/review/main navbatda. AWS/current DB tegilmadi.
  Native telefon/audio codec va printer acceptance ochiq.
