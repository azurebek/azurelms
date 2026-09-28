# Q18 — Telegram Mini App, lokal prototip

2026-09-28, D31 continuation; base `9d5e53d`, branch
`codex/q18-miniapp-prototype`. **Packet75: U35–U39,5 UI manzili qurildi.**
Admission EXPERIMENT: canonical state yozmaydi. KPI: noto‘g‘ri synthetic
login va Mini→web→Backda yo‘qolgan kontekst0 (quyidagi sinov qamrovida).
Runtime, DB, AWS, provider va Telegram sozlamalari o‘zgarmadi.

## Tayyor qism

Preview: `http://127.0.0.1:8080/bot/miniapp/home/`.
Registry `0.75.0-miniapp`: **136 URL /74 page template /115 source nomi /
1212 route-state /201 action**. Kirish, bosh sahifa, kurslar, AI va profil.
Source: `bot/views.py`, `bot/miniapp.py`, `bot/urls.py`,
`templates/bot/miniapp_*.html`, `static/js/miniapp.js`.

- STRATEGYdagi Mini shell: existing token/component/iconlar, source4tab
  tartibi. Natural document scroll, sticky bottom nav, viewport-fit va
  safe-area CSS;44px nazoratlar. Yangi palette/font/breakpoint yo‘q.
- Entry linked/unlinked/invalid/expired/no-SDK holatlari explicit sinov
  panelida. Haqiqiy initData/token qabul qilinmaydi, SDK yuklanmaydi.
  Native CSRF POST→303→exact result GET; safe next, run/version/UUID,
  stale/replay/unknown-result himoyasi. Xato holatida auth o‘zgarmaydi.
  Local receipt cap64 — disposable fixture bound, runtime sozlamasi emas.
- Home/kurs/profil/AI existing records, progress, communication va privacy
  projectionlarini o‘qiydi. Yangi access/XP/grade/quota hisoblash yo‘q.
  AI yangi chat existing `state.act('ai.room.new')`ga delegatsiya qiladi;
  bo‘sh xona qayta ishlatiladi, prompt/provider so‘rovi yuborilmaydi.
- Mini→web havolasi same-tab from/to marker saqlaydi; faqat exact targetda
  “Mini App’ga qaytish” ko‘rinadi. Identity/token yo‘q, DOM node API,
  innerHTML yo‘q. Native Back saqlanadi; optional storage ishlamasa Back
  bor. Yangi tabni ochish marker yozmaydi; original Mini tabga qaytiladi.
- Tema uchun bitta existing `theme.js`: user tanlovi >sintetik host >OS.
  Mini bo‘lmagan sahifalarga host tema ta’sir qilmaydi. Mini shell personal
  platform bootstrap/pollingni yuklamaydi; blocked holat private UI bermaydi.

## Tekshirilgan dalil

Trial cwd: `playground/Eleventh Trial`. Python root `venv/Scripts/python.exe`.
`AZURELMS_SKIP_ENV_FILE=1`, bo‘sh `GEMINI_API_KEY`/`TELEGRAM_BOT_TOKEN`,
`LOCAL_USE_REMOTE_SERVICES=0`; real `.env`, DB yoki provider ishlatilmagan.

| Buyruq / tekshiruv | Natija |
|---|---|
| `python manage.py check` |0 issue |
| `python manage.py test tests --verbosity 0` |**788 PASS**,338.319s |
| `python manage.py test tests.test_miniapp tests.test_preview.PreviewTests.test_preview_routes_match_observed_django_url_definitions tests.test_preview.PreviewTests.test_teacher_primary_navigation_never_switches_to_learner --verbosity 0` |Final focused20 PASS,3.112s |
| `node --test tests/*.test.mjs` |**195 PASS**,0 skipped |
| IAB5 sahifa ×6width ×2theme ×2state |**120 checks**,overflow0,4tab targets≥44px |

Mini18 tests:5×9 states, safe next, signed-out redirect, CSRF, invalid/
duplicate/secret fields, stale/reset/collision, session-scoped immutable
receipt, uncertain GET reconcile, blocked no-write, existing AI delegation/
empty reuse, shared profile/memory/progress, empty/long va receipt cap.
Source URL nom/path hamda no-workspace Mini navigation regressiyasi bor.

Browser widths320/360/390/768/1024/1440; light/dark, normal/long. Qo‘shimcha
320×568 va740×320. Entry→unlinked error→linked recovery→courses next;
home→lesson→explicit return; new AI→receipt→room72→Back; offline no-data;
unknown result→read-only reconcile (roomni takror yaratmaydi). Lab Tab
wrap va Escape/focus return tekshirildi. Matrix paytida console warn/error0;
unlinked404 va uncertain503 keyingi expected synthetic javoblar.

Lokal dalil: `evidence/PACKET-75-RESULTS.md`, `packet-75-responsive.json`,
`packet-75-django.log`, `packet-75-node.log`, `packet-75-mobile.png`,
`packet-75-desktop.png`. Computer-use tekshiruvi viewport/fokus/handoff
qarorlarini tasdiqladi; vaqtinchalik viewport override reset qilindi.

## Chegaralar va keyingi port

**Bu haqiqiy Telegram qabuli emas.** Source auto-auth o‘rnida prototipda
explicit synthetic POST bor. Real SDK/HMAC, BackButton/themeChanged,
Telegram safe-area, native iOS/Android keyboard va assistive-tech G3 OPEN.
Source authning csrf_exempt xususiyati prototipga ko‘chirilmagan.

Lokal handoff existing A1/03 lesson3/course overviewga boradi. Arbitrary
`course_study?cohort=` redirect yoki canonical access tekshiruvi bu paketda
yozilmadi: portda existing source adapterga ulanadi, fixture ID ko‘chirilmaydi.
Umumiy XP/onboarding level uchun alohida yangi raqam/formula ixtiro qilinmadi;
bor shared course/progress/profile qiymatlari ishlatiladi. Screenshot yoki
120 browser case real Telegram native muhitining o‘rnini bosa olmaydi.

Q03 advanced, U17/A2-D01, broad Q14, owner G2/G3 va real port qarzlari
ochiq. Q18 **lokal implementation** bajarildi; endi **6 yangi band
(3 UI+3 handler),3 qadam**: Q19 → Q08 legacy/paritet → final qabul.
AWS oxirgi qayd `8bb6b95`/19flags; bu turn qayta deploy qilinmadi.

## Xavfsiz nusxa / rollback

Ignored prototype Gitga qo‘shilmadi va upload qilinmadi. Lokal checkpoint:
`playground/Eleventh Trial/checkpoints/packet-75-20260928-032108.zip`,
**591 fayl**, har ZIP entry SHA256 asl nusxa bilan tekshirildi.

SHA256: `011ABDCEF0BA19C9E511C1F02F11150C963C274DB372FA4B6B778D5C4B9F615F`.

Rollback: mavjud Packet74 checkpointi saqlangan. Hech qaysi eski nusxa
o‘chirilmadi. Restore canonical source checkout/existing venv talab qiladi;
ZIP venv/DB/secretlarni olmaydi. Tracked PR faqat shu dalil va reja/jurnal.
