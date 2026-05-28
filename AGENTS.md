# AzureLMS — Agent Bootstrap

O'zbek tilida turk tili o'rgatuvchi Django LMS. AI tutor, RAG, real-time messenger, Telegram bot, subscription va exam oqimlari bilan. Asosiy branch: `main`.

Bu fayl har AI agent (Claude Code / Codex / Antigravity / boshqa) sessiya boshlashidan oldin **eng birinchi o'qishi kerak bo'lgan** kirish. To'liq qoidalar va loyiha wiki'si `nuclear-program/` ichida.

---

## O'zgartirish kiritishdan oldin

1. `nuclear-program/rules-for-agents.md` — to'liq ish qoidalari (branch ownership, worktree setup, test/commit discipline, conflict protocol, emergency stop)
2. `nuclear-program/marinebook.md` — so'nggi 3-5 yozuvni o'qing (boshqa agentlar nima qildi)
3. `nuclear-program/project-context.md` — arxitektura kerak bo'lganda (10 apps, AI agent qatlami, URLs, env, data model)
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

---

## Asosiy buyruqlar

```bash
# Local server
python manage.py runserver

# Tekshiruv
python manage.py check
python manage.py test <changed-app>

# RAG indeks
python manage.py reindex_rag --force

# Telegram bot polling (alohida terminal)
python manage.py runbot
```

Tech stack qisqacha: Django 6.0.2 + Python (local venv 3.14, Dockerfile 3.12), Channels (ASGI), Celery, PostgreSQL + pgvector (prod) / SQLite (lokal), Gemini API (`google-genai 1.65`), Aiogram 3.26.

---

## Sessiya tugagach

- O'zgarishlaringizni logical holatga keltiring: testdan o'tsa commit qiling; WIP bo'lsa statusni aniq yozing (nima yarim, nima tayyor)
- O'z branch'ingizga push qiling
- Major bo'lsa `nuclear-program/marinebook.md` ga yozuv qo'shing (eng tepaga, teskari xronologik)
- Final response qisqa: nima o'zgardi, qaysi muhim fayllar, test natijasi (aniq command), commit hash, qoldirilgan risklar

---

*Diqqat: bu fayl faqat kirish. To'liq qoidalar `nuclear-program/rules-for-agents.md`'da. Agar siz biror noaniq holatda qolsangiz — shu hujjatni o'qing yoki Azurbek'dan so'rang. Taxmin qilib ish qilmang.*
