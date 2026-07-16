# Telegram bot qayta-arxitektura rejasi

> Muallif: Claude · 2026-07-12 · Azurbek bilan kelishilgan
> Branch: `claude/telegram-bot`
> Maqsad: bot — kompyuter ishlatmaydigan auditoriya uchun platformaning to'liq interfeysi.

## Vizyon (Azurbek talabi)

Bot uch xil auditoriyaga uch xil rejimda xizmat qiladi:

1. **Yangi user (hisobi yo'q, reklamadan kelgan)** — landing vazifasi: tanituv, kurslar, narxlar, AI bilan savol-javob (demo), ro'yxatdan o'tish voronkasi.
2. **Bog'langan user (shaxsiy chat)** — ish stoli: rolga qarab (o'quvchi / o'qituvchi / admin) platformaning core imkoniyatlari saytga kirmasdan.
3. **Dars guruhi (kohortga ulangan)** — `/...` buyruqlar bilan avtomatik DB operatsiyalari, birinchi navbatda davomat.

Davomat oqimi (etalon misol): o'qituvchi jonli efir boshlanishida guruhga `/dars 1` yozadi →
bot "Keldim" tugmali post tashlaydi → o'quvchilar bosadi → `/dars tugadi` → tugma o'chadi,
bot ismlar bilan keldi/kech/kelmadi e'lonini beradi, kelmaganlarga shaxsiy ogohlantirish DM yuboradi.

## Arxitektura tamoyillari

- **Bot = yupqa UI adapter.** Biznes-mantiq takrorlanmaydi — sayt bilan bitta Django servislari
  chaqiriladi (davomat `bot/services.py` allaqachon shu uslubda: `upsert_attendance_and_xp`,
  huquq tekshiruvi, kech qolish). AI ham: messenger'dagi tayyor engine (skill, xotira, kvota).
- **Modulli router'lar** (aiogram 3 `Router` per modul) + identity-middleware
  (har update'da telegram_id → user + rol bir marta aniqlanadi).
- **FSM** ko'p bosqichli oqimlar uchun (ro'yxatdan o'tish, forma to'ldirish).
- **Notification outbox**: platforma hodisalari (to'lov, yangi dars, baho, davomat ogohlantirishi)
  → navbat jadvali → yuboruvchi worker (Telegram rate-limit ~30 msg/sek hisobga olinadi).
- **Lazy Bot init**: `bot/aiogram_app.py` hozir import vaqtida `Bot(token=...)` quradi —
  bo'sh token butun loyihani yiqitadi (runserver/check/migrate). F0'da tuzatiladi.

## Qatlamlar sxemasi

```
Kirish (webhook prod / polling dev)
  └─ Identity middleware (telegram_id → user + rol)
       ├─ Shaxsiy chat, bog'lanmagan  → ONBOARDING router
       ├─ Shaxsiy chat, bog'langan    → WORKSPACE router (rolga qarab menyu)
       └─ Guruh chat (kohortga ulangan) → GROUP_OPS router
            └─ Service facade qatlami → Django domenlar
               (cohorts, courses, subscriptions, messenger AI, aicontrol)
```

## Bosqichlar

| # | Nima | Tarkib | Holat |
|---|------|--------|-------|
| **F0** | Skelet | Lazy Bot init, identity-middleware, modulli router tuzilma (`bot/routers/`), o'zbekcha buyruqlar, xatolik-qatlami | ✅ 2026-07-12, jonli sinalgan |
| **F1** | Davomat v2 | `/dars N`, `/dars tugadi`, `/davomat` (holat); ismli keldi/kech/kelmadi e'loni; kelmaganlarga DM ogohlantirish (bog'lanmaganlar guruhda @mention) | ✅ 2026-07-12, jonli sinalgan |
| **F2** | Onboarding voronkasi | Tanituv, kurslar/narxlar, AI demo savol-javob (5 savol, BotGuest), **ikki yo'lli ro'yxat**: (a) telefon-kontakt bilan bot ichida, (b) sayt havolasi + token | ✅ 2026-07-12, jonli sinalgan |
| **F3** | O'quvchi workspace + AI | Menyu: /darslarim (progress), /davomatim, /tolov; erkin matn → messenger AI engine ("Telegram AI suhbati" xonasi) | ✅ 2026-07-12 |
| **F3.5** | Kursga yozilish | /yozilish → kurs → tarif → rekvizitlar (SiteSettings karta) → chek rasmi → PaymentReceipt (sayt checkout servislari) | ✅ 2026-07-12 |
| **F4** | O'qituvchi + Admin + Outbox | /guruhlarim, /baholash; admin: /stat, /cheklar (rasm + tasdiqlash/rad tugmalari); Notification→DM outbox (signal + worker) | ✅ 2026-07-12, outbox jonli isbotlangan |
| **F5** | Mini App qatlami | initData HMAC auth-ko'prik (`/bot/miniapp/` + `/bot/miniapp/auth/`), avto-login, open-redirect himoya; public domenda web_app menyu tugmasi (lokalda avto-fallback) | ✅ 2026-07-13 — ko'prik tayyor; to'liq webview sinovi prod HTTPS'da |

Keyingi navbat: admin broadcast, o'qituvchi e'loni, prod deploy (alohida bot token,
webhook, `telegram_outbox --loop`), Mini App'ni og'ir sahifalarga yoyish
(mobil-moslashuv rejasi bajarilgach).

> Yangilanish 2026-07-13: F6 (admin kengaytmasi: /qidiruv, /broadcast, /ai_stat) va
> F7 (AI nazorat: /ai_sozlama, /ai_limit, /ai_tarif, /ai_reset, /ai_bonus, user-blok)
> ham bajarildi. Quyida 2-qism rejasi.

---

# 2-QISM: To'liq quvvatli alternativ (F8–F13)

> Maqsad (Azurbek, 2026-07-13): saytga kirolmaydigan foydalanuvchi uchun bot
> platformaning TO'LIQ o'rnini bossin — nafaqat kuzatuv, balki O'QISH ham.

## Hozirgi kamchilik xaritasi

1-qism (F0–F7) "atrofdagi" hamma narsani qopladi: ro'yxat, yozilish, to'lov,
davomat, kuzatuv, AI, admin-pult. Yetishmayotgan yadro — **dars jarayonining o'zi**:
o'quvchi botdan turib darsni KO'RA olmaydi, vazifa TOPSHIRA olmaydi, quiz/imtihon
YECHA olmaydi, sertifikatini OLA olmaydi. O'qituvchi baholay olmaydi. Shu 2-qism
aynan shularni yopadi.

Model-tayyorlik tekshirildi: `Lesson.video_url` (YouTube unlisted havola),
`Lesson.content` (HTML → matnga o'giriladi), Quiz=MCQ (inline tugmalarga ideal),
`ExamAttempt.answer_text` (writing=matn xabar) + `audio_file_url` (speaking=Telegram
ovozli xabar) — hammasi chat-interfeysga yotadi.

## Fazalar

| # | Faza | Tarkib | Hajm |
|---|------|--------|------|
| **F8** | **Dars-yetkazish (botda o'qish)** — yadro | /darslarim → kurs → modul/dars ro'yxati (✅ o'tilgan / 🔒 qulf, sayt lock-mantig'i bilan); dars ochish: video tugmasi (YouTube unlisted), kontent HTML→matn (bo'laklab), "✅ Darsni tugatdim" → LessonProgress+XP (sayt servisi); deep-link `t.me/bot?start=dars_ID` — davomat ogohlantirishidagi havola endi botning o'zida ochiladi; "🤖 Shu dars bo'yicha savol" → AI repetitorga dars-kontekst | ~1.5 kun |
| **F9** | **Vazifa va quiz** | Dars ichida 📝 Vazifa: topshiriq → javob matn/foto/fayl → AssignmentSubmission (pending) → o'qituvchi navbatiga; baholanganda DM (outbox tayyor). ❓ Quiz: savollar inline tugmalar bilan ketma-ket, mavjud quiz-submit servisi, natija+XP darhol | ~1 kun |
| **F10** | **Prod-ga chiqarish** ⚡ | Alohida prod bot + BotFather profil (rasm/description); webhook + secret; `telegram_outbox --loop` alohida worker (DO App Platform/Procfile); deploy'da setup_bot_commands; Mini App Menu Button aktivatsiyasi (mobil-moslashuv tuzatishlari bilan birga); media file_id keshi; xatolik-monitoring (kritik xato → admin DM); rate hardening | ~1.5 kun |
| **F11** | **Imtihon va sertifikat** | /imtihonlarim (jadval/holat/natija); topshirish v1: MCQ tugmalar, writing=matn, speaking=ovozli xabar (mavjud audio-upload oqimiga); vaqt nazorati xabarda; murakkab holat uchun Mini App'ga yo'naltirish opsiyasi. /sertifikatlarim: ro'yxat + PDF/rasm chatga | ~2 kun |
| **F12** | **O'qituvchi to'liq ish stoli** | /baholash interaktiv: ishni ochish (matn/fayl) → baho + izoh → o'quvchiga avto-DM; guruhga e'lon botdan; dars eslatmalari (jadval bo'yicha guruhga avto-post) | ~1 kun |
| **F13** | **Profil/reyting/polish** | /reyting (leaderboard), /profil (ism, AI tone/model sozlash), /yordam FAQ DB'dan; onboarding→yozilish→to'lov→o'qish voronkasining uzluksizligini end-to-end tekshirish | ~1 kun |

**Tavsiya tartibi:** F8 → F9 → **F10 (prod!)** → F11 → F12 → F13.
Sabab: F8+F9 bilan bot haqiqiy "o'qish joyi"ga aylanadi — shu zahoti prod'ga
chiqarib real o'quvchilarga berish kerak (20-sentyabr launch'iga zaxira vaqt
qoladi), qolgan fazalar jonli foydalanish ustiga iterativ qo'shiladi.

## Halol chegaralar (qabul qilingan)

- **Video himoyasi yo'q**: YouTube unlisted havola/Telegram fayl forward qilinishi mumkin — saytdagi bilan bir xil daraja, qo'shimcha DRM rejalashtirilmagan.
- **Imtihon halolligi**: botda taymer "yumshoq" (xabar vaqtlari bilan), sayt darajasidagi nazorat yo'q — jiddiy imtihonlar uchun Mini App/sayt tavsiya etiladi, botdagi rejim mashq-imtihonlar uchun.
- **FSM holati**: polling'da xotirada; webhook prod'da ko'p-jarayonlik bo'lsa DB-storage kerak bo'ladi (F10'da hal qilinadi — hozirgi oqimlar ataylab stateless qurilgan).

## Sinov strategiyasi (1-qismdagidek)

Har faza: servis-testlar (bot suite) + to'liq regressiya + Azurbek telefon-sinovi
→ marinebook yozuvi → commit. F10'dan keyin sinovlar prod botda staging-kohort bilan.

## Sinov strategiyasi

1. **Avtomatik** (har bosqich): servis testlari (mavjud `bot/tests.py` uslubi) + handler testlari
   soxta Telegram update bilan (tarmoqsiz). To'liq to'plam regressiya uchun.
2. **Jonli** (Azurbek telefondan): polling (`run_bot.py`) — public URL kerak emas; test-guruh +
   lokal debug ma'lumotlar (4-kohort, debug userlar). Kod → avtotest → "telefondan sinang" →
   DB'dan tasdiqlash sikli.
3. **Token siyosati (Azurbek qarori, 2026-07-12):** joriy bot devda ishlatiladi;
   production uchun keyinroq ALOHIDA bot ochiladi.

## Cheklovlar (bilingan holda qabul qilingan)

- Bot DM faqat botni bir marta ochgan userga ketadi — bog'langanlar OK, qolganlarga guruhda @mention.
- Uzun kontent/murakkab formalar sof chatda noqulay → Mini App (F5).
- Video 2GB'gacha yuborish mumkin, lekin forward-himoyasiz.

## Bog'liq hujjatlar

- Davomat mexanikasi: `bot/services.py` (start/checkin/close, Attendance+XP yozuvi)
- Mobil-moslashuv auditi va reja: marinebook 2026-07-12 yozuvi (Mini App F5 shunga tayanadi)
