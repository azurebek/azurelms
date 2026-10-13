# BACKOFFICE-02 / B2.6 — birgalikdagi sifat tekshiruvi

Sana: 2026-10-13. Tayanch: `de3bfa0` (B2.5). Ownerning «davom et»
topshirig‘i bilan [yagona rejadagi](BACKOFFICE-REFORM-PLAN.md#backoffice-02)
o‘nta ssenariy birgalikda tekshirildi. Holat: **10/10 lokal texnik ssenariy
PASS**. Integratsiya uchta required CI va review gate’idan keyin; ownerning
shaxsiy qabuli bu natijaga qo‘shilmagan.

Mavjud canonical state va writerlar o‘zgarmaydi. Zarur nuqson tuzatishlari
shu oqimlar bilan chegaralanadi. Yangi funksiya, provider yoki operatsion
xizmat qamrovga qo‘shilmaydi. Ownerning shaxsiy qabuli keyinga qoldirilgan;
bu texnik tekshiruvni to‘xtatmaydi.

## Ssenariylar va dalil

| № | Tekshiruv | Dalil va holat |
|---|---|---|
| 1 | Material noto‘g‘ri sana → qiymat saqlanishi → tuzatish → ayni dars | PASS. `core.test_workspace_materials` invalid date/form/draft scope, `library.test_material_authoring` invalid/stale/no-op. Browser native datetime maydoni erkin noto‘g‘ri matnni qabul qilmaydi; server-invalid dalili avtomatik testdan. Browserda nom va valid sana saqlanib, lesson9 qayta ochildi. |
| 2 | Material tartibi → namuna → darsdan olish; shared fayl qolishi | PASS. Browserda link9→1, link7→2; namuna shu tartibda. Link7 darsdan olindi, lesson10 dagi links8/10 va resource5/6 fayllari/hashlari o‘zgarmadi. Service atomic/reorder/detach regressiyasi o‘tdi. |
| 3 | Yangi exam+section, aniq ikkinchi section, ishlatilgan exam himoyasi | PASS. Imtihonsiz course7 dan exam8+section10 yaratildi; exam7/section9 saqlandi, section8 o‘zgarmadi. Used exam3 UI’da read-only. `core.test_backoffice_exam_authoring`, `courses.test_exam_authoring_service` role/replay/stale/used/race guard’lari; SQLite’da row-lock testlari skip. |
| 4 | Assignment yaratish → saqlash → reopen → yozuvsiz namuna | PASS. Browserda lesson11 assignment6 yaratildi, reload va preview; 768px/text200. `core.test_backoffice_practice`, `courses.test_practice_authoring` preview no-write, replay va scope. |
| 5 | Uch savolli quiz → xato → tuzatish → save/reopen/namuna; used guard | PASS. Birinchi savolda correct tanlanmagani haqida aniq xato, uch savol/variantlar saqlanib qoldi. Tuzatildi, quiz3 saqlandi, reload/preview uchala savolni ko‘rsatdi. Javobsiz attempt va eski natija guard’lari avtomatik testda. |
| 6 | Search → ayni dars → boshqa bo‘lim → recent; rol chegarasi | PASS. “Birinchi uchrashuv” → lesson9 → kontekstli Imtihonlar → course/lesson9 → ayni qidiruv filtri; Ish stolida shu dars recent’da. Search/recent/return regressiyalari role/session/flag/scope/tamper holatlarini qoplaydi. |
| 7 | Learner natijasi → aniq review → return → recheck | PASS. Madina/course3/lesson4 natijasidan assignment2 review ochildi, ayni kartaga qaytildi va recheck. Natija turi/tab, o‘quvchiga e’lon qilingan baho, exact exam review va POST return `core.test_student_support_*` testlarida. Browserda baho yozilmadi. |
| 8 | Delivery yo‘q/navbat/yuborilgan/xato; ko‘rishda yozuv yo‘q | PASS. Barcha holatlar, failed-only va aniq notification12 dead-letter sahifasi ko‘rildi, ayni filtrga qaytildi. Outbox/read/learner holatlari snapshot teng; hech xabar qayta yuborilmadi. |
| 9 | Design → publish → 8 forma → rollback | PASS. Stale qoralama explicit rebase → publish12; 8 formaning field18px, label16px, button32px/field12px/card16px radiuslari mos. Rollback11 → yangi13; sakkiz forma button17px/card0px va published value to‘liq tiklandi. |
| 10 | 320/768/1440px, theme, keyboard, text200, error/Back/reload/flags | PASS, quyidagi aniq muhit chegarasi bilan. Error pane/native focus, quiz alert, heading-menu/Escape/Tab; 8 legacy forma 320/768px text200, asosiy oqimlar 320/768/1440px. Four flags OFF’da legacy home200, gated course/practice/design404; ON tiklangach saqlangan test ochildi. Role/CSRF/stale/replay/Back/reload/offline matritsasi Django/Node testlarida. |

## Topilgan va tuzatilgan uch nuqson

1. Qidiruvdan ochilgan darsning kontekstli **Imtihonlar** havolasi return
   tokenni tushirib qoldirardi. Endi ro‘yxat/create/invalid/save/stale/section/
   pagination va kursga qaytish shu session-bound, allowlist bilan tekshirilgan
   tokenni saqlaydi. Writer yoki ruxsat modeli o‘zgarmadi. Uch regressiya
   qo‘shildi; eski HEAD shabloni memory loader orqali ayni testda yiqildi.
2. Telefon ko‘rinishida bo‘sh **Modul nomi** native xatosi editor panelini
   ochib, outline’dagi xato maydonini yashirardi. Endi invalid maydonning o‘z
   paneli va disclosure’i ochiladi. Browser320: `outline`, required invalid
   maydon fokusda va ko‘rinadi; qiymat/draft yozuvi o‘zgarmaydi.
3. Practice muharriridagi CKEditor toolbar 320px/text200’da 468pxgacha
   kengayardi. Practice’ga cheklangan wrapping bilan scroll/client **305/305**;
   dropdown ham sig‘adi, tugmalar yashirilmaydi. 1440pxda toolbar bitta qatorda.

Implementatsiya commitlari: `9287427`, `02823b5`. Yangi model/migration,
canonical writer, provider yoki doimiy xizmat yo‘q.

## Avtomatik tekshiruv

Quyidagi buyruqlar safe env’da bajarildi:
`AZURELMS_SKIP_ENV_FILE=1`, `APP_ENV=local`,
`LOCAL_USE_REMOTE_SERVICES=False`, `GEMINI_API_KEY=` va `TELEGRAM_BOT_TOKEN=`.

- `venv/Scripts/python.exe manage.py test core courses library bot --verbosity 1`
  — **1784 jami / 1735 PASS / 49 skip**, 148.214s. Skip: 21 row-lock,
  10 PostgreSQL backup, 17 diskdagi SQLite/bot concurrency, 1 Windows/POSIX.
- `venv/Scripts/python.exe manage.py test core.test_backoffice_return core.test_backoffice_exam_authoring core.test_backoffice_exams --verbosity 1`
  — **46/46 PASS**, 14.752s; fixning focused dalili.
- `venv/Scripts/python.exe manage.py test core.test_student_support_results core.test_student_support_delivery core.test_student_support_return core.test_student_support_evidence_views core.test_design_views core.test_design_service core.test_design_runtime --verbosity 1`
  — **139 jami / 137 PASS / 2 PostgreSQL skip**, 18.863s.
- `node --test tests/frontend_v1/*.test.mjs` — **172/172 PASS**, 619ms;
  native invalid regression fixdan oldin 13/14, keyin 14/14.
- `venv/Scripts/python.exe manage.py check` — 0 issue;
  `venv/Scripts/python.exe manage.py makemigrations --check --dry-run` — drift yo‘q;
  `git diff --check` PASS. Independent product diff review: actionable finding0.

## Browser va ma’lumot saqlanishi

IAB synthetic8104; mavjud synthetic hisob/ruxsatlar saqlandi. Nav/course/
practice/design flaglari tekshiruvdan keyin ON. Eski frontend library/editors
flaglari OFF; navigation ON bo‘lgani uchun sakkiz eski forma rendereri yangi
boshqaruv qobig‘ida ko‘rildi.
Matn sinovi computed shriftni 2x oshiruvchi fixture tugmasi bilan; iframe yoki
native zoom deb talqin qilinmaydi. Light/dark va keyboard representative
holatlarda; bu barcha yordamchi texnologiyalar sertifikati emas.

Sakkiz legacy forma 320/768px text200’da horizontal document overflow0.
Asosiy course/quiz/results/design oqimlari 320/768/1440px text200; quiz
overflow tuzatildi. Course320’da 1px subpixel farq, kesilgan amal/matn yo‘q.
Browser console’da unexpected error0 (flag OFF’dagi kutilgan404 alohida).

- Synthetic final: **148 jadval / 1261 qator**, 134 jadval o‘zgarmagan,
  46 ruxsatli row-change, unexpected0; ikkala shared PDF hash teng.
  Ruxsatli o‘zgarishlar: yangi authoring obyektlari, ayni dars materiallari,
  section9, design/flag/audit/session. Eski natija, bildirishnoma, read belgisi,
  auth/ruxsat, brend va legacy kontent saqlandi. Design13 original11 qiymatiga teng.
- Primary local smoke: **23 GET / HTTP200**, **149 jadval / 1316 qator**
  oldin/keyin hash teng; public1/private2 media teng. Mavjud owner login/recent/
  initializer yozuvlari bitta transaction’da rollback qilindi. Tarmoq va media
  yozuvlari bloklangan; flag/parol o‘zgarmadi. Tanlangan primary kursda existing
  exam yo‘q, exam list/new-form GET tekshirildi; hech imtihon yaratilmagan.
- Lokal server8092 yangi kod bilan qayta ishga tushirildi. Default flag
  qiymatlari o‘zgarmadi; primary’da avval yoqilgan beshta B2 gate ON saqlandi.

Ignored dalillar `.tools/backoffice-b26/` ichida: `fixture-report.json`,
`route-smoke-report.json`, `design-consumers.json`, `design-rollback.json`,
`responsive.json`, `flow-layouts.json` (quiz tuzatishidan oldingi o‘lchov),
`final-state.json`, `final-invariants.json`, `local-smoke-report.json`,
`quiz-320-text200-fixed.png`, `quiz-preview-final.png`. Test loglari `.tools/`
ichida `b26-final-tests.log`, `b26-node-tests.log`, `b26-support-design-tests.log`.
Ular repositoryga DB/media yoki shaxsiy eksport sifatida qo‘shilmaydi.

## Muhit va chegaralar

Brauzerda alohida `.tools/backoffice-b26/` synthetic nusxa ishlatiladi.
Asosiy lokal bazaga sinov kontenti yoki natija yozilmaydi. Testlar env-file
OFF, `APP_ENV=local`, remote services OFF va Gemini/Telegram kalitlari bo‘sh
holatda ishlaydi. Haqiqiy xabar yuborish yoki pulli provider chaqiruvi yo‘q.

Native telefon, browser zoom, screen reader, owner usability va production
rollout alohida OPEN. Material/imtihonning to‘liq builderi, ishlatilgan
kontentni keng versiyalash, vendor/print va A2 AI audit qarzi B2 scope’idan
tashqarida; bu qayd ularni bajarilgan deb belgilamaydi.
