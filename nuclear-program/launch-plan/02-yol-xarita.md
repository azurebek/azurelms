# 02 — Yo'l xaritasi: 22-iyul → 20-sentyabr (60 kun)

*Rebaseline: 2026-07-22. Model: AzureLMS — Azurbek boshqaradigan bitta kurs operatsion tizimi. Fazalar sana bilan emas, exit kriteriy bilan yopiladi. Oldingi faza gate'dan o'tmasa keyingi faza scope'i qisqaradi; yangi subsystem ochilmaydi.*

## Qat'iy ishlash tartibi

1. **Bitta active product slice:** bir paytda faqat bitta canonical flow state'i o'zgaradi; agentlar uning test, UI va ops qismlarida parallel ishlashi mumkin.
2. **Poydevor featuredan oldin:** security, deploy, CI va control keyinga surilmaydi; mobile parity P0'dan boshlab har slice'ning cross-cutting gate'i.
3. **Adapterlar state yaratmaydi:** Web, bot, Mini App va AI canonical service/policy'ni chaqiradi.
4. **Evidence-first:** `EVIDENCE READY` bo'lmagan feature marketing claim yoki premium entitlement bo'lmaydi.
5. **Scope freeze:** `03-mahsulot-backlog.md`dagi `NEXT/CUT` bandlari launch-critical ishni siqib chiqarmaydi.
6. **Haftalik owner review:** juma kuni Control Center stoplight, tests, flow video, cost/quality va backlog admission qayta ko'riladi.

## Umumiy manzara

```text
22–28 IYUL     29 IYUL–9 AVG     10–23 AVG       24 AVG–6 SEN      7–16 SEN       17–20 SEN
P0             P1                P2              P3                P4              P5
STOP-SHIP  →   CONTROL/POLICY →  GOLDEN FLOW  →  OUTCOME LOOP  →   BETA/GATES  →   LAUNCH
security       canonical state   mobile parity   structured AI     hardening        only proven
runtime        CI/observability   owner console   proof/escalate    price pilot      capabilities
```

Kontent va marketing parallel yuradi, lekin kod fazasining gate'ini chetlab o'tmaydi. 1-sentyabr beta faqat P0–P2 exit'lari yashil bo'lsa real to'lovli **core kurs** cohortiga ochiladi; AI Outcome capability P3 premium gate'igacha free beta/add-on yoki feature-flag off bo'ladi. P0–P2 yopilmasa Telegram fallback bilan cheklangan pilot qoladi.

---

## P0 — Stop-ship poydevor (22–28 iyul)

**Maqsad:** production va user data'ni featurelardan oldin himoyalash.

- Telegram login tokenini bir martalik va expiry'li qilish; webhook default secret/secret loggingni yo'qotish; inactive staffni bot admin deb qabul qilmaslik.
- Payment receipt, assignment, messenger attachment va exam audio uchun private media yo'li; upload MIME/magic-byte/size validatsiyasi.
- Production-like muhitda broker/cache/channel `memory://` yoki in-memory'ga jim fallback qilmasin.
- `telegram_outbox --loop`ni alohida 1-replica process qilish va end-to-end DM smoke.
- `.dockerignore`; local secret/DB/media/venv image'ga kirmasligi.
- Minimal CI: check, deploy check, migration drift, full tests, collectstatic, secret/dependency scan.
- `/healthz`/readiness: DB, cache/channels, broker va critical workerlar.
- Telegram auth/payment/access permission regressionlari.
- Har P0 fixining tegishli mobile auth/upload/access smoke'i.

**Ketma-ket cutline:** avval A0 security, keyin A1 runtime. Bir haftaga sig'masa private-media yoki CI scope'i kesilmaydi; keyingi feature fazasi suriladi.

**Exit — hammasi kerak:** critical auth/webhook/private-media finding yopilgan; CI required checks yashil; broker fail-fast; outbox DM smoke; `check --deploy`; isolated targetga initial backup restore proof. Yopilmasa yangi AI skill, SRS, streak yoki placement build boshlanmaydi.

## P1 — Control plane va canonical policy (29-iyul – 9-avgust)

**Maqsad:** Azurbek bir joydan haqiqat, health, release va kill switchlarni ko'rsin.

- Mavjud `aicontrol`ni yangi subsystem qilmay, owner-only **Azure Control Center v0**ga kengaytirish: status, queues, flags, audit va effective config; chuqur analytics keyin.
- Capability registry: DB, cache/channels, broker, workers, Telegram webhook/outbox, media, AI provider, RAG, memory va backup.
- Effective config: global → plan → cohort → user; runtime qaysi model/policy ishlatayotganini ko'rsatish.
- Feature flags/kill switches; release record; append-only system audit; correlation/idempotency key contract.
- Permission matrix: superuser control mutationlari; teacher faqat explicit course/cohort scope; student faqat o'z state/media'si.
- Alohida domain contractlar: `LessonRun` (schedule/live/check-in), `LessonAccess` (locked/released), `AssignmentLifecycle` (open/submitted/reviewed); bitta Lesson Orchestrator ularni owner flow'ida aggregate qiladi.
- Alohida `Application`, `Payment` va `Enrollment/Entitlement` state graphlari; Control Center bitta aggregate ko'rsatadi, mega-state yaratilmaydi.
- P1'da contract/service/test foundation; teacher/student UI va adapter migration P2'da tugaydi.
- AI uchun system-role, untrusted context separation, 20s global deadline, maksimal bitta fallback va quota/cost reservation dizayni.
- A9 eval foundation: rubric/schema, 50 ta critical golden case va CI smoke; premium gate keyin.

**Exit:** `/backoffice/control/` v0 ownerga effective config, queues, flags, audit va release stoplightni ko'rsatadi; uchta learning va uchta acquisition state contracti permission/idempotency testli; staff scope default-deny; AI eval schema va 50 critical case CI'da. UI migration P2'ga aniq qoladi.

## P2 — Oltin oqim va mobil parity (10–23 avgust)

**Maqsad:** learner va owner asosiy siklini real telefonlarda barqaror qilish.

- O'quvchi: registration/login/Telegram claim → checkout/receipt → active enrollment → released lesson → quiz/assignment → feedback → mock/result; P1 canonical servicelariga adapter migration.
- Ustoz: bugungi dars → attendance → release → grading queue → feedback; P1 Lesson Orchestrator ustidagi bitta control point.
- AI navigator platformadagi ayni release/access policy'ni chaqiradi; locked lesson tavsiya qilmaydi.
- Messenger 320–414px layout, WebSocket reconnect va access recheck; lesson header 360px; exam 568×320/640×360 landscape.
- Android Chrome, iOS Safari va desktop Chrome'da keyboard, upload/mic, empty/error, dark/light va accessibility smoke.
- Checkout course/cohort/plan bog'lanishi va inactive default cohort reactivation xatosi yopiladi.
- Placement/waitlist faqat core acquisition flow'ga zarar bermasa deterministic minimal ko'rinishda.

**Exit:** fresh account bilan oltin yo'l 3 qurilmada video-evidence; critical parity incident `0`; owner routine flow'ni developer/DB yordamisiz tugatadi; core flow success `≥98%`.

## P3 — Learner Outcome Loop minimal slice (24-avgust – 6-sentyabr)

**Maqsad:** AI'ni generic chatdan o'lchanadigan o'quv jarayoniga aylantirish.

- Launch data contracti faqat uchta model: `PracticeSession`, `LearnerAttempt`, `MasteryEvidence`. Objective va review policy versionlangan fields/config orqali; yangi taxonomy/scheduler modeli faqat dalil bo'lsa.
- Daily Coach: joriy dars, quiz/assignment xatosi va due review'dan deterministic 10–15 daqiqalik plan.
- Bitta stateful practice mode: bir item → learner javobi → hint/retry → feedback → transfer check; answer key oldindan yo'q.
- Minimal Progress Proof: oldingi/yangi natija va next action. Writing Revision va Teacher Inbox faqat P4/NEXT pilot.
- Eval: P1'dagi 50 case'ni 75 critical case'gacha kengaytirish; prompt injection, access, Turkish correctness, CEFR va grounding. Premium narx gate'i uchun P4'da ≥150.

**Exit:** bitta structured activity success `≥98%`; first activity completion `≥60%`; critical access/safety `0`; Turkish correctness `≥92%`; grounded support `≥95%`; p95 text `<8s`; 75-case eval va feature flag Control Center'da. Gate o'tmasa generic AI beta qoladi, premium claim yopiq.

## P4 — Beta, hardening va narx piloti (7–16 sentyabr)

**Maqsad:** real cohortda reliability, learning value, owner workload va economicsni isbotlash.

- Kichik cohort rollout: avval staff, keyin 10–15 learner, so'ng kuzgi guruh; har bosqich flag bilan.
- Backup restore mashqi, rollback drill, owner kill-switch drill, load/queue/outbox/private-media smoke.
- Daily triage: Control Center stoplight + Sentry/log + user feedback + teacher review queue.
- AI price ledger va per-user/day/global spend circuit breaker; budget 80% alert, 100% configured degradation/kill switch.
- Learning/teacher baseline va post: correction rate va pre/post accuracy. Writing/teacher-review metrikasi faqat conditional pilot ochilsa.
- Honest pricing smoke: outcome capability va human SLA; token/unlimited claim yo'q.
- Writing Revision/Teacher Inbox faqat A7 + A9 gate o'tsa va owner capacity bo'lsa kichik flagli pilot; launch sharti emas.
- 13-sentyabr: kontent va scope freeze; faqat Sev-0/Sev-1 blocker fix.

**Exit:** fresh production-like restore revalidation, rollback/kill switch va 7+ kun critical incidentsiz; `05-launch-ops.md` metric contract bo'yicha `N≥50` completed activities va `N≥20` learner bo'lmasa AI `INSUFFICIENT_DATA → beta`; premium pricing uchun ≥150 eval case va paid-user/cost denominator yetarli bo'lishi shart.

## P5 — Taqdimot va boshqariladigan launch (17–20 sentyabr)

- 17-sen: demo account, release record va claim-evidence freeze.
- 18-sen: repetitsiya №1 va fallback video.
- 19-sen: faqat blocker fix, repetitsiya №2, Control Center RED/AMBER drill.
- 20-sen: `README.md` go/no-go bo'yicha qaror. Faqat `EVIDENCE READY` capability'lar ochiladi.
- Demo: “bir learnerning haftasi” va “owner bir markazdan nazorat qiladi”; AI chat soni emas, outcome proof va teacher handoff ko'rsatiladi.

---

## Parallel yo'laklar

| Yo'lak | P0–P1 | P2 | P3 | P4–P5 |
|---|---|---|---|---|
| **Kontent** | curriculum/objective taxonomy, mock format | minimal lesson/mock bank | practice + writing rubric cases | freeze va faqat xato tuzatish |
| **Marketing** | claim audit, testimonial ruxsatlari | waitlist va beta taklif | beta copy, “AI beta” halolligi | faqat evidence-ready claimlar |
| **Ops** | CI, private media, workers, Control Center | device/flow matrix | AI eval/cost telemetry | restore/rollback/launch monitoring |
| **Owner** | scope/admission, permission matrix | oltin flow sign-off | rubric/eval sign-off | pricing va go/no-go |
| **SIT** | S1 portal (bajarildi), real katalog ma'lumoti | S2 yordam so'rovi lifecycle | S4 owner workflow | S3 AI advisor; to'lov gate'i (flag) |

> SIT (`03-mahsulot-backlog.md` → `S`) owner qarori bilan A-narvoniga parallel yuriladi. U core launch gate'lariga kirmaydi: SIT holati P0–P5 chiqishini bloklamaydi va bloklanmaydi.

## Risk reestri

| # | Risk | Javob |
|---|---|---|
| R1 | Solo-owner capacity featurelar orasida yoyiladi | Bir active product slice; admission gate; NEXT/CUT qat'iy |
| R2 | Security yoki private data incident | P0 stop-ship; private media; permission tests; no marketing before closure |
| R3 | Adapter policy drift | Canonical service + parity contract + system audit |
| R4 | Worker/outbox jim ishlamaydi | Broker fail-fast, heartbeat, queue age, 1 outbox replica, e2e smoke |
| R5 | AI javobi yaxshi ko'rinadi, lekin o'qitmaydi | Structured outcome, teacher-authored eval va learning KPI |
| R6 | AI cost/latency marjani buzadi | 20s deadline, one fallback, ledger/reservation, circuit breaker |
| R7 | Mobil asosiy flow buziladi | P2 oldingi gate; real Android/iOS/landscape evidence |
| R8 | Beta real learnerga zarar beradi | Progressive flag rollout, Telegram fallback, rollback/kill switch |
| R9 | Video/mock kontent kechikadi | Minimal cohort slice; live lesson birlamchi; kontent scope qisqaradi |
| R10 | Claim capabilitydan oldinga o'tadi | Claim-evidence register; NO-GO yoki beta label |
| R11 | SIT owner vaqtini core launchdan tortadi | Kichik ketma-ket slice; SIT core gate'ga kirmaydi; sekinlashsa S2/S3 kechiktiriladi, A narvoni to'xtamaydi |
| R12 | SIT'dagi eskirgan qabul/narx ma'lumoti ishonchni buzadi | `source_url` + `last_verified_on` nashr sharti; S4'da eskirish signali; shubhali yozuv `is_published=False` |

## Asosiy metrikalar

| Guruh | Metrika | Gate |
|---|---|---:|
| Reliability | core structured flow success | `≥98%` |
| Access/safety | critical violation | `0` |
| Mobile | critical parity/overflow/blocking issue | `0` |
| AI quality | Turkish correctness / grounded support | `≥92% / ≥95%` |
| AI latency | text p50 / p95; queue p95 | `≤3s / <8s; ≤1s` |
| Learning | practice pre/post yoki writing rubric delta | `+15 pp` yoki `+0.5/5` |
| Adoption | first activity completion | `≥60%` |
| Teacher | review time reduction | `≥30%` premium target |
| Economics | incremental AI cost / premium revenue | `≤25%` |
| Owner control | manual DB rescue / unknown RED state | `0 / 0` |

---

*Keyingi source of truth: [03-mahsulot-backlog.md](03-mahsulot-backlog.md).*
