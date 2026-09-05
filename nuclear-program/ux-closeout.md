# UX audit closeout — 2026-09-05

Owner: Azurbek, «endi ishni boshla». Branch: `codex/ux-context-closeout`.
Admission: **ADMIT — launch-critical**, mavjud buzilgan oqimlarni yakunlash.

| Slice | Outcome / asosiy KPI | Canonical state va adapter | Verification / rollback |
|---|---|---|---|
| Davomat | Eski boshqaruv URL'i ishlaydi; GET 500 = 0 | Mavjud AttendanceManageView + attendance_service, teacher scope; model o'zgarmaydi | GET/POST/date/permission regression, browser; template rollback |
| Public nav | Telefon mehmoni Kurslar/Narxlar/Blog/SITga o'tadi; 320–1040px navigatsiya yo'qolishi = 0 | Bitta shared link partial, desktop/mobile shell | No-JS native disclosure, keyboard, resize/overflow/browser; shell rollback |
| Owner CSS | Forma, tasdiq, xato va audit tarixi o'qiladi | Mavjud owner mutationlar; faqat presentation | Actual loaded styles + mobile/dark/browser; CSS rollback |
| Static assets | Yangi CSS/JS eski cache bilan aralashmaydi | Manifest static storage; media o'zgarmaydi | collectstatic, hashed URL/reference, full tests; storage config rollback |
| Onboarding | AI foydalanuvchi aytgan maqsad/darajani kontekstda oladi; profile bor va ruxsat yoqilganda context inclusion 100% | UserOnboarding read-only, existing PromptBuilder; access/grade/progress yozilmaydi | Missing/unknown/invalid/profile privacy/offline prompt contract; feature flag rollback |

Qo'shimcha remote AI chaqiruvi, model yoki premium claim yo'q. A8 supply/retry gate o'zgarmaydi.
Daraja self-report, baholangan CEFR emas; input faqat model choices allowlistidan olinadi.
Onboarding konteksti AI memory privacy toggle va owner flag bilan o'chiriladi.
Ownerning haftalik qo'lda ishi oshmaydi. AI pedagogik sifatini isbotlash va teacher-authored
eval A9ning alohida gate'i; bu slice adaptiv mastery yoki natija yaxshilanishini va'da qilmaydi.

Demo hisoblar: `demo-tolov`, `demo-sinfdosh` dev bazasida. Bog'lanishlar va seed ownership
avval tekshiriladi; haqiqiy billing tarixi yo'qolmaydi. Tozalash natijasi alohida qayd etiladi.


## Tekshiruv natijasi (Claude, 2026-09-05)

Reja va kod Codex tomonidan yozilgan, ammo limitga urilgani uchun bironta
ham slice tekshirilmagan edi. Ishga tushirilganda to'rtta haqiqiy nuqson
chiqdi:

| Nuqson | Ta'siri | Tuzatish |
|---|---|---|
| `collectstatic` butunlay yiqilardi | **Deploy to'xtardi.** `jazzmin` paketi Bootstrap bundle'ini mavjud bo'lmagan `.map` ga ishora bilan yuboradi | `core.custom_storage.HashedStaticFilesStorage` — ichki havola kechiriladi, `{% static %}` esa qat'iy qoladi |
| `onboarding_context_enabled` `RegisterView` ga qo'yilgan | Matn hech qachon ko'rinmasdi; sahifani `OnboardingChoiceView` chizadi | Kontekst to'g'ri view'ga ko'chirildi |
| Testlarda emailsiz `create_user` | 5 ta test `IntegrityError` berardi (`email` `unique=True`) | Har bir test foydalanuvchisiga alohida email |
| Escape faqat fokus menyu ichida bo'lganda ishlardi | Sichqoncha bilan ochgan odam menyuni yopa olmasdi | Tinglovchi `document` ga ko'chirildi |

Qo'shimcha: `brand-logo-image--large` shablonda ishlatilardi, hech qayerda
aniqlanmagan edi — yuklangan logo ko'rik panelini yorib yuborardi. Aniqlandi;
endi `brand_control.html` da aniqlanmagan klass qolmadi.

Nazorat yugurishlari: storage'ni Codex'ning asl variantiga qaytarish
`MissingFileError` berdi; davomat shablonini o'chirish 4 ta testni,
kontekstni doim bo'sh qaytarish 2 tasini qizartirdi.

Brauzerda tekshirildi: mobil menyu 320/375px da ochiladi va viewport ichida
turadi, Escape/tashqi bosish/havola bosish yopadi, 1042px da to'liq
navigatsiya qaytadi, gorizontal siljish yo'q; davomat sahifasi o'qituvchi
qobig'ida ro'yxat bilan chiziladi. Haqiqiy `collectstatic`: 359 fayl,
1053 post-processed, xatosiz.

Demo hisoblar (`demo-tolov`, `demo-sinfdosh`) hali dev bazasida — ular
tegilmadi.
