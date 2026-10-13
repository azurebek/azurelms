# Backoffice islohoti — uch asosiy ishni osonlashtirish

**2026-10-12 — faol navbat: [BACKOFFICE-02 — kundalik ishlarni yakunlash](#backoffice-02).**
Owner shaxsiy tekshiruvini keyinga qoldirib, takomillashtirish uchun yangi phase
rejasini so‘radi. Bu qabulni o‘tdi deb belgilamaydi va yangi ishni boshlashni
to‘xtatmaydi. Birinchi islohotning tayyor qismlari [asosiy lokal bazada ON](BACKOFFICE-LOCAL-ROLLOUT.md).
Quyidagi 2026-10-10 xaritasi tarixiy tayanch; hali mavjud bo‘lmagan capability
va qolgan ishlarga oid joriy qaror hujjat oxiridagi BACKOFFICE-02 bo‘limida.

2026-10-10. **Birinchi bosqich xaritasi va 2–5-bosqich runtime kesimlari qurildi; 6-bosqich ekspert tekshiruvi bajarildi.**
[Ikkinchi bosqich](BACKOFFICE-REFORM-STAGE-2.md): Boshqaruv, modul/dars yaratish,
material, namuna va guruhga ochishga ulanish. Flag default OFF; owner usability
va production qabuli ochiq.
[Uchinchi bosqich](BACKOFFICE-REFORM-STAGE-3.md): o‘quvchi qidirish → kurs/dars
bo‘yicha sabab → aniq mavjud qaror sahifasi → qayta tekshirish. Flag default OFF.
[To‘rtinchi bosqich](BACKOFFICE-REFORM-STAGE-4.md): kodsiz dizayn ustaxonasi;
[beshinchi bosqich](BACKOFFICE-REFORM-STAGE-5.md): qolgan bo‘limlar yagona menyuda.
[Oltinchi bosqich](BACKOFFICE-REFORM-STAGE-6.md): T1–T8 synthetic browser
sinovi, olti amaliy tuzatish va flag qaytish regressiyasi. Insonning vaqtli
qabuli, native qurilma va production rollout alohida ochiq.
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
| **Qolgan backoffice — runtime kesimi qurildi** | [Bosqich 5](BACKOFFICE-REFORM-STAGE-5.md): To‘lovlar, Blog/SIT, Guruhlar va Sozlamalar bir xil menyu; tarif/guruh alohida, texnik tafsilotlar ochiladigan bo‘limlarda | [Eski-yangi action xaritasi](BACKOFFICE-REFORM-STAGE-5-MAP.md), scoped GET markazlar, mavjud writer/ruxsat/audit pariteti. Bosqich 6da rendered kirishlar, rol/flag kombinatsiyalari va OFF/ON qaytish tekshirildi; ownerning yordamsiz topish hamda qolgan mustaqil yuzalar qabuli ochiq |
| **Qabul va bosqichli port — ekspert tekshiruvi bajarildi** | [Bosqich 6](BACKOFFICE-REFORM-STAGE-6.md): T1–T8 synthetic browser sinovi, olti amaliy tuzatish, 16 flag kombinatsiyasi va saqlangan holatni OFF/ONda o‘qish | Agentning amaliy dalili mavjud; insonning vaqtli/yordamsiz natijasi o‘lchanmagan. Required CI/review integration gate; native qurilma, production rollout va DESIGN-01 DC6 qabuli alohida |

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

<a id="backoffice-02"></a>
## 11. BACKOFFICE-02 — kundalik ishlarni yakunlash

**Holat: B2.1–B2.3 lokal tayyor (2026-10-13); B2.4–B2.6 reja.**
[B2.1 dalili](BACKOFFICE-02-STAGE-1.md), [B2.2 dalili](BACKOFFICE-02-STAGE-2.md),
[B2.3 dalili](BACKOFFICE-02-STAGE-3.md).
Reja sanasi 2026-10-12; kod tayanchi
`cd2ce2c`. Yangi phase shu hujjatda yuritiladi; parallel roadmap ochilmaydi.
Owner topshirig‘i: shaxsiy usability sinovini keyinroq bajaradi, shu vaqtgacha
backoffice’ni takomillashtirish davom etadi. Mavhum menyu so‘rovnomasi yoki
har bir kichik qadam uchun owner tasdig‘i talab qilinmaydi.

### Nima tugagan, nima qolgan

Yagona menyu, kurs/modul/dars yozish, material qo‘shish, kirish sababini topish,
kodsiz dizayn qoralama/nashr/tarix va eski formalarni soddalashtirish mavjud.
2026-10-12 lokal rollout tayyor kodni asosiy bazada yoqdi; yangi authoring
capability yoki barcha yuzalar dizayn paritetini yaratmagan.

**Faqat owner sinovi qolmagan.** Quyidagi source audit yangi ish uchun tayanch.
Manbada topilgan xato hali bu turn davomida brauzerda qayta yaratilgan degani emas;
B2.1 avval uni regressiya testi bilan qayta ko‘rsatadi, keyin tuzatadi.

| Joriy fakt | Manba (`cd2ce2c`) | Yangi ish |
|---|---|---|
| Materialning xatoli legacy POST’i redirect qiladi, kiritilgan qiymat yo‘qoladi; reorder validatsiyasi V1 holatiga bog‘langan | [material writerlari](../../library/backoffice_views.py):344–435, [eski dars formasi](../../templates/backoffice/lesson_form.html) | B2.1 — bound xato va rendererga bog‘liq bo‘lmagan validatsiya |
| Kurs ustaxonasida upload/attach bor; biriktirmaning ko‘rinishi, sanasi, tartibi va uzish amali shu yerda yo‘q | [kurs yuzasi](../../templates/backoffice/workspace/course.html):38–41, [library usage havolasi](../../templates/backoffice/library_form.html):71 | B2.1 — mavjud amallarni dars kontekstida yakunlash |
| Bo‘limi yo‘q imtihonda section form majburiy tekshiriladi, lekin uning maydonlari/xatolari render qilinmaydi; kirish birinchi imtihonni tanlaydi | [exam view](../../core/views.py):1168–1178, [exam form](../../templates/backoffice/exam_form.html):40–62 | B2.1 — bo‘sh holat va aniq tanlash |
| Assignment/quiz modellari bor, oddiy backoffice’da ularni yaratish yo‘li yo‘q; admin odatda o‘chiq | [modellar](../../courses/models.py):277,958,981,1010, [eski dars](../../templates/backoffice/lesson_form.html):42–46, [authoring service](../../courses/authoring_service.py) | B2.2 — cheklangan yangi authoring |
| Ish stoli so‘nggi yaratilgan 6 kursni oladi; oxirgi ochilgan darsni bilmaydi. Kurs qidiruvi faqat kurs nomiga qaraydi | [workspace](../../core/backoffice_workspace.py):104–127, [Ish stoli](../../templates/backoffice/workspace/home.html) | B2.3 — topish va haqiqiy davom ettirish |
| O‘quvchi kartasi darsga kirish tashxisiga qurilgan; umumiy natija va xabar yetkazish diagnostikasi yo‘q | [support service](../../core/student_support_service.py):53, [karta](../../templates/backoffice/workspace/student.html) | B2.4 — ikkita chegaralangan o‘qish oqimi |
| Dizayn writeri va 87 typed sozlama mavjud; eski formalar matn/radiuslari ba’zan literal, theme geometry asosan V1/workspace klasslariga ulangan | [editor uslubi](../../static/backoffice/editor-forms.css):2–12,38, [theme projection](../../static/backoffice/design-runtime.css):26–34 | B2.5 — mavjud sozlamalarni eski formalarga ulash |

### Maqsad va qat’iy qamrov

Asosiy natija: owner kursni tayyorlash, o‘quvchining muammosini aniqlash va
ko‘rinishni moslash ishlarini oddiy backoffice orqali yakunlay oladigan texnik
imkoniyatlarni to‘ldirish. Yangi menyu tizimi yoki uchinchi backoffice qurilmaydi.

**Asosiy texnik KPI:** quyidagi o‘nta aniq ssenariy dalil bilan bajariladi,
kiritilgan/saqlangan ma’lumot yo‘qolishi, yolg‘on muvaffaqiyat xabari va
ruxsatsiz ko‘rinish/yozish — **0**. Bu insonning tezligi yoki yordamsiz
foydalanish natijasi emas. Oldingi 7/8 va vaqt mezonlari owner sinovi uchun
keyinga qoldiriladi; o‘lchanmaguncha foizli yaxshilanish da’vo qilinmaydi.

### Olti bosqich va tugash mezoni

| Tartib | Owner ko‘radigan natija | Shu bosqich tugash mezoni |
|---|---|---|
| **B2.1 — Kursdagi uzilishlarni yopish** | Tanlangan dars ichida material ko‘rinishi/sanasi/tartibini o‘zgartirish va darsdan uzish. Xato kiritilgan matnni yo‘qotmaydi. Kursga mos imtihonni aniq tanlash yoki birinchi bo‘limi bilan yaratish | Invalid/stale POST’da DB yozuvi va success xabari yo‘q; qiymat va xato ko‘rinadi. Detach umumiy faylni o‘chirmaydi. Bo‘shdan imtihon+bitta bo‘lim saqlanadi; urinishsiz ko‘p bo‘limli imtihonda tanlangan bo‘lim tahriri boshqasini o‘zgartirmaydi. Urinish bor imtihonning baholash/tarkib/vaqt sozlamalari himoyalangan. Kurs/dars/qoralama konteksti saqlanadi |
| **B2.2 — Topshiriq va oddiy test tayyorlash** | Dars ichida topshiriq nomi/sharti/XP, bir javobli variantli test savollari/variantlari/to‘g‘ri javobini yaratish va ruxsatli tahrirlash | Bitta topshiriq va uch savolli test create→save→reopen→yozuvsiz namuna orqali o‘tadi. Chala savol saqlanmaydi; xato ayni savolda. Boshqa kursga yozish, eskirgan tahrir va takroriy yaratish himoyalangan. Mavjud submission/attempt/baho/XP o‘zgarmaydi |
| **B2.3 — Topish va davom ettirish** | Boshqaruvda kurs, dars, o‘quvchi va bo‘limni bitta qidiruvdan topish. Ish stolida ayni sessiyada oxirgi ochilgan ishga qaytish | Natija obyekt turi va kursini ko‘rsatib, ayni dars/kartaga olib boradi. Begona scope natijasi chiqmaydi. Filtr, tanlangan dars va Back konteksti saqlanadi. “Davom ettirish” haqiqiy ochilgan ish; yangi yaratilgan kurs soxta recent activity bo‘lmaydi |
| **B2.4 — O‘quvchiga yordamni kengaytirish** | Mavjud “Darsga kira olmayapti” yonida “Topshiriq/natija” va owner uchun “Bildirishnoma yetmagan” | O‘quvchi/kurs tanlovi yo‘qolmasdan submission holati, tekshiruv va o‘quvchiga ochilgan natija farqlanadi. Xabar yo‘q/navbatda/yuborilgan/xato farqlanadi. Tegishli mavjud amal sahifasidan qaytgach ayni odam qayta tekshiriladi; ko‘rish hech qanday baho, yuborish yoki read belgisini yozmaydi |
| **B2.5 — Dizaynning ichki formalarda bir xilligi** | Mavjud matn, tugma/maydon/karta shakli va oralig‘i sozlamalari eski imtihon, kutubxona, tarif/guruh, blog va SIT backoffice formalarida ham ishlaydi. Oddiy ustaxonada shu formaning namunasini ko‘rish | Har belgilangan formadagi computed qiymat mavjud typed sozlamaga mos. Yorug‘/qorong‘i, 320px va kattalashtirilgan matnda o‘qiladi. Publish→real forma→rollback o‘tadi; flag OFF statik ko‘rinishni qaytaradi. Logo/kontent dizayn rollback’i bilan o‘zgarmaydi |
| **B2.6 — Birgalikdagi sifat tekshiruvi** | Yuqoridagi ishlar katta/kichik ekranda, klaviaturada, xato va qaytish holatlarida izchil ishlaydi | O‘nta ssenariy, rol/flag/saqlash regressiyasi, xato matni/fokus, 320/768/1440px, light/dark va 200% matn tekshiruvi dalilli. Texnik tafsilotlar oddiy ishga chiqmaydi. Critical yo‘qolish/ruxsat/yolg‘on success topilmasi qolmaydi; har cheklov aniq qayd etiladi |

B2.1 birinchi real implementatsiya bo‘ladi: qayta inventar yoki yangi maket
phase’i kerak emas. Qolgan ketma-ketlik yuqoridagicha; har bosqich ishlaydigan
natija bilan yopiladi. B2.2 ikki kichik kesimda — topshiriq, keyin variantli
test — topshiriladi; ikkalasi bitmaguncha B2.2 yopilmaydi.
Topilgan unrelated feature ushbu ro‘yxatga jimgina qo‘shilmaydi.

### Implementatsiya shartnomalari

#### B2.3 admission — 2026-10-13

**ADMIT — launch-critical.** Ownerning «davom et» topshirig‘i bilan kurs,
dars, o‘quvchi va ruxsatli bo‘limni bitta qidiruvdan ochish hamda ayni
sessiyada oxirgi ochilgan ishga qaytish quriladi. KPI: 6-ssenariy — qidiruv
→ ayni dars → boshqa bo‘lim → davom ettirish; begona natija va soxta recent 0.
Canonical manbalar `teacher_course_queryset`, `support_student_queryset`
va mavjud navigatsiya registri; yangi qidiruv faqat o‘qiydi. Fresh active
staff/owner ruxsati, ota kurs va destination flaglari tekshiriladi.
Kontent, baho, enrollment va progress yozilmaydi. Recent faqat actor va
sessiyaga tegishli obyekt IDlari hamda cheklangan tanlovlardan iborat;
ism, aloqa ma’lumoti yoki qoralama matni saqlanmaydi. Ochishda ruxsat va
mavjudlik qayta tekshiriladi. Qidiruv/listga qaytish konteksti URL orqali
chegaralangan va tasdiqlangan manzilga boradi; tashqi redirect yo‘q.
Haftalik yuk kamayadi: qayta-qayta bo‘lim va dars qidirish kerak bo‘lmaydi.
Mavjud `backoffice_unified_navigation` OFF yangi qidiruv/recentni yopadi;
saqlangan kontent va eski kirishlar qoladi. Noto‘g‘ri so‘rovda sodda xato,
bo‘sh natijada aniq qaytish yo‘li; sahifalash va chegaralangan so‘rovlar.
Migration, yangi provider, production va qurilmalararo tarix qamrovda yo‘q.
Sinovlar alohida synthetic bazada; owner bazasiga sinov kontenti yozilmaydi.

#### B2.2 admission — 2026-10-13

**ADMIT — launch-critical.** Ownerning «davom et» topshirig‘i bilan darsga
topshiriq va bir javobli test tayyorlash yo‘li quriladi. KPI: 4–5 ssenariy
create → save → reopen → yozuvsiz namuna orqali o‘tadi; chala savol,
ruxsatsiz yoki eskirgan tahrir va takroriy yaratishda noto‘g‘ri yozuv 0.
`courses/authoring_service.py` Assignment/Quiz/Question/Choice uchun yagona
writer; yangi scoped HTTP adapter faqat uni iste’mol qiladi. Submission va
grading `submission_service`da qolib, birinchi topshirish ham authoring bilan
bir parent lock ostida tekshiriladi. Har qanday submission/attempt mavjud
kontentni o‘qish rejimiga o‘tkazadi; murakkab eski testlar o‘zgartirilmaydi.
Audit va kontent bir transactionda. Saqlash amaldagi dars kontentini yangilashi
oldindan ko‘rsatiladi; preview progress/attempt/XP/release yaratmaydi.
Haftalik admin yuki kamayadi; yangi xizmat yoki provider ishlatilmaydi.
`backoffice_practice_authoring` registry gate’i default OFF; render va yangi
writer ikkalasini yopadi. OFF saqlangan learner kontentini o‘chirmaydi.
Invalid/stale so‘rovda bound maydonlar va sabab qaytadi, yozuv yo‘q.
Rollback shu gate bilan; tekshiruv synthetic bazada, asosiy lokal yoqish
faqat nusxadagi dalildan keyin. Production va ishlatilgan kontentni
versiyalash bu kesimga kirmaydi.

#### B2.1 admission — 2026-10-13

**ADMIT — launch-critical.** Ownerning «boshla unda» topshirig‘i bilan kursdagi
material va imtihon uzilishlari yopiladi. KPI: yuqoridagi 1–3 ssenariy ishlaydi;
invalid/stale so‘rovda ma’lumot yo‘qolishi, yolg‘on success va scope buzilishi 0.
Material update/detach/reorder uchun `library` canonical service, exam va section
uchun `courses/exam_authoring_service.py` atomik writer ishlatiladi; legacy/V1
va kurs ustaxonasi faqat adapter. Attempt boshlash shu imtihon yozuvi bilan
bir lock chegarasida tekshiriladi. Audit yozuvi mutation bilan bir transactionda.
Haftalik yuk kamayadi: material sozlamasi dars ichida, bo‘sh imtihon yaratish
texnik yordam talab qilmaydi. Mavjud `backoffice_course_workspace` flagi
ustaxona yuzasini boshqaradi; OFF eski yo‘lni va saqlangan kontentni qoldiradi.
Validatsiya, ruxsat va ishlatilgan imtihon himoyasi renderer flagidan mustaqil.
Failure: bound forma va aniq xato, stale holatda yozuvsiz 409; detach umumiy
resource/faylni o‘chirmaydi. Rollback: ustaxona flagini OFF qilish; yangi
kontent mavjud modellarda eski yo‘ldan o‘qiladi. Xavfli tahrirni qayta ochuvchi
kod rollback’i bu qaytish shartnomasiga kirmaydi. Tekshiruvlar synthetic bazada;
production/provider amali, yangi grading qoidasini joriy qilish qamrovda yo‘q.

2026-10-12 reja admissioni: **EXPERIMENT — canonical state yozmaydi**. O‘sha
turn faqat manba auditi va reja edi; runtime o‘zgarmagan. B2.1 yuqoridagi
aniq admission bilan boshlandi. Quyidagi qolgan admissionlar tavsiya,
bajarilgan capability emas.
Har bosqich boshida uning aniq xizmat/ruxsat/failure shartnomasi qayd qilinadi;
ownerning keyingi “B2.Nni boshla” topshirig‘i shu kesim ishini boshlatadi.

| Kesim | Admission tavsiyasi va asosiy KPI | Canonical manba / writer | Haftalik yuk va qaytish |
|---|---|---|---|
| B2.1 | ADMIT — launch-critical; darsdan chiqmay material ishini xatosiz yakunlash | `library.services` va mavjud material writerlari; atomik exam/form yozuvi uchun yagona service ajratish. Web adapter. Yangi baholash/release qoidasi yo‘q | Texnik yordam kamayadi. Workspace flag OFF va eski yo‘l yangi holatni o‘qiydi; validatsiya/ruxsat tuzatishi renderer flagi bilan o‘chmaydi |
| B2.2 | ADMIT — launch-critical; topshiriq va oddiy testni admin’siz tayyorlash | `Assignment`, `Quiz`, `Question`, `Choice`; yangi authoring komandalarini `courses/authoring_service.py`da birlashtirish. Submission/grading `submission_service`da qoladi | Yashirin admin yuki kamayadi. Yangi writer uchun registryda default-OFF gate; render va POST ikkalasi yopiladi, yaratilgan kontent saqlanadi |
| B2.3 | ADMIT — launch-critical; qidiruvdan ayni obyektga bevosita kirish | `teacher_course_queryset`, `support_student_queryset`, ruxsatli route registry. Recent state canonical kontent emas; actor+sessiya doirasidagi obyekt IDlari | Qayta qidirish kamayadi. Unified-navigation flag OFF oddiy menyuga qaytaradi; mavjud sahifalar va URLlar qoladi |
| B2.4 | ADMIT — launch-critical; natija/yetkazish sababini ma’lumot bilan ajratish | `AssignmentSubmission`, quiz attempt, `exam_publication.learner_result`, `Notification` va `TelegramOutbox` read projection. Qaror writerlari o‘z joyida | Qo‘lda bir necha panelni tekshirish kamayadi. Support flag bilan yangi o‘qish yuzasi yopiladi; baho/xabar holati o‘zgarmaydi |
| B2.5 | ADMIT — launch-critical; bitta mavjud sozlama barcha belgilangan formalarda mos qiymat beradi | `design_schema`/`design_service`/public CSS; mavjud legacy klasslarga token bog‘lash. Yangi theme engine yo‘q | Har forma uchun qo‘lda tuzatish kamayadi. Design flag OFF statik uslub; rollback faqat dizayn versiyasini almashtiradi |
| B2.6 | ADMIT — launch-critical; 10/10 texnik ssenariy, kritik xato 0 | Yuqoridagi canonical manbalar; QA alohida synthetic baza va browser | Yangi doimiy xizmat/navbatchilik yo‘q. Har kesim o‘z gate’i va oldingi renderer bilan qayta tekshiriladi |

Muhim tafsilotlar:

- **Material:** update/detach/reorder writerlari hali adapterda qolgan joyda
  workspace uchun nusxa yozilmaydi; umumiy servicega chiqariladi. Bir xil tartib
  raqamining mavjud deterministic tie qoidasi saqlanadi; duplicate POST kaliti
  bilan bir xil raqam ikki xil tushuncha. Invalid input ikkala rendererda rad etiladi.
- **Imtihon:** B2.1 metadata va mavjud section form maydonlari bilan chegaralanadi;
  savollar, reading/listening bloklari yoki yangi baholash engine’i emas. Exam
  va section bir transactionda saqlanadi; birinchi obyektni yashirin tanlash yo‘q.
  Har qanday `ExamAttempt` bor imtihonning baholash, tarkib, vaqt/audio chekloviga
  ta’sir qiluvchi maydonlari birinchi kesimda read-only; faqat tugagan urinishlar
  emas. Server yozish va attempt boshlash o‘rtasidagi race’ni ham tekshiradi.
  Ikki bo‘limni mustaqil tahrirlash sinovi urinishsiz fixture’da bajariladi.
- **Assignment/test:** mavjud modellar to‘liq draft/publish/version lifecycle’i
  bor deb olinmaydi. Preview hech qanday attempt, progress yoki XP yaratmaydi.
  Har qanday `QuizAttempt` — hatto `QuizAnswer` bo‘lmasa ham — quiz/savol/variant/XP
  tahririni bloklaydi. Assignment uchun har qanday statusdagi submission hisobga
  olinadi, faqat approved emas. Bu birinchi writerda ishlatilgan kontent xavfli
  tahrir/o‘chirishga ochilmaydi; read-only sabab va aniq keyingi yo‘l ko‘rsatiladi.
  Yangi test writeri faqat `lesson`ga bog‘langan quiz, bo‘sh bo‘lmagan savol va
  variantlar, kamida ikki variant va aynan bitta `is_correct`ni tekshiradi.
  Bu modelning hozirgi kafolati emas, yangi authoring service validatsiyasi.
  Exam’ga bog‘langan, ikki ota obyektli yoki mos kelmaydigan eski savollar
  avtomatik aylantirilmaydi; o‘qish uchun saqlanadi. Saqlashdan oldin
  amaldagi darsga ta’sir ko‘rsatiladi. Student submit bilan authoring race’i ham
  tekshiriladi; xizmat lock/revision shartnomasi kerak bo‘lsa additive migration
  alohida yoziladi. “Faqat UI, migration bo‘lmaydi” degan oldindan kafolat yo‘q.
- **Qidiruv/recent:** matn va shaxsiy xabar tanalari indekslanmaydi; keyword va
  parent nomi yetarli. Natija sahifalanadi, qator soniga qarab N+1 so‘rov ko‘paymaydi.
  Recent state’da qoralama mazmuni/contact yozilmaydi; chiqish/almashtirilgan login,
  o‘chirilgan obyekt va bekor qilingan ruxsat qayta tekshiriladi. Boshqa qurilmada
  avtomatik davom ettirish bu kesimga kirmaydi.
- **O‘quvchi yordami:** teacher faqat o‘z kursidagi ish/natijani ko‘radi; xususiy
  baholash drafti “o‘quvchi ko‘ryapti” deb berilmaydi. Bildirishnoma modelida
  majburiy kurs bog‘lanishi yo‘q, shu sabab yetkazish tafsiloti dastlab owner-only.
  Raw Telegram ID, xabar tanasi, provider error yoki chat mazmuni ochilmaydi.
  `sent` — yetkazish yozuvi, o‘qiganlik yoki muammo hal bo‘lganligi isboti emas.
  Bu yerda yuborish/qayta yuborish, bahoni tasdiqlash va account impersonation yo‘q.
- **Dizayn:** yangi CSS kiritish yoki drag-and-drop builder yo‘q. Mavjud 87 typed
  parametrdan tegishlisi ishlatiladi. Bitta qo‘shimcha inert legacy-form namuna;
  nashrsiz haqiqiy o‘quvchi holatiga yozish yo‘q. Uchinchi tomon CKEditor toolbar’i,
  rasmning o‘zi va print alohida chegaralangan; qamrov UI’da sodda aytiladi.

### O‘nta yakun ssenariysi

1. Materialning noto‘g‘ri sanasini yuborish → yozgan qiymat qoladi → xatoni tuzatish → ayni darsda saqlash.
2. Material tartibini o‘zgartirish → namuna → darsdan uzish; umumiy kutubxona fayli boshqa darsda qoladi.
3. Imtihonsiz kursdan yangi imtihon+bitta bo‘lim yaratish; urinishsiz ikki bo‘limli fixture’da ikkinchisini tahrirlash birinchisini o‘zgartirmaydi. Urinish mavjud bo‘lsa xavfli tahrir yozishsiz rad etiladi.
4. Darsga topshiriq yaratish → saqlash → qayta ochish → yozuvsiz o‘quvchi namunasi.
5. Uch savolli bir javobli test yaratish → xato javob konfiguratsiyasini tuzatish → saqlash → qayta ochish/namuna; javobsiz attempt ham tahrirdan himoyalaydi, mavjud learner natijasiga tegilmaydi.
6. Dars nomini qidirish → ayni kurs/dars → boshqa bo‘lim → ayni sessiyadagi “Davom ettirish”; begona rol yozuvi chiqmaydi.
7. O‘quvchining topshirgan ishi/nashrdagi natijasini topish → kerakli mavjud ko‘rib chiqish sahifasi → ayni kartaga qaytish va recheck.
8. Owner o‘quvchining bildirishnoma holatini ajratadi; o‘qish hech qanday xabar yubormaydi yoki read belgisini o‘zgartirmaydi.
9. Matn va tugma shaklini sozlash → nashr → exam/library/catalog/blog/SIT backoffice formalarida computed qiymat → rollback.
10. Yuqoridagi oqimlarda 320px/klaviatura/200% matn, invalid/stale/Back/reload va flag OFF/ON; saqlangan kontent va ruxsatlar saqlanadi.

Asosiy lokal owner bazasiga sinov topshiriq/natija/xabar yozilmaydi. Read-only
smoke va faollashtirish nusxadagi isbotdan keyin; real provider chaqirish bu
phase’ning avtomatik tekshiruviga kirmaydi. Tests: changed-app va canonical
service regressiyasi, kerakli Node tests, browser action; docs-only rejaga
`git diff --check` va ichki havolalar tekshiruvi yetarli. Owner/teacher/begona
teacher/inactive/anonymous, CSRF, replay va stale matritsasi yangi writerlar uchun.

### Qachon tugaydi va nimalar alohida qoladi

**BACKOFFICE-02 texnik jihatdan tayyor** — B2.1–B2.6 natijalari va o‘nta
ssenariy bajarilgan, tegishli CI/review o‘tgan, qaysi muhitda yoqilgani va
qaytish yo‘li qayd etilgan. “Hamma uchun qulay” qabuli bilan aralashtirilmaydi.
Muddati hozir o‘lchanmagan; keyingi kesimning haqiqiy hajmi B2.1 natijasida
aniqlashadi. Belgilangan olti bosqichni tugatish mezoni cheksiz yangi dizayn
talablarini qo‘shib surilmaydi.

Quyidagilar alohida kuzatiladi va B2 ishlarini boshlash sharti emas:

- **Owner qabuli:** owner keyinga qoldirdi; so‘ralganida uch asosiy ish bilan
  qisqa amaliy sinov. Oldingi DC6 ham o‘tdi deb belgilanmaydi.
- **Haqiqiy qurilma/zoom/AT:** mavjud muhitdagi browser viewport va matn sinovi
  agent tomonidan bajariladi. Native zoom imkoni bo‘lsa alohida dalil olinadi;
  shriftni ikki baravar qilish native zoom deb yozilmaydi. Haqiqiy telefon va
  screen reader dalili olinmagan bo‘lsa OPEN bo‘lib qoladi; owner usability
  sinovining o‘zi bilan ham avtomatik yopilmaydi.
- **Production rollout:** internetdagi muhit uchun backup, migration, xizmat
  konfiguratsiyasi va real smoke alohida reliz. Lokal ON production ON emas.

Keyingi alohida capability navbati: to‘liq ko‘p bo‘limli imtihon savol/reading/
listening muharriri; ishlatilgan kontentning keng versiyalash siyosati; mustaqil
SIT/Mini App theme porti; vendor/print moslash; AI sozlamalarining A2 audit qarzi.
Ular “faqat owner sinovi qoldi” jumlasi bilan yashirilmaydi, lekin B2 scope’iga
yashirin qo‘shilmaydi. Universal undo, bulk payment/access qarori, CRM ticket,
AI operator yoki yangi pulli provider ushbu rejada yo‘q.
