# AzureLMS — Agentlar uchun qoidalar

Bu hujjat **Claude Code**, **Codex**, **Antigravity** (yoki boshqa AI agent) bir repo ustida ishlaganda mahsulot yo'nalishi va kod ownership'ini bitta markazda tutish uchun. Har agent sessiya boshlashidan oldin shuni o'qiydi.

Maqsad: 3+ ta agent bir vaqtda ishlasin, lekin bir-biriga aralashmasin, bir-birining ishini buzmasin, takroriy kontekst sarflashga vaqt ketmasin.

---

## 0. Eslab qolinishi kerak bo'lgan 5 ta qoida

Agar faqat 5 ta narsani eslab qolish kerak bo'lsa:

1. `main` integratsiya trunk'i. Unda faqat Azurbek ruxsati bilan ishlanadi.
2. Har agent o'z prefiks branch'ida ishlaydi: `codex/`, `claude/`, `antigravity/`.
3. Hamma bitta checkout'da ishlaydi (`C:\Users\azizb\Desktop\project\azurelms`); worktree ochilmaydi.
4. Bitta task tugasa: **test → commit → marinebook yozuvi**.
5. **Begona uncommitted o'zgarishni revert, delete yoki overwrite qilma.**

### Product authority va arxitektura doktrinasi

1. **AzureLMS'ning yagona product owneri — Azurbek.** Agentlar audit, variant, implementatsiya va verifikatsiya qiladi; scope, pricing, product claim va go/no-go qarorini o'zlashtirmaydi.
2. **Bir control plane, ko'p adapter.** Canonical Django domain model/service va backoffice yagona haqiqatni boshqaradi. Web, Telegram bot, Mini App, messenger, Celery va AI providerlar shu haqiqatga kirish adapterlaridir.
3. **Adapter biznes qoidasini egallamaydi.** Enrollment/access, lesson release, submission, grade, progress, XP, pricing/entitlement, quota va notification trigger bir canonical service/policy/state machine'da yashaydi.
4. Bir qoida ikki surface'da kerak bo'lsa, nusxa yozilmaydi: domain service chiqariladi va adapterlar unga ulanadi.
5. **Bitta markaz mega-file degani emas.** Control plane modul bo'ladi, lekin capability registry, effective policy, feature flags/kill switch, audit/event ledger va health/release holati bitta boshqaruv nuqtasida tutashadi.
6. AI yoki tashqi provider access, payment, grade yoki progressning system-of-record'i bo'lmaydi; u faqat tavsiya/evidence beradi, canonical state deterministic service yoki human approval orqali o'zgaradi.
7. **Operatsion qiymat kodda qotirib qo'yilmaydi** (owner qarori, 2026-09-11: «qotirib qo'yiladigan qiymatlar qo'yma, masalan 1 soat oldin yuborilsin desam 1 soat qilma uni — men admin paneldan o'zgartira olayin kerak bo'lganda»). Vaqt, oyna, limit va chegara ishlab turgan tizimda, deploy'siz o'zgarishi kerak: qiymat DB'dagi sozlamada, env faqat fallback, maydonda chegara validatori. **Naqsh ikki qismdan iborat va ularni aralashtirmaslik kerak:**
   - **Model shakli** — `aicontrol.AISettings`: singleton, maydonda `default=`, `help_text` bilan izoh, «bo'sh bo'lsa `settings.py` qiymati» fallback'i. Shuni ko'chirish to'g'ri.
   - **Mutation yuzasi** — `core/views.py` dagi brend/landing/kill-switch yuzalari: majburiy `change_reason`, majburiy tasdiq checkbox'i, `SystemAuditEvent` va no-op yo'l. Audit talabi **shundan** olinadi.
   **Diqqat:** mavjud AI sozlama yuzalari bu ikkinchi qismni qondirmaydi — `AISettingsAdmin` faqat `updated_by` yozadi, `backoffice_ai_control` esa singletonni to'g'ridan-to'g'ri saqlaydi; ikkisida ham sabab, tasdiq va `SystemAuditEvent` yo'q. Ya'ni `AISettings` ni **audit naqshi sifatida ko'chirmang** — aks holda yana bitta auditlanmagan operatsion yuza paydo bo'ladi. (Mavjud yuzalarni retrofit qilish alohida A2 qarzi sifatida ochiq.)
   **Yoqish/o'chirish sozlamaga emas, `core/flags.py` registriga boradi.** Bitta narsani ikki DB manbasi boshqarsa (sozlamadagi `enabled` va flag) ular bir-biriga zid bo'lib qolishi mumkin va owner qaysi qiymat amalda ekanini aniqlay olmaydi. Effective policy manbasi bitta bo'ladi: **vaqt/limit → sozlama, yoqilgan/o'chirilgan → flag.**
   **Ikki istisno ataylab kodda qoladi:** protokol faktlari (Telegram xabarining 4096 belgisi, HMAC algoritmi) va kafolatni ushlab turuvchi qo'riqchilar (masalan issiq siklni oldini oluvchi minimal kechikish) — ularni «sozlash» sozlama emas, nosozlik yo'li. Sinov savoli: *owner buni jonli dars kunida o'zgartirishni xohlashi mumkinmi, va o'zgartirish xavfsizmi?* Ikkisiga ham «ha» bo'lsa — sozlama.

Arxitektura piramidasi:

```text
Azurbek / Azure Control Center
  Policy · Health · Quality · Cost · Release
    Enrollment · Learning · AI outcome loop · Messaging
      Canonical domain services + state machines + event/audit ledger
        Web · Telegram · Mini App · Messenger · Celery · AI providers
```

---

## 1. Source of truth

Sessiya boshlanganda quyidagilar source of truth hisoblanadi:

| Tartib | Fayl / buyruq | Nima uchun |
|---|---|---|
| 1 | `git status --short --branch` | qaysi branch va dirty state |
| 2 | `git log --oneline --decorate -8` | so'nggi ishlar |
| 3 | `git branch -a` | mavjud branchlar va ownership |
| 4 | `nuclear-program/marinebook.md` (so'nggi 3-5 yozuv) | so'nggi major sessionlar |
| 5 | `nuclear-program/project-context.md` | loyiha arxitekturasi |
| 6 | task tegadigan app fayllari (model/view/url/test) | haqiqiy kod source of truth |

**Hech bir agent faqat eski chat xotirasi asosida qaror qilmaydi.** Hozirgi repo holatini tekshiradi.

Product qarorida authority yuqoridan pastga: (1) Azurbekning yozilgan qarori, (2) launch strategiya va admission/status, (3) canonical domain contract/service, (4) model/migration, (5) adapter contract, (6) UI/copy, (7) eski chat yoki marinebook. Quyi qatlam yuqoridagiga zid bo'lsa, mavjud dublikat kod yangi product haqiqatiga aylantirilmaydi.

---

## 2. Branch/write ownership

Bu jadval faqat Git write boundary. Product va integration authority Azurbekda qoladi.

| Owner | Prefiks | Misol |
|---|---|---|
| Codex | `codex/` | `codex/messenger-reply-threading` |
| Claude Code | `claude/` | `claude/rag-admin-panel` |
| Antigravity | `antigravity/` | `antigravity/dashboard-polish` |
| Human / Azurbek | `feature/`, `hotfix/`, yoki `main` | `feature/payment-flow` |
| Integration | `main` | release-ready trunk |

### Qattiq taqiqlar

- ❌ Boshqa agent branch'iga commit qilma
- ❌ Boshqa agent branch'ini force-push qilma
- ❌ `main`'ga bevosita commit/push qilma — 2026-08-15 dan buyon buni serverning o'zi rad etadi, **Azurbek uchun ham** (§9 ga qarang)
- ❌ Begona uncommitted o'zgarishni "tozalash" uchun revert qilma
- ❌ `git reset --hard`, `git clean -fd`, `git checkout -- .` ishlatma (Azurbek ruxsat bermasa)

### Branch yaratish

```powershell
git fetch origin
git checkout -b codex/<task-name> origin/main
```

**Branch nomi:** kichik harflar, 3-5 so'z, task'ni bildiradi. Umumiy `work`, `fix`, `final`, `new` kabi nomlardan qoching.

Yaxshi: `codex/ai-widget-fallback`, `claude/rag-source-panel`, `antigravity/mobile-dashboard-polish`
Yomon: `codex/work`, `claude/fix`, `antigravity/test2`

`<agent>/work` kabi umumiy branchlar ishlatilmaydi. Har feature uchun `origin/main`dan alohida branch ochiladi va PR merge bo'lgach o'chiriladi.

---

## 3. Bitta checkout tartibi (worktree yo'q)

**Owner qarori — 2026-09-10:** loyihada `git worktree` ishlatilmaydi. Hamma agent
bitta papkada ishlaydi:

```text
C:\Users\azizb\Desktop\project\azurelms     yagona checkout (venv, .env.local, db.sqlite3 shu yerda)
```

Sabab: parallel worktree'lar ikki agentga bitta muammoni bir-biridan bexabar
tuzatish imkonini berdi (2026-09-10, classbook Postgres testi), `main` integratsiya
papkasida band bo'lgani uchun oddiy `git pull` yiqilardi, va har papka o'z venv/DB'sini
talab qilardi. Endi izolyatsiya faqat **branch** darajasida.

### Ish tartibi

```bash
git fetch origin
git switch -c <prefiks>/<task-nomi> origin/main   # yangi ish
git switch <mavjud-branch>                        # boshlangan ishni davom ettirish
```

Bir vaqtda ikki task ustida ishlash kerak bo'lsa: birini commit qiling (WIP commit
ham bo'ladi), keyin `git switch`. `git stash` ishlatmang — stash stack repo bo'ylab
umumiy va boshqa sessiyaning ishini tortib olishi mumkin.

### Qoidalar

- Yangi worktree ochilmaydi — `git worktree add` taqiqlangan.
- Branch almashtirishdan oldin checkout toza bo'lishi kerak.
- Begona uncommitted o'zgarish ustidan `git switch` qilinmaydi: avval kimniki ekanini
  aniqlang (§4 dagi triage), keraksa Azurbekdan so'rang.
- Boshqa agentning branch'iga — uning ochiq PR branch'iga ham — push qilinmaydi.
  Tuzatish kerak bo'lsa o'z prefiksingizda branch ochib alohida PR yuboring.
- PR merge bo'lgach branch o'chiriladi: `git push origin --delete <branch>`, so'ng
  `git branch -d <branch>`. Maqsad — `main`dan boshqa branch faqat hozir ishlanayotgani bo'lsin.

Verify:

```bash
git worktree list        # faqat bitta qator chiqishi kerak
git branch -a
git status --short --branch
```

---

## 4. Sessiya boshlash

Har yangi sessiya ~5 daqiqalik bootstrap bilan boshlanadi:

```powershell
git status --short --branch
git log --oneline --decorate -8
git branch -a
```

Keyin:

1. `nuclear-program/marinebook.md` so'nggi 3-5 yozuvini o'qi
2. Arxitektura kerak bo'lsa `nuclear-program/project-context.md`'ni o'qi
3. Task tegadigan app'ning `models.py`, `urls.py`, `views.py`, `tests.py`'sini tekshir
4. Branch to'g'ri prefiksda ekanini tasdiqla
5. Checkout dirty bo'lsa — kim qilganini ajrat (quyidagi triage)

### Dirty checkout triage

`git status` dirty bo'lsa:

| Holat | Amal |
|---|---|
| O'z sessiyangdagi o'zgarish | davom et, lekin tez commit qil |
| User yoki boshqa agent o'zgarishi | tegma, faqat o'qib moslash |
| Task'ga bevosita xalaqit beradi | Azurbek'dan yo'l so'ra |
| Kimniki ekanini bilmaysan | `git diff` bilan o'rgan, **revert qilma** |

---

## 5. Task scope

Har task boshida aniqlanadi:

- Maqsad nima
- Qaysi app/fayllar tegadi
- Test qanday bo'ladi
- Data migration kerakmi
- Frontend bo'lsa qaysi sahifada browser verify kerak
- AI/provider bo'lsa external key yoki network kerakmi

### Feature admission gate

Har yangi yoki material o'zgargan capability, flow, business rule yoki product claim — shu jumladan mavjud view/service ichidagi o'zgarish, yangi app/model/sahifa/background job/provider/AI skill — boshlanishidan oldin quyidagilar yoziladi:

1. Qaysi learner outcome yoki owner workload muammosi yechiladi?
2. Bitta asosiy KPI nima?
3. Qaysi canonical state o'zgaradi va uning yagona service/policy/state machine'i qaysi?
4. Qaysi adapterlar bu serviceni faqat iste'mol qiladi?
5. Azurbekning haftalik operatsion yuki oshadimi yoki kamayadimi?
6. Feature flag/kill switch, failure va rollback yo'li bormi?
7. Launch uchun zarurmi, post-launch'mi yoki experimentmi?

Natija faqat `ADMIT — launch-critical`, `ADMIT — post-launch`, `EXPERIMENT — canonical state yozmaydi`, yoki `REJECT — duplicate/no measurable outcome/owner burden`. “Yangi skill”, “yangi sahifa” yoki “demo chiroyli bo'ladi” mustaqil admission sababi emas.

### Scope kattaligi

| Task turi | Tavsiya |
|---|---|
| CSS/UI polish | 1-5 fayl, browser verify |
| Bug fix | minimal fayl, regression test |
| Model change | migration + tests |
| AI behavior | engine/prompt/skill + messenger tests |
| RAG/memory | unit tests + management command smoke |
| Full feature | kichik bosqichlarga bo'linadi |

**Agent unrelated refactor qilmaydi.** "Ko'rib qoldim, shuni ham tuzatdim" faqat juda kichik va xavfsiz bo'lsa qabul qilinadi; aks holda alohida task.

---

## 6. Edit discipline

### Faylga tegishdan oldin

1. Faylni o'qi
2. Existing pattern'ni tushun
3. Fayl dirty bo'lsa, diff'ni ko'r
4. O'zgarishni minimal qil

### Taqiqlar

- ❌ Begona formatting churn
- ❌ Katta rename/move (task talab qilmasa)
- ❌ Generated/media/venv fayllarni commit qilish
- ❌ `.env`, secrets, API keys commit qilish
- ❌ `db.sqlite3`, `media/`, `staticfiles/` commit qilish

### Maxsus ehtiyot fayllar (multi-agent collision zonalari)

Bu fayllarga tegishda `git diff`'ni tez-tez ko'r:

- `messenger/models.py`, `messenger/tasks.py`, `messenger/consumers.py`, `messenger/views.py`
- `static/js/messenger-chat.js`, `static/css/messenger-shell.css`
- `courses/models.py`, `courses/views.py`
- `users/models.py`, `users/views.py`
- `core/settings.py`, `core/urls.py`
- `nuclear-program/*.md`

---

## 7. Test discipline

### Minimal test matrix

| O'zgarish | Minimum |
|---|---|
| Docs only | `git diff --check` |
| CSS/template only | browser verify + `python manage.py check` |
| Python view/form | `python manage.py check` + app tests |
| Model/migration | `python manage.py makemigrations --check` + app tests |
| Messenger | `python manage.py test messenger` |
| Users/dashboard/settings | `python manage.py test users` |
| Courses/lesson/exam | focused `courses` tests |
| AI skill/memory/RAG | `python manage.py test messenger` + focused tests |
| Checkout/subscription | `python manage.py test cohorts subscriptions` |
| Domain service/state machine | transition + permission + idempotency + invariant tests |
| Bir flow bir nechta adapterda | parity contract test + har adapter smoke |
| AI product behavior | functional test + versionlangan quality eval + failure/fallback gate |

Adapter testi parsing/serialization va canonical service chaqirilganini tekshiradi. Adapter ichida alohida enrollment/release/payment/progress hisobi topilsa, yangi test bilan dublikatni mustahkamlash emas, logikani control plane'ga qaytarish kerak.

### Test natijasini halol yozish

Final yoki marinebook'da:

- Qaysi command yugurdi
- Pass / fail soni
- Fail bo'lsa aynan qaysi test
- Fail task bilan bog'liqmi yoki pre-existing'mi

**"Testlar o'tdi" deb umumiy aytma — command'ni yoz.**

### Testni skip qilish

Faqat shu hollarda mumkin:

- Testning o'zi noto'g'ri yoki eskirganligi isbotlangan
- Azurbek rozilik bergan
- Marinebook'da sabab yozilgan

**Tezroq tugatish uchun testni susaytirish mumkin emas.**

---

## 8. Commit discipline

### Qachon commit

Commit qil:

- Bitta logical feature tugaganda
- Bug fix + regression test o'tganda
- Migration + model change stable bo'lganda
- Session yopilishidan oldin
- 30 daqiqadan ortiq ish yig'ilib qolsa va holat testdan o'tsa

Commit qilma:

- Test'dan o'tmagan WIP'ni (Azurbek "WIP commit" demasa)
- Secret yoki local generated fayllarni
- Boshqa agent o'zgarishini o'zingniki bilan aralashtirib

### Commit format

```text
<type>(<scope>): <short summary>

<optional body>

Co-Authored-By: <Agent Name> <agent-noreply-email>
```

**Types:** `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `style`, `perf`

**Misollar:**

```text
feat(messenger): add AI room pinning
fix(courses): preserve lesson cohort query
test(ai): cover medium web search routing
docs(agent): add branch workflow playbook
```

### Commit identity

Repo-local `git config user.name` **`Codex`** ga o'rnatilgan, ya'ni hech narsa qilmasangiz
commitingiz Codex nomida ko'rinadi. Bitta checkout tartibida (§3) bu ayniqsa chalg'itadi —
tarixda kim nima qilganini ajratib bo'lmaydi. 2026-09-10 da Antigravity yozgan uchta commit
aynan shu sababdan `Codex` muallifligida turibdi.

Shuning uchun:

- `Co-Authored-By:` trailer **har commitda majburiy** — u ishni kim qilganini aytadi.
- Codex bo'lmasangiz, identityni bir martalik bering:

```bash
git -c user.name="<Agent>" -c user.email="<agent-noreply>" commit -F - <<'MSG'
...
MSG
```

- `git config` ni doimiy o'zgartirish Azurbekning qarori; agent o'zi jimgina qilmaydi.

---

## 9. Push, PR, merge

### Push

```powershell
git push -u origin codex/<task-name>
```

**Push faqat o'z branch'ingizga.**

### Force push

`--force-with-lease` faqat:

- O'z branch'ingiz
- Boshqa agent tegmagan
- Rebase/amend sababli zarur
- Azurbek yoki task context bunga ruxsat bergan

**`--force` (bez lease) hech qachon ishlatilmaydi.**

### Merge to main

**`main` 2026-08-15 dan buyon branch protection ostida.** Bu qoida endi hujjatda emas, serverda turadi:

| Amal | Holat |
|---|---|
| `git push origin main` | ❌ rad etiladi — **Azurbek uchun ham** (`enforce_admins: true`) |
| force-push `main` ga | ❌ rad etiladi |
| `main` ni o'chirish | ❌ rad etiladi |
| PR merge, uchala check yashil | ✅ yagona yo'l |

Required checklar (CI job nomlari bilan bir xil bo'lishi shart):

- `Checks va to'liq test suite (SQLite)`
- `PostgreSQL+pgvector va Valkey smoke`
- `Sir va bog'liqlik zaifligi skani`

`strict: true` — PR merge oldidan branch `main` bilan yangilangan bo'lishi kerak, ya'ni checklar aynan merge bo'ladigan holatda yugiradi.

Shoshilinch holatda gate'ni owner vaqtincha ochadi va **darhol yopadi**:

```bash
gh api -X DELETE repos/azurebek/azurelms/branches/main/protection/enforce_admins
```

```bash
gh api -X POST repos/azurebek/azurelms/branches/main/protection/enforce_admins
```

CI job nomini o'zgartirsangiz, protection ham o'sha commitda yangilanishi shart — aks holda GitHub hech qachon kelmaydigan checkni kutadi va har qanday PR abadiy bloklanadi.

### PR tayyorlash va merge vakolati

**Owner workflow qarori — 2026-09-03:** agent o'z prefiksidagi PR'ni quyidagi gate'lar bajarilgach alohida ruxsat so'ramasdan merge qiladi:

- Uchala required check yashil
- Review izohlari resolve qilingan
- Branch `main` bilan yangilangan va conflict yo'q
- Destructive migration, data-loss yoki secret/security anomaly yo'q

Agent `--admin` ishlatmaydi, branch protection yoki required checkni bypass qilmaydi. Conflict, failed/missing check yoki yuqoridagi xavf signallarida merge qilmaydi va Azurbekka xabar beradi.

**Faqat o'z PR'ingiz.** Boshqa agentning PR'ini merge qilish taqiqlanadi — uchala check yashil bo'lsa ham.
Uning branch'iga, shu jumladan ochiq PR branch'iga, commit yoki push qilish ham taqiqlanadi.

> **2026-09-10 hodisasi.** Antigravity Codex review botining PR #94 dagi ikki topilmasini tuzatib,
> commitlarni to'g'ridan-to'g'ri `codex/classbook-live-orchestrator` ga push qildi va PR #94 ni o'zi
> merge qildi. Kod to'g'ri edi va CI yashil edi, lekin: (a) Codex ayni paytda o'z ishida xuddi shu
> PostgreSQL test muammosini boshqa yo'l bilan (`TransactionTestCase`) tuzatayotgan edi — ikkala tomon
> bir-biridan bexabar qoldi; (b) merge qilingan PR egasi o'z ishining yakuniy holatini ko'rmay qoldi.
> To'g'ri yo'l: `antigravity/<task>` branchida alohida PR ochib, uni Codex PR'idan keyin merge qilish.

#### Merge qo'lda va kutib bajariladi (owner qarori — 2026-09-03)

Ruxsat **usulni ham belgilaydi.** Auto-merge ishlatilmaydi: agent checklar tugashini o'zi kutadi, holatni o'zi ko'radi va o'zi merge qiladi. Tartib aynan shunday:

```bash
gh pr checks <N> --watch                  # uchala check tugashini kutasiz
gh pr view <N> --json mergeStateStatus    # CLEAN bo'lishi kerak
gh pr merge <N> --merge                   # merge commit — repo tarixi shunday
git fetch origin                          # `origin/main` yangilanadi
```

Lokal `main` ni ham yangilash uchun: `git switch main && git pull --ff-only origin main`. Bitta checkout tartibida (§3) `main` hech qayerda band emas, shuning uchun bu buyruq har doim ishlaydi. So'ng merge bo'lgan branch o'chiriladi: `git push origin --delete <branch>` va `git branch -d <branch>`.

Merge'dan oldin review thread'lar ham tekshiriladi. Avtomatik reviewer (`chatgpt-codex-connector`) izoh qoldirgan bo'lsa, topilmani halol baholang: rost bo'lsa tuzating, keyin thread'ga javob yozib resolve qiling. Hal qilinmagan topilmani "tozalash uchun" resolve qilish mumkin emas.

**Bular ruxsatga kirmaydi:**

| Amal | Nega yo'q |
|---|---|
| `gh pr merge --auto` | Merge hech kim qaramay turganda, kutilmagan paytda bajariladi |
| `allow_auto_merge` va boshqa **repository sozlamasi** | Doimiy va **hamma uchun**; bitta PR uchun berilgan ruxsat repo konfiguratsiyasini o'zgartirishga yetmaydi |
| Branch protection tahriri, `enforce_admins` o'chirish | Bu owner'ning shoshilinch kaliti, agentniki emas |
| Admin bypass yoki force merge | Gate'ning butun ma'nosini yo'q qiladi |
| Boshqa agentning PR'ini merge qilish | Har kim o'z ishini yakunlaydi |

CI **infratuzilma** sababli qizil bo'lsa (masalan `pip-audit` tarmoq uzilishi) — gate'ni o'chirmang yoki chetlab o'tmang. Yo qayta yugurtiring, yo workflow'ni chidamli qiling, lekin **fail-closed** saqlang.

Merge oldidan agent tayyorlaydi:

- Branch push'lanagan
- Test status (aniq command + natija)
- Summary (3-5 jumla)
- Known risks
- Migration kerak bo'lsa aniq yozuv
- Screenshots/browser verify kerak bo'lsa dalil
- Feature admission statusi va asosiy outcome KPI
- Canonical service hamda tegilgan adapterlar ro'yxati
- Duplicate business logic yo'qligi
- Feature'ni disable/rollback qilish yo'li
- Product claim o'zgargan bo'lsa, uni tasdiqlovchi evidence

---

## 10. Marinebook qoidasi

`nuclear-program/marinebook.md` major sessionlar kundaligi.

### Qachon yoziladi

✅ Yoz:
- Major feature tugasa
- Architecture o'zgarsa
- Branch merge/push qilinsa
- Muhim qaror yoki rollback bo'lsa
- Boshqa agent davom ettirishi kerak bo'lsa

❌ Yozish shart emas:
- Juda kichik typo/CSS fix
- Faqat local exploration
- Test run xolos

### Format

Yangi yozuv **eng tepaga** (teskari xronologik):

```markdown
## 2026-MM-DD [Agent_nomi]: Qisqa sarlavha

2-4 jumla: nima qilindi, nima uchun muhim, nimalarga tegildi.

- Branch: `codex/task-name`
- Commitlar: `abc1234`, `def5678`
- Test holati: `python manage.py test messenger` pass (68/68)
- Davom etilishi kerak: yo'q / aniq keyingi qadam
```

### Marinebook'da yolg'on yo'q

- ❌ Commit hali yo'q bo'lsa "keyin qo'shiladi" deb yozma — commit'dan keyin yoz
- ❌ Test yugurmagan bo'lsa "yashil" deb yozma — "yugurilmadi" deb yoz
- ❌ `--amend` yoki rebase'dan **oldingi** hashni yozma: amend hashni o'zgartiradi. Yozishdan oldin
  `git log --oneline -1` bilan tasdiqla — 2026-09-10 da uchta yozuv shu sababdan noto'g'ri hash bilan `main` ga kirdi
- ❌ Pre-existing failure'ni o'z ishingga aybdor qilma — alohida ayt

---

## 11. Project-context.md yangilash

`project-context.md` major architecture wiki.

✅ Yangilanadi:
- Yangi app yoki katta modul
- AI engine/memory/RAG/skills contract o'zgarsa
- URL yoki WebSocket/API contract o'zgarsa
- Model relationships o'zgarsa
- Deployment/env o'zgarsa
- Major frontend shell migration bo'lsa

❌ Yangilanmaydi:
- Oddiy CSS polish
- Copy text o'zgarishi
- Bitta bug fix
- Faqat test qo'shish

**Context faylga faqat verified ma'lumot yoziladi.** Taxmin yoki bir martalik kuzatuv → `marinebook.md`'ga.

---

## 12. Long session signallari

Quyidagi belgilar chiqsa, agent session'ni yopishga tayyorlaydi:

- 50+ turn bo'ldi
- Bir nechta unrelated task aralashdi
- 20+ fayl dirty bo'lib qoldi
- Agent nima o'zgartirganini og'zaki qayta ayta olmayapti
- Test/debug loop 3 marotabadan ko'p takrorlandi
- **User "nima qilayotgandik?" deb so'radi** (eng kuchli signal)

### Session yopish protokoli

1. `git status --short`
2. O'zgarishlarni logical guruhlarga ajrat
3. Test/check yugurtir
4. Commit qil yoki WIP holatini aniq yoz
5. Marinebook yangila (major bo'lsa)
6. User'ga qisqa status ber

---

## 13. Conflict protocol

Conflict chiqsa:

1. Panika qilma
2. `git status` va conflicted fayllarni ko'r
3. Har conflict uchun:
   - Current branch nima qilgan
   - Incoming nima qilgan
   - Ikkalasining niyati nima
   - Test qanday tasdiqlaydi
4. Begona feature logikasini olib tashlama
5. Hal bo'lgach focused test yugurtir
6. Marinebook'da conflict haqida yoz

### Cross-agent feature collision

Ikki agent bir feature ustida ishlaganini sezsang:

- **STOP**
- Ikkala branch holatini yoz
- Azurbek'dan qaysi yo'l tanlanishini so'ra

---

## 14. Frontend verify

Frontend o'zgarishida agent quyidagilarni qiladi:

- Relevant sahifani browser'da ochadi
- Desktop va kerak bo'lsa mobile width tekshiradi
- Text overflow, overlap, scrollbar, hover/active state tekshiradi
- JS console error bo'lsa ko'radi
- Dark/light theme ta'sirini hisobga oladi

**Messenger/course/lesson/dashboard kabi interactive sahifalarda faqat HTML render yetarli emas** — kamida asosiy user action tekshiriladi.

---

## 15. AI outcome va safety gate

AI'ga tegadigan o'zgarishda:

- Har feature learning outcome yoki teacher minutes saved tezisiga ega bo'ladi; prompt/skill qo'shilishi feature completion hisoblanmaydi
- “Adaptiv”, “zaif joyni biladi”, “speaking coach” yoki “tekshiruvni yengillashtiradi” claim'i uchun structured state, eval va real workflow evidence kerak
- AI output canonical state'ni faqat deterministic service yoki human approval orqali o'zgartiradi
- Provider system instructions haqiqiy system-role'da, learner/RAG/PDF/memory esa untrusted data sifatida uzatiladi
- Prompt injection va `<SAVE_MEMORY>` safety tekshiriladi
- Memory on/off behavior saqlanadi
- RAG access user enrollment scope bilan cheklanadi
- Free tier'da API web grounding hard-off; effort qoidalari faqat non-free, explicit admitted grounding rejimida qo'llanadi
- `AIResponseRun.metadata` telemetry buzilmaydi
- Model/skill/token/latency operatsion metric; pedagogik outcome emas
- Marketing copy runtime capability va fresh eval dalilidan oldinga o'tmaydi
- Provider adapterida learner progress, access, pricing yoki grading logikasi bo'lmaydi

**AI behavior o'zgarsa functional test, teacher-authored/versionlangan quality eval va failure/fallback tekshiruvi yangilanadi.** Premium capability release gate'dan o'tmasa feature flag yopiq qoladi.

---

## 16. Data migration

Model o'zgarishi:

1. Migration yarat
2. Migration'ni o'qi
3. Data loss bor-yo'qligini tekshir
4. Default/null/backfill masalasini hal qil
5. Test yoki `manage.py check` yugurtir

### Danger signs

- Field rename auto-detected emas
- `RemoveField`
- Non-null field without default
- Large data migration
- Index/constraint on large table

Bunday hollarda Azurbek'ka aniq risk yoziladi.

---

## 17. Secrets va private data

**Hech qachon commit qilinmaydi:**

- `.env`, `.env.local`
- API keys (Gemini, Telegram, OpenAI, ...)
- DB password
- Redis/Valkey URL bilan creds
- User personal data export
- `db.sqlite3`
- Media uploads

**Sensitive qiymat ko'rinsa:**

- Final'da plaintext qaytarilmaydi
- Maskalanadi (`sk-***`, `ghp_***`)
- Kerak bo'lsa rotate qilish tavsiya qilinadi

---

## 18. Per-agent notes

### Codex

- Branch prefiks: `codex/`
- Kuchli tomon: repo bo'ylab refactor, tests, CLI, browser verify
- Ko'p faylga tegsa tez-tez `git diff --stat` tekshiradi
- Manual edit uchun patch/diff discipline saqlaydi

### Claude Code

- Branch prefiks: `claude/`
- Kuchli tomon: refactor, dokumentatsiya, structured analysis, tests
- Long context'da session'ni erta yopish foydali
- Imzo: `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>` (model yangilansa shu qator ham yangilanadi)

### Antigravity

- Branch prefiks: `antigravity/`
- Kuchli tomon: frontend/UI exploration
- **Har 10-15 daqiqada kichik commit/checkpoint** tavsiya etiladi
- Katta uncommitted UI experimentlarni main branch'da saqlama (bugun bo'lgan ish — 3000+ qator yo'qoldi)
- **2026-09-10:** boshqa agentning branch'iga push qilma va uning PR'ini merge qilma (§9); tuzatishing bo'lsa `antigravity/<task>` da alohida PR och
- Commit hash'ini marinebook'ga yozishdan oldin `--amend` qilib bo'lgan bo'l — amend hashni o'zgartiradi (§10)

### Human / Azurbek

- Integration qarorini beradi
- Scope va xavfli integratsiya qarorini beradi; odatiy yashil agent PR'lari uchun 2026-09-03 standing merge ruxsati amal qiladi (§9)
- Agentlar conflict yoki duplicated effort bo'lsa final tanlovni qiladi

---

## 19. Final response qoidasi

Agent ishni tugatganda user'ga qisqa aytadi:

- Nima o'zgardi
- Qaysi muhim fayllar
- Test/check natijasi (aniq command bilan)
- Nima qilinmadi yoki risk
- Commit/push qilingan bo'lsa hash/branch

**Uzun diff'ni final'ga ko'chirma.** Kerak bo'lsa clickable file path beradi.

---

## 20. Emergency stop

Darhol to'xtash kerak:

- Branch noto'g'ri ekanini sezsa
- `main` dirty bo'lsa va task feature bo'lsa
- Destructive command kerak bo'lsa (bu user tomonidan tasdiqlanishi kerak)
- Migration data loss ehtimoli bo'lsa
- Secret commit bo'lganini sezsa
- User'ning o'zgarishi ustidan yozish xavfi bo'lsa
- **Test failure sababini tushunmay turib "fix" qilish loop'i boshlangan bo'lsa**

To'xtaganda agent user'ga:

1. Nima xavf borligini
2. Hozirgi branch/status'ni
3. Xavfsiz variantlarni
4. Tavsiya qilingan keyingi qadamni aytadi

---

## 21. Bu faylni yangilash

Bu hujjat ham living document.

- Faqat real muammo yoki yangi workflow paydo bo'lsa yangilanadi
- Qoida qisqa va actionable bo'lsin
- Eski qoidani o'chirishdan ko'ra, sababi bilan almashtir
- Major o'zgarish marinebook'da qayd etilsin

---

*Yangilanish: 2026-07-22 (solo-owner control plane, feature admission va AI outcome gate qo'shildi).*
