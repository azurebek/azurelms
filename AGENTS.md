# AzureLMS — Agent Bootstrap

O'zbek tilida turk tili o'rgatuvchi Django LMS. AI tutor, RAG, real-time messenger, Telegram bot, subscription va exam oqimlari bilan. Asosiy branch: `main`.

Bu fayl har AI agent (Claude Code / Codex / Antigravity / boshqa) sessiya boshlashidan oldin **eng birinchi o'qishi kerak bo'lgan** kirish. To'liq qoidalar va loyiha wiki'si `nuclear-program/` ichida.

---

## O'zgartirish kiritishdan oldin

1. `nuclear-program/rules-for-agents.md` — to'liq ish qoidalari (branch ownership, worktree setup, test/commit discipline, conflict protocol, emergency stop)
2. `nuclear-program/marinebook.md` — so'nggi 3-5 yozuvni o'qing (boshqa agentlar nima qildi)
3. `nuclear-program/project-context.md` — arxitektura kerak bo'lganda (11 domain app, AI agent qatlami, URLs, env, data model)
4. Quyidagi buyruqlarni yugurting:

```bash
git status --short --branch
git log --oneline --decorate -8
git worktree list
```

5. Branch siz uchun mo'ljallangan prefiks ekanini tasdiqlang (pastdagi jadval).

---

## 5 ta asosiy qoida

1. **`main`** integratsiya trunk'i. Unga **faqat Azurbek** ruxsati bilan ishlanadi.
2. Har agent **o'z prefiks branch'ida** ishlaydi: `codex/`, `claude/`, `antigravity/`.
3. Har agent imkon qadar **o'z worktree papkasi**da ishlaydi (`azurelms-codex/`, `azurelms-claude/`, ...).
4. Bitta task tugasa: **test → commit → marinebook yozuvi**.
5. **Begona uncommitted o'zgarishni** revert, delete yoki overwrite **qilmang**.

---

## Branch ownership

| Agent | Prefiks | Misol |
|---|---|---|
| Codex | `codex/` | `codex/messenger-reply-threading` |
| Claude Code | `claude/` | `claude/rag-admin-panel` |
| Antigravity | `antigravity/` | `antigravity/dashboard-polish` |
| Human / Azurbek | `feature/`, `hotfix/`, `main` | `feature/payment-flow` |

Yangi branch:

```bash
git fetch origin
git checkout -b <prefiks>/<task-name> origin/main
```

**Hech qachon:** boshqa agent branch'iga commit, `main`'ga bevosita push, force-push, `git reset --hard` (Azurbek ruxsat bermasa).

> **2026-08-15 dan buyon bu qoida serverda majburlangan.** `main` branch protection ostida: to'g'ridan-to'g'ri push, force-push va branchni o'chirish rad etiladi — **Azurbek uchun ham** (`enforce_admins`). Yagona yo'l — PR, va CI ning uchala ishi yashil bo'lgach merge. Batafsil: [rules-for-agents.md §9](nuclear-program/rules-for-agents.md).

> **Owner workflow qarori — 2026-09-03:** agent o'z prefiksidagi PR'ni required CI yashil, review izohlari resolve va branch `main` bilan yangilangan bo'lsa alohida merge ruxsati so'ramasdan merge qiladi. **Qo'lda va kutib:** `gh pr checks <N> --watch` → `gh pr merge <N> --merge`. Auto-merge (`--auto`), repository sozlamasini o'zgartirish (`allow_auto_merge` va h.k.), `--admin`/gate bypass va boshqa agentning PR'ini merge qilish taqiqlanadi. Conflict, failed check, xavfli migration, data-loss yoki security anomaly bo'lsa agent to'xtab Azurbekka xabar beradi. Batafsil: [rules-for-agents.md §9](nuclear-program/rules-for-agents.md).

---

## Asosiy buyruqlar

```bash
# Local server
python manage.py runserver

# Tekshiruv
python manage.py check
python manage.py test <changed-app>

# DIQQAT — testni har doim `.env.local`siz yugurtiring: aks holda haqiqiy
# GEMINI_API_KEY yuklanadi va testlar bepul kvotani sarflaydi.
AZURELMS_SKIP_ENV_FILE=1 GEMINI_API_KEY= TELEGRAM_BOT_TOKEN= python manage.py test

# RAG indeks
python manage.py reindex_rag --force

# Telegram bot polling (alohida terminal)
python manage.py runbot
```

Tech stack qisqacha (2026-09-03 verified): Django 6.0.8 + Python (local venv 3.12.10, Dockerfile 3.12), Daphne 4.2.3 + Channels 4.3.2 (ASGI), Celery 5.6.2, SQLite (joriy local) / PostgreSQL + pgvector (future prod), Gemini API (`google-genai 1.65.0`) + dormant DigitalOcean Serverless Inference adapteri, Aiogram 3.30.0.

2026-08-14 owner resurs qarori: production qayta ochilmaguncha DigitalOcean hosting/Spaces/inference ishlatilmaydi. Joriy local AI provider Gemini va uning bepul kvotasi hard engineering constraint; AI feature ishidan oldin `nuclear-program/launch-plan/README.md`dagi A8 budget gate'ini tekshiring.

---

## Sessiya tugagach

- O'zgarishlaringizni logical holatga keltiring: testdan o'tsa commit qiling; WIP bo'lsa statusni aniq yozing (nima yarim, nima tayyor)
- O'z branch'ingizga push qiling
- Major bo'lsa `nuclear-program/marinebook.md` ga yozuv qo'shing (eng tepaga, teskari xronologik)
- Final response qisqa: nima o'zgardi, qaysi muhim fayllar, test natijasi (aniq command), commit hash, qoldirilgan risklar

---

*Diqqat: bu fayl faqat kirish. To'liq qoidalar `nuclear-program/rules-for-agents.md`'da. Agar siz biror noaniq holatda qolsangiz — shu hujjatni o'qing yoki Azurbek'dan so'rang. Taxmin qilib ish qilmang.*
