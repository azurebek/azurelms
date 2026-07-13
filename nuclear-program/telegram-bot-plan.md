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
