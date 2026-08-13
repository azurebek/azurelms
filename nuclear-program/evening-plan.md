# Kechgi ish rejasi — historical pointer

2026-07-06 dagi prompt/skill-first kechgi reja **bekor qilingan historical snapshot**. Uning to'liq matni Git tarixida saqlanadi; unchecked checkboxlari joriy task emas.

2026-08-14 dan amaldagi tartib:

1. [`launch-plan/README.md`](launch-plan/README.md) — local/pre-production owner qarori va current truth;
2. [`launch-plan/02-yol-xarita.md`](launch-plan/02-yol-xarita.md) — R0–R4 fazalar va exit gate'lar;
3. [`launch-plan/03-mahsulot-backlog.md`](launch-plan/03-mahsulot-backlog.md) — `A8` Gemini free-tier planned next, `ADMIT / NEXT / HOLD / CUT`;
4. [`launch-plan/05-launch-ops.md`](launch-plan/05-launch-ops.md) — local ops, Control Center, CI, security, AI supply va future production gate.

DigitalOcean production qayta admissionigacha `HOLD`; eski “Gemini faqat web search” farazi joriy `AI_CHAT_PROVIDER=gemini` profiliga mos emas. Eski checklistdan biror AI feature qayta olinmasidan oldin A8 global budget/circuit breaker exit'i yopiladi.

Eski `conversation_partner + word_builder + model picker` tavsiyasi prompt-only feature sprawl yaratgani uchun active navbatdan chiqarildi. Ular faqat structured outcome contract, eval va owner admission'dan keyin `NEXT`dan qayta ko'riladi.
