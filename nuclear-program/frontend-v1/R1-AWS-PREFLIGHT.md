# R1 — AWS release preflight

2026-09-25. Owner public sahifalarni avval chiqarishni so‘radi, domenni
`azurebek.me` deb ko‘rsatdi va mobil tekshiruvdan keyin deployni davom ettirdi.

## Tasdiqlangan joriy holat

- AWS EC2 `azurelms-prod`, Frankfurt `eu-central-1`, Ubuntu 24.04,
  `t3.medium`, Running, 3/3 instance checks. Domen A yozuvi aynan shu
  instance Elastic IP’siga mos. Yangi resurs yaratilmagan.
- HTTPS `/healthz`: alive; `/readyz`: ready; live release
  **`1ddd23e19556`**. Database/media/security green; backup green,
  so‘nggi zaxira ~0.7 kunlik. Jobs amber: heartbeat o‘lchanmaydi.
- Bu HTTP dalili container image, git checkout va diskdagi fayllar
  bir xilligini hali isbotlamaydi; serverga kirilgach qayta solishtiriladi.
- HTTP va HTTPS ochiq. SSH faqat avvalgi bitta /32 manbaga ruxsatli;
  hozirgi lokal outbound IP boshqa. CLI SSH timeout, AWS Instance Connect
  ham ulanmagan. IAM role yo‘q; SSM access taxmin qilinmadi.
- Xavfsizlik qoidasi o‘zgartirilmadi. Ownerdan faqat 22-portning source
  /32 qiymatini hozirgi IP’ga yangilash ruxsati va lokal SSH key yo‘li
  so‘ralgan. Secret mazmunini yuborish so‘ralmagan.

## Kod va compatibility

PR #126: initial CI `36175187721` uchala PASS; review correction
`d7c3e43`dan keyingi final CI/merge hali kutilmoqda.

Live SHA → target diff faqat public CSS emas: oldingi merge qilingan
I1/I2/I3/I4a, library va deploy tuzatishlari ham bor. Shuning uchun:

- Yagona yangi migration `library.0001_initial`: CreateModel va yangi
  kutubxona jadvallaridagi index/constraintlar. Existing jadval/ustun
  olib tashlash yoki data rewrite yo‘q. Serverdagi applied plan hali
  tekshirilmagan; xavfli kutilmagan migration bo‘lsa rollout to‘xtaydi.
- Compose endi `APP_WWW_DOMAIN` talab qiladi; serverdagi qiymat va `www`
  DNS aliasi preflightda tekshiriladi. `.env` plaintext chop etilmaydi.
- Beat schedule `/app/beat` persistent volume’ga o‘tgan; mavjud runtime
  va writable ownership tekshiriladi. Media/private/DB volumes saqlanadi.
- AnyIO/Autobahn patched versiyalari image qayta build bo‘lganda olinadi.
- `frontend_v1_*` flaglar default OFF. Public flag birinchi tekshiriladi;
  boshqa flaglar avtomatik ravishda yoqilmaydi yoki o‘chirilmaydi.

## Serverga kirilgach bajariladigan tartib

1. Haqiqiy repo/compose path, clean checkout, SOURCE_VERSION/image,
   disk/RAM, process health va migration plan; secretlarsiz env presence.
2. Existing canonical `backup_db` va `backup_media`; integrity va exact
   backup paths. Old image ID/SHA va flag state rollback uchun qayd etiladi.
3. Faqat yashil main SHA fast-forward; reviewed image build. Data volume
   delete/prune yo‘q. Controlled migration va app restart, liveness/readiness.
4. `record_release` va public flag explicit reason bilan; public/login/link/
   CSS/JS/media smoke, desktop/mobile. Test user/order/comment productionda
   o‘zicha yaratilmaydi; AI/provider/Telegram demo chaqirilmaydi.
5. Muammo bo‘lsa avval public flag OFF; kerak bo‘lsa old verified imagega
   code rollback. Ishlab turgan DBni avtomatik restore/delete qilish yo‘q.

**Hali deploy yoki flag activation bajarilmadi.** Offsite backup,
real-device sign-off va controlled real-account flow yakunlanmagan.
