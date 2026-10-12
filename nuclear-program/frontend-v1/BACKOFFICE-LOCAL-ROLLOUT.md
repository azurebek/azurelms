# Backoffice — asosiy lokal bazada faollashtirish

2026-10-12. Tayanch `9f2c5fd` (PR181). Ownerning “davom et” topshirig‘i bilan
tayyor backoffice oqimlari shu kompyuterdagi asosiy `db.sqlite3`da yoqildi.
Bu lokal pilot; AWS yoki boshqa production muhitiga deploy emas.

## Scope va natija

Mavjud capability faollashtirildi; yangi mahsulot funksiyasi, model, migration
yoki flag defaulti kiritilmadi. Kurs/dars, o‘quvchi muammosi, dizayn va yagona
menyu uchun to‘rtta mavjud flag DB override orqali ON bo‘ldi. Boshqa flaglar
oldingi qiymatida qoldi. Avval barcha to‘rttasi default OFF edi, DB row yo‘q edi.

Manzil: `http://127.0.0.1:8092/backoffice/`. Oddiy kirish yangi Ish stoliga
yo‘naltiradi. Kurslar, O‘quvchilar va Sayt va dizayn shu menyudan ochiladi.
Asosiy mavjud hisob bilan kirish talab qilinadi; parol va ruxsatlar o‘zgarmadi.

Server loopbackda, env-file OFF, `APP_ENV=local`, remote services OFF,
Gemini/Telegram kalitlari bo‘sh holda ishga tushiriladi. Bu ish davomida AI,
Telegram, email yetkazish yoki tashqi hosting tekshirilmagan.

## Oldingi holat va zaxira

- Asosiy baza: SQLite, taxminan 2.2 MB, 151 ta qo‘llangan migration.
- 12 ta qo‘llanmagan migration; dizayn jadvallari hali yo‘q edi. Eski nashr
  qayta faollashishi xavfi tekshirildi: nashr/draft/state mavjud emas.
- Canonical `backup_db` (SQLite `VACUUM INTO`) bilan izchil nusxa:
  `backups/backoffice-local-20261012-before.sqlite3`.
- `restore_db --into .tools/backoffice-local-rollout/rehearsal.sqlite3`
  bilan alohida nusxaga tiklash bajarildi; asosiy bazani ustidan yozish yo‘q.
- Zaxira va nusxa `integrity_check=ok`, `foreign_key_check=0`.
  Manifest zaxira SHA-256 qiymati va mavjud ustunlar/qatorlarning xeshlarini
  saqlaydi; shaxsiy ma’lumotlar dalil fayliga chiqarilmaydi.

## Yangilash va faollashtirish

Avval nusxada, so‘ng asosiy bazada ayni 12 migration qo‘llandi:

- `classbook.0003_preparation_revision`;
- `core.0005_operationalsettings_checkout_quote_minutes`, `0006_operationalsettings_exam_receipt_limit`, `0007_design_workspace`;
- `courses.0021_examresultpublication` dan `0025_assignmentsubmission_review_revision` gacha;
- `library.0001_initial`, `0002_libraryresource_edit_revision`;
- `users.0022_customuser_ai_preferences_version`.

Mustaqil source audit: hammasi `CreateModel`/`AddField`; data backfill,
`RunPython`/`RunSQL`, delete yoki tashqi yon ta’sir yo‘q. SQLite ichki jadval
ko‘chirishidan keyin eski qiymatlar alohida solishtirildi.

`core.flags.set_flag` orqali bitta tashqi transaction ichida quyidagilar ON:

- `backoffice_course_workspace`;
- `backoffice_student_support`;
- `backoffice_design_workspace`;
- `backoffice_unified_navigation`.

Asosiy bazaga to‘rtta `feature_flag.update` audit yozuvi qo‘shildi. CLI sababi
Codex va owner topshirig‘ini aniq aytadi; inson hisobidan soxta amal yozilmadi.
Dizaynning ON holati muharrir bilan birga public CSSni ham faollashtiradi;
nashr bo‘lmagani uchun zavod qiymatlari ishlatiladi. Dizayn nashr qilinmadi.

## Bajarilgan tekshiruv

- Nusxa va asosiy bazada **21 ta authenticated route** HTTP 200: barcha
  markazlar, uch asosiy oqim, mavjud kurs/dars muharriri, mavjud o‘quvchi
  diagnostikasi, eski muharrir kirishlari, dizayn holati va CSS.
- To‘rtta asosiy kirish anonymous so‘rovda login/403 bilan yopiq.
- In-app brauzerda `8092/backoffice/` mavjud login sahifasiga ochildi;
  shu oyna owner kirishi uchun qoldirildi. Bu brauzerda owner paroli bilan
  kirish yoki yangi native-device qabul sinovi bajarilganini anglatmaydi.
- HTTP tekshiruvdagi vaqtinchalik session/last_login va lazy singleton yozuvi
  transaction rollback bilan bekor qilindi; asosiy kontentga sinov yozuvi yo‘q.
- Mavjud **130 jadval / 358 qator** eski ustunlari qiymatlari o‘zgarmadi.
  Migration/auth metadata hamda ataylab qo‘shilgan flag/audit jadvallari bu
  taqqoslashdan ajratilgan. Boshqa flaglar aynan avvalgi holatda.
- Asosiy bazada ham `integrity_check=ok`, `foreign_key_check=0`; pending
  migration qolmadi.
- Nusxada barcha flaglarni oldingi qiymatiga qaytarish va yana ON qilish
  ishladi; qayta yoqilgach sahifalar qayta tekshirildi, kontent saqlandi.
- Env-file OFF, Gemini/Telegram bo‘sh:
  `venv/Scripts/python.exe manage.py test core.test_backoffice_acceptance core.test_backoffice_workspace core.test_student_support_views --verbosity 1`:
  **58/58 PASS**, 23.022s; system check 0 issue. Yangi test/model kodi yo‘q.

Xususiy lokal dalillar `.tools/backoffice-local-rollout/` ichida:
`before.json`, `rehearse-result.json`, `activate-result.json`, `run.py`.
Bazalar va bu papka Gitga kiritilmaydi.

## Qaytish

Odatiy UI rollback — yuqoridagi to‘rtta flagni canonical `set_flag` yoki
Yoqish/o‘chirish sahifasi orqali oldingi **OFF** qiymatiga sabab bilan qaytarish.
Bu darslar, o‘quvchi qarorlari yoki dizayn tarixini o‘chirmaydi. Migrationni
orqaga qaytarish yoki zaxirani asosiy baza ustiga yozish shart emas.

Shu rollout uchun xususiy helper:
`venv/Scripts/python.exe .tools/backoffice-local-rollout/run.py rollback`.
U kutilgan lokal baza va zaxira fingerprintini tekshiradi; flaglar ON
bo‘lmasa taxmin qilib davom etmaydi. Keyingi mustaqil flag o‘zgarishlari bo‘lsa,
avval ularning sababi tekshirilib, kerakli flaglar canonical UI orqali tanlanadi.

## Ochiq qabul chegaralari

Bu asosiy lokal baza bilan texnik release tekshiruvi. Ownerning yordamsiz
foydalanish qabuli, haqiqiy telefon, native browser zoom va assistive technology
sinovi bajarildi deb hisoblanmaydi. DC6 owner qabuli hamon PENDING.

Internetdagi platformaga rollout alohida ish. Keng assignment/quiz/savol
muallifligi va dizaynning mustaqil Mini App/SIT/vendor/print yuzalariga to‘liq
tarqalishi avvalgi scope chegaralari bo‘yicha ochiq; lokal yoqish ularni yopmaydi.
