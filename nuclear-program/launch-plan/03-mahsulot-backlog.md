# 03 — Mahsulot backlog: ADMIT / NEXT / HOLD / CUT

*Rebaseline: 2026-08-14. Platforma = Azurbek boshqaradigan bitta kurs operatsion tizimi. Local/pre-productionda DigitalOcean `HOLD`; Gemini free-tier global supply budgeti yangi stop-gate. Har band learner outcome yoki owner workload, canonical owner, adapterlar, acceptance evidence, flag/rollback va fazaga ega bo'lmasa ish boshlanmaydi.*

## Ish tartibi

1. Bir vaqtda bitta `ADMIT` band active product slice bo'ladi.
2. Agentlar uning domain, test, mobile va ops qismlarida parallel ishlashi mumkin; yangi authority yoki subsystem yaratmaydi.
3. Oldingi band exit kriteriydan o'tmasa, keyingisi boshlanmaydi yoki scope'dan kesiladi.
4. `NEXT` band faqat Azurbek admission berganda `ADMIT`ga o'tadi.
5. Queue qarori: `ADMIT` / `NEXT` / `HOLD` / `CUT`. Execution holati: `PLANNED` / `IN PROGRESS` / `IMPLEMENTED/TESTED — LOCAL REGRESSION GREEN` / `EVIDENCE READY` / `BLOCKED`.
6. **Istisno — `S. SIT`:** owner qarori bilan A-narvoniga parallel yuritiladi (1-qoidadan ozod). Uning slice'lari o'zaro ketma-ket boradi va A bandlarini to'xtatmaydi; narxi — owner vaqtining bo'linishi (`S-R1`).
7. **Joriy active closeout — `A5` owner sign-off'i (2026-08-21):** A2 ham yopildi (flag registri, cost ledgeri, backup/email/memory probe'lari va `restore_db --into` drill'i). A5 ning oltita texnik bandi ham yopildi; qolgani agent bajara olmaydigan qism — Android Chrome, iOS Safari va desktop Chrome'da uch qurilmali o'tish (mikrofon, upload, Mini App, dark/light). A8, A0b, A1a bajarildi; A2 da flag registridan boshqa hamma narsa kodda; A3/A4 slice'lari main'da. Yangi AI skill, bulk generation, `heavy` search yoki ommaviy AI beta hamon yo'q.

### Joriy status snapshot

| Band | Queue | Execution | Izoh |
|---|---|---|---|
| A0 | `ADMIT` | `IMPLEMENTED/TESTED` | A0a va A0b beshala slice ham bajarilgan; `EVIDENCE READY` labeli owner qarorida |
| A1a | `ADMIT` | `IMPLEMENTED/TESTED` | GitHub Actions CI (8 required check) + readiness/backup/outbox bajarildi; bog'liqlik zaiflik qarzi reyestrda |
| A1b | `HOLD` | `PLANNED` | cloud deploy va managed services |
| A2 | `ADMIT` | `IMPLEMENTED/TESTED` | audit ledgeri, kill switch, circuit reset, heartbeat, `ReleaseRecord`, flag registri, cost ledgeri va backup/email/memory probe'lari kodda; **qolgan yagona band — AI quality/cost release gate, u esa A9 ning ishi** |
| A8 | `ADMIT` | `IMPLEMENTED/TESTED — LOCAL REGRESSION GREEN` | supply guard kod/target/full testlarda; PostgreSQL contention proofi CI `integration` ishida yopildi, alohida OS processlari bilan takrorlash ochiq |
| A3 | `ADMIT` | `IN PROGRESS` | to'rt slice main'da (davomat parity, session atomikligi, lesson release, grade→learner), 36 test; adapter parity va Mini App qolgan |
| A4 | `ADMIT` | `IN PROGRESS` | to'rt slice main'da (checkout side-effect, yagona pending receipt, receipt binding, Telegram claim), 25 test; typed entitlement qolgan |
| A5 | `ADMIT` | `IMPLEMENTED/TESTED` | oltita texnik band ham yopildi (messenger, dars, imtihon, checkout, attendance, reconnect) + shell tap targetlari; **qolgani faqat owner'ning uch qurilmadagi sign-off'i** |
| S1/S3/S4 | `— delivered` | `EVIDENCE READY` | portal, grounded advisor va owner backoffice kodda |
| S2 | `NEXT` | `PLANNED` | canonical inquiry lifecycle yo'q |
| A10 | `ADMIT` | `PLANNED` | AI Optimise — persona, suhbatlararo davomiylik; R5, owner qarori 2026-08-19 |

---

## A. ADMIT — launch-critical

### A0. Stop-ship security pack — `IMPLEMENTED/TESTED`, `XL → A0a DONE + A0b DONE`

- **Outcome:** account, payment va private learner data xavfsiz; owner favqulodda manual rescue qilmaydi.
- **Canonical owner:** auth/access/media policies.
- **Scope A0a (M):** one-time/expiring Telegram auth token; webhook secret fail-closed va no-secret logging; inactive staff denial. **A0b (L):** teacher default-deny scope, upload inventory, private media, MIME/magic-byte/size validation, WebSocket access recheck va django-csp v4 header/Mini App exception testi.
- **Adapters:** web auth, Telegram webhook, media download, Messenger WebSocket.
- **Acceptance:** replay, forged webhook, cross-user media va expired enrollment socket regressionlari; anonymous private media `403/404`; kill/rollback runbook.
- **Evidence (A0a, 2026-07-23):** `e7cd4a6` va `5bea4a5` — one-time/browser-bound Telegram auth, webhook fail-closed/no-secret logging, inactive staff denial; implementatsiya paytida full suite 385/385 va check yashil.
- **Evidence (A0b/1, 2026-08-15):** teacher course/cohort scope default-deny. Qoida `core/access.py`da canonical (`teacher_course_queryset`/`teacher_cohort_queryset`); web teacher paneli, Telegram bot va davomat sahifasi faqat shuni iste'mol qiladi. Audit uchta nusxani topdi, ikkitasi default-allow edi — bot adapterida qoida teskari yozilgan bo'lib, har qanday active staff barcha guruhlarni ko'rardi. 10 yangi test, jumladan adapter parity; full suite 537/537.
- **Evidence (A0b/2, 2026-08-15):** upload MIME/magic-byte/size gate'i. `core/upload_validation.py` faylni nomiga yoki klient yuboradigan `content_type` ga emas, boshidagi baytlariga qarab tekshiradi; uchta profil (`image` 5MB, `document` 12MB, `audio` 25MB) va kengaytma izchilligi. Beshta learner upload yo'li ulandi: chat biriktirmasi (ilgari tur tekshiruvi umuman yo'q edi), to'lov cheki, vazifa fayli (canonical servisda — web va bot ulashadi), imtihon speaking audiosi (ilgari soxtalashtiriladigan `content_type`) va avatar. Model field validatorlari `.create()`/`.save()` yo'lida ishlamagani uchun gate view/servis darajasida turadi. 19 yangi test; CKEditor upload'i staff-gated deb tekshirildi.
- **Evidence (A0b/3, 2026-08-15):** private media. To'lov cheki, vazifa fayli, chat biriktirmasi va speaking yozuvi `PRIVATE_MEDIA_ROOT` ga (public ildizdan tashqariga) ko'chirildi; yagona kirish nuqtasi `core/private_media_views.py` — egasi, kurs o'qituvchisi yoki owner, aks holda `404`. `Content-Type` fayl baytlaridan aniqlanadi, rasm `inline`, qolgani `attachment`, `nosniff` va `no-store`. Owner qarori bo'yicha signed URL emas, stream. 14 yangi test; full suite 583/583.
- **Evidence (A0b/4, 2026-08-15):** WebSocket access recheck. Ruxsat endi har `receive()` da DB holatidan qayta hisoblanadi; obuna tugasa yoki hisob bloklansa ochiq socket `4403` bilan yopiladi va xabar saqlanmaydi. `self.user` scope nusxasi eskirgani uchun foydalanuvchi holati ham qayta o'qiladi. 5 yangi WebSocket testi; nazorat yugurishida tuzatishsiz 3 tasi yiqiladi.
- **Evidence (A0b/5, 2026-08-15):** django-csp v4 migratsiyasi. Eski `CSP_*` nomlari v4 tomonidan o'qilmagani uchun `SECURITY_STRICT=True` da ham header umuman chiqmasdi; siyosat endi `CONTENT_SECURITY_POLICY` dictida va `core/csp_policy.py` da quriladi (`object-src 'none'`, `base-uri`/`form-action 'self'`, Mini App skript manbasi qo'shildi). Mini App middleware headerni o'zi yozishdan to'xtadi va v4 ning `_csp_replace` mexanizmiga o'tdi. 9 yangi test real javob sarlavhasi darajasida.
- **A0b holati:** beshala slice ham bajarildi (teacher scope, upload validatsiya, private media, socket recheck, CSP v4). A0 endi `EVIDENCE READY` ga nomzod — yakuniy label owner qarori.
- **Faza:** R1. A8 bilan parallel faqat test/docs ishlari; yangi product featurelardan oldin.

### A1. Reproducible runtime va CI — `A1a IMPLEMENTED/TESTED`, `A1b HOLD`

- **Outcome:** web, AI task va Telegram notification jim yo'qolmaydi; release qayta tiklanadi.
- **Canonical owner:** deployment config + release gate; vendor alohida adapter qarori.
- **A1a — bajarildi:** ~~`.dockerignore`~~ **(2026-08-15: sirlar image'ga tushmaydi)**; ~~CI required checks~~ **(2026-08-15: `.github/workflows/ci.yml`, §4 dagi 8 check, uchta ish)**; ~~health/readiness contract~~ **(2026-08-15: `/healthz` + `/readyz`, 9 test)**; ~~static build~~ **(CI `collectstatic` bosqichi)**; ~~secret/dependency scan~~ **(2026-08-15: `scan_secrets` + `pip-audit` reyestri)**; ~~Telegram outbox claim/lease~~ **(2026-08-15: atomik claim + lease expiry, 8 test, Control Center `in_flight` ko'rsatkichi)** va local e2e; ~~reproducible local backup/restore~~ **(2026-08-15: `backup_db`/`restore_db`, WAL-safe `VACUUM INTO`, 8 test)**.
- **Evidence (A1a/CI, 2026-08-15):** GitHub Actions yoqildi; birinchi yashil yugurish `69004d3`. `checks` va `supply-chain` SQLite/offline profilda, `integration` esa `pgvector/pgvector:pg16` va `valkey/valkey:8` konteynerlarida: `engine=django.db.backends.postgresql`, `cache=RedisCache`, `layer=RedisChannelLayer`, pgvector `enabled=True`, to'liq suite **689/689 PostgreSQL'da**. Butun run ~2 daqiqa (uchala ish parallel). Bu A8 dan beri kutilgan **real PostgreSQL contention proofining** bir qismini yopadi: SQLite'da `select_for_update()` no-op edi, endi barcha qulf yo'llari haqiqiy `FOR UPDATE` bilan yugiradi.
- **CI birinchi yugurishda topgan production xatosi:** enrollment transfer va promotion PostgreSQL'da butunlay yiqilardi — `select_for_update()` nullable `plan` FK ustidagi LEFT OUTER JOIN bilan birga ishlatilgan (`FOR UPDATE cannot be applied to the nullable side of an outer join`). Tuzatildi (`of=("self",)`) va SQLite'da ham ushlaydigan regressiya testi qo'shildi.
- **Evidence (A1a/deps, 2026-08-15):** gate ishga tushganda topilgan 19 paket / 93 advisory o'sha kuni yopildi. 20 paket ko'tarildi — Django `6.0.2 → 6.0.8`, cryptography `46 → 50`, pyOpenSSL `25 → 26`, Twisted `25.5 → 26.4`, aiohttp `3.13.3 → 3.14.3` (u bilan birga aiogram `3.26 → 3.30`, chunki eskisi `aiohttp<3.14` talab qilardi), pillow, requests, urllib3 va boshqalar. Django 6.1 mavjud, ammo ataylab **olinmadi**: bu xavfsizlik patchi, framework migratsiyasi emas. Suite 689/689 (SQLite va PostgreSQL), `pip check` toza, migration drift yo'q. Reyestr endi bo'sh — har qanday yangi advisory darhol qizil.
- **A1b — `HOLD`:** public hosting, managed PostgreSQL/Valkey/object storage, webhook process va production restore. DigitalOcean majburiy target emas; owner productionni qayta ochganda vendor tanlanadi.
- **Acceptance:** local profile remote xizmatga jim o'tmaydi; test Notification → outbox `sent`; checks/migration/static; isolated local restore. Production acceptance A1b admissionidan keyin alohida.
- **Faza:** R1.

### A2. Azure Control Center v0 — `IMPLEMENTED/TESTED`, `L`

- **Outcome:** Azurbek bitta joydan policy, health, queues, quality, cost va release holatini boshqaradi.
- **Canonical owner:** mavjud backoffice + `aicontrol` kengaytmasi; yangi parallel admin subsystem yo'q.
- **Scope:** `/backoffice/control/`; owner-only; capability registry; effective config; feature flags/kill switches; queue/worker health; audit va release stoplight. Chuqur analytics v0 scope'ida emas.
- **Acceptance:** GREEN/AMBER/RED sababli; har mutation reason+confirmation+idempotency+audit; arbitrary shell yo'q; `/backoffice/ai-control/` AI tab/compatibility yo'liga tutashadi.
- **2026-07-22 foundation evidence:** active superuser-only read-only route, 10-capability registry, safe partial-failure snapshot, effective config va shu servisdagi `system_audit` CLI tayyor; 1280x900/390x844 browser QA hamda permission/CLI testlari o'tdi. Hali kerak: mutation audit/confirmation/idempotency, flags/kill switches, active worker heartbeat, `ReleaseRecord`, cost/quality va qolgan capability probe'lari. Shu sabab band `EVIDENCE READY` emas.
- **2026-07-22 birinchi mutation surface — markaziy brend:** `/backoffice/control/brand/` A2 scope'i ichida, mavjud backoffice ustida qurildi; yangi parallel admin subsystem yaratilmadi. A2ning mutation acceptance shartlarini qondiradi: majburiy `change_reason`, majburiy confirmation checkbox, `LogEntry` audit yozuvi va o'zgarish bo'lmasa yozmaydigan no-op yo'l. Canonical owner: `frontend.SiteSettings`; adapterlar (public, app, teacher, backoffice, messenger, Mini App, auth, exam, sertifikat, error shell'lari) faqat `templates/components/brand_logo.html` orqali iste'mol qiladi. Evidence: `python manage.py test` 336/336, 1280x900 va 390x844 light/dark browser QA — overflow `0`, console xato `0`. **Admission label Azurbekniki:** bu band alohida ADMIT sifatida ochilmadi, A2 ichidagi owner control surface deb yozildi.
- **2026-08-15 append-only audit ledgeri:** `aicontrol.SystemAuditEvent` — kim, qayerdan (`source`), nima qildi (`action`), qanday sabab bilan, `before/after` snapshot, natija, IP/user-agent va release SHA. Append-only model darajasida majburlangan (`save`/`delete` rad etadi), admin read-only. Yozish yagona nuqtadan (`core/audit.py`), maxfiy kalitlar maskalanadi. Uchala owner yuzasi (kill switch, brend, landing) `LogEntry` dan ko'chirildi. 16 test. Qolgani: `05-launch-ops.md` §3 dagi minimal ro'yxatning boshqa bandlari (receipt qarori, enrollment transition, lesson release, grade/review, outbox replay, media denial, release/rollback).
- **2026-08-16 worker heartbeat:** `82f3daa` — Control Center ilgari workerning tirikligini *bilvosita* chiqarardi (navbatda ish bormi). Endi `aicontrol.WorkerHeartbeat` bevosita o'lchanadi: worker har siklda o'zi yozadi (`bot/outbox.py`), snapshot esa oxirgi zarbani o'qiydi — `ALIVE_WINDOW` 2 daqiqa, `DEAD_WINDOW` 15 daqiqa. Bo'sh navbat endi "worker o'lgan" degani emas.
- **2026-08-18 §3 audit ro'yxatining qolgani:** `4e7aa62` — `05-launch-ops.md` §3 dagi minimal ro'yxatdan qolgan bandlar ledgerga ulandi: receipt qarori (tasdiq **va** rad etilgan urinish), enrollment transfer/promotion, lesson release, grade/review va private-media denial. Media denial ataylab cheklangan — faqat autentifikatsiyadan o'tgan aktor va 15 daqiqalik takrorlanish oynasi, chunki ledger append-only va skaner uni bosib keta olmasligi kerak. **Outbox replay ataylab qoldirildi: bunday amal hali mavjud emas** (lease avtomatik qaytadi, owner tugmasi yo'q) — mavjud bo'lmagan amalni auditlash mumkin emas.
- **2026-08-18 `ReleaseRecord`:** `48a454e` — `aicontrol.ReleaseRecord` commit SHA, qo'llangan/qo'llanmagan migrationlar, gate natijalari va owner qarorini saqlaydi; `core/release_service.py` dagi `migration_state()` kod bilan baza o'rtasidagi drift'ni ochadi (deploy'dan keyin unapplied migration qolgani eng jim buziluvchi holat). Owner qarori `release.decision` sifatida auditlanadi. **Halol chegara:** gate natijalari va deploy holatini yozadigan tomon hali yo'q — A1b `HOLD` da; model yozuvni qabul qiladi, yozuvchi keyin keladi.
- **2026-08-20 backup/email/memory probe'lari:** bu uchtasi capability registrida **umuman yo'q** edi — Control Center ularni na yashil, na qizil ko'rsatardi, jim o'tkazib yuborardi. Endi ro'yxatda va har birining probe'i bor. **Zaxira:** so'nggi faylning yoshi (7 kundan eski → AMBER; umuman yo'q → local'da AMBER, production'da RED). **Email:** backend moduli tekshiriladi — `console`/`dummy`/`locmem` production'da RED, chunki xat yuborilgandek ko'rinadi, ammo hech kimga yetib bormaydi; SMTP host bo'sh bo'lsa AMBER. **Xotira:** faol faktlarning embedding qamrovi — `embedding_dim=0` bo'lgan fakt bazada bor, lekin semantik qidiruvda **ko'rinmaydi** (jim degradatsiya); ulush 25% dan oshsa AMBER. Uchala probe ham **read-only**: zaxira olmaydi, xat yubormaydi, xotira yozmaydi. 11 test. **Birinchi yugurishdayoq topdi:** lokal loyihada zaxira umuman yo'q (`backup_db` buyrug'i bor, hech qachon ishlatilmagan) — umumiy holat AMBER'ga o'tdi.
- **2026-08-20 AI xarajat ledgeri:** `core/ai_cost.py` + `aicontrol.AIModelPrice` — `AISupplyEvent` dagi `prompt_tokens`/`completion_tokens` owner kiritgan **sanali narx snapshot'lari** bilan pulga aylantiriladi (kirish va chiqish alohida narxlanadi, pul `Decimal` da). Narx qattiq yozilmadi: u hisobga va vaqtga bog'liq, kodga yozilgani aynan o'lik model va noto'g'ri deadline kabi jim eskirardi. Snapshotlar **append-only** — narx o'zgarsa yangi `effective_from` bilan yangi qator, eskisi tahrirlanmaydi. Xarajat **o'qish paytida** hisoblanadi, chunki owner narxni ko'pincha sarfdan keyin kiritadi; muzlatilgan qiymat abadiy bo'sh qolardi. **Eng muhim qoida — narxlanmagan sarf nol deb yozilmaydi:** rejaning "«Bepul» cost=0 deb yozilmaydi — quota ham scarcity" talabi shu yerda majburlanadi, snapshot topilmasa chaqiruv `unpriced` deb alohida sanaladi. Owner yuzasi `/backoffice/control/ai-cost/` (narx kiritish sabab+tasdiq+`ai_price.record` audit bilan). 21 test. **Qolgani:** user/day va plan margin kesimlari, ular daromad ma'lumotiga bog'lanadi.
- **2026-08-20 umumiy feature flag registri:** `core/flags.py` — flaglar **kodda** e'lon qilinadi (`FLAG_REGISTRY`), DB esa faqat **override** saqlaydi (`aicontrol.FeatureFlag`). Qatori yo'q flag e'lon qilingan default bilan ishlaydi; registrdan olib tashlangan flagning eski qatori jim ta'sir qilmaydi va yuzada "yetim" deb ko'rsatiladi. Noma'lum slug `UnknownFlag` bilan yiqiladi — jim `False` qaytarish xato yozilgan slug tufayli capabilityni jimgina o'chirib qo'yardi. Baza o'qilmasa e'lon qilingan default qaytariladi. Owner yuzasi `/backoffice/control/flags/`: sabab + tasdiq + `feature_flag.update` audit + no-op yo'l. Kesh ataylab yo'q: eskirgan kesh tufayli o'chirilmay qolgan capability arzon so'rovdan yomonroq. **Ikkita haqiqiy flag ulandi** — `public_registration` (yopilganda sahifa ham, POST ham to'xtaydi; mavjud foydalanuvchilar kirishda davom etadi) va `telegram_outbox_sending` (yopilganda xabarlar navbatda saqlanib turadi va **heartbeat baribir yoziladi**, aks holda pauza worker o'lgandek ko'rinardi). 27 test. **AI kill switch ataylab ko'chirilmadi:** u fail-closed va tarmoqdan oldin tekshiriladi, umumiy flag esa default'iga tushadi — semantikasi boshqa.
- **2026-08-19 AI circuit cooldown tozalash:** `/backoffice/control/ai-circuit-reset/` — A8 circuit breaker provider xatolaridan keyin bir soatga ochiladi; sabab bartaraf etilganda owner cooldown'ni sabab+tasdiq bilan tozalaydi va bu `ai.circuit.reset` sifatida auditlanadi. Circuit allaqachon yopiq bo'lsa no-op — ledgerga yozilmaydi. Himoya olib tashlanmaydi: sabab tuzatilmasa circuit qayta ochiladi. 9 test.
- **2026-08-15 AI kill switch:** `/backoffice/control/ai-kill-switch/` — owner bitta tugma bilan barcha remote AI chaqiruvini to'xtatadi. `reserve_supply()` uni tarmoqdan oldin tekshiradi va budjet enforcement o'chiq bo'lsa ham ishlaydi; rad etish ledgerga `kill_switch` sababi bilan yoziladi. Control Center to'xtatilgan holatni AMBER ko'rsatadi (ataylab qilingan degradatsiya, nosozlik emas). 14 test. Qolgani: append-only `SystemAuditEvent` (hozir `LogEntry`), umumiy flag registri, worker heartbeat, `ReleaseRecord`.
- **2026-07-27 landing editor foundation:** `/backoffice/landing/` Bosqich 1 va bo'lim TOC/tab main'da; owner-only, reason+confirmation, `LogEntry` va no-op patterni. Repeatable CRUD/reorder, iframe preview, audit history/rollback hali `HOLD/NEXT`; A2 tugagan degani emas.
- **Faza:** R1.

### A3. Live Lesson Orchestrator — `IN PROGRESS`, `M contract + L adapters/UI`

- **Outcome:** Azurbek dars kunini ≤3 asosiy amalda boshqaradi; web/bot/Mini App bir xil state ko'rsatadi.
- **Canonical state:** mega-state emas. `LessonRun` schedule/live/check-in, `LessonAccess` locked/released, `AssignmentLifecycle` open/submitted/reviewed alohida graph; orchestrator ularni owner flow'ida aggregate qiladi.
- **Scope:** oldingi A0 “Dars kuni” + bot attendance + release + core notification + grading queue.
- **Acceptance:** transitionlar permission/idempotency/invariant testli; notification side-effect `on_commit`; test cohortda end-to-end; adapter parity contract.
- **2026-08-16 to'rt slice (36 test):** (1) `a02f3fc` — teacher davomati o'z hisobini yuritardi va bot bilan XP/streak natijasi farq qilardi; endi ikkala adapter ham `upsert_attendance_and_xp` canonical servisini chaqiradi, 6 parity testi. (2) `88bb094` — dars sessiyasini yopish yarim bajarilishi mumkin edi (davomat yozildi, xabar ketmadi yoki aksincha); endi atomik, 6 test. (3) `82e428c` — `courses/release_service.py` + `/teacher/release/`: owner darsni sabab bilan ochadi/yopadi, `lesson.release` auditlanadi, drip bilan birga ishlaydi, 14 test. (4) `86940c0` — baholangan vazifa learnerga yetib bormasdi; `courses/submission_service.py` XP'ni diff bilan hisoblaydi (idempotent) va bildirishnomani faqat verdikt o'zgarganda yuboradi, 10 test.
- **Qolgan scope:** Mini App deep action parity va test cohortdagi to'liq end-to-end o'tish.
- **Faza:** R2.

### A4. Acquisition, payment va entitlement — `IN PROGRESS`, `M contract + L adapters`

- **Outcome:** learner to'g'ri course/cohort/plan bilan yoziladi va faqat haqiqiy active access oladi.
- **Canonical state:** identity/claim, `Application`, `Payment` va `Enrollment/Entitlement` alohida graph; bitta chiziqli mega-state yo'q.
- **Scope:** checkout course binding; inactive cohortni tasodifiy reactivation qilmaslik; receipt ayni tanlangan enrollmentga; typed entitlement; Telegram credential claim; idempotent receipt/approval.
- **Acceptance:** web/Telegram parity; duplicate/replay tests; permission matrix; selected plan checkoutgacha saqlanadi.
- **2026-08-16 to'rt slice (25 test):** (1) `f1e433e` — checkout sahifasini **ochish** owner holatini o'zgartirardi (enrollment yaratardi, promo band qilardi); o'qish va yozish yo'llari ajratildi (`find_checkout_enrollment` / `resolve_checkout_enrollment`), 8 test. (2) `70fceb2` — bitta enrollmentga bir nechta pending receipt tushishi mumkin edi; endi qisman unique constraint bilan **bazada** kafolatlanadi (`unique_pending_receipt_per_enrollment`), 6 test. (3) `70088ed` — bot chekni kursni taxmin qilib bog'lardi; endi `checkout_started_at` orqali aynan tanlangan kursga bog'lanadi, 3 test. (4) `cbf846e` — Telegram claim havolasi cheksiz va qayta ishlatiladigan edi; `TelegramLinkToken` bilan muddatli va bir martalik bo'ldi, 8 test.
- **2026-08-21 typed entitlement:** `core/entitlements.py` — "bu o'quvchi nimaga haqli?" savoli bitta joyga yig'ildi. Ilgari u ikkiga bo'lingan edi (enrollment faolmi + AI token limiti), plan esa kirish uchun **umuman o'qilmasdi**: Premium to'lagan Starter bilan bir xil huquq olardi. Endi `Capability` enum'i sakkizta nomlangan qobiliyatni e'lon qiladi, `entitlements_for(user, course=...)` esa enrollment holati va plan kodidan kelib chiqib to'plam qaytaradi. **Plan kodi bo'yicha, nomi bo'yicha emas:** `Plan.code` qo'shildi (`unique`), migratsiya mavjud qatorlarni nomdan to'ldiradi — ko'rsatiladigan nomni tahrirlash kirishni jimgina buzmasligi kerak. Faollik qoidasi qayta yozilmadi: `has_active_access()` chaqiriladi, grace day bitta joyda qoladi. Noma'lum qobiliyat `UnknownCapability` beradi; xaritada yo'q plan asos to'plamni oladi. 13 test.
- **Ataylab qilinmagani — plan farqi.** Qaysi tarif nimaga haqli ekani **narx qarori va u ownerniki**. `PLAN_MATRIX` bo'sh qoldirildi, barcha planlar bir xil to'plamni oladi, mavjud xulq **aynan** saqlanadi. Owner matritsani berganda u to'ldiriladi va farq testlar bilan qulflanadi.
- **2026-08-21 Telegram checkout parity testi:** inactive cohort qoidasi web tomonida allaqachon testlangan edi; Telegram adapteri esa sinalmagan edi. Adapter bir xil servisni chaqiradi (dublikat mantiq yo'q), ammo "servis to'g'ri qaror qildi" va "adapter uni to'g'ri yetkazdi" bir xil narsa emas. 5 test.
- **Qolgan scope:** `PLAN_MATRIX` uchun owner qarori. Undan keyin cost ledgerining `plan margin` kesimi ham ochiladi.
- **Faza:** R2.

### A5. Mobil oltin oqim quality gate — `CROSS-CUTTING, R1'dan`

- **Outcome:** asosiy learner/teacher flow'lari telefon ekranida bloklanmaydi.
- **Scope:** Messenger 320–414px; lesson header 360px; exam 568×320/640×360 landscape; reconnect; keyboard/accessibility; checkout; teacher attendance; Mini App deep actions.
- **Acceptance:** desktop Chrome + Android Chrome + iOS Safari video-evidence; overflow/overlap/console/blocking keyboard issue `0`; real mic/upload; empty/error/dark/light states.
- **2026-08-18/19 messenger (5 commit):** owner telefonda ochib "dahshatli darajada buzuq" dedi va aynan shu sahifada beshta nuqson topildi: `d3f69e2` o'lik WebSocket + header overflow; `6957b5e` ikonka rail'i telefonda chatni siqib qo'yardi; `5eac801` `100vh` iOS Safari chrome'ini hisobga olmagani uchun xabar yozish qismi ekran ostida qolardi (`100dvh`); `08b3b47` yopiq drawer chap chekkada 9px bo'lib turardi; `42c3dd5` 16px dan kichik input iOS'da avtomatik zoom ochib, qaytmasdi. **Metodologiya darsi:** avtomatik overflow probe'i bularni o'tkazib yuborgan edi — bo'sh bazada yugurgani va faqat `right > viewport` ni tekshirgani uchun (chapdan chiqqan element ko'rinmagan). Ikkalasi ham tuzatildi.
- **2026-08-20 qolgan texnik bandlar yopildi (6 PR):** `#38` dars sarlavhasi — o'ng guruh `flex:0 0 auto` va ichida qat'iy 160px progress bar bo'lgani uchun 360px da 371px joy talab qilardi: "AI repetitor" 11px kesilar, kurs nomi **nolga siqilardi**. `#39` imtihon landscape — javob maydoni 568x320 da **38px** ga siqilib, so'z hisoblagichi va "min 40 · max 120" talabi `.exam{overflow:hidden}` ortida **yetib bo'lmas** joyda qolardi; sabab `40vh` qoidasi kenglikka qarab yozilgani edi, muammo esa balandlikda. `#40` checkout — grid bandining `min-width:auto` si xulosa paneliga 31px qoldirar va **umumiy summa ekrandan chiqib ketardi**. `#41` teacher attendance — sahifa **toza chiqdi**, tuzatish kerak bo'lmadi. `#42` reconnect — socket bir marta yaratilardi, uzilganda "sahifani yangilang" deb qolardi. `#43` public shell tap targetlari.
- **2026-08-20 sinash imkoniyatidagi bo'shliqlar (bular tuzatilmaguncha bandlarni sinab bo'lmasdi):** `seed_demo` imtihon yaratmasdi (endi beshala bo'lim turi, speaking mikrofon uchun majburiy); `demo-teacher` ga parol berilmagan edi, ya'ni owner teacher oqimini qurilmada ocha olmasdi; guruhda bitta o'quvchi bor edi (endi 6 ta, oxirgisining ismi ataylab uzun).
- **2026-08-20 probe metodologiyasi (besh marta yolg'on gapirdi):** inline elementlar `clientWidth` ni har doim `0` qaytaradi — "siqilgan matn" emas; gorizontal siljiydigan konteyner ichidagi element toshgan emas; yopiq drawer **butunlay** tashqarida — nuqson faqat chetni **kesib o'tgan** element; input `label` ichida bo'lsa nishon label o'lchami; va eng qimmati — men faqat gorizontal toshishni tekshirardim, imtihondagi nuqson esa **vertikal** edi.
- **Qolgan scope — faqat owner qila oladigan ish:** Android Chrome, iOS Safari va desktop Chrome'da uch qurilmali sign-off — mikrofon, upload, Telegram Mini App, dark/light. Mikrofon LAN orqali ishlamaydi (secure context), tunnel majburiy.
- **Qanday sinaladi:** [`nuclear-program/mobile-qa-runbook.md`](../mobile-qa-runbook.md) — LAN va HTTPS tunnel yo'llari, qaysi band qaysi yo'l bilan qoplanishi va dalil formati. Mikrofon LAN orqali ishlamaydi (secure context talab qilinadi), shuning uchun speaking va Mini App uchun tunnel majburiy.
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
- **Model contract (2026-08-19 da yangilandi):** primary `gemini-3.1-flash-lite`, temporary fallback `gemini-3.5-flash-lite`; ikkalasi allowlistda. 3.1 Flash-Lite stable/free-tier va cost-efficient default sifatida tanlangan. **`gemini-2.5-flash-lite` o'lik** — Google uni `404 ... no longer available to new users` bilan rad etadi, ya'ni 2026-10-16 ichki review deadline'i voqea tomonidan bosib o'tildi. Model `RETIRED_MODELS` ro'yxatida: sozlamada qolib ketsa ham ishlatilmaydi. **Tuzoq:** `models.list` uni hamon ro'yxatda ko'rsatardi — haqiqatni faqat real `generateContent` probe'i ochdi. 3.7 Flash joriy projectdagi 20 RPD sabab hozir allowlistga kiritilmagan.
- **Control Center/admin:** free-tier mode, configured cap, used/reserved/remaining, minute burst, actual attempts, event holatlari va cooldown stoplight; supply policy/event/state adminlari. Exact Google quota raqamlari hardcode qilinmaydi, chunki ular dynamic/account-specific; minute cap project ichki RPM-uslubidagi guard.
- **Target acceptance evidence:** mocked/offline testlarda duplicate, missing usage, 429=1 attempt, non-quota fallback≤2, cooldown network=0, DO HOLD va joriy caller accounting tekshirilgan; post-A8 offline full suite 527/527 va local system audit 10/10 GREEN.
- **SQLite concurrency (2026-08-15, yopildi):** `aicontrol/test_supply_concurrency.py` — 8 threadli real contention testi kunlik/minute/token cap, to'liq reserve→reconcile sikli va idempotency key uchun. Test avval kamchilikni ochdi: `select_for_update()` SQLite'da no-op, `BEGIN DEFERRED` esa write-upgrade'da busy_timeout'ni kutmaydi → 8 dan 7 rezervatsiya `database is locked`. Yechim `core/settings.py`da: `transaction_mode=IMMEDIATE` + `timeout=15` + WAL. Bu serializatsiya `supply.py`dan tashqaridagi 13 ta `select_for_update()` chaqiruv joyini ham qamraydi (enrollment transition, promo redemption, exam attempt/answer, davomat, streak, XP va Telegram auth tokenini bir martalik consume qilish).
- **Closeout (2026-08-15 da yangilandi):** PostgreSQL proofi **yopildi** — CI `integration` ishi to'liq suite'ni `pgvector/pgvector:pg16` da yugurtiradi, ya'ni barcha qulf yo'llari haqiqiy `FOR UPDATE` bilan ishlaydi (SQLite'da ular no-op edi). Birinchi yugurishdayoq real production xatosi chiqdi: `select_for_update()` nullable FK ustidagi LEFT OUTER JOIN bilan yiqilardi. **Hali ochiq:** alohida OS processlari bilan takrorlash; SmartForm/guest counter va lesson reindex uchun to'liq lease/claim; joriy Gemini adapteri vision qabul qilmaydi.
- **Degradatsiya:** free-mode search intent bitta plain chatga tushadi va live ma'lumot tekshirilmaganini halol aytadi; guest default-off. Supply denialda core flow, local catalog, cache/lexical retrieval va human/Telegram handoff qoladi. System-wide audited kill-switch UI **2026-08-15 da chiqdi** (`/backoffice/control/ai-kill-switch/`), cooldown'ni tozalash esa 2026-08-19 da (`/backoffice/control/ai-circuit-reset/`).
- **Faza:** R0 closeout. Boshqa AI behavior ishidan oldin.

### A9. AI eval, latency va cost release gate — `PLANNED`, `M foundation + rolling gate`

- **Outcome:** premium AI claim'i model taassurotiga emas, fresh evidence'ga tayanadi.
- **Scope:** A8 supply guard ustida 320-case target golden dataset; R1 foundation `50`, R3 critical beta gate `75`, premium price gate `≥150` teacher-authored case. 0–4 rubric; system-role/prompt-injection; Turkish/CEFR; RAG/citation; memory/privacy; routing/access; provider fallback; price/quota ledger.
- **Acceptance:** critical safety/access `0`; injection success `<1%`; Turkish `≥92%`; grounded support `≥95%`; RAG recall@4 `≥90%`; memory precision `≥97%`; p95 text `<8s`; hard deadline `35s` (**2026-08-19 da 20s dan ko'tarildi** — Google 10s dan past deadline'ni rad etadi, §A8 ga qarang); max 1 fallback; AI cost/premium revenue `≤25%`.
- **Faza:** A8'dan keyin R1 foundation, R3 gate A7'dan keyin; production/premium real-data validation alohida admission.


### A10. AI Optimise — `PLANNED`, `L`

*Owner admission: 2026-08-19, Azurbek — "loyiha yakunrog'ida mutlaqo bajarilishi kerak".*

- **Outcome:** AzureAI har suhbatda notanish yordamchi bo'lib qaytmaydi. U bitta izchil shaxsiyatga ega, o'quvchi haqida allaqachon bilganini eslaydi va uzluksiz hamroh sifatida ishlaydi — silliq, kutilmagan uzilishlarsiz.
- **Canonical owner:** mavjud `ai/memory/` servisi va `ai/skills/` registri. Yangi parallel "persona engine" yaratilmaydi; shaxsiyat prompt qatlamining canonical qismi bo'ladi.

**Poydevor allaqachon bor — bu band noldan boshlanmaydi:**

- `AIMemoryFact` foydalanuvchi bo'yicha saqlanadi (xona bo'yicha emas): kategoriya, ishonch darajasi, holat, ko'rinuvchanlik, embedding va `last_used_at`. Ya'ni **faktlar suhbatlar orasida allaqachon ko'chadi**.
- `ai/memory/` to'liq qatlam: `extractor`, `policy`, `repository`, `retriever`, `semantic` scorer, `summarizer`, `evaluation`. Decay/maintenance va o'quvchi uchun boshqaruv paneli (`/users/settings/ai-memory/`) ishlaydi.
- Ohang (`ai_tone`) to'rtta presetdan iborat va saqlanadi; skill tanlovi 2026-08-19 dan saqlanadigan bo'ldi.

**Uch aniq bo'shliq:**

1. **Shaxsiyat bor, lekin kafolatlanmagan.** *(2026-08-20 tuzatish: dastlab "hech qayerda ta'riflanmagan" deb yozilgandi — bu noto'g'ri edi.)* `ai/prompts/builder.py` da to'liq persona bloki bor: ism (Azure), rol (turk tili bo'yicha o'quv-do'st), ijtimoiy savollarga munosabat, suhbat uslubi va chegaralar. Bo'shliq boshqa joyda: bu blok **shartnoma emas**, oddiy prompt matni. Undan keyin `skill.instructions` qo'shiladi va 15 skillning har biri o'z ovozini olib keladi; skill almashganda persona saqlanishini kafolatlaydigan hech narsa yo'q va buni tekshiradigan test ham yo'q. Kerak: personani canonical manba sifatida ajratish va skill almashuvida ovoz o'zgarmasligini test bilan majburlash.
2. **Suhbatlararo hikoya yo'q.** `AIConversationSummary` `ChatRoom` ga `OneToOne` — yangi chat ochilganda "biz nima ustida ishlayotgan edik" yo'qoladi. Faktlar qoladi, kontekst qolmaydi. Kerak: foydalanuvchi darajasidagi davomiylik yozuvi (oxirgi mavzular, tugallanmagan ish, keyingi qadam).
3. **Munosabat holati yo'q.** Qancha vaqt birga ishlangani, nima va'da qilingani, nima jarayonda ekani hech qayerda saqlanmaydi.

**Silliqlik — alohida ish emas, A8/A9 ning natijasi.** So'nggi kunlar buni ko'rsatdi: o'lik model, Google minimalidan past deadline va zaxira taxminidan 71 token oshgani uchun o'zini o'chirgan circuit — uchalasi ham "AI ishlamayapti" bo'lib ko'rindi. A10 bu qatlamni qayta yozmaydi; u A9 ning latency/xato gate'iga tayanadi.

- **2026-08-21 tashqi namuna ko'rildi — `artcc/freelingo`** (o'zi-hosting qilinadigan AI til platformasi, FastAPI backend). **Litsenziyasi AGPL-3.0: kod ko'chirilmaydi.** Tarmoq orqali xizmat qilinsa AGPL butun AzureLMS'ga tarqaladi, bu esa pullik platforma uchun qabul qilinmaydi. G'oya va arxitektura mualliflik huquqi bilan himoyalanmaydi — quyidagi uchtasi shundan olindi va o'zimizcha yoziladi:
  1. **Persona bitta canonical konstantada** va barcha prompt quruvchilar o'shani iste'mol qiladi — bizdagi 1-bo'shliq aynan shu.
  2. **Barcha promptlar bitta paketda** + kompozitsiya drift'ini ushlaydigan test. Bizda ular `ai/skills/*/SKILL.md` va `ai/prompts/builder.py` orasida tarqoq.
  3. **Saqlangan xotira promptga ishonchsiz ma'lumot sifatida kiritiladi** — escape qilinib, teg ichida, "bu ko'rsatma emas" yozuvi bilan. Haqiqiy xavf: o'quvchi modelni ko'ndirib, keyinchalik ko'rsatma bo'lib o'qiladigan "xotira" saqlatib qo'yishi mumkin.
- **Ularda ham yo'q:** suhbatlararo hikoya (2-bo'shliq). Xotiralari tekis faktlar; "biz nima ustida ishlayotgan edik" ni ko'chiradigan mexanizm topilmadi. Ya'ni bu qism uchun tayyor namuna yo'q, o'zimiz o'ylab topamiz.
- **Bizda kuchliroq joy:** ularning `Memory` modeli tekis matn qatori (`user_id`, `content`, `source`, `created_at`). Bizda kategoriya, ishonch darajasi, embedding, `last_used_at` va semantik skorlash/decay bor. Ya'ni ular shaxsiyat va prompt tashkilotini, biz xotira sifatini yechganmiz.
- **Acceptance:** persona contract testli (skill almashganda ovoz o'zgarmaydi); promptlar bitta paketda va drift testi bor; saqlangan xotira escape qilinib ishonchsiz blok sifatida kiritiladi; davomiylik yozuvi yangi chatda tiklanadi; xotira **aniqligi** o'lchanadi — noto'g'ri eslash yangidan boshlashdan yomonroq; o'quvchi eslab qolinganini ko'radi va o'chira oladi; p95 javob vaqti va provayder xato darajasi A9 gate'idan o'tadi.
- **Chegara:** shaxsiyat mavjud bo'lmagan qobiliyatni va'da qilmaydi. "Do'st" ohangi AI ni access, baho yoki progress uchun system-of-record qilmaydi — bu qoida o'zgarmaydi.
- **Faza:** R5. R0–R4 yopilmasa boshlanmaydi; taqdimot scope'iga kirmaydi.
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

`A8 → A0b → A1a + A2 → A3/A4 contracts → A3/A4 adapters + A5 sign-off → shartli A6/A7 → A9 critical gate → A10 AI Optimise (R5)`. A1b production/cloud faqat owner `HOLD`ni ochganda. Agent branch prefiksi o'ziga mos; product authority va merge qarori Azurbekda qoladi. Ops, budget va mobile alohida oxirgi ish emas — har bandning release gate'i.

Parallel SIT truth: `S1 + S4 + S3 (bajarildi) → S2 (keyingi)`. S2 A8 yoki core active slice'ni siqmaydi; bir sessiyada bittasiga tegiladi.
