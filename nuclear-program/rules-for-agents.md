# AzureLMS — agentlar uchun qoidalar

Bu hujjat **Claude Code**, **Codex**, **Antigravity** (yoki boshqa AI IDE) bilan parallel ishlash uchun. Har agent sessiya boshlashidan oldin shuni o'qiydi.

Maqsad: 3 ta agent bir vaqtda ishlasin, lekin **bir-biriga aralashmasin va bir-birining ishini buzmasin**.

---

## 1. Branch konvensiyasi (qattiq qoida)

Har agent **o'z prefiks bilan** branch ochadi:

| Agent | Prefiks | Misol |
|---|---|---|
| Claude Code | `claude/` | `claude/web-search-skill`, `claude/dashboard-fix` |
| Codex | `codex/` | `codex/messenger-quality`, `codex/exam-flow` |
| Antigravity | `antigravity/` | `antigravity/telegram-bot`, `antigravity/ai-widget` |
| Inson (Azurbek) | `feature/` yoki to'g'ridan-to'g'ri `main` | `feature/payment-update` |

**Hech qachon:**
- ❌ Boshqa agentning branch'iga commit qilmaslik
- ❌ Boshqa agentning branch'ini merge qilmaslik (faqat Azurbek qiladi)
- ❌ `main` ga to'g'ridan-to'g'ri commit qilmaslik (Azurbek ruxsat bersa istisno)
- ❌ Boshqa agent ishlayotgan fayllarga tegmaslik (bilmaslik kerak bo'lsa, avval `git log` orqali tekshirib ko'rish kim oxirgi tegan)

**Doim:**
- ✅ O'z prefiks bilan branch och: `git checkout -b claude/feature-name main`
- ✅ Bittadan feature/fix uchun bitta branch
- ✅ Branch nomi qisqa va aniq: `claude/fix-pricing-grid`, `codex/add-quiz-timer`

---

## 2. Worktree sozlamasi (ixtiyoriy lekin tavsiya etiladi)

Disk papkalarining ham ajratilishi to'qnashuvni **fizik jihatdan imkonsiz** qiladi. Sozlash:

```bash
# Asosiy papka (Azurbek + integratsiya)
cd C:\Projects\azurelms      # main branch shu yerda

# Har agent uchun alohida worktree
git worktree add ../azurelms-claude       claude/work
git worktree add ../azurelms-codex        codex/work
git worktree add ../azurelms-antigravity  antigravity/work
```

Endi:
- Claude IDE → `C:\Projects\azurelms-claude\` ochsa, `claude/work` branchida ishlaydi
- Codex → `C:\Projects\azurelms-codex\` → `codex/work`
- Antigravity → `C:\Projects\azurelms-antigravity\` → `antigravity/work`

Har papka bitta git repo'siga ulangan (`.git/` `C:\Projects\azurelms\` da bir marta), lekin har biri o'z working tree'siga ega.

**Yangi feature boshlash:**
```bash
cd C:\Projects\azurelms-claude
git checkout -b claude/<new-feature> main
git pull origin main   # main eng so'nggi bo'lsin
```

---

## 3. Sessiya boshlash protokoli

Har **yangi chat sessiya** boshlanganda agent quyidagi tartibda kontekstga kiradi:

1. **`nuclear-program/project-context.md`** o'qish — loyihaning to'liq tushunish (5-10 daqiqa)
2. **`nuclear-program/marinebook.md`** ning so'nggi 3-5 yozuvini o'qish — yaqinda nima bo'lganini bilish (2-3 daqiqa)
3. **`git status` va `git log --oneline -10`** ishga tushirish — joriy holatni ko'rish
4. **`git branch -a`** — qaysi branch'da turganini tasdiqlash. Agar `main` da bo'lsa — yangi feature uchun darhol o'z prefiks bilan branch ochish (1-bo'limga qarang)

Bu 4 ta qadam ~10 daqiqa oladi va **5000-10000 token sarflashning oldini oladi** (avval har sessiya zerikarli exploration bilan boshlanardi).

---

## 4. Commit discipline

### 4.1 Commit hajmi

**Bitta commit = bitta logical o'zgarish.** Stack qilmaslik. Misol:
- ❌ "feat: lots of stuff" (10 ta o'zaro bog'liqsiz feature)
- ✅ "feat(messenger): add reply threading"
- ✅ "fix(blog): handle None sender in reply preview"
- ✅ "refactor(ai): extract mention detection to separate module"

### 4.2 Commit xabari formati

```
<type>(<scope>): <short summary>

<optional details>

Co-Authored-By: <Agent Name> <noreply@anthropic.com>
```

`type` lar: `feat`, `fix`, `refactor`, `chore`, `docs`, `test`, `perf`, `style`
`scope` (ixtiyoriy): `messenger`, `ai-agent`, `ai-memory`, `ui`, `blog`, `users`, va h.k.

### 4.3 Commit oraliqlari

- Yangi fayl yaratdingizmi → testlaringiz o'tdimi → **commit qiling**
- Yangi class/funksiya — **commit**
- Bug fix — **commit**
- 30+ minut ish to'planib qoldi va commit qilinmagan? **Stop. Commit qiling.** Stack — keyingi muammoning ildizi.

---

## 5. Test discipline

### 5.1 Commit oldidan

- `python manage.py check` — minimum
- O'zgartirilgan app testlari: `python manage.py test <app>` (masalan `messenger`, `users`, `courses`)
- Yangi feature qo'shganda — yangi test ham yozish (bitta-ikkita)

### 5.2 Branch'ni main'ga qo'shishdan oldin

- **Hammasini** yugurtirish: `python manage.py test`
- Hammasi yashil bo'lishi shart
- Sinmagan testlari bo'lsa — ular bekor qilinmasligi kerak, ulardan biri tuzatilishi yoki muammo qaytarilishi kerak

### 5.3 Test xafa qilish (skip / xfail) — istisno

Faqat: testning o'zi noto'g'ri yozilgan bo'lsa yoki sinadigan feature hali yo'q bo'lsa. **Hech qachon "tezroq merge qilish uchun"** test'ni skip qilmaslik.

---

## 6. Push va merge protokoli

### 6.1 Push

- O'z branch'ingizga doim push qilish: `git push origin <your-branch>`
- `main` ga **to'g'ridan-to'g'ri push qilmaslik** — faqat Azurbek qiladi
- Force-push (`--force`, `--force-with-lease`) — faqat o'z branch'ingizga, va boshqa agent shu branch'ga tegmagan bo'lsa

### 6.2 Merge to main

Bu **inson tomonidan** (Azurbek tomonidan) qilinadi:

1. Agent o'z branch'ida ishni tugatadi, push qiladi
2. GitHub'da Pull Request ochadi (yoki Azurbek lokal'da merge qiladi)
3. Azurbek tasdiqlaydi, merge qiladi (preferensial: **squash merge** yoki **fast-forward**)
4. Branch o'chiriladi: `git branch -d claude/feature && git push origin --delete claude/feature`

### 6.3 Main'dan yangilanish olish

Boshqa agent ishi main'ga qo'shildi → siz ham o'z branch'ingizni yangilang:

```bash
git checkout claude/your-branch
git fetch origin
git rebase origin/main   # yoki: git merge origin/main
```

Konflikt chiqsa — toza hal qilish, keyin commit.

---

## 7. Agentlar orasidagi etiketka

### 7.1 Qaerda ishlasangiz, shu yerda turing

- Boshqa agentning branch'iga checkout qilmaslik
- Boshqa agentning worktree'siga (papkasiga) fayl yozmaslik
- Boshqa agent ochib qo'ygan PR'ni yopib qo'ymaslik

### 7.2 Shared fayllar (`messenger/tests.py`, `messenger/models.py`...)

Ba'zi fayllar barchaga teng. Ularga o'zgartirish kiritganda:

- **Avval** main'dan pull oling
- **Faqat o'z qism**ingizni o'zgartiring (boshqa agent o'sha faylga teggan bo'lsa, konflikt chiqishi mumkin)
- Test yugurting → konflikt chiqsa, hal qiling
- Commit qilganda — `feat(messenger): X bo'limini qo'shish` deb aniq belgilang

### 7.3 Tortishuv chiqsa

- Ikki agent bir paytda bitta feature ustida ishlaganini sezsangiz → STOP
- Azurbek'ga xabar qiling (xabar yo'l: sessiya tugatishda `marinebook.md` ga yozib qoldirish)
- Bittasini saqlash, ikkinchisini bekor qilish — Azurbek tanlaydi

---

## 8. Qachon `project-context.md` va `marinebook.md` ni yangilash

### 8.1 `project-context.md`

**Yangilanadi:**
- Yangi major feature qo'shilganda (skill, API, model, oqim)
- Major refactor — modullar qayta tashkil qilinganda
- Tech stack o'zgarsa (yangi kutubxona, yangi DB)
- URL nomlari, environment o'zgarsa
- Foydalanuvchi sozlamalari (`CustomUser` choices) qo'shilsa

**Yangilamaydi:**
- Kichik bug fix
- CSS polish
- Faqat test qo'shildi
- Vaqtinchalik WIP

### 8.2 `marinebook.md`

**Doim yangilanadi.** Har sessiya yakunida (yoki har major commitdan keyin) agent o'z yozuvini qo'shadi. Format quyida.

---

## 9. Sessiya yakunlash protokoli

Sessiya tugashidan oldin (yoki uzayib ketganda):

1. **Hammasini commit qiling** — uncommitted ish qoldirmaslik
2. **Push qiling** — o'z branch'ingizga
3. **Testlar yugurtirildi** — yashil bo'lsin
4. **`marinebook.md`** ga yozuv qo'shing (eng yuqoriga, teskari xronologik):
   ```markdown
   ## 2026-MM-DD [Agent nomi]: Qisqa sarlavha
   
   Nima qilindi, qisqa izoh (2-4 jumla).
   
   - Branch: `claude/feature-name`
   - Commitlar: abc1234, def5678
   - Test holati: 91/91 yashil
   - Davom etilishi kerak bo'lgan ishlar: [agar bor bo'lsa]
   ```
5. **Major feature bo'lsa** `project-context.md` ga qism qo'shing yoki yangilang
6. Chat sessiyani yoping. Yangi chat yangi bootstrap'dan boshlanadi (bu 3-bo'limdagi qisqa protokol).

---

## 10. Anti-pattern signallari

Quyidagilarni sezsangiz — **darhol to'xtang va commit qiling**:

- "30+ fayl uncommitted" — kelajakdagi muammo
- "Hech bir muammo tugamayapti" — yarim-tayyor narsalarni stack qilyapsiz
- "Adashib ketdim, qaysi branch'da turganimni bilmayman" — chalkash worktree
- "Bu boshqa agent ishlayotgan fayl shekilli" — STOP, tasdiqlang
- "Bu menga begona kod kabi" — main'dan yangilanish oling, kontekstni qayta o'qing

Sessiya uzayib ketsa (`>50 turn`) — yangi chat ochish kerak. Yangi chat 30 sekundda bootstrap qiladi (3-bo'lim).

---

## 11. Per-agent maxsus qoidalar

### Claude Code

- Tools: kuchli **edit-based** ish, fayl-fayl o'qish va o'zgartirish
- Imzo: `Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>`
- Sessiya uzunligi: 50-100 turn, undan keyin yangi chat
- Kuchli tomon: refactoring, test yozish, debug, dokumentatsiya

### Codex

- Tools: **CLI + agent** ko'proq, autonom code generation
- Branch prefiksi: `codex/`
- Tarixiy: `codex/playground-next` branch ishlatilgan (endi main'ga qo'shilgan)
- Kuchli tomon: katta refactor, butun feature qurish

### Antigravity

- Google IDE
- Branch prefiksi: `antigravity/`
- Tarixiy: `antigravity/dev` ishlatilgan (o'chirilgan — uncommitted ish yo'qoldi)
- **DARS:** Antigravity bilan ishlaganda har 10-15 daqiqada commit qilish, stack yo'q
- Kuchli tomon: UI/UX, frontend, design implementation

---

## 12. Bu hujjatni o'zi yangilash

`rules-for-agents.md` ham yashash hujjati. O'zgartirish kerak bo'lsa:

1. Azurbek tasdiqlaydi
2. Yangi qoida qo'shilsa — yangi raqamli bo'lim
3. Eski qoida olib tashlansa — sababi `marinebook.md` ga yoziladi
4. Versiya nomi yo'q, lekin commit history saqlanadi

---

*Yangilanish: 2026-05-28 (nuclear-program tizimi yaratildi)*
