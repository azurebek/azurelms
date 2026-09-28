# DESIGN-01 — kodsiz dizayn boshqaruvi, reja oxiridagi kengaytma

2026-09-28 **USER-DECIDED — rejalashtirish**. Owner ranglar, button/karta
shakllari va fontlarni admin paneldan kodga tegmasdan keng boshqarishni
so‘radi: sodda/chala yechim emas. **Hozir implementatsiya boshlanmaydi.**
Navbat: Q08 legacy/paritet → joriy qamrov qabuli → DESIGN-01.
Bu yangi capability: mavjud45 UI/handler inventariga yashirin qo‘shilmaydi.

## Maqsad va chegaralar

Outcome: owner umumiy dizaynni sahifama-sahifa kod tahririsiz izchil boshqaradi.
KPI: kelishilgan sozlamani barcha mapped consumerlarda tatbiq qilish uchun
qo‘lda kod tahriri0; qabul matritsasida o‘qilmas matn/layout regressiyasi0.
Mavjud `tokens.css`/componentlar poydevor; hozir faqat fixed light/dark tema
va umumiy tokenlar bor. Q16b brend/landing formasi bu capabilityni bajarmaydi.

Hozir faqat reja tasdiqlangan. Ish boshlanganda aniq field/component inventari,
admission, permission, source-of-truth va rollback kontrakti yoziladi;
canonical schema/DB, runtime yoki AWS bu reja bilan o‘zgarmaydi.

## Quriladigan qamrov

- **Ranglar:** light/dark uchun canvas/surface/text/muted/border/accent,
  hover/active/focus/disabled holatlari va semantik success/warning/error.
  Kontrast va ma’no saqlanadi; bitta accentni almashtirish bilan cheklanmaydi.
- **Typography:** asosiy matn/sarlavha/code rollari, tekshirilgan font oilalari,
  fallback, vazn, o‘lchamlar iyerarxiyasi, line-height va ruxsatli letter-spacing.
  O‘zbek/turk belgilar, uzun matn, zoom, font yuklanmasligi va layout shift sinaladi.
  Font manbasi/litsenziyasi, self-hosting/cache/CSP va yuklanish hajmi baholanadi;
  tasodifiy tashqi URL yoki erkin CSS kiritish standart yo‘l emas.
- **Komponentlar:** button/input/card/dialog kabi rollar radiusi mustaqil;
  border qalinligi, shadow, ruxsatli o‘lcham/ichki bo‘shliq va density presetlari.
  Global baza va component override munosabati aniq; yashirin sahifa override yo‘q.
  Minimal touch target, focus va responsive chegaralari buzilmaydi.
- **Brend bilan bog‘lanish:** existing logo/brend va landing sozlamalari qayta
  ixtiro qilinmaydi; yagona effective theme bilan munosabatlari xaritalanadi.
  Admin global palette tanlovi foydalanuvchining light/dark tanlovini yo‘qotmaydi.
- **Boshqaruv oqimi:** preset tanlash/saqlash, dirty draft, oldingi-yangi taqqoslash,
  ko‘p sahifa/component preview, defaultga qaytarish, validation va explicit publish.
  Qoralama boshqa foydalanuvchilarga ta’sir qilmaydi; preview publish degani emas.
- **Versiyalash:** joriy published versiya, tarix/diff, reason/confirmation/audit,
  no-op, stale/concurrent edit himoyasi, idempotent publish va explicit rollback.
  Natijasi noma’lum publish avtomatik qayta yuborilmaydi; GET readback bilan aniqlanadi.

## Arxitektura va port talabi

Yagona canonical design settings/version service; web/public/Mini consumerlar
undan effective tokenlarni oladi. DB konfiguratsiya, static fallback va cache
versiyasi bir-biriga zid alohida authority bo‘lmaydi. Sahifa ichida yangi theme
writer yo‘q. Flag kerak bo‘lsa existing flag registry ishlatiladi. Faqat vakolatli
owner publish/rollback qiladi; CSRF, input allowlist, typed bounds va audit shart.
Global effekt atomik versiya bilan; cache invalidation/readback tekshiriladi.
500/minimal fallback DB yoki theme service ishlamay qolganda ham o‘qiladigan
xavfsiz defaultda qoladi; bu istisno aniq ko‘rsatiladi.

Eski CSS, vendor editor, chart, print/PDF, rasmdagi matn va Telegram host tema
avtomatik mos deb sanalmaydi. Har consumerga `mapped / constrained / not applicable`
dalili yoziladi; ta’sirlanmaydigan joylar ownerga ko‘rinadi. Rasmlar/iconlar
qayta chizilishi, erkin layout builder, navigatsiya/permission/biznes mantiqini
almashtirish bu customizationning yashirin qismi emas.

## Tugatish va qabul checklisti

- [ ] DC1 — token/component/consumer inventari va mustaqil rol xaritasi.
- [ ] DC2 — to‘liq sozlama formasi, preset/draft, light/dark desktop/mobile preview.
- [ ] DC3 — kontrast, font/zoom, uzun matn, responsive va xavfsiz chegaralar validatsiyasi.
- [ ] DC4 — publish/readback/history/rollback; stale/unknown/no-op/failure holatlari.
- [ ] DC5 — barcha mapped shell/komponentlarda regressiya, vendor/print/fallback istisnolari.
- [ ] DC6 — owner walkthrough va yangi checkpoint; real service/port/CI va release
  alohida kuzatiladi. Faqat lokal demo yoki token almashtirish bilan “to‘liq” yozilmaydi.

Bu bosqich 11-qadamdagi bazaviy qabuldan keyin dizaynni o‘zgartirgani uchun
yakunida uning ta’sir doirasi bo‘yicha qayta qabul majburiy. Muddat qo‘yilmagan.
