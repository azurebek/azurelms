# I1 — kirish, bosh sahifa va kurslarim

2026-09-25. Branch: `codex/frontend-v1-learning-shell`.
Status: **LOCAL IMPLEMENTED / SECURITY FIX VERIFIED LOCALLY / CI RECHECK / NOT DEPLOYED**.
Owner “yangi branch ochib ishni boshla” bilan I1 ijrosini boshladi.

## Admission va chegarasi

`ADMIT — launch-critical`. Natija/KPI: haqiqiy hisob bilan login → dashboard
→ o‘z kurslari, safe next va ruxsat regressiyasi. Yangi enrollment/progress/
grade/payment qoidasi yo‘q. Owner uchun yangi kundalik operatsiya yo‘q;
faqat existing audited flag boshqaruvi. DB migration va tashqi API chaqiruv
talab qilinmaydi. Qolgan UI va Eleventh Trial runtime’i o‘zgartirilmadi.

## Source → yangi renderer

| URL nomi | Canonical view / real ma’lumot | Yangi template |
|---|---|---|
| `login` | Django `LoginView`, existing auth backends, CSRF, safe-next, native form errors | `frontend_v1/login.html` |
| `dashboard` | `users.views.DashboardView`, `build_student_enrollments`, `streak_snapshot`, existing metrics | `frontend_v1/dashboard.html` |
| `my_courses` | `users.views.MyCoursesView`, faqat request.user enrollmentlari | `frontend_v1/courses.html` |

`core/frontend_v1.py` faqat renderer/nav/presentation tanlaydi. Read context
va auth/access query/servislar o‘zgarmadi. Course CTA mavjud `course_study`
URLiga **course_id + cohort** bilan boradi; lesson hali legacy (I2).

- POST login/logout mavjud endpoint/form bilan; parol storage’ga yozilmaydi.
- Telegram tugmasi existing init/statusni ishlatadi. Init faqat explicit click;
  deep-link alohida link, no forced popup. Cancel/pagehide pollingni to‘xtatadi;
  aloqa noaniq bo‘lsa o‘sha tokenni tekshirish mumkin, initni auto-resend yo‘q.
  Server authenticated/used javobidan so‘ng `LoginView` orqali safe-next
  qayta tekshiriladi; yangi backend token contracti yo‘q.
- Nav/accountda role linklari va POST logout saqlangan; native details va
  mobil dialog, Escape/focus return. Ko‘chmagan yo‘llar ochiq legacy deb belgilangan.
- Tokens/base/components/shell/theme approved trialdan ajratildi; yangi
  `static/frontend_v1/` va `templates/frontend_v1/`. Legacy global assetlar
  bilan aralash yuklash yo‘q. Preview app.js, fixture, lab/state ko‘chmadi.
- Dynamic nomlar escape qilinadi, no-store/private response. Saqlangan yagona
  frontend preference — existing `az-v2-theme`; hisob yoki progress storage yo‘q.

## Real ma’lumotga moslashtirish (redesign emas)

Prototipdagi bitta fixture kurs real enrollmentlar ro‘yxatiga moslandi.
Bir kursda bir vaqtning o‘zida ikki active enrollment canonical modelda
taqiqlangan: test ham bu qoidani chetlab o‘tmaydi, ikkita real kursni ishlatadi.
Pending/frozen/expired yoki grace’dan tashqari active yozuvga resume yo‘q.
100% progressning o‘zi access bermaydi.

Fixture “bugungi jonli dars/19:00” va oldindan yozilgan hafta kataklari
haqiqiy jadval deb chiqarilmadi: shu card patternida mavjud canonical
XP/streak ko‘rsatildi. Resume kursi mavjud view tanlovidan; aniq keyingi
darsni existing `course_study` hal qiladi. Kurs outline/matn/media I2da.
Dashboard sana joriy, login errorlar o‘zbekcha; yangi biznes hisob-kitob yo‘q.

## Flag va rollback

Slug: `frontend_v1_learning`, **default=False**. Existing owner control:
`/backoffice/control/flags/`. Boshqaruvning sabab/tasdiq/audit qoidasi saqlanadi.
Flag uchala view uchun template + assetsni almashtiradi, accessni emas.
DB flag o‘qilmasa default OFF; o‘chirilganda eski login/dashboard/my-courses
qaytadi. Existing baza va AWS flagi bu ishda yoqilmadi.

## Fresh tekshiruv

PowerShell’da testlardan oldin `.env.local` o‘qishni o‘chirish:

```powershell
$env:AZURELMS_SKIP_ENV_FILE='1'
$env:GEMINI_API_KEY=''
$env:TELEGRAM_BOT_TOKEN=''
.\venv\Scripts\python.exe manage.py check
.\venv\Scripts\python.exe manage.py test users core.test_app_shell core.test_feature_flags core.test_feature_flag_effects core.test_flag_surface core.test_golden_flow_e2e courses.test_locked_lesson_write_gate courses.test_lesson_release courses.test_lesson_completion library.test_student_access --noinput --verbosity 1
node --test tests/frontend_v1/login.test.mjs
git diff --check
```

- Django check: 0 issue; Python: **294 PASS**, jumladan 24 yangi V1 test.
- Node: **8 PASS** — native password toggle, no unsolicited init,
  Telegram pending/authenticated/expired/unknown/network/cancel/unsafe-link.
- V1 static assets: isolated `collectstatic` + CompressedManifest storage,
  DEBUG=False hashed CSS/JS/SVG existence PASS. To‘liq repo collectstatic CI’da.
- Full root suite lokal qayta yugurilmadi; required CI alohida tekshiradi.
  Oldingi Windows fontTools muammosi sabab testlar skip/susaytirilmagan.
- CI SQLite jobiga Node controller test qo‘shildi; required job nomlari
  o‘zgarmadi. Provider kvota sarfi yo‘q.

## Browser dalili

Mahalliy real Django server `127.0.0.1:8048`, yangi vaqtinchalik SQLite baza,
alohida session/CSRF cookie nomlari va test hisoblar. Existing `db.sqlite3`
seed/migrate qilinmadi. Provider/bot tokenlari bo‘sh. Harness ignored
`playground/frontend-v1-smoke/serve.py`; productionga qo‘shilmaydi.

- 1440×900: desktop login/dashboard, light/dark; uzun course/cohort nomlari.
- 320×740: login/dashboard/course list; horizontal overflow yo‘q (document width 305).
- 390×844: kursi yo‘q hisob, dark; document width 375, layout sig‘adi.
- Noto‘g‘ri parol → o‘zbekcha xato + username/next qoladi; to‘g‘ri kirish
  → so‘ralgan kurslarim; boshqa hisobga o‘tganda oldingi kurslar ko‘rinmaydi.
- Mobil drawer → Escape → opener focus; hisob menyusi → POST logout →
  yopiq URL qayta login talab qiladi.
- Kurs CTA → real `/courses/1/lesson/2/?cohort=1` → Back → V1 kurslarim.
- Telegram init local serverdan havola oldi; cancel ishladi. Bot havolasi
  ochilmadi, jonli Telegram tasdig‘i tekshirilmagan.
- Kuzatilgan browser console error/warn: 0. Bu barcha device/transport
  kombinatsiyasi yoki real telefon testi emas.

## PR va xavfsizlik tuzatishi

Implementation: `1dcaf49`; birinchi CI head: `08ee934`.
[PR #120](https://github.com/azurebek/azurelms/pull/120),
[CI run 36082028361](https://github.com/azurebek/azurelms/actions/runs/36082028361).

Required xavfsizlik jobidagi `audit_dependencies` FAIL: mavjud
`anyio==4.12.1` uchun `CVE-2026-63374`, `CVE-2026-64847`; mavjud
`autobahn==25.12.2` uchun `CVE-2026-77528` reyestrda yo‘q.
Bu PR `requirements.txt`ni o‘zgartirmagan. Secret scan PASS, lekin
paket xavfsizlik gate’i yiqilgani sabab production image qadamlari SKIPPED.
Bu logdagi advisory identifikatorlari; ta’sir/fix-versiya auditi hali qilinmadi.

Owner tasdig‘idan so‘ng `18b5a0b`da faqat ikki pin yangilandi:
`anyio==4.14.2`, `autobahn==26.7.1`. Maintainer manbalari:
[AnyIO TLS tuzatishi](https://github.com/agronholm/anyio/security/advisories/GHSA-82r6-8w77-94w6),
[AnyIO process-pool tuzatishi](https://github.com/agronholm/anyio/security/advisories/GHSA-5p39-cfhj-2xmp),
[Autobahn message-limit tuzatishi](https://github.com/crossbario/autobahn-python/security/advisories/GHSA-hxp9-w8x3-p566).
Tegishli zaifliklar TLS hostname tekshiruvi, worker stderr bloklanishi va
siqilgan WebSocket xabari hajm chekloviga taalluqli; backend/UI qoidasi
o‘zgartirilmadi. Audit reyestri bo‘sh qoladi; gate bypass yo‘q.

Yangilangan local venv uchun yangi dalil:

```powershell
.\venv\Scripts\python.exe -m pip check
.\.tools\dependency-audit-20260925\Scripts\python.exe -m pip_audit -r requirements.txt --no-deps -f json --progress-spinner off -o .tools/dependency-audit-20260925/report.json
$env:AZURELMS_SKIP_ENV_FILE='1'
$env:GEMINI_API_KEY=''
$env:TELEGRAM_BOT_TOKEN=''
.\venv\Scripts\python.exe manage.py audit_dependencies --report .tools/dependency-audit-20260925/report.json
.\venv\Scripts\python.exe manage.py check
.\venv\Scripts\python.exe manage.py test core.test_supply_chain_gate users messenger classbook --noinput --verbosity 1
```

`pip check`: moslik xatosi yo‘q. `pip-audit` + existing gate:
**107 pinned dependency, 0 skipped, 0 advisory**. Django check: 0 issue.
Focused suite: **433 test, OK (skipped=1)**. Audit tool alohida ignored
`.tools/` venvda; project venvda faqat ikki paket yangilandi. Ishlab turgan
oldingi lokal preview processlari restartgacha eski importni tutishi mumkin.

Eski `13e24e6` CI’da SQLite va PostgreSQL full-suite joblari PASS;
security job FAIL edi. Yangi pinlar bilan uch required job qayta o‘tishi
shart; oldingi yashil natija yangi pinlar uchun dalil emas. Latest CI/merge
holati PR #120da. AWS deploy/flag enable bu tuzatish doirasiga kirmaydi.

## Release oldidan qolganlar

PR uch required check/review; I2 real dars/material va teacher release;
staging dataset, real device, deploy SHA/smoke/rollback va owner go/no-go.
I1ning lokal ishlashi butun V1 yoki production release PASS emas.
