# 05 — Launch operatsiyalari: Control Center, deploy, security, QA va go/no-go

*Rebaseline: 2026-08-14. Bu hujjat local/pre-production haqiqatini kelajak production arxitekturasidan ajratadi. “Maqsad” deb yozilgan capability implementatsiya va test tugamaguncha joriy tizim deb hisoblanmaydi.*

## 1. Runtime va kelajak deploy arxitekturasi

### Joriy local/pre-production profil — `LOCAL BOOT VERIFIED`, production emas

| Qism | Joriy qiymat | Chegara |
|---|---|---|
| App | `APP_ENV=local`, Django/Daphne local | Public production SLA yo'q |
| DB | SQLite | Production migration/restore dalili emas |
| Cache/Channels | LocMem + in-memory | Multi-process coordination bermaydi |
| Celery | `memory://` + eager | Worker/beat/outbox production heartbeati yo'q |
| Media | local filesystem, `USE_S3=False` | Private object-storage policy hali qurilmagan |
| Telegram | polling/local token | Public webhook va alohida outbox process `HOLD` |
| AI | `AI_CHAT_PROVIDER=gemini`; DO key bo'sh; `AI_ALLOW_DIGITALOCEAN=False` | A8 global supply guard implement/test qilingan; real DB contention proof pending |

`LOCAL_USE_REMOTE_SERVICES=False` DigitalOcean DB/cache/storage'ni o'chiradi, lekin Gemini API'ni o'chirmaydi. AI provider factory alohida fail-closed: DO faqat explicit `AI_ALLOW_DIGITALOCEAN=True` owner admissionida yaratiladi, noma'lum provider esa rad etiladi. `system_audit` local profil yoki AI supply stoplightini GREEN ko'rsatishi Google quota reachability, true concurrency yoki production readiness dalili emas.

### Kelajak production target — vendor-neutral, `HOLD`

DigitalOcean kreditlari bekor qilingan. App Platform, Serverless Inference, Managed PostgreSQL/Valkey va Spaces owner productionni qayta admission qilmaguncha target emas. Quyidagi contract vendor tanlashdan oldin ham amal qiladi; DigitalOcean keyin faqat nomzodlardan biri bo'lishi mumkin.

| Komponent | Process/xizmat | Gate |
|---|---|---|
| Web | Daphne/ASGI | HTTP + WebSocket readiness |
| Celery worker | `celery -A core worker -l info` | broker round-trip + heartbeat |
| Celery beat | `celery -A core beat -l info` | subscription lifecycle schedule va heartbeat |
| Telegram outbox | `python manage.py telegram_outbox --loop` | Majburiy alohida process; atomik claim/lease qurilgan (2026-08-15), qolgani exponential backoff va dead-letter |
| DB | Managed PostgreSQL-compatible + pgvector | migration, DB ping, vector smoke, restore drill |
| Cache/Channels/Broker | Managed Redis/Valkey-compatible | production'da in-memory/memory fallback taqiqlanadi |
| Public media | S3-compatible object storage | marketing asset, course thumbnail, public preview; explicit policy |
| Private media | Private object storage + permission-checked download | receipt, assignment, messenger attachment, exam audio |
| Static | Whitenoise | `collectstatic` CI/deploy gate |

**Future production env:** `SECRET_KEY`, `APP_ENV`, `APP_DOMAIN`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `SECURITY_STRICT=True`, `DATABASE_URL`, `VALKEY_URL`/`REDIS_URL`, `CELERY_BROKER_URL`, private/public object-storage config, admitted AI provider key/model policy, `TELEGRAM_BOT_TOKEN`, unique webhook secret, `TELEGRAM_MODE=webhook`, email provider. DO-specific env hozir bo'sh qoladi.

### Broker fail-fast gate

`APP_ENV != local` bo'lsa haqiqiy remote broker/cache/channel majburiy. Bo'sh qiymat, `memory://` yoki in-memory backend web/worker/beat startup'ini non-zero exit bilan to'xtatadi. Bu contract hozir `PLANNED`; local rejim ataylab in-memory ishlaydi. Readiness URL mavjudligini emas, configured connection va task round-tripni tekshiradi.

### Telegram outbox gate

- **Future production GO sharti:** app spec/Procfile'ga outbox process qo'shilgan va 1 replica ishlaydi; joriy Procfile'da u yo'q. Hozir local polling smoke yetarli, public process `HOLD`.
- Test Notification konfiguratsiyadagi SLA ichida `TelegramOutbox.sent` bo'ladi.
- Control Center pending soni, eng eski pending yoshi, failed soni va so'nggi muvaffaqiyatni ko'rsatadi.
- Owner failed itemni reason bilan replay qiladi; replay auditga yoziladi.
- Delivery contract `at-least-once, duplicate-tolerant`: Telegram downstream aynan-once idempotency bermaydi; send muvaffaqiyatli bo'lib DB update'dan oldin process o'lsa duplicate oynasi qoladi.
- DB atomic claim/lease va lease expiry **qurilgan** (2026-08-15, A1a): parallel workerlar bir qatorni ikki marta olmaydi va o'lgan worker qatori muzlab qolmaydi. Ikkinchi replica uchun qolgani — exponential retry/backoff va terminal dead-letter. Kafolat at-least-once bo'lgani uchun notification matni duplicate kelsa ham zarar qilmaydigan bo'lishi kerak.

### Private media gate

Avval upload inventari tasniflanadi: marketing/course thumbnail va public preview — public; avatar va CKEditor lesson image — alohida owner qarori bilan public yoki authenticated-public; payment receipt, assignment submission, messenger attachment va exam speaking audio — private. Private obyektlar ACL bilan storage key sifatida saqlanadi; doimiy public yoki signed URL DBga yozilmaydi. Permission-checked endpoint qisqa muddatli signed URL yoki stream qaytaradi.

| Actor | Ruxsat |
|---|---|
| Student | faqat o'z fayli yoki qatnashayotgan chat fayli |
| Teacher | faqat explicit course/cohort scope |
| Owner | operatsion tekshiruv scope'i |
| Anonymous | hech qachon |
| Worker | faqat job talab qilgan scoped object |

Gate: anonymous GET va cross-user access rad; signed URL expiry test; bot/storage `.open()` bilan ishlaydi.

## 2. Azure Control Center — yagona operatsion boshqaruv

**Maqsad canonical nuqta:** `/backoffice/control/`. Bu yangi alohida mahsulot emas, mavjud backoffice va `aicontrol`ni owner-only bitta shellga tutashtiradi. `/backoffice/ai-control/` keyinchalik AI tabiga ko'chadi yoki compatibility redirect bo'ladi.

```text
Overview
├── Core flow stoplight
├── Queues & workers
├── Capabilities & effective config
├── Feature flags / kill switches
├── Permissions
├── AI quality / latency / cost
├── Releases / rollback
└── System audit
```

Kirish faqat `is_superuser`. Har mutation CSRF, sabab, explicit confirmation, idempotency key va append-only `SystemAuditEvent` talab qiladi. Browserdan arbitrary shell command bajarilmaydi; faqat allowlist qilingan service amallari.

Capability registry DB, cache/channels, broker, Celery worker/beat, Telegram webhook/outbox, public/private media, AI provider, RAG, memory, backup va emailni ro'yxatlaydi. Har capability: criticality, owner, health probe, runbook, feature flag/kill switch, dependency va so'nggi heartbeat.

Stoplight:

- **GREEN:** barcha majburiy probe va release gate o'tgan;
- **AMBER:** degradatsiya bor, lekin oltin kurs oqimi ishlaydi va fallback aniq;
- **RED:** checkout/access/data-loss/privacy xavfi, majburiy worker yo'q yoki critical eval yiqilgan. Traffic/capability ochilmaydi.

**Joriy foundation (2026-08-19):** yuqoridagi 2026-08-14 xatboshisidan beri ochiq qolgan bandlarning aksariyati yopildi. Endi kodda: append-only `SystemAuditEvent` ledgeri (`core/audit.py` yagona yozish nuqtasi), AI kill switch (`/backoffice/control/ai-kill-switch/`), AI circuit cooldown tozalash (`/backoffice/control/ai-circuit-reset/`), bevosita o'lchanadigan `WorkerHeartbeat` va `ReleaseRecord` + migration drift detektori. **Hali ulanmagan:** AI quality/cost release gate (A9 ning ishi). *(Backup, email va memory probe'lari 2026-08-20 da qo'shildi — ular avval capability registrida umuman yo'q edi.)* *(Umumiy feature flag registri 2026-08-20 da qo'shildi: `core/flags.py` + `/backoffice/control/flags/`. Hozircha ikkita flag ulangan — ochiq ro'yxatdan o'tish va Telegram outbox; qolgan capabilitylar hamon flagsiz. Money cost ledgeri ham o'sha kuni: `core/ai_cost.py` + `/backoffice/control/ai-cost/`, narxlanmagan sarf nol deb yozilmaydi.)* `ReleaseRecord` modeli bor, ammo gate natijalari va deploy holatini yozadigan tomon A1b `HOLD` da qolgani uchun hali yo'q.

**Joriy foundation (2026-08-14):** `/backoffice/control/` active superuser uchun read-only stoplight; brand va landing uchun reason+confirmation+`LogEntry`li tor mutation surface'lari bor. DB, cache, Channels, Celery config, Telegram outbox, media, AI provider/policy, RAG, security va release identity bitta snapshotdan olinadi; `system_audit` shu servis adapteri. AI probe endi free-tier mode, DO admission, supply enforcement, daily request/token va minute request used/limit/remaining, attempt/event counts hamda cooldownni xavfsiz ko'rsatadi; supply policy Django admin'da owner tomonidan boshqariladi, event/state esa read-only ko'riladi. Hali umumiy append-only audit, system-wide flags/kill switch, active worker heartbeat, `ReleaseRecord`, backup/email/memory va AI quality/cost release gate ulanmagan. Credential borligi AI supply sog'lom degani emas.

## 3. Permission matrix va system audit

| Amal | Owner/superuser | Teacher/staff | Student | Worker |
|---|---:|---:|---:|---:|
| Control mutation/kill switch/release | Ha | Yo'q | Yo'q | Yo'q |
| AI global/plan policy | Ha | Yo'q | Yo'q | Enforcement |
| Receipt qarori, broadcast, user block | Ha | Yo'q | Yo'q | Scoped execution |
| Attendance/grading | Ha | Faqat biriktirilgan scope | O'z yozuvi | Scoped job |
| Private media | Boshqaruv scope | Biriktirilgan kurs/cohort | O'z/chat scope | Job scope |

Teacher'ga kurs/cohort biriktirilmagan bo'lsa barcha ma'lumot ochilmaydi; default natija bo'sh. Inactive staff har bir adapterda rad qilinadi.

`SystemAuditEvent` append-only: vaqt, actor/snapshot, source (`web|bot|worker|release`), action code, target, scope, redacted before/after, request/correlation ID, idempotency key, reason, IP/user-agent, outcome/error va release SHA. UI orqali edit/delete yo'q.

Minimum audit: permission/role, receipt qarori, enrollment transition, lesson release, grade/review, AI policy/reset/bonus/block, broadcast/outbox replay, kill switch, private-media denial, release va rollback.

**Holat (2026-08-19):** yuqoridagi ro'yxatga `ai.circuit.reset` (cooldown tozalash) va `release.decision` (owner release qarori) qo'shildi — ya'ni **release/rollback endi auditlanadi**, quyidagi 2026-08-16 yozuvidagi "keyinroq keladi" bandi yopildi. Kodda yozilayotgan amallar to'liq ro'yxati: `ai.kill_switch.enable/disable`, `ai.circuit.reset`, `brand.update`, `landing.update`, `lesson.release`, `assignment.review`, `receipt.verify`, `enrollment.transfer`, `enrollment.promote`, `private_media.denied`, `release.decision`. **Minimal ro'yxatdan hamon qolgani:** broadcast, per-user block, AI bonus va outbox replay (oxirgisi — amal mavjud emasligi uchun).

**Holat (2026-08-16):** kill switch, brend, landing, lesson release, grade/review, receipt qarori (tasdiq va rad etilgan urinish), enrollment transfer/promotion va private-media denial ledgerda. Private-media denial ataylab cheklangan: faqat autentifikatsiyadan o’tgan aktor va 15 daqiqalik takrorlanish oynasi — ledger append-only, ya’ni skaner uni bosib keta olmasligi kerak. **Outbox replay auditlanmagan, chunki bunday amal hali mavjud emas** ( avtomatik lease qaytarish, owner tugmasi emas); band replay yuzasi qurilganda ochiladi. Release/rollback  bilan birga keladi.

## 4. CI, demo va production release gate

PR required checks:

1. `python manage.py check`
2. production-safe env bilan `python manage.py check --deploy`
3. `python manage.py makemigrations --check --dry-run`
4. to'liq test suite
5. PostgreSQL+pgvector va Valkey integration smoke
6. `python manage.py collectstatic --noinput`
7. secrets va dependency vulnerability scan
8. domain permission/idempotency va cross-adapter parity tests

**Holat (2026-08-15): sakkiztasi ham `.github/workflows/ci.yml` da avtomatlashtirildi va `main` branch protection'ida majburiy qilindi** — har PR'da va `main` ga har merge'dan keyin. `enforce_admins: true`, ya'ni owner ham `main` ga to'g'ridan-to'g'ri push qila olmaydi; yagona yo'l — uchala check yashil bo'lgan PR. "Gate yiqilsa traffic ochilmaydi" endi qoida emas, sozlama. Uchta ish: `checks` (offline: check, `check --deploy`, migration drift, collectstatic, permission/idempotency/parity to'plami, to'liq suite), `integration` (pgvector'li PostgreSQL + Valkey konteynerlari) va `supply-chain` (sir skani + `pip-audit`). Hech bir ish AI provayderiga chiqmaydi: `GEMINI_API_KEY` bo'sh va `AZURELMS_SKIP_ENV_FILE=1`, ya'ni free-tier kvota CI tomonidan yeyilmaydi.

§4.7 ning ikkinchi yarmi — bog'liqlik zaifligi. Gate ishga tushganda 19 paketda 93 advisory topilgan edi; o'sha kuni 20 paket ko'tarilib **hammasi yopildi**. `security/dependency-audit-baseline.json` reyestri bo'sh, ya'ni endi **har qanday** advisory CI'ni qizil qiladi — uni oqlaydigan yozuv yo'q. Istisno yozish yo'li ochiq qolgan (major/RC ko'tarishni talab qiladigan holatlar uchun), ammo sababsiz va `review_by` sanasisiz istisno qabul qilinmaydi.

`main`dan public deploy A1b `HOLD` ochilib, gate'lar o'tgachgina. Migration oldidan backup/restore point; deploydan keyin readiness, login/Telegram auth, enrollment, AI async task, outbox DM va private-media permission smoke. Gate yiqilsa traffic ochilmaydi; destructive DB rollback avtomatik emas.

Har release uchun commit SHA, migrationlar, gate natijalari, deploy/rollback holati va owner qarori `ReleaseRecord`/system auditda saqlanadi.

## 5. Observability, backup va runbook

- Sentry: Django, Channels va Celery xatolari; secret/PII redaction.
- Uptime/readiness: public page, login, WebSocket, DB, Valkey, broker, worker, outbox va private-media denial.
- Queue SLO: queue age, pending/failed count, last success; alertlar ownerga bitta kanal orqali.
- Backup: localda SQLite/media recoverability smoke; kelajak productionda managed DB snapshot + encrypted export va media versioning/lifecycle.
- Restore drill: yangi isolated targetga restore → migration/schema check → owner smoke → evidence timestamp.
- Runbook: RED sabab, user ta'siri, kill switch, fallback, escalation va recovery check.

## 6. AI quality, privacy va Gemini free-tier supply gate

Mavjud per-user panel 5h/weekly token allowance'ni boshqaradi; u product access siyosati bo'lib, fail-open va staff-exempt xulqi saqlangan. Uning ustida alohida A8 project supply gate'i bor: staff ham kiradigan, ledger DB xatosida fail-closed, global kunlik+minute request va kunlik token pre-reservation/reconciliation. Chat, SmartForm, guest, RAG/memory embedding va reindex calllari `AISupplyEvent`da hisoblanadi; grounding call turi faqat kelajak paid/admitted rejim uchun saqlangan. Minute cap projectning ichki RPM-uslubidagi guardi; Google'ning dynamic/account-specific external RPM/RPD kvotasi emas.

| Gate | Metrika |
|---|---|
| Technical | failed/fallback rate, queue delay, TTFT, p50/p95/p99, empty response, provider attempt/error taxonomy |
| Quality/safety | versionlangan golden eval, Turkish/CEFR, grounding, prompt injection, permission/data leak, negative feedback repair |
| Cost | provider/model price snapshot, estimated cost, user/day va global/day budget, plan margin |

### A8 holati — `IMPLEMENTED/TESTED — LOCAL REGRESSION GREEN`

- Yagona provider-call ledger: chat, grounding, SmartForm extractor, bot guest demo, RAG/memory embedding, reindex, retry/failure. Main chat auxiliary retrievaldan oldin pre-reserve qiladi va `AIResponseRun.idempotency_key` duplicate taskni to'xtatadi.
- Global daily+minute request va daily token cap; transactional pre-call reservation va actual usage reconciliation. Staff ham global supply budgetga kiradi; usage bo'lmasa konservativ reservation charge qoladi.
- Model allowlist: primary `gemini-3.1-flash-lite`, yagona temporary fallback `gemini-3.5-flash-lite` (**2026-08-19 da almashtirildi**, pastda). Pro/preview clamp qilinadi; Free tier API grounding barcha effortlarda hard-off, guest default yopiq.
- Text caps: output `640` token, prompt `12,000` belgi, request timeout `15s`, end-to-end deadline `35s`. **2026-08-19 da 8s/20s dan ko'tarildi:** Google 10s dan past deadline'ni `400 INVALID_ARGUMENT` bilan rad etadi va so'rov umuman bajarilmaydi. Xato matnida "deadline" borligi uchun provider uni `timeout` deb tasniflagan va sabab yashiringan edi. O'lchangan haqiqiy javob vaqti to'liq 12k kontekstda `1.8-2.8s`; yangi qiymatlar zaxira bilan minimumdan yuqorida va ikkita urinishga yetadi. Embedding: `64` input/batch, har input `8,000` belgi, batch `64,000` belgi, timeout `8s`; SDK retry `1` physical attempt.
- `429/quota/billing` circuit breaker: birinchi quota xatosida boshqa modelga fan-out yo'q; cooldown ochiq bo'lsa yangi network call `0`. Non-quota logical chain maksimal `1 primary + 1 fallback`.
- Control Center: mode, API grounding disabled/enabled, configured cap, daily/minute used/remaining, actual attempt, reserved/failed/rejected va cooldown stoplight. Tashqi quota raqami hardcode qilinmaydi.
- Local/pre-prod DO HOLD fail-closed: explicit owner admissionisiz `digitalocean` provider yaratilmaydi; snapshot RED va DO network call `0`. Noma'lum provider ham fail-closed.
- Targeted mock/offline tests yuqoridagi provider/supply/idempotency/caller guardlarini tekshirgan. Provider kalitlari va env-file loading o'chirilgan final post-A8 full suite 527/527, `manage.py check` 0 issue, migration drift yo'q va local `system_audit` 10/10 GREEN. Real SQLite/PostgreSQL concurrent contention proof hali kutilmoqda; shu sabab status `EVIDENCE READY` emas.

**Model lifecycle riski:** Google'ning [3.1 Flash-Lite model kartasi](https://ai.google.dev/gemini-api/docs/models/gemini-3.1-flash-lite), [pricing jadvali](https://ai.google.dev/gemini-api/docs/pricing), [rate-limit yo'riqnomasi](https://ai.google.dev/gemini-api/docs/rate-limits) va [deprecation jadvali](https://ai.google.dev/gemini-api/docs/deprecations) tekshirildi. 3.1 Flash-Lite stable/free-tier/cost-efficient primary sifatida tanlandi. **2026-08-19 — 2.5 Flash-Lite o'ldi, review deadline'dan oldin.** Jonli chaqiruv `404 NOT_FOUND — no longer available to new users` qaytardi va AI javob bermay qoldi; Google `gemini-3.5-flash-lite` ga o'tishni so'radi. Fallback o'shanga almashtirildi va ikkala model jonli tekshirildi. Muhim tafsilot: Google'ning `models.list` endpointi o'lik modelni hamon ro'yxatda ko'rsatadi — ya'ni ro'yxat hisobga xos ruxsatni bildirmaydi, faqat haqiqiy `generateContent` chaqiruvi haqiqatni aytadi. Shu sababli iste'moldan chiqqan modellar `ai/providers/gemini.py` dagi `RETIRED_MODELS` da qo'lda yuritiladi va test ularning sozlamaga qaytishini to'xtatadi. 2026-08-14 login qilingan `AzureAI` Free-tier snapshotida 3.1 Lite **15 RPM / 250K input TPM / 500 RPD**, yangi 3.7 Flash esa **5 RPM / 250K input TPM / 20 RPD**; shu sabab 3.7 hozir admit qilinmadi. Exact tashqi limitlar project/account holatiga bog'liq va o'zgarishi mumkin.

**Migrationlar va tekshiruv buyruqlari:**

```powershell
python manage.py migrate
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test ai.providers.tests aicontrol.tests messenger.test_embedding_supply
python manage.py system_audit --json --fail-on never
```

Schema o'zgarishlari: `aicontrol/migrations/0002_ai_supply_budget.py`, `messenger/migrations/0014_ai_response_idempotency.py`, `users/migrations/0015_free_tier_model_default.py` va deterministic notification ordering uchun `users/migrations/0016_alter_notification_options.py`; to'rttalasi local SQLite'ga apply qilingan. `reindex_rag --force` va `reindex_ai_memory --force` jonli embedding supply'ini ishlatadi; faqat budget/credential ataylab yoqilganda ishga tushiriladi.

### Degradatsiya tartibi

1. Free tier'da automatic/explicit/heavy API groundingning barchasi yopiq; search intent bitta plain chatga tushib live tekshiruv yo'qligini halol aytadi;
2. yangi embedding/reindex batch'i to'xtaydi, cache/lexical fallback ishlaydi;
3. guest/demo AI deterministic FAQ yoki vaqtincha disabled bo'ladi;
4. non-critical AI featurelar yopiladi;
5. core enrollment, lesson, quiz, assignment, payment, messenger human flow va Telegram deterministic adapterlari ishlashda qoladi.

- System instructions haqiqiy system-role'da; RAG/PDF/memory/submission typed untrusted context.
- End-to-end hard deadline `20s`; maksimal `1 primary + 1 fallback` provider va targeted testlarda enforcement qilingan.
- Request boshida transactional reservation, yakunda actual usage reconciliation; usage yo'q bo'lsa konservativ estimate.
- SQLite va PostgreSQL'dagi haqiqiy parallel process contention/transaction proof hali pending. SmartForm/guest counterlari va lesson reindex batch'i uchun to'liq concurrency lease/claim ham qurilmagan.
- Current Gemini adapterida vision unavailable; `image_qa` routing yoki upload primitive'i rasm tahlili capability'sini ochmaydi.
- “Clear memory” archive emas: product copy, hard-delete/retention va trace/run redaction bir contractda.
- Thresholdlar Control Center'da versionlanadi. Sample minimumiga yetmagan holat `PASS` emas, `INSUFFICIENT_DATA`.
- Critical privacy/permission eval xatosi release'ni bloklaydi. Configured supply budget 80%da AMBER; 100%da RED, pre-network denial va degradatsiya. System-wide audited kill switch A2ning qolgan scope'i. “Bepul” cost=0 deb yozilmaydi — quota ham scarcity.

## 7. QA matritsasi

**Oqim × actor × adapter × device × data state.** Minimum:

- Actors: anonymous, student, scoped teacher, inactive staff, owner.
- Adapters: web, Telegram bot, Mini App, Messenger/WebSocket, worker.
- Devices: desktop Chrome, Android Chrome 360/390px, iOS Safari, exam landscape 568×320/640×360.
- States: empty, normal, full/large, expired/frozen, duplicate/replay, provider/worker degraded.

Oltin oqimlar: auth/account claim; checkout/receipt/enrollment; lesson lifecycle; quiz/assignment/review; exam media/submit/result; Messenger reconnect/access expiry; AI text/PDF/limit/fallback; current Gemini'da image capability unavailable holati; private media; owner Control Center mutation/rollback.

Bug bar: Sev-0 data loss/auth/payment/access/privacy — darhol; Sev-1 core flow yoki owner control — taqdimot/betadan oldin; Sev-2 faqat feature flag bilan yopilishi mumkin.

## 8. Beta va monetizatsiya protokoli

Rollout: staff → 10–15 learner → bitta cohort → keng launch. Har bosqich alohida flag va stop condition bilan.

- Telegram guruhi jonli dars/material fallback'i sifatida qoladi.
- Har kun: Control Center stoplight, queue/worker, feedback, teacher review time va Gemini attempts/remaining/cooldown. Caller coverage regressioni alohida test contracti; joriy snapshot avtomatik “untracked call” detektori emas. Sentry production admissionidan keyin.
- Survey: onboarding to'sig'i, first activity completion, usefulness, willingness-to-pay va testimonial consent.
- Premium GO: structured flow `≥98%`, first completion `≥60%`, meaningful learning delta, teacher time `≥30%` kamayish, p95 text `<8s`, AI cost/revenue `≤25%`, critical safety/access `0`.
- Gate o'tmasa core course launch qilinishi mumkin, AI premium esa beta/yopiq qoladi; narx oshirilmaydi.

### Premium metric contract

| Metrika | Formula va source | Window / minimum sample | Yetmasa |
|---|---|---|---|
| Structured flow success | `completed_or_validly_escalated / started`; outcome events | rolling 14 kun, `N≥50` session | `INSUFFICIENT_DATA` |
| First activity completion | first `practice_session_completed / first_started`; outcome events | eligible cohort 14 kun, `N≥20` learner | `INSUFFICIENT_DATA` |
| Learning delta | matched pre/post item accuracy yoki writing rubric v2−v1 | `N≥20` matched learner/artifact | `INSUFFICIENT_DATA` |
| Teacher time reduction | beta median review minutes vs pre-beta baseline | `N≥20` reviewed artifact har davrda | `INSUFFICIENT_DATA` |
| AI cost/revenue | paid cohort AI+speech+storage cost / shu capability uchun incremental collected revenue | 14 kun, `N≥10` paid user va revenue `>0` | `INSUFFICIENT_DATA`; divide-by-zero yo'q |

Event nomi, numerator/denominator, cohort/plan filter va timezone versionlangan metric registry'da bo'ladi. Bepul plan monetizatsiya denominatoriga kirmaydi; eval sample minimumi alohida A9 gate bo'yicha `≥150`.

## 9. 20-sentyabr taqdimoti va production qarori

8–10 daqiqalik demo ikki haqiqatni ko'rsatadi:

1. **Learner Outcome Loop:** dars → xato evidence → structured practice/revision → oldingi/yangi proof → zarur bo'lsa teacher handoff.
2. **Solo-owner Control:** Azurbek health, queues, release, payment/access, AI quality/cost va kill switchni bitta markazdan ko'radi.

Demo account fresh state'dan qayta yaratiladi; fallback video, hotspot va Telegram fallback tayyor. 18 va 19-sentyabr repetitsiya. Public production ochilmagan bo'lsa demo local yoki vaqtinchalik xavfsiz tunnelda o'tadi va “production launch” deb atalmasin. 20-sentyabrda `README.md` bo'yicha alohida `DEMO GO`, `BETA GO`, `PRODUCTION HOLD` yoki `NO-GO` qarori beriladi.

### Demo/beta checklist — joriy scope

**Technical:** local CI/checks · A8 budget/cooldown drill · local readiness · polling/outbox local smoke · private-media/CSP permission tests · local backup recoverability · deterministic fallback · owner kill-switch drill · no secret in repo/log.

**Product:** oltin yo'l 3 qurilmada · scoped teacher flow · payment/access parity · mock/exam media · Progress Proof claim evidence · AI quality/cost gate yoki beta flag · manual DB rescue `0`.

**Marketing:** landing claim audit · testimonial consent · demo/fallback · pricing typed entitlement bilan mos · “unlimited/speaking/mastery” isbotsiz claim yo'q.

### Production GO qo'shimcha checklist — `HOLD`

Owner hosting/provider admissioni · production-safe env/secret rotation · remote broker/cache/channel fail-fast · outbox alohida process + DM smoke · managed DB/object storage · private signed media · `ReleaseRecord`/release SHA · Sentry/alerting · isolated remote backup restore · rollback drill · production-like health/readiness va load smoke. Bular local demo uchun yolg'on majburiyat emas, lekin public trafficdan oldin barchasi kerak.

### Launch kuni

T-2 soat: demo restore point, Control Center local stoplight, Gemini budget/cooldown drill, demo account va fallback → taqdimot → agar beta admissioni bo'lsa flag bosqichma-bosqich → blocker fix o'z branchida test+review → kun yakuni evidence manifest va marinebook. Public traffic faqat production gate alohida ochilganda.
