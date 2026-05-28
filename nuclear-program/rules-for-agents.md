# AzureLMS — Agentlar uchun qoidalar

Bu hujjat **Claude Code**, **Codex**, **Antigravity** (yoki boshqa AI agent) bir repo ustida ishlaganda to'qnashuvni minimumga tushirish uchun. Har agent sessiya boshlashidan oldin shuni o'qiydi.

Maqsad: 3+ ta agent bir vaqtda ishlasin, lekin bir-biriga aralashmasin, bir-birining ishini buzmasin, takroriy kontekst sarflashga vaqt ketmasin.

---

## 0. Eslab qolinishi kerak bo'lgan 5 ta qoida

Agar faqat 5 ta narsani eslab qolish kerak bo'lsa:

1. `main` integratsiya trunk'i. Unda faqat Azurbek ruxsati bilan ishlanadi.
2. Har agent o'z prefiks branch'ida ishlaydi: `codex/`, `claude/`, `antigravity/`.
3. Har agent imkon qadar o'z worktree papkasida ishlaydi.
4. Bitta task tugasa: **test → commit → marinebook yozuvi**.
5. **Begona uncommitted o'zgarishni revert, delete yoki overwrite qilma.**

---

## 1. Source of truth

Sessiya boshlanganda quyidagilar source of truth hisoblanadi:

| Tartib | Fayl / buyruq | Nima uchun |
|---|---|---|
| 1 | `git status --short --branch` | qaysi branch va dirty state |
| 2 | `git log --oneline --decorate -8` | so'nggi ishlar |
| 3 | `git worktree list` | papka/branch ownership |
| 4 | `nuclear-program/marinebook.md` (so'nggi 3-5 yozuv) | so'nggi major sessionlar |
| 5 | `nuclear-program/project-context.md` | loyiha arxitekturasi |
| 6 | task tegadigan app fayllari (model/view/url/test) | haqiqiy kod source of truth |

**Hech bir agent faqat eski chat xotirasi asosida qaror qilmaydi.** Hozirgi repo holatini tekshiradi.

---

## 2. Branch ownership

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
- ❌ `main`'ga bevosita commit/push qilma (Azurbek aniq aytmasa)
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

`<agent>/work` faqat **uzoq muddatli worktree base branch** sifatida ishlatilsa bo'ladi. Har feature uchun alohida branch ochiladi.

---

## 3. Worktree setup

Tavsiya etilgan papkalar:

```text
C:\Projects\azurelms                main / integration
C:\Projects\azurelms-codex          Codex worktree
C:\Projects\azurelms-claude         Claude worktree
C:\Projects\azurelms-antigravity    Antigravity worktree
```

**Branchlar hali mavjud bo'lmasa:**

```powershell
cd C:\Projects\azurelms
git worktree add -b codex/work ../azurelms-codex main
git worktree add -b claude/work ../azurelms-claude main
git worktree add -b antigravity/work ../azurelms-antigravity main
```

**Branchlar mavjud bo'lsa:**

```powershell
git worktree add ../azurelms-codex codex/work
```

### Worktree qoidalari

- Har IDE o'z worktree papkasini ochadi
- Agent boshqa agent papkasiga fayl yozmaydi
- Worktree o'chirishdan oldin `git status` tekshiriladi
- Worktree branch'ini almashtirishdan oldin dirty state hal qilinadi

Verify:

```powershell
git worktree list
git status --short --branch
```

---

## 4. Sessiya boshlash

Har yangi sessiya ~5 daqiqalik bootstrap bilan boshlanadi:

```powershell
git status --short --branch
git log --oneline --decorate -8
git worktree list
```

Keyin:

1. `nuclear-program/marinebook.md` so'nggi 3-5 yozuvini o'qi
2. Arxitektura kerak bo'lsa `nuclear-program/project-context.md`'ni o'qi
3. Task tegadigan app'ning `models.py`, `urls.py`, `views.py`, `tests.py`'sini tekshir
4. Branch to'g'ri prefiksda ekanini tasdiqla
5. Dirty worktree bo'lsa — kim qilganini ajrat (quyidagi triage)

### Dirty worktree triage

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

Co-Authored-By: <Agent Name> <noreply@anthropic.com>
```

**Types:** `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `style`, `perf`

**Misollar:**

```text
feat(messenger): add AI room pinning
fix(courses): preserve lesson cohort query
test(ai): cover medium web search routing
docs(agent): add worktree playbook
```

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

Merge'ni **Azurbek** hal qiladi. Agent tayyorlaydi:

- Branch push'lanagan
- Test status (aniq command + natija)
- Summary (3-5 jumla)
- Known risks
- Migration kerak bo'lsa aniq yozuv
- Screenshots/browser verify kerak bo'lsa dalil

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

## 15. AI feature qoidasi

AI'ga tegadigan o'zgarishda:

- Prompt injection va `<SAVE_MEMORY>` safety tekshiriladi
- Memory on/off behavior saqlanadi
- RAG access user enrollment scope bilan cheklanadi
- Web search faqat effort qoidalariga mos yoqiladi
- `AIResponseRun.metadata` telemetry buzilmaydi
- UI skill/model/tone settings bilan mos ishlaydi

**AI behavior o'zgarsa kamida bitta test qo'shiladi yoki mavjud test yangilanadi.**

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
- Imzo: `Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>`

### Antigravity

- Branch prefiks: `antigravity/`
- Kuchli tomon: frontend/UI exploration
- **Har 10-15 daqiqada kichik commit/checkpoint** tavsiya etiladi
- Katta uncommitted UI experimentlarni main branch'da saqlama (bugun bo'lgan ish — 3000+ qator yo'qoldi)

### Human / Azurbek

- Integration qarorini beradi
- Main merge/push ruxsatini beradi
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

*Yangilanish: 2026-05-28 (Codex'ning alternative versiyasi bilan birlashtirilgan yakuniy variant).*
