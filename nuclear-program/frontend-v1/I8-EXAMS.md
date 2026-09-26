# I8 — imtihonlar va ustoz tekshiruvi

## Admission — runtime tahriridan oldin

**ADMIT — launch-critical.** Frozen V1 imtihonlar markazi va keyingi
natija/urinish/review yuzalarini canonical Django holatiga ulash. KPI:
o‘quvchi o‘z faol kursining aynan o‘z urinishini topadi; ko‘rish yangi
urinish yaratmaydi; 320–1280 pxda asosiy amal yo‘qolmaydi.

- Birinchi mustaqil bo‘lak **I8a: imtihonlar markazi va natija** (`exam_center`, `exam_result`).
  `ExamCenterView`, `enrollment_active_access_q` va mavjud latest-attempt
  projectioni haqiqat manbasi. V1 faqat render qiladi; baho, attempt,
  timer, enrollment, review yoki sertifikat yozmaydi. JS hisoblash yo‘q.
- Default-OFF `frontend_v1_exams` hozir faqat shu read-only yuzalarni
  tanlaydi. OFF eski renderer/navga qaytaradi, ma’lumotni o‘zgartirmaydi.
  Detail/review hali eski renderer: urinish havolasida bu ochiq aytiladi.
- Mavjud layout/tokenlar, 640/1024 breakpointlar va umumiy theme/nav.
  Boshlanmagan/jarayonda/kutilmoqda/tasdiqlangan/limit/empty holatlari;
  qoralama ball markazda mavjud canonical qoidadek ko‘rsatilmaydi.
- Ownerning haftalik operatsion yuki oshmaydi. Yangi operatsion sozlama,
  provider chaqiruvi, AWS o‘zgarishi yoki yangi prototype yo‘q.
- **Owner 2026-09-26:** “Ha, faqat tasdiqlangan natija ko‘rinsin”.
  Canonical `ExamAttempt.finalize_review` ball bilan bir transactionda
  `ExamResultPublication`ga oxirgi tasdiqlangan section/answer feedback,
  notes va ball nusxasini yozadi. Oddiy draft save bu nusxani o‘zgartirmaydi;
  qayta tasdiqlash uni yangilaydi. Bitta canonical projection V1, legacy
  result va public certificate appendixda ishlaydi; flag OFF privacy
  himoyasini bekor qilmaydi. Bu to‘liq revision/history yoki certificate
  qayta berish siyosati emas. Eski approved urinishlarda tasdiqlangan
  nusxasi yo‘q tafsilotlar taxminan backfill qilinmaydi; oldingi umumiy
  ball saqlanadi, tafsilotlar qayta tasdiqlanganda paydo bo‘ladi.
  Additive migration: yangi publication jadvali, data-loss/backfill yo‘q.
  Persistent form revision, audio qurilma, timer/submit acceptance I8b/cda ochiq.

## Qabul

- [ ] I8a runtime va regressiya.
- [ ] I8a mobile/desktop browser.
- [ ] Required CI/review/main.
- [ ] I8b/c: attempt/audio/timer, result/publication va teacher review.
- [ ] AWS/native-device release.

Sinov: isolated provider-free `manage.py test courses`, yangi focused
tests, full suite, Node suite, check/migration drift/diff; browserda
list → aniq pending/reviewed result yoki instructions → Back, mobil drawer,
theme va empty/long-content. Ko‘rinish porti butun I8 tayyor degani emas.
