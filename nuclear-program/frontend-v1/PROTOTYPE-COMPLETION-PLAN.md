# Qolgan prototiplar — aniq qamrov va tugatish rejasi

**2026-09-27–28 ijro:** Q14 U01/U02, Q15a U03–U06, Q15b U07–U11, Q16a U12–U19,
Q16b U20/U21, Q17a U22–U24, Q17b U25–U34, Q18 U35–U39 va Q19
U40/U41/H01–H03 va Q08 U42 lokal qurildi:
[Paket67](Q14-EXAM-EDITOR-PROTOTYPE.md), [Paket68](Q15A-DAILY-BACKOFFICE-PROTOTYPE.md),
[Paket69 dalili](Q15B-CATALOG-PROTOTYPE.md), [Paket70 dalili](Q16A-CONTROL-PROTOTYPE.md),
[Paket71 dalili](Q16B-BRAND-LANDING-PROTOTYPE.md), [Paket72 dalili](Q17A-BLOG-STUDIO-PROTOTYPE.md).
Joriy son **139 named URL /77 template /118 source nomi +3 handler diagnostic**.
Boshlang‘ich inventarda prototipi yo‘q **0 UI manzili**; bu to‘liq
paritet/native qabul yoki real port tugadi degani emas. [Paket73](Q17A-RICH-CONTENT-PARITY.md)
Q17a boy matn/inline media lokal paritetini yakunladi; keyin
[Paket74](Q17B-SIT-STUDIO-PROTOTYPE.md) SIT studiyasining10 UI manzilini
qurdi. [Paket75](Q18-MINIAPP-PROTOTYPE.md) Mini App5UI va web handoffni
qurdi. [Paket76](Q19-SYSTEM-PROTOTYPE.md) tizimning5 holatini qurdi.
[Paket77](Q08-DATED-ATTENDANCE-PROTOTYPE.md) U42 dated-ledger prototipini
va eski holatlarning dalil/ochiq-farq auditini bajardi.823 Django/197 Node PASS.
Endi **2 ochiq qadam**: joriy qamrov qabuli va tuzatishlar →
**DESIGN-01 kodsiz dizayn boshqaruvi** (owner 2026-09-28 reja oxiriga qo‘shdi).
Boshlang‘ich45 bandning lokal UI qurilishi bajarildi; DESIGN-01 yangi capability bo‘lib,
45 bandni qayta sanamaydi. Hozir DESIGN-01 qurilmaydi. Q17–Q19 lokal
implementation yakunlandi; real adapter/owner/native acceptance emas.
U17/A2-D01 to‘liq write-parity alohida OPEN; UI soni bu qarzni yopmaydi.
Keng Q14 savol/ko‘p-bo‘lim/nashr capabilitysi alohida ochiq; real port
va AWS bu turn o‘zgarmadi. Quyidagi45 soni boshlang‘ich audit snapshotidir.

Inventar sanasi: **2026-09-26**. Tekshirilgan source: `4d1ae70`;
AWSdagi tayyor V1 runtime: `8bb6b95` ([R2 dalili](R2-READY-V1-AWS.md)).
Owner topshirig‘i: yangi sahifa qurishdan **oldin** qolgan qamrovni aniqlash
va sanasiz tugatish rejasini tuzish. Bu hujjat reja, yangi UI yoki deploy emas.

## 1. Qisqa xulosa

- Mavjud Eleventh Trial: **95 preview manzil, 54 page template,
  76 noyob real UI URL nomi**. Barcha 54 template fayli joyida.
- Shu tayyor bo‘laklarning rejalangan **I1–I9 real porti AWSga chiqarilgan**.
  Haqiqiy qurilma/provider/real-content qabulining ochiq bandlari alohida;
  ular “hali prototipi yo‘q sahifa” hisobiga qo‘shilmaydi.
- Oldingi inventardagi **44 named-preview yo‘q URL** hozir ham mavjud.
  Shundan **2 tasi mavjud dizaynning muqobil manzili**; qayta dizayn kerak emas.
- Demak **42 ta ilova UI manzili + 3 ta xato handler sahifasi = 45 qamrov bandi**
  uchun prototip yetishmaydi. Bu 45 xil maket degani emas: yangi/tahrirlash
  rejimlari, umumiy ro‘yxat va formalar qayta ishlatiladi.
- Boshlang‘ich reja: **11 qadam — 10 qurish/bo‘shliqlarni yopish paketi va
  1 umumiy qabul**. Ownerning2026-09-28 qarori bilan oxiriga12-qadam
  DESIGN-01 qo‘shildi; dastlabki45 band inventari o‘zgarmadi.
  Real kodga ko‘chirish va AWSga chiqarish alohida kuzatiladi.

**“Prototipi yo‘q” — “loyihada umuman yo‘q” emas.** Quyidagi manzillarning
backend/legacy sahifalari bor; ularga tasdiqlangan yangi dizayn hali qurilmagan.
Hatto runtime-settingsga yangi operatsion forma qo‘shilgani ham uning yangi
frontend prototipi yoki V1 renderer porti tugadi degani emas.

| Oila | Named UI manzili | Qo‘shimcha handler | Ish turi |
|---|---:|---:|---|
| Q14 — Imtihon muharriri | 2 | 0 | Umumiy muharrirning kirish/tahrirlash holatlari |
| Q15 — Boshqaruv, to‘lov, foydalanuvchi, tarif/guruhlar | 9 | 0 | Ro‘yxatlar, formalar, a’zolik qarorlari |
| Q16 — Operatsion nazorat, AI, brend/landing | 10 | 0 | Nazorat va tasdiqli sozlamalar |
| Q17 — Blog va SIT studiolari | 13 | 0 | Kontent ro‘yxatlari va yaratish/tahrirlash |
| Q18 — Telegram Mini App | 5 | 0 | Kirish + 4 mobil bo‘lim |
| Q19 — Tizim holatlari | 2 | 3 | Maintenance/offline va 403/404/500 |
| Q08 bo‘shlig‘i — eski davomat boshqaruvi manzili | 1 | 0 | Mavjud teacher patternini qayta ishlatish |
| **Jami** | **42** | **3** | **45 qamrov bandi** |

## 2. Bajarish navbati — vaqt taxminisiz

`[ ]` ochiq; `[-]` ishda; `[x] ~~nom~~` faqat dalil bilan tugagan.
Qadam ichidagi bir forma tayyor bo‘lsa butun qadam chizilmaydi.
Eski Q raqamlari saqlanadi; a/b bo‘linishi faqat paket chegarasidir.

- [x] ~~0. Inventarni hozirgi kod bilan qayta solishtirish.~~
  95/54/76 qayta sanaldi, 120 UI nomi/pathi tekshirildi; 44 = 42+2 alias.
  Uch handler alohida qo‘shildi. Usul va cheklovlar 7-bo‘limda.
- [x] ~~1. Q14 — mavjud backendga mos imtihon muharriri (2 URL).~~ Imtihon/kurs konteksti,
  mavjud forma maydonlari, bo‘lim ma’lumoti, prerequisite, bo‘sh va xato
  holatlari. **Yakun:** aniq imtihon → tahrir → tasdiqli saqlash → o‘sha
  imtihonga qaytish; invalid/begona ID boshqa imtihonni ochmaydi.
  Savol CRUD va ko‘p bo‘limli authoring chegarasi 5-bo‘limda — jimgina
  ishlaydigan feature sifatida namoyish qilinmaydi.
  **Dalil:** [Paket67](Q14-EXAM-EDITOR-PROTOTYPE.md), 18/18 maydon,
  606 Django +168 JS PASS; local-only. Keng Q14 capability va owner/native
  qabul yopilmadi; yuqoridagi chiziq faqat U01/U02 source-supported UI uchun.
- [x] ~~2. Q15a — Kundalik boshqaruv (4 URL).~~ Bosh panel, cheklar,
  foydalanuvchilar va chatlar ro‘yxati. **Yakun:** qidiruv/filtr/pagination
  → tafsilot yoki mavjud oqimga kirish → ayni filtrga qaytish; chek
  tasdiqlash/rad etish sababi va natijasi ravshan. Foydalanuvchini
  bloklash yoki chatni o‘chirish kabi mavjud bo‘lmagan amallar ixtiro qilinmaydi.
  **Ijro:** [Paket68](Q15A-DAILY-BACKOFFICE-PROTOTYPE.md); 4 lokal UI,
  checkout→owner qarori→learner holati, 40 responsive ko‘rinish tekshirildi.
  **630 Django +170 JS PASS**; real port va owner/native qabul ochiq.
- [x] ~~3. Q15b — Tarif va guruh boshqaruvi (5 URL).~~ Katalog, tarif
  formasi, guruh yaratish/tahrirlash, a’zolar. **Yakun:** tarif/guruh → a’zo
  → joyni bo‘shatish/tiklash yoki ko‘chirish/farq summasi → qayta ko‘rish;
  pul, joy va access hisoblari fixture’da canonical natija sifatida beriladi.
  **Ijro:** [Paket69](Q15B-CATALOG-PROTOTYPE.md), 657 full +28 final focused,
  174 JS PASS;
  50 responsive ko‘rinish, create/readback, tier consent, unknown-result.
  Farq so‘rovi lokal metadata; real receipt/upload/approval adapteri va
  owner/native qabul ochiq. Production yoki yangi payment yozilmagan.
- [x] ~~4. Q16a — Nazorat va AI boshqaruvi UI (8 URL).~~ Control center,
  flags, runtime settings, AI xarajat, dead-letter, AI sozlamalari,
  kill-switch, circuit reset. **Yakun:** joriy qiymat va qoralama alohida;
  source qo‘llaydigan mutationlarda ta’sir doirasi → sabab/tasdiq →
  natija/audit → takroriy/no-op holati. **U17 istisnosi:** eski AI settings
  write yuzalari buni to‘liq qo‘llamaydi; quyidagi A2-D01 alohida backend
  qarzi, Q16a ichida jimgina retrofit qilinmaydi. UI qurilishi va to‘liq
  write-parity qabuli alohida belgilanadi. Prototip hech qanday haqiqiy
  limit, flag yoki tashqi xizmatni o‘zgartirmaydi.
  **Ijro:** [Paket70](Q16A-CONTROL-PROTOTYPE.md): 24 flag,7 panel,16 xizmat,
  native sabab/tasdiq/readback va 100 responsive ko‘rinish. U17 faqat
  read/form/action chegarasini ko‘rsatadi; uning uch write actioni yopiq.
  **A2-D01 write-parity va real port ochiq**, ushbu chiziq faqat lokal UIga.
- [x] ~~5. Q16b — Brend va landing boshqaruvi (2 URL).~~ Logo/brend
  formasi va bosh sahifa kontenti. **Yakun:** qoralama/preview → explicit
  saqlash → public namuna bilan moslik; tasdiqsiz global tema yoki brend
  o‘zgarishi yo‘q. Dizayn tizimini qayta yaratish bu paketga kirmaydi.
  **Ijro:** [Paket71](Q16B-BRAND-LANDING-PROTOTYPE.md),7 brend/60 landing
  maydoni,9 bo‘lim; draft preview→native save→saved sample.710 full +52
  final focused Django /182 JS PASS,40 responsive cases. Faqat lokal
  kontent namunasi; real public layout/RBAC/media/port/native qabul ochiq.
- [x] ~~**6. Q17a — Blog studiyasi (3 URL), lokal implementation.**~~ Maqolalar ro‘yxati,
  yaratish va tahrirlash. **Yakun:** qoralama → preview → mavjud status
  bo‘yicha nashr → public maqola; uzun matn, media va validation saqlanadi.
  **Ijro:** [Paket72](Q17A-BLOG-STUDIO-PROTOTYPE.md),13 source maydon,
  draft→preview→native save/publish→shu storedan public maqola.735 Django
  /186 JS PASS,50 responsive +54 state case. Muqova normalize/clear bor;
  keyingi [Paket73](Q17A-RICH-CONTENT-PARITY.md) source CKEditor/inline media
  preview/save/public lokal paritetini bajardi.752 Django/190 JS PASS,
  30 responsive case; format, table, image/alt/caption, reload/consent,
  native save/public va unsafe HTML/media rad etilishi tekshirildi.
  Real port/RBAC/durable save va owner/native qabul ham alohida ochiq.
- [x] ~~**7. Q17b — SIT studiyasi (10 URL), lokal implementation.**~~ Boshqaruv markazi,
  universitetlar, e’lonlar va qo‘llanmalar list/new/edit. **Yakun:**
  universitet ichki formsetlari/kontent → qoralama preview → nashr →
  mavjud public sahifa; nashr qilinmagan yozuv oddiy tashrifchiga chiqmaydi.
  **Ijro:** [Paket74](Q17B-SIT-STUDIO-PROTOTYPE.md),43 source field va7
  child formset/33 field; native save/preview, filtered return, rich guide
  va public stored-content pariteti.120 responsive case, overflow0.
  Real RBAC/storage/port, tashqi CTA va owner/native acceptance alohida ochiq.
- [x] ~~**8. Q18 — Telegram Mini App (5 URL), lokal implementation.**~~ Kirish, home, kurslar,
  AI va profil. **Yakun:** Telegram kirish holatlari → tegishli bo‘lim →
  mavjud web oqimi → Back; safe-area, klaviatura, tema va sessiya xatosi.
  Sintetik auth holati haqiqiy Telegram/HMAC qabuli deb belgilanmaydi.
  **Ijro:** [Paket75](Q18-MINIAPP-PROTOTYPE.md),788 Django/195 Node PASS,
  120 responsive check. Explicit synthetic auth/receipt, shared projections,
  existing AI room delegate, same-tab web return va browser Back tekshirildi.
  Haqiqiy Telegram SDK/Back/theme/safe-area/native keyboard qabuli OPEN.
- [x] ~~**9. Q19 — Tizim sahifalari (5 holat), lokal implementation.**~~ 403,404,500,
  maintenance, offline. **Yakun:** tushunarli sabab va xavfsiz qaytish/retry;
  redirect loop yo‘q, 500 minimal kontekstda ham ishlaydi; noto‘g‘ri
  retry foydalanuvchi amalini ikki marta bajarmaydi.
  **Dalil:** [Paket76](Q19-SYSTEM-PROTOTYPE.md),800 Django/195 Node,
  final12 focused,60 responsive checks. Source HTTP statuslar, minimal500,
  actual DEBUG=False handler dispatch, allowlisted GET va keyboard/handoff
  verified. Real PWA/network outage/native/AT/owner qabul va port OPEN.
- [x] ~~**10. Q08 bo‘shlig‘i va mavjud sahifalar paritet auditi (1 yangi URL).**~~
  `/users/attendance/manage/` uchun mavjud teacher-davomat patterni;
  qo‘shimcha ravishda 4-bo‘limdagi eski holat qarzlari tekshiriladi.
  **Yakun:** barcha ochiq holatlarning dalili yoki aniq ochiq qarori bor;
  boshqa URLga redirect qilish tanlansa bu owner qarori bo‘ladi, qamrov
  jimgina yo‘qolmaydi. Bu qadam tayyor 76 URLni qayta dizayn qilish emas.
  **Dalil:** [Paket77](Q08-DATED-ATTENDANCE-PROTOTYPE.md), U42 alohida
  exact-date forma/shared ledger;823 Django/197 Node,32 responsive check.
  4-bo‘limning har qatori existing evidence/missing state/capability yoki
  acceptance OPEN sifatida tasniflandi. Missing-state bandlari PAR-01–05
  final qabulda qoladi; bu chiziq barcha paritet qarzlari yopildi degani emas.
- [ ] **11. Q20–Q21 — Umumiy tekshiruv va qabul.** Yangi oilalardan
  mavjud learner/teacher/public oqimlariga handoff, rol chegaralari,
  desktop/mobile va owner walkthrough. **Yakun:** 45 bandning har biri
  registry/action/source xaritasi, test dalili va qabul holatiga ega;
  blocker yo‘q, qolgan cheklovlar ochiq yozilgan, lokal checkpoint/zaxira bor.
  Native device/AT tekshirilmagan bo‘lsa to‘liq G3 PASS yozilmaydi.
  [Ochiq tuzatishlar](FINAL-ACCEPTANCE-ISSUES.md): owner iPhone Chrome
  keyboard/chat nuqsonini shu bosqichga qoldirdi; Q08da unga tegilmadi.
- [ ] **12. DESIGN-01 — Admin paneldan keng kodsiz dizayn boshqaruvi.**
  **Owner qarori,2026-09-28:** sodda rang tanlagich bilan chala qoldirmaslik;
  rang, button/karta shakli va shriftlarni kodga tegmasdan boshqarish imkonini
  reja oxirida kengaytirish. Hozirgi Q08→qabul navbati o‘zgarmaydi.
  [Qamrov va yakun mezonlari](DESIGN-CUSTOMIZATION-PLAN.md).
  **Yakun:** token/komponent xaritasi → alohida qoralama va ko‘p sahifali preview
  → validatsiya → tasdiqli yagona versiyani tatbiq qilish → history/rollback;
  public/learner/teacher/owner/Mini shelllarda desktop/mobile/light/dark
  regressiya va owner qabuli. Bir demo sahifada rang almashishi yakun emas.
  11-qadam bazaviy checkpoint; dizayn kengayishidan keyin acceptance qaytariladi.
  Prototip, canonical sozlama xizmati/real port va AWS relizi alohida dalillanadi.

Paket — bir tugma yoki screenshot emas, yuqoridagi **yakunlangan oqim**.
Oddiy ichki bosqichlarda ish to‘xtatib turilmaydi; faqat yangi vakolat,
product qarori, xavfsizlik yoki tashqi blok kerak bo‘lsa ownerga chiqiladi.
Qolgan sahifalarni doimiy kattalashtiradigan redesign va yangi featurelar
alohida backlogda turadi; shu rejaning ichiga yashirincha kiritilmaydi.
DESIGN-01 owner explicit qo‘shgan yagona yangi kengaytma, vaqt va’dasisiz.

## 3. To‘liq sahifa/manzil ro‘yxati

Jadval boshlang‘ich **YO‘Q** inventaridir. **2026-09-28 delta:** U01/U02
Paket67da, U03–U06 Paket68da, U07–U11 Paket69da, U12–U19 UI Paket70da
lokal qurildi; Q16b U20/U21, Q17a U22–U24 va Q17b U25–U34 UI ham qurildi.
Q18 U35–U39 UI Paket75da, Q19 U40/U41 vaH01–H03 Paket76da, U42 Paket77da
lokal qurildi. Boshlang‘ich barcha45 bandning renderer prototipi bor;
qolgan state-parity/native/owner qarzlari alohida ochiq.
Mini App real Telegram va Q19 haqiqiy offline/PWA/native/owner qabuli
bundan alohida ochiq.
Q17a rich-text/inline media lokal pariteti Paket73 bilan bajarildi;
haqiqiy blog media/RBAC/sanitizer porti va native/owner qabul alohida.
U17 write-parity/A2-D01 alohida ochiq.
Jadvaldagi IDlar progress/dalilni bog‘lash uchun barqaror. `<...>` parametr,
demo ID emas. Lokal UI borligi real port yoki G3 qabul degani emas.

| ID | Paket | Real URL nomi yoki handler | Manzil / holat |
|---|---|---|---|
| U01 | Q14 | `backoffice_exams` | `/backoffice/exams/` |
| U02 | Q14 | `backoffice_exam_edit` | `/backoffice/exams/<int:exam_id>/` |
| U03 | Q15a | `backoffice_dashboard` | `/backoffice/` |
| U04 | Q15a | `backoffice_receipts` | `/backoffice/receipts/` |
| U05 | Q15a | `backoffice_users` | `/backoffice/users/` |
| U06 | Q15a | `backoffice_chats` | `/backoffice/chats/` |
| U07 | Q15b | `backoffice_catalog` | `/backoffice/catalog/` |
| U08 | Q15b | `backoffice_plan_edit` | `/backoffice/catalog/plans/<int:plan_id>/` |
| U09 | Q15b | `backoffice_cohort_create` | `/backoffice/catalog/cohorts/new/` |
| U10 | Q15b | `backoffice_cohort_edit` | `/backoffice/catalog/cohorts/<int:cohort_id>/` |
| U11 | Q15b | `backoffice_cohort_members` | `/backoffice/catalog/cohorts/<int:cohort_id>/members/` |
| U12 | Q16a | `backoffice_control` | `/backoffice/control/` |
| U13 | Q16a | `backoffice_feature_flags` | `/backoffice/control/flags/` |
| U14 | Q16a | `backoffice_runtime_settings` | `/backoffice/control/runtime-settings/` |
| U15 | Q16a | `backoffice_ai_cost` | `/backoffice/control/ai-cost/` |
| U16 | Q16a | `backoffice_dead_letter` | `/backoffice/control/dead-letter/` |
| U17 | Q16a | `backoffice_ai_control` | `/backoffice/ai-control/` |
| U18 | Q16a | `backoffice_ai_kill_switch` | `/backoffice/control/ai-kill-switch/` |
| U19 | Q16a | `backoffice_ai_circuit_reset` | `/backoffice/control/ai-circuit-reset/` |
| U20 | Q16b | `backoffice_brand` | `/backoffice/control/brand/` |
| U21 | Q16b | `backoffice_landing` | `/backoffice/landing/` |
| U22 | Q17a | `blog:studio` | `/blog/studio/` |
| U23 | Q17a | `blog:studio_create` | `/blog/studio/new/` |
| U24 | Q17a | `blog:studio_edit` | `/blog/studio/<slug:slug>/edit/` |
| U25 | Q17b | `sit_backoffice:dashboard` | `/backoffice/sit/` |
| U26 | Q17b | `sit_backoffice:universities` | `/backoffice/sit/universities/` |
| U27 | Q17b | `sit_backoffice:university_create` | `/backoffice/sit/universities/new/` |
| U28 | Q17b | `sit_backoffice:university_edit` | `/backoffice/sit/universities/<int:university_id>/` |
| U29 | Q17b | `sit_backoffice:announcements` | `/backoffice/sit/announcements/` |
| U30 | Q17b | `sit_backoffice:announcement_create` | `/backoffice/sit/announcements/new/` |
| U31 | Q17b | `sit_backoffice:announcement_edit` | `/backoffice/sit/announcements/<int:announcement_id>/` |
| U32 | Q17b | `sit_backoffice:guides` | `/backoffice/sit/guides/` |
| U33 | Q17b | `sit_backoffice:guide_create` | `/backoffice/sit/guides/new/` |
| U34 | Q17b | `sit_backoffice:guide_edit` | `/backoffice/sit/guides/<int:guide_id>/` |
| ~~U35~~ | Q18 · Packet75 | `bot:miniapp_entry` | `/bot/miniapp/` |
| ~~U36~~ | Q18 · Packet75 | `bot:miniapp_home` | `/bot/miniapp/home/` |
| ~~U37~~ | Q18 · Packet75 | `bot:miniapp_courses` | `/bot/miniapp/courses/` |
| ~~U38~~ | Q18 · Packet75 | `bot:miniapp_ai` | `/bot/miniapp/ai/` |
| ~~U39~~ | Q18 · Packet75 | `bot:miniapp_profile` | `/bot/miniapp/profile/` |
| ~~U40~~ | Q19 · Packet76 | `maintenance` | `/maintenance/` |
| ~~U41~~ | Q19 · Packet76 | `offline` | `/offline/` |
| U42 | Q08 | `attendance_manage` | `/users/attendance/manage/` |
| ~~H01~~ | Q19 · Packet76 | `handler403` | `core.views.permission_denied` → `errors/403.html` |
| ~~H02~~ | Q19 · Packet76 | `handler404` | `core.views.page_not_found` → `errors/404.html` |
| ~~H03~~ | Q19 · Packet76 | `handler500` | `core.views.server_error` → `errors/500.html` |

### Alohida yangi dizayn kerak bo‘lmagan ikki manzil

| Real nom / manzil | Hozirgi source dalili | Qoladigan tekshiruv |
|---|---|---|
| `messenger:index` — `/messenger/` | `MessengerAIView` va `AIMessengerV1Mixin`: `/messenger/ai/` bilan bitta renderer | Alias kirishi, active nav, sessiya/Back |
| `cohorts:checkout_success_latest` — `/checkout/success/` | `checkout_success_view`: eng so‘nggi o‘zining tasdiqlangan cheki, I7 renderer | Chek bor/yo‘q, ownership va safe return |

Bu ikkisining **alohida named previewi yo‘q**, lekin yangi ekran hisobiga
kiritish takror sanash bo‘ladi. 11-qadamda alias regressiyasi tekshiriladi.

## 4. Prototipi bor, lekin eski trackerda ochiq qolgan ishlar

`REMAINING-PLAN.md`dagi “22/26 ochiq” qurilmagan sahifalar soni emas.
U implementation, integration va acceptance’ni bir qatorda hisoblagan.
Eski dalil saqlanadi; joriy port statusi [PORT-LEDGER](PORT-LEDGER.md) va
[R2](R2-READY-V1-AWS.md)dan olinadi. Quyidagi tekshiruvlar yangi URL emas:

| Eski band | Bor narsa / qayta qilinmaydi | Faqat qolgan farq qanday yopiladi |
|---|---|---|
| Q02–Q03 | Public/catalog/blog/SIT/legal prototipi va I5a real porti | Ko‘p yozuv/pagination, blog interaction, SIT program/advisor/application ichki holatlari source bilan solishtiriladi; bor real dalil qayta ishlatiladi |
| Q04 | Dars material/homework/quiz prototipi va I2–I3 porti | Native upload/audio, failure/Back va yangi oilalar bilan handoff |
| Q05–Q06 | AI/human messenger prototipi, tasdiqlangan B layout, I4 porti | Keyingi compact message action qarori va eski preview orasidagi farq hujjatlashtiriladi; chat qayta dizayn qilinmaydi |
| Q07 | Checkout/chek holatlari prototipi, I7 porti | Real to‘lov qabuli alohida; sintetik denied/pending/rejected/retry va ikki kirish manzili |
| Q08 | Account/profile/privacy/billing/records va I5 porti | Faqat U42 yangi; qolganlariga qo‘shimcha dizayn emas, regressiya |
| Q09–Q10 | Classbook prototipi yopilgan, I9 porti chiqarilgan | Native multi-user/device qabulini prototip qurishga tenglashtirmaslik |
| Q11–Q12 | Course/lesson editorlar prototipi, I6 real to‘liq forma adapteri | Previewda yetishmaydigan field/state bo‘lsa faqat delta; canonical’da yo‘q assignment/quiz authoring alohida ochiq capability qarori |
| Q13 | Kutubxona prototipi yopilgan va I6a porti chiqarilgan | Qayta ochilmaydi; yangi editorlardan picker handoff regressiyasi |
| Exam result/review | I8da owner tasdiqlagan published-only natija real kodda | Eski preview qoralama ko‘rsatsa owner qaroriga moslashtirish; grading formulasi ixtiro qilinmaydi |

**Inventar cheklovi:** bu turn route/template/source auditidir, barcha
843 eski route-state kombinatsiyasining yangi browser audit’i emas.
4-bo‘limdagi state qarzlari to‘liq yopildi deb da’vo qilinmaydi. 10-qadam
har biriga `existing evidence / missing state / capability decision` holatini
qo‘yadi; aniqlangan yangi backend imkoniyati 45 sahifa soniga yashirin qo‘shilmaydi.

**2026-09-28 ijro:** [Packet77 audit jadvali](Q08-DATED-ATTENDANCE-PROTOTYPE.md)
har bir qatorga shu tasnifni qo‘ydi. [Final ro‘yxat](FINAL-ACCEPTANCE-ISSUES.md)
UX-01–06/DATA-01/RULE-01 va PAR-01–05ni yo‘qotmasdan kuzatadi.

## 5. Ko‘lamni cho‘zadigan chegaralar — oldindan aniq

1. **Imtihon muharriri hozir to‘liq savol konstruktori emas.**
   `core.views.backoffice_exam_editor` exam formasi va birinchi bo‘limni
   saqlaydi; savol CRUD endpointi emas. ID’siz kirish birinchi ruxsatli
   imtihonni tanlaydi. Yangi UI bu tanlovni yashirmaydi, unknown IDni unga
   fallback qilmaydi. Eski Q14dagi keng savol/bo‘lim authoring va nashr
   boshqaruvi istagi ochiq qoladi: source-supported V1 va yangi capability
   kontrakti ajratiladi. Owner qarorisiz scope chiqarib tashlanmaydi,
   soxta tugma bilan “bajarildi” ham qilinmaydi.
2. **Davomatning ikkinchi manzili alias emas.** `AttendanceManageView`
   alohida template/POSTga ega. Uni teacher sahifasiga jim redirect qilish
   o‘rniga U42 sifatida hisobladik; qayta foydalanish mumkin, permission
   va query contracti saqlanishi kerak.
3. **Kill-switch va circuit reset haqiqiy GET sahifalar.** Ular POST
   actionga o‘xshab nomlansa ham forma/template qaytaradi, shuning uchun
   Q16dan olib tashlanmadi. Boshqa POST/file/socket endpointlar alohida
   sahifa emas, o‘z consumerining action contractiga kiradi.
4. **SIT program/advisor/application mustaqil route emas.** Joriy
   `sit/urls.py`da to‘rtta public route bor; bular mavjud home/detail
   ichidagi blok yoki chiqish oqimi. Ularni uchta yangi sahifa deb sanamadik.
5. **Legacy Django admin shartli mount.** `ENABLE_LEGACY_ADMIN` source’da
   default OFF. Django generatsiya qiladigan admin sahifalariga individual
   yangi maket shu 45 hisobida yo‘q; oldingi `INCLUDED-IF-ENABLED` sharti
   saqlanadi. Yoqilsa alohida inventar/qamrov qarori kerak; agent uni
   yoqmaydi ham, jimgina DEFERRED ham qilmaydi.
6. **Operatsion qarzlar yangi prototip emas.** SMTP xat yetkazish,
   real payment/provider/Telegram, native phone/audio, backup scheduling
   va real-content qabuli [R2](R2-READY-V1-AWS.md)da alohida ochiq.
   Rejani chizib tugatish bu xizmatlar tayyor degani emas.
7. **A2-D01 — AI sozlamalarining audit retrofiti, alohida backend qarzi.**
   `backoffice_ai_control`dagi `save_settings` va `save_policy` to‘g‘ridan-to‘g‘ri
   yozadi; majburiy sabab/tasdiq va `SystemAuditEvent` shartnomasi yo‘q.
   `apply_event`dagi reset/bonusning o‘z event yozuvi borligi qolgan
   amallarni auditlangan qilmaydi. [Agent qoidalari §1](../rules-for-agents.md)
   aynan shu retrofitni alohida A2 qarzi deb belgilaydi.
   **Holat: OPEN / alohida admission talab qilinadi; ushbu reja uni
   implementatsiya qilishga ruxsat emas.** Q16a U17 uchun hozirgi
   canonical read/form/action chegarasini ko‘rsatadi; mavjud bo‘lmagan
   audit/no-op kafolati yoki soxta muvaffaqiyatni mock qilmaydi.
   Kuchaytirilgan write oqimi uchun owner admission → alohida canonical
   service/form/test paketi → prototype contract yangilanishi kerak.
   A2-D01 yopilmaguncha yoki owner explicit qabul chegarasini belgilamaguncha
   Q16a/U17ning **to‘liq write-parity qabuli ochiq** qoladi; UI tayyorligi
   bu qarzni yashirmaydi. 45 sahifa soni o‘zgarmaydi.

## 6. Har paket uchun bir xil tugatish mezoni

- Sahifa, action, source view/form/service va fixture mosligi yozilgan;
  canonical access/narx/grade/quota frontendda qayta hisoblanmaydi.
- Barcha shu paketdagi manzillar, valid/empty/invalid/denied/error va
  relevant offline/loading/stale/unknown-result holatlari mavjud.
- Formani tasdiqlamasdan tashqi ta’sir yo‘q; duplicate yoki natijasi
  noma’lum so‘rov avtomatik takror yuborilmaydi; qoralama yo‘qolmaydi.
  Source bu himoyani bermasa (masalan A2-D01), bu frontendda kafolatlangandek
  ko‘rsatilmaydi: alohida backend dependency va ochiq qabul bandi yoziladi.
- 320/390/768/1024/1280px, light/dark, uzun matn, keyboard/focus/Escape,
  Back/refresh tekshirilgan; horizontal overflow yoki yopilgan asosiy amal yo‘q.
- Console/network va bog‘liq oldingi oqim regressiyasi tekshirilgan;
  registry status faqat dalil darajasida ko‘tarilgan.
- **Prototip / real kod / AWS / owner-native qabul** to‘rtta alohida status.
  Real kodga ulashda qayta maket yasash emas, shu contractning adapteri yoziladi.
- Evidence va lokal checkpoint ko‘rsatilgach tegishli qadam chiziladi.
  Prototip secret, production data yoki haqiqiy providerga ulanmaydi.

Mavjud Eleventh Trial V1 fayllari va zaxirasi ushbu reja turnida o‘zgarmadi.
Keyingi qurishdan oldin oldingi checkpoint saqlanib, faqat yangi oilalar va
zarur parity delta uchun continuation chegarasi yoziladi. Yangi umumiy shell,
font/palitra yoki katta redesign rejalashtirilmadi.

## 7. Tekshiruv dalili va qayta sanash

2026-09-26 provider-free `venv/Scripts/python.exe -` orqali read-only audit:
`AZURELMS_SKIP_ENV_FILE=1`, bo‘sh `GEMINI_API_KEY`/`TELEGRAM_BOT_TOKEN`,
`LOCAL_USE_REMOTE_SERVICES=0`; Django resolver metadata, view source va
lokal JSON o‘qildi. DB yozuvi, browser mutation yoki provider chaqiruvi yo‘q.

Manbalar:

- `playground/Eleventh Trial/prototype/contracts/registry.json`
  (`0.66.0-multi-resource-library`): routes95, unique names76,
  unique templates54, missing template files0.
- `playground/Eleventh Trial/evidence/q01-runtime-map.json`dagi120
  SCREEN/SCREEN_ALIAS nomi **joriy resolver bilan qayta solishtirildi**:
  o‘chgan nom0, o‘zgargan UI path0, preview nomi unresolved0.
- Named UI difference44; U01–U42 va ikki aliasga bir martadan ajratildi.
  `api_exam_v1` yangi helper, yangi UI emas; CKEditor image-upload
  dependency endpointi ham sahifa hisobiga kirmaydi.
- `core/urls.py` handler403/404/500, `core/views.py`, `core/backoffice_forms.py`,
  `subscriptions/backoffice_views.py`, `users/views.py`, `messenger/urls.py`,
  `cohorts/views.py`, `blog/urls.py`/`views.py`, `sit/urls.py`/`views.py`/
  `backoffice_urls.py`/`backoffice_views.py`, `bot/urls.py`/`views.py` tekshirildi.
- [Boshlang‘ich inventar](INVENTORY.md) tarixiy snapshot; ushbu hujjat
  qolgan prototip qamrovi uchun yangi kesim. [Port jurnali](PORT-LEDGER.md)
  va [R2 release](R2-READY-V1-AWS.md) real kod/AWS statusi uchun manba.

Qayta audit algoritmi: registry route nomlarini unique set qilish →
resolver bilan nom/path tekshirish → 120 UI/alias setidan ayirish →
ikki shared-renderer aliasni alohida yozish → uch error handlerni qo‘shish.
Yangi URL paydo bo‘lsa avval screen/action/alias sifatida tasniflanadi.
Ro‘yxat kengaysa sabab/owner qarori yoziladi, eski son jim almashtirilmaydi.
