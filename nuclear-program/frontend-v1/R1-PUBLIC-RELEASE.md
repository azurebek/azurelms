# R1-public — AWS reliz dalili

2026-09-25 (UTC). **Public V1 texnik relizi bajarildi**:
https://azurebek.me/. Bu barcha LMS oqimlari yoki 1-oktyabr uchun umumiy
GO emas; quyidagi scope va ochiq gate’lar saqlanadi.

Keyingi holat: [R1-internal](R1-INTERNAL-RELEASE.md) bilan owner ruxsatidan
so‘ng learning/lesson/teacher/human messenger ham yoqildi. Pastdagi public-only
flag va auth holatlari dastlabki public reliz snapshotidir, joriy holat emas.

## Versiya va yoqilgan qism

- Public port PR #126 → `2787e86`; Docker boundary fix PR #127 →
  **`363ff95e9fcbcbff4d2227374707c50f993888f2`** — deployed SHA.
- Frankfurt EC2, `/home/ubuntu/azurelms/deploy`. Running web/worker/beat/outbox
  image: `sha256:1fa24b72b342b7fd099f5f652631a0534f560eabeed5e33b91d439e86ef8c12f`.
  To‘rt process running, restart0. DB/cache/Caddy qayta yaratilmagan.
- `frontend_v1_public=True`. `frontend_v1_learning`, `frontend_v1_lesson`,
  `frontend_v1_teacher`, `frontend_v1_messenger` **False**; o‘zicha yoqilmadi.
  Faqat canonical audited `core.flags.set_flag` ishlatildi.
- `record_release --sha 363ff95e9fcbcbff4d2227374707c50f993888f2`
  gate dalillari bilan bajarildi: **152 migration, kod/baza mos**.

## Zaxira, migratsiya va xavfsizlik

- Deploy oldidan `backup_db`: `backups/db-20260926-003658.dump`, integrity OK.
  Server timezone tufayli fayl sanasi 26-sentabr. Host yo‘li:
  `/home/ubuntu/azurelms/deploy/backups/db-20260926-003658.dump`.
- Ikkinchi nusxa: `C:\Users\azizb\AzureLMS-Backups\AWS-Public-Release-20260925`.
  Ikkala nusxa SHA256 bir xil:
  `74daf1e3c4cc083ad48351f36adb1002cb8ac6002352368de276242011758e47`.
- Oldingi shu sessiya zaxirasi `db-20260926-001254.dump` alohida
  `restore_drill_r1_20260925` bazasiga tiklandi: integrity OK, 135 table,
  151 migration. Yangi image shu drill bazasiga `library.0001_initial`ni
  muvaffaqiyatli qo‘lladi. So‘ng faqat biz yaratgan drill DB o‘chirildi;
  production DB va zaxira fayllari saqlandi.
- Production `migrate --plan`: faqat library yangi model/indexlari.
  Existing field/table delete yoki data rewrite yo‘q. Compose migrate
  exited0; `migrate --check` PASS.
- `check --deploy`: 0 issue. `up -d --no-build --pull never --wait
  --wait-timeout 120 web worker beat outbox` bilan controlled restart;
  SOURCE_VERSION yuqoridagi aniq SHAga o‘rnatildi.
- Media ildizlari mavjud, USE_S3=False, public0/private0. `backup_media`
  bo‘sh arxivni rad etadi; bu PASS deb berilmaydi. Media volume o‘zgarmagan.
- SSH source faqat owner tasdiqlagan hozirgi /32ga yangilangan, 80/443
  saqlangan. Maxfiy kalitning mazmuni chat/log/gitga chiqarilmadi.
- Eski image’da nested `deploy/.env`/`deploy/backups` topilganda rollout
  to‘xtatildi. Owner tasdiqlagan `cc861c8` tuzatishidan so‘ng **real server
  image’i mount va networksiz tekshirildi**: recursive env/backups yo‘q,
  kerakli public static asset bor. [Docker pattern semantics](https://docs.docker.com/build/concepts/context/#dockerignore-files).
- Eski running image va deploydan chiqarilmagan `held-20260925-2787e86`
  image/cache layerlari hali tarixiy sir nusxalarini saqlashi mumkin.
  Registryga push qilinmadi. Credential rotation yoki broad Docker prune
  bajarilmadi; bu alohida xavfsizlik follow-up, clean rebuild tarixni o‘chirmaydi.

## Tekshiruvlar

| Tekshiruv | Natija |
|---|---|
| Offline `manage.py test core.test_deploy_artifacts --noinput --verbosity 1` | 22 OK |
| PR127 final CI `36179879066` — barcha uch required job | PASS |
| CI `python manage.py test`, SQLite | 1948 OK, skip44 |
| CI `python manage.py test`, PostgreSQL | 1948 OK, skip20 |
| Real CI Docker image, 3-depth harmless env/backup canary | PASS |
| HTTPS `/healthz`, `/readyz` | alive / ready, release363ff95e9fcb |
| `/`, about, courses, pricing, FAQ, terms, privacy, blog, SIT, universities | 10 × HTTP200, V1, private/no-store |
| `/users/login/`, `/users/register/` | 2 × HTTP200, legacy saqlangan |
| Home sahifasidan olingan hashed CSS/JS/SVG | 11 × HTTP200 |
| `https://www.azurebek.me/` | 301 → canonical HTTPS |
| IAB320×740, home/catalog + qolgan 8 public sahifa | document overflow0 |
| IAB1280×800 home | overflow0, header64.8px |
| Dark/light, mobil menu open/Escape/focus, explicit catalog GET filter | PASS |
| Final browser warn/error | 0 |
| Public flag OFF → HTTPS old renderer → ON → HTTPS V1 | PASS, auditlangan |

Temporary viewport va tema testdan keyin qaytarildi. Productionda test user,
kurs, izoh, buyurtma yoki provider/Telegram demo yaratilmagan/yuborilmagan.
CI dagi branch reopen bir xil SHAda ikkinchi run boshladi; birinchi
`36179251633` ham yashil edi, merge faqat final run tugagach bajarildi.

## Rollback

Birinchi xavfsiz yo‘l — yangi, toza image’da faqat renderer flagini OFF:

```bash
docker compose -f docker-compose.prod.yml exec -T web python manage.py shell -c "from core.flags import set_flag; set_flag('frontend_v1_public', enabled=False, reason='Owner public V1 rollback: sababni yozing')"
```

Bu ma’lumotni o‘chirmaydi; native legacy public sahifalar qaytishi jonli
HTTP orqali tekshirildi. To‘liq code rollback avtomatik bajarilmaydi:
old image `azurelms:rollback-20260925-1ddd23e` va old compose/Caddy
`/home/ubuntu/azurelms-release-20260925/`da bor, ammo eski image secret
boundary muammosi sabab faqat favqulodda, alohida baholangan yo‘l.
Production bazani avtomatik restore/delete qilish yo‘q.

## Qolgan gate va kontent

- Productionda course/blog/university/guide soni **0**. Empty state real
  ma’lumotdan keladi; demo fixture ko‘chirilmagan. Shu sabab populated
  detail/comment oqimlari faqat avvalgi izolatsiyalangan test daliliga ega.
- Landing `Statistic` qiymatlari (2400+, 6, 94%, 4.9) mavjud boshqariladigan
  marketing yozuvlari, real platforma hisoblagichi emas. Owner ularning
  to‘g‘riligini va qolgan placeholder/kontentni taqdimotdan oldin qabul qiladi;
  bu deployda editorial ma’lumot o‘zboshimchalik bilan almashtirilmadi.
- Haqiqiy Android/iOS sign-off va controlled real-account login/learning
  oqimi ochiq. Browser responsive viewport real telefon sinovi emas.
- Jobs probe amber: heartbeat hali o‘lchanmaydi; restart0 funksional job
  isbotining o‘rnini bosmaydi. Scheduled offsite backup hali yo‘q;
  joriy relizda qo‘lda off-host nusxa olindi.
- I4b va qolgan portlar ochiq; I1–I4a kodlari deployed bo‘lsa ham V1
  flaglari OFF. Scope faqat public release, qolganlarini alohida chiqaramiz.
