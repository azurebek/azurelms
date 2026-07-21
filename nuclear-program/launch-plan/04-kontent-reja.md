# 04 — Kontent reja: video darslar, milliy sertifikat mock'lari, test banki, ko'priklar, blog

*Model: kontentning YADROSI — Azurbekning kursi (u yillardir o'tayotgan dastur). Platforma-kontent uni o'raydi: har darsga video + konspekt + lug'at + quiz + vazifa; ustiga mock imtihonlar va oqim-kontenti. AI faqat qoralama tayyorlaydi; curriculum, level, answer key, rubric va publish qarori Azurbek tasdig'idan o'tadi. Rebaseline: 2026-07-22.*

---

## 1. Kurs strukturasi — manba: Azurbekning mavjud dasturi

**Owner vazifasi (P0–P1 parallel):** Azurbek joriy o'quv dasturini shu shablonga tushiradi; agent qoralama va strukturada yordam beradi:

```
Modul N: <nomi>            (masalan: "Kelishiklar")
  Dars N.1: <mavzu> — jonli darsda nima o'tiladi (3-5 band)
  Dars N.2: ...
  Modul yakuni: quiz mavzulari + vazifa turi
Daraja nishoni: <A1/A2/B1/B2 qaysi qismiga xizmat qiladi>
```

Platforma strukturasi (Course→Module→Lesson) aynan shundan quriladi. **Kurs allaqachon isbotlangan** (bitiruvchilar sertifikat olgan) — biz uni raqamlashtiramiz, qayta ixtiro qilmaymiz. Mening oldingi "A1 Ko'prik kursi" skeletim (arxiv: shu hujjat git-tarixida) kerak bo'lsa to'ldiruvchi g'oyalar manbai — asos EMAS.

## 2. Bitta darsning platforma-to'plami (shablon)

Har jonli darsga mos platforma-dars quyidagilardan iborat:

| Element | Kim yaratadi | Qachon ochiladi |
|---|---|---|
| 1. **Video dars** (10–20 daq, yozib olingan) | Azurbek | jonli dars o'tilgach (A3 lifecycle transition) |
| 2. Konspekt (dars xulosasi, jadval/misollar) | AI-qoralama → Azurbek tahriri | video bilan |
| 3. **Ko'prik ochilishi** (o'zbek paralleli 2-3 jumla — imzo) | AI-qoralama → tahrir | konspekt boshida |
| 4. Lug'at (8–12 so'z: tr/uz/misol/🔗kognat) → approved structured vocabulary | AI-qoralama → Azurbek tasdig'i | video bilan |
| 5. Quiz (5–8 savol, dvigatelda) | AI-qoralama → tahrir | video bilan |
| 6. Vazifa (modulda 1–2 marta; matn/audio) | Azurbek belgilaydi | ustoz aktivlashtiradi |
| 7. Structured practice CTA | avtomatik | faqat A6/A7 gate'dan o'tib, feature flag ochiq bo'lsa |

**AI-quvur:** jonli dars mavzusi + Azurbekning eski materiallari → Claude konspekt/lug'at/quiz qoralaydi → Azurbek 15–20 daqiqada tahrir qiladi → backoffice yoki `load_course_content` bilan kiradi. **Azurbekning darsga sarfi: video (asosiy) + 20 daq tahrir.**

## 3. Video yozish jadvali — owner capacity bilan real bo'lsin

Gipoteza-reja (Azurbek tasdiqlaydi/to'g'irlaydi):

| Davr | Norma | Jami |
|---|---|---|
| P0–P1 (22 iyul – 9 avg) | haftasiga 3–4 video | ~8–10 dars |
| P2 (10–23 avg) | haftasiga 4 video | ~8 dars (jami ~16–18) |
| P3 (24 avg – 6 sen) | haftasiga 2–3 (beta tayyorgarligi) | jami ~21–24 |
| P4 | 13-sen kontent va scope freeze | — |

**Minimal launch-to'plam (pastki chegara):** kuzgi guruhning birinchi 4–6 haftasini qoplaydigan darslar + 1 to'liq namunaviy dars (bepul qatlamga). Guruh jonli o'qiydi — video "dars o'tilgach" ochilgani uchun kurs oxirigacha hamma video launch kuni SHART EMAS; guruhdan 2 hafta oldinda yurish yetadi. Bu R1 riskini keskin kamaytiradi.

**Sifat standarti (P1 oxirigacha):** yozish sozlamasi (yorug'lik/mikrofon/ekran-yozuv sxemasi), intro/outro shablon, "bir video = bir mavzu ≤20 daq" qoidasi.

## 4. Milliy sertifikat mock imtihonlari (IH-3 — S1'ning yuragi)

**Publish gate:** UZBMB turk tili spetsifikatsiyasi/demo variantini rasmiy sahifa va topshirgan o'quvchilar tajribasi bilan tekshirish. Format ma'lum qadar: ko'p darajali (A1–C2), yozma kun = tinglash+o'qish+yozish, og'zaki alohida.

| Mock | Tarkib | Tayyor bo'lish |
|---|---|---|
| **Mock №1 (yozma)** — lead-magnit nomzodi | Tinglash (2 audio, replay-limit) + O'qish (2 matn, aralash task turlari) + Yozish (2 prompt, so'z chegarasi) | P2 oxiri, exam/mobile gate'dan keyin |
| **Mock og'zaki** | 3 prompt (audio yozish) + ustoz baholash oqimi; AI pronunciation claim'i yo'q | P3 oxiri, private media gate'dan keyin |
| **Mock №2 (yozma, to'liq)** | №1 formatida yangi variantlar — kurs obunachilariga | P4 capacity bo'lsa; aks holda post-launch |

Audio manba: TTS (turkcha ovozlar) + kerak joyda Azurbek ovozi. Har mock natijasi ball va bo'lim kesimini beradi; zaif mavzu faqat A6 Outcome Ledger'da objective-taglangan evidence sifatida yoziladi, AI memory mastery manbasi bo'lmaydi.

**Halollik yorlig'i:** "UZBMB formatiga yaqin MASHQ imtihoni — rasmiy imtihon emas". TYS-yo'nalish (Turkiyaga ketuvchilar) — post-launch qo'shimcha mock.

## 5. Daraja testi banki (`NEXT`)

60–80 savol: leksika-ko'prik 24 (kognatlardan boshlanadi — "% tanish" hisobi), grammatika 24, o'qish 12. Daraja taqsimoti A0/A1/A2/B1. Faqat tanlov (avto-baho). AI-qoralama → Azurbek tez ko'rik (u darajalarni his qiladi — kalibrlash uning tajribasidan).

## 6. Tovush ko'priklari — 30 karta (IH-6)

Format (mahsulot ichida "bugungi ko'prik" + Telegram post + reels):

> **№7 · b ↔ v** — bor → **var** · ber- → **ver-** · "Vaqtim bor" → "Vaktim var". Bitta harf farqi!

1–15: tovush/morfologiya (alifbo, ı↔i, ö/ü, q↔k, o'↔ö/ü, -lar/-ler, egalik, -da/-de, -ga/-e, -dan/-den, -di o'tgan zamon, -mi so'roq, sonlar...); 16–30: leksik oilalar (oila, ranglar, taom, vaqt, tana, shahar...). AI qoralaydi, Azurbek 2–3 daqiqada tasdiqlaydi.

## 7. Blog — SEO urug'lari (12 post, S1 so'rovlariga o'q)

| # | Sarlavha (draft) | So'rov |
|---|---|---|
| 1 | Magistraturaga chet tili sertifikati: 2026–27 to'liq qo'llanma (B1/B2/C1 kimga) | magistratura sertifikat talab |
| 2 | Nega turk tili — sertifikat uchun eng qisqa yo'l (qardosh-til B2 qoidasi bilan) | magistratura turk tili |
| 3 | UZBMB turk tili milliy sertifikati: format, ro'yxatdan o'tish, sanalar | milliy sertifikat turk tili |
| 4 | Turk tilidan B2 necha oyda? Halol reja | turk tili B2 |
| 5 | Milliy sertifikat yozma imtihoni: bo'limma-bo'lim tayyorlanish | uzbmb turk tili imtihon |
| 6 | Og'zaki imtihonda nima so'raladi va qanday mashq qilish kerak | turk tili og'zaki imtihon |
| 7 | O'zbeklar turkchada eng ko'p qiladigan 7 xato | turk tili xatolar |
| 8 | Turk va o'zbek tili: 10 hayratlanarli o'xshashlik | o'xshashlik |
| 9 | ev→evim→evimde: turkcha so'z qurilishi | turk tili grammatika |
| 10 | Doktoranturaga sertifikat: nimalar o'zgardi | doktorantura chet tili |
| 11 | AI bilan til o'rganish: nimaga yordam beradi, nimaga yo'q (halol) | AI til o'rganish |
| 12 | Bepul boshlash: daraja testi + 1 mock — qanday ishlaydi | turk tili bepul test |

AI-qoralama → Azurbek tahriri; haftasiga 2 post 24-avgustdan, faqat launch-critical kontent ritmiga zarar bermasa. Har biri kanalga parchalanadi.

## 8. Marketing mikro-kontent

- Ko'prik kartalari (30) — asosiy oziqa
- **Bitiruvchi hikoyalari:** "X ball oldim, magistraturaga kirdim" — consent va tekshirilgan natija bilan
- Azure demo-gif'lar (foto-vazifa tekshiruvi, mock natijasi)
- "Sertifikat savol-javob" seriyasi (buyruq faktlari asosida — odamlar B1/B2 talabini bilmaydi, biz tushuntiramiz = ishonch)

## 9. Texnik talablar (03-backlog bog'lari)

1. Lesson'ga approved **lug'at strukturasi** — A6 Outcome Ledger/SRS uchun keyingi manba; avto-SRS launch sharti emas
2. **Preview/entitlement** — faqat A4 typed access policy orqali
3. **Seed quvuri:** `load_course_content` management command (qoralamalarni bir urishda kiritish; backoffice keyin tahrir)
4. Video hosting: MVP = YouTube unlisted embed (Lesson.video_url bor; 0 xarajat, tez) — kamchiligi: yuklab olish himoyasi zaif. Protected learner media bilan aralashtirilmaydi.
5. Mock tinglash audiosi public/course asset policy bilan; learner speaking yozuvi private media policy bilan saqlanadi

---

*Qisqartirish tartibi: blog 12→6 → ko'priklar 30→15 → placement bank va mock №2 post-launch → video norma pasayadi, lekin guruhdan 2 hafta oldinda yurish saqlanadi. Dars sifati va core cohort uchun zarur mock №1 qurbon qilinmaydi.*
