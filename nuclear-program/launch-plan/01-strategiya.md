# 01 — Strategiya: bozor, pozitsiyalash, farqlash

*2026-07-11 (kechqurun qayta yozildi — model aniqlandi: platforma Azurbekning jonli kursi dastagi). Manbalar hujjat oxirida.*

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

---

## 1. Bozor va foydalanuvchi

### 1.1 Asosiy talab drayveri — magistratura sertifikat majburiyati (rasmiy faktlar)

2024-yil 24-maydagi PF-81 Farmoni ijrosida Oliy ta'lim, fan va innovatsiyalar vazirining 211-son buyrug'i (2024): **2024/2025 o'quv yilidan magistratura va oliy ta'limdan keyingi ta'limga hujjat topshirishda chet tilini bilish sertifikati majburiy**:

| Yo'nalishlar guruhi | Talab daraja |
|---|---|
| Xorijiy tillar yo'nalishlari (filologiya, tarjima, lingvistika...) | **C1*** |
| Gumanitar, biologiya, matematika/statistika, biznes/boshqaruv, huquq, xizmatlar, ijtimoiy fanlar, jurnalistika, AKT | **B2** |
| Boshqa barcha sohalar (muhandislik, tibbiyot, qishloq xo'jaligi, san'at, sport...) | **B1** |

**\* Hal qiluvchi izoh (buyruqning o'zida):** *"O'zbek, rus va qardosh tillar bo'yicha B2 daraja talab etiladi"* — ya'ni turkcha (qardosh til) bilan **hatto C1-yo'nalishlarga ham B2 yetadi**. Turk tili uchun shift maksimal talab — B2. *(Talqinni P0'da rasmiy manba bilan bir marta tasdiqlab olish kerak — marketing va'dasiga aylanishidan oldin.)*

Doktorantura (2-ilova): ixtisosliklar bo'yicha B1/B2.

### 1.2 Nega talabgorlar turkchani tanlaydi (Azurbek kursining isbotlangan tezisi)

Sertifikat **istalgan tan olingan chet tilidan** bo'lishi mumkin — daraja yo'nalishga bog'liq, til emas. Demak ratsional talabgor eng tez olinadigan tilni tanlaydi:
- Ingliz B2 (IELTS 5.5–6.5 ekvivalenti) — o'rtacha o'zbek uchun 1.5–3 yil mehnat
- **Turkcha B2 — qardosh til: bir necha oyda erishiladigan real maqsad** (agglyutinatsiya, SOV, egalik/kelishik parallellari, ulkan umumiy leksika)

Bozor hajmi o'lchangan: **UZBMB turk tili milliy sertifikat imtihonining bitta yozma kunida 5200+ topshiruvchi** (2025-03-02); imtihonlar yiliga bir necha marta, viloyatlarda + Toshkentda. 2025'dan ko'p darajali format (A1–C2): yozma kun (tinglash+o'qish+yozish) + og'zaki alohida kunlarda. **Bizning imtihon dvigatelimiz aynan shu 4 ko'nikmani qoplaydi.**

### 1.3 Segmentlar

| # | Segment | Ulush | Xususiyat |
|---|---|---|---|
| S1 | **Magistratura talabgori** (sertifikat B1/B2 kerak) | ~99% (Azurbek kursining real statistikasi) | Muddat bosimi (qabul mavsumi), natijaga to'laydi, "imtihondan o'tish" — yagona mezon |
| S2 | Doktorantura/ilmiy xodim | kichik | Xuddi shu ehtiyoj, kattaroq yosh, pul bor |
| S3 | Turkiyaga yo'l (grant/ish/o'qish), serial ixlosmandlari | kichik, o'sadigan | Freemium + kontent orqali o'zi keladi; post-launch fokus |

**Launch fokusi: S1.** Hamma xabar, kontent va mock imtihon S1 tiliga gapiradi: *"Magistraturaga sertifikat kerakmi? Turkcha — eng qisqa yo'l. Biz shu yo'lning o'zimiz."*

### 1.4 Mavsumiylik (rejaga ta'siri)

Magistratura qabuli yozda; sertifikat imtihonlari yil davomida. **Sentyabr = yangi tayyorgarlik mavsumining boshi** — kuzda boshlagan 2027-yil yozgi qabulga bemalol ulguradi. "20-sentyabr launch + kuzgi guruh" mavsum bilan ideal mos. Marketing kalendari UZBMB imtihon sanalariga bog'lanadi (P1'da rasmiy 2026–2027 taqvimni olib qo'yamiz).

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

**Bizning himoya qatlamlarimiz (moat):** (1) ustozning isbotlangan kursi va bitiruvchilari, (2) platforma-injiniring (yillik ish — nusxalab bo'lmaydi), (3) o'zbekcha AI repetitor, (4) milliy sertifikat formatiga mos mock dvigateli, (5) Ko'prik metodikasi kontenti.

---

## 3. Pozitsiyalash

### 3.1 Pozitsiya bayonoti

> **AzureLMS — magistraturaga sertifikat yo'lidagi eng mustahkam tizim:** Azurbek ustozning jonli kursi + har darsga video/vazifa/test + milliy sertifikat formatidagi mock imtihonlar + seni eslab qoladigan Azure AI yordamchi. Turkcha — eng qisqa yo'l; biz shu yo'lning xaritasi, hamrohi va mashqxonasimiz.

### 3.2 Xabar piramidasi (auditoriyaga qarab)

1. **S1 talabgorga (asosiy):** "Magistratura uchun sertifikat kerakmi? Turkchadan B2 — real 4–6 oy. Jonli darslar + tizimli platforma + AI yordamchi. Birinchi mock imtihonni bepul topshirib ko'r."
2. **Ota-ona/homiy:** "Farzandingiz qayerda, qachon, qancha o'qigani — hammasi ko'rinadi: davomat, baho, progress."
3. **Keng auditoriya (kontent):** "Turkchaning yarmini allaqachon bilasan" — ko'prik postlari qiziqish uyg'otadi → daraja testi → kurs.

### 3.3 Slogan nomzodlari (P0 tanlovi)

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

**Holat:** bloklar qurilgan (bot davomat, release, assignment, leaderboard) — bitta silliq oqimga bog'lash kerak (03-backlog A0).

### ⭐ IH-2. Azure AI — darslar orasidagi 24/7 yordamchi (jonli demo qiroli)

**Nima:** o'quvchi yarim kechada vazifa fotosini yuklaydi → AI o'qiydi (vision bor), xatoni o'zbekcha tushuntiradi, zaif mavzuni eslab qoladi (memory bor), ertasiga shu mavzudan mashq beradi (quiz_generator bor). Ustozga: tekshiruv navbati yengillashadi (AI birinchi qatlam), o'quvchi savollari 3 kun kutmaydi.

**Nega kuchli:** o'qituvchining eng katta og'rig'i — masshtab (100 o'quvchining savoli/vazifasi); AI buni yechadi, lekin ustozni ALMASHTIRMAYDI — bu xabarda muhim ("AI + ustoz", "AI o'rniga" emas). O'zbekistonda buni ko'rsatadigan kurs yo'q.

**Holat:** texnik 90% tayyor; "ertasi kuni davom" trigger + haftalik hisobot qoladi.

### ⭐ IH-3. Milliy sertifikat mock-markazi (S1'ning yuragi)

**Nima:** UZBMB turk tili imtihoni formatida mock: yozma kun (tinglash — replay-limit bilan, o'qish — 8 task turi, yozish — so'z chegarasi + per-esse feedback) + og'zaki (audio yozish + ustoz baholashi). "Sertifikat tayyorligi: B2 — 68%" progress. Har mock natijasi zaif-mavzu sifatida AI xotirasiga tushadi.

**Nega kuchli:** S1 uchun yagona haqiqiy savol "imtihondan o'tamanmi?" — mock bunga javob beradi. Imtihon dvigatelimiz shu format uchun ortiqchasi bilan yetarli. Birinchi mock bepul = eng kuchli lead-magnit.

**Holat:** dvigatel to'liq; UZBMB spetsifikatsiyasini olish (P1 tadqiqot) + 2 mock kontenti (04) + JS brauzer sinovi qarzi.

### ⭐ IH-4. Telegram-native ritm (darslar allaqachon shu yerda)

**Nima:** darslar Telegramda o'tilgani uchun butun ritm shu yerda: "bugun 20:00 jonli dars" eslatma, dars ochildi xabari, vazifa muddati, streak, kunlik ko'prik, haftalik hisobot — hammasi bot orqali, deep-link platformaga.

**Nega kuchli:** O'zbekiston Telegram mamlakati (76–88% qamrov); auditoriyani yangi kanalga ko'chirish shart emas — mavjud odatga qo'shilamiz.

**Holat:** bot davomat qiladi xolos — scheduler + xabar qatlamí build (P2).

### ⭐ IH-5. Daraja testi — kirish eshigi

**Nima:** "Darajangni 10 daqiqada aniqla" — anonim test, natija: daraja + "turkchaning X%i senga tanish" + **"sen B2 gacha ~N oyda yetasan — kuzgi guruh N-sentyabrda boshlanadi"** (kursga to'g'ridan-to'g'ri ko'prik). Ulashiladigan natija kartasi.

**Nega kuchli:** kurs uchun lead-mashina (hozirgi og'zaki-tavsiya oqimini tizimlashtiradi) + viral halqa. Sertifikat konteksti bilan yanada o'tkir: "darajang B1 — imtihonga shu-shu yetishmayapti".

**Holat:** build (P1). Quiz/SmartForm dvigatellari bor — o'rta hajm.

### ⭐ IH-6. Ko'prik metodikasi — kontent imzosi

**Nima:** "sen allaqachon yarmini bilasan" — tovush ko'priklari (b↔v: bor=var), morfologiya parallellari (uy-im=ev-im); dars materiallari va AI tushuntirishlari (word_builder skilli) shu tilda gapiradi; tashqarida — Telegram/Instagram mikro-kontent.

**Nega kuchli:** brend eslab qolinadigan qiladi; ustoz darslarida baribir shu usul bor (o'zbeklarga o'rgatish tajribasi) — biz uni nomlab, formatlab, imzoga aylantiramiz.

**Holat:** format + 30 karta (04), word_builder skilli (P1).

### ⭐ IH-7. Shaffof tizim — ishonch dvigateli

**Nima:** o'quvchi (va xohlasa ota-onasi) hamma narsani ko'radi: davomat jurnali, vazifa statuslari, quiz natijalari, mock dinamikasi, AI-limit paneli (bor!). To'lov — chek + tez tasdiqlash + aniq status. Reyting — halol formulada.

**Nega kuchli:** norasmiy kurslar bozorida shaffoflik = premium signal; ota-ona pul to'lovchi bo'lgan holatlarda hal qiluvchi.

**Holat:** ko'p qismi bor (jurnal, statuslar, panel) — bir butun "mening natijalarim" ko'rinishiga yig'ish (P2–P3).

### Imzo-harakatlar bir jumlada

> Daraja testi va ko'prik kontenti bilan **kirasan** (IH-5, IH-6), jonli kurs tizimi va AI yordamchi bilan **o'qiysan** (IH-1, IH-2, IH-4, IH-7), milliy sertifikat mock'lari bilan **imtihondan o'tasan** (IH-3).

---

## 5. Retention arxitekturasi

Jonli kurs o'zi kuchli retention beradi (jadval + guruh + ustoz majburiyati) — platforma uni kunlik odat bilan to'ldiradi:

```
Haftalik yadro: JONLI DARS (Telegram, ustoz bilan)
   ↓ dars ochilishi + vazifa (platforma)
Kunlik halqa: Telegram xabar → 3-daqiqalik sessiya
   (SRS takror 5 karta + bugungi ko'prik) → streak
Haftalik yakun: "Azure haftaligi" hisobot + reyting yangilanishi
Oylik cho'qqi: MOCK IMTIHON → tayyorgarlik % o'sishi
```

| Qatlam | Mexanika | Holat |
|---|---|---|
| Jonli dars ritmi | jadval, eslatmalar, davomat | bor (bot) + xabarlar P2 |
| Kunlik ritual | SRS + ko'prik + streak | BUILD (P1–P2); streak hozir placeholder! |
| AI xotira ko'rinishi | haftalik hisobot | BUILD-kichik (P2) |
| Ijtimoiy | leaderboard (bor), guruh chat (bor) | POLISH |
| Maqsad-gradient | sertifikat tayyorligi % | BUILD-kichik (P2) |
| Yutuqlar | XP/badge/sertifikat (bor) | POLISH |

---

## 6. Narx strategiyasi (gipoteza — P0'da Azurbek kiritadi, beta'da tekshiriladi)

**Asosiy mahsulot — kurs obunasi** (jonli darslar + platforma birga; platforma alohida sotilmaydi — u kursning ustunligi). Mavjud checkout (kohort + chek + tasdiqlash) aynan shu model uchun qurilgan.

| Taklif | Narx (gipoteza) | Nima kiradi |
|---|---|---|
| **Bepul qatlam** (oqim uchun) | 0 | Daraja testi, 1 mock imtihon (yozma), kunlik ko'prik, AI-lite (haftalik token limit), namunaviy video dars |
| **Kurs obunasi** | Azurbekning joriy narxi ± platforma-prim | Jonli darslar + barcha ochilgan video/materiallar + vazifa tekshiruvi + quiz/reyting + AI standart limit + Telegram ritm |
| **Kurs+ (premium)** | +40–60% | + barcha mock imtihonlar cheksiz + og'zaki mock ustoz baholashi bilan + AI yuqori limit + ustuvor feedback |

Taktikalar: kuzgi guruhga "launch narxi" (birinchi guruhga chegirma yoki premium-bonus); bitiruvchi-referral (sertifikat olgan o'quvchi tavsiyasi = ikkalasiga bonus); **"sertifikat kafolati" o'ylab ko'rish** (davomat+vazifa sharti bilan o'tmasa — keyingi mavsum bepul) — ishonch bombasi, risk past.

AI tannarx: token telemetriya bor (AIResponseRun); P4'da o'quvchi-boshiga haftalik so'm hisobi → limitlar moslanadi. DO $200 kredit — yostiq.

---

## 7. Brend va ovoz

- Platforma — **AzureLMS**; AI xarakter — **Azure** (persona yozilgan); **ustoz — brendning yuzi** (ishonch shaxsdan keladi, ayniqsa bu bozorda), Azure — texnologik imzo.
- Vizual: azure ko'k #1257e6 + Space Grotesk (tayyor dizayn-tizim).
- Ovoz: halol (limitlar, natija va'dalari real), tizimli, iliq; "Ko'prik" metafora oilasi (Ko'prik metodi, tovush ko'priklari, bugungi ko'prik).
- Ijtimoiy dalil: **bitiruvchilarning sertifikat natijalari** — eng kuchli aktiv (P0: mavjud bitiruvchilardan testimonial/ruxsat yig'ishni boshlash).

---

## 8. Muvaffaqiyat mezonlari (20-sentyabr)

1. **Taqdimot:** 8–10 daqiqalik demo "bir o'quvchining haftasi + ustoz paneli" uzilishsiz (fallback video tayyor)
2. **Platforma:** kuzgi jonli guruh 3 haftadir platformada o'qiyapti (1-sentyabrdan) — demo emas, real ish
3. **Raqamlar (launch haftasi):** kuzgi guruh to'liq platformada · 100+ yangi registratsiya · 200+ daraja testi tugatilgan · Telegram kanal 300+
4. **Hikoya:** 3+ testimonial (shu jumladan avvalgi bitiruvchilardan) landing'da

---

## Tadqiqot manbalari

- **Vazirlik buyrug'i №211/2024** (PF-81 ijrosi): magistratura/doktorantura sertifikat darajalari — foydalanuvchi taqdim etgan rasmiy PDF (ilova ro'yxatlari, C1*/B2/B1 va "qardosh tillarga B2" izohi)
- UZBMB turk tili milliy sertifikati: [ko'p darajali format e'loni](https://uzbmb.uz/post/view/turk-tilidan-milliy-sertifikat-imtihonlari-ko-p-darajali-shaklda-o-tkaziladi), [2025-03-02 imtihoni 5200+ topshiruvchi](https://uzbmb.uz/post/view/turk-tilini-bilish-darajasini-aniqlash-imtihonlari-bo-lib-o-td1), [milliy sertifikat sahifasi](https://uzbmb.uz/page/cefr)
- Telegram O'zbekiston: [UzDaily — 76% qamrov](https://www.uzdaily.uz/en/telegram-76-reach-youtube-no-1-e-commerce-on-the-rise-inside-uzbekistans-digital-landscape/), [DataReportal 2025](https://datareportal.com/reports/digital-2025-uzbekistan)
- Duolingo'da o'zbek bazasi yo'qligi: [kurslar ro'yxati](https://www.duolingo.com/courses/tr), [Talkpal tahlili](https://talkpal.ai/culture/does-duolingo-have-an-uzbek-course/)
- TYS (ikkilamchi maqsad — Turkiyaga yo'l segmenti): [TYS rasmiy](https://tys.yee.org.tr/), [2026 taqvim](https://tys.yee.org.tr/index.php?Itemid=473&catid=9%3Ahaberler-duyurular&id=219%3Atystakvim-2026&option=com_content&view=article)
- AI-tutor bozori saboqlari (retention): [LinguaLive 2026](https://www.lingualive.ai/blog/best-ai-language-tutor-2026), [Borderset](https://www.borderset.com/blogs/posts/duolingo-vs-talkpal-best-ai-language-learning-app-2026)
