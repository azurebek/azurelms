# Frontend V1 — prototipdan ishlaydigan platformaga

Sana: 2026-09-25. Owner qarori: Eleventh Trial birinchi versiya sifatida
qabul qilinadi; yangi prototiplar va jiddiy qayta dizayn vaqtincha to‘xtaydi.
Tayyor qismlar real Django platformasiga ko‘chiriladi; 1-oktyabrda kamida
bitta tugallangan real oqim maqsad qilinadi. Keyin qolgan prototiplarga
qaytiladi. **Bu hujjat ko‘chirish rejasi; ko‘chirish bajarildi degani emas.**

Joriy ijro: [I1 — 3 real sahifa](I1-LEARNING-SHELL.md) PR #120 orqali
`b991a68` bilan main’ga qo‘shildi; uch required CI PASS. Advisory 0,
koddagi default OFF, joriy AWS override quyida. [I2a — dars/material va ustoz release](I2-LESSON-RELEASE.md)
PR #121 bilan main’da (`5528c74`, uch required CI PASS).
[I2b — assignment/quiz](I2B-PRACTICE.md) PR #122 bilan main’da (`c8c3864`),
final required CI `36089727327` uchala PASS. I2 yopildi.
[I3a — teacher navbat/review](I3A-TEACHER-REVIEW.md) PR #123 bilan main’da
(`4e48416`), final CI `36092407070` uchala PASS.
[I3b — teacher ro‘yxatlar/davomat](I3B-TEACHER-DIRECTORY.md) PR #124 bilan
main’da (`9eb3830`), final CI `36162882956` uchala PASS. I3 yopildi.
[I4a — human Messenger B](I4A-HUMAN-MESSENGER.md) PR #125 bilan main’da
(`89f89b7`), final CI `36170298967` uchala PASS.
Owner yangi navbati: [I5a public](I5A-PUBLIC.md) → `azurebek.me` AWS release
qabuli → I4b va qolgan qismlar. Tayyor bo‘laklar qolgan portni kutmaydi.
I5a lokal runtime `74818ee`: 14 public route adapteri va ixcham mobil menu;
1945 Python OK (skip45), 53 Node PASS. PR126 main’da `2787e86`;
image-boundary fix PR127 bilan AWS **`363ff95` deployed**. Dastlab public ON;
keyingi owner ruxsati bilan learning/lesson/teacher/human messenger ham ON.
[Ichki rollout dalili](R1-INTERNAL-RELEASE.md): haqiqiy HTTPS/WSS synthetic
oqim va renderer rollback, mobile/desktop owner sessiyasi tekshirildi.
AWS Hisob/settings hali eski ko‘rinishda. [I5b.1 Profil/Hisob](I5B-ACCOUNT-PROFILE.md)
porti PR131 bilan main’da `af4ed76`; final CI `36196388190` uchala PASS.
[I5c.1 Maxfiylik/To‘lov/Imkoniyatlar](I5C-SETTINGS.md) PR132 bilan main’da
`dd198b7`; final CI `36206802175` uchala PASS, 2000 Python/73 Node.
Review fix `725d47c`: monotonic preference counter va confirmed-ID clear;
additive users0022 migration. AWS deploy alohida.
[I5b.2 Register/reset/onboarding](I5B2-AUTH.md) lokal tayyor `ec0ff27`:
100 focused, 2019 full (skip45), 79 Node; 42 responsive o‘lchov overflow0.
PR133 review fix `ac2d13b`: Telegram-success redirect dirty guarddan chiqadi;
Node82 PASS. PR133 MERGED `75bba33`; final CI36208937362 uchala PASS
(SQLite2019 skip44, PostgreSQL2019 skip20). [Final dalil](https://github.com/azurebek/azurelms/pull/133#issuecomment-5842048014).
[I5d records/help/notifications](I5D-RECORDS-SUPPORT.md) lokal tayyor `d3aa3dc`:
olti route, 2040 full OK (skip45), 508 app OK (skip6), 87 Node PASS,
48 mobile/desktop readback overflow0. PR134 MERGED `337a73c`, final CI
`36211060029` all3PASS (SQLite2040 skip44, PostgreSQL2040 skip20, Node87).
AWS alohida gate. Certificate detail/appendix hanuz legacy.
[I6a — kutubxona](I6A-LIBRARY.md) lokal `9a76fed`: list/create/edit/picker,
canonical upload/private-file/attach va stale-form guard. Library66 OK,
full2063 OK (skip45), Node95 PASS; 24 responsive readback overflow0.
Default-OFF; PR135 MERGED `12b0e3c`, final CI36214042911 all3PASS
(SQLite2063 skip44/PostgreSQL2063 skip20/Node95).
[I6b — kurs/dars muharrirlari](I6B-COURSE-LESSON-EDITORS.md) runtime `c72c1fd`:
besh URL oilasi + material settings/reorder/detach; 111 focused OK,
final2091 full OK skip45, Node95. 30 responsive readback overflow0.
PR136 MERGED `0278331`; final CI36215540990 all3PASS
(SQLite2091 skip44/PostgreSQL2091 skip20). AWS alohida gate.
[I7 — checkout va chek holati](I7-CHECKOUT.md) lokal runtime `3621e9c`:
canonical narx/access, explicit quote va native receipt POST; 262 focused,
2119 full OK skip45, Node95. To‘rt holat × olti width =24 overflow0.
Required CI/main yopiq, AWS release alohida gate.
I7 review fix `f681a5b`: owner-audited DB quote TTL, bounded core0005;
UI/enforcement bitta qiymatdan. Final focused71 PASS, full2126 OK skip45,
PR137 MERGED `df054c1`; CI36217772724 uchala PASS (SQLite2126 skip44,
PostgreSQL2126 skip20/Node95).
[I8a — imtihonlar markazi va natija](I8-EXAMS.md) runtime `2fe920f`:
2156 full OK skip45, 95 Node, 36 responsive readback overflow0. Ownerning
“faqat tasdiqlangan natija” qarori: canonical publication snapshot,
V1/legacy/appendixda qoralama chiqmaydi. Additive courses0021. I8dagi 4
UI oilasidan 2 renderer ulandi; attempt/audio/timer va teacher review UI
hali legacy. PR138 MERGED `17cfc3a`; finalCI36219639823 all3PASS,
SQLite/PostgreSQL2159, Node95; final local2159 OK skip45 (139.635s).
I8b oldidan owner tasdiqlagan [attempt API ruxsat/privacy](I8-API-SECURITY.md)
PR139 MERGED `b8c1604`, CI36221144145 all3PASS (2183 Python/95 Node).
[I8b real topshirish](I8B-ATTEMPT.md) lokal `fc80c7f`/`deef10c`:
explicit save, per-answer revision va receipt, scoped draft, server vaqt,
audio va submit tasdig‘i; additive courses0022, default-OFF. Full2210 OK
skip49; final focused86 OK skip4, Node104. 12 width readback overflow0,
two-tab stale va ikkita unknown-response recovery oqimi brauzerda o‘tdi.
I8b required CI/review/main va native-device/AWS gate ochiq; I8c review UI qoladi.
PR140 P1/P2 review fix `6085156`: bounded cancellation epoch (courses0023),
same-origin audio/preflight va scoped blob CSP. Final local2221 OK skip50,
Node107 PASS; [fresh evidence](I8B-ATTEMPT.md). AWSga chiqarilmagan.
Second review `425ecc3` reading cap/disabled flagni ham tuzatdi: courses265
OK/Node109. Final full2225da existing library same-timestamp ABA1 FAIL;
merge held, ownerga alohida fix savoli berildi. I8b main’da deb qabul qilmang.
Owner roziligidan keyin library guard `453b6dd`da tuzatildi (library0002);
same-clock regression endi PASS. [Qamrov](LIBRARY-ABA.md). Final full2229
OK skip51 (145.501s); fresh CI/review/main acceptance ochiq.
Head110cfd2 CI all3PASS; keyingi review applied-receipt growthni topdi.
Owner-approved `842edb4` [jurnal sig‘imi](EXAM-RECEIPT-BOUND.md)ni auditlangan
sozlamaga chiqardi; fresh full/CI/review kutilmoqda. AWS o‘zgarmadi.
I4b AI adapteri PR #130 bilan main’da `a25cf4b`:
[scope, compact transcript va tekshiruv](I4B-AI-MESSENGER.md).
1961 Python OK/61 Node PASS; final CI `36192585672` uchala PASS;
default-OFF AI flag. AWS AI sahifasi hanuz legacy.
[R1-public dalili](R1-PUBLIC-RELEASE.md): final CI1948×2, zaxira/drill,
clean image, HTTPS/mobile va renderer rollback PASS. Real-device/real-content
qabuli, AI relizi va I5ning qolgan qismlari–I9 ochiq.

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

I3ning learner assignment/quiz tablari I2 bog‘liqligi sifatida **I2b**ga
ko‘chirildi; amaldagi tab funksiyasi yo‘qotilmaydi. I2a vaqtida practice
darsi to‘liq eski rendererda qolgan edi; I2b native form + canonical service
orqali shu bog‘liqlikni yopadi. I3ning teacher review/ro‘yxatlar/davomati
alohida qoladi. Har navbat yangi muhokama/approval turn talab qilmaydi;
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
| Wiki’dagi eski hosting holati | 2026-09-25 AWS SHA/config/health tekshirildi; `363ff95` public relizining fresh dalili [R1-public](R1-PUBLIC-RELEASE.md)da, eski preflight statuslari tarixiy |

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
- Authenticated bo‘lak uchun real test user/cohort/lesson/material, staff va
  student bilan bitta yo‘l; real qurilmada asosiy amal. Staging mavjud emas:
  controlled production test hisobi/dataset uchun owner bilan alohida kelishuv
  kerak. R1-internal uchun tor kelishuv olindi, pilot bajarildi va dataset
  faol ishlashdan chiqarildi. Yangi dataset uchun ruxsatni taxmin qilmang.
- Deploy SHA, health/static/private media, smoke, rollback flag va owner
  go/no-go qaydi. **Public deploy vakolati berildi va reliz bajarildi**:
  zaxira/restore/schema drill, clean image, health/assets va renderer rollback
  dalili [R1-public](R1-PUBLIC-RELEASE.md)da. Bu ishni qayta boshlash kerak emas.
  Keyin ichki rendererlar uchun ham owner vakolati va synthetic account
  pilot olindi: [R1-internal](R1-INTERNAL-RELEASE.md). Qolgan gate — haqiqiy
  device/content qabuli va hali port qilinmagan keyingi bo‘laklarning relizi.
- Ruxsatli kosmetik qarz alohida ro‘yxatda; broken submit, data loss, access
  buzilishi va real bo‘lmagan success “V1 mukammal emas” bahonasi bilan qolmaydi.

## 8. Keyingi agent/turn uchun kirish

Avval git/flag/live SHA holatini fresh tekshiring va
[R1-public reliz dalili](R1-PUBLIC-RELEASE.md)ni o‘qing. I4a PR125 main’da
`89f89b7`, public PR126 `2787e86`, image-boundary PR127 `363ff95` — tugagan;
ularning implementatsiya, initial zaxira yoki rollout ishini qayta boshlamang.
Public/learning/lesson/teacher/human messenger ON; [ichki rollout](R1-INTERNAL-RELEASE.md)
ham bajarildi. Uni yoki synthetic datasetni qayta yaratmang. R1da qolganlari:
real-device/owner-content qabuli, history image/cache xavfi va yangi portlar.
I4b ham PR130 `a25cf4b` bilan main’da; qayta port qilinmaydi.
I5b.1/I5c.1/I5b.2 main’da tugagan; qayta boshlamang. I5d olti route lokal
tayyor, navbat CI/review/main; keyin I6 library/course/lesson editor.
Certificate detail/appendixning legacy chegarasi ochiq, I5 to‘liq yopilmagan.
Yangi AI engine yoki prototip yaratilmaydi. Submission/grade/XP canonical servislar orqali qoladi.
Yangi trial, framework, global shell rewrite yoki DB ko‘chirish boshlamang.
Single checkout saqlanadi.
