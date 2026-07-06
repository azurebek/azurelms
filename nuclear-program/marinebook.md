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
