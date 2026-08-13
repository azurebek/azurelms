# 01 — Strategiya: bozor, pozitsiyalash, farqlash

*2026-07-11 da jonli kurs modeli aniqlandi. 2026-07-22 audit rebaseline'i solo-owner control plane, Learner Outcome Loop va AI evidence gate'ini qo'shdi. 2026-08-14 rebaseline'i local-first ish rejimi, DigitalOcean `HOLD` va Gemini free-tier supply gate'ini belgiladi. Manbalar hujjat oxirida.*

---

## 0. Model — hamma narsadan avval

**Bu SaaS-o'zi-o'rganish ilovasi emas.** Azurbek yillardir onlayn turk tili kursi o'tadi: darslar **Telegram video chatda jonli** o'tiladi va shunday davom etadi. Platformaning vazifasi — shu kursni professional infratuzilma bilan o'rash:

| Kurs elementi | Hozir (platformasiz o'qituvchilar) | AzureLMS bilan |
|---|---|---|
| Jonli dars | Telegram video chat | O'zgarmaydi (bu yadro qadriyat) |
| Dars materiali | PDF/rasm guruhga tashlanadi | Yozilgan sifatli video dars + konspekt + lug'at — **jonli dars o'tilgach avtomatik ochiladi** (drip) |
| Davomat | Qo'lda ro'yxat | Telegram bot check-in (qurilgan!) → platforma jurnali |
| Uyga vazifa | Guruhga yuboriladi, tekshiruv tartibsiz | Assignment tizimi: topshirish → o'qituvchi/AI tekshiruvi → status/XP |
| Bilim nazorati | Ahyon-ahyon test | Har dars quiz + modul testlari + **milliy sertifikat formatidagi mock imtihonlar** |
| Motivatsiya | — | Reyting (leaderboard), streak, XP, badge, sertifikat |
| Savollar | O'qituvchiga yoziladi (kechikadi) | **Azure AI 24/7** — darslar orasidagi yordamchi; o'qituvchi dam oladi |
| Yangi o'quvchi oqimi | Og'zaki tavsiya | Landing + daraja testi + blog + Telegram kontent → kursga yozilish |

Bir jumlada: **o'qituvchi o'rgatadi, platforma tizim beradi, AI oradagi bo'shliqni to'ldiradi.**

### 0.1 Operatsion model — yakka owner, bitta markaz

Azurbek bitta ustoz va bitta product owner. Platforma uning ishini ko'paytiradigan ko'p kanal emas, bitta control plane atrofidagi adapterlar tizimi. Web, Telegram, Mini App, Messenger va AI alohida enrollment, release, submission, review yoki progress qoidasi yaratmaydi; bir xil canonical service va state'ni ko'rsatadi.

```text
Azure Control Center
  policy · health · quality · cost · release
    Diagnose → Plan → Practice → Proof → Escalate
      canonical domain services + state machines
        Web · Telegram · Mini App · Messenger · Celery · AI providers
```

Yangi capability learner outcome yoki owner vaqtiga bitta o'lchanadigan ta'sir ko'rsatmasa, canonical owner'i va kill switch'i bo'lmasa, launch scope'ga kirmaydi. Bitta markaz mega-view yoki mega-service emas: modullar mustaqil, boshqaruv va haqiqat esa yagona.

### 0.2 Resurs siyosati — local-first, provider adapter

- Production alohida owner qarorigacha DigitalOcean ishlatilmaydi; bekor bo'lgan kreditlar mahsulot arxitekturasi yoki fallback va'dasiga aylantirilmaydi.
- DO adapter kodi dormant qoladi. Hosting, DB, cache, storage va inference provider production qayta admissionida vendor-neutral gate bo'yicha tanlanadi.
- Joriy local/pre-production AI primary — Gemini. Demak oddiy chat, web grounding va embedding ham free-tier supply'ni ishlatadi.
- Free-tier `0 so'm = unlimited` emas. Global request/token budget, model allowlist, one-fallback, full accounting va 429 circuit breaker bo'lmaguncha AI scale/premium claim yo'q.
- AI kvotasi tugasa deterministic kurs, payment, lesson, quiz/assignment, human messenger va Telegram flow ishlashda qoladi.

---

## 1. Bozor va foydalanuvchi

### 1.1 Asosiy talab drayveri — magistratura sertifikat majburiyati (rasmiy faktlar)

2024-yil 24-maydagi PF-81 Farmoni ijrosida Oliy ta'lim, fan va innovatsiyalar vazirining 211-son buyrug'i (2024): **2024/2025 o'quv yilidan magistratura va oliy ta'limdan keyingi ta'limga hujjat topshirishda chet tilini bilish sertifikati majburiy**:

| Yo'nalishlar guruhi | Talab daraja |
|---|---|
| Xorijiy tillar yo'nalishlari (filologiya, tarjima, lingvistika...) | **C1*** |
| Gumanitar, biologiya, matematika/statistika, biznes/boshqaruv, huquq, xizmatlar, ijtimoiy fanlar, jurnalistika, AKT | **B2** |
| Boshqa barcha sohalar (muhandislik, tibbiyot, qishloq xo'jaligi, san'at, sport...) | **B1** |

**\* Hal qiluvchi izoh (buyruqning o'zida):** *"O'zbek, rus va qardosh tillar bo'yicha B2 daraja talab etiladi"* — ya'ni turkcha (qardosh til) bilan **hatto C1-yo'nalishlarga ham B2 yetadi**. Turk tili uchun shift maksimal talab — B2. *(Talqinni marketingda ishlatishdan oldin rasmiy manba bilan qayta tasdiqlash publish gate'i.)*

Doktorantura (2-ilova): ixtisosliklar bo'yicha B1/B2.

### 1.2 Nega talabgorlar turkchani tanlaydi (Azurbek kursining isbotlangan tezisi)

Sertifikat **istalgan tan olingan chet tilidan** bo'lishi mumkin — daraja yo'nalishga bog'liq, til emas. Demak ratsional talabgor eng tez olinadigan tilni tanlaydi:
- Ingliz B2 (IELTS 5.5–6.5 ekvivalenti) — o'rtacha o'zbek uchun 1.5–3 yil mehnat
- **Turkcha B2 — qardosh til: bir necha oyda erishiladigan real maqsad** (agglyutinatsiya, SOV, egalik/kelishik parallellari, ulkan umumiy leksika)

Bozor hajmi o'lchangan: **UZBMB turk tili milliy sertifikat imtihonining bitta yozma kunida 5200+ topshiruvchi** (2025-03-02); imtihonlar yiliga bir necha marta, viloyatlarda + Toshkentda. 2025'dan ko'p darajali format (A1–C2): yozma kun (tinglash+o'qish+yozish) + og'zaki alohida kunlarda. Platformada to'rt ko'nikma uchun asosiy komponentlar bor; UZBMB format parity'si, content bank va real browser/device evidence hali gate'dan o'tishi kerak.

### 1.3 Segmentlar

| # | Segment | Ulush | Xususiyat |
|---|---|---|---|
| S1 | **Magistratura talabgori** (sertifikat B1/B2 kerak) | ~99% (Azurbek kursining real statistikasi) | Muddat bosimi (qabul mavsumi), natijaga to'laydi, "imtihondan o'tish" — yagona mezon |
| S2 | Doktorantura/ilmiy xodim | kichik | Xuddi shu ehtiyoj, kattaroq yosh, pul bor |
| S3 | Turkiyaga yo'l (grant/ish/o'qish), serial ixlosmandlari | kichik, o'sadigan | Freemium + kontent orqali o'zi keladi; post-launch fokus |

**Launch fokusi: S1.** Hamma xabar, kontent va mock imtihon S1 tiliga gapiradi: *"Magistraturaga sertifikat kerakmi? Turkcha — eng qisqa yo'l. Biz shu yo'lning o'zimiz."*

**SIT va S3 (2026-07-28 owner qarori).** Study in Turkey portali (`03-mahsulot-backlog.md` → `S`) S3 segmentiga to'g'ridan-to'g'ri kirish eshigi ochadi va uni "post-launch fokus"dan hozirgi ishga ko'chiradi. Ikki tomonlama bog'lanish: SIT tashqi trafikni olib keladi (universitet qidiruvi), til tayyorlov narxi esa AzureLMS kursiga tabiiy o'tish beradi. **Launch fokusi baribir S1 bo'lib qoladi** — SIT S1 xabarini almashtirmaydi, yonida turadi.

*Ochiq owner savoli (3.4 bilan bog'liq):* SIT yordam xizmati bizni "ta'lim agentligi" qiladimi yoki biz kurs bo'lib qolib, yordamni yondosh xizmat sifatida beramizmi? Pozitsiya bayonoti va "nima biz EMASMIZ" ro'yxati shu javobdan keyin yangilanadi.

### 1.4 Mavsumiylik (rejaga ta'siri)

Magistratura qabuli yozda; sertifikat imtihonlari yil davomida. **Sentyabr = yangi tayyorgarlik mavsumining boshi** — kuzda boshlagan 2027-yil yozgi qabulga bemalol ulguradi. "20-sentyabr taqdimot + kuzgi guruh" mavsum bilan mos. Marketing kalendari UZBMB imtihon sanalariga bog'lanadi; 2026–2027 rasmiy taqvim publishdan oldin qayta tekshiriladi.

---

## 2. Raqobat tahlili

Haqiqiy raqobat maydoni o'zgardi (model aniqlangach): biz "app bozori"da emas, **"turk tili kursi bozori"**damiz.

| Raqib | Kuchi | Zaifligi (bizning ustunlik) |
|---|---|---|
| **Boshqa onlayn turk tili o'qituvchilari** (asosiy raqib!) — Telegram guruh + jonli dars + PDF | Jonli ustoz, arzon, shaxsiy munosabat | Infratuzilma nol: davomat/vazifa qo'lda, video arxiv tartibsiz, mock imtihon yo'q, o'quvchi progressi ko'rinmaydi, savollar javobsiz qoladi. **Platformamiz — ko'chirib bo'lmaydigan farq** |
| **Oflayn markazlar** (Toshkent va viloyatlar) | Ishonch, jonli muhit | Qimmat, jadvalga bog'liq, viloyat qamrovi yo'q, texnologiya nol |
| **UZBMB'ga "o'zi tayyorlanuvchi"lar** (YouTube+kitob) | Bepul | Tizimsiz, feedback yo'q, mock yo'q — bular bizning freemium-auditoriyamiz |
| Duolingo / global applar | Brend, gamifikatsiya | O'zbek bazasi yo'q (tekshirildi), milliy sertifikatni bilmaydi, jonli ustoz yo'q |
| Yunus Emre kurslari/portali | Rasmiylik | O'zbekcha emas, milliy sertifikatga tayyorlamaydi; TYS bo'yicha hamkor-potentsial |

**Maqsadli himoya qatlamlari (moat):** `MAVJUD` — Azurbekning curriculum'i/teacher judgment'i va Ko'prik metodikasi; `QURILMOQDA` — milliy sertifikat kontent banki va canonical teacher workflow; `PLANNED/EVIDENCE REQUIRED` — learner attempt/mastery evidence, o'zbek–turk misconception taxonomy, o'lchangan cohort outcome va teacher efficiency. Kod, model nomi yoki AI personaning o'zi moat emas.

---

## 3. Pozitsiyalash

### 3.1 Pozitsiya bayonoti

> **AzureLMS — magistraturaga sertifikat yo'lidagi eng mustahkam tizim:** Azurbek ustozning jonli kursi + har darsga video/vazifa/test + milliy sertifikat formatidagi mock imtihonlar + seni eslab qoladigan Azure AI yordamchi. Turkcha — eng qisqa yo'l; biz shu yo'lning xaritasi, hamrohi va mashqxonasimiz.

### 3.2 Xabar piramidasi (auditoriyaga qarab)

1. **S1 talabgorga (asosiy):** "Magistratura uchun sertifikat kerakmi? Turkcha uchun boshlang'ich darajangiz, davomat va practice'ingizga mos aniq reja oling. Jonli darslar + tizimli platforma + AI yordamchi." Muddat claim'i beta cohort taqsimoti va aniq shartlar bilan o'lchangandan keyin qo'shiladi.
2. **Ota-ona/homiy:** "Farzandingiz qayerda, qachon, qancha o'qigani — hammasi ko'rinadi: davomat, baho, progress."
3. **Keng auditoriya (kontent):** "Turkchaning yarmini allaqachon bilasan" — ko'prik postlari qiziqish uyg'otadi → daraja testi → kurs.

### 3.3 Slogan nomzodlari (owner pre-freeze tanlovi)

1. **"Sertifikatgacha — bitta tizim"** (S1 og'rig'iga to'g'ridan)
2. **"Jonli ustoz. Aqlli platforma. Aniq natija."** (gibrid model)
3. **"Turkcha — eng qisqa yo'l. Biz — yo'l xaritasi."**
4. "Sen allaqachon yarmini bilasan" (keng auditoriya kontenti uchun qoladi)

### 3.4 Nima biz EMASMIZ

- "Yana bir mobil app" emas — biz kurs; app-lar sertifikat bermaydi.
- Repetitor-marketplace emas — bitta ustoz, bitta tizim, bitta natija.
- Hamma tillar markazi emas — **faqat turkcha, faqat o'zbeklar uchun** (torlik = o'tkirlik).

---

## 4. Yetti imzo-harakat — "nima qilsak o'zgacha bo'lamiz"

### ⭐ IH-1. Jonli-kurs infratuzilmasi — "boshqa hech bir ustozda yo'q"

**Nima:** o'qituvchining kun-oqimi bir tugmada: jonli dars tugadi → bot davomatni yozdi → video dars kohortga ochildi (CohortLessonRelease — qurilgan!) → vazifa aktivlashdi → o'quvchilarga Telegram xabar ketdi. O'quvchi tomonida: jurnal, progress, reyting, keyingi dars qachonligi.

**Nega kuchli:** asosiy raqib (Telegram-guruh o'qituvchilari) uchun bu yetib bo'lmas tizim; o'quvchi/ota-ona uchun "jiddiy kurs" signali. **Bu launch'ning yadro va'dasi.**

**Holat:** bloklar qurilgan (bot davomat, release, assignment, leaderboard) — ularni alohida state graphlar va bitta owner flow'iga bog'lash kerak (`03-backlog` A3 Live Lesson Orchestrator).

### ⭐ IH-2. Azure AI — course-grounded yordamchidan natija loop'iga

**Launch capability (mavjud primitive'lar):** kurs/dars kontekstiga tayangan matn savol-javobi, PDF matn tahlili, draftga izoh, conversation history/memory va texnik telemetry. `image_qa` routing primitive'i bor, ammo joriy Gemini adapteri `supports_vision=False`; rasmni haqiqiy ko'rish vision provider admissionigacha capability deb sotilmaydi. Yordamchi o'qituvchini almashtirmaydi va high-stakes bahoni mustaqil tasdiqlamaydi.

**Premium outcome gate (qurilishi va isbotlanishi kerak):** item-level xato evidence → keyingi structured practice → qayta urinishdagi o'sish → Progress Proof → past confidence yoki takroriy xatoni ustozga eskalatsiya. Writing'da revision history va teacher approval; speaking'da esa real audio pipeline bo'lmasa “pronunciation coach” claim'i yo'q.

**Nega kuchli bo'lishi mumkin:** AI 24/7 chat bo'lgani uchun emas, learner correction rate'ni oshirsa yoki ustozning review vaqtini kamaytirsa. Har ikkisi real cohort KPI va eval bilan o'lchanadi.

**Holat:** RAG/memory/chat, document flow va SIT advisor primitive'lari bor; image routing bor, lekin joriy providerda vision yo'q. Local primary Gemini; eski “maverick asosiy, Gemini faqat web search” arxitekturasi joriy envga mos emas. Structured mastery, stateful practice, teacher review, hard deadline va `A8/A9` supply-quality gate hali `PLANNED`. AI narx oshirishning mustaqil asosi emas.

### ⭐ IH-3. Milliy sertifikat mock-markazi (S1'ning yuragi)

**Nima:** UZBMB turk tili imtihoni formatida mock: yozma kun (tinglash — replay-limit bilan, o'qish — 8 task turi, yozish — so'z chegarasi + per-esse feedback) + og'zaki (audio yozish + ustoz baholashi). Mock natijasi canonical learning evidence'ga aylangachgina objective/mastery va keyingi practice'ga ulanadi; validatsiyalanmagan “B2 — 68%” marketing qilinmaydi.

**Nega kuchli:** S1 uchun asosiy savol "imtihonga qanchalik tayyorman?" — formatga mos, kalibrlangan mock bunga evidence beradi. Bepul mock kuchli lead-magnit bo'lishi mumkin, lekin faqat exam/mobile QA va content review'dan keyin.

**Holat:** tinglash/o'qish/yozish/speaking review komponentlari mavjud; UZBMB spetsifikatsiyasi parity'si, 2 mock kontenti, private audio va JS real browser/device sinovi `PLANNED`.

### ⭐ IH-4. Telegram-native ritm (darslar allaqachon shu yerda)

**Nima:** darslar Telegramda o'tilgani uchun butun ritm shu yerda: "bugun 20:00 jonli dars" eslatma, dars ochildi xabari, vazifa muddati, streak, kunlik ko'prik, haftalik hisobot — hammasi bot orqali, deep-link platformaga.

**Nega kuchli:** O'zbekiston Telegram mamlakati (76–88% qamrov); auditoriyani yangi kanalga ko'chirish shart emas — mavjud odatga qo'shilamiz.

**Holat:** F0–F9 main'da: onboarding, checkout, attendance, learner workspace/AI, admin-AI controls, outbox, Mini App foundation, botda dars, assignment va quiz bor. Public webhook/outbox process, to'liq exam/certificate, interactive grading/reminder va production WebView hali yo'q; production `HOLD`.

### ⭐ IH-5. Daraja testi — kirish eshigi

**Nima:** "Darajangni 10 daqiqada aniqla" — anonim test, natija: daraja + "turkchaning X%i senga tanish" + **"sen B2 gacha ~N oyda yetasan — kuzgi guruh N-sentyabrda boshlanadi"** (kursga to'g'ridan-to'g'ri ko'prik). Ulashiladigan natija kartasi.

**Nega kuchli:** kurs uchun lead-mashina (hozirgi og'zaki-tavsiya oqimini tizimlashtiradi) + viral halqa. Sertifikat konteksti bilan yanada o'tkir: "darajang B1 — imtihonga shu-shu yetishmayapti".

**Holat:** `NEXT`. Quiz/SmartForm primitive'lari bor, lekin kalibrlangan placement banki va halol result formula kodda yo'q; A0–A5 gate'laridan oldinga chiqmaydi.

### ⭐ IH-6. Ko'prik metodikasi — kontent imzosi

**Nima:** "sen allaqachon yarmini bilasan" — tovush ko'priklari (b↔v: bor=var), morfologiya parallellari (uy-im=ev-im); dars materiallari shu tilda gapiradi. AI `word_builder` keyinchalik approved morphology dataset va structured PracticeMode ustida quriladi; prompt-only skill launch capability hisoblanmaydi. Tashqarida — Telegram/Instagram mikro-kontent.

**Nega kuchli:** brend eslab qolinadigan qiladi; ustoz darslarida baribir shu usul bor (o'zbeklarga o'rgatish tajribasi) — biz uni nomlab, formatlab, imzoga aylantiramiz.

**Holat:** format va 30 karta kontent rejasida; `word_builder` joriy 14 skill ichida yo'q. U faqat approved morphology dataset + structured PracticeMode + eval bilan `NEXT`dan admission oladi.

### ⭐ IH-7. Shaffof tizim — ishonch dvigateli

**Nima:** o'quvchi (va xohlasa ota-onasi) hamma narsani ko'radi: davomat jurnali, vazifa statuslari, quiz natijalari, mock dinamikasi, AI-limit paneli (bor!). To'lov — chek + tez tasdiqlash + aniq status. Reyting — halol formulada.

**Nega kuchli:** norasmiy kurslar bozorida shaffoflik = premium signal; ota-ona pul to'lovchi bo'lgan holatlarda hal qiluvchi.

**Holat:** ko'p qismi bor (jurnal, statuslar, panel) — bir butun "mening natijalarim" ko'rinishiga yig'ish (R2–R3).

### Imzo-harakatlar bir jumlada

> Daraja testi va ko'prik kontenti bilan **kirasan** (IH-5, IH-6), jonli kurs tizimi va AI yordamchi bilan **o'qiysan** (IH-1, IH-2, IH-4, IH-7), milliy sertifikat mock'lari bilan **imtihondan o'tasan** (IH-3).

---

## 5. Learner Outcome Loop — retention va AI uchun bitta yadro

Jonli kurs haftalik ritmni beradi. Platforma retentionni ko'proq badge bilan emas, yopiq natija sikli bilan quradi:

```text
DIAGNOSE: quiz / assignment / mock / learner goal
  → PLAN: bugungi 10–15 daqiqalik next action
    → PRACTICE: 3–8 structured item yoki revision
      → PROOF: oldingi urinish → yangi natija
        → ESCALATE: faqat human attention kerak bo'lgan holat
```

| Qatlam | Scope | Gate |
|---|---|---|
| Jonli dars lifecycle | jadval → check-in → release → assignment → review | canonical state machine va adapter parity |
| Daily Coach | deterministic 3-task reja | completion state + next-action policy |
| Structured practice | item/attempt/feedback/retry | objective va outcome event |
| Progress Proof | quiz/assignment/mock/practice evidence | validatsiyalangan formula, vanity % yo'q |
| Teacher escalation | R3/NEXT conditional pilot | A7/A9 quality gate + review time va resolution SLA |

SRS, streak, haftalik AI report va certificate readiness foizi mustaqil subsystem bo'lmaydi; ular shu loopning ishonchli event/evidence qatlamidan keyin capability sifatida qo'shiladi.

---

## 6. Narx strategiyasi — outcome gate'dan keyin

**Asosiy mahsulot — kurs obunasi** (jonli darslar + platforma birga; platforma alohida sotilmaydi — u kursning ustunligi). Mavjud checkout (kohort + chek + tasdiqlash) aynan shu model uchun qurilgan.

| Taklif | Narx (gipoteza) | Nima kiradi |
|---|---|---|
| **Bepul qatlam** (oqim uchun) | 0 | Placement/diagnostic, namunaviy dars yoki mock, cheklangan course-grounded AI beta |
| **Kurs obunasi** | Azurbekning joriy narxi | Jonli darslar + canonical platform oqimi + vazifa/quiz/mock + standart AI yordamchi |
| **Kurs+ pilot** | Narx faqat beta'dan keyin | Adaptive practice, revision history, Progress Proof, ko'proq human-reviewed mock va aniq feedback SLA |

Kurs+ narxi AI tokeni yoki “unlimited chat” bilan emas, o'lchangan learning gain, revision proof, teacher review capacity va SLA bilan oqlanadi. `+40–60%` faqat pricing experiment gipotezasi; “sertifikat kafolati” real cohort data, aniq legal shart va downside hisobi bo'lmaguncha launch scope'dan tashqarida.

AI tannarx: final chat token telemetriyasi bor, lekin SmartForm, bot guest, embedding va failed attemptlar to'liq hisoblanmaydi. Pre-productionda birinchi economics gate — Gemini free-tier supply'ni tugatmaslik: global request/token reservation, cheap-model allowlist, one-fallback va cooldown. Keyingi premium target: incremental AI xarajati premium incremental revenue'ning `≤25%`; bepul kvota yoki vaqtinchalik kredit mahsulot iqtisodini isbotlamaydi.

---

## 7. Brend va ovoz

- Platforma — **AzureLMS**; AI xarakter — **Azure** (persona yozilgan); **ustoz — brendning yuzi** (ishonch shaxsdan keladi, ayniqsa bu bozorda), Azure — texnologik imzo.
- Vizual: azure ko'k #1257e6 + Space Grotesk (tayyor dizayn-tizim).
- Ovoz: halol (limitlar, natija va'dalari real), tizimli, iliq; "Ko'prik" metafora oilasi (Ko'prik metodi, tovush ko'priklari, bugungi ko'prik).
- Ijtimoiy dalil: **bitiruvchilarning sertifikat natijalari** — eng kuchli aktiv (R1 parallel owner ishi: testimonial va foydalanish ruxsatini yig'ish).

---

## 8. Muvaffaqiyat mezonlari (20-sentyabr taqdimoti)

1. **Taqdimot:** 8–10 daqiqalik demo "bir o'quvchining haftasi + ustoz paneli" uzilishsiz (fallback video tayyor)
2. **Platforma:** kuzgi jonli guruh 3 haftadir platformada o'qiyapti (1-sentyabrdan) — demo emas, real ish
3. **Raqamlar (launch haftasi):** kuzgi guruh to'liq platformada · 100+ yangi registratsiya · 200+ daraja testi tugatilgan · Telegram kanal 300+
4. **Hikoya:** 3+ testimonial (shu jumladan avvalgi bitiruvchilardan) landing'da

Bu bandlar target, joriy evidence emas. Public production hosting/provider admissioni ochilmasa, 20-sentyabr natijasi `DEMO GO` yoki `BETA GO`; u “production launch” deb atalmasin.

### Outcome va owner-control mezonlari

- Core flow'ni developer/DB aralashuvisiz tugatgan learnerlar ulushi `≥98%`.
- Adapter parity bo'yicha critical incident `0`; manual DB rescue `0`.
- Assignment turnaround va teacher minutes/student/week beta boshida va oxirida o'lchangan.
- Structured practice ishlatilsa, birinchi activity completion `≥60%`, pre/post accuracy `+15 pp` yoki writing rubric `+0.5/5`.
- AI feedbackdan keyingi correction rate va 7 kunlik retention/transfer check yozilgan.
- Premium AI ochilsa, README'dagi quality, latency, safety va cost gate'lari o'tgan.

---

## Tadqiqot manbalari

- **Vazirlik buyrug'i №211/2024** (PF-81 ijrosi): magistratura/doktorantura sertifikat darajalari — foydalanuvchi taqdim etgan rasmiy PDF (ilova ro'yxatlari, C1*/B2/B1 va "qardosh tillarga B2" izohi)
- UZBMB turk tili milliy sertifikati: [ko'p darajali format e'loni](https://uzbmb.uz/post/view/turk-tilidan-milliy-sertifikat-imtihonlari-ko-p-darajali-shaklda-o-tkaziladi), [2025-03-02 imtihoni 5200+ topshiruvchi](https://uzbmb.uz/post/view/turk-tilini-bilish-darajasini-aniqlash-imtihonlari-bo-lib-o-td1), [milliy sertifikat sahifasi](https://uzbmb.uz/page/cefr)
- Telegram O'zbekiston: [UzDaily — 76% qamrov](https://www.uzdaily.uz/en/telegram-76-reach-youtube-no-1-e-commerce-on-the-rise-inside-uzbekistans-digital-landscape/), [DataReportal 2025](https://datareportal.com/reports/digital-2025-uzbekistan)
- Duolingo'da o'zbek bazasi yo'qligi: [kurslar ro'yxati](https://www.duolingo.com/courses/tr), [Talkpal tahlili](https://talkpal.ai/culture/does-duolingo-have-an-uzbek-course/)
- TYS (ikkilamchi maqsad — Turkiyaga yo'l segmenti): [TYS rasmiy](https://tys.yee.org.tr/), [2026 taqvim](https://tys.yee.org.tr/index.php?Itemid=473&catid=9%3Ahaberler-duyurular&id=219%3Atystakvim-2026&option=com_content&view=article)
- AI-tutor bozori saboqlari (retention): [LinguaLive 2026](https://www.lingualive.ai/blog/best-ai-language-tutor-2026), [Borderset](https://www.borderset.com/blogs/posts/duolingo-vs-talkpal-best-ai-language-learning-app-2026)
