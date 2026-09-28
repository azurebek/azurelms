# Q08 — sana bo‘yicha davomat va eski paritet bandlari

2026-09-28, Packet77; base `b2ba464`, branch `codex/q08-dated-attendance`.
Owner D33: iPhone Chrome chat klaviaturasi va auditdagi UX nuqsonlarini
yakuniy tuzatish ro‘yxatiga yozib, prototip rejasini davom ettirish.
**Faqat lokal EXPERIMENT.** Canonical runtime, DB, AWS va provider o‘zgarmadi.

## U42: alohida sana varag‘i

`http://127.0.0.1:8082/users/attendance/manage/` — teacher shell, yangi
palette yoki navigation emas. Manba `users.views.AttendanceManageView`,
`cohorts.attendance_service.upsert_attendance_and_xp`; bu URL latest-record
teacher sahifasining aliasi emas, unga redirect qilinmadi.

- Explicit GET: `cohort_id`, `lesson_id`, ISO `date`. Guruh o‘zgarganda
  o‘zining birinchi darsi, dars/sana o‘zgarganda aynan tanlangan varaq.
  Invalid/duplicate/foreign query400, noto‘g‘ri sana bugunga jim almashtirilmaydi.
- 6/6/22 synthetic roster, uch holat. Qayd yo‘q bo‘lsa source kabi “Kelmadi”
  taklif qilinadi; GET hech narsa yozmaydi. Native CSRF POST →303→natija.
  To‘liq ro‘yxat va alohida tasdiq; noto‘g‘ri/missing mark butun yozuvni rad etadi.
- Bitta **dated ledger**. Existing teacher sahifasi shundan eng so‘nggi
  sanani ko‘rsatadi; learner faqat o‘z tarixini ko‘radi. Eski sanani tahrirlash
  yangi sanani almashtirmaydi. XP, progress, streak, release, notification
  yoki real enrollment huquqi fixture tomonidan hisoblanmaydi.
- Exact run/sheet revision/UUID/payload: stale409, duplicate no-write,
  no-op revisionni oshirmaydi. Bitta saqlashning immutable receipt’i keyingi
  tahrirdan keyin ham o‘zgarmaydi. Uncertain503 → faqat shu natija uchun GET;
  qayta POST yo‘q. Reset/cross-session/cross-date receipt ishlamaydi.
- Tab qoralamasi run/sheet/date/revisionga ajratilgan; reload’da belgilar
  tiklanadi, tasdiq tiklanmaydi. Qo‘llanmagan filtr eski varaqni saqlashni
  bloklaydi. Native forma JSsiz ham server validatsiyasi bilan ishlaydi;
  bu o‘chirilgan JS bilan haqiqiy device testi degani emas.
- Memory-only 60 dated operation chegarasi preview texnik qo‘riqchisi;
  production siyosati emas. Real atomicity/XP/RBAC/durable receipt shu mock
  orqali kafolatlanmaydi; port alohida canonical adapter/test admission oladi.

Registry: **139 named URL /77 page template /118 source nomi /1223 route-state
/206 action**, bundan alohida3 handler diagnostic. Boshlang‘ich42 UI+3handler
inventarida endi prototipi umuman yo‘q manzil qolmadi. Bu barcha amallar,
real port yoki native qabul yakunlandi degani emas.

## 4-bo‘lim eski tracker pariteti — qarzlarni qayta tasniflash

`EXISTING EVIDENCE` — oldingi dalil qayta ishlatiladi, bugun real xizmat qayta
sinovdan o‘tdi degani emas. `MISSING STATE` — mavjud sahifa ichidagi ochiq
farq; yangi URL emas. `CAPABILITY / ACCEPTANCE OPEN` — yangi vakolat yoki
haqiqiy qurilma/xizmat qabuli; UI screenshot bilan yopilmaydi.

| Eski band | Dalil / ko‘rilgan source | Qolgan aniq holat |
|---|---|---|
| Q02 public/katalog | Packet24–26; [I5a](I5A-PUBLIC.md) native GET pagination, multi-record, safe return va320px menu; [I7](I7-CHECKOUT.md) initial enrollment | EXISTING EVIDENCE. Public logged-in header/CTA/filter ishqalanishi final UX-06; native va owner kontenti OPEN. Eski 390px bandi yangi URL emas. |
| Q03 blog/SIT/legal | Packet27–30,72–74; [I5a](I5A-PUBLIC.md) real comments/reactions, Packet73 rich sanitization va74 source formsets/public readback | EXISTING EVIDENCE + MISSING STATE: eski previewda comments/clap kabi public interactionning real adapterga to‘liq tengligi hali yo‘q; real adapter dalili alohida. Program/advisor/application chiqishi va real editorial/legal kontent owner qabuli OPEN, uch yangi URL deb sanalmaydi. |
| Q04 dars/material/vazifa | Packet31–33, [I2](I2-LESSON-RELEASE.md), [I2b](I2B-PRACTICE.md), [I3a](I3A-TEACHER-REVIEW.md); shared synthetic attachment/review tests | EXISTING EVIDENCE. Real telefonda file/audio/Back/permission, AT va xizmat chegaralari ACCEPTANCE OPEN. Predecessor-only qulf xulqi RULE-01: owner product qarori, prototipda yangi access formulasi yozilmadi. |
| Q05–Q06 messenger | Packet34–40 va tasdiqlangan wide B; [I4a](I4A-HUMAN-MESSENGER.md), [I4b](I4B-AI-MESSENGER.md) | MISSING STATE: frozen preview doimiy feedback/copy qatori; real I4b owner qaroriga ko‘ra long-press/right-click/Shift+F10/⋯. Finalda yangi redesign emas, approved delta moslashtiriladi. iPhone Chrome keyboard UX-01 OPEN. Real provider/socket/private-file/native/AT va source’da yo‘q reply capability alohida. |
| Q07 checkout | Packet41; [I7](I7-CHECKOUT.md), Packet68 owner receipt qarori, Packet69 difference request | EXISTING EVIDENCE. Real rejected receipt canonical’da o‘chirilishi preview persistent rejected namunasi bilan teng emas — final parityda saqlanadi. Quote/price/card real-content/transfer owner qabuli OPEN; UX-03 va DATA-01. |
| Q08 account/records | Packet42–46; [I5b](I5B-ACCOUNT-PROFILE.md), [I5c](I5C-SETTINGS.md), [I5d](I5D-RECORDS-SUPPORT.md); Packet77 U42 | U42 LOCAL BUILT. Real privacy/memory/password delivery/device/RBAC qabuli OPEN; registratsiya/intro UX-04 alohida. Q08ning eski katta checkbox’i avtomatik to‘liq qabul qilinmaydi. |
| Q09–Q10 Classbook | Packet47–50; [I9a](I9A-PREPARATION.md), [I9b](I9B-LIVE.md); preparation/live scoped tests | EXISTING EVIDENCE. Real multi-user/device/Telegram delivery va owner dars qabuli OPEN. Mashq/playbook maketi qayta qurilmadi. |
| Q11–Q12 course/lesson | Packet51+; [I6b](I6B-COURSE-LESSON-EDITORS.md): real14 course/6 lesson maydoni, canonical module scope | MISSING STATE: eski prototype4 course field, real adapter14; finalda maydon xaritasi/delta ko‘rib chiqiladi,10 field yo‘qolgandek da’vo qilinmaydi. Assignment/quiz/general module authoring CAPABILITY OPEN, yashirin yangi feature emas. |
| Q13 library | Packet61–65; [I6a](I6A-LIBRARY.md), [I6b](I6B-COURSE-LESSON-EDITORS.md); picker/per-link/81 learner regression | EXISTING EVIDENCE. Q13 qayta ochilmadi. Yangi muharrirlardan picker handoff umumiy final matrixga kiradi; native upload/durable storage acceptance OPEN. |
| Exam result/review | `tests.test_exam_review.test_save_does_not_publish_and_public_payload_omits_draft_and_ledger`; [I8c](I8C-REVIEW.md) | EXISTING EVIDENCE: draft o‘quvchiga chiqmaydi, faqat explicit publish. MISSING STATE: real reviewed attempt re-reviewni qo‘llaydi; eski previewda qayta baholash yo‘q. Final parityda shu farq ochiq, grading formulasi ixtiro qilinmadi. |
| Keyingi capability chegaralari | [Q14](Q14-EXAM-EDITOR-PROTOTYPE.md), [Q16a](Q16A-CONTROL-PROTOTYPE.md), [DESIGN-01](DESIGN-CUSTOMIZATION-PLAN.md) | Keng savol/ko‘p-bo‘lim/nashr, U17/A2-D01 audit-retrofit va legacy admin enabled inventari OPEN. DESIGN-01 owner qo‘shgan12-qadam; bu paketda qurilmadi. |

Shu jadval 10-qadamning “har ochiq holatga dalil yoki aniq ochiq qaror”
mezonidir. **Q20/Q21 yoki G2/G3 PASS emas.** Missing-state bandlari
11-qadamda kuzatiladi; scope owner nomidan chiqarib tashlanmadi.
[Yakuniy tuzatishlar](FINAL-ACCEPTANCE-ISSUES.md) va bu jadval birga o‘qiladi.

## Tekshiruv va saqlash

Trial cwd: `playground/Eleventh Trial`; root venv, `.env` o‘qilmaydi,
`AZURELMS_SKIP_ENV_FILE=1`, `GEMINI_API_KEY=` va `TELEGRAM_BOT_TOKEN=`.

- Full `python manage.py test tests --verbosity 1`: **823 PASS**,488.684s,
  check0. Oxirgi header-context aniqligi keyingi focused test bilan tekshirildi.
- Final focused `test tests.test_attendance_manage tests.test_teacher_attendance
  tests.test_preview.PreviewTests.test_registry_uniqueness_and_required_metadata
  tests.test_preview.PreviewTests.test_teacher_primary_navigation_never_switches_to_learner
  --verbosity 1`: **52 PASS**,12.550s; check0.
- Node `node --test tests/*.test.mjs`: **197 PASS**,0 skipped.
- Dastlab generic form allowlist/action metadata testlari yangi sahifa uchun
  to‘liq emas edi: aniq native GET/POST kontrakti va metadata qo‘shildi.
  Strict teacher-only URL uchun workspace override yuborilmaydi; source
  query kontrakti yumshatilmadi. Root cwd’dan `test tests`0 topdi; suite
  trial cwd’dan qayta ishga tushirildi va README bu farqni aniq ko‘rsatadi.
- IAB normal6/long22 roster ×8 width(320/390/639/640/768/1023/1024/1280)
  ×2 theme: **32 tekshiruv**, document overflow0, asosiy forma controls va
  checkbox label≥44px. Har text link uchun44px da’vo qilinmaydi.
- Browser: local draft/reload/unchecked consent, unapplied-date guard,
  keyboard native save→receipt, boshqa sanada no-record, group8/22 roster,
  uncertain503→faqat GET→aniq22-row receipt. Initial pointer automation
  izchil ishlamagani sabab keyboard bilan davom etildi; native touch qabuli
  da’vo qilinmaydi. Navigation tugamasdan olingan/theme tasdiqlanmagan
  o‘lchovlar32 soniga kiritilmadi. Console yakunida warn/error0.
- `computer-use` tekshiruvi headerdagi stale default group/stage yozuvini
  ko‘rsatdi; page context tanlangan guruh va Q08 bosqichiga moslashtirildi.
  Screenshot `evidence/packet-77-mobile.png`, `packet-77-desktop.png`,
  `packet-77-responsive.json`; viewport reset,8082 preview ochiq qoldi.

Canonical real port, AWS, haqiqiy device/date-picker/keyboard/AT qabuli OPEN.
Keyingi navbat: **11. umumiy qabul va tuzatishlar →12. DESIGN-01**.

## Lokal checkpoint

`playground/Eleventh Trial/checkpoints/packet-77-20260928-051620.zip`:
**620 fayl**, har ZIP entry SHA256 asl fayl bilan tekshirildi.
ZIP SHA256 `F6EF0CBA50CBF1BCCB142A71B6AF741186C81EEAB9E6DC2A1C46898040BA08DD`.
Packet76/plan-remaining va oldingi nusxalar o‘chirilmagan. Bir diskdagi
checkpoint mustaqil disaster-recovery backup emas. Ignored source Gitga
force-add/push/upload qilinmadi; tracked PR faqat evidence/reja/jurnal.
