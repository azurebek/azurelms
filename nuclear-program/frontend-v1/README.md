# Frontend V1 — prototipdan ishlaydigan platformaga

Sana: 2026-09-25. Owner qarori: Eleventh Trial birinchi versiya sifatida
qabul qilinadi; yangi prototiplar va jiddiy qayta dizayn vaqtincha to‘xtaydi.
Tayyor qismlar real Django platformasiga ko‘chiriladi; 1-oktyabrda kamida
bitta tugallangan real oqim maqsad qilinadi. Keyin qolgan prototiplarga
qaytiladi. **Bu hujjat ko‘chirish rejasi; ko‘chirish bajarildi degani emas.**

Joriy ijro: [I1 — 3 real sahifa lokal ulandi](I1-LEARNING-SHELL.md),
default OFF; CI/release ochiq. Qolgan I2–I9 navbatlari saqlanadi.

## 1. Qayerdamiz

- [Inventar va barcha manzillar xaritasi](INVENTORY.md): 95 sinov manzili,
  54 noyob page template, 76 real UI/alias URL nomiga moslik.
- Asosiy source inventar: 120 UI/alias + 76 yordamchi endpoint + bitta
  shartli admin mount = 197 leaf. 44 UI/aliasda named prototype hali yo‘q.
- 180 action va 843 route-state **registrlangan**; bu sonlar real integratsiya
  tayyorligi yoki qurilmalarda 100% verifikatsiya degani emas.
- Messenger B alohida tasdiqlangan layout. Uning lokal demo controlleri
  haqiqiy xabar jo‘natish yoki AI adapteri emas.
- [Bajarish va qabul jurnali](PORT-LEDGER.md): qadam faqat dalil bilan yopiladi.

Eski Qxx trackeridagi 4/26 yopiq ko‘rsatkichi tayyor dizayn ulushi emas:
unda UI, real integratsiya va yakuniy qabul aralash hisoblangan. Bundan buyon
**prototip mavjudligi / real kodga ulanganligi / reliz tekshiruvi** alohida
yuritiladi. Avvalgi yopilmagan Qxx bandlari yashirilmaydi yoki soxta yopilmaydi.

## 2. V1 freeze va vakolat

Ownerning joriy yozma qarori avvalgi “barcha UI tugamaguncha G4 boshlanmasin”
navbatini **qisman V1 ko‘chirish** tartibiga o‘zgartirdi. Bu to‘liq G2/G3 PASS
emas: eski to‘liq qamrov gate’lari ochiq, endi har chiqariladigan bo‘lakning
alohida real flow, xavfsizlik va release qabuli bor. D23 umumiy qamrov qoladi;
birinchi relizga hammasi sig‘ishi shart emas. Q14–Q19 yangi prototipi pauzada.

Frozen boshlang‘ich nusxa:

- `C:\Users\azizb\AzureLMS-Backups\Eleventh-Trial-20260925-033842\`
- `Eleventh-Trial.zip`, 614 fayl; original/copy/ZIP ichidagi har fayl SHA256
  bilan tekshirilgan. B variant va D29 tasdig‘i ichida.
- ZIP SHA256: `4AC56E1D29E9D565CCB16E716A5A5A2D8A3C55E72A2653CE9168EA4A6EF33272`.
- Source backend bazasi: `d0cce32eec392717e9bb6d0c1488740bc34b3831`.
- Zaxira o‘zgartirilmaydi. Original trialda faqat qaror/evidence/link hujjatlari
  yangilanadi; yangi vizual variantlar yaratilmaydi. Backup shu fizik diskda.
- `playground/` force-add/push qilinmaydi. Bu katalogdagi hujjatlar — alohida
  integration reja; ignored prototipning kod/assets nusxasi emas.

**Ruxsat etilgan V1 tuzatishlari:** real data/auth bilan bog‘lash, ishlamaydigan
amal, ruxsat xatosi, yo‘qoladigan qoralama, bloklangan mobil asosiy tugma,
CSS/JS to‘qnashuvi. Yangi palitra, yangi framework, funksional scope yoki
biznes qoidani o‘zgartirish bu ko‘chirish vazifasiga kirmaydi.

## 3. Eng avval chiqariladigan natija

**Kirish → mening kurslarim → haqiqiy dars → ruxsatli material**, unga
**ustoz bosh sahifasi → darsni ochish/yopish → o‘quvchidagi natija** juftligi.
Bu I1 + I2. Birinchi release shu bo‘lak tekshirilishi bilan mumkin;
I3–I9 tugashini kutmaydi. Kurs/material tayyorlashning mavjud backoffice’i
hozircha ishlaydi, shuning uchun yangi editorlar birinchi release sharti emas.

| Navbat | Real kodga ulanadigan bo‘lak | Ish hajmi / asosiy qiyinchilik |
|---|---|---|
| I0 | Freeze, inventar, mapping, baseline va ish jurnali | Ushbu hujjatlar; runtime o‘zgarmaydi |
| I1 | Izolyatsiyalangan V1 shell + login + dashboard + kurslarim | O‘rta: eski CSS/JSdan ajratish, ko‘p enrollment/bo‘sh holat |
| I2 | Dars/matn/video/material + ustoz home/release | O‘rta–katta: cohort/access/private file va ikki rolning mosligi |
| I3 | Assignment/quiz → ustoz review; teacher ro‘yxatlar/davomat | Katta: mavjud submission/grade/XP va qayta yuborish |
| I4 | Tasdiqlangan B messenger: guruh/ustoz, keyin AI | Katta: mavjud socket/delivery/upload va AI quota/error adapterlari |
| I5 | Public/auth qoldig‘i, profil/settings, records/help/notifications | Aralash: o‘qish yuzalari osonroq; parol/privacy mutationlari alohida |
| I6 | Material kutubxonasi, kurs/dars boshqaruvining tayyor qismi | Katta: real fayl/scoped form; qisman form mavjud maydonlarni yo‘qotmasin |
| I7 | Checkout → receipt pending/success/difference | Katta/xavfli: real narx, idempotency, pul va access chegarasi |
| I8 | Learner exam → result → ustoz review | Juda katta: timer, answer/audio, draft/publication kontraktlari |
| I9 | Classbook tayyorlash → live session → natija | Juda katta: ko‘p foydalanuvchi, socket/reconnect, turli mashqlar |

I3 assignment/quiz lesson tabsiga tegishli: I2da amaldagi tab funksiyasi
yo‘qotilmaydi. I3 tayyor bo‘lmaguncha existing renderer/controller izolyatsiyasi
sinovdan o‘tadi; bu imkonsiz bo‘lsa **dars sahifasi to‘liq eski rendererda qoladi**,
yarim ishlaydigan yangi dars yoqilmaydi. I2 PASS yozilmaydi; shu bog‘liq I3
qismi tugatiladi. Har navbat yangi muhokama/approval turn talab qilmaydi;
faqat mahsulot qarori yoki yangi tashqi vakolat zarur bo‘lsa so‘raladi.

I5 bitta ulkan PR emas: public/records read-only, auth/account, privacy/preferences
alohida tugallangan bo‘laklar. I4 ham human chat va AI adapterini ajratadi.
Joriy tartib dependency/xavf asosida; qiyin navbat butun relizni ushlab turmaydi.
Tayyor bo‘lmagan yo‘lning hozir ishlayotgan real varianti saqlanadi.

## 4. Uzoq vaqt oladimi?

**Hammasini ko‘chirish sezilarli ish; bu papkani nusxalash emas.** Dizayn va
backend mavjudligi ishni kamaytiradi. Eng katta xarajat: fixture bilan real
view/form contract farqlari, eski assetlar, multi-record holatlar, regressiya
va release. AI/socket/exam/Classbook oddiy o‘qish sahifalaridan ancha murakkab.

Hozir aniq soat/kun va 1-oktyabrga kafolat berish uchun real port tezligi
o‘lchanmagan. I1 — birinchi o‘lchov: qaysi adapter to‘sig‘i chiqdi, nimalar
qayta ishlatildi, nechta test va browser xatosi qoldi — jurnalga yoziladi.
Shundan keyin I2 va keyingi navbat bahosi yangilanadi. Natija mezoni
“nechta fayl ko‘chdi” emas, **real ma’lumot bilan ishlaydigan tugallangan oqim**.

Tezlashtirish: yangi dizayn yo‘q; yangi API faqat zarur contract bo‘shlig‘ida;
backend servislarni qayta yozish yo‘q; har tugma uchun yangi paket yo‘q;
UI+adapter+test bitta mantiqiy bo‘lakda. Test va ruxsatlar evaziga tezlashtirilmaydi.

## 5. Ko‘chirish usuli — shu qoidalar qat’iy

1. **Alohida asset/template namespace:** `templates/frontend_v1/`,
   `static/frontend_v1/`. Eski `base.html`, `static/css/tokens.css`,
   `static/js/app.js` ustiga global almashtirish yo‘q. V1 documentga legacy
   umumiy theme/app controllerlari ikkinchi marta yuklanmaydi.
2. **Bir xil haqiqiy URL:** yangi view tashqi ko‘rinishi tanlanadi, Django
   URL nomlari, real PKlar, query/cohort/next parametrlari saqlanadi.
   `/assets/experiments/` production URL bo‘lmaydi. Demo ID va ism ko‘chmaydi.
3. **Canonical view/service saqlanadi:** `request.user`, enrollment, queryset,
   Django form/error/CSRF, progress/release/grade/payment policy asl manbada.
   Presentation mapper yangi permission/XP/price hisoblamaydi.
4. **Flag orqali qaytish:** `core/flags.py` registrida per-flow V1 flag
   (I1da `frontend_v1_learning` qo‘shildi), default off, mavjud
   audited control yo‘li. Flag faqat renderer tanlaydi, accessni o‘zgartirmaydi.
   Flag o‘chirilganda eski UI+controller qaytadi; rollback ma’lumotni o‘chirmaydi.
5. **Toza runtime:** preview settings/fixtures/state, `/_preview/*`, scenario
   paneli, sample response, demo storage/progress va Messenger Wide demo
   controlleri production bundle’ga kirmaydi. Token/CSS/markup va zarur pure
   util alohida ko‘rib olinadi; preview `app.js` butunlay ko‘chirilmaydi.
6. **Qoralamalar:** user/room/course/record bo‘yicha ajratilgan; logout/account
   almashganda boshqa odamga o‘tmaydi. Form xatosida matn qoladi; password,
   tanlangan fayl yoki audio asossiz saqlangan deb aytilmaydi.
7. **Eski-yangi chegarasi:** ko‘chmagan bo‘lim yashirilmaydi, soxta tugma bo‘lmaydi;
   zarur joyda “Avvalgi ko‘rinishda ochiladi” ochiq aytiladi. Menyu URL/rol
   scope’i saqlanadi. Legacy renderer uchun tests ham ishlashda qoladi.
8. **DB migration boshlang‘ich maqsad emas.** Zarur yangi backend invariant
   chiqsa minimal alohida contract/migration/review; frontend ichida yasama
   receipt/revision yoki access kafolati yaratilmaydi.

## 6. Ko‘rilgan muhim nomuvofiqliklar

| Masala | V1 qarori |
|---|---|
| Kutubxona formida ogohlantirishsiz draft yo‘qoladi | I6 release oldidan tuzatish; qayta dizayn emas, ma’lumot yo‘qotish nuqsoni |
| Prototip 3-dars matni fixture; editor bilan to‘liq bog‘lanmagan | I2da haqiqiy `Lesson`/material context; fixture proyeksiyasini port qilmaslik |
| B variant faqat lokal matn namunasini qo‘shadi | I4 layoutini olish; existing room IDs/socket/private attachment/AI qayta ulash |
| Preview version/operation receipt contracti hamma real viewda yo‘q | Real POST/redirect/GET authoritative natijasi; mavjud bo‘lmagan ackni da’vo qilmaslik |
| Course/lesson preview formasi production formadan kichik | Existing full-form maydonlarini default bilan overwrite qilmaslik; to‘liq xavfsiz mapping bo‘lmasa editor legacy qoladi |
| Existing teacher release invalid cohortdan birinchi cohortga fallback qiladi | I2da explicit target/confirm; noma’lum POST context boshqa guruhga yozmasligi uchun adapter regression |
| Old shell tests klass/nav joylashuviga ham bog‘langan | Yangi approved UI uchun variant-aware assertions; POST logout, role scope va eski variant coverage’ni yo‘qotmaslik |
| Wiki’dagi eski hosting holati | AWS deploy qilinganligi owner fakti; joriy server SHA/config/health bu ishda tekshirilmagan |

## 7. Har bo‘lakni chiqarish shartlari

- Runtime kod + targeted backend/adapter test + desktop/mobile/keyboard
  tekshiruv birgalikda. Bo‘sh, uzun, ko‘p record, begona ID/rol, expired,
  retry/duplicate va validation holatlari tegishlisicha tekshiriladi.
- Mavjud forma, endpoint, permission va natija regressiyasi; yangi renderer
  ON/OFF hamda old/new o‘tishlar. Xavfsizlik yoki asosiy oqim nuqsoni = STOP.
- Local test `.env.local`siz, bo‘sh provider/bot tokenlari bilan. AI/Telegram
  kvota ishlatilmaydi; jonli tashqi test uchun alohida test muhit/vakolat.
- PR uch required CI: SQLite suite, PostgreSQL+pgvector/Valkey, sir/dependency
  skani. `collectstatic`/hashed asset va Django `check` ham o‘tadi. Gate bypass yo‘q.
- Stagingda real test user/cohort/lesson/material, staff va student bilan bitta
  yo‘l; real qurilmada asosiy amal. Yangi UI faqat shu bo‘lak uchun yoqiladi.
- Deploy SHA, health/static/private media, smoke, rollback flag va owner
  go/no-go qaydi. **Staging/AWS vakolat va test account hozir tasdiqlanmagan**;
  bu local implementationni emas, tashqi release’ni to‘xtatadigan aniq gate.
- Ruxsatli kosmetik qarz alohida ro‘yxatda; broken submit, data loss, access
  buzilishi va real bo‘lmagan success “V1 mukammal emas” bahonasi bilan qolmaydi.

## 8. Keyingi agent/turn uchun kirish

`PORT-LEDGER.md`dagi birinchi ochiq band — **I1**. Avval inventardagi uch
source URL/controller va existing testsni o‘qing. Shu flow uchun admission:
**ADMIT — launch-critical**, learner natijasi = haqiqiy hisob bilan o‘z kursiga
barqaror kirish; KPI = login→dashboard→my-courses success + denied access
regressiyasi. Canonical state o‘zgarmaydi; owner yuki oshmaydi; old-renderer
rollback bor. Yangi trial, framework, global shell rewrite yoki DB ko‘chirish
boshlamang. Yangi ish o‘z `codex/` branchida; single checkout saqlanadi.
