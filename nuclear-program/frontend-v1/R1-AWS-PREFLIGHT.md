# R1 — AWS release preflight

2026-09-25. Owner public sahifalarni avval chiqarishni so‘radi, domenni
`azurebek.me` deb ko‘rsatdi va mobil tekshiruvdan keyin deployni davom ettirdi.

**Yakuniy holat:** `363ff95` productionda, faqat public V1 ON.
[Amaliy reliz, zaxira, smoke va qolgan risklar](R1-PUBLIC-RELEASE.md).
Quyidagi checkpointlar tarixiy; yakuniy holatni almashtirmaydi.

## Tarixiy SSHdan keyingi checkpoint — 2026-09-25

- Owner SSH /32 yangilanishini tasdiqladi; faqat mavjud 22-port source
  almashtirildi. Key yo‘li owner ko‘rsatgan lokal yozuvdan olindi;
  plaintext secret chiqarilmadi. Serverga SSH muvaffaqiyatli.
- PR #126 MERGED `2787e86`; final CI `36176730769` uchala PASS:
  SQLite1946 skip44, PostgreSQL1946 skip20, Node53.
- Host checkout oldin clean `ef99cb2`, running image esa
  `0123d4f41895fcde82edac95c2a970c1cace2ba5dd6e6ff75874808195c2b001`,
  SOURCE_VERSION `1ddd23e195563d2c3328c57bfa6092ece9c74743` edi.
  Web/db/cache healthy; beat restart100015 (old schedule permission bug).
  Hostda 35GB bo‘sh, available RAM ~2.5GB; APP_WWW_DOMAIN mos.
- `backup_db` → `/app/backups/db-20260926-001254.dump`, integrity OK.
  Server timezone sabab fayl sanasi 26-sentabr. `restore_db --input
  backups/db-20260926-001254.dump --into restore_drill_r1_20260925` PASS:
  135 jadval, 151 migration. Production DB ustidan tiklash bajarilmadi.
- Lokal ikkinchi nusxa `C:\Users\azizb\AzureLMS-Backups\AWS-Public-Release-20260925`.
  Ikkala SHA256: `219ee7e97d3d5091f35c5d322d1b35d5fa6d8d26111f02b93d1ff549b8722176`.
  Bu bir martalik off-host nusxa; scheduled offsite mexanizm emas.
- `backup_media` bo‘sh arxivni ataylab rad etdi. Tekshiruv: mavjud
  public/private volume ildizlari, USE_S3=False, har birida 0 fayl.
  Media zaxirasi/drill PASS deb belgilanmaydi; ko‘chirish/o‘chirish yo‘q.
- Old image `azurelms:rollback-20260925-1ddd23e`; old compose/Caddy
  `/home/ubuntu/azurelms-release-20260925/`da saqlandi. Host checkout
  `2787e86`ga fast-forward; image build bo‘ldi, lekin rollout **HOLD**.
- Sabab: eski va yangi image’da `/app/deploy/.env` va
  `/app/deploy/backups` borligi mazmunni o‘qimasdan tekshirildi.
  Root-only `.dockerignore` nested production fayllarini to‘smagan.
  Image registryga push qilinmagan; tashqi sizishga dalil yo‘q.
  Old image/layer/cachelarda tarixiy nusxalar qolishi alohida xavf;
  bu patch ularni o‘chirib yoki secretlarni rotate qilib bermaydi.
- Owner minimal fix + CI + clean rebuild + deployni tasdiqladi.
  `cc861c8`: recursive `**/.env`, `**/.env.*`, `**/backups/`;
  CI haqiqiy image’da 3-depth harmless canarylar yo‘qligini tekshiradi.
  Offline `manage.py test core.test_deploy_artifacts --noinput --verbosity 1`:
  **22 OK**, check0issue; `git diff --check` PASS. Required CI hali ochiq.
- Migration/restart/public flag activation hali **bajarilmadi**.
  FeatureFlag override jadvali bo‘sh; old effective holatlar o‘zgarmadi.

## Dastlabki, SSHdan oldingi holat (tarixiy)

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

## Dastlabki kod va compatibility rejasi (tarixiy)

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

## Dastlabki serverga kirilgach bajarish tartibi (tarixiy)

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

**Ushbu dastlabki checkpoint vaqtida** deploy/flag activation bajarilmagan
edi. Keyinchalik public rollout va bir martalik off-host backup yakunlandi;
[joriy holat](R1-PUBLIC-RELEASE.md)ga qarang. Real-device/account qabuli va
scheduled offsite mexanizm ochiq qoladi.
