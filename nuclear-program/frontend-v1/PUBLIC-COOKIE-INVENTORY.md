# PUBLIC-COOKIE-INVENTORY — brauzerda nima saqlanadi

> Avtomatik yaratilgan: `python manage.py privacy_inventory --write` (manba:
> `frontend/privacy_inventory.py`). Qo'lda tahrirlamang — test farqni ushlaydi.

Hamma yozuv birinchi tomon (azurelms) va **zarur**: xizmat ishlashi yoki foydalanuvchi
tanlagan sozlama. Analitika va marketing cookie'si yo'q (PUB-D6 qaroriga qadar o'chiq),
shuning uchun rozilik banneri ham yo'q. Bu hujjat huquqiy muvofiqlik da'vosi emas.

## Cookie

| Nom | Holat | Kim yozadi | Maqsad | Asos | Muddat | Qanday o'chadi | Kod |
|---|---|---|---|---|---|---|---|
| `sessionid` | faol | server (Django sessiyasi) | Kirgan holatni, Telegram orqali kirish oqimini va forma xabarlarini saqlash. Anonim public sahifa uni qo'ymaydi. | Zarur — xizmat ishlashi uchun | 14 kun (chiqishda o'chadi) | Chiqish (logout) yoki muddat tugashi; HttpOnly, SameSite=Lax | `core/settings.py`<br>`users/telegram_auth_service.py` |
| `csrftoken` | faol | server (Django CSRF) | Forma va so'rovlarni boshqa saytdan soxtalashtirishdan (CSRF) himoya qilish; formali sahifada qo'yiladi. | Zarur — xizmat ishlashi uchun | 364 kun | Muddat tugashi yoki brauzerda tozalash; JS faqat o'qiydi (so'rov sarlavhasi uchun) | `core/settings.py`<br>`static/admin/js/landing_nav_sort.js`<br>`static/classbook/live-activity.js`<br>`static/js/messenger-chat.js`<br>`static/js/blog-runtime.js` |
| `messages` | faol | server (Django xabarlari) | Bir martalik xabar (masalan, “saqlandi”) keyingi sahifada ko'rsatilishi uchun. | Zarur — xizmat ishlashi uchun | Brauzer yopilguncha; ko'rsatilgach o'chadi | Xabar ko'rsatilgach avtomatik | `core/settings.py` |
| `blog_visitor` | olib tashlangan | server (eski blog kuzatuvi) | Endi qo'yilmaydi (PUB1.0g): anonim blog o'qishlari kuzatilmaydi; eski brauzerdagi qiymat o'chiriladi. | — | — | Blog sahifasi ochilganda o'chiriladi | `blog/utils.py` |

## localStorage

| Nom | Holat | Kim yozadi | Maqsad | Asos | Muddat | Qanday o'chadi | Kod |
|---|---|---|---|---|---|---|---|
| `az-v2-theme` | faol | brauzer (JS) | Yorug'/qorong'i mavzu tanlovi (V1 va ilova sahifalari). | Zarur — foydalanuvchining o'zi tanlagan sozlama | O'chirilguncha (faqat shu brauzerda) | Brauzer ma'lumotlarini tozalash; serverga yuborilmaydi | `static/frontend_v1/js/theme.js`<br>`static/js/app.js`<br>`static/js/exam-shell.js`<br>`templates/users/settings/account.html`<br>`templates/base.html`<br>`templates/courses/exam_detail.html` |
| `az-theme` | faol | brauzer (JS) | Eski public, blog va to'lov sahifalarida mavzu tanlovi. | Zarur — foydalanuvchining o'zi tanlagan sozlama | O'chirilguncha (faqat shu brauzerda) | Brauzer ma'lumotlarini tozalash; serverga yuborilmaydi | `static/js/public-home.js`<br>`static/js/blog-runtime.js`<br>`static/js/billing.js`<br>`static/js/prototype-ui.js` |
| `lms-theme` | faol | brauzer (JS) | Eski blog sahifasidagi mavzu tanlovi (az-theme bilan birga yoziladi). | Zarur — foydalanuvchining o'zi tanlagan sozlama | O'chirilguncha (faqat shu brauzerda) | Brauzer ma'lumotlarini tozalash; serverga yuborilmaydi | `static/js/blog-runtime.js` |
| `sit-theme` | faol | brauzer (JS) | “Turkiyada o'qish” sahifalaridagi mavzu tanlovi. | Zarur — foydalanuvchining o'zi tanlagan sozlama | O'chirilguncha (faqat shu brauzerda) | Brauzer ma'lumotlarini tozalash; serverga yuborilmaydi | `static/js/sit-theme.js` |

## sessionStorage

| Nom | Holat | Kim yozadi | Maqsad | Asos | Muddat | Qanday o'chadi | Kod |
|---|---|---|---|---|---|---|---|
| `azurelms:v1:practice:*` | faol | brauzer (JS) | Mashq javoblari qoralamasi — sahifa tasodifan yangilansa yo'qolmasin. | Zarur — xizmat ishlashi uchun | Tab yopilguncha | Tab yopilishi, chiqish (shell.js tozalaydi) yoki yuborish | `static/frontend_v1/js/practice.js`<br>`static/frontend_v1/js/shell.js` |
| `azurelms:v1:exam:*` | faol | brauzer (JS) | Imtihon javoblari qoralamasi va yuborish holati — aloqa uzilsa javob yo'qolmasin. | Zarur — xizmat ishlashi uchun | Tab yopilguncha | Tab yopilishi, chiqish (shell.js tozalaydi) yoki yuborish | `static/frontend_v1/js/exam-attempt.js`<br>`static/frontend_v1/js/shell.js` |
| `azurelms:v1:messenger:*` | olib tashlangan | brauzer (JS) | Endi yozilmaydi; eski qoralama kaliti chiqishda o'chiriladi. | — | — | Chiqishda shell.js o'chiradi | `static/frontend_v1/js/shell.js` |
| `azurelms:practice:draft:v1:*` | faol | brauzer (JS) | Backoffice: mashq yaratish qoralamasi. | Zarur — xizmat ishlashi uchun | Tab yopilguncha | Tab yopilishi yoki saqlash | `static/backoffice/practice.js` |
| `azurelms:workspace:draft:v1:*` | faol | brauzer (JS) | Backoffice: kurs/dars tahriri qoralamasi. | Zarur — xizmat ishlashi uchun | Tab yopilguncha | Tab yopilishi yoki saqlash | `static/backoffice/workspace.js` |

## Uchinchi tomon manbalari

| Manba | Maqsad | Qayerda yuklanadi | Ular nimani ko'radi | Izoh |
|---|---|---|---|---|
| https://telegram.org | Telegram Mini App skripti | Faqat Telegram ichida ochiladigan Mini App sahifalari | IP manzil, brauzer turi | Public va auth sahifalarida yuklanmaydi. |

## Kuzatuv xizmatlari

Sahifada ham, Content-Security-Policy'da ham yo'q: `google-analytics.com`, `googletagmanager.com`, `doubleclick.net`, `facebook.net`, `facebook.com/tr`, `mc.yandex`, `metrika`, `hotjar`, `clarity.ms`, `tiktok`, `segment.io`, `mixpanel`.

## Faoliyat eslatmalari (forma yonida)

| Faoliyat | Qayerda | Matn |
|---|---|---|
| Ro‘yxatdan o‘tish | Ro‘yxat formasi (V1 va legacy) | Hisob uchun ismingiz, familiyangiz (ixtiyoriy) va emailingiz saqlanadi; parolning o‘zi emas, faqat shifrlangan izi. Ko‘p urinishni cheklash uchun IP manzilingiz xesh ko‘rinishida vaqtincha sanaladi. |
| Parolni tiklash | Tiklash so‘rovi formasi (V1 va legacy) | Email faqat tiklash havolasini yuborish uchun ishlatiladi; bu sahifa hisob bor-yo‘qligini aytmaydi. Ko‘p so‘rovni cheklash uchun email va IP xesh ko‘rinishida vaqtincha sanaladi. |
| Telegram orqali kirish | Telegram paneli (kirish va ro‘yxat sahifalari) | Telegrami ulangan hisobga kirasiz; ulanmagan bo‘lsa yangi profil ochiladi va unga Telegram ismingiz hamda username’ingiz yoziladi. Telefon raqamingiz so‘ralmaydi. |
| Blogga izoh | Maqola ostidagi izoh formasi (V1 va legacy) | Izohingiz va hisobingizdagi ism maqola ostida hammaga ko‘rinadi. |
| To‘lov cheki | To‘lov sahifasi (V1 va legacy) | Chek rasmi, tarif va summa to‘lovni tekshirish uchun saqlanadi. Chek yopiq saqlanadi: uni faqat siz va platforma xodimlari ochadi. |
