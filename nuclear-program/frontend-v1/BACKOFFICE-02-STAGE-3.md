# BACKOFFICE-02 / B2.3 — topish va davom ettirish

Sana: 2026-10-13. Tayanch: `c1b70a8` (B2.2). Ownerning «davom et» topshirig‘i.
Admission: [yagona reja §11](BACKOFFICE-REFORM-PLAN.md#backoffice-02).
Bu hujjat implementatsiya dalili; alohida roadmap emas.

## Natija

- Yagona backoffice qobig‘ining yuqorisida **Qidirish**. Kurs, dars,
  o‘quvchi va mavjud ruxsatli bo‘limlar bitta sahifada topiladi. Turi,
  ota kurs/modul yoki o‘quvchining ko‘rinadigan kursi natijada yozilgan.
  Bir xil dars nomlari ota kursi bilan ajraladi; havola ayni darsga boradi.
- Barchasi/Kurslar/Darslar/O‘quvchilar/Bo‘limlar filtri, 12 tadan sahifalash,
  bo‘sh natija va xatoni joyida tuzatish. Ko‘p so‘zli ism turli tartibda,
  oddiy va tipografik apostrof variantlari bilan topiladi.
- Qidiruv va kurs ro‘yxatidagi filtr/sahifaga qaytish; lesson outline,
  material qidiruvi, topshiriq/test, kurs ma’lumotlari, save/stale yo‘llari
  hamda o‘quvchi kurs/dars selectorlari kontekstni saqlaydi.
- **Ishni davom ettirish** — shu hisobning joriy sessiyasida oxirgi ochilgan
  uchta kurs/dars, o‘quvchi kartasi yoki owner dizayn ustaxonasi. Obyekt
  nomi va ruxsati qaytishda yangidan o‘qiladi. Yangi yaratilgan kurslar
  alohida eski ro‘yxat bo‘lib qoladi, ochilgan ish deb ko‘rsatilmaydi.

## Shartnoma

`core/backoffice_search.py` GET `/backoffice/workspace/search/` adapteri.
Fresh active staff/owner, `teacher_course_queryset`, `support_student_queryset`
va mavjud `navigation`/`section_links` registri ishlatiladi. Yangi permission
manbasi yo‘q. O‘quvchi email/telefon, xabar va dars matnlari qidirilmaydi.
O‘quvchi natijasidagi kurs nomi faqat actor scope’idan bitta subquery bilan
olinadi; barcha enrollment tarixi yuklanmaydi. Har tur COUNT va faqat
sahifaga tushgan kesim olinadi. So‘rov soni natija qatorlari bilan oshmaydi.
200 belgi, sahifa raqami va natija hajmi request/render qo‘riqchilari;
operatsion muddat/kvota qoidasini yaratmaydi.

`core/backoffice_return.py` source+parametrlarni imzolaydi va actor/session
bilan bog‘laydi. Faqat ikki list source, aniq mahalliy destination route’lar;
tashqi URL, o‘zgartirilgan yoki boshqa sessiya tokeni qabul qilinmaydi.
Matnli qidiruv konteksti faqat URL bo‘ylab o‘tadi, recent’da saqlanmaydi.

`core/backoffice_recent.py` successful GET 200’dan keyin ruxsatli IDlarni
session’da saqlaydi. POST (shu jumladan namuna)/error/redirect, list/home/search qayd
yaratmaydi. Session’da ism, aloqa, URL/token, qoralama, revision yoki CSRF
yo‘q. Home o‘qishi session’ni qayta yozmaydi; bir xil takroriy GET ham no-op.
O‘chirilgan/moved/revoked obyekt chiqmaydi; logout yoki boshqa hisobga
kirish tarixni ajratadi. Course/lesson rich matni home projection’da olinmaydi.
Session holati canonical learning state emas; GET progress/baho/attempt yozmaydi.

## Tekshiruv dalili

Test muhiti: env-file OFF, `APP_ENV=local`, remote services OFF,
`GEMINI_API_KEY` va `TELEGRAM_BOT_TOKEN` bo‘sh.

- `venv/Scripts/python.exe manage.py test core courses --verbosity 1`:
  **1373 / 1328 PASS / 45 skip**, 349.015s. SQLite’dagi PG-only sinovlar
  required PostgreSQL CI’da bajariladi. Birinchi broad run paytida eski
  yuklangan Python va yangilanayotgan template aralashib bitta context
  assertion yiqildi; barcha tahrirlar tugagach ayni suite qayta o‘tdi.
- `venv/Scripts/python.exe manage.py test core.test_backoffice_search
  core.test_backoffice_navigation --verbosity 1`: **30/30 PASS**.
- `venv/Scripts/python.exe manage.py test core.test_backoffice_return
  --verbosity 1`: **16/16 PASS**, course-settings parent tekshiruvi bilan.
- Yakuniy scoped suite: search/recent/return/workspace/material/practice/
  support/design sakkiz moduli — **155/155 PASS**, 43.409s.
- `node --test tests/frontend_v1/*.test.mjs`: **171/171 PASS**.
- `manage.py check`: 0; `makemigrations --check --dry-run`: drift yo‘q.
- `git diff --check` va 51 ichki hujjat havolasi PASS.

IAB sinovi alohida `.tools/backoffice-b23/demo.sqlite3`, port 8101’da:

1. `tanishuv` → ota nomlari bilan darslar → lesson 8 → To‘lovlar → Ish stoli
   → ayni dars recent’da. `Madina` → karta → boshqa dars tanlash → qaytishda
   ayni qidiruv. Recent orqali learner/course/lesson tanlovi tiklandi.
2. `O'zingizni` oddiy apostrof bilan tipografik nomdagi uch darsni topdi.
   Dars → Kurs ma’lumotlari → Kursga qaytish → ayni lesson 8 va qidiruv.
3. 320px + 200% rendered text: search/recent scrollWidth 305, viewport 320;
   1440px desktop: scrollWidth 1425. Dark/light va klaviatura fokus ramkasi
   screenshotda tekshirildi. Console error 0. Bu native zoom yoki telefon emas.
4. Independent review topgan material GET, kurs sozlamalari va konflikt
   qaytish konteksti yo‘qolishi tuzatildi. Natijadagi fokus ramkasi ota
   konteyner tomonidan kesilmasligi uchun ichkariga chizildi.

Rasm/loglar `.tools/backoffice-b23/`da: `search-desktop.png`,
`resume-desktop.png`, `search-phone-200.png`, `resume-phone-200.png`.
Test kontenti owner bazasiga ko‘chirilmagan.

## Lokal holat va chegaralar

Asosiy lokal bazada mavjud unified-navigation flagi allaqachon ON. Yangi
flag, migration yoki kontent yozuvi yo‘q. To‘rtta authenticated read smoke
200/private/no-store; vaqtinchalik login/recent yozuvlari transaction rollback
qilindi. Barcha jadvallarning oldingi/keyingi snapshotlari aynan teng.
8092 lokal server yangilangan kod bilan qayta ishga tushirildi; login HTTP 200.

Rollback: `backoffice_unified_navigation` OFF qidiruv va recentni yopadi;
eski yo‘llar va learner kontenti qoladi. Destination flag OFF uning turini
natija/recentdan yashiradi. Token ruxsatni oshirmaydi, destination o‘zi
ham ruxsatini tekshiradi.

Recent free-text qidiruvni eslamaydi: qayta ochilgan obyekt, kurs/dars va
ID/enum tanlovlari qaytadi; matnli eski qidiruv faqat uning qaytish havolasi
bo‘ylab saqlanadi. Cross-device tarix, to‘liq imtihon/material/assignment
qidiruvi va har bir legacy muharrirning recent’i qamrovda yo‘q.
Owner/native qurilma/AT qabuli va production alohida. Keyingi bosqich B2.4.
