# 03 — Mahsulot backlog: ADMIT / NEXT / HOLD / CUT

*Rebaseline: 2026-08-14. Platforma = Azurbek boshqaradigan bitta kurs operatsion tizimi. Local/pre-productionda DigitalOcean `HOLD`; Gemini free-tier global supply budgeti yangi stop-gate. Har band learner outcome yoki owner workload, canonical owner, adapterlar, acceptance evidence, flag/rollback va fazaga ega bo'lmasa ish boshlanmaydi.*

## Ish tartibi

1. Bir vaqtda bitta `ADMIT` band active product slice bo'ladi.
2. Agentlar uning domain, test, mobile va ops qismlarida parallel ishlashi mumkin; yangi authority yoki subsystem yaratmaydi.
3. Oldingi band exit kriteriydan o'tmasa, keyingisi boshlanmaydi yoki scope'dan kesiladi.
4. `NEXT` band faqat Azurbek admission berganda `ADMIT`ga o'tadi.
5. Queue qarori: `ADMIT` / `NEXT` / `HOLD` / `CUT`. Execution holati: `PLANNED` / `IN PROGRESS` / `IMPLEMENTED/TESTED — LOCAL REGRESSION GREEN` / `EVIDENCE READY` / `BLOCKED`.
6. **Istisno — `S. SIT`:** owner qarori bilan A-narvoniga parallel yuritiladi (1-qoidadan ozod). Uning slice'lari o'zaro ketma-ket boradi va A bandlarini to'xtatmaydi; narxi — owner vaqtining bo'linishi (`S-R1`).
7. **Joriy active closeout — `A8`:** Gemini free-tier budget mode **`IMPLEMENTED/TESTED — LOCAL REGRESSION GREEN`**. Real DB contention proof tugamaguncha yangi AI skill, bulk generation, `heavy` search yoki ommaviy AI beta yo'q.

### Joriy status snapshot

| Band | Queue | Execution | Izoh |
|---|---|---|---|
| A0 | `ADMIT` | `IN PROGRESS` | A0a auth/webhook/inactive-staff bajarilgan; A0b va teacher/socket scope qolgan |
| A1a | `ADMIT` | `PLANNED` | vendor-neutral local CI/readiness |
| A1b | `HOLD` | `PLANNED` | cloud deploy va managed services |
| A2 | `ADMIT` | `IN PROGRESS` | read-only Control Center + brand/landing mutation foundation |
| A8 | `ADMIT` | `IMPLEMENTED/TESTED — LOCAL REGRESSION GREEN` | supply guard kod/target/full testlarda; real concurrency proof pending |
| S1/S3/S4 | `— delivered` | `EVIDENCE READY` | portal, grounded advisor va owner backoffice kodda |
| S2 | `NEXT` | `PLANNED` | canonical inquiry lifecycle yo'q |

---

## A. ADMIT — launch-critical

### A0. Stop-ship security pack — `IN PROGRESS`, `XL → A0a DONE + A0b L`

- **Outcome:** account, payment va private learner data xavfsiz; owner favqulodda manual rescue qilmaydi.
- **Canonical owner:** auth/access/media policies.
- **Scope A0a (M):** one-time/expiring Telegram auth token; webhook secret fail-closed va no-secret logging; inactive staff denial. **A0b (L):** teacher default-deny scope, upload inventory, private media, MIME/magic-byte/size validation, WebSocket access recheck va django-csp v4 header/Mini App exception testi.
- **Adapters:** web auth, Telegram webhook, media download, Messenger WebSocket.
- **Acceptance:** replay, forged webhook, cross-user media va expired enrollment socket regressionlari; anonymous private media `403/404`; kill/rollback runbook.
- **Evidence (A0a, 2026-07-23):** `e7cd4a6` va `5bea4a5` — one-time/browser-bound Telegram auth, webhook fail-closed/no-secret logging, inactive staff denial; implementatsiya paytida full suite 385/385 va check yashil.
- **Evidence (A0b/2, 2026-08-15):** upload MIME/magic-byte/size gate'i. `core/upload_validation.py` faylni nomiga yoki klient yuboradigan `content_type` ga emas, boshidagi baytlariga qarab tekshiradi; uchta profil (`image` 5MB, `document` 12MB, `audio` 25MB) va kengaytma izchilligi. Beshta learner upload yo'li ulandi: chat biriktirmasi (ilgari tur tekshiruvi umuman yo'q edi), to'lov cheki, vazifa fayli (canonical servisda — web va bot ulashadi), imtihon speaking audiosi (ilgari soxtalashtiriladigan `content_type`) va avatar. Model field validatorlari `.create()`/`.save()` yo'lida ishlamagani uchun gate view/servis darajasida turadi. 19 yangi test; CKEditor upload'i staff-gated deb tekshirildi.
- **Qolgan:** private media (permission-checked stream view — owner qarori 2026-08-15), WebSocket access recheck va django-csp v4 header testi. A0 to'liq `EVIDENCE READY` emas.
- **Faza:** R1. A8 bilan parallel faqat test/docs ishlari; yangi product featurelardan oldin.

### A1. Reproducible runtime va CI — `PLANNED`, `A1a M + A1b HOLD`

- **Outcome:** web, AI task va Telegram notification jim yo'qolmaydi; release qayta tiklanadi.
- **Canonical owner:** deployment config + release gate; vendor alohida adapter qarori.
- **A1a — hozir:** `.dockerignore`; local CI required checks; health/readiness contract; static build; secret/dependency scan; Telegram outbox claim/lease va local e2e; reproducible local backup/restore.
- **A1b — `HOLD`:** public hosting, managed PostgreSQL/Valkey/object storage, webhook process va production restore. DigitalOcean majburiy target emas; owner productionni qayta ochganda vendor tanlanadi.
- **Acceptance:** local profile remote xizmatga jim o'tmaydi; test Notification → outbox `sent`; checks/migration/static; isolated local restore. Production acceptance A1b admissionidan keyin alohida.
- **Faza:** R1.

### A2. Azure Control Center v0 — `IN PROGRESS`, `L`

- **Outcome:** Azurbek bitta joydan policy, health, queues, quality, cost va release holatini boshqaradi.
- **Canonical owner:** mavjud backoffice + `aicontrol` kengaytmasi; yangi parallel admin subsystem yo'q.
- **Scope:** `/backoffice/control/`; owner-only; capability registry; effective config; feature flags/kill switches; queue/worker health; audit va release stoplight. Chuqur analytics v0 scope'ida emas.
- **Acceptance:** GREEN/AMBER/RED sababli; har mutation reason+confirmation+idempotency+audit; arbitrary shell yo'q; `/backoffice/ai-control/` AI tab/compatibility yo'liga tutashadi.
- **2026-07-22 foundation evidence:** active superuser-only read-only route, 10-capability registry, safe partial-failure snapshot, effective config va shu servisdagi `system_audit` CLI tayyor; 1280x900/390x844 browser QA hamda permission/CLI testlari o'tdi. Hali kerak: mutation audit/confirmation/idempotency, flags/kill switches, active worker heartbeat, `ReleaseRecord`, cost/quality va qolgan capability probe'lari. Shu sabab band `EVIDENCE READY` emas.
- **2026-07-22 birinchi mutation surface — markaziy brend:** `/backoffice/control/brand/` A2 scope'i ichida, mavjud backoffice ustida qurildi; yangi parallel admin subsystem yaratilmadi. A2ning mutation acceptance shartlarini qondiradi: majburiy `change_reason`, majburiy confirmation checkbox, `LogEntry` audit yozuvi va o'zgarish bo'lmasa yozmaydigan no-op yo'l. Canonical owner: `frontend.SiteSettings`; adapterlar (public, app, teacher, backoffice, messenger, Mini App, auth, exam, sertifikat, error shell'lari) faqat `templates/components/brand_logo.html` orqali iste'mol qiladi. Evidence: `python manage.py test` 336/336, 1280x900 va 390x844 light/dark browser QA — overflow `0`, console xato `0`. **Admission label Azurbekniki:** bu band alohida ADMIT sifatida ochilmadi, A2 ichidagi owner control surface deb yozildi.
- **2026-07-27 landing editor foundation:** `/backoffice/landing/` Bosqich 1 va bo'lim TOC/tab main'da; owner-only, reason+confirmation, `LogEntry` va no-op patterni. Repeatable CRUD/reorder, iframe preview, audit history/rollback hali `HOLD/NEXT`; A2 tugagan degani emas.
- **Faza:** R1.

### A3. Live Lesson Orchestrator — `PLANNED`, `M contract + L adapters/UI`

- **Outcome:** Azurbek dars kunini ≤3 asosiy amalda boshqaradi; web/bot/Mini App bir xil state ko'rsatadi.
- **Canonical state:** mega-state emas. `LessonRun` schedule/live/check-in, `LessonAccess` locked/released, `AssignmentLifecycle` open/submitted/reviewed alohida graph; orchestrator ularni owner flow'ida aggregate qiladi.
- **Scope:** oldingi A0 “Dars kuni” + bot attendance + release + core notification + grading queue.
- **Acceptance:** transitionlar permission/idempotency/invariant testli; notification side-effect `on_commit`; test cohortda end-to-end; adapter parity contract.
- **Faza:** R2.

### A4. Acquisition, payment va entitlement — `PLANNED`, `M contract + L adapters`

- **Outcome:** learner to'g'ri course/cohort/plan bilan yoziladi va faqat haqiqiy active access oladi.
- **Canonical state:** identity/claim, `Application`, `Payment` va `Enrollment/Entitlement` alohida graph; bitta chiziqli mega-state yo'q.
- **Scope:** checkout course binding; inactive cohortni tasodifiy reactivation qilmaslik; receipt ayni tanlangan enrollmentga; typed entitlement; Telegram credential claim; idempotent receipt/approval.
- **Acceptance:** web/Telegram parity; duplicate/replay tests; permission matrix; selected plan checkoutgacha saqlanadi.
- **Faza:** R2.

### A5. Mobil oltin oqim quality gate — `CROSS-CUTTING, R1'dan`

- **Outcome:** asosiy learner/teacher flow'lari telefon ekranida bloklanmaydi.
- **Scope:** Messenger 320–414px; lesson header 360px; exam 568×320/640×360 landscape; reconnect; keyboard/accessibility; checkout; teacher attendance; Mini App deep actions.
- **Acceptance:** desktop Chrome + Android Chrome + iOS Safari video-evidence; overflow/overlap/console/blocking keyboard issue `0`; real mic/upload; empty/error/dark/light states.
- **Faza:** sequential feature emas. R1'dan boshlab har band tegadigan mobile/auth/media flow evidence beradi; R2'da to'liq 3-qurilma sign-off.

### A6. Learner Outcome Ledger minimal — `PLANNED`, `M`

- **Outcome:** platforma chat sonini emas, nima o'rganilgani va qaysi yordam kerakligini biladi.
- **Canonical contract:** launch uchun faqat `PracticeSession`, `LearnerAttempt`, `MasteryEvidence` va versionlangan outcome event. Objective/review policy fields yoki config'da; yangi model faqat evidence bilan admission oladi.
- **Scope:** quiz/assignment/mock/practice evidence; onboarding CEFR/goal; misconception taxonomy; event correlation.
- **Acceptance:** same attempt duplicate yozilmaydi; mastery faqat evidence'dan; AI memory preference/goal uchun, mastery system-of-record emas.
- **Faza:** R3 foundation.

### A7. Daily Coach + bitta Structured Practice mode — `PLANNED`, `L`

- **Outcome:** learner har kuni keyingi 10–15 daqiqalik aniq ishni oladi va qayta urinish o'sishini ko'radi.
- **Canonical owner:** Outcome Loop orchestration; Messenger faqat yordamchi drawer.
- **Flow:** `Diagnose → Plan → one item → hint/retry → feedback → transfer check → Proof`.
- **Scope:** release-aware navigator; deterministic 3-task plan; one-item-at-a-time quiz; due review; no upfront answer key.
- **Acceptance:** structured flow success `≥98%`; first activity completion `≥60%`; pre/post `+15 pp` pilot target; dashboard/course/Mini App faqat entry point.
- **Faza:** R3.

### A8. Gemini free-tier budget mode — `IMPLEMENTED/TESTED — LOCAL REGRESSION GREEN`, `M`

- **Outcome:** development va kichik beta Gemini free-tierni bir foydalanuvchi, retry fan-out yoki hisoblanmagan embedding bilan tugatib qo'ymaydi; core LMS AI'siz ham ishlaydi.
- **Canonical owner:** provider-call ledger + reservation/budget policy + Control Center. Per-user `aicontrol` allowance product policy; global Gemini supply budgeti undan yuqori hard gate.
- **Implementatsiya:** `AISupplyEvent`/`AISupplyState` global kunlik+minute request va kunlik token reservation/reconciliation ledgeri; ledger DB failure fail-closed; staff ham hisoblanadi. Main chat `AIResponseRun.idempotency_key` bilan pre-reserve qiladi. Chat/grounding, SmartForm, bot guest, RAG/memory embedding va reindex calllari qamralgan; cache hit request sarflamaydi.
- **Provider guard:** SDK retry off; `1 primary + max 1 fallback`; 429/quota/billing fail-fast+circuit; free allowlist; prompt/output/timeout/deadline caps. Free-mode'da API grounding engine va provider chegarasida hard-off (`GoogleSearch()` construction `0`), guest default-off. DO explicit `AI_ALLOW_DIGITALOCEAN=True` admissionisiz, noma'lum provider esa har doim factoryda fail-closed.
- **Model contract:** primary `gemini-3.1-flash-lite`, temporary fallback `gemini-2.5-flash-lite`; ikkalasi allowlistda. 3.1 Flash-Lite stable/free-tier va cost-efficient default sifatida tanlangan. 2.5 Flash-Lite uchun public shutdown e'lon qilinmagan; 2026-10-16 ichki reviewda fallbackni olib tashlash yoki yangi admitted modelga migrate qilish qayta ko'riladi. 3.7 Flash joriy projectdagi 20 RPD sabab hozir allowlistga kiritilmagan.
- **Control Center/admin:** free-tier mode, configured cap, used/reserved/remaining, minute burst, actual attempts, event holatlari va cooldown stoplight; supply policy/event/state adminlari. Exact Google quota raqamlari hardcode qilinmaydi, chunki ular dynamic/account-specific; minute cap project ichki RPM-uslubidagi guard.
- **Target acceptance evidence:** mocked/offline testlarda duplicate, missing usage, 429=1 attempt, non-quota fallback≤2, cooldown network=0, DO HOLD va joriy caller accounting tekshirilgan; post-A8 offline full suite 527/527 va local system audit 10/10 GREEN.
- **Closeout pending:** SQLite/PostgreSQL haqiqiy concurrent reservation/transaction proof. SmartForm/guest counter va lesson reindex concurrency lease/claim to'liq emas; current Gemini vision unavailable.
- **Degradatsiya:** free-mode search intent bitta plain chatga tushadi va live ma'lumot tekshirilmaganini halol aytadi; guest default-off. Supply denialda core flow, local catalog, cache/lexical retrieval va human/Telegram handoff qoladi. System-wide audited kill-switch UI A2ning qolgan scope'i.
- **Faza:** R0 closeout. Boshqa AI behavior ishidan oldin.

### A9. AI eval, latency va cost release gate — `PLANNED`, `M foundation + rolling gate`

- **Outcome:** premium AI claim'i model taassurotiga emas, fresh evidence'ga tayanadi.
- **Scope:** A8 supply guard ustida 320-case target golden dataset; R1 foundation `50`, R3 critical beta gate `75`, premium price gate `≥150` teacher-authored case. 0–4 rubric; system-role/prompt-injection; Turkish/CEFR; RAG/citation; memory/privacy; routing/access; provider fallback; price/quota ledger.
- **Acceptance:** critical safety/access `0`; injection success `<1%`; Turkish `≥92%`; grounded support `≥95%`; RAG recall@4 `≥90%`; memory precision `≥97%`; p95 text `<8s`; hard deadline `20s`; max 1 fallback; AI cost/premium revenue `≤25%`.
- **Faza:** A8'dan keyin R1 foundation, R3 gate A7'dan keyin; production/premium real-data validation alohida admission.

---

## S. SIT — Study in Turkey portali (parallel mahsulot yo'nalishi)

*Owner admission: 2026-07-28, Azurbek — “SIT launch rejasidan oldin, zudlik bilan”. Bu band A-narvonining bir qismi emas: alohida auditoriya, alohida daromad oqimi va alohida canonical domen. Shuning uchun A0–A9 tartibiga qo'shilmaydi, yoniga qo'yiladi.*

### Admission gate javoblari

1. **Muammo:** platformaga faqat til kursi orqali kirish mumkin edi; “Turkiyada o'qish” niyati bor keng auditoriya uchun kirish nuqtasi va owner uchun yangi daromad oqimi yo'q edi.
2. **Asosiy KPI:** kvalifikatsiyalangan yordam so'rovi soni (universitet sahifasi → yordam CTA → messenger handoff). Trafik yoki universitet soni KPI emas.
3. **Canonical state:** yangi `sit` domeni. Katalog haqiqati — `University`/`UniversityFaculty`/`UniversityProgram` va yondosh ro'yxatlar; xabar haqiqati — `Announcement`; kontent — `KnowledgeArticle`. Yordam so'rovi lifecycle'i hali canonical emas (S2).
4. **Joriy adapterlar:** public web (`/sit/`), Django admin, messenger handoff, `sit_advisor` va `/backoffice/sit/`. **Keyin:** S2 contextli handoff/lifecycle va zarur bo'lsa Telegram adapteri.
5. **Owner yuki:** **oshadi** — katalogni dolzarb tutish va lead follow-up doimiy ish. Bu ataylab qabul qilingan savdo yuki, avtomatlashtirish bilan qoplanmaydi.
6. **Flag/rollback:** `is_published` per-record gate; butun portalni o'chirish = `/sit/` route'ini olib qo'yish. Core LMS oqimlariga bog'liq emas, shuning uchun rollback izolyatsiyalangan.
7. **Faza:** owner qarori bilan launch rejasidan oldin. Core A-narvoni to'xtamaydi, lekin owner vaqti bo'linadi (pastdagi risk).

### S1. Data foundation va public portal — `EVIDENCE READY`, `L`

- **Outcome:** universitet, dastur, kontrakt, qabul holati va hujjat ma'lumoti bitta manbadan, filtrlanadigan public portalda.
- **Canonical owner:** `sit` app modellari + `sit/selectors.py`.
- **Adapterlar:** `/sit/`, `/sit/universities/`, `/sit/universities/<slug>/`, `/sit/guides/<slug>/`, Django admin.
- **Evidence (2026-07-28, `58bcf50`):** `python manage.py test` — 443/443 OK (2026-07-29 mustaqil qayta yugurtirildi, o'sha natija); `check` — 0 issues; `makemigrations --check` — No changes; live `/sit/` real published data bilan render bo'ladi, console xato 0.
- **Data integrity gate:** `is_published=True` uchun `source_url` va `last_verified_on` majburiy (`clean()`da). Vaqtga sezgir qabul/narx ma'lumoti manbasiz chiqmaydi. Migratsiya soxta universitet seed qilmaydi.

### S2. Yordam so'rovi lifecycle — `PLANNED`, `M`

- **Outcome:** yordam CTA bosgan real niyatli foydalanuvchi kuzatiladigan so'rovga aylanadi; owner DM oqimida yo'qotmaydi.
- **Canonical state:** `SITInquiry` state machine (`yangi → bog'lanildi → jarayonda → yakunlandi/bekor`), universitet konteksti bilan.
- **Adapterlar:** universitet sahifasi CTA (auth talab qiladi), messenger handoff, owner ro'yxati.
- **Acceptance:** auth gate; duplicate/spam himoyasi; owner uchun holat ro'yxati; transition va permission testlari; hech qanday pipeline DM xotirasida qolmaydi.
- **Ochiq:** jiddiylik to'lovi (pastda).

### S3. SIT AI advisor — `EVIDENCE READY`, `M`

- **Outcome:** foydalanuvchi byudjet/til/daraja aytadi, faqat portaldagi tasdiqlangan ma'lumotdan tavsiya oladi, keyin ownerga yo'naltiriladi.
- **Canonical owner:** mavjud AI engine + yangi `sit_advisor` skill va katalog retrieval tool. Yangi AI subsystem emas.
- **Acceptance:** javob faqat `is_published` yozuvlardan; katalogda yo'q universitet/narx **taklif qilinmaydi**; tavsiya oxirida handoff; grounded support evalida A9 qoidalari qo'llanadi.
- **Xavf:** AI viza/qabul kabi rasmiy masalada maslahat berayotgandek ko'rinishi. Javob doirasi qat'iy cheklanadi.
- **Evidence (2026-07-29, `a43a654`):** deterministic `sit_catalog` retrieval, published-only selectors, bounded context va routing regressionlari; implementatsiya sessiyasida `python manage.py test sit ai messenger` 158/158, check 0.

### S4. Owner workflow va real ma'lumot — `EVIDENCE READY` foundation, `M`

- **Outcome:** owner katalogni Jazzmin admin'siz, dolzarblik nazorati bilan yuritadi.
- **Scope:** `/backoffice/sit/` (landing editor pattern'ida), eskirgan yozuvlarni ko'rsatuvchi signal (`last_verified_on` bo'yicha), real universitet ma'lumotini faqat rasmiy manbadan kiritish.
- **Acceptance:** owner-only gate; audit; nashr qilishdan oldin manba/sana majburiyligi UI'da ko'rinadi.
- **Evidence (2026-07-29, `4cb3487`):** `/backoffice/sit/` dashboard, 90 kunlik stale signal, filter/editor/formset, preview, reason+confirmation+audit; implementatsiya sessiyasida full suite 453/453 va focused 42/42.
- **Qolgan:** real universitet ma'lumoti owner tomonidan rasmiy manbadan kiritiladi; foundation `EVIDENCE READY`, data completeness emas.

### Ochiq owner qarorlari

| # | Savol | Holat |
|---|---|---|
| S-D1 | Bilim bazasi `KnowledgeArticle` bo'lib qoladimi yoki `blog`ga birlashadimi? | **Ochiq.** Muhokamada blog'ni qayta ishlatish kelishilgan edi; implementatsiya alohida model bilan ketdi (sababi: manba/tekshiruv gate'i blogda yo'q). Hozir ishlayapti, zarari yo'q. |
| S-D2 | 5 000 so'mlik jiddiylik to'lovi qachon yoqiladi? | **Bloklangan.** `University.application_help_fee` modelda bor, lekin qo'lda receipt oqimi mayda to'lov uchun owner yukini **oshiradi**. Real gate uchun avtomatik to'lov kerak — u `C. CUT`da (Payme/Click/Uzum). S2 v1 = auth + intake, to'lov gate'i flag ortida keyin. |
| S-D3 | E'lonlar uchun alohida sahifa kerakmi? | Ochiq. Hozir bosh sahifada section; “Barcha e'lonlar” havolasi hali sahifasiz. |

### Risklar

- **S-R1 — owner sig'imi:** `Ish tartibi`ning 1-qoidasi (“bir vaqtda bitta ADMIT band”) SIT bilan buziladi. Owner buni bilib qabul qildi. Yumshatish: SIT slice'lari kichik va ketma-ket, A-narvoni to'xtamaydi.
- **S-R2 — ma'lumot eskirishi:** qabul muddati va kontrakt narxi tez o'zgaradi. Eskirgan public narx = ishonch va claim riski. Yumshatish: `last_verified_on` majburiy, S4'da eskirish signali.
- **S-R3 — lead follow-up qarzi:** javobsiz qolgan so'rov obro'ga zarar beradi. S2 gacha DM oqimi kuzatilmaydi — shuning uchun S2 SIT'ning keyingi ustuvor slice'i.

---

## Yetkazilgan, lekin active navbat emas

| Capability | Joriy haqiqat | Ochiq evidence/gap |
|---|---|---|
| Learner streak/freeze | `LearnerStreak`, canonical `record_activity` va self-updating nudge main'da | Windows/SQLite teng timestamp ordering flake'i `-created_at, -id` tie-breaker va state-change bubble bilan tuzatildi; post-fix full 527/527 va focused streak 15/15; “done” update qayta Telegram outbox yaratmaydi |
| Landing editor | Bosqich 1 + TOC/tab main'da | Bosqich 2–5 `HOLD/NEXT`; active core slice emas |
| Telegram F0–F9 | onboarding, checkout, attendance, AI, admin, outbox, lesson, assignment va quiz main'da | Public webhook/outbox process `HOLD`; F11–F13 to'liq emas |

## B. NEXT — faqat core gate'lardan keyin

| Band | Qaror | Qayta admission sharti |
|---|---|---|
| Placement/daraja testi | Minimal deterministic acquisition slice mumkin | A0–A5 yashil; result claim curriculum bilan kalibrlangan |
| Writing Revision + Teacher Inbox | R3dan keyingi kichik conditional pilot; taqdimot sharti emas | A7 va A9 critical gate; owner capacity; private media/scope; teacher baseline |
| `word_builder` | Prompt skill emas, structured morphology PracticeMode | Approved dataset + objective/item schema + 30–50 eval case |
| `conversation_partner` | Text-only bounded scenario; pronunciation claim yo'q | PracticeSession state + turn/rubric + safety/cost gate |
| SRS “Lug'atim” | Outcome Ledger ichidagi scheduler capability | A6 stable; manual/dars vocabulary manbasi ishonchli |
| “Azure haftaligi” AI report | Defer | Outcome data, memory precision va report eval o'tgan |
| “B2: 68%” tayyorgarlik foizi | Defer/rename | Validatsiyalangan mastery formula; aks holda course-requirement progress |
| Telegram “Bugungi ko'prik” va streak-risk | Defer | Core lesson/payment/outbox xabarlari GREEN |
| Freemium qatlam | Controlled experiment | Typed entitlements va acquisition flow stable |
| PWA install/offline | Defer | Responsive browser flow GREEN; install real outcome bersa |
| DOCX reader | Defer | Writing flow va private upload policy stable |
| XP iqtisodi/badge polish | Defer | Outcome eventlari canonical; abuse/idempotency testli |
| Blog/home cleanup | Defer | Launch-critical emas |

---

## C. CUT — launchgacha yo'q

| Nima | Sabab |
|---|---|
| Native mobil app | Responsive web/Mini App parity tugamagan |
| Payme/Click/Uzum | Manual receipt core flow yetadi; avval correctness/idempotency |
| Speaking pronunciation auto-baholash | Real audio/STT/alignment/human calibration yo'q |
| Rus interfeysi/boshqa tillar | Fokus: o'zbek → turk tili |
| AI foto-generatsiya | Learner outcome yadrosi emas |
| Ko'p-o'qituvchi marketplace | Solo-owner modeliga zid |
| Sof self-study tarif | Jonli kurs dastagi modelidan tashqari |
| LLM-router va ko'proq model/skill picker | Ichki murakkablik; user outcome emas |
| Chatdan avtomatik SRS kartalar | Shovqin va noto'g'ri mastery riski |
| O'z video-chat platformasi | Telegram live ishlaydi; parallel infratuzilma |
| “Unlimited AI” marketing claim'i | Real quota/cost va outcome modeliga zid |
| High-stakes AI-only grade | Human approval talabi |

---

## D. Har band uchun definition of done

- Admission status, learner/owner outcome va bitta KPI yozilgan.
- Canonical service/state machine va adapterlar aniq; duplicate business logic yo'q.
- Permission, transition, idempotency, invariant va failure/fallback testlari o'tgan.
- Mobile yoki cross-adapter flow bo'lsa real browser/device evidence bor.
- Control Center health/flag/audit ko'rinadi; disable va rollback yo'li sinalgan.
- Product claim bo'lsa fresh evidence yoki `beta` label bor.
- `git diff --check`, tegishli testlar, commit va marinebook protokoli bajarilgan.

## E. Sessiya tartibi

`A8 → A0b → A1a + A2 → A3/A4 contracts → A3/A4 adapters + A5 sign-off → shartli A6/A7 → A9 critical gate`. A1b production/cloud faqat owner `HOLD`ni ochganda. Agent branch prefiksi o'ziga mos; product authority va merge qarori Azurbekda qoladi. Ops, budget va mobile alohida oxirgi ish emas — har bandning release gate'i.

Parallel SIT truth: `S1 + S4 + S3 (bajarildi) → S2 (keyingi)`. S2 A8 yoki core active slice'ni siqmaydi; bir sessiyada bittasiga tegiladi.
