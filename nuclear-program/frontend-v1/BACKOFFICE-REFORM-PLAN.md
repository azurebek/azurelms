# Backoffice islohoti — uch asosiy ishni osonlashtirish

2026-10-10. **Birinchi bosqich xaritasi, kurs/dars ustaxonasi va o‘quvchiga yordam kesimi qurildi.**
[Ikkinchi bosqich](BACKOFFICE-REFORM-STAGE-2.md): Boshqaruv, modul/dars yaratish,
material, namuna va guruhga ochishga ulanish. Flag default OFF; owner usability
va production qabuli ochiq.
[Uchinchi bosqich](BACKOFFICE-REFORM-STAGE-3.md): o‘quvchi qidirish → kurs/dars
bo‘yicha sabab → aniq mavjud qaror sahifasi → qayta tekshirish. Flag default OFF.
Keyingi kesim oddiy dizayn boshqaruvi; u va qolgan ishlar hali reja.
[Birinchi bosqich qaydi](BACKOFFICE-REFORM-STAGE-1.md): ownerning boshlang‘ich bahosi, aniq action/writer/scope xaritasi va sakkizta amaliy vazifa.
Owner nomlar va tuzilmani agent hal qilishini topshirdi; yangi so‘rovnoma javobi ishni boshlash sharti emas.
Azurbek belgilagan ustuvorlik: **kurs/dars tayyorlash → o‘quvchi muammosini hal qilish → platforma dizaynini texnik bilimsiz boshqarish**.
To‘lovlar va texnik xizmatlar saqlanadi, lekin asosiy ishlarni to‘sib turmaydi.

Maqsad: owner kerakli ishini qayerdan boshlashini darhol bilishi, uni boshqa-boshqa panellar orasida yurmasdan yakunlashi va natijani tekshira olishi.
Reja bitta hujjatda yuritiladi; yangi paket nomlari va hisobot sahifalari oddiy interfeysga chiqarilmaydi.

## 1. Qanday backoffice quramiz

**Boshqaruv alohida ish maydoni bo‘ladi.** O‘quvchi va ustoz maydoniga o‘tish aniq, ruxsatga mos tanlov orqali bajariladi.
Owner maydoni o‘z navigatsiyasiga ega; ustoz menyusi ichiga joylanmaydi.

| Asosiy kirish | Ichida nima bor | Qaysi savolga javob beradi |
|---|---|---|
| **Ish stoli** | Uch asosiy amalga bevosita kirish, mavjud ishga qaytish, tekshirishni kutayotgan yozuvlar, muhim ogohlantirish | Nimadan boshlayman? |
| **Kurslar** | Kurs → modul → dars; materiallar, imtihonlar, guruhning dars jarayoni | Darsni qanday tayyorlayman va guruhga ochaman? |
| **O‘quvchilar** | O‘quvchining kurs/a’zolik/to‘lov/ruxsat holati, mavjud suhbatlarga havola | Bu o‘quvchiga nima bo‘lgan? |
| **Sayt va dizayn** | Ko‘rinish, brend, sayt bosh sahifasi, blog va Turkiyada o‘qish kontenti | Sayt qanday ko‘rinadi va unda nima yozilgan? |
| **To‘lovlar** | Cheklar, tariflar, to‘lov tarixi va mavjud qarorlar | Kimning to‘lovi tekshirilishi kerak? |
| **Sozlamalar** — menyu quyi qismida | Xizmatlar, AI, muddat/limitlar, yoqish/o‘chirish, yetkazilmagan xabarlar, mavjud ustoz/admin ro‘yxati | Zarur boshqaruvni qayerdan sozlayman? |

Bu tuzilma ownerning «o‘zing hal qil» ko‘rsatmasi asosida agent tanlagan yechim; inson usability qabuli deb hisoblanmaydi. Ichki menyu faqat tanlangan bo‘limga tegishli bo‘ladi.
Guruhning yagona asosiy sahifasi **Kurslar → Guruhlar**da; o‘quvchi sahifasi uning a’zoligiga havola beradi.
Tarif **To‘lovlar**da; guruh muharriri shu tarifni tanlaydi. Bir obyekt uchun ikkita mustaqil muharrir yaratilmaydi.
Menyu tartibi foydalanish davomida o‘z-o‘zidan almashmaydi. Bo‘lim, sarlavha va faol menyu bir-biriga mos bo‘ladi.

**Ish stoli**ning birinchi qismi ownerning uch ishiga xizmat qiladi: dars tayyorlash, o‘quvchiga yordam, dizaynni o‘zgartirish.
Faoliyat sonlari va xizmat hisobotlari pastroq turadi. Xizmat jiddiy to‘xtagan bo‘lsa, uning ta’siri tepada qisqa ko‘rsatiladi.
Ma’lumoti yo‘q ish yoki navbat uchun soxta son/holat berilmaydi; normal holat, bo‘sh holat, yuklanmagan va eskirgan ma’lumot farqlanadi.

## 2. Birinchi ustuvorlik — kurs va dars ustaxonasi

**Bitta kurs ochilganda uning tuzilmasi va tayyorlanayotgan dars bir kontekstda qoladi.**

- Chapda modul va darslar daraxti; markazda tanlangan dars muharriri; kerak paytda yonida o‘quvchi ko‘rinishi.
- Global «Darslar» ro‘yxati asosiy ish yo‘li bo‘lmaydi. Qidiruv yoki kutubxonadan kirganda ham kurs va modul ko‘rinadi.
- Dars yaratish avval minimal ma’lumotdan boshlanadi: nom va modul. Video, matn, fayl va qo‘shimcha parametrlar kerakli joyda qo‘shiladi.
- Mavjud darsni tahrirlash va material biriktirish bir ish maydonida. Qaytishda tanlangan dars, ro‘yxat holati va saqlanmagan matn yo‘qolmaydi.
- Saqlash holati bir joyda: «Saqlanmagan», «Saqlanmoqda», «Saqlandi» yoki bajarilishi kerak bo‘lgan aniq xato.
- «O‘quvchi ko‘rinishi» tanlangan kurs/guruh kontekstini ko‘rsatadi. Bu impersonation yoki o‘quvchi akkauntiga kirish emas.
- Kontentni saqlash va guruhga darsni ochish alohida amallar. Ochishdan oldin kimga va qaysi darsga ta’siri ko‘rsatiladi.
- Telefon ekranida uch ustun siqilmaydi: tuzilma → muharrir → ko‘rish o‘rtasida aniq o‘tish, har safar joy va matn saqlanadi.

**Hozirgi haqiqiy bo‘shliqlar:** kurs create/edit mavjud; custom backoffice’da modul yaratish/tartiblash oqimi topilmadi.
Yangi darsni odatiy tarzda qo‘shish ham to‘liq emas: alohida `lessons/new` yo‘li yo‘q, mavjud yo‘l ko‘pincha bor darsni tanlaydi.
Shu ikki vazifa birinchi ishlaydigan kesim tarkibida backend shartnomasi bilan quriladi.
Material upload/biriktirish/tartiblash mavjud xizmatlardan olinadi.

Assignment/quiz yaratuvchi va ko‘p bo‘limli savol muharriri to‘liq mavjud deb olinmaydi.
Ular uchun maydon/holat/ruxsat/paritet ro‘yxati alohida aniqlanadi; tugallanmagan amallar ishlaydigan tugma sifatida ko‘rsatilmaydi.
Classbook mashq muharriri dars quiz/assignment muharririning o‘rniga qo‘yilmaydi.

**Birinchi namoyish natijasi:** kurs ochish → modul/dars qo‘shish → tayyor matn/video/materialni joylash → ko‘rinishni tekshirish → saqlash → guruhga ochish ta’sirini ko‘rish.

## 3. Ikkinchi ustuvorlik — o‘quvchi bo‘yicha bitta ish maydoni

Odamni topgach, uning ismi, kerakli aloqa ma’lumoti, kurs/guruhi va joriy kirish holati bir joyda ko‘rinadi.
Keyin faqat muammoga tegishli ma’lumot ochiladi: **darsga kira olmayapti**, **to‘lov**, **topshiriq/natija** yoki **xabar**.

Misol: «Madina nega darsga kira olmayapti?» → o‘quvchini topish → kursni tanlash → amaldagi ruxsatning sababi → ruxsatli tuzatish joyiga o‘tish → natijani qayta tekshirish.
Sabab mavjud access policy va service javobidan olinadi. Noma’lum holat uchun ishonchli taxmin ko‘rsatilmaydi; «Sababni aniqlash uchun ma’lumot yetarli emas» deyiladi.

- To‘lov, obuna muddati, guruh a’zoligi va darsning ochilishi alohida holatlar; bitta noaniq «Faol» belgisi bilan birlashtirilmaydi.
- Tuzatish mavjud vakolatli service orqali bajariladi. Interfeys «hamma cheklovni olib tashlash» tugmasini yaratmaydi.
- Ro‘yxatga qaytish filtri va o‘quvchi tanlovini saqlaydi; boshqa odamga o‘tganda avvalgi odamning formasi yoki ma’lumoti aralashmaydi.
- To‘lov yoki guruh amali oldidan aniq shaxs va ta’sir takror ko‘rsatiladi. Muhim qarorlar tasdiqsiz bajarilmaydi.
- Birinchi versiya yordam ticketlari tizimi emas; mavjud ma’lumotlarni bog‘lovchi o‘qish yuzasi va aniq amallarga yo‘l bo‘ladi.

Hozir users sahifasi o‘qish/qidiruv ro‘yxati. Birlashtirilgan o‘quvchi kartasi **yangi o‘qish qatlami** bo‘lib, kurs doirasi, ruxsat va maxfiylik testlarini talab qiladi.
Chat matni, moliyaviy ma’lumot va AI tarixini hamma rolga ochish rejaning bir qismi emas.

## 4. Uchinchi ustuvorlik — kodsiz ko‘rinish boshqaruvi

Asosiy yo‘l: **ko‘rinishni tanlash → o‘ziga moslash → sahifalarda solishtirish → saqlash/nashr → kerak bo‘lsa qaytish**.

| Oddiy boshqaruv | Kengaytirilgan boshqaruv |
|---|---|
| Tayyor ko‘rinishlar; brend rangi; matn o‘lchami; tugma va karta shakli; sahifa oralig‘i | Komponent rollari, light/dark palitralar, maydon chegaralari, density, typography va barcha qo‘llab-quvvatlangan aniq qiymatlar |
| «Tekis», «Yumshoq», «Yumaloq», «Odatdagi», «Yirikroq» kabi tushunarli tanlovlar | Raqam, diapazon, meros olinadigan qiymat va kerakli texnik izoh |
| Ko‘rish maydoni asosiy joyni oladi; yonida ayni tanlov | Kerakli guruh ochiladi; birdaniga 87 maydon tashlanmaydi |

Oddiy tanlovlar mavjud typed schema qiymatlariga deterministik moslanadi. Ikkinchi theme engine yoki CSS kiritish yo‘li qurilmaydi.
Qo‘lda sozlangan qiymat presetga mos bo‘lmasa «Moslashtirilgan» ko‘rsatiladi; oddiy rejimga qaytish uni jimgina almashtirmaydi.
«Asliga qaytarish» tanlangan bo‘limga tegishli bo‘ladi; barcha sozlamalarni qaytarish alohida va tasdiqli.

O‘quvchi, dars, chat va telefon ko‘rinishi bevosita yonida tekshiriladi; yorug‘/qorong‘i tanlovi yo‘qolmaydi.
Yomon kontrast tanlanganda matn nima uchun o‘qilmasligini va qayerini tuzatish kerakligini sodda tilda aytamiz.
Qoralama, joriy nashr va oldingi versiya aniq farqlanadi. Saqlash muvaffaqiyati server tasdig‘idan keyin ko‘rsatiladi.
Print, vendor editor, rasmlar va Telegram tashqi qobig‘i kabi cheklangan yuzalar ko‘rish paytida tushunarli belgilanadi.

**Mavjud tayanch:** DESIGN-01 DC2–DC6 lokal forma, preset, validatsiya, preview va release-history tajribasi.
**2026-10-10 runtime kesimi qurildi:** [bosqich 4](BACKOFFICE-REFORM-STAGE-4.md)
haqiqiy owner ruxsati, doimiy draft/preset/version va receipt, yagona writer,
atomic audit hamda V1/workspace va legacy umumiy palitrasiga tatbiqni beradi.
Qolgan mustaqil yuzalar va ownerning yordamsiz foydalanish qabuli ochiq.
Local sessionStorage qoralama yo‘qolishidan ishonchli himoya deb hisoblanmaydi. Real portda saqlanmagan matn, qayta kirish va boshqa tab bilan to‘qnashuv alohida tekshiriladi.
Dizayn qabuli yangi backoffice maketlari uchun ham takrorlanadi; oldingi DC6 avtomatik yopilmaydi.

## 5. Zichlik va til uchun majburiy qoida

1. Har sahifaning bitta asosiy maqsadi va aniq asosiy amali bor. «Saqlash» bilan «Nashr» bir xil urg‘uda turmaydi.
2. Ish turiga mos maket ishlatiladi: kursda daraxt/muharrir; o‘quvchida muammo/kontekst; dizaynda jonli namuna; chekda navbat/tafsilot; tizimda ta’sir/sabab.
3. Birinchi ko‘rinishda zarur ma’lumot. Kam ishlatiladigan sozlama «Qo‘shimcha sozlamalar»da, o‘qiladigan yordam zarur joyning yonida.
4. Kerakli narsani topish uchun umumiy qidiruv bosqichma-bosqich qo‘shiladi: avval kurs/dars, keyin vakolat doirasidagi odam/bo‘lim/sozlama. Qidiruv asosiy menyuning o‘rnini bosmaydi.
5. Ro‘yxatlar qisqa mazmunli ustunlarga ega. Tanlangan yozuv uchun batafsil ko‘rinish ochiladi; ekran kengayganda ham hamma fakt doimiy ko‘rsatilmaydi.
6. «Bosh sahifa» noaniqligi yo‘qoladi: boshqaruv kirishi «Ish stoli», marketing sahifasi «Sayt bosh sahifasi».
7. `Source action`, `revision`, `canonical state`, `no-op`, `RAG`, `dead-letter` kabi atamalar oddiy ish oqimidan texnik tafsilotga olinadi. Masalan: «O‘zgarish yo‘q», «AI foydalanadigan darslar», «Yetkazilmagan xabarlar».
8. Xato «nima bo‘ldi / nima saqlandi / endi nima qilish kerak»ni aytadi. Amal javobi noma’lum bo‘lsa «Holatni tekshirish» beriladi; yashirin qayta yuborish yo‘q.
9. Xavfsizlik uchun zarur sabab, aniq ta’sir va tasdiq saqlanadi. Har oddiy maydon uchun ortiqcha tasdiq so‘ralmaydi.
10. Telefon va klaviatura oqimi boshidan birga quriladi. Muhim amal hoverga bog‘lanmaydi, fokus panel tagida qolmaydi, haqiqiy matn kattalashtirishda ma’lumot yo‘qolmaydi.

Kam ishlatiladigan tanlovlarni keyin ochish usuli [NN/g progressive disclosure](https://www.nngroup.com/articles/progressive-disclosure/) tavsiyasiga mos; asosiy ishlarni yashirib yubormaslik owner sinovi bilan tekshiriladi.
Klaviatura fokusi uchun [W3C focus not obscured](https://www.w3.org/WAI/WCAG22/Understanding/focus-not-obscured-minimum), nishon o‘lchami uchun [W3C target size](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum) tekshiriladi.
Mahsulotning muhim touch boshqaruvlari uchun 44px maqsad qo‘yiladi; bu WCAG AA barcha targetlar uchun aynan 44px talab qiladi degani emas va butun sayt muvofiqligi da’vosi emas.

## 6. Eski joydan yangi joyga xarita

| Bugungi yuza | Yangi joy / qaror |
|---|---|
| Backoffice dashboard, tarqoq count kartalari | Ish stoli; uch ustuvor ish, faqat kerakli signal va mavjud navbatlar |
| Kurslar va alohida dars muharriri | Kurslar → Kurs → Tuzilma → Dars; global dars ro‘yxati qo‘shimcha kirish |
| Kutubxona, material biriktirish | Kurslar → Materiallar; dars ichidan ayni kutubxonaga kirish |
| Imtihon muharriri va teacher tekshiruv | Kurslar → Imtihonlar; authoring va grading vazifalari ajratiladi, mavjud xizmatlar ulanishi saqlanadi |
| Tariflar va guruhlar bir katalogda | Tariflar → To‘lovlar; guruhlar → Kurslar; bog‘lanish saqlanadi |
| Users va chats ro‘yxatlari | O‘quvchilar; shaxsga oid kontekst va mavjud suhbat havolalari; ustoz/admin filtri Sozlamalarda |
| Chek tekshirish | To‘lovlar → Cheklar; odam kartasidan shu yozuvga kirish |
| Brand, landing, blog, SIT | Sayt va dizayn ichidagi aniq guruhlar; brend/kontent uchun mavjud writerlar |
| DESIGN-01 alohida ustaxona | Sayt va dizayn → Ko‘rinish; oddiy va kengaytirilgan boshqaruv |
| Control Center, AI, flags, runtime, xarajat, yetkazish xatolari | Sozlamalar; kundalik ishga ta’sir tepada, texnik tafsilot ichkarida |
| Django admin | Kundalik yo‘lning o‘rniga ishlatilmaydi; yetishmayotgan authoring vazifalari inventarda ochiq, favqulodda kirish existing policy bo‘yicha |

Eski deep linklar birinchi bosqichda saqlanadi. GET yo‘llari uchun kerakli moslashtirish mumkin; POSTlar ko‘r-ko‘rona redirect qilinmaydi.
Har eski actionning yangi joyi, permissioni va writeri xaritada bo‘lmaguncha eski kirish olib tashlanmaydi.

## 7. Amalga oshirish tartibi

| Bosqich | Aniq natija | O‘tish mezoni |
|---|---|---|
| **Vazifalar va xarita — loyihalash tayyor** | Ownerning sifat bahosi qayd etildi; agent tuzilmani tanladi; eski action → yangi joy/scope/writer va mavjud/yangi imkoniyatlar xaritasi tayyor | Boshlanish, yakun, xato va writer aniq; ikkinchi bosqich topshirig‘i tayyor. Owner vaqtli sinovi/keyingi UI qabuli ochiq; so‘rovnoma davom ettirish sharti emas |
| **Kurs bilan ishlaydigan birinchi kesim** | Boshqaruv shell, Kurslar daraxti, kerakli modul/yangi dars yaratish, mavjud muharrir va material, preview, releasega ulanish | Bitta haqiqiy ruxsatli kurs oqimi boshidan oxirigacha; matn va tanlov yo‘qolmaydi; yaratish uchun yangi backend talabi yopilgan |
| **O‘quvchi muammosi — runtime kesimi qurildi** | Scope-aware qidiruv, o‘quvchi kartasi, canonical access sababi, aniq release/receipt/submission/member handoff va recheck | Synthetic release → recheck hamda testlarda receipt/assignment → recheck o‘tdi; privacy/GET zero-write tekshirildi. Ownerning yordamsiz bajarish qabuli hali ochiq |
| **Oddiy dizayn boshqaruvi — runtime kesimi qurildi** | Besh oddiy guruh, to‘rt inert namuna, private qoralama/uslub, nashr tarixi va rollback; V1/workspace va legacy palitra | Synthetic save/reload/publish/rollback, custom/rebase va ikki oynali stale sinovi o‘tdi. Owner CSS/ID bilmasdan yordamsiz sozlashi haqidagi usability qabuli ochiq |
| **Qolgan backoffice — runtime kesimi qurildi** | [Bosqich 5](BACKOFFICE-REFORM-STAGE-5.md): To‘lovlar, Blog/SIT, Guruhlar va Sozlamalar bir xil menyu; tarif/guruh alohida, texnik tafsilotlar ochiladigan bo‘limlarda | [Eski-yangi action xaritasi](BACKOFFICE-REFORM-STAGE-5-MAP.md), scoped GET markazlar, mavjud writer/ruxsat/audit pariteti. Ownerning yordamsiz topish qabuli va yakuniy port auditi hali ochiq |
| **Qabul va bosqichli port** | Har tugagan kesim uchun real adapter, foydalanish sinovi, required CI, qaytish yo‘li; yakuniy eski-yangi paritet auditi | Owner uch asosiy ishni bajaradi; jiddiy regressiya yo‘q; real qurilma va release qabuli alohida tasdiqlanadi |

Har kesim: agentning sodda maketi va ekspert tekshiruvi → service shartnomasi → implementatsiya → tegishli test/CI → aniq ishlaydigan vazifani ko‘rsatish → boshqariladigan port.
Ownerning 2026-10-10 ko‘rsatmasi bo‘yicha mavhum menyu so‘rovnomasi old shart emas. Inson usability dalili va real release qabuli shu bilan yopilmaydi.
Barcha sahifalar birdan qayta bezatilmaydi. Keyingi kesim avvalgisidagi yo‘l topish muammolari yechilmaguncha kengaytirilmaydi.
Muddatlar ish hajmi va yangi authoring bo‘shliqlari baholangach belgilanadi; taxminiy kun soni tayyorlik dalili bo‘lmaydi.

## 8. Qulaylikni qanday qabul qilamiz

Quyidagilar **taklif etilayotgan mezonlar**, hali o‘lchangan natija emas. Sifat bo‘yicha owner bazasi qayd etildi; vaqtli o‘lchov yo‘q. [Sakkizta aniq vazifa](BACKOFFICE-REFORM-STAGE-1.md#sakkizta-amaliy-qabul-vazifasi) keyingi ishlaydigan versiya uchun belgilandi.

| Sinov | Maqsad |
|---|---|
| Kerakli kurs/darsni topish | Owner yordam so‘ramasdan 20 soniyada topadi |
| Tayyor matn bilan dars yaratish, material biriktirish va namunasini ochish | Kontentni yozish va upload kutish vaqtini hisoblamasdan, 3 daqiqa ichida |
| O‘quvchining belgilangan kirish muammosini aniqlash | 60 soniya ichida odam, kurs va haqiqiy sababni aytadi; taxminiy tashxis yo‘q |
| Ko‘rinishni oddiy tanlovlar bilan moslash, solishtirish va saqlash | 3 daqiqa ichida, texnik atama yoki CSS kerak bo‘lmaydi |
| Joriy va qoralama dizaynni farqlash, oldingi variantga qaytish | Yordamsiz bajaradi; qoralama tasodifan nashr bo‘lmaydi |
| Ishni to‘xtatib qaytish, filtr/Back/reload | Saqlangan ma’lumot va kontekst saqlanadi; saqlanmagan holat rost ko‘rsatiladi |

Umumiy maqsad: oldindan belgilangan 8 vazifadan kamida 7 tasi yordamsiz bajarilishi, kritik noto‘g‘ri qaror/yo‘qolgan saqlangan ma’lumot **0**.
Avval ham yakunlash mumkin bo‘lgan bir xil vazifalarning median vaqti bazadan **kamida 30% kamayishi** ko‘zlanadi.
Hozir to‘liq bajarib bo‘lmaydigan yangi modul/dars yaratish uchun vaqt nisbati hisoblanmaydi: baseline muvaffaqiyatsizligi alohida qayd etiladi, yangi oqim yordamsiz yakunlash va yuqoridagi mutlaq vaqt mezoni bilan baholanadi.
Bu chegaralar bazaviy sinovdan keyin owner bilan aniqlashtiriladi. Natija mezonini o‘zgartirish dalil bilan yoziladi.
Avval owner; imkon bo‘lsa yana 3–4 vakolatli kelajak operator. Ishtirokchi soni va tanishlik darajasi ko‘rsatiladi; bitta odam sinovi umumiy usability isboti deyilmaydi.
Yordam berilgan, xato yo‘l tanlangan va orqaga qaytilgan joylar ham qayd etiladi. Test soni va overflow yo‘qligi qulaylik qabuli o‘rniga o‘tmaydi.

## 9. Texnik chegaralar va qaytish

Reja uchun admission: **EXPERIMENT — canonical state yozmaydi**. Natija ownerning uch ishini tezlashtiradigan ko‘rib chiqiladigan taklif.
KPI — yordamsiz bajarish, vaqt va xato. Hozir runtime o‘zgarmaydi; yangi doimiy operatsion yuk qo‘shilmaydi.
Implementatsiyada yangi har bir capability uchun admission, write/read scope, failure va rollback belgilanadi.

- Yangi read projectionlar: birlashtirilgan o‘quvchi kartasi, doiraga mos umumiy qidiruv, Ish stoli xulosasi. Bular shunchaki CSS o‘zgarishi emas.
- Yangi yozish scope: modul/yangi dars authoring bo‘shlig‘i, doimiy design draft/version/preset. Mavjud modellarga mos service va audit/validation bilan quriladi.
- Receipt qarori `receipt_service`, guruh a’zoligi `membership_service`, dars ochilishi `release_service`, tariflar `catalog_service` orqali qoladi.
- UI maydon almashtirgichi, yashirilgan tugma yoki qidiruv hech kimga qo‘shimcha permission bermaydi. Server ruxsat tekshiruvi majburiy.
- AI sozlamalaridagi reason/consent/audit qarzi (A2-D01) ochiq; qayta bezash bilan yopilmaydi. AI bajaruvchi operator qo‘shish bu rejaga kirmaydi.
- Ommaviy qarorlar, universal undo, impersonation, yordam ticketlari, yangi bildirishnoma triggerlari va yangi access qoidasini yashirin qo‘shish yo‘q.
- Muhim amallarda stale/concurrent edit, javob yo‘qolishi, double submit va safe readback saqlanadi. Yangi `Saqlandi` faqat real tasdiq bilan.
- Har real kesim existing flag registryga muvofiq alohida yoqiladi. Rollback rendererni qaytaradi; DB migration yoki amalga oshgan biznes qarorini orqaga aylantirdi deb hisoblanmaydi.
- Qaytishda eski renderer yangi saqlangan holatni o‘qiy olishi tekshiriladi. Migration kerak bo‘lsa expand/contract va backup/recovery rejasi oldindan yoziladi.
- AWS/production deploy, pricing/access siyosatini o‘zgartirish va DESIGN-01ni qabul qilish ushbu reja yozilishi bilan sodir bo‘lmaydi.

## 10. Audit tayanchi

2026-10-10 repo tayanchi `4325ca6`. Tracked Django source va lokal Eleventh Trial alohida tekshirildi; AWS jonli auditi bajarilmadi.

| Tekshirilgan holat | Manba |
|---|---|
| Tracked legacy menyuda biznes, kontent va texnik bo‘limlar bir qatorda; dashboardda RAG/kpi/countlar navbatdan oldin | [backoffice base](../../templates/backoffice/base.html), 35–54-qatorlar; [dashboard](../../templates/backoffice/dashboard.html), 21–52-qatorlar |
| Lokal prototipda owner sahifalari teacher/courses ostida; noto‘g‘ri faol Kurslar belgisi | Lokal `prototype/contracts/registry.json:80–89,125`, `prototype/preview/views.py:87–96`; bu tracked legacy active-link xatosi deb umumlashtirilmaydi |
| Texnik terminlar oddiy sahifada | [control center](../../templates/backoffice/control_center.html), 12–84-qatorlar; lokal `prototype/templates/patterns/operations_ai.html:3–5` |
| Kurs create/edit bor; modul auto-create; dars yaratish oqimi cheklangan | [core views](../../core/views.py), 908–1026-qatorlar; [forms](../../core/backoffice_forms.py), 8 va 72-qatorlar; [URLs](../../core/urls.py) |
| Assignment/quiz legacy admin va oddiy exam editorning chegarasi | [admin](../../courses/admin.py), 207–221 va 550-qatorlar; [core views](../../core/views.py), 1076–1094-qatorlar |
| Read-only odam ro‘yxati, ma’lumot va scope manbalari | [core views](../../core/views.py), 1128–1209; [course access](../../core/access.py); [enrollment](../../cohorts/models.py), 215–325; [teacher context](../../core/teacher_views.py), 168–222 |
| Canonical qarorlar | [receipt](../../cohorts/receipt_service.py), [membership](../../cohorts/membership_service.py), [release](../../courses/release_service.py), [catalog](../../subscriptions/catalog_service.py) |
| AI audit qarzi va real gate | [control prototype](Q16A-CONTROL-PROTOTYPE.md), [core views](../../core/views.py), 1212–1250; source hozir owner-only, eski wiki staff ta’rifi tayanch olinmadi |
| Local design va real port/qabul chegarasi | [DESIGN-01 reja](DESIGN-CUSTOMIZATION-PLAN.md), [DC6 qabul](DESIGN-01-DC6-ACCEPTANCE.md) |

Rejani tekshirish: local havolalar va source mavjudligi; `git diff --check`. Runtime testlari reja uchun qayta yugurtirilmaydi.
Yonidagi bosiladigan namuna faqat taklifning navigatsiyasi va uch ish shaklini tushuntiradi; haqiqiy o‘quvchi ma’lumoti yoki backend amali yo‘q.
