# DESIGN-01 DC4 — lokal nashr, tarix va rollback

**Tarixiy snapshot:** quyidagi19hash Packet88ga tegishli. Joriy lokal
consumer preview va source hashlar [DC5](DESIGN-01-DC5-REGRESSION.md)da.

2026-10-10. Owner “davom et” bilan DC4ni boshlashni topshirdi.
Lokal publish/readback/history/rollback qurildi va sinovdan o‘tdi.
Real owner autentifikatsiyasi, DB va barcha consumerlarga tarqatish hali ochiq.

## Admission va chegaralar

| Savol | Qaror |
|---|---|
| Outcome / KPI | Owner tasdiqlagan ko‘rinishga qaytish; duplicate/stale/unknown oqimda ortiqcha nashr0 |
| Admission | EXPERIMENT — production canonical state yozilmaydi |
| Writer | Lokal preview processidagi yagona release service; signed synthetic browser identity bilan scope |
| Adapter | Design editor → prepare/publish/readback/history/rollback API; inert frame joriy versiyani ko‘rsatadi |
| Owner yuki | Sabab/tasdiq, joriy versiya va farq; yo‘qolgan javob uchun alohida readback |
| Failure / rollback | Atomic copy-on-write; revision/epoch/idempotency; tarix o‘chmaydi, rollback yangi version |
| Release | Loopback va vaqtinchalik RAM. Server restartda experiment yo‘qoladi; Packet87 saqlanadi. Real DB/flag/auth/port/AWS alohida |

DC2dagi production `/backoffice/control/design/` namespace va existing
active-superuser gate kontrakti saqlanadi. Quyidagi lokal endpointlar
production authentication/RBAC enforce qilindi degani emas. DC4 lokal
state machine qabuli va **DC4 real port qabuli** alohida kuzatiladi.

## Lokal oqim va yagona writer

`prototype/preview/design_release.py` yagona writer; adapterlar saqlashni
takrorlamaydi. `design_validation.py` serverda catalogdagi typed bounds,
30 kontrast juftligi ×2mode va typography policy’ni qayta tekshiradi.
Frontend ayni `design_catalog.json.validation` kontraktini o‘qiydi.
Catalog versiyasi1;20guruh/87field/118qiymat saqlangan.

| Endpoint | Amal va chegarasi |
|---|---|
| GET `/_preview/design/release/` | Published snapshot, private editor draft, history; optional operation/epoch bilan receipt. Writer emas |
| POST `/_preview/design/release/prepare/` | Private draft revision CAS; schema va semantic validation |
| POST `/_preview/design/release/publish/` | Tayyorlangan revision + base version + sabab/tasdiq; qayta validation |
| POST `/_preview/design/release/rollback/` | History target qayta validation; o‘chirish o‘rniga yangi versiya |

POST envelope: UUID `editor`/`operation`, scope `epoch`, integer
`base_version`; prepare uchun `draft_revision,value`, publish uchun
`draft_revision,reason,confirmed`, rollback uchun `target,reason,confirmed`.
Ortiqcha yoki takrorlangan JSON/query maydonlari, NaN/Infinity, boolean
raqam, invalid enum/range/step rad etiladi. JSON body ≤40000byte;
reason3–300belgi, control character yo‘q; confirmed aynan true.
CSRF majburiy, GET mutatsiya qilmaydi, method mos kelmasa405.

Service boundary authenticated/active/superuser tekshiradi. **Lokal HTTP
adapter ishonchli synthetic owner fixture beradi**, login/RBAC o‘rnini
bosmaydi. Request actor/role qabul qilmaydi. Sinovlarda server fixture
anonymous401, staff/non-owner403 va inactive403 bilan tekshirildi.
Signed browser identity’lar bir-biridan ajralgan; shu brauzerdagi tablar
published/history’ni ulashadi, draft va operation receipt editorga tegishli.
General preview projection private release/draft/actor/scope’ni chiqarmaydi.

## Holat o‘tishlari va invariantlar

| Trigger | Natija |
|---|---|
| Draftni tayyorlash | Server validation; private revision oshadi, published o‘zgarmaydi |
| Sabab/tasdiq + publish | Atomic published/history/receipt; current preview yangi versiyani oladi |
| Same typed snapshot | No-op receipt; tarix/version oshmaydi |
| Bir operation, bir payload | Oldingi receipt qaytadi; ortiqcha nashr yo‘q |
| Operation boshqa payload/editor bilan |409idempotency_conflict |
| Stale base yoki draft revision |409; GET va yangi farq/tasdiq talab qilinadi |
| Response yo‘qolgan yoki500 | Pending marker saqlanadi; mutation yopiq, faqat GET readback |
| Reload + matching receipt | Natija aniqlanadi; POST takrorlanmaydi |
| Receipt topilmadi | No-write deb taxmin qilinmaydi; unknown yopiq qoladi |
| Process/browser identity/session reset | Scope epoch almashadi; oldingi amal replay qilinmaydi |
| Storage quota yoki before-send failure | POST yuborilmaydi |
| Rollback | Immutable targetdan yangi versiya; eski tarix saqlanadi |

Pending operation markeri so‘rovdan **oldin** sessionStorage’ga yoziladi.
Broken store ustiga yozilmaydi; busy/double-click guard bor. Avtomatik POST
retry yo‘q. Server lock va copy-on-write oldingi snapshotni xatoda saqlaydi.
500dan keyin receipt yo‘q bo‘lsa bu processda yangi mutation ochilmaydi;
sinov sessiyasini yangilash alohida recovery, production recovery talabi ochiq.

Memory guardlar:500receipt,50history (v0ham),32editor draft.
Limitda fail-closed; tarix/receipt yashirin evict qilinmaydi. Preview’ning
existing100browser-session evictioni scope epoch bilan ajratiladi.
Server restart/session reset bu disposable tarixni yo‘qotadi.

UI publish oldidan aynan ko‘rinayotgan draft serverdagi tayyorlangan
revisionga tengligini tekshiradi. Draft/sabab/history tanlovi o‘zgarsa
tasdiq bekor bo‘ladi. History tanlanganida publish yopiq; rollback farqi
ko‘rsatiladi. Joriy versiyani qoralamaga olish explicit yes/no bilan.
Readback qoralamani almashtirmaydi. Tab-local preset/draft saqlash DC2da
qoladi; real persisted preset CRUD/RBAC ham port qabuli ichida ochiq.

## Tekshiruv dalillari

- Eleventh Trial ichida env-file off, Gemini/Telegram keys bo‘sh:
  `../../venv/Scripts/python.exe manage.py test --verbosity 0`:
  **902 PASS**,325.508s; `manage.py check`:0issue. To‘liq suite serverdagi
  scope reset fixidan keyin o‘tdi; keyingi o‘zgarish faqat UI tarix/diff matni.
- Node `tests/*.test.mjs` PowerShell array bilan: **281 PASS**,852.2959ms.
  Yangi9test pending/reload/readback, absent receipt, quota, stale, epoch,
  before-send, double-click, corrupt contextni tekshiradi.
- Focused Django release: **14 PASS**,0.060s; service+HTTP permission,
  CSRF, parity policy, atomic failure, no-op/rollback, concurrency,
  receipt isolation, scope reset va capacity tekshirildi.
- IAB: publish v1; ayni payload yangi operation bilan no-op v1;
  lost response/reload GET bilan v2; rollback v0→v3, radius24→8;
  keyingi v4dan so‘ng ikkinchi tab stale409, radius12 draft saqlandi.
  Load cancel12/confirm24; before-send v4 o‘zgarmadi.
- Published preview7page ×2mode ×4width = **56frame**, actual
  innerWidth320/390/768/1280, mode/page matched, root overflow0.
  Vertical scrollbar sabab clientWidth15px kichik — hisobda ajratilgan.
  Editor4width: root va release control overflow0; desktop/mobile screenshot
  ko‘rildi. Bu turnda DC4tab console error/warn0; native/AT qabuli emas.
- Lokal dalil: `playground/Eleventh Trial/evidence/dc4-browser.json`,
  `dc4-desktop.jpg`, `dc4-mobile.jpg`, Django/Node loglari.

## Ochiq qabul

DC4 real port: actual existing owner gate/login bilan barcha namespace
endpointlari; own draft/preset ACL; DB transaction va multi-worker CAS;
durable idempotency/audit/readback; cache invalidation; core flag registry;
consumer effective tokens/fallback. Bu turnda production import/model/
migration/provider/AWS o‘zgarmadi. Remote CI ignored prototype source’ni
ishga tushirmaydi; lokal test dalili alohida.

DC5 barcha mapped consumer regression va istisnolar, DC6 native zoom/AT,
owner walkthrough va real release gate ochiq. Oldingi UX/DATA/RULE qabul
bandlari ham saqlanadi. Lokal katalog24action/18state,4URLpattern/2template;
existing registry0.84/139route/77page/213action o‘zgarmagan.

## Lokal source fingerprintlar

CRLF → LF normalizatsiyasidan keyingi SHA256; Eleventh Trialga nisbiy.

| Fayl | SHA256 |
|---|---|
| `prototype/contracts/design_catalog.json` | `220f4135d053e6a280c1f9bd85f7a8e0d6e2a15389714721ca90db33c2458446` |
| `prototype/preview/design.py` | `f1c79686450380fdd0f98b7eb9e689397a3d950135549561c2368fb894a687b9` |
| `prototype/preview/urls.py` | `e912c1a98d9d5589290c833a1a90e28d6a89282df953f89c8a083d6d9247605e` |
| `prototype/templates/design/studio.html` | `b8b0fad853ed44f9203ae9f7a2b7e1a79b241203549d833c668153ab4b8f4d63` |
| `prototype/templates/design/frame.html` | `5bf290245092f4f366d71ee6d1f67e3851aeaed5a263f80049632a4316455c53` |
| `prototype/static/js/design_model.mjs` | `29a15e2c4f365ee137a22f4cf5950289790b85d572262a16ca3d638b9ea24f67` |
| `prototype/static/js/design_studio.mjs` | `513637e7a45dc44f22e2a04e9a006a37046383def33df7ab7348cb8d9fa3cf3f` |
| `prototype/static/css/design_studio.css` | `5fcab1e4e3c560cdb8b06ac2f4890408519701a5ed77e77e46e9ff6273e113c6` |
| `prototype/static/css/design_preview.css` | `d7ae8e0b87c83eb0d27b561d673cf3a7607a097b75040079fe27f174acd82566` |
| `tests/test_design.py` | `1d7b9f576a4dcb9d3ef7983edb34512105a38eaa0196e80b9965bd5f084d1c18` |
| `tests/design_model.test.mjs` | `14271502d613dc97a738f66ce6e8c788951b45472850574470c094a964b5ae02` |
| `tests/design_validation.test.mjs` | `e5c5c8c890bdd04f1987df6c27554ed0b04471b025a5f5729ee2f7433b3a2755` |
| `prototype/preview/state.py` | `5200a46b667283bc48141af3664788d76430cdb7397d882bea11aff6be6275b4` |
| `prototype/preview/design_release.py` | `d203fc3b8f857d2f8965ca0c02f6c66536898424a1a25f366884da394a3eb15c` |
| `prototype/preview/design_validation.py` | `7b57842b32b8aee8523d8480157ea92b3e5a5d01c8964a630475841027a69fb1` |
| `prototype/static/js/design_release.mjs` | `c487f199704861082801282a799247e06d3e5b5d7103f663397d7ae5d9f4bd58` |
| `prototype/static/js/design_release_ui.mjs` | `281708239d131583d9c4d90fccdf738a26e009f2075cdd47d3a0968a16a7ca16` |
| `tests/test_design_release.py` | `8d7a19f5b55baaedc1211da70b10c2e7ec3c65cf0b13cd82bd9960d0a89ced64` |
| `tests/design_release.test.mjs` | `9c8105f5bd8098193e4b017a9963c1312daec5f8d8a54bd3b0d4d5797096b77a` |

## Tiklash checkpointi

`playground/Eleventh Trial/checkpoints/packet-88-20261010-094736.zip` — **715 fayl**; har entry
SHA256 bilan tekshirildi. ZIP SHA256: `CA47D28BA0825E7034354C876A61E1A9F975E733F7EC2131AD6F4CA75AB3B0FA`.
Packet87 retained/hash matched; uning12source hashi archive ichida tekshirildi.
Shared tokens/base/components/shell CSS va existing registry baytlari o‘zgarmagan.
Joriy19source hash live va Packet88 uchun tekshiriladi. Archive env/cache,
checkpoint papkasi/index va DC2/DC3/DC4 server loglarini olmaydi.
Source/arxiv ignored, force-add/upload yo‘q; bir diskdagi recovery, offsite emas.
