# AzureLMS — Marinebook (loyiha kundaligi)

Bu fayl loyihaga qo'shilgan har major contribution'ning xronologik yozuvi. Yangi yozuv **eng yuqoriga** qo'shiladi (teskari xronologik) — yangi agent faylni ochishi bilan eng so'nggi holatni darhol ko'radi.

**Format:**
```markdown
## YYYY-MM-DD [Agent nomi]: Qisqa sarlavha

Qisqa izoh (2-4 jumla) — nima qilindi va nima uchun muhim.

- Branch: `<branch-nomi>` yoki `main`
- Commitlar: `abc1234`, `def5678`
- Test holati: <pass/fail soni>
- Davom etilishi kerak: <agar bor bo'lsa>
```

---

## 2026-07-22 [Claude Code]: Markaziy brend boshqaruvi commit va main'ga merge

Worktree'da commit qilinmagan holda turgan markaziy brend ishi tekshirildi, saqlandi va `main`'ga birlashtirildi. `SiteSettings` endi to'rtta brand assetini (asosiy wordmark, qorong'i fon wordmark, ixcham belgi, favicon) saqlaydi; barcha logo yuzalari bitta canonical `templates/components/brand_logo.html` adapteridan o'qiydi va hardcode qilingan marklar olib tashlandi. Owner-only `/backoffice/control/brand/` har saqlashda sabab + tasdiq talab qiladi va `LogEntry`ga audit yozadi. Implementatsiya oldingi sessiyada yozilgan; bu sessiya uni verifikatsiya qildi, commit qildi va bir xil commitga ishora qilayotgan ortiqcha `codex/control-center-foundation` branchini o'chirdi.

- Branch: `codex/central-brand-control` → `main`
- Commitlar: `dd76c30` (brend), oldin merge qilinmagan `e1529ce` + `39269dc` (Control Center foundation) ham shu merge bilan `main`'ga o'tdi
- Test holati: `python manage.py test` — **335/335 OK**; `python manage.py check` — **0 issues**; `python manage.py makemigrations --check --dry-run` — **No changes**; `git diff --cached --check` — **OK**
- Davom etilishi kerak: `templates/bot/miniapp_entry.html` o'z `<head>`iga ega, lekin `brand_favicon.html` include'i yo'q (kosmetik). Brend sahifasining browser QA'si (1280x900 / 390x844) hali yugurtirilmagan. Bu band backlogda `ADMIT` sifatida yozilmagan — admission statusini Azurbek tasdiqlashi kerak.

## 2026-07-22 [Codex]: Azure Control Center read-only foundation

Platforma Telegram yoki boshqa bitta adapter atrofida kengaymasligi uchun owner-only `/backoffice/control/` yaratildi. DB, cache, Channels, Celery config, Telegram outbox, media, AI provider/effective token policy, RAG, security va release identity bitta canonical capability registry/snapshot servisida GREEN/AMBER/RED sabab bilan tutashdi; shu servis `system_audit` CLI va responsive backoffice UI tomonidan qayta ishlatiladi. Foundation ataylab read-only: keyingi mutationlar append-only audit, confirmation va idempotency contractisiz qo'shilmaydi.

- Branch: `codex/control-center-foundation`
- Commitlar: `e1529ce`
- Test holati: `python manage.py test` — **330/330 OK**; `python manage.py test core aicontrol` — **40/40 OK**; `python manage.py check` — **0 issues**; `makemigrations --check --dry-run` — **No changes**; browser QA 1280x900 va 390x844 — overflow/console xatosi yo'q, mobil menu ishladi
- Davom etilishi kerak: A2 hali `IN PROGRESS` — `SystemAuditEvent`, feature flag/kill switch, worker/beat heartbeat, `ReleaseRecord`, backup/email/memory probes, AI cost/quality gate va allowlist mutationlar

## 2026-07-22 [Codex]: Nuclear Program solo-owner control plane'ga qayta bazalandi

Uch parallel agent auditidan keyin launch reja feature-first yo'ldan poydevor→control→canonical flow→mobile parity→minimal AI outcome tartibiga o'tkazildi. Agent qoidalariga product authority, adapter boundary va feature admission gate qo'shildi; roadmap/backlog/ops/kontent bir xil ID va exit kriteriylarga moslandi. Azure AI premium claim'i structured evidence, quality/latency/cost gate va yetarli sample bo'lmaganda `INSUFFICIENT_DATA → beta` qaroriga bog'landi; bu commit faqat hujjatlarni o'zgartirdi.

- Branch: `codex/nuclear-program-rebaseline`
- Commitlar: `cf147ac`
- Test holati: `.\venv\Scripts\python.exe manage.py check` — **0 issues**; `git diff --check` — **OK**; relative Markdown links va code fences — **OK**
- Davom etilishi kerak: backlog `A0a` Telegram auth/webhook/access security → `A0b` private media/upload/WebSocket → `A1` production runtime/CI

## 2026-07-21 [Codex]: Telegram bot brendingi yangilandi

`@azureLMSbot` uchun AzureLMS vizual tiliga mos yangi profil logosi yaratildi va loyiha ichida qayta ishlatish uchun branding asseti sifatida saqlandi. BotFather orqali profil rasmi hamda foydalanuvchiga ko'rinadigan tavsif yangilandi; ikkala o'zgarish ham BotFather muvaffaqiyat xabari bilan tasdiqlandi.

- Branch: `codex/mini-app-interface-prototype`
- Commitlar: `8346631`
- Test holati: logo preview vizual QA — **OK**; BotFather description update — **Success**; BotFather profile photo update — **Success**
- Davom etilishi kerak: Telegram keshi yangilangach bot profilining boshqa klientlarda ham tarqalishini kuzatish

## 2026-07-21 [Codex]: Telegram Mini App alohida mobil interfeysi

Telegram Mini App endi katta sayt sahifalariga tayangan bitta home emas, umumiy mobil shell ichidagi to'rtta alohida bo'limga ega: Bosh sahifa, Darslar, Azure AI va Profil. Yangi sahifalar real enrollment, AI suhbatlari va foydalanuvchi sozlamalari bilan ishlaydi; mavjud `initData`, lokal preview va iframe session oqimlari saqlandi. 390x844 va 720x900 browser QA'da active navigatsiya, responsive grid, overflow va console holati tekshirildi. Telegram Web eski CSS'ni cache'da ushlab qolgan holat asset URL versiyasi bilan bartaraf etildi va real iframe'da qayta tasdiqlandi.

- Branch: `codex/mini-app-interface-prototype`
- Commitlar: `629a045`, `5d30cb8`
- Test holati: `python manage.py test bot` — **70/70 OK**; `python manage.py test bot.tests.MiniAppAuthTests` — **10/10 OK**; `python manage.py check` — **0 issues**; browser QA — gorizontal overflow va console xatolari yo'q
- Davom etilishi kerak: real Telegram WebView'da production theme/safe-area sinovi va foydalanuvchi fikriga ko'ra vizual iteratsiya

## 2026-07-21 [Codex]: Telegram Web Mini App real iframe sinovi

Ngrok orqali real Telegram Web Mini App oqimi tekshirildi va ikki blok bartaraf etildi: Django `X-Frame-Options: DENY` hamda iframe ichidagi third-party session cookie. Mini App kirish/home endpointlari iframe uchun ochildi; Telegram HMAC orqali tasdiqlangan sessionlargagina platforma bo'ylab `web.telegram.org` frame ruxsati beradigan middleware qo'shildi. Real Telegram sinovida `admin` sessiyasi bilan Mini App home va ichkaridagi Azure AI sahifasi muvaffaqiyatli ochildi.

- Branch: `codex/local-development-session`
- Commitlar: `20e6660`
- Test holati: `python manage.py test bot` — **69/69 OK**; `python manage.py test bot.tests.MiniAppAuthTests` — **9/9 OK**; `python manage.py check` — **0 issues**; real Telegram Web iframe QA — home va Azure AI ochildi
- Davom etilishi kerak: production deployda `SESSION_COOKIE_SAMESITE=None` va `SESSION_COOKIE_SECURE=True` qiymatlarini HTTPS muhitida berish

## 2026-07-21 [Codex]: Telegram Mini App lokal workspace

Telegram Mini App auth-ko'prigi alohida mobil platforma home sahifasi bilan kengaytirildi: kurslar, Azure AI, imtihon, davomat, sertifikat, to'lov, reyting va yordam oqimlariga bitta WebView markazidan o'tiladi. `APP_ENV=local` uchun oddiy Django login talab qiladigan xavfsiz `?preview=1` rejimi qo'shildi; production Telegram `initData` HMAC oqimi o'zgarmadi. Mobil 390×844 va desktop browser QA'da overflow hamda console xatolari kuzatilmadi.

- Branch: `codex/local-development-session`
- Commitlar: `77cfaba`
- Test holati: `python manage.py test bot` — **69/69 OK**; `python manage.py test` — **321/321 OK**; `python manage.py check` — **0 issues**
- Davom etilishi kerak: public HTTPS domen bilan Telegram WebView'da real `initData` sinovi va BotFather Menu Button aktivatsiyasi

---

## 2026-07-21 [Codex]: Telegram branch main'ga tayyorlandi

`antigravity/telegram-bot-prod` dagi 20 ta commit `main` ustiga fast-forward qilish uchun tekshirildi. Integratsiya oldidan buzilgan `python manage.py runbot` entrypoint lazy `get_bot()` / `get_dispatcher()` API'ga moslandi va regression test bilan himoyalandi.

- Branch: `codex/promote-telegram-main`
- Commitlar: `19526a8`
- Test holati: `python manage.py test` — **316/316 OK**; `python manage.py check` — **0 issues**
- Davom etilishi kerak: `origin/main` ga fast-forward push

---

## 2026-07-18 [Antigravity]: Telegram Deep-Link Auth, AI Limit va Guruhsiz Kurslar Yechimi

Telegram orqali login/register qilish (Deep-link & polling custom flow) sahifalarda tugma orqali ishlaydigan qilindi. AI limit reset yoki bonus qo'llanganda har bir ta'sirlangan foydalanuvchiga platforma va Telegram outbox orqali avtomatik bildirishnoma yuboriladigan bo'ldi. Agar kurs yaratilgan bo'lib, unga birorta ham faol guruh (cohort) biriktirilmagan bo'lsa (ya'ni qabul ochilmagan bo'lsa), tizim endi avtomatik vaqtinchalik guruh yaratmaydi, balki to'g'ridan-to'g'ri `CheckoutUnavailable` xatosi bilan ro'yxatdan o'tishni cheklaydi. Jami 315/315 testlar yashil holatga keltirildi.

- Branch: `antigravity/telegram-bot-prod`
- Commitlar: `79c6149`, `49b45e7`
- Test holati: `python manage.py test` — **315/315 OK**
- Davom etilishi kerak: yo'q

---

## 2026-07-13 [Claude]: Telegram bot F9 — vazifa topshirish + quiz botda (o'qish sikli yopildi)

O'quvchi endi botda nafaqat o'qiydi, balki TOPSHIRADI ham. **Refactor (muhim):** quiz baholash va vazifa saqlash mantig'i `courses/views.py` ichida edi (SubmitQuizView/SubmitAssignmentView) — `courses/submission_service.py` ga chiqarildi (`submit_assignment`, `grade_quiz`); view'lar endi shu servisni chaqiradi, bot ham. Bitta manba: XP hisobi (eng yaxshi urinishdan oshgani beriladi), obuna tekshiruvi, qayta-topshirishda pending'ga qaytish — hammasi bir xil. Courses testlari 31/31 refactor'ni himoya qildi. **Vazifa oqimi:** dars → 📝 Vazifa tugmasi → ro'yxat (holat: ⏳ tekshiruvda / ✅ tasdiqlangan / 🔁 qayta ishlash + o'qituvchi izohi) → shart matni → javob: matn YOKI rasm/fayl (caption bilan) → AssignmentSubmission → o'qituvchi navbatiga (/baholash). **Quiz oqimi:** ❓ Quiz → savol-savol inline tugmalar bilan (javob bosilgach tugmalar o'chadi — qayta bosish yo'q), oxirida natija + XP. **Holat:** aiogram FSM (xotira) o'rniga `BotPendingAction` DB-modeli — bot restart/webhook ko'p-jarayonligida yo'qolmaydi; har userda bitta faol holat. **Handler ustuvorligi:** `AwaitingAssignment` custom filter — vazifa kutilayotganda matn AI'ga emas vazifaga, rasm chekka emas vazifaga ketadi; filter False qaytarsa aiogram odatdagi handler'ga o'tadi (AI/chek oqimlari buzilmadi). /bekor bilan chiqish.

- Branch: `claude/telegram-bot`
- Commitlar: quyidagi commit (F9)
- Test holati: `python manage.py test` — **311/311 OK** (bot: 58→63, +5 F9; courses 31/31 refactor'ni himoya qildi)
- Davom etilishi kerak: **F10 PROD** (yadro tayyor — real o'quvchilarga berish vaqti): alohida bot token, webhook, telegram_outbox --loop worker, BotFather profil, Mini App menu button

---

## 2026-07-13 [Claude]: Telegram bot F8 — botda O'QISH (2-qism boshi, dars-yetkazish)

2-qism (F8–F13) reja: bot saytga kirolmaydiganlar uchun TO'LIQ alternativ bo'lsin (nafaqat kuzatuv — o'qish ham). F8 yadro: o'quvchi endi darsni botning o'zida ochib o'qiydi. `/darslarim`da har kursda "📖 darslar" tugmasi → `student_course_map` modul→dars ro'yxatini beradi (✅ o'tilgan / ▶️ ochiq / 🔒 qulf — qulf mantig'i AYNAN sayt bilan bitta: `_build_lesson_access_bundle` qayta ishlatildi, drip-release + oldingi-dars-vazifasi-tasdiqlangan qoidalari bilan). Darsni ochish (`student_open_lesson`): video havolasi tugmasi (YouTube unlisted) + kontent (CKEditor HTML → `html_to_text` bilan matnga, abzats/ro'yxat saqlanadi, 4000-bo'lak) + "✅ dars o'tildi" — MUHIM: ochish = `_mark_lesson_progress_completed` (sayt LessonDetailView bilan bir xil semantика, LessonProgress+keyingi dars ochiladi). Deep-link: `t.me/bot?start=dars_12` → darsni to'g'ridan-to'g'ri ochadi (`parse_start_payload`); F1 davomat-ogohlantirish DM'iga "📖 Darsni botda ochish" tugmasi qo'shildi — endi kelmagan o'quvchi bir bosishda darsni oladi. Kontent HTML-escape qilinadi (parse_mode xatosidan himoya). Vazifa/quiz mavjudligi ko'rsatiladi (topshirish F9).

- Branch: `claude/telegram-bot`
- Commitlar: quyidagi commit (F8)
- Test holati: `python manage.py test` — **306/306 OK** (bot: 53→58, +5 F8)
- Davom etilishi kerak: F9 vazifa topshirish (matn/foto/fayl → AssignmentSubmission) + quiz inline tugmalar; keyin F10 PROD deploy (yadro tayyor bo'lgach real o'quvchilarga)

---

## 2026-07-13 [Claude]: Telegram bot F7 — AI nazorat botdan (aicontrol to'liq)

Azurbek so'rovi: AI nazorat qismlari botdan boshqarilsin. Backoffice `/backoffice/ai-control/` imkonlari endi botda: **`/ai_sozlama`** — global holat (enforcement, xodim-ozodlik, default limitlar, model), tarif siyosatlari, so'nggi 5 amal (audit) + bitta bosishda "Limitlarni yoqish/o'chirish" tugmasi (bosh rubilnik). **`/ai_limit <5h> <hafta>`** — global default limitlarni o'zgartirish (validatsiya: musbat, hafta ≥ 5h; updated_by yoziladi). **`/ai_reset`** va **`/ai_bonus <miqdor>`** — uch bosqichli oqim: scope (Hammaga/kohort/tarif) → oyna (5h/haftalik/ikkalasi) → qamrov soni bilan tasdiqlash → mavjud `apply_reset_event` servisi (audit `AIUsageResetEvent`, reason="Telegram bot orqali"); callback-zanjir parametrlari 64-bayt limitga sig'adi, draft-model kerak emas. **`/qidiruv` kartasi boyidi**: AI holati qatori (5h/haftalik foiz yoki blok/limitsiz) + "🚫 AI'ni bloklash / ✅ ochish" tugmasi (`AIUserAllowance.is_blocked`). **`/ai_tarif`** (Azurbek so'roviga qo'shimcha): tarif siyosatlari ro'yxati ID'lar bilan; `/ai_tarif ID 50000 500000` — o'rnatish/yangilash (update_or_create, is_active=True), `/ai_tarif ID off` — o'chirish (is_active=False → global defaultga qaytadi, resolve_limits shunga qaraydi). Hech qanday yangi biznes-mantiq yo'q — hammasi aicontrol servislarining ustida.

- Branch: `claude/telegram-bot`
- Commitlar: quyidagi commit (F7)
- Test holati: bot **53/53** (+6 F7: enforcement toggle+guard, limit validatsiya, reset audit bilan, bonus, user-blok/karta, tarif siyosati CRUD); to'liq suite **300/300 OK**; aicontrol 20/20
- Davom etilishi kerak: per-user shaxsiy limit override botdan; prod deploy to'plami

---

## 2026-07-13 [Claude]: Telegram bot F6 — admin paneli kengaytmasi (qidiruv, broadcast, AI stat)

Azurbek so'rovi: platformadagi admin imkonlarini botga kengroq ko'chirish. **`/qidiruv <so'z>`** — user qidiruv (ism/username/email/telefon/telegram, min 3 belgi, top-5): karta (rol, kontaktlar, XP, obunalar+muddatlar) + 🔒 Bloklash/🔓 Faollashtirish tugmasi (himoya: o'zini va staff'ni bloklab bo'lmaydi). **`/broadcast <matn>`** — ommaviy e'lon: matn `BotBroadcastDraft`ga yoziladi (callback 64-bayt limiti uchun; restart'ga chidamli), nishon tugmalari (Hammaga soni bilan / faol kohortlar) → ikkinchi bosqich tasdiqlash → `NotificationBroadcast` yozuvi + har userga Notification. MUHIM nuance: saytdagi `send_broadcast` bulk_create ishlatadi — signal otmaydi, TG'ga tushmaydi; bot versiyasi ATAYIN bitta-bitta create qiladi → post_save signali → outbox → DM (worker 25/15s rate-limit bilan tarqatadi). **`/ai_stat`** — bugun/7 kun token+javob soni, xatolar, top-5 token-user (AIResponseRun aggregate). Buyruqlar menyusi scope'landi: admin buyruqlari faqat admin chatlarida ko'rinadi (BotCommandScopeChat, startup'da staff+telegram_id ro'yxatidan).

- Branch: `claude/telegram-bot`
- Commitlar: quyidagi commit (F6)
- Test holati: `python manage.py test` — **295/295 OK** (bot: 42→47, +5 F6)
- Davom etilishi kerak: backoffice'dagi og'ir tahrir ekranlari (kurs/dars/imtihon formalari) — Mini App orqali prod'da; AI reset/bonus (aicontrol) botdan berish; broadcast'da title/url berish opsiyasi

---

## 2026-07-13 [Claude]: Telegram bot F5 — Mini App auth-ko'prigi (initData → avto-login)

Bot qayta-arxitekturasining so'nggi bosqichi: sayt sahifalarini bot ichida parolsiz ochish poydevori. `bot/miniapp.py` — Telegram WebApp `initData` HMAC-SHA256 validatsiyasi (rasmiy spets bo'yicha: kalit = HMAC("WebAppData", bot_token), 24h muddat, sof funksiya — tarmoqsiz testlanadi) + `safe_next_path` open-redirect himoyasi. `/bot/miniapp/` kirish sahifasi (telegram-web-app.js → initData'ni POST qiladi) va `/bot/miniapp/auth/` (validatsiya → telegram_id bo'yicha user → Django session login; csrf_exempt xavfsiz — autentifikatsiya initData imzosining o'zi). Student menyusida "🌐 Saytni ochish (Mini App)" web_app tugmasi — FAQAT public domenda (Telegram web_app ham localhost'ni rad etadi, F2'dagi URL-tugma saboqlari); Telegram'dan tashqarida ochilsa oddiy login'ga yo'naltiradi. To'liq webview oqimi prod HTTPS chiqqanda sinaladi — validatsiya/login qatlami esa 5 test bilan qoplangan (roundtrip, tampered/expired/wrong-token, unlinked 404, session ochilishi, next-sanitizatsiya).

- Branch: `claude/telegram-bot`
- Commitlar: quyidagi commit (F5)
- Test holati: `python manage.py test` — **290/290 OK** (bot: 37→42, +5 F5)
- Davom etilishi kerak: prod deploy'da BotFather orqali Menu Button (Web App) sozlash; og'ir sahifalarga (dars tahriri, imtihon, checkout) miniapp_button'lar mobil-moslashuv tuzatishlaridan keyin; admin broadcast

---

## 2026-07-12 [Claude]: Telegram bot F4 — o'qituvchi/admin buyruqlari + notification outbox

Bot endi platformaning push-kanali va admin-pulti. **Outbox:** `users.Notification` yaratilganda signal `TelegramOutbox`ga yozadi (recipient'da telegram_id bo'lsa); worker (run_bot ichida polling bilan parallel, prod uchun `manage.py telegram_outbox [--loop]`) 15s siklda 25 tadan yuboradi, 3 urinishdan keyin failed; user botni bloklagan bo'lsa jim failed, sayt-qo'ng'iroqcha baribir turadi. Jonli tasdiqlandi: Notification → 15s ichida real DM. **O'qituvchi:** /guruhlarim (o'quvchi soni, TG bog'langanligi, oxirgi davomat), /baholash (tekshirilmagan imtihon/vazifalar — teacher_views helper'lari qayta ishlatildi). **Admin:** /stat (platforma sonlari), /cheklar — chek RASMI bilan keladi, ✅ Tasdiqlash / ❌ Rad tugmalari: tasdiq `PaymentReceipt.save()` orqali enrollmentni faollashtiradi (mavjud model-mantiq), userga Notification yoziladi → outbox orqali DM ham boradi (to'liq zanjir: chek → tasdiq → o'quvchiga avto-xabar). Rad: receipt o'chadi (promo bo'shaydi), userga qayta-yuborish xabari. Yo'lda: run_bot print'idagi '→' cp1252 konsolda UnicodeEncodeError berdi — ASCII'ga almashtirildi.

- Branch: `claude/telegram-bot`
- Commitlar: quyidagi commit (F4)
- Test holati: `python manage.py test` — **285/285 OK** (bot: 30→37, +7 F4: outbox mirror/holatlar, verify/reject/huquq, teacher scope, stats)
- Davom etilishi kerak: broadcast (admin ommaviy xabar) — rate-limit bilan; teacher e'lon guruhga; prod: webhook + `telegram_outbox --loop` worker + alohida bot tokeni; F5 Mini App

---

## 2026-07-12 [Claude]: Telegram bot F3.5 — botdan kursga yozilish (to'liq checkout oqimi)

Azurbek taklifi: qabul ochiq kurslar + yozilish botda bo'lsin. Oqim: `/yozilish` (yoki menyudagi 🎓) → faol kurslar ro'yxati inline tugmalar bilan → tarif tanlash (narx/⭐️ ommabop) → to'lov rekvizitlari (summa, karta raqami/egasi — SiteSettings'dan, davr) → user chek RASMINI yuboradi (F.photo) → Telegram'dan fayl yuklab olinib `PaymentReceipt` yaratiladi → backoffice'dagi mavjud tasdiqlash oqimiga tushadi. MUHIM: biznes-mantiq yozilmadi — sayt checkout servislari qayta ishlatildi (`resolve_checkout_enrollment` kohort tanlash/pending enrollment, `create_checkout_receipt_with_promo` chek+summa, davr hisobi checkout_view bilan bir xil). Guard'lar: tasdiqlanmagan chek borida qayta boshlash/qayta chek bloklanadi; tarif tanlanmagan rasmga halol hint; chek nishoni = tarifi tanlangan, cheki yo'q eng so'nggi enrollment (stateless — bot restart holatni yo'qotmaydi).

- Branch: `claude/telegram-bot`
- Commitlar: quyidagi commit (F3.5)
- Test holati: `python manage.py test` — **278/278 OK** (bot: 26→30, +4 F3.5)
- Davom etilishi kerak: promo-kod kiritish botda (servis tayyor, UI yo'q); chek tasdiqlanganda userga DM (F4 outbox); F4 o'qituvchi/admin

---

## 2026-07-12 [Claude]: Telegram bot F3 — o'quvchi workspace + AI repetitor DM

F2 telefon-sinovda tasdiqlandi (yo'lda 2 tuzatish: localhost URL-tugmani Telegram rad etadi → lokalda callback-tugma + global error-boundary; email unique='' to'qnashuvi → placeholder email). F3: bog'langan user uchun ish stoli. `/darslarim` — progress bar bilan kurslar (users.views.build_student_enrollments QAYTA ishlatiladi, dashboard bilan bir xil hisob), `/davomatim` — so'nggi 10 davomat, `/tolov` — tarif/holat/muddatlar; /start menyusi inline tugmalar bilan. Eng muhimi: **erkin matn → messenger AI engine** (`telegram_ai_reply`): har userga doimiy "Telegram AI suhbati" xonasi (saytdagi Messengerda ko'rinadi), `generate_ai_response.run` — skills/xotira/RAG/aicontrol-kvota hammasi sayt bilan bitta; suppress_ai_signal bilan dublikat generatsiya oldi olinadi; javob 4000-belgili bo'laklarda, parse_mode'siz (markdown-entity xatolaridan xavfsiz). Guruh (F1) va mehmon (F2) oqimlariga tegilmagan.

- Branch: `claude/telegram-bot`
- Commitlar: quyidagi commit (F3), `422dad4` (email fix), `0de42f3` (URL-tugma fix), `1d21049` (F2), `377f9e9` (F0+F1)
- Test holati: `python manage.py test` — **274/274 OK** (bot: 21→26, +5 F3 testi)
- Davom etilishi kerak: F4 o'qituvchi/admin buyruqlari + notification outbox (platforma hodisalari → DM); AI javobida rasm/hujjat attachment'lar (engine SVG/PDF qaytarsa hozircha faqat matn ketadi); prod: alohida bot + webhook + kvota belgisi

---

## 2026-07-12 [Claude]: Telegram bot F2 — onboarding voronkasi (landing, AI demo, telefon-ro'yxat)

F0+F1 Azurbek tomonidan telefonda sinab tasdiqlandi, davomi qurildi. Mehmon (bog'lanmagan) user endi botda to'liq landing oladi: /start → tanituv + inline menyu (📚 Kurslar / 💰 Narxlar / 🤖 AI savol / 📝 Ro'yxat). Kurslar va tariflar to'g'ridan-to'g'ri DB'dan (faol kurslar, Plan+PlanFeature, HTML strip). AI demo: mehmon oddiy matn yozsa `get_chat_provider().generate` mahsulot-konteksti bilan javob beradi (kurs/tarif ma'lumoti promptga quyiladi, to'qish taqiqlangan) — `BotGuest` modelida 5 savollik limit, provider xatosi kvotani yemaydi. Ro'yxat ikki yo'l: (a) telefon-kontakt tugmasi — `contact.user_id == from_user.id` tekshiruvi bilan (faqat o'z raqami), mavjud hisob telefon bo'yicha topilsa bog'lanadi, bo'lmasa yangi user yaratiladi (unusable password, normalize qilingan +998... raqam); (b) sayt register havolasi. Bog'langan userning erkin matni F3'gacha hint oladi.

- Branch: `claude/telegram-bot`
- Commitlar: quyidagi commit (F2), `377f9e9` (F0+F1)
- Test holati: `python manage.py test` — **266/266 OK** (bot: 11→18, +7 F2 testi)
- Davom etilishi kerak: F3 o'quvchi workspace (darslarim/to'lov/davomat menyusi) + AI repetitor DM (messenger engine'ga ulash) + notification outbox; F4 o'qituvchi/admin; prod uchun alohida bot + webhook

---

## 2026-07-12 [Claude]: Telegram bot qayta-arxitektura F0+F1 — skelet + Davomat v2

Azurbek talabi: bot kompyutersiz auditoriya uchun platformaning to'liq interfeysi bo'lsin (reja: `nuclear-program/telegram-bot-plan.md`, F0–F5 bosqichlar kelishilgan). Bu sessiyada F0+F1:

**F0 (skelet):** `Bot(token=...)` endi lazy (`get_bot()/get_dispatcher()`) — bo'sh token loyihani yiqitmaydi (eski boot-mina yopildi, `manage.py check` bo'sh token bilan ham o'tadi). `bot/middleware.py` IdentityMiddleware — har update'da telegram_id → user + rol (admin/teacher/student/linked/guest), handler'lar `lms_user`/`lms_role` oladi. `bot/handlers.py` → `bot/routers/` paketi: `group_ops` (guruh, chat-type filtr) + `onboarding` (shaxsiy chat; F2 landing shu yerga quriladi).

**F1 (Davomat v2):** o'zbekcha buyruqlar `/dars 1`, `/dars tugadi` (aliaslar: tamom/yakun/stop; eski /start_lesson, /close_lesson ham ishlaydi), `/davomat` — joriy sessiya holati. Yopishda: ismli keldi/kech/kelmadi e'loni (kelmaganlar @username yoki tg://user link bilan chertiladi, HTML-escape bilan), kelmaganlarga DM ogohlantirish (dars havolasi bilan; botni ochmaganlarga jim o'tadi) + platforma-Notification (idempotent `tg-absent-<session>` external_key). Servis qatlami kengaydi: `CloseLessonResult.details` (ismli ro'yxatlar), `get_open_session_status`, `student_display_name`.

Jonli tekshirildi: @azureLMSbot polling'da ishga tushdi (dev token — production uchun keyin alohida bot, Azurbek qarori).

- Branch: `claude/telegram-bot`
- Commitlar: quyidagi commit
- Test holati: `python manage.py test` — **259/259 OK** (bot: 4→11, +7 yangi)
- Davom etilishi kerak: F2 onboarding voronkasi (tanituv, kurslar, AI demo, ikki yo'lli ro'yxat — telefon-kontakt + sayt); F3 o'quvchi workspace + AI repetitor DM; guruhda haqiqiy telefon-sinov (Azurbek)

---

## 2026-07-12 [Claude]: Branch konsolidatsiya — main yagona zamonaviy branch (Azurbek ruxsati)

Azurbek buyrug'i bilan barcha tarqoq branch'lar main'ga jamlandi va o'chirildi. `claude/ai-context-understanding` (AI suhbat-konteksti + vidjet tuzatish, 8 commit) main'ga merge qilindi; `claude/ai-conversation-quality`ning 4 commit'i allaqachon patch-ekvivalent holda main'da edi (git cherry tasdiqladi), qolgan 5 branch (ai-admin-control, ai-hybrid-search, ai-persona, fix-new-chat-405, user-usage-panel) to'liq merge bo'lgan edi. Hammasi (lokal + remote) o'chirildi. Bundan keyin yangi ish yana prefiks-branch'larda boshlanadi, lekin eski qoldiqlar yo'q — main = yagona haqiqat manbai.

- Branch: `main`
- Commitlar: merge `claude/ai-context-understanding` (`0cdaecf`..`f6a3238`), `566f17d` (vidjet cherry-pick, avvalroq)
- Test holati: `python manage.py test` — **252/252 OK** (merge'dan keyin to'liq to'plam)
- Davom etilishi kerak: `python manage.py reindex_ai_memory` bir marta (9-iyul yozuvidagi qoldiq); mobil moslashuv rejasi kutmoqda

---

## 2026-07-12 [Claude]: AI vidjet (boyo'g'li) tuzatildi — dublikat skript panelni ochirmayotgan edi

Floating AzureAI vidjeti (app sahifalardagi boyo'g'li tugma) umuman ishlamayotgan edi: `ai-widget.js` ham `base_app.html` head'ida, ham include (`ai_assistant_widget.html`) ichida ulangan — IIFE ikki marta yugurib, ikkita click-listener panelni ochib-darhol yopar, submit esa ikki POST yuborar edi. Head'dagi dublikat olib tashlandi (skript endi faqat include ichida — include o'zi-yetarli bo'lib qoldi), JS'ga `dataset.azaiInit` ikki-marta-init himoyasi qo'shildi. Dars sahifasiga (`lesson_detail.html`) ham vidjet qo'shildi — o'quvchi darsdan chiqmasdan savol so'raydi. Backend (lazy room) allaqachon to'g'ri edi, tegilmadi: bo'sh ochib-yopilsa xona yaratilmaydi; birinchi xabardan keyin xona yaratilib messengerda avto-nomlangan suhbat sifatida chiqadi, keyingi xabarlar o'sha xonada davom etadi — hammasi jonli tekshirildi (real AI javob bilan, room 83).

Diagnostika eslatmasi: lokal `runserver`ni `--noreload` bilan yugurtirmang — Django 4.1+ cached template loader'ni DEBUG'da ham yoqadi va keshni faqat autoreloader tozalaydi; `--noreload`da template tahrirlari serverga yetib bormaydi (shu sessiyada 20 daqiqa yegan tuzoq).

- Branch: `claude/ai-context-understanding`
- Commitlar: `cf52d4e`
- Test holati: `python manage.py test messenger` — **85/85 OK**
- Davom etilishi kerak: mobil moslashuv auditi alohida reja bo'lib turibdi (messenger 1-panel rejimi, checkout/dashboard gridlari); vidjet hozir student shell + dars sahifasida — teacher/backoffice'ga ataylab qo'shilmadi

---

## 2026-07-09 [Claude]: AI suhbat-konteksti — skill stickiness, kontekstli retrieval, embed-on-write

Uch yo'nalishda takomil: (1) SUHBAT OQIMI — skill tanlash faqat joriy xabarga qarardi, quiz o'rtasidagi "B" yoki "davom et" javobi keyword'siz bo'lgani uchun general_chat'ga tushib oqim uzilardi. Endi keyword'siz qisqa davomiy xabar xonaning oxirgi muvaffaqiyatli skillida qoladi (AIResponseRun, 3 soatlik oyna; web_search/smart_form/general_chat sticky emas). Prompt'ga SUHBAT OQIMI bo'limi (qisqa xabar = oxirgi mavzu; berilgan savolga javobni AVVAL baholash; mavzuni ushlab turish), quiz SKILL.md'ga javob-baholash qoidasi. (2) USERNI TUSHUNISH — memory+RAG retrieval faqat oxirgi xabar bilan qidirardi ("buni tushuntir" hech narsa topmasdi). Endi ≤5 so'zli anaforik savol retrieval uchun oldingi 2 user xabari bilan boyitiladi (promptdagi user_question o'zgarmaydi). Oldingi sessiyada qoldirilgan "yozganda embed" ham bajarildi: fakt saqlanganda vektor yoziladi (fail-open, reindex_ai_memory bilan bir xil format) — semantik vektor-retrieval endi tirik. (3) SKILL ANIQLIGI — keyword matching substring edi ("protest"→"test", "diskurs"→"kurs" false-positive); endi so'z boshi talab qilinadi, o'zbek qo'shimchalari ("kursi") ishlayveradi.

Yo'lda tuzatildi: GenerateAiResponseTaskTests setUp'ida messenger.rag.embed_texts guard — lokalda GEMINI_API_KEY bor muhitda SAVE_MEMORY testlari tarmoqqa chiqmasin (embed-on-write fail-open bo'lgani uchun saqlash oqimi buzilmaydi).

Jonli sinov tuzatishi (room 78): "kajol'ni taniysanmi?" savoli ko'rsatdiki, "qisqa xabar = oxirgi mavzu" qoidasi mavzu ALMASHUVI bilan ziddiyatga tushardi — model yangi savolga javob berib, oxirida eski mavzuni (mushuklar) majburan qaytarardi, ustiga Kajol ismini "kajal/surma"ga tarjima qilishga urinardi. Prompt qoidasi ikkiga ajratildi: qisqa DAVOM xabari ≠ qisqa YANGI-mavzu xabari; yangi mavzuda eski mavzu qaytarilmaydi, javobsiz qolgan savol qistalmaydi; ismlarni tarjima qilish/majburan turkchaga bog'lash taqiqlandi.

Ikkinchi jonli tuzatish (room 79): "internetdan qidirib..." web_search'ga TO'G'RI tushdi, lekin Gemini bepul kvotasi tugagan (429 RESOURCE_EXHAUSTED, 9 modelning hammasi; pro-modellarda limit: 0 — bepul tarif yo'q) va butun javob yiqilib qo'pol billing-xabar chiqardi. Endi mutaxassis runtime-xatosi butun so'rovni yiqitmaydi — maverick'ka qaytiladi va u "jonli qidira olmadim" deb halol javob beradi (metadata: search_specialist_failed). Kvota har kuni Tinch okeani yarim tunida (~Toshkent 12:00) yangilanadi.

- Branch: `claude/ai-context-understanding`
- Commitlar: `0cdaecf`, `28314d6` (jonli sinov tuzatishi), `354702e` (Gemini-yiqilish degradatsiyasi)
- Test holati: `python manage.py test` — **250/250 OK** (11 yangi: 4 registry stickiness/word-boundary, 3 retrieval-query, 3 embed-on-write, 1 engine)
- Davom etilishi kerak: mavjud eski faktlar uchun `python manage.py reindex_ai_memory` bir marta yugurtirilishi kerak (yangi faktlar o'zi embed bo'ladi); stickiness hozir evristik (≤6 so'z + davom-so'zlari) — kerak bo'lsa keyin LLM-router; jonli suhbatda smoke-test qilib main'ga merge Azurbek ruxsati bilan

---

## 2026-07-06 [Claude]: AI suhbat sifati — persona qayta-yozish + xotira relevance-darvoza

Real suhbat transkripti (room 68) tahlili ko'rsatdiki, asosiy muammo mexanikada emas, AI'ning SUHBATLASHISHIDA edi: har javob bir xil qolipda (iliq gap + emoji + savol), hamma narsaga rozilik (sikofant bo'shlik), aloqasiz mavzuga xotira-fakt quyilishi ("mushuk obsessiyasi"), inglizcha so'z o'yini hazillari, oddiy o'yin qoidasini ushlab turolmaslik.

Dalilga asoslangan diagnoz (scratchpad probalar + jonli maverick): (1) xotira vektorlari o'lik — faktlar yozilganda umuman embed qilinmaydi (embedding_model=''), shu bois retrieve_scored har javobga category_prior baseline (~0.286) bo'yicha HAMMA faktni quyardi; (2) "Shoy shovliq" kabi noto'g'ri tarjima model chegarasi emas — maverick toza promptda "Görüşmek üzere→ko'rishguncha"ni to'g'ri qiladi, aybdor prompt ortiqcha yuklanishi + axlat-xotira; (3) mistral-3-14B fallback o'zbekchada kirill axlat chiqaradi.

Tuzatishlar:
- Persona qayta-yozildi (builder.py + general_chat SKILL.md): umurtqa (rozi bo'lavermaslik), dars-niyati (turkchani tabiiy qo'shish), emoji kam, doim savol bilan tugatmaslik, ichki-mexanika taqiqi, hazil lokalizatsiyasi, o'yin-holati intizomi, SAVE_MEMORY shablon-echo taqiqi.
- Xotira relevance-darvoza (retriever): faqat lexical/semantic/vector signali bor fakt promptga tushadi — baseline-dump yo'q. Jonli tasdiq: user 38'da "hayot ma'nosi/hazil/Toshkent" endi mushuk quymaydi.
- Extraction hardening (policy): "category: X" shablon-echo + yalang'och toifa nomlarini rad. Dedup (repository): fingerprint apostrof/tinish variantlarini birlashtiradi. prune_ai_memory buyrug'i — mavjud axlatni arxivlaydi (mahalliy: 5 ta).
- mistral-3-14B DO fallback zanjiridan olib tashlandi.

Halol chegara: hazil sifati va chuqur ko'p-turlik o'yin-holati baribir maverick chegarasi (prompt qisman yaxshiladi, to'liq emas). Vektor semantik-qidiruvni tiriltirish (yozganda embed) — keyingi ish; reindex_ai_memory buyrug'i bor, faqat ishga tushirilmagan.

- Branch: `claude/ai-conversation-quality` (playground — main'ga tegilmadi)
- Commitlar: `f60bcdc` (memory), `71ceab7` (persona), `e0d45f5` (provider)
- Test holati: `python manage.py test` — **239/239 OK**
- Davom etilishi kerak: yozganda embed → semantik retrieval (RAG_EMBEDDING_MODEL/bge-m3); mem0 baholash; conversation_partner/word_builder skilllari; vocab skilliga few-shot; so'ng user ruxsati bilan main'ga merge

---

## 2026-07-05 [Claude]: O'quvchilar uchun AI foydalanish paneli (Claude Settings→Usage uslubida)

User Claude'ning o'z "Plan usage limits" ekranini ko'rsatib, o'quvchilarga ham shunday panel so'radi. Backend (aicontrol) tayyor edi — faqat UI. `aicontrol/service.build_usage_panel(user)` — get_quota_status'ni tayyor-shablon dict'ga aylantiradi (session/weekly: used/limit/percent/remaining/reset_at + unlimited/blocked bayroq). Settings sahifasida to'liq "AI foydalanish limiti" bo'limi (2 progress-bar: joriy sessiya 5h + haftalik; %, token hisobi, timeuntil reset; 80%→amber, 100%→qizil; staff→"Limitsiz"; blocked→qizil ogohlantirish). Dashboard'da ixcham 5h-% indikator karta (settings'ga havola). Ikkalasi bir manba. Model bo'yicha bo'linmaydi (maverick bitta, Gemini faqat qidiruvda) — 2 bar yetarli. 3 yangi test.

- Branch: `claude/user-usage-panel` → main'ga merge
- Test holati: `python manage.py test` — **239/239 OK**
- Davom etilishi kerak: real-time yangilanish (hozir sahifa yuklashda server-render); "qolgan token" messenger composer yonida (ixtiyoriy)

---

## 2026-07-05 [Claude]: AI token-limit boshqaruv markazi (admin nazorati kengaytirildi)

User AI token-iqtisodiyotini admin uchun markazlashgan boshqaruv talab qildi: modellar/tokenlar/limitlar bir joydan; foydalanuvchi 5 soatlik + haftalik limitlari; bayram/event uchun ommaviy/guruh/tarif reset-bonuslari. Qarorlar (AskUserQuestion): birlik=TOKEN, ko'lam=tarif+shaxsiy override, reset=hammaga+kohort+tarif.

**Yangi `aicontrol` app.** Modellar: AISettings (singleton — global default 5h/haftalik limit, enforcement master switch, staff-exempt, default model/effort), AIPlanPolicy (tarif bo'yicha limit), AIUserAllowance (OneToOne — shaxsiy override, reset markerlari, bonus, is_blocked), AIUsageResetEvent (audit: scope all/cohort/plan · kind reset/bonus · window 5h/weekly/both · sabab · affected_count · created_by).

**Token hisobi:** ProviderResponse.usage; DO payload['usage'] + Gemini usage_metadata; AIResponseRun'ga prompt/completion/total_tokens (messenger migration 0013); tasks.py saqlaydi.

**Limit mantig'i (service.py):** resolve = override → tarif siyosati → global default (+ bonus). Oyna rolling: used = AIResponseRun.total_tokens yig'indisi (now-5h/now-7d dan yoki reset markeridan, qaysi kech). get_quota_status → allowed/reason/used/limit/reset_at. Enforcement generate_ai_response boshida, **fail-open** (limiter xatosi chatni bloklamaydi): limit oshsa engine chaqirilmaydi, halol xabar + tiklanish vaqti; staff ozod; master switch. apply_reset_event scope bo'yicha (bounded: so'nggi 7 kun faollar) qo'llaydi.

**Admin UI 2 xil:** (1) Django admin — 4 model + reset event saqlansa avtomatik qo'llanadi (tez yo'l). (2) **AdminShell `/backoffice/ai-control/`** — usage overview (5h/hafta token, faol/bloklangan), global limit formasi, tarif-policy jadval (inline tahrir), reset/bonus formasi (scope→dinamik kohort/tarif tanlov, JS bilan), top-10 token-user, so'nggi amallar. Backoffice nav'ga "AI boshqaruvi" qo'shildi.

- Branch: `claude/ai-admin-control`
- Test holati: `python manage.py test` — **236/236 OK** (aicontrol 17 + backoffice AI 3 yangi)
- Davom etilishi kerak: `/settings` sahifasidagi AI model tanlovi hali AISettings bilan bog'lanmagan (ixtiyoriy); token narx→so'm hisobi hisobot uchun; o'quvchi dashboard'ida "qolgan token" indikatori

---

## 2026-07-05 [Claude]: Gibrid AI — Gemini FAQAT web-qidiruv uchun (maverick asosiy)

User web-qidiruvni tikladi, lekin Gemini bepul kvotasini tejash sharti bilan: qidiruv Gemini'da, qolgani maverick'da. Muammo edi: DO/maverick `supports_web_search=False` — jonli qidira olmaydi, `web_search` skilli tanlansa ham AI faktlarni to'qirdi.

**Arxitektura (qobiliyat-asosli provayder tanlash):** `get_search_provider()` — Gemini'ni FAQAT kalit+qobiliyat bo'lsa qaytaradi (`GeminiProvider.supports_web_search=True`). `AIEngine`'ga `search_provider` inject (sentinel bilan; konstruktor tarmoqqa chiqmaydi — arzon). `generate_reply`: `wants_web_search AND rasm yo'q` bo'lsa — asosiy qidira olsa asosiy, aks holda Gemini mutaxassisi (grounding, selected_model uzatilmaydi — DO modelini tanimaydi); aks holda maverick. Rasm bo'lsa vision ustun (maverick'da qoladi). Kalit yo'q → maverick'da halol javob, crash yo'q. Metadata: `search_specialist_used`.

**web_search skilli takomili:** `_render_web_search` tool-konteksti SKILL.md bilan ZID edi ("(Manba N) yoz" deb, skill esa "yozma" derdi) — tuzatildi; halollik kuchaytirildi (jonli natija yo'q bo'lsa faktni TO'QIMASLIK). Bir nechta yuqori-aniqlikdagi trigger qo'shildi (eng so'nggi, valyuta kursi, real vaqt...) — konservativ, minimal-usage saqlanadi.

**Jonli sinov (haqiqiy Gemini+maverick):** "Internetdan qidirib ber: bugungi yangiliklar" → Gemini (gemini-2.5-flash), grounding, **8 haqiqiy manba**, jonli O'zbekiston yangiliklari ✓; "Turkchada rahmat qanday?" → maverick, Gemini TEGMADI ✓. 6 ta unit test aynan shu kafolatni tekshiradi (oddiy chat search_provider'ni chaqirmaydi).

**NB (deploy):** ishlashi uchun `GEMINI_API_KEY` env'da bo'lishi shart (lokalda bor). Yo'q bo'lsa — jonli qidiruv o'chadi, chat ishlayveradi. Bu DO-only qaroriga maqsadli, tor istisno (faqat qidiruv).

- Branch: `claude/ai-hybrid-search`
- Test holati: `python manage.py test` — **216/216 OK** (6 yangi ai.agent provayder-routing testi); jonli Gemini+maverick smoke o'tdi
- Davom etilishi kerak: web_search skill-tanlash hali kalit-so'zga bog'liq (semantik "aholisi qancha" kabi savollar general_chat'ga tushadi — ataylab, kvota tejash uchun); kerak bo'lsa LLM-router; prod'da GEMINI_API_KEY env qo'shish

---

## 2026-07-05 [Claude]: Azure AI endi rasmlarni ko'radi va o'zi chizadi (vision + SVG)

**Kashfiyot:** DO'dagi llama-4-maverick tug'ma multimodal ekan — jonli probe rasmdagi "MERHABA" yozuvini o'qib tarjima qildi. Yangi xizmat/xarajat YO'Q. **Ko'rish:** provider `images` param oldi (OpenAI-uslub content array, `supports_vision=True`); yuklangan rasm Pillow bilan 1280px JPEG data-URL'ga tayyorlanadi (`ai/documents/images.py`); AI xonasiga rasm yuklansa AI o'zi javob boshlaydi, keyingi savollarda xonadagi oxirgi rastr rasm avtomatik so'rovga biriktiriladi (AI'ning o'z SVG'lari hisobga olinmaydi — loop yo'q). **Chizish:** `<SVG_IMAGE title>` bloki (PDF_DOC naqshi) → server QAT'IY allowlist sanitizer bilan zararsizlantiradi (script/foreignObject/on*/href butunlay o'chadi, ElementTree asosida) → .svg attachment (image/svg+xml) → chatda rasm sifatida ko'rinadi. Yangi `image_qa` skilli (rasm/chiz/flashcard triggerlari; rasm bor + neytral savol → shu skill; tanlash tartibi: image → document → lesson).

Yo'lda tuzatildi: chat bubble'larida attachment SERVER-RENDER'da umuman chiqmasdi (sahifa yangilanganda fayllar "yo'qolardi") — ai.html'ga ikkala tarafga attachment bloki qo'shildi; JS'da rasm uchun haqiqiy <img> preview.

Jonli DO sinov: rasmdagi "KITAP OKUMAK / COK GUZELDIR" o'qilib to'g'ri tarjima qilindi ✓; "ev uchun flashcard chiz" → "Ev sozi uchun flashcard.svg" (sanitizer'dan o'tgan, is_image) ✓.

- Branch: `claude/ai-persona` (persona + PDF + rasm — bitta AI-yaxshilanishlar to'plami)
- Test holati: `python manage.py test` — **210/210 OK** (9 yangi rasm testi bilan)
- Davom etilishi kerak: foto-realistik rasm generatsiyasi ATAYLAB yo'q (tashqi pullik API kerak bo'lardi — DO-only byudjet qaroriga zid); SVG hozircha bitta blok/javob

---

## 2026-07-04 [Claude]: AI'ga shaxsiyat berildi — "sovuq yordamchi" muammosi hal

Shikoyat: "do'stlashamizmi / senga yoqdimi / qaysini tanlarding" kabi savollarga AI "men AI yordamchiman, didim yo'q" deb oqimni sovutardi. Sabab (jonli repro bilan tasdiqlandi): prompt'da persona YO'Q edi (bitta jumla: "xavfsiz va ishonchli AI yordamchisisiz"), xavfsizlik qoidasi "o'zingizni boshqa obrazda tanishtirmang" ijtimoiy savollarni ham bosardi, Llama-maverick defolt RLHF naqshiga tushardi.

Yechim (`ai/prompts/builder.py` + `ai/skills/general_chat/SKILL.md`): "SIZNING SHAXSINGIZ" bloki — ism (Azure), xarakter (turk tili/madaniyati/seriallarini yaxshi ko'radigan quvnoq o'quv-do'st), ijtimoiy savol qoidasi (tanlov so'ralsa bittasini tanlab sabab aytish, do'stlashishni iliq qabul qilish, "men AI man"ni faqat jiddiy so'ralganda aytish), chegaralar (romantika yo'q, real inson deb da'vo qilmaslik). Xavfsizlik taqiqi aniqlashtirildi: faqat qoida-buzuvchi obraz almashtirishga tegishli. Friendly tonga munosabat qoidasi qo'shildi.

Oldin/keyin (haqiqiy DO maverick): "qaysi serialni tanlarding?" → OLDIN: "Men AI yordamchisiman, shaxsiy didim yo'q..." → KEYIN: "Men 'Erkenci Kuş' serialini juda yaxshi ko'raman, chunki...". Guardrail'lar tekshirildi: DAN-jailbreak xarakter ichida rad etiladi, "jiddiy so'rayapman, dasturmisan?" ga halol "Men dasturman" javobi.

- Branch: `playground`
- Test holati: `python manage.py test` — **189/189 OK**; 4 ta jonli DO smoke (2 ijtimoiy + 2 guardrail)
- Davom etilishi kerak: boshqa skill SKILL.md'lariga ham (grammar_corrector, speaking_coach...) persona-mos ohang tekshiruvi (ixtiyoriy)

---

## 2026-07-05 [Claude]: Azure AI endi PDF bilan ishlaydi (o'qish + yaratish, e2b'siz)

Ikki yo'nalish, ikkalasi jonli DO sinovidan o'tdi. **O'qish:** AI xonasiga PDF yuklansa AI o'zi javob boshlaydi (upload view'da dispatch; avval `suppress_ai_signal` tufayli fayl xabarlari AI'ga umuman yetmasdi); keyingi savollarda xonadagi oxirgi PDF avtomatik kontekst bo'ladi (`ai/documents/reader.py` — pypdf, 40 sahifa/15k belgi limit, xato-chidamli; prompt'da "YUKLANGAN HUJJAT" bo'limi). **Yaratish:** foydalanuvchi hujjat so'rasa AI javob oxirida `<PDF_DOC title>markdown-subset</PDF_DOC>` bloki yozadi (SAVE_MEMORY naqshidek), server `ai/documents/writer.py` (fpdf2 + DejaVu Unicode — turkcha ı/ğ/ş to'liq; sarlavha/ro'yxat/jadval render, brend header/footer) bilan haqiqiy PDF yasab AI xabariga biriktiradi — chatdagi mavjud attachment UI'da yuklab olinadi (broadcast'ga attachment payload qo'shildi). AI kodi BAJARILMAYDI — e2b/sandbox keraksiz (arxitektura qarori marinebook 2026-07-04 muhokamasiga mos).

Yangi `document_qa` skilli (trigger: pdf/hujjat/fayl...; hujjat bor+neytral savol→shu skill). Deps: pypdf 6.14.2, fpdf2 2.8.7 (requirements'da). Jonli sinov: konspekt-PDF yuklab "beklemek nima degani?" → AI hujjatdan "kutmoq" + qoidani topdi ✓; "3 fe'ldan PDF lug'at yasab ber" → "Turkcha-Ozbekcha Fellar Lugati.pdf" (18KB) biriktirildi, ichida so'zlar bor ✓.

- Branch: `claude/ai-persona` (persona fixi ustiga — ikkalasi bitta PR bo'lib main'ga boradi)
- Test holati: `python manage.py test` — **201/201 OK** (12 yangi ai.documents testi bilan)
- Davom etilishi kerak: DOCX o'qish (python-docx, xuddi shu quvurga oson qo'shiladi); skan-rasm PDF'lar uchun OCR yo'q (matn bo'sh bo'lsa AI foydalanuvchiga tushuntiradi)

---

## 2026-07-04 [Claude]: Smart Form Engine ta'mirlandi — endi haqiqatan ishlaydi

Antigravity'ning kechagi Smart Form MVP'si (AI bilan suhbat orqali onboarding) 6 ta bug tufayli ishlamasdi: (1) `users/forms/` namespace-package `users/forms.py` soyasida — forma registry HECH QACHON to'lmasdi (asosiy sabab); (2) extractor google.genai'ga qattiq bog'langan — DO stack'da hech narsa ajratmasdi, suhbat bitta savolda aylanardi; (3) status exclude UPPERCASE vs lowercase qiymatlar — tugagan session xonani abadiy band qilardi; (4) submit URL o'rniga matn qaytarardi; (5) "ha" tasdiqlash sikli hal qilinmagan; (6) xona bo'sh ochilardi.

Tuzatishlar: forma `users/smart_forms.py`da (apps.ready import, pydantic normalizatsiya validatorlari — goal/level model choices'ga), extractor provider-agnostik (`get_chat_provider`, fence-tolerant JSON, prompt'da tasdiqlash qoidasi), `SmartFormSession.ACTIVE_STATUSES`+`active_for_room()` helper, submit → `reverse('dashboard')`, welcome AI xabari + takroriy sessiya guard, AIEngine bloki try/except himoyada.

**Jonli sinov (haqiqiy DO maverick bilan):** "sayohat uchun o'rganmoqchiman" → goal=travel ✓ → "B1 deb o'ylayman" → needs_confirmation → CONFIRM_LEVEL ✓ → "Ha, to'g'ri" → confirmed → SUBMIT → UserOnboarding(travel, b1), session completed, dashboard URL ✓.

- Branch: `claude/teacher-shell` → **playground'ga merge qilindi** (user so'rovi: "ishlata olsang playgroundga olib kel")
- Commitlar: `490e3a7` (fix), `59de4d5` (test), + marinebook
- Test holati: `python manage.py test` — **189/189 OK** (14 yangi smart_form testi bilan); jonli DO smoke o'tdi
- Davom etilishi kerak: "Tezkor anketa" (klassik yo'l) hozir to'g'ridan dashboard'ga o'tadi — xohlansa oddiy forma sahifasi qo'shish; SmartFormSession'ga eskirish (expired) cron'i

---

## 2026-07-04 [Claude]: TeacherShell paneli to'liq ko'chirildi (grading bilan)

Proto'dagi qolgan 6 teacher sahifasi Django'ga ko'chirildi — endi o'qituvchi Django admin'siz ishlaydi: **Tekshirish** (navbat: kutayotgan imtihon urinishlari + uy vazifalari; imtihonni bo'limma-bo'lim baholash — writing/speaking javoblariga ball + per-esse `grader_feedback`, avto bo'limlar readonly xulosa, bo'lim ballari live-jamlanadi, "Tasdiqlash" `finalize_review` ni chaqiradi va sertifikat beradi; vazifani tasdiqlash keyingi darsni ochadi), **Boshqaruv** (KPI + navbat + guruhlar), **Guruhlar**, **O'quvchilar** (kohort filtri, qidiruv, progress), **Kontent** (backoffice muharrirlariga ko'prik), **Davomat olish** (kohort+dars bo'yicha present/partial/absent, upsert, "hammasini keldi" tugmasi). Routelar `teacher/*` (core/teacher_views.py), kirish `is_staff`; ko'lam: superuser→hamma, staff→o'z kurslari (kursi yo'q staff→hamma, kichik markaz rejimi). AppShell sidebar'ga "O'qituvchi paneli" havolasi qo'shildi.

Yo'lda tuzatildi: `ai/smart_form/*` (cb5a6ac) barcha fayllari `\"\"\"` escape-docstring SyntaxError bilan kelgan — test discovery yiqilardi; 5 fayl tuzatildi.

**Muhim ogohlantirish (multi-agent):** `cb5a6ac` (Antigravity "Smart Form Engine MVP") commiti mening o'sha paytdagi yarim-tayyor teacher fayllarimni (grading.html, grade_exam.html, teacher_views.py ilk holati, core/urls.py teacher routelari, base_teacher nav) tasodifan qamrab olgan — ehtimol `git add -A`. Fayllar yakuniy holatga shu branchdagi keyingi commitlarim bilan yetkazildi; antigravity branchiga tegilmadi, ish `claude/teacher-shell`da (antigravity/smart-form-engine ustiga qurilgan).

- Branch: `claude/teacher-shell` (bazasi: `antigravity/smart-form-engine` ← `playground`)
- Commitlar: `8eddee0` (fix ai syntax), `a7e1005` (feat teacher), `dd6d3bc` (test), + marinebook
- Test holati: `python manage.py test` — **175/175 OK** (6 ta yangi TeacherPanelTests bilan)
- Davom etilishi kerak: admin-payments/admin-settings sahifalari (ixtiyoriy, Django admin qoplaydi); exam JS jonli brauzer sinovi; AI model tanlovini DO stack'ka ko'chirish

---

## 2026-07-03 [Claude]: Yangi dizayn migratsiyasi + exam quyi-tizimi to'liq yakunlandi

azurelms-proto/ dagi yangi dizayn (Space Grotesk / azure #1257e6) Django'ga TO'LIQ ko'chirildi — eski frontend (61 fayl CSS/shablon) o'chirilib, o'rniga qatlamli shell tizimi qurildi: `base.html` → public / auth / AppShell (11 sahifa) / TeacherShell / AdminShell / ExamShell / errors; messenger 3-panel (messenger-chat.js DOM kontraktiga to'liq mos, WebSocket real-time). Floating AzureAI widget tiklandi (base_app include).

**Exam quyi-tizimi backend+frontend bilan tugallandi:** stub `exam:` app o'chirildi → yagona `courses` engine. `build_section_payload` dispatcheri (ReadingTask bo'lsa boy 8-turli avto-baholanadigan engine, aks holda Question/Choice); barcha 5 section turiga premium section-state (saqlab-borish, question_map, review-flag). Speaking — audio upload quvuri (default_storage). Listening — server-enforced replay limiti. Writing — min/max so'z chegaralari + per-esse `grader_feedback` + text-bomb himoyasi (migratsiyalar 0017–0019). Frontend: `exam-shell.js` runtime (deadline taymer avto-submit, renderer dispatch, MediaRecorder, autosave flush, blur proctoring) + `exam_detail` (start-overlay) + `exam_result` (3 holat) + sertifikat sahifalari qayta yaratildi (0abdce7 da o'chirilgan ekan).

Migratsiya paytida tushib qolgan funksiyalar testlar orqali topilib tiklandi: landing dinamik how-it-works (LandingPage/ProcessStep), footer site_settings kontaktlari, dashboard multi-kohort ro'yxati, leaderboard kohort selektori, my_courses "Tasdiq kutilmoqda" holati + kohort nomi, kurs kartasida yuklangan cover overlay, backoffice "E'tibor talab qiladi" + AI RAG index holati, messenger AI sozlamalar popover (uslub/model/skill backend choices'dan) va server-render feedback kontraktlari (copy/regenerate/skill chip).

- Branch: `playground`
- Commitlar: `a5acf01`…`0a3ed29` (13 ta: foundation → public → auth → app → lesson → messenger → blog+teacher → backoffice → errors → exam backend → sertifikat → exam UI → test moslash)
- Test holati: `python manage.py test` — **169/169 OK** (Ran 169 tests, OK); `manage.py check` toza
- Davom etilishi kerak: exam JS'ni brauzerda jonli sinash (recorder/audio limit/autosave); settings'dagi AI model tanlovini Gemini'dan DO stack'ka ko'chirish (task_9bf37dd1); home_view eski kontekst qoldiqlarini tozalash

---

## 2026-05-28 [Claude + Codex]: Nuclear-program fayllari Codex variantlari bilan birlashtirildi

Codex parallel sessiyada `alternative-project-context.md` (1239 satr) va `alternative-rules-for-agents.md` (635 satr) yozib qo'ygan ekan. Ikkalasi ham mendagi original variantlarning kengaytmasi sifatida ishlangan. Ikkalasini section-by-section taqqoslab, eng yaxshi qismlarni asosiy fayllarga birlashtirdim, alternative fayllarni o'chirdim.

**`project-context.md` (314 → 827 satr)** — qo'shildi: foydalanuvchi rollari jadvali, app-by-app responsibility breakdown (10 ta app), 10 ta user flow + WebSocket payload contractlari, data model relationship ASCII tree, security/access qoidalari bo'limi, task → fayl xaritasi, deployment subsection (Procfile + Dockerfile), to'liqroq env vars ro'yxati va management commands jadvali.

**`rules-for-agents.md` (281 → 573 satr)** — Codex versiyasi base sifatida olindi, mendagi ohang/spirit saqlandi. Qo'shildi: 5-rule executive summary (sec 0), dirty worktree triage jadvali, task scope size jadvali, "maxsus ehtiyot fayllar" ro'yxati (multi-agent collision zonalari), test matrix by change type, "marinebook'da yolg'on yo'q" qoidasi, long session signallari (50+ turn, user "nima qilayotgandik?" deb so'rasa), conflict protocol, frontend verify checklist, AI feature special rules, data migration danger signs, secrets/private data ro'yxati, emergency stop checklist.

Drift watchlist g'oyasi rad etildi (project-context.md doimiy ⚠️ note'lari va marinebook.md bir martalik kuzatuvlar bilan o'rnini bosadi).

- Branch: `main`
- Commitlar: shu yozuv bilan birga commit qilinadi
- Test holati: docs only — `python manage.py check` toza
- Davom etilishi kerak: root `AGENTS.md` yaratish (har IDE startup'da o'qiydigan giriş fayli), worktree'larni sozlash

---

## 2026-05-28 [Claude]: Nuclear-program kontekst tizimi yaratildi

`docs/` papkasidagi eskirgan migration plans + arxitektura fayllari o'chirildi va `nuclear-program/` papkasi yaratildi. Yangi kontekst tizimi 3 ta fayldan tashkil topgan:
- `project-context.md` — loyihaning to'liq wikipediyasi (stack, apps, AI agent qatlami, URL'lar, env, har major qism uchun batafsil)
- `rules-for-agents.md` — Claude/Codex/Antigravity uchun ish qoidalari (branch konvensiya, worktree sozlamasi, commit discipline, sessiya protokoli)
- `marinebook.md` — bu fayl, kundalik yozuv

Maqsad: 3 ta AI IDE bilan parallel ishlashda chalkashlik kamaytirish, har yangi sessiyaning bootstrap token narxini 5000-10000'dan 500-1000 ga tushirish.

- Branch: `main`
- Commitlar: keyin qo'shiladi (bu yozuv bilan birga commit qilinadi)
- Test holati: 91/91 messenger + users yashil (oxirgi run)
- Davom etilishi kerak: agentlar uchun worktree'larni sozlash (`git worktree add ../azurelms-claude claude/work` va h.k.)

---

## 2026-05-28 [Claude]: Branch tarixini soddalashtirish (main yagona branch)

3 ta lokal va 3 ta remote branch quyidagi tartibda toza qilindi:
1. `playground` (lokal + remote) o'chirildi — `codex/playground-next` tarixida to'liq mavjud edi
2. `codex/playground-next` (lokal + remote) fast-forward bilan `main` ga ko'tarildi (24 ta commit, 89 fayl, +9987/-1850 satr)
3. `codex/playground-next` (lokal + remote) o'chirildi — endi `main` bilan bir xil
4. `antigravity/dev` (avval o'chirilgan) — uncommitted telegram bot WIP yo'qotildi

Natija: faqat `main` qoldi. AI agent strategiyasi (har agent o'z branch'i + worktree'si) toza boshlanish uchun tayyor.

- Branch: `main` (oxirgi commit: `e693924`)
- Commitlar: fast-forward (yangi commit yo'q)
- Test holati: yashil
- Davom etilishi kerak: nuclear-program tuzilmasi (yuqoridagi yozuv)

---

## 2026-05-28 [Claude]: docs/ tozalash

`docs/` ichidagi 9 ta `.md` fayl o'chirildi (CLAUDE_CONTEXT, ARCHITECTURE, BLITZKRIEG_PLAN, FRONTEND_HTML_INVENTORY, FRONTEND_REBUILD_TARGETS, LOCAL_PROD_SETUP, MOBILE_FIRST_READINESS, PLAYGROUND_READINESS_GATE, PROTOTYPE_COVERAGE_MATRIX). Hammasi eskirgan migration plans yoki agent kontekst uchun yangi tizim (nuclear-program/) tomonidan almashtirildi. Foydali bo'lgan bitlar (env setup, runbot buyrug'i) `project-context.md` ga ko'chirildi.

- Branch: `main`
- Commitlar: `e693924 chore(docs): remove obsolete migration plans and architecture docs`
- Test holati: yashil
- Davom etilishi kerak: nuclear-program tizimi yaratish

---

## 2026-05-28 [Claude]: Web search testlari va xato qoldiqlari tozalandi

`messenger/tests.py` ga 10 ta test qaytarildi (avval `antigravity/dev` o'chirilganda yo'qolib ketgan edi):
- Web_search skill routing (Bugungi yangiliklar, Dollar kursi, Internet'dan qidir)
- Medium effort tier pair-detection (hozir + kim, kechagi + natija)
- Light effort tier pair-skip
- Heavy effort tier — har savolda grounding yoqilishi
- Inline `(Manba N)` strip
- Trailing `Manbalar:` ro'yxat strip
- Follow-up'da leading salom strip
- First-message'da salom saqlanish

`templates/users/base_app.html` da o'lik `{% include "includes/ai_assistant_widget.html" %}` qatori olib tashlandi (widget template o'chirib yuborilgan edi).

- Branch: `codex/playground-next` (keyinroq main'ga merge)
- Commitlar: `9db3398 test(messenger): restore web_search, sanitize, and effort-tier coverage`
- Test holati: 68/68 messenger yashil

---

## 2026-05-28 [Claude]: Antigravity/dev WIP butunlay olib tashlandi

`antigravity/dev` branchining ~3000 qatorlik uncommitted ishi — chuqur Telegram bot integratsiyasi (bot/handlers/ 8 modulga split, Notification→Telegram signal bridge, embedded AI assistant widget, `Message.reply_to` threading, `ChatRoomUserState.is_active_on_telegram`) butunlay o'chirildi. Foydalanuvchi qaroriga ko'ra — qaytadan, kichikroq commit'lar bilan yozish ma'qulroq deb topildi.

Saqlanmadi:
- `bot/handlers/` papkasi (ai_chat, attendance, base, courses, leaderboard, messenger, study)
- `bot/notifications.py`, `users/signals.py`, `messenger/ai_mentions.py`
- `messenger/migrations/0012_*`, `0013_*`
- `static/{css,js}/ai-widget.*`, `templates/includes/ai_assistant_widget.html`
- Lesson video URL helpers (`youtube_video_id`, `embed_video_url`, `video_watch_url`)

- Branch: `codex/playground-next` (working tree)
- Commitlar: o'chirish operatsiyasi commit emas
- Test holati: yashil (66/66 messenger)
- Davom etilishi kerak: kelajakda telegram bot deep integration kichik bosqichlar bilan qayta qurilishi kerak

---

## 2026-05-28 [Claude]: Web search skill, effort tiers va UX polish

Major feature qatlam: Gemini `google_search` grounding bilan web search skill qo'shildi. Foydalanuvchi `settings` sahifasida `light` / `medium` / `heavy` effort tier tanlaydi:
- **light** — faqat aniq keyword (qidir, bugungi, kursi qancha)
- **medium** — light + pair detection (vaqt + ma'lumot juftligi)
- **heavy** — har savolda `google_search` tool yoqilgan

Manbalar (URLs + titles) faqat `AIResponseRun.metadata.web_search_sources` ga saqlanadi, javob matnida ko'rsatilmaydi. Inline `(Manba N)` va trailing `Manbalar:` strip qilinadi (regex bilan defense-in-depth). Davomli suhbatda leading salom (`Salom, Aziz!`) ham strip qilinadi.

UX polish qo'shimchalari:
- Blog navigatsiyasi: "AzureBlog Beta" o'rniga AzureLMS logo (auth bo'lsa dashboard, bo'lmasa home'ga)
- Pricing sahifa: 3 ta karta 2+1 o'rniga bitta qatorda (grid 360→340)
- Dashboard: inline "Telegram ulanish" va notification blocklar olib tashlandi
- Profile: "Ijtimoiy tarmoqlar" kartasiga Telegram ulash tugmasi qo'shildi
- Sidebar: account dropdown outside-click + Esc yopadi; messenger sidebar new-chat tugmasi sticky, scrollbar ko'rinarli
- Messenger templatelar: reply preview None-safe sender (AI xabariga reply qilinganda)

- Branch: `codex/playground-next` (keyinroq main'ga)
- Commitlar: `b13c925 feat: add web search skill, effort tiers, and UX polish`
- Test holati: messenger + users 91/91 yashil

---

## 2026-05-28 [Claude]: docs/CLAUDE_CONTEXT.md to'liq qayta yozildi

Eski `CLAUDE_CONTEXT.md` (16-may holati) eskirgan ma'lumotlar bilan to'la edi: `young-mantis-version` mavjud bo'lmagan branch sifatida ko'rsatilgan, migration jadvali tugagan ishlarni "keyingi" deb e'lon qilingan, AI agent qatlami umuman tilga olinmagan. 319 satrlik yangi versiya yozildi — AI agent arxitekturasi, 9 ta skill, memory tizimi, RAG, chat oqimi, URL'lar, environment, foydalanuvchi sozlamalari va h.k.

Keyinroq bu fayl `nuclear-program/project-context.md` ga ko'chirildi va kontekst tizimi nuclear-program/ ga ko'chgani uchun docs/CLAUDE_CONTEXT.md o'chirildi.

- Branch: `codex/playground-next`
- Commitlar: `65cdd13 docs: refresh CLAUDE_CONTEXT with AI agent + migration state`
- Test holati: docs faqat, kod o'zgarmadi

---

## Avvalgi sessiyalar (yig'iq xulosa)

`9b8d9c4` (playground'ning oxirgi commiti) dan oldingi tarix `git log` orqali ko'rinadi. Asosiy bosqichlar:

- **Mayda Maydan (24-may) gacha:** AI agent qatlami qurish — `74f2d60` Refactor AI messenger into agent engine, `f4c1fc4` structured AIMemoryFact, `81bbeba` user toggle/archive, `8b43742` conversation summaries, `c8d4292` semantic scoring + traces, `fd48dd6` AI response reliability, `3b0e42c` feedback controls, `348b272` hover actions, `88d68e1` reject + decay maintenance, `82b29db` memory report UI, `54a81c6` staleness fix, `fe1b6c2` skill routing + tool context, `b48630f` AI skill picker, `6036b33` subtle metadata, `b511f3d` course-level RAG retrieval.

- **24-may:** `1a9ff5f Improve messenger product quality` — backoffice chats sahifasi, attachment, ChatRoomUserState, message edit/delete polish.

- **Avvalgi:** Fourth Trial playground prototype'lari Django shellariga ko'chirilishi (Auth, Public, Student App, Blog, Learning, Exam, Messenger, Legal, Error). `playground` branch bu bosqichning yakuniy checkpoint'i edi.

---

*Eng so'nggi yangilanish: 2026-05-28 (Claude)*
