# 02 — Yo'l xaritasi: 11-iyul → 20-sentyabr (71 kun)

*Model: platforma = Azurbek jonli kursining dastagi (01-strategiya §0). Fazalar ketma-ket; KONTENT (video darslar — Azurbek + mock/test kontenti) va MARKETING parallel yo'lak. Har faza oxirida chiqish-kriteriy — o'tmasa scope qisqaradi, sana emas.*

## Umumiy manzara

```
IYUL                    AVGUST                      SENTYABR
11───15│16──────────5│6──────────24│25────────7│8──────16│17──20
  P0   │     P1      │     P2      │    P3     │   P4    │  P5
Poydevor│ Farqlovchi  │ Odat halqasi│ Ishonch + │Qattiqlash│Launch
qarorlar│ yadro +     │ + 1-DEPLOY  │ KUZGI     │ + demo  │
        │ ustoz oqimi │             │ GURUH 1sen│ aktivlar│
────────┴─────────────┴─────────────┴───────────┴─────────┴──────
KONTENT: [video yozish jadvali ──── har hafta N ta dars ────][muzlatish 13sen]
         [placement bank][mock №1 yozma][mock og'zaki][mock №2]
MARKETING: [bitiruvchi testimoniallar][TG kanal ~10avg][kuzgi guruh qabuli][launch]
```

**Qat'iy qoidalar:**
1. **Scope-freeze:** 03-backlog KESISH ro'yxati muqaddas.
2. **Juma — yashil kun:** testlar yashil + tree toza + marinebook.
3. **Jonli kurs birinchi o'rinda:** Azurbekning dars jadvali qurilishdan aziyat chekmasin — video-yozish bloklari haftalik rejaga *oldindan* qo'yiladi.

---

## P0 — Poydevor va qarorlar (11–15 iyul)

| # | Vazifa | Kim |
|---|---|---|
| 0.1 | `claude/ai-context-understanding` → smoke → **main merge** + `reindex_ai_memory` | Claude |
| 0.2 | B4: settings AI-model ro'yxatini DO'ga moslash | Claude |
| 0.3 | **Kurs dasturi kiritiladi:** Azurbek mavjud o'quv dasturini modul/dars ro'yxatiga tushiradi (04-hujjat shabloni) — platforma strukturasi shundan quriladi | Azurbek |
| 0.4 | **Qarorlar:** kurs narxi (joriy narx + platforma bilan yangi narx), video-yozish haftalik jadvali (nechta dars/hafta real?), slogan, taqdimot auditoriyasi | Azurbek |
| 0.5 | **"Qardosh tilga B2" talqinini tasdiqlash** (211-buyruq izohi) — marketing va'dasidan oldin | Azurbek+Claude |
| 0.6 | UZBMB turk tili imtihon spetsifikatsiyasi/demo variantini topib olish (mock dizayni uchun) + 2026–27 imtihon taqvimi | Claude |
| 0.7 | Bitiruvchilardan testimonial/natija-ruxsat yig'ishni boshlash (eng kuchli marketing aktivi) | Azurbek |
| 0.8 | Domen/hosting inventarizatsiyasi (DO App Platform, SSL, email provayder) | Claude |

**Chiqish:** main yashil; kurs dasturi hujjatda; narx/jadval qarorlari yozilgan; UZBMB format hujjati qo'lda.

---

## P1 — Farqlovchi yadro + ustoz oqimi (16-iyul – 5-avgust, 3 hafta)

**Maqsad:** kursni platformada o'tkazish uchun kerak hamma narsa silliq + farqlovchi qismlar ishlaydi.

### Hafta 1 (16–22 iyul): Ustoz kun-oqimi (IH-1) + exam JS qarzi
- **A0 "Dars kuni" oqimi:** o'qituvchi panelida bitta sahifa — bugungi jonli dars: davomat (bot check-in natijasi ko'rinadi/qo'lda to'g'irlanadi), "darsni ochish" tugmasi (CohortLessonRelease + video dars + vazifa aktiv + o'quvchilarga xabar), navbatdagi vazifa-tekshiruvlar
- Exam JS jonli brauzer sinovi (recorder/audio-limit/autosave/timer) — mock'lar bunga tayanadi
- Bot davomat oqimini jonli guruhda sinash (start_lesson → check-in → jurnal)

### Hafta 2 (23–29 iyul): Daraja testi (IH-5) + AI skilllar
- Placement test to'liq oqim (anonim → natija → "kuzgi guruhga yozil" CTA → registratsiya)
- `word_builder` + `conversation_partner` skilllari (sticky ro'yxat bilan)

### Hafta 3 (30-iyul – 5-avg): SRS lug'at v1 (kunlik odat yadrosi)
- `vocab` app: modellar + soddalashtirilgan SM-2 + sessiya UI + dars-lug'atidan avto-to'ldirish + dashboard karta

**Parallel kontent:** video darslar yozish boshlanadi (0.4 jadvali bo'yicha); placement bank 60 savol; mock №1 yozma qism drafti; ko'priklar 1–10.

**Chiqish:** ustoz test-kohortda to'liq dars-siklini bir tugmalar bilan o'tkaza oladi; yangi foydalanuvchi placement→dars→AI→SRS zanjiridan o'tadi; exam JS tasdiqlangan.

---

## P2 — Odat halqasi + birinchi DEPLOY (6–24 avgust)

### Hafta 1 (6–12 avg): DEPLOY (launch'dan 6 hafta oldin — ataylab erta)
- DO App Platform: Postgres+pgvector, Valkey, Spaces, Daphne+worker+beat, `SECURITY_STRICT=True`, webhook-rejim bot
- Sentry + uptime + kunlik backup + **restore mashqi**; `/healthz`
- Analytics: Plausible/Umami + o'z ProductEvent jadvali

### Hafta 2 (13–19 avg): Telegram ritm (IH-4) + streak
- Kunlik "Bugungi ko'prik" + **"bugun 20:00 jonli dars" eslatmalari** + vazifa muddati + dars-ochildi xabarlari (A0 bilan ulanadi)
- Streak (haqiqiy modeli) + freeze; dashboard+bot ko'rinishi

### Hafta 3 (20–24 avg): Shaffoflik va oqim
- "Mening natijalarim" ko'rinishi (IH-7): davomat+vazifa+quiz+mock bir sahifada
- Freemium simlari: bepul qatlam (placement, 1 mock yozma, AI-lite, namunaviy dars) → kursga yozilish oqimi
- "Azure haftaligi" hisobot + sertifikat-tayyorgarlik % vidjeti

**Parallel kontent:** video darslar davom; mock №1 to'liq (yozma) dvigatelga kiritilgan; og'zaki mock promptlari.

**Parallel marketing:** ~10-avg Telegram kanal start (ko'priklar + "sertifikat yo'li" postlari); **kuzgi guruh qabuli e'loni** (avgust oxiri).

**Chiqish:** prod'da to'liq sikl ishlaydi (yozilish→chek→tasdiq→dars→vazifa→AI→xabarlar); mock №1 topshirsa bo'ladi; restore sinalgan.

---

## P3 — Ishonch + KUZGI GURUH START (25-avgust – 7-sentyabr)

**1-sentyabr: kuzgi jonli guruh platformada boshlanadi — bu bizning beta.** Real o'quvchilar, real to'lov, real darslar; launch kuni "3 haftalik jonli tizim" ko'rsatamiz, demo emas.

### Hafta 1 (25–31 avg): konversiya va to'lov
- Landing yangi pozitsiyada (S1 xabari: sertifikat yo'li; ustoz + natijalar; daraja testi CTA; kuzgi guruh qabuli)
- To'lov UX + **admin Telegram-ping** (yangi chek → 2 soat ichida tasdiqlash SLA)
- Mobil audit (360px hamma asosiy oqim) + PWA manifest
- Kuzgi guruh onboarding tayyorgarligi: yozilish → guruhga ulanish → birinchi hafta ssenariysi

### Hafta 2 (1–7 sen): guruh jonli + QA
- 1-sen: birinchi jonli dars platforma bilan (davomat→ochilish→vazifa→xabarlar zanjiri jonli!)
- Kunlik kuzatuv: analytics + guruh feedback → tez fixlar
- QA to'liq matritsa (05-hujjat): mobil imtihon (mikrofon!), websocket, bo'sh/to'la holatlar
- Qo'shimcha beta-to'lqin: kanal obunachilaridan 10–15 kishi bepul qatlamga (oqim sinovi)

**Chiqish:** guruh 1 hafta uzilishsiz o'qidi; P0/P1 bug nol; to'lov real cheklar bilan ishladi; testimonial yig'ish boshlandi.

---

## P4 — Qattiqlash (8–16 sentyabr)

- Guruh/beta topilmalari yopiladi; performance (AI <3s median start, N+1, statika)
- **AI tannarx hisobi** (real guruh ma'lumotidan) → limit/narx tasdig'i
- Xavfsizlik o'tishi + launch checklist (05) 100%
- Marketing aktivlari: 2-daq demo video, taqdimot slaydlar, launch-hafta 10 post
- **13-sen: kontent muzlatish** (yangi material yo'q, faqat fix)

**Chiqish:** prod 7+ kun barqaror; checklist yashil; demo aktivlar tayyor.

---

## P5 — Taqdimot va launch (17–20 sentyabr)

- 17: demo-akkauntlar + taqdimot final; 18: **repetitsiya №1**; 19: fixlar + **repetitsiya №2** + fallback video
- **20-sen: TAQDIMOT + ommaviy ochilish** — daraja testi keng e'lon, founder-taklif, kun bo'yi monitoring navbati
- Demo yadrosi: real kuzgi guruhning 3 haftalik jonli ma'lumoti + "bir o'quvchining haftasi" ssenariysi (05)

---

## Parallel yo'laklar xulosasi

| Yo'lak | P1 | P2 | P3 | P4 |
|---|---|---|---|---|
| **Video darslar** (Azurbek) | jadval start | davom | davom (guruh bilan sinxron) | muzlatish 13-sen |
| **Mock/test kontenti** | placement 60, mock№1 draft | mock№1 jonli, og'zaki promptlar | mock№2 | — |
| **Marketing** | testimonial yig'ish | TG kanal, guruh qabuli | guruh start hikoyalari | demo video, postlar |
| **Ops** | — | deploy, Sentry, backup | guruh monitoringi | checklist, xavfsizlik |

---

## Risk reestri

| # | Risk | Ehtimol | Zarba | Javob |
|---|---|---|---|---|
| R1 | **Video darslar kechikadi** (Azurbek vaqti — eng uzun ustun) | Yuqori | Yuqori | P0'da real haftalik jadval; jonli guruh baribir o'qiy oladi (video darsdan keyin ham chiqsa bo'ladi — jonli dars birlamchi!); minimal launch-to'plam: guruhning 1-oyi uchun yetarli darslar |
| R2 | **Prod deploy qilinmagan** | Aniq | Yuqori | P2 boshida, launch'dan 6 hafta oldin |
| R3 | **Jonli kurs + qurilish parallel yuki** | Yuqori | Yuqori | Video-bloklar kalendarga oldindan; scope-freeze; AI-agentlar kod/kontent qoralamasini ko'taradi |
| R4 | **Kuzgi guruh platformada qiynaladi** (beta og'riqlari real mijozlarda) | O'rta | Yuqori | P1'da ustoz-oqimi test-kohortda sinaladi; 1-hafta kunlik kuzatuv; Telegram-guruh zaxira kanal sifatida qoladi (hech narsa yo'qolmaydi) |
| R5 | AI xarajat | O'rta | O'rta | aicontrol limitlar kun-1'dan; telemetriya bor; P4 hisob |
| R6 | Mobil UX oqsashi | O'rta | Yuqori | P3 audit majburiy; guruh asosan telefonda — 1-haftada bilinadi |
| R7 | Exam JS sinalmagan | Aniq | O'rta | P1-h1 yopiladi |
| R8 | To'lov qo'lda | O'rta | O'rta | Telegram-ping + SLA; Payme/Click post-launch |
| R9 | UZBMB format ma'lumoti yetarsiz (mock aniqligi) | O'rta | O'rta | P0.6 tadqiqot; topshirgan o'quvchilardan so'rov (Azurbekda bor!); "formatga YAQIN mashq" halol yorlig'i |
| R10 | Bot token/env gotcha | Past | O'rta | hujjatlangan; webhook health monitoringda |

---

## Metrikalar

**Instrumentatsiya P2:** Plausible/Umami + ProductEvent.

| Bosqich | Metrika | Maqsad |
|---|---|---|
| P3 | Kuzgi guruh platformaga to'liq o'tgan | 100% |
| P3 | Guruhda vazifa topshirish ulushi (1-hafta) | ≥70% |
| P3 | Guruh D7 platforma-qaytish | ≥60% (jonli kurs bor — baland bo'lishi kerak) |
| Pre-launch | TG kanal obunachi | 300+ |
| Launch hafta | Yangi registratsiya | 100+ |
| Launch hafta | Daraja testi tugatish | 200+ |
| Launch hafta | Yangi kurs-arizalar (chek) | 15+ |
| Doimiy | AI javob starti (median) | <3s |
| Doimiy | O'quvchi-haftasiga AI tannarx | marja ichida (P4) |

---

*Keyingi: [03-mahsulot-backlog.md](03-mahsulot-backlog.md).*
