# 05 — Launch operatsiyalari: Control Center, deploy, security, QA va go/no-go

*Rebaseline: 2026-07-22. Bu hujjat maqsad operatsion arxitektura va release gate'larini belgilaydi. “Maqsad” deb yozilgan capability implementatsiya va test tugamaguncha joriy tizim deb hisoblanmaydi.*

## 1. Deploy arxitekturasi

**Maqsad platforma:** DigitalOcean App Platform. Quyidagi jadval joriy Procfile emas, production `GO` arxitekturasi; har qator implementatsiya va smoke tugamaguncha `PLANNED`.

| Komponent | Process/xizmat | Gate |
|---|---|---|
| Web | Daphne/ASGI | HTTP + WebSocket readiness |
| Celery worker | `celery -A core worker -l info` | broker round-trip + heartbeat |
| Celery beat | `celery -A core beat -l info` | subscription lifecycle schedule va heartbeat |
| Telegram outbox | `python manage.py telegram_outbox --loop` | Majburiy alohida process; atomic claim qurilmaguncha aynan 1 replica |
| DB | Managed PostgreSQL + pgvector | migration, DB ping, vector smoke |
| Cache/Channels/Broker | Managed Valkey | production'da in-memory/memory fallback taqiqlanadi |
| Public media | Spaces/S3 | marketing asset, course thumbnail, public preview; avatar va CKEditor lesson image uchun explicit policy kerak |
| Private media | Private Spaces storage + permission-checked download | receipt, assignment, messenger attachment, exam audio |
| Static | Whitenoise | `collectstatic` CI/deploy gate |

**Env:** `SECRET_KEY`, `APP_ENV`, `APP_DOMAIN`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `SECURITY_STRICT=True`, `DATABASE_URL`, `VALKEY_URL`/`REDIS_URL`, `CELERY_BROKER_URL`, private/public Spaces config, AI provider keys/model registry, `TELEGRAM_BOT_TOKEN`, unique webhook secret, `TELEGRAM_MODE=webhook`, email provider.

### Broker fail-fast gate

`APP_ENV != local` bo'lsa haqiqiy remote broker/cache/channel majburiy. Bo'sh qiymat, `memory://` yoki in-memory backend web/worker/beat startup'ini non-zero exit bilan to'xtatadi. Readiness URL mavjudligini emas, connection va task round-tripni tekshiradi.

### Telegram outbox gate

- **GO sharti:** App spec/Procfile'ga outbox process qo'shilgan va 1 replica ishlaydi; joriy Procfile'da u yo'q.
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

## 4. CI va release gate

PR required checks:

1. `python manage.py check`
2. production-safe env bilan `python manage.py check --deploy`
3. `python manage.py makemigrations --check --dry-run`
4. to'liq test suite
5. PostgreSQL+pgvector va Valkey integration smoke
6. `python manage.py collectstatic --noinput`
7. secrets va dependency vulnerability scan
8. domain permission/idempotency va cross-adapter parity tests

`main` faqat gate'lar o'tgach deploy qilinadi. Migration oldidan backup/restore point qayd etiladi. Deploydan keyin readiness, login/Telegram auth, enrollment, AI async task, outbox DM va private-media permission smoke. Gate yiqilsa trafik ochilmaydi; oldingi app artifactiga rollback qilinadi, destructive DB rollback avtomatik emas.

Har release uchun commit SHA, migrationlar, gate natijalari, deploy/rollback holati va owner qarori `ReleaseRecord`/system auditda saqlanadi.

## 5. Observability, backup va runbook

- Sentry: Django, Channels va Celery xatolari; secret/PII redaction.
- Uptime/readiness: public page, login, WebSocket, DB, Valkey, broker, worker, outbox va private-media denial.
- Queue SLO: queue age, pending/failed count, last success; alertlar ownerga bitta kanal orqali.
- Backup: managed PG daily snapshot + haftalik encrypted export; media versioning/lifecycle.
- Restore drill: yangi isolated targetga restore → migration/schema check → owner smoke → evidence timestamp.
- Runbook: RED sabab, user ta'siri, kill switch, fallback, escalation va recovery check.

## 6. AI quality, privacy va cost gate

Mavjud AI panel token limit/usage/resetni boshqaradi; bu hali to'liq release control emas. Premium AI uch qatlamdan o'tadi:

| Gate | Metrika |
|---|---|
| Technical | failed/fallback rate, queue delay, TTFT, p50/p95/p99, empty response, provider attempt/error taxonomy |
| Quality/safety | versionlangan golden eval, Turkish/CEFR, grounding, prompt injection, permission/data leak, negative feedback repair |
| Cost | provider/model price snapshot, estimated cost, user/day va global/day budget, plan margin |

- System instructions haqiqiy system-role'da; RAG/PDF/memory/submission typed untrusted context.
- End-to-end hard deadline `20s`; maksimal `1 primary + 1 fallback`; widget ham async oqimda.
- Request boshida transactional reservation, yakunda actual usage reconciliation; usage yo'q bo'lsa konservativ estimate.
- “Clear memory” archive emas: product copy, hard-delete/retention va trace/run redaction bir contractda.
- Thresholdlar Control Center'da versionlanadi. Sample minimumiga yetmagan holat `PASS` emas, `INSUFFICIENT_DATA`.
- Critical privacy/permission eval xatosi release'ni bloklaydi. Budget 80% alert; 100% configured degradation/kill switch.

## 7. QA matritsasi

**Oqim × actor × adapter × device × data state.** Minimum:

- Actors: anonymous, student, scoped teacher, inactive staff, owner.
- Adapters: web, Telegram bot, Mini App, Messenger/WebSocket, worker.
- Devices: desktop Chrome, Android Chrome 360/390px, iOS Safari, exam landscape 568×320/640×360.
- States: empty, normal, full/large, expired/frozen, duplicate/replay, provider/worker degraded.

Oltin oqimlar: auth/account claim; checkout/receipt/enrollment; lesson lifecycle; quiz/assignment/review; exam media/submit/result; Messenger reconnect/access expiry; AI text/image/PDF/limit/fallback; private media; owner Control Center mutation/rollback.

Bug bar: P0 data loss/auth/payment/access/privacy darhol; P1 core flow yoki owner control launchdan oldin; P2 faqat flag bilan yopilishi mumkin.

## 8. Beta va monetizatsiya protokoli

Rollout: staff → 10–15 learner → bitta cohort → keng launch. Har bosqich alohida flag va stop condition bilan.

- Telegram guruhi jonli dars/material fallback'i sifatida qoladi.
- Har kun: Control Center stoplight, queue/worker, Sentry, feedback, teacher review time va AI cost.
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

## 9. 20-sentyabr taqdimoti va launch

8–10 daqiqalik demo ikki haqiqatni ko'rsatadi:

1. **Learner Outcome Loop:** dars → xato evidence → structured practice/revision → oldingi/yangi proof → zarur bo'lsa teacher handoff.
2. **Solo-owner Control:** Azurbek health, queues, release, payment/access, AI quality/cost va kill switchni bitta markazdan ko'radi.

Demo account fresh state'dan qayta yaratiladi; fallback video, hotspot va Telegram fallback tayyor. 18 va 19-sentyabr repetitsiya. 20-sentyabrda `README.md` go/no-go bajarilmasa faqat proven core ochiladi.

### Launch checklist

**Technical:** CI required checks · broker fail-fast · outbox GREEN + DM smoke · private media tests · release SHA/record · health/readiness · Sentry · backup restore · rollback drill · owner kill-switch drill · no secret in image/log.

**Product:** oltin yo'l 3 qurilmada · scoped teacher flow · payment/access parity · mock/exam media · Progress Proof claim evidence · AI quality/cost gate yoki beta flag · manual DB rescue `0`.

**Marketing:** landing claim audit · testimonial consent · demo/fallback · pricing typed entitlement bilan mos · “unlimited/speaking/mastery” isbotsiz claim yo'q.

### Launch kuni

T-2 soat: release/restore point, Control Center GREEN, demo account va fallback → taqdimot → traffic flag bosqichma-bosqich → har 2 soat stoplight/queue/error/conversion → blocker hotfix o'z branchida test+review+deploy → kun yakuni release record va marinebook.
