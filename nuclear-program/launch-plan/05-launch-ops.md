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
| AI | `AI_CHAT_PROVIDER=gemini`; DO key bo'sh | Gemini remote call qiladi; free-tier global guard hali yo'q |

`LOCAL_USE_REMOTE_SERVICES=False` DigitalOcean DB/cache/storage'ni o'chiradi, lekin Gemini API'ni o'chirmaydi va AI provider factory'ni ham guard qilmaydi. DO inference hozir bo'sh key + `AI_CHAT_PROVIDER=gemini` bilan operationally o'chiq, code-level HOLD enforcement esa A8/A1a gap'i. `system_audit` local profilni GREEN ko'rsatishi quota yoki production readiness dalili emas.

### Kelajak production target — vendor-neutral, `HOLD`

DigitalOcean kreditlari bekor qilingan. App Platform, Serverless Inference, Managed PostgreSQL/Valkey va Spaces owner productionni qayta admission qilmaguncha target emas. Quyidagi contract vendor tanlashdan oldin ham amal qiladi; DigitalOcean keyin faqat nomzodlardan biri bo'lishi mumkin.

| Komponent | Process/xizmat | Gate |
|---|---|---|
| Web | Daphne/ASGI | HTTP + WebSocket readiness |
| Celery worker | `celery -A core worker -l info` | broker round-trip + heartbeat |
| Celery beat | `celery -A core beat -l info` | subscription lifecycle schedule va heartbeat |
| Telegram outbox | `python manage.py telegram_outbox --loop` | Majburiy alohida process; atomic claim qurilmaguncha aynan 1 replica |
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
- Ikkinchi replica faqat DB atomic claim/lease, lease expiry, exponential retry/backoff va terminal dead-letter qurilgach. User-facing notification copy duplicate kelsa ham zarar qilmaydigan bo'ladi.

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

**Joriy foundation (2026-08-14):** `/backoffice/control/` active superuser uchun read-only stoplight; brand va landing uchun reason+confirmation+`LogEntry`li tor mutation surface'lari bor. DB, cache, Channels, Celery config, Telegram outbox, media, AI provider/policy, RAG, security va release identity bitta snapshotdan olinadi; `system_audit` shu servis adapteri. Hali umumiy append-only audit, global flags/kill switch, active worker heartbeat, `ReleaseRecord`, backup/email/memory va Gemini budget/cooldown probe'lari ulanmagan. Credential borligi AI supply sog'lom degani emas.

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

Hozir A1a shu checksni local runnerda reproduksiya qiladi; `.github/workflows` hali yo'q. `main`dan public deploy A1b `HOLD` ochilib, gate'lar o'tgachgina. Migration oldidan backup/restore point; deploydan keyin readiness, login/Telegram auth, enrollment, AI async task, outbox DM va private-media permission smoke. Gate yiqilsa traffic ochilmaydi; destructive DB rollback avtomatik emas.

Har release uchun commit SHA, migrationlar, gate natijalari, deploy/rollback holati va owner qarori `ReleaseRecord`/system auditda saqlanadi.

## 5. Observability, backup va runbook

- Sentry: Django, Channels va Celery xatolari; secret/PII redaction.
- Uptime/readiness: public page, login, WebSocket, DB, Valkey, broker, worker, outbox va private-media denial.
- Queue SLO: queue age, pending/failed count, last success; alertlar ownerga bitta kanal orqali.
- Backup: localda SQLite/media recoverability smoke; kelajak productionda managed DB snapshot + encrypted export va media versioning/lifecycle.
- Restore drill: yangi isolated targetga restore → migration/schema check → owner smoke → evidence timestamp.
- Runbook: RED sabab, user ta'siri, kill switch, fallback, escalation va recovery check.

## 6. AI quality, privacy va Gemini free-tier supply gate

Mavjud AI panel per-user token limit/usage/resetni boshqaradi; default 100k/5h va 1m/hafta upstream Gemini RPM/RPD yoki project supply'ni himoya qilmaydi. Limiter fail-open, staff odatda exempt, SmartForm/guest/embedding calllari to'liq ledgerda emas. Shu sabab free-tier budget `A8` stop-gate.

| Gate | Metrika |
|---|---|
| Technical | failed/fallback rate, queue delay, TTFT, p50/p95/p99, empty response, provider attempt/error taxonomy |
| Quality/safety | versionlangan golden eval, Turkish/CEFR, grounding, prompt injection, permission/data leak, negative feedback repair |
| Cost | provider/model price snapshot, estimated cost, user/day va global/day budget, plan margin |

### A8 free-tier acceptance

- Yagona provider-call ledger: chat, grounding, SmartForm extractor, bot guest demo, RAG/memory embedding, retry/failure.
- Global daily request/token cap; atomic pre-call reservation va actual usage reconciliation. Staff ham global supply budgetga kiradi.
- Free-model allowlist; Pro/preview va `heavy` effort default yopiq. Bitta primary + maksimum bitta verified-free fallback.
- Prompt/output cap, global deadline va duplicate logical request uchun bitta provider zanjiri.
- `429/quota/billing` circuit breaker: cooldown ochiq bo'lsa yangi network call `0`; 9-model fan-out yo'q.
- Control Center: mode, configured cap, used/reserved/remaining, attempt, untracked call va cooldown. Tashqi quota raqami hujjatga hardcode qilinmaydi.
- Local/pre-prod DO HOLD fail-closed: explicit owner admissionisiz `digitalocean` tanlovi startup/audit RED va network call `0`.

### Degradatsiya tartibi

1. automatic/`heavy` web search yopiladi; explicit searchgina qoladi;
2. yangi embedding/reindex batch'i to'xtaydi, cache/lexical fallback ishlaydi;
3. guest/demo AI deterministic FAQ yoki vaqtincha disabled bo'ladi;
4. non-critical AI featurelar yopiladi;
5. core enrollment, lesson, quiz, assignment, payment, messenger human flow va Telegram deterministic adapterlari ishlashda qoladi.

- System instructions haqiqiy system-role'da; RAG/PDF/memory/submission typed untrusted context.
- End-to-end hard deadline `20s`; maksimal `1 primary + 1 fallback`; bu hozir target, A8 testidan oldin mavjud kafolat emas.
- Request boshida transactional reservation, yakunda actual usage reconciliation; usage yo'q bo'lsa konservativ estimate.
- “Clear memory” archive emas: product copy, hard-delete/retention va trace/run redaction bir contractda.
- Thresholdlar Control Center'da versionlanadi. Sample minimumiga yetmagan holat `PASS` emas, `INSUFFICIENT_DATA`.
- Critical privacy/permission eval xatosi release'ni bloklaydi. Configured supply budget 80% alert; 100% circuit/degradation/kill switch. “Bepul” cost=0 deb yozilmaydi — quota ham scarcity.

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
- Har kun: Control Center stoplight, queue/worker, feedback, teacher review time, Gemini attempts/remaining/cooldown va untracked calls. Sentry production admissionidan keyin.
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
