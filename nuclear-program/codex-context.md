# AzureLMS — Codex kod xaritasi

Ishni [yagona hujjat xaritasidan](README.md) boshlang. Bu fayl canonical kodga
tez kirish uchun barqaror navigatsiya; faol ish navbati, launch qabuli yoki
serverning joriy salomatligi haqidagi ikkinchi manba emas.

**Kod bilan solishtirish:** 2026-10-13, `main` bazasi `62dd358`.
Bu hujjat sinxroni serverga ulanish, DB auditi yoki provider chaqiruvi emas.
Arxitektura tafsiloti [project-context.md](project-context.md)da; sanalangan
ish va tekshiruv dalillari [marinebook.md](marinebook.md)da saqlanadi.

## Ish boshlash

1. `AGENTS.md` va [agent qoidalari](rules-for-agents.md)ni o'qing.
2. Git holati, so'nggi commitlar va branch ownershipini tekshiring.
3. Marinebookning so'nggi 3–5 yozuvi va hubdan taskning tegishli rejasiga o'ting.
4. Model → canonical service/policy → adapter → test zanjirini ko'ring.

Bitta checkout ishlatiladi: `C:\Users\azizb\Desktop\project\azurelms`.
Codex o'z `codex/` branchida ishlaydi; begona dirty o'zgarishlarga tegmaydi.
Commit, PR, required CI va merge tartibi qoidalar hujjatida saqlanadi.

Azurbek product, curriculum, pricing va `GO/HOLD/NO-GO` qarorining egasi.
Web, Telegram, Mini App, Messenger, Celery va AI providerlar canonical
Django holati va service'larining adapterlari. Biznes qoida bir nechta
surface'da kerak bo'lsa, alohida nusxalar emas, bitta service va parity
tekshiruvi ishlatiladi.

## Canonical kodga kirish

Jadvaldagi yo'llar repository ildiziga nisbatan berilgan.

| Ish | Asosiy manba |
|---|---|
| Auth/profile/settings | `users/models.py`, `users/views.py`, `users/urls.py` |
| Teacher course/cohort scope | `core/access.py` |
| Enrollment, plan va access | `cohorts/models.py`, `core/entitlements.py`, `courses/access_service.py` |
| Checkout, promo, receipt | `cohorts/checkout_service.py`, `cohorts/receipt_service.py`, `subscriptions/promo_service.py` |
| Membership va guruhga o'tish | `cohorts/membership_service.py`, `cohorts/transition_service.py`, `cohorts/delivery_service.py` |
| Davomat, XP, lesson release | `cohorts/attendance_service.py`, `users/xp.py`, `courses/release_service.py` |
| Lesson progress, assignment/quiz submit va review | `courses/progress_service.py`, `courses/submission_service.py` |
| Kurs/modul/dars va practice tayyorlash | `courses/authoring_service.py`, `core/backoffice_workspace.py`, `core/backoffice_practice.py` |
| Material kutubxonasi | `library/` service'lari va access qatlami; workspace ularning adapteri |
| Imtihon tayyorlash | `courses/exam_authoring_service.py`; backoffice HTTP adapterlari `core/views.py`da |
| Imtihon topshirish va yakunlash | `courses/exam_service.py`, `courses/exam_section_service.py`, `courses/reading_service.py`, `courses/policy_service.py`, `courses/completion_service.py` |
| Jonli dars | `classbook/models.py`, `classbook/services.py`, `classbook/access.py`, `classbook/consumers.py` |
| O'quvchi muammosi, natija va yetkazish diagnostikasi | `core/student_support_service.py`, `core/student_support_results.py`, `core/student_support_delivery.py`, `core/student_support_views.py` |
| Qidiruv va ishga qaytish | `core/backoffice_search.py`, `core/backoffice_recent.py`, `core/backoffice_return.py`, `core/student_support_return.py` |
| Kodsiz dizayn draft/publish/runtime | `core/design_service.py`, `core/design_schema.py`, `core/design_views.py`, `core/design_models.py` |
| Messenger | `messenger/consumers.py`, `messenger/tasks.py`, `messenger/access.py`, `static/js/messenger-chat.js` |
| AI behavior va supply | `ai/agent/engine.py`, `ai/prompts/builder.py`, `ai/skills/registry.py`, `aicontrol/supply.py` |
| RAG va memory | `messenger/rag.py`, `ai/rag/context.py`, `ai/memory/` |
| Telegram, outbox, retry/replay | `bot/services.py`, `bot/routers/`, `bot/outbox.py`, `bot/retry_policy.py`, `bot/dead_letter.py` |
| Notification yaratish | `users/notification_service.py`; Telegram yetkazish outbox orqali |
| Control, flag, audit, release | `core/control_center/`, `core/flags.py`, `core/audit.py`, `core/ai_cost.py`, `core/release_service.py` |
| Private upload/access | `core/upload_validation.py`, `core/private_media_views.py` |
| Public/SIT/content | `frontend/`, `blog/`, `sit/` va tegishli template/CSS |
| Runtime va deploy | `core/settings.py`, `core/runtime_gate.py`, `deploy/`, `Dockerfile`, `Procfile`, `.github/workflows/ci.yml` |

Route authority — `core/urls.py` va domain `urls.py` fayllari. Frontend V1 va
backoffice o'tishlari `core/flags.py`dagi flaglar hamda renderer/view
tekshiruvlariga bog'liq; bitta eski template nomini barcha sahifalarning
amaldagi qobig'i deb qabul qilmang.

## O'zgartirishda saqlanadigan chegaralar

- Access uchun raw `status == active` emas, canonical enrollment/access
  qarori ishlatiladi. Checkout niyati hali entitlement emas.
- Lesson ochilishi completion emas; review, XP, release va notification
  tegishli canonical writerning transaction/idempotency tartibidan o'tadi.
- `courses.Certificate` o'quv oqimidagi canonical sertifikat modeli;
  `gamification.Certificate`ni unga avtomatik teng deb hisoblamang.
- Support natija/yetkazish ekranlari diagnostika va mavjud qaror yuzalariga
  kirish beradi; yangi grade, access yoki notification writer yaratmaydi.
- `SystemAuditEvent` append-only. Owner mutationi uchun reason, confirmation
  va audit naqshi mavjud audited surface'dan olinadi. `backoffice_ai_control`
  settings/policy writerlari va `AISettingsAdmin` hali shu retrofitga muhtoj;
  owner-only ruxsat bu A2 audit qarzini yopmaydi.
- Vaqt/limit/threshold — DB runtime settings; on/off — `core/flags.py`.
  Protokol faktlari va safety floor uchun istisnolar agent qoidalarida.
- Private fayl public media orqali berilmaydi; upload turi va hajmi serverda
  tekshiriladi. URL yoki socket ochilgani doimiy access huquqi emas.
- AI provider access, payment, grade yoki progress uchun system-of-record
  emas. Remote call global supply pre-reservationdan o'tadi; ledger xatosida
  call fail-closed to'xtaydi.
- Guest limiti providerdan oldin atomik slot oladi; muvaffaqiyatsiz javobda
  slot qaytariladi. SmartForm va reindex supply fingerprintlari takror remote
  callni to'xtatadi; bu umumiy crash-recovery lease kafolati emas.
- Outbox claim/lease, retry/backoff va dead-letter replay ishlatadi.
  Yetkazish kafolati at-least-once; exactly-once deb talqin qilinmaydi.

## Runtime va tekshiruvni ajratish

Local profil SQLite/filesystem, in-memory cache/channel va eager Celery bilan
ishlay oladi. Non-local profil cache/channel manzili yoki shared broker
bo'lmasa `core/runtime_gate.py` orqali startupni to'xtatadi. Production
compose'da PostgreSQL/pgvector, Valkey, web, worker, beat, outbox, migrate va
Caddy bor. Koddagi konfiguratsiya mavjudligi xizmatlar hozir ishlayotganini
isbotlamaydi.

[2026-09-26 AWS reliz dalili](frontend-v1/R2-READY-V1-AWS.md) — so'nggi qayd
qilingan reliz dalili; ushbu hujjat sinxronida server tekshirilmadi. Keyingi
lokal backoffice o'zgarishlari AWSga chiqarilgan deb hisoblanmaydi.
DigitalOcean admission cheklovi, owner qabuli, native qurilma sinovi va
production qarori tegishli rejalarda alohida yuritiladi; ularning faol holati
uchun [hub](README.md)dan boshlang.

Testlarda `.env.local` yuklanishini va tashqi provider chaqiruvini o'chiring.
Quyidagi buyruqlar namuna; ular ushbu docs-only sinxronida bajarildi degan
claim emas. Taskka tegishli test modulini tanlang:

```powershell
$env:AZURELMS_SKIP_ENV_FILE='1'
$env:APP_ENV='local'
$env:GEMINI_API_KEY=''
$env:TELEGRAM_BOT_TOKEN=''
$env:DIGITALOCEAN_INFERENCE_API_KEY=''
.\venv\Scripts\python.exe manage.py test <changed-app-or-module>
git diff --check
```

Inherited muhitdagi remote service/DB sozlamalarini ham tekshirib, task uchun
ajratilgan test konfiguratsiyasidan foydalaning. File-DB contention testlari
`AZURELMS_TEST_FILE_DB=1` talab qiladi. `reindex_rag --force` va
`reindex_ai_memory --force` remote embedding ishlatishi mumkin; oddiy smoke
sifatida ishga tushirilmaydi.

Muhim test xaritalari: `core.test_golden_flow_e2e`, domain service testlari,
`core.test_backoffice_*`, `core.test_student_support_*`, `core.test_design_*`,
`courses.test_*authoring*`, `tests/frontend_v1/`, `classbook` realtime/load
sinovlari, `core.test_private_media`, `core.test_upload_validation` va
`aicontrol.test_supply_concurrency`. CI joblari va release tartibi uchun
workflow hamda [agent qoidalari](rules-for-agents.md) authoritative.

## Saqlangan tarixiy snapshot — 2026-09-14

Quyidagilar avvalgi Codex kontekstidan saqlangan **o'sha sanadagi** dalillar.
Ular 2026-10-13 holati, joriy hajm yoki yangi bajarilgan test natijasi emas.
O'sha snapshotning bazasi: `origin/main = ef99cb2`.

| Qayd | 2026-09-14 snapshoti |
|---|---|
| Hajm | 794 tracked fayl, taxminan 75 ming Python qatori, 126 template, 19 CSS, 16 JS |
| Custom Django qatlam | 12 product app + `core`; `ai/` oddiy Python package |
| Stack | Python 3.12.10, Django 6.0.8, Daphne 4.2.3, Channels 4.3.2, Celery 5.6.2, `google-genai` 1.65.0, Aiogram 3.30.0 |
| AI registry | 14 skill; routing mavjudligi vision/grounding capability dalili emas |
| `manage.py check` | 0 issue |
| `makemigrations --check --dry-run` | Drift yo'q |
| `system_audit --json --fail-on never` | 16 capability: 9 GREEN, 7 AMBER, 0 RED |
| `core.test_golden_flow_e2e` + `classbook.tests` | 24/24 OK |

AMBER izohlari o'sha local tekshiruvda Telegram token/dispatcher, Gemini
kaliti, RAG indeks, outbox worker belgisi va DB/media zaxira holatiga tegishli
edi. Bu sabablardan bugungi runtime holati chiqarilmaydi. Oldingi snapshotdagi
“hali qilinmagan” bandlar yangi ish navbati sifatida ko'chirilmaydi; hozirgi
kod va tegishli rejaning sanalangan dalili qayta o'qiladi.

Bu xarita canonical owner, yangi surface yoki runtime/security boundary
almashganda yangilanadi. Oddiy CSS o'zgarishi yoki har yangi test soni uchun
parallel status jadvali yaratilmaydi.
