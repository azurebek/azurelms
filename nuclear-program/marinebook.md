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

## 2026-08-15 [Claude Code]: A0b/2 — upload gate baytlar bo'yicha (MIME/magic-byte/size)

A0b ning ikkinchi slice'i. Oldingi holat: `core/utils.py` da faqat ikkita tekshiruv bor edi — hajm va **kengaytma**. Ikkalasi ham faqat `CustomUser.avatar` va `PaymentReceipt.receipt_image` maydonlariga biriktirilgan, ustiga model field validatorlari `Model.objects.create()` va `instance.save()` yo'llarida umuman ishga tushmaydi — bizning upload endpointlarimiz aynan shu yo'llarni ishlatadi. Ya'ni amalda hech qanday tur tekshiruvi yo'q edi.

Yangi `core/upload_validation.py` faylning **birinchi 512 baytini** o'qib turini aniqlaydi. Fayl nomi va klient yuboradigan `content_type` ga ishonilmaydi — ular brauzerdan keladi va soxtalashtirilishi mumkin. Kengaytma faqat ikkilamchi izchillik tekshiruvi: haqiqiy PDF `.png` nomi bilan kelsa rad etiladi. Uchta profil: `image` (5MB), `document` (12MB), `audio` (25MB).

Beshta learner upload yo'li ulandi va har birida aniq nuqson yopildi:

| Yo'l | Oldingi holat |
|---|---|
| `messenger.upload_message_attachment` | faqat 12MB; tur tekshiruvi **umuman yo'q** — `.html`, `.svg`, exe bemalol o'tardi |
| `cohorts.checkout_view` chek rasmi | model validatori bor, lekin servis `.create()` qilgani uchun **ishlamasdi** |
| `courses.submission_service.submit_assignment` | hech qanday tekshiruv yo'q |
| `courses.UploadExamAudioView` | faqat `upload.content_type` — klient yuboradigan qiymat, bo'sh bo'lsa tekshiruv butunlay o'tkazib yuborilardi |
| `users.AvatarUpdateView` | model validatori `save()` yo'lida **ishlamasdi** |

Gate canonical joyda turadi: vazifa fayli uchun u `submission_service` da, shuning uchun web view ham, Telegram bot ham bir xil qoidani oladi.

Ikkita nozik qaror. (1) `.txt` yuklashni buzib qo'ymaslik uchun matn turi qo'shildi, ammo xavfsiz shartlar bilan: matnli kengaytma + UTF-8 + `<` bilan boshlanmaslik — shunda `.txt` niqobidagi HTML/SVG o'tmaydi. (2) Audio profili brauzer MediaRecorder chiqaradigan konteynerlar (webm/ogg/wav/mp3/mp4-m4a) bilan cheklandi; ro'yxatdan biror format chiqib qolsa u bitta konfiguratsiya qatori bilan qo'shiladi.

- Branch: `claude/a0b-upload-validation` (`origin/main` dan; A8 va A0b/1 branchlaridan mustaqil)
- Yangi: `core/upload_validation.py`, `core/test_upload_validation.py` (19 test). Tegilgan: `messenger/views.py`, `cohorts/views.py`, `courses/views.py`, `courses/submission_service.py`, `users/views.py`, `cohorts/tests.py`, `ai/documents/tests.py`. **Migration yo'q**
- Testlar: magic-byte tanish, `content_type` bilan aldash urinishi, kengaytma nomuvofiqligi, SVG/HTML rad etilishi, `.txt` niqobidagi HTML, bo'sh va katta fayl, sniff'dan keyin fayl saqlanadigan holatda qolishi, beshta audio konteyneri, hamda endpoint darajasidagi gate testlari (avatar, messenger, vazifa)
- Test holati: `manage.py test` — **546/546 OK** (baseline 527 + 19); `manage.py check` — 0 issue
- **Yo'lda topilgan ikkinchi nuqson:** `ai/documents/tests.py` dagi `test_captionless_generic_file_does_not_dispatch_ai` soxta `b"PK fake docx"` baytlari bilan ishlardi va **noto'g'ri sababdan o'tardi** — u "AI chaqirilmadi" deb tasdiqlardi, aslida fayl umuman qabul qilinmasdi. Endi haqiqiy `PK\x03\x04` baytlari va `assertEqual(status_code, 200)` bor
- **Test gigienasi:** yangi endpoint testlari `TempMediaMixin` orqali vaqtinchalik `MEDIA_ROOT` ishlatadi. Mavjud testlarning bir qismi hali ham repo ichidagi `media/` ga yozadi (bugungi runlardan keyin u yerda 148 fayl) — bu alohida tozalash ishi sifatida ajratildi
- Inventarizatsiya qo'shimchasi: CKEditor upload'i (`/ckeditor5/`) `CKEDITOR_5_FILE_UPLOAD_PERMISSION` defaulti bo'yicha **staff-gated**, ya'ni learner teshigi emas. SIT/blog/landing rasm maydonlari owner-only backoffice formalarida qoladi — bu slice ularga tegmadi
- Line-ending intizomi: `users/views.py`, `cohorts/views.py`, `cohorts/tests.py` va `ai/documents/tests.py` repoda aralash CRLF/LF saqlanadi; tahrir ularni normallashtirib yubormasligi uchun to'rttasi ham HEAD baytlaridan qayta qurildi. Xom diff mantiqiy diffga teng (82/15), churn yo'q
- Davom etilishi kerak: A0b/3 — private media permission-checked stream view (**owner qarori 2026-08-15**: signed URL emas, `FileResponse` bilan stream; S3 ochilsa shu view redirectga kengaytiriladi). Keyin A0b/4 WebSocket access recheck, A0b/5 django-csp v4
## 2026-08-15 [Claude Code]: A0b/1 — teacher scope default-deny va canonical scope

A0b ning birinchi slice'i. Rejada bitta band ("teacher course/cohort default-deny") edi, amalda **bir qoidaning uchta nusxasi** topildi va ikkitasi default-allow tomonga og'gan edi:

1. **Web teacher paneli** (`core/teacher_views.py`): `_teacher_courses()` biriktirilgan kursi yo'q staff uchun `Course.objects.all()` qaytarardi. Ya'ni yangi qo'shilgan har qanday staff butun platformaning kurslari, guruhlari, o'quvchilari, baholash navbati va davomatini ko'rardi. Fayl docstring'i buni ataylab "kichik markaz rejimi" deb izohlagan edi, ammo `05-launch-ops.md` permission matritsasi (*"biriktirilmagan bo'lsa default natija bo'sh"*) va backlog `A0b` uni supersede qiladi.
2. **Telegram bot** (`bot/services.teacher_cohorts_overview`): qoida **teskari** yozilgan edi — `if not is_active_staff(user): filter(course__instructor=user)`. Ya'ni har qanday active staff barcha guruhlarni ko'rardi, faqat staff bo'lmagan instructor cheklanardi. Mavjud test faqat staff-bo'lmagan tarmoqni qoplagani uchun bu ushlanmagan.
3. **Davomat sahifasi** (`users.AttendanceManageView.get_allowed_cohorts`): xulqi to'g'ri edi, lekin uchinchi mustaqil nusxa.

Yechim rules §"Adapter biznes qoidasini egallamaydi" bo'yicha: qoida `core/access.py`ga `teacher_course_queryset()` / `teacher_cohort_queryset()` sifatida chiqarildi (superuser → hammasi; qolgan har kim → faqat `instructor=user`; anonim yoki `is_active=False` → bo'sh), uchala yuza ham faqat shuni iste'mol qiladi. Bot `teacher_grading_queue` ham view modulining private helperini import qilishdan to'xtadi. Teacher panelining 8 view'i, jumladan ID bo'yicha ochiladigan baholash sahifalari ham, shu yagona scope'dan oziqlanadi — shuning uchun bitta funksiya butun panelni yopdi.

- Branch: `claude/a0b-teacher-scope` (`origin/main` dan; `claude/a8-supply-concurrency-proof` dan mustaqil, alohida merge qilinadi)
- Yangi/tegilgan: `core/access.py` (+30, canonical scope), `core/teacher_views.py`, `bot/services.py`, `users/views.py` (har biri adapterga aylandi), `core/tests.py` (+160, `TeacherScopeDefaultDenyTests`). **Migration yo'q**
- Testlar (10 yangi): default-deny, faqat o'z kursi, superuser hammasini ko'radi, nofaol staff bo'sh oladi, 6 ta ro'yxat sahifasi bo'sh render bo'ladi, baholash detail sahifalari `404`, begona o'qituvchi POST bilan ham baholay olmaydi, davomatda cohort yo'q, va **adapter parity** — bot bilan web bir xil scope beradi
- Nazorat yugurishi: eski default-allow xulqi qaytarilganda 7 ta yangi testning hammasi (12 subtest) yiqiladi
- Test holati: `manage.py test` — **537/537 OK** (baseline 527 + 10 yangi); `test core bot` — 140/140; `test users core` — 148/148; `manage.py check` — 0 issue
- Churn: `users/views.py` HEAD'da aralash line-ending bilan saqlanadi (1226 CRLF + 29 LF); tahrir avval 29 qatorni normallashtirib yubordi, fayl HEAD baytlaridan qayta qurildi — yakuniy diff aynan 10/6 qator. `git diff --check` dagi ogohlantirishlar shu aralash fayl uchun pre-existing artefakt
- **Owner e'tiboriga:** endi superuser bo'lmagan staff faqat `Course.instructor` sifatida biriktirilgan kurslarini ko'radi. Merge qilishdan oldin real bazada har kursga instructor biriktirilganini tekshiring, aks holda o'sha teacher uchun panel bo'sh chiqadi. Bot tomonida bo'sh holat matni allaqachon bor ("Sizga biriktirilgan faol guruhlar yo'q")
- Qamrab olinmagan: `bot/middleware.py:30` dagi `Course.objects.filter(instructor=user)` — u rol *aniqlash*, data scoping emas, shuning uchun tegilmadi
- Davom etilishi kerak: A0b ning qolgan 4 slice'i — upload validatsiya (MIME/magic-byte/size), private media permission endpoint, WebSocket access recheck, django-csp v4 migratsiya
## 2026-08-15 [Claude Code]: A8 closeout — SQLite'da supply reservation contention tuzatildi

R0 ning yagona ochiq bandi — "haqiqiy parallel contention proof" — yozildi va u darhol real kamchilikni ochdi. `reserve_supply()` va `reconcile_supply()` singleton qatorlarni `select_for_update()` bilan qulflaydi, ammo SQLite'da `BaseDatabaseFeatures.has_select_for_update = False` va sqlite3 backend uni override qilmaydi — Django `FOR UPDATE` bandini jimgina tushirib qoldiradi (`django/db/models/sql/compiler.py:840`). Ustiga Django SQLite'da `BEGIN DEFERRED` ishlatadi: o'qigan tranzaksiya yozishga ko'tarilganda SQLite deadlock xavfi sabab `busy_timeout`ni **kutmaydi** va darhol `database is locked` qaytaradi. Natija: 8 parallel rezervatsiyadan 7 tasi `SupplyUnavailable` bilan yiqilardi. Bu budjet overshooti emas (fail-closed to'g'ri ishlagan), lekin ikki foydalanuvchi bir vaqtda AI'ga yozsa ikkalasi ham xato olardi.

Yechim `core/settings.py`ning local SQLite blokida: `transaction_mode='IMMEDIATE'` (write lock tranzaksiya boshida olinadi, raqiblar xato o'rniga navbatda kutadi), `timeout=15` va WAL. Bu sozlama faqat A8 ga tegishli emas — `aicontrol/supply.py`dan tashqarida `select_for_update()` ga tayanadigan yana **13 ta chaqiruv joyi** bor (8 faylda: enrollment transition, promo redemption, exam attempt/answer/reading response, davomat, streak, XP va `users/views.py:1222` dagi Telegram auth tokenini bir martalik consume qilish). Oxirgisi A0a da yopilgan replay teshigi bo'lib, uning "parallel so'rov ikkinchi marta ololmaydi" kafolati SQLite'da qulfsiz ishlab kelgan; endi u ham ketma-ketlashtirildi.

Test strategiyasi ataylab ikki qatlamli. Django'ning default SQLite test bazasi — shared-cache in-memory (`file:memorydb_default?mode=memory&cache=shared`), uning qulflash semantikasi real `db.sqlite3` dan farq qiladi va contention regressiyasini yashiradi. Fayl bazasini default qilish esa to'liq suite'ni yana ~50% sekinlashtiradi. Shuning uchun: og'ir contention testlari `AZURELMS_TEST_FILE_DB=1` bilan fayl bazasida ishlaydi (default runda skip), arzon `SQLiteConcurrencyConfigTests` esa har yugurishda konfiguratsiya regressiyasini aniq xabar bilan ushlaydi.

- Branch: `claude/a8-supply-concurrency-proof` (`origin/main` dan)
- Yangi: `aicontrol/test_supply_concurrency.py` (5 contention + 4 config test). Tegilgan: `core/settings.py` (+20), `.gitignore` (+4, WAL yon fayllari va `test_db.sqlite3`), `AGENTS.md`/`README.md`/`project-context.md` (kvota-xavfsiz test buyrug'i va yangi bayroqlar), `02-yol-xarita.md`, `03-mahsulot-backlog.md`. **Migration yo'q**
- Before/after dalil: `transaction_mode='DEFERRED'` bilan fayl bazasida 4 contention + 1 config testi yiqiladi — `SupplyUnavailable <- OperationalError('database is locked')`; `IMMEDIATE` bilan **9/9 OK** (1.9s)
- Test holati: `AZURELMS_TEST_FILE_DB=1 ... manage.py test aicontrol.test_supply_concurrency` — **9/9 OK**; default `AZURELMS_SKIP_ENV_FILE=1 ... manage.py test` — **536 test, OK (skipped=6)**, 425s. Baseline 527/527 (303s) edi: +9 test, +6 skip (5 contention + 1 runtime-WAL, in-memory rejimda kutilgan). Suite vaqti +40% — narxi `IMMEDIATE`/WAL, ataylab qabul qilindi
- `manage.py check` — 0 issue; `makemigrations --check --dry-run` — No changes; `system_audit --fail-on never` (normal env) — **10/10 GREEN**
- Dev server smoke: `/`, `/sit/`, `/users/login/` → **200**, `db.sqlite3` endi doimiy WAL rejimida
- `git diff --check`: `.gitignore`dagi 4 ta ogohlantirish **pre-existing** — bu fayl repoda CRLF bilan saqlanadi, Azurbekning `75dc252` commiti ham aynan shunday 2 ta ogohlantirish bergan. Qolgan barcha fayllar toza; churn yo'q
- Halol qolgan chegaralar: (1) PostgreSQL contention proofi **bajarilmadi** — bu mashinada PG server ham, docker ham yo'q (`psycopg2-binary` faqat klient); (2) proof multi-thread/multi-connection, alohida OS processlari bilan emas — SQLite qulfi fayl darajasida ishlagani uchun semantika yaqin, ammo bir xil emas; (3) `timeout=15` — og'ir yozuv raqobatida so'rov 15 soniyagacha kutishi mumkin; (4) `IMMEDIATE` har write tranzaksiyani erta serializatsiya qiladi (`ATOMIC_REQUESTS=False` bo'lgani uchun blast radius cheklangan); (5) WAL `db.sqlite3`ga birinchi ulanishda yoziladi va `-wal`/`-shm` yon fayllari paydo bo'ladi
- A8 ning queue/execution labelini **o'zgartirmadim** — bu owner qarori. Fakt qatorlari (nima bajarildi, nima qoldi) yangilandi
- Davom etilishi kerak: PostgreSQL contention proofi (owner PG o'rnatsa); keyin `A0b`. Recon paytida A0b uchun 4 ta teshik tasdiqlandi: teacher default-allow (`core/teacher_views.py:38` — biriktirilgan kursi yo'q teacher barcha kurslarni ko'radi), django-csp **4.0** o'rnatilgan bo'lsa-da settings eski `CSP_*` nomlarini ishlatadi (real CSP header chiqmaydi), WebSocket `is_authorized()` faqat `connect()` da, va to'lov cheki/vazifa fayli/messenger attachment `/media/` dan imzosiz uzatiladi

## 2026-08-14 [Codex]: A8 Gemini free-tier supply guard implementatsiyasi

`A8` holati: **`IMPLEMENTED/TESTED — LOCAL REGRESSION GREEN`**. `AISupplyEvent` va `AISupplyState` asosidagi project-wide ledger har remote AI call oldidan kunlik request/token hamda bir daqiqalik request capacity'ni rezerv qiladi, yakunda actual usage/attempt bilan reconciliation qiladi va ledger DB xatosida fail-closed to'xtaydi. Bu per-user 5h/weekly allowance'dan alohida upstream supply gate: staff/superuser ham unga kiradi. Main chat reservation'i memory/RAG'dan oldin olinadi; `AIResponseRun.idempotency_key` duplicate taskni qayta providerga yubormaydi. SmartForm, Telegram guest, chat/grounding, RAG/memory embedding va ikkala reindex yo'li ledgerga ulandi; cache-hit embedding remote request sarflamaydi.

Gemini provider SDK retry'si o'chirildi va logical call `1 primary + max 1 fallback` bilan cheklandi. `429/quota/billing` birinchi urinishdayoq fan-outni to'xtatib cooldown circuit'ini ochadi; circuit network oldidan yana tekshiriladi. Rasmiy model tekshiruvidan keyingi allowlist: stable/free-tier/cost-efficient primary `gemini-3.1-flash-lite` va faqat vaqtinchalik fallback `gemini-2.5-flash-lite`. Google deprecation jadvalida 2.5 Flash-Lite uchun shutdown sanasi e'lon qilinmagan; **2026-10-16** esa fallbackni qayta tekshirish/remove/migrate qilish uchun ichki review deadline. Text caplari: output `640` token, prompt `12,000` belgi, request timeout `8s`, deadline `20s`; embedding caplari: `64` input, har input `8,000` belgi, batch `64,000` belgi, timeout `8s`. `AI_FREE_TIER_MODE=True`; guest demo default-off va API grounding barcha effortlarda hard-off. `AI_CHAT_PROVIDER=digitalocean` explicit `AI_ALLOW_DIGITALOCEAN=True` bo'lmasa provider yaratilishidan oldin rad etiladi, noma'lum provider ham fail-closed. Control Center global supply stoplightini va xavfsiz budget/cooldown ko'rsatkichlarini chiqaradi; policy va event/state adminlari mavjud. Eski live model-list diagnostikasi o'chirildi.

**Live-call shaffoflik tuzatishi:** oldingi rebaseline yozuvidagi “live Gemini request yuborilmadi” jumlasi o'sha docs-only auditga tegishli edi. Keyingi A8 ishida broad testlar noto'g'ri local credentialni ko'rib jami **3 ta tasodifiy real Gemini request** yubordi: provider subagent runida 2 ta, UI agentning 62-test runidagi attachment testida yana 1 ta. Uchalasi ham model `404` bilan tugadi; muvaffaqiyatli generation bo'lmadi. Shundan keyingi targeted runlarning barchasi mock/offline bajarildi.

**2026-08-14 model/quota tekshiruvi:** Google `gemini-3.7-flash`ni 2026-08-13 kuni GA chiqardi, ammo public hujjat exact Free RPM/TPM/RPDni bermaydi. Login qilingan [AI Studio Rate Limit](https://aistudio.google.com/rate-limit?timeRange=last-28-days) oynasidagi `AzureAI` Free-tier snapshotida 3.7 Flash **5 RPM / 250K input TPM / 20 RPD**, joriy 3.1 Flash Lite esa **15 RPM / 250K input TPM / 500 RPD** ko'rsatdi. Shu sabab 3.7 A8 allowlistiga kiritilmadi: uning RPD sig'imi joriy modeldan 25 baravar past, ichki `100/day` va `10/minute` caplari bilan ham mos emas. Snapshot account/project holatiga bog'liq va vaqt o'tishi bilan o'zgarishi mumkin.

**Free-tier grounding closeout:** Google pricing bo'yicha Free Standard API'da Search/Maps grounding mavjud emas. Endi `AI_FREE_TIER_MODE=True` bo'lsa engine explicit/medium/legacy-heavy search intentini specialistga yubormaydi, provider esa direct caller `enable_web_search=True` bersa ham `GoogleSearch()` toolini qurmaydi. Natija bitta plain `gemini-3.1-flash-lite` request, ledgerda `chat`, metadata'da `requested=true`, `blocked_by_free_tier=true`, `enabled=false`; paid/admitted yo'l `AI_FREE_TIER_MODE=False` va `GEMINI_GROUNDING_ENABLED=True` bo'lgandagina saqlanadi.

- Branch: `codex/nuclear-plan-rebaseline`
- Migrationlar: `aicontrol/migrations/0002_ai_supply_budget.py`; `messenger/migrations/0014_ai_response_idempotency.py`; `users/migrations/0015_free_tier_model_default.py`; `users/migrations/0016_alter_notification_options.py`
- Apply/check buyruqlari: `python manage.py migrate`; `python manage.py check`; `python manage.py makemigrations --check --dry-run`
- Offline target buyruqlar: `python manage.py test ai.providers.tests aicontrol.tests messenger.test_embedding_supply`; yakuniy full suite provider kalitlari va env-file loading o'chirilgan holda bajarildi
- Test holati: **527/527 OK**; `manage.py check` — 0 issue; `makemigrations --check --dry-run` — no changes; barcha 4 migration local SQLite'ga apply; `system_audit --json --fail-on never` — **10/10 GREEN**, supply 0/100 daily request, 0/10 minute request, 0/250000 token va circuit closed
- Full-suite closeoutda eski Windows/SQLite notification timestamp flake'i ham tuzatildi: `Notification` ordering'i `-created_at, -id`, streak holati o'zgarganda deterministic bubble timestamp; focused streak suite 15/15 OK
- Final QA qo'shimchalari: client resend idempotency stable `client_message_id` bilan dedupe; explicit retry yangi server key oladi; Telegram guest update key ledgerda dedupe; grounding metadata faqat real groundingni “used” deb belgilaydi; `GEMINI_API_KEY` bo'lmasa ambient `GOOGLE_API_KEY` ishlatilmaydi va SDK/network `0`
- Halol qolgan risklar: SQLite va PostgreSQL'da haqiqiy bir vaqtdagi contention/transaction proof testi hali yo'q; AI Studio tashqi quota snapshoti dynamic/account-specific; SmartForm/guest counterlari va lesson reindex uchun to'liq concurrency lease/claim hali qurilmagan; temporary `gemini-2.5-flash-lite` fallbacki 2026-10-16 ichki review deadline'ida remove/migrate uchun qayta ko'riladi; joriy Gemini adapterida vision mavjud emas
- Davom etilishi kerak: ikki DB backendda parallel reservation/duplicate contention testi; keyin A8 production-concurrency closeout qarori. Bu holat production readiness yoki public rollout `GO` degani emas

## 2026-08-14 [Codex]: Local-first Nuclear Program rebaseline va Gemini free-tier contracti

Azurbekning owner qarori bo'yicha loyiha production qayta ochilguncha **LOCAL/PRE-PROD** rejimida qoladi. DigitalOcean kreditlari bekor qilingan: App Platform, inference, Managed DB/Valkey va Spaces ishlatilmaydi; adapter kodi o'chirilmadi, ammo config bo'yicha dormant/HOLD. Joriy local primary `AI_CHAT_PROVIDER=gemini`; oddiy chat, grounding va embedding ham Gemini kvotasiga tegadi. Shu sabab keyingi birinchi kod slice'i `A8 — Gemini free-tier budget mode`, production esa alohida qayta admission.

Source audit eski “maverick/DO primary, Gemini faqat web search” farazini bekor qildi. Hozir providerda 9 model × 2 urinishgacha fan-out, global daily request/token budget va circuit breaker yo'q; SmartForm, guest bot va embedding calllari to'liq ledgerda emas. DO HOLD ham hozir code-level kill switch emas, bo'sh credential va env config bilan ta'minlangan. Rejaga barcha call-path accounting, atomic reservation, free-model allowlist, `1 primary + max 1 fallback`, `429` cooldown, prompt/output cap, idempotency, staffni supply budgetga kiritish, deterministic degradation va owner admissionisiz DO network call `0` acceptance'i yozildi.

Rebaseline tarixiy driftlarni ham yopdi: SIT S3/S4 va Telegram F0–F9 kodda; landing Bosqich 1 implement/test qilingan, ammo authenticated visual QA kutadi; 14 AI skill mavjud; local Python 3.12.13. Muhim yangi halol chegaralar: current Gemini adapterida vision o'chiq (`image_qa` routing bor, rasm tahlili capability emas); django-csp v4 bilan eski `CSP_*` config real full header bermaydi; guest bot selected-user allowlisti yo'q; local GREEN production GO emas. Oldingi marinebook yozuvlari historical evidence sifatida o'zgartirilmadi — ushbu yozuv ulardagi DO-primary, Gemini-search-only va F10-next-production yo'nalishlarini supersede qiladi.

- Branch: `codex/nuclear-plan-rebaseline`
- Rebaseline commit: `52fd543` — launch-plan `README` + `01–05`, Telegram/Landing/Evening rejalari, `project-context.md`, root `README.md` va `AGENTS.md`
- Runtime kod/migration: o'zgarmadi; live Gemini request yuborilmadi, bepul token sarflanmadi
- Test holati: `python manage.py check` — **0 issues**; `makemigrations --check --dry-run` — **No changes**; AI/provider/control target suite — **39/39 OK**; full suite — **467/467 OK**; streak focused regression — **1/1 OK**
- Audit: `system_audit --json --fail-on never` — localda **10 GREEN / 0 AMBER / 0 RED** (`gemini`, polling mode, SQLite/LocMem/InMemory/local media); bu quota reachability yoki production readiness dalili emas
- Docs QA: barcha changed Markdown relative linklari va code fence'lari **OK**; `git diff --check` **OK**; ikki mustaqil source/plan QA topilmalari kiritildi
- Davom etilishi kerak: avval `A8`; keyin `A0b` (private media, teacher/socket scope, CSP) va `A1a` (local CI/readiness/restore). `A1b` production/cloud va Telegram F10 owner HOLDni ochmaguncha boshlanmaydi

## 2026-07-29 [Claude Code]: SIT AI maslahatchisi (`sit_advisor` skill) — S3

SIT sahifalaridagi "AI bilan maslahatlashish" CTA oddiy Azure AI'ga olib borardi, u esa SIT bazasini umuman bilmasdi — ya'ni tugma AI bera olmaydigan narsani va'da qilardi (`rules-for-agents` §15 buzilishi). Endi AI portaldagi tekshirilgan katalogdan javob beradi. Owner qarorlari: kirish auth-gated (anonim AI kvota/xarajat nazoratisiz bo'lardi), tartibda S3 avval.

Texnik qaror: **RAG embedding emas, deterministik so'rov**. Katalog strukturali (narx, shahar, til, daraja, holat) — `sit/selectors.advisor_catalog_queryset()` orqali aniq o'qiladi, shuning uchun AI narx yoki muddat "taxmin" qila olmaydi. Faqat `is_published` yozuvlar chiqadi. Prompt hajmi chegaralangan (25 universitet / 8 dastur / 12 qo'llanma), katalog o'sganda ham portlamaydi.

Ikkita nozik joy hal qilindi. (1) Kalit so'zlarda **"magistratura" ataylab yo'q** — u core LMS (sertifikat talabgori, S1 segment) auditoriyasining so'zi; qo'shilsa til kursi savollari SIT'ga adashib ketardi, regressiya testi buni qo'riqlaydi. (2) `registry.select_for_request`da medium/heavy web-search effort vaqtga bog'liq savolni **keyword scoring'gacha** web'ga yuborardi — "yangi qabul qachon boshlanadi" kabi SIT savoli tekshirilgan lokal katalog turganda webga chiqib ketardi; endi SIT savoliga istisno bor.

- Branch: `claude/sit-advisor-skill` (`main`dan; avval codex'ning merge qilinmagan S4 commitlari ustida qurilgan edi — egasi S3'ni mustaqil merge qila olishi uchun toza `main`ga ko'chirildi)
- Yangi/tegilgan: `ai/tools/context.py` (`_render_sit_catalog`), `ai/skills/registry.py` (skill + web_search istisnosi), `ai/skills/sit_advisor/SKILL.md`, `sit/selectors.py` (`advisor_catalog_queryset`), `sit/test_ai_advisor.py`
- Test holati: `python manage.py test sit ai messenger` — **158/158 OK** (13 yangi: routing, core-LMS regressiya, tool faqat published, inactive dastur, qo'llanma, qat'iy qoidalar, tartib); `check` — 0 issues; churn yo'q (140 qator sof qo'shimcha). Uchdan-uchiga real bazada tekshirildi: savol → `sit_advisor` → `sit_catalog` tool → real dastur/narx/tayyorlov ma'lumoti.
- **DIQQAT — ma'lumot gigienasi:** hozir public portalda ikkita soxta universitet nashr etilgan holatda turibdi (`TEST: Bosphorus Technology University`, `TEST: Anatolia State University`, manba `example.com`, o'ylab topilgan narxlar). Ular anonim tashrifchiga ko'rinadi va endi AI ham ularni haqiqiy variant sifatida tavsiya qiladi. Bu `02-yol-xarita` R12 riskining amaldagi ko'rinishi. Ma'lumotga tegmadim — owner qarori; tavsiya: `is_published=False` qilish.
- Davom etilishi kerak: S2 (yordam so'rovi lifecycle) hali yo'q — yordam CTA `messenger:tutor`ga universitet konteksitisiz boradi va kuzatilmaydi. Codex parallel ravishda S4 (backoffice workflow) ni qilgan, u alohida `codex/sit-backoffice` branchida.

## 2026-07-29 [Codex]: SIT owner backoffice workflow

Study in Turkey katalogi owner-only `/backoffice/sit/` control surface'iga ulandi: dashboard va 90 kunlik dolzarblik signali, filterlangan universitet/e'lon/qo'llanma ro'yxatlari, universitetning fakultet/dastur/tayyorlov/talab/hujjat/xizmat/media formsetlari, preview hamda reason+confirmation+`LogEntry` audit ishlaydi. `Announcement.show_on_home` public publish'dan ajratildi — endi oddiy nashr avtomatik bosh sahifaga chiqmaydi; migratsiya mavjud published e'lonlarning oldingi ko'rinishini saqlaydi.

- Branch: `codex/sit-backoffice`
- Commitlar: `4cb3487`
- Migratsiya: `sit/0002_announcement_show_on_home.py` — Boolean AddField + mavjud published e'lonlarni `show_on_home=True` backfill; data loss yo'q
- Test holati: `python manage.py test` — **453/453 OK**; SIT + backoffice/template focused suite — **42/42 OK**; `check` — **0 issues**; `makemigrations --check --dry-run` — **No changes**; `collectstatic` — **OK**
- Browser QA: owner sessiyasi, 1280×720 va 390×844, light/dark; dashboard, katalog GET filteri, 7 ichki universitet paneli, e'lon/qo'llanma editorlari, mobile drawer va internal table scroll tekshirildi; page overflow **0**, console error/warning **0**. Screenshotda topilgan row/badge overlap shu commitda tuzatildi.
- Davom etilishi kerak: real universitet ma'lumotini rasmiy manbadan kiritish; S2 canonical `SITInquiry` lifecycle va keyingi AI advisor alohida slice. Claude'ning `claude/sit-nuclear-program` reja branchi bu branchga aralashtirilmadi.

## 2026-07-29 [Claude Code]: SIT launch-plan hujjatlariga yozildi (audit + admission)

Codex `project-context.md`ni (arxitektura wiki) puxta yangilagan edi, lekin SIT `launch-plan/` hujjatlarida umuman yo'q edi: admission gate javoblari, ustuvorlik qarori va A-narvoni bilan ziddiyat yozilmagan. Avval codex ishi mustaqil auditdan o'tkazildi (marinebook da'volariga ishonmay), keyin SIT strategiya/roadmap/backlogga qo'shildi.

Backlogda yangi `S` bo'limi: admission gate 7 javobi, `S1` (bajarildi, `EVIDENCE READY`), `S2` yordam so'rovi lifecycle, `S3` AI advisor, `S4` owner workflow; 3 ochiq owner qarori va 3 risk. Muhim ziddiyat ochiq yozildi: `Ish tartibi`ning "bir vaqtda bitta ADMIT band" qoidasi SIT bilan buziladi — owner buni bilib qabul qilgan, shuning uchun 6-band istisno sifatida qo'shildi. Yana bir topilma: **5k jiddiylik to'lovi bloklangan** — u avtomatik to'lovni talab qiladi, avtomatik to'lov esa `C. CUT`da (Payme/Click); qo'lda receipt bilan mayda to'lov owner yukini kamaytirmay, oshiradi.

- Branch: `claude/sit-nuclear-program` (commit `e2a59c9`)
- Tegilgan: `launch-plan/01-strategiya.md` (SIT ↔ S3 segmenti + pozitsiya chegarasi savoli), `02-yol-xarita.md` (parallel yo'lak qatori + R11/R12 risk), `03-mahsulot-backlog.md` (`S` bo'limi, ish tartibi istisnosi, sessiya tartibi)
- Codex ishi auditi (mustaqil tasdiqlangan): `python manage.py test` — **443/443 OK**; `test sit` — 5/5; `check` — 0 issues; `makemigrations --check` — No changes; live `/sit/` real published data bilan render, console xato 0. Codex marinebook da'volari haqiqatga mos chiqdi.
- Divergensiya qayd etildi: muhokamada bilim bazasi uchun `blog`ni qayta ishlatish kelishilgan edi, implementatsiya alohida `KnowledgeArticle` bilan ketdi (sababi: manba/tekshiruv gate'i). Zarari yo'q, qaror owner'ga qoldi (`S-D1`).
- Davom etilishi kerak: `S2` (yordam so'rovi lifecycle) — SIT'ning keyingi ustuvor slice'i, chunki hozir lead oqimi kuzatilmaydi.

## 2026-07-28 [Codex]: SIT backend va data-driven public portal

`playground/SIT/` prototipi alohida `sit` Django appiga ko'chirildi: universitet, fakultet/dastur, tayyorlov kursi, talab/hujjat/xizmat, media, e'lon va qo'llanma modellari; admin boshqaruvi; katalog filterlari; public home/list/detail sahifalari; responsive light/dark interfeys tayyor. Vaqtga sezgir public ma'lumotlar rasmiy manba va oxirgi tekshirilgan sanasiz nashr qilinmaydi; boshlang'ich migratsiya ataylab tekshirilmagan demo universitetlarni seed qilmaydi.

- Branch: `codex/sit-migration`
- Commitlar: `58bcf50`
- Migratsiya: `sit/0001_initial.py`
- Test holati: `python manage.py test` — **443/443 OK**; SIT + template/brand contractlar — **9/9 OK**; `python manage.py check` — **0 issues**; `makemigrations --check --dry-run` — **No changes**; `collectstatic` va `node --check static/js/sit-theme.js` — **OK**
- Browser QA: 1280×900 va 390×844; katalog qidiruv/filteri, daraja tablari, source link, light/dark theme va internal table scroll tekshirildi; gorizontal sahifa overflow **0**, console xato/warning **0**
- Davom etilishi kerak: real universitet ma'lumotlarini faqat rasmiy manbalardan kiritish; alohida SIT AI retrieval, ariza/payment/help lifecycle va owner uchun maxsus `/backoffice/sit/` workflow keyingi slice

## 2026-07-28 [Codex]: Claude SIT prototipi main'ga birlashtirildi

Claude tayyorlagan `playground/SIT/` statik prototipi to'liq saqlandi va fast-forward orqali `main`ga birlashtirildi. Prototipda bosh sahifa, universitetlar katalogi, universitet tafsiloti, davlat/xususiy turi, light/dark theme va responsive e'lonlar bo'limi bor. Bu hozircha faqat `playground/` referensi; Django production runtime, model yoki real universitet ma'lumotlariga ulanmagan.

- Branch: `claude/sit-portal-prototype` → `main`
- Commitlar: `7c4e909`, `3847e1e`, `18febdf`, `787c109`, `7f97d53`
- Test holati: `python manage.py check` — **0 issues**; `node --check playground/SIT/sit-theme.js` — **OK**; 3 HTML fayl parse va local link tekshiruvi — **OK**; `git diff --check` — **OK**
- Browser QA: bu integratsiya sessiyasida yugurilmadi; production migratsiyadan oldin desktop/mobile light/dark interaktiv tekshiruv kerak
- Davom etilishi kerak: yangilangan `main`dan `codex/sit-migration` branchida prototipni canonical Django model/view/template oqimiga ko'chirish

## 2026-07-27 [Claude Code]: Landing editor Bosqich 1 — LandingPage matn editori

Landing editor rejasining (nuclear-program/landing-editor-plan.md) 1-bosqichi bajarildi: bosh sahifa matnlari endi Jazzmin admin o'rniga backoffice ichida, `/backoffice/landing/` da, sahifa bo'limlariga mos qulay UI orqali tahrirlanadi. Owner qarorlari: faqat superuser, majburiy change_reason, anchor havola (iframe keyin). `LandingPageForm` ~55 matn maydonini 9 bo'limga guruhlaydi (rail/hero/demo/jarayon/daraja/AI/imtihon/sertifikat/footer); `backoffice_landing` view brend paneli pattern'ida (`transaction.atomic` + `LogEntry` audit + no-op). Repeatable ro'yxatlar (statistika, daraja bosqichlari, AI/imtihon kartalari) — Bosqich 2.

- Branch: `claude/backoffice-landing-editor`
- Commitlar: `feat(backoffice): landing editor Bosqich 1` (yuqoridagi HEAD)
- Yangi fayllar: `core/landing_forms.py`, `templates/backoffice/landing_editor.html`, `static/css/landing-control.css`, `core/test_landing_editor.py`; tegilgan: `core/views.py`, `core/urls.py`, `templates/backoffice/base.html`
- Test holati: `python manage.py test core.test_landing_editor frontend` — **12/12 OK** (6 yangi: owner-only access, confirm/reason majburiy, save+audit, no-op, landing'da aks etishi); `check` — 0 issues. Churn minimal (446 vs 443 real).
- Browser QA: anonim `/backoffice/landing/` → login redirect tasdiqlandi (owner gate, crash yo'q). Authenticated visual QA qilinmadi — parol kiritib login qilmayman (xavfsizlik qoidasi); owner o'zi kirsa screenshot bosqichi qilinishi mumkin. Funksional to'g'rilik test client (200 + template + kontent) bilan tasdiqlangan.
- Davom etilishi kerak: Bosqich 2 — repeatable ro'yxatlar menejeri (CRUD + drag-reorder). `main`ga merge qilinmagan.

## 2026-07-27 [Claude Code]: Landing editor rejasi + branch (backoffice'ga ko'chirish)

Landing hozir faqat Jazzmin admin (`/admin/`, `ENABLE_LEGACY_ADMIN`) orqali tahrirlanadi — owner uchun noqulay va prod'da ishonchsiz. Azurbek uni backoffice ichiga chiroyli/qulay shaklda ko'chirishni so'radi. Backoffice pattern auditi qilindi (brand mutation: `transaction.atomic` + o'zgargan maydon + no-op + `LogEntry` audit; `admin-shell.css` dizayn tizimi; nav guruhlari) va 6 bosqichli reja `nuclear-program/landing-editor-plan.md`ga saqlandi. Hali kod yozilmadi — bu bosqich faqat reja/branch.

- Branch: `claude/backoffice-landing-editor` (`origin/main`dan)
- Reja: `nuclear-program/landing-editor-plan.md` (admission gate javoblari, dizayn tamoyillari, 6 bosqich + DoD, ochiq owner qarorlari)
- Test holati: yugurilmadi (kod yo'q)
- Davom etilishi kerak: Bosqich 1 — `/backoffice/landing/` route + `LandingPage` singleton editor (bo'lim-markazli forma). Ochiq qarorlar: change_reason majburiymi, ruxsat darajasi, Jazzmin fallback, live preview — owner tasdig'i kerak.

## 2026-07-27 [Claude Code]: Landing page to'liq admin nazoratiga o'tkazildi

Bosh sahifa (`templates/index.html`) v2 redizayni kontentni deyarli to'liq hardcode qilib, mavjud model/admin qatlamini (LandingPage hero/cta maydonlari, Statistic, hero slides, testimonials, popular_courses) e'tiborsiz qoldirgan edi — `home_view` context'ga uzatsa ham template faqat "Qanday ishlaydi?", brend va footer kontaktni dinamik ko'rsatardi. Azurbek to'liq admin nazoratini so'radi (owner admission; demolar ham tahrirlanadigan bo'lsin). Endi rail, hero, demo dashboard, statistika, daraja yo'li, AI repetitor, imtihon, sertifikat va pastki CTA/footer'ning har bir matni admin paneldan boshqariladi.

`LandingPage`ga ~50 yangi maydon (rail, hero kicker/tugma, demo dashboard, bo'lim sarlavhalari, AI/sertifikat demo matnlari, footer) qo'shildi; 3 yangi child model — `LandingLevelStage`, `LandingAIFeature`, `LandingExamSkill` (admin'da tahrir + tartib); `Statistic` animatsiya uchun `numeric_value`/`suffix`/`decimals`/`is_active` bilan kengaytirildi; footer ustunlari mavjud `LandingNavItem` (`footer_*_links`) ga ulandi. Defaultlar joriy ko'rinadigan matnga teng qilib data migratsiyasida seed qilindi — vizual o'zgarish yo'q.

- Branch: `claude/landing-admin-control` (`origin/main`dan)
- Commitlar: `58c8db6`
- Migratsiyalar: `0019` (3 model + ~50 AddField, hammasi default bilan — data loss yo'q), `0020` (data seed: singleton hero matnini joriy nusxaga moslaydi + child modellarni seed qiladi + fresh install uchun footer nav; reversible)
- Test holati: `python manage.py test frontend` — **6/6 OK** (yangi `LandingAdminControlledContentTests`: hero/section text, repeatable modellar, hidden itemlar, footer nav); `python manage.py check` — 0 issues; `makemigrations --check` — No changes. Browser QA (lokal dev server, owner sessiyasi, 800px, light): hero/stats(2,400+ count-up)/how/path(locked=lock icon)/ai(typing)/exam(4 karta)/cert(namuna)/footer — hammasi modeldan render, console xato 0, vizual baseline bilan bir xil.
- Kontent farqi (kutilgan): footer "Platforma" ustuni endi admin-sozlangan `LandingNavItem`larni ko'rsatadi (Kurslar/Narxlar/Sertifikatlar/Qabul yo'li) — eski hardcoded "AI repetitor" o'rniga.
- Line-ending: tegilgan `.py`/`.html` fayllar LF'ga normallashtirildi (repo indeksi oldindan mixed CRLF/LF edi), shu sabab xom diff kattaroq (2086/1217); mantiqiy o'zgarish `git diff --ignore-cr-at-eol` bilan ancha kichik (masalan `views.py` atigi 11 qator). `.md` fayllar indeksi LF bo'lgani uchun ular churn qilmadi.
- Davom etilishi kerak: `main`ga merge qilinmagan (Azurbek qaroriga qoldi). Demo dashboard sidebar navi (Dashboard/Darslar/...) va PATH jadval sarlavhalari (Bosqich/Daraja/Darslar/...) ataylab statik qoldirildi — strukturaviy chrome, kontent emas. Mixed line-ending repo-wide holati alohida masala.

## 2026-07-24 [Claude Code]: Bo'sh AI chatlar to'planmasin (lazy new chat)

"Yangi suhbat" har bosilganda yangi bo'sh AI xona yaratilib, ro'yxatda to'planib qolardi (ikki marta bossang ikkita keraksiz bo'sh chat). Endi `messenger.access.get_or_create_ai_draft_room` bo'sh (xabarsiz) xona bo'lsa uni qayta ishlatadi — `create_ai_chat` shuni chaqiradi, ko'p bosish ham bitta bo'sh xona bilan cheklanadi. Qo'shimcha: suhbatlar ro'yxati faqat xabarli yoki ayni ochiq turgan xonani ko'rsatadi (`ai.html`da `{% if room.message_count or room.id == active_ai_room_id %}`), bo'sh xona ilk xabardan keyingina ro'yxatda saqlanadi.

- Branch: `claude/messenger-lazy-chat` (`origin/main`dan)
- Test holati: `python manage.py test messenger.test_lazy_ai_chat` — **6/6 OK**; `check` — 0 issues; browser: `get_or_create_ai_draft_room` uch chaqiruvda bir xil xona (id 7,7,7) qaytardi, sidebar 5 bo'sh xona bo'lsa ham ko'rsatmadi. Churn yo'q (byte-patch).
- Davom etilishi kerak: to'liq "xonasiz" oqim (ilk xabargacha DB'da umuman yozuv bo'lmasligi) WebSocket qayta yozishni talab qiladi. Hozircha bitta qayta ishlatiladigan bo'sh xona (ro'yxatda yashirin).

## 2026-07-24 [Claude Code]: Messenger AI chat avatari owl mascot bo'ldi

Messenger'dagi AI chat avatarlari `bi-stars` yulduzcha ikonasi edi. Endi Azure mascot rasmi (`img/ai-assistant-widget.png` — floating widget'dagi owl) ishlatiladi: suhbatlar ro'yxati, chat sarlavhasi, xabar pufakchalari va bo'sh holat. Yagona `components/ai_avatar.html` komponenti; owl transparent character bo'lgani uchun konteyner foni `:has(.ai-avatar-img)` bilan tozalanadi. Jonli xabarlar `messenger-chat.js` orqali quriladi — u ham owl'ni ishlatadi (URL shablondan `data-ai-avatar-url`).

- Branch: `claude/messenger-owl-avatar`
- Test holati: `check` — 0 issues; browser: 4 avatar joyi + jonli typing/javob avatari owl ko'rsatdi, console xato yo'q. Churn yo'q.

## 2026-07-23 [Claude Code]: Haqiqiy o'quv seriyasi (streak) + mascot undash tizimi

Streak butunlay soxta edi — `streak_days` hech qaysi modelda maydon emas, 7 ta joyda `|default:0` bilan doim 0 ko'rsatardi. Azurbek to'liq streak tizimini qurishni so'radi (backlog uni "Defer" qilgan; bu owner qarori bilan admission oldindan berildi). Dizayn qarori: streak DAVOMATDAN emas, o'quvchining o'z tashabbusi bilan qilgan kunlik MALAKALI O'QUV HARAKATIDAN oshadi — davomat o'qituvchi belgilaydi va faqat dars kunlari bo'ladi, shuning uchun kunlik seriya undash mexanizmi uchun yaramaydi.

Ikki qismda qurildi. (1) O'zak: `LearnerStreak` modeli + `users/streak.py` canonical service (`record_activity` yagona yozuv nuqtasi — kun asosida idempotent, freeze bilan bir kunlik bo'shliqni qoplaydi, aks holda reset). Dars tugatish, quiz/vazifa topshirish, imtihon urinishi va present/partial davomat shu servisni chaqiradi; 7 ta soxta display haqiqiy qiymatga ulandi, leaderboard N+1 `select_related('student__streak')` bilan. (2) Undash: mascot xabar banki (holat × kun vaqti), generator + Celery beat (kechqurun 19:00) + management command. Azurbek so'roviga ko'ra bildirishnoma **event-bound va vaqtinchalik**: kunlik bitta bildirishnoma joyida yangilanadi — "dars qil" nudge borgach o'quvchi harakat qilsa `record_activity` (on_commit) o'sha bildirishnomani tabrikка aylantiradi, va holat o'zgarganda `created_at` yangilanib ro'yxat tepasiga chiqadi.

- Branch: `claude/streak-system`
- Commitlar: `f906cb6` (o'zak), `0745664` (undash)
- Test holati: `python manage.py test` — **422/422 OK**; `check` — 0 issues; `makemigrations --check` — No changes; migratsiyalar `0013` (LearnerStreak), `0014` (Notification.CATEGORY_STREAK) xavfsiz. Browser QA (lokal, owner sessiyasi): dashboard/topbar "🔥 5 kun"; at-risk nudge "Seriyangiz kutmoqda", harakatdan keyin joyida "Seriya saqlandi"ga aylandi (COUNT 1 da qoldi), eski xabar yo'q. `core/celery.py` CRLF churn'i baytma-bayt qayta qo'llash bilan bartaraf etildi.
- Davom etilishi kerak: Telegram yetkazish (hozir faqat ilova bildirishnomasi; outbox infra A0b/A1 bilan); freeze token'ni o'quvchi qanday olishi (hozir faqat `grant_freeze` admin/mukofot); "done" tabriki hozir faqat kunlik bildirishnomada — istasa toast/animatsiya qo'shsa bo'ladi. Backlog `03-mahsulot-backlog.md`dagi "Streak/freeze — Defer" bandini Azurbek admission qarori bilan yangilash kerak.

## 2026-07-23 [Claude Code]: A0a stop-ship security — auth token, bot admin va webhook

P0 backlogining A0a bandidagi to'rtta security teshigi yopildi. (1) Telegram deep-link kirish tokeni jiddiy zaif edi: `authenticated` bo'lgach sessiya cheksiz yashardi va endpoint har chaqirilganda qayta login qilardi — tokenni bilgan istalgan kishi, istalgan brauzerdan kira olardi. Endi token bir martalik (`consumed_at`, `select_for_update` qulfi bilan), brauzerga bog'langan (`client_key`) va `authenticated` holat ham TTL'ga bo'ysunadi. (2) Deaktivatsiya qilingan staff hali ham bot admini edi — `is_active` hech qayerda tekshirilmasdi; yagona `is_active_staff()` helperi va middleware `resolve_identity` tuzatildi. (3) Webhook secret uchun taniqli default bor edi — default bo'sh qilindi va view fail-closed, `setwebhook` ham secret'siz o'rnatishni rad etadi. (4) Mos kelmagan secret token endi logga yozilmaydi, taqqoslash `constant_time_compare` bilan.

Yo'lda ikkita qo'shimcha xato topildi va tuzatildi: muddati o'tgan `authenticated` sessiya frontendga yolg'on `authenticated` javob berardi (login bo'lmagan holda) — endi `expired` qaytaradi; va `setwebhook` secret'siz o'rnatsa view fail-closed bo'lgani uchun bot jimgina ishlamay qolardi — endi command oldindan to'xtatadi. `users/tests.py`dagi ikki eski test haqiqiy init oqimiga moslandi, chunki auth xulqi ataylab o'zgardi.

- Branch: `claude/a0a-auth-hardening`
- Commitlar: `e7cd4a6` (auth token), `5bea4a5` (bot/webhook)
- Test holati: `python manage.py test` — **385/385 OK**; `python manage.py check` — **0 issues**; `makemigrations --check` — **No changes**; migratsiya `0012` ikkita default'li AddField + choices, ma'lumot yo'qolmaydi. Focused: 22/22 (auth+bot security). Haqiqiy trailing bo'shliq yo'q (`--check` signali sof CRLF, fayllar repoda oldindan CRLF).
- Davom etilishi kerak: A0a ning qolgan qismi — teacher scope default-deny (hujjatda yozilgan, hali kodda tasdiqlanmagan), private media/upload MIME-magic-byte gate (A0b). Keyingi P0 band — A1 production runtime/CI. Branch `main`ga merge qilinmagan, Azurbek qaroriga qoldi.

## 2026-07-23 [Claude Code]: Sozlamalar bo'limlarga ajratildi, profil joyida tahrirlanadigan bo'ldi

Azurbek sozlamalarni Claude'ning sozlamalar oynasi kabi bo'limlarga ajratishni so'radi. Endi 4 bo'lim, har biri alohida sahifa: Hisob, Maxfiylik, To'lov, Imkoniyatlar. Bo'lim nomlari app sidebar'ining o'zida — sozlamalarda dashboard navigatsiyasi o'rnini shu 4 bo'lim egallaydi (`base_app.html`dagi yangi `app_nav` bloki orqali). Birinchi urinishda men sahifa ichida ikkinchi navigatsiya yasab qo'ygan edim; Azurbek buni ko'rsatgach bitta sidebar modeliga o'tkazildi. Eski `/settings/` va `/settings/ai-memory/` havolalari redirect bilan ishlashda qoldi, chunki ularga profil menyusi, Mini App, messenger va dashboard murojaat qiladi.

Shu sessiyada uchta yondosh ish ham bajarildi. (1) Profil avatari ko'k banner ostida yarim ko'rinmay qolardi: banner `position:relative`, avatar qatori esa `static` edi va CSS chizish tartibida pozitsiyalangan element statikdan yuqori turadi. (2) Profildagi "Tahrirlash" boshqa sahifaga sakrardi va u yerda sidebar ham almashardi; endi forma profil kartasi ichida ochiladi va maydonlar `ProfileFieldsForm` + `components/profile_fields_form.html` orqali Sozlamalar > Hisob bilan bitta manbadan keladi. Eski `UserProfileView.post()` `username` va `email`ni tekshiruvsiz qabul qilardi — UI'dan yetib bo'lmasdi, lekin joyida tahrirlash o'sha yo'lni ochardi, shuning uchun ModelForm bilan almashtirildi va `next` uchun ochiq-redirect himoyasi qo'shildi. (3) AI boshqaruvi sahifasidagi inputlar uslubsiz edi: `field-input` klassi CSS'da umuman aniqlanmagan, ustiga `color-scheme` hech qayerda e'lon qilinmagani uchun brauzerning native elementlari qorong'i temada ham yorug' chizilardi.

- Branch: `claude/settings-sections` (`claude/sidebar-profile-menu` ustiga qo'yilgan — u hali `main`ga merge qilinmagan)
- Commitlar: `12c659f`, `88a7580`, `22484b9`, `0b3bc8e`
- Test holati: `python manage.py test` — **367/367 OK**; `python manage.py check` — **0 issues**; `git diff --numstat` va `-w` bilan bir xil (churn yo'q). Browser QA (lokal dev server, owner sessiyasi): 4 bo'lim 1180x820 va 390x844 da, light va dark — sidebar'da dashboard elementlari yo'q, gorizontal overflow `0`; AI sozlamasini o'zgartirgach POST Imkoniyatlarga qaytdi; profilda saqlash URL'ni o'zgartirmadi va ism darhol yangilandi; AI boshqaruvi inputlari 44px/`--paper-2`/10px radius, `color-scheme` `dark`.
- Davom etilishi kerak: `users/views.py` va `users/urls.py` uchun `git diff --check` "trailing whitespace" beradi — bu repoda oldindan mavjud holat (fayllar CRLF bilan commit qilingan, `core.autocrlf=true`), qo'shilgan qatorlar faylning o'z konvensiyasiga mos. Ikkala branch ham `main`ga merge qilinmagan, Azurbek qaroriga qoldi.

## 2026-07-23 [Claude Code]: Sidebar hisob amallari profil menyusiga ko'chdi

Azurbek sidebar pastidagi scroller'dan tashqaridagi qotgan blokdan norozi bo'ldi va uni profil dropdown'iga yig'ishni taklif qildi. Blok navigatsiya uchun ~260px joy yeb turgan edi; endi profil menyusi atigi 53px va 1280x760 da nav to'liq sig'adi (594px kontent / 594px joy, scroll kerak emas). Hisob amallari (Profil, Sozlamalar, Chiqish) va rol almashtirish (O'qituvchi/Admin paneli, O'quvchi rejimi) menyuga ko'chdi.

Bitta joyda taklifdan chetlashildi: `Yig'ish` menyuga tushmadi, chunki u hisob amali emas — ko'rinish boshqaruvi. U logotip yoniga ko'chdi va mobilda yashiriladi, chunki drawer rejimida yig'iladigan narsa yo'q. Uchala shell endi bitta `templates/components/app_user_menu.html` adapteridan foydalanadi.

- Branch: `claude/sidebar-profile-menu`
- Commitlar: `90743a7`
- Test holati: `python manage.py test` — **346/346 OK** (5 tasi yangi `core.test_app_shell.AppShellUserMenuTests`); `python manage.py check` — **0 issues**. Browser o'lchovlari (lokal dev server, owner sessiyasi): menyu yuqoriga ochiladi va ekran ichida qoladi (548–742px), `aria-expanded` almashadi, Escape va tashqi bosish yopadi, Chiqish POST forma bo'lib qoldi; yig'ilgan holatda popup 210px ga kengayadi va yorliqlar ko'rinadi (`:has()` orqali sidebar clipping'i ochiladi); 390px da yig'ish tugmasi yashirin, popup 215px va ekran ichida; console xato `0`. Uchala shell tekshirildi — o'qituvchi `is-violet`/"Muallif", backoffice `is-dark`/"Administrator", rol nishonlari joyida.
- Davom etilishi kerak: brauzer paneli ochilmagani uchun bu sessiyada vizual skrinshot olinmadi — tekshiruv DOM o'lchovlariga tayanadi. Azurbek ko'z bilan tasdiqlashi foydali. Alohida muhokama ochiq: sozlamalar sahifasini bo'limlarga ajratib alohida sahifalar qilish (hozircha tavsiya — kechiktirish, 4 bo'lim uchun erta).

## 2026-07-22 [Claude Code]: Mobil drawer va messenger layout xatolari

Azurbek telefonda ikkita jiddiy layout xatosini topdi va ikkalasi ham tasdiqlanib tuzatildi. (1) `app-shell.css` mobil rejimda `.app-side`ni `position:fixed` qilardi, lekin `.app-side-inner`da hech qanday `background` yo'q edi — drawer normal oqimdan chiqib shaffof holda kontent ustida suzardi va ikkala matn ustma-ust tushib o'qib bo'lmas edi. Bu dashboard, o'qituvchi va backoffice shell'larining uchalasiga ham tegardi. Endi drawer opaque `--panel` foniga va ortida scrim'ga ega. (2) Messenger 820px dan pastda rail va suhbat ro'yxatini qat'iy ushlab turardi, natijada 390px ekranda chatga atigi 108px qolardi; 680px dan pastda ro'yxat endi drawer, chat esa 336px oladi. Ikkala drawer tashqi bosish va Escape bilan yopiladi.

Yo'lda ikkita regress kiritildi va o'sha sessiyada tuzatildi: CSS kaskad tartibi sabab toggle tugmasi hech qachon ko'rinmasdi, va ko'p qatorli `{# #}` izoh sahifada matn bo'lib render bo'ldi (Django'da `{# #}` faqat bir qatorli). `messenger/tests.py` aralash qator tugashlariga ega bo'lgani uchun qo'shimcha baytma-bayt yozildi — aks holda ~130 qatorlik keraksiz diff chiqardi.

- Branch: `claude/mobile-sidebar-overlay-fix`
- Commitlar: `fa380a5`
- Test holati: `python manage.py test` — **339/339 OK** (3 tasi yangi `MessengerMobileShellTests`); `python manage.py check` — **0 issues**; `makemigrations --check --dry-run` — **No changes**; `git diff --check` — **OK**. Browser QA (lokal dev server, owner sessiyasi), light va dark: `/users/dashboard/`, `/backoffice/`, `/messenger/ai/` — 1280, 768, 390, 320px. Drawer ochiq holatda opaque fon va scrim tasdiqlandi; messenger chat kengligi 390px da 108px → 336px; desktop 1280px o'zgarishsiz (rail 62 / ro'yxat 288 / chat 930); gorizontal overflow `0`, console xato `0`.
- Davom etilishi kerak: alohida topilma — `templates/courses/exam_detail.html` va `exam_result.html` 1-qatorida ko'p qatorli `{# #}` izoh bor, ular sahifada matn bo'lib render bo'ladi va `<!DOCTYPE`dan oldin turgani uchun brauzerni quirks rejimiga tushirishi mumkin. Bu branch scope'idan tashqarida, alohida vazifa sifatida belgilandi.

## 2026-07-22 [Claude Code]: Brend bandining ochiq uchta gap'i yopildi

Oldingi yozuvda qoldirilgan uchta ochiq band yopildi. (1) `templates/bot/miniapp_entry.html`ga favicon include'i qo'shildi va bir martalik yamoq o'rniga yangi kontrakt testi yozildi: `templates/` ichidagi har mustaqil `<head>` canonical `brand_favicon.html`ni deklaratsiya qilishi shart, aks holda test yiqiladi. (2) Brend sahifasining haqiqiy browser QA'si yugurtirildi. (3) Band backlogda A2 ichidagi birinchi mutation surface sifatida yozildi — yangi parallel subsystem emas, va A2ning reason+confirmation+audit+no-op shartlarini qondirishi qayd etildi. Admission label ataylab Azurbekka qoldirildi.

- Branch: `main`
- Commitlar: `ee979aa`
- Test holati: `python manage.py test` — **336/336 OK**; `python manage.py check` — **0 issues**; `makemigrations --check --dry-run` — **No changes**. Browser QA (lokal dev server, owner sessiyasi): `/backoffice/control/brand/` 1280x900 va 390x844, light va dark — gorizontal overflow `0`, console xato `0`, save/confirm/reason elementlari interaktiv, CSRF va `multipart/form-data` joyida, 4 ta file input `accept="image/png,image/jpeg,image/webp"` bilan. Downstream yuza (`/users/dashboard/`) markni `AL`, nomni `AzureLMS` sifatida `SiteSettings`dan o'qidi.
- Davom etilishi kerak: yo'q. Keyingi navbat — `03-mahsulot-backlog.md` bo'yicha A0a stop-ship security pack (Telegram auth token replay, webhook secret default va secret logging, inactive staff denial, teacher scope).

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

*Eng so'nggi yangilanish: 2026-08-14 (Codex)*
