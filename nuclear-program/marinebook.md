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
