# AzureLMS — AWS EC2 deploy runbook

Bu papka loyihani **bitta AWS EC2 mashinasida** ishga tushirish uchun kerak
bo'lgan hamma narsani saqlaydi. Har bir buyruq serverda, `azurelms/deploy/`
ichida bajariladi (boshqacha aytilmagan bo'lsa).

| Fayl | Nima |
|---|---|
| `docker-compose.prod.yml` | To'liq stack: PostgreSQL+pgvector, Valkey, web, worker, beat, outbox, Caddy |
| `Caddyfile` | Reverse proxy va avtomatik HTTPS |
| `env.example` | Env kontrakti — `.env` ga nusxalanadi va to'ldiriladi |

---

## 0. Nega shunday — qisqa asos

**Nega managed xizmatlar (RDS + ElastiCache + ECS) emas.** Joriy maqsad —
30-sentyabrda 50 kishilik boshqariladigan guruhni ishga tushirish. Bitta
mashina bu yukni ko'taradi, xarajat bitta qatorda ko'rinadi va butun stack
`docker compose logs` bilan bir joydan o'qiladi. Managed xizmatga o'tish
keyinchalik faqat `DATABASE_URL` va `VALKEY_URL` ni almashtirish bo'ladi —
kod o'zgarmaydi (`05-launch-ops.md` §1 dagi vendor-neutral kontrakt).

**Nega HTTPS majburiy.** Mikrofon (speaking mashqlari) faqat secure contextda
ishlaydi, Telegram webhook faqat HTTPS manzil qabul qiladi va Django
`SECURITY_STRICT` da HSTS bilan `SECURE_SSL_REDIRECT` yoqadi.

**Nega beshta alohida process.** Web, Celery worker, Celery beat va Telegram
outbox — har biri alohida konteyner. Outbox `05-launch-ops.md` §1 bo'yicha
**majburiy alohida process**; web ichida yugurtirilsa Daphne qayta ishga
tushganda navbat to'xtardi.

---

## 1. EC2 mashinasi

| Parametr | Tavsiya | Izoh |
|---|---|---|
| Instance | `t3.medium` (2 vCPU / 4 GB) | `t3.small` (2 GB) ham ishlaydi, ammo PostgreSQL + Valkey + to'rtta Python processi 2 GB'ga tiqiladi; birinchi haqiqiy dars paytida OOM olishdan ko'ra 4 GB olish arzon |
| Disk | 30 GB `gp3` | Media va PostgreSQL shu diskda |
| OS | Ubuntu 24.04 LTS | Quyidagi buyruqlar shunga mo'ljallangan |
| Region | Foydalanuvchiga yaqini | O'zbekiston uchun `eu-central-1` (Frankfurt) yoki `me-central-1` (BAA) — kechikish sezilarli farq qiladi |

**Security group (kirish):** faqat `80/tcp` va `443/tcp` hammaga; `22/tcp`
**faqat sizning IP'ingizga**. Boshqa hech narsa ochilmaydi — PostgreSQL va
Valkey portlari compose'da tashqariga umuman chiqarilmagan.

**Elastic IP** oling va domenning `A` yozuvini o'shanga qarating. Elastic
IP'siz mashinani qayta ishga tushirganda IP almashadi va Let's Encrypt
sertifikati ham, Telegram webhook ham buziladi.

---

## 2. Serverni tayyorlash

```bash
sudo apt-get update && sudo apt-get upgrade -y && sudo apt-get install -y ca-certificates curl git
```

```bash
sudo install -m 0755 -d /etc/apt/keyrings && sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc && sudo chmod a+r /etc/apt/keyrings/docker.asc
```

```bash
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
```

```bash
sudo apt-get update && sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin && sudo usermod -aG docker $USER
```

Oxirgi buyruqdan keyin **sessiyadan chiqib qayta kiring**, aks holda `docker`
har safar `sudo` so'raydi.

Swap qo'shing — `pip install` build paytida xotirani yeydi va 4 GB mashinada
ham OOM bo'lishi mumkin:

```bash
sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile && echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

---

## 3. Kodni olish va env to'ldirish

```bash
git clone https://github.com/azurebek/azurelms.git && cd azurelms/deploy && mkdir -p backups && sudo chown -R 10001:10001 backups && cp env.example .env && chmod 600 .env
```

> **`chown` ni o'tkazib yubormang.** `backups/` konteynerga **bind mount**
> bilan beriladi, bind mount esa host papkasining egaligini saqlaydi.
> `git clone` qilgan foydalanuvchi (`ubuntu`, uid 1000) yaratgan `0755`
> papkaga konteynerdagi ilova foydalanuvchisi (`Dockerfile`, uid **10001**)
> yoza olmaydi — ya'ni kechasi yuguradigan zaxira cron'i **har kuni
> yiqilardi** va buni Control Center zaxira chirog'i sariq bo'lgunicha
> (default 7 kun) hech kim sezmasdi. Unutilsa `backup_db`/`backup_media`
> yozishdan oldin to'xtaydi va aynan shu buyruqni ko'rsatadi.

```bash
nano .env
```

`.env` da **majburiy** to'ldiriladiganlar: `SECRET_KEY`, `APP_DOMAIN`,
`TLS_EMAIL`, `POSTGRES_PASSWORD`, `DATABASE_URL` (ichidagi parol bilan),
`TELEGRAM_BOT_TOKEN`, `TELEGRAM_WEBHOOK_SECRET`, `GEMINI_API_KEY`.

Kalit yasash:

```bash
python3 -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(64)); print('TELEGRAM_WEBHOOK_SECRET=' + secrets.token_urlsafe(32))"
```

> `ALLOWED_HOSTS` ni qo'lda yozmang. Yozsangiz default ro'yxat butunlay
> almashadi va `127.0.0.1` yo'qoladi — compose'ning `/healthz` tekshiruvi
> `DisallowedHost` (400) bilan yiqilib, web konteyner cheksiz restart
> bo'ladi. `APP_DOMAIN` yetarli.

---

## 4. Birinchi ishga tushirish

```bash
export SOURCE_VERSION=$(git -C .. rev-parse HEAD) && docker compose -f docker-compose.prod.yml up -d --build
```

```bash
docker compose -f docker-compose.prod.yml ps
```

> `SOURCE_VERSION` — Control Center «Release identity» chirog'i shu
> o'zgaruvchini o'qiydi. Berilmasa u `unknown` ko'rsatadi, ya'ni nosozlik
> paytida «serverda qaysi kod turibdi?» degan savolga javob bo'lmaydi.
> Har `up -d --build` dan oldin qo'ying — yoki `.env` ga yozib qo'ying.

`migrate` servisi bir marta ishlab `exited (0)` bo'ladi — bu normal; web,
worker, beat va outbox faqat shundan keyin ko'tariladi.

Keyin uch qadam:

```bash
docker compose -f docker-compose.prod.yml run --rm web python manage.py setup_rag_pgvector --skip-backfill
```

```bash
docker compose -f docker-compose.prod.yml run --rm web python manage.py createsuperuser
```

```bash
docker compose -f docker-compose.prod.yml run --rm web python manage.py reindex_rag --force
```

Oxirgisi Gemini kvotasini sarflaydi — bir marta, dars vaqtida emas
yugurtiring.

### Tekshirish

```bash
curl -sS https://lms.example.com/healthz; echo
```

```bash
curl -sS https://lms.example.com/readyz; echo
```

`/healthz` — process tirikmi (bazaga tegmaydi). `/readyz` — critical
capability'lar; birortasi `red` bo'lsa `503` qaytadi va javobda **qaysi biri**
ekani yozilgan bo'ladi. To'liq manzara: `/backoffice/control/`
(Azure Control Center).

Zaxira yo'lini **birinchi kuni** bir marta qo'lda yugurtiring — cron kechasi
birinchi marta ishlaganda emas, hozir bilib qo'ygan yaxshi:

```bash
docker compose -f docker-compose.prod.yml run --rm web python manage.py backup_media
```

**Birinchi ochilishda ikki chiroq sariq bo'lishi normal:**

| Chiroq | Nega sariq | Qachon yashil bo'ladi |
|---|---|---|
| `Telegram dispatcher` | Webhook rejimida bot o'z holatini faqat **update kelganda** yozadi, ya'ni hali hech kim yozmagan | Botga birinchi `/start` kelganda |
| `Zaxira` | Hali birorta zaxira olinmagan | Yuqoridagi buyruqdan keyin |

Dispatcher chirog'i birinchi update'dan keyin ham sariq qolsa, xabar
aniq bo'ladi: «hali birorta update kelmagan» — bu odatda `setwebhook`
qilinmaganini bildiradi (keyingi bo'lim).

---

## 5. Telegram webhook

Webhook faqat sayt HTTPS bilan ochilgandan **keyin** o'rnatiladi:

```bash
docker compose -f docker-compose.prod.yml run --rm web python manage.py setwebhook https://lms.example.com
```

Buyruq `TELEGRAM_WEBHOOK_SECRET` bo'sh bo'lsa ataylab to'xtaydi: secret'siz
o'rnatilgan webhookda `bot/views.py` fail-closed ishlaydi va **hamma** update
rad etiladi — bot jimgina ishlamay qolardi.

Tekshirish: botga `/start` yozing, so'ng

```bash
docker compose -f docker-compose.prod.yml logs --tail=50 web
```

---

## 6. Kundalik ish

```bash
docker compose -f docker-compose.prod.yml logs -f web
```

```bash
docker compose -f docker-compose.prod.yml run --rm web python manage.py shell
```

Yangi versiyani chiqarish:

```bash
git pull && export SOURCE_VERSION=$(git -C .. rev-parse HEAD) && docker compose -f docker-compose.prod.yml up -d --build
```

`up -d --build` migratsiyani `migrate` servisi orqali o'zi qayta yugurtiradi.

> `SOURCE_VERSION` bu yerda ham kerak. U faqat birinchi ishga tushirishda
> berilsa, keyingi har bir yangilanish konteynerlarni bo'sh qiymat bilan
> qayta yaratadi va Control Center release identity'ni yana `unknown`
> ko'rsatadi — ya'ni nosozlik paytida serverda qaysi kod turgani noma'lum
> bo'ladi.

### To'xtagan xabarlar

Telegram xabari urinishlari tugagach yoki tuzalmaydigan xato olgach
**terminal** bo'ladi va o'zi hech qachon qaytmaydi. Sabab bartaraf
etilgandan keyin (token tuzatildi, tarmoq tiklandi, blok yechildi) uni
`/backoffice/control/dead-letter/` dan sabab bilan navbatga qaytarasiz.

Ikki marta bosish xabarni ikki marta yubormaydi, va har qaytarish audit
tarixiga yoziladi. «Hech qachon tuzalmaydi» turidagi xabar (foydalanuvchi
botni bloklagan, bot guruhdan chiqarilgan) alohida tasdiq so'raydi — uni
blok yechilmasdan qaytarish faqat rate budjetini yeydi.

### Zaxira

Zaxira **canonical buyruq** orqali olinadi — u `pg_dump -Fc` ni chaqiradi va
yozilgan faylni darhol `pg_restore --list` bilan tekshiradi. Yarim yozilgan
dump (masalan disk to'lganda) shu yerda ushlanadi va o'chiriladi, ya'ni
"zaxira bor" degan yolg'on taassurot qolmaydi:

```bash
docker compose -f docker-compose.prod.yml run --rm web python manage.py backup_db
```

Fayl `backups/db-<sana>.dump` bo'lib tushadi va Azure Control Center'ning
backup probe'i uni ko'radi (7 kundan eski bo'lsa AMBER).

**Baza zaxirasi yolg'iz o'zi yetarli emas.** Baza fayllarning o'zini emas,
ularga **yo'lni** saqlaydi: to'lov cheki, vazifa fayli, chat biriktirmasi va
speaking audiosi diskda turadi. Faqat bazani tiklasangiz, har bir chek qatori
mavjud bo'lmagan faylga ishora qiladi — tiklash ishlagandek ko'rinadi, aslida
chek ham, vazifa ham qaytmaydi. Shuning uchun ikkinchi buyruq:

```bash
docker compose -f docker-compose.prod.yml run --rm web python manage.py backup_media
```

Arxiv `backups/media-<sana>.tar.gz` bo'lib tushadi; ichida `public/` va
`private/` alohida bo'limlar. Control Center'da bu alohida chiroq
(«Media zaxirasi») — baza zaxirasi yashil turib media zaxirasi yo'qligi
ko'rinmay ketmasligi uchun.

Har kuni avtomatik olish uchun `crontab -e` ga ikki qator:

```
0 3 * * * cd /home/ubuntu/azurelms/deploy && docker compose -f docker-compose.prod.yml run --rm web python manage.py backup_db >> /home/ubuntu/azurelms/deploy/backup-cron.log 2>&1
15 3 * * * cd /home/ubuntu/azurelms/deploy && docker compose -f docker-compose.prod.yml run --rm web python manage.py backup_media >> /home/ubuntu/azurelms/deploy/backup-cron.log 2>&1
30 3 * * * cd /home/ubuntu/azurelms/deploy && docker compose -f docker-compose.prod.yml run --rm web python manage.py prune_backups >> /home/ubuntu/azurelms/deploy/backup-cron.log 2>&1
```

> **Uchinchi qator — rotatsiya, va usiz disk to'ladi.** Kuniga ikkita fayl
> qo'shiladi va hech kim eskisini o'chirmaydi. Disk to'lganda nima
> bo'lishini aniq bilamiz: `pg_dump` yiqiladi, yarim yozilgan fayl
> o'chiriladi (ataylab), va siz buni zaxira chirog'i sariq bo'lgach —
> ya'ni **zaxirasiz qolganingizda** — bilib qolasiz.
>
> **Nega host'dagi `find -delete` emas.** Faylni o'chirish uchun
> **papkaga yozish** huquqi kerak. `backups/` §3 da konteyner
> foydalanuvchisiga (uid 10001) berilgan va `0755`, ya'ni `ubuntu`
> undan fayl o'chira olmaydi — `find -delete` "Permission denied" bilan
> chiqib, rotatsiya faqat qog'ozda qolardi. Buyruq esa konteyner ichida,
> o'sha uid ostida yuguradi.
>
> **Muddat sozlamada**, crontabda emas:
> `/backoffice/control/runtime-settings/` → «Zaxira saqlash muddati»
> (default 14 kun). SSH'siz o'zgaradi. Nima o'chishini oldindan ko'rish:
>
> ```bash
> docker compose -f docker-compose.prod.yml run --rm web python manage.py prune_backups --dry-run
> ```
>
> Eng yangi zaxira **hech qachon** o'chirilmaydi, muddati o'tgan bo'lsa
> ham — aks holda zaxira olish bir hafta yiqilib turgan holatda rotatsiya
> oxirgi tiklash nuqtasini ham olib tashlardi.

> **Log ataylab `backups/` dan TASHQARIDA.** `>>` redirecti cron'ning host
> shelli tomonidan, `ubuntu` foydalanuvchi ostida ochiladi — Docker hali
> ishga tushmasdan oldin. `backups/` esa §3 da konteyner foydalanuvchisiga
> (uid 10001) berilgan, ya'ni log o'sha yerda bo'lsa `ubuntu` faylni yarata
> olmay, **redirect yiqilardi va zaxira buyrug'i umuman ishga tushmasdi**.
> Bu avvalgi nuqsondan ham yomon holat: hech narsa yugurmaydi va sababni
> yozadigan log ham yo'q.
>
> `deploy/backups/` host papkasi compose'da konteynerning `/app/backups` iga
> mount qilingan. Mount bo'lmasa buyruqlar faylni ephemeral konteyner ichiga
> yozardi va u konteyner bilan birga yo'qolardi — cron har kuni ishlab
> turgandek ko'rinib, aslida hech narsa saqlamagan bo'lardi.

### Tiklash mashqi (restore drill)

> Zaxira olinganini emas, **tiklanishini** tekshiring. Mashq alohida bo'sh
> bazaga qilinadi va ishlab turgan bazaga umuman tegmaydi:

```bash
docker compose -f docker-compose.prod.yml run --rm web python manage.py restore_db --input backups/db-<sana>.dump --into restore_drill_2026_09
```

Buyruq tiklangan bazaning jadval sonini va migratsiya sathini chiqaradi —
dump ochilishi kam, uning **sxemasi** kod kutayotganiga mos kelishi kerak.
Mashqdan keyin bazani tozalang:

```bash
docker compose -f docker-compose.prod.yml exec -T db dropdb -U azurelms restore_drill_2026_09
```

Media arxivi ham xuddi shunday — alohida **bo'sh papkaga**:

```bash
docker compose -f docker-compose.prod.yml run --rm web python manage.py restore_media --input backups/media-<sana>.tar.gz --into /tmp/media-mashq
```

Buyruq `public/` va `private/` bo'yicha fayl sonini chiqaradi va joriy holat
bilan solishtiradi. Joriy media ildizining **ichiga** chiqarishga urinish rad
etiladi — aks holda «mashq» yashiringan destruktiv tiklash bo'lib qolardi.

### Haqiqiy falokat tiklashi

Joriy bazaning ustidan tiklash `restore_db` orqali **ataylab qilinmaydi**: u
ishlab turgan bazadagi hamma obyektni tashlab qaytadan yozish degani va
sinalmagan destruktiv yo'l falokat kunida birinchi marta ishlab ko'riladigan
kod bo'lardi. Buni qo'lda, app to'xtatilgan holda qiling:

```bash
docker compose -f docker-compose.prod.yml stop web worker beat outbox
```

```bash
docker compose -f docker-compose.prod.yml exec -T db pg_restore --clean --if-exists --no-owner -U azurelms -d azurelms < backups/db-<sana>.dump
```

```bash
export SOURCE_VERSION=$(git -C .. rev-parse HEAD) && docker compose -f docker-compose.prod.yml up -d
```

Media fayllarini tiklash ham qo'lda. Arxivni bo'sh papkaga chiqarib,
so'ng volume'ga ko'chiring — `public/` va `private/` **aralashmasligi**
shart, aks holda har bir to'lov cheki `/media/` ostida hech qanday
tekshiruvsiz tarqatiladigan URL bo'lib qoladi:

```bash
docker compose -f docker-compose.prod.yml run --rm web sh -c '
  set -e
  rm -rf /app/backups/.restore-tmp
  python manage.py restore_media --input backups/media-<sana>.tar.gz --into /app/backups/.restore-tmp
  cp -a /app/backups/.restore-tmp/public/.  /app/media/
  cp -a /app/backups/.restore-tmp/private/. /app/private-media/
  rm -rf /app/backups/.restore-tmp
'
```

> **Nega bitta buyruq va nega `/tmp` emas.** Ilgari bu yerda ikki qadam
> turgan edi: birinchisi arxivni `/tmp/tiklash` ga chiqarardi, ikkinchisi
> undan `/app/media` ga ko'chirardi. **Ikkinchisi hech qachon ishlamasdi.**
> `run --rm` konteynerni tugagach o'chiradi va u bilan birga uning
> yoziladigan qatlamini ham; `/tmp` esa volume emas, ya'ni o'sha qatlamda
> yotadi. Ikkinchi buyruq **yangi** konteynerda yugurib, bo'sh `/tmp` ni
> ko'rardi. Endi ikkala qadam bitta konteynerda, oraliq papka esa
> `backups/` ichida — u host'ga mount qilingan va saqlanadi.
>
> Oraliq papka media'ning **ikkinchi nusxasi**, ya'ni diskda vaqtincha
> ikki barobar joy kerak bo'ladi. Buyruq oxirida u o'chiriladi.

Avval **albatta** mashq qiling: yuqoridagi buyruqlar mavjud ma'lumotni
qaytarib bo'lmaydigan tarzda almashtiradi.

### Orqaga qaytarish

```bash
git log --oneline -5
```

```bash
git checkout <oldingi-commit> && export SOURCE_VERSION=$(git -C .. rev-parse HEAD) && docker compose -f docker-compose.prod.yml up -d --build
```

> Migratsiya qo'llangan release'dan orqaga qaytish sxemani o'zi qaytarmaydi.
> Xavfsiz yo'l — avval zaxiradan tiklash, keyin kodni qaytarish.

---

## 7. Tez-tez uchraydigan nosozliklar

| Belgi | Sabab | Yechim |
|---|---|---|
| Web konteyner `ImproperlyConfigured: ... majburiy xizmatlar sozlanmagan` bilan yiqiladi | `VALKEY_URL` yoki broker bo'sh | `.env` ni to'ldiring. Gate ataylab: in-memory fallback WebSocket va Celery tasklarini jimgina yo'qotardi (`core/runtime_gate.py`) |
| Sayt ochilmaydi, Caddy logida `obtain certificate` xatosi | DNS hali Elastic IP'ga qaramaydi yoki 80-port yopiq | DNS'ni tekshiring; HTTP-01 challenge uchun `80/tcp` ochiq bo'lishi shart |
| `ERR_TOO_MANY_REDIRECTS` | Proxy `X-Forwarded-Proto` bermayapti | Caddy orqali yuring; Django `SECURE_PROXY_SSL_HEADER` aynan shu sarlavhani o'qiydi |
| Web cheksiz restart, logda `Invalid HTTP_HOST` | `.env` da `ALLOWED_HOSTS` qo'lda yozilgan va `127.0.0.1` tushib qolgan | O'sha qatorni o'chiring |
| Bot javob bermaydi | Webhook secret'siz o'rnatilgan yoki `TELEGRAM_MODE` `webhook` emas | `.env` ni tekshirib `setwebhook` ni qayta yugurting |
| Rasm/fayl 404 | `USE_S3=False` da public media'ni Caddy tarqatadi | `media` volume Caddy'ga mount qilinganini tekshiring |
| AI javob bermaydi, logda kvota xatosi | Gemini bepul kvotasi tugagan | Control Center'dagi AI supply ledgerini ko'ring; kvota kunlik tiklanadi |
| `Zaxira papkasi yozishga tayyor emas` | `backups/` host papkasi konteyner foydalanuvchisiga tegishli emas | Xato matnidagi `chown` buyrug'ini bajaring (§3) |
| Zaxira chirog'i sariq, cron logida `Permission denied` | Yuqoridagi bilan bir xil sabab, eski deployda | `sudo chown -R 10001:10001 backups`, so'ng zaxirani qo'lda bir marta yugurting |
| Cron logi umuman yozilmaydi / bo'sh | Log `backups/` ichiga yo'naltirilgan, u esa uid 10001 ga tegishli | Log yo'lini `deploy/backup-cron.log` ga ko'chiring (§6) |
| Eski zaxiralar to'planyapti, disk to'lyapti | Rotatsiya host'dan `find -delete` bilan yugurtirilgan | `prune_backups` ni konteyner ichida yugurting (§6); host `ubuntu` o'sha papkadan fayl o'chira olmaydi |
| `Telegram dispatcher` chirog'i qizil (polling) yoki uzoq sariq (webhook) | Polling'da bot jarayoni yo'q; webhook'da update umuman kelmayapti | `setwebhook` ni qayta yugurting va `logs web` da update ko'rinishini tekshiring |

---

## 8. Bu runbook yopmaydigan gate'lar

Deploy texnik jihatdan ishga tushishi `GO` degani emas. Quyidagilar alohida
qoladi (`05-launch-ops.md` §9 "Production GO qo'shimcha checklist"):

- Owner'ning uch qurilmada sign-off'i (Android Chrome, iOS Safari, desktop) —
  mikrofon, upload, Mini App, dark/light.
- Real Telegram guruhda Classbook jonli darsini o'tkazish.
- Sentry / alerting hali ulanmagan.
- Izolyatsiyalangan tiklash mashqi va rollback mashqi **dalili**. Mexanizm
  qurilgan (`restore_db --into` va `restore_media --into`, yuqoridagi §6),
  ammo uni real serverda bir marta yugurtirib, natijani yozib qo'yish kerak.
- **Release yozuvi qo'lda:** `up -d --build` dan keyin
  `docker compose -f docker-compose.prod.yml run --rm web python manage.py record_release`
  ni yugurtiring, aks holda `ReleaseRecord` bo'sh qoladi va rollback
  qaysi versiyaga qaytishni bilmaydi.
- **Offsite nusxa yo'q:** zaxiralar o'sha EC2 diskida qoladi. Disk yo'qolsa
  zaxira ham yo'qoladi — S3 ga ko'chirish alohida ish.
- `ReleaseRecord` ga release SHA yozadigan tomon (`A1b`).

Ularning holati `nuclear-program/launch-plan/03-mahsulot-backlog.md` da
yuritiladi — hujjatdagi status kod holatidan oldinga chiqmasin.
