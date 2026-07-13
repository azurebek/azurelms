# 05 — Launch operatsiyalari: deploy, kuzgi guruh (beta), QA, taqdimot, marketing

---

## 1. Deploy arxitekturasi (P2-h1, 6–12 avgust)

**Platforma: DigitalOcean App Platform** (kredit bor, Procfile/Dockerfile tayyor, AI ham DO'da).

| Komponent | Xizmat | Eslatma |
|---|---|---|
| Web | Daphne (8080) | ASGI — websocket |
| Worker | celery worker | AI, PDF/rasm |
| Beat | celery beat | Telegram ritm-xabarlari, obuna lifecycle |
| DB | Managed PostgreSQL + **pgvector** | `setup_rag_pgvector` kun-1 |
| Cache/Channels | Managed Valkey | `VALKEY_URL` |
| Media | Spaces (`USE_S3=True`) | chek rasmlari, exam audio, PDF |
| Static | Whitenoise | bor |

**Env-parad:** `SECRET_KEY` (yangi) · `APP_ENV` · `APP_DOMAIN`/`ALLOWED_HOSTS`/`CSRF_TRUSTED_ORIGINS` · `SECURITY_STRICT=True` · `DATABASE_URL` · `VALKEY_URL` · Spaces kalitlari · `DIGITALOCEAN_INFERENCE_API_KEY`+model · `GEMINI_API_KEY` · `TELEGRAM_BOT_TOKEN` + `TELEGRAM_MODE=webhook` + `setwebhook` · Email provayder (parol tiklash — Resend/Brevo bepul qatlam; P0 qarori).

**Ma'lum tuzoqlar:** bo'sh TELEGRAM_BOT_TOKEN boot'ni yiqitadi (eager Bot init — hujjatlangan); Dockerfile py3.12 vs lokal 3.14 drift — deploy oldi tekshiruv.

**Amaliyot:** `main` → auto-deploy. Bitta muhit: launch'gacha "yopiq prod" (kuzgi guruh ishlatadi), 20-sen shu ochiladi.

## 2. Kuzatuv va zaxira (P2-h1)

- **Sentry** (Django+Celery, bepul qatlam) · **UptimeRobot** (`/`, login, websocket) · `/healthz` (DB+cache ping)
- **Backup:** managed PG kunlik snapshot + haftalik `pg_dump` → Spaces; **restore mashqi P2'da majburiy**
- AI telemetriya: AIResponseRun (bor) — backoffice AI-boshqaruv paneli (bor)

## 3. Xavfsizlik o'tishi (P4)

- [ ] `SECURITY_STRICT=True` barcha oqimlar (CSP: YouTube embed buzilmasin — video darslar!)
- [ ] Rate-limit: login/registratsiya/AI/upload · [ ] Upload validatsiya ko'rik (chek, audio, messenger)
- [ ] `ENABLE_LEGACY_ADMIN=False`, backoffice faqat staff · [ ] DEBUG=False xato sahifalari jonli
- [ ] Secrets audit (git tarixi) · [ ] `check --deploy` toza

## 4. QA rejasi (P3-h2)

**Matritsa: oqim × (desktop Chrome, Android Chrome, iOS Safari) × (bo'sh, to'la akkaunt).**

Oqimlar: registratsiya/login/parol-tiklash · daraja testi (anonim→saqlash) · **kuzgi guruh o'quvchi sikli:** dars ochilishi xabari → video → konspekt/lug'at → quiz → vazifa topshirish → SRS sessiya → streak · AI chat (matn/rasm/PDF/limit) · **mock imtihon to'liq** (tinglash replay → yozish so'z-hisob → og'zaki yozish → submit → ustoz baholash → natija) · chek→tasdiq→enrollment · **ustoz sikli:** dars kuni sahifasi → bot davomat → ochish → tekshiruv navbati → baholash · backoffice amallar.

**Maxsus:** og'zaki mock real telefonda (mikrofon ruxsati, MediaRecorder Safari farqlari); websocket reconnect; video embed mobil trafikda.

Bug-bar: P0 (oltin yo'l/ma'lumot yo'qotish) darhol · P1 launch'gacha · P2 backlog.

## 5. Kuzgi guruh = beta (1–16 sentyabr)

**Bu klassik beta emas — real mijozlar, real to'lov, real darslar.** Shuning uchun himoya choralari:

- **Zaxira kanal:** mavjud Telegram guruh tirik qoladi — platforma yiqilsa dars baribir o'tadi, material guruhga tashlanadi (o'quvchi hech narsa yo'qotmaydi). Bu va'da guruhga e'lon qilinadi — ishonch.
- **1-hafta protokoli:** har dars kuni kechqurun triyaj (analytics + guruh feedback + Sentry) → tungi fix → ertalab deploy.
- **Kutish sozlamasi:** guruhga "yangi tizim — takliflaringiz shakllantiradi" ramkasi; birinchi hafta uchun kichik bonus (premium-limit).
- **To'lqin-2 (5-sen):** kanaldan 10–15 kishi **bepul qatlamga** (daraja testi→mock№1→AI-lite) — sotuv-oqim sinovi, guruhga tegmaydi.
- **Yig'im:** eventlar + 3 so'rovnoma (1-kun taassurot / 4-kun to'siqlar / 7-kun NPS + narx-savol + testimonial rozilik).

## 6. Taqdimot — 20-sentyabr (8–10 daqiqa)

*Ustunlik: 3 haftalik REAL guruh ma'lumoti bilan chiqamiz — "demo" emas, "hisobot". Qahramon: "Madina, magistratura talabgori, B2 kerak".*

| Daq | Sahna | "Vau" |
|---|---|---|
| 0–1 | **Muammo (zal biladi):** magistraturaga sertifikat majburiy (buyruq slaydi: B1/B2/C1) — ingliz B2 = yillar | Og'riq real, raqamlar rasmiy |
| 1–2 | **Yechim mantiqi:** turkcha qardosh — B2 yetadi (izoh slaydi) + 3 ko'prik jonli (zal: "bor?" — "var!") + UZBMB'da 5200 kishi topshiryapti | Zal o'zi ishonch hosil qiladi |
| 2–3 | **Kurs modeli:** jonli ustoz darsi (bu o'zgarmaydi) + platforma nima qo'shadi — 1 slayd (01 §0 jadval) | "App emas — tizimli kurs" |
| 3–5 | **Bir o'quvchining haftasi (jonli ekran):** Telegram'da "dars ochildi" → video+konspekt → quiz → vazifa fotosi → **Azure AI o'qib, xatoni o'zbekcha tushuntiradi, zaif mavzuni eslab qoladi** → ertasi shaxsiy mashq | AI zanjiri — hech kimda yo'q 2 daqiqa |
| 5–6.5 | **Mock imtihon:** yozma bo'lim ekrani (timer, tinglash-limit) → natija → "B2: 68% tayyor" → og'zaki yozish | "Imtihondan o'tamanmi?"ga javob |
| 6.5–7.5 | **Ustoz paneli:** dars kuni sahifasi — davomat (bot), bir tugmada dars ochish, tekshiruv navbati | Boshqa kurslar buni qila olmaydi |
| 7.5–8.5 | **3 haftalik real raqamlar:** kuzgi guruh davomati, vazifa %, AI savollar soni, birinchi mock o'rtachasi + 1–2 testimonial | Isbot, va'da emas |
| 8.5–10 | **Taklif:** daraja testi QR (zal topshiradi!) + kuzgi-2 guruh qabuli + launch-taklif | Harakat |

**Texnik:** demo-akkauntlar (Madina + ustoz), oldindan yozilgan vazifa-foto, zaxira internet (hotspot), **fallback: 3-daq yozib olingan demo**, AI kutish-lahzalari uchun gap-skript. Repetitsiya 18 va 19-sen, savol-mashqi: "AI xato qilsa?" (ustoz-qatlam + halollik), "nega app emas?" (sertifikat app bilan olinmaydi), "narx?" (repetitor/markaz solishtiruvi).

## 7. Launch checklist (P4 oxiri 100%)

**Texnik:** `check --deploy` toza · testlar yashil · domen+SSL · robots/sitemap/OG · Sentry jonli · uptime 2 hafta · backup restore sinalgan · rate-limit · 404/500 · webhook barqaror · beat ishlayapti (log) · AI limitlar launch qiymatida · DO kredit balansi.

**Mahsulot:** oltin yo'l 3 qurilmada video-tasdiq · daraja testi anonim OK · kuzgi guruh 3 hafta uzilishsiz · mock №1–2 + og'zaki jonli · sertifikat oqimi sinalgan · narx sahifa to'g'ri · promo-kod ishlaydi · legal sahifalar dolzarb.

**Marketing:** landing yangi pozitsiya + testimoniallar + demo video · kanal 300+ · 10 post navbatda · waitlist xabari tayyor · taqdimot + fallback + demo-akkauntlar.

## 8. Marketing kalendari

| Sana | Harakat |
|---|---|
| P0–P1 | Bitiruvchi testimoniallari yig'iladi (eng qimmat aktiv) |
| ~10-avg | TG kanal start: ko'priklar + "sertifikat yo'li" seriyasi (buyruq faktlari — odamlar talablarni bilmaydi, biz tushuntiramiz) |
| 25-avg | **Kuzgi guruh qabuli e'loni** (joylar cheklangan — realdir ham) |
| 1-sen | "Guruh boshlandi" kontenti: birinchi dars, platforma skrinshotlari |
| 5-sen | Bepul qatlamga 15 kishi (to'lqin-2) e'loni |
| 10-sen | "Launch'ga 10 kun" + waitlist'ga xabar |
| 18-sen | Demo video premyera |
| **20-sen** | Taqdimot → ommaviy ochilish posti → launch-taklif (72 soat) → daraja testi keng targ'ib |
| 21–27 sen | Har kuni 1 post: imzo-harakatlar birma-bir + guruh natijalari + kuzgi-2 qabul |

**Tamoyillar:** har post o'zi qiymatli (mini-dars/fakt); bitta CTA (ko'pincha daraja testi); Azure AI skrinshotlari bilan javob berish — mahsulot o'zi kontent; **ustoz yuzi va ovozi** — ishonch shaxsdan (video-postlar Azurbekdan, texnik postlar Azure'dan).

## 9. Launch kuni protokoli (20-sen)

T-2s: health to'liq, demo-akkauntlar toza, monitoring ochiq → taqdimot (hotspot, fallback USB+bulut) → T+0: e'lon → har 2 soat: Sentry/server/registratsiya/feedback → hotfix yo'li: `hotfix/` → test → main → deploy (≤15 daq) → AI limit klapani (aicontrol) → kun yakuni: raqamlar + marinebook yozuvi.
