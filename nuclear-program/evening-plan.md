# Kechgi ish rejasi — 2026-07-06

Bugungi holat: AI qatlami sezilarli kengaydi va **hammasi `main`da jonli** — shaxsiyat, PDF (o'qish/yaratish), vision (rasm ko'rish), SVG chizish, gibrid web-qidiruv (Gemini faqat qidiruvda), admin token-boshqaruv markazi, o'quvchi foydalanish paneli. `python manage.py test` — 239/239 OK.

Quyida qiymat/mehnat bo'yicha tartiblangan nomzodlar. Kechqurun tanlaymiz.

---

## A. AI'ni yaxshiroq o'qituvchi qilish  ⭐ (eng katta qiymat, kam xavf, jonli DO bilan sinaladi — sof prompt)

- [ ] **A1. `conversation_partner` — jonli suhbat mashqi** 🥇
  "Kel, kafeda ovqat buyurishni turkchada mashq qilaylik." Darajaga moslashadi, turkchada qoladi, yumshoq tuzatadi. AI-repetitordan eng ko'p istaladigan narsa — hozir yo'q. (~1 soat)

- [ ] **A2. `word_builder` — turkcha so'z tuzilishi** 🥈
  `ev → evim → evimde → evimdekiler`, unli uyg'unlik. Aynan o'zbek auditoriyasi uchun oltin ("buni o'zbekchadan bilasan" ko'prigi). (~1 soat)

- [ ] **A3. `vocab_coach` — lug'at takrori (spaced repetition)**  *(kattaroq — alohida sessiya)*
  Retention bo'shlig'i. Yengil "bilingan so'zlar" ma'lumot qatlami kerak; bir kechga sig'masligi mumkin.

## B. Nomuvofiqlik / tozalash  (aniqlik, tez)

- [ ] **B4. Settings'dagi AI model tanlovi Gemini nomlarini ko'rsatadi** — biz DO maverick'da ishlaymiz, chalg'itadi. AISettings/DO modellariga ulash yoki olib tashlash. (~40 daq)
- [ ] **B5. home_view eski kontekst qoldiqlari** (hero_slides, portal_tabs) — zararsiz, tozalansa toza bo'ladi. (~20 daq)
- [ ] **B6. DOCX o'qish** (python-docx) — PDF quvuriga bitta reader; Word hujjatlarini ham o'qiydi. (~40 daq)

## C. Tekshirish / deploy  (muhim, ishtirok kerak)

- [ ] **C7. Jonli brauzer sinovi** — `runserver` bilan ochib PDF/rasm/qidiruv/limit panelini bosib-tekshirish. Exam JS (recorder/audio/autosave) hali brauzerda ko'rilmagan.
- [ ] **C8. Deploy env** — `GEMINI_API_KEY`ni serverga qo'shish (web-qidiruv uchun). Procfile/env hujjati tayyorlanadi.

---

## Tavsiya (bir kecha uchun)

**A1 + A2 + B4** — ikkita yangi o'qituvchi-skill (suhbat + so'z tuzilishi), orada settings model-tanlovini to'g'irlash. Hammasi jonli DO bilan sinaladi, main'ga qo'shiladi. Mazmunli, ko'rinadigan, xavfsiz. ~2.5–3 soat.

> Qaytганda: "A rejadan boshla" yoki tanlagan raqamlarni ayt — darhol kirishaman.
