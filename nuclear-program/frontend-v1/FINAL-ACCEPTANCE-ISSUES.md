# Yakuniy qabul — ochiq nuqsonlar

2026-09-28. Owner qarori: hozir prototip navbati davom etadi, quyidagi
nuqsonlar yakuniy tuzatishda tekshiriladi. Bu defer — FIXED/PASS emas.
Yangi redesign yoki production mutation vakolati emas.

| ID | Holat / ustuvorlik | Dalil va yopish mezoni |
|---|---|---|
| UX-01 | OPEN · major | Owner iPhone **Chrome**da Azure AI inputiga bosganda klaviatura ochilib, chat ko‘rinmay qolishini screenshot bilan ko‘rsatdi; yana scroll kerak. Local `static/frontend_v1/js/messenger.mjs:74` faqat visualViewport.height/resize oladi; offset/scroll boshqaruvi yetishmasligi **gumon**, native reproduksiya emas. Input focus→typing→keyboard close/reopen/rotate, history position va composer ko‘rinishi real iPhone Chrome’da sinalmaguncha yopilmaydi. AI yuborish/provider talab qilinmaydi. |
| UX-02 | OPEN · copy/UX | Claude audit va local source: V1/migratsiya/eski ko‘rinish yozuvlari, ortiqcha izohlar, til/apostrof izchilligi. Foydalanuvchiga kerakli xato/permission/saqlash ogohlantirishlari yo‘qolmasin. |
| UX-03 | OPEN · checkout | Summa formati, explicit quote UX, hisob joylashuvi, karta nusxalash, ikki raqamlash. Jami submit oldida ham bor; 30 daqiqa allaqachon admin sozlamasi. Quote expiry protection olib tashlanmaydi; bankdan qaytish recovery tekshirilsin. |
| DATA-01 | OPEN · real release verification | Source default karta raqami va seed 2400+/94%/4.9 bor. AWSning amaldagi qiymati bu auditda tekshirilmagan. Rekvizit va marketing dalillari owner bilan tekshiriladi; taxminiy statistika nashr qilinmaydi. |
| RULE-01 | OPEN · owner decision | Dars access faqat immediate predecessor assignmentsga qaraydi. Qat’iy transitive ketma-ketlik kerakmi — owner qarori; qarorsiz business-rule o‘zgarmaydi. |
| UX-04 | OPEN · auth | Takroriy banner/inline xato, errorlist styling, password mismatch/strength ikki yuborish, onboarding CTA, footer tap area; actual form/keyboard sinovi kerak. |
| UX-05 | OPEN · notification | Receipt approval va enrollment activation ikkita notification yo‘li; pending→active uchun “yana” noto‘g‘ri. Trigger/idempotency va renew/first activation ajratilib tekshirilsin. |
| UX-06 | OPEN · public continuity | Logged-in headerda O‘quv maydoni bor, mobilda menyu ichida. Katalog filter/first-fold, detail price/CTA/0 exam, landing CTA, pricing bullet/feature, rich description spacing, favicon fallback tekshiriladi. |

Claude kuzatuvlari to‘liq native regression yoki server attestatsiyasi emas.
AI javobi, imtihon, Classbook, Telegram login va real telefonning qolgan
yo‘llari NOT TESTED; mavjud gate hujjatlari bilan birga qabulda tekshiriladi.
Hozirgi navbat: Q08 → joriy qamrov qabul/tuzatish → DESIGN-01.

## Packet77 paritet auditi — finalda yo‘qolmasin

[Q08 audit jadvali](Q08-DATED-ATTENDANCE-PROTOTYPE.md) to‘liq dalil va
chegarani beradi. Quyidagilar yangi URL yoki yangi redesign emas:

- PAR-01 OPEN: eski course prototype4 maydon / real I6b14 maydon;
  source maydon xaritasi va preview deltasini tekshirish.
- PAR-02 OPEN: AI previewdagi doimiy copy/feedbackni owner tasdiqlagan
  real I4b compact action menyusi bilan muvofiqlashtirish; UX-01 alohida.
- PAR-03 OPEN: blog public comment/reaction va SIT application/advisor
  handoffni source bo‘yicha solishtirish; real content qabuli alohida.
- PAR-04 OPEN: real imtihon re-review / preview first-review farqi;
  oldingi published natija yangi draft sabab learnerdan yo‘qolmasin.
- PAR-05 OPEN: real rejected chek o‘chirilishi / preview namuna holati;
  alias kirishlar, picker va yangi oilalardan existing journey handoff.

U17/A2-D01, keng Q14 va source’da yo‘q reply/assignment/quiz authoring
alohida capability qarorlari: bu ro‘yxat ularni implementatsiya qilish
uchun ruxsat emas. Native/AT/provider go-no-go ham alohida qoladi.
