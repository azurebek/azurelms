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
Hozirgi navbat: joriy qamrov qabul/tuzatish (ishda) → DESIGN-01.

## Packet77 paritet auditi — finalda yo‘qolmasin

[Q08 audit jadvali](Q08-DATED-ATTENDANCE-PROTOTYPE.md) to‘liq dalil va
chegarani beradi. Quyidagilar yangi URL yoki yangi redesign emas:

- [x] ~~PAR-01 lokal kurs formasidagi4/14 maydon farqi~~:
  [Packet80](PAR01-COURSE-FIELDS-PROTOTYPE.md),2026-10-03. Create/edit14field,
  exact receipt, stale-reload baseline va saved active list parity tekshirildi.
  Plain-text cap/current-teacher scope/native va real adapter chegarasi ochiq.
- [x] ~~PAR-02 lokal AI compact action menyusi~~:
  [Packet79](PAR02-AI-COMPACT-PROTOTYPE.md),2026-10-01. Ism/matn va44px
  `⋯`; copy/feedback native dialogda, keyboard/focus/unknown/reload
  va48 responsive check. Native long-press/AT va UX-01 alohida OPEN.
- [x] ~~PAR-03 admitted lokal blog interaction/SIT handoff~~:
  [Packet81](PAR03-PUBLIC-INTERACTIONS-PROTOTYPE.md),2026-10-04. Comment/
  one-level reply/like/clap, native fallback/draft/stale/unknown receipt;
  SIT existing AI/tutor link (ariza backend emas).858 Django/223 Node,
  final73/48 DOM responsive. Screenshot unavailable: pixel/native/owner
  acceptance hamda real canonical idempotency adapteri alohida OPEN.
- [x] ~~PAR-04 lokal re-review / first-review farqi~~:
  [Packet78](PAR04-EXAM-REREVIEW-PROTOTYPE.md),832 Django/203 Node/48
  responsive; yangi private draft eski published natijani almashtirmaydi,
  explicit publish talab qilinadi. Native/real port qabuli alohida ochiq.
- PAR-05 OPEN: real rejected chek o‘chirilishi / preview namuna holati;
  alias kirishlar, picker va yangi oilalardan existing journey handoff.

U17/A2-D01, keng Q14 va source’da yo‘q reply/assignment/quiz authoring
alohida capability qarorlari: bu ro‘yxat ularni implementatsiya qilish
uchun ruxsat emas. Native/AT/provider go-no-go ham alohida qoladi.
