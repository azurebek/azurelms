# 03 — Mahsulot backlog: ADMIT / NEXT / CUT

*Rebaseline: 2026-07-22. Platforma = Azurbek boshqaradigan bitta kurs operatsion tizimi. Har band learner outcome yoki owner workload, canonical owner, adapterlar, acceptance evidence, flag/rollback va fazaga ega bo'lmasa ish boshlanmaydi.*

## Ish tartibi

1. Bir vaqtda bitta `ADMIT` band active product slice bo'ladi.
2. Agentlar uning domain, test, mobile va ops qismlarida parallel ishlashi mumkin; yangi authority yoki subsystem yaratmaydi.
3. Oldingi band exit kriteriydan o'tmasa, keyingisi boshlanmaydi yoki scope'dan kesiladi.
4. `NEXT` band faqat Azurbek admission berganda `ADMIT`ga o'tadi.
5. Holat: `PLANNED` / `IN PROGRESS` / `EVIDENCE READY` / `BLOCKED` / `CUT`.
6. **Istisno — `S. SIT`:** owner qarori bilan A-narvoniga parallel yuritiladi (1-qoidadan ozod). Uning slice'lari o'zaro ketma-ket boradi va A bandlarini to'xtatmaydi; narxi — owner vaqtining bo'linishi (`S-R1`).

---

## A. ADMIT — launch-critical

### A0. Stop-ship security pack — `PLANNED`, `XL → A0a M + A0b L`

- **Outcome:** account, payment va private learner data xavfsiz; owner favqulodda manual rescue qilmaydi.
- **Canonical owner:** auth/access/media policies.
- **Scope A0a (M):** one-time/expiring Telegram auth token; webhook secret fail-closed va no-secret logging; inactive staff denial; owner/teacher scope. **A0b (L):** upload inventory, private media, MIME/magic-byte/size validation va WebSocket access recheck.
- **Adapters:** web auth, Telegram webhook, media download, Messenger WebSocket.
- **Acceptance:** replay, forged webhook, cross-user media va expired enrollment socket regressionlari; anonymous private media `403/404`; kill/rollback runbook.
- **Faza:** P0. Boshqa featurelardan oldin.

### A1. Production runtime va CI — `PLANNED`, `L`

- **Outcome:** web, AI task va Telegram notification jim yo'qolmaydi; release qayta tiklanadi.
- **Canonical owner:** deployment config + release gate.
- **Scope:** broker/channel fail-fast; `telegram_outbox --loop` 1-replica process; `.dockerignore`; CI required checks; health/readiness; backup/restore; static build; release smoke.
- **Acceptance:** test Notification → outbox `sent`; broker round-trip; `check --deploy`; full suite; restore va rollback drill.
- **Faza:** P0.

### A2. Azure Control Center v0 — `IN PROGRESS`, `L`

- **Outcome:** Azurbek bitta joydan policy, health, queues, quality, cost va release holatini boshqaradi.
- **Canonical owner:** mavjud backoffice + `aicontrol` kengaytmasi; yangi parallel admin subsystem yo'q.
- **Scope:** `/backoffice/control/`; owner-only; capability registry; effective config; feature flags/kill switches; queue/worker health; audit va release stoplight. Chuqur analytics v0 scope'ida emas.
- **Acceptance:** GREEN/AMBER/RED sababli; har mutation reason+confirmation+idempotency+audit; arbitrary shell yo'q; `/backoffice/ai-control/` AI tab/compatibility yo'liga tutashadi.
- **2026-07-22 foundation evidence:** active superuser-only read-only route, 10-capability registry, safe partial-failure snapshot, effective config va shu servisdagi `system_audit` CLI tayyor; 1280x900/390x844 browser QA hamda permission/CLI testlari o'tdi. Hali kerak: mutation audit/confirmation/idempotency, flags/kill switches, active worker heartbeat, `ReleaseRecord`, cost/quality va qolgan capability probe'lari. Shu sabab band `EVIDENCE READY` emas.
- **2026-07-22 birinchi mutation surface — markaziy brend:** `/backoffice/control/brand/` A2 scope'i ichida, mavjud backoffice ustida qurildi; yangi parallel admin subsystem yaratilmadi. A2ning mutation acceptance shartlarini qondiradi: majburiy `change_reason`, majburiy confirmation checkbox, `LogEntry` audit yozuvi va o'zgarish bo'lmasa yozmaydigan no-op yo'l. Canonical owner: `frontend.SiteSettings`; adapterlar (public, app, teacher, backoffice, messenger, Mini App, auth, exam, sertifikat, error shell'lari) faqat `templates/components/brand_logo.html` orqali iste'mol qiladi. Evidence: `python manage.py test` 336/336, 1280x900 va 390x844 light/dark browser QA — overflow `0`, console xato `0`. **Admission label Azurbekniki:** bu band alohida ADMIT sifatida ochilmadi, A2 ichidagi owner control surface deb yozildi.
- **Faza:** P1.

### A3. Live Lesson Orchestrator — `PLANNED`, `M contract + L adapters/UI`

- **Outcome:** Azurbek dars kunini ≤3 asosiy amalda boshqaradi; web/bot/Mini App bir xil state ko'rsatadi.
- **Canonical state:** mega-state emas. `LessonRun` schedule/live/check-in, `LessonAccess` locked/released, `AssignmentLifecycle` open/submitted/reviewed alohida graph; orchestrator ularni owner flow'ida aggregate qiladi.
- **Scope:** oldingi A0 “Dars kuni” + bot attendance + release + core notification + grading queue.
- **Acceptance:** transitionlar permission/idempotency/invariant testli; notification side-effect `on_commit`; test cohortda end-to-end; adapter parity contract.
- **Faza:** P1–P2.

### A4. Acquisition, payment va entitlement — `PLANNED`, `M contract + L adapters`

- **Outcome:** learner to'g'ri course/cohort/plan bilan yoziladi va faqat haqiqiy active access oladi.
- **Canonical state:** identity/claim, `Application`, `Payment` va `Enrollment/Entitlement` alohida graph; bitta chiziqli mega-state yo'q.
- **Scope:** checkout course binding; inactive cohortni tasodifiy reactivation qilmaslik; receipt ayni tanlangan enrollmentga; typed entitlement; Telegram credential claim; idempotent receipt/approval.
- **Acceptance:** web/Telegram parity; duplicate/replay tests; permission matrix; selected plan checkoutgacha saqlanadi.
- **Faza:** P1–P2.

### A5. Mobil oltin oqim quality gate — `CROSS-CUTTING, P0'dan`

- **Outcome:** asosiy learner/teacher flow'lari telefon ekranida bloklanmaydi.
- **Scope:** Messenger 320–414px; lesson header 360px; exam 568×320/640×360 landscape; reconnect; keyboard/accessibility; checkout; teacher attendance; Mini App deep actions.
- **Acceptance:** desktop Chrome + Android Chrome + iOS Safari video-evidence; overflow/overlap/console/blocking keyboard issue `0`; real mic/upload; empty/error/dark/light states.
- **Faza:** sequential feature emas. A0'dan boshlab har band tegadigan mobile/auth/media flow evidence beradi; P2'da to'liq 3-qurilma sign-off.

### A6. Learner Outcome Ledger minimal — `PLANNED`, `M`

- **Outcome:** platforma chat sonini emas, nima o'rganilgani va qaysi yordam kerakligini biladi.
- **Canonical contract:** launch uchun faqat `PracticeSession`, `LearnerAttempt`, `MasteryEvidence` va versionlangan outcome event. Objective/review policy fields yoki config'da; yangi model faqat evidence bilan admission oladi.
- **Scope:** quiz/assignment/mock/practice evidence; onboarding CEFR/goal; misconception taxonomy; event correlation.
- **Acceptance:** same attempt duplicate yozilmaydi; mastery faqat evidence'dan; AI memory preference/goal uchun, mastery system-of-record emas.
- **Faza:** P3 foundation.

### A7. Daily Coach + bitta Structured Practice mode — `PLANNED`, `L`

- **Outcome:** learner har kuni keyingi 10–15 daqiqalik aniq ishni oladi va qayta urinish o'sishini ko'radi.
- **Canonical owner:** Outcome Loop orchestration; Messenger faqat yordamchi drawer.
- **Flow:** `Diagnose → Plan → one item → hint/retry → feedback → transfer check → Proof`.
- **Scope:** release-aware navigator; deterministic 3-task plan; one-item-at-a-time quiz; due review; no upfront answer key.
- **Acceptance:** structured flow success `≥98%`; first activity completion `≥60%`; pre/post `+15 pp` pilot target; dashboard/course/Mini App faqat entry point.
- **Faza:** P3.

### A9. AI eval, latency va cost release gate — `PLANNED`, `M foundation + rolling gate`

- **Outcome:** premium AI claim'i model taassurotiga emas, fresh evidence'ga tayanadi.
- **Scope:** 320-case target golden dataset; P1 foundation `50`, P3 critical beta gate `75`, premium price gate `≥150` teacher-authored case. 0–4 rubric; system-role/prompt-injection; Turkish/CEFR; RAG/citation; memory/privacy; routing/access; provider fallback; price ledger/reservation.
- **Acceptance:** critical safety/access `0`; injection success `<1%`; Turkish `≥92%`; grounded support `≥95%`; RAG recall@4 `≥90%`; memory precision `≥97%`; p95 text `<8s`; hard deadline `20s`; max 1 fallback; AI cost/premium revenue `≤25%`.
- **Faza:** P1 foundation A2 bilan, P3 gate A7'dan keyin, P4 premium/real-data validation.

---

## S. SIT — Study in Turkey portali (parallel mahsulot yo'nalishi)

*Owner admission: 2026-07-28, Azurbek — “SIT launch rejasidan oldin, zudlik bilan”. Bu band A-narvonining bir qismi emas: alohida auditoriya, alohida daromad oqimi va alohida canonical domen. Shuning uchun A0–A9 tartibiga qo'shilmaydi, yoniga qo'yiladi.*

### Admission gate javoblari

1. **Muammo:** platformaga faqat til kursi orqali kirish mumkin edi; “Turkiyada o'qish” niyati bor keng auditoriya uchun kirish nuqtasi va owner uchun yangi daromad oqimi yo'q edi.
2. **Asosiy KPI:** kvalifikatsiyalangan yordam so'rovi soni (universitet sahifasi → yordam CTA → messenger handoff). Trafik yoki universitet soni KPI emas.
3. **Canonical state:** yangi `sit` domeni. Katalog haqiqati — `University`/`UniversityFaculty`/`UniversityProgram` va yondosh ro'yxatlar; xabar haqiqati — `Announcement`; kontent — `KnowledgeArticle`. Yordam so'rovi lifecycle'i hali canonical emas (S2).
4. **Adapterlar:** public web (`/sit/`), Django admin, messenger handoff. Keyin: AI advisor, Telegram, `/backoffice/sit/`.
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

### S3. SIT AI advisor — `PLANNED`, `M`

- **Outcome:** foydalanuvchi byudjet/til/daraja aytadi, faqat portaldagi tasdiqlangan ma'lumotdan tavsiya oladi, keyin ownerga yo'naltiriladi.
- **Canonical owner:** mavjud AI engine + yangi `sit_advisor` skill va katalog retrieval tool. Yangi AI subsystem emas.
- **Acceptance:** javob faqat `is_published` yozuvlardan; katalogda yo'q universitet/narx **taklif qilinmaydi**; tavsiya oxirida handoff; grounded support evalida A9 qoidalari qo'llanadi.
- **Xavf:** AI viza/qabul kabi rasmiy masalada maslahat berayotgandek ko'rinishi. Javob doirasi qat'iy cheklanadi.

### S4. Owner workflow va real ma'lumot — `PLANNED`, `M`

- **Outcome:** owner katalogni Jazzmin admin'siz, dolzarblik nazorati bilan yuritadi.
- **Scope:** `/backoffice/sit/` (landing editor pattern'ida), eskirgan yozuvlarni ko'rsatuvchi signal (`last_verified_on` bo'yicha), real universitet ma'lumotini faqat rasmiy manbadan kiritish.
- **Acceptance:** owner-only gate; audit; nashr qilishdan oldin manba/sana majburiyligi UI'da ko'rinadi.

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

## B. NEXT — faqat core gate'lardan keyin

| Band | Qaror | Qayta admission sharti |
|---|---|---|
| Placement/daraja testi | Minimal deterministic acquisition slice mumkin | A0–A5 yashil; result claim curriculum bilan kalibrlangan |
| Writing Revision + Teacher Inbox | P4'dagi kichik conditional pilot; launch sharti emas | A7 va A9 critical gate; owner capacity; private media/scope; teacher baseline |
| `word_builder` | Prompt skill emas, structured morphology PracticeMode | Approved dataset + objective/item schema + 30–50 eval case |
| `conversation_partner` | Text-only bounded scenario; pronunciation claim yo'q | PracticeSession state + turn/rubric + safety/cost gate |
| SRS “Lug'atim” | Outcome Ledger ichidagi scheduler capability | A6 stable; manual/dars vocabulary manbasi ishonchli |
| Streak/freeze | Defer | Real activity semantics va retention baseline mavjud |
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

`A0 → A1 → A2 + A9-foundation → A3/A4 contracts → A3/A4 adapters + A5 sign-off → A6 → A7 → A9 critical gate → conditional Writing/Teacher pilot`. Agent branch prefiksi o'ziga mos bo'ladi; product authority va merge qarori Azurbekda qoladi. Ops va mobile alohida oxirgi ish emas — har bandning release gate'i.

Parallel: `S1 (bajarildi) → S2 → S4 → S3`. SIT slice'i A bandi bilan bir sessiyada aralashtirilmaydi — har sessiya bittasiga tegadi.
