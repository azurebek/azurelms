# CLASSBOOK-01 — darsni tayyorlash, olib borish va yakunlash islohoti

**Holat: REJA TAYYOR, IMPLEMENTATSIYA BOSHLANMAGAN.**
2026-10-13; source audit tayanchi `main`dagi **`7cf1cae`**.
Owner topshirig‘i: Classbook qismini radikal takomillashtirish uchun batafsil
reja. Bu hujjat shu ishning yagona batafsil rejasi; umumiy navbat va holat
[loyiha kirishida](../README.md). [B3 backoffice rejasi](BACKOFFICE-REFORM-PLAN.md#backoffice-03)
saqlanadi, ushbu reja bilan bajarilgan yoki bekor qilingan hisoblanmaydi.

## 1. Yakunda qanday mahsulot bo‘ladi?

Classbook o‘qituvchi uchun **dars ish stoli**, o‘quvchi uchun **jonli mashq
xonasi** bo‘ladi. O‘qituvchi bitta dars ichida tayyorlaydi, mashqlarni olib
boradi va kimga yordam kerakligini ko‘radi. O‘quvchi hozir nima qilishini,
javobi qabul qilinganini va nimani yaxshilashini tushunadi.

Asosiy o‘zgarishlar:

- Uzoq guruh/dars ro‘yxati o‘rniga davom etayotgan ish, tanlangan guruh va
  kerakli dars. Barcha guruhlar va tarix qidiruv/filtr orqali ochiladi.
- Maxsus belgilar bilan yoziladigan mashqlar o‘rniga o‘nta turga mos oddiy
  muharrir, tushunarli misol va o‘quvchi ko‘rinishidagi namuna.
- Mashq yaratib boshqa ro‘yxatda qolib ketish o‘rniga ayni darsga qaytish,
  yangi mashqni rejaga qo‘shish va saqlanganini aniq ko‘rish.
- Jonli darsda bitta asosiy mashq va keyingi amal; reyting, batafsil javoblar
  hamda sozlamalar zarur bo‘lganda ochiladi.
- Yakunda faqat ball emas: davomat, javob bermaganlar, qiynalgan savollar,
  ochilgan dars/material va xabar yetkazish holati.

**Chekli qamrov:** quyidagi CB1.1–CB1.8. Birinchi foydali natija CB1.1da
chiqadi; hamma bosqich tugashini kutadigan alohida katta prototip davri yo‘q.
Ownerning keyinga qoldirilgan shaxsiy sinovi texnik ishlarni to‘xtatmaydi.

**Admission natijasi: ADMIT — post-launch.** Bu sakkiz bosqich mavjud
Classbook ustidagi keyingi mahsulot islohoti; avvalgi A3b launch-critical
minimumini qaytadan ochmaydi yoki yangi launch to‘sig‘iga aylantirmaydi.
Bu tasnif production/owner qabuli tugagan degani emas: eski real Telegram,
qurilma va owner gate’lari o‘z holatida qoladi. Owner so‘rovi bilan hozir
reja tayyorlandi; kodlash bu taskda boshlanmaydi. Har bosqich boshlanganda
quyidagi canonical chegara, schema va rollout contracti uning implementatsiya
daliliga bog‘lanadi. CB1.1a shu islohotning birinchi lokal kesimi.

Asosiy KPI — o‘qituvchining darsni texnik yordamsiz tayyorlab, jonli oqimni
muvaffaqiyatli tugatish ulushi; haqiqiy owner o‘lchovi keyingi qabulda.
Learnerning javob holatini aniq bilishi alohida qabul ssenariysi. Texnik maqsad:
§6dagi 12/12 ssenariy, 10/10 muharrir turi, noaniq muvaffaqiyat/data-loss0.
Amal/vaqt baseline bilan solishtiriladi; owner usability natijasi alohida.

| Yangi contract | Canonical egasi va adapterlar | Owner yuki, yoqish/qaytish |
|---|---|---|
| Dars rejasi/policy va tarix — CB1.1 | Classbook service + session/history modeli; web, bot, admin | Takroriy qo‘lda kelishtirishni kamaytiradi; eski ochiq session compatibility, CB1.8 gate |
| Server qoralamasi/preview — CB1.2–3 | Classbook preparation service/form/validator; teacher web, ruxsatli admin | Har mashq uchun texnik yordam talab qilmaydi; bounded retention, preview no-write, draftni o‘chirmaydigan rollback |
| Close/reveal va receipt — CB1.4–5 | Classbook lifecycle/submit service + response; web, bot finish, learner HTTP/socket | Har uzilishda qo‘lda javob tekshirishni kamaytiradi; versionli service contract, eski response compatibility |
| Hisobot va yordam — CB1.6 | Mavjud response/attendance/release/outbox ustidagi read projection | Yangi nazorat jadvali yoki qo‘lda ikki joyda yozish yo‘q; mavjud owner replay, read-only fallback |

Flag va qaytarish talablari CB1.8da majburiy; yangi persistent contract
renderer flagi bilan chetlab o‘tilmaydi. Yangi AI/provider xarajati yo‘q.

## 2. Audit: nima tayyor, aynan nima yetishmaydi?

Bu jadval kod va hujjat o‘qishidan olingan. Ushbu reja uchun yangi browser,
real Telegram, DB yoki production tekshiruvi bajarilmadi. Kuzatilgan kod
yo‘li foydalanuvchida o‘lchangan vaqt yoki qayta ko‘rsatilgan nosozlik emas.

| Mavjud tayanch yoki topilma | Manba | Rejadagi javob |
|---|---|---|
| 10 deterministic mashq, server baholashi, `ActivityRun` snapshot, bitta qabul qilingan javob, realtime/polling mavjud. | [models](../../classbook/models.py), [grading](../../classbook/grading.py), [services](../../classbook/services.py) | Shu imkoniyatlar ustiga qulay oqim; yangi baholash tizimi qurilmaydi. |
| Bosh sahifa barcha faol guruhlarning darslarini yoyadi; bankda qidiruv/filtr/pagination yo‘q. | [views](../../classbook/views.py) `teacher_home`, `exercise_list`; [home](../../templates/frontend_v1/classbook/teacher_home.html) | CB1.1 ish stoli, CB1.2 qidiriladigan bank. |
| 10 tur bir textarea orqali: `*`, `chap = o‘ng`, `Kategoriya: element`. | [forms](../../classbook/forms.py) `HELP_BY_KIND`, `ExerciseForm`; [muharrir](../../templates/frontend_v1/classbook/exercise_form.html) | CB1.2 alohida maydonlar va qatorma-qator xato. |
| Yangi mashq yaratish dars/guruh kontekstini olib bormaydi; saqlash bankka qaytaradi. | [views](../../classbook/views.py) `exercise_edit`; [dars formasi](../../templates/frontend_v1/classbook/playbook_form.html) | CB1.3 dars ichida yaratish va xavfsiz qaytish. |
| Tayyorlik status orqali tekshiriladi; umumiy tekshiruv/yozuvsiz repetitsiya yo‘q. Bo‘sh mashq rejasi ataylab ruxsat etilgan. | [services](../../classbook/services.py) `start_class_session`; [I9a](I9A-PREPARATION.md) | CB1.3 aniq sabab va tuzatish havolasi; faqat davomat/material darsi saqlanadi. |
| Mavjud activity snapshoti saqlanadi, ammo resume hozirgi rejadagi yetishmagan tartiblarni qo‘sha oladi; finish release/homework/ism e’lonini o‘zgargan playbookdan oladi. | [services](../../classbook/services.py) `_ensure_activity_runs`, `start_class_session`, `finish_class_session` | CB1.1a butun boshlangan dars rejasi va yakun siyosatini mahkamlash. |
| Jonli ustoz oynasida barcha mashqlar, reyting va yakun birga; V1 tayyorlov matnida hali “avvalgi ko‘rinish”, “snapshot”, “playbook” bor. | [teacher session](../../templates/frontend_v1/classbook/teacher_session.html), [playbook](../../templates/frontend_v1/classbook/playbook_form.html) | CB1.1 til; CB1.4 markazda joriy mashq. |
| Learner home → dars → mashq → natija o‘rtasida o‘tadi. Noma’lum submit natijasi GET bilan tekshiriladi, ammo receipt yo‘q; reload javob qoralamasini tiklamaydi. | [live JS](../../static/frontend_v1/js/classbook-live.js), [I9b contract](I9B-LIVE.md) | CB1.5 yagona xona va server tasdiqlagan aniq yuborish holati. |
| Poll webda baholanmaydi, lekin shaxsiy Telegram natija matni umumiy ball/to‘g‘ri javob shablonidan o‘tadi. | [services](../../classbook/services.py) `_publish_activity_notifications`; [natija](../../templates/frontend_v1/classbook/activity_result.html) | CB1.6 web/Telegram ma’nosini moslashtirish. |
| Session ro‘yxati/CSV hozirgi faol enrollmentlardan tuziladi, reytingda tarixiy javoblar bor. Guruhdan chiqish eski hisobotdagi qatnashchini yo‘qotishi mumkin. | [views](../../classbook/views.py) `_session_context`, `teacher_session_export`; [services](../../classbook/services.py) `session_leaderboard` | CB1.1a tarix shartnomasi; CB1.6 izchil hisobot. |
| Kirish/material formasi birgalikda 3500 escaped belgi qabul qiladi; yuborishda har matn alohida 1400da qisqaradi. | [models](../../classbook/models.py) `LessonPlaybook.clean`; [services](../../classbook/services.py) `_material_text` | CB1.3 yuboriladigan matnning aynan o‘zi bilan preview va aniq limit xabari. |
| PostgreSQL 50 parallel submit, stale/replay, reveal privacy, socket revocation testlari bor. | [load](../../classbook/test_load.py), [V1 live](../../classbook/test_frontend_v1_live.py), [realtime](../../classbook/test_realtime.py) | Yopilgan gate qaytadan “yo‘q” deyilmaydi; CB1.7 to‘liq 50 client oqimini o‘lchaydi. |

Oldingi ishlangan port va sanali sinovlar: [I9a](I9A-PREPARATION.md),
[I9b](I9B-LIVE.md), [ko‘chirish ledgeri](PORT-LEDGER.md).
[Launchdagi real guruh/telefon qabuli](../launch-plan/03-mahsulot-backlog.md)
hamon alohida. R2 HTTPS smoke real jonli dars qabuli emas.

## 3. Sahifalar va foydalanuvchi yo‘li

### O‘qituvchi

| Yuza | Birinchi ko‘rinadigan mazmun | Asosiy amal |
|---|---|---|
| **Darslarim** | Ochiq dars, davom ettiriladigan tayyorlov, guruh tanlovi va qisqa dars ro‘yxati | Davom ettirish / darsni tayyorlash |
| **Dars rejasi** | Guruh+dars, ketma-ket mashqlar, tayyorlik; “Mashqlar”, “Material va vazifa”, “Sozlamalar” bo‘limlari | Mashq qo‘shish / sinab ko‘rish / boshlash |
| **Mashqlarim** | Qidiruv, kurs, dars, tur; qisqa namunali kartalar | Yaratish / darsga qo‘shish / nusxa olish |
| **Darsni olib borish** | Hozirgi mashq, vaqt, qabul qilingan javoblar, keyingi qadam | Mashqni ochish / javoblarni yopish / natijani e’lon qilish |
| **Dars hisoboti** | Umumiy natija, o‘quvchilar, savollar, davomat va yuborish holati | Muammoni ko‘rish / tegishli yordamga o‘tish |

Bu beshta teng og‘ir menyu emas: asosiy kirish **Darslarim**, bank va tarix
ikkinchi darajada. Dars tanlangach guruh/dars sarlavhasi va ortga yo‘l barcha
ichki ekranlarda saqlanadi. Mavjud URL/deep-linklar ishlashda davom etadi.
Backoffice kurs/darsidan tayyorlashga kirish va qaytish mavjud ruxsat hamda
qaytish shartnomalarini ishlatadi; Classbook course quiz/assignmentni almashtirmaydi.

### O‘quvchi

**Jonli darsga kirish → ustozni kutish → joriy mashq → javob qabul qilindi →
natija va tushuntirish → keyingi mashq → dars xulosasi.**

Bitta xonaning holatlari sifatida ko‘rsatiladi. Keyingi mashq kelishi yozayotgan
javobni, audio yoki fokusni o‘z-o‘zidan uzmaydi; “Keyingi mashq tayyor” aniq
amal bo‘ladi. Reyting ikkinchi darajada, shaxsiy javob holati birinchi o‘rinda.

### Atamalar va holatlar

| Hozir uchraydigan atama | Asosiy UI matni |
|---|---|
| Playbook | Dars rejasi |
| Exercise bank | Mashqlarim |
| Activity/session/snapshot | Mashq / jonli dars / shu darsda ishlatiladigan nusxa |
| Queued / open / closed / revealed | Navbatda / javob qabul qilinmoqda / javoblar yopildi / natija e’lon qilindi |
| Retry/reconcile/stale | Holatni tekshirish / sahifada yangiroq o‘zgarish bor |

Texnik izoh diagnostikada qoladi. “Saqlash” — tayyorlovni saqlash,
“Boshlash” — haqiqiy darsni ochish va xabarni navbatga qo‘yish. “Yuborildi”
faqat yetkazish dalili bo‘lsa ishlatiladi; “o‘qildi” degan yangi da’vo yo‘q.
“Tayyor” ham botning ayni damda yetkazishini kafolatlamaydi.

## 4. O‘zgarmaydigan mahsulot va xavfsizlik chegaralari

- [Owner strategiyasi](../launch-plan/01-strategiya.md) bo‘yicha jonli video
  Telegram video chatda qoladi. Classbook ichida yangi videokonferensiya yo‘q.
- `TelegramLessonSession`, `ActivityRun`, `StudentResponse`, attendance/XP,
  release, `Notification` va outbox canonical bo‘lib qoladi. UI o‘zicha
  ball, kirish, davomat yoki xabar yuborish qoidasi yaratmaydi.
- Bitta ochiq activity, bitta qabul qilingan javob; deadline serverniki.
  Javob kaliti reveal oldidan learnerga chiqmaydi; grading serverda.
- Teacher faqat o‘ziga ruxsatli kurs/guruhni, learner faol ruxsatini ko‘radi.
  Tarixni saqlash bekor qilingan learner accessini qayta ochmaydi.
- Hozirgi mashq turlari va baholash ma’nosi saqlanadi: poll baholanmaydi;
  matnni taqqoslash, qisman ball va tezlik bonusini “chiroyli UI” sabab
  yashirincha o‘zgartirish yo‘q. Ular sodda misol bilan tushuntiriladi.
- Operatsion vaqt/limit DB sozlamasida, yoqish/o‘chirish flag registrida;
  ikki xil truth yo‘q. Sozlama mutatsiyasi sabab, tasdiq, no-op va audit bilan.
  Har oddiy matn tahririga ortiqcha modal qo‘shilmaydi; tashqi ta’sirli
  start/reveal/finish aniq natija va server tekshiruviga ega.
- Yangi AI generation/AI grading, kalendar/eslatma, speaking engine,
  adaptiv kurs, o‘quvchi bahosini qo‘lda qayta hisoblash, faol mashqqa vaqt
  qo‘shish/pause va boshqa kursga ommaviy import CB1 qamrovi emas.
  Hozir haqiqiy dars jadvali yo‘q: soxta “bugun 20:00” kartasi yaratilmaydi.
- Umumiy dizayn tokenlari qayta ishlatiladi; mustaqil ikkinchi theme tizimi yo‘q.
  Har yangi o‘qituvchi yoki learner sirtida light/dark, tor ekran va katta matn bor.

## 5. Bosqichlar: ish, bog‘liqlik va tugash mezoni

### CB1.1 — ishonchli dars holati va tushunarli kirish

**CB1.1a — birinchi ish, UI’dan oldingi zarur poydevor.**

- Startda mashqlar ketma-ketligi va yakun sozlamalarini (release, uyga vazifa,
  ism e’loni va tegishli matnlar) session uchun bir marta mahkamlash.
  Bank/reja tahriri keyingi darsga tegishli; resume yangi qadam qo‘shmaydi.
  Web va `/dars` bitta servis shartnomasidan o‘tadi.
  `frontend_v1_live.session_revision` ham joriy playbookni emas, sessionga
  mahkamlangan contractni kuzatadi; kelajak reja tahriri live actionni eskirtirmaydi.
- Tarixiy qatnashchilar uchun qoida: startdagi ro‘yxat, keyin haqiqiy qatnashganlar
  va yakundagi davomat qarori yo‘qolmaydi. Hisobot bu dalillarni ajratadi;
  faol membership esa har yangi kirish/javobda qayta tekshiriladi. O‘rtada
  kelgan/chiqqan o‘quvchining bahosi yoki attendance qoidasi yashirin o‘zgarmaydi.
- Additive schema zarurati va barcha writerlar (web/bot/admin) xaritasi yoziladi.
  Eski session uchun tarixiy roster/policy o‘ylab topilmaydi: dalil yo‘q bo‘lsa
  “tarixiy tarkib to‘liq saqlanmagan”. Yoqishdan oldin eski ochiq sessionlar
  eski contract bilan tugatiladi yoki aniq versionli compatibility yo‘lida qoladi.
- Native adminning live snapshot/status, response, outbox holati va add/delete/
  inline yo‘llari ham shu chegaraga kiradi: operatsion yozuvlar read-only yoki
  canonical audited action orqali. Faqat yangi UI’ga guard qo‘yish universal
  himoya deyilmaydi; arbitrary SQL/bulk write ushbu kafolatni chetlab o‘tadi.

**CB1.1b — ko‘rinadigan birinchi natija.** Darslarim, bitta guruh filtri,
qidiruv/pagination, ochiq darsga qaytish, qisqa holatlar va yangi atamalar.
Tanlangan darsni qayta izlash talab qilinmaydi; barcha darslar birdan yoyilmaydi.
Baseline uchun 3 guruh/100 dars/1000 mashq synthetic ma’lumoti: ayni darsga
kirish, mashq qo‘shish, start→reveal→finish yo‘lidagi sahifa almashish/amal
soni va davomiylik qayd qilinadi. Keyin ayni fixture/muhit bilan solishtiriladi;
bu sonlar production limit yoki hozir o‘lchangan natija emas.

**Tugashi:** reja tahriri→resume→finish sinovida boshlangan dars ma’nosi
o‘zgarmaydi; yangi dars yangilangan rejani oladi; eski sessionlar o‘qiladi;
faol ruxsatni bekor qilish ishlaydi. Start/resume/finish ikki marta bajarilishi
takroriy attendance/XP/release/xabar yaratmaydi. Asosiy uch yo‘l bosh sahifada
ko‘rinadi. Keyingi CB1.2–CB1.6 shu contract ustida quriladi.

### CB1.2 — o‘nta tur uchun kodsiz mashq muharriri

**CB1.2a:** bank, kurs/dars/tur filtri, namunali tur tanlash, single/multiple
choice, true/false, poll. **CB1.2b:** short answer, fill blank, matching,
ordering, categorization, unscramble. Ikkinchi kesim tugamaguncha “10 tur
kodsiz tayyor” deyilmaydi.

| Tur | Yangi boshqaruv |
|---|---|
| Bitta / ko‘p javobli tanlov | Variant qatorlari, radio/checkbox bilan to‘g‘ri javob |
| To‘g‘ri / noto‘g‘ri | Ikki aniq tanlov |
| Qisqa javob / bo‘sh joy | Qabul qilinadigan javoblar ro‘yxati; mavjud bitta javob sloti semantikasi |
| Moslashtirish | Chap va o‘ng kataklar juftligi |
| Tartiblash / so‘z yig‘ish | Qatorlar va yuqoriga/pastga tugmalari; drag ixtiyoriy |
| Kategoriyalar | Kategoriya nomi va uning elementlari |
| So‘rov | Variantlar; javob kaliti/ball boshqaruvi ko‘rsatilmaydi |

- Savol, tushuntirish, rasm/audio oddiy maydonlar; vaqt/ball/bonus “Qo‘shimcha
  sozlamalar”da. O‘lcham/tur xatosi ayni maydonda. Media keep/replace/clear
  va eski snapshot ishlatgan faylning saqlanishi hisobga olinadi.
  Mazmunli rasm tavsifi authoring va snapshotga birga qo‘shiladi; audio uchun
  matnli muqobil answer/reveal siyosatini chetlab o‘tib erta ko‘rsatilmaydi.
- UI canonical config/answer_key validatoriga ulanadi. Eski textarea orqali
  yaratilgan mashqlar yo‘qotishsiz ochiladi; round-trip barcha 10 turda tekshiriladi.
  Tur almashtirish saqlanmagan variant/keyni jimgina yo‘qotmaydi: mos bo‘lmagan
  maydonni bekor qilish explicit yoki qayta tiklanadigan tanlov bo‘ladi.
- Chala tayyorlov uchun alohida server qoralamasi: actor+course+item/revision
  scope, cheklangan son/hajm va sozlanadigan expiry. Qoralama tayyor Exercise
  deb olinmaydi; “saqlanmoqda/saqlandi/saqlanmadi” haqiqatga mos.
  Javob kaliti localStorage, URL yoki telemetriyaga yozilmaydi. Fayl tanlovi
  qayta yuklashdan keyin tiklandi deb va’da qilinmaydi.
- Bir xil learner renderer orqali yozuvsiz preview; server baholash namunasi
  haqiqiy response/session, XP, attendance yoki Telegram yaratmaydi.

**Tugashi:** har tur texnik sintaksissiz create→xato→tuzatish→preview→save→
reopen yo‘lidan o‘tadi; eski data/key teng; chala qoralama ruxsatli userga
tiklanadi; stale tahrir boshqa tab ishini bosmaydi. Turkish harflar,
apostrof, bo‘sh variant va uzun matn; choice→matching→back, invalid/save/reload
regressiyasi bor.

### CB1.3 — darsni bitta joyda yig‘ish va sinab ko‘rish

CB1.1 va muharrirning tegishli turi tayyor bo‘lishiga bog‘liq.

- Dars rejasi ichidan yangi mashq yaratish, bankdan namuna bilan tanlash,
  tartiblash va faqat rejadan olib tashlash. Saqlashdan keyin ayni dars va
  qadamga qaytish; shared mashqni tahrirlash boshqa kelajak rejalariga ta’sir
  qilishini ko‘rsatish. “Alohida nusxa” yangi Exercise yaratadi.
  Mavjud `teacher_note` ustozga xususiy qadam eslatmasi sifatida ochiladi;
  yig‘indi mashq vaqti ko‘rsatiladi, butun dars davomiyligi deb talqin qilinmaydi.
- Shu kursdagi oldingi dars rejasidan nusxa: qadamlar/sozlama, yangi qoralama;
  session, learner javobi, ball, attendance yoki xabar nusxalanmaydi.
  Mos kelmaydigan lesson/media ruxsati fresh tekshiriladi, bo‘sh targetni
  egallash yoki mavjud rejani overwrite qilish avtomatik emas.
- Material va vazifa mavjud kurs/dars obyektlariga bog‘lanadi; Classbookdagi
  vazifa xabari LMS Assignment yaratildi degani emas. Yuboriladigan Telegram
  matni ayni canonical formatter bilan ko‘rsatiladi; yashirin kesilish o‘rniga
  cheklov yoki oldindan ko‘rinadigan qisqartirish bo‘ladi.
- Tayyorlik: guruh bog‘langanmi, kontent validmi, fayl bormi, ochiq dars
  bormi, yakunda nima ochiladi. To‘suvchi sabab, ogohlantirish va ixtiyoriy
  tavsiya ajraladi; mashqsiz davomat/material darsi valid qoladi.
- “Darsni sinab ko‘rish” o‘qituvchi/o‘quvchi namunasini yonma-yon yoki
  navbat bilan ochadi. Repetitsiya real session, xabar yoki learner data yozmaydi.

**Tugashi:** mashq yaratish uchun bankka chiqib yo‘l yo‘qolmaydi; copy/remove/
reorder asliga va o‘tgan natijaga tegmaydi; previewdan hech qanday operatsion
yozuv chiqmaydi; start fresh holatni qayta tekshiradi. CB1.1 pinning previewda
ko‘rsatilgan dars ma’nosini start transactionigacha himoya qiladi.

### CB1.4 — ustoz uchun diqqat markazidagi jonli boshqaruv

CB1.1 holat shartnomasi va CB1.3 tayyor darsdan boshlanadi.

- Markazda joriy mashq, vaqt va “qabul qilingan javob / ruxsatli qatnashchilar”.
  Qisqa keyingi mashq, yonida ochiladigan reja. To‘liq reyting/javoblar alohida
  panelda; mobil ekranda bittadan. “Davomat”, “javob yubordi”, “ulanish holati”
  bir xil son sifatida talqin qilinmaydi; aniq presence dalilisiz “onlayn” yo‘q.
- “Javoblarni yopish” va “Natijani e’lon qilish” ajraladi. Mavjud
  `close_activity(publish=False)` servisi qayta ishlatiladi, ammo viewdagi
  doimiy publish=True, closed learner 404, result gating va stale-action
  tekshiruvlari bir kesimda moslashtiriladi. Yopilgan mashqni ochib yuborish yo‘q.
- Primary amal holatga mos. Xabar yuborishga/bahoni ko‘rsatishga ta’sirli
  harakatda aniq oqibat va tasdiq; oddiy panel ochish bunday tasdiq talab qilmaydi.
- Yakun oldidan davomat, hali ochiq mashq, release va vazifa oqibatlari
  ko‘rsatiladi. Yakun ortga qaytariladigan oddiy navigatsiya tugmasi emas.
  Yangi alohida close holati uchun qaror: finish ochiq va yopilgan, ammo hali
  e’lon qilinmagan mashqlarning natijasini bir marta e’lon qiladi; umuman
  boshlanmagan mashq uchun natija yasamaydi. Shu taklif qilingan kengayish
  web/bot canonical finishda birga quriladi, previewda oldindan ko‘rinadi.
  Yangi contractdagi session yopilgach kechikkan reveal takroriy no-op yoki
  rad javobi; yashirin yangi e’lon yo‘q. Eski closed-unrevealed sessionlar
  compatibility holatida alohida ko‘rsatiladi, migratsiya ularni e’lon qilmaydi.
- Ikki ustoz tabida yangi holat haqida bildirish; fresh revision olmasdan
  eski tugma ishga tushmaydi. Javoblar soni o‘sishi actionni keraksiz eskirtirmaydi.

**Tugashi:** open→close without reveal→discuss→reveal→next→finish hamda
open va closed-unrevealed activity bilan finish sinovlari; 0 javob/kech javob/takroriy bosish/
boshqa tab boshqaruvi izchil. Teacher kutish holatini ko‘radi; learnerga
nashr etilmagan kalit/ball chiqmaydi. Har bir real amal server auditi bilan.

### CB1.5 — o‘quvchi xonasi va uzilishdan tushunarli qaytish

CB1.4 holatlari hamda canonical submit contractga bog‘liq.

- Kutish/mashq/qabul/natija/keyingi qadam bir xona ichida. Mavjud deep-link
  aniq mashqni ochadi; katta kartalar, klaviatura bilan to‘liq ishlaydigan
  10 renderer, aniq xato va rasm/audio holati. Avtomatik sahifa almashish yo‘q.
- Aloqa uzildi, login eskirdi, access bekor qilindi, vaqt tugadi, dars yopildi
  va javob tekshirilmoqda turli holat. Yordam faqat ruxsatli ma’lumotni aytadi.
- **Yuborish tasdig‘i:** canonical submitga actor+activity+snapshotga bog‘langan
  operation ID va javob fingerprinti qo‘shiladi; qabul qilingan response bilan
  bitta transactionda saqlanadi. Shu ID/boshqa payload rad qilinadi, bir xil
  operatsiya oldingi javobni qaytaradi. Boshqa tabning javobi “aynan shu
  yuborishingiz” deb ko‘rsatilmaydi. Raw answer audit/URLda bo‘lmaydi.
  Receipt qo‘shilishidan oldingi response faqat “javob mavjud” dalili;
  unga soxta operation ID bog‘lanmaydi. Browserdagi identifikator actor/sessiya
  almashganda va expiryda tozalanadi; uning o‘zi access token bo‘lmaydi.
- Timeoutdan keyin GET bilan receipt tekshiriladi; natija noma’lum paytda
  avtomatik qayta POST yo‘q. Tasdiqlanmagan javob DOMda qoladi. Reload/crash
  uchun faqat maxfiy javobsiz operation identifikatori va mavjud response
  tiklanadi; yuborilmagan learner qoralamasini doimiy offline saqlash CB1da
  va’da qilinmaydi. Ochiq va hali qabul qilinmagan amalni explicit retry qilish
  faqat shu operationning idempotent shartnomasi isbotlangach ochiladi.
- Taymer server-time offset bilan ko‘rsatiladi; internet qaytganda server
  vaqti va holati qayta olinadi. Kech javobni
  orqaga vaqt qo‘yib qabul qilish, qurilma vaqtiga ishonish yoki grade almashtirish yo‘q.

**Tugashi:** submit oldida/undan keyin uzilish, server qabul qilib javobi
yo‘qolishi, ikki tab, deadline, reload va permission revoke holatlari aniq
ko‘rinadi; bitta response va bir xil ball. Qayta kirish boshqa odamning
receiptini ko‘rsatmaydi. Offline submit muvaffaqiyatli deb ko‘rsatilmaydi.

### CB1.6 — foydali dars xulosasi va muammodan yechimga yo‘l

CB1.1 tarix shartnomasi, CB1.4–CB1.5 holatlaridan foydalanadi.

- Ustoz: qatnashganlar, javob bermaganlar, savol bo‘yicha xatolar/taqsimot,
  o‘quvchi kesimi. Javob bermaganlik 0 ball bilan javob berganlikdan farq qiladi.
  Aniqlik va tezlik bonusi ajratiladi. Yangi subyektiv “zaif o‘quvchi” reytingi yo‘q.
- O‘quvchi: o‘z javobi, e’lon qilingan to‘g‘ri javob, mavjud tushuntirish,
  shu darsning material/vazifasiga yo‘l. Shaxsiy natija asosiy; mavjud
  leaderboard visibility qoidasi saqlanadi, peer private javoblar ochilmaydi.
- Poll web va Telegramda so‘rov natijasi bo‘lib qoladi; noto‘g‘ri/to‘g‘ri,
  0/0 ball yoki baholanadigan mashq da’vosi berilmaydi.
- Yakun sahifasida attendance yozildi, dars ochildi/sozlamada o‘chirilgan,
  vazifa xabari navbatda/yuborilgan/xato alohida. Group delivery bilan
  individual DM aralashtirilmaydi. Eski xabarlarda “o‘qildi” taxmin qilinmaydi.
  Yetkazish at-least-once: Telegram qabul qilgach DB qaydi oldidan worker
  to‘xtasa takror xabar ehtimoli bor; UI exactly-once yetkazishni va’da qilmaydi.
- Ruxsatli foydalanuvchi mavjud support/attendance/release/dead-letter
  sahifasiga aniq context bilan o‘tib qaytadi. Owner-only replay teacherga
  berilmaydi; ikkinchi yuborish yoki tuzatish writeri yaratilmaydi.
- Tarix filtrlari va eksport bir xil cohort/session/qatnashchi dalilini oladi;
  keyingi transfer/withdrawal eski bahoni o‘chirmaydi. CSV formula injection,
  access va private-media himoyasi saqlanadi.

**Tugashi:** web/CSV/Telegramdagi bir mashq bir ma’noni beradi; noto‘liq
legacy tarix aniq belgilanadi; yopiq sessionni qayta ochish yozuv yaratmaydi;
supportga o‘tish va qaytish ayni o‘quvchi/darsni saqlaydi. Yetkazish xatosi
baholash yoki attendance xatosi deb ko‘rsatilmaydi.

### CB1.7 — ko‘p qatnashchi, telefon va to‘liq foydalanish qulayligi

Har bosqich o‘z testini topshiradi; bu kesim umumiy oqim va kesishmalarni tekshiradi.

- 50 parallel submit gate qayta saqlanadi. Ustiga 50 learner client + teacher,
  reconnect/polling + group/DM navbatining birgalikdagi synthetic sinovi.
  Har javob eventi barcha clientda GET uyg‘otadigan hozirgi yo‘l o‘lchanadi;
  keraksiz refresh coalesce/debounce va hidden-tab budget bilan kamaytiriladi.
  Correctness, request soni, queue yoshi va p50/p95 vaqtlar qayd qilinadi;
  o‘lchanmagan “real-time tez” yoki 50 real telefon dalili e’lon qilinmaydi.
- 320/390/768/1440px, 200% matn, landscape, uzun Uzbek/Turkish matn,
  light/dark; asosiy sahifada gorizontal scroll yo‘q. Drag yagona usul emas.
- Klaviatura, label/fieldset, fokus tartibi va qaytishi, xato summary,
  live region. Timer har soniyada screen readerni gapirtirmaydi; rang
  holatning yagona belgisi emas. Audio bekor qayta yuklanmaydi/autoplay qilinmaydi.
- Browser/node test, DB/service integration va PG races alohida dalil;
  haqiqiy Android/iOS, Telegram WebView, native zoom va screen reader mavjud
  bo‘lsa tekshiriladi, bo‘lmasa **OPEN** qoladi. Emulation ularning o‘rnini bosmaydi.

**Tugashi:** critical privacy/data-loss blocker0; barcha o‘nta tur va asosiy
holatlar matrixi to‘liq; oldingi service guardlari saqlangan; o‘lchovlar va
aniq muhit bir hisobotda. Native/owner ochiqligi texnik PASSga yashirilmaydi.

### CB1.8 — bosqichma-bosqich yoqish va yakuniy paket

- Preparation/live mavjud flaglari bilan compatibility xaritasi. Yangi
  contract flagi kerak bo‘lsa registryda bitta maqsad, default OFF, in-flight
  xatti-harakat va rollback yo‘li bilan. Renderer flagOFF yangi policy/receipt
  talabini eski writer orqali aylanib o‘tishga ruxsat bermaydi.
- Additive migration, backup/restore nusxada; eski session/response o‘qilishi,
  yangi sessionversion va eski code mosligi tekshiriladi. UI rollback schema
  yoki learner natijasini o‘chirmaydi; mos bo‘lmagan eski releasega ko‘r-ko‘rona qaytilmaydi.
- Avval synthetic alohida DB va providersiz muhit, keyin lokal ruxsatli
  pilot. Haqiqiy guruh xabari/yakun/attendance tajribasi alohida aniq qamrov
  bilan; reja yozishning o‘zi real guruhga yozish yoki deploy ruxsati emas.
- Required CI, review, hujjat/qo‘llanma va support runbook; owner uchun
  tayyor sinov darsi hamda qisqa “qayerdan boshlash” yo‘riqnomasi.

**Tugashi uch xil qayd qilinadi:** (1) CB1 muhandislik ishlari tayyor,
(2) owner/haqiqiy qurilma/Telegram qabuli, (3) aniq muhitga reliz.
Birining bajarilishi qolgan ikkisini avtomatik yopmaydi.

## 6. Tekshiruv ssenariylari va dalil formati

| № | Boshidan oxirigacha ssenariy | Asosiy dalil |
|---|---|---|
| 1 | Guruh/darsni topish → tayyorlash → chiqish → ayni joydan davom | Aniq yo‘l, fresh scope, GET no-write |
| 2 | O‘nta mashq turini yaratish/xato/preview/qayta ochish | 10/10; definition/grade semantikasi teng |
| 3 | Mashq va dars rejasini nusxalash, tartiblash/olish | Asl kontent va tarix o‘zgarmagan |
| 4 | Repetitsiya → tayyorlikdagi xato → tuzatish → start | Namuna no-write, real start bitta |
| 5 | Reja tahriri → web/bot resume → finish | Boshlangan session policy va mashqlari o‘zgarmagan |
| 6 | 50 learner javobi + teacher close/reveal | Bitta response; client/server natija mos; transport o‘lchovi |
| 7 | Uzilish/unknown/reload/ikki tab/deadline | Receipt to‘g‘ri; auto-resend yo‘q; ball dublikat emas |
| 8 | Publish qilmay close → kutish → reveal → next | Javob kaliti/izoh/ball erta chiqmagan |
| 9 | Finish → attendance/release/homework/DM holatlari | Canonical yozuvlar va xabar navbati ajralgan |
| 10 | Transfer/withdrawal → tarix/CSV/support | Tarix dalili saqlangan, joriy access yopilgan |
| 11 | Poll, mashqsiz dars, javobsiz dars, unavailable media | Tushunarli to‘liq holatlar, soxta natija yo‘q |
| 12 | Mobil/katta matn/klaviatura/flagOFF/stale tab | Oqim tugaydi; yashirin yozuv yoki data-loss yo‘q |

Har bosqichda tegishli focused testlar; umumiy CB1.7–CB1.8da:

```powershell
$env:APP_ENV = 'local'
$env:LOCAL_USE_REMOTE_SERVICES = 'False'
$env:AZURELMS_SKIP_ENV_FILE = '1'
$env:GEMINI_API_KEY = ''
$env:TELEGRAM_BOT_TOKEN = ''
venv/Scripts/python.exe manage.py check --fail-level WARNING
venv/Scripts/python.exe manage.py makemigrations --check --dry-run
venv/Scripts/python.exe manage.py test classbook bot cohorts courses core --noinput
node --test tests/frontend_v1/*.test.mjs
git diff --check
```

Bu kelajakdagi buyruqlar; ushbu reja ishida app suite bajarildi degani emas.
PostgreSQL race/load required CI’da; SQLite skip PASS dalili o‘rnini bosmaydi.
API/provider kalitlari testda ishlatilmaydi. Har hisobot: commit, flag/muhit,
ssenariy, natija, skip, screenshot/measurement manzili va ochiq qabul.

## 7. Bajarish tartibi, hajm va yakun chegarasi

| Bosqich | Bog‘liq | Hajm/xavf | Ko‘rinadigan natija |
|---|---|---|---|
| CB1.1a → CB1.1b | Source contract | Katta; session/history compatibility | Ishonchli dars va sodda kirish |
| CB1.2a → CB1.2b | CB1.1 scope/revision | Katta; 10 tur/secret draft/media | Kodsiz tayyorlash |
| CB1.3 | CB1.1 + tegishli CB1.2 | O‘rta–katta; copy/preview/start | To‘liq dars rejasi |
| CB1.4 | CB1.1 + CB1.3 | Katta; state/reveal | Qulay jonli boshqaruv |
| CB1.5 | CB1.4 holatlar | Katta; transport/receipt/access | Bitta o‘quvchi xonasi |
| CB1.6 | CB1.1/4/5 | O‘rta–katta; tarix/xabar parity | Foydali natija va yordam |
| CB1.7 | Har bir kesim bilan, yakuni CB1.6dan keyin | Katta; real oqim/accessibility | Birgalikdagi sifat dalili |
| CB1.8 | CB1.7 | Muhitga bog‘liq | Lokal yakun va reliz paketi |

Bu **sakkiz bosqichli, bir nechta PRdan iborat ish**, bitta dizayn tahriri
emas. Kalendar deadline yoki o‘lchanmagan “5 daqiqada dars tayyorlash” va’dasi
berilmaydi. CB1.1a yakunida migration/compatibility hajmi, CB1.2a yakunida
muharrirning qolgan turlari hajmi aniqroq qayd qilinadi; yangi talab paydo
bo‘lsa CB1ni cheksiz kengaytirmasdan alohida navbatga yoziladi.

**Keyingi amaliy ish — CB1.1a:** session rejasi/policy va tarix shartnomasi,
regression holatlari, additive model/service kesimi; so‘ng CB1.1b Darslarim.
Owner har bir ekran nomini tanlab berishi shart emas. Agent qulay variantni
qurib, ishlaydigan oqim va dalil bilan taqdim etadi.

**CB1 muhandislik yakuni:** sakkiz bosqichning lokal texnik exitlari, 12
ssenariy va required CI/review yopilgan, qaytarish yo‘li tekshirilgan,
hujjatlar mos. Owner shaxsiy qabulining keyinga qolishi yoki real qurilma
mavjud emasligi nomi bilan ochiq turadi. B3, public UX/DATA/RULE, A9 va
productionning boshqa gate’lari bu yakun bilan avtomatik yopilmaydi.
