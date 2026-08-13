# 02 — Yo'l xaritasi: 14-avgust → 20-sentyabr (37 kun)

*Rebaseline: 2026-08-14. AzureLMS hozir local/pre-production rejimida. 20-sentyabr maqsadi — evidence-backed taqdimot va production readiness qarori; public cloud deploy avtomatik scope emas. Fazalar sana bilan emas, exit kriteriy bilan yopiladi.*

## Qat'iy qarorlar

1. **Local-first:** `APP_ENV=local`, SQLite, LocMem/in-memory, eager Celery, local media va Telegram polling — joriy ish profili.
2. **DigitalOcean `HOLD`:** kreditlar bekor qilingan. DO inference, App Platform, Managed DB/Valkey va Spaces production uchun yangi owner admission bo'lmaguncha chaqirilmaydi.
3. **Gemini free-tier — hard constraint:** oddiy chat ham Gemini ishlatadi; u “faqat web search” emas. Global budget/circuit breaker yo'q ekan, yangi AI feature yoki ommaviy rollout boshlanmaydi.
4. **Bitta active product slice:** agentlar test/UI/docs qismlarida parallel ishlashi mumkin, ammo bir paytda bitta canonical outcome o'zgaradi.
5. **Adapter state yaratmaydi:** Web, Telegram, Mini App, Messenger, Celery va AI canonical Django service/policy'ni chaqiradi.
6. **Evidence-first:** `EVIDENCE READY` bo'lmagan capability marketing claim, premium entitlement yoki production `GO` bo'lmaydi.
7. **Cloudsiz poydevor mumkin:** CI, `.dockerignore`, health/readiness, private-media policy, idempotency, budget ledger va browser QA vendor tanlamasdan quriladi.

## 2026-08-14 baseline

| Soha | Tasdiqlangan holat | Ochiq gate |
|---|---|---|
| Repo/runtime | Joriy checkout local venv bilan ishlaydi; check yashil; full suite 467/467 va streak focused 1/1 (2026-08-14) | Local GREEN production readiness emas; security/CI/AI supply gate'lari ochiq |
| DigitalOcean | Config bo'yicha o'chiq: credential bo'sh, `USE_S3=False`, remote DB/cache yo'q | Local/pre-prod AI provider selection uchun code-level fail-closed HOLD; future production owner admissioni |
| Gemini | `AI_CHAT_PROVIDER=gemini`; chat, grounding va embedding remote call qiladi | Global daily budget, cheap-model allowlist, attempt cap, full accounting |
| AI usage | Per-user 5h/weekly token enforcement va final chat usage telemetry bor | Staff exemption, fail-open limiter, untracked SmartForm/guest/embed calllar |
| A0 | Telegram one-time auth, webhook fail-closed va inactive-staff denial kodda | Private media/upload, teacher default-deny, socket access recheck |
| A1 | Procfile mavjud | CI, `.dockerignore`, readiness, restore proof; cloud deploy `HOLD` |
| A2 | Read-only Control Center, brand va landing mutation surface'lari bor | Flags, release/audit, heartbeat va Gemini budget stoplight |
| Telegram | F0–F9, outbox, Mini App foundation | Public webhook/outbox process va real prod WebView — `HOLD` |
| Landing | Admin-controlled landing + backoffice Bosqich 1/TOC | Repeatable CRUD/reorder va preview polish |
| SIT | S1 portal, S3 advisor va S4 backoffice kodda | S2 `SITInquiry`; real source hygiene |

## Umumiy manzara

```text
14–18 AVG        19–30 AVG          31 AVG–8 SEN       9–15 SEN          16–20 SEN
R0               R1                 R2                 R3                R4
AI BUDGET    →   SAFETY/CONTROL  →  GOLDEN FLOW    →  EVIDENCE/BETA  →  DEMO/DECISION
truth + caps      local CI/media     mobile parity      minimal outcome   no fake prod
```

Oldingi 2026-07-22 rejasidagi `P0–P5` tarixiy rebaseline sifatida Git tarixida qoladi. Joriy bajarish tartibi faqat quyidagi `R0–R4` bo'yicha.

---

## R0 — Gemini free-tier budget mode va haqiqat sinxroni (14–18 avgust)

**Birinchi implementation slice:** backlog `A8`; ushbu docs rebaseline tugagach alohida kod ishi sifatida ochiladi.

### Ish

- Barcha provider call turlarini bitta ledgerga kiritish: chat, web grounding, SmartForm extractor, Telegram guest demo, RAG va memory embedding, failed attempt.
- Global kunlik request/token hard cap; requestdan oldin atomic reservation, keyin actual usage reconciliation.
- Staff/superuser ham global supply budgetga kiradi; per-user allowance alohida product policy bo'lib qoladi.
- Free-mode model allowlist: bitta arzon primary va ko'pi bilan bitta tekshirilgan free fallback; Pro/preview va model fan-out yopiq.
- Har request uchun global deadline, prompt/output cap va maksimum `1 primary + 1 fallback`.
- `429/quota/billing`da circuit breaker; cooldown davomida yangi provider request yo'q, deterministic yumshoq degradatsiya.
- Local/pre-production profil `digitalocean` providerini env xatosi bilan tanlasa startup/audit fail-closed; DO faqat owner HOLDni ochadigan explicit admission flag/policy bilan qaytadi.
- `heavy` web-search free-mode'da yopiq; `light` default, search faqat explicit/time-sensitive evidence kerak bo'lsa.
- `client_message_id`/job idempotency: duplicate task bitta provider call.
- Control Center: mode, configured budget, used/reserved/remaining, attemptlar, untracked-call va cooldown stoplight.

### Exit — hammasi kerak

- Concurrency/reservation, duplicate job, blanket 429, missing usage va har call-path accounting testlari yashil.
- Bitta 429 ko'p modelni aylanmaydi; attempt count acceptance testda `≤2`.
- Free-mode'da Pro/preview va `heavy` UI/runtime orqali tanlanmaydi.
- Budget tugaganda core LMS, deterministic katalog/RAGsiz yordam va Telegram oqimi ishlashda qoladi; AI halol “limit” holatini qaytaradi.
- Hujjat va Control Center “Gemini faqat search” deb noto'g'ri ko'rsatmaydi.

## R1 — Vendor-neutral safety, runtime va control (19–30 avgust)

**Backlog:** `A0b`, `A1`, `A2`; cloud deploy yo'q.

- Payment receipt, assignment, messenger attachment va exam audio private-media policy/permission endpointiga o'tadi.
- MIME/magic-byte/size validatsiyasi; anonymous va cross-user access regressionlari.
- Teacher course/cohort scope default-deny; expired enrollment uchun WebSocket access recheck.
- `.dockerignore`, local CI checks, migration drift, collectstatic, secret/dependency scan.
- `/healthz`/readiness vendor-neutral contracti: local profil uchun DB va configured subsystemlar; remote probe faqat production profile ochilganda.
- Telegram outbox atomic claim/lease dizayni va local end-to-end smoke; Procfile/public process `HOLD` bo'lsa ham worker contract testlanadi.
- Control Center flags/kill switch, append-only audit, active service heartbeat va release evidence foundation.

**Exit:** A0b permission tests yashil; teacher default-deny; CI required checks local runnerda; readiness configured capabilityni rost ko'rsatadi; AI budget kill switch va audit ishlaydi. Hosting account talab qilinmaydi.

## R2 — Canonical oltin oqim va mobil parity (31-avgust – 8-sentyabr)

**Backlog:** `A3`, `A4`, `A5`.

- Learner: registration/Telegram claim → checkout/receipt → active enrollment → released lesson → quiz/assignment → feedback → mock/result.
- Owner/teacher: bugungi dars → attendance → release → grading queue → feedback.
- Web, bot va Mini App bir xil enrollment/access/submission service'larini ishlatadi; duplicate business logic mustahkamlanmaydi.
- Messenger reconnect/access expiry; lesson 360px; exam 568×320/640×360; checkout/teacher/Telegram Mini App mobile smoke.
- Android Chrome, iOS Safari va desktop Chrome: keyboard, upload/mic, empty/error, dark/light va accessibility evidence.

**Exit:** fresh account bilan core flow local/test muhitda 3 device classda reproduksiya qilinadi; critical permission/parity incident `0`; owner routine flow uchun DB qo'lda tahriri `0`. Public production shart emas.

## R3 — Minimal outcome evidence va boshqariladigan beta (9–15 sentyabr)

**Backlog:** `A6`, keyin shartli `A7/A9`. R0–R2 yopilmasa bu scope qisqaradi.

- Uchta minimal evidence contract: `PracticeSession`, `LearnerAttempt`, `MasteryEvidence`; AI memory mastery system-of-record emas.
- Bitta structured practice: item → answer → hint/retry → feedback → transfer check.
- Minimal Progress Proof: oldingi/yangi natija va next action.
- Teacher-authored critical eval; prompt injection, access, Turkish/CEFR, grounding va failure/fallback.
- 10–15 learner beta faqat owner capacity va data mavjud bo'lsa; aks holda staff/demo cohort.
- Kontent inventory: birinchi cohort uchun 2 hafta oldinda darslar va kamida bitta review qilingan mock slice.

**Exit:** structured flow success `≥98%`, critical access/safety `0`; sample yetmasa `INSUFFICIENT_DATA → beta`, premium claim yo'q. Gemini global budget buzilmasa ham token soni learner outcome o'rnini bosmaydi.

## R4 — Taqdimot, freeze va production qarori (16–20 sentyabr)

- 16-sen: claim/evidence register va scope freeze.
- 17-sen: fresh demo account, release manifest, local backup/restore va fallback video.
- 18-sen: repetitsiya №1; internet/Gemini yo'q holatdagi deterministic fallback.
- 19-sen: faqat blocker fix; repetitsiya №2; Control Center RED/AMBER va Gemini budget exhaustion drill.
- 20-sen: “bir learnerning haftasi + owner control” demo. Production bo'lmasa local yoki vaqtinchalik xavfsiz tunnel; bu public launch deb atalmasin.

**Qaror:**

- `DEMO GO` — core flow va dalil reproduksiya qilinadi;
- `BETA GO` — kichik, nazoratli cohort va rollback mavjud;
- `PRODUCTION HOLD` — hosting/provider, remote backup/restore yoki security gate qayta admission olmagan;
- `NO-GO` — payment/access/privacy/canonical state xatosi yoki claim reproduksiya qilinmaydi.

---

## Parallel yo'laklar

| Yo'lak | R0 | R1 | R2 | R3–R4 |
|---|---|---|---|---|
| Kontent | inventory, Gemini bulk-generation yo'q | lesson template + owner review | first-cohort pack | mock/rehearsal freeze |
| Marketing | claim audit; “unlimited AI” yo'q | waitlist/demo copy | beta consent | faqat evidence-ready claim |
| Ops | AI ledger/circuit | CI/media/health/control | device/flow matrix | restore/fallback drill |
| Owner | budget va model allowlist | permission/kill-switch sign-off | golden flow sign-off | demo va production qarori |
| SIT | S1/S3/S4 truth sync | S2 faqat A8ni siqmasa | real data hygiene | demo scope'idan tashqari |

## Risk reestri

| # | Risk | Javob |
|---|---|---|
| K1 | Free-tier bitta 429da model fan-out bilan tugaydi | A8 one-fallback + circuit breaker + hard global budget |
| K2 | “Bepul” staff testlari hisobga kirmaydi | Staff ham supply budgetda; barcha call-path ledger |
| K3 | DigitalOcean eski docs/env orqali tasodifan qayta yoqiladi | Owner `HOLD`, credential bo'sh, policy audit va startup evidence |
| K4 | Security/private data incident | A0b stop-ship; permission tests; public claim yo'q |
| K5 | Adapter policy drift | Canonical service + parity contract + system audit |
| K6 | Worker/outbox jim ishlamaydi | Claim/lease, heartbeat, queue age va local e2e smoke |
| K7 | Mobil core flow bloklanadi | R2 real-device evidence; keyboard/upload/access states |
| K8 | AI yaxshi ko'rinadi, lekin o'qitmaydi | Structured outcome + teacher-authored eval + beta label |
| K9 | SIT owner vaqtini core'dan tortadi | S2 faqat active core slice'ni siqmasa |
| K10 | Reja statusi koddan oldinga o'tadi | Commit/test/browser evidence bo'lmasa `EVIDENCE READY` yo'q |

## Asosiy metrikalar

| Guruh | Metrika | Gate |
|---|---|---:|
| AI supply | provider attempts per logical request | `≤2` |
| AI supply | global budget overrun / untracked call | `0 / 0` |
| AI safety | 429 circuit ochiq paytdagi yangi remote call | `0` |
| Reliability | core structured flow success | `≥98%` |
| Access/safety | critical violation | `0` |
| Mobile | blocking parity/overflow issue | `0` |
| AI quality | Turkish correctness / grounded support | `≥92% / ≥95%` |
| Owner control | manual DB rescue / unknown RED state | `0 / 0` |

Aniq Gemini tashqi quota raqamlari hujjatga qotirilmaydi: ular providerda o'zgaradi. Runtime budget Control Center'da konfiguratsiya qilinadi va release evidence bilan versionlanadi.

---

*Keyingi source of truth: [03-mahsulot-backlog.md](03-mahsulot-backlog.md).*
