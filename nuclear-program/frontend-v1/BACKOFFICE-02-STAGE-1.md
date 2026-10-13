# BACKOFFICE-02 / B2.1 — kursdagi uzilishlarni yopish

2026-10-13. [Yagona reja va admission](BACKOFFICE-REFORM-PLAN.md#backoffice-02).
Holat: implementatsiya va lokal tekshiruv tayyor; PR uchun required CI va review
integratsiya gate’i qo‘llanadi. Owner usability sinovi kechiktirilgan.

## Natija

- Tanlangan darsdagi material kartasida nom, auditoriya, ko‘rinish, sana,
  yuklash va majburiylik sozlanadi. Alohida ochiladigan tartib formasi va
  darsdan olish amali bor; umumiy resource/fayl o‘chirilmaydi.
- Legacy material xatosi redirect bilan yo‘qolmaydi: bound forma 400/409,
  xatoli sana brauzer blank qilmaydigan matn maydonida qaytadi. Tartibning
  noto‘g‘ri, takrorlangan, yetishmaydigan yoki begona kaliti ikki rendererda
  rad etiladi; teng raqamning oldingi deterministic tartibi saqlangan.
- `library/material_authoring.py` update/detach/reorder uchun yagona atomik
  writer: current actor, kurs/dars scope, signed snapshot, no-op va audit.
  Workspace va legacy/V1 adapterlar bir xil xizmatni chaqiradi.
- Kursdan «Imtihonlar» ayni kursga kiradi. Birinchi exam yashirin tanlanmaydi;
  yangi imtihon birinchi bo‘limi bilan atomik saqlanadi, mavjud bo‘lim aniq
  tanlanadi. `courses/exam_authoring_service.py` yagona writer.
- Har qanday `ExamAttempt`, shu jumladan davom etayotgan javobsiz urinish,
  bu muharrirdagi barcha tahrirni yopadi. Attempt boshlash va authoring bir
  `Exam` row lock’ini ishlatadi; entry policy lock olingach yangidan o‘qiladi.
- Dars, material va tartib qoralamalari actor+sessiya+obyekt scope’da alohida.
  Tiklash explicit; revision/CSRF/fayl brauzer qoralamasiga kirmaydi. Save
  receipt faqat o‘z formasi va yuborilgan nusxani tozalaydi. Qo‘shni formani
  saqlash hal qilinmagan eski qoralamani bosmaydi; storage ishlamasa chiqish
  ogohlantirishi qoladi. Material xatosidan Back/reload GET kontekstiga qaytadi.

## Dalil

Avval ikkita material regressiyasi 302 o‘rniga bound 400 kutib yiqildi:
invalid sana va flag OFF reorder. Exam regressiyasi bo‘sh bo‘lim maydonlari
yo‘qligini hamda `new=1` mavjud examni tanlayotganini ko‘rsatdi. Tuzatishdan
keyin regressiyalar o‘tdi; eski valid POST testlariga haqiqiy GETdan olinadigan
majburiy tokenlar qo‘shildi, natija/ruxsat assertionlari susaytirilmadi.

Env-file OFF, `APP_ENV=local`, remote services OFF, Gemini/Telegram kalitlari bo‘sh:

```powershell
venv/Scripts/python.exe manage.py test core library courses --verbosity 1
venv/Scripts/python.exe manage.py check
venv/Scripts/python.exe manage.py makemigrations --check --dry-run
node --test tests/frontend_v1/*.test.mjs
git diff --check
```

- Django: **1349 test / 1305 PASS / 44 skip**, 273.171s. Skiplar SQLite’da
  ishlamaydigan mavjud va yangi PostgreSQL tekshiruvlarini ham o‘z ichiga oladi.
- Node: **153/153 PASS**. Check 0, migration drift yo‘q, diff-check PASS.
- Yangi PostgreSQL testlari: ikki actor bitta material snapshotini saqlaganda
  bitta commit; exam authoring va birinchi attempt overlap’i har ikki tartibda.
  Lokal SQLite natijasi bu lock testlari bajarilgan degani emas; required
  PostgreSQL CI ularni tekshiradi.
- Mustaqil source review: scope/atomicity/shared-file/lock tekshiruvi; topilgan
  sibling draft overwrite va invalid number/date blank muammolari tuzatildi.

Brauzer faqat `.tools/backoffice-b21/demo.sqlite3` synthetic nusxada, loopback
8099 portida ishladi. Asosiy `db.sqlite3`ga sinov kontenti yozilmadi.

1. Dars title qoralamasi → material nomi/ko‘rinishini saqlash → ayni dars va
   tiklanadigan matn; reorder → ayni qoralama. Materialning o‘z qoralamasi
   reload → ochilgan karta → explicit tiklash → save/readback orqali o‘tdi.
2. Materialni darsdan olish → ayni kursdagi boshqa darsda shared resource
   qoldi. Unsaved lesson title DBda o‘zgarmadi. O‘quvchi ko‘rinishi canonical
   visibility predicate’dan olinadi; HTTP test yashirilgan materialni chiqaradi.
3. Bo‘sh kurs → yangi exam+bitta bo‘lim → save/reopen. Keyin synthetic ikkinchi
   bo‘lim tanlanib tahrirlandi; birinchi bo‘lim nomi o‘zgarmagani DBda tasdiqlandi.
   Synthetic active attempt qo‘shilgach UI sababi bilan read-only va save yo‘q.
4. 320px/1440px, light/dark va 200% **rendered text** tekshirildi. 320pxda
   course heading/pane switch/grid overflow tuzatildi; material/exam controls
   sahifadan chiqmaydi (scrollWidth 305 ≤ viewport 320). Tab fokusi ko‘rinadi,
   browser console error 0. Native zoom yoki haqiqiy telefon sinovi deyilmaydi.

Lokal log/rasmlar `.tools/backoffice-b21/`da (Gitga kirmaydi):
`app-tests.log`, `node-tests.log`, `material-phone-200.png`,
`exam-phone-200.png`, `material-desktop.png`.

## Qaytish va chegaralar

Yangi model/migration/flag default/provider yo‘q. Mavjud lokal workspace flagi
allaqachon ON; bu bosqich flag holatini o‘zgartirmaydi. Workspace OFF bo‘lsa
yangi POST 409, kontent saqlanadi va eski muharrirdan o‘qiladi. Legacy/V1
validation, signed token va used-exam himoyasi flagdan mustaqil. Oldindan ochiq
tokeni yo‘q legacy material/exam formasi xavfsiz rad etiladi; qayta ochish kerak.

Snapshotlar durable revision counter emas; tashqi writer qiymatni o‘zgartirib
aynan oldingi holatga qaytarsa (ABA), bu alohida kafolat emas. Browser draft
shu sessiyaga tegishli; fayl yuklash va cross-device tiklashni bermaydi.
Exam savollari/reading/listening to‘liq builder’i va ishlatilgan kontentni
versiyalash bu kesimga kirmaydi. Legacy admin orqali yozish uchun yangi
global model-level himoya da’vo qilinmaydi. Native qurilma/AT, production va
owner qabuli alohida; keyingi implementatsiya **B2.2 — topshiriq va oddiy test**.
