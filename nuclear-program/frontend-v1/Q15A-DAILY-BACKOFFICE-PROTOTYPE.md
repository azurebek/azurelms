# Q15a — kundalik boshqaruv prototipi

Sana: **2026-09-27**. Source/runtime bazasi `acdd0fc` (main).
Branch: `codex/q15a-backoffice-prototype`. D31 continuation, owner “davom et”.
Paket68 source va testlari ignored `playground/Eleventh Trial` ichida;
Gitga faqat tekshirish dalili va progress hujjatlari kiradi. Real runtime,
DB, staff akkauntlari, moliyaviy ma’lumot va AWS o‘zgarmadi.

## Admission va bajarilgan oqim

**EXPERIMENT — canonical state yozmaydi.** Owner navbatdagi chekni topib,
sababli qaror qilib, ayni filtrga qayta olishini tekshirish maqsad qilingan.
Asosiy mezon: to‘rtta ro‘yxat/qaror yo‘lida noto‘g‘ri obyektga o‘tish yoki
takroriy yozish yo‘q. Production operatsion yuk, provider yoki yangi flag
qo‘shilmadi. Reset faqat lokal sintetik sessiyani tiklaydi; old Paket67
checkpointi saqlanadi. Bu yangi launch majburiyati yoki deploy emas.

| Source / URL | Prototipdagi tayyor qism |
|---|---|
| `core.views.backoffice_dashboard` — `/backoffice/` | Tekshiruv navbati, ro‘yxatlarga kirish, aniq nomlangan sintetik KPI snapshoti |
| `core.views.backoffice_receipts` — `/backoffice/receipts/` | Qidiruv/holat → exact chek → verify/reject → sabab/consent → qaror tasdig‘i → o‘sha filtr |
| `core.views.backoffice_users` — `/backoffice/users/` | Qidiruv, rol/holat, 12 tadan pagination, joyida readonly tafsilot |
| `core.views.backoffice_chats` — `/backoffice/chats/` | Qidiruv/tur, 12 tadan pagination, ishtirokchi/xabar soni va oxirgi xabar; readonly |

Platform shell/tokens saqlangan. Bitta lokal to‘rt bo‘limli navigatsiya;
user block, chat delete yoki boshqa odam AI chatiga kirish qo‘shilmadi.
GET o‘zi yozmaydi, filtr o‘zgarganda avtomatik navigatsiya qilmaydi.
Noma’lum, takroriy, noto‘g‘ri query qiymati va begona result ID rad etiladi.
Native tafsilot disclosure bir xil URLda qoladi; list→detail→Back/return
querysi saqlanadi. Sinov panelining qaytish URLi ham allowlist bilan.

## Chek qarorining yagona manbasi

- Checkoutdan yuborilgan #31 va tarif-farqi #301 cheklari owner ro‘yxatida
  aynan mavjud `purchase` holatidan olinadi. Qaror existing `payments.apply`
  adapteridan o‘tadi; learner pending/success o‘sha natijani ko‘radi.
- #701/702/703 — boshqa ro‘yxat misollari uchun alohida sintetik yozuvlar.
  Ularning qarori learner purchase/progress/accessga tegmaydi. Boshqaruv
  state’i, qaror sababi va operatsiya jurnali umumiy bootstrapga kirmaydi.
- Canonical manba: `core/receipt_forms.py`, `cohorts/receipt_service.py`.
  Ikkala qarorda ham 1–240 belgi sabab va alohida tasdiq kerak. Tarif
  farqi muddatni uzaytirmaydi. Reject chek yozuvini olib tashlaydi;
  qolgan natija UI audit tombstone, saqlangan PaymentReceipt emas.
- Native POST → 303 → exact result GET. Run/receipt/revision/operation
  tekshiriladi; duplicate no-op, altered payload/stale/reset409.
  64 qaror sig‘imi to‘lsa yangi write429; eski result evict qilinmaydi.
- Invalid422, error/offline503, locked/empty403, expired401da write yo‘q.
  Sabab bound formada qoladi; chek boshqa oynada o‘chirilsa matn alohida
  ko‘rsatiladi. Unknown-result503da takror yuborish tugmasi yopiq, faqat
  exact result GET. Qoralama run/chek/versiya bo‘yicha sessionStorage’da;
  consent va operation avtomatik tiklanmaydi.

## Muhim port chegaralari — yopilmagan

1. Synthetic workspace haqiqiy staff RBAC emas. Real permission, audit,
   notification va enrollment/plan transactioni canonical xizmat orqali
   testlanadi. Preview yangi access/narx/daromad formulasini hisoblamaydi.
2. Chek bayti saqlanmagan; metadata nomi ko‘rsatiladi, asl bank cheki
   deyilmaydi. Real private `cohorts:receipt_file` previewi integratsiyada
   ulanishi va negative access sinovidan o‘tishi shart.
3. Receipt qidiruv/holat/pagination — UI convenience; joriy canonical
   receipt view pending va recent10ni beradi, POST filtrlarga qaytmaydi.
   Real query/PRG return va durable revision/idempotency port talabi;
   ular hozir real backendda mavjud deb ko‘rsatilmaydi.
4. Dashboard moliyaviy snapshoti oldindan yozilgan namuna; qarordan
   taxminiy daromad/access hisoblanmaydi. Users/chats source supported
   readonly maydonlar bilan cheklangan. Yangi moderation capability yo‘q.
5. Real qurilma, iOS/Android/AT, owner acceptance, Q15 real port va to‘liq
   G2/G3 ochiq. AWS `8bb6b95` va19 renderer flag holati o‘zgarmadi.

## Tekshiruv va checkpoint

Trial cwd; provider-free env: `AZURELMS_SKIP_ENV_FILE=1`, bo‘sh
`GEMINI_API_KEY`/`TELEGRAM_BOT_TOKEN`, `LOCAL_USE_REMOTE_SERVICES=0`.

```powershell
& 'C:/Users/azizb/Desktop/project/azurelms/venv/Scripts/python.exe' manage.py check
& 'C:/Users/azizb/Desktop/project/azurelms/venv/Scripts/python.exe' manage.py test tests --verbosity 1
$trialTestFiles = @(Get-ChildItem -LiteralPath tests -Filter '*.test.mjs' | ForEach-Object FullName)
node --test @trialTestFiles
```

- Isolated check:0 issue. To‘liq final **630 Django PASS** (204.472s),
  yangi24 Q15a test. Oldingi628 run ham PASS. Focused25 PASS;
  **Node170 PASS**, yangi2 draft testi. JS syntax va `git diff --check` PASS.
- Browser: 4 route × 5 width (320/390/768/1024/1280) × light/dark =40
  ko‘rinish; gorizontal overflow/tor hit-box aniqlanmadi. Mobil uzun matn,
  menu Escape/fokus, GET filter, 12→3 user pagination, Back va tafsilot PASS.
- Sabab reload’da tiklandi, consent unchecked qoldi; native approve/result,
  reject unknown→read-only result, reset va o‘sha filtrga return PASS.
  Learner checkout #31 yuborish→owner approve→learner “Tasdiqlangan”
  browserda yakunlandi. JS error/warn0; real bank/providerni ishlatmaydi.
- Dastlabki test action metadata yetishmasligini topdi; kontrakt to‘ldirildi.
  Browser lab-return query400ni topdi; exact allowlist va regression qo‘shildi.
  Testlar susaytirilmadi, muvaffaqiyatsiz urinishlar PASSga sanalmadi.
- Local screenshots: `evidence/q15a-desktop-light.png`,
  `q15a-mobile-light.png`, `q15a-mobile-dark.png`.

Registry qayta sanaldi: **103 URL /60 page template /82 source nomi /
915 route-state /185 action**. U03–U06 lokal UI qurildi. Endi yangi
prototipi yo‘q **36 UI +3 handler =39 band, 9 navbatdagi qadam**.
Keyingi **Q15b: tarif/guruh/a’zolar (5 URL)**. Keng Q14 va eski state-parity
qarzlari shu39 ga yashirin qo‘shilmaydi yoki yopilmaydi; rejada alohida.

Paket68 nusxa: `playground/Eleventh Trial/checkpoints/packet-68-20260927-011831.zip`;
**485 fayl**, har birining source/archive SHA256 mosligi tekshirildi.
Arxiv SHA256: `6F5354ADB7DD1D9D55712CBF1E56787145C355AFB6D7AB67818FC526F0DFE356`.
Old Paket67 nusxasi overwrite qilinmadi. `CHECKPOINT.md` ZIPga kirmaydi;
dalil source/xeshga tsiklik bog‘lanmaydi. Tracked docs PR uchala required
CI yashil bo‘lmaguncha merge qilinmaydi; bu CI ignored prototip testlarini
yurgizadi degani emas — lokal test natijalari yuqorida alohida yozilgan.
