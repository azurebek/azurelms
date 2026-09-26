# R2 — tayyor V1 kodining AWS relizi

2026-09-26 UTC. Owner: «tayyorlarini AWSga chiqar, yakunlasang keyin yana
prototip yaratishga qaytamiz». **Texnik rollout bajarildi.** Bu yangi Q14+
prototiplari, haqiqiy telefon yoki barcha provider oqimlari qabuli emas.

## Aniq versiya va qamrov

- `https://azurebek.me` live SHA **8bb6b95da6fa9b3308bfbe8c0fa43ad440dfca23**.
  Old running SHA `363ff95e9fcbcbff4d2227374707c50f993888f2` SSH va HTTPSda
  tasdiqlandi. Clean server checkout fast-forward qilindi; runtime patch yo‘q.
- Main CI [36267650359](https://github.com/azurebek/azurelms/actions/runs/36267650359)
  uch required job PASS. PR143 final CI36267213566: SQLite/PostgreSQL
  2303 test (skip57/20), Node122 PASS; release shu reviewed main kodidan.
- Image build manifest `sha256:7774b3c464515df53066dc3ac581c980de5a09e6cc6d5faf292d30d69f9f1000`.
  Web/worker/beat/outbox shu image bilan running, restart0. DB/cache/Caddy
  sentabr13dagi processlarida qoldi, qayta yaratilmagan yoki restart qilinmagan.
- Registrydagi **19 ta `frontend_v1_*` flag ON**, faqat canonical audited
  `core.flags.set_flag` orqali. Oldingi beshta ON saqlandi, 14 tasi qo‘shildi.
  Public, auth/learning/lesson, teacher, human/AI messenger, account/settings,
  records/certificates, library/editors, checkout, exams/attempt/review,
  Classbook preparation/live. Boshqa capability flaglari o‘zgartirilmadi.
- `record_release` 161 applied migration va unapplied0ni qayd etdi.
  Q14 exam editori va boshqa hali prototipsiz backoffice yuzalari legacy;
  «barcha mavjud sahifalar yangi» degan da’vo yo‘q.

## Zaxira, schema va rollout

Pre-release backup (server timezone sabab nom sanasi sentabr27):

| Fayl | SHA256 |
|---|---|
| `db-20260927-010316.dump` | `3bf5f3449095d9498e623b11cab7afdac386d98c649acdf04ecd86e413988a39` |
| `media-20260927-010326.tar.gz` | `b7321453efb1330cd7814cdcd691de4335cec32962879e298cff0f4e917c3aba` |

Server: `/home/ubuntu/azurelms/deploy/backups/`. Off-host nusxa:
`C:\Users\azizb\AzureLMS-Backups\AWS-V1-Release-20260926\`.
Ikkala nusxaning SHA256 qiymati mos. Media: public0/private1.

`restore_db --into restore_drill_v1_20260926`: integrity OK, 140 table,
152 migration. Yangi image shu **alohida** bazaga to‘qqiz migratsiyani
qo‘llab, `migrate --check`dan o‘tdi. Drill DB saqlangan; production restore
qilinmadi. `restore_media --into /tmp/media-v1-drill-20260926`: private1
mos, production media o‘zgarmadi; vaqtinchalik nusxa eski web containerda edi.

Ko‘rilgan migratsiyalar: classbook0003, core0005/0006, courses0021–0024,
library0002, users0022. AddField/CreateModel/constraintlar, destructive
remove yoki ma’lumot backfilli yo‘q. Eski approved exam tafsilotlarini
avtomatik publication qilish qo‘shilmagan; oldingi I8 privacy chegarasi qoladi.

Yangi image mount/network/envsiz tekshirildi: recursive `.env*` yoki
`backups` nusxalari yo‘q, zarur V1 JS mavjud. App processlari to‘xtatilib,
migrate0dan keyin pinned `SOURCE_VERSION` bilan controlled restart qilindi.
Web20:07:08Z, qolganlari20:07:09Zda ishga tushdi. Ishlab turgan baza/cache
va proxy saqlandi. `check --deploy`: 0 issue; `migrate --check`: PASS.
Post-release `backup_db`: `db-20260927-011427.dump`, integrity OK.

## Real-server dalili

Ignored operational harness `playground/frontend-v1-smoke/verify_aws_v1_release.py`
Django shell orqali stdin bilan ishlatildi; keys faqat shu seed processida
bo‘sh, jonli provider konfiguratsiyasi o‘zgarmadi. **327 assertion PASS**:

- Uchta ajratilgan hisobda haqiqiy HTTPS password+CSRF login/safe-next.
- Public/auth, profil/settings, records, teacher, AI/human chat renderer,
  library/course/lesson editorlari, Classbook preparation sahifalari HTTP200,
  V1 assetlari va private/no-store. Hidden course public404, outsider lesson404.
- Native profil save → DB tasdiq; ayni eski forma qayta yuborilganda409.
- Exam start → save → exact retry (bitta answer) → submit → teacher draft →
  stale409 → learnerdan draft yashirin → explicit publish → learnerda natija.
  Synthetic certificate detail/appendix HTTP200, published-only projection.
- Classbook canonical isolated start → HTTPS teacher open → stale409 →
  learner javob → DB → outsider404 → reveal → teacher/learner result → finish.
- 13 yangi renderer oilasida OFF→legacy→ON→V1 jonli rollback tekshirildi.
  Checkout hidden-course404 saqlandi; active public course **0**, shuning
  uchun jonli checkout purchase/receipt yaratish sinovi qilinmadi.
- Sahifalardan yig‘ilgan **35 hashed static asset HTTP200**.
- `/readyz` yangi SHA bilan ready. `/healthz` alive.

Qo‘shimcha `verify_aws_v1_socket.py`: shu synthetic datasetda haqiqiy WSS
send→echo→DB, JSON edit200, eski revision409/no-write PASS. Xonada faqat
synthetic qatnashchilar, Telegram ID yo‘q; `@azure`/provider chaqirilmadi.

IAB haqiqiy owner sessiyasida yetti oila × olti width
(320/639/640/1023/1024/1280) = **42 actual viewport readback**: positive
horizontal overflow0. Hisob/maxfiylik/library/course create/exam center/
AI chat/Classbook home. Mobil menu Enter→Escape→focus restore PASS,
desktop va mobil dark screenshot ko‘rildi, browser warn/error0. Vaqtinchalik
viewport reset qilindi; owner formasi yuborilmadi, logout/parol o‘zgartirilmadi.

Local screenshotlar: `playground/frontend-v1-smoke/r2-aws-account-desktop.png`
va `r2-aws-account-mobile.png`. Screenshotlar Gitga qo‘shilmagan.

## Synthetic yozuvlar va qolgan chegaralar

Marker `R2-v1-20260926-201016`: course2/cohort2/lesson2, users7/8/9,
exam1/2, Classbook exercise1/session1/activity1. Users inactive/unusable
password, enrollment frozen, cohort inactive, course doim inactive.
Real users1–3 o‘zgartirilmadi. Ma’lumotlar o‘chirilmagan; owner arxiv/noaktiv
sinov yozuvlarini ko‘rishi mumkin. Audit: fixture/smoke/WSS/quarantine va flags.
Ephemeral parollar faqat process xotirasida, chat/log/Gitda yo‘q.

**Muhim mavjud konfiguratsiya cheklovi:** production `EMAIL_BACKEND`
`django.core.mail.backends.console.EmailBackend`, EMAIL_HOST bo‘sh.
Parolni email orqali tiklash xat yubormaydi. V1 auth ko‘rinishi chiqarildi,
lekin SMTP delivery gate **PASS emas**. Ownerga xabar berildi; xat yuborish
yoki credentials/vendor sozlash bu deployda qilinmadi. Legacy ham shu
backenddan foydalanadi, renderer rollbacki SMTPni tuzatmaydi.

AI provider javobi, real SMTP/Telegram, real payment va native microphone/
codec/telefon/50-user load bu relizda qayta sinalmadi. Tegishli local/CI
evidence saqlanadi, production end-to-end PASSga aylantirilmaydi. Jobs probe
oldingi kabi amber: worker/beat heartbeat o‘lchanmaydi, restart0 yetarli
funksional dalil emas. Old image/cache secret copies/rotation va scheduled
offsite backup qarzlari ham bu reliz bilan yopilmadi.

## Rollback va keyingi ish

Bir oilada xato bo‘lsa shu yangi image ichida tegishli `frontend_v1_*`
flagni owner panel/canonical service orqali sabab bilan OFF qiling.
Bu data restore yoki migration reverse qilmaydi. Additive schema yangi
ustunlarga yozadigan writerlarni talab qilishi mumkin: eski imagega ko‘r-ko‘rona
qaytilmaydi. `azurelms:pre-v1-20260926-363ff95` clean old image tagi saqlandi,
ammo to‘liq code rollback alohida compatibility bahosini talab qiladi.

Owner navbati endi **Q14 — imtihon muharriri** (`/backoffice/exams/`,
detail/section/question/prerequisite/publication scope) prototipiga qaytish.
Q14 shu reliz turnida boshlanmadi. Yangi prototype darhol productionga
almashtirilmaydi; tasdiq→real port→tekshiruv→alohida release. Frozen V1 va
qolgan Q02–Q12/device/provider qarzlari yo‘qolmaydi.
