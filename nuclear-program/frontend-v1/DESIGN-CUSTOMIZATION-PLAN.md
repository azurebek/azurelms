# DESIGN-01 — kodsiz dizayn boshqaruvi, reja oxiridagi kengaytma

**2026-10-10 DC4:** [lokal nashr, readback, tarix va rollback](DESIGN-01-DC4-RELEASE.md) tayyor.
Sabab/tasdiq, stale/no-op/unknown himoyasi va56frame+4editor tekshirildi.
DC4 real port, DC5–DC6 va oldingi UX/DATA/RULE/native/owner qabuli ochiq.
Quyidagi DC3/DC2 yozuvlari tarixiy snapshot.

**2026-10-10 owner topshirig‘i:** DC1/DC2dan keyin [DC3 validatsiya](DESIGN-01-DC3-VALIDATION.md)
lokal Eleventh Trialda qurildi:68 qoida, xavfli kombinatsiyani saqlashdan
himoya,200% matn/spacing/uzun matn/fallback sinovlari.224frame+5font+4editor
holatida overflow0. Oldingi UX/DATA/RULE/native/owner qabul, DC4–DC6,
real canonical design service/DB va AWS alohida ochiq.

2026-09-28 **USER-DECIDED — rejalashtirish**. Owner ranglar, button/karta
shakllari va fontlarni admin paneldan kodga tegmasdan keng boshqarishni
so‘radi: sodda/chala yechim emas. **Runtime implementatsiyasi boshlanmagan.**
Navbat: Q08 legacy/paritet → joriy qamrov qabuli → DESIGN-01.
Bu yangi capability: mavjud45 UI/handler inventariga yashirin qo‘shilmaydi.

## Maqsad va chegaralar

Outcome: owner umumiy dizaynni sahifama-sahifa kod tahririsiz izchil boshqaradi.
KPI: kelishilgan sozlamani barcha mapped consumerlarda tatbiq qilish uchun
qo‘lda kod tahriri0; qabul matritsasida o‘qilmas matn/layout regressiyasi0.
Mavjud `tokens.css`/componentlar poydevor; hozir faqat fixed light/dark tema
va umumiy tokenlar bor. Q16b brend/landing formasi bu capabilityni bajarmaydi.

DC1 inventari tayyor; DC2 lokal forma/schema, preview hamda real port uchun
route/permission kontraktini beradi. DC3 lokal guard va sinov dalilini beradi; DC4
lokal release service/rollback va fixture permission testlarini beradi.
Actual owner enforcement va doimiy yagona source-of-truth DC4 real portda ochiq.
Canonical schema/DB, runtime va AWS alohida port/release.

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

- [x] DC1 — token/component/consumer inventari va mustaqil rol xaritasi:
  [2026-10-10 source dalili](DESIGN-01-DC1-MAP.md). Bu dinamik theme yoki visual PASS emas.
- [x] DC2 — [to‘liq lokal forma, preset/draft, light/dark desktop/mobile preview](DESIGN-01-DC2-PREVIEW.md):
  888 Django/261 Node, 56 frame + 4 editor viewport; lokal bosqich tayyor. Real service emas.
- [x] DC3 — [lokal kontrast/typography gate,200% matn va xavfsiz chegaralar](DESIGN-01-DC3-VALIDATION.md).
  Native full-page zoom/AT/qurilma qabuli DC6da; butun sayt WCAG qabuli emas.
- [x] DC4 lokal — [publish/readback/history/rollback](DESIGN-01-DC4-RELEASE.md); stale/unknown/no-op/failure holatlari.
- [ ] DC4 real port — actual owner auth/ACL, DB transaction, durable audit/idempotency, cache/flag va consumer enforcement.
- [ ] DC5 — barcha mapped shell/komponentlarda regressiya, vendor/print/fallback istisnolari.
- [ ] DC6 — owner walkthrough va yangi checkpoint; real service/port/CI va release
  alohida kuzatiladi. Faqat lokal demo yoki token almashtirish bilan “to‘liq” yozilmaydi.

Bu bosqich 11-qadamdagi bazaviy qabuldan keyin dizaynni o‘zgartirgani uchun
yakunida uning ta’sir doirasi bo‘yicha qayta qabul majburiy. Muddat qo‘yilmagan.
