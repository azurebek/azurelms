# BACKOFFICE-02 / B2.2 — dars topshirig‘i va oddiy test

2026-10-13. [Yagona reja va admission](BACKOFFICE-REFORM-PLAN.md#backoffice-02).
Topshiriq va bir javobli test tayyorlash implementatsiyasi hamda lokal tekshiruv
tayyor. Asosiy lokal bazada yoqildi; production va ownerning yordamsiz sinovi
alohida. Integratsiya uchun uch required CI va review gate’i saqlanadi.

## Natija

- Tanlangan darsda «Topshiriq va testlar»: aniq yaratish tugmalari, saqlangan
  yozuvlar va ayni darsga qaytish. Topshiriq nomi/sharti/rag‘bat balli;
  test nomi/balli, ochiladigan savollar, variantlar va bitta to‘g‘ri javob.
- Variant/savol qo‘shish va olish faqat bound formani o‘zgartiradi. Saqlash
  alohida tasdiqlanadi; amaldagi darsga ta’siri tushuntirilgan. Preview
  attempt, submission, progress yoki XP yozmaydi, javob yubormaydi.
- `courses/authoring_service.py` yagona writer: fresh actor va teacher course
  scope, parent/object lock, signed snapshot, create replay/stale, no-op va
  atomik audit. Question/Choice ID saqlanadi; begona/takror ID rad etiladi.
  Rich matn mavjud canonical sanitizer orqali o‘tadi; preview inert.
- Har qanday assignment submission yoki javobsiz quiz attempt ham barcha
  tahrirni yopadi. Cross-quiz QuizAnswer va exam StudentAnswer havolalari
  ham hisobga olinadi. Noto‘g‘ri/aralash/imtihonga bog‘langan eski quiz
  avtomatik aylantirilmaydi. Sabab va yangi yozuv yaratish yo‘li ko‘rsatiladi.
- `submission_service` learner user → Assignment/Quiz lock’ini olib,
  content/accessni yangidan o‘qiydi. Birinchi topshirish va authoring umumiy
  parent bilan ketma-ketlashadi. Baholash/XP/access formulasi o‘zgarmagan.
- Xato ayni maydon/savolda; invalid raqam, stale va ishlatila boshlaganidan
  keyingi POST matni saqlanadi. Buzilgan tuzilmada cheklangan maydonlar va
  nusxalash uchun raw savol matni qoladi, saqlash yopiladi. Parserning
  900 content-field, 100 question, 20 choice chegaralari request himoyasi;
  kattaroq eski test formaga jimgina kesib joylanmaydi.
- `practice.js` qoralamasi actor/session/course/lesson/object bo‘yicha
  ajralgan; savol/variantlar va radio tanlovi tiklanadi. Restore explicit
  POST orqali faqat formani qayta quradi. CSRF/revision/tasdiq saqlanmaydi;
  receipt faqat o‘z scope/nonce/ayni matnini tozalaydi. Serverning add/remove
  javobi faqat matching transfer bilan qoralamani yangilaydi.

## Tekshiruv dalili

Env-file OFF, `APP_ENV=local`, remote services OFF, Gemini/Telegram bo‘sh:

```powershell
venv/Scripts/python.exe manage.py test core courses bot --verbosity 1
node --test tests/frontend_v1/*.test.mjs
venv/Scripts/python.exe manage.py check
venv/Scripts/python.exe manage.py makemigrations --check --dry-run
git diff --check
```

- Django: **1572 test / 1525 PASS / 47 skip**, 273.768s. SQLite’da PG-only
  overlap sinovlari bajarilmaydi; ular required PostgreSQL CI’da tekshiriladi.
- Node: **171/171 PASS**, yangi practice controller **18/18**. Check 0,
  migration drift yo‘q, diff-check PASS.
- Yangi domain regression: gate, owner/teacher/foreign/inactive, parent/ID,
  stale/create replay, no-op, audit rollback, barcha used-state va rich matn.
  Uch PG testi ikkala tur uchun learner-first, author-first va ikki actor
  overlap’ini tekshiradi. HTTP: 29 ta scope/CSRF/flag/preview/retention testi.
- Mustaqil review topgan quiet invalid-number va aggregate form-budget
  muammolari tuzatildi. Brauzer `form.action` nomli tugmalar bilan soyalanib
  restore manzilini buzishini ko‘rsatdi; `getAttribute` bilan tuzatildi.
  CKEditor boshlang‘ich normalizatsiyasidagi yolg‘on recovery banneri ham
  tuzatildi. Uchala browser-controller chekka holati regressiyaga qo‘shildi.

IAB sinovi faqat `.tools/backoffice-b22/demo.sqlite3`, port 8100’da:

1. Dars → topshiriq → shart → preview → tahrir → save → reopen; ayni darsga qaytish.
2. Uch savol/ikki variant; ikkinchi savolda correct yo‘q → inline xato va
   ochiq savol → tuzatish → preview. Reload → explicit restore → uchala
   savol va tanlov DOM’da → save → qayta ochish va preview.
3. DB readback: bitta assignment, uch savolli quiz va har savolda bitta
   correct. Previewdan keyin shu darsda learner attempt/submission/progress 0.
4. Synthetic javobsiz attemptdan keyin quiz read-only; asl savol/variantlar
   saqlangan. Pending assignment fixture va boshqa holatlar HTTP/domain’da.
5. 320px + 200% rendered text: assignment, quiz va preview scrollWidth 305;
   1440pxda scrollWidth 1425. Dark/light, variant maydoni va Tab → tasdiq
   fokusi ko‘rindi. Browser console error 0. Native zoom/telefon/AT emas.

Lokal rasm/loglar `.tools/backoffice-b22/`da: `lesson-practice.png`,
`quiz-preview.png`, `quiz-phone-200.png`, `preview-phone-200.png`,
`assignment-phone-200.png`, `quiz-protected.png`. Sinov yozuvlari owner
bazasiga ko‘chirilmagan.

## Lokal faollashtirish va qaytish

`backoffice_practice_authoring` registry default **OFF**. Lokal ON’dan oldin
uch authenticated GET rollback ichida tekshirildi; probe’dan keyin qator
sonlari o‘zgarmadi. Canonical backup:
`backups/backoffice-b22-20261013-before.sqlite3`.
So‘ng `set_flag` bilan faqat shu flag yoqildi. Backup bilan barcha jadvallar
solishtirildi: eski qatorlar aynan saqlangan, faqat **1 flag + 1 audit** yangi;
integrity va foreign-key tekshiruvi OK. Birinchi tekshiruv skriptida audit
jadvali nomi noto‘g‘ri kutilgani tuzatilib, yozishsiz readback bilan tasdiqlandi;
faollashtirish takror yuborilmadi.

Rollback: shu flagni OFF qilish yangi muharrir GET/POST va canonical writerini
yopadi; learner kontenti, urinish/natijalar qoladi. Schema migration yo‘q.
Workspace flagi ham HTTP kirishini yopadi. Production deploy bajarilmadi.

## Chegaralar

Bu oddiy lesson quiz muharriri; exam builder, question reorder, ishlatilgan
kontentni versiyalash yoki draft/publish lifecycle emas. Ishlatilgan kontent
o‘rniga yangi assignment/test yaratiladi; mavjud nusxa o‘chirilmaydi.
Snapshotlar tashqi ABA uchun durable revision emas; admin/bulk/SQL yozuvlari
shu yangi authoring shartnomasining global kafolatiga kirmaydi.
Qoralama shu brauzer sessiyasida; boshqa qurilma va fayl tiklash yo‘q.
Keyingi kesim **B2.3 — topish va davom ettirish**. Owner qabuli kechiktirilgan;
bu qolgan bosqichlarni boshlash sharti emas.
