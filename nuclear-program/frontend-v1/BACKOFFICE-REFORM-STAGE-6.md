# Backoffice islohoti — 6-bosqich: yakuniy amaliy tekshiruv

2026-10-10. Tayanch `0808e44`. Owner foydalanish qulayligini yakuniy
tekshirishni topshirdi; yangi imkoniyatlarni kengaytirish bu bosqichga kirmaydi.

## Admission va chegara

**ADMIT — launch-critical.** Maqsad: kurs tayyorlash, o‘quvchiga yordam va
dizaynni boshqarishdagi uzilgan yoki chalkash qadamlarni topish va tuzatish.
Asosiy KPI — [T1–T8 vazifalari](BACKOFFICE-REFORM-STAGE-1.md#sakkizta-amaliy-qabul-vazifasi)
yakun dalili bilan bajarilishi. Agentning ekspert/browser tekshiruvi insonning
yordamsiz bajarish vaqti yoki owner qabuli sifatida hisoblanmaydi.

Canonical writerlar authoring, library, release, receipt, membership va design
servicelarida qoladi. Yangi model, migration, tashqi provider yoki background
vazifa rejalashtirilmagan. Tuzatishlar mavjud web adapter va taqdimot qatlamiga
cheklanadi; haftalik qo‘shimcha operatsion yuk yo‘q. Mavjud to‘rtta backoffice
flagi bilan qaytish tekshiriladi; renderer qaytishi saqlangan biznes holatini
bekor qilmaydi. Production va ownerning asosiy DB’si o‘zgartirilmaydi.

## Tekshiruv muhiti

- Ajratilgan lokal Django va synthetic ma’lumotlar. Sinov `127.0.0.1:8092`da
  boshlandi; yakuniy Back/reload tekshiruvi `127.0.0.1:8095`da bajarildi.
- DB: `.tools/backoffice-stage2/demo.sqlite3`; oldingi holatning SQLite backup’i:
  `.tools/backoffice-stage6/demo-before-acceptance.sqlite3`.
- Env fayli o‘chiq, Gemini va Telegram kalitlari bo‘sh.
- Amaliy browser sinovi: T1–T8, desktop/mobile, yorug‘/qorong‘i ko‘rinish,
  klaviatura, xato va qaytish yo‘llari. Parallel source/test auditi: ruxsat,
  navigatsiya, saqlash holati va flag kombinatsiyalari.

## Natijalar

T1–T8 ekspert sinovida bajarildi. Oltita amaliy xato tuzatildi; quyidagi dalil
agentning synthetic ma’lumotlar bilan ishlashiga tegishli. Ownerning vaqtli
sinovi, yordamsiz bajarish foizi yoki vaqtning 30% qisqarishi o‘lchanmadi.

| Vazifa | Browserda kuzatilgan yakun |
|---|---|
| T1 — kurs va darsni topish | Kerakli kurs, modul va mavjud dars ochildi; tanlangan dars konteksti saqlandi. |
| T2 — modul va dars yaratish | Synthetic kursda modul va yangi dars haqiqiy writer orqali saqlandi; modulni tahrirlashdan keyin ayni darsga qaytish tekshirildi. |
| T3 — material va namuna | Darsga material biriktirildi, o‘quvchi namunasi ochildi. Materialdan qolgan `#materials` belgisi namuna panelini berkitmaydi. |
| T4 — kirish sababini aniqlash | Madina (2), kurs 3, dars 5: hali ochilmagan dars sababi va ayni guruh/darsga vakolatli release havolasi ko‘rindi. Shu sinovda release yozuvi bajarilmadi. |
| T5 — kerakli chek va ta’sir | Aziza (3) uchun pending chek 1 topildi; synthetic PNG, qaror formasi va odam kartasiga qaytish tekshirildi. Chek bo‘yicha qaror bajarilmadi. |
| T6 — oddiy dizayn | Rang, shakl va matn tanlovlari hamda oldin/keyin namuna orqali haqiqiy qoralama saqlandi. |
| T7 — nashr va qaytish | Nashr 4 → reload → keyingi qoralamani saqlash; tarixdan nashr 3ga qaytish yangi nashr 5ni yaratdi. Private qoralama saqlanib, yangi asosda qayta saqlandi. |
| T8 — boshqa ish, Back va reload | Namuna → saqlanmagan nom → Ish stoli → Back ishladi. Reload serverdagi nom va alohida tiklash taklifini ko‘rsatdi. Tiklash → saqlashdan keyin `Bozorda suhbat · qaytish tekshirildi` qayta o‘qildi. |

T5ning maqsadi qaror ta’sirini ko‘rish edi; real pul qarori yoki synthetic
chekni tasdiqlash qabul sharti sifatida qo‘shilmadi. T4 kirish sababi va to‘g‘ri
tuzatish joyini tekshiradi; avvalgi bosqichning release → recheck dalili
[bosqich 3](BACKOFFICE-REFORM-STAGE-3.md)da qoladi.

## Topilgan va tuzatilgan olti muammo

1. **To‘liq ism bilan qidiruv.** Ism va familiya bitta maydon sifatida qidirilib,
   ko‘rinib turgan ism orqali odam topilmas edi. Har so‘z ayni ruxsatli learner
   yozuvida tekshiriladi; ism/familiya tartibi va ortiqcha bo‘shliq xalaqit bermaydi.
   Teacher scope va kurs filtri saqlanadi.
2. **Modulni o‘zgartirganda darsdan chiqib ketish.** Modul nomi yoki tartibi
   saqlangach tanlangan dars yo‘qolardi. Outline formasi va redirect manzili
   tekshirilgan kurs/dars yoki yangi dars moduli orqali quriladi. Brauzer
   qoralamasining original scope’i va aniq tiklash qarori saqlanadi.
3. **Materialdan keyingi namuna yashirinishi.** Qolgan `#materials` fragmenti
   muvaffaqiyatli preview javobini muharrir paneliga almashtirardi. Server
   belgilagan namuna paneli ustuvor; materialga oddiy qaytish muharrirni ochadi.
4. **O‘z nashridan keyingi yolg‘on to‘qnashuv.** Nashr → reload → yangi tanlovni
   saqlash eski private draft asosini yuborib 409 qaytarardi. Fresh o‘qishda
   qoralama aynan amaldagi nashrga teng bo‘lsa yangi tahrir shu nashrdan
   boshlanadi. Draft revision saqlanadi; boshqa dizayn yoki boshqa tabdagi
   yangilanishni tekshiruvchi server CAS susaytirilmagan.
5. **Qisqa sababdan keyin oynani yopib bo‘lmasligi.** Sababga 1–2 belgi
   yozilganda native minlength tekshiruvi Bekor qilish va ×ni bloklardi.
   `formnovalidate` faqat shu ikki bekor qilish tugmasiga qo‘shildi; nashr
   sabab/tasdiq validatsiyasi o‘z joyida.
6. **POST namunadan Back paytida `ERR_CACHE_MISS`.** Non-cacheable preview yoki
   xato javobidagi history yozuvi tekshirilgan ayni dars GET manziliga
   `replaceState` bilan bog‘lanadi. Ochiq namuna/xatolar almashtirilmaydi,
   POST qayta yuborilmaydi. Reload saqlangan nusxani ochadi; brauzerdagi
   matn faqat explicit tiklash bilan qo‘yiladi. Same-origin va ayni pathname
   chegarasi bor; history amali bajarilmasa qolgan qoralama boshqaruvi ishlaydi.

## Avtomatik regressiya va qaytish dalili

`core/test_backoffice_acceptance.py`dagi besh test:

- To‘rtta backoffice flagining barcha **16 kombinatsiyasi**, owner/staff uchun
  render qilingan navigatsiya va karta manzillarini haqiqatan ochish.
- Asosiy bo‘limlarning kirishlari va ichki havolalari; teacherning begona
  kurs/guruh/o‘quvchiga kira olmasligi, eski va V1 teacher rendererlarida qaytish.
- Flaglar OFF bo‘lganda yangi writer yopilishi, oldingi muharrir saqlangan
  darsni o‘qishi va ONdan keyin ayni dars tiklanishi.
- Dizayn draft/version/operation/pointer yozuvlari OFF/ON davomida saqlanishi;
  OFFda public CSS o‘chishi, ONda ayni nashr va receipt qaytishi.

Focused regressiyalar full-name qidiruvi, outline konteksti va foreign parent,
original new-lesson scope, preview fragment, xavfsiz history manzili,
post-publish asosini ham qamraydi. JS qoralama testi eski tasdiq bilan yangi
matnni o‘chirmaslik, storage failure, explicit tiklash va logoutni saqlaydi.

Barcha Python testlar env faylisiz, Gemini/Telegram kalitlari bo‘sh holda:

- `venv/Scripts/python.exe manage.py test core frontend courses.test_authoring_service library cohorts subscriptions --verbosity 1`:
  **1291 test / 1252 PASS / 39 skip**, 144.691s. Bu run oltinchi history
  tuzatishidan oldingi holat; undan keyingi o‘zgarishlar quyidagi yakuniy
  focused Python va to‘liq Node suite bilan tekshirildi.
- `venv/Scripts/python.exe manage.py test core.test_backoffice_workspace core.test_student_support_views core.test_backoffice_acceptance --verbosity 1`:
  **58/58 PASS**, 16.779s.
- `node --test tests/frontend_v1/*.test.mjs`: **146/146 PASS**.
- Design regressiya kesimi: `node --test tests/frontend_v1/backoffice-design.test.mjs`
  **15/15 PASS**; ikkala design MJS syntax tekshiruvi PASS.
- `venv/Scripts/python.exe manage.py check`: **0 issue**.
  `venv/Scripts/python.exe manage.py makemigrations --check --dry-run`:
  **No changes detected**. Yakuniy `git diff --check`: **PASS**.

Required CI va review integration bosqichida tekshiriladi. Merge faqat uchala
required check yashil, review resolve va branch main bilan yangilangan holatda;
lokal natijalar bu gate’larning o‘rniga o‘tmaydi.

## Responsive va klaviatura dalili

1440px desktopda asosiy oqimlar hamda qisqa sababdan keyingi dialogni bekor
qilish tekshirildi. 320×800 viewportda kurs muharriri, haqiqiy POST namuna
javobi va dizayn ustaxonasi horizontal overflow bermadi. Browserning haqiqiy
`innerWidth` qiymati 320 bo‘lgani tekshirildi; kursda hujjat eni 305 edi.
Qorong‘i ko‘rinishdagi dars tugmalari o‘raladi, matn va amallar ko‘rinadi.

Dizaynning Telefon + Qorong‘i namunasi o‘qiladi; unda ham hujjat eni 305,
viewport 320 edi. Mobil menyu Enter bilan ochildi; Escape dialogni yopib,
fokusni «Menyuni ochish»ga qaytardi va `aria-expanded=false` bo‘ldi.
8095dagi yakuniy tab console error/warn ro‘yxati bo‘sh.

Viewport resetidan keyin 1280px yorug‘ dars namunasi ham overflow bermadi.
Yakuniy namoyish — kurs 3/dars 5; lokal screenshot
`.tools/backoffice-stage6/final-course-preview.png` (commitga kirmaydi).
8092dagi asosiy demo server ham yangi kod bilan qayta ochildi.
Barcha breakpoint yoki native qurilma sinovi da’vo qilinmaydi; oldingi
bosqich dalillari yangi natija sifatida hisoblanmaydi.

## Yakuniy chegara

Bu kesim mavjud backoffice adapterlarini ekspert tekshiruvi va aniqlangan
amaliy regressiyalarning tuzatilishini beradi. Yangi migration, biznes writer,
provider, notification yoki doimiy operatsion vazifa qo‘shilmadi. Flaglar
default OFFligicha; joriy browser namoyishi alohida lokal muhitga tegishli.

Ownerning yordamsiz va vaqtli sinovi, native qurilma/zoom/AT/print, barcha
mustaqil legacy yuzalarning geometry pariteti, production rollout va
DESIGN-01 DC6 qabuli ochiq. Yangi savolnoma javobi bu tuzatishlarni amalga
oshirishning old sharti qilinmadi. Ekspert testi «professional darajada hamma
uchun qulay» yoki to‘liq WCAG muvofiqligi haqidagi da’voga aylantirilmaydi.
