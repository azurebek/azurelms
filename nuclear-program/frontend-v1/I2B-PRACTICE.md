# I2b — real topshiriq va quizli dars

2026-09-25, `codex/frontend-v1-lesson-practice`.
Admission: **ADMIT — launch-critical**, V1 portning I2 bog‘liqligi.

- Outcome/KPI: o‘quvchi haqiqiy topshiriq/quizni yuborib, reload’dan keyin
  aynan saqlangan ish/natijani ko‘radi; xatoda javobi yo‘qolmaydi.
- Canonical state: AssignmentSubmission / QuizAttempt / QuizAnswer / XP;
  `courses.submission_service` yozadi, web va bot uning iste’molchisi.
- Owner yuki oshmaydi: ustozning mavjud review navbati saqlanadi, yangi
  editor, baholash formulasi, tashqi provider yoki jadval yaratilmaydi.
- `frontend_v1_lesson` default OFF; OFF eski rendererga qaytaradi. Input,
  atomiklik va XP invariant tuzatishlari renderer flagiga bog‘lanmaydi.
- Native CSRF POST → redirect → GET; JS faqat qoralama, dirty guard va
  double-submit yordamchisi. Soxta API/revision/receipt kafolati yo‘q.
- Scope: learner assignment/quiz tabs, real attachment/private URL, review
  holati, tanlangan cohort, empty/error/retry, latest quiz attempt. I3ning
  teacher review UI/ro‘yxatlar/davomati bu paketga kirmaydi.
- Invariantlar: malformed quiz no-write; quiz best-XP farqi parallel
  yozuvda ham ortmaydi; resubmission bahoni tozalasa eski XP ham mos
  qaytariladi; o‘zgarmagan pending ishning takror POSTi no-op. Service
  optional enrollment oladi, uni student/course/faol scope bilan tekshiradi.
- Tekshiruv: flag ON/OFF, CSRF/auth/foreign IDs/locked cohort, form errors,
  file bytes, native/JSON/bot parity, XP/review/resubmit/duplicate/rollback,
  desktop/compact/theme/keyboard va barcha required CI.

I2a oldingi PR #121 (`5528c74`) main’da. CI `36086594312` uchala PASS;
SQLite 1862 OK (skip=40), PostgreSQL 1862 OK (skip=20), Node 13 PASS.
I2b uchun natijalar quyida faqat haqiqiy tekshiruvdan keyin yoziladi.
Staging, haqiqiy telefon, AWS rollout va owner go/no-go **ochiq**.
