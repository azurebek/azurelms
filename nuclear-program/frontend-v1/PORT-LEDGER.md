# Frontend V1 — bajarish va qabul jurnali

Qabul: `[ ]` ochiq; `[-]` ishda; `[x] ~~...~~` dalil bilan tugagan.
“Prototype bor” real portga `[x]` qo‘yish uchun yetmaydi.
Sana emas, tugallangan natija bilan kuzatiladi. I1/I2/I3 main’da;
I4a PR #125 bilan main’da (`89f89b7`); final CI `36170298967` uchala PASS.
Flaglar kodda default OFF. AWS `363ff95`: public, learning, lesson,
teacher va human messenger V1 override ON. [R1-public](R1-PUBLIC-RELEASE.md),
[ichki rollout dalili](R1-INTERNAL-RELEASE.md). Hisob/settings va boshqa
ko‘chirilmagan yuzalar legacy; barcha sahifa yangi degani emas.

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
- [-] **R1 — Birinchi ishlaydigan bo‘lakni chiqarish.** I1+I2ning relevant
  test/browser, required CI, staging, deploy smoke va rollbacki. I3–I9ni kutmaydi.
  - [x] ~~Owner ustuvor qilgan R1-public texnik relizi.~~ AWS `363ff95`;
    backup/restore/schema drill, clean image, public ON, HTTPS/mobile va
    renderer OFF/ON rollback PASS. [Dalil](R1-PUBLIC-RELEASE.md).
  - [x] ~~Owner tasdiqlagan learning/lesson/teacher/human messenger texnik rollout.~~
    HTTPS synthetic login → release/material → submission/review/quiz,
    WSS send/edit/stale409, to‘rt renderer rollback; 320/1280 browser PASS.
    [Dalil va inactive sinov yozuvlari](R1-INTERNAL-RELEASE.md).
  - [ ] Haqiqiy Android/iOS va owner real-content qabuli.
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
- [x] ~~I4 — Messenger B kod integratsiyasi.~~ Guruh/ustoz: real room/history/send/edit/delete/
  attachment/reconnect; AI: mavjud provider/choice/quota/context/error.
  Qoralama saqlansin, layout barcha gap holatlarida ishlasin; yangi AI engine yo‘q.
  - [x] ~~I4a lokal implementatsiya va tekshiruv: guruh/ustoz human chat.~~
    Tasdiqlangan B layout, canonical socket/HTTP/private fayl, multi-room,
    session draft, unknown no-resend va atomic stale edit/delete.
    [Dalil](I4A-HUMAN-MESSENGER.md).
  - [x] ~~I4a required CI va integratsiya.~~ PR #125 MERGED `89f89b7`;
    final CI `36170298967`: SQLite1931 skip44, PostgreSQL1931 skip20, Node45.
  - [x] ~~I4b lokal AI adapteri va tekshiruv.~~ Alohida default-OFF flag,
    canonical model/skill/context/status/feedback/retry; owner so‘ragan
    ixcham transcript va xabar menyusi. [Dalil](I4B-AI-MESSENGER.md).
    1961 Python OK (skip45), 61 Node PASS; browser320/1280, fake provider.
  - [x] ~~I4b required CI/review/integratsiya.~~ PR #130 MERGED `a25cf4b`;
    final CI `36192585672` uchala PASS; accessibility P2 fix `1910aed`,
    61 Node PASS. AWS AI rollout va native-device qabuli alohida ochiq.
- [-] **I5 — Tayyor yordamchi yuzalar.** 5a public/records/help,
  5b auth/account/profile, 5c preferences/privacy/notifications. Har kichik
  tugallangan oqim alohida qabul; hammasi bir relizga bog‘lanmaydi.
  - [x] ~~I5a-public implementatsiya/integratsiya va texnik reliz.~~ Owner qarori bilan I4bdan oldin. Barcha 14 public route
    oilasi → `azurebek.me` release qabuli → I4bga qaytish. [Dalil](I5A-PUBLIC.md).
    Lokal runtime `74818ee`: 1945 Python OK (skip45), 53 Node PASS.
    PR126 `2787e86`, final CI36176730769 all3PASS. AWS release `363ff95`
    image-boundary fix bilan, final CI36179879066 all3PASS. Public ON;
    real-device va populated real-content owner qabuli alohida ochiq.
    Records/help bu public portga aralashtirilmaydi, keyingi yordamchi paketda.
  - [x] ~~I5b.1 lokal implementatsiya — Profil va Hisob.~~ Shared form, avatar/parol canonical POST,
    stale-profile guard va learner/teacher shell. [Scope/dalil](I5B-ACCOUNT-PROFILE.md).
    `1a4d6a3`: full1975 OK (skip45); follow-up Node68 PASS, browser320–1280 overflow0.
  - [x] ~~I5b.1 required CI/review/integratsiya.~~ PR131 MERGED `af4ed76`;
    final CI `36196388190` uchala PASS; bound-error dirty guard `3d51a61`.
  - [x] ~~I5c.1 lokal — Maxfiylik, To‘lov va Imkoniyatlar.~~ `d3c286e`;
    focused65 OK, Node73 PASS, uch route320–1280 overflow0.
    Review fix `725d47c`: ABA counter/users0022 va confirmed-ID clear.
    [Scope/rollback/dalil](I5C-SETTINGS.md). Canonical writer/quota saqlandi.
  - [x] ~~I5c.1 required CI/review/integratsiya.~~ PR132 MERGED `dd198b7`;
    CI `36206802175` uchala PASS: SQLite2000 skip44, PostgreSQL2000 skip20, Node73.
  - [x] ~~I5b.2 lokal — Register/reset/onboarding.~~ `ec0ff27`; 6 route +
    closed/invalid/expired/complete holatlari. [Scope/dalil](I5B2-AUTH.md).
    Focused100 OK, full2019 OK (skip45), Node79 PASS, 42 responsive check overflow0.
  - [x] ~~I5b.2 required CI/review/integratsiya.~~ PR133 MERGED `75bba33`;
    final CI36208937362 all3PASS, SQLite2019 skip44, PostgreSQL2019 skip20,
    Node82. Review fix `ac2d13b`, [final dalil](https://github.com/azurebek/azurelms/pull/133#issuecomment-5842048014).
  - [x] ~~I5d lokal — sertifikatlar ro‘yxati/davomat/obunalar/reyting/bildirishnomalar/yordam.~~
    `d3aa3dc`: full2040 OK (skip45), app508 OK (skip6), Node87 PASS;
    48 responsive check overflow0. [Scope va dalil](I5D-RECORDS-SUPPORT.md).
  - [x] ~~I5d required CI/review/main.~~ PR134 MERGED `337a73c`;
    CI36211060029 all3PASS, SQLite2040 skip44/PostgreSQL2040 skip20/Node87.
    [Final acceptance](https://github.com/azurebek/azurelms/pull/134#issuecomment-5842321154).
  - [ ] I5b.1/I5b.2/I5c.1 AWS/SMTP release va haqiqiy qurilma qabuli — alohida.
    I5d AWS va sertifikat detail/appendix legacy porti ham ochiq.
- [x] ~~I6 — Library + course/lesson editor kod integratsiyasi.~~ Common resource/link/private
  storage parity; real forms existing fieldsni saqlaydi. Qisman field/save
  contract mos kelmasa tegishli editor legacy qoladi va qarz ochiq yoziladi.
  - [x] ~~I6a lokal — kutubxona list/create/edit/picker.~~ Runtime `9a76fed`;
    library66/full2063 OK (skip45), Node95 PASS, 24 responsive readback overflow0.
    [Scope va dalil](I6A-LIBRARY.md); 10 real form field, private upload,
    scoped attach, lifecycle confirmation va stale409/no-write.
  - [x] ~~I6a required CI/review/main.~~ PR135 MERGED `12b0e3c`,
    final CI36214042911 all3PASS, SQLite2063 skip44/PostgreSQL2063 skip20/Node95.
    [Final acceptance](https://github.com/azurebek/azurelms/pull/135#issuecomment-5842697120).
  - [x] ~~I6b lokal course/lesson editor, per-link settings/reorder/detach V1.~~
    `c72c1fd`: 111 focused OK, 2089 full OK skip45 (final labels/2 testdan oldin),
    Node95, 30 responsive check overflow0. [Scope va dalil](I6B-COURSE-LESSON-EDITORS.md).
  - [x] ~~I6b required CI/review/main.~~ PR136 MERGED `0278331`,
    finalCI36215540990 all3PASS: SQLite2091 skip44/PostgreSQL2091 skip20/Node95.
  - [ ] I6 AWS/device release.
- [-] **I7 — Checkout/receipt.** Quote→upload→pending→owner decision→access;
  - [x] ~~Lokal V1 port `3621e9c`.~~ 28 yangi test, 262 focused OK skip6,
    full2119 OK skip45, Node95; 24 responsive readback overflow0.
    [Dalil va chegaralar](I7-CHECKOUT.md).
  - [x] ~~I7 required CI/review/main.~~ PR137 MERGED `df054c1`,
    finalCI36217772724 all3PASS: SQLite2126 skip44/PostgreSQL2126 skip20,
    Node95; final local2126 skip45 (135.378s), TTL review fix `f681a5b`.
  - [ ] AWS/device release.
  difference/rejected, direct URL permission, duplicate/unknown reconciliation.
- [-] **I8 — Exam va teacher review.** Real attempt/audio/timer/revision,
  save/submit/review/publication; backend natijasi o‘zgarmaydi.
  - [x] ~~I8a markaz va result lokal porti `2fe920f`.~~ 30 yangi test,
    full2156 OK skip45, Node95; 36 responsive readback overflow0.
    Owner qarori bilan qoralama izoh/ball faqat explicit publicationdan
    keyin ko‘rinadi; canonical snapshot, additive courses0021.
    [Dalil va release chegarasi](I8-EXAMS.md).
  - [x] ~~I8a required CI/review/main.~~ PR138 MERGED `17cfc3a`;
    finalCI36219639823 all3PASS, SQLite/PostgreSQL2159, Node95.
    Final local2159 OK skip45 (139.635s), focused33 OK.
  - [x] ~~[I8b oldidan attempt API access/privacy lokal tuzatishi](I8-API-SECURITY.md).~~
    `40c6ba6`, 24 yangi test; courses223 OK skip1, full2183 OK skip45,
    Node95. Required CI/review/main final dalili security PRda.
  - [x] ~~I8b attempt/answer/audio/timer/revision/submit lokal port.~~
    `fc80c7f`, `deef10c`; full2210 OK skip49, final focused86 OK skip4,
    Node104 PASS; 12 width readback overflow0, stale/unknown browser proof.
    [Dalil va native release chegarasi](I8B-ATTEMPT.md). Additive courses0022.
  - [ ] I8b required CI/review/main (5 PG race testi ham).
    Final lock-order `948878c`, focused111 OK skip5 (9.839s), Node104.
  - [ ] I8c teacher review UI va stale-form confirmation.
  - [ ] I8 AWS/native-device release.
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
Keyinchalik owner public deploy va image-boundary blocker fixni tasdiqladi;
public reliz bajarildi. Keyingi yozma `boshla` bilan tayyor ichki rendererlar
rollouti, alohida javob bilan yopiq sinov course/accounts tasdiqlandi va
bajarildi. Test accounts inactive, cohort inactive, course publicdan yashirin.
Haqiqiy mobil qurilma va real-content qabuli ochiq. Yangi pulli muhit yoki
boshqa production dataset bu tor ruxsatga kirmaydi; secrets yozilmaydi.
