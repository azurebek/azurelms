# BACKOFFICE-02 / B2.4 — o‘quvchi natijalari va bildirishnomalarni tekshirish

Sana: 2026-10-13. Tayanch: `79c5f37` (B2.3). Owner topshirig‘i:
topshiriq/natija va yetib bormagan bildirishnomalarni oson tekshirish oqimi.
Admission: [yagona reja §11](BACKOFFICE-REFORM-PLAN.md#backoffice-02).
Holat: lokal oqim qurildi va tekshirildi; owner qabuli alohida.

## Natija

- O‘quvchi kartasida **Darsga kirish**, **Topshiriq va natijalar**, owner
  uchun **Bildirishnomalar**. Har safar bitta yordam mavzusi ko‘rsatiladi.
- Natijalarda **Topshiriqlar**, **Dars testlari**, **Imtihonlar** alohida
  tanlanadi; har tur 6 tadan sahifalanadi. Kurs/dars tanlovi, ro‘yxatdagi
  qidiruv va oldingi yagona qidiruvga qaytish havolasi saqlanadi.
- Topshiriq yuborilmagan, tekshiruv kutilmoqda, tasdiqlangan yoki qayta
  ishlash kerak holatlari farqlanadi. Testda oxirgi va oldingi urinish;
  imtihonda davom etayotgan urinish, tekshiruv va o‘quvchiga ochilgan
  tasdiqlangan natija ajratiladi.
- Bildirishnomalar 10 tadan: **Hammasi** yoki **Yuborish to‘xtagan** filtri.
  Eski xatoli xabar yangi muvaffaqiyatli xabarlar ortida qolib ketmaydi.
  Saytdagi qayd/o‘qilgan belgisi Telegramga yuborish holatidan alohida.
- Mavjud tekshirish sahifasiga ayni ish yoki xabar bilan o‘tiladi.
  Qarordan keyin shu o‘quvchi va tekshiruvga qaytiladi; “Qayta tekshirish”
  holatni yangidan o‘qiydi. Oxirgi ish orqali mavzu, tur, filtr va sahifa tiklanadi.

## Shartnoma

Yangi URL oilasi yo‘q. Mavjud
`/backoffice/workspace/students/<student>/` GET sahifasida `topic=access|results|delivery`,
`result_kind=assignments|quizzes|exams`, `delivery_filter=all|failed` va
sahifa parametrlari ishlatiladi. `core/student_support_views.py` fresh active
staff/owner va mavjud support flagini tekshiradi; javoblar private/no-store.
Takrorlangan yoki yaroqsiz tanlovlar rad etiladi. Ko‘rish baho, progress,
attempt, notification read yoki Telegram navbatini o‘zgartirmaydi.

`core/student_support_results.py` canonical staff/student/course scope’ini
yangidan o‘qiydi. Assignment va oddiy quiz tanlangan darsga, exam tarixi
kursga tegishli. Exam va lesson ota bog‘lanishi bir vaqtda bor buzilgan quiz
natijasi bu oddiy test ro‘yxatiga kirmaydi. Submissionning matni, fayli,
ustoz izohi va draft exam feedback support kartasiga chiqarilmaydi.
Exam bali `courses.exam_publication.learner_result` orqali olinadi;
qoralama raqami yakuniy baho emas. Oldingi tasdiqlangan urinish yangi urinish
o‘rniga joriy natija deb ko‘rsatilmaydi. Publicationdan oldingi eski
tasdiqlangan aggregate alohida “Eski natija” izohi bilan chiqadi.

`core/student_support_delivery.py` faqat fresh owner va aniq nonstaff
o‘quvchi uchun. `Notification`da course FK yo‘q, shuning uchun ro‘yxat
**butun hisob bo‘yicha**; xabar URLi yoki external key orqali soxta kurs
scope’i chiqarilmaydi. Umumiy hisoblar account-wide, sahifalash filtri
esa faqat tanlangan holatga tegishli. Tana, provider error, Telegram ID,
stored URL va claim token kartaga chiqmaydi.

Outbox yo‘qligi “yuborish muvaffaqiyatsiz” degani emas: navbat yaratilmaganining
tarixiy sababi modelda yo‘q. Joriy Telegram bog‘lanishi shu tarixni isbotlamaydi.
`pending`, `sending`, `sent`, `failed` yozuvlari alohida; global pauza va
canonical reminder quiet hours navbatning joriy kutish sababi sifatida
tushuntiriladi. Xabarni o‘qilgan yoki tarixan “bekor qilingan” deb taxmin qilish
yo‘q. Yuborish manzili joriy bog‘langan hisobdan farq qilsa, IDni chiqarmasdan
ogohlantiradi. “Telegramga yuborilgan” o‘qilganlik dalili emas.

`core/student_support_return.py` cheklangan parametrlarni imzolab,
actor/session hamda haqiqiy student/course bilan bog‘laydi. Grading/replay
sahifasi o‘z obyektini odatdagi ruxsat bilan yuklagach qaytishni tekshiradi.
Token yozish ruxsatini bermaydi. Course/lesson/topic/result kind/delivery
filter/pagination va mavjud upstream search token qaytishda saqlanadi.
Recent’da esa faqat ID/enum/sahifa; qidiruv matni va token saqlanmaydi.

Assignment va exam qarorlari mavjud teacher review oqimida qoladi.
`frontend_v1_exam_review` OFF bo‘lsa exam amali ko‘rsatilmaydi; avval ochilgan
support havolasi eski GET initializerga tushmay, kartaga qaytadi yoki rad etiladi.
Telegram amali `/backoffice/control/dead-letter/?student=S&notification=N`
bilan ayni qabul qiluvchi/xabarga chegaralanadi. Shu filtrda guruh xabarlari
yo‘q; forma boshqa yozuvni POST qilishni qabul qilmaydi. Mavjud sabab,
tasdiq, permanent holat uchun qo‘shimcha tasdiq, replay va atomik audit saqlanadi.
Replay xabarni navbatga qaytaradi; shu HTTP so‘rovda Telegramga yubormaydi.

## Tekshiruv dalili

Muhit: env-file OFF, `APP_ENV=local`, remote services OFF,
`GEMINI_API_KEY` va `TELEGRAM_BOT_TOKEN` bo‘sh.

- `venv/Scripts/python.exe manage.py test core.test_student_support_results
  --verbosity 1`: **18/18 PASS**.
- `venv/Scripts/python.exe manage.py test core.test_student_support_delivery
  core.test_student_support_evidence_views --verbosity 1`: **39/39 PASS**,
  8.681s. Fresh ruxsat, maxfiy ma’lumot, zero-write GET, eski failed qatorlar,
  exact action → return → recent va filtrli sahifalash.
- `venv/Scripts/python.exe manage.py test core.test_student_support_return
  --verbosity 1`: **17/17 PASS**.
- Yakuniy to‘rtta yangi modul birga: `venv/Scripts/python.exe manage.py test
  core.test_student_support_results core.test_student_support_delivery
  core.test_student_support_evidence_views core.test_student_support_return
  --verbosity 1`: **74/74 PASS**, 11.927s.
- Filtr qo‘shilishidan oldingi support views/service/results/delivery,
  backoffice recent/return regressiyasi: **113/113 PASS**. Bu yakuniy broad
  suite o‘rnini bosmaydi.
- `node --test tests/frontend_v1/*.test.mjs`: **171/171 PASS**.
- `manage.py check`: 0; `makemigrations --check --dry-run`: o‘zgarish yo‘q.

- Yakuniy broad: `venv/Scripts/python.exe manage.py test core courses bot
  --verbosity 1`: **1698 / 1651 PASS / 47 skip**, 381.616s; exit 0.
  Skiplar mavjud muhit/backend shartlariga tegishli; test susaytirilmadi.
  Provider kalitlari bo‘sh holatdagi kutilgan fallback loglari failure emas.

IAB synthetic 8102, alohida SQLite nusxada: assignment → aniq review →
ayni o‘quvchi/kurs/dars; quizning oxirgi 0% natijasi va oldingi urinishlar;
examning draft bali yashirin, tasdiqlangan 82.50% va yangi urinish tarixi;
failed filtri → birinchi sahifadan tashqaridagi eski xabar → aniq replay
sahifasi → kartaga qaytish → recheck → Ish stoli/recent orqali filtrni tiklash.
Qaror POSTlari avtomatik integratsiya testlarida; brauzerda real xabar yuborilmadi.

320/1440px, dark/light, 200% rendered text (native zoom emas), Tab fokusi
tekshirildi. Assignment/quiz/exam/delivery hamda focused replay sahifasida
gorizontal overflow 0; console error/warning 0. Uchta takroriy qaytish havolasi,
focused provider-error tafsiloti va noto‘g‘ri eski exam GET initializerga
tushish holati reviewda topilib tuzatildi. Umumiy texnik sahifa/audit dalili saqlandi.
Mahalliy synthetic rasmlar (Gitga kirmaydi):
`.tools/backoffice-b24/results-desktop.png`, `delivery-desktop.png`,
`delivery-mobile-200.png`.

Primary lokal `db.sqlite3`: `.tools/backoffice-b24/local_smoke.py` orqali
home + access + uch natija turi + delivery all/failed — **7 HTTP 200,
private/no-store**. Vaqtinchalik login/recent transaction ichida rollback;
**149 jadval / 1315 qator** oldingi/keyingi hash va sonlari bir xil.
Sinov yozuvlari, parol, ruxsat yoki flag asosiy bazaga yozilmadi.
8092 lokal server yangi kod bilan qayta ishga tushirildi; mavjud login
sahifasi va kirish yo‘li 200. Ishlayotgan foydalanuvchi paroli o‘zgarmadi.

## Flaglar va chegaralar

Yangi model, migration, flag, provider yoki background xizmat yo‘q.
Mavjud `backoffice_student_support` OFF kartani va signed qaytishni yopadi;
saqlangan natijalar, bildirishnomalar va mavjud mustaqil qaror sahifalari qoladi.
`backoffice_unified_navigation` faqat yagona qidiruv/recent qaytishiga ta’sir
qiladi. `telegram_outbox_sending`ning haqiqiy yuborish boshqaruvi workerda qoladi.

Bu o‘quvchiga yordam kartasi: yangi grade engine, avtomatik qayta yuborish,
yangi notification trigger yoki o‘quvchi o‘rniga kirish yo‘q. Assignment/quiz
sharhi va exam feedback tafsilotlari tegishli mavjud tekshirish sahifasida;
email/SMS yoki Classbook guruh yetkazilishi bu shaxsiy xabar kartasiga kirmaydi.
Xabarning tarixda nega yaratilmagani, Telegramda o‘qilgani yoki qurilma/internet
muammosi mavjud yozuvlardan aniqlanmaydi.

Owner usability, native telefon/zoom/AT va production qabuli alohida.
Keyingi kesim **B2.5 — mavjud dizayn sozlamalarini eski formalarga ulash**;
B2.6 birgalikdagi sifat tekshiruvi ham qolgan.
