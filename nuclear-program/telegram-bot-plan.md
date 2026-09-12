# Telegram bot qayta-arxitektura rejasi

> Muallif: Claude · 2026-07-12 · Azurbek bilan kelishilgan
> Branch: `claude/telegram-bot` (ish `main` da; branch 2026-09-10 da o'chirilgan)
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
- **Ko'p bosqichli oqim holati DB'da** (`BotPendingAction`), xotiradagi FSM'da emas — 2026-09-11 auditi: kodda bitta `StatesGroup` yo'q va bu ataylab shunday. Xotira FSM'i process restartida yo'qoladi, ya'ni vazifa yozayotgan o'quvchi deploy paytida javobini boy beradi.
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
| **F10** | **Vendor-neutral production gate** | Alohida production bot qarori, webhook+unique secret, outbox process, commands/menu button, monitoring/rate hardening | `PARTIAL` — owner 2026-09-10 da AWS'ni tanladi, ya'ni gate ochildi. **Bajarildi:** webhook + unique secret fail-closed (`setwebhook` secret'siz ishga tushmaydi), outbox alohida process (PR #97: `Procfile` + compose `outbox` servisi), rate/retry hardening (PR #101: `bot/retry_policy.py` — 429 backoff, dead-letter, yuborish oralig'i). **Qolgan (owner 2026-09-11 da keyinga qoldirdi):** qurish davomida mavjud `@azureLMSbot` lokal polling bilan ishlatiladi; alohida production bot tokeni, public domenda Menu Button/commands va haqiqiy webhook production ochilganda ko'riladi |
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
2. **Jonli** (Azurbek telefondan): polling (`python manage.py runbot`) — public URL kerak emas; test-guruh +
   lokal debug ma'lumotlar (4-kohort, debug userlar). Kod → avtotest → "telefondan sinang" →
   DB'dan tasdiqlash sikli.
3. **Token siyosati (2026-08-14):** joriy `@azureLMSbot` local/polling integratsiya uchun ishlatiladi. Alohida production bot, webhook va public Menu Button faqat production qayta admissionida ko'riladi.
4. **Evidence yozuvi:** har admitted faza test + telefon QA → marinebook → commit. F10 production admissioni ochilsa, staging-kohort/prod-bot sinovi alohida gate bo'ladi.

## Gemini free-tier siyosati

- Bog'langan user botdan ham Messenger bilan bir canonical quota/budget gate'ni ishlatadi; alohida “bot AI” supply yo'q.
- F2 guest demo A8 dan keyin **default-off** (`AISettings.guest_demo_enabled`) va global supply reservation/reconciliation ledgeriga ulangan; yoqilganda unlinked user uchun 5 muvaffaqiyatli savol bilan cheklanadi. Selected-user allowlist yo'q — rollout system-wide flag bilan boshqariladi. PR #59 hisoblagich oshishini `F()` bilan atomik qildi, ammo parallel check→provider→increment oralig'i lease emas; bu K11 closeout bandi.
- `heavy` web search, Pro/preview model va retry fan-out botdan yoqilmaydi.
- Budget/circuit ochiq bo'lsa bot core menu, kurs, payment, lesson, assignment/quiz va human handoffni AI'siz davom ettiradi.

## Cheklovlar (bilingan holda qabul qilingan)

- Bot DM faqat botni bir marta ochgan userga ketadi — bog'langanlar OK, qolganlarga guruhda @mention.
- Uzun kontent/murakkab formalar sof chatda noqulay → Mini App (F5).
- Video 2GB'gacha yuborish mumkin, lekin forward-himoyasiz.

## Bog'liq hujjatlar

- Davomat mexanikasi: `bot/services.py` (start/checkin/close, Attendance+XP yozuvi)
- Mobil-moslashuv auditi va reja: marinebook 2026-07-12 yozuvi (Mini App F5 shunga tayanadi)

---

# 3-QISM: Keskin takomillashtirish rejasi (T1–T8)

> Muallif: Claude · 2026-09-11 · **Taklif** — scope qarori Azurbekda.
> Asos: shu kunda `main` (`2635453`) ustida o'tkazilgan kod auditi. Har band
> o'lchangan faktga tayanadi; taxminlar alohida belgilangan.

## Auditning raqamlari

| O'lchov | Qiymat | Izoh |
|---|---|---|
| Bot kodi | ~9 300 satr (`bot/`), shundan `services.py` **2 343** | Bitta fayl butun facade'ni ko'taradi |
| Router | 4 ta (`group_ops`, `staff`, `workspace`, `onboarding`) | Tartib `__init__.py` da, catch-all oxirida |
| Buyruq | **23 ta** slash buyruq | Menyuda: 8 private, 9 admin, 3 guruh |
| Doimiy klaviatura | **yo'q** | `ReplyKeyboardMarkup` faqat telefon ulashish uchun |
| Identity narxi | har update'ga **3 DB so'rovi** | `user` + `Course.instructor.exists` + `Enrollment.exists`, kesh yo'q |
| Proaktiv xabar triggerlari | **11 ta**, hammasi **reaktiv** | Voqea sodir bo'lgandan **keyin** yuboriladi |
| Beat jadvali | **2 ta** task | Obuna lifecycle (03:05), streak undash (19:00) |
| Bot tomonidagi metrika | **yo'q** | Outbox'da heartbeat bor, handler yo'lida hech narsa yo'q |

## Avval: nima allaqachon yaxshi (qayta qurilmaydi)

Audit bir necha taxminni **rad etdi** — bu bandlarga vaqt sarflanmaydi:

- **Xato qatlami bor.** `bot/routers/__init__.py::error_boundary` har handler xatosini
  ushlaydi, logga yozadi va foydalanuvchiga javob beradi. "O'lik tugma" holati yo'q.
- **Xabar uzunligi boshqarilgan.** `TG_MESSAGE_LIMIT = 4000` bilan bo'lib yuborish,
  guruh ro'yxatlarida `MAX_NAMES_PER_LIST = 60`.
- **Holat restartga chidamli.** Reja hujjati arxitektura tamoyillarida FSM deb yozgan,
  amalda esa `BotPendingAction` (DB) ishlatiladi — **bu yaxshiroq** va hujjatning o'z
  "halol chegaralar" bo'limi shuni tasdiqlaydi. Tamoyillar ro'yxati shu bilan tuzatildi.
- **Proaktiv kanal tayyor va mustahkam.** `users.Notification` yaratilsa
  `bot/signals.py` uni avtomatik `TelegramOutbox` ga ko'chiradi; navbat esa 2026-09-11
  dan `429` backoff, dead-letter va yuborish oralig'i bilan ishlaydi (PR #101).
  **Ya'ni yangi xabar turi qo'shish uchun kanal qurish kerak emas** — faqat trigger.

## Asosiy tashxis

Bot **imkoniyat jihatidan to'liq, boshqarish jihatidan qiyin va jim**.

1. **Navigatsiya yo'q, buyruq ro'yxati bor.** 23 ta slash buyruq. Hujjatning o'z
   vizyonida auditoriya "kompyuter ishlatmaydigan" deb yozilgan, ammo undan
   `/davomatim` ni **eslab qolish** talab qilinadi. Doimiy klaviatura yo'q.
2. **Bot hech qachon birinchi gapirmaydi.** 11 ta xabar triggeri bor va
   **hammasi** allaqachon sodir bo'lgan voqeaga javob: chek tasdiqlandi, dars
   ochildi, vazifa baholandi. Oldinga qaragan bitta xabar yo'q — "darsingiz bir
   soatdan keyin", "vazifa muddati ertaga". Jonli kurs uchun eng qimmatli xabar
   aynan shu va u mavjud emas.
3. **Launch kuni bot holatini ko'rsatadigan hech narsa yo'q.** Outbox navbati
   ko'rinadi, handler yo'li ko'rinmaydi. "Bot sekinlashdimi?" savoliga bugun
   javob beradigan o'lchov yo'q.

---

## Kesuvchi talab — qotirib qo'yilgan qiymat yo'q

> **Owner qarori — 2026-09-11:** «qotirib qo'yiladigan qiymatlar qo'yma, masalan
> 1 soat oldin yuborilsin desam 1 soat qilma uni — men admin paneldan
> o'zgartira olayin kerak bo'lganda.»

Bu quyidagi **barcha** bandlarga tegadi, faqat T2 ga emas. Har operatsion yoki
mahsulot parametri — vaqt, oyna, limit, chegara, yoqish/o'chirish — **ishlab
turgan tizimda, deploy'siz** o'zgarishi kerak.

**Mexanizm yangi emas, ammo naqsh ikki qismdan iborat** va ularni aralashtirish
xato bo'ladi:

- **Model shakli — `aicontrol.AISettings`.** Singleton, maydonda `default=`,
  `help_text` bilan izoh, `default_model` da «bo'sh bo'lsa `settings.py` qiymati»
  fallback'i. Shuni ko'chirish to'g'ri.
- **Mutation yuzasi — `core/views.py` dagi brend/landing/kill-switch yuzalari.**
  Majburiy `change_reason`, majburiy tasdiq checkbox'i, `SystemAuditEvent` va
  o'zgarish bo'lmasa yozmaydigan no-op yo'l. Audit talabi **shundan** olinadi.

> **Diqqat — mavjud AI sozlama yuzalari audit naqshi EMAS.**
> `AISettingsAdmin` faqat `updated_by` yozadi; `backoffice_ai_control`
> singletonni to'g'ridan-to'g'ri saqlaydi. Ikkisida ham sabab, tasdiq va
> `SystemAuditEvent` yo'q. `AISettings` ni audit namunasi deb ko'chirish yana
> bitta auditlanmagan operatsion yuza yasaydi. Mavjud yuzalarni retrofit qilish
> alohida **A2 qarzi** sifatida ochiq qoladi va bu reja uni o'z ichiga olmaydi.

Yangi parametr uchun to'rt shart:

1. **Qiymat DB'da**, Python konstantasida emas; env faqat fallback.
2. **Default bor** — toza o'rnatish hech narsa sozlamasdan ishlashi kerak.
3. **Chegaralar tekshiriladi** — `0` yoki `999999` kiritilganda tizim
   to'xtamasligi kerak. Validator maydonda bo'ladi, izohda emas.
4. **O'zgarish auditlanadi** — sabab + tasdiq + `SystemAuditEvent` (yuqoridagi
   ikkinchi naqsh).

**Effective policy manbasi bitta bo'ladi.** Vaqt, oyna, limit va chegara —
sozlamada. Yoqilgan/o'chirilgan — **faqat** `core/flags.py` registrida. Bitta
narsani ikki DB manbasi boshqarsa (sozlamadagi `enabled` va flag) ular
bir-biriga zid bo'lishi mumkin va owner qaysi qiymat amalda ekanini aniqlay
olmaydi.

**Chegara — hamma konstanta emas.** Ikki narsa ataylab kodda qoladi:

- **Protokol faktlari:** Telegram xabarining 4096 belgisi, HMAC algoritmi.
  Bularni «sozlash» sozlama emas, xato.
- **Kafolatni ushlab turuvchi qo'riqchilar:** masalan
  `MIN_RATE_LIMIT_DELAY_SECONDS` — u `retry_after=0` kelganda issiq siklni
  oldini oladi. Uni `0` ga qo'yish mumkin bo'lsa, sozlamaning o'zi nosozlikka
  aylanadi.

Sinov savoli: *«Azurbek buni jonli dars kunida o'zgartirishni xohlashi
mumkinmi, va o'zgartirish xavfsizmi?»* Ikkisiga ham «ha» bo'lsa — sozlama.
Ikkinchisiga «yo'q» bo'lsa — kodda qoladi yoki chegara bilan o'raladi.

---

## T0 — Mavjud qotirib qo'yilgan qiymatlarni sozlanuvchi qilish · `S/M` — `IMPLEMENTED/TESTED` (2026-09-11)

Qoida orqaga ham qaraydi: joriy kodda owner o'zgartirishi kerak bo'ladigan,
ammo bugun faqat deploy bilan o'zgaradigan qiymatlar bor.

| Qiymat | Joy | Nega sozlama bo'lishi kerak |
|---|---|---|
| `SEND_INTERVAL_SECONDS = 0.05` | `bot/retry_policy.py` | PR #101 ning o'zida yozib qo'yilgan: «jonli darsda hamon `429` ko'rinsa, oraliqni oshirish kerak». Ya'ni bu **isbotlangan** knob |
| `BATCH_SIZE = 25`, `POLL_INTERVAL = 15` | `bot/outbox.py` | 50 o'quvchilik darsdan keyin navbat tezligini owner boshqarishi kerak |
| `MAX_ATTEMPTS = 5`, `BASE_BACKOFF_SECONDS = 30`, `MAX_BACKOFF_SECONDS = 900` | `bot/retry_policy.py` | Telegram yoki tarmoq qanday tutishiga qarab moslanadi |
| `BATCH_SIZE = 10` (guruh navbati) | `classbook/delivery.py` | `process_outbox_once()` guruh batch'ini DM batch'idan **oldin** oladi, ya'ni bu ham o'sha workerning jonli throughput chegarasi |
| `LEASE_SECONDS = 120` | `bot/outbox.py`, `classbook/delivery.py` | Ikkinchi replika yoqilganda qayta o'lchanadi |
| `BACKUP_STALE_AFTER_DAYS = 7` | `core/control_center/snapshot.py` | Zaxira qachon AMBER bo'lishi — operatsion qaror |

**Kodda qoladi:** `MIN_RATE_LIMIT_DELAY_SECONDS` (issiq sikl qo'riqchisi),
`TG_MESSAGE_LIMIT` (protokol), `JITTER_SHARE` (o'zgartirishdan foyda yo'q).

- **Canonical owner:** yangi singleton (masalan `bot.BotRuntimeSettings`) —
  `AISettings` bilan bir xil shakl. Chegara/probe tomoni Control Center'da.
- **Acceptance:** sozlama bo'sh yoki noto'g'ri bo'lsa kod defaultiga tushadi va
  jim buzilmaydi; har maydonda chegara validatori; o'zgarish auditlanadi; mavjud
  testlar default qiymat bilan o'tishda davom etadi.
- **Nega T0:** keyingi bandlar ham shu singletonga yozadi. Avval u qurilsa, T2
  o'z sozlamalarini qo'shadi va yangi naqsh o'ylab topmaydi.

**Bajarildi — 2026-09-11:** ikki singleton qurildi, chunki bir modelga ikki
domenni tiqish noto'g'ri uy bo'lardi:

- `bot.BotRuntimeSettings` — yetkazish tezligi va qayta urinish siyosati
  (8 maydon). Jadvaldagi `SEND_INTERVAL_SECONDS` → `send_interval_ms`
  (millisekund, admin uchun qulay va `0` ma'noli).
- `core.OperationalSettings` — Control Center chegaralari (3 maydon). Jadvalda
  `BACKUP_STALE_AFTER_DAYS` bor edi; yonidagi `_telegram_probe` ning qotirib
  qo'yilgan `60`/`15` daqiqasi ham shu yerga kirdi — ular bir xil sinf va
  bittasini qoldirish sahifani o'z qoidasiga zid qilardi.

Qiymat `resolved()` orqali o'qiladi: sozlama qatori bo'lmasa kod defaulti,
chegaradan chiqqan qiymat esa xavfsiz oraliqqa **qisiladi**. Sabab — validator
faqat formani qo'riqlaydi, `update()` va fixture uni chetlab o'tadi; owner esa
sozlamani jonli dars kunida o'zgartiradi.

Yozish yuzasi `/backoffice/control/runtime-settings/` — majburiy sabab, majburiy
tasdiq, `SystemAuditEvent` va no-op yo'l. **Django admin'da ikki model ham
faqat o'qish uchun**: admin orqali tahrirlash o'zgarishni izsiz qoldirardi, ya'ni
`AISettingsAdmin` dagi nuqsonni takrorlardi. Buni test qulflaydi.

Mavjud AI sozlama yuzalarini retrofit qilish hamon **A2 qarzi** — bu slice uni
o'z ichiga olmadi.

---

## T1 — Rolga mos doimiy klaviatura · `S` — `IMPLEMENTED/TESTED` (2026-09-11)

- **Outcome:** o'quvchi hech qanday buyruqni eslab qolmasdan asosiy to'rt amalga
  yetadi. Buyruqni eslash talabidan voz kechish — bu auditoriya uchun eng katta
  bitta yaxshilanish.
- **Canonical owner:** `bot/keyboards.py` — rolga qarab klaviatura quradi
  (`student` / `teacher` / `admin` / `linked`). Rol allaqachon middleware'dan keladi.
- **Adapterlar:** tugma matni mavjud handlerlarga **aynan** tushadi; yangi biznes
  yo'li yaratilmaydi. Buyruqlar ham o'z joyida qoladi (muskul xotira buzilmasin).
- **Acceptance:** har rol uchun to'g'ri tugma to'plami; tugma bosilganda slash
  buyruq bilan **bir xil** javob (parity testi); klaviatura `/start` da o'rnatiladi
  va `/yordam` da qayta tiklanadi; guruh chatlarida **chiqmaydi**.
- **Riskni boshqarish:** klaviatura ekranning pastini egallaydi — tugma soni 4 dan
  oshmaydi va "⌨️ Yopish" yo'li bo'ladi.

**Bajarildi — 2026-09-11:**

- `bot/keyboards.py`: tugma matn konstantalari + `workspace_keyboard(role)`.
  Matn ikki tomon uchun bitta manba — klaviatura quruvchi va router filtri
  (`F.text == ...`). Ikki joyda qo'lda yozilsa, bittasini o'zgartirib
  ikkinchisini unutish tugmani jimgina ishlamaydigan qilardi.
- Tugma → mavjud handler **stacked dekorator** bilan ulandi
  (`@router.message(Command(...))` ustiga `@router.message(F.text == BTN_...)`).
  Ya'ni nusxa yozilmadi va parity qurilish jihatidan kafolatlangan: bitta
  funksiya, ikki kirish yo'li.
- Rollar: student (Darslarim / Davomatim / To'lov / AI), teacher (Guruhlarim /
  Baholash / AI / Yordam), admin (Statistika / Cheklar / Guruhlarim /
  Baholash), linked (Kursga yozilish / Yordam). **Guest — klaviatura yo'q**
  (sabab pastda).
- Klaviatura `/start`, `/yordam` va start-token bilan bog'langan zahoti
  qo'yiladi; `⌨️ Klaviaturani yopish` uni olib tashlaydi, `/yordam` qaytaradi.

**Ikki qaror sabab bilan:**

1. **Guestga klaviatura qo'yilmaydi.** Telegramda chatda bir vaqtda faqat
   bitta reply klaviatura bo'ladi — yangisi eskisini almashtiradi. Guest
   oqimida telefon ulashish tugmasi (`request_contact`) ishlatiladi; ish stoli
   klaviaturasi qo'yilsa, ro'yxatdan o'tish o'rtasida o'sha tugma yo'qolib
   qolardi.
2. **Klaviatura alohida ikkinchi xabar bilan yuboriladi.** Bitta xabarda bitta
   `reply_markup` bo'ladi, xush kelibsiz xabari esa inline menyuni ko'taradi.

**Yo'lda tuzatilgan parity nuqsoni:** inline «Darslarim» (`ws:courses`) buyruq
varianti ko'rsatadigan kurs tugmalarini bermasdi — bitta amal ikki yuzada ikki
xil javob berardi. Endi uchala yuza (buyruq, inline, klaviatura) bir xil.

**Owner qarori (2026-09-11):** klaviatura buyruqlarni **almashtirmaydi**,
ularga qo'shiladi — muskul xotira buzilmasin.

## T2 — Oldinga qaragan eslatmalar · `M` — `PARTIAL` (2026-09-11)

- **Outcome:** o'quvchi darsni **o'tkazib yubormaydi** va vazifa muddatini
  bilmasdan qolmaydi. O'qituvchi ko'rilmagan topshiriqni eslatmasdan ko'radi.
- **Canonical owner:** yangi `users/reminder_service.py` (yoki `courses/`) —
  **faqat** `create_notification` ni chaqiradi. Adapter umuman o'zgarmaydi, chunki
  kanal tayyor.
- **Scope (birinchi uchta, ko'pi emas):**
  1. **Dars eslatmasi** — rejalashtirilgan dars boshlanishidan `N` soat oldin.
  2. **Vazifa muddati** — tugashidan bir kun oldin, faqat topshirmaganlarga.
  3. **O'qituvchi navbati** — `N` kundan beri ko'rilmagan topshiriq bo'lsa.
- **Hamma vaqt va oyna sozlanuvchi** (kesuvchi talab, yuqoriga qarang): darsdan
  necha soat yoki daqiqa oldin, vazifa muddatidan necha kun oldin, o'qituvchi
  navbati necha kundan keyin, jim soatlar boshlanishi va tugashi. Hech biri kodda
  raqam bo'lib turmaydi: default bor, owner esa admin panelidan istagan payt
  o'zgartiradi.
- **Yoqish/o'chirish sozlamada EMAS.** Har eslatma turining yoqilgani faqat
  `core/flags.py` registrida bo'ladi. Agar u ham sozlamada `enabled` maydoni
  bo'lsa, ikki DB manbasi bir-biriga zid bo'lib qolishi mumkin va owner qaysi
  biri amalda ekanini aniqlay olmaydi. Bo'linish: **vaqt → sozlama, yoqilgan →
  flag.**
- **Acceptance:** `external_key` bilan **idempotent** (bitta voqea uchun bitta
  xabar, beat ikki marta yugursa ham); har tur uchun `core/flags.py` da alohida
  flag/kill switch va u **yagona** yoqish manbasi; jim soatlar **sozlamadan**
  o'qiladi; "o'tkazib yuborilgan" eslatma keyin yuborilmaydi — eskirgan eslatma
  zarar; sozlama o'zgarsa keyingi beat sikli **darhol** yangi qiymat bilan
  ishlaydi, restart kutmaydi.
- **Nega endi:** bu bandning butun qiymati Classbook jonli darsiga qatnashuvda.
  30-sentyabr maqsadi aynan shu.

**Bajarildi — 2026-09-11, `PARTIAL`.** Uchta eslatmadan **ikkitasi ma'lumot
modelida umuman yo'q** ekan, shuning uchun ular taxmin qilinmadi:

| Eslatma | Holat |
|---|---|
| Dars boshlanishi | **Blok.** Hech qayerda rejalashtirilgan dars vaqti saqlanmaydi — `Cohort.start_date` kurs boshlanishi, `attendance_date` o'tgan darsning yozuvi, jonli dars esa `/dars N` bilan ad-hoc boshlanadi |
| Vazifa muddati | **Blok.** `Assignment` da muddat maydoni yo'q (faqat lesson, title, description, max_xp) |
| O'qituvchi navbati | **Qurildi** — kunlik yig'ma eslatma |
| *(qo'shimcha)* To'lov muddati | **Bor edi**, lekin oynasi kodda qotib turardi (`days_left in {3, 1, 0}`) — sozlamaga ko'chirildi |

Ikki blok **mahsulot qaroriga** bog'liq (jadval haftalik takrorlanuvchimi yoki
har sessiya alohidami; vazifa muddati kurs bo'yichami yoki dars bo'yicha).
Ularsiz eslatma yozish soxta bo'lardi.

**Qurilgani:**

- `users/reminder_service.py` — o'qituvchi navbati yig'ma eslatmasi. Har
  kutayotgan topshiriq uchun alohida xabar emas, **kuniga bitta**: o'nta
  topshiriq o'nta bildirishnoma bo'lsa, u o'qituvchining haqiqiy ishidan
  ko'ra ko'proq shovqin yasardi. Navbat bo'shagach o'z-o'zidan to'xtaydi.
  Scope canonical funksiyadan (`core/access.py`) — A0b/1 aynan shu
  nusxalanishda buzilgan edi.
- `users.ReminderSettings` — to'lov oynasi (`3,1,0` ko'rinishida), o'qituvchi
  chegarasi va **jim soatlar**. Hammasi
  `/backoffice/control/runtime-settings/` da, T0 bilan bir sahifada.
- Yoqish/o'chirish `core/flags.py` da (`reminder_payment_due`,
  `reminder_teacher_review`) — sozlamada `enabled` maydoni yo'q, effective
  policy manbasi bitta.

**Jim soatlar — topilgan haqiqiy nosozlik.** Obuna eslatmasi kunlik lifecycle
ishi bilan **soat 03:05 da** yaratiladi va outbox uni o'sha zahoti yuborardi:
o'quvchi tunda DM olardi. Endi eslatma turidagi qatorlar jim soatlarda
navbatdan **olinmaydi** — hech narsa yozilmaydi, qator joyida qoladi va
ertalab o'z-o'zidan oqimga qaytadi. Hodisaga javob beruvchi xabar (chek
tasdiqlandi, vazifa baholandi) hech qachon kechiktirilmaydi, Classbook guruh
navbati esa umuman boshqa jadvalda.

## T3 — O'qituvchi to'liq ish stoli (F12 closeout) · `L`

- **Outcome:** Azurbek kun o'rtasida saytga kirmasdan baholaydi.
- **Holat:** `/baholash` bugun **faqat navbat ko'rsatadi** (`teacher_grading_queue`).
  Ball qo'yish, izoh yozish va qayta topshirishga yuborish yo'q.
- **Canonical owner:** mavjud `courses/submission_service.py::review_assignment_submission`
  — yangi review engine **yozilmaydi**, bot uni chaqiradi.
- **Acceptance:** teacher default-deny scope saqlanadi; ball/izoh sayt bilan bir xil
  natija beradi (adapter parity testi); `BotPendingAction` bilan restartga chidamli;
  XP diff idempotent (PR #92 da tuzatilgan yo'l buzilmaydi).
- **Ochiq qaror:** hujjat F11 va F12 orasidagi tanlovni ownerga qoldirgan.

## T4 — Bot observability · `S/M` — `IMPLEMENTED/TESTED` (2026-09-12)

- **Outcome:** launch kuni "bot tirikmi va tezmi?" savoliga **raqam bilan** javob.
- **Canonical owner:** `aicontrol.WorkerHeartbeat` va Control Center capability
  registri — yangi monitoring tizimi qurilmaydi, mavjudi kengaytiriladi.
- **Scope:** dispatcher heartbeat'i (oxirgi update vaqti); handler davomiyligi
  (o'rtacha va p95, middleware'da o'lchanadi); xato soni. Control Center'da bitta
  `telegram_dispatcher` chirog'i.
- **Acceptance:** o'lchash handler javobini sekinlashtirmaydi (yozuv batch/async);
  polling to'xtasa chiroq AMBER→RED bo'ladi; probe **hech narsa yubormaydi**.

**Bajarildi — 2026-09-12.** Uchala acceptance sharti test bilan qulflangan.

**O'lchovning narxi nolga yaqin.** `bot/metrics.py::DispatcherMetrics` faqat
xotiraga yozadi (lock + `deque`), DB'ga esa **sikl bo'yicha bitta** yozuv
boradi. Buning sababi o'lchangan: jonli darsda 50 o'quvchi bir vaqtda «Keldim»
bosadi va har update uchun bitta `UPDATE` o'lchovning o'zini nosozlik manbasiga
aylantirardi. Shart testda qulflangan — `bot/test_metrics.py::MeasurementCostTests`
`SimpleTestCase` da yuguradi, ya'ni **DB so'rovi taqiqlangan**: kimdir o'lchov
yo'liga yozuv qo'shsa test o'z-o'zidan yiqiladi.

**Tiriklik trafikdan ajratilgan — bu bandning eng muhim qarori.** Eng tabiiy
dizayn «oxirgi update vaqti = sog'liq» bo'lardi va u **har tongda yolg'on
qizil** berardi: tunda hech kim yozmasa sog'lom bot o'lik ko'rinadi. Shuning
uchun:

| Nima | Qaydan o'qiladi | Nimani bildiradi |
|---|---|---|
| Tiriklik | `last_seen_at` — flush sikli yozadi | jarayon bor |
| Trafik | `detail["last_update_at"]` | foydalanuvchi faolligi, sog'liq **emas** |
| Tezlik | oynadagi p95/o'rtacha | sekinlashdimi |
| Xato | oynadagi xato ulushi | nosozlik chastotasi |

**Ikki yo'l, chunki ikki rejim bor.** Polling'da uzoq yashovchi event loop bor
→ `asyncio` sikli trafikdan qat'i nazar yozadi. Webhook'da har so'rov o'z
loop'ini ochib yopadi → yozuv update'ga ilashadi, ammo **oraliqqa bir marta**.
Sikl `aiogram` ning `startup`/`shutdown` hodisalariga ulangan, `runbot` yoki
`run_bot.py` ga emas: ikkita polling kirish nuqtasi bor va har biriga qo'lda
ulash bittasini unutish yo'li.

**Shu bo'linishning oqibati — probe rejimga qarab o'qiydi.** Bu PR #108
review topilmasi va u haqiqiy nuqsonni ko'rsatdi: birinchi versiyada yosh
ikki rejimda ham tiriklik deb o'qilardi, holbuki webhook'da alohida bot
jarayoni **yo'q** va yozuvni faqat update olib keladi. Natijada yangi
deploy «hech qachon ishga tushmagan» bo'lib ko'rinardi va jim tun chiroqni
qizil qilardi — ya'ni bu bandning o'z qoidasi (`trafiksizlik nosozlik emas`)
productionning **default** rejimida buzilgan edi, chunki `TELEGRAM_MODE`
local'dan tashqarida `webhook`.

| Rejim | Yosh nimani bildiradi | Eng yomon rang |
|---|---|---|
| `polling` | tiriklik — sikl yozmasa jarayon yo'q | RED |
| `webhook` | o'lchovning yangiligi, tiriklik emas | AMBER |

Webhook'da web tier tirikligi boshqa chiroqlarning va `/readyz` ning ishi.
Yo'qolgan signal o'rniga yangi, amal qilinadigan signal qo'shildi: webhook
rejimida hech qachon update kelmagan bo'lsa AMBER — bu odatda webhook
ro'yxatdan o'tmaganini bildiradi. Rejim **heartbeat'dan** o'qiladi, joriy
sozlamadan emas: sozlama keyin o'zgartirilgan bo'lishi mumkin, yozuv esa
eski rejimda qilingan.

**Oynadan eski raqam rang bermaydi.** `samples`/`p95` heartbeat yozilgan
paytdagi oynani tasvirlaydi. Yozuvning o'zi o'sha oynadan eski bo'lsa
raqamlar muddati o'tgan: uch soat oldin o'lchangan sekinlik hozirgi sekinlik
emas. Bu qoida ikki rejimda ham ishlaydi va yana bitta yolg'on qizilni
yopadi.

**Rejali to'xtatish halokatdan ajratiladi.** `shutdown` da `stopped_at`
yoziladi va probe uni **yoshdan oldin** ko'radi — aks holda to'xtatish
yozuvining yangi `last_seen_at` i botni tirik qilib ko'rsatardi (soxta-yashil).
Bot qaytib ko'tarilsa bayroq o'z-o'zidan yo'qoladi.

**Sozlama o'zini nosozlikka aylantirmaydi.** Eskirish chegarasi sozlanuvchi,
ammo probe uni jarayon **o'zi ishlatayotgan** yozuv oralig'idan ikki baravar
pastga tushirmaydi. Aks holda owner `metrics_flush_seconds` ni 300 qilsa,
chegara 120 bo'lib qolib, chiroq abadiy sariq bo'lib turardi — ya'ni sozlamani
o'zgartirish mavjud bo'lmagan nosozlik yasardi. Oraliq heartbeat'dan o'qiladi,
sozlamadan emas: owner bir daqiqa oldin o'zgartirgan qiymat hali kuchga
kirmagan bo'lishi mumkin.

**Statistik to'rlar rang bermaydi.** Bittadan bitta xato 100% bo'ladi, ya'ni
bot ishga tushgan zahoti qizil chiroq berardi — shuning uchun xato foizi
kamida 20 namunadan keyin rang beradi. Namuna umuman bo'lmasa javob «namuna
yo'q», «hammasi tez» emas.

**Tartib tuzatishi chegarani buzmaydi.** Review ikkinchi topilma berdi:
AMBER/RED tartibini `red = amber + 1` bilan tuzatish xato foizida ishlamaydi
— ikkala chegara ham 0–100 oralig'ida, ya'ni fixture yoki `update()` ikkisini
100 qilib yozsa RED 101 ga chiqardi. 101% xato kuzatilishi mumkin emas,
demak chiroq xato sababli **hech qachon qizil bo'lmasdi** va tuzatishning
o'zi yangi ko'r nuqta yasagan bo'lardi. Endi uch bosqich: RED ni ko'tarish →
bo'lmasa AMBER ni tushirish → bo'lmasa juftlikni kod defaultiga qaytarish.

**Sozlamalar (owner qoidasi):** yozuv oralig'i va o'lchov oynasi
`bot.BotRuntimeSettings` da; chiroqning oltita chegarasi (bot belgisi,
javob vaqti, xato foizi — har biri AMBER/RED) `core.OperationalSettings` da.
Hammasi `/backoffice/control/runtime-settings/` da, T0/T2 bilan bir sahifada.
`MAX_SAMPLES` va `MIN_ERROR_SAMPLES` ataylab **sozlamada yo'q**: biri xotira
kafolati, ikkinchisi statistik to'r — ikkalasi ham owner uchun ma'noli
operatsion savol emas.

**Flag ataylab qo'shilmadi.** «Kuzatuvni o'chirish» flagi chiroqni qizil
qilardi (heartbeat yo'q = bot o'lik), ya'ni o'chirish nosozlikdan farq
qilmasdi. Yozuv yuki muammo bo'lsa to'g'ri knob — oraliqni oshirish, va u
sozlamada bor.

**Chiroq `critical` emas, `high`.** `/readyz` faqat critical probe'larni
yugurtiradi; bot ishlamayotgani web instance trafik qabul qila olmasligini
bildirmaydi. Butun saytni `503` qilish nosozlikni tuzatmay, ko'paytirardi.
Shu sabab `telegram-dispatcher` `EXPECTED_WORKERS` ga ham qo'shilmadi —
bitta uzilish ikkita qizil chiroq bermasligi kerak.

**T5 uchun asos tayyor.** Reja T5 ni «o'lchanmaguncha past prioritet» deb
yozgan edi: identity har update'da 3 DB so'rovi qiladi, ammo bu muammo
sifatida **isbotlanmagan** taxmin edi. O'lchov `MetricsMiddleware` da
identity'dan **tashqarida** turadi, ya'ni p95 aynan shu narxni ham qamrab
oladi. Endi T5 ni ochishdan oldin haqiqiy raqam bor.

## T5 — Identity narxini kamaytirish · `S` · **ehtiyot bilan**

- **Muammo:** har update 3 DB so'rovi. 50 o'quvchi bir vaqtda "Keldim" bosganda —
  faqat identity uchun ~150 so'rov, ish boshlanmasdan.
- **Yechim:** `telegram_id → (user_id, rol)` ni qisqa TTL bilan keshlash (Valkey
  productionda bor).
- **Ogohlantirish — bu bandning asosiy gapi:** rolni keshlash **xavfsizlik
  regressiyasi** bo'lishi mumkin. Bloklangan hisob (`is_active=False`) kesh
  muddati tugaguncha botda huquqini saqlab qolardi, holbuki A0a aynan shuni
  yopgan. Shuning uchun: TTL ≤ 60 sekund **va** `is_active`/enrollment
  o'zgarganda explicit invalidatsiya, **yoki** faqat `user_id` keshlanadi, rol
  esa har safar hisoblanadi. Tezlik uchun xavfsizlik chegirmasi qilinmaydi.
- **Acceptance:** bloklangan foydalanuvchi **darhol** huquqsiz qoladi (test);
  enrollment tugaganda rol darhol o'zgaradi (test); keshsiz ham to'g'ri ishlaydi.
- **Prioritet:** o'lchanmaguncha past. T4 (2026-09-12) o'lchovni berdi:
  `MetricsMiddleware` identity'dan tashqarida turadi, ya'ni Control Center'dagi
  p95 identity narxini ham qamrab oladi. **Raqam ko'rilmaguncha bu band hamon
  ochilmaydi** — kesh xavfsizlik regressiyasi bo'lishi mumkin va uni
  isbotlanmagan taxmin uchun olish mantiqsiz.

## T6 — Dead-letter replay · `S` — `IMPLEMENTED/TESTED` (2026-09-12)

- **Outcome:** terminal bo'lgan xabarni owner sababi bilan qayta yuboradi.
- **Kelib chiqishi:** PR #101 dead-letter'ni qurdi, replay amalini qurmadi.
  `05-launch-ops.md` §2 ilgari "mavjud bo'lmagan amalni auditlash mumkin emas"
  deb yozgan edi — endi amal mantiqiy.
- **Canonical owner:** Control Center mutation surface'i (reason + confirmation +
  idempotency + audit — A2 shartlari).
- **Acceptance:** replay `SystemAuditEvent` ga yoziladi; `permanent` turdagi qator
  uchun ogohlantirish beriladi (bloklagan foydalanuvchiga qayta yuborish befoyda);
  replay urinish hisoblagichini nolga qaytaradi.

**Bajarildi — 2026-09-12.** Yuza: `/backoffice/control/dead-letter/`.

**Ikki navbat bitta modulda.** `bot.TelegramOutbox` (DM) va
`classbook.TelegramGroupDelivery` (guruh) alohida modellar, ammo bu amal uchun
bir xil shaklda. Qayta urinish siyosati allaqachon ikkisi uchun **bitta**
(`bot/retry_policy.py`) — replay ham shunday, aks holda bittasi tuzatilib
ikkinchisi eskirib qolardi. Test ikkala navbatni ham qamrab oladi: faqat DM
sinalsa guruh yo'li jim buzilishi mumkin edi.

**Idempotentlik sahifa holatida emas, shartli `UPDATE` da.** Qator faqat
`WHERE status='failed'` bo'lganda qaytadi, ya'ni ikki brauzer oynasi bir
vaqtda bossa ham xabar bir marta ketadi. Ikkinchi chaqiruv nol qator
o'zgartiradi va yuza hech narsa yozmaydi.

**Nima tiklanadi va nega:**

| Maydon | Nima bo'ladi | Nega |
|---|---|---|
| `attempts` | `0` | Aks holda qaytarilgan xabar birinchi transient xatoda darhol yana dead-letter bo'lardi — amal amalda hech narsa bermasdi |
| `next_attempt_at` | `None` | Keyingi siklda darhol olinadi |
| `failure_kind`, `last_error` | tozalanadi | `pending` qatorda eski nosozlik matni chalg'itadi; qiymat audit yozuvining `before` snapshotida saqlanadi |
| `claimed_at`, `claim_token` | tozalanadi | Himoya: terminal qatorda ular bo'sh bo'lishi kerak, lekin bo'sh emas deb ishonmaymiz |

**`permanent` uchun ikkinchi tasdiq, to'siq emas.** Bu tur — foydalanuvchi
botni bloklagan, chat o'chirilgan yoki bot guruhdan chiqarilgan; qayta urinish
hech qachon yordam bermaydi va faqat rate budjetini yeydi. Baribir
taqiqlanmaydi: blok yechilgan bo'lishi mumkin va buni faqat owner biladi.
Shu sabab ro'yxatda alohida belgi, formada esa alohida tasdiq va yuborilgandan
keyin alohida ogohlantirish.

**Chegara sozlamada.** `BotRuntimeSettings.dead_letter_replay_limit` (default
200) sahifa nechta qator ko'rsatishini ham, bitta amal nechtasiga tegishini
ham belgilaydi — «bir o'tirishda qanchasini qaytaraman» bitta qaror, ikki
knob emas. Chegaradan oshiq qator bo'lsa sahifa buni aytadi, aks holda owner
«hammasini qaytardim» degan xato xulosa chiqarardi.

**Yopilgan qarz.** `05-launch-ops.md` §2 ikki joyda «outbox replay
auditlanmagan, chunki bunday amal hali mavjud emas» deb yozgan edi; ikkalasi
ham yangilandi. `bot/retry_policy.py` dagi `KIND_CONFIG` izohi ham
«(replay amali hali yo'q)» deb turgan edi — endi amal bor, lekin u **qo'lda**,
o'sha qarorning o'zi esa avtomatik bo'lib qoladi.

## T7 — Mini App'ni haqiqiy yuzaga aylantirish · `L` · **serverni kutadi**

- **Holat:** F5 **ko'prik** berdi (initData HMAC, avto-login, open-redirect himoya).
  To'liq webview HTTPS'da hali sinalmagan.
- **Nega muhim:** uzun forma, imtihon va murakkab oqim sof chatda noqulay — hujjat
  buni 2026-07-13 da yozgan va shundan beri holat o'zgarmagan.
- **Bog'liqlik:** AWS serveri va domen. Lokalda Telegram `web_app` tugmasini rad
  etadi, ya'ni bu bandni serversiz **yopib bo'lmaydi**.

## T8 — F11 imtihon va sertifikat · `L` · **T7 dan keyin**

- Hujjatning o'z qarori: botdagi imtihon taymeri "yumshoq", jiddiy imtihon uchun
  Mini App/sayt tavsiya etiladi. Shu sabab T8 T7 ga bog'langan: botda faqat
  **mashq** imtihonlari, jiddiysi Mini App'da.
- `/sertifikatlarim` — mustaqil va kichik qism, T8 dan ajratib olinishi mumkin.

---

## Tartib taklifi

| Bosqich | Bandlar | Nega shu tartib |
|---|---|---|
| **Hozir (serversiz)** | ~~T0~~ ~~T1~~ ~~T2~~ ~~T4~~ ~~T6~~ (2026-09-11/12; T2 `PARTIAL`) — **serversiz navbat tugadi** | T2 ning ikki qismi ma'lumot modeliga bog'liq va owner qaroriga qoldi. Qolgan bandlar (T3, T5, T7, T8) yo owner tanlovini, yo o'lchovni, yo serverni kutadi |
| **Server ochilganda** | T7 tekshiruvi, F10 qoldig'i | Webhook, Menu Button, Mini App webview |
| **Launchdan keyin** | T3, T5, T8 | T3 owner tanlovini kutadi; T5 o'lchovni kutadi |

**Tavsiyam: T0, so'ng T1 va T2.** Sababi bitta — ularning ikkalasi ham bitta narsani
beradi: o'quvchi darsga **keladi** va platformani **eslab qolishga majbur emas**.
Qolgan bandlar muhim, ammo hech biri qatnashuvga bunday bevosita tegmaydi.

## Owner qarorlari

**Javob berilgan (2026-09-11):**

1. ~~T2 eslatma vaqti: necha soat oldin?~~ → **Savol emas.** Vaqt kodda
   belgilanmaydi; sozlama bo'ladi va Azurbek uni admin panelidan o'zgartiradi.
   Shu qoida butun rejaga tarqaldi (kesuvchi talab + T0).
2. ~~Production bot tokeni?~~ → **Keyinga qoldirildi.** Qurish davom etayotganda
   mavjud `@azureLMSbot` lokal polling bilan ishlatiladi. Alohida production bot,
   webhook va public Menu Button production haqiqatan ochilganda ko'riladi.

3. ~~T1 qamrovi: klaviatura buyruqlarni almashtiradimi?~~ → **Qo'shiladi**
   (2026-09-11 da tasdiqlandi va shunday bajarildi).

**Ochiq qolgan:**

4. **F11 yoki F12 (T8 yoki T3):** hujjat bu tanlovni ochiq qoldirgan. T3 sizning
   ish vaqtingizni qisqartiradi, T8 o'quvchi natijasiga tegadi.
5. **Dars jadvali modeli — T2 ning bloki:** dars vaqti qayerda saqlanadi?
   Guruh bo'yicha haftalik takrorlanuvchi jadvalmi (masalan dushanba va
   chorshanba 19:00) yoki har sessiya alohida rejalashtiriladimi? Bu javobsiz
   «darsingiz bir soatdan keyin» eslatmasini yozib bo'lmaydi — hozir hech
   qayerda rejalashtirilgan dars vaqti saqlanmaydi.
6. **Vazifa muddati — T2 ning ikkinchi bloki:** `Assignment` ga muddat
   qo'shiladimi, va u dars ochilganidan necha kun keyin bo'ladimi (nisbiy)
   yoki har vazifaga alohida sana yoziladimi (absolyut)?

## Bu reja ataylab qilmaydigan ishlar

- **Yangi AI imkoniyati yo'q.** Gemini bepul kvotasi qattiq cheklov bo'lib qoladi;
  hech bir band yangi remote chaqiruv qo'shmaydi.
- **`bot/services.py` ni 2 343 satrdan bo'lish rejaga kiritilmadi.** Fayl katta,
  ammo uni bo'lish o'z-o'zidan na o'quvchiga, na ownerga foyda bermaydi — bu
  churn. Bo'lish faqat biror band shu faylni jiddiy o'zgartirganda, shu bandning
  ichida qilinadi.
- **Bot dizayni bo'yicha "to'liq qayta yozish" yo'q.** Audit ko'rsatdi: arxitektura
  sog'lom (yupqa adapter, canonical servislar, DB holati, xato qatlami). Muammo
  arxitekturada emas, **yetishmayotgan uchta qatlam**da: navigatsiya, proaktivlik,
  ko'rinish.

## Halol chegaralar

- T1–T6 ning hammasini avtomatik test qoplaydi, ammo **hech biri haqiqiy telefonda
  sinalmagan bo'ladi** — bu `A5` owner sign-off'ining bir qismi bo'lib qoladi.
- T2 ning qiymati (qatnashuv oshishi) **o'lchanmagan taxmin**. Birinchi cohortdan
  keyin `LessonRun` davomati bilan solishtirilsa o'lchanadi; undan oldin bu
  "kutilgan foyda", isbot emas.
- T4 latency o'lchovi polling rejimida olinadi; webhook rejimida raqamlar boshqa
  bo'ladi va qayta o'lchash kerak.
