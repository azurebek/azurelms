# 02 — Yo'l xaritasi: 14-avgust → 20-sentyabr (37 kun)

*Rebaseline: 2026-08-14. AzureLMS hozir local/pre-production rejimida. 20-sentyabr maqsadi — evidence-backed taqdimot va production readiness qarori; public cloud deploy avtomatik scope emas. Fazalar sana bilan emas, exit kriteriy bilan yopiladi.*

## Qat'iy qarorlar

1. **Local-first:** `APP_ENV=local`, SQLite, LocMem/in-memory, eager Celery, local media va Telegram polling — joriy ish profili.
2. **DigitalOcean `HOLD`:** kreditlar bekor qilingan. DO inference, App Platform, Managed DB/Valkey va Spaces production uchun yangi owner admission bo'lmaguncha chaqirilmaydi.
3. **Gemini free-tier — hard constraint:** oddiy chat ham Gemini ishlatadi; u “faqat web search” emas. Global supply budget/circuit breaker implement/test qilingan; SQLite va CI PostgreSQL contention prooflari yopilgan. Ommaviy rollout uchun production admission va ochiq K11 caller-specific lease/claim riski alohida gate.
4. **Bitta active product slice:** agentlar test/UI/docs qismlarida parallel ishlashi mumkin, ammo bir paytda bitta canonical outcome o'zgaradi.
5. **Adapter state yaratmaydi:** Web, Telegram, Mini App, Messenger, Celery va AI canonical Django service/policy'ni chaqiradi.
6. **Evidence-first:** `EVIDENCE READY` bo'lmagan capability marketing claim, premium entitlement yoki production `GO` bo'lmaydi.
7. **Cloudsiz poydevor mumkin:** CI, `.dockerignore`, health/readiness, private-media policy, idempotency, budget ledger va browser QA vendor tanlamasdan quriladi.

## 2026-08-14 baseline

| Soha | Tasdiqlangan holat | Ochiq gate |
|---|---|---|
| Repo/runtime | 2026-08-14 baseline: post-A8 offline full suite 527/527, streak focused 15/15 va audit 10/10 GREEN; latest recorded suite PR #59 da 1013/1013 | Local GREEN production readiness emas; production gate alohida |
| DigitalOcean | Credential/service o'chiq; `AI_ALLOW_DIGITALOCEAN=False` provider yaratishdan oldin fail-closed | Future production uchun alohida owner admissioni va provider qayta bahosi |
| Gemini | `AI_CHAT_PROVIDER=gemini`; allowlistdagi 1 primary + max 1 fallback; SDK retry off; prompt/output/timeout/deadline cap | External-quota monitoring, K11 caller lease/claim va production admission |
| AI usage | Per-user allowance'dan alohida global daily request/token + minute request reservation ledgeri; staff, chat/search, SmartForm, guest va embedding/reindex qamralgan; SQLite va CI PostgreSQL prooflari yopilgan | Alohida OS-process takrori; guest/SmartForm/lesson-reindex caller-specific lease/counter risklari (K11) |
| A0 | A0a + A0b kod/testda: Telegram auth/webhook/staff, private media/upload, teacher default-deny, socket recheck va CSP v4 | `EVIDENCE READY` yakuniy labeli owner qarorida |
| A1 | Procfile, CI, `.dockerignore`, `/healthz`+`/readyz`, backup/restore va outbox lease mavjud (A1a bajarildi) | cloud deploy `HOLD`; production restore proofi A1b bilan |
| A2 | Control Center mutationlari, flags, append-only audit, heartbeat, release, backup/email/memory probe'lari va AI cost ledgeri bor | A9 AI quality/cost release gate |
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

**Status:** backlog `A8` — **`IMPLEMENTED/TESTED — LOCAL REGRESSION GREEN`**. SQLite va CI PostgreSQL prooflari yopilgan; R0 dan ochiq qolgan K11 caller-specific lease/claim va alohida OS-process takrori production admissionidan oldin closeout qilinadi. Keyingi AI behavior baribir alohida owner admissionini talab qiladi.

### Implement qilingan scope

- Barcha provider call turlarini bitta ledgerga kiritish: chat, web grounding, SmartForm extractor, Telegram guest demo, RAG va memory embedding, failed attempt.
- Global kunlik va bir daqiqalik request hamda kunlik token hard cap; requestdan oldin transactional reservation, keyin actual usage reconciliation. Ledger DB xatosida fail-closed.
- Staff/superuser ham global supply budgetga kiradi; per-user allowance alohida product policy bo'lib qoladi.
- Free-mode model allowlist: stable/free-tier/cost-efficient primary `gemini-3.1-flash-lite` va vaqtinchalik fallback `gemini-3.5-flash-lite`; Pro/preview va boshqa model fan-out yopiq. `gemini-2.5-flash-lite` yangi chaqiruvlarda `404` bergani uchun retired va runtime'da rad etiladi.
- Text request: output `640` token, prompt `12,000` belgi, timeout `15s`, deadline `35s`, maksimum `1 primary + 1 fallback`. Embedding: `64` input, input `8,000` belgi, batch `64,000` belgi, timeout `8s`, SDK retry off.
- `429/quota/billing`da circuit breaker; cooldown davomida yangi provider request yo'q, deterministic yumshoq degradatsiya.
- Local/pre-production profil `digitalocean` providerini env xatosi bilan tanlasa provider factory tarmoqdan oldin fail-closed, Control Center/audit RED; `manage.py check`ning o'zi startup gate emas. DO faqat owner HOLDni ochadigan explicit admission flag/policy bilan qaytadi.
- Free-mode'da Google API grounding to'liq hard-off: explicit, medium/time-sensitive va legacy heavy intentlar specialist/tool request yaratmaydi; bitta plain 3.1 Lite chat va halol no-live-data degradatsiyasi ishlaydi. Paid/admitted rejim alohida ikki flag bilan ochiladi.
- `client_message_id`/job idempotency: duplicate task bitta provider call.
- Control Center: mode, configured budget, used/reserved/remaining, actual attempt va cooldown stoplight; supply policy/event/state adminlari.

### Exit holati

- Targeted mock/offline testlarda duplicate idempotency, reservation/reconciliation, missing usage konservativ charge, call-path accounting, `429 = 1 attempt`, non-quota fallback `≤2` va cooldown paytida yangi network call `0` tekshirilgan.
- Free-mode'da Pro/preview model tanlovi clamp qilinadi, API grounding barcha effortlarda hard-off; guest demo ham default-off.
- Budget/ledger xatosida core LMS, cache/lexical retrieval va human/Telegram deterministic oqimlari ishlashda qoladi; reindex yoki auxiliary AI yumshoq degradatsiya qiladi.
- **Historical local evidence (2026-08-14):** provider kalitlari/env-file loading o'chirilgan post-A8 full suite 527/527, focused streak 15/15, `manage.py check` 0 issue, migration drift yo'q va `system_audit` 10/10 GREEN. Latest recorded full suite PR #59 da 1013/1013; test soni uchun latest marinebook entry source of truth.
- **SQLite contention proof (2026-08-15):** yozildi va real kamchilikni ochdi. `select_for_update()` SQLite'da no-op bo'lgani va Django `BEGIN DEFERRED` ishlatgani sabab 8 parallel rezervatsiyadan 7 tasi `database is locked` bilan yiqilardi (budjet overshooti emas, ammo har qanday parallellikda AI callning ishdan chiqishi). Yechim: local SQLite uchun `transaction_mode=IMMEDIATE` + `timeout` + WAL. Testlar `AZURELMS_TEST_FILE_DB=1` bilan fayl bazasida ishlaydi.
- **Qolgan closeout (2026-08-15 da yopildi):** PostgreSQL contention/transaction testi. Yozilganda bu mashinada PG server yoki docker yo'q edi; A1a bilan kelgan GitHub Actions `integration` ishi endi to'liq suite'ni `pgvector/pgvector:pg16` konteynerida yugurtiradi, ya'ni PG yarmi CI'da bajariladi va birinchi yugurishdayoq real production xatosini topdi (nullable FK ustidagi `select_for_update()`). **Hamon ochiq:** alohida OS processlari bilan takrorlash.
- **Qolgan operatsion risk:** SmartForm va guest counterlari hamda lesson reindex batch'lari uchun to'liq claim/lease yo'q; parallel workerda duplicate work oynasi qolishi mumkin.
- Bir daqiqalik request cap — loyihaning ichki RPM-uslubidagi budgeti; u Google'ning aniq tashqi RPM/RPD kvotasini o'lchamaydi yoki kafolatlamaydi.
- Joriy Gemini adapteri vision payload qabul qilmaydi; `image_qa` routing borligi rasm tahlili capability'si degani emas.

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

## R5 — AI Optimise (taqdimotdan keyin, loyiha yakuni)

**Backlog:** `A10`. Owner admission: 2026-08-19.

Bu faza taqdimot scope'ida emas va R4 qaroridan keyin boshlanadi — ammo loyiha **u bajarilmaguncha yakunlangan hisoblanmaydi**.

- Persona `ai/prompts/builder.py` da allaqachon yozilgan (ism, rol, uslub, chegaralar), ammo u shartnoma emas: undan keyin `skill.instructions` qo'shiladi va skill almashganda ovoz saqlanishini kafolatlaydigan narsa yo'q. Kerak: personani canonical manba sifatida ajratish va skill almashuvida ovoz o'zgarmasligini test bilan majburlash.
- Foydalanuvchi darajasidagi davomiylik yozuvi: yangi chat "biz nima ustida ishlayotgan edik" ni tiklaydi. Hozir `AIConversationSummary` xonaga bog'langan, shuning uchun faktlar ko'chadi, kontekst ko'chmaydi.
- Munosabat holati: birga ishlangan davr, tugallanmagan ish, keyingi qadam.
- Silliqlik A9 gate'iga tayanadi: p95 latency, provayder xato darajasi va fallback xulqi. A10 bu qatlamni qayta yozmaydi.

**Exit:** skill almashganda persona o'zgarmasligi testli; yangi chatda davomiylik tiklanadi; xotira **aniqligi** o'lchangan (noto'g'ri eslash yangidan boshlashdan yomonroq); o'quvchi eslab qolinganini ko'radi va o'chira oladi.

**Chegara:** shaxsiyat mavjud bo'lmagan qobiliyatni va'da qilmaydi; "do'st" ohangi AI ni access, baho yoki progress uchun system-of-record qilmaydi.

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
| K1 | Free-tier bitta 429da model fan-out bilan tugaydi | Implement qilingan: 429 fail-fast, one-fallback bound, global circuit/budget; local full regression 527/527 |
| K2 | “Bepul” staff yoki auxiliary calllar hisobga kirmaydi | Staff ham supply budgetda; SmartForm/guest/RAG/memory/reindex ledgerga ulangan |
| K3 | DigitalOcean eski docs/env orqali tasodifan qayta yoqiladi | Owner `HOLD`; `AI_ALLOW_DIGITALOCEAN=False` factory fail-closed; Control Center RED |
| K4 | Security/private data incident | A0b stop-ship; permission tests; public claim yo'q |
| K5 | Adapter policy drift | Canonical service + parity contract + system audit |
| K6 | Worker/outbox jim ishlamaydi | Claim/lease, heartbeat, queue age va local e2e smoke |
| K7 | Mobil core flow bloklanadi | R2 real-device evidence; keyboard/upload/access states |
| K8 | AI yaxshi ko'rinadi, lekin o'qitmaydi | Structured outcome + teacher-authored eval + beta label |
| K9 | SIT owner vaqtini core'dan tortadi | S2 faqat active core slice'ni siqmasa |
| K10 | Reja statusi koddan oldinga o'tadi | Commit/test/browser evidence bo'lmasa `EVIDENCE READY` yo'q |
| K11 | SQLite/PostgreSQL parallel reservation yoki caller counteri to'qnashadi | SQLite contention testi + `transaction_mode=IMMEDIATE`/WAL va CI PostgreSQL `FOR UPDATE` proofi yopilgan. **2026-09-03 auditi:** lesson-reindex va SmartForm uchun "duplicate work" xavfi aslida yo'q ekan — `embed_texts`/`execute_provider_call` supply kalitini kirish hash'idan quradi va `reserve_supply` takroriy kalitni tarmoqdan **oldin** rad etadi. Haqiqiy nuqson teskari edi: bu himoya `failed_lessons` va `xato` logi bo'lib ko'rinardi; PR #63 da u alohida `skipped_duplicate` holatiga ajratildi. Guest demo limiti PR #64 da yopildi: slot provider chaqiruvidan **oldin** shartli `UPDATE` bilan band qilinadi va yiqilgan chaqiruvda qaytariladi. **Ochiq qolgani:** alohida OS processlari bilan takrorlash (joriy prooflar bitta process ichidagi oqimlar bilan) |
| K12 | Temporary Gemini fallback eskiradi yoki quota profili o'zgaradi | 2.5 Lite hodisasi yopildi: model retired. Joriy temporary `gemini-3.5-flash-lite` va external quota profile owner monitoring/re-admissioniga bo'ysunadi |

## Asosiy metrikalar

| Guruh | Metrika | Gate |
|---|---|---:|
| AI supply | provider attempts per logical request | `≤2` |
| AI supply | global budget overrun / caller coverage regression | `0 / 0` (coverage testda; snapshot avtomatik untracked detector emas) |
| AI safety | 429 circuit ochiq paytdagi yangi remote call | `0` |
| Reliability | core structured flow success | `≥98%` |
| Access/safety | critical violation | `0` |
| Mobile | blocking parity/overflow issue | `0` |
| AI quality | Turkish correctness / grounded support | `≥92% / ≥95%` |
| Owner control | manual DB rescue / unknown RED state | `0 / 0` |

Aniq Gemini tashqi quota raqamlari hujjatga qotirilmaydi: ular providerda o'zgaradi. Control Center'dagi minute request cap loyiha ichki RPM-uslubidagi guard, Google tashqi quota telemetriyasi emas. Runtime budget konfiguratsiya qilinadi va release evidence bilan versionlanadi.

---

*Keyingi source of truth: [03-mahsulot-backlog.md](03-mahsulot-backlog.md).*
