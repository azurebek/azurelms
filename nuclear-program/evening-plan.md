# Kechgi ish rejasi — historical pointer

2026-07-06 dagi prompt/skill-first kechgi reja **bekor qilingan historical snapshot**. Uning to'liq matni Git tarixida saqlanadi; unchecked checkboxlari joriy task emas.

Joriy ishni [yagona holat sahifasidan](README.md) aniqlang. Quyidagi hujjatlar
strategiya va domen gate'larini saqlaydi; 2026-08-14 ketma-ketligi bugungi
navbat yoki yangi deadline emas:

1. [`launch-plan/README.md`](launch-plan/README.md) — owner resurs qarorlari va launch strategiyasi;
2. [`launch-plan/02-yol-xarita.md`](launch-plan/02-yol-xarita.md) — R0–R4 fazalar va exit gate'lar;
3. [`launch-plan/03-mahsulot-backlog.md`](launch-plan/03-mahsulot-backlog.md) — `A8` Gemini free-tier dalili va `ADMIT / NEXT / HOLD / CUT` chegaralari;
4. [`launch-plan/05-launch-ops.md`](launch-plan/05-launch-ops.md) — local ops, Control Center, CI, security, AI supply va future production gate.

DigitalOcean qayta admissionigacha `HOLD`; eski “Gemini faqat web search” farazi
joriy `AI_CHAT_PROVIDER=gemini` profiliga mos emas. A8 lokal implementatsiya va
test daliliga ega; keyingi AI ishi uning budget/circuit gate'larini saqlashi
kerak. AWSning alohida reliz dalili yagona holat sahifasida ko'rsatilgan.

Eski `conversation_partner + word_builder + model picker` tavsiyasi prompt-only feature sprawl yaratgani uchun active navbatdan chiqarildi. Ular faqat structured outcome contract, eval va owner admission'dan keyin `NEXT`dan qayta ko'riladi.
