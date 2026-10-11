# Eski backoffice muharrirlari — soddalashtirish va reflow

2026-10-11. Tayanch `7425b03`. Owner qolgan eski muharrirlarni tekshirish,
zich/texnik joylarni soddalashtirish, telefon va kattalashtirilgan matnda
foydalanishni tekshirishni topshirdi.

## Admission

**ADMIT — launch-critical.** Maqsad: mavjud formani texnik yordamsiz to‘ldirish
va saqlashni osonlashtirish. Asosiy KPI — asosiy maydonlar, xatolar va saqlash
amallari tor ekranda ham o‘qilishi va foydalanish uchun ochiq qolishi.
Avtomatik yoki agent sinovi insonning yordamsiz foydalanish natijasi emas.

Bu ish taqdimot qatlamiga tegishli. Blog/SIT/core/library/catalog mavjud
formalari, domen writerlari, permission, CSRF, revision, sabab/tasdiq va
formset management maydonlari saqlanadi. Yangi model, migration, provider,
operatsion ish yoki production flag o‘zgarishi kiritilmaydi.
Odatdagi owner yuki kamayishi ko‘zlanadi; yangi boshqariladigan xizmat yo‘q.
Qaytish — taqdimot commitini revert qilish yoki mavjud renderer flaglari;
saqlangan kontent o‘chmaydi.

## Tekshiruv

Tarkib: imtihon, landing/brend, blog/SIT, kutubxona materiali, tarif/guruh
formalari va ularning umumiy qobig‘i. Qolgan kurs/dars va texnik sozlama
yuzalari regressiya uchun ko‘riladi. Native qurilma va production qabuli
alohida; faqat haqiqatan bajarilgan viewport/matn sinovi qayd etiladi.

## Natija

- Imtihon: nom/kurs/tur, baholash, kirish shartlari va bo‘lim materiallari
  ajratildi. Yorliqlar o‘zbekcha; server xatosi tegishli yopiq bo‘limni ochadi.
- Bosh sahifa: telefon uchun bo‘lim tanlash formadan oldinda; server xatosi
  oldingi tanlovdan ustun. Yashirin majburiy maydon xatosida bo‘limlar ochilib,
  brauzer birinchi xatoga fokus qo‘ya oladi.
- Brend: asosiy logo oldinda, maxsus logolar va tarix ixtiyoriy ochiladi.
  Namuna faqat saqlangan holatni ko‘rsatishi aniq aytilgan.
- Blog va SIT: asosiy matn/nashr amallari ochiq, rasm/ulashish/qo‘shimcha
  bo‘limlar yig‘ilgan. Universitetning barcha 7 ichki formseti va xatolari,
  blogning 13 maydoni, CKEditor va uploadlar saqlangan.
- Kutubxona legacy/V1: nom/fayl va asosiy ma’lumotlar birinchi; qidiruv
  ma’lumotlari, tarix va arxivlash alohida. Tarif/guruh qo‘shimcha sozlamalari
  yig‘ilgan; sabab/tasdiq doim ochiq.
- Dars materiallari: bir nechta resurs uchun takrorlangan HTML IDlar
  farqlandi; POST nomlari o‘zgarmadi. Matn, yordam va tugmalar reflow qiladi.
- Umumiy uslub: 44px dan kichik bo‘lmagan asosiy amallar, rem shriftlari,
  yuqori panel tugmalarining wrap’i, qorong‘i CKEditor matni kontrasti.
  Legacy fallback qobig‘ining yuqori amallari ham kesilmaydi.

## Bajarilgan browser tekshiruvi

Faqat `.tools/backoffice-stage2/demo.sqlite3` synthetic bazasi; oldingi nusxa
`.tools/backoffice-editors/before.sqlite3`. Owner bazasi, production,
to‘lov qarori va jonli nashrga tegilmagan. Vaqtinchalik renderer flaglari
sinovdan keyin oldingi qiymatiga qaytarilgan.

| Muharrir | 320px | 1280px | 200% matn |
|---|---|---|---|
| Imtihon | PASS | PASS | PASS |
| Kutubxona (legacy) | PASS | PASS | PASS |
| Tarif va guruh | PASS | PASS | PASS |
| Bosh sahifa va brend | PASS | PASS | PASS |
| Blog | PASS | PASS | PASS |
| SIT universitet/e’lon/qo‘llanma | PASS | PASS | PASS |
| Darsning eski muharriri | PASS | — | PASS |
| Kutubxona V1 | PASS | — | PASS |

200% sinov lokal QA middleware orqali har bir render qilingan matn shriftini
ikki baravar qilish bilan bajarildi (brauzer native zoom’i emas). Qo‘shimcha
root 32px sinovida exam/library/SIT inputlari 32px bo‘lib qoldi, eski 14px
uslub ularni bosmadi. 320px’da `scrollWidth == clientWidth`; ochiq qo‘shimcha
bo‘limlarda ham ko‘rinadigan elementlar ekran chegarasidan chiqmadi. Universitet
tahririda 7 formset ochiq holatda tekshirildi; duplicate ID yo‘q. Landingning
barcha 9 bo‘limi xatodan keyin ochiq holatda ham reflow qildi.

Amaliy tekshiruvlar: imtihon nomini saqlash/qayta o‘qish, blog matnini CKEditor
orqali qoralama saqlash/qayta o‘qish, landing yashirin required maydoniga fokus,
tarif yopiq required maydonining avtomatik ochilishi. Blog dark/light matn
kontrasti tekshirildi. Unified OFF fallback exam/blog/library ham tor ekranda
ko‘rildi; topbar kesilishi tuzatilib, qayta tekshirildi.

Lokal dalillar: `.tools/backoffice-editors/blog-saved-desktop.png`,
`exam-saved-phone.png`, `library-200-phone.png`, `landing-error-200.png`.
QA middleware, bazalar, log va rasmlar Gitga kirmaydi.

## Avtomatik tekshiruv

Env-file OFF, GEMINI_API_KEY va TELEGRAM_BOT_TOKEN bo‘sh:

- `venv/Scripts/python.exe manage.py test core library subscriptions blog sit
  --verbosity 1`: **1065 test, 1033 PASS, 32 skip**, 138.167s. Dastlab bitta
  eski sarlavha assertioni yiqildi; yangi ataylab tanlangan “Imtihonni tayyorlash”
  matniga yangilanib, to‘liq buyruq qayta yashil tugadi. Test susaytirilmadi.
- `node --test tests/frontend_v1/landing-editor.test.mjs
  tests/frontend_v1/backoffice-workspace.test.mjs tests/frontend_v1/library.test.mjs`:
  **20/20 PASS**.
- `manage.py check`: 0 issue. `manage.py makemigrations --check --dry-run`:
  drift yo‘q. `git diff --check`: PASS.
- Mustaqil source review: maydonlar, writer/ruxsat, revision/tasdiq,
  formset management/hidden/DELETE saqlangan. Topilgan shrift ustuvorligi
  tuzatilib, computed font bilan qayta tasdiqlandi.

## Chegaralar

Bu ekspertning lokal render/oqim tekshiruvi. Native telefon, brauzer native
zoom, screen reader, ownerning yordamsiz/vaqtli usability qabuli va production
rollout hali alohida. Barcha Django admin yoki texnik operatsiya panellari
qayta qurildi degan da’vo yo‘q. Mavjud legacy material invalid POST redirect
yo‘li o‘zgartirilmagan. Oldingi DC6/owner qabul bandlari shu ish bilan yopilmaydi.
