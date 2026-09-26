# Q15b — tarif va guruh boshqaruvi prototipi

Sana: **2026-09-27**. Source bazasi `680e9f0` (Q15a main).
Branch: `codex/q15b-catalog-prototype`. D31 continuation, owner “davom et”.
Paket69 source/test/screenshotlari ignored `playground/Eleventh Trial`da.
Gitga faqat dalil va reja kiradi. Real runtime, DB va AWS o‘zgarmadi.

## Admission va qamrov

**EXPERIMENT — canonical state yozmaydi.** Maqsad: owner tarif/guruhni
tahrirlaydi, aniq a’zolik qarorini tasdiqlaydi va natijani qayta o‘qiydi.
Mezon: 5 canonical UI, to‘g‘ri obyekt, native saqlash/natija, no double-write,
mobil/desktop tekshiruvi. Yangi provider, AI siyosati yoki production flag yo‘q.
Lokal yuk: bitta katalog revision/run, 64 natijali bounded ledger. Rollback:
lab reset yoki saqlangan Paket68 ZIP. Production majburiyati qo‘shilmadi.

| Canonical UI | Lokal oqim |
|---|---|
| `backoffice_catalog` | Tariflar, guruhlar, band/yopiq/full/default/istisno holatlari |
| `backoffice_plan_edit` | 8 model maydoni + features + sabab/tasdiq; kod readonly, legacy capacity yo‘q |
| `backoffice_cohort_create` | 8 maydon + sabab/tasdiq → yangi aniq ID → tahrir/a’zolar |
| `backoffice_cohort_edit` | Band joydan past sig‘im, duplicate default va a’zoli guruh kurs/tarif almashishi rad |
| `backoffice_cohort_members` | Release/restore/transfer/difference → sabab/tasdiq → exact natija → joriy holat |

5 URL pattern, 3 yangi page template. Umumiy **108 route /63 template /
87 source URL nomi /960 route-state /187 action**. Dynamic IDlar shu pattern
ichidagi sintetik yozuvlar; alohida canonical sahifa sifatida sanalmaydi.
Q15a to‘rt tabiga katalog tabiiy beshinchi bo‘lim bo‘lib qo‘shildi;
platform shell, breakpoint, rang tokenlari va asosiy navigatsiya saqlandi.
Mobil tekshiruvda takroriy o‘z-sahifa havolasi olib tashlandi.

## Canonical qoidalar va lokal holat

Manbalar: `subscriptions/backoffice_views.py`, `catalog_forms.py`,
`catalog_service.py`, `subscriptions/models.py`, `cohorts/models.py`,
`membership_service.py`, `transition_service.py` va uch source template.

- Tarif kodi va legacy/delivery turi o‘zgarmaydi. Guruh standarti 1–500,
  narx manfiy emas; imkoniyatlar 40 satr, satrda 200 belgi. Tarif yangilash
  mavjud guruh sig‘imi, oldingi xarid, AI kvota yoki huquqni yozmaydi.
- Yangi guruhning bo‘sh sig‘imi tarif standartidan olinadi. Ustoz kursdan
  keladi. A’zoli guruh kurs/tarifi immutable; sig‘im occupieddan kam emas.
  Course+plan uchun bitta default; legacy capacity/plan juftligi saqlanadi.
- Active/expired joy band; frozen band emas. Ochiq paid-access release
  rad etiladi. Restore faqat frozen→expired: **kirish ochilmaydi**.
- Transfer shu kursdagi boshqa faol, bo‘sh guruhga. Pending receipt,
  full target va tarixiy duplicate membership rad. Boshqa tarif uchun
  alohida consent. Yangi enrollment ID, eski yozuv frozen; status/muddat
  saqlanadi, synthetic progress ko‘chadi. Davomat tarixi va pul yozilmaydi.
- Difference: musbat integer summa, sabab, tasdiq → “Chek rasmi kutilmoqda”.
  Duplicate request rad; keyingi transfer outstanding request bilan yopiq.
  **Bu to‘lov tasdig‘i emas.** Muddat/huquq o‘zgarmaydi. 120000 namuna taklifi
  oldindan fixture’da yozilgan; narx/grace/entitlement formulasi ko‘chirilmagan.
- Store o‘quvchi va oddiy teacher bootstrapga chiqmaydi. Existing purchase
  va learner fixturelari alohida; sinov katalogi ularni qayta hisoblamaydi.

## Native forms va xato holatlari

GET yozmaydi. POST→303→GET exact result; result origin+IDga bog‘langan.
Run/revision/operation va field/query allowlist; duplicate parametr rad.
Bir xil operation+payload qayta yuborilsa no-op; altered payload, stale yoki
reset409. 64 natija saqlanadi, chegara429; eski natija evict qilinmaydi.
Yozuv nusxasiga validation/qaror qo‘llanib, faqat muvaffaqiyatda almashtiriladi.

422da maydonlar va sabab bound qoladi. Empty/locked403, expired401,
offline/error503 yozmaydi. Unknown-response503da saqlangan natija alohida
GET bilan tekshiriladi, submit disabled. Qoralama run/entity/action/revisionga
scoped; yangi versiyaga jimgina ko‘chmaydi. Faqat allowlisted fieldlar,
consent/CSRF/operation saqlanmaydi. Result readonly before→after ko‘rsatadi.

## Port va qabul chegaralari — ochiq

1. Preview synthetic owner context haqiqiy RBAC emas. Real `require_owner`,
   audit, notification, lock/transaction va exact cohort/member binding
   canonical xizmatlar orqali alohida sinovdan o‘tadi.
2. Real formalar hozir revision/idempotency/result ledger bermaydi;
   ular adapter talabi, backend mavjud capabilitysi deb ko‘rsatilmaydi.
3. Difference so‘rovi shu katalogda metadata sifatida qayta o‘qiladi.
   Existing checkout #301 yoki Q15a receipt queuega ko‘chirilmaydi.
   Haqiqiy `request_tier_difference` yaratadigan receipt, learner upload,
   owner approval va notification oqimi **real portda ulanishi shart**.
4. Access/price/proration source-of-truth hisoblari bajarilmagan. Description
   uchun lokal 10000 belgi, summa uchun 10 raqam himoyasi bounded preview
   cheklovi; bu yangi product siyosati sifatida backendga ko‘chirilmaydi.
5. Native iOS/Android/AT, owner acceptance, Q15 real port va umumiy G2/G3
   ochiq. AWS `8bb6b95` /19 renderer holati o‘zgarmadi.

## Tekshiruv

Trial cwd; provider-free `AZURELMS_SKIP_ENV_FILE=1`, bo‘sh `GEMINI_API_KEY`,
`TELEGRAM_BOT_TOKEN`, `LOCAL_USE_REMOTE_SERVICES=0`.

```powershell
& 'C:/Users/azizb/Desktop/project/azurelms/venv/Scripts/python.exe' manage.py check
& 'C:/Users/azizb/Desktop/project/azurelms/venv/Scripts/python.exe' manage.py test tests --verbosity 1
$trialTestFiles = @(Get-ChildItem -LiteralPath tests -Filter '*.test.mjs' | ForEach-Object FullName)
node --test @trialTestFiles
```

- Check0; **656 Django PASS** (283.950s), yangi26 Q15b test. Yakuniy
  result/ixcham navigation tuzatishidan keyin27 focused PASS (5.144s).
  **174 Node PASS**, yangi4 draft testi; ikki yangi JS syntax check PASS.
- 5 route ×320/390/640/1024/1440px ×light/dark = **50 ko‘rinish**:
  horizontal overflow0, ko‘rinadigan link/button/field/choice height ≥44px.
  Bu engine geometriya tekshiruvi, haqiqiy telefon qabuli emas.
- Brauzer: create→ID100→readback; qoralama reload/tasdiq unchecked;
  boshqa tarif consent yo‘q422→matn/fokus→consent→yangi a’zolik;
  difference request readback (to‘lov bo‘lmadi); unknown503→exact result;
  320px uzun matn, menu Escape/focus PASS. Final page JS error/warn0.
- Dastlabgi 60-test run bitta CSS token typo sabab FAIL bo‘lgan;
  mavjud `--az-reading` tokeniga tuzatildi, keyingi to‘liq suite PASS.
  Muvaffaqiyatsiz run dalildan yashirilmadi, test susaytirilmadi.
- Lokal dalil: `evidence/PACKET-69-RESULTS.md`, `q15b-desktop-light.png`,
  `q15b-mobile-dark.png`. Preview `http://127.0.0.1:8073/backoffice/catalog/`.

## Checkpoint va navbat

- ZIP: `playground/Eleventh Trial/checkpoints/packet-69-20260927-015747.zip`.
- **501 fayl**, har archive entry va source SHA256 mosligi tekshirildi.
- SHA256: `913A1C27DEEF545A3617B7C3993B68B0F8B4AE3EBA40A4F0026A6832BEFD6E17`.
- Paket68 saqlanadi; source/screenshots ignored, remote’ga yuborilmadi.

Q15b U07–U11 lokal prototipi qurildi. **31 UI +3 handler =34 band,
8 keyingi qadam** qoldi. Keyingi: **Q16a — Nazorat va AI boshqaruvi (8 URL)**.
Keng Q14 savol/bo‘lim/nashr capability, real port va owner/native qabul
bu qolgan sahifa hisobidan alohida ochiq.
