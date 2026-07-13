# 03 — Mahsulot backlog: QURISH / SAYQALLASH / KESISH

*Model: platforma = jonli kurs dastagi. Har band: nima, qaysi imzo-harakat (01 §4), qabul kriteriysi, hajm (S ≤0.5 kun, M ≤2, L ≤5, XL bo'linadi), faza. Kod-fakt holati 2026-07-11 auditidan. Holat belgisi: ☐ / ◐ / ✅.*

---

## A. QURISH

### ☐ A0. "Dars kuni" — ustoz kun-oqimi (LAUNCH YADROSI)
- **IH:** IH-1 · **Faza:** P1-h1 · **Hajm: L**
- **Nima:** teacher panelda bitta operatsion sahifa. Bloklar: (1) bugungi/keyingi jonli dars (kohort, vaqt, mavzu); (2) davomat — bot check-in natijasi jonli ko'rinadi (TelegramLessonCheckIn→Attendance bog'i bor), qo'lda to'g'irlash (attendance upsert bor); (3) **"Darsni ochish" tugmasi** — tanlangan darsni kohortga release qiladi (`CohortLessonRelease` bor!) + vazifa aktiv + o'quvchilarga Telegram xabar (A6 bilan); (4) tekshiruv navbati (grading queue bor — havola).
- **Fakt:** hamma blok alohida qurilgan (bot davomat, release modeli, teacher grading) — bitta oqimga yig'ilmagan; release hozir faqat admin orqali.
- **Qabul:** test-kohortda to'liq sikl: `/start_lesson` bot → check-in'lar sahifada ko'rinadi → "ochish" bosildi → o'quvchi akkauntida dars ochiq + (P2'dan) xabar keldi; 3 bosqich ≤ 3 bosishda
- **Fayllar:** `core/teacher_views.py`, `templates/teacher/`, `bot/services.py`, `cohorts`/`courses` release

### ☐ A1. `word_builder` AI skilli
- **IH:** IH-6 · **Faza:** P1-h2 · **Hajm: M**
- So'z morfologiya zanjiri (ev→evim→evimde) o'zbek paralleli bilan; unli uyg'unlik vizual; mikro-mashq bilan tugaydi. Trigger: "so'z qur/qo'shimcha/suffiks/unli uyg'unlik...".
- **Qabul:** 5 jonli DO sinov; registry testlari; STICKY ro'yxatda

### ☐ A2. `conversation_partner` AI skilli
- **IH:** IH-2 · **Faza:** P1-h2 · **Hajm: M**
- Rol-o'yin (kafe/bozor/aeroport/imtihon og'zaki-suhbati!); darajaga mos; har 2–3 almashinuvda bitta yumshoq tuzatish; yakunda yangi so'zlar xulosasi (A4c'ga oziqa). Og'zaki mock'ka tayyorlovchi rejim — S1 uchun ayni muhtoj narsa.
- **Qabul:** 10+ almashinuvli jonli ssenariy oqim uzilmasdan; sticky ishlaydi

### ☐ A3. Daraja testi (placement) — kirish eshigi
- **IH:** IH-5 · **Faza:** P1-h2 · **Hajm: L**
- Anonim 15–20 savol (leksika-ko'prik / grammatika / o'qish), oddiy adaptivlik; natija: daraja + "turkchaning X%i tanish" + **"B2 gacha ~N oy — kuzgi guruh N-sentyabrda"** CTA → registratsiya → natija `UserOnboarding`ga.
- **Qabul:** anonim→natija→yozilish zanjiri; 60 savol bank; mobil silliq; natija sahifasi ulashishga arziydi

### ☐ A4. SRS lug'at ("Lug'atim") — kunlik odat yadrosi
- **IH:** retention · **Faza:** P1-h3 · **Hajm: XL → A4a modellar+SM-2 (L), A4b sessiya UI (M), A4c avto-to'ldirish darsdan+quiz xatosidan (M), A4d dashboard karta (S)**
- **Qabul:** dars o'qigan o'quvchida kartalar avto paydo; interval unit-testlari; mobilda bir qo'lda

### ☐ A5. Streak (haqiqiy)
- **Faza:** P2-h2 · **Hajm: M** · **Fakt:** `users/views.py:567` placeholder — doim 0!
- `DailyActivity` + ketma-ket kunlar + haftasiga 1 avto-freeze; dashboard + bot.
- **Qabul:** TZ-to'g'ri (Toshkent) testlar; freeze ishlaydi; placeholder o'chdi

### ☐ A6. Telegram ritm-xabarlari
- **IH:** IH-4 · **Faza:** P2-h2 · **Hajm: L** · **Fakt:** bot faqat davomat qiladi; beat bor.
- (a) jonli dars eslatmasi ("bugun 20:00 — 12-dars"); (b) dars ochildi (A0 trigger); (c) vazifa muddati; (d) kunlik "Bugungi ko'prik" (tanlangan vaqt); (e) streak xavfda; (f) chek tasdiqlandi; (g) haftalik hisobot. Har birida deep-link; settings'da boshqariladi.
- **Qabul:** real akkauntda 4+ tur xabar; o'chirish yo'li; botni start qilmaganlarga xatosiz skip

### ☐ A7. "Azure haftaligi" hisobot
- **IH:** IH-2 · **Faza:** P2-h3 · **Hajm: M**
- Hafta statistikasi + memory'dan zaif mavzular + 3-band reja; sahifa + Telegram qisqa. AI qismi yiqilsa statistika chiqadi (fail-open).

### ☐ A8. Sertifikat-tayyorgarlik % vidjeti
- **IH:** IH-3 · **Faza:** P2-h3 · **Hajm: S-M**
- Kurs progressi + mock natijalari + SRS'dan formula → "B2: 68%". Dashboard + exam center. Halol izoh bilan.

### ☐ A9. Kuzgi guruh qabul oqimi + waitlist
- **Faza:** P1 oralig'ida · **Hajm: S-M**
- Landing'da "Kuzgi guruhga yozilish" (mavjud checkout'ga ko'prik) + to'lgan/kutish holati (waitlist yozuvi). Launch'da keyingi guruh uchun ham ishlaydi.

### ☐ A10. Bepul qatlam simlari (oqim)
- **IH:** IH-7/oqim · **Faza:** P2-h3 · **Hajm: M**
- Bepul akkaunt: daraja testi, namunaviy video dars (preview bayroq), 1 yozma mock, AI-lite (AIPlanPolicy), kunlik ko'prik. Hammasi "kursga yozil" CTA bilan. Kurs obunasi = enrollment (bor oqim).
- **Qabul:** bepul akkaunt chegaralari ishlaydi; limit xabari halol; preview darsdan enrollmentga o'tish ravon

### ☐ A11. Analytics eventlar
- **Faza:** P2-h1 · **Hajm: S-M**
- Plausible/Umami + `ProductEvent` (registered, placement_*, lesson_completed, assignment_submitted, ai_message, srs_session, mock_*, receipt_*). Backoffice mini-hisobot.

### ☐ A12. PWA minimal
- **Faza:** P3-h1 · **Hajm: S** — manifest + install; offline yo'q.

---

## B. SAYQALLASH

| # | Nima | Fakt/muammo | Faza | Hajm |
|---|---|---|---|---|
| ☐ B1 | **Exam JS jonli brauzer sinovi** | 2026-07-02 e'tirofi: brauzerda sinalmagan; mock'lar tayanadi | P1-h1 | M |
| ☐ B2 | Settings AI-model ro'yxati | Gemini nomlari ko'rinadi, DO'damiz | P0 | S |
| ☐ B3 | Oltin yo'l qo'lda audit (endi: yozilish→guruh→dars→vazifa→mock) | — | P0+P3 | M |
| ☐ B4 | **Mobil audit** (360px) | guruh telefonda o'qiydi | P3-h1 | M-L |
| ☐ B5 | To'lov UX + **admin Telegram-ping** | ping yo'q; SLA 2 soat | P3-h1 | M |
| ☐ B6 | "Mening natijalarim" sahifasi (IH-7) | davomat+vazifa+quiz+mock bir joyda (qismlar bor, yig'ilmagan) | P2-h3 | M |
| ☐ B7 | Onboarding birlashtirish (daraja testi / smart form / o'tkazish) | ikkala mexanizm bor | P1-h2 (A3 bilan) | S-M |
| ☐ B8 | Bot davomat UX (guruhda jonli sinov, xatolar) | qurilgan lekin real guruhda kam ishlatilgan | P1-h1 (A0 bilan) | S-M |
| ☐ B9 | home_view eski kontekst tozalash | hero_slides qoldiq | P3 | S |
| ☐ B10 | DOCX o'qish (python-docx) | o'quvchilar Word yuboradi | P3 bo'sh kun | S-M |
| ☐ B11 | XP iqtisodi bir jadvalda (yangi manbalar: SRS, streak, davomat) | tarqoq | P2-h3 | S |
| ☐ B12 | Sertifikat oqimi e2e (final mock bilan) | dvigatel bor | P3-h2 | S |
| ☐ B13 | Bo'sh/xato holatlar yangi sahifalarda | — | P3 | S |

---

## C. KESISH (launch'gacha YO'Q)

| # | Nima | Nega | Qachon |
|---|---|---|---|
| C1 | Native mobil app | PWA yetadi | Post-launch |
| C2 | Payme/Click/Uzum | chek oqimi ishlaydi | Okt–noy |
| C3 | Speaking avto-baholash (STT) | ustoz baholaydi — bu selling point ham | Tadqiqot keyin |
| C4 | Rus interfeysi / boshqa tillar | fokus | 2027 |
| C5 | AI foto-generatsiya | DO-only byudjet qarori | Byudjet bo'lsa |
| C6 | Offline PWA | murakkab | Post-launch |
| C7 | Ko'p-o'qituvchi marketplace | bitta ustoz modeli | 2027 |
| C8 | LLM-router skill tanlash | evristika ishlayapti | Zarurat bo'lsa |
| C9 | bge-m3 embedding migratsiyasi | launch oldi xavfli qimirlatish | Oktabr |
| C10 | Real-time usage panel | sahifa-refresh yetadi | Post-launch |
| C11 | Jonli video darsni platformaga ko'chirish (o'z video-chat) | Telegram video chat ishlaydi, o'quvchilar o'rgangan — ko'chirish launch'ga keraksiz risk | 2027± |
| C12 | Sof self-study tarif (ustozsiz) | model = kurs dastagi; self-study alohida mahsulot | Post-launch, talabga qarab |
| C13 | AI-suhbatdan avto SRS-kartalar (chuqur) | shovqin riski | A4 ma'lumotiga qarab |

---

## D. Ops majburiyatlari
Deploy (P2-h1), Sentry, backup+restore mashqi, rate-limit, `SECURITY_STRICT`, bot webhook health, `/healthz` — [05-launch-ops.md](05-launch-ops.md).

## E. Sessiya tartibi
1. Faza bo'yicha band ol (A0 → A3 → A4 ustuvor) → 2. `claude/<band>` branch → 3. Qabul kriteriysi + test + marinebook → 4. Shu faylda ☐→✅.
