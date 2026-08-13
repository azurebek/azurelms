# Telegram bot qayta-arxitektura rejasi

> Muallif: Claude · 2026-07-12 · Azurbek bilan kelishilgan
> Branch: `claude/telegram-bot`
> Maqsad: bot — kompyuter ishlatmaydigan auditoriya uchun platformaning to'liq interfeysi.

> **Rebaseline 2026-08-14:** F0–F9 va Mini App foundation main'da. DigitalOcean/public production `HOLD`; joriy ish Telegram polling + local app. F10 production gate vendor-neutral bo'lib, owner productionni qayta ochmaguncha active task emas. Gemini bot AI uchun ham umumiy free-tier budgetdan tashqarida emas.

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
- **Lazy Bot init**: `bot/aiogram_app.py` bo'sh token bilan runserver/check/migrate'ni yiqitmaydi — F0'da bajarilgan.

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

F6/F7 admin broadcast va AI controls, F8 dars yetkazish hamda F9 assignment/quiz keyinroq main'ga qo'shilgan. Joriy navbat production emas: A8 Gemini free-tier guard, local bot regression/phone QA va core canonical flow parity. Teacher to'liq interactive grading, exam/certificate va reminderlar alohida `NEXT`.

> Yangilanish 2026-07-13: F6 (admin kengaytmasi: /qidiruv, /broadcast, /ai_stat) va
> F7 (AI nazorat: /ai_sozlama, /ai_limit, /ai_tarif, /ai_reset, /ai_bonus, user-blok)
> ham bajarildi. Quyida 2-qism rejasi.

---

# 2-QISM: To'liq quvvatli alternativ (F8–F13)

> Maqsad (Azurbek, 2026-07-13): saytga kirolmaydigan foydalanuvchi uchun bot
> platformaning TO'LIQ o'rnini bossin — nafaqat kuzatuv, balki O'QISH ham.

## Hozirgi kamchilik xaritasi

F8/F9 bilan darsni ko'rish, assignment topshirish va quiz botda ishlaydi. Hali to'liq bo'lmagan yadro: exam/certificate, teacher interactive grading/reminder, public webhook/outbox process va production WebView. `/baholash` queue bor, lekin F12ning to'liq workflow'i emas.

Model-tayyorlik tekshirildi: `Lesson.video_url` (YouTube unlisted havola),
`Lesson.content` (HTML → matnga o'giriladi), Quiz=MCQ (inline tugmalarga ideal),
`ExamAttempt.answer_text` (writing=matn xabar) + `audio_file_url` (speaking=Telegram
ovozli xabar) — hammasi chat-interfeysga yotadi.

## Fazalar

| # | Faza | Tarkib | Holat |
|---|------|--------|------|
| **F8** | **Dars-yetkazish (botda o'qish)** | Saytdagi lesson access/progress service'lari, video/kontent/deep-link | `IMPLEMENTED/TESTED`; phone QA pending |
| **F9** | **Vazifa va quiz** | `BotPendingAction` DB state, canonical assignment/quiz service, result+XP | `IMPLEMENTED/TESTED`; phone QA pending |
| **F10** | **Vendor-neutral production gate** | Alohida production bot qarori, webhook+unique secret, outbox process, commands/menu button, monitoring/rate hardening | `HOLD` — DO target emas; owner productionni qayta ochadi |
| **F11** | **Imtihon va sertifikat** | `/imtihonlarim`, bounded bot practice, complex flow Mini App; `/sertifikatlarim` | `PLANNED`, active emas |
| **F12** | **O'qituvchi to'liq ish stoli** | Queue mavjud; interactive grade+comment, e'lon va reminder qolgan | `PARTIAL / NEXT` |
| **F13** | **Profil/reyting/polish** | Yordam/Mini App entry primitive'lari bor; leaderboard/profile/E2E qolgan | `PARTIAL / NEXT` |

**Joriy tartib:** `A8 Gemini budget → A0b/A1a → core flow bilan birga local F0–F9 parity/phone QA → owner tanlagan F11 yoki F12`. F10 faqat production `HOLD` ochilganda; bot feature tayyorligi cloud deployga o'z-o'zidan ruxsat bermaydi.

## Halol chegaralar (qabul qilingan)

- **Video himoyasi yo'q**: YouTube unlisted havola/Telegram fayl forward qilinishi mumkin — saytdagi bilan bir xil daraja, qo'shimcha DRM rejalashtirilmagan.
- **Imtihon halolligi**: botda taymer "yumshoq" (xabar vaqtlari bilan), sayt darajasidagi nazorat yo'q — jiddiy imtihonlar uchun Mini App/sayt tavsiya etiladi, botdagi rejim mashq-imtihonlar uchun.
- **Ko'p bosqichli holat:** assignment/quiz oqimlari `BotPendingAction` DB state bilan restartga chidamli. Yangi F11–F13 flow xotira FSM'iga suyanmasdan shu pattern yoki canonical state ishlatadi.

## Sinov strategiyasi

1. **Avtomatik** (har bosqich): servis testlari (mavjud `bot/tests.py` uslubi) + handler testlari
   soxta Telegram update bilan (tarmoqsiz). To'liq to'plam regressiya uchun.
2. **Jonli** (Azurbek telefondan): polling (`run_bot.py`) — public URL kerak emas; test-guruh +
   lokal debug ma'lumotlar (4-kohort, debug userlar). Kod → avtotest → "telefondan sinang" →
   DB'dan tasdiqlash sikli.
3. **Token siyosati (2026-08-14):** joriy `@azureLMSbot` local/polling integratsiya uchun ishlatiladi. Alohida production bot, webhook va public Menu Button faqat production qayta admissionida ko'riladi.
4. **Evidence yozuvi:** har admitted faza test + telefon QA → marinebook → commit. F10 production admissioni ochilsa, staging-kohort/prod-bot sinovi alohida gate bo'ladi.

## Gemini free-tier siyosati

- Bog'langan user botdan ham Messenger bilan bir canonical quota/budget gate'ni ishlatadi; alohida “bot AI” supply yo'q.
- F2 guest demo hozir har qanday unlinked user uchun ochiq va faqat 5 savol bilan cheklangan; selected-user allowlist/kill switch **mavjud emas**. Direct provider call `AIResponseRun` ledgeriga to'liq kirmaydi. A8 acceptance guest AI'ni server-side allowlist/default-off qiladi yoki deterministic FAQ/1–2 bounded demoga almashtiradi; owner bungacha ommaviy bot reklamasini ochmaydi.
- `heavy` web search, Pro/preview model va retry fan-out botdan yoqilmaydi.
- Budget/circuit ochiq bo'lsa bot core menu, kurs, payment, lesson, assignment/quiz va human handoffni AI'siz davom ettiradi.

## Cheklovlar (bilingan holda qabul qilingan)

- Bot DM faqat botni bir marta ochgan userga ketadi — bog'langanlar OK, qolganlarga guruhda @mention.
- Uzun kontent/murakkab formalar sof chatda noqulay → Mini App (F5).
- Video 2GB'gacha yuborish mumkin, lekin forward-himoyasiz.

## Bog'liq hujjatlar

- Davomat mexanikasi: `bot/services.py` (start/checkin/close, Attendance+XP yozuvi)
- Mobil-moslashuv auditi va reja: marinebook 2026-07-12 yozuvi (Mini App F5 shunga tayanadi)
