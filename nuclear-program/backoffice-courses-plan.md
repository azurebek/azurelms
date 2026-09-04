# Backoffice kurslar ro'yxati

Owner admission: 2026-09-05 — mavjud kurslar sonini ko'rish va ularni tahrirlashga kirish hozir backoffice'da yo'q.

## Feature admission

1. **Outcome / workload:** owner mavjud kursni topish uchun URL yoki Django adminni bilmasligi kerak; barcha kurslar bitta backoffice yuzasida ko'rinadi.
2. **Asosiy KPI:** owner scope'idagi har bir kurs ro'yxatdan ko'pi bilan bitta bosishda muharrirga ochiladi va ko'rsatilgan jami son scope bilan teng bo'ladi.
3. **Canonical state:** yangi state yo'q. `courses.Course` va mavjud `backoffice_course_editor` yagona yozish yo'li bo'lib qoladi; yangi sahifa read-only ro'yxatdir.
4. **Adapterlar:** faqat Django backoffice view/template'i mavjud model va access policy'ni o'qiydi.
5. **Owner yuki:** kamayadi — kursni qidirish, sonini bilish va tahrirlash uchun alohida admin/URL kerak bo'lmaydi.
6. **Failure / rollback:** ro'yxat ishlamasa mavjud create/edit URL'lari saqlanadi; route, sidebar link va template'ni qaytarish kifoya. Data migration yo'q.
7. **Qaror:** **ADMIT — launch-critical**. Kontentni solo-owner boshqarish oqimining yetishmayotgan read/navigation qismi.

## Slice

- scope-aware kurslar ro'yxati, jami/faol/qoralama/dars ko'rsatkichlari;
- nom yoki o'qituvchi bo'yicha qidiruv va holat filtri;
- har bir kursdan mavjud muharrirga kirish;
- sidebar'da `Kurslar` va son badge'i, yangi kurs esa ro'yxat ichidagi aniq amal;
- permission, filter va regression testlari; desktop hamda tor ekran browser QA.
