# PAR-03 — public blog va SIT yo‘llari

2026-10-04, Packet81; source base `a33d87d`. Admitted lokal implementation
yakunlandi. Bu **G3/G4, pixel/native/owner qabul yoki real port emas**.
Ignored Eleventh Trial o‘zgardi; canonical runtime/DB/AWS o‘zgarmadi.

## Manba va qurilgan qism

`blog/views.py`, `blog/forms.py`, `blog/models.py`, `blog/urls.py`, SIT view/
selector va `templates/frontend_v1/public/sit/` o‘qildi. AST regressiya
source’dagi2000belgi,50clap,one-level reply,9/page va help→tutorni solishtiradi.

- Blog: plain-text izoh, bitta darajali javob, like toggle, viewerga50clap.
  Guest clap mumkin; comment/like hisob talab qiladi. Yopiq izohlar yangi
  comment/replyni to‘xtatadi, existing like’ni emas. Faqat live publication;
  parent same-post/root/nondeleted. Matn HTML sifatida bajarilmaydi.
- Run/actor/post revision/interaction revision/UUID strict envelope,
  CSRF, exact replay va immutable receipt. Noaniq so‘rovdan keyin reload
  ham takror yuborishni ochmaydi; explicit GET receipt kerak. Peer stale
  holatda draft qoladi. Draft run/post/actor/tabga scoped.
- Native POST→303→GET; invalid/stale matn escaped/wrapped ko‘rinadi.
  Blog9/page va featured exclusion, filter/detail return saqlanadi.
- SIT home maslahatchi mavjud Azure AIga; yordam yoqilgan universitet
  mavjud tutor chatiga olib boradi. Guest login next bor; native Back bilan
  qaytish. **Ariza backend/wizard yoki avtomatik AI/xabar yuborish yo‘q.**

Registry:139namedURL/77page/118source/1223state/**213action** +3handler.
5action va4non-UI endpoint qo‘shildi; screen soni o‘zgarmadi. Existing shell,
token va patternlar ishlatildi; yangi palitra/font/breakpoint/dependency yo‘q.

## Tekshiruv dalili

Isolated `playground/Eleventh Trial` cwd; `AZURELMS_SKIP_ENV_FILE=1`,
`GEMINI_API_KEY=` va `TELEGRAM_BOT_TOKEN=`. Real env/provider ishlatilmagan.

- `../../venv/Scripts/python.exe manage.py test tests --verbosity 0`:
  **858 PASS**,767.520s, check0.
- Oxirgi native error/comment text-wrap template tuzatishlaridan keyin
  `../../venv/Scripts/python.exe manage.py test tests.test_blog_public tests.test_public_content tests.test_blog_studio tests.test_sit_studio --verbosity 0`:
  **73 PASS**,39.760s; yangi17backend test shu son ichida.
- PowerShellda barcha `tests/*.test.mjs` kengaytirilib `node --test`:
  **223 PASS**,final700.4257ms; yangi4state test. JS syntax va Django check PASS.
- IAB8086: izoh/reply/like/clap; draft→reload; unknown503→reload locked→
  GET receipt→bitta yozuv; two-tab stale409→refresh→save. Guest clap va login
  next/Back; SIT→AI/tutor→Back. Tab/Enter submit→status focus/draft clear.
 502belgili multiline/unbroken comment reload oldi/keyin exact teng,
 320px overflow0; server/enhanced text bir xil `pre-wrap` ishlatadi.
- **48 DOM responsive**:3surface×2theme×8width(320..1920),overflow0,
  yangi blog controls/SIT CTA≥44px. Blog1840belgi draft/duplicateID0.
  Warning/error log0. Normal/unknown/stale/expired/empty browserda ko‘rildi.
- Full9-state browser loop navigatsiya timingida to‘xtadi; PASSga kirmaydi.
  Backend/route-state suite yuqoridagi858test ichida o‘tdi.
- Screenshot ikkala documented API’da unavailable: **pixel-level visual
  review NOT VERIFIED**. DOM tekshiruvi uning o‘rnini bosmaydi. Native phone,
  iPhone Chrome UX-01, AT/Firefox/WebKit/no-JS browser smoke NOT TESTED.
  Native POST fallback faqat Django client bilan tekshirildi.

## Real port chegarasi va saqlash

Legacy real blog endpointlarda yangi strict revision/idempotency/receipt
kafolatlari yo‘q; real portda canonical adapter alohida kerak. Local preview
real RBAC/durable storage/multi-user concurrency/rate-limit tasdig‘i emas.
128comment/256receipt technical cap, reset/restart local state’ni tozalaydi.
Real content, SIT fakt/narx va native/owner acceptance ochiq qoladi.
Human messenger reply capability bu blog reply bilan yopilmaydi.

Source/assets/testlar `playground/`da ignored; force-add/upload qilinmadi.
Gitga faqat dalil/tracker/marinebook kiritildi. Verified checkpoint:
`playground/Eleventh Trial/checkpoints/packet-81-20261004-123924.zip`,
**652fayl**,har ZIP entry SHA256 asl nusxa bilan tekshirildi.
ZIP SHA256 `8233465C786F06E17BD691A6CA920799D69BBAECDED7448458ECA9DC5201F949`.
Oldingi12:34 Packet81 checkpoint ham saqlandi; final matn-wrap tuzatishi
12:39 nusxaga kirgan. Full858 testdan keyingi template delta focused73 bilan qoplandi.
Old Packet80 saqlandi/hash qayta tekshirildi. Bu bir diskdagi lokal
checkpoint; mustaqil disaster-recovery backup emas.

Qolgan local-parity **PAR-05**. Keyin UX/DATA/RULE/native/owner final qabul,
undan keyin DESIGN-01. Real port/deploy alohida, avtomatik bajarilmaydi.
