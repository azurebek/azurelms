# Frontend V1 — bajarish va qabul jurnali

Qabul: `[ ]` ochiq; `[-]` ishda; `[x] ~~...~~` dalil bilan tugagan.
“Prototype bor” real portga `[x]` qo‘yish uchun yetmaydi.
Sana emas, tugallangan natija bilan kuzatiladi. I1/I2/I3 main’da;
I4a PR #125 bilan main’da (`89f89b7`); final CI `36170298967` uchala PASS.
Flaglar default OFF. Ushbu port doirasida deploy hali 0.

## Navbat

- [x] ~~I0 — V1 freeze, zaxira reference, joriy inventar, mapping, baseline va reja.~~
  2026-09-25: 95 preview → 76 source UI name, 54 template; 44 unmapped UI/alias.
  [Inventar](INVENTORY.md), [strategiya](README.md). Runtime o‘zgartirilmagan.
- [x] ~~I1 — V1 foundation + login/dashboard/my-courses.~~
  [PR #120](https://github.com/azurebek/azurelms/pull/120) main’da: `b991a68`.
  Required CI run `36082949974`: uchala job PASS. Lokal full 1846 test
  OK (skipped=41); audit 107 dependency / 0 advisory. Deploy qilinmadi.
  [Adapter dalili](I1-LEARNING-SHELL.md).
  Flag OFF: existing
  UI ishlaydi. Flag ON: haqiqiy user va real enrollmentlar; logout POST,
  CSRF, safe next, role menu, empty/multi-course, theme/draft isolation.
- [x] ~~I2 — O‘qish/material + teacher home/release.~~ Real lesson kontenti,
  cohort saqlanishi, direct private file gate; teacher open/lock→student
  read/write/file. Assignment/quiz mavjud funksiyasi saqlanmasa I2 yopilmaydi.
  - [x] ~~I2a: matn/video/material + teacher home/release.~~ PR #121,
    `5528c74`, required CI `36086594312` uchala PASS.
    [Implementatsiya va dalil](I2-LESSON-RELEASE.md).
  - [x] ~~I2b implementatsiya va lokal tekshiruv: assignment/quizli dars.~~
    `7e2efb6`; 1879 Python OK (skip=42), 28 Node PASS; native yuborish,
    review status, latest result, private fayl va scoped qoralama.
    [Dalil va cheklovlar](I2B-PRACTICE.md).
  - [x] ~~I2b required CI va integratsiya.~~ PR #122 MERGED `c8c3864`;
    final CI `36089727327` uchala PASS: SQLite1882 skip41,
    PostgreSQL1882 skip20, Node28. I2 yopildi, R1 release ochiq.
- [ ] **R1 — Birinchi ishlaydigan bo‘lakni chiqarish.** I1+I2ning relevant
  test/browser, required CI, staging, deploy smoke va rollbacki. I3–I9ni kutmaydi.
- [x] ~~I3 — Teacher review + ro‘yxatlar/davomat.~~ Learner assignment/quiz
  qismi I2bda ulandi.
  - [x] ~~I3a lokal implementatsiya: navbat → yozma ish qarori → learner natijasi.~~
    Native CSRF/PRG, explicit tasdiq, stale/duplicate no-write, canonical XP.
    [Dalil va cheklovlar](I3A-TEACHER-REVIEW.md).
  - [x] ~~I3a required CI va integratsiya.~~ PR #123 MERGED `4e48416`;
    final CI `36092407070` uchala PASS: SQLite1898 skip42,
    PostgreSQL1898 skip20, Node31.
  - [x] ~~I3b lokal implementatsiya: kurslar/guruhlar/o‘quvchilar/davomat.~~
    Real scope/count/search/pagination; native atomic davomat va canonical XP,
    stale/duplicate no-write, session-scoped qoralama. [Dalil](I3B-TEACHER-DIRECTORY.md).
  - [x] ~~I3b required CI va integratsiya.~~ PR #124 MERGED `9eb3830`;
    final CI `36162882956` uchala PASS: SQLite1914 skip44,
    PostgreSQL1914 skip20, Node34. Resume/finish locking P2 regression yopilgan.
- [-] **I4 — Messenger B.** Guruh/ustoz: real room/history/send/edit/delete/
  attachment/reconnect; AI: mavjud provider/choice/quota/context/error.
  Qoralama saqlansin, layout barcha gap holatlarida ishlasin; yangi AI engine yo‘q.
  - [x] ~~I4a lokal implementatsiya va tekshiruv: guruh/ustoz human chat.~~
    Tasdiqlangan B layout, canonical socket/HTTP/private fayl, multi-room,
    session draft, unknown no-resend va atomic stale edit/delete.
    [Dalil](I4A-HUMAN-MESSENGER.md).
  - [x] ~~I4a required CI va integratsiya.~~ PR #125 MERGED `89f89b7`;
    final CI `36170298967`: SQLite1931 skip44, PostgreSQL1931 skip20, Node45.
  - [ ] I4b AI adapteri: provider/choice/quota/context/error va mavjud amallar.
- [-] **I5 — Tayyor yordamchi yuzalar.** 5a public/records/help,
  5b auth/account/profile, 5c preferences/privacy/notifications. Har kichik
  tugallangan oqim alohida qabul; hammasi bir relizga bog‘lanmaydi.
  - [-] I5a-public: owner qarori bilan I4bdan oldin. Barcha 14 public route
    oilasi → `azurebek.me` release qabuli → I4bga qaytish. [Dalil](I5A-PUBLIC.md).
    Lokal runtime `74818ee`: 1945 Python OK (skip45), 53 Node PASS.
    Owner ko‘rsatgan mobil header tuzatildi; required CI/integratsiya va
    real-content/AWS go-no-go ochiq. Hali deploy qilinmagan.
    Records/help bu public portga aralashtirilmaydi, keyingi yordamchi paketda.
- [ ] **I6 — Library + course/lesson editor.** Common resource/link/private
  storage parity; real forms existing fieldsni saqlaydi. Qisman field/save
  contract mos kelmasa tegishli editor legacy qoladi va qarz ochiq yoziladi.
- [ ] **I7 — Checkout/receipt.** Quote→upload→pending→owner decision→access;
  difference/rejected, direct URL permission, duplicate/unknown reconciliation.
- [ ] **I8 — Exam va teacher review.** Real attempt/audio/timer/revision,
  save/submit/review/publication; backend natijasi o‘zgarmaydi.
- [ ] **I9 — Classbook.** Preparation→session→activity→result; multi-user,
  late join/reconnect va 10 exercise type’ning tegishli adapterlari.
- [ ] **R-next — Har qo‘shimcha tayyor bo‘lakning o‘z release qabuli.** R1
  shartlari qaytariladi; oldingi ishlaydigan release keyingisini kutmaydi.
- [ ] **P-resume — Tanlangan V1 ko‘chirish/relizidan so‘ng prototip ishiga qaytish.**
  Q14dan yangi oilalar; Q02–Q12 ochiq qarzlari yo‘qolmaydi. 1-oktyabrgacha
  faqat ulgurgan va gate’dan o‘tgan qo‘shimcha natija, majburiy yangi redesign yo‘q.

## Portdan oldingi fresh tekshiruv — 2026-09-25

Runtime source: `d0cce32`. Production kod o‘zgarmagan.

| Tekshiruv | Natija | Chegara |
|---|---|---|
| Root `venv\Scripts\python.exe manage.py check` | 0 issue | Local offline profile, deploy check emas |
| Root `venv\Scripts\python.exe manage.py test core.test_golden_flow_e2e courses.test_locked_lesson_write_gate courses.test_lesson_release courses.test_lesson_completion library.test_student_access --noinput --verbosity 1` | 46 PASS | Existing real domain regression; yangi UI testi emas |
| Trial `..\..\venv\Scripts\python.exe manage.py test --verbosity 1 --noinput` | 590 PASS; 216.100 s | Synthetic isolated preview, real DB/provider emas |
| Root `node --test "playground/Eleventh Trial/tests/*.test.mjs"` | 164 PASS | Pure/local JS; production socket/AI emas |
| Inventar/link tekshiruvi + `git diff --check` | PASS | 95 preview ID va 120 source UI nomi hujjatda; 6 local link; source SHA mos |

Root tekshiruvlarda `AZURELMS_SKIP_ENV_FILE=1`, `GEMINI_API_KEY=''`,
`TELEGRAM_BOT_TOKEN=''`. Test DB vaqtinchalik; current DBga seed/migrate yo‘q.
Baseline vaqtida full root suite yugurilmagan edi. Keyingi I1/I2a/I2b
full natijalari tegishli dalil hujjatlarida. 18-sentabr marinebook’da Windows
fontTools/DLL bilan bog‘liq `ai.documents` failure’lari bor; yangi full CI
natijasi ularni taxminan PASS deb almashtirmaydi.

## Har implementatsiya yozuvi uchun shablon

```text
ID / sana / status:
Source va target URL/template/controller:
Read context va POST/file/socket endpoint mapping:
Changed files / commit / PR:
Canonical service va saqlangan invariants:
Flag OFF/ON hamda rollback dalili:
Command → aniq pass/fail/skipped:
Browser/device/theme/viewport → natija:
Qolgan blocker yoki qabul qilingan kosmetik qarz:
CI / staging / deployed SHA / smoke / owner go-no-go:
```

## Hozir ochiq release ma’lumotlari

2026-09-25 owner javobi: **alohida staging yo‘q, faqat AWS asosiy server bor**.
Bu deploy yoki yangi UI flaglarini yoqishga ruxsat emas. Target SHA, xavfsiz
sinov hisobi/dataset, zaxira va rollout/rollback usuli, haqiqiy mobil qurilma
sinovchisi va owner go/no-go release oldidan aniqlanadi. Yangi pulli muhit
ochish yoki productionda sinov yozuvlari yaratish alohida kelishiladi;
secrets hujjatga yozilmaydi.
