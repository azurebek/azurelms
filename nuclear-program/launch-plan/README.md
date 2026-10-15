# AzureLMS — 30-sentyabr ishga tushirish va readiness rejasi

> **Joriy holat uchun:** [loyiha holati va hujjatlar xaritasi](../README.md).
> Bu papka ownerning launch strategiyasi va qabul mezonlarini saqlaydi.
> 2026-09-10 rebaseline va 30-sentyabr sanasi tarixiy reja; yangi muddat yoki
> launch qabuli sifatida talqin qilinmaydi. Kod, oxirgi deploy dalili va owner
> qabuli alohida holatlardir.

**Ownerning 2026-09-10 dagi maqsadi:** 30-sentyabr 2026 — 50 kishigacha bo'lgan boshqariladigan jonli guruhni Classbook oqimida ishga tushirish, beta dalilini yig'ish va production `GO/HOLD/NO-GO` qarori. Public production deploy bu sananing avtomatik natijasi emas; yangi launch sanasi bu hujjat bilan belgilanmaydi.

> **Owner rebaseline — 2026-09-10:** oldingi 20-sentyabr taqdimot checkpointi 30-sentyabr ishga tushirish maqsadiga uzaytirildi. `A3b Classbook` launch-critical scope'ga qabul qilindi: o'qituvchi bitta `Darsni boshlash` amali bilan davomat/material oqimini ochadi, turli mashqlarni jonli boshqaradi, 50 learner natijasi avtomatik baholanadi va reytingga tushadi; yakunlash attendance, access, homework va shaxsiy Telegram natijalarini bitta canonical oqimda yopadi. Hosting/provider admissioni bundan alohida gate bo'lib qoladi.

> **Owner resurs qarori — 2026-08-14:** DigitalOcean kreditlari bekor qilingan. Production alohida qayta admission olmaguncha DigitalOcean App Platform, Serverless Inference, Managed DB/Valkey yoki Spaces ishlatilmaydi. Adapter kodi o'chirilmaydi, lekin dormant qoladi. Provider factory `AI_ALLOW_DIGITALOCEAN=False` defaulti bilan DO'ni provider yaratilishidan oldin, noma'lum providerlarni esa doim fail-closed rad etadi. Local/pre-production profil `AI_CHAT_PROVIDER=gemini`, lokal DB/cache/storage va Telegram polling mode bilan ishlaydi. Gemini free-tier “bepul va cheksiz” emas; A8 hard guardi implement/test qilingan, real DB contention va production admission evidence tugamaguncha ommaviy AI rollout ochilmaydi.

**Model:** platforma mustaqil o'rgatuvchi SaaS emas — **Azurbekning jonli onlayn turk tili kursining operatsion tizimi**. Jonli dars Telegram video chatda qoladi; platforma enrollment, davomat, dars release, vazifa, quiz, mock, progress, AI yordamchi, muloqot va to'lov oqimlarini bitta haqiqatga bog'laydi.

Bu papka launch strategiyasi, scope va go/no-go mezonlarini saqlaydi. Joriy bajarilish holati uchun yuqoridagi yagona holat sahifasi, tafsilot uchun canonical kod, migration, test va sanalangan release dalili o'qiladi.

| # | Hujjat | Nima haqida |
|---|---|---|
| 01 | [Strategiya](01-strategiya.md) | Bozor, pozitsiyalash, solo-owner modeli, AI outcome tezisi va narx gate'i |
| 02 | [Yo'l xaritasi](02-yol-xarita.md) | 14-avgust rebaseline'idan taqdimotgacha exit-gated ish tartibi |
| 03 | [Mahsulot backlog](03-mahsulot-backlog.md) | ADMIT / NEXT / HOLD / CUT queue'i — canonical owner va qabul kriteriylari bilan |
| 04 | [Kontent reja](04-kontent-reja.md) | Video darslar, milliy sertifikat mocklari, test banki va ko'prik kontenti |
| 05 | [Launch operatsiyalari](05-launch-ops.md) | Deploy, security, Control Center, CI, QA, beta va launch protokoli |

---

## Operating doctrine — bir owner, bir control plane

```text
APEX: sertifikatga tayyorlik + owner nazorati
  LEARNER OUTCOME LOOP: Diagnose → Plan → Practice → Proof → Escalate
    CONTROL PLANE: canonical services · policy · state · audit · release gate
      ADAPTERLAR: Web · Telegram · Mini App · Messenger · Celery · AI providers
```

- Azurbek product, curriculum, pricing va go/no-go qarorining yagona egasi. Agentlar parallel ishlashi mumkin, ammo parallel authority yaratmaydi.
- Web, Telegram, Mini App va AI alohida mahsulot holati yoki biznes qoidasi yaratmaydi; canonical service'ni chaqiradi.
- “Bitta markaz” mega-file emas. Modullar alohida qoladi, lekin policy, health, quality, cost, feature flags va release holati **Azure Control Center**da tutashadi.
- Daily Coach, structured practice, Writing Studio, Teacher Inbox va Progress Proof mustaqil tarqoq mahsulotlar emas; bitta Learner Outcome Loop capability'lari.
- Pastki qatlam learner outcome yoki owner workloadni yaxshilamasa, launch scope'ga kirmaydi.
- Hosting va AI provider — adapter qarori. DigitalOcean'ni vaqtincha ishlatmaslik canonical domain yoki mahsulot oqimlarini o'zgartirmaydi.

## Launch tezisi

**Biznes:** asosiy auditoriya — magistratura uchun B1/B2 turk tili sertifikati oluvchi talabgor. AzureLMSning farqi ko'p feature emas, jonli kursning bir xil va tekshiriladigan sikli:

`qabul → to'lov → dars release → o'qish → mashq/vazifa → ustoz review → mock → progress isboti`

**AI:** Azure AI hozir course-grounded yordamchi beta. Uning premium qiymati chat, token yoki skill soni emas:

1. o'quvchining xatosini aniqlab, keyingi urinish natijasini yaxshilash; yoki
2. o'qituvchining review vaqtini kamaytirish.

Bu natijalardan kamida biri real cohortda o'lchanmaguncha AI kurs narxini oshirishning mustaqil asosi emas. “Speaking/pronunciation coach”, “adaptiv mastery” va “ustoz ishini avtomatik kamaytiradi” kabi claimlar faqat tegishli structured flow va eval gate'dan keyin ochiladi.

## Holat izohi — 2026-10-13 repo dalili

Quyidagi jadval oldingi 2026-09-10 snapshotidagi eskirgan statuslarni
aniqlashtiradi. AWS bo'yicha oxirgi qayd — [2026-09-26 R2 relizi](../frontend-v1/R2-READY-V1-AWS.md),
`8bb6b95`, 19 ta V1 renderer flagi ON. Bu sessiyada server qayta tekshirilmagan;
shu SHA yoki konfiguratsiya hozir ham jonli degan yangi da'vo yo'q.

| Yo'nalish | Joriy holat | Keyingi gate |
|---|---|---|
| Local runtime | Lokal ish profili va test dalillari mavjud; yangi backoffice oqimlari [B2.6](../frontend-v1/BACKOFFICE-02-STAGE-6.md) da tekshirilgan | Test soni va aniq buyruq sanalangan dalilda; lokal PASS production qabuli emas |
| AI provider | Gemini primary; allowlistdagi 1 primary + max 1 fallback, SDK retry off, `429`da 1 attempt/cooldown | `A8` **`IMPLEMENTED/TESTED — LOCAL REGRESSION GREEN`**; PostgreSQL contention proofi CI'da yopildi, production admission alohida |
| A0 security | A0a **va** A0b beshala slice kodda: teacher default-deny scope, upload MIME/magic-byte gate'i, private media, WebSocket access recheck, CSP v4 | `EVIDENCE READY` labeli owner qarorida |
| A1 runtime/CI | A1a kodda; AWS texnik rollout, isolated restore va real-server smoke R2 dalilida qayd etilgan | R2 dagi SMTP, worker/beat heartbeat, offsite backup/secret rotation va real provider chegaralari ochiq; yangi kod avtomatik deploy bo'lmaydi |
| A2 Control Center | Capability registry, audit, flags, heartbeat, release yozuvi va cost/probe poydevori kodda | A9 bilan birga eski `AISettingsAdmin` va `backoffice_ai_control` sozlama yozishlarining sabab/tasdiq/`SystemAuditEvent` qarzi ham ochiq; A2 to'liq yopilmagan |
| Telegram | Outbox process, retry/dead-letter va Mini App kodi mavjud; R2 outbox processi running bo'lganini qayd etadi | Real Telegram yetkazish, webhook va WebView qabuli R2 smoke bilan tasdiqlanmagan |
| Classbook | `main`da (PR #94, 2026-09-10): canonical session/activity/response, 10 mashq turi, realtime+poll fallback va Telegram group outbox `IMPLEMENTED/TESTED — LOCAL REGRESSION GREEN`. PostgreSQL 50-parallel gate yopildi — `classbook/test_load.py` CI `integration` ishida yashil | Real Telegram guruh / Mini App va Android/iOS/desktop owner sign-off |
| Landing editor | Bosqich 1 + bo'lim navigatsiyasi bor | Repeatable ro'yxatlar faqat core gate'lardan keyin |
| SIT | S1/S4 implemented foundation; S3 local foundation, public entry mavjud va release blockerlar ochiq; S2 yo‘q | [SIT-01](../frontend-v1/SIT-REFORM-PLAN.md): avval containment/filter/source/version, keyin canonical `SITInquiry`, public decision tools va A9-gated advisor |
| Backoffice | BACKOFFICE-01 va B2.1–B2.6 lokal implementatsiya/tekshiruvlari tugagan; [B2.6 yakuni](../frontend-v1/BACKOFFICE-02-STAGE-6.md) | Owner qabuli keyinga qoldirilgan; native telefon/zoom/AT va yangi AWS rollout alohida |

## Owner rebaseline ustuvorligi — 2026-09-10 tarixiy tartib

Quyidagi ustuvorliklar ownerning o'sha qarorini saqlaydi; ayni paytda qaysi
ish bajarilgani yuqoridagi holat manbasidan olinadi.

1. **A3b Classbook closeout:** bitta start/finish control plane, turli deterministic mashqlar, 50 learner grading/leaderboard, Telegram guruh outbox va shaxsiy natija DM'lari. Merge gate: full suite, PostgreSQL parallel test, mobile browser va real Telegram owner sign-off.
2. **A8 closeout — `IMPLEMENTED/TESTED — LOCAL REGRESSION GREEN`:** barcha joriy Gemini call-pathlari ledgerga ulangan; free-model allowlist, kunlik/minute request va kunlik token cap, one-fallback, idempotency va 429 cooldown ishlaydi. Ikki DB backenddagi contention proofi **yopildi** — SQLite yarmi `aicontrol/test_supply_concurrency.py` bilan, PostgreSQL yarmi CI `integration` ishi bilan. 2026-09-10 dagi tarixiy suite dalili: `main` (`da07d0c`), 1411 test (skipped=30). Guest/SmartForm/lesson-reindex aniqlashtirishlari va qolgan alohida OS-process sinovi [K11 reestrida](02-yol-xarita.md#risk-reestri).
3. **A0b + vendor-neutral A1:** private media/upload/access; `.dockerignore`, CI, readiness va restore proof. Cloud xizmati shart emas.
4. **A2 Control Center:** effective config, capability registry, flags/kill switches, event/audit ledger, health, AI quota va release gate.
5. **Canonical oqimlar + mobil oltin yo'l:** enrollment, lesson lifecycle, access, submission/review va notificationlar shared policy/state machine orqali; real qurilma parity.
6. **Learner Outcome Loop minimal:** poydevor gate'lari yashil bo'lsa uch evidence modeli, Daily Coach, bitta structured practice va Progress Proof.
7. **A10 AI Optimise (R5, owner admission 2026-08-19):** AzureAI har suhbatda notanish yordamchi bo'lib qaytmaydi — canonical persona contract, suhbatlararo davomiylik va o'lchangan xotira aniqligi. Poydevor bor (`ai/memory/`, foydalanuvchi bo'yicha `AIMemoryFact`); bo'shliq — persona (`ai/prompts/builder.py` da yozilgan) shartnoma emasligi va `AIConversationSummary` ning xonaga bog'langani. Taqdimot scope'ida emas, lekin loyiha usiz yakunlanmaydi.
8. **Production va monetizatsiya:** hosting/provider faqat yangi owner qarori, learning evidence, reliability va iqtisod gate'idan keyin.

Prompt-only `word_builder`, `conversation_partner`, yangi model picker, streak/PWA bezaklari va chuqur SRS avtomatikasi yuqoridagi qatlamlardan oldinga chiqmaydi.

**A8 model lifecycle (2026-08-19):** primary `gemini-3.1-flash-lite`; vaqtinchalik fallback endi `gemini-3.5-flash-lite`. **`gemini-2.5-flash-lite` o'lik** — Google `404 ... no longer available to new users` qaytaradi, ya'ni 2026-10-16 review deadline'i voqea tomonidan bosib o'tildi; model `RETIRED_MODELS` da. `models.list` uni hamon ro'yxatda ko'rsatgani uchun haqiqat faqat real `generateContent` probe'ida ochildi. 2026-08-14 `AzureAI` Free-tier snapshotida 3.1 Lite `15 RPM / 250K TPM / 500 RPD`, 3.7 Flash `5 RPM / 250K TPM / 20 RPD`; shu sabab 3.7 hozir admit qilinmagan. External quota dynamic/account-specific, Control Center budgetlari esa loyiha ichki hard guardlari.

## Status tili

**Queue qarori** bandning qachon ishlanishini bildiradi: `ADMIT` — joriy narvonga qabul qilingan; `NEXT` — faqat keyingi owner admissionidan so'ng; `HOLD` — owner ataylab scope'dan tashqarida ushlab turibdi; `CUT` — joriy taqdimot/release scope'idan chiqarilgan.

**Execution holati** esa quyidagilardan biri:

- `PLANNED` — scope va acceptance yozilgan;
- `IN PROGRESS` — owner/branch va test yo'li aniq;
- `EVIDENCE READY` — test, browser/production evidence va metric mavjud;
- `BLOCKED` — tashqi qaror yoki critical bog'liqlik yetishmaydi.
- `IMPLEMENTED/TESTED — LOCAL REGRESSION GREEN` — kod, targeted offline testlar va post-change local full suite yashil; real-device/production yoki concurrency evidence tugamagani uchun bu hali `EVIDENCE READY` yoki production `GO` emas.

Sana o'tgani task tugaganini anglatmaydi. Exit kriteriydan o'tmagan faza yopilmaydi; keyingi faza scope'i qisqaradi.

## Launch go/no-go

### GO

- Azurbek core weekly flow'ni developer yoki DB aralashuvisiz bitta control plane'dan boshqara oladi.
- Payment/access/release/submission/review/mock holatlari canonical service orqali ishlaydi va adapterlar bir xil haqiqatni ko'rsatadi.
- Asosiy mobil va Telegram oqimlari real qurilmada o'tgan.
- Real cohort evidence, backup restore, monitoring va critical rollback tasdiqlangan.
- Demo va marketingdagi har claim fresh account bilan qayta ko'rsatilgan.
- Premium AI gate'i ochilsa: critical safety/access violation `0`, Turkish correctness `≥92%`, grounded support `≥95%`, structured flow success `≥98%`, text p95 `<8s`, incremental AI cost premium revenue'ning `≤25%`.
- Public production uchun hosting/provider qayta admissioni, secret rotation, remote backup/restore va production-like smoke alohida o'tgan.

### CONDITIONAL GO

- Non-core AI, SRS, streak yoki vizual feature feature flag bilan yopiladi yoki `beta` deb belgilanadi.
- Core jonli kurs oqimi va fallback Telegram kanali buzilmagan.
- Taqdimot/ishga tushirish checkpointi (2026-09-10 rebaseline bo'yicha 30-sentyabr) local yoki vaqtinchalik xavfsiz tunnelda o'tishi mumkin; bunday demo **production GO** deb talqin qilinmaydi.

### NO-GO

- Routine operation uchun developer/DB intervention kerak.
- Payment, access, grade yoki progressda noto'g'ri state ehtimoli bor.
- Adapterlar bir learner uchun turli haqiqat ko'rsatadi.
- Reklama qilingan AI zanjiri reproduksiya qilinmaydi yoki evaldan o'tmagan.
- Restore, critical monitoring yoki kill switch isbotlanmagan.
- Gemini free-tier budjeti global darajada boshqarilmaydi yoki bitta request ko'p modelni aylanib kvotani yesa.

---

*Yaratilgan: 2026-07-11. 2026-07-22 kuni solo-owner control plane va outcome-first modeliga, 2026-08-14 kuni esa local-first, DigitalOcean-hold va Gemini free-tier budget rejimiga qayta bazalandi.*
