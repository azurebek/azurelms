# Backoffice islohoti — o‘quvchiga yordam

2026-10-10. Owner uchinchi bosqichni amalda qurishni topshirdi.
Tayanch: [asosiy reja](BACKOFFICE-REFORM-PLAN.md), main `671cb67`.

## Admission

**ADMIT — launch-critical.** Owner «o‘quvchi darsga kira olmayapti» sababini
qayerdan tekshirishni bilmaydi. KPI: T4 vazifasida to‘g‘ri o‘quvchi/kurs/dars
sababini va vakolatli tuzatish yo‘lini yordamsiz topish. Vaqt hali o‘lchanmagan.

- Yangi o‘qish qatlami: actor doirasidagi o‘quvchi qidiruvi va karta; account,
  enrollment, dars release/ketma-ketlik holatlarini alohida ko‘rsatish.
- Canonical qarorlar existing Enrollment access query/method va
  courses.access_service orqali olinadi. Diagnostika learner view’ni ochmaydi:
  visit/progress/XP, notification yoki boshqa state yozilmaydi.
- Yozish mavjud receipt_service, membership_service, release_service va
  submission_service yuzalarida qoladi. Karta aniq obyektga havola beradi,
  alohida oynadan keyin ayni kurs/darsni qayta tekshiradi. Umumiy access override,
  impersonation, ticket/AI tashxis, yangi payment/grade qoidasi yo‘q.
- Staff faqat teacher_course_queryset doirasidagi enrollmenti bor o‘quvchini
  ko‘radi; owner oddiy learnerlarni, jumladan hali enrollmenti yo‘qlarni topadi.
  Target staff/admin bu o‘quvchi ro‘yxatiga kirmaydi. Boshqa kurslar, chat matni,
  AI tarixi, private receipt bytes yoki yashirin global countlar chiqmaydi.
- Asosiy oqim kurs bo‘yicha eng so‘nggi active enrollmentni (canonical tartib)
  tekshiradi; uning guruhini aniq ko‘rsatadi. Boshqa cohort parametri bo‘lgan
  havola diagnostikasi bu kesimda da’vo qilinmaydi.
- `backoffice_student_support` registr flagi default OFF. OFF yangi yuzani
  yopadi, mavjud o‘quvchi/teacher/qaror yo‘llari qoladi. Yangi schema yo‘q.
- Haftalik ish: bir qidiruv va bir kartadan sabab/amal/readback; yangi doimiy
  operator navbati, provider yoki jadval yo‘q. Owner DB’da sinov yozuvi yo‘q;
  browser dalili alohida synthetic DB’da olinadi. Production deploy yo‘q.

## Tekshiruv chegarasi

Inactive account, pending/expired/frozen/no enrollment, grace boundary, multiple
historical groups, active renewal pending receipt, drip, previous assignment,
no lesson, forged/cross-course IDs, inactive actor, CSRF, flag rollback, scoped
search/pagination va GET zero-write. Resolutionda aniq learner/enrollment/receipt
tekshiriladi; restore seat access ochildi degani emas. Desktop/mobile keyboard
va diagnosis → existing action → recheck haqiqiy synthetic oqimi tekshiriladi.

## Qurilgan oqim

- `O‘quvchilar`: ism, email, username yoki telefon orqali qidiruv; kurs filtri,
  20 kishilik sahifalash va qidiruvga qaytish. Boshqa kurs nomlari ham yashiriladi.
- O‘quvchi kartasi: hisob holati, kurs/dars tanlovi, tekshiruv sababi, aynan qaysi
  guruh tekshirilgani, keyingi qadam va vaqtli `Qayta tekshirish`. A’zolik/tarif
  va kutilayotgan chek tafsilotlari yopiq turadi; kerak bo‘lsa ochiladi.
- Dars yopiq bo‘lsa existing release confirmation; topshiriq kutilsa aniq ish
  review’i; to‘lov kutilsa aniq chek; owner uchun aniq guruh a’zoligi.
  Guruh bo‘yicha amal butun guruhga ta’sir qilishi oldindan yozilgan.
- Scoped handoff GET/POST receipt↔enrollment va enrollment↔cohort parentlarini
  tekshiradi. Chek rad etilgach deleted receipt IDga qaytilmaydi. Qarorlar
  mavjud validation, permission, audit va notification xizmatlaridan o‘tadi.
- Tavsiya faqat tashxis qo‘yilgan a’zolikning chekiga tegishli; boshqa guruh
  cheklari tafsilotlardagi alohida dalil. Tavsiya 20 talik dalil chegarasidan
  mustaqil olinadi. Receipt/member handoff tanlangan darsni course parenti bilan
  tekshiradi va POST redirect/return havolasida saqlaydi; boshqa darsga jim
  qaytib “ochiq” degan xulosa chiqarmaydi. PR177 review’dagi ikki holat shu
  regressiyalar bilan yopildi. Browserda member → ayni dars qaytishi ham tekshirildi.
- GET diagnostika writer emas; cached/stale actor qayta o‘qiladi. Karta/qidiruv
  va focused handoff javoblari `private, no-store`; generic middleware CSRF403
  Django’da qolgan. Course va support flaglari mustaqil rollback qilinadi.

## Tekshiruv dalili

- Review tuzatishlaridan keyin env-file OFF va kalitlar bo‘sh:
  `venv/Scripts/python.exe manage.py test core.test_student_support_service
  core.test_student_support_views core.test_student_support_handoffs --verbosity 1`
  **64/64 PASS**, 5.001s, check0. Kengaytirilgan 1077 app run’da yangi receipt
  regressionining teacher/owner subcaselari URLdagi yangi `lesson`ni kutmagani
  sababli 2 assertion yiqildi; exact URL expectationga lesson qo‘shildi va
  yuqoridagi yakuniy to‘liq support suite o‘tdi. Mavjud mahsulot qoidasi o‘zgarmadi.
- Service: **25 PASS**; root HTTP/privacy/navigation: **14 PASS**; handoff+
  existing receipt/seat: **46 PASS**.
- Env-file OFF, Gemini/Telegram bo‘sh: `venv/Scripts/python.exe manage.py test
  core.test_student_support_service core.test_student_support_views
  core.test_student_support_handoffs core.test_backoffice_workspace
  core.test_feature_flags core.test_receipt_decisions core.test_frontend_v1_review
  core.test_frontend_v1_directory courses.test_lesson_release
  courses.test_assignment_review courses.test_locked_lesson_write_gate
  cohorts.test_seat_release --verbosity 1`: **196 test / 194 PASS / 2 SQLite skip**,
  16.267s. `venv/Scripts/python.exe manage.py test core cohorts subscriptions
  --verbosity 1`: **1069 test / 1034 PASS / 35 environment skip**, 83.429s.
  System check0 va diff-check PASS. Dastlab jamlangan buyruqda ikki mavjud
  bo‘lmagan test modul nomi yozilgani uchun import error bo‘ldi; haqiqiy modul
  nomlari bilan yuqoridagi yakuniy run yashil. Test qoidasi susaytirilmadi.
- IAB, ajratilgan `.tools/backoffice-stage2/demo.sqlite3`: `Madina Karimova`
  synthetic learner → `O‘zingizni tanishtirish` → “Dars guruhga ochilmagan” →
  aniq `Kechki guruh · A1` confirmation → tasdiqlash → kartadagi recheck →
  “Darsga kirish ochiq”. Owner DB va 8088 dizayn prototipi o‘zgarmadi.
- Testlarda pending → real receipt verify → original recheck open va sequence
  → real assignment approve → original recheck open; learner progress yozilmadi.
- Desktop va 320px ro‘yxat/karta/ochilgan tafsilot overflow0; light/dark,
  Enter/Escape menyu va qidiruvga qaytishda `Madina` saqlanishi tekshirildi.
  Captured console error/warn0. Native device yoki owner usability qabuli emas.
- Lokal dalil: `.tools/backoffice-stage2/support-blocked.png` va
  `support-resolved.png` (ignored, faqat synthetic ma’lumot). Demo `8092`.

## Qolgan chegaralar

Accountni faollashtirish writeri, o‘quvchi nomidan kirish, ticket, qurilma/internet
tashxisi, explicit cohort-link diagnostikasi bu kesimga kirmaydi. Amalsiz holatda
kim bilan nimani aniqlashtirish yozilgan. To‘lov muddati kirish yopilgan sana deb
talqin qilinmaydi; grace canonical hisoblanadi. Seat restore faqat EXPIREDga
qaytarishi mumkin — “kirish ochildi” faqat recheck natijasi bilan ko‘rsatiladi.
Muammo sabablari ketma-ket yechiladi: birinchi blocker yo‘qolgach boshqasi chiqishi
mumkin. Yangi renderer default OFF, demo DB’da ON; production deploy qilinmagan.

Holat: runtime kesimi va agent sinovi tayyor. Owner usability, haqiqiy qurilma va
production qabuli ochiq. Keyingi rejalangan kesim: oddiy dizayn boshqaruvi.
