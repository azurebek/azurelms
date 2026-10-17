# BLOG-01 — Azure Journal’ni o‘quv kontent markaziga aylantirish

**Holat: REJA TAYYOR, IMPLEMENTATSIYA BOSHLANMAGAN.**
2026-10-15; source audit tayanchi `main`dagi **`66344f0`**.

Owner topshirig‘i: blog qismini radikal isloh qilish, takomillashtirish va
texnik bilimsiz ham qulay boshqariladigan qilish. Bu hujjat BLOG-01 uchun
yagona batafsil reja. Joriy umumiy holat [loyiha kirishida](../README.md),
oldingi public port dalili [I5a](I5A-PUBLIC.md), tarixiy Q17a prototipi esa
[alohida workshop qaydida](Q17A-BLOG-STUDIO-PROTOTYPE.md). Prototip real
runtime, ruxsat, sanitizatsiya yoki saqlash shartnomasi deb olinmaydi.

## 1. Qaror: yakunda qanday mahsulot bo‘ladi?

Blog umumiy “yangiliklar sahifasi” emas, **Azure Journal — o‘zbek tilida
turk tilini o‘rganishga yordam beradigan ishonchli o‘qish va yo‘naltirish
markazi** bo‘ladi.

O‘quvchi yoki mehmon:

- daraja, mavzu va maqsad bo‘yicha foydali maqolani tez topadi;
- telefonda chalg‘itmaydigan, o‘qilishi qulay maqolani ko‘radi;
- maqolaning o‘quv maqsadi, asosiy turkcha iboralari va keyingi amali aniq
  ekanini tushunadi;
- saqlash, izoh, ulashish va kursdagi tegishli darsga o‘tishda holatini
  yo‘qotmaydi;
- JavaScriptsiz ham asosiy o‘qish, qidiruv, izoh va reaksiyadan foydalana
  oladi.

Muallif, muharrir va owner:

- qoralama → ko‘rib chiqish → rejalash → nashr → arxiv oqimini bir joyda
  boshqaradi;
- saqlangan, kim o‘zgartirgan, nashrga aynan qaysi revision chiqqan va
  xato bo‘lsa nimaga qaytishni ko‘radi;
- texnik HTML, teg sintaksisi yoki admin ichidagi yashirin amallarsiz
  maqola, glossary, SEO, bog‘liq kurs/dars va coverni tayyorlaydi;
- komment, tarqatish va natijani bir ish stolida ko‘radi, lekin Telegram,
  notification yoki analitika uchun alohida parallel haqiqat yaratmaydi.

### Admission va qamrov

**Umumiy natija: `ADMIT — post-launch`.** BLOG-01 mavjud public blog ustidagi
mahsulot islohoti; u oldingi launch-critical public minimumni qayta ochmaydi.
Ammo BLOG1.0dagi stored-XSS xavfi, preview/ruxsat va ma’lumot yaxlitligi ishlari
**xavfsizlik maintenance’i** sifatida qolgan bosqichlardan mustaqil oldinga
olinishi mumkin. “Post-launch” xavfsizlik topilmasini kutish degani emas.

BLOG-01 yangi kurs engine’i emas. U:

- course/lesson, access, progress, XP, streak, notification va Telegram
  qoidalarini takrorlamaydi;
- real-time tarjimon, universal lug‘at/SRS, videokonferensiya, yangi email
  platformasi yoki alohida analytics vendor yaratmaydi;
- blog o‘qilishini kurs tugatildi, XP berildi yoki bilim o‘zlashtirildi deb
  hisoblamaydi;
- AI’ni avtomatik yozuvchi yoki nashr qiluvchi qilmaydi.

Bu rejaning tayyorligi [BACKOFFICE-03](BACKOFFICE-REFORM-PLAN.md#backoffice-03),
[CLASSBOOK-01](CLASSBOOK-REFORM-PLAN.md) yoki A8→A9 navbatini yashirincha
o‘zgartirmaydi. BLOG1.0 xavfsizlik ishi incident/maintenance sifatida alohida
ustuvorlashtirilishi mumkin; qolgan kesimlar ownerning joriy queue qaroriga kiradi.
**Implementatsiya hozir queuega qo‘yilmadi.** Owner keyingi aniq task sifatida
BLOG1.0a1ni yozma tanlamaguncha agent ushbu reja sabab branch ochmaydi; mavjud
B3.1a/CB1.1a va launch navbati o‘z hujjatlaridagi holatda qoladi.

### O‘lchanadigan natija

Bugungi baseline alohida synthetic fixture va owner walkthrough bilan
BLOG1.0da olinadi. Hozir o‘lchanmagan son reja ichida “yaxshilandi” deb
yozilmaydi.

| Outcome | KPI | Qanday o‘lchanadi |
|---|---|---|
| Kerakli maqolani topish | search zero-result ulushi, list → detail ochilishi | first-party minimal event/aggregate; raw query cheklangan retention |
| Mazmunli o‘qish | 30 soniya + kamida 50% mazmun ko‘rilgan engaged read | bot/previewdan xoli, takroriy event idempotent; bu “o‘rgandi” degani emas |
| O‘qishdan o‘qishga o‘tish | glossary ochilishi, saqlash, bog‘liq kurs/dars CTA | server tasdiqlagan action/event; access qarori course service’da |
| Owner ishi | draftdan publishgacha vaqt, xato sabab qaytish, moderatsiya navbati | audit/revision timestamp va owner usability walkthrough |
| Ishonchlilik | noma’lum save/publish0, data-loss0, counter drift0 | receipt/CAS, reconciliation va SQLite/PostgreSQL testlari |
| Sifat | §10dagi texnik ssenariylar 100%; native/AT/owner alohida sign-off | avtomat test + sanalgan manual dalil |

KPI maxfiylikni buzmaydi: maqola matni, komment qoralamasi, to‘liq IP yoki
uzoq muddatli raw user-agent analitika eventiga ko‘chirilmaydi.

## 2. Tadqiqot xulosasi va amaldagi kod auditi

Ushbu audit repository kodi, migrationlar, testlar va joriy hujjatlarga
tayandi. Production/AWS qayta kuzatilmadi; real owner, telefon yoki screen
reader sinovi bajarilmadi.

| Mavjud tayanch yoki aniq topilma | Source | Rejadagi javob |
|---|---|---|
| Backendda list/detail, qidiruv, tag, featured, pagination, related va action endpointlar bor. To‘liq reply/like UI V1da; legacyda reply UI yo‘q va clap form raw JSONga tushishi mumkin. | [views](../../blog/views.py), [URLlar](../../blog/urls.py), [testlar](../../blog/tests.py), [I5a testlari](../../frontend/test_public_v1.py) | Capability renderer bo‘yicha alohida testlanadi; mavjud URL/model IDlari saqlanib, UI canonical actionlarga ulanadi. |
| Faqat `draft/published`; future `published_at` amalda schedule, lekin studiya uni oddiy “Nashr” deb ko‘rsatadi. | [model](../../blog/models.py) `BlogPost`, [studiya](../../templates/blog/studio_list.html) | Derived “Rejalangan” holat, review/archive, atomik publication service. |
| Har staff yaratadi/publish qiladi; non-superuser faqat o‘z postini edit qiladi, ammo `?preview=1` bilan har staff istalgan postni ko‘ra oladi. | [views](../../blog/views.py) `BlogStaffRequiredMixin`, `BlogDetailView`, `BlogPostUpdateView` | Django permissionlari va bitta scope policy; preview ham ayni scope’dan o‘tadi. |
| Form/model to‘g‘ridan-to‘g‘ri yozadi; revision, stale/CAS, publish confirmation, reason, audit yoki idempotent operation yo‘q. | [form](../../blog/forms.py), [views](../../blog/views.py) create/update | BLOG1.1 canonical editorial service, immutable revision va publish receipt. |
| Legacy detail `post.body|safe`; V1 render-time Bleach ishlatadi. Sanitizer `iframe`, global `style/id` va har qanday iframe `src`ni qabul qiladi. Bir xil canonical safe snapshot yo‘q. | [legacy detail](../../templates/blog/post_detail.html), [V1 detail](../../templates/frontend_v1/public/blog/post_detail.html), [filter](../../frontend/templatetags/bleach_tags.py) | BLOG1.0 write-time versionlangan sanitizer, allowlisted structured embed va barcha renderer paritysi. |
| View GET bazaga yozadi, bir yillik anonymous cookie, IP hash va raw user-agent saqlaydi; retention/purge contracti yo‘q. | [utils](../../blog/utils.py), [models](../../blog/models.py), `BlogDetailView._register_view` | Data-minimization qarori, retention, purge va cache/analytics contracti. |
| Clap limiti `50`, reading speed `220` kodda qotgan; clap update ikki counterga bo‘lingan va row lock yo‘q. Like toggle ham parallel so‘rovda race qilishi mumkin. | [models](../../blog/models.py) `save`, `add_clap`; [views](../../blog/views.py) reaction views | Semantic invariant va operatsion settingni ajratish; atomic canonical engagement service, PostgreSQL concurrency testi. |
| Barcha izohlar bitta detail so‘roviga olinadi; invalid form matn/xatoni yo‘qotib redirect qiladi; moderatsiya `is_deleted` va raw admin bilan cheklangan. | `BlogDetailView.get_context_data`, `BlogCommentCreateView`, [admin](../../blog/admin.py) | Pagination, PRG draft recovery, rate limit/report/moderation status va audited action. |
| V1 public oilasining barcha javoblari `private, no-store`; published blog uchun canonical/sitemap/JSON-LD/OG image/Twitter contracti topilmadi. | [public adapter](../../frontend/public_v1.py), public base/templates | BLOG1.3 indekslash va cache matrixi; preview/auth doimo private/noindex. |
| Reaction endpointlar JSON-only. V1 tugmalari JavaScript kelguncha disabled; `<noscript>` reaksiyani yopadi. Legacy HTML form JSON sahifaga tushadi. | [public JS](../../static/frontend_v1/js/public.js), public/legacy detail | `Accept` bo‘yicha JSON yoki POST→redirect; no-JS parity, unknown natijada auto-retry yo‘q. |
| `BlogHomeSettings` va barcha blog modellari admin orqali to‘g‘ridan-to‘g‘ri yoziladi; studiya qidiruv, status filter, pagination, revision va moderatsiyasiz. | [admin](../../blog/admin.py), studio views/templates | Canonical writerga ulangan studiya; admin read-only/diagnostic yoki ayni service actioni. |
| `BlogHomeSettings.load()` public GETda singleton yaratishi mumkin; ayrim carousel/copy maydonlari ikki rendererda turlicha yoki ishlatilmaydi. | [model](../../blog/models.py) `SingletonModel.load`, `BlogListView.get_context_data` | GET write-free selector; landing copy audited owner surface va real consumer contracti. |
| Legacy template `reading_time` deb mavjud bo‘lmagan propertyni chaqiradi, card coverni CSS background qiladi va detail coverda `cover_alt_text`ni ishlatmaydi. | [legacy list](../../templates/blog/post_list.html), [legacy detail](../../templates/blog/post_detail.html) | BLOG1.0 parity regression; semantic responsive image va to‘g‘ri derived field. |
| `tag_names` count/length/case-normalization contractisiz; post saqlangach tag yaratish yiqilsa partial write qolishi mumkin. | [form](../../blog/forms.py) `_save_tags` | Atomic service, normalized key/constraint, bounded tag count va field error. |
| Malformed `parent_id` yoki reply-to-reply `ValidationError` 4xx/form xatosiga aylantirilmagan; root soft-delete tirik replyni sanab, lekin ko‘rsatmay qo‘yadi. | `BlogCommentCreateView`, `BlogComment.clean`, detail comment mapping | BLOG1.0 error hotfix; BLOG1.6 tree/moderation invariant. |
| Raw, imzosiz va uzunligi tekshirilmagan visitor cookie DB keyga qo‘shiladi; proxy trust contractisiz `X-Forwarded-For` hash qilinadi. | [utils](../../blog/utils.py), `BlogPostRead` | Bounded signed/rotating identifier yoki trackingni olib tashlash; trusted proxy va retention qarori. |
| Post author, comment user va reply parent `CASCADE`; account yoki parent o‘chishi public kontent/evidence’ni birga yo‘qotishi mumkin. | [models](../../blog/models.py) foreign keylar | SET_NULL/pseudonymize yoki explicit retention policy; destructive action preflight/audit. |
| Vaqtga sezgir/faktual maqola uchun source, verified-on yoki review-due contracti yo‘q; seed bunday da’volarni manbasiz publish qilishni ataylab cheklaydi. | [content seed](../../core/content_seed.py) | Content kindga bog‘liq ordered source/verification checklist va version snapshot. |
| Blogga tegishli global vocabulary/SRS modeli yo‘q. Launch kontent rejasida structured lesson vocabulary kelajak manbasi sifatida yozilgan, runtime contract emas. | repository model/search auditi; [kontent reja](../launch-plan/04-kontent-reja.md) | Faqat postga tegishli author-approved glossary. “Lug‘atim/SRS” alohida admission va canonical domain bo‘lmaguncha va’da qilinmaydi. |
| Existing `Notification`, `NotificationBroadcast`, `create_notification` va `TelegramOutbox` bor. | [notification service](../../users/notification_service.py), [bot outbox](../../bot/outbox.py) | Blog Telegramga bevosita yozmaydi; manual distribution shu canonical zanjirga idempotent adapter bo‘ladi. |
| `frontend_v1_public` default-OFF presentation gate’i bor. | [flag registry](../../core/flags.py), [I5a](I5A-PUBLIC.md) | Shell gate saqlanadi; yangi behavior faqat mustaqil rollback kerak bo‘lgan joyda qo‘shimcha flag oladi. |
| `static/js/blog-runtime.js`dagi bookmark/progress/TOC/chart kodini joriy template yuklamaydi; persistent backend ham yo‘q. | [legacy JS](../../static/js/blog-runtime.js) | Dead code capability hisoblanmaydi; feature canonical contractdan keyin ulanadi yoki olib tashlanadi. |

### Tashqi tadqiqotdan olingan, ko‘chirib olinmaydigan patternlar

- [WCAG 2.2](https://www.w3.org/WAI/WCAG22/Understanding/)dagi
  [Resize Text](https://www.w3.org/WAI/WCAG22/Understanding/resize-text.html),
  [Reflow](https://www.w3.org/WAI/WCAG22/Understanding/reflow.html),
  [Text Spacing](https://www.w3.org/WAI/WCAG22/Understanding/text-spacing.html),
  [Target Size](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html)
  va focus/status mezonlari qabul kontraktiga aylantiriladi. Audio berilsa
  [transcript/media
  alternative](https://www.w3.org/WAI/media/av/planning/) ham shu feature’ning
  bir qismi, keyingi qarz emas.
- [OWASP XSS Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet)
  author HTMLni sanitizatsiya qilish, URLni alohida tekshirish va `iframe src`
  uchun allowlist talab qilishini ko‘rsatadi. Faqat `safe` yoki umumiy
  scheme filtri yetarli contract emas.
- Google’ning [Article/BlogPosting structured data](https://developers.google.com/search/docs/appearance/structured-data/article),
  [canonical URL](https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls)
  va [sitemap](https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap)
  yo‘riqnomasi ko‘rinadigan kontent bilan bir xil JSON-LD, self-canonical va
  faqat indexable absolute URLlarni talab qiladi. Rich result kafolat emas.
- [Core Web Vitals](https://web.dev/articles/vitals) production p75 uchun
  LCP ≤ 2.5s, INP ≤ 200ms, CLS ≤ 0.1 chegaralarini beradi. Lokal Lighthouse
  balli bu production dalilining o‘rnini bosmaydi.
- [Readlang](https://readlang.com/about) va [LingQ](https://www.lingq.com/)
  kontekstdagi so‘z/ibora hamda qayta ko‘rish qulayligini; Duolingo’ning
  [advanced stories](https://blog.duolingo.com/duolingo-advanced-stories/)
  turli real matn formatlari va aniq o‘quv maqsadini ko‘rsatadi. AzureLMS
  bundan faqat pattern oladi: avtomatik tarjima yoki global vocabulary modeli
  bor deb hisoblamaydi.

## 3. Foydalanuvchilar, asosiy yo‘llar va axborot arxitekturasi

### Public va learner yo‘li

| Yuza | Birinchi ko‘rinadigan narsa | Asosiy amal | Bo‘sh/xato holati |
|---|---|---|---|
| **Journal bosh sahifasi** `/blog/` | aniq va’da, tavsiya etilgan maqola, mavzu/daraja, so‘nggi kontent | Qidirish yoki maqolani ochish | filter saqlanadi; zero-resultda tegishli mavzular va “tozalash” |
| **Mavzu/daraja natijasi** shu canonical route querysi | qo‘llangan filter chipi, natija soni, tartib | Filtrni o‘zgartirish | noma’lum tag 404 emas, tushunarli empty; index siyosati aniq |
| **Maqola** `/blog/<slug>/` | learning goal, title, daraja/vaqt, author/date | O‘qish; glossary/TOC; saqlash; keyingi amal | media fallback, closed comments, preview banner |
| **Saqlanganlar** `/blog/saved/` | authenticated user saqlagan maqolalar | Davom ettirish / olib tashlash | login exact-next; bo‘sh holatda mavzu tavsiyasi |
| **Bog‘liq kurs/dars** existing course URL | accessga mos CTA | Kursni ko‘rish yoki ruxsatli darsga o‘tish | blog o‘zi enrollment/access hisoblamaydi |

Detail bitta uzun “hamma narsa” sahifasi bo‘lmaydi. Tartib: sarlavha va
maqsad → article → key phrases/glossary → foydali keyingi qadam → author →
izohlar → related. Sticky TOC faqat yetarli heading bo‘lsa; u mobil
kontentni to‘smasligi va JavaScriptsiz oddiy anchorlar bo‘lib qolishi kerak.

### Muallif/editor/owner yo‘li

| Yuza | Asosiy savol | Asosiy amal |
|---|---|---|
| **Studiya** `/blog/studio/` | Hozir nimani davom ettiraman, nima review/scheduled, qayerda muammo bor? | Draftni davom ettirish / yangi maqola |
| **Muharrir** existing new/edit URL | Mazmun, o‘quv qatlami va nashrga tayyorgarlik qanday? | Saqlash / preview / reviewga yuborish |
| **Preview** permission-scoped route | Publicga aynan nima chiqadi? | Muharrirga ayni revision bilan qaytish |
| **Nashr paneli** muharrir ichida | Qachon, SEO/cover/alt/glossary tayyormi? | Hozir nashr / vaqtga qo‘yish / unpublish |
| **Revisionlar** postga tegishli route | Kim nima o‘zgartirdi va qaysi revision live? | Diff / yangi draft sifatida restore |
| **Moderatsiya** `/blog/studio/comments/` | Qaysi izoh review/report talab qiladi? | Hide/restore/reject, sabab bilan |
| **Tarqatish** published post ichida | Kimga, qaysi kanalga, necha recipient? | Dry-run → confirm → existing notification/outbox |

“Saqlash” qoralamani saqlaydi; “Nashr” tashqi ko‘rinadigan holatni o‘zgartiradi
va alohida confirmation/receipt oladi. Oddiy harf tahririga modal kerak emas.
Muallifga “autosave” ko‘rsatilsa, server revisioni haqiqatan tasdiqlaganidan
keyingina “Saqlandi” deyiladi.

### Rollar

- **Contributor:** o‘z draftini yaratadi/tahrirlaydi, preview qiladi, reviewga
  yuboradi; publish/settings/distribution yo‘q.
- **Editor:** ruxsatli postlarni tahrirlaydi, reviewni qabul/qaytaradi, metadata
  va glossaryni boshqaradi.
- **Publisher/owner:** publish/unpublish/archive, featured/home settings va
  audience distribution. Owner global sozlama va retention qarorini qiladi.
- **Moderator:** komment navbatini boshqaradi; post matnini publish qilish
  huquqi avtomatik berilmaydi.

Django model/custom permissionlari va bitta `blog/policy.py` ishlatiladi.
`is_staff` yakka o‘zi capability emas. Superuser emergency override auditda
ko‘rinadi. Admin va V1 studiya ayni policy/service’dan chetlab o‘tmaydi.

## 4. Canonical arxitektura va ma’lumot shartnomasi

### Yagona yozuv yo‘llari

| Modul | Javobgarlik | Adapterlar |
|---|---|---|
| `blog/policy.py` | actor post/review/publish/moderate/settings scope’i | studio, admin, preview, task |
| `core/rich_content_policy.py` | named `PUBLIC_EDITORIAL_V1` sanitize/link/embed/media/heading engine va policy; safe HTML + plain text + warninglar | Blog/SIT domain wrapperlari |
| `blog/content_policy.py` | Blog adapteri; faqat named shared profilni tanlaydi, global bleach filterini almashtirmaydi | form preview, save service, migration audit, Blog renderer |
| `blog/editorial_service.py` | draft save, review, publish/schedule, unpublish/archive, restore; transaction/CAS/audit | studio POST, ruxsatli admin action, scheduler |
| `blog/selectors.py` | published list/detail, filters, related, studio queue; bounded/prefetched querylar | public web, sitemap/feed, studio |
| `blog/engagement_service.py` | bookmark, clap, comment, like/report; rate limit, idempotency va counter | HTML/JSON endpoints |
| `blog/distribution_service.py` | recipient preview, confirm receipt, existing notification/broadcast/outboxga topshirish | studio action, scheduled task |
| `blog/metrics.py` | minimal event/aggregate, privacy/retention, owner KPI projection | public event endpoint, studio read-only dashboard |

View, model `save()`, signal, admin action yoki Celery task biznes qarorini
o‘zida takrorlamaydi. `transaction.on_commit` tashqi enqueue uchun ishlatiladi;
DB mutation va audit bir transactionda muvaffaqiyatli yoki birga rollback.

### Additive schema yo‘nalishi

Aniq migration nomi implementatsiya paytidagi branch holatidan olinadi;
quyidagi maydon nomlari contract, migration raqami emas.

Termin: **draft revision** — parallel tahrirni aniqlaydigan CAS raqami;
**content version** — preview/publish/rollback uchun immutable snapshot. Bu
ikkisi aralashtirilmaydi: har autosave alohida public version yaratishi shart
emas, lekin publish doimo aniq pinned versionni oladi.

**`BlogPost`ni kengaytirish:**

- `BlogPost` stable identity/slug/ownership va working draftni saqlaydi;
  public kontent mutable draft ustunlaridan to‘g‘ridan-to‘g‘ri o‘qilmaydi.
- `editorial_state`: `draft`, `in_review`, `approved`; `lifecycle_state`:
  `active`, `archived`. Public holat bu ikkisi emas, version pointerlaridan
  derived projection. Shu sabab live post bir vaqtning o‘zida yangi draft yoki
  kelajak update’iga ega bo‘la oladi.
- `edit_revision`, nullable `review_version`, `current_version`,
  `scheduled_version` pointerlari va nullable `scheduled_for`. Schedule
  versiondagi kontent va postdagi mutable control-plane vaqt juftligidir:
  `scheduled_version`/`scheduled_for` ikkalasi birga null yoki birga non-null
  bo‘lishi DB constraint bilan tekshiriladi. Barcha tahrir `expected_revision`
  bilan CAS qiladi; schedule/reschedule/cancel esa post row-lock, expected
  schedule pair va idempotent operation orqali ayni juftlikni atomik almashtiradi.
  Har before/after vaqt audit operationda qoladi. Keyingi draft editi pin qilingan
  rejalangan matnni yashirincha almashtirmaydi. Selector `scheduled_for <= at`
  bo‘lsa `scheduled_version`ni workerga bog‘lanmasdan live deb oladi.
- Working `body` author source bo‘lib qoladi; version ichida `rendered_body`,
  `sanitizer_version` va `content_hash`. Public faqat trusted version snapshotni
  ko‘radi. Stale save 409/forma xatosi va diff; boshqa tabni bosmaydi.
- `first_published_at`, `last_published_at`, `updated_by`. Review qarori
  mutable maydon emas, immutable `BlogReviewDecision` qatori. Published date
  yashirincha har editda yangilanmaydi; modified date alohida.
- learning metadata: `content_language` (`tr`, `uz`, `mixed`), optional
  `learning_goal`, `content_kind`, nullable `related_course` va `related_lesson`.
  `cefr_level` faqat courses/library o‘rtasidagi mavjud coarse/exact enum
  farqi shared taxonomy qarori bilan yopilgach qo‘shiladi; blog uchinchi CEFR
  ro‘yxatini yaratmaydi. Related lesson coursega mosligi service’da tekshiriladi.
- mavjud slug published bo‘lgach default immutable. Keyinchalik owner slugni
  o‘zgartirsa eski URL uchun `BlogSlugRedirect`; redirect loop/duplicate yo‘q.

**Yangi modellar:**

- `BlogPostVersion`: post+number unique; source/sanitized body, metadata,
  cover asset reference+alt, actor label, reason, content hash va snapshot
  timestampi. Schedule vaqti immutable kontent versioniga kirmaydi.
  Append-only; restore eski qatorni o‘zgartirmaydi, yangi version va draft
  revision yaratadi. `current_version`/`scheduled_version` faqat shu jadvalga
  ishora qiladi.
- `BlogReviewDecision`: pinned version, `approved` yoki `changes_requested`,
  editor, note va time. Approved versiondan keyin draft o‘zgarsa approval
  bekor bo‘ladi; publish yangi matnni eski approval bilan chiqarmaydi.
- `BlogEditorialOperation`: unique UUID, action, actor, post, requested/base va
  resulting revision, canonical request fingerprint va terminal result;
  publication promotionida original `effective_at` va real `promoted_at` ham.
  Unique `(actor, operation_id)`: same key+same fingerprint original receiptni
  qaytaradi; same key+different payload `409`; validation/no-op terminal
  natijasi ham xavfsiz replay qilinadi. Pattern:
  [design service](../../core/design_service.py).
- `BlogContentRepair`: version, target sanitizer policy, bounded enum
  `reason_code`, alohida diagnostic detail, status va audit timestamps.
  `(version, target_policy, reason_code)` unique; faqat save/backfill yoki
  periodic reconciliation yozadi. Public request bu jadvalga yozmaydi.
- Working draft uchun `BlogGlossaryItem` va `BlogPostSource`; publish paytida
  `BlogVersionTag`, `BlogVersionGlossaryItem` va `BlogVersionSource` immutable
  child qatorlariga snapshot. Public version current mutable M2M/child rowni
  o‘qimaydi. Glossary: Turkish term/phrase, Uzbek explanation, optional
  example/notes va order; author-approved, post-scoped, global SRS emas.
- Source snapshotda tartibli URL/title/publisher/checked-on. Faqat policy
  talab qilgan content kindda majburiy; public source link xavfsiz URL contracti
  bilan. `review_due_at` vaqtga sezgir maqolani queuega qaytarishi mumkin,
  avtomatik unpublish faqat owner aniq siyosat qilsa.
- `BlogTopic`: bitta primary editorial category uchun human name, stable slug,
  description/order/active va normalized uniqueness; `BlogTopicAlias` merge/
  eski filter URLni canonical topicga olib boradi. Working draft topic tanlaydi,
  version child topic ID+name+slug snapshot qiladi. Erkin taglar topic o‘rnini
  bosmaydi.
- `BlogBookmark`: user+post unique, created/updated. Saqlash course progress,
  XP yoki streakni o‘zgartirmaydi.
- `BlogCommentReport` va kommentga moderation state/reason/reviewer/time.
  Original matn audit/evidence uchun saqlanadi; public projection hide qiladi.
- `BlogDistributionIntent`: post version, explicit audience specification,
  schedule, operation, state va sent/failed counts. Notificationning o‘zi
  `users` domenida; intent delivery transportini takrorlamaydi.
- Privacy qaroridan keyin `BlogEngagementEvent`: unique event UUID, kind,
  post version, nullable user yoki rotated viewer hash, source va timestamp;
  raw IP/UA/body/query yo‘q. Bounded raw retentiondan so‘ng `BlogDailyMetric`
  aggregate qolishi mumkin. Ungacha dashboard faqat server action/canonical
  row aggregatlaridan foydalanadi.

Author/commenter account lifecycle’i ham migration preflightiga kiradi.
Published post yoki moderation evidence user row o‘chishi bilan `CASCADE`
bo‘lmaydi. BLOG-01 defaulti: author/comment user `SET_NULL`, versionda immutable
display label; publicda “O‘chirilgan foydalanuvchi”. Parent hard-delete
`PROTECT`; moderatsiya status/placeholder orqali. Boshqa privacy/legal policy
kerak bo‘lsa schema oldidan owner yozma qarori bu defaultni almashtiradi.

Version cover/inline media reference’i bor ekan fayl cleanup qilinmaydi.
Replace/clear yangi draft reference yaratadi; DB rollbackdan oldin eski fayl
o‘chirilmaydi va orphan cleanup faqat commitdan keyin reference count bilan.
Rollback testi eski version media baytlari/hashini aynan saqlaganini tekshiradi.

**Ownership va public read contracti:**

| Qatlam | Nima yashaydi | Kim o‘qiydi/yozadi |
|---|---|---|
| `BlogPost` stable | ID, slug, creator/author relation, lifecycle, version pointerlar, `scheduled_for`, aggregate counters | service row-lock bilan; router/engagement identity sifatida |
| `BlogPost` working draft | title/body/cover, SEO, learning metadata, related course/lesson, working tags/glossary/sources, `edit_revision` | ruxsatli studio; public hech qachon emas |
| `BlogPostVersion` | immutable scalar snapshot, sanitized HTML, media ref, dates, sanitizer/hash | editorial service yaratadi; public effective versionni o‘qiydi |
| Version child rows | `BlogVersionTag`, `BlogVersionGlossaryItem`, `BlogVersionSource`, `BlogVersionLearningLink` | publish/review snapshotda clone; public faqat shularni o‘qiydi |
| Post-level community | comments, reactions, bookmark va bounded metrics | engagement services; published version eligibility fresh tekshiriladi |

`BlogPostVersion(post, number)` unique; number allocation `BlogPost` row lock
ostida. `BlogPostVersion.post`, postning version pointerlari va version-child
relationlari destructive delete’dan `PROTECT`; model/admin/service guard bilan
append-only: persisted versionni model `save()` bilan update va custom queryset
`update/delete` qilish taqiqlanadi; admin read-only, faqat migration/backfill
aniq bypass kontekstida yaratadi. Har pointer ayni post
versioniga ishora qilishi service/model validation va system check bilan
tekshiriladi; cross-post pointer regression testi majburiy. Legacy hamda V1
rendererlar flag holatidan qat’i nazar faqat `effective_version(post, at)`
projectionini o‘qiydi — flag OFF working draft leak qilmaydi.

**Publication/review state machine:**

| Command | Old shart | Atomik natija |
|---|---|---|
| save draft | expected edit revision | working draft+revision; in-review/approved bo‘lsa approval tozalanib draftga qaytadi |
| submit review | valid draft | immutable review version pin; `in_review` |
| approve/request changes | editor permission + exact review version | immutable decision; `approved` yoki `draft`; note saqlanadi |
| publish now | exact approved version; owner override sabab+audit bilan | row lock; due schedule avval promote; target `current_version`, `scheduled_version`+`scheduled_for` clear |
| schedule/replace | exact approved version + future time + expected current/schedule pair | current live saqlanadi; `scheduled_version`+`scheduled_for` atomik almashtiriladi; first publishda current null |
| cancel schedule | expected schedule pair, hali future | `scheduled_version`+`scheduled_for` clear; current live bo‘lsa davom etadi |
| unpublish | expected live/schedule pair + reason/confirm | current va ikkala schedule field clear; immutable versions qoladi |
| archive | expected pointers/time + reason/confirm | lifecycle archived, schedule pair clear; public selector none, history qoladi |
| rollback publication | publisher, target old version, expected live, operation/reason/confirm | target new rollback version sifatida current; schedule pair default clear |

`effective_version(at)`: archived yoki current/schedule pair yo‘q bo‘lsa none;
`scheduled_for <= at` bo‘lgan scheduled version currentdan ustun; aks holda
current. Har publication
mutationi `promote_due_locked()`ni avval bajaradi, shuning uchun exact boundary,
reschedule/cancel/unpublish va parallel commandlardan row-lock winner o‘tadi,
stale ikkinchisi `409` oladi. GET esa hech qachon pointer promote qilib yozmaydi.
`effective_publication_dates(post, at)` due pair hali promote qilinmagan bo‘lsa
ham `scheduled_for`ni effective sana sifatida qaytaradi. `promote_due_locked()`
aynan shu eski vaqtni system `BlogEditorialOperation.effective_at` receiptiga va
`last_published_at`ga (first publishda `first_published_at`ga ham) ko‘chiradi,
so‘ng current pointerga o‘tib schedule pairni clear qiladi; real execution vaqti
`promoted_at` sifatida alohida turadi. Worker va keyingi manual mutation bir xil
service/idempotency contractidan foydalanadi, shu bois kech worker visible/
JSON-LD sanasini surmaydi.
Due version uchun cache invalidation time-aware TTL/tag bilan; worker faqat
housekeeping/distribution, visibility correctness uchun shart emas.

**Yangi modelni hozir qo‘shmaslik:** pixel scroll state, avtomatik tarjima,
universal vocabulary progress, article quiz score, XP va AI-generated body
canonical state BLOG-01ning asosiy migrationiga kirmaydi.

### Sanitizer va media contracti

1. Author source hech qachon `|safe` bilan publicga chiqmaydi.
2. Save service allowlist policy versiyasi bilan `rendered_body` yaratadi.
   Render payti qayta sanitizatsiya defense-in-depth bo‘lishi mumkin, lekin
   ikki rendererning turli natijasi canonical haqiqat bo‘lmaydi.
   Selector minimum-safe sanitizer versionni biladi: unknown/outdated snapshot
   response vaqtida current policy bilan qayta sanitize qilinadi; bu DBga
   yozmaydi. Sanitizatsiya ishonchli tugamasa request faqat deterministik
   plain-text safe fallback beradi. Deduplicated `BlogContentRepair` rowi
   `(version, target_policy, reason_code)` unique contracti bilan save/backfill yoki
   periodik reconciliationda yaratiladi; public GET hech qachon enqueue yoki
   boshqa DB write qilmaydi. Policy upgrade yangi audited version yaratadi;
   eski immutable qatorni joyida tahrirlamaydi.
3. Inline `style`, arbitrary `id`, event handler, executable/data URL va
   protocol-relative/untrusted embed olib tashlanadi. Link `rel` va target
   server policy bilan normallashtiriladi.
4. Raw iframe author HTMLida ruxsat etilmaydi. Kerakli video/embed alohida
   structured blok, host allowlist, privacy-conscious URL, title va sandbox
   bilan render qilinadi. Prerecorded video captions, kerak bo‘lsa transcript/
   audio description va keyboard-accessible player/provider gate’isiz ship
   qilinmaydi. Owner providerlarni alohida tasdiqlaydi.
5. Cover/inline image magic-byte, size/dimension va public media policy’dan
   o‘tadi. Mazmunli coverda alt majburiy; dekorativ rasm aniq decorative.
   Responsive width/height/srcset layout shiftni kamaytiradi.
6. Audio keyingi capability bo‘lsa transcript va “maqolaning audio varianti”
   labeli bilan birga ship qilinadi; transcriptsiz audio rollout yo‘q.

Backfill ikki qadamli: **dry-run report** (changed/unsafe/embed/media) → owner
review → batch write. Unsafe published post jimgina qayta yozilmaydi. Jiddiy
payload topilsa public renderer deterministik safe/plain fallback beradi,
lekin queuega yozmaydi; backfill/save/reconciliation unique repair rowini
oldindan yoki keyingi sweepda yaratadi. Avtomatik unpublish yo‘q. Unpublish
faqat ownerning sabab+tasdiq+auditli amali. Original source/version tiklash
uchun saqlanadi; count/hash/reversibility dalili olinadi.

### Cache, preview va indekslash matrixi

| Holat | Cache | Robots/SEO | Yon ta’sir |
|---|---|---|---|
| anonymous published list/detail | faqat personalized cookie/CSRF ajratilgach bounded public cache | canonical/index; detail sitemap+BlogPosting | GET write-free bo‘lishi shart |
| authenticated published page | private; `Vary` contract testli | canonical public URL | bookmark/reaction alohida POST |
| staff preview/draft/revision | `private, no-store` | `noindex,nofollow`; sitemap/feedda yo‘q | view/reaction/comment/analytics yo‘q |
| search query | bounded private yoki short cache | default noindex; canonical policy listga | raw query analytics minimallashtiriladi |
| tag/level landing | safe query kombinatsiyasi bo‘lsa cacheable | curated page index; self-canonical | filter GET-only |

Hozir detail GET `BlogPostRead` yozadi va cookie beradi. Shuning uchun public
cache shunchaki header almashtirib yoqilmaydi. BLOG1.0/1.3da GET write-free,
engaged-read event esa alohida idempotent endpoint yoki aggregate pipelinega
ko‘chmasdan cache rollout qilinmaydi.

## 5. Roadmap — aniq bosqich, fayl, test va tugash mezoni

Har bosqich kichik review qilinadigan PRlarga bo‘linadi. Keyingi bosqich
oldingi canonical contractni ishlatadi; bir PRda model+butun redesign+AI
qo‘shilmaydi.

### BLOG1.0 — xavfsizlik, baseline va mavjud haqiqatni birlashtirish

**BLOG1.0a1 — owner Blog implementatsiyasini boshlasa birinchi kesim:**
`core/rich_content_policy.py`dagi named `PUBLIC_EDITORIAL_V1` profil,
`blog/content_policy.py` wrapper va malicious fixture corpus (script/event/style URL,
iframe, SVG/data URL, malformed HTML, duplicate ID, target/rel). Legacy va V1
`|safe`/render-time farqini bitta safe projectionga ulash. Model maydoni hali
bo‘lmasa selector property compatibility bridge; keyingi migrationda version
snapshot canonical. Amaldagi CSP inline contentga keng ruxsat bergani sanitizer
o‘rnini bosmaydi; CSP report-only inventory alohida, fixni kechiktirmaydi.

**BLOG1.0a2 — preview scope va side-effect:** `policy.can_preview` defaulti:
contributor faqat o‘z posti; editor review huquqidagi barcha post; publisher
global; superuser override auditlanadi. Preview private/no-store/noindex,
view/reaction/comment/metrics0. Slugni bilish capability bermaydi.

**BLOG1.0a3 — malformed input va identity hardening:** invalid/uzun visitor
cookie, non-integer/cross-post/deep `parent_id` va sanitizer errori 4xx/form
error yoki safe fallback; hech biri 500/partial write bermaydi. Cookie/trusted
proxy privacy qarorigacha bounded compatibility yo‘lida.
*2026-10-17 eslatma:* visitor cookie/identity qismi PUB1.0g’da bajarildi —
`blog/utils.py` anonim cookie’ni umuman o‘qimaydi va o‘chiradi, o‘qish/olqish
faqat kirgan foydalanuvchi kaliti (`reader_key`) bilan. BLOG1.0a3 shu
implementatsiyani reuse qiladi va faqat `parent_id`/sanitizer qismini qoldiradi.

**BLOG1.0b — o‘lchash va data qarori.**

- Synthetic fixture: 0/1/100/1000 post, 0/1000 comment, uzun Turkish/Uzbek
  text, cover/no-cover, future publish, unsafe legacy body.
- Bugungi editor publish click/page count, list/detail query count va response
  size, 320/768/1440 render, no-JS flow baseline. Sonlar sanali dalilga yoziladi.
- `BlogPostRead` cookie/IP/UA uchun owner privacy qarori: purpose, retention,
  purge, authenticated/anonymous semantics va trusted-proxy source. Qarorsiz
  yangi tracking ship yo‘q; existing cookie avval length/format bilan bounded.
- Security fix eski post ko‘rinishini o‘zgartirsa affected postlar ro‘yxati va
  owner review. Production write/deploy alohida gate.
- Existing clap/like/comment/view counter invariantini nomlash va reconciliation
  command dry-run. Broken count report; `--apply` explicit, auditli va backupdan
  keyin. Allaqachon CASCADE bilan yo‘qolgan row backup/audit bo‘lmasa tiklanmaydi;
  yangi schema faqat kelajakdagi yo‘qotishni to‘xtatadi.

**Tegiladigan joylar:** `core/rich_content_policy.py`, `blog/content_policy.py`,
`blog/policy.py`, models/views, ikkala detail template, migration/backfill
command, blog va frontend testlari. Global
`frontend.templatetags.bleach_tags.sanitize` va uning constantlari o‘zgarmaydi;
uning course/exam/pricing/legal/help consumerlari bu slice qamroviga kirmaydi.

**Tugashi:** bir xil post legacy/V1da bir xil safe semantic HTML beradi;
malicious corpus executable node/URL/embed chiqarmaydi; unauthorized preview
404/403 va side-effect0; barcha counters dry-run izohlanadi; baseline artifact
bor. Rollback eski rendererga qaytsa ham raw source `safe`ga chiqmaydi.

### BLOG1.1 — canonical editorial lifecycle, revision va ruxsat

**BLOG1.1a — faqat expand schema:** additive version/operation/review/child
jadvallari, nullable pointerlar, custom permissionlar va index/constraints.
Mavjud read/write yo‘li o‘zgarmaydi; data backfill `RunPython` ichida katta
transaction qilib bajarilmaydi. `makemigrations --check` va empty/legacy DB
migration testlari.

Custom permissionlar: `review_blogpost`, `publish_blogpost`,
`moderate_blogcomment`, `manage_blogsettings`, `distribute_blogpost`.
Superuserdan tashqari `is_staff` fallback taqiqlanadi. Preflight existing
staff/authorlarni chiqaradi; default migration mavjud authorsni contributor
(own draft) qiladi, editor/publisher/moderator/distributorni owner explicit
assign qiladi. Mapping tugamasdan writer switch ON qilinmaydi.

**BLOG1.1b — lifecycle service va dual contract:** `editorial_service.py`,
selectors, policy, state table, row lock, expected revision/pointer,
idempotency fingerprint va audit. Contractlar: `save_draft`, `submit_review`,
`decide_review`, `publish_now`, `schedule`, `cancel_schedule`, `unpublish`,
`archive`, `restore_as_new_draft`, `rollback_publication`. Publish fresh
permission, approved version, sanitizer, required metadata va schedule time’ni
transaction ichida qayta tekshiradi. Audit write yiqilsa mutation rollback.
Legacy/new adapter hali bir xil service’ga dual-write/read qiladi.

**BLOG1.1c — resumable backfill va verify:** schema migrationdan alohida
checkpointli management command: `--dry-run`, bounded `--batch-size`, resume
cursor va idempotent rerun. Expected mapping:

- mavjud draft → `draft`;
- published future → version 1 + `scheduled_version` va
  `scheduled_for=legacy published_at`, current pointer yo‘q, derived
  `scheduled`;
- published past/current → version 1 + `current_version`, `published`;
- current sanitized snapshot version 1 sifatida; unsafe flag reportda;
- `first_published_at` dalil yetarli bo‘lmasa joriy `published_at`, “taxminiy
  backfill” deb migration note’da yoziladi.

Migration preflight case-insensitive duplicate/oversize taglar, null/future
publication, counter drift, invalid/deep comment parent, deleted user va orphan
media’ni sanaydi. Tag merge M2Mni idempotent ko‘chiradi; canonical slug/alias
saqlanadi. Interrupted/resume, duplicate-run, version/media hash va row count
tekshiriladi. Unsafe anomaly quarantine/report; pointer faqat verified rowga.

`current_version` live snapshotni, `scheduled_version` pinned kelajak
snapshotini, `scheduled_for` esa mutable due vaqtini ko‘rsatadi. Selector due
versionni shu pairdan workerga qaramay tanlaydi; background task faqat pointer
housekeeping/tarqatish bilan shug‘ullanadi. Reschedule immutable versionni
mutatsiya qilmaydi; schedule pair va audit operation yaratadi.

**BLOG1.1d — finalize va barcha writerlar:** studio create/update, Django admin, seed/demo
yo‘li, management command va kelajak tasklar xaritasi. Admin operational
modelni inline raw edit qilmaydi: read-only diagnostic yoki canonical form/
action. Seeder explicit test/dev adapter bo‘lib, production postni title/slug
bo‘yicha egallamaydi.

Legacy form ham server bergan `expected_revision` va operation UUIDni yuboradi;
missing/stale token raw save emas, bound error/409. `frontend_v1_public` ON/OFF
ikkalasi `effective_version`ni o‘qiydi. Shadow parity/count/hash 0 mismatchdan
keyin final constraint/pointer switch; eski content columns kamida bitta
release+backup window qoladi. Ularni drop qilish alohida owner-approved contract
migration, ushbu kesim emas.

`BlogHomeSettings` GETda yaratilmaydi; migration/default row yoki write-time
owner service orqali mavjud bo‘ladi. Tag yaratish post save bilan bir atomic
operation; max count/length va normalized uniqueness xatosi ayni fieldga qaytadi.

**Tugashi:** ikki tab stale save bir-birini bosmaydi; repeated publish bitta
revision/audit/effect; scheduled post ayni vaqtdan oldin yo‘q, keyin workerga
qaramasdan bor; live update schedule/reschedule/cancel exact; parallel publish/
unpublish/rollbackda bitta row-lock winner, stale `409`; contributor publish
qila olmaydi; owner public rollback expected-live guard bilan ishlaydi. SQLite
va PostgreSQL transaction testlari yashil.

### BLOG1.2 — ultra qulay studiya va muharrir

**BLOG1.2a — Studiya:** qidiruv, `Mening/Review/Rejalangan/Nashr/Arxiv`,
topic/author filter, bounded pagination; CEFR filter faqat shared taxonomy
admitted bo‘lsa. Kartada derived status, jumladan **Live + rejalangan update**,
updated actor/time, validation muammosi va primary next action. Vanity total
views markaz emas; review va davom ettiriladigan ish oldin.

Owner-only **Journal sozlamalari** shu studiyada: hero/copy preview, primary
topic/category va tag taxonomy. Human label+stable slug; create/rename/alias/
merge/deactivate. Ishlatilayotgan topic/tag hard-delete qilinmaydi — merge yoki
deactivate. `BlogHomeSettings` va taxonomy save reason/audit/CAS bilan; Django
admin ichidagi yashirin parallel writer yo‘q.

**BLOG1.2b — Muharrir:** uch progressiv bo‘lim:

1. **Maqola:** title, excerpt, body, cover/alt, tags.
2. **O‘quvchi uchun:** til, decision-gated daraja, learning goal, glossary,
   related course/dars.
3. **Nashr:** preview, SEO/social snippet, comments, featured, now/schedule.

Toolbar oddiy vazifa nomlari bilan; heading hierarchy, link, image, quote,
table va structured embed. Media upload progress/error/cancel; keep/replace/
clear. So‘z/reading-time, missing alt va SEO preview maslahat, bloklovchi xato
alohida. Tag yaratish case-insensitive canonical normalizationdan o‘tadi;
input/chip har doim human-readable label, URL esa stable encoded slug/ID.

Form contracti: error summary fokuslanadi va ayni fieldga link beradi;
fieldda `aria-invalid` hamda help/error `aria-describedby`; autosave/reaction
`role=status` live region; rich-editor toolbar keyboard name/role/value bilan;
glossary/media reorder drag-only emas (yuqori/past tugma). Minimum target
WCAG AA 24×24 CSS px, asosiy action maqsadi 44×44; contrast AA.

**BLOG1.2c — draft/recovery:** server tasdiqli autosave faqat BLOG1.1 CAS
ustida. “Saqlanmoqda / Saqlandi / Saqlanmadi / boshqa tab yangiroq” holatlari.
Bounded local recovery faqat source draft; maxfiy answer yo‘q, boshqa userga
ko‘rinmaydi, serverdan newer bo‘lsa avtomatik overwrite qilmaydi. File input
reload’dan keyin tiklandi deb ko‘rsatilmaydi.

Preview ayni revisionni ko‘radi. Publish checklist: safe body, title/excerpt,
learning goal (content_kind talab qilsa), cover alt, canonical/SEO, schedule,
broken internal link va content-kind talab qilgan source/checked-on. Warningni
owner sabab bilan qabul qilishi mumkin;
security/access xatosi bypass qilinmaydi.

**Tugashi:** create → invalid → recovery → preview → review → publish/schedule
yo‘li texnik HTMLsiz; 320px va 200%da barcha field/action; keyboard order va
visible focus; stale/offline/413/invalid media qoralamani yo‘qotmaydi. Owner
5 ta fixture taskning 5/5ini HTML, Django admin yoki agent yordamisiz tugatadi;
critical error/data-loss0, publish va rollback natijasi to‘g‘ri. Median amal
soni va vaqt bir xil fixture/muhitdagi baseline’dan yomon emas; aks holda
“ultra qulay” qabul qilinmaydi va topilgan friction keyingi kesimga yoziladi.

### BLOG1.3 — topish, SEO va public Journal bosh sahifasi

- Bitta server-side qidiruv/filter contracti: `q`, topic/tag, language,
  content kind, decision-gated shared CEFR va stable sort. Filter
  pagination/copy URLda saqlanadi; unknown
  qiymat data leak/500 bermaydi. Hozirgi `icontains body + distinct` kichik
  data fallback; PostgreSQL FTS faqat explain/query baseline zarurligini
  ko‘rsatsa, portable selector ortiga qo‘shiladi. Elasticsearch qo‘shilmaydi.
- Featured va “yangi” bir postni ikki marta ko‘rsatmaydi. Mavzular editorial
  curated; tag spam/filter explosion indekslanmaydi. Search suggestion raw
  user querylardan avtomatik public taxonomy yasamaydi.
- Stable semantic cards: title, purpose/excerpt, level/topic, date/reading
  time, meaningful cover. Cover derivatives width/height/srcset/lazy loading;
  hero LCP image eager/high-priority va bounded. Legacy `reading_time` typo,
  CSS-background cover va title-as-alt regression test bilan yopiladi.
- `<title>`, description, self-canonical, OpenGraph/Twitter, absolute image,
  `BlogPosting` JSON-LD visible content bilan bir xil. Preview/search noindex;
  published detail va curated landings sitemapda, `lastmod` published revision
  bilan. RSS/Atom faqat published selectorni ishlatadi.
- Pagination oddiy crawlable `<a href>`; har page self-canonical (page 2 ni
  page 1ga canonical qilmaydi). Raw search noindex; faqat curated topic/filter
  landing self-canonical/index. Draft, not-due, unpublished va archived URL
  default 404; old public slug faqat verified `BlogSlugRedirect` bilan 301.
  JSON-LD author name va mavjud bo‘lsa canonical profile URL ishlatadi.
- `seo_title` haqiqiy document titlega ulanadi. Visible published/modified
  dates JSON-LD bilan bir xil; future vaqt “published” sana sifatida chiqmaydi.
- Cache matrix §4 bo‘yicha. Personalized form/token/event ajratilmaguncha
  private/no-store xavfsiz fallback qoladi.
- Ulanmagan `static/js/blog-runtime.js` inventar qilinadi: canonical featurega
  ko‘chirilmagan fake bookmark/progress/chart dead code sifatida olib tashlanadi.

**Tugashi:** qidiruv/filter/pagination deep-link va back ishlaydi; 0/1/1000
post query budget; schema validator critical xato0; sitemapda draft/future/
archive/preview yo‘q; canonical va internal links bir URLga; 320px overflow0,
cover sabab CLS regressiyasi yo‘q. Search ranking va rich result tashqi
provider natijasi bo‘lgani uchun “kafolatlandi” deyilmaydi.

### BLOG1.4 — chalg‘itmaydigan maqola o‘qish tajribasi

- 60–75ch o‘qish eni, fluid type/line-height, aniq h1→h2→h3, Turkish segment
  uchun kerak bo‘lsa `lang="tr"`. Resize Text 200%; Reflow 320 CSS px/400%;
  Text Spacing alohida: line-height 1.5, paragraph 2×, letter .12em, word
  .16em override’da content/action yo‘qolmaydi. Light/dark tokenlar existing
  design systemdan; article author style global theme’ni buzmaydi.
- TOC server-generated anchorlar; sticky/progress/focus mode enhancement.
  Reduced motion; scroll progress accessible name bilan, o‘qishni tugatdi deb
  canonical progress yozmaydi.
- Copy-link native/fallback, Web Share optional; URLda tracking secret yo‘q.
  Bookmark authenticated canonical POST, guest exact-next. Share count yoki
  soxta “hozir N kishi o‘qiyapti” yo‘q.
- Related content tag count bilan emas, deterministic priority: explicit
  related → same learning goal/level/topic → recent; current post excluded,
  unpublished leak yo‘q. Related course/dars CTA canonical access policyga
  delegation qiladi.
- No-JS: article/TOC/search/bookmark login handoff/comment/clap/like HTML PRG.
  JSON client server ACKdan keyin yangilaydi; timeoutda unknown va explicit
  reload, automatic duplicate yo‘q.

**Tugashi:** keyboard-only va JS-off primary journey; focus hech qachon sticky
header ostida qolmaydi; 320 CSS px/400% reflow, 200% resize va yuqoridagi text
spacing override alohida PASS; meaningful image alt, table caption/header,
link purpose; long code/table controlled scroll. Native screen reader va
device qabuli BLOG1.8da alohida.

### BLOG1.5 — o‘quv qiymati: maqsad, glossary va keyingi qadam

- Avval taxonomy qarori: courses’dagi coarse level va library’dagi exact A1–C2
  ro‘yxati yagona shared enumga kelmasa, Blog faqat Course/Lesson link va
  learning goal ishlatadi; uchinchi CEFR ro‘yxati yoki erkin claim yo‘q.
- Editor-approved `learning_goal`, admitted shared CEFR/content kind va 3–12
  asosiy ibora.
  Glossary maqola yonida/inline anchor bilan Turkish term, Uzbek izoh va
  kontekstdagi misol ko‘rsatadi. Tushuntirish hidden title/hover-only emas;
  keyboard/touch va no-JS paneli bor.
- Blog bodydagi har so‘zni avtomatik o‘rash yoki uchinchi tomon tarjima API
  chaqirish yo‘q. Glossary term collision, Turkish casing va phrase boundary
  fixture bilan tekshiriladi; article text sanitizer’dan keyin buzilmaydi.
- Bog‘liq course/lesson author tanlaydi; server same-course constraint va
  ruxsatni tekshiradi. Mehmon course detailga, active learner ochiq darsga,
  yopiq dars esa aniq access izohiga boradi. Blog access ochmaydi.
- “Saqlangan maqolalar” bookmarkdan. Optional coarse `last_read_at` faqat
  owner admission/private retention bilan; course completion/XP/streak emas.

**Tugashi:** author glossary create/reorder/error/reopen, public keyboard/
touch/no-JS ko‘rinishi; wrong-course lessonni save rad etadi; access revoke
CTA bilan chetlab o‘tilmaydi; bookmark duplicate0. Glossary yo‘q post oddiy
maqola sifatida to‘liq ishlaydi.

**Keyingi alohida gate:** “So‘zni Lug‘atimga qo‘shish”, spaced repetition,
global vocabulary progress yoki AI translation uchun canonical vocabulary
domain, source/provenance, duplicate/normalization, delete/export/privacy,
course integration va measurable learning outcome alohida owner admission
oladi. Hozir mavjud bo‘lmagan model nomi rejada bor deb ko‘rsatilmaydi.

### BLOG1.6 — sog‘lom community va ownerga yengil moderatsiya

- Commentlar bounded root pagination + bir darajali reply. Sort aniq;
  deleted/hidden parent javob kontekstini xavfsiz placeholder bilan saqlaydi.
- Invalid POST matn va ayni parentni qaytaradi. CSRF, login exact-next,
  duplicate submit operation key, per-user/IP bounded rate limit. HTML/JSON
  bir engagement service’ga boradi.
- Edit/delete policy: muallif uchun qisqa edit window yoki owner qarori;
  hard delete emas, visible “tahrirlangan/o‘chirilgan”. Moderator hide/restore/
  reject va reason; report unique user/comment va abuse limit.
- Moderatsiya queue: reported/pending/hidden filter, post/user context, safe
  text, bulk external effect yo‘q. Har action audit; moderator original HTML
  executable ko‘rmaydi.
- Clap/like row-lock/constraint/F-expression contracti. Counter canonical
  detail rowlardan reconcile qilinadi; negative/limit-over drift mumkin emas.

**Tugashi:** invalid form recovery, double-click/replay, 20 parallel clap va
like, concurrent delete/report, closed comments, banned/permission revoked,
1000 comment pagination. PostgreSQL TransactionTestCase va integration CI;
SQLite behavior ham yashil. Spam detection “AI moderation”ga bog‘liq emas.

### BLOG1.7 — tarqatish, kuzatuv va owner dashboardi

- Published postdan distribution tayyorlash: explicit users yoki ruxsatli
  cohorts; `all active` faqat owner tanlagan alohida high-impact option.
  Title/message/url, fresh recipient count va channel preview; “Yuborish”dan
  oldin confirmation, reason va operation UUID. Auto-follow/subscription
  BLOG-01 scope emas.
- Existing `NotificationBroadcast`/`create_notification` canonical yo‘li va
  Telegram outbox/retry/dead-letter ishlatiladi. Blog raw Bot API, yangi bot
  worker yoki “yetkazildi” degan taxmin yaratmaydi. Yangi
  `Notification.CATEGORY_CONTENT`; quiet-hours va global send kill switch
  existing notification/outbox policy’da.
- Muhim existing trap: `send_broadcast()` `bulk_create` qiladi, Django
  `post_save` signalini chaqirmaydi va shu sabab Telegram outbox avtomatik
  yaratilmaydi. BLOG1.7da `users.notification_service` ichida canonical
  `create_notification_batch(commands)` quriladi: Notification external-key
  dedupe va mos TelegramOutbox qatorlarini bitta transactionda yaratadi;
  single-create signal ham shu outbox builderdan foydalanadi. Blog hech qachon
  outboxga direct yozmaydi. `(recipient, post, version)` external key aynan
  bitta Notification va ko‘pi bilan bitta Outbox beradi.
- Default audience **bo‘sh**; yangi maqola barcha userga avtomatik blast
  qilinmaydi. Oddiy edit/rollback/republish ham default fanout bermaydi.
- Schedule article visibility workerga qaramaydi; scheduled distribution esa
  due task tomonidan row-lock/claim va idempotent receipt bilan bir marta
  enqueue qilinadi. Worker down bo‘lsa article live, distribution “Kutilmoqda/
  Xato” bo‘lib ko‘rinadi; yashirin duplicate yo‘q.
- Owner dashboard: published/draft/review queue, engaged reads trend,
  zero-result, article→course CTA, comment moderation, distribution state.
  View/clap faqat context; “vanity” raqamni learning outcome deb atamaydi.
- Metrics cardinality/retention bounds, bots/preview exclusion, purge command,
  Control Center probe faqat actionable holat uchun. Raw qidiruv va UA dump
  dashboardga chiqmaydi. Engaged-read timer faqat visible/foreground active
  va 50% article intersectionda yuradi; no-JS yoki telemetrysiz o‘quvchi
  “o‘qimadi” emas, **unknown**. Bu metric learning evidence emas.

**Tugashi:** dry-run recipient soni va send transactionidagi fresh scope;
double submit/worker retry duplicate notification0; unauthorized cohort0;
Telegram permanent/transient xato existing dead-letterda; dashboard empty/
large data, bounded query va timezone boundary. Provider/live send alohida
owner-approved test account bilan.

### BLOG1.8 — performance, accessibility, migration va rollout qabuli

- Full safe backfill dry-run → backup → sampled diff → batch apply → count/hash
  reconciliation. Old/new post, revision, tag, comment, bookmark va media
  counts; rollback rehearsal nusxada.
- Query budgets, cover derivative generation, cache hit/miss/Vary, sitemap/feed,
  purge/rebuild/reconcile commandlar. Production-like PostgreSQL+Valkey/Daphne
  profilida cold/warm o‘lchov.
- WCAG matrix: keyboard, focus, landmarks/headings, name/role/value, errors/
  status, contrast, reflow, text spacing, target, reduced motion, language,
  image/table/embed/audio alternatives. Automated axe yordamchi; native NVDA/
  VoiceOver/TalkBackni almashtirmaydi.
- Core Web Vitals synthetic budget va production RUM p75 alohida. CI’da
  deterministic asset/query/size budget; network natijasi sanali release
  evidence’da.
- Flag/rollback, docs, runbook, support va owner walkthrough. Required CI
  yashil; real-content sample va permission matrix sign-off.

**Tugashi:** §10 14/14; migration/rollback rehearsal; 320/768/1440,
Resize Text 200%, Reflow 320 CSS px/400% va WCAG Text Spacing override alohida;
Chromium/Firefox/WebKit synthetic, kamida bir Android va iOS native, keyboard
va kamida bitta desktop/mobile screen reader. Owner
publish+moderate+rollback walkthrough alohida PASS. AWS faqat deployed SHA,
backup va smoke dalili bilan “released”.

## 6. Feature flag, sozlama va rollback shartnomasi

Flag faqat capabilityni yoqadi/o‘chiradi; limit yoki vaqt qiymatini saqlamaydi.
Hammasini birdan registrga qo‘shish shart emas — tegishli bosqichda va aniq
rollback bo‘lsa qo‘shiladi. Yangi presentation/capability rollout flaglari
default OFF. Compatibilityni saqlovchi emergency negative kill switch bundan
mustasno: `blog_community_writes` registry defaulti ON bo‘ladi, aks holda faqat
flagni deploy qilishning o‘zi mavjud comment/clap/like yozuvlarini o‘chiradi.

| Gate | Qamrov | OFF holati |
|---|---|---|
| existing `frontend_v1_public` | umumiy public V1 shell | current legacy renderer, lekin BLOG1.0 security projection saqlanadi |
| `blog_editorial_v2` | revision/service/studio UI | compatibility studio; canonical safe writes chetlab o‘tilmaydi |
| `blog_public_v2` | yangi Journal list/detail presentation | existing public presentation, same selectors/actions |
| `blog_learning_layer` | metadata/glossary/bookmark UI | maqola oddiy o‘qiladi, data saqlanadi |
| `blog_community_v2` | pagination/report/moderation projection | safe existing comments; canonical write/service saqlanadi |
| `blog_community_writes` (default ON) | comment/clap/like/report emergency kill switch | public read qoladi; POST 503/closed state, yangi row yo‘q |
| `blog_distribution` | manual/scheduled audience send | yangi intent va worker claim/send to‘xtaydi; pending row o‘chmaydi |

Schema, sanitizer, permission va audit invariantlari flag OFF bilan
o‘chmaydi. Renderer rollback data rollback emas. Additive migration kamida
bitta release compatibility saqlaydi; destructive column removal alohida
owner qarori va backup/restore evidence’dan keyin.

Public renderer kombinatsiyasi bitta URL/selectorga ega:

| `frontend_v1_public` | `blog_public_v2` | Renderer |
|---|---|---|
| OFF | OFF yoki ON | safe legacy presentation; `blog_public_v2` ignored |
| ON | OFF | mavjud V1 presentation, effective version/selectors |
| ON | ON | yangi Journal presentation, ayni effective version/actions |

`blog_editorial_v2` faqat studio presentationini almashtiradi; OFF legacy
form ham hidden expected-revision/operation token bilan canonical servicega
boradi. `blog_distribution` OFF bo‘lsa fresh check tashqi senddan oldin ham
qilinadi; allaqachon `sending` claim tugatiladi, yangi claim olinmaydi. Pending
intentlar pause holatida saqlanadi, ON bo‘lganda idempotent davom etadi.

Runtime o‘zgartirilishi kerak bo‘lgan retention/queue/rate chegarasi mavjud
audited operational settings surface’ga yoki aniq blog policy modeliga kiradi.
Product invariantlar (bir daraja reply, allowed workflow transition, no-XP)
kod/testda versionlanadi. Bir qiymat env+DB+constantda uch marta yashamaydi.

## 7. Security, privacy va abuse gate’i

- Stored/reflected/DOM XSS, link/embed/open redirect, CSRF, IDOR, preview leak,
  media polyglot/oversize, cache mix-up va formula/CSV injection test corpus.
- Published rich HTMLga CSP defense-in-depth; policy amaldagi global asset va
  CKEditor talablarini inventar qilmasdan productionda birdan yoqilmaydi.
- Permission revoke har GET/POSTda fresh; signed preview token actor accessini
  almashtirmaydi. Public share-preview owner alohida so‘ramasa yo‘q.
- Anonymous identifier first-party, rotated/bounded; IP/UA minimallashtiriladi.
  Retention tugaganda purge va aggregate qolish sharti docs/privacy copy bilan
  mos. Bu huquqiy xulosa emas; owner/legal review kerak bo‘lsa release gate.
- Rate limit fail-open/fail-closed qarori actionga mos: comment/report/clapni
  abuse’dan saqlaydi, article o‘qishni cache/Valkey nosozligida yopmaydi.
- Moderation evidence faqat ruxsatli rolga; public “nima uchun yashirildi” copy
  shaxsiy ma’lumot yoki internal reasonni chiqarmaydi.
- Seed/test/demo post production kontentiga aralashmaydi; `SeededRecord`
  provenance va wipe guard saqlanadi.

## 8. AI uchun alohida eksperiment — asosiy roadmapga shart emas

**`BLOG-X1: EXPERIMENT — canonical state yozmaydi`.** BLOG1.1–1.2, A8
Gemini budget gate’i va A9 teacher-authored critical quality/cost evallari
PASS bo‘lgandan keyingina owner alohida qabul qilishi mumkin. Oddiy fixture
“A9 yopildi” degani emas; threshold va evidence A9 contractidan olinadi.

Allowed suggestions: excerpt/SEO variant, heading audit, shared taxonomy
admitted bo‘lsa CEFR taxmini, glossary candidate va alt-text draft. Har natija:

- suggestion sifatida alohida ko‘rinadi; “Qabul qilish” human actioni normal
  editorial service orqali yangi revision yaratadi;
- article matni va embedded instructions untrusted input; tool/URL/publish/
  distribution huquqi yo‘q;
- supply reservation, timeout/cost, eval fixture va provenance bilan;
- AI ishlamasa butun studio qo‘lda to‘liq ishlaydi;
- CEFR/translation factual claimlari owner/editor tekshiruvisiz publicga
  o‘tmaydi. Auto-generate, auto-publish va background mass rewrite yo‘q.

Image generation, TTS yoki avtomatik translation BLOG-X1ga yashirincha
qo‘shilmaydi; har biri cost, copyright/provenance, accessibility va owner
workload bo‘yicha alohida admission oladi.

## 9. Agentlar uchun bajarish protokoli

Har implementer quyidagi tartibni saqlaydi:

1. AGENTS/rules/marinebook/README va ushbu bosqichni o‘qish; Git status/log/
   branch. Bitta checkout, faqat o‘z `codex/` branchi.
2. Bosqich source map: barcha writer/reader/admin/signal/task/command/template/
   JS/test. Topilmagan model yoki service’ni bor deb taxmin qilmaslik.
3. Admission line, outcome/KPI, canonical owner, adapter, flag/rollback va
   owner workloadni PR tavsifida qayta yozish.
4. Avval failing contract/regression testi; keyin minimal schema/service;
   so‘ng adapter/UI. View yoki JS ichida parallel business rule yo‘q.
5. Migration forward/backward compatibility, data backfill dry-run va
   production sample count. User data’ni “test uchun” o‘zgartirmaslik.
6. Safe env bilan focused Django → PostgreSQL kerak bo‘lsa integration → Node
   → `manage.py check` → tegishli full suite. Docs-only bosqich app testini
   yugurtirmasa buni aniq yozadi.
7. Browser qabulni real server ACK va DB readback bilan; screenshot chiroyli
   ko‘ringani canonical natija emas. No-JS va unknown/retry holati majburiy.
8. `git diff --check`, docs verifier, logical commit, marinebook, push, PR,
   required CI/review. Merge faqat repo standing tartibida; deploy/flag ON
   alohida sanalgan gate.

### PR/kesim navbati

| Navbat | Tavsiya etilgan kesim | Dependency | Qamrovdan chiqmaydigan natija |
|---|---|---|---|
| 1 | BLOG1.0a1 sanitizer + renderer parity | owner starts Blog | raw-safe path0; migration shart emas |
| 2 | BLOG1.0a2 preview policy/side-effect | 1 | foreign draft leak0 |
| 3 | BLOG1.0a3 malformed input/cookie | 1–2 | controlled 4xx/fallback; 500/partial0 |
| 4 | BLOG1.0b baseline/privacy + reconcile dry-run | 1–3 | dalil; silent apply yo‘q |
| 5 | BLOG1.1a expand schema/permissions | 1–4 | nullable additive schema; runtime parity |
| 6 | BLOG1.1b lifecycle service/dual contract | 5 | CAS/state/idempotency/audit |
| 7 | BLOG1.1c resumable backfill/verify | 6 | pointer/version hash-count parity |
| 8 | BLOG1.1d writer finalize/admin | 7 | direct mutable writer0; compatibility window |
| 9 | BLOG1.2a studio/taxonomy/landing | 8 | queues, owner settings, primary actions |
| 10 | BLOG1.2b editor/publish checklist | 8–9 | body/metadata/glossary/source authoring |
| 11 | BLOG1.2c autosave/recovery/version UI | 10 | stale/offline no data loss |
| 12 | BLOG1.3 public discovery/SEO/feed/cache | 7–8 | public list/index contract |
| 13 | BLOG1.4 reader/no-JS/bookmark shell | 12 | accessible detail journey |
| 14 | BLOG1.5 learning layer | 10,13 | glossary/course bridge; no SRS |
| 15 | BLOG1.6 community | 8,13 | moderation/concurrency |
| 16 | BLOG1.7 distribution/metrics | 8; 15 optional | canonical batch outbox; bounded analytics |
| 17 | BLOG1.8 hardening/rollout | 1–16 enabled scope | acceptance and rollback evidence |

Parallel ish faqat bir-birining canonical contractiga tegmaydigan read/UI/test
paketlarida. Ikki agent bir paytda migration yoki editorial service semanticsini
o‘zgartirmaydi. Oldingi bosqich review topilmasi yopilmay turib uning ustiga
keyingi UI contracti “test bilan mustahkamlanmaydi”.

## 10. Yakuniy qabul ssenariylari

1. Contributor faqat o‘z draftini yaratadi/preview qiladi; foreign preview
   404/403. Invalid cover/alt/embed inline xato, matn yo‘qolmaydi, publicga
   hech narsa chiqmaydi; editor/publisher mapping `is_staff`ga suyanmaydi.
2. Ikki tab bir postni tahrirlaydi; eski revision save’i yangisini bosmaydi,
   recovery/diff va aniq tanlov beradi. Same operation+payload receipt replay;
   same operation+different payload `409`.
3. First-publish schedule va live-post update schedule alohida; reschedule/
   cancel va exact due boundary/cache to‘g‘ri. Oldin eski live yoki 404, vaqtda
   pinned version live; schedule vaqti versionni mutatsiya qilmaydi, pair
   atomik/auditli almashadi; worker nosoz bo‘lsa ham visibility to‘g‘ri.
4. Publish double-click/replay bitta version/audit/effect. Parallel publish/
   unpublish/archive/rollbackdan row-lock winner o‘tadi; rollback targeti same
   post, expected-live fresh, schedule clear; tarix/media yo‘qolmaydi.
5. Malicious legacy HTML dry-run flaglanadi; publicda script/style/unsafe URL/
   iframe yo‘q, source version saqlanadi; unknown/outdated sanitizer plain-safe
   fallback beradi, save/backfill/reconciliation esa unique repair row yaratadi;
   request pathda avtomatik unpublish/write yo‘q.
6. Guest qidiruv→topic/conditional-level→pagination→detail→back yo‘lida filter
   va human label saqlanadi; draft/future/archive leak qilmaydi, page self-canonical.
7. 320px/400% reflow va JS-off foydalanuvchi article/TOCni o‘qiydi, comment
   yuboradi va clap/like’da HTML receipt ko‘radi; 200% resize, text-spacing,
   field error/live-region/target/keyboard contractlari alohida PASS.
8. Auth learner bookmark qiladi, glossaryni keyboard/touchda ochadi va related
   course/darsga o‘tadi; revoke qilingan access blog orqali ochilmaydi, XP0.
9. Invalid comment/reply matni va parent saqlanadi; duplicate submit bitta;
   report/hide/restore permission va audit bilan, bir daraja reply saqlanadi;
   account delete author/content/replyni cascade qilmaydi.
10. PostgreSQLda parallel clap/like/comment counter limit/unique invariantni
    buzmaydi; schedule/publication races stale `409`; reconciliation drift0.
11. Published detail canonical/OG/JSON-LD/sitemap/feedda bir xil title/date/
    image/author; page 2 self-canonical; preview/search indexlanmaydi;
    authenticated content cachega oqmaydi.
12. Audience dry-run va confirm oralig‘ida permission/recipient fresh tekshirildi;
    batch retry duplicate Notification/Outbox0; distribution OFF pendingni
    saqlab claim/sendni pauza qiladi; Telegram xatosi existing dead-letterda.
13. 1000 post/1000 comment fixture’da pagination/query/response budget; cover
    width/height, p75 measurement hook va no unbounded prefetch.
14. Rollout flaglari reverse tartibda OFF:
    `blog_distribution`→`blog_community_v2`→`blog_public_v2`→
    `blog_editorial_v2`; eski safe yo‘lga qaytadi va
    post/revision/comment/bookmark ma’lumoti o‘qiladi. Negative
    `blog_community_writes` default ON qoladi, faqat abuse/security incidentida
    alohida OFF qilinadi. Migration rollback nusxada va backup restore
    hash/count bilan.

## 11. Har bosqich dalili va BLOG-01 Definition of Done

Har stage hujjati quyidagilarni beradi:

- branch, base va final commit; migration/flag/setting ro‘yxati;
- o‘zgargan canonical service va barcha adapterlar;
- aniq safe-env test command/output, skip va backend;
- data backfill oldin/keyin count/hash va dry-run artifact;
- browser viewport/theme/zoom/no-JS/keyboard hamda native/AT chegarasi;
- flag OFF/ON readback va rollback; provider/server/deploy bajarilgan-bajarilmagan;
- yangi risk, owner qarori va keyingi exact slice.

BLOG-01 faqat quyidagida yakunlangan deyiladi:

- BLOG1.0–1.8ning admitted scope’i code/test/docsda, §10 14/14;
- publicda raw author HTML yo‘q, preview/ruxsat/cache/index leak0;
- revision/CAS/audit/idempotency barcha editorial writerlarda;
- owner texnik yordamsiz draft→publish→rollback va comment moderationni
  bajargan, sanalgan usability natijasi baseline bilan solishtirilgan;
- real-content, native device, keyboard/screen reader va production-like
  performance dalili mavjud;
- backup/restore va flag rollback mashq qilingan; required CI/review yashil;
- AWSga chiqsa deployed SHA va live smoke alohida qayd etilgan.

Rejaning yozilishi, prototip, lokal render, test yashil bo‘lishi, rollout
capability flagining default-OFF registrga qo‘shilishi, ownerning ko‘rib chiqishi
va production release — besh xil holat. Bittasi boshqasini avtomatik anglatmaydi.

## 12. Hozir ochiq owner qarorlari

Bu qarorlar BLOG1.0/1.1 source va data dalilidan keyin, tegishli stage oldidan
olinadi; butun roadmapni boshlashga blocker emas.

1. Contributor/editor/publisher/moderator rollariga amaldagi qaysi userlar
   kiradi? Default: least privilege, hozirgi owner publishni saqlash.
2. Anonymous read cookie/IP/UA qaysi maqsad va qancha retention bilan qoladi?
   Default: minimal/short retention; qarorsiz yangi tracking yo‘q.
3. Qaysi structured embed hostlari kerak? Default: hech biri; link fallback.
4. Courses coarse level va Library exact A1–C2 orasida qaysi shared taxonomy
   canonical bo‘ladi? Default: qarorgacha Blog CEFR ro‘yxati yaratmaydi;
   learning goal faqat “o‘quv maqolasi” turida majburiy.
5. Comment muallifi uchun edit window va public deletion copy qanday? Default
   hard delete yo‘q, moderator evidence saqlanadi.
6. `all active` content broadcastga umuman ruxsat beriladimi? Default: yo‘q;
   audience bo‘sh boshlanadi, owner har safar explicit user/cohort preview/
   confirm qiladi. Ruxsat berilsa high-impact owner-only action.
7. Audio article kerakmi? Default: asosiy roadmapga kirmaydi; transcript va
   content supply bo‘lmasa HOLD.
8. BLOG-X1 AI assist kerakmi? Default: OFF/EXPERIMENT; A8 hamda A9 critical
   teacher-authored eval PASS va alohida owner admissionsiz yo‘q.
9. Qaysi content kind source/checked-on/review-due talab qiladi? Default:
   vaqtga sezgir yangilik/faktual guide talab qiladi, shaxsiy metodik esse esa
   source bo‘lmasa publishdan avtomatik bloklanmaydi.

**Owner Blog implementatsiyasini keyingi aniq task qilib tanlasa, birinchi
kesim `BLOG1.0a1` — canonical rich-content sanitizer va renderer parity.**
Ungacha bu READY reja, joriy queue’ni almashtiradigan buyruq emas.
