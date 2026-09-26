# Q14 — source-supported imtihon muharriri prototipi

Sana: **2026-09-27**. Runtime/source bazasi `204bc15` (main).
Ownerning inventar/rejadan keyingi “Davom et” topshirig‘i: D31 continuation.
Branch: `codex/q14-exam-editor-prototype`. Barcha UI va test o‘zgarishlari
ignored `playground/Eleventh Trial` ichida; bu tracked hujjat faqat dalil.
Production kod, DB, konfiguratsiya, real akkaunt va AWS o‘zgarmadi.

## Tayyor natija va chegarasi

- `/backoffice/exams/`: yashirin birinchi-imtihon tanlovi o‘rniga aniq ro‘yxat.
- `/backoffice/exams/101/`, `/102/`, `/201/`: ikki kursdagi uchta ajratilgan
  sintetik imtihon. ID101/102/201 mavjud learner exam5 bilan aralashmaydi.
- `core.views.backoffice_exam_editor`, `ExamBackofficeForm`dagi10 va
  `ExamSectionBackofficeForm`dagi8 maydon: **18/18**. Imtihon/kurs/tur,
  ball/ulush/urinish, prerequisite/uy vazifa/dars/davomat talablari va
  birinchi bo‘limning matn/tur/media-manzil/ball/vaqt/tartibi.
- Birinchi bo‘lim source kabi order bo‘yicha tanlanadi. Mavjud bo‘lmasa
  explicit save uni yaratadi. Qolgan bo‘limlar va savol sonlari readonly.
- Native POST → 303 → o‘sha imtihon receipt GET; JSsiz ham asosiy forma
  ishlaydi. Qoralama tiklash, local save holati va dirty warning JS enhancement.
- Stale revision, reset-run, boshqa kurs prerequisite, noma’lum/takroriy
  maydon, invalid input rad etiladi. Formaning ikkala qismi atomik.
  Bir operation qayta yuborilsa takror yozmaydi; payload almashtirish409.
  64 receipt chegarasi to‘lsa429; eski receipt o‘chirilmaydi.
- Aloqa/xato/expired/locked/emptyda write yo‘q; bound qiymatlar saqlanadi.
  Unknown-result503dan keyin tugma blok; faqat exact receipt GET tasdiqlaydi.
- Qoralama run/exam/first-section identity bilan ajratilgan. Eski versiya
  avtomatik rebase qilinmaydi. Tasdiq, CSRF, run va operation draftdan
  tiklanmaydi. Lab reset shu tabdagi qoralamalarni tozalaydi.

**Q14ning keng savol konstruktori hali tugamagan.** Savol CRUD, barcha
bo‘limlarni authoring, nashr boshqaruvi va yangi imtihon yaratish uchun
joriy source’da tayyor oqim yo‘q. Bu capabilitylar olib tashlanmadi;
owner admission + canonical contract + alohida implementation kerak.
Hozir yopilgan qism — rejaning U01/U02 uchun source-supported local UI.
Real port/AWS/owner-native acceptance yopilgani emas.

## Canonical farqlar — keyingi portga aniq topshiriq

1. Preview revision/idempotency/atomic save himoyasi real backend kafolati
   emas. Portdan oldin scoped RBAC va durable concurrency/action receipt
   canonical xizmatida alohida qurilib tekshiriladi.
2. Kurs ko‘chirishda ushbu examga boshqa exam prerequisite orqali
   bog‘langan bo‘lsa, preview dangling cross-course talabga yo‘l qo‘ymaydi.
   Bu local himoya source’ning mavjud paritysi deb ko‘rsatilmaydi.
3. Source CKEditor o‘rnida xavfsiz escaped oddiy textarea: instructions4000,
   reading8000 belgi; request32KiB. Rich HTML, media upload/ijro/fetch yo‘q.
4. Section order teng bo‘lganda preview ID bilan deterministik tanlaydi;
   source tie qoidasi portda tekshiriladi. Learner timer/grade/access yangi
   metadata bilan qayta hisoblanmaydi va sinovdan “nashr” qilinmaydi.
5. Preview session/workspace haqiqiy staff RBAC emas. DB, provider,
   boshqa browser engine, actual touch/AT va production data ishlatilmadi.

## Tekshiruv

Barcha Python buyruqlar provider-free: `AZURELMS_SKIP_ENV_FILE=1`, bo‘sh
`GEMINI_API_KEY`/`TELEGRAM_BOT_TOKEN`, `LOCAL_USE_REMOTE_SERVICES=0`.

Trial papkasidan:

```powershell
& 'C:/Users/azizb/Desktop/project/azurelms/venv/Scripts/python.exe' manage.py check
& 'C:/Users/azizb/Desktop/project/azurelms/venv/Scripts/python.exe' manage.py test tests --verbosity 1
$trialTestFiles = @(Get-ChildItem -LiteralPath tests -Filter '*.test.mjs' | ForEach-Object FullName)
node --test @trialTestFiles
```

- Isolated check: **0 issue**. To‘liq Django: **606 PASS**, shu jumladan
  yangi16 editor testi. Node: **168 PASS**, yangi4 draft-state testi.
- Dastlabki umumiy regression ustoz workspace querysini400 qaytarishini
  topdi; `workspace=teacher` qabul qilindi, learner/unknown query rad qoladi.
  Test susaytirilmadi. Root cwd’dan `test tests` 0 topgan urinish PASS
  hisoblanmadi; trial cwd’dan haqiqiy discovery bilan qayta bajarildi.
- IAB/Chromium desktop + 320/390/768/1024/1280px, light/dark:
  document overflow yo‘q; yangi input/select/choice/button hit-boxlari
  kamida45px. 320px uzun sarlavha, mobil ro‘yxat va editor tekshirildi.
- Native save/receipt, cross-course inline validation va error focus,
  ro‘yxatga qaytish/draft restore, unchecked consent, unknown-result→receipt,
  mobile menu Escape/focus, reset va fresh sample tekshirildi.
- Native confirm dastlab IAB boshqaruvini to‘xtatdi; shu sabab yangi popup
  o‘rniga mavjud `c-dialog` ishlatildi. Qayta sinovda Escape triggerga,
  restore esa title maydoniga fokus qaytardi. Browser logs: JS error/warn0.
- Screenshots (local ignored): `evidence/q14-desktop-light.png`,
  `q14-mobile-light.png`, `q14-mobile-dark.png`. Real qurilma/AT PASS emas.

Registry: **99 preview URL /56 page template /78 source nomi /879 route-state**.
Oldingi95/54/76dan o‘sish:4 URL,2 template,2 source nomi. Qolgan yangi UI:
**40 URL +3 handler =43 qamrov bandi**, keyingi10 reja qadami. Oldingi
oilalarning state paritysi va keng Q14 capability qarzi alohida ochiq.

## Lokal saqlash

V1 boshlang‘ich nusxa: `playground/Eleventh Trial/checkpoints/packet-66-20260927-000623.zip`;
452 faylning arxiv/source hash mosligi tekshirildi. SHA256:
`6E374B5000C0F73155B75EAF1BF3BA87901449BE8C4809B93D1F017E577738DE`.
Paket67 yakuniy nusxa: `playground/Eleventh Trial/checkpoints/packet-67-20260927-003746.zip`;
466 faylning arxiv/source hash mosligi tekshirildi. SHA256:
`855BC5BE22F979FFF961EE7ADE52F6E65EDE3C29A4F10399218A0F521B5F1D10`.
Yakuniy qayta regressiya:606 PASS (190.471s); Node168 PASS, JS syntax PASS.
Prototype fayllari Gitga force-add yoki tashqi joyga upload qilinmaydi.
