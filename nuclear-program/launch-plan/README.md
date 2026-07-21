# AzureLMS — Launch rejasi (2026-09-20)

**Maqsad:** 20-sentyabr 2026 — loyiha taqdimoti va boshqariladigan ishga tushirish. **Rebaseline:** 2026-07-22; 60 kun qoldi.

**Model:** platforma mustaqil o'rgatuvchi SaaS emas — **Azurbekning jonli onlayn turk tili kursining operatsion tizimi**. Jonli dars Telegram video chatda qoladi; platforma enrollment, davomat, dars release, vazifa, quiz, mock, progress, AI yordamchi, muloqot va to'lov oqimlarini bitta haqiqatga bog'laydi.

Bu papka launch strategiyasi, scope, status va go/no-go qarorlarining yagona manbai. Runtime holati uchun canonical kod, migration, test va production evidence source of truth bo'lib qoladi.

| # | Hujjat | Nima haqida |
|---|---|---|
| 01 | [Strategiya](01-strategiya.md) | Bozor, pozitsiyalash, solo-owner modeli, AI outcome tezisi va narx gate'i |
| 02 | [Yo'l xaritasi](02-yol-xarita.md) | 22-iyuldan launchgacha fazalar va majburiy exit kriteriylari |
| 03 | [Mahsulot backlog](03-mahsulot-backlog.md) | ADMIT / NEXT / CUT — canonical owner va qabul kriteriylari bilan |
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

## Launch tezisi

**Biznes:** asosiy auditoriya — magistratura uchun B1/B2 turk tili sertifikati oluvchi talabgor. AzureLMSning farqi ko'p feature emas, jonli kursning bir xil va tekshiriladigan sikli:

`qabul → to'lov → dars release → o'qish → mashq/vazifa → ustoz review → mock → progress isboti`

**AI:** Azure AI hozir course-grounded yordamchi beta. Uning premium qiymati chat, token yoki skill soni emas:

1. o'quvchining xatosini aniqlab, keyingi urinish natijasini yaxshilash; yoki
2. o'qituvchining review vaqtini kamaytirish.

Bu natijalardan kamida biri real cohortda o'lchanmaguncha AI kurs narxini oshirishning mustaqil asosi emas. “Speaking/pronunciation coach”, “adaptiv mastery” va “ustoz ishini avtomatik kamaytiradi” kabi claimlar faqat tegishli structured flow va eval gate'dan keyin ochiladi.

## Rebaseline ustuvorligi

1. **Stop-ship poydevor:** auth/webhook/private media/upload/access muammolari, broker fail-fast, Telegram outbox worker, `.dockerignore`, CI va restore.
2. **Azure Control Center:** effective config, capability registry, flags/kill switches, event/audit ledger, health, cost va release gate.
3. **Canonical oqimlar:** enrollment, lesson lifecycle, access, submission/review va notificationlar shared policy/state machine orqali.
4. **Mobil oltin yo'l:** student, teacher, checkout, lesson, messenger va exam oqimlarining 360px hamda real qurilmadagi parity'si.
5. **Learner Outcome Loop minimal:** uchta evidence modeli, Daily Coach, bitta structured practice va Progress Proof; Writing Revision/Teacher Inbox faqat quality gate va owner capacitydan keyingi pilot.
6. **Monetizatsiya:** faqat learning gain, teacher time, reliability va margin gate'lari o'tgach.

Prompt-only `word_builder`, `conversation_partner`, yangi model picker, streak/PWA bezaklari va chuqur SRS avtomatikasi yuqoridagi qatlamlardan oldinga chiqmaydi.

## Status tili

Har yirik band quyidagi holatlardan birida bo'ladi:

- `PLANNED` — scope va acceptance yozilgan;
- `IN PROGRESS` — owner/branch va test yo'li aniq;
- `EVIDENCE READY` — test, browser/production evidence va metric mavjud;
- `BLOCKED` — tashqi qaror yoki critical bog'liqlik yo'q;
- `CUT` — launch scope'dan chiqarilgan.

Sana o'tgani task tugaganini anglatmaydi. Exit kriteriydan o'tmagan faza yopilmaydi; keyingi faza scope'i qisqaradi.

## Launch go/no-go

### GO

- Azurbek core weekly flow'ni developer yoki DB aralashuvisiz bitta control plane'dan boshqara oladi.
- Payment/access/release/submission/review/mock holatlari canonical service orqali ishlaydi va adapterlar bir xil haqiqatni ko'rsatadi.
- Asosiy mobil va Telegram oqimlari real qurilmada o'tgan.
- Real cohort evidence, backup restore, monitoring va critical rollback tasdiqlangan.
- Demo va marketingdagi har claim fresh account bilan qayta ko'rsatilgan.
- Premium AI gate'i ochilsa: critical safety/access violation `0`, Turkish correctness `≥92%`, grounded support `≥95%`, structured flow success `≥98%`, text p95 `<8s`, incremental AI cost premium revenue'ning `≤25%`.

### CONDITIONAL GO

- Non-core AI, SRS, streak yoki vizual feature feature flag bilan yopiladi yoki `beta` deb belgilanadi.
- Core jonli kurs oqimi va fallback Telegram kanali buzilmagan.

### NO-GO

- Routine operation uchun developer/DB intervention kerak.
- Payment, access, grade yoki progressda noto'g'ri state ehtimoli bor.
- Adapterlar bir learner uchun turli haqiqat ko'rsatadi.
- Reklama qilingan AI zanjiri reproduksiya qilinmaydi yoki evaldan o'tmagan.
- Restore, critical monitoring yoki kill switch isbotlanmagan.

---

*Yaratilgan: 2026-07-11. 2026-07-22 kuni auditlardan keyin solo-owner control plane va outcome-first launch modeliga qayta bazalandi.*
