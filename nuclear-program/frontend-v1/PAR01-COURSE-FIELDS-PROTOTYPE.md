# PAR-01 — kurs formasining maydon pariteti

2026-10-03, Packet80. Source base `263debb`. Ignored Eleventh Trial ichida
lokal qurildi; real runtime/AWS o‘zgarmadi. Bu **14-field gap** yopilishi,
G2/G3/G4, native qabul yoki to‘liq real adapter tugallanishi emas.

## Manba va o‘zgarish

`core/backoffice_forms.py:CourseBackofficeForm`,
`core/views.py:backoffice_course_editor`, `courses/models.py:Course`,
`courses/cover_art.py` o‘qildi. AST testi domain app importisiz real formning
14 maydonini va15 gradient variantini prototip bilan solishtiradi.

| Maydonlar | Lokal xulq |
|---|---|
| title, description, level, duration | Oldingi4 maydon saqlandi; tavsif plain-text,2000 belgi technical cap |
| instructor | Joriy synthetic staff ustoz; forged/foreign ID rad, owner reassignment ochilmaydi |
| price | 0–99999999.99; decimal string,2 kasr, float/quote hisoblash yo‘q |
| cover_mode, gradient_preset, gradient_cover_title, gradient_cover_label | Source enumlari;15 preset;80/48 belgi; rasm upload bu14 maydon tarkibida emas |
| is_active | Explicit diff/consent; list/overview/editor bir saved qiymat; create default inactive |
| certificate_requires_all_assignments_approved, certificate_min_lesson_completion_percent, certificate_min_attendance_percent | Boolean va0..100 butun foiz; sertifikat berish/access hisoblash yo‘q |

Create/edit bir komponentdan foydalanadi. Barcha14 qiymat draft, diff,
revision/no-op, replay va exact receiptga kiradi. Missing/duplicate/unknown
field yoki foreign instructor yozmaydi. Noaniq javobda input va submit
qulflanadi; natija GET bilan aniqlanadi, avtomatik qayta yuborish yo‘q.

Eski draft saqlashdagi reload bo‘shlig‘i ham tuzatildi: baseline revision
va14 original qiymat saqlanadi. Ikkinchi oynadagi saqlovdan keyin reload
yangi revisionni jimgina qabul qilmaydi; refresh mahalliy tahrirni ushlab,
tegmagan maydonlarni yangi saved qiymatga olib keladi. Tasdiq qayta talab
qilinadi. Create natijasiga fokus qaytadi, yashirilgan forma triggeriga emas.

Registry o‘zgarmadi: **139 named URL /77 page template /118 source name /
1223 route-state /208 action +3 diagnostic handler**. Yangi shell, rang,
font, breakpoint, global CSS override, dependency yoki business formula yo‘q.

## Tekshiruv

Isolated trial cwd, `AZURELMS_SKIP_ENV_FILE=1`, `GEMINI_API_KEY=` va
`TELEGRAM_BOT_TOKEN=`. Haqiqiy env/DB/AI/Telegram yuklanmadi.

- `../../venv/Scripts/python.exe manage.py test tests --verbosity 0`:
  **841 PASS**, yakuniy toza process333.051s (birinchi run323.768s).
- Focused6 module:55 PASS; yangi source/payload/configuration7test.
- Barcha `tests/*.test.mjs` PowerShell orqali kengaytirilib `node --test`:
  **219 PASS**; yakuniy uch JS faylga `node --check`:PASS.
- `../../venv/Scripts/python.exe manage.py check`:0 issues.
- IAB8085: edit/diff/cancel/save/reload/list, create→exacteditor,
  peer-refresh va peer-save→reload→stale→refresh, unknown→reload→GET receipt.
  844×390 dialog va Tab/escape/result focus tekshirildi.
- **56 responsive**:2 forma×2 tema×14 kenglik(320..1920, breakpointlar
  ikki tomoni bilan). Overflow0/duplicateID0/14 visiblefield/controls≥44px.
- **36 state**:2 forma×9 state×320/1280. Normal/long/slow/uncertain forma
  bor; empty/locked/error/offline/expired forma yo‘q, overflow0.
- Browser console error/warn0. Lokal screenshots va JSON:
  `evidence/PACKET-80-desktop-light.jpg`, `PACKET-80-mobile-dark.jpg`,
  `PACKET-80-responsive.json`. Native phone/AT/Firefox/WebKit NOT TESTED.

Oraliq takroriy suite eski metadata-only izoh matnini kutgan1 assertionda
to‘xtadi. Matn yangi admissionga moslandi, scope/link/no-write himoyalari
saqlandi; yakuniy focused55 PASS. Yakuniy full repeat841 PASS,333.051s.

## Chegaralar va saqlash

Bu local config form; learner/public publication, pricing quote, enrollment,
certificate award, media upload, default module va durable real RBAC emas.
Plain-text tavsif/cap, current-teacher scope va bitta create slot preview
chegaralari sifatida ochiq. Source/UI bounded input formati barcha real
backend validatorlarining to‘liq ekvivalenti deb ko‘rsatilmaydi.

Source/assets/testlar Gitga kirmaydi. `playground/` force-add/upload yo‘q;
Gitga faqat ushbu dalil, trackerlar va marinebook kiradi. Old Packet79
backup saqlandi va SHA256 qayta tekshirildi. Yangi checkpoint:
`playground/Eleventh Trial/checkpoints/packet-80-20261003-012905.zip`,
**642 fayl**; har ZIP entry SHA256 asl nusxa bilan tekshirildi.
ZIP SHA256 `613F8CE53E9DF7E2740E66F9240592E7D2076124726E14AFEB2F61F6CD07544F`.
Bu bir diskdagi lokal checkpoint, mustaqil disaster-recovery backup emas.

Qolgan local-parity: **PAR-03** public blog/SIT handoff va **PAR-05**
receipt/alias/picker journey. Keyin UX/DATA/RULE/native/owner final qabul,
undan keyin DESIGN-01. Real port/deploy alohida ish.
