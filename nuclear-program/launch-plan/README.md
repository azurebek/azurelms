# AzureLMS — 20-sentyabr taqdimot va readiness rejasi

**Maqsad:** 20-sentyabr 2026 — loyiha taqdimoti, boshqariladigan beta uchun dalil va production `GO/HOLD/NO-GO` qarori. **Joriy rebaseline:** 2026-08-14. Public production deploy bu sananing avtomatik natijasi emas.

> **Owner resurs qarori — 2026-08-14:** DigitalOcean kreditlari bekor qilingan. Production alohida qayta admission olmaguncha DigitalOcean App Platform, Serverless Inference, Managed DB/Valkey yoki Spaces ishlatilmaydi. Adapter kodi o'chirilmaydi, lekin dormant qoladi. Bu HOLD hozir env config va bo'sh credential bilan ta'minlangan; AI provider tanlovida hali code-level fail-closed policy yo'q, shuning uchun A8/A1a buni enforcement testiga aylantiradi. Local/pre-production profil `AI_CHAT_PROVIDER=gemini`, lokal DB/cache/storage va Telegram polling mode bilan ishlaydi. Gemini free-tier “bepul va cheksiz” emas — loyiha request/token budjetini tejaydigan hard guardrail qurmaguncha ommaviy AI rollout qilinmaydi.

**Model:** platforma mustaqil o'rgatuvchi SaaS emas — **Azurbekning jonli onlayn turk tili kursining operatsion tizimi**. Jonli dars Telegram video chatda qoladi; platforma enrollment, davomat, dars release, vazifa, quiz, mock, progress, AI yordamchi, muloqot va to'lov oqimlarini bitta haqiqatga bog'laydi.

Bu papka launch strategiyasi, scope, status va go/no-go qarorlarining yagona manbai. Runtime holati uchun canonical kod, migration, test va production evidence source of truth bo'lib qoladi.

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

## 2026-08-14 source-of-truth snapshot

| Yo'nalish | Joriy holat | Keyingi gate |
|---|---|---|
| Local runtime | `LOCAL BOOT VERIFIED`: SQLite, LocMem/in-memory, eager Celery, local media; DO credential/service yo'q; 2026-08-14 full suite 467/467 | Lokal rejimni remote xizmatga jim o'tkazmaslik testi; production gate alohida |
| AI provider | Gemini barcha oddiy chat, web grounding va embeddinglar uchun primary | `A8` free-tier budget mode; hozirgi 9-model/2-urinish zanjiri qisqarmaguncha scale yo'q |
| A0 security | A0a Telegram auth/webhook/inactive-staff qismi kodda | A0b private media, upload va WebSocket access recheck |
| A1 runtime/CI | `PLANNED`; `.github/workflows`, `.dockerignore`, readiness yo'q | Vendor-neutral local/CI gate; cloud deploy `HOLD` |
| A2 Control Center | Read-only foundation + brand va landing mutation surface'lari bor | Global flags, release/audit, worker heartbeat va AI budget stoplight |
| Telegram | F0–F9, outbox va Mini App foundation bor | Local polling QA; webhook/public deploy `HOLD` |
| Landing editor | Bosqich 1 + bo'lim navigatsiyasi bor | Repeatable ro'yxatlar faqat core gate'lardan keyin |
| SIT | S1, S3 va S4 kodda; S2 yo'q | `SITInquiry` lifecycle; real data gigiyenasi |

## Rebaseline ustuvorligi

1. **A8 — Gemini free-tier budget mode:** barcha Gemini call-pathlari hisoblanadi; cheap-model allowlist, request/token cap, one-fallback, idempotency va 429 cooldown ishlaydi.
2. **A0b + vendor-neutral A1:** private media/upload/access; `.dockerignore`, CI, readiness va restore proof. Cloud xizmati shart emas.
3. **A2 Control Center:** effective config, capability registry, flags/kill switches, event/audit ledger, health, AI quota va release gate.
4. **Canonical oqimlar + mobil oltin yo'l:** enrollment, lesson lifecycle, access, submission/review va notificationlar shared policy/state machine orqali; real qurilma parity.
5. **Learner Outcome Loop minimal:** poydevor gate'lari yashil bo'lsa uch evidence modeli, Daily Coach, bitta structured practice va Progress Proof.
6. **Production va monetizatsiya:** hosting/provider faqat yangi owner qarori, learning evidence, reliability va iqtisod gate'idan keyin.

Prompt-only `word_builder`, `conversation_partner`, yangi model picker, streak/PWA bezaklari va chuqur SRS avtomatikasi yuqoridagi qatlamlardan oldinga chiqmaydi.

## Status tili

**Queue qarori** bandning qachon ishlanishini bildiradi: `ADMIT` — joriy narvonga qabul qilingan; `NEXT` — faqat keyingi owner admissionidan so'ng; `HOLD` — owner ataylab scope'dan tashqarida ushlab turibdi; `CUT` — joriy taqdimot/release scope'idan chiqarilgan.

**Execution holati** esa quyidagilardan biri:

- `PLANNED` — scope va acceptance yozilgan;
- `IN PROGRESS` — owner/branch va test yo'li aniq;
- `EVIDENCE READY` — test, browser/production evidence va metric mavjud;
- `BLOCKED` — tashqi qaror yoki critical bog'liqlik yetishmaydi.

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
- 20-sentyabr taqdimoti local yoki vaqtinchalik xavfsiz tunnelda o'tishi mumkin; bunday demo **production GO** deb talqin qilinmaydi.

### NO-GO

- Routine operation uchun developer/DB intervention kerak.
- Payment, access, grade yoki progressda noto'g'ri state ehtimoli bor.
- Adapterlar bir learner uchun turli haqiqat ko'rsatadi.
- Reklama qilingan AI zanjiri reproduksiya qilinmaydi yoki evaldan o'tmagan.
- Restore, critical monitoring yoki kill switch isbotlanmagan.
- Gemini free-tier budjeti global darajada boshqarilmaydi yoki bitta request ko'p modelni aylanib kvotani yesa.

---

*Yaratilgan: 2026-07-11. 2026-07-22 kuni solo-owner control plane va outcome-first modeliga, 2026-08-14 kuni esa local-first, DigitalOcean-hold va Gemini free-tier budget rejimiga qayta bazalandi.*
