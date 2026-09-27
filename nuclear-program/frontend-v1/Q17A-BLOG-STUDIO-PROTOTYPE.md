# Q17a — blog studiyasi lokal prototipi

2026-09-27; D31 continuation, source base `324ad57`,
branch `codex/q17a-blog-prototype`. Real runtime/DB/AWS o‘zgarmadi.

## Qamrov va source xaritasi

| Band | Canonical nom | Lokal manzil |
|---|---|---|
| U22 | `blog:studio` | `/blog/studio/` |
| U23 | `blog:studio_create` | `/blog/studio/new/` |
| U24 | `blog:studio_edit` | `/blog/studio/<slug>/edit/` |

Preview: `http://127.0.0.1:8077/blog/studio/`.
Registry `0.72.0-blog-studio`: **121 route /67 page template /100 source
nomi /1077 route-state /191 action**. Uch yangi canonical UI; mavjud
public blog list/detail endi shu sessiyadagi bitta maqola manbasini o‘qiydi.
Dinamik slug va `?preview=1` yangi canonical UI sifatida sanalmaydi.

Source: `blog/views.py`dagi BlogStudioView, BlogPostCreateView,
BlogPostUpdateView va BlogDetailView; `BlogPostForm`/`BlogPost`.
AST testi13 source field va CharField uzunliklarini DB/domain importsiz
solishtiradi. Source UI statuslari draft/published; kelajak published_at
alohida yangi status emas, “Rejalashtirilgan” presentationi.

- Boshqaruv va sinov paneli → studiya → new/edit → draft preview →
  explicit save → immutable exact result → saved sample/public maqola.
- Sintetik muallif o‘z yozuvlarini ko‘radi; foreign edit/draft va
  signed-out private preview404. Qoralama/kelajak nashri publicda yo‘q.
  Shu store generic learner/teacher bootstrapga kiritilmaydi.
- Native POST/303/GET; source13 maydon, muqova preserve/replace/clear,
  teglarni case-insensitive dedup, excerpt/meta fallback, title tahririda
  barqaror slug va takror title uchun unique slug. Eng yangi tahrir yuqorida;
  public featured/published_at tartibi saqlanadi.
- Per-record revision/run/operation, create replay exact slug, stale/reset/
  wrong payload rad, no-op,64 receipt/32 post lokal guard. Unknown javobda
  resend yopiq, exact result faqat GET bilan. GET view/clap yozmaydi.
- Draft run/path/revisionga bog‘liq; uzoq Unicode matn va booleanlar
  saqlanadi; fayl/clear/consent/transport tiklanmaydi. Shared reset prefix
  saqlanadi. Validation bound inputni qoldiradi; yangi tahrir consentni bekor qiladi.
- Q16b raster normalizer reused: source5MiB PNG/JPEG/WebP; local4096px,
  1024px sample/1MiB encoded guard. Original disk/cloudga yozilmaydi.
  Cover fingerprint replayni ajratadi; file+clear yoki oversize no-write.
  CSP data/blob faqat brand/blog yuzalarida, tashqi image host yo‘q.

## Ochiq chegaralar — to‘liq real blog release emas

Prototip fixed clock **2026-09-27 12:00 Europe/Istanbul** bilan ishlaydi;
real soat/scheduling job emas. Sintetik authored scope haqiqiy staff/
superuser permission testining o‘rnini bosmaydi. Backendda revision,
durable replay/receipt kafolati hozir mavjud deb da’vo qilinmaydi; bular
real adapterdan oldingi dependency. Source’da yo‘q audit/sabab maydoni,
delete, yangi status yoki notification qo‘shilmadi. Lokal unchecked save
consent qo‘shimcha UX guard; canonical form maydoni emas.

Body/excerpt20000/4000 va teglar1000 belgi faqat lokal memory guard;
real model limiti deb olinmaydi. HTML escaped oddiy matn; **CKEditor,
inline image upload, sanitizer va rich-text parity OPEN**. Cover clear
lokal `cover_clear` → real ClearableFileInput `cover_image-clear` mappingi
portda kerak. BlogHomeSettings alohida nashr muharriri bu3 URLga kirmaydi.
Public9-item pagination, featured hero va clap/comment capabilitylari eski
Q03 state-parity qabulida ochiq; bu paket ularni yopilgan deb belgilamaydi.

## Tekshiruv

Trial cwd, repository venv; AZURELMS_SKIP_ENV_FILE=1, bo‘sh GEMINI_API_KEY/
TELEGRAM_BOT_TOKEN, LOCAL_USE_REMOTE_SERVICES=0.

- `manage.py check`:0 issue.
- Yakuniy `manage.py test tests --verbosity 1`: **735 PASS (271.959s)**.
- Dastlabki focused blog+public37 PASS; nav fixdan keyin38 PASS.
- `node --test <expanded tests/*.test.mjs>`:186 PASS (567.1105ms); JS syntax PASS.
- IAB Chromium/Windows:50 case —3 studio+2 public ×320/390/768/1024/1280
  ×light/dark; overflow0, ko‘rinadigan controls≥44px. Native create/edit/
  publish, draft reload/unchecked consent,422 retained input, file chooser
  →blob preview→normalized saved image va unknown→exact GET result sinaldi.
  Final mobile create/publish qayta tekshirildi. Qo‘shimcha54 state case:
  3 studio ×9 holat ×320/1280px; overflow0, blocked holatlarda save yopiq.
  Mobile menu Escape fokusni openerga qaytardi; final console error/warn0.
  Viewport override reset qilindi. Actual phone/Safari/AT ochiq.

First full734 run nav regressionda bitta xato topdi: `?workspace=teacher`
new editor tomonidan rad etildi. Allowlisted teacher context qo‘shilib,
learner qiymati hali rad qilinadi; invariant/test yumshatilmadi. Test helperda
slug argument collision tuzatildi. Public `preview=1` eski denied testi
source-backed staff preview admissioniga moslandi; boshqa querylar fail-closed.
CUA locator-evaluate timeoutlari DOM snapshot/read-only document check bilan
tekshirildi; unknown POST ko‘r-ko‘rona qayta yuborilmadi.

## Saqlash va navbat

PR151 review trackerda haqiqiy bo‘shliqni topdi: UI borligi Q17a media
pariteti tugaganini anglatmaydi. Q17a `[x]` emas, `[-]` bo‘lib qoldi;
rich-text/inline media preview/save/public va xavfsiz rendering qabuli
aynan shu ochiq qadamning yakun sharti. Hech qaysi talab hisobdan chiqarilmadi.

Packet72 yakuniy checkpoint (tracker tuzatishidan keyin):
`playground/Eleventh Trial/checkpoints/packet-72-20260927-052810.zip`,
**542 fayl**, har entry SHA256 source bilan tekshirildi. ZIP SHA256:
`2B3FD73853D794083CDDB344E5A3742A0FDDE2A82A22CF3CC61216EB97626751`.
Oldingi `packet-72-20260927-052103.zip` (542 fayl,
SHA256 `5EACBA7E95402213092A2AE84848FF1C05EFCDCF90F4768E8D1F532F0B583456`)
interim dalil sifatida saqlanadi; u Q17a’ni yopilgan deb atagan eski hisobni o‘z ichiga oladi.
Ignored source/screenshots lokal qoladi, force-add/push/upload yo‘q.
Packet71 saqlanadi. Native/owner acceptance,
real port, U17/A2-D01 va kengQ14 capability hamon ochiq.

U22–U24 source-shaped lokal UI qurildi, **Q17a to‘liq yopilmadi**.
Prototipi hali yo‘q **18 UI +3 handler =21 band**; jami **6 ochiq qadam**:
Q17a rich-text/inline media yakuni, Q17b SIT10, Q18 Mini5, Q19 system5,
Q08 legacy attendance1 va final qabul. Keyingi ish Q17a pariteti.
Real port/AWS release ushbu qoldiqdan alohida.
