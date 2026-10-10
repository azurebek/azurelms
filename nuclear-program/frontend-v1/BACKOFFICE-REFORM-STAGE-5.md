# Backoffice islohoti — 5-bosqich

2026-10-10. Tayanch `45d94b9`; owner qolgan backoffice bo‘limlarini ulashni so‘radi.

## Admission

**ADMIT — launch-critical.** Owner kurs/dizayn ustaxonasidan to‘lov, guruh,
ochiq kontent yoki sozlamaga o‘tganda joyini yo‘qotmasligi kerak.
KPI: rejaning sakkiz amaliy vazifasida kerakli kirishni yordamsiz topish;
inson sinovi hali o‘tkazilmadi, avtomatik testlar bu qabulning o‘rniga o‘tmaydi.

Yangi qatlam faqat navigatsiya va o‘qish: To‘lovlar, Sayt va dizayn,
Sozlamalar markazlari; alohida Guruhlar va Tariflar ro‘yxatlari. Yagona
yozuvchilar receipt_service, membership_service, catalog_service, mavjud
core/SIT/blog formalaridir. Ularning ruxsat, sabab, tasdiq va audit
shartnomalari saqlanadi; yangi biznes qoidasi yoki ma’lumot modeli yo‘q.

`backoffice_unified_navigation` default OFF: ON yangi kirishlar va umumiy
qobiq, OFF avvalgi ko‘rinish. Bu renderer flagi; amaldagi eski POST yozuvchisi
o‘zgarmaydi va biznes qarorini ortga qaytarmaydi. Yangi markazlar faqat GET,
private/no-store; flag OFF bo‘lsa 404. Migratsiya, tashqi provider yoki
production deploy yo‘q. Haftalik yangi xizmat vazifasi qo‘shilmaydi.

## Qamrov va tekshiruv rejasi

- Bir xil asosiy menyu, tegishli bo‘lim ichki yo‘llari, aniq faol belgi.
- Owner va staff kirishlari farqlanadi; kurs/guruhlar canonical teacher scope.
- To‘lov cheki bilan tarif, guruh bilan narx bitta ro‘yxatga yig‘ilmaydi.
- Eski deep linklar va form actionlar saqlanadi; plan/guruh muvaffaqiyatidan
  keyin tegishli yangi ro‘yxatga qaytish faqat flag ON holatida.
- Blog author scope va SIT owner gate o‘zgarmaydi. AI audit qarzi yopildi
  degan claim yo‘q; texnik tafsilotlar ochiladigan bo‘limga olinadi.
- Permission/flag/route/GET zero-write, form action va audit pariteti,
  desktop/mobile/theme/keyboard hamda haqiqiy synthetic amal bilan sinov.
- Oldingi V1 teacher/library rendererlarining revision va confirmation
  maydonlari saqlanadi; ularning chuqur muharrirlari alohida qobiqda qolishi
  mumkin, ularga kirish va boshqaruvga qaytish aniq bo‘lishi kerak.

## Amalga oshirilgan chegara

[Barcha ko‘chirilgan kirishlar va writerlar](BACKOFFICE-REFORM-STAGE-5-MAP.md).
Asosiy menyu stage2–4 ustaxonalari hamda legacy core/catalog/SIT/blog
sahifalarida bir xil. Kurs ichidan guruh qidiruvi kurs nomi bilan ochiladi;
yopiq guruhda ishlamaydigan davomat/release havolasi berilmaydi. A’zolar va
guruh sozlamalari owner uchun qoladi; to‘lgan guruh faol bo‘lishi mumkin.
Tarif sig‘imi mutlaq maksimum emas, standart sifatida ko‘rsatiladi.

Legacy sahifalar mavjud bo/page blocks, CSRF, media, formset va scriptlarni
saqlaydi. Eski global shell scriptlari yangi shellga qo‘shilmaydi; faqat
content ichidagi CSS moslashtirish va native validation disclosure reveal
bor. Brand mark canonical componentdan o‘qiladi. Blogda oddiy til faqat
label/placeholder presentationi; form validation va nashr qarori o‘zgarmaydi.

Runtime’da 7 mustaqil forma yopiq task bo‘limlari; invalid/bound forma ochiq.
Xizmat kaliti, AI narxi va kerakli texnik diagnostika ham alohida ochiladi.
Sabab/tasdiq/ta’sir olib tashlanmagan. Blog/SIT forma va statuslari saqlangan;
AI settingsning oldingi umumiy audit qarzi bu UI ishi bilan yopilmaydi.

Yangi GET markazlari domain state yozmaydi. Testda umumiy SiteSettings,
AuthPageSettings va LandingPage oldindan yaratilgan; global context loaderning
tarixiy singleton yaratish xatti-harakati bu da’voga kirmaydi.

## Lokal browser dalili

Faqat ajratilgan `.tools/backoffice-stage2/demo.sqlite3`, oldindan SQLite
backup: `.tools/backoffice-stage5/demo-before-navigation.sqlite3`.
Ownerning asosiy DB’si yoki production o‘zgartirilmagan. Stage5 flag ON.

- Sozlamalar → muddat → 30 dan 35 daqiqaga saqlash → qayta ochish: qiymat35,
  muvaffaqiyat xabari va sababli audit satri ko‘rindi.
- Kurslar → Guruhlar → «Yangi qulay guruh · sinov» yaratish: Standard,8 joy,
  aniq kurs. Saqlangach yangi guruhlar ro‘yxatiga qaytdi.
- Blog → yangi maqola → CKEditor matn → qoralama saqlash: muvaffaqiyat
  xabari, edit URL va ayni matn qaytdi; nashr holati Qoralama bo‘lib qoldi.
- 320px: guruh/tarif ro‘yxati, plan/guruh editor, settings hub/runtime/AI,
  flags, control, brand, blog, SIT yuzalari; sahifa horizontal overflow yo‘q.
  SIT tabs dastlab ichki scroller edi, barcha tablar ko‘rinishi uchun wrap qilindi.
- Mobile Enter menyuni ochadi, Escape yopadi; dark/light tanlovi o‘tishlarda
  saqlanadi. 1440px desktopda umumiy shell va SIT ko‘rildi. Browser console
  error/warn topilmadi. Bu real qurilma yoki inson usability qabuli emas.

## Test dalili

Barcha Python testlarda env-file OFF; Gemini/Telegram tokenlari bo‘sh.
Yangi hub testlari permission, flag mustaqilligi, private/no-store, domain
zero-write, teacher scope, pagination, eski route renderi, blog author
chegarasi, canonical logo va yopiq guruh havolalarini tekshiradi.
Catalog testlari ON/OFF redirect, audit, invalid input, focused member POST
va support recheckni; settings testlari control/payload pariteti hamda error
bo‘limining ochilishini tekshiradi.

Dastlabki app run: 1289 test, bitta contract failure — canonical logo testi
oldingi base fayli yo‘lini tekshirardi. Tekshiruv haqiqiy legacy va workspace
rendererlariga ko‘chirildi, yangi shell uchun saqlangan logo render testi ham
qo‘shildi. Test susaytirilmagan. Yakuniy natijalar integration oldidan yoziladi.

`node --test tests/frontend_v1/*.test.mjs`: 142/142 PASS.

Yakuniy `venv/Scripts/python.exe manage.py test core frontend subscriptions blog sit library cohorts --verbosity 1`:
**1295 test / 1257 PASS / 38 skip**, 97.859s. Kalitsiz AI fallback loglari
kutilgan test holatlari; failure yo‘q. `manage.py check`: 0 issue;
`manage.py makemigrations --check --dry-run`: No changes detected.
`node --check static/backoffice/legacy-workspace.js`, `git diff --check`: PASS.
Blog focused suite 9/9, settings va operational focused suite 28/28,
catalog navigation 7/7; barchasi yakuniy app suite ichida ham tekshirildi.
Required CI, review va merge integration bosqichida tekshiriladi.
