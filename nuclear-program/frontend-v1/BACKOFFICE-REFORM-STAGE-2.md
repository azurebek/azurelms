# Backoffice islohoti — kurs va dars ustaxonasi

2026-10-10. Owner ikkinchi bosqichning haqiqiy kurs/dars oqimini qurishni topshirdi.
[Reja](BACKOFFICE-REFORM-PLAN.md), [action xaritasi](BACKOFFICE-REFORM-STAGE-1.md).

## Admission va chegaralar

**ADMIT — launch-critical.** Owner kurs/modul/dars tayyorlashni yordamsiz tugata
olmayotgani qayd etilgan; kontent tayyorlash platformani ishlatishning zarur yo‘li.
KPI: T1–T3/T8 vazifalarini yordamsiz yakunlash. Hozir natija o‘lchanmagan.

- Canonical state: mavjud Course, Module, Lesson; yangi authoring service scope,
  validation, stale snapshot va auditni boshqaradi. HTTP faqat adapter.
- Material: mavjud LibraryResource/LessonMaterial va library.services upload/attach.
  Release: mavjud courses.release_service va guruhga ochish yuzasi.
- Haftalik yuk kamayadi: bitta kurs konteksti, oddiy matn muharriri, material va namuna.
  Yangi navbatchilik, provider yoki AI chaqiruvi qo‘shilmaydi.
- `backoffice_course_workspace` registr flagi default OFF. OFF yangi yuzani va
  in-flight yozishni yopadi; eski renderer va saqlangan kontent qoladi.
- Schema migration, production/AWS deploy, access/pricing o‘zgarishi yo‘q.
  Lokal ko‘rsatish alohida synthetic DB bilan; owner ma’lumoti sinov uchun yozilmaydi.
- Saqlash canonical kontentni yangilaydi. Lesson’da private draft status mavjud emas:
  ochiq dars matni o‘zgaradi, drip bo‘lmagan guruh yangi darsni ko‘rishi mumkin.
  Course.is_active katalog ko‘rinishini boshqaradi; yashirilgan kurs mavjud
  o‘quvchi kirishini bekor qilmaydi. UI aynan shuni aytadi. Brauzer qoralamasi
  serverda saqlangan yoki o‘quvchidan yopiq dars deb ko‘rsatilmaydi.
- Rich text existing CKEditor; fayl mavjud private upload validation orqali.
  Namuna saqlanmagan matnni yozmasdan ko‘rsatadi, o‘quvchi akkauntiga kirmaydi.

## Tekshiruv rejasi

Service: scope/parent, validatsiya, stale/no-op/repeated create, audit rollback.
HTTP: real authoring va material oqimi, CSRF, begona kurs, flag OFF, read-only preview.
Browser: desktop/mobile, klaviatura, boy matn, qoralama qaytarish, saqlash va material.
Required CI va yakuniy holat tekshirilgach dalil shu faylga qo‘shiladi.

## Qurilgan oqim

- `/backoffice/workspace/`: alohida Boshqaruv menyusi, uch asosiy ishga kirish.
  Kurslar ishlaydi; o‘quvchi/dizayn/to‘lov/sozlama havolalari mavjud yuzalarga boradi.
- Kursni qidirish va katalog holati bo‘yicha saralash; kurs yaratish va sozlash.
- Kurs ichida modul yaratish, nomlash, yuqori/pastga tartiblash; dars yaratish
  va tahrirlash. Boy matn, video havolasi, modul/tartib/ball qo‘shimcha bo‘limda.
- Saqlanmagan matn namunasi DB yozmaydi. Saqlash server tasdig‘idan keyin ko‘rsatiladi.
- Shu joyda fayl yuklash yoki kutubxonadan biriktirish. Namuna mavjud library
  policy bo‘yicha faqat o‘quvchiga ochiq materiallarni chiqaradi.
- Guruhga ochish havolasi aynan tanlangan dars/guruh bilan mavjud tasdiqlash
  oynasini ochadi; yangi release writer yoki access qoidasi yaratilmagan.
- Tor ekranda Tuzilma / Tahrirlash / Ko‘rinish alohida panellar. Keng ekranda
  kurs daraxti dars yonida qoladi. Menyu klaviatura bilan ochiladi/yopiladi.

### Saqlash va qaytish chegarasi

`courses/authoring_service.py` actor/course scope, model/form validation, transaction,
stale snapshot va auditni boshqaradi. `core/backoffice_workspace.py` HTTP adapteri;
materiallar mavjud `library.services` orqali yoziladi. Upload muvaffaqiyatsiz INSERT
yoki attach/audit xatosida yaratilgan faylni ham tozalaydi. Begona kurs/modul/dars
so‘rovlari yozmaydi; preview audit/release/enrollment o‘zgartirmaydi.

Browser sessionStorage qoralamasi actor/session/kurs/dars yoki yangi darsning
boshlang‘ich moduli bilan chegaralangan. Tiklash operator tanlovi bilan; bound xato
formasidagi matn jimgina almashtirilmaydi. Faqat muvaffaqiyatli server yozuvi nonce
va aynan yuborilgan matnni tasdiqlaganda eski qoralama tozalanadi. Bu doimiy server
qoralamasi emas: logout/brauzer storage tozalanishi/yangi sessiya uni saqlamaydi;
fayllar qoralamaga kirmaydi. Storage ishlamasa sahifa ogohlantiradi.

HMAC snapshot stale yozuvlarni rad etadi; takroriy create dublikat yaratmaydi.
Bu durable idempotency receipt emas. Legacy writer parallel qiymatni o‘zgartirib
yana aynan avvalgi holatga qaytarsa snapshot buni alohida tarix sifatida bilmaydi.

## Lokal ko‘rish dalili

Haqiqiy Django server va alohida synthetic DB, `127.0.0.1:8092`; ownerning
`db.sqlite3` ma’lumotlari va 8088 design prototipi sinovda yozilmadi.
IAB orqali kurs → modul → boy matnli dars → saqlanmagan namuna → saqlash → fayl
biriktirish bajarildi. Sahifadan ketib qaytish, matnni tiklash va qayta saqlash
ham bajarildi. Guruh havolasi to‘g‘ri tasdiqlash oynasini ochdi; release tasdiqlanmadi.
320px da uch panelning har biri horizontal overflow0; desktop va light/dark
ko‘rinish ko‘rildi. Menyu Enter bilan ochilib, Escape bilan yopildi.

Guruh nomi fallbackidagi template xatosi browser sinovida topilib tuzatildi;
real Cohort regression testi qo‘shildi. Bu agent sinovi, owner usability/vaqtli
o‘lchov, haqiqiy telefon/AT yoki production release qabuli emas.

Holat: kurs kesimi implementatsiya qilingan; yakuniy test/CI dalili quyida yuritiladi.
O‘quvchi ish maydoni, oddiy dizayn porti va qolgan backoffice keyingi bosqichlar.
DESIGN-01 DC6 owner qabuli PENDING. Production flag OFF, deploy bajarilmadi.

## Avtomatik tekshiruv dalili

Env-file o‘qilmagan (`AZURELMS_SKIP_ENV_FILE=1`), Gemini/Telegram kalitlari bo‘sh.

```powershell
venv/Scripts/python.exe manage.py check
venv/Scripts/python.exe manage.py test core.test_backoffice_workspace courses.test_authoring_service core.test_frontend_v1_editors core.test_backoffice_courses core.test_backoffice_lessons core.test_feature_flags library --verbosity 1
node --test tests/frontend_v1/backoffice-workspace.test.mjs
node --check static/backoffice/workspace.js
git diff --check
```

Django: **185 test, 183 PASS / 2 SQLite skip**, 14.450s; check0. Skiplar haqiqiy
row-lock talab qiluvchi yangi authoring concurrency va mavjud library concurrency
sinovlari; PostgreSQL CI to‘liq suite’da ishlaydi. Scope/replay/stale/CSRF,
flag rollback/fail-closed, audit/file rollback, Cohort template, modul almashtirganda
qoralama identifikatori va canonical material ko‘rinishi qamrab olingan.

Node controller testi nonce mos kelishi, yangiroq matnni o‘chirmaslik, scope,
bound POST, saqlanmagan preview, storage failure va logoutni tekshiradi.
CI/merge natijasi marinebook/PR’da qayd etiladi; lokal PASS production qabuli emas.
