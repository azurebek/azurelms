# Sertifikat hujjati va ballar ilovasi — V1

ADMIT — launch-critical: qolgan ikki frozen read-only hujjatni ko‘chirish.
KPI: berilgan real sertifikat/ilovani telefonda o‘qish va explicit native
print; GET baho yoki sertifikat yaratmaydi. Canonical Certificate va
learner_result publication projection saqlanadi, yangi formula yo‘q.

Mavjud real policy o‘zgarmaydi: exact IDli detail/appendix PUBLIC; private
learner shellga yashirilmaydi. Jamoat hujjati uchun mavjud V1 foundation
va frozen certificate layout; ortiqcha shaxsiy ma’lumot yoki draft yo‘q.
Public/private product qarori bu portda yangilanmaydi. Yangi imzo, QR,
rasmiy akkreditatsiya claimi yoki avtomatik PDF servisi qo‘shilmaydi.

Mustaqil default-OFF frontend_v1_certificates; OFF legacy rendererlarga
qaytaradi. Migration/provider/AWS yo‘q. ?download=1 V1da auto-print qilmaydi;
faqat user tugmasi. Print muvaffaqiyati/saving OSga bog‘liq, UI taxmin qilmaydi.
Owner yuki oshmaydi; regression, browser va CI orqali qabul qilinadi.

## Dalil

- Runtime `66f671c`; 7 yangi Django +1 Node testi. Combined provider-free
  `manage.py test courses.test_frontend_v1_certificates core.test_frontend_v1_exam_review courses.test_frontend_v1_exams --noinput`:
  **57 OK skip1 (9.195s)**. Node111 PASS, check0/drift0/diff clean.
- Historical testning initial fixtureida is_completed yetishmagan; canonical
  learner_result bunday attemptni natija deb bermaydi. Fixture tuzatildi,
  policy/assertion susaytirilmadi. Pending/draft/foreign privacy saqlandi.
- IAB8071 disposable DB, anonymous exact-ID detail→appendix, ikki sahifa ×
  320/639/640/1023/1024/1280 =12 readback, positive overflow0. Dark desktop,
  light mobile ko‘rildi, console0; viewport reset. Real printer/OS PDF/native
  telefon NOT TESTED. Print user-click trigger Node testda tekshirildi.
- PR141 tarkibida I8c bilan navbatdagi real-port paketi. Fresh full/CI/review
  gate ochiq; AWS/current DB o‘zgarmadi. Qolgan port yo‘nalishi I9 Classbook.
- Combined local full2263 OK skip54 (220.319s), Node111, CI36258423702
  all3PASS. I8c missing-section follow-up bilan focused59 OK skip1;
  [PR141](https://github.com/azurebek/azurelms/pull/141) final headning CI/main
  statusi uchun authoritative havola. Native printer va AWS gate alohida.
