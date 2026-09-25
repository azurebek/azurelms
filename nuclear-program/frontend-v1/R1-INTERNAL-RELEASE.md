# R1-internal — tayyor ichki V1 ko‘rinishlari yoqildi

2026-09-25 UTC (saytdagi sana 26-sentabr). Owner publicdan tashqari eski
ko‘rinish sababini so‘ragach, tayyor ichki oqimlarni tekshirish va yoqishga
`boshla` deb ruxsat berdi. Yopiq sinov kursi/akkauntlariga alohida yozma
tasdiq olindi. **Bu barcha sahifalar ko‘chirildi degani emas.**

## Amaldagi holat

Server kodi/image o‘zgarmadi: `363ff95e9fcbcbff4d2227374707c50f993888f2`.
Rebuild, restart, migration va prototype o‘zgarishi yo‘q. Oldingi
[public reliz](R1-PUBLIC-RELEASE.md) zaxira/image dalili saqlanadi.
Canonical `core.flags.set_flag` orqali auditlangan override:

| Flag | Yakuniy holat | Yangi ko‘rinish |
|---|---|---|
| `frontend_v1_public` | ON, saqlandi | Public oilalar |
| `frontend_v1_learning` | ON | Login, dashboard, kurslarim |
| `frontend_v1_lesson` | ON | Dars, material, assignment va quiz |
| `frontend_v1_teacher` | ON | Home, release, review, kurs/guruh/o‘quvchi, davomat |
| `frontend_v1_messenger` | ON | Guruh va ustoz chati; AI emas |

Hisob sozlamalari/profil/registration/privacy/notifications, AI chat,
backoffice/editorlar, checkout, exam va Classbook hali legacy. Bu yo‘llar
uchun tayyor port yo‘q; flag yoqish ularni yangi dizaynga o‘tkazmaydi.
Keyingi port navbati I4b va I5ning qolgan qismlari–I9; yangi redesign yo‘q.

## Tekshiruv dalili

Fresh local testlar `.env.local`siz, `AZURELMS_SKIP_ENV_FILE=1`,
`GEMINI_API_KEY=''`, `TELEGRAM_BOT_TOKEN=''` bilan:

```powershell
.\venv\Scripts\python.exe manage.py test users.test_frontend_v1 courses.test_frontend_v1_study messenger.test_frontend_v1 --noinput --verbosity 1
.\venv\Scripts\python.exe manage.py test courses.test_frontend_v1_practice core.test_frontend_v1_review core.test_frontend_v1_directory --noinput --verbosity 1
```

- Birinchi suite: 57 OK (7.104 s); ikkinchisi: 48 OK, skipped3 (6.698 s).
  Skiplar mavjud PostgreSQL-specific concurrency testlari; susaytirilmadi.
  Deployed kodning avvalgi required CI dalili PR127da 1948×2.
- Server `manage.py check --deploy`: 0 issue.
- Haqiqiy `https://azurebek.me` orqali uchta synthetic role bilan
  CSRF/password login, safe-next, dashboard/course list, teacher 7 route,
  private/no-store, begona rol denial va public hidden-course404 tekshirildi.
- Teacher release → learner darsning to‘rt tabi → private PDF exact bytes;
  outsider404; assignment yuborish → teacher approve → learner feedback;
  quiz result DBda; lock → lesson/private file yopilishi → qayta release.
- Haqiqiy WSS orqali group send/echo va DBga yozish; JSON edit200,
  oldingi revision bilan409 va no-write. Guruh faqat test ishtirokchilaridan
  iborat, Telegram ID yo‘q; `@azure` va AI chat ishlatilmagan.
- Har to‘rt flag OFF → HTTPS legacy → ON → HTTPS V1 tekshirildi.
  Rollback ma’lumotni o‘chirmadi. Yakuniy `/readyz`: ready.
- Dastlab 92 assertiondan keyin **sinov skripti** editga JSON o‘rniga
  form yubordi. Uch pilot flag oldingi OFFga qaytdi, test hisoblari
  faolsizlantirildi. Runtime nuqsoni emasligi view/controllerdan tasdiqlandi;
  ayni datasetda to‘g‘ri JSON bilan davom etildi: 41 qo‘shimcha assertion
  PASS. Yangi dataset yoki kod tuzatishi qilinmadi.
- IAB haqiqiy owner sessiyasi: dashboard/kurslarim, teacher home/release,
  besh ro‘yxat sahifasi 320/1280px, chat mobile/desktop: overflow0.
  Mobil menu/Escape/focus, release confirmation/cancel, light/dark ko‘rildi.
  Tutor chat tarixi 320×740da496px, 1280×800da540px; composer ekranga sig‘di.
  Owner sessiyasidan logout yoki xabar yuborish bajarilmadi.

Bu desktop brauzerdagi responsive tekshiruv; haqiqiy Android/iOS keyboard,
uzoq muddatli socket/reconnect va barcha real kontent kombinatsiyasi qabuli
emas. Live attendance mutation va chat upload/delete bu pilotga kirmadi;
ularning oldingi local/CI dalili mavjud, yangi production PASS deyilmaydi.

## Sinov yozuvlari va xavfsiz yopish

Aniq marker: `R1-internal-20260925-204712`. Course1 doim `is_active=False`:
public katalogda yo‘q, public detail404. Cohort1, lesson1, resource1/material1;
test users4/5/6, group room6. Haqiqiy oldingi users1–3 o‘zgartirilmadi.

Sinov yakunida users4/5/6 inactive va unusable password; enrollment frozen,
cohort inactive, resource canonical archive orqali arxivlangan. Avtomatik
ochilgan synthetic private room8dan owner membership olib tashlandi.
Test ma’lumotlari/audit saqlandi, **qator yoki fayl o‘chirilmadi**. Owner
backoffice’da bu inactive/arxiv sinov yozuvlarini ko‘rishi mumkin.
Temporary test credentiallar log/chat/git/faylga chiqarilmagan.

`SystemAuditEvent`: fixture creation, flag changes/rollback, smoke natijasi
va quarantine yozilgan. Provider kalitlari faqat seed CLI processida bo‘sh;
jonli web/worker konfiguratsiyasi yoki boshqa flaglar o‘zgartirilmagan.

## Rollback va qolganlar

Muammoli oilaning yuqoridagi flagini existing owner control orqali OFF
qiling, sababni yozing. Xabar, enrollment, submission yoki bazani restore
qilish kerak emas. Runtime kodi shu relizda almashtirilmagan.

R1 technical internal rollout bajarildi; real telefon/owner content qabuli
ochiq. I5 hisob sozlamalari porti yo‘q. Kosmetik qarz: V1 kurslarimning
empty-state matni katalogni hali “avvalgi ko‘rinishda” deb ataydi, lekin
katalog V1; navigatsiya ishlaydi. Public relizdagi old image/cache sir
nusxalari, credential rotation, scheduled offsite va heartbeat qarzlari
bu ish bilan yopilgan emas.
