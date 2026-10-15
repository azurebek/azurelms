# MESSENGER-01 — ishonchli, xavfsiz va ultra qulay yordam markazi

**Holat: REJA TAYYOR, IMPLEMENTATSIYA BOSHLANMAGAN.**
2026-10-15; source audit tayanchi `main`dagi **`84720ca`**.

Owner topshirig‘i: AzureLMS Messenger qismini radikal isloh qilish,
takomillashtirish va o‘quvchi, ustoz hamda owner uchun ultra qulay qilish.
Bu hujjat MESSENGER-01 uchun yagona batafsil product, data, security, AI,
UX va rollout rejasidir.

Oldingi [I4a human Messenger](I4A-HUMAN-MESSENGER.md) va
[I4b AI Messenger](I4B-AI-MESSENGER.md) ishlari bekor qilinmaydi: ular
V1 presentation porti, reconnectdagi no-auto-resend, compact history,
`AIResponseRun` idempotency va default-OFF rollout poydevorini bergan.
MESSENGER-01 “hech narsa yo‘q”dan boshlamaydi; aynan shu poydevor ustidagi
canonical command, membership, receipt, privacy va usability qarzlarini yopadi.

Ushbu reja yozilishi runtime muammolari tuzatildi, flaglar yoqildi, AWSga
deploy qilindi yoki owner qabul qildi degani emas. Birinchi implementatsiya
kesimi **MSG1.0a1**. Roadmap to‘qqiz phase va **34 reviewable slice**dan
iborat; bir PR bir slice’dan katta bo‘lmaydi.

---

## 1. Mahsulot qarori

### 1.1 Yakunda nima quriladi?

Messenger uchta parallel chat mahsuloti emas, **bitta yordam markazi** bo‘ladi:

- o‘quvchi kerakli guruh, kurs ustoz yoki shaxsiy AI yordamni nomlardan
  taxmin qilmasdan topadi;
- bitta mantiqiy yuborish reconnect, timeout, double-click yoki broker
  nosozligida ham ko‘pi bilan bitta xabar yaratadi;
- “yuborilyapti”, “server qabul qildi”, “natija noma’lum”, “xato” va “qayta
  urinildi” holatlari haqiqiy persisted receiptga tayanadi;
- history uzilsa sequence orqali aniq gap to‘ldiriladi; ko‘rilmagan soni
  sahifa ochilgani uchun emas, foydalanuvchi ko‘rgan watermark bo‘yicha yuradi;
- ustoz faqat o‘z kurs/cohort doirasidagi suhbatni ko‘radi va kontekstni
  qayta so‘ramasdan javob beradi;
- owner support ishlari uchun navbat, holat va auditni ko‘radi, lekin oddiy
  `is_staff` barcha shaxsiy/AI matnlarni qidira olmaydi;
- AI javobi quota, access, context va idempotency gate’laridan o‘tadi; private
  learner memory hech qachon guruhga chiqmaydi;
- Telegram, WebSocket va HTTP yangi business logic yaratmaydi — ular bir
  canonical command/event qatlamining adapterlari bo‘ladi;
- JavaScriptsiz kamida xona ro‘yxati, tarix, oddiy matn yuborish va xato
  tiklash ishlaydi; enhanced real-time tajriba ustiga qo‘shiladi.

### 1.2 Admission va navbat

**Umumiy natija: `ADMIT — post-launch`.** MESSENGER-01 mavjud ishlaydigan
human/AI Messenger ustidagi keng product islohoti; joriy core/B3/CLASSBOOK/
A8→A9 navbatini o‘z-o‘zidan almashtirmaydi.

Ammo quyidagilar feature emas, **security/correctness maintenance**:

1. WebSocket Origin himoyasi va qat’iy envelope/size/rate gate’i;
2. group yoki tutor/private human roomdagi `@azure` orqali private memory/
   progress chiqishini contain qilish;
3. AI workerda fresh access va raw provider error himoyasi;
4. direct Telegram Bot API yo‘lini darhol yopish; durable canonical
   notification/outboxni transactional eventdan keyin yoqish;
5. backoffice chat matni uchun least-privilege scope;
6. default legacy historyning eng eski 100 xabarda qolish xatosi.

Owner implementatsiyani boshlashni buyursa shu oltita qarzning xavfli runtime
yo‘llari MSG1.0 ichida birinchi contain qilinadi. Durable Telegram delivery kabi
canonical dependency talab qilgan closure esa roadmapdagi MSG1.2c → MSG1.7a
tartibida tugaydi. Keng inbox redesigni yoki yangi media MSG1.0 containmentidan
oldin chiqmaydi.

### 1.3 O‘lchanadigan natija va guardraillar

Baseline MSG1.0da synthetic fixture, PostgreSQL/Redis profili va owner
walkthrough bilan olinadi. Hozir o‘lchanmagan metric “yaxshilandi” deb
yozilmaydi.

| Outcome | Qabul targeti | Dalil |
|---|---|---|
| Ruxsat | cross-room/cross-user delivery **0**; revoke qilingan user keyingi command/event/workerda rad | permission matrix, open-socket revoke va delayed-worker test |
| Exactly-once logical send | bir `client_message_id` + bir payload → bitta `Message`/sequence; boshqa payload → conflict | SQLite va PostgreSQL concurrent/replay test |
| Truthful send UX | har local send 15 soniya ichida `accepted` yoki explicit `unknown`; unknown readback bilan yechiladi, jim auto-resend **0** | transport-fault browser test |
| History/realtime | message sequence bilan creation/history gap, event cursor bilan edit/delete/membership gap; reconnectdan keyin missing mutation **0**, duplicate render **0** | disconnect/reorder/1000-message va mutation scenario |
| Unread | concurrent send/read/reconnectdan keyin drift **0** | watermark invariant + reconciliation query |
| Topish | mavjud conversationni topish yoki to‘g‘ri yangi handoffga o‘tish ≤3 aniq amal | 5 vazifali owner/learner usability walkthrough |
| Human tezlik | stagingda matn command receipt p95 ≤500 ms; event visibility p95 ≤2 s | body-free timing telemetry; upload/AI alohida |
| AI | transport replay yangi run/attempt yaratmaydi; har user-authorized cycle’da generation `1 primary + ko‘pi bilan 1 fallback`, remote context embedding ≤1 batch va deferred memory embedding ≤1 bounded batch — jami provider network call ≤4, har biri attempt+supply bilan; provider gate’idan oldin revoke → call **0**, call davomida revoke → late output publish **0** va call metered | intent/attempt/idempotency/lease + end-to-end provider-call counter |
| Accessibility | 320 CSS px/400% reflowda gorizontal page scroll **0**; keyboard flow to‘liq; status semantik | automated + native keyboard/NVDA evidence |
| Owner yuki | membership enrollmentdan derived; oddiy ishda manual participant sync **0**; dead-letter/abuse queue bounded | reconciliation va owner workflow evidence |

Telemetry xabar matni, attachment nomi, AI prompti, Telegram tokeni, email yoki
to‘liq URL querysini yozmaydi. Browser recipient `Delivered` ACK contracti bu
roadmapda HOLD; outbox `published` hech qachon delivered deb ko‘rsatilmaydi.
“Read” esa faqat explicit user watermarkni anglatadi; ko‘z bilan o‘qilganini
da’vo qilmaydi va MSG-D5 admitted bo‘lmasa peer labeli ko‘rsatilmaydi.

### 1.4 Qamrovga kirmaydigan ishlar

MESSENGER-01:

- o‘z video/audio call platformasi, ekran ulashish yoki livestream qurmaydi;
- end-to-end encryption da’vo qilmaydi; server-side access/privacyni aniq
  boshqaradi;
- arbitrary public user-to-user DM yoki ko‘p-o‘qituvchi marketplace ochmaydi;
- PWA/offline-first background send yaratmaydi;
- AI pronunciation/STT baholash, avtomatik tarjima yoki “unlimited AI”
  va’da qilmaydi;
- Messenger ichida payment, enrollment, LessonProgress, Classbook session,
  SIT inquiry yoki support ticketning parallel canonical holatini yaratmaydi;
- typing indicator, online presence, typed human mentions, emoji pack, reactions,
  threads, forwarding va voice note’ni foundationdan oldin kiritmaydi;
- eski schema/fieldsni shu roadmap ichida shoshilib drop qilmaydi.

---

## 2. Tadqiqot chegarasi va amaldagi holat

### 2.1 Tekshirilgan ichki yuzalar

Audit quyidagilarni source, migration, test va hujjat darajasida ko‘rdi:

- [models](../../messenger/models.py), [access](../../messenger/access.py),
  [views](../../messenger/views.py), [consumer](../../messenger/consumers.py),
  [tasks](../../messenger/tasks.py), [signals](../../messenger/signals.py);
- [URLlar](../../messenger/urls.py), [ASGI](../../core/asgi.py),
  [private media](../../core/private_media_views.py) va
  [upload validation](../../core/upload_validation.py);
- legacy human/AI template va JavaScriptlari, V1
  [human template](../../templates/frontend_v1/messenger.html),
  [human controller](../../static/frontend_v1/js/messenger.mjs),
  [state reducer](../../static/frontend_v1/js/messenger-state.mjs),
  [AI template](../../templates/frontend_v1/ai_messenger.html) va
  [AI controller](../../static/frontend_v1/js/messenger-ai.mjs);
- existing [notification service](../../users/notification_service.py),
  [Telegram outbox](../../bot/outbox.py), Telegram AI adapteri va backoffice
  chat monitoring yuzasi;
- I4a/I4b evidence, launch backlog, feature flag registry va 175 ta focused
  Messenger testi.

Safe env baseline:

```powershell
$env:AZURELMS_SKIP_ENV_FILE='1'
$env:APP_ENV='local'
$env:LOCAL_USE_REMOTE_SERVICES='False'
$env:GEMINI_API_KEY=''
$env:TELEGRAM_BOT_TOKEN=''
.\venv\Scripts\python.exe manage.py check
.\venv\Scripts\python.exe manage.py test messenger --noinput --verbosity 1
```

Natija: system check **0 issue**, Messenger **175/175 PASS**. Testlarda
provider/broker failure loglari mock qilingan kutilgan ssenariylar; real Gemini,
Telegram, Redis yoki production tekshirilmagan.

Local DB faqat audit signali sifatida ko‘rildi: 9 xona, 23 xabar, 10 AI run;
bitta private participant anomaly topildi. Bu production hajmi, sifat KPI yoki
foydalanuvchi xulqi dalili emas.

### 2.2 Saqlanadigan yaxshi poydevor

| Mavjud tayanch | Nega saqlanadi | Reform chegarasi |
|---|---|---|
| Socket connect, receive va event deliveryda fresh room access tekshiruvi | enrollment/account revoke ochiq socketni yopadi | command write va delayed worker ham ayni policyga o‘tadi |
| V1 reconnectda implicit resend yo‘q | unknown natijada duplicate xavfini kamaytiradi | persisted nonce/receipt/readback unknownni yechadi |
| `created_at + PK` history cursor | teng timestampda stable ordering bor | canonical per-room sequencega compatibility bridge bo‘ladi |
| Private attachment storage, magic-byte gate va authorized stream | public media leakini kamaytiradi | sniffed type, lifecycle/quarantine va idempotent upload to‘ldiriladi |
| edit/delete row lock va optional revision | stale mutationni qisman ushlaydi | immutable revision, operation receipt va auditga o‘tadi |
| `AIResponseRun.idempotency_key` va supply ledger | provider duplicate/cost gate poydevori | stable request identity, lease, fresh access va outbox qo‘shiladi |
| Notification va `TelegramOutbox` | retry/lease/dead-letter mavjud | Messenger direct Bot API’ni tashlab aynan shu yo‘ldan foydalanadi |
| `frontend_v1_messenger` va `frontend_v1_ai_messenger` default OFF | presentation rollback mavjud | data/security behavior bu flaglarga bog‘lanmaydi |

### 2.3 P0 — yangi feature’dan oldin containment

| # | Aniq topilma va source | Xavf | Majburiy javob |
|---|---|---|---|
| P0-1 | [`core/asgi.py`](../../core/asgi.py) L21–27 WebSocketni faqat `AuthMiddlewareStack` bilan o‘raydi; `OriginValidator` yo‘q. Local [`ALLOWED_HOSTS`](../../core/settings.py) L145–152 ataylab `*` oladi, shuning uchun `AllowedHostsOriginValidator`ning o‘zi safe manba emas | cookie-auth socket boshqa origin’dan ochilishi yoki local wildcard orqali guard amalda ochiq qolishi mumkin | MSG1.0a1: scheme+hostli alohida `WEBSOCKET_ALLOWED_ORIGINS`, wildcard/missing Origin deny va aniq wrapper order |
| P0-1a | Messenger [`consumers.py`](../../messenger/consumers.py) L252–275 va Classbook consumer user/accessni yangilaydi, lekin connectdagi session key/auth hash hanuz validligini tekshirmaydi | logout/password/session revoke qilingan ochiq socket membership qolsa yozishda davom etishi mumkin | shared cookie-socket fresh session/auth helper; ikkala family command/delivery logout regressioni |
| P0-2 | [`consumers.py`](../../messenger/consumers.py) L53–124 JSON/action/text uchun strict schema, action allowlist, frame/text cap va rate limit bermaydi | storage/AI/Telegram abuse, memory/CPU pressure, noaniq protocol | versionlangan envelope, unknown action close/error, 64 KiB frame ceiling va kichik domain limitlari |
| P0-2a | [`Dockerfile`](../../Dockerfile) L70, [`deploy/docker-compose.prod.yml`](../../deploy/docker-compose.prod.yml) web commandi va root [`Procfile`](../../Procfile) L2 Daphne’ni frame/message limitisiz ishga tushiradi; [`README.md`](../../README.md) L86dagi `manage.py runserver`/manual Daphne yo‘li ham uncapped (Daphne runserver defaulti 1 MiB). Consumer checkigacha ASGI server payloadni buffer qiladi | app-level 64 KiB check memory-pressure chegarasi emas; CLI, runserver yoki runbookdan bittasi unutilsa himoya chetlab o‘tadi | MSG1.0a1: `DAPHNE_WEBSOCKET_MAX_MESSAGE_SIZE/FRAME_SIZE=65536`, barcha uch CLI launch source’da ayni explicit cap, safe root README/project-context/mobile-QA/**deploy README** runbook va artifact/runtime readback |
| P0-3 | [`models.py`](../../messenger/models.py) L39–112da sender nonce yoki room sequence yo‘q; [`consumers.py`](../../messenger/consumers.py) L108–159 client IDni faqat echo qiladi | ACK yo‘qolishi/manual retry duplicate xabar; ordering/unread drift | persisted `client_message_id`, unique constraint, sequence va canonical receipt |
| P0-4 | [`tasks.py`](../../messenger/tasks.py) L240–290 delayed AI worker xona ruxsatini qayta tekshirmaydi | revoke qilingan user provider budget ishlatishi va javob yozishi mumkin | worker claimdan va write’dan oldin fresh access/context check; terminal cancel |
| P0-5 | current `room_type='ai' OR '@azure'` triggeri [`consumers.py`](../../messenger/consumers.py) L147–159 va [`signals.py`](../../messenger/signals.py) L59–100dan AI’ni har qanday non-AI roomda, jumladan group va tutor/private human roomda chaqiradi; engine senderning private memory/progressidan foydalanadi | bir learnerning private konteksti group, tutor yoki support recipientiga chiqishi mumkin | MSG1.0bda **barcha** non-AI/shared-room AI OFF; faqat explicit shared-room profile/evaldan keyin qayta admission |
| P0-5a | [entitlements](../../core/entitlements.py) L37–47, L82–112 `AI_TUTOR`ni typed capability qiladi, lekin Messenger web/task/Telegram submission uni tekshirmaydi; test enrollment-siz AI roomni ochiq deb qotirgan | pricing/access contract drift; haqiqiy provider xarajati entitlementdan tashqari | owner ADR; default yangi remote AI send entitlement-gated, mavjud tarix read-only qolishi mumkin |
| P0-5b | staff lesson context [`access.py`](../../messenger/access.py) L22–36da keng; RAG `allowed_course_ids=None` bilan barcha kursga ketishi mumkin, canonical [teacher scope](../../core/access.py) esa default-deny | bir instructor boshqa course private materialini AI orqali olishi mumkin | canonical teacher-course + lesson access policy; no-scope = empty, “all” emas |
| P0-6 | [`tasks.py`](../../messenger/tasks.py) L588–618 Bot API’ga tokenli URL bilan direct `requests.post` qiladi, status/retry/idempotency/mute/fresh-recipient yo‘q | xabar yo‘qolishi/duplicate/stale recipient/content leak; exceptionda secret URL | MSG1.0c unsafe senderni yopadi va deliveryni truthful pause qiladi; durable Notification → TelegramOutbox faqat MSG1.2c event outboxidan keyin MSG1.7a’da |
| P0-7 | [`core/views.py`](../../core/views.py) L921–974 har qanday backoffice userga barcha room nomi, participant emaili va message body qidiruvini beradi | ordinary staff AI/private suhbatlarini ko‘rishi mumkin | role/course scope; body search default OFF; faqat MSG-D13 admitted bo‘lsa owner break-glass reason+audit |
| P0-8 | legacy [`views.py`](../../messenger/views.py) L285–289 `order_by('created_at')[:100]` bilan eng eski 100ni qaytaradi; page/history GET L369–376, L549–558 read state yozadi | 100+ xonada yangi xabar ko‘rinmaydi, lekin unread tozalanadi; legacy hozir rollback/default yo‘l | latest window hotfix; GET write-free; explicit visible watermark command |

P0 security fixlari presentation flag ortiga yashirilmaydi. Har biri backward
compatible test va alohida rollback/runbook bilan kichik PR bo‘ladi; “katta
redesign keladi” deb ochiq qoldirilmaydi.

### 2.4 P1 — canonical islohotning asosiy qarzlari

| Topilma | Source dalili | Target contract |
|---|---|---|
| Room modeli `room_type/cohort/participants` semantikasini DBda himoya qilmaydi | [models](../../messenger/models.py) L12–36 | stable subject, membership role/status, room-kind constraint va reconciliation |
| Private tutor xona mutable `name` va DBdagi birinchi superuserga bog‘langan; course instructor ishlatilmaydi | [access](../../messenger/access.py) L130–169; [Course instructor](../../courses/models.py) L53 | learner+course/enrollment subjectli tutor room; owner support alohida |
| AI room create/get atomik emas; duplicate bo‘lishi mumkin | [access](../../messenger/access.py) L39–74 | conditional unique subject + transactional get/create/backfill |
| Group instructor avtomatik participant emas; access participant rowga tayanadi | [access](../../messenger/access.py) L106–127 | canonical course/cohort teacher scope → derived membership |
| `is_read` bitta global Boolean; room state timestampga tayangan | [models](../../messenger/models.py) L39–67, L115–139 | per-tenure `last_read_sequence`; browser delivery ACK/label HOLD |
| room/page/history GET DBga state/access sync yozadi va readni erta belgilaydi | [views](../../messenger/views.py) L54–160, L345–390, L549–647 | query-safe selector; explicit read command only visible sequencegacha |
| socket DB write yangi transaction/service emas; broad exception `print` qiladi | [consumers](../../messenger/consumers.py) L278–299 | atomic command service, structured error va body-free log |
| shared eventdagi `can_edit` actor uchun hisoblanib butun groupga broadcast qilinadi | [views](../../messenger/views.py) L202–281, L714–778; [consumer](../../messenger/consumers.py) L208–213 | shared event universal; viewer capability recipient projectionda |
| WebSocket, widget/upload, AI worker, onboarding va Telegram adapteri turli joyda direct `Message.objects.create` qiladi | [consumer](../../messenger/consumers.py) L278–296; [views](../../messenger/views.py) L475/L768; [tasks](../../messenger/tasks.py) L300/L368/L469; [onboarding](../../users/views.py) L148/L158; [bot](../../bot/services.py) L1116–1141 | barcha supported writer canonical service; signal provider dispatcher emas |
| process ichidagi background task va broker-error direct `.run()` fallback duplicate qilishi mumkin | [consumers](../../messenger/consumers.py) L246–249, L343–375; [signals](../../messenger/signals.py) L59–100 | transactional outbox; broker acceptance noaniq bo‘lsa duplicate provider call yo‘q |
| AI retry har clickda random yangi key yaratadi | [consumers](../../messenger/consumers.py) L77–100 | transport replay attempt0; explicit retry yangi linked immutable generation cycle/attemptlar; regenerate yangi logical run, stable lineage/ID |
| Active SmartForm turn avval extractor providerini, keyin oddiy chat/search providerini chaqiradi; har chain fallback qilsa bitta user action 4 generation callgacha boradi | `ai/agent/engine.py` L62–75/L159–186; `ai/smart_form/extractor.py` L141–149 | deterministic local extraction yoki ayni generation response’dagi bitta structured reply+form-patch; generation total `1 primary + max 1 definite-failure fallback`, har call attempt+supply row |
| Oddiy AI turn chatdan oldin Memory/RAG query embedding, javobdan keyin esa har memory candidate uchun remote embedding chaqirishi mumkin; hozir bir user turni uchun total network bound/lineage yo‘q | [memory query](../../ai/memory/semantic.py) L112–120; [RAG query](../../messenger/rag.py) L905–913; [memory write](../../ai/memory/repository.py) L115–123 | per-turn memoized bitta context embedding batch, generation 1+1, successful outputdan keyin deferred/bounded bitta memory batch; provider-internal retry0, total ≤4 va har real call immutable attempt+supply |
| quota fail-open; quota-block message/run bitta transactionda emas | [tasks](../../messenger/tasks.py) L292–398 | fail-closed/admitted policy, atomic run/message/ledger receipt |
| AI run lease/stale recovery/cancel yo‘q; raw exception WSga chiqishi mumkin | [models](../../messenger/models.py) L302–368; [tasks](../../messenger/tasks.py) L527–567 | lease/expiry/cancel/reconcile; user-safe error taxonomy, raw internal only |
| upload sniffed kindni ignore qilib browser content type’ni saqlaydi; AI image action provider visioni yo‘q bo‘lsa ham taklif etiladi | [views](../../messenger/views.py) L748–818; [upload gate](../../core/upload_validation.py) L145–183 | canonical sniffed media type/lifecycle; capability-driven UI; unsupported image AI CTA0 |
| edit 4000 belgida jim truncate; delete textni bo‘shatadi, fayl/revision retentioni noaniq | [views](../../messenger/views.py) L692–743 | validation error, immutable revision/tombstone, explicit retention/delete job |
| V1 full message listni har eventda qayta render qiladi; faqat loaded roomsda client search | [messenger.mjs](../../static/frontend_v1/js/messenger.mjs) L79–129 | append/reconcile, server-side bounded search, focus/scroll preservation |
| legacy human pages AI template/sidebar contractiga bog‘langan; human rooms yo‘qolishi mumkin | [legacy AI template](../../templates/messenger/ai.html) L49–63 | shared inbox shell + typed room projection; renderer parity tests |
| legacy “Onlayn” va double-check haqiqiy receipt/presence bo‘lmasa ham ko‘rinadi | [legacy AI template](../../templates/messenger/ai.html) L90, L110 | yolg‘on status olib tashlanadi; faqat measured connection/receipt label |
| Telegram AI adapteri message yaratib `generate_ai_response.run`ni sync chaqiradi, stable update replay key yo‘q | [bot services](../../bot/services.py) L1093–1156 | Telegram update/message ID → canonical message/run idempotency |

### 2.5 P2 — product va polish qarzlari

- xona qidiruvi full history/participants/course bo‘yicha server-side emas;
- reply-to, bounded message search, mute/archive, report/block va moderator queue
  yo‘q; pin end-to-end mavjud, ammo `ChatRoomUserState` current-state/timestamp
  modelida va canonical membership/user-stream/no-JS parityga ko‘chirilmagan;
- tarix timestampi faqat `HH:MM`; eski kun va timezone konteksti yo‘q;
- attachment draft reload/reconnectda tiklanmaydi;
- unread real-time update va boshqa tab/device read reconciliationi yo‘q;
- transcript `role="log"` semantikasi, yangi xabarning qisqa announcementi va
  screen reader cadence aniq emas;
- 320px CSS bor, lekin native virtual keyboard, 400% browser zoom, iOS/Android
  va NVDA/VoiceOver acceptance ochiq;
- contextual course/lesson/SIT/Classbook handoff cardlari yo‘q; foydalanuvchi
  kontekstni matnda qayta yozadi;
- mavjud Control Center Telegram outbox pending/in-flight/oldest/failed/dead/
  backoff/last-sent healthini ko‘rsatadi; uni saqlab kengaytirish kerak. Ammo
  Messenger event-outbox lag/executor, stuck AI run, unread drift, room anomaly
  va moderation uchun birlashtirilgan health yuzasi yo‘q.

P2 ro‘yxat “hammasini birdan qurish” uchun emas. Har capability canonical
foundation va real user jobga bog‘lanmasa CUT/HOLD bo‘ladi.

---

## 3. Tashqi tadqiqotdan chiqarilgan majburiy qoidalar

Bu bo‘lim raqobatchi UI’ni ko‘chirmaydi. Rasmiy standart va framework
contractlarini AzureLMS acceptance talabiga aylantiradi.

1. Django Channels cookie-auth WebSocket boshqa sayt tomonidan ochilishi
   mumkinligini va private socketlar `OriginValidator` bilan explicit origin
   ro‘yxatga cheklanishini aytadi:
   [Channels security](https://channels.readthedocs.io/en/stable/topics/security.html).
   **Qaror:** `ALLOWED_HOSTS` localda `*` bo‘lishi mumkinligi sabab u security
   source emas. Alohida `WEBSOCKET_ALLOWED_ORIGINS` faqat scheme+hostlardan
   iborat; `*`, `null` va missing Originga jim ruxsat yo‘q. Wrapper:
   Channels matching/deny semantikasini saqlaydigan
   `BodyFreeOriginValidator(AuthMiddlewareStack(URLRouter(...)),
   allowed_origins)`; stock validator bermaydigan safe reject-reason telemetrysi
   origin/cookie/body qiymatisiz.
2. OWASP WebSocket Security explicit Origin allowlist, har message uchun
   authorization, qat’iy schema/size, rate limit, replay nonce, heartbeat,
   backpressure va sensitive-body’siz security loggingni tavsiya qiladi:
   [OWASP WebSocket Security](https://cheatsheetseries.owasp.org/cheatsheets/WebSocket_Security_Cheat_Sheet.html).
   **Qaror:** socket faqat event transporti; command service HTTP/WS adapteridan
   qat’i nazar ayni auth/idempotency contractini bajaradi. Consumer size checki
   bilan birga Daphne frame va message limitlari ham 65 536 byte; aks holda
   payload consumerga yetguncha allaqachon bufferlangan bo‘ladi.
3. OWASP upload fayl extension yoki browser Content-Type’iga ishonmaslik,
   allowlist/signature/size, generated filename, authorized access, webrootdan
   tashqari saqlash va parser/ZIP-bomb himoyasini talab qiladi:
   [OWASP File Upload](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html).
   **Qaror:** mavjud private storage/magic-byte saqlanadi; parserga beriladigan
   PDF/image alohida capability va resource budgetdan o‘tadi.
4. Celery late acknowledgment yoki worker nosozligida task bir necha marta
   bajarilishi mumkinligini, shuning uchun task idempotent bo‘lishini aytadi:
   [Celery configuration](https://docs.celeryq.dev/en/stable/userguide/configuration.html),
   [Celery optimizing](https://docs.celeryq.dev/en/stable/userguide/optimizing.html).
   **Qaror:** provider/notification side effect stable key, DB claim/lease va
   terminal receipt bilan; broker exceptionidan direct sync provider fallback yo‘q.
5. WCAG 2.2 Reflow 320 CSS px/400% ekvivalentida mazmun va amal yo‘qolmasligini,
   Target Size AA kamida 24×24 CSS px bo‘lishini talab qiladi:
   [Reflow](https://www.w3.org/WAI/WCAG22/Understanding/reflow.html),
   [Target Size Minimum](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum).
   **Qaror:** normative 24px gate, asosiy controls uchun product target 44px;
   mobile list/detail va composer virtual keyboard bilan testlanadi.
6. WCAG Status Messages holatni focus ko‘chirmasdan programmatic e’lon qilishni,
   ammo keraksiz live-region shovqinidan qochishni talab qiladi:
   [Status Messages](https://www.w3.org/WAI/WCAG22/Understanding/status-messages.html).
   **Qaror:** connection/send holati `role=status`, transcript `role=log`;
   har rerender butun chatni qayta o‘qitmaydi.
7. Telegram Bot API `sendMessage` matnini 1–4096 belgi bilan cheklaydi:
   [Telegram Bot API](https://core.telegram.org/bots/api).
   **Qaror:** faqat generic privacy copy + deep link; raw chat body/filename/AI
   output bu roadmapda Telegramga yuborilmaydi va persisted notification/outbox
   nusxasiga aylanmaydi.
8. KVKK deletion/destruction/anonymization uchun hujjatlashtirilgan policy,
   periodik bajarish va re-identification riskini baholashni talab qiladi:
   [KVKK qoidalar indeksi](https://www.kvkk.gov.tr/Icerik/5257/yonetmelikler),
   [deletion/anonymization guide](https://www.kvkk.gov.tr/yayinlar/Kisisel_Verilerin_Silinmesi_Yok_Edilmesi_veya_Ananonim_Hale_Getirilmesi.pdf).
   **Qaror:** retention raqami agent tomonidan o‘ylab topilmaydi; owner/legal
   qarori oldidan yangi cheksiz telemetry yoki body nusxasi yaratilmaydi.

---

## 4. Foydalanuvchilar va asosiy ishlar

### 4.1 Rollar

| Rol | Asosiy job | Ko‘rishi mumkin | Ko‘rmasligi kerak |
|---|---|---|---|
| Learner | to‘g‘ri yordamni topish, xabar/attachment yuborish, javobni davom ettirish | active membership xonalari, o‘z send/read holati | boshqa learner private/AI xonasi, internal moderation/provider error |
| Course instructor | o‘z course/cohort learnerlariga javob, kontekstli handoff | canonical teacher scope’dagi group/tutor xonalari | boshqa kurs, learner AI memory, owner support body |
| Owner/support | bounded support queue, explicitly authorized investigation | policy ruxsat bergan metadata; MSG-D13 admitted bo‘lsa break-glass bilan zarur transcript | sababsiz global body search, token/prompt/raw private attachment |
| AI actor | explicit private requestga bounded yordam | requesterga ruxsatli course/RAG va privacy-safe memory | boshqa learner, shared groupda private profile, stale attachment |
| Telegram adapter | generic notification va deep link, explicit inbound command | ayni userga mapped event | canonical room state yozish yoki access qarorini mustaqil chiqarish |
| System worker | outbox/run claim va side effect | stable operation/context hash | yangi business qaror, raw exceptionni foydalanuvchiga yuborish |

`is_staff` yoki room `participants` yagona authorization policy emas.
Instructor, owner-support va break-glass alohida permission/scope bo‘ladi.

### 4.2 Asosiy learner yo‘li

1. Headerdagi **Xabarlar** badge’i server tasdiqlagan unread aggregate ko‘rsatadi.
2. Inbox ochilganda **Barchasi / Guruhlar / Ustoz / AI** filterlari va server
   qidiruvi mavjud; xona nomi odamga tushunarli subjectdan hosil bo‘ladi.
3. Mobile’da avval room list, keyin detail; “Orqaga” scroll/filter/draftni
   saqlaydi. Desktopda split view.
4. Transcript latest windowga ochiladi; “Oldingi xabarlar” cursor/sequence bilan.
5. Composer oddiy matn uchun HTML POST fallbackga ega. Enhanced rejim
   HTTP command yoki socket orqali ayni `client_message_id`ni yuboradi.
6. Server receipt kelgach “Yuborildi”; timeoutda “Natija noma’lum — tekshirish”
   chiqadi. Refresh yoki reconnect jim qayta yubormaydi.
7. User ko‘rgan eng katta sequence explicit, debounced read command bilan
   tasdiqlanadi; room GET yoki hidden tab read qilmaydi.
8. Course/lesson/Classbook/SITdan kirilsa chat cardda manba konteksti va
   “Kontekstni ko‘rish” linki bor; domain canonical state Messengerga ko‘chmaydi.

### 4.3 Ustoz va owner yo‘li

**Ustoz inboxi:**

- faqat o‘z active course/cohort subjectlari;
- unread, “javob kutilmoqda”, course va learner bo‘yicha filter;
- conversation headerda learner/course/cohort va source handoff;
- canned reply faqat owner tasdiqlagan plain text template bo‘lsa, auto-send emas;
- boshqa ustozga assignment/transfer keyingi admission; v1da owner supportga
  explicit escalation card yetarli.

**Owner/support queue:**

- metadata-first: room turi, subject, oxirgi activity, unanswered age,
  outbox/run health;
- transcript ochish oddiy listning defaulti emas;
- private/AI body access faqat MSG-D13 `ADMIT` bo‘lsa purpose/reason,
  `SystemAuditEvent`, exact scope va expiry bilan; `DENY`da owner body access0;
- body qidiruvi default OFF; vaqtli incident/legal break-glass ham faqat D13
  `ADMIT`, `DENY`da route/control0;
- Telegram/AI dead-letter bir clickda canonical room/run/operation receiptga
  olib boradi, token yoki raw promptga emas.

### 4.4 Axborot arxitekturasi

| Yuza | URL yo‘nalishi | Asosiy amal | Empty/error |
|---|---|---|---|
| Unified Inbox | existing `/messenger/` entryni saqlab progressive replace | room topish/ochish | nega xona yo‘qligi; eligible course CTA |
| Conversation | stable room URL | tarix, send, reply, attachment | revoke 404/403; recoverable draft |
| AI private | existing AI route/room identity compatibility | prompt, stop/retry/regenerate, citation | quota/provider failda deterministic yordam |
| Server search | inbox query + bounded message search | room yoki xabarni topish | query retained, no-result suggestion |
| Notification deep link | signed/authenticated existing web route | exact room/sequence atrofini ochish | access revoke → generic inbox, body leak0 |
| Owner support | backoffice workspace ichidagi scoped route | queue/investigate/reconcile | permission denied yoki audited break-glass |

Yangi URLlar stable opaque room identitetini ishlatadi. Name, username yoki
mutable course title URL/authorization identiteti bo‘lmaydi. Existing bookmarks
redirect yoki compatibility adapter bilan saqlanadi.

### 4.5 Conversation UX contracti

Har message rowda faqat haqiqat ko‘rsatiladi:

- sender display name/role, local date separator va timezone-aware exact time;
- text/attachment/reply preview, edited marker va tombstone;
- own message uchun `Sending → Sent`; `Unknown` va `Failed` actionable;
- `Delivered` labeli admitted emas; outbox/channel publish undan dalil emas;
- `Read` faqat MSG-D5 admitted bo‘lib, boshqa memberning explicit read
  watermarkidan derive qilinsa; defaultda peer label yo‘q;
- AI rowda running/cancelled/fallback status va citation; internal stack/error
  yo‘q;
- retry ayni logical request uchun yangi linked immutable attempt/cycle;
  regenerate yangi logical run/request ekanini oldindan aytadi;
- composer limit va upload policy submitdan oldin va server xatosida bir xil.

V1da typing/presence/double-check haqiqiy contract bo‘lmaguncha ko‘rsatilmaydi.
“Onlayn” socket ochiqligini ham, odam hozir chatga qarayotganini ham isbotlamaydi.

---

## 5. Canonical arxitektura va ownership

### 5.1 Bitta yozuv yo‘li

Target oqim:

```text
HTTP POST / WebSocket command / Telegram inbound
                  |
                  v
        messenger.commands schema
                  |
                  v
 messenger.policy + command_service (atomic)
                  |
       +----------+-----------+
       |                      |
       v                      v
 Message/receipt/sequence   ChatEventOutbox/event_cursor
                                  |
                    +-------------+-------------+
                    |             |             |
                    v             v             v
                 Channels     Notification   AI run request
                    |             |             |
                    v             v             v
               browser gap   TelegramOutbox  provider worker
                  reconcile       adapter       lease/result
```

Canonical qatlam:

- `messenger/policy.py` — room/membership/action/content/fresh-context qarori;
- `messenger/commands.py` — typed input va stable operation identity;
- `messenger/services.py` — transaction, row lock, sequence, mutation, receipt;
- `messenger/selectors.py` — write-free inbox/history/search projections;
- `messenger/events.py` — versionlangan public event mapping;
- `messenger/outbox.py` — claim/lease/publish/retry/reconcile;
- `messenger/ai_service.py` — run/admission/retry/regenerate orchestration;
- `messenger/notifications.py` — canonical Notification payload, preference va
  privacy preview;
- HTTP views, Channels consumer va Telegram handler — faqat adapter.

Fayl nomi implementatsiyada repository conventioniga mos birlashtirilishi
mumkin, lekin ownership chegarasi o‘zgarmaydi. Consumer ichida ORM create,
provider dispatch yoki Telegram HTTP bo‘lmaydi.

### 5.2 Direct writer policy

Qo‘llab-quvvatlanadigan mutationlarning barchasi service’dan o‘tadi:

- message send/edit/delete/reply;
- upload finalize/delete;
- explicit self read watermark; browser delivery watermark HOLD;
- pin/mute/notification preference;
- AI request/retry/regenerate/cancel;
- report/moderation;
- room/membership provisioning va revoke;
- Telegram inbound message.

Django admin Messenger uchun general-purpose writer emas. Diagnostic list
read-only; tuzatish faqat named audited action/service. `QuerySet.update`,
model `save()` yoki signal orqali hidden business side effect test/commanddan
tashqari qo‘llanmaydi.

### 5.3 Transaction chegarasi

Bitta DB transaction:

1. actor/contextni lock/fresh tekshiradi;
2. operation key/payload hash replay yoki conflictni aniqlaydi;
3. yangi message bo‘lsa room `message_sequence`; room-visible create/edit/delete/
   access mutation bo‘lsa room `event_cursor` + `ChatEventOutbox`; self read/pin/
   mute/targeted revoke kabi private mutation bo‘lsa faqat ayni userning
   `user_event_cursor` + `MessengerUserEvent`ini ajratadi. Private mutation room
   cursorida teshik yaratmaydi;
4. message/revision/state yozadi;
5. command contractiga ko‘ra immutable receipt yoki monotonic/CAS result va
   tegishli room outbox/user event yaratadi;
6. commitdan keyin broker wake-up qiladi.

Broker/API chaqiruvi transaction ichida emas. Broker wake-up yiqilsa outbox row
qoladi va periodic reconciler oladi. “Broker qabul qilgan bo‘lishi mumkin”
exceptionida service/providerni sync qayta chaqirmaydi.
Composer text draft browser/session-local: server mutation, receipt va user
event0. Canonical `ChatRoom draft → active` esa birinchi accepted message
transactionining room-state qismi bo‘lib, shu message/outbox bilan atomik.

### 5.4 Canonical domain chegaralari

| Kontekst | Canonical owner | Messenger nimani saqlaydi |
|---|---|---|
| enrollment/course/cohort/instructor | courses/enrollment access policy | stable subject ref/snapshot label; accessni qayta hisoblaydi |
| Classbook live session/activity | Classbook | typed handoff card/ref; session state nusxasi emas |
| lesson/progress | courses/LessonProgress | source ref; progress foizi Messengerda yozilmaydi |
| SIT inquiry | `SITInquiry` roadmapdagi service | inquiry ref/status display; chat status canonical emas |
| payment/subscription | payment/subscription service | safe link/ref; receipt yoki entitlement mutation yo‘q |
| notification/Telegram delivery | Notification + TelegramOutbox | event/notification ref va channel preference |
| AI quota/supply/RAG/memory | existing AI control/ledger/RAG contracts | run/request ref, allowed context snapshot/hash |

---

## 6. Ma’lumot modeli va invariantlar

### 6.1 Room taxonomy

Bugungi `group/private/ai` qiymatlari birdan rename qilinmaydi. Target
semantika additive field va compatibility projection bilan:

| Target `kind` | Subject | Majburiy a’zolar | Tarix chegarasi |
|---|---|---|---|
| `academic_group` | aynan bitta cohort/course context | active cohort learners + assigned instructor(lar) | owner qarori bo‘yicha cohort start yoki membership join sequence |
| `academic_direct` | aynan bitta learner + course/cohort | learner + canonical `Course.instructor` | membership join sequence; instructor handoff policy explicit |
| `support` | optional inquiry/support case | requester + assigned support/owner | assignment va purpose bo‘yicha |
| `ai_private` | learner + conversation `public_id` | aynan bitta learner human membership | aynan shu private conversation tarixi; bir learnerda bir nechta boshlangan conversation mumkin |

Default tavsiya: **academic direct xona learner + course**. Bir learnerning
barcha kursi uchun bitta “Ustoz bilan” xona kontekst, instructor handoff va
history scope’ni aralashtiradi. Pre-enrollment/platform yordam esa `support`;
u “ustoz” deb ko‘rsatilmaydi.

AI/system uchun privileged synthetic `CustomUser` yoki login-capable participant
yaratilmaydi. AI provenance `Message.kind=ai`, `sender=NULL` va majburiy
AI run/attempt/operation receipt bilan; system message ham `sender=NULL` va named
service operation bilan. Haqiqiy service principal keyin kerak bo‘lsa alohida
non-login model/ADR/migration/test, learner membershipga qo‘shish emas.

AI uchun bugungi product ataylab topical conversationlar va onboardingdagi
`SmartFormSession` conversationini alohida saqlaydi; bular bitta active roomga
collapse qilinmaydi. Faqat hali xabarsiz “Yangi suhbat” drafti dedupe qilinadi.
SmartForm linki/backfilli o‘z conversation identity’sini saqlaydi va boshqa AI
room bilan uniqueness conflict bermaydi.

Existing private xonalar nom/participantdan jim taxmin bilan yangi subjectga
o‘tkazilmaydi. Audit:

- exact learner + exact active course/instructor isbotlansa map qiladi;
- bir nechta moslik yoki birinchi-superuser pattern bo‘lsa `ambiguous`
  quarantine reportiga qo‘yadi;
- ambiguity owner resolve qilmaguncha yangi send read-only yoki support
  fallbackga aniq yo‘naltiriladi; boshqa instructorga avtomatik ochilmaydi.

### 6.2 `ChatRoom` additive kengayishi

Existing PK va URLlar compatibility uchun qoladi. Additive target:

- `public_id UUID` — stable, unique, non-guessable external identity;
- `kind` — yuqoridagi semantic enum;
- `status = draft | active | read_only | closed | archived`; `draft` faqat
  `ai_private`ning hali xabarsiz yangi conversationi uchun;
- explicit nullable `course_id`, `cohort_id`, `learner_id` va kerak bo‘lsa
  typed support reference; generic mutable name subject bo‘lmaydi;
- `next_sequence` — default `1`, faqat yangi Message yaratish uchun keyingi
  room-local monoton raqam; edit/delete/read/membership buni sarflamaydi;
- `next_event_cursor` — default `1`, room-scoped content/generic access-version
  eventlari uchun alohida monoton cursor; private user state bu cursorni
  sarflamaydi;
- `last_message_id` va `last_activity_at` — inbox query budgeti uchun;
- `access_version` — membership/context policy o‘zgarishini event/clientga
  bildirish;
- `created_at/updated_at`.

DB invariantlari:

- active `academic_group` uchun cohort majburiy va learner bo‘sh;
- active `ai_private` uchun learner majburiy va cohort bo‘sh;
- active group per cohort unique;
- bir learnerda bir nechta `active` AI conversationga ruxsat; conversation
  identity `public_id` bilan;
- ko‘pi bilan bitta `draft ai_private` per learner conditional unique; ilk
  message transactionida `draft → active`, message countga qarab DB constraint
  qilish yo‘q;
- direct room canonical unique key MSG-D1 qaroridan so‘ng;
- invalid subject kombinatsiyasi model clean’ga emas, DB checkga ham uriladi;
- source FK delete room/message tarixini jim cascade qilmaydi: `PROTECT`,
  `SET_NULL` + snapshot yoki explicit close service.

### 6.3 `ChatMembership`

Yangi canonical row:

- `room_id, user_id`; unique pair;
- `role = learner | instructor | support | owner`; AI/system author user
  membership emas;
- `state = active | left | revoked | suspended`;
- `source_kind/source_id` yoki explicit enrollment/course assignment ref;
- current state/preference va current tenure pointer; tarixiy join/leave interval
  bu rowda overwrite qilinmaydi;
- current tenure FK; optional denormalized unread cache authority emas;
- `is_pinned, archived_at, muted_until`;
- notification preference ayni unique membership rowida: `notification_level`,
  `web_notification_enabled`, `telegram_notification_enabled`, nullable triple
  `quiet_timezone` (IANA/`zoneinfo`), `quiet_start_local`, `quiet_end_local`.
  Quiet triple yo hammasi NULL (disabled), yo hammasi non-null; interval
  half-open `[start,end)`, start>end bo'lsa midnightdan o'tadi, start=end disabled.
  Delivery instanti UTCdan IANA zonaga convert qilinadi, shuning uchun DST fall
  repeatdagi ikkala real instant bir xil wall interval policyga tushadi;
  membership unique `(room,user)` bo'lgani uchun preference scope ham bitta;
- `state_version` va `preference_version` monoton CAS tokenlari. Role/state/
  source/current-tenure lifecycle mutationi `state_version`ni; pin/archive/mute/
  notification-level/quiet/channel mutationi `preference_version`ni increment
  qiladi. Client/admin non-monotonic mutation expected tegishli versionni beradi;
  reconciler row lock ostida update+increment qiladi;
- `notification_level = all | non_group | none`: `all` barcha eligible room
  kindlari; `non_group` faqat `academic_direct|support|ai_private`, group0;
  `none` external Notification/Telegram0, lekin Inbox/user-event/unread qoladi.
  Human mention modeli bu roadmapda CUT, shuning uchun raw `@username` parsing
  permission/notification authority emas;
- `created_by_operation_id` va policy version; policy version CAS tokeni emas.

Membership source yo‘qolsa reconciler state’ni revoke qiladi, row/history
evidence’ni o‘chirmaydi.

### 6.3a `ChatMembershipTenure`

Leave → rejoin, suspend → resume, revoke → restore yoki instructor transfer bitta
intervalni kengaytirib, oraliqdagi maxfiy tarixni ochmaydi. Har contiguous access
davri alohida row:

- `membership_id`, room/user snapshot, source kind/ID;
- inclusive `visible_from_sequence`, nullable inclusive
  `visible_until_sequence`;
- `visible_from_event_cursor`, nullable `visible_until_event_cursor`;
- `last_read_sequence` shu contiguous tenure uchun; `last_delivered_sequence`
  browser device ACK contracti alohida admitted bo‘lmaguncha schema/UIga kirmaydi;
- `joined_at`, `left_at`, join/close reason, `join_receipt` va nullable
  `close_receipt`. Expand tartibida MSG1.1b avval nullable raw join/close
  operation UUIDlarini yaratadi;
  canonical `ChatOperationReceipt` FKlari substrate mavjud bo'ladigan MSG1.1dda
  additive qo'shiladi/validatsiya qilinadi;
- `boundary_state = provisional | sequence_final | final`. Receipt oldidagi
  compatibility davrida faqat hali `NULL` bo'lgan boundaryni bir marta exact
  qiymatga to'ldirish va state'ni oldinga surish mumkin; non-null boundaryni
  qayta yozish, state'ni orqaga qaytarish yoki intervalni kengaytirish mumkin
  emas. `final` open tenure uchun exact lower sequence+event boundarylar,
  closed tenure uchun esa lower+upper boundarylar mavjudligini anglatadi; active
  open tenure upper boundarylarining `NULL` bo'lishi normal;
- bir membershipga ko‘pi bilan bitta open tenure conditional unique.

Membership cutover receiptidan keyin tenure identity/history va lower boundary
immutable; `provisional|sequence_final` row bilan authority switch taqiqlanadi.
Open rowda faqat monotonic `last_read_sequence` va bir martalik close transition
(`visible_until_sequence`, `visible_until_event_cursor`, `left_at`, close reason,
`close_receipt`) ruxsat. Close service room/membership/tenure rowlarini bitta
transactionda lock qiladi, shu exact upper boundarylarni va close dalilini
yozadi, `ChatMembership.state/current_tenure/state_version`ni atomik yangilaydi;
tenure `boundary_state=final` bo'lib qoladi. Close qilingach upper boundary ham
immutable. Rejoin yangi tenure yaratadi; eski interval
o'zgarmaydi. Tenure interval unioni history/search/event uchun faqat **candidate
boundary**, accessning o'zi emas: `active` membership fresh source/policy bilan
allowed intervalni oladi; `left` default 404 bo'lib, faqat MSG-D2/domain policy
explicit post-exit read-only huquq bersa yopilgan intervalni o'qiydi;
`revoked|suspended` user projectioni interval mavjud bo'lsa ham non-enumerable
404, room content/fanout va external notification0. Faqat affected userga
minimal body-free `access_revoked|access_suspended` user-event + socket close
signali stale clientni converge qilish uchun required; u history/content access
bermaydi. Privileged moderation accessi alohida audited endpoint/policy, oddiy
selector emas. Current send active membership + open
tenure talab qiladi. Yangi tenure read watermarki
`visible_from_sequence - 1`dan boshlanadi; eski read evidence overwrite
qilinmaydi. MSG-D2 continuous old-history siyosatini tasdiqlasa ham u explicit
new tenure boundary/policy bilan, intervalni jim kengaytirish bilan emas.

`next_sequence` next assignable value bo‘lgani uchun open tenure
`last_read_sequence <= min(next_sequence - 1,
visible_until_sequence yoki next_sequence - 1)`; bo‘sh roomda watermark `0`.
Read POST faqat current open tenure’ni va uning visible max’igacha
`max(old, requested)` bilan suradi. Leave/revoke/**suspend** tenure’ni final
watermark bilan yopadi; rejoin/restore/resume fresh join receipt va current
`visible_from_sequence`/`visible_from_event_cursor` lower boundaryli yangi
tenure’ni ochib, read watermarkni `visible_from_sequence - 1`da boshlaydi. Send
paytida watermark avtomatik surilmaydi: parallel unseen peer message tasodifan
read bo‘lmaydi; own message unread hisobidan alohida chiqariladi.

Existing `participants` M2M va `ChatRoomUserState`:

1. avval read-only audit/backfill source;
2. canonical service bir compatibility release davomida ularga projection
   dual-write qiladi;
3. cutover receiptigacha legacy participants/state access authority bo'lishi
   majburiy; canonical row faqat compare/pilot renderer va toraytiruvchi veto,
   hech qachon send/history/delivery recipientini qo'shmaydi. Routing flag
   evidence/render projectionini tanlaydi, access authorityni emas;
4. immutable `MessengerMembershipCutoverReceipt` yaratilgach access authority
   faqat canonical row; flag/config/cache/DB read muammosi legacy participantni
   qayta authority qilmaydi — send fail-closed, safe history read-only;
5. stable evidence va owner approvaldan keyin alohida cleanup roadmapida
   freeze/drop; MESSENGER-01 ichida shoshilinch drop yo‘q.

### 6.4 `Message`

Additive target fields:

- `public_id UUID`;
- `sequence BIGINT`, unique `(room, sequence)`;
- `client_message_id` bounded opaque ASCII `CharField` va
  `client_payload_hash` — raw digest emas, versionlangan server-keyed HMAC;
  current legacy `Date.now()-random` IDlar compatibility
  davrida valid, yangi V2 client UUID yuboradi. Har sender migratsiya bo‘lmasdan
  DBda UUID constraint enforce qilinmaydi;
- `idempotency_origin = client_supplied | legacy_backfilled`; faqat
  `client_supplied` row canonical operation receipt sifatida reklama qilinadi;
- nullable forward `operation_receipt` OneToOne; post-writer-cutover new
  non-legacy Message uchun non-null, `legacy_backfilled` row uchun nullga ruxsat.
  MSG1.6ada nullable `ai_generation_cycle` FK qo‘shilib post-AI-cutover
  `kind=ai` uchun non-null enforce qilinadi;
- `kind = text | attachment | system | ai`;
- `reply_to_id`;
- `version`;
- `author_display_snapshot`; account delete policyga qarab sender `SET_NULL`;
- `edited_at, deleted_at, deleted_by_id, deleted_reason_code`;
- `created_at` — display/audit vaqt, ordering authority esa `sequence`.

Idempotency:

- human/user adapter uchun unique `(room, sender, client_message_id)`;
- system/AI uchun synthetic user yo‘q; stable named service actor scope +
  `operation_id` orqali `ChatOperationReceipt` unique. Bound Telegram human
  operationi real user actor + stable external update IDdan derive qilinadi;
- V2 human send ikkala aliasni yuboradi: `operation_id` va
  `client_message_id`; retry ikkalasini ham aynan qayta ishlatadi;
- service avval `(actor, operation_id)` receiptni, keyin
  `(room, sender, client_message_id)` Messageni tekshiradi. Ikkala alias ayni
  receipt/message/hashga bog‘langan bo‘lsa replay; bittasi boshqa counterpartga
  yoki boshqa hashga map qilsa `idempotency_conflict`, effect 0. Existing
  immutable accepted receipt conflict statusga mutatsiya qilinmaydi;
- legacy WS/V1/no-JSda explicit operation ID bo‘lmasa server yangi random
  **message nonce** yaratmaydi; deterministic UUIDv5 bridge:
  `legacy-v1:<actor_pk>:<room_public_id>:<client_message_id>`. Transport turi
  bridge identityga kirmaydi, shuning uchun HTTP/WS reconcile bir xil;
- payload hash versionlangan `message.send.v1`: command type, room public ID,
  Unicode NFC + CRLF→LF + outer-trim text (internal whitespace saqlanadi), reply
  public ID, ordered attachment public IDs va command-specific context refs.
  `request_id`, legacy action alias, timestamps va transport metadata excluded.
  Canonical bytes versionlangan secret bilan HMAC-SHA256 qilinadi; key ID
  saqlanadi, rotation/replay window va key destruction MSG-D3ga kiradi;
- bir key pair + ayni canonical payload hash → oldingi receipt/message;
- biror alias + boshqa hash/counterpart → `idempotency_conflict`, write/effect 0;
- client nonce server tomonidan generatsiya qilinmaydi; no-JS form uchun hidden
  UUID server renderda beriladi va PRG refreshda saqlanadi.

Pre-reform Message uchun accepted operation ixtiro qilinmaydi. Backfill avval
stable `public_id` beradi, keyin reserved `legacy:<public_id>` client ID,
`legacy.message.snapshot.v1` hash versioni va `idempotency_origin=
legacy_backfilled`ni deterministik yozadi. Ular uchun `ChatOperationReceipt`
yaratilmaydi va receipt endpoint ularni accepted client operation deb
qaytarmaydi. Existing sender bo‘lsa author faqat attribution; AI/system/null-
sender row kindi mavjud marker/room/task dalilidan aniqlanadi, ambiguous row
quarantine qilinadi — synthetic user/service operation yaratilmaydi. Non-null
constraint yangi post-cutover writerlarga qat’iy, legacy markerli rowlarga exact
conditional; rerun ayni ID/hashni beradi va reserved `legacy:` namespace yangi
client inputiga taqiqlanadi.

Content invariantlari:

- client command `kind`, sender yoki service scope tanlamaydi. New
  `text|attachment` human row real `sender` + user receiptni; `ai` row
  `sender IS NULL` + MSG1.2bda existing successful `AIResponseRun`/output link +
  named AI service receiptni, MSG1.6adan keyin esa forward
  `ai_generation_cycle` linkini; `system` row `sender IS NULL` + named service
  receiptni talab qiladi. DB same-row constraint receipt non-null, sender/kind
  shape va post-1.6 AI cycle FKni; canonical service esa receipt actor scope va
  run/cycle terminal holatini tekshiradi. Cross-table reverse existence DB CHECK
  deb da’vo qilinmaydi; faqat `legacy_backfilled` markerli eski AI/system rowga
  exact compatibility istisnosi;
- blank text faqat active attachment/system tombstone bilan;
- 4 000 Unicode code point va 16 KiB encoded text hard gate;
- reply ayni roomdagi visible messagega;
- deleted message body public projection/search/notificationga chiqmaydi;
- edit jim truncate qilmaydi; validation xato va user matni qaytadi.

### 6.5 `MessageRevision`

Har successful edit/delete/moderation:

- message, old version, actor, action, reason code, created_at;
- old text/attachment reference owner retention siyosatiga muvofiq encrypted/
  redacted snapshot yoki hash+metadata;
- append-only, ordinary admin update/delete yo‘q;
- stale `expected_version` mismatch `409`;
- restore eski rowni mutatsiya qilmaydi, yangi revision/action.

Revision body qancha saqlanishi owner/legal MSG-D3 qarori. Qarorgacha yangi
cheksiz body nusxasi yaratilmaydi; minimal actor/action/hash audit bilan
feature read-only qolishi mumkin.

### 6.6 `ChatOperationReceipt`

Replay-sensitive canonical mutation receipt. Message send/edit/delete, upload
finalize, AI request/retry, membership/moderation/report, pin/mute/archive/
notification preference va Telegram inbound kabi non-monotonic effectlar receipt
oladi. Explicit read watermark bundan yagona named exemption: `max(old,
through_sequence)` DB monotonic updatei o‘zidan idempotent, operation receipt
yaratmaydi; heartbeat/ping va local draft server mutation emas.

User operation scope'ining canonical substrate'i
`MessengerActorSubject(user OneToOne NULL/SET_NULL, opaque_ref UUID unique,
state=live|pseudonymized, created_at, unlinked_at)`. `opaque_ref` user ID/email/
hashidan derive qilinmaydi. Canonical receipt service unique user rowini lock/
get-or-create qiladi; parallel ilk operations bitta subject beradi. Account
deletion ayni privacy transactionida `user=NULL,state=pseudonymized` qiladi;
subject/opaque ref receipt retention tugamaguncha qoladi, yangi/recreated account
unga qayta bog'lanmaydi va yangi subject oladi.

- `operation_id UUID`, `actor_kind=user|ai_worker|system|telegram_service`,
  nullable `actor_subject` FK (`PROTECT` receipt mavjud paytda), nullable named
  `service_scope`, room, command type;
- DB check: user actor uchun `actor_subject` non-null/`service_scope` null;
  non-user actor uchun `actor_subject` null/`service_scope` non-null.
  `MessengerActorSubject`ning o'z checki `live→user non-null`,
  `pseudonymized→user null`; service receipt yaratishda mapping consistency fresh
  tekshiriladi. Conditional unique `(actor_subject, operation_id)` barcha live/
  deleted user rowsda va
  `(actor_kind, service_scope, operation_id)` non-user rowsda; oddiy nullable
  unique yoki synthetic `CustomUser`ga tayanilmaydi;
- optional human `client_message_id` alias;
- message result uchun forward authority `Message.operation_receipt`; receipt
  reverse relation orqali resultni topadi. Boshqa mutation resultlari quyidagi
  typed object ID/version bilan;
- canonical payload hash;
- result object type/ID/version, kerak bo‘lsa `message_sequence` va
  `event_cursor`;
- status `accepted | terminal_rejected | conflict`; `conflict` faqat oldin
  ko‘rilmagan operation ID existing client alias/counterpart bilan to‘qnashsa
  o‘sha **yangi** operation uchun terminal receipt bo‘lishi mumkin. Existing
  operation ID boshqa hash/alias bilan kelsa old accepted/rejected receipt
  o‘zgarmaydi va yangi row yaratilmaydi — service 409ni comparisondan qaytaradi;
  rate/cache/temporary
  pre-accept failure durable receipt emas va nonce’ni zaharlamaydi;
- bounded stable error code;
- created/full-response-expiry/compacted timestamps. Expiry keyni qayta
  ishlatishga ruxsat bermaydi: MSG1.8a receiptni **in-place** minimal body-free
  compact rowga aylantiradi; stable receipt PK saqlanadi, shuning uchun
  `Message.operation_receipt` va boshqa dependent FKlar hech qachon dangling
  bo'lmaydi. Compact rowda actor-scope yoki deletiondan keyingi pseudonymous
  scope, operation ID, versionlangan keyed payload HMAC va terminal safe code
  qoladi (unkeyed short-text digest taqiqlanadi) va keyingi
  replay `idempotency_key_expired`/old terminal result beradi, yangi effect0.
  Stable base receipt faqat actor endi authenticate bo'la olmaydi **va** barcha
  dependent side effect approved purge/rewire bilan yo'qolgach MSG-D3/
  PrivacyActionLedger contractida physical purge qilinadi. HMAC key retired/
  yo'q bo'lsa payload
  qayta solishtirilmaydi, har replay `idempotency_key_expired`, effect0;
  Message body purge `client_payload_hash`ni ham ayni key-lifecycle/compaction
  policyga kiritadi.

Null-safe actor scope + operation ID replayni yopadi. Terminal rejection replayda
ayni safe code qaytadi; retryable infrastructure/rate failure keyingi attemptni
bloklamaydi. Parallel AI/system/Telegram replay ham bitta receipt/effect beradi.
Receipt response body yoki raw chatni takrorlamaydi. Retention user
unknown reconcile oynasidan uzunroq. Full response muddati MSG-D3da belgilanadi,
ammo key expiry/purge duplicate side effectga yo‘l ochmaydi.

### 6.7 `ChatEventOutbox`

- aggregate room/message/membership;
- `event_cursor`, unique `(room, event_cursor)`; room-scoped canonical
  mutationlarning ordering/reconnect authority’si;
- optional `message_sequence`; faqat yangi message yaratilgan eventlarda;
- aggregate object/version; edit/delete eski Messagening eski sequence’ini
  yangi event ordering sifatida ishlatmaydi;
- `event_id` deterministic va unique;
- immutable `transport_generation`; writer transactionidagi
  `MessengerEventTransportRoute.generation` bilan bir xil, historical seed esa
  reserved generationda;
- versionlangan event type va body-free ref: object ID/version, cursors va
  safe reason code; text/body/filename/URL/email/prompt saqlanmaydi;
- audience basis privacy-safe va immutable: message eventi uchun room +
  `message_sequence`/membership epoch, private event uchun targeted tenure/user
  ref; body yoki mutable “current members” ro‘yxati emas;
- room-event publish holati `compatibility_only | historical_no_fanout | pending |
  claimed | published | dead`, attempt, lease, next attempt, last safe code;
- created/published timestamps.

`Message.sequence` faqat creation/history/unread ordering authority’si;
`ChatEventOutbox.event_cursor` esa create/edit/delete/reply/attachment-ready va
generic `access_version_changed` kabi room mutation ordering authority’si.
Peer read receipt MSG-D5 HOLD paytida room streamga umuman kirmaydi; read, pin,
mute va affected-user revoke kabi private state user streamida. Composer draft
browser-local va event0; room `draft→active` esa first-message room transaction/
eventi. Outbox
row mutation transactionida yaratiladi. Room broadcast `published` faqat
channel layerga universal hint
berilganini anglatadi, har client yetkazilganini emas; consumer forwarddan oldin
fresh accessni qayta tekshiradi va client event cursor bilan authorized fetch
qiladi. Shared event viewer-specific `can_edit`, email yoki internal reason olib
yurmaydi; capability recipient projectionda hisoblanadi.

User-scoped inbox/private-state uchun `MessengerUserStream`
(`user`, `next_user_event_cursor`) va logical
`MessengerUserEvent(recipient, membership_tenure, user_event_cursor, room_event?,
message_sequence?, type, object_ref, logical_key)` ishlatiladi. DB constraintlar:
unique `(recipient, user_event_cursor)` va globally unique deterministic
`logical_key`; room fanout keyi `event_id:recipient`, private-state keyi
`private_event_id:recipient`. Nullable `room_event` dedupeni chetlab o‘tmaydi.

Fanout ishining lease/retry holati alohida
`ChatEventDelivery(room_event/private_event ref, recipient, user_event?,
delivery_key, pending|claimed|published|dead, attempt, lease, safe_error)`da,
unique logical recipient key bilan; unda `channel` yoki ikkinchi user cursor
yo‘q. Browser `/user-events/` faqat `MessengerUserEvent`ni scan qiladi va
realtime publish durable device delivery deb sanalmaydi. Web/Telegram kabi
external channel attemptlari bu jadvalda ko‘paytirilmaydi: MSG1.7a canonical
`Notification`/`TelegramOutbox`ni alohida deterministic external key bilan
yaratadi.

Message transactioni individual user-stream cursorlarini lock qilmaydi: body-free
outbox row + immutable event-time audience basisni atomik saqlaydi. Fanout worker
content/inbox eventlarida append-only tenure visibilitydan candidate’larni derive
qiladi, keyin fresh room access faqat toraytiradi. Targeted body-free
`access_revoked|access_suspended` eventi esa oldindan persisted affected userga
current account/session identity orqali yetadi; active room access talab qilmaydi,
content/object projection bermaydi va boshqa recipient qo‘sha olmaydi.
Notification preference logical Inbox/user-eventni hech qachon tushirmaydi va
yangi recipient qo‘shmaydi. Worker recipient
IDlari bo‘yicha deterministic sorted, bounded batchlarda user-stream rowlarini
lock qilib bitta logical user event + delivery receipt yaratadi. Eventdan keyin join qilgan user eski notificationni
olmaydi; leave-before-claim send0 va rejoin absence gapini qayta ochmaydi.
Partial fanout bitta room-event statusiga yashirilmaydi. Browser inbox uchun minimal
`inbox.changed {room_id, user_event_cursor, room_event_cursor?}` hint yetarli;
client authorized selectorni qayta oladi. Telegram esa canonical Notification/
TelegramOutbox receiptiga ega.

Room event row/delivery/dead-letter hech qachon chat body nusxasi emas. Publisher
va gap endpoint object refni fresh access bilan canonical Message/tombstone’dan
projection qiladi; MSG-D3 tasdiqlamagan encrypted snapshot default emas. Delete/
purge’dan keyin persisted event va dead-letterda old body/filename qolmaydi.

`MessengerEventTransportRoute` singletoni `compatibility_v1 | event_v2`,
generation va cutover cursor/high-watermarkni saqlaydi; har transition uchun
immutable body-free receipt bor. Receipt exact generation, cutover high-watermark,
`minimum_event_epoch` va `minimum_schema_epoch`ni bind qiladi; trusted controller,
runtime lease va service-entry guard shu minimumlarga solishtiradi. Writer row
lock ostida route’ni o‘qiydi:
`compatibility_v1`da outbox `compatibility_only` va faqat fresh-authorized
post-commit V1 projection, `event_v2`da outbox shu immutable
`transport_generation` bilan `pending` va direct V1 broadcast0. Executor faqat
event-v2 transition receiptiga ega generationdagi pending rowni claim qiladi;
compatibility/historical rowni hech qachon claim qilmaydi. Mode pause/drain
bilan atomik o‘zgaradi; client/event projection ayni deterministic `event_id`ni
ishlatib, crash/reconnectda dedupe qiladi.

### 6.8 Attachment lifecycle

Existing Message FileField birdan alohida jadvalga ko‘chirilmaydi; additive
metadata yoki `ChatAttachment` bilan:

- generated storage key, original filename faqat escaped display metadata;
- size, hash, canonical `sniffed_kind`/MIME;
- `pending | ready | rejected | quarantined | deleted | purge_due`;
- uploader, room, operation ID, scanner/parser policy version;
- width/height/pages kabi bounded derived metadata;
- created/deleted/purge timestamps.

Browser `content_type` routing authority emas. DB rollbackdan keyingi orphan,
missing object va hash mismatch uchun default dry-run reconciliation commandi
bo‘ladi. Physical purge faqat owner retention, backup/legal-hold va idempotent
worker bilan.

### 6.9 `MessageReport` va moderation

Keyingi admitted slice:

- reporter, message, category, optional bounded note;
- status `open | reviewing | resolved | dismissed`;
- assigned moderator, resolution reason, audit;
- same reporter/message active duplicate constraint;
- reported content snapshot policy MSG-D3ga bog‘liq;
- report boshqa foydalanuvchining accessini kengaytirmaydi.

Instructor/supportni “block” qilish v1da yo‘q: learner mute + report qiladi.
Peer DMning o‘zi qamrovdan tashqarida.

### 6.10 Migration tartibi

Har schema oilasi **expand → audit → backfill → shadow → enforce → cleanup**
bo‘ladi:

1. nullable fields/jadvallar/indexlar; existing reads/writes o‘zgarmaydi;
2. `audit_messenger --dry-run` duplicate room, invalid subject/member, orphan
   file, private ambiguity va sequence hajmini sanaydi;
3. resumable `--batch-size --resume-token` backfill; rerun idempotent;
4. membership/history old/new projection shadow comparisoni;
5. qisqa controlled cutoverda legacy writer pause, qolgan null sequence catch-up,
   `next_sequence=max(message.sequence)+1`, historical fanout yaratmaydigan
   per-room snapshot/event baseline seed va `next_event_cursor=
   max(real_event_cursor)+1`, constraint va canonical writer enable;
6. rollout rollback read/adapter switch; row delete/drop emas;
7. kamida ikki stable release, backup/restore drill va owner sign-offdan keyin
   cleanup alohida admission.

Message sequence deterministic `(created_at,id)`. Historical message’lardan
pending event/notification yasalmaydi; snapshot baseline yoki terminal
`historical_no_fanout` marker ishlatiladi. Production-size backfill
katta `RunPython` transactioniga kiritilmaydi. Count/hash/quarantine artifact
stage evidencega qo‘shiladi.

---

## 7. Command, URL va realtime protocol

### 7.1 Target URLlar

| Method/URL | Contract |
|---|---|
| `GET /messenger/` | unified inbox; write0; mobile list-first, desktop safe last selection |
| `GET /messenger/rooms/<uuid>/` | canonical room shell/history; foreign/revoked non-enumerable 404 |
| `GET /messenger/rooms/<uuid>/messages/?before_sequence=N&limit=50` | older keyset page |
| `GET /messenger/rooms/<uuid>/messages/?after_sequence=N&limit=100` | yangi Message/history creation gap fill |
| `GET /messenger/rooms/<uuid>/events/?after_event_cursor=N&limit=200` | create/edit/delete/reply/attachment/generic access-version gap fill; retentiondan eski cursor snapshot talab qiladi |
| `GET /messenger/user-events/?after_user_event_cursor=N&limit=200` | faqat authenticated userning inbox/read/mute/revoke/multi-device state’i |
| `GET /messenger/inbox-snapshot/` | authorized room previews/unread/preferences consistent snapshoti + `snapshot_user_event_cursor`; user-event retention reset authority |
| `GET /messenger/rooms/<uuid>/messages/<uuid>/` | deep-link “around message” projection |
| `POST /messenger/rooms/<uuid>/messages/` | HTTP/no-JS send, nonce/idempotency |
| `GET /messenger/receipts/<uuid>/` | faqat actorga tegishli unknown reconciliation |
| `POST /messenger/rooms/<uuid>/reconcile-message/` | CSRF/no-store bodydagi legacy/V1 `client_message_id` (+ optional operation ID)ni ayni authenticated actor+room scope’da receipt/Messagega resolve qiladi; raw ID URL/logda yo‘q |
| `POST /messenger/rooms/<uuid>/read/` | explicit monotonic `through_sequence` |
| `POST .../edit/`, `.../delete/` | operation ID + expected version |
| `POST /messenger/search/` | CSRF-protected/no-store body orqali active scope ichida bounded message/room search; raw query URL/history/referrer/logga kirmaydi |
| `WS /ws/messenger/inbox/` | user-scoped room preview/unread events |
| `WS /ws/messenger/rooms/<uuid>/` | active room command/event adapter |

Existing numeric/group/tutor/AI routes compatibility davrida authenticated
redirect/projection. Foreign numeric ID leak bermaydi. Rollback eski unsafe
writerga emas, canonical service ustidagi legacy response/templatega qaytadi.

### 7.2 Command envelope

```json
{
  "v": 2,
  "type": "message.send",
  "request_id": "5e0b…",
  "operation_id": "a2ab…",
  "room_id": "d7fa…",
  "payload": {
    "client_message_id": "6fb9…",
    "text": "Salom"
  }
}
```

`request_id` faqat bir transport urinishining correlation IDsi va retryda
o‘zgarishi mumkin. `operation_id` hamda `client_message_id` logical send
aliaslari va V2 retryda o‘zgarmaydi; V1/no-JS bridge qoidasi `6.4`da.

Gate tartibi:

1. Daphne frame/message ceiling;
2. raw frame kelishi bilanoq, JSON decode va binary branchdan **oldin** cheap
   local per-connection transport token consume; binary, malformed JSON va valid
   frame bir xil hisoblanadi;
3. fresh session/user-active guard, so‘ng distributed per-user
   **transport/frame** bucket; barcha command, replay, conflict, binary va
   malformed frame hisoblanadi;
4. binary explicit rad yoki JSON decode; application object/minimal `v/type`,
   full schema/unknown-field policy;
5. fresh membership/subject access, so‘ng operation/client key + canonical
   payload hash lookup: same → existing
   receipt, different → conflict;
6. faqat yangi operation uchun per-user + per-room **mutation/business** bucket;
7. normalized content limit va idempotent service transaction.

Provisional transport limit: per connection va per user 30/10 soniya burst,
180/minute. Human mutation: per user+room 10/10 soniya burst va 60/minute.
Transport bucket DB receipt lookupni same-key flooddan himoya qiladi; replay
mutation bucketni yemaydi, transport bucketdan ozod emas. Bu abuse-safe starting
value; product metric bilan audited settingga kalibrlanadi. Limitni oshirish code
bypass yoki client-only check emas. AI quota/rate alohida va qattiqroq.

Har connectionda local cheap bucket cache’dan mustaqil qoladi. Distributed
per-user yoki mutation limiter cache’i unavailable bo‘lsa write command
fail-closed `temporary_transport_failure`; ping/close va HTTP read/history
qoladi. DB lookupka fail-open yo‘q.

Compatibility parser current actionless legacy payloadni aniq `message.send.v1`
ga map qiladi va bounded opaque client IDni qabul qiladi; bu noma’lum actionga
ruxsat emas. V1/V2 klientlar ko‘chirilgach compatibility branch telemetry bilan
alohida olib tashlanadi. `rate_limited` va `temporary_transport_failure` kabi
retryable pre-accept rad javobi immutable operation receipt yaratib nonce’ni
abadiy zaharlamaydi; faqat committed accepted/conflict yoki policy bo‘yicha
terminal rejection durable receipt bo‘ladi.

### 7.3 Event envelope

```json
{
  "v": 2,
  "type": "message.created",
  "event_id": "message:018f…:v1",
  "stream": "room",
  "room_id": "d7fa…",
  "event_cursor": 144,
  "message_sequence": 87,
  "occurred_at": "2026-10-15T12:34:56.123Z",
  "payload": {
    "message": {}
  }
}
```

Qoidalar:

- event at-least-once hint; DB event log/history authority;
- client `event_id`/message public ID bilan dedupe;
- expected `event_cursor`dan katta event → renderdan oldin `after_event_cursor`
  event gap fetch; kichik/takror event → ignore/reconcile;
- `message_sequence` faqat `message.created` va Message reference’i uchun;
  edit/delete/reply/attachment/access-version eventlari eski message sequence’ini
  ordering cursor sifatida qayta ishlatmaydi; read/mute/pin/private membership
  user `user_event_cursor` oqimida;
- event retention oynasidan eski gap → typed `snapshot_required` + floor/high
  watermark. Client authorized room snapshotdan transcript/tombstone/current
  membershipni ayni consistent read fence’dagi `snapshot_event_cursor` va
  `snapshot_message_sequence` bilan atomik almashtiradi, faqat successdan keyin
  cursorlarni persist qiladi va keyin fence’dan keyingi event/message gapni
  oladi; cursorni taxminan sakratish yo‘q. Concurrent edit/delete/revoke snapshot
  oralig‘ida yo‘qolmaydi;
- room event endpoint actorning membership-tenure/content visibilitysi bo‘yicha
  filter qiladi va har page’da `scanned_through_event_cursor`,
  `room_event_high_watermark`, `has_more` qaytaradi. Hidden audience event
  tafsiloti/placeholderi chiqmaydi; client visible listda cursor teshigi bo‘lsa
  ham `scanned_through_event_cursor`gacha atomik advance qiladi. Shu tariqa
  private event leak va cheksiz gap/refetch loop0;
- user stream faqat shu userga tegishli monoton `user_event_cursor`; peer read
  state room streamga chiqmaydi;
- `after_user_event_cursor` retention floor’dan eski bo‘lsa typed
  `snapshot_required` + floor/high-watermark qaytadi, event list yoki guessed
  cursor jump emas. Client `/messenger/inbox-snapshot/`dan authorized full
  Inbox/unread/preferencesni va ayni consistent read fence’dagi
  `snapshot_user_event_cursor`ni oladi, private state’ni atomik replace qiladi va
  faqat muvaffaqiyatdan keyin cursorni persist qiladi. Snapshot/revoke orasida
  yangi event bo‘lsa fence’dan keyingi gap odatiy fetch bilan keladi;
- ISO-8601 UTC timestamp + UI local timezone; faqat `HH:MM` contract emas;
- shared event universal data; `can_edit/can_delete` recipient projectionda;
- schema ichidagi noma'lum **optional field** ignore+metric qilinishi mumkin.
  Explicit noncritical event type registrydagi unknown type body-free metric bilan
  skip qilinib `scanned_through_event_cursor`gacha yurishi mumkin. Ammo unsupported
  major version, delete/revoke/access kabi critical type yoki criticalitysi
  noma'lum type cursorni jim advance qilmaydi: client stream apply'ni to'xtatadi
  va typed `upgrade_required` oladi yoki authorized room/Inbox snapshotni cursor
  fence bilan atomik almashtiradi;
- application heartbeat har 30 soniyada, 90 soniyalik idle deadline va bounded
  backpressure; slow/idle consumer close kodlari runbookda. Heartbeat/presence
  deb ko'rsatilmaydi.

Envelope’dagi `payload.message` wire-time fresh authorized projection; persisted
outbox payload emas. Outbox faqat body-free ref/version/cursors saqlaydi.

### 7.4 Send/unknown state machine

```text
draft_local
  -> submitting
      -> saved_on_server
      -> failed_definite
      -> reconciling_unknown
             -> saved_on_server
             -> failed_definite
             -> still_unknown (userga aniq tanlov)
```

`saved_on_server` — DB receipt, “recipient o‘qidi” emas. Socket ACK yo‘qolsa
receipt GET yoki history by nonce tekshiradi. Faqat idempotent service rollout
bo‘lgach client same nonce’ni avtomatik retry qilishi mumkin; yangi nonce yaratib
silent retry hech qachon yo‘q.

Attachment local intent textdan alohida upload sessionga ega; page reload
qilingan pending file browser xavfsizlik sababi bilan avtomatik qayta biriktirildi
deb ko‘rsatilmaydi. Persisted upload token bo‘lsa readback, aks holda file qayta
tanlash so‘raladi.

### 7.5 Read va delivery contracti

- GET room/history/search — write0;
- client transcript haqiqatan visible bo‘lganda eng katta visible sequence’ni
  debounced POST qiladi;
- hidden tab, failed history, room shell yoki deep-linkning mavjudligi read emas;
- self message, tombstone va membership visibilitydan tashqari sequence unreadga
  kirmaydi;
- cross-device read `max` bilan converge;
- group uchun boshqa har userning “read” ro‘yxati v1da ko‘rsatilmaydi;
- 1:1 read receipt faqat MSG-D5 owner/privacy qarori va haqiqiy watermark bilan;
- delivery external channel/browser device tomonidan tasdiqlanmasa label yo‘q.

### 7.6 Stable error taxonomy

User/clientga raw exception emas:

- `invalid_command`, `unsupported_version`, `message_too_large`;
- `rate_limited` + bounded `retry_after_ms`;
- `access_revoked`, `room_read_only`, `membership_required`;
- `idempotency_conflict`, `stale_revision`;
- `attachment_rejected`, `attachment_processing`;
- `quota_exhausted`, `ai_unavailable`, `context_unavailable`;
- `temporary_transport_failure`.

Internal log correlation/request ID bilan stack oladi, ammo body, prompt, token,
filename/email yo‘q. Foreign room uchun existence ochmaydigan generic 404/close.

---

## 8. AI, Telegram va domain integratsiyalari

### 8.1 AI private-room admission

AI — Messenger transportiga yashirilgan umumiy “hamma narsani biluvchi” actor
emas. Har request:

1. explicit user action yoki typed adapter event;
2. stable request/operation ID;
3. fresh user, membership, owner-approved entitlement policy/quota/supply;
4. requested skill va capability;
5. fresh course/lesson/RAG access;
6. privacy-safe context snapshot/hash;
7. run claim/lease;
8. provider;
9. user-safe result + canonical message/outbox.

Tavsiya etilgan default: typed `Capability.AI_TUTOR` yangi remote provider
requestining gate’i. Actual cutover MSG-D4 owner qarorisiz bajarilmaydi va reja
uni hozir enforced deb da’vo qilmaydi. Enrollment-siz existing room/history
birdan yo‘qolmaydi: read-only projection va aniq holat. Free/guest AI kerak
bo‘lsa alohida typed entitlement/quota/pricing ADR; testdagi eski permissive
behavior business qaror deb qabul qilinmaydi.

I4bdagi `AIResponseRun` compatibility parent/logical request aggregate sifatida
saqlanadi; additive `AIGenerationCycle` retry lifecycle'ni,
`AIDerivativeJob` esa publishdan keyingi bounded memory ishini ajratadi.
`AIAttempt` har physical provider callni hisoblaydi:

- logical run state `open | succeeded | cancelled | expired`; `failed` va
  `unknown_outcome` cycle outcome’lari. Run `open` paytda oldingi terminal
  cycle’dan explicit retry ochilishi mumkin; terminal run qayta ochilmaydi;
- `AIGenerationCycle`: `public_id UUID`, run + unique ordinal,
  `kind=initial|explicit_retry`,
  accepted user `request_receipt`, immutable input/context hash, state
  `queued → claimed → succeeded | failed | cancelled | unknown_outcome`;
  terminal cycle mutatsiya/reopen qilinmaydi, bir run uchun ko‘pi bilan bitta
  active cycle conditional unique;
- successful outputning alohida deterministic `publish_receipt`i
  `actor_kind=ai_worker`, named `service_scope=messenger.ai.publish` va
  `operation_id=UUIDv5(AI_PUBLISH_NAMESPACE, cycle.public_id)` bilan cycle'ga
  one-to-one linked. Output `Message.operation_receipt` shu service receiptga,
  `Message.ai_generation_cycle` esa cycle'ga qaraydi. User request receiptni
  worker actor receipt o'rnida qayta ishlatish taqiqlanadi;
- regenerate yangi logical run + initial cycle; explicit retry ayni open run
  ostida yangi user-authorized cycle. Run `succeeded` faqat bitta selected output
  Message atomik bog‘langanda; retry limiti tugasa user cancel yoki expiry bilan
  aggregate yopiladi;
- har physical provider network call = bitta immutable `AIAttempt`; parent XOR
  constraint bilan u generation cycle **yoki** derivative jobga tegishli. Kind
  `context_embedding | generation_primary | generation_fallback |
  memory_embedding_batch`, state
  `queued → claimed → provider_started → succeeded | failed | cancelled |
  unknown_outcome`. `explicit_retry` attempt kind emas; `retry_of_attempt` faqat
  generation fallback lineage’si uchun;
- `AIDerivativeJob`: successful cycle/outputga FK, kind=`memory_embedding`,
  bounded candidate manifest/hash, state/lease/expiry/cancellation va ko'pi bilan
  bitta `memory_embedding_batch` attempt. Cycle terminal bo'lgandan keyin bu job
  alohida yuradi; uning late failure'i published output/run holatini qayta
  ochmaydi;
- `lease_owner, lease_expires_at, ordinal, retry_of_attempt`, parent operation
  lineage va har attemptga one-to-one `AISupplyEvent`/accounting reference;
- request/context/prompt-policy/provider config hashes; publish receipt, output
  Message/outbox va cycle+run terminal state bitta transactionda;
- har accepted cycle generation boundi: `1 generation_primary + max 1
  generation_fallback`; fallback faqat adapter provider contracti bo‘yicha
  **definite primary failure** qaytarsa. Request bytes yuborilgandan keyingi
  connect/read timeout, reset yoki boshqa ambiguous outcome → primary
  `unknown_outcome`, fallback0 va warned explicit retry;
- Memory va RAG ayni query uchun cycle-scoped memoized embedding service’dan
  foydalanadi: cache/local hitda call0, missda ko‘pi bilan bitta batched
  `context_embedding`. Successful outputdan keyingi memory candidate embeddingi
  response publishni bloklamaydigan deferred jobda bounded candidate listni
  **bitta** `memory_embedding_batch` callga birlashtiradi; per-candidate N-call
  loop va unbounded candidate0. Generation cycle foreground boundi
  `context ≤1 + generation ≤2 = ≤3`; uning authorized derivative jobi
  `memory ≤1`, demak bitta user-authorized end-to-end lineage total provider
  network boundi `≤4`;
- provider `generate()` va `embed_content()` ichida yashirin retry/model-
  candidate/per-item loop bo‘lmaydi. Adapter bitta network request qiladigan primitive va typed
  `definite_failure | ambiguous_outcome | success` natija beradi; cycle
  orchestrator har call **oldidan** immutable `AIAttempt` + supply reservation/
  event yaratib, `provider_started`ni network boundaryda belgilaydi va primary/
  fallback qarorini o‘zi qabul qiladi. Shu contractga mos bo‘lmagan provider
  disabled qoladi;
- active SmartForm turn alohida extractor provider chain ochmaydi: local
  deterministic parse yoki ayni primary/fallback response’dagi schema-validated
  `{assistant_reply, form_patch}`; generation boundi `1 primary + max 1
  definite-failure fallback`, derivative bilan end-to-end total yuqoridagi ≤4;
- `provider_started`dan oldingi stale claim safe reclaim qilinishi mumkin;
  undan keyingi crash auto-call qilinmaydi; stale cycle/attempt reconciler va
  bounded retry-cycle/time limit;
- cancellation providerni har doim to‘xtatish kafolati emas, lekin late resultni
  userga publish qilmaslik gate’i.

### 8.2 Worker fresh-access va context gate

Current worker room/user/message’ni olgach providerga ketishidan oldin canonical
room accessni qayta tekshirmaydi. Target worker:

- claimdan oldin user active, membership active va source enrollmentni;
- provider oldidan quota/supply/context capabilityni;
- provider natijasini yozish oldidan room/access version va cancellationni
  qayta tekshiradi;
- revoke/context change bo‘lsa `status=cancelled` va bounded
  `terminal_reason_code=context_changed`; provider hali chaqirilmagan bo‘lsa
  call 0, call davomida revoke bo‘lsa late output discard va urinish metered;
- history/message parent ayni room/requesterga tegishli ekanini tekshiradi.

RAG faqat active enrollmentga emas, canonical lesson access/drip/sequential
policyga suyanadi. [Course access service](../../courses/access_service.py)
ishlatiladi; locked lesson matni prompt/citationga kirmaydi.

Har intent uchun immutable `AIContextGrant` saqlanadi: channel mode, authorized
course/lesson IDs, memory read/write, personal progress, selected attachment
IDs, policy/access version va expiry. Worker fresh policy bilan grantni
runtime intersectionda toraytiradi, kengaytirmaydi; persisted grant mutatsiya
qilinmaydi. Per-user allowance ham provider oldidan
atomik reserve/reconcile bo‘ladi; metering read xatosi, explicit admin block va
global A8 denial bir xil broad-except fail-open yo‘lga tushmaydi.

### 8.3 Non-AI/shared room `@azure`

**Default va immediate qaror: OFF.** Hozir senderning private memory, homework
va progress konteksti shared responsega aralashishi mumkin. MSG1.0b:

- group, tutor/private va support human-room trigger/marketing/UIni disable
  qiladi;
- existing non-AI room message oddiy human text bo‘lib qoladi;
- provider call 0 test;
- old non-AI room AI javoblari uchun body-free count/room/message-ID audit; potensial
  private-context rows default learner projectionidan quarantine qilinadi;
- review queue defaultda faqat body-free room/message ID, reason va risk
  metadata ko‘rsatadi; body faqat MSG-D13 alohida `ADMIT` bo‘lsa named owner
  break-glass reason/scope/expiry/audit bilan. D13 qarorisiz owner body access0;
  delete/purge esa retention/legal qarorisiz bajarilmaydi.

Kelajakda qayta admission uchun:

- `shared_room` prompt profile private memory/progress/DM/historyni mutlaqo
  olmaydi;
- faqat ayni cohortga public course content va group-visible messages;
- raw `@azure` parsing emas, typed shared-AI action va teacher/admin enable;
- admitted shared-room turiga mos quota/cost/rate;
- 30+ privacy/injection/cross-user eval, A9 va owner pilot;
- UI “guruhga ko‘rinadi” deb requestdan oldin aytadi.

### 8.4 System instruction va untrusted context

Provider adapter system va user/context rolini haqiqatan ajratishi kerak.
Bugungi flat user prompt contracti target emas:

- versionlangan system policy providerning system/instruction kanalida;
- user message, RAG, profile, attachment extracti **untrusted data** delimiters
  va source metadata bilan;
- data ichidagi “oldingi ko‘rsatmani unut” instructionga aylanmaydi;
- output citation faqat requester hozir ochishi mumkin bo‘lgan sourcega;
- provider switch ayni golden eval va system-role capability testidan o‘tadi;
- prompt/output body observability logiga yozilmaydi.

Evidence canonical `EvidenceRef` bo‘ladi: kind, object ID, content version/hash,
safe title/deep-link, excerpt hash, retrieval time, access-scope hash va
freshness. UI citationni tooltipga yashirmaydi; clickda access qayta tekshiriladi.
Embedding unavailable bo‘lsa launch contractidagi bounded lexical fallback
ishlaydi yoki aniq `context_unavailable`; jim empty RAG + ishonchli ohang yo‘q.

### 8.5 AI attachment

- `supports_vision=False` bo‘lsa image analysis CTA, auto-prompt va “ko‘ra
  olaman” copy **0**; image oddiy human attachment sifatida qolishi mumkin;
- route canonical sniffed kindga qaraydi, browser MIME/filenamega emas;
- PDF extract page/byte/time/token cap, encrypted/password/ZIP bomb va malformed
  failure code bilan;
- attachment text untrusted; embedded prompt instruction emas;
- faqat requestdagi explicit `selected_attachment_ids`; xonadagi “oxirgi 30”
  fayldan ambient tanlash yo‘q;
- source access provider oldidan va citation click paytida tekshiriladi;
- upload muvaffaqiyati AI analysis muvaffaqiyati degani emas;
- raw extracted text/multimodal derivative retention MSG-D3ga kiradi.

### 8.6 Retry, regenerate va idempotency

- **Transport replay:** ayni operation; terminal success bo‘lsa oldingi outputni
  qaytaradi, yangi attempt/provider call 0;
- **Explicit retry:** latest cycle’i `failed` yoki `unknown_outcome` bo‘lgan
  hali `open` logical run bilan bog‘langan yangi user-authorized immutable
  `explicit_retry` cycle; uning physical
  urinishlari yangi primary/fallback `AIAttempt` rowlari;
  userga oldingi natija noma’lumligi va yangi quota ehtimoli aniq;
- **Regenerate:** user tasdiqlagan yangi logical operation/run; oldingi output/
  revision saqlanadi va qo‘shimcha quota aniq;
- transport reconnect yangi run emas;
- web/widget/Telegram bir xil canonical request service;
- Telegram inbound stable key: bot identity + chat ID + update/message ID;
- widget browser operation ID; login/cross-device scope aniq;
- post-save signal AI command dispatcher bo‘lmaydi.

### 8.7 AI memory delete/clear

“Chatni o‘chirish” Message qatorini bo‘shatib, memory summary/fact/embedding/
trace/file extractini qoldiradigan yolg‘on amal bo‘lmaydi. UI alohida tushuntiradi:

- conversationdan yashirish/tombstone;
- AI personal memoryni ko‘rish/o‘chirish;
- account/data deletion requesti;
- legal/audit retention istisnosi.

Purge graph source message → summary/fact/embedding/trace/attachment derivative
bo‘yicha dry-run count beradi. Qaror va backupdan oldin destructive job yo‘q.
Yangi memory fact/trace provenance’i source message/intent va policy versionga
ulanadi; raw question/value trace’da maqsadsiz ko‘paytirilmaydi. Deleted message
conversation context va stale summaryga qayta kirishi mumkin emas.

### 8.8 AI A8/A9 release gate

MSG AI v2 quyidagisiz public default ON emas:

- A8 quota/supply fail-closed va concurrency proof;
- A9 50+ case: Uzbek/Turkish normal, hallucination, unavailable source, locked
  lesson, cross-user memory, group privacy, prompt injection, PDF poison,
  provider timeout/retry, quota va cost;
- latency/token/cost budgets;
- fallback copy va deterministic safe handoff;
- owner sampled review; raw private content eval artifactiga ko‘chirilmaydi.

Repositorydagi A9 contracti o‘zgarmaydi: foundation 50, critical beta 75,
premium gate kamida 150 teacher-authored case, target 320; 0–4 rubric.
Critical safety/access failure **0**, injection success <1%, Turkish ≥92%,
grounded support ≥95%, RAG recall@4 ≥90%, memory precision ≥97%, text p95 <8s,
hard deadline 35s, max bir fallback va AI cost/premium revenue ≤25%.
Sample minimumiga yetmagan natija `PASS` emas, `INSUFFICIENT_DATA`. Messenger
subset bu global A9 o‘rnini bosmaydi; uning privacy/adapter casesini qo‘shadi.

Foundation 50 Messenger taqsimoti:

- 12 Turkish/CEFR correctness;
- 8 pedagogik correction/scaffolding;
- 8 RAG/citation/released-vs-locked access;
- 8 injection: user, lesson/RAG, PDF, memory, submission;
- 6 memory/privacy/shared-room;
- 4 routing/capability;
- 4 failure/idempotency/adapter parity.

Har case dataset version, actor/channel/entitlement, room/course/lesson access,
untrusted context, expected route/evidence, forbidden disclosure,
`max_generation_calls=2`, `max_context_embedding_calls=1`,
`max_memory_embedding_batches=1` va `max_total_provider_calls=4`ni yozadi.
Production chat
avtomatik training/eval corpusiga
tushmaydi; feedback faqat manual redaction va teacher promotiondan keyin.

### 8.9 Telegram outbound

Messenger direct Bot API taski MSG1.0c containmentida olib tashlanadi va
canonical durable yo‘l tayyor bo‘lguncha Messenger→Telegram delivery aniq
`paused` bo‘ladi; unsafe best-effort replacement “migratsiya tugadi” deb
atalmaydi. MSG1.2c event outboxidan keyin MSG1.7a quyidagi final oqimni yoqadi:

```text
message.created event
  -> fresh recipient + preference + quiet-hours
  -> users.Notification (deterministic external key)
  -> existing TelegramOutbox
  -> lease/retry/dead-letter sender
```

Preview faqat “Ustozdan yangi xabar” / “Guruhda yangi xabar” kabi generic copy
va authenticated deep link. Notification/outbox faqat typed room/message
reference saqlaydi; relative deep link fresh access tekshiruvidan keyin delivery
vaqtida materialize qilinadi, URL/host/query/token persisted emas. Raw chat body,
attachment filename yoki AI output MESSENGER-01da Telegram payloadiga kirmaydi;
“preview opt-in” CUT. Kelajakda raw preview so‘ralsa bu MSG-D3 retention/export
graphi va alohida privacy admission bilan yangi task bo‘ladi. Generic copy Bot
API capdan past; token URL/logda chiqmaydi.

Mute yoki `notification_level=none` canonical web historyni o‘chirmaydi.
Recipient access send attemptida yana tekshiriladi. Delivery yiqilsa Message
saqlangan qoladi, owner dead-letter ko‘radi.

### 8.10 Telegram inbound va widget

Telegram AI/human inbound:

- account binding/fresh access;
- stable external update ID;
- ayni `send_message/request_ai` service;
- duplicate webhook/poll replay → bitta Message/run;
- sync `.run()` provider chaqiruvi yo‘q;
- platformga mos max length/attachment mapping;
- unsupported feature uchun web deep link.

Widget:

- anonymous bo‘lsa alohida guest-support product admissionisiz Messengerga
  yashirin AI room yaratmaydi;
- authenticated widget ayni operation ID/access/quota/policyga;
- full-screen Inboxga deep link exact context bilan.

### 8.11 Course, Classbook va SIT handoff

Typed card faqat reference/snapshot:

- `source_kind`, stable source ID, safe title, origin URL;
- actorning current accessi render/clickda tekshiriladi;
- delete/unpublish/revoke bo‘lsa generic unavailable;
- recipientga ruxsatsiz course/learner metadata event/Telegramga chiqmaydi.

SIT inquiry status `SITInquiry`da; Messenger “yangi/yakunlandi”ni mustaqil
yozmaydi. Classbook session/activity Classbookda. Course progress Messenger
message orqali oshmaydi. Handoff unavailable bo‘lsa canonical domain object
saqlanadi va ownerga visible failure beradi.

---

## 9. Security, privacy, accessibility va performance

### 9.1 WebSocket va session

- dedicated `WEBSOCKET_ALLOWED_ORIGINS` scheme+host ro‘yxati; `ALLOWED_HOSTS`
  bilan implicit bog‘lanmaydi, chunki local profil unda `*` ishlatadi; wildcard
  konfiguratsiya check/deployni yiqitadi;
- exact ASGI order: Channels matching contractini ishlatadigan kichik audited
  `BodyFreeOriginValidator(AuthMiddlewareStack(URLRouter(...)),
  settings.WEBSOCKET_ALLOWED_ORIGINS)` outer wrapperi; u stock
  `OriginValidator`ning deny semantikasini saqlaydi, lekin reject sababini
  (`missing|null|malformed|not_allowed`) origin qiymati/cookie/body'siz structured
  security eventga yozadi. Validator barcha cookie-auth Messenger/Classbook
  socketlarini o‘raydi;
- foreign, `null`, missing Origin policy browser/non-browser contract bilan;
- trusted reverse proxy/HTTPS host testi;
- barcha cookie-auth HTTP mutationlar (`send/read/edit/delete/upload/preference/
  moderation/search`) standard Django CSRF validationni saqlaydi; enhanced client
  uchun blanket `csrf_exempt` yoki permissive CORS yo‘q. Telegram/webhook alohida
  signature/binding gate’dan o‘tadi;
- source settingda immutable hard ceiling
  `DAPHNE_WEBSOCKET_MAX_MESSAGE_SIZE=65536` va
  `DAPHNE_WEBSOCKET_MAX_FRAME_SIZE=65536`; bu `manage.py runserver` yo‘lini ham
  Daphne’ning 1 MiB defaultidan himoyalaydi;
- Dockerfile, production compose va Procfile Daphne commandlarida defense-in-
  depth sifatida ayni explicit `--websocket-max-message-size 65536
  --websocket-max-frame-size 65536`; README/project-context/runbook misollari,
  deploy artifact va runtime readback; `0` (unlimited) taqiqlanadi;
- applicationda JSON/command 64 KiB, text 4 000 code point/16 KiB va binary
  frame explicit reject — edge cap domain validationni almashtirmaydi;
- session key validity va auth hash bounded interval/har commandda tekshiriladi;
- logout, password change, session delete va user deactivate ochiq socketni
  keyingi command/eventda `4403` bilan yopadi;
- unknown route ID/invalid UUID non-enumerable;
- application heartbeat 30s, idle deadline 90s; authenticated user uchun barcha
  Messenger/Classbook tab/device bo‘yicha distributed provisional maksimum 6
  concurrent socket va har-process local accounting. 1–6 tab ishlaydi, 7-socket
  typed temporary reject/close oladi; setting audited safe range ichida
  kalibrlanadi. Distributed admission cache unavailable bo‘lsa **yangi** socket
  fail-closed `1013`, mavjud socketlar local cap/session guard bilan davom etadi
  va UI HTTP fallbackni ko‘rsatadi — hammasini birdan uzmaydi;
- max frame va command limit;
- origin/rate/access reject body-free security event.

### 9.2 Authorization matrix

Har action uchun:

| Action | Learner | Assigned instructor | Support/owner | System |
|---|---|---|---|---|
| list/read room | own active membership/visibility | own course scope | assigned purpose; D13 admitted bo‘lsa break-glass audited | explicit worker scope |
| send human | active, room writable | active assignment | assigned room | no |
| edit/delete own | window/version/policy | ayni | moderation service | no direct admin |
| mark read/mute/pin | own membership only | own membership | own membership | no |
| search | visible non-deleted projection | scoped | metadata; body faqat D13-admitted break-glass | no general search |
| AI request | private AI room/quota | learner nomidan emas | explicit support tool alohida | claimed run only |
| attachment | same room + visibility | same | assigned/audited | claimed processor |

`participants` M2M, `is_staff` yoki frontend button authorization emas. Server
har command, attachment stream, search result, event delivery va delayed workerda
policy chaqiradi.

Jadvaldagi “System” login user yoki `ChatMembership.role` emas; stable
operationga bog‘langan named worker/service scope. Synthetic superuser yaratish
taqiqlanadi.

### 9.3 Backoffice privacy

Default dashboard:

- counts, room type, scoped course/cohort, last activity, unanswered age;
- message body/last snippet/email qidiruvi yo‘q;
- assigned teacher faqat own course rooms;
- owner support faqat assigned support rooms.

Break-glass — faqat MSG-D13 `ADMIT` bo‘lsa; `DENY`da quyidagi route/control
yaratilmaydi va owner body access0:

- owner-only named permission;
- reason va ticket/purpose majburiy;
- short expiry, exact room scope;
- view/search/download har biri audit;
- UI visible banner;
- export va bulk body search defaultda yo‘q.

Authenticated legacy/V1/backoffice va canonical Inbox/room/history/search/
receipt/event/user-event/inbox-snapshot/deep-link HTML/JSON response, redirect va
auth/error variantlari `Cache-Control: private, no-store`, `Vary: Cookie` va
appropriate `Referrer-Policy`; shared CDN/proxy cache bypass. Authorized media
o‘zining private/no-store/nosniff policy’sida. Search/preview indexlanmaydi;
sensitive search query POST bodyda, URL/browser history/referrer/access logda
emas.

### 9.4 Upload security

- extension + signature/sniffed kind + size + permission;
- allowed type list use-case bo‘yicha: human attachment va AI-readable type
  alohida;
- generated storage key, private root va authorized stream saqlanadi;
- image dimension/pixel cap; PDF page/byte/parser timeout; archive/Office
  container bomb va macro policy;
- scanner/CDR mavjud bo‘lmasa “scanned/safe” da’vo qilinmaydi; risky parsing
  disabled yoki sandbox;
- upload/user/day va room storage quota;
- temporary/pending object expiry va orphan dry-run;
- CSP/nosniff/content-disposition;
- original filename log/notification/URLga chiqmaydi.

### 9.5 Retention va data-subject amallari

Owner/legal MSG-D3 matrixi:

| Data | Qaror kerak | Default qarorgacha |
|---|---|---|
| human message body | active/closed course retention | cheksiz yangi nusxa yo‘q; current data destructive purge yo‘q |
| AI prompt/output/run | product support va eval retention | raw log/export yo‘q |
| attachment/object/derived extract | delete/purge/legal hold | tombstone + authorized storage; dry-run audit |
| revisions/moderation | evidence muddati | minimal metadata/hash |
| receipts/chat event delivery/Notification/TelegramOutbox/security log | reconciliation/incident muddati | body-free bounded record; generic copy yoki safe refs only |
| memory/embedding/summary | user clear/account delete graph | explicit linked dry-run |

Receipt/outbox/delivery/dead-letter persisted payloadi faqat operation/object
ID, version, cursor, audience selector va safe code; text/body/prompt/excerpt/
filename/URL/email yo‘q. Publisher canonical objectni fresh policy bilan
project qiladi. Delete/purge acceptance testi barcha pending/published/dead
event rowlarida old body yoki filename nusxasi qolmaganini tekshiradi.

Purge/anonymize command default `--dry-run`, batch/resume, legal-hold skip,
count/hash va rerun idempotency beradi. Account delete author/historyni jim
CASCADE qilmaydi; pseudonymization yoki explicit policy.

### 9.6 Accessibility

- initial transcript `aria-live=off`, load tugagach `role=log`; yangi message
  sender + qisqa matn bilan polite, edit/read eventlar keraksiz announce emas;
- connection/save/reconnect `role=status`; revoke/irrecoverable `role=alert`;
- incoming event focus/scrollni tortmaydi; user bottomda bo‘lmasa “N ta yangi”
  tugmasi;
- older page prepend ko‘rinadigan anchor/focusni saqlaydi;
- room list va transcript headings/landmarks; selected room programmatic;
- unread/status icon, rang va matn;
- Enter newline; Ctrl/Cmd+Enter send; explicit button; IME composition submit0;
- dialog/menu focus trap/restore va Escape;
- 24×24 WCAG minimum, primary control 44×44 target;
- 320px/400%, 200% text, text spacing, forced colors, dark/light, reduced motion;
- virtual keyboard/safe area/composer, landscape va long Uzbek/Turkish strings;
- no-JS latest history, pagination, send va validation/PRG.

Native acceptance: NVDA+Firefox/Chrome, VoiceOver+iOS Safari va TalkBack+Android
Chrome. Automated axe/unit dalili buning o‘rnini bosmaydi.

### 9.7 Performance va capacity budgets

- first inbox 50 room; keyset pagination; ≤10 fixed DB query target;
- first history 50 message; older/gap bounded 100;
- 5 000-message fixture full table/DOM load qilmaydi;
- DOM window target ≤300 row; event append/patch, full `replaceChildren` emas;
- composer local feedback ≤100 ms;
- staging human command receipt p95 ≤500 ms; event visible p95 ≤2 s;
- reconnect gap convergence p95 ≤2 s;
- uploadga umumiy 20s timeout emas: progress, cancel va server limits;
- 20 parallel same-nonce PostgreSQL → 1 message/receipt/outbox;
- 100 active socket fanout/gap test; slow consumer backpressure;
- Redis/channel outage Message durabilityni yo‘qotmaydi;
- AI/provider latency human receiptni bloklamaydi.

Bu targetlar production-like fixture va p75/p95 telemetry bilan. Local empty DB
Lighthouse yoki bitta request production dalili emas.

### 9.8 Observability va alertlar

Body-free metriclar:

- command accepted/rejected/unknown/conflict/rate-limit;
- receipt p50/p95/p99 va transport bo‘yicha;
- duplicate prevented va idempotency conflict;
- event outbox oldest age/pending/dead/attempt;
- socket connect/close code/origin/access/session reject;
- message-sequence va event-cursor gap, resync latency/failure;
- unread reconciliation drift;
- membership/room anomaly;
- Telegram outbox age/dead/privacy mode;
- AI pending/running age, lease expiry, provider call/result/quota/cancel;
- attachment pending/rejected/orphan/purge due;
- backoffice break-glass use va moderation queue age.

Alert thresholds runbookda environment baseline bilan. Log correlation ID,
room/message public ID yoki hashed internal ref bilan; raw body/prompt/output,
token, email, attachment filename va signed URL yo‘q.

### 9.9 Reconciliation va owner health

Idempotent commands:

- `audit_messenger --dry-run`;
- `reconcile_messenger_memberships --dry-run`;
- `reconcile_messenger_sequences --dry-run`;
- `replay_chat_event_outbox --dry-run`;
- `audit_chat_attachments --dry-run`;
- `reconcile_ai_runs --dry-run`;
- retention qaroridan keyin `purge_messenger_data --dry-run`.

Owner health card faqat aggregated counts/oldest age va exact safe deep link.
GET health canonical data yaratmaydi, outboxni claim qilmaydi yoki anomaly’ni
avtomatik “tuzatdim” demaydi.

---

## 10. Roadmap — dependency tartibidagi reviewable kesimlar

Har `MSGx.yz` alohida PR chegarasi. Bir PRda “schema + barcha writerlar +
to‘liq UI + AI” yo‘q. Oldingi slice DoD’i va review topilmasi yopilmasdan
keyingi consumerga o‘tilmaydi.

Har slice PR tavsifida:

- base/final commit, migration, flag va setting;
- touched canonical service va barcha adapterlar;
- safe-env exact test outputi va backend;
- security/privacy/rollback ta’siri;
- “code merged / flag ON / deployed / owner accepted” holatlari alohida;
- keyingi exact slice yoziladi.

### MSG1.0 — containment va bugungi haqiqat

#### MSG1.0a1 — birinchi kesim: Origin va ASGI transport ceiling

**Dependency:** yo‘q; security maintenance. Baseline `84720ca`.

**Ish:**

1. `WEBSOCKET_ALLOWED_ORIGINS`ni scheme+hostli dedicated env setting qilish;
   `ALLOWED_HOSTS`dan derive qilmaslik, `*`/path/query/credentialni config
   checkda rad etish.
2. [ASGI](../../core/asgi.py) websocket branchini Channels matching/deny
   semantikasini saqlaydigan audited
   `BodyFreeOriginValidator(AuthMiddlewareStack(URLRouter(...)),
   allowed_origins)` outer wrapperi bilan o‘rash; HTTP branch o‘zgarmaydi.
3. `core/settings.py`da
   `DAPHNE_WEBSOCKET_MAX_MESSAGE_SIZE=65536` va
   `DAPHNE_WEBSOCKET_MAX_FRAME_SIZE=65536` immutable hard ceiling; bu primary
   local `manage.py runserver`ni ham Daphne 1 MiB defaultidan tushiradi.
4. [`Dockerfile`](../../Dockerfile),
   [`deploy/docker-compose.prod.yml`](../../deploy/docker-compose.prod.yml) va
   [`Procfile`](../../Procfile) Daphne commandlariga
   `--websocket-max-message-size 65536` va
   `--websocket-max-frame-size 65536`; `0`/missing qiymat deploy testida FAIL.
   Root [`README.md`](../../README.md) L86dagi manual Daphne misolini ham capli
   argvga almashtirish; agar Procfile amalda dormant bo‘lsa ham cap bilan safe
   saqlash yoki alohida decommission PRda olib tashlash — nazoratsiz qoldirmaslik.
5. Messenger va Classbook valid socket compatibility; foreign/`null`/missing
   Origin connectdan oldin rad.
6. Mobile QA LAN/ngrok uchun wildcard emas, exact
   `WEBSOCKET_ALLOWED_ORIGINS=http://<LAN-IP>:8000` yoki
   `https://<ngrok-host>`ni CSRF origin bilan birga runbookda talab qilish.
7. Origin/config reject body/token/cookie’siz structured security outcome.

**Tegiladigan joylar:** `core/settings.py`, `core/asgi.py`, `Dockerfile`,
`deploy/docker-compose.prod.yml`, `Procfile`, root `README.md`,
`nuclear-program/project-context.md`, `nuclear-program/mobile-qa-runbook.md`,
`deploy/README.md`, `deploy/env.example`, deploy artifact/system check va
Messenger/Classbook socket testlari.

**Test:** allowed production/local/test scheme+host; foreign/`null`/missing/
malformed/wildcard; reverse-proxy HTTPS; Messenger va Classbook connect;
LAN/ngrok exact origin; settings va `manage.py runserver` ikkala 65 536 capni
olishi; Dockerfile/compose/Procfile uchalasida exact argv/readback,
README/project-context/mobile/deploy runbook safe commandi; har origin reject
uchun stable safe reason, secret/body/origin-value log0.

**Tugashi:** cross-site cookie socket yopiq; CLI va `manage.py runserver` ASGI
processlari 65 536 bytedan katta frame/message’ni consumerdan oldin qabul
qilmaydi; ikkala socket family valid origin, LAN va ngrok exact config bilan
regressiyasiz.

**Rollback:** guard flag ortida emas. Config xatosida explicit verified origin
ro‘yxati tuzatiladi; `ALLOWED_HOSTS=*`, validatorni olib tashlash yoki Daphne
limitini `0` qilish rollback emas.

#### MSG1.0a2 — Messenger schema, binary va content boundary

**Dependency:** MSG1.0a1.

**Ish:** legacy-compatible allowlist parser: JSON object, known V1/V2 action,
required/unknown field policy, application 64 KiB, human text ≤4 000 code point
va ≤16 KiB, bounded IDs/skill. Current legacy payloadda `action` yo‘q va
`Date.now()-random` opaque ID bor: missing action faqat exact legacy shape’da
`message.send.v1`ga map qilinadi; V1 `action='message'` saqlanadi. Binary frame
stable error/close bilan rad. Barcha rejectlarda DB/provider/notification 0 va
body-free metric. WebSocket bo‘lmagan Messenger command/search/read/edit/delete/
preference kabi **non-upload** POSTlar uchun exact path allowlistli outer ASGI
receive limiter va Caddy defense-in-depth: `Content-Length > 65536`ni body
bufferdan oldin `413`, missing/chunked/forged-short lengthni cumulative 65 536
byte streaming cap bilan. Upload init/chunk/finalize exact alohida route va o‘z
MSG1.5 size limiterida; global katta upload limiti commandga meros bo‘lmaydi.

**Tegiladigan joylar:** `core/asgi.py`dagi exact-path bounded HTTP body wrapper,
`deploy/Caddyfile`, `messenger/consumers.py`, `messenger/routing.py`, URL registry,
yangi kichik `messenger/protocol.py` yoki `validation.py`, legacy/V1 JS contract
fixtures, HTTP va socket tests.

**Test:** current actionless legacy payload + opaque ID, V1 action payload,
future V2 envelope; unknown action, array/scalar/malformed JSON, binary frame,
oversize frame/text, Unicode/emoji byte boundary, ID/field overflow va unknown
field. Non-upload HTTPda 65 536/65 537, huge declared length, chunked/no-length,
forged-short length va upload-route exclusion; har rad holatida effect0/log
body0.

**Tugashi:** current legacy va V1 valid send ishlaydi; malformed/binary/oversize
command effect0; parser contract versionlangan.

**Rollback:** compatibility projection saqlanishi mumkin; server/content cap va
unknown/binary deny olib tashlanmaydi.

#### MSG1.0a3 — rate limit va live-session revoke

**Dependency:** MSG1.0a2 parser va MSG1.0a1 security logging.

**Ish:** raw frame kelishi bilan JSON decode/binary rejectdan oldin cheap local
per-connection token consume. Keyin Messenger va Classbook cookie-auth
consumerlari ishlatadigan shared fresh session-key/auth-hash/user-active helper
va distributed per-user transport bucket; logout/password/session delete keyingi
command **yoki outbound event** boundaryda `4403`. Har ikki transport bucket
barcha binary, malformed,
valid command va replayga 30/10s va 180/minute, receipt/command DB ishidan
oldin. Current per-user+room human mutation limiter 10/10s va 60/minute,
bounded `retry_after_ms`; AI quota alohida. Bu containment
slice’da persisted receipt/payload hash hali yo‘q: temporary cache receipt
qurilmaydi va ACK-loss replayni mutation rate’dan chiqarish da’vo qilinmaydi.
Target order: Daphne cap → raw-frame local bucket → fresh auth/session +
distributed user bucket → decode/schema → scope → receipt key/hash lookup →
faqat yangi operation mutation limiteri — MSG1.2b canonical writerda atomik.
Distributed cache unavailable bo‘lsa current write fail-closed
`temporary_transport_failure`, local transport bucket/ping/close va HTTP
read/history qoladi; DB lookupka fail-open yo‘q.

Socket admission ham shu kesimda: user bo‘yicha Messenger+Classbook jami
provisional 6 concurrent socket. Distributed connection lease har process/tab
uchun unique va expiryli; orderly close/reaper countni bo‘shatadi. Cache
unavailable bo‘lsa yangi socket `1013` bilan fail-closed, mavjud socketlar local
cap/fresh-session guard bilan ishlashda davom etadi va client HTTP fallbackga
o‘tadi. 30s heartbeat/90s idle/slow-consumer enforcement current legacy/V1 va
Classbook clientlari heartbeat compatibility olmaguncha yoqilmaydi; u MSG1.2cda
barcha current clientlar bilan atomik chiqadi. Multi-tabning o‘zi online/
presence yoki delivered receipt deb talqin qilinmaydi.

**Tegiladigan joylar:** shared core realtime-session/connection-lease guard,
Messenger consumer/access, `classbook/consumers.py`, canonical rate helper/config,
protocol error mapper va ikkala socket family tests.

**Test:** transport va mutation burst/window/multi-room/multi-user; 10 000
same-key/replay/conflict frame → bounded DB work; 10 000 malformed JSON va
binary frame decode/log loopini chetlab o‘tmay limiter/closega tushadi; cache
outage write0; Messenger va Classbookda logout/password/session delete/inactive
user command/event close; delivery revoke; secret/body log0.
Persisted replay/conflict/non-poisoning testlari ataylab MSG1.2b acceptance’iga
yoziladi. 1–6 parallel tab/device accepted, 7-si typed reject, close/expiry slotni
bo‘shatadi; ikki processdagi aggregate cap va cache outage paytida existing
socket saqlanib new admission0. Heartbeat/idle testi bu slice’da ataylab deferred
va config enforcement0.

**Tugashi:** flood va revoked session Messenger/Classbook write/event/provider/
notification0; valid user bounded traffic ishlaydi. Persisted idempotent replay guarantee MSG1.2bga
ochiq va aniq deferred.

**Rollback:** rate qiymati audited safe range’da kalibrlanishi mumkin; session
revoke va fail-closed abuse boundary olib tashlanmaydi.

#### MSG1.0b — AI privacy/access containment

**Dependency:** MSG1.0a2 parser va MSG1.0a3 fresh-session/access logging.

**Ish:**

1. group **va tutor/private/support kabi barcha non-AI human roomlarda**
   `@azure` trigger/UI claimini OFF; worker admission helperining o‘zi current
   `room.room_type != 'ai'`ni (keyingi `kind != ai_private` bilan compatibility)
   `messenger_ai_shared_room=OFF`da deny qiladi. Shuning uchun pre-upgrade
   serialized/old-signature queued task ham provider/memory/outputga o‘tmaydi;
   provider call0; existing non-AI room AI outputlari uchun body-free audit va
   suspected-private row quarantine.
2. AI worker claim/provider/write oldidan fresh room/user/context/access version.
3. staff RAG scope `teacher_course_queryset` va canonical lesson accessdan;
   no course scope = empty.
4. WebSocket, upload, widget va bound Telegramning har biri bitta containment
   admission helperdan o‘tadi; adapter-specific bypass yo‘q.
5. `supports_vision=False`da image analysis CTA/auto-prompt/claim 0.
6. raw provider exception user event/historyga emas, stable safe code.
7. broker dispatch exceptionida direct `.run()`/daemon provider fallback yo‘q;
   pending run visible va reconcilerga.
8. `Capability.AI_TUTOR` enforcement outcome **MSG-D4**ga bog‘liq: bu slice
   entitlement semanticsini jim o‘zgartirmaydi. Qarorgacha barcha adapterlar
   ayni existing policy + quota/A8 gate’dan o‘tadi va body-free shadow denial
   count beradi; typed entitlement cutover MSG1.6a’da.

**Tegiladigan joylar:** `messenger/consumers.py`, `signals.py`, `tasks.py`,
`access.py`, `rag.py`, `messenger/views.py`dagi upload/widget,
`bot/services.py`dagi bound Telegram, AI builder/provider capability projection,
V1 AI UI va tests. Inventar `rg` bilan barcha `.run()`, daemon/thread,
`Message.objects.create` va provider dispatch call sitelarini qamraydi.

**Test:**

- group yoki tutor/private human room mentioni → ordinary message,
  provider/run/memory query0;
- pre-upgrade serialized old-signature group **va private-direct**
  `generate_ai_response` yangi workerda → terminal cancelled safe audit yoki
  no-op; new run/provider/memory/output Message0;
- active→revoked before worker, before write va late result;
- assigned/unassigned staff course, locked lesson, enrollment states;
- WebSocket/upload/widget/Telegramda ayni fresh access va capability natijasi;
- vision false image upload, PDF allowed/denied type;
- provider/broker timeout raw text leak0; hech bir adapter sync `.run()` yoki
  daemon fallback bilan providerga ketmaydi.

**Tugashi:** group/tutor/support kabi non-AI shared roomga private memory/
progress chiqish yo‘li yopiq; revoke
provider gate’idan oldin bo‘lsa barcha adapterda provider call0; foreign-scope
context0; supported private AI foundation ishlaydi. D4 unresolved bo‘lsa bu
holat ochiq decision sifatida qoladi, “entitlement yopildi” deyilmaydi.

**Rollback:** private AI renderer eski I4b projectionga qaytishi mumkin, lekin
group AI OFF, fresh access, existing quota/A8 va error-redaction gate’i qoladi;
D4 hal bo‘lmagan typed entitlement enforcementi bajarildi deb aytilmaydi.

#### MSG1.0c — Telegram privacy containment va unsafe senderni yopish

**Dependency:** MSG1.0b direct fallback olib tashlangan.

**Ish:**

- direct `send_telegram_notification` HTTP yo‘lini call sitelardan uzish;
- legacy task entrypointning o‘zi fail-closed no-op/tombstone bo‘ladi: deploydan
  oldin queue drain isbotlanmagan bo‘lsa pre-upgrade serialized Celery job yangi
  workerda bajarilganda ham Telegram network/body egress0;
- Messenger→Telegram remote deliveryni canonical transactional intent hali
  yo‘qligi sabab explicit `paused` holatga tushirish; history/send ishlaydi;
- UI/owner health’da “Telegram xabarnomasi vaqtincha pauzada”ni truthful
  ko‘rsatish, jim success bermaslik;
- keyingi final contract uchun additive `Notification.CATEGORY_MESSENGER`,
  faqat typed room/message reference + generic copy va fresh-accessdan keyingi
  authenticated relative deep-link formatterini side-effect’siz tayyorlash;
  raw body/filename/AI output saqlamaslik, generic `system`ga yashirin
  aralashtirmaslik;
- current message commitdan keyingi Celery `.delay()`/direct HTTP yo‘lini
  “durable retry” deb atamaslik; deterministic external key dedupe bo‘lishi
  mumkin, ammo retry manbai emasligini test/hujjatda qotirish.

**Tegiladigan joylar:** `messenger/tasks.py`/`signals.py`, feature/settings
registry, owner health/UI, `users/models.py`/choices migration, privacy-safe
formatter va tests. `bot/outbox.py` senderi bu kesimda qayta yozilmaydi.

**Test:** human/AI message send ishlaydi, Messenger direct HTTP/Celery
notification dispatch0, Telegram network0, raw body/token log0, paused holat
truthful; `external_key`ning o‘zi message-commit failure recovery emasligini
characterization bilan qotirish; pre-upgrade serialized
`send_telegram_notification` taskini post-upgrade worker bajarsa no-op/network0.

**Tugashi:** Messenger runtime’dan direct Bot API `requests.post` call0 va raw
body egress0. Telegram delivery vaqtincha, ko‘rinadigan tarzda paused; exactly
one durable intent/outbox, at-least-once external delivery va dead-letter
**MSG1.2c + MSG1.7a’gacha yopildi deyilmaydi**.

**Rollback:** human Messenger/history ishlaydi; notification pause qoladi.
Direct HTTP eski task qayta yoqilmaydi.

#### MSG1.0d — backoffice va authenticated cache privacy

**Dependency:** yo‘q; MSG1.0a1–a3 bilan shared file code-touch bo‘lmasa.

**Ish:**

- generic staff global room/body/email searchini yopish;
- instructor uchun canonical course scope;
- owner/supportga metadata-first list;
- transcript/body/snippet default hech kimga global emas. Owner-only temporary
  break-glass faqat MSG-D13 tasdiqlansa reason/expiry/`SystemAuditEvent` bilan;
  qaror bo‘lmasa metadata-only va body access0;
- Django `/admin/` ham ayni policy chegarasi: `MessageInline` orqali create/edit,
  Message text qidiruvi/change formi, `AIResponseRun.user_question/error_message`
  va memory value/prompt/body fieldlari defaultda olib tashlanadi yoki
  metadata-only read-only projectionga aylanadi. D13 admitted bo‘lsa ham generic
  superuser bypass emas, ayni reason+exact scope+expiry+audit gate ishlaydi;
- legacy/V1/backoffice va canonical Inbox/history/search/receipt/event/user-
  event/snapshot/deep-link HTML/JSON/redirect/error responsega private/no-store,
  `Vary: Cookie`, noindex/referrer/proxy policy;
- attachment/open/searchning exact audit contracti.

**Tegiladigan joylar:** `core/access.py`, `core/views.py`,
`templates/backoffice/chats.html`, `messenger/admin.py` hamda tegishli AI/memory
admin registratsiyalari, Messenger policy/audit helper, legacy/V1 response mixin
va tests.

**Test:** ordinary staff, assigned/unassigned instructor; D13 bo‘lmasa owner
body access0; D13 qabul qilinsa owner no-reason/valid/expired break-glass;
Django admin changelist/search/change/add/inline va direct admin URLlarda body/
prompt/error/memory value leak/write0; room list/body search/snippet/download;
HTML/JSON/redirect/error/cache-hit matrixida private/no-store/Vary, canary search
string URL/referrer/proxy/app log0; audit failure rollback.

**Tugashi:** broad `is_staff` body access0; teacher foreign course leak0.
Break-glass admitted bo‘lsa reason/auditli, admitted bo‘lmasa umuman yo‘q; bu
safe containmentni bloklamaydi.

**Rollback:** metadata UI eski layoutga qaytishi mumkin; least-privilege policy,
body-search default OFF va no-store saqlanadi.

#### MSG1.0e — legacy/default truth va history hotfix

**Dependency:** MSG1.0a2 input contract.

**Ish:**

- legacy transcript eng so‘nggi 100ni stable orderda ko‘rsatishi;
- sidebar ruxsatli human roomsni yashirmasligi;
- doimiy “Onlayn”, isbotsiz double-check va nonexistent `updated_at` copy’ni
  olib tashlash;
- GET read markerini vaqtincha explicit POST/at least successful visible-history
  compatibility actionga ajratish; yangi canonical sequence MSG1.2d’da;
- locked/empty holatda aniq reason va safe support/dashboard CTA;
- current V1 behavior regressiyasini saqlash.

**Tegiladigan joylar:** `messenger/views.py`, legacy templates/JS/CSS,
`messenger/urls.py` va characterization tests.

**Test:** 0/1/100/101/1000 xabar, equal timestamp, all room types, multiple
groups/direct rooms, JS fail, V1 flag ON/OFF; GET row/write count; false
presence/receipt copy snapshot.

**Tugashi:** flag OFF/rollback ham latest conversationni ko‘rsatadi; xona
yashirmaydi; mavjud bo‘lmagan online/read da’vosi0; plain GET unreadni
tozalamaydi.

**Rollback:** template visual rollback safe projectionga; oldest-100/false-read/
false-status bug qayta ochilmaydi.

### MSG1.1 — data audit, identity va additive schema

#### MSG1.1a — read-only integrity auditor

**Dependency:** MSG1.0 hotfixlar; migration yo‘q.

**Ish:** `audit_messenger --dry-run --json-output`:

- duplicate group/private candidate; AI’da faqat bitta learnerning duplicate
  **empty draft**lari yoki ayni stable conversation/SmartForm source identity
  collisioni candidate. Bir learnerning bir nechta nonempty active topical AI
  conversationi valid va merge/quarantine candidate emas;
- invalid room type/subject/cohort;
- missing/extra/stale participant va wrong tutor;
- ambiguous private name/superuser mapping;
- attachment missing/orphan/kind mismatch;
- message order/nonce/sequence backfill hajmi;
- AI run/message mismatch/stuck state;
- current unread/state anomaly.

Default dry-run; repair0. Output body/email/filename emas, internal ID/count va
safe reason code. Production data olish owner deploy/ops qarori bilan.

**Fayllar:** yangi management command, selectors/audit dataclass, tests, runbook.

**Test:** clean, har anomaly fixture, bir learnerda ikki nonempty AI conversation
valid/not-candidate, duplicate empty draft va same SmartForm identity candidate;
10k fixture query/memory bound, JSON determinism, rerun DB write0, foreign PII
output0.

**Tugashi:** migration oldi count/quarantine format va owner resolution checklist
tayyor; local fixture report archive qilinadi, production deb ko‘rsatilmaydi.

**Rollback:** commandni olib tashlash mumkin; data mutation bo‘lmagan.

#### MSG1.1b — room va membership expand schema

**Dependency:** MSG1.1a report; MSG-D1/MSG-D2 qaroridan mustaqil nullable
foundation, ammo direct unique enforce qarordan keyin; AI draft/conversation
constrainti MSG-D14 resolved bo‘lmaguncha enforce qilinmaydi va slice accepted
hisoblanmaydi.

**Ish:** `ChatRoom.public_id/kind/status/subject/next_sequence/
next_event_cursor/last_message/access_version`; `ChatMembership` va append-only
tenure identity/history hamda yuqoridagi bounded lifecycle fieldli
`ChatMembershipTenure`; bu slice tenureda faqat nullable raw join/close operation
UUIDlarini yaratadi, join/close receipt FKlari MSG1.1dga deferred;
`MessengerRuntimeInstanceLease(release_sha, manifest_hash, role, instance_id,
supported_membership_epoch, supported_writer_epoch, supported_schema_epoch,
supported_event_epoch, lease_expires_at)` unique `(role, instance_id)`;
index/check/conditional unique
mumkin bo‘lganlari; no destructive rename/drop. Bu per-replica lease mavjud
global-name-unique `aicontrol.WorkerHeartbeat`ni qayta ishlatmaydi.

**Fayllar:** `messenger/models.py`, 0016+ kichik migrations, admin read-only
projection, migration tests.

**Test:** empty/legacy DB migrate, reverse schema rehearsal nusxada, UUID unique,
room-kind check, duplicate group/AI draft concurrency PostgreSQL, leave→rejoin
non-contiguous tenure constraint, FK deletion, bir role’ning ikki replica lease’i
va stale expiry; existing `WorkerHeartbeat`ga collision0; `makemigrations --check`.

**Tugashi:** existing URLs/M2M/readers ishlaydi; yangi schema bo‘sh/nullable
safe; invalid newly-created group/AI DBda rad.

**Rollback:** application old fieldsdan o‘qiydi; expand tables/columns data
saqlab qoladi, emergencyda migration down faqat empty pilot DBda sinovli.

#### MSG1.1c — membership backfill va shadow projection

**Dependency:** MSG1.1b; MSG-D1/MSG-D2/MSG-D14; audit report; ambiguous rowlar
uchun owner mapping yoki quarantine policy.

**Ish:** resumable command:

- exact cohort enrollment + `Course.instructor` membership;
- AI learner + explicit conversation/SmartForm source identity; faqat duplicate
  empty draft yoki ayni stable source collisioni quarantine candidate, bir
  learnerning nonempty topical conversationlari hech qachon learner IDning o‘zi
  bilan merge qilinmaydi;
- current participants/state → role/source va deterministic initial tenure;
- legacy `ChatRoomUserState.last_read_at` va global `Message.is_read` faqat
  body-free migration input/anomaly sifatida inventar qilinadi; sequence hali
  backfill bo‘lmagani uchun bu slice read watermarkni taxminan surmaydi — exact
  conservative mapping MSG1.2d’da;
- historical leave/rejoin isbotlanmasa intervalni kengaytirmaslik; ambiguous
  gap quarantine;
- ambiguous private row quarantine, silent reassignment0;
- old/new access/inbox projection diff;
- compatibility service M2M/state projection dual-write.

**Test:** rerun idempotent, batch/resume/crash, instructor transfer, enrollment
start/end, duplicate empty AI draft/same SmartForm identity, multiple nonempty AI
conversations preserved, ambiguity, empty user/cohort, legacy read-state
inventory count/hash; SQLite/PostgreSQL.

**Tugashi:** non-quarantined rowlar old accessni kengaytirmasdan canonical
membership oladi; difference report tushuntirilgan; enforce hali OFF.

**Rollback:** readers old M2Mda; backfill rows saqlanadi/ignored; delete rollback
emas.

#### MSG1.1d — message/receipt/event expand va sequence rehearsal

**Dependency:** MSG1.1b room identity.

**Ish:** `MessengerActorSubject` one-to-one/opaque lifecycle substrate; Message
UUID/nullable sequence/bounded opaque client ID/hash/kind/
version/idempotency-origin; nullable forward `Message.operation_receipt`
OneToOne (legacy marker istisnosi bilan) va tenure raw operation UUIDlari uchun
nullable canonical join/close receipt FK/additive validation; event outbox/event cursor,
`MessengerEventTransportRoute`, `MessengerUserStream` va user-scoped
`MessengerUserEvent`/fanout-delivery/user cursor;
revision/attachment minimal substrate; indexes va
conditional constraints non-null rowlarda.

Backfill dry-run deterministic `created_at,id` order, duplicate/null report.
Live cutover hali yo‘q.

**Test:** migrate legacy attachment/AI/system/null-sender messages without
accepted operation invention; reserved legacy ID/hash/origin rerun/collision;
equal timestamp; UUID/nonce constraints; receipt hash; transport route default;
room/user event uniqueness, outbox transport generation, logical user-event vs
fanout-delivery constraints; body-free outbox/delivery serializer;
parallel first-operation actor subject create bitta row/ref, subject ref account
ID/email/hashdan derive0, recreated account old subjectga relink0;
index query plans;
PostgreSQL parallel row lock prototype.

**Tugashi:** old writer ishlaydi, yangi columnlar safe nullable; full backfill
hajmi/count/hash ma’lum; app read behavior o‘zgarmagan.

**Rollback:** old model projection; yangi rows drop qilinmaydi.

### MSG1.2 — canonical policy, writer va realtime correctness

#### MSG1.2a — room provisioning va yagona policy

**Dependency:** MSG1.1b–d; MSG-D1/MSG-D2/MSG-D12/MSG-D14.

**Ish:**

- `MessengerPolicy` action matrix;
- atomic group/AI/direct/support get-or-create;
- enrollment/instructor lifecycle hook yoki explicit reconciliation;
- GETdan membership/state creationni chiqarish;
- instructor handoff/visibility va room close/read-only transition;
- admin direct participant mutation read-only/audited service;
- membership compatibility dual-write/shadow compare va provisional
  `ChatMembershipTenure` boundary evidence. Faqat one-way
  `NULL → exact`/state-forward lifecycle ruxsat; non-null boundary rewrite0.
  Bu slice canonical access receiptini hali
  **yozmaydi**: exact `visible_from_sequence/event_cursor` MSG1.2b sequence va
  MSG1.2c event baseline’dan oldin xavfsiz emas. Ambiguous boundary quarantine;
- membership cutover receipt schema/checklist + minimum membership/schema epoch
  guard/readinessni tayyorlash; real receipt/authority switch MSG1.2c oxiridagi
  coordinated gate;
- `deploy/messenger-runtime-epochs.json`, post-migrate
  `check_messenger_epoch`, per-instance lease register/renew va
  membership-service entry guardning base implementationi; import/AppConfig DB
  query0, `/healthz` liveness va `/readyz` readiness ajratilgan.

**Fayllar:** yangi `messenger/policy.py`/`services.py` yoki service package,
`access.py`, `views.py`, enrollment/course signals/service adapter, runtime epoch
model/guard/management command, `deploy/messenger-runtime-epochs.json`,
`deploy/docker-compose.prod.yml`, `deploy/Caddyfile`, `deploy/README.md`, root
`Dockerfile`, `Procfile` yoki shared production entrypoint, trusted deploy
controller/preflight, Control Center readiness/snapshot, admin/tests.

**Test:** all roles/states, concurrent provision, instructor transfer,
leave→rejoin, revoke→restore va suspend→resume yangi tenure; har absence
intervalidagi history/message/event/unread/fanout leak0, provisional join/paytdagi
concurrent legacy send exact later mapping yoki
quarantine, close transaction failureda membership/upper-bound/receipt atomik0;
state_version stale lifecycle mutation 409/effect0; receipt unissued/canonical
authority OFF; GET write0, old/new parity, simulated old
runtime epoch fail-closed, empty/pre-receipt migrate/collectstatic, two replicas
same role/stale lease, liveness/readiness/prestart/service-entry separation;
missing/mismatched image label, `SOURCE_VERSION`, manifest yoki wrapper command
start0; old candidate `/readyz=200` bo'lsa ham traffic0 va direct eski
`docker compose up` bypass0; no broad staff default.

**Tugashi:** supported room/membership mutation service orqali compatibility
dual-write; new tutor exact course instructor; no duplicate canonical room; GET
sync0; shadow evidence tayyor, ammo sequence/event boundarysiz membership
receipt va authority switch0.

**Rollback:** bu kesimda receipt hali yo‘q, routing flag old read projectionga
qaytishi mumkin; canonical shadow rows saqlanadi. MSG1.2c coordinated
receipt’dan keyin flag/config failure canonical accessni pause/read-only qiladi,
eski M2Mni authority qilmaydi. Yangi unsafe direct writer qayta ochilmaydi.

#### MSG1.2b — canonical message writer va durable receipt

**Dependency:** MSG1.0b, MSG1.1d, MSG1.2a.

**Ish:**

- `send_message` atomic service: policy, validation, room lock, nonce/hash,
  message sequence, message, receipt va event cursor/outbox; sender read
  watermarkini avtomatik surmaydi;
- accessdan keyin existing nonce/hash lookup rate limitdan oldin; same replay
  existing receipt, conflict stable; faqat yangi operation mutation budget
  yeydi. Cheap transport bucket esa DB lookupdan oldin barcha replay/conflictni
  hisoblaydi;
- retryable rate/cache/transport pre-accept failure durable rejection receipt
  yaratmaydi;
- HTTP POST/no-JS adapter;
- current WebSocket adapter shu service;
- widget/upload/Telegram human adapterlari shu servicega;
- trusted `send_ai_message`/`send_system_message` compatibility entrylari:
  `messenger/tasks.py`dagi quota-block/supply-block/success, onboarding
  `users/views.py`, admin/system va boshqa runtime writerlar named service actor
  scope + stable operation bilan canonical sequence/receipt/outboxdan o‘tadi;
  bu kesim AI orchestration semanticsini o‘zgartirmaydi;
- runtime `Message.objects.create` va `ChatRoom.objects.create` call-site
  inventory/allowlist: migrations/test factorydan tashqari Message writer shu
  service, room writer MSG1.2a provisioning service; zero-inventory dalilisiz
  global receipt berilmaydi;
- signal-based hidden send effectini olib tashlash;
- MSG1.1d rehearsaldan keyin resumable message sequence backfillni real bajarish,
  final bounded writer pause/catch-up, `next_sequence=max(sequence)+1`, duplicate/
  quarantine resolution, count/hash va sequence/nonce constraint validation.
  Legacy rowga deterministic reserved `legacy:<public_id>` ID/hash/origin marker,
  lekin accepted receipt yo‘q; AI/system/null-sender ambiguity quarantine;
- ayni paused final catch-upda MSG1.2a provisional tenure boundarylarini exact
  `visible_from_sequence/visible_until_sequence`ga one-way finalize qilish;
  concurrent legacy join/send
  ordering isbotlanmasa quarantine va membership receipt0. Event boundary hali
  MSG1.2cga deferred;
- MSG1.2c chiqguncha canonical commitdan keyin fresh-authorized ephemeral V1
  compatibility broadcast projection: current V1 recipient kutgan message body
  faqat wire’da bo‘lishi mumkin, outbox/log/dead-letterda saqlanmaydi. Har
  recipientga send oldidan **current membership-route authority** tekshiriladi:
  receipt oldida legacy participants/state authority va canonical tenure shadow
  faqat toraytiruvchi veto bo'lishi mumkin, hech qachon recipient qo'shmaydi;
  receipt keyin canonical tenure authority. Mismatch/ambiguous/failureda body0,
  history/refresh authority; provider/notificationni chaqirmaydi;
- canonical writer cutover receipt, minimum writer/schema epoch guard va
  enforce-able non-null/check constraints faqat barcha writer inventory0,
  backfill/quarantine complete va compatibility broadcast tayyor bo‘lgach;
  aks holda receipt unissued va cutover OFF. `11.3`dagi pause/drain → old lease0
  → final catch-up/count/hash → constraints → immutable receipt → compatible
  **allaqachon shadow/compatibility mode’da started** processlarning readiness/
  traffic admissioni → smoke tartibi shart. Membership receipt esa event
  boundary tayyor bo‘ladigan MSG1.2cgacha unissued. Pre-fence binary fail-closed.

**Test:**

- first 201, same key/payload 200 same receipt, same key/different payload 409;
- same operation/new client key, new operation/same client key va ikkala
  alias/canonical hash mismatch → 409/effect0;
- V1/no-JS deterministic UUIDv5 bridge; ayni client key HTTP/WSda bir result;
- hash normalizatsiyasi NFC/CRLF/outer trim/ordered attachment/context va
  excluded transport fields bo‘yicha golden vectors;
- rate exhausted paytda existing replay receipt qaytadi; transient rejectdan
  keyin same nonce yangi valid attemptni qabul qiladi;
- 10 000 same-key replay/conflict transport bucketda bounded DB lookup/write;
- 20 parallel same key → 1 message/receipt/outbox;
- 20 unique → unique monoton sequence;
- access revoke/rate/blank/oversize;
- DB/outbox/audit failure atomic;
- channel layer down bo‘lsa history/receipt saqlangan;
- ikki client: canonical senddan keyin interim V1 peer event oladi yoki channel
  failda authorized refresh/history ayni message’ni topadi; silent outage0;
- HTTP/WS response semantic parity;
- barcha cookie-auth HTTP mutationlarda missing/invalid CSRF → status safe/effect0;
  Telegram/webhook faqat o‘z signature/binding gate’i bilan ajratilgan;
- existing operation + boshqa hash/alias 409da immutable accepted receipt
  o‘zgarmaydi/yangi row0; yangi operation + occupied client alias terminal
  conflict receipt semanticsi; barcha alias mismatchdan keyin persistence hash;
- AI quota block, supply block, AI success, onboarding/system va bound Telegram
  parallel replay → har biri 1 Message/receipt/outbox; nullable-actor duplicate0;
- client `kind=ai|system`/sender spoof reject effect0; DB/direct ORM test faqat
  same-row sender/kind shape, post-cutover `operation_receipt` non-null va exact
  legacy-marker istisnosini isbotlaydi. Canonical service/inventory testi new AI
  uchun existing successful `AIResponseRun`/output, system uchun to'g'ri named
  service actor scope va terminal receiptni tekshiradi; cross-table invariant DB
  CHECK deb da'vo qilinmaydi. Cycle FK/constraint aynan MSG1.6aga deferred, bu
  slice invented cycle yaratmaydi;
- runtime Message/ChatRoom direct-writer inventory allowlistdan tashqari 0;
- backfill crash/resume/rerun, catch-up concurrent send, next-sequence seed,
  duplicate quarantine va count/hash; legacy reserved ID/hash rerunda ayni,
  namespace clientdan reject, legacy receipt0, AI/system/null-sender ambiguity
  invent qilinmaydi;
- V1 broadcast boshqa/left/revoked recipientga body0; wire body log/outbox0;
- receipt mavjud + unsupported writer epoch → prestart/readiness/service entry
  write0; old direct create constraint failure atomik; cutover har pause/drain/
  receipt crash boundarysida safe resume yoki fail-closed.

**Tugashi:** barcha runtime human/AI/system/onboarding create pathlarida direct
`Message.objects.create`0 va room provisioning tashqarisida direct
`ChatRoom.objects.create`0; client ID persisted; sequence authority; ACK loss
readback mumkin; 1.2c oldidagi deployda V1 realtime yoki refresh ishlaydi.

**Rollback:** frontend renderer/enhancement flag OFF legacy projectionga; bu
`messenger_event_transport_v2` route toggle emas. Barcha send adapter canonical
service’da qoladi. Sequence/receipt data o‘chmaydi.

#### MSG1.2c — transactional event outbox va protocol v2

**Dependency:** MSG1.2b.

**Ish:**

- MSG1.1d rehearsal asosida event streamni resumable seed qilish: historical
  Message/history uchun yangi pending event **yaratilmaydi**; har room snapshot
  baseline/floor va `next_event_cursor` deterministik o‘rnatiladi. Audit sabab
  historical row kerak bo‘lsa u terminal `historical_no_fanout`, browser/
  Notification/Telegram projectoriga qat’iy excluded. Final catch-up,
  `next_event_cursor=max(real_event_cursor)+1`, event/delivery uniqueness/NOT NULL
  validation va count/hash/quarantine evidence;
- active/closed tenure'larning provisional event boundarylarini snapshot baseline
  va future `next_event_cursor`ga one-way exact fill qilib `boundary_state=final`
  qilish; MSG1.2b sequence mappingi bilan birga old/new access shadow diff/
  quarantine0ni prove qilgachgina initial event-route transition bilan **bitta
  transactionda** `MessengerMembershipCutoverReceipt`ni yozish, canonical
  membership authority va event-v2 generationni yoqish. Commit oldidagi crashda
  ikkalasi ham eski compatibility holatda; commitdan keyingi crashda ikkalasi ham
  yangi authorityda va resume smoke/admissiondan davom etadi. Sequence/event map
  tugamaguncha receipt0;
- room event outbox va user delivery claim/lease/retry/dead;
- versionlangan shared event, recipient-side capability;
- room va user inbox sockets;
- message `before_sequence/after_sequence/around` va mutation
  `after_event_cursor`, user `after_user_event_cursor` HTTP;
- user-event retention floor, typed `snapshot_required` va consistent
  `/messenger/inbox-snapshot/` cursor fence;
- room-event retention floor, typed `snapshot_required` va consistent authorized
  room snapshotdagi `snapshot_event_cursor`/`snapshot_message_sequence` fence;
- filtered room page `scanned_through_event_cursor`/high-watermark semantics;
- client protocol negotiation/V1 projection;
- unknown optional field/noncritical type skip policy; unsupported major yoki
  delete/revoke/access/unknown-criticality eventda apply/cursor advance0,
  `upgrade_required` yoki fenced snapshot;
- `MessengerEventTransportRoute` pause/drain cutover: admission pause, V1
  compatibility projection drain, old `compatibility_only`/historical rowsni
  terminal suppress. Dedicated executor avval compatibility/no-claim mode'da
  start qilinib lease/epochi isbotlanadi; event-v2 receipt/generation yo'qligida
  claim0. So'ng DB mode+cursor+minimum event/schema epoch receipt atomik ON,
  executor wake/claim admission, smoke va user admission resume. Rollbackda
  admission pause, claimed rows drain/
  lease-expire, cutoff receipt+mode OFF; old pending rows o‘z generationida
  qoladi, yangi commit faqat V1 projection oladi;
- legacy/V1/new Messenger va Classbook clientlarida compatible heartbeat ACK;
  shundan keyin 30s heartbeat/90s idle, slow-consumer backpressure/gap metrics
  bitta release’da enable;
- dedicated lease-safe `python manage.py messenger_event_outbox --loop`
  executor: DB pending claim → channel/user delivery projection, heartbeat,
  graceful shutdown va periodic wake-up/reconcile. Uni `Procfile`, production
  compose, deploy env/runbook va Control Center required-process/readiness
  inventoryiga qo‘shish; “generic Celery bor” executor dalili emas.

**Tegiladigan joylar:** event/delivery models/services/command, Messenger va
Classbook consumerlari hamda legacy/V1/new client heartbeatlari, selectors/
endpoints/client; `Procfile`, `deploy/docker-compose.prod.yml`,
`deploy/README.md`, settings/env, Control Center snapshot va tests.

**Test:** duplicate/out-of-order/lost event, broker accepted-but-error,
worker crash/lease expiry, channel outage/recovery, slow consumer, actor
`can_edit` leak regression, hidden-audience event ikki shared event orasida →
leak0/loop0, peer read room-event0, other-room unread user event, foreign
delivery; device user-event retentiondan uzoq offline → typed reset + authorized
Inbox snapshot + cursor fence, concurrent revoke/new event convergence va guessed
jump0; room retention reset paytida concurrent edit/delete/revoke → fenced
snapshotdan keyin missing mutation0; unknown optional/noncritical event safe skip,
unknown delete/revoke/major/criticality → cursor advance0 + upgrade/snapshot;
historical seed crash/resume/rerun/catch-up, old history browser/Notification/
Telegram network0, next cursor seed, constraint validation/count/hash;
provisional tenure sequence+event boundary mapping, join/send race ambiguity
quarantine va receipt0; clean mappingdan keyin receipt + old/new access parity,
receipt mavjud old runtime access/write0;
concurrent projector PostgreSQLda `MessengerUserEvent` unique
`(recipient,user_event_cursor)` + `logical_key`, `ChatEventDelivery` unique
logical-recipient `delivery_key`; dead-letter/body/filename
leak0 va delete/purge ref projection; executor absent/stale heartbeat → deploy/
cutover required-process gate FAIL + Control Center degraded;
compatibility/no-claim executor lease fresh bo'lsa ham transition receipt0da
claim0; minimum event/schema epoch past replica/candidate claim0;
web `/readyz` named critical-lag threshold bo‘lmasa up/degraded HTTP pollingda,
claim crash/restart/lease expiry recovery, process argv/artifact va lag alert
test; transport ON/OFFning har crash boundarysida parallel send → har
recipientda bitta render yoki authorized refreshda topiladi, double fanout0;
30/90s heartbeat/idle, throttled/background tab, legacy/V1/new Messenger va
Classbook compatibility, slow consumer close kodi va HTTP fallback.

**Tugashi:** commitdan oldin broadcast0; event failure data loss emas; reconnect
event cursor bilan mutationlarga, message sequence bilan history/unreadga
converge; per-user inbox boshqa roomni generic hint + authorized fetch bilan
yangilaydi; partial fanout alohida delivery rowda ko‘rinadi; canonical
membership authority faqat exact sequence/event tenure boundaryli coordinated
receipt’dan keyin.

**Rollback:** `messenger_event_transport_v2` OFF executor claimini pause qilib V1
compatibility projection/poll refreshga faqat yuqoridagi pause/drain/cutoff
transition orqali; outbox pending o‘z generationi bilan saqlanadi. Canonical
writer qoladi; processni o‘chirishdan oldin paused/readback runbook bajariladi.

#### MSG1.2d — explicit unread/read watermark

**Dependency:** MSG1.2a membership, MSG1.2b sequence, MSG1.2c user-event
transport.

**Ish:**

- `POST read through_sequence`; receipt exemptioni aniq: current tenure row lock
  ostida `max(old, bounded_visible_sequence)`, shuning uchun replay o‘zidan
  idempotent va user event faqat watermark real oldinga siljisa yaratiladi;
- current open tenure `last_read_sequence` authority; closed tenure final
  evidence immutable;
- initial backfill faqat trustworthy per-user `ChatRoomUserState.last_read_at`
  uchun: tenure visibility ichidagi `created_at < last_read_at` (strict boundary)
  bo‘lgan eng katta sequence; exact-equal timestamp ataylab unread qoladi.
  Missing/out-of-tenure/ambiguous timestamp → `0` + quarantine reason. Global
  `Message.is_read` per-user proof bo‘lmagani sabab watermarkga map qilinmaydi;
- unread aggregate own/deleted/out-of-visibility exclusions;
- cross-device monotonic convergence;
- old `last_read_at/is_read` compatibility projection faqat explicit yangi
  watermarkdan one-way derive qilinadi; legacy GET yoki eski field canonical
  watermarkga teskari write qilmaydi;
- reconciliation query/metric.

**Test:** legacy timestamp before/between/equal/after messages, missing/ambiguous/
out-of-tenure timestamp → conservative `0`, global `is_read` ignored, dry-run
old/new unread count+hash shadow diff; hidden tab, failed/invalid GET, exact
boundary, older POST, future sequence, two devices, deleted/self/system message,
member join/leave, concurrent send/read PostgreSQL, leave→rejoin old watermark
preserved va absence unread/history leak0, flag ON/OFF.

**Tugashi:** GET write0; unread drift0 in acceptance; room/badge/inbox bir
projection.

**Rollback:** read-v2 flag OFF old display projectionga; new watermark authority
saqlanadi, legacy display faqat undan one-way derive qilinadi. Reverse
dual-write va GET false-read qaytmaydi.

### MSG1.3 — ultra qulay unified Inbox va resilient client

#### MSG1.3a — unified routes, room list va no-JS core

**Dependency:** MSG1.2a–d; MSG-D14.

**Ish:**

- `/messenger/` unified Inbox, UUID room route va old routes redirects;
- All/Group/Ustoz/AI filters; server-scoped room search;
- desktop split, mobile list/detail;
- latest 50 server-rendered transcript va standard POST form;
- pagination, empty/locked/revoked states;
- consistent terminology: “Guruh”, “Kurs ustozingiz”, “Yordam”, “AI yordamchi”.

**Fayllar:** URLs/views/selectors, V1 templates/components/CSS, legacy redirect,
functional tests.

**Test:** 0/1/50/51/500 room fixture, all role scopes, search/filter/back,
no-JS read/send/error/PRG, old bookmark, 320/1440, query budget.

**Tugashi:** JS/WebSocket bloklansa core read/send ishlaydi; barcha ruxsatli
rooms topiladi; mobile navigation state/draft yo‘qolmaydi.

**Rollback:** `messenger_inbox_v2` OFF old safe template, canonical routes/send
saqlanadi; redirects loop yoki writer fork qilmaydi.

#### MSG1.3b — reducer, unknown reconcile va multi-tab

**Dependency:** MSG1.2b–c, MSG1.3a.

**Ish:**

- normalized client store by public ID/sequence;
- incremental append/patch/prepend; whole transcript rerender0;
- receipt yoki actor+room-scoped `reconcile-message`/history-by-client-ID unknown
  reconcile; legacy/V1 client server UUIDv5 operation IDni bilishi shart emas;
- reconnect gap logic;
- text draft active authenticated sessionga server bergan opaque
  `draft_scope_token` + room public ID namespace’da; 7 kun TTL, jami/per-draft
  bounded size (text hard capdan oshmaydi), attachment/blob/filename/auth/CSRF
  tokeni saqlanmaydi. Refresh/crashda ayni active user/session tiklanadi;
  accepted sendda clear, definite/unknown holatda receipt yechilguncha saqlanadi,
  room revoke/account delete/logoutda purge va account switchdan oldin barcha
  old-scope keylar o‘chiriladi; pending intent identity;
- BroadcastChannel/storage coordination bilan multi-tab dedupe;
- HTTP fallback; optional idempotent retry same nonce;
- scroll anchor va “N ta yangi”.

**Fayllar:** `messenger-state.mjs`, `messenger.mjs`, shared fetch/socket helper,
Node tests, browser tests.

**Test:** ACK lost before/after commit, duplicate/reordered/gap event, offline/
online, two tabs same draft/send, refresh/crash, TTL/size/clear-on-send/revoke,
user A logout → user B login draft leak0 (Aning active-session refresh recoverysi
saqlanadi), attachment/blob/token storage0; active/non-bottom scroll,
409 conflict, transport fallback; legacy ACK-loss actor+room/client-ID lookup,
foreign room/user/alias conflict 404/409, raw ID/body log0.

**Tugashi:** duplicate DOM/message0; unknown actionable va eventually reconciled;
silent new-nonce resend0; reconnect latest statega converge.

**Rollback:** enhanced client OFF/no-JS server core; pending draft export/discard
aniq, canonical server state saqlanadi.

#### MSG1.3c — mobile, keyboard va assistive technology

**Dependency:** MSG1.3a–b.

**Ish:** `role=log`/status cadence, focus/scroll contract, IME-safe composer,
touch targets, virtual keyboard/safe-area, reflow/text spacing/forced colors/
reduced motion, accessible connection/error/unknown dialog.

**Test:** automated semantics + keyboard; 320/360/390px, 400% zoom, 200% text,
long strings, iOS/Android keyboard; NVDA Firefox/Chrome, VoiceOver Safari,
TalkBack Chrome manual evidence.

**Tugashi:** `9.6` matrix PASS; incoming event focusni tortmaydi; screen reader
butun historyni qayta o‘qimaydi; core no-JS saqlanadi.

**Rollback:** CSS/enhancement flag OFF semantic SSR corega; accessibility
bugfixlar renderer flagdan mustaqil qoladi.

### MSG1.4 — conversation productivity

#### MSG1.4a — reply, deep-link, date va context card

**Dependency:** MSG1.2 protocol/sequence, MSG1.3 shell.

**Ish:** same-room reply constraint, one-level quote preview, around-message
deep link/jump, date separators/ISO timezone, unread divider, typed
course/lesson/Classbook/SIT context card.

**Test:** foreign/deleted/out-of-visibility reply, old page jump, equal time,
timezone/DST, revoked context, no-JS reply form, notification deep link.

**Tugashi:** user contextni qayta yozmasdan savol beradi; link exact message
atrofini access-safe ochadi; canonical domain state nusxalanmaydi.

**Rollback:** `messenger_reply_v2` OFF new reply rows plain message sifatida
o‘qiladi; FK/data yo‘qolmaydi.

#### MSG1.4b — edit/delete/revision va truthful retention copy

**Dependency:** MSG1.1d revision substrate, MSG1.4a reply/around projection;
MSG-D3 edit/delete/retention.

**Ish:** service + expected version + operation receipt; owner window; immutable
revision/minimal audit; tombstone; attachment lifecycle link; admin inline
read-only; copy physical retentionni aniq aytadi.

**Test:** exact window ±1s, stale tabs, duplicate operation, audit failure,
deleted reply/search/notification, attachment retained/purged policy, actor
delete/account anonymize.

**Tugashi:** silent truncate0; old content policy bo‘yicha evidence; admin bypass0;
UI va storage semantics mos.

**Rollback:** edits/deletes temporarily read-only; history/revision saqlanadi,
direct legacy mutation qaytmaydi.

#### MSG1.4c — scoped search, pin va per-user archive

**Dependency:** MSG1.2d membership state, MSG1.3a selectors va MSG1.4a
around-message projection.

**Ish:** CSRF-protected `POST /messenger/search/` body orqali room/all-visible
search, sender/date/file filter va around result; raw q URL/history/referrer/
access logga kirmaydi. Existing
pin state’ni duplicate model yaratmasdan `ChatMembership` + user-streamga
migrate qilish va per-user membership archive/unarchive; har desired-state
mutation operation receipt + expected `preference_version`/CAS bilan. Oddiy user
global `ChatRoom.status`ni o‘zgartirmaydi; global room archive/close faqat
canonical lifecycle service + authorized owner/policy. Mute/quiet/channel
MSG1.7a ownerligida; notification/read semantics ajratilgan;
PostgreSQL indexes.
SQLite local parity bounded fallback bilan, production search capability
backendga aniq.

**Test:** foreign/left/deleted/revision/body scope, Turkish/Uzbek case behavior,
CSRF missing/invalid effect0, canary query URL/history/referrer/proxy/app log0,
no-store JSON/HTML/error, empty/long query, pagination, pin order, per-user
archive/unarchive, ordinary global-room-archive effect0, authorized lifecycle
archive, two-tab stale `preference_version` 409/effect0 va winner increment,
query plan/count.

**Tugashi:** user kerakli conversation/message’ni ≤3 amalda topadi; search
accessni kengaytirmaydi; mute history/unreadni o‘chirmaydi.

**Rollback:** search/personal-state flags OFF; existing state/data saqlanadi.

---

### MSG1.5 — ishonchli attachment va decision-gated voice

#### MSG1.5a — canonical upload session va media metadata

**Dependency:** MSG1.1d attachment substrate, MSG1.2b–c canonical send/event va
MSG1.3b resilient client state.

**Ish:**

- upload-init → private object → finalize command yoki single-request small file
  uchun ayni operation receipt;
- canonical sniffed kind/MIME/hash/size/generated key persisted;
- client preflight, progress, cancel va server error;
- same operation/file retry duplicate object/message yaratmaydi;
- attachment-only Message canonical service orqali;
- human-display va AI-readable capability alohida;
- legacy FileField rows cutover oldidan default private
  `application/octet-stream` + attachment download, `ai_readable=false`; eski
  browser MIME/filename hech qachon routing authority emas. Resumable bounded
  re-sniff/hash backfill valid rowni typed ready qiladi, missing/mismatch/parser
  failureni quarantine qiladi; count/hash/checkpoint va rerun idempotent.

**Fayllar:** Messenger upload views/service/model, `core/upload_validation.py`
adapteri, private media view, V1 client/template/CSS va tests.

**Test:** MIME/extension spoof, empty/oversize, Unicode filename, duplicate
operation, cancelled/partial, DB fail after save, storage fail, unauthorized,
slow upload, file-only preview, browser content type ignore; legacy unknown row
forced-download/AI-readable0, valid re-sniff, missing/mismatch quarantine,
backfill crash/resume/rerun/count/hash.

**Tugashi:** new va successfully backfilled routing persisted sniffed kinddan;
unverified legacy row safe forced-download/AI-readable0; duplicate object/message0;
progress/cancel truthful; private/no-store/nosniff saqlanadi.

**Rollback:** post-MSG1.2b `messenger_upload_v2=OFF` faqat canonical
compatibility adapterga qaytadi: private storage + persisted sniffed kind +
canonical send/receipt saqlanadi, faqat upload-session/progress UI o‘chadi.
Bunday adapter tayyor bo‘lmasa OFF = yangi upload read-only. Baseline direct
`Message.objects.create`, client MIME routing yoki web-process AI
`.run()`/daemon fallback yo‘li hech qachon qaytmaydi. New ready objects o‘qiladi,
pending reconcilerga; public storagega qaytmaydi. Rollback testi flag OFFda ham
canonical writer, persisted sniffed kind, unverified legacy safe-download va
provider direct-call0ni isbotlaydi.

#### MSG1.5b — lifecycle, quota va reconciliation

**Dependency:** MSG1.5a; MSG-D3 retention.

**Ish:** per-file/user/room/day quotas, pending expiry, missing/orphan/hash
audit, delete/tombstone/legal-hold/purge state, parser resource bounds, owner
health. Purge default dry-run/batch/resume.

**Test:** quota boundaries/concurrency, object missing, orphan, hash mismatch,
delete + reply/search/notification, legal hold, purge crash/rerun, backup
restore, object-store failure.

**Tugashi:** object lifecycle har holatda izohli; orphan growth visible;
physical delete faqat approved policy; audit body/filename leak0.

**Rollback:** purge worker pause; rows/objects retained, new uploads optionally
read-only. Completed purge backup/legal contractdan tashqari “undo” deb
va’da qilinmaydi.

#### MSG1.5c — human voice note, faqat MSG-D8 `ADMIT` bo‘lsa

**Dependency:** MSG1.3c native device/a11y, MSG1.5a–b generic retention hooks,
MSG-D3 approved policy va MSG-D8 `ADMIT`; completed MSG1.8a talab qilinmaydi,
speaking AI CUT.

**Ish:** browser record/upload, duration/size/type, playback, transcript
alternative policy, no-JS file fallback. Auto-transcription, pronunciation
score va auto-AI analysis yo‘q.

**Test:** permission denied, interruption, max duration, malformed audio,
iOS/Android playback, keyboard/screen reader controls, retention/quota.

**Tugashi:** faqat real learner/teacher ehtiyoji va owner admissioni bo‘lsa.
Qaror bo‘lmasa UI/route/model promise0; roadmapning qolgan qismi bloklanmaydi.

**Rollback:** `messenger_voice_notes` OFF existing files authorized download
bilan; new recording disabled, data saqlanadi.

### MSG1.6 — AI v2 correctness va grounded yordam

#### MSG1.6a — run lease, entitlement va canonical request service

**Dependency:** MSG1.0b containment, MSG1.2 writer/outbox va MSG-D4 entitlement
qarori.

**Ish:**

- `request_ai_response`/`claim_ai_run` service;
- typed entitlement, quota, supply va room access;
- stable operation/idempotency web/widget/Telegramda;
- additive `AIContextGrant` migration: logical run bilan one-to-one, immutable
  channel/authorized course+lesson/memory/progress/attachment IDs,
  policy/access version/hash va expiry;
- logical run + immutable `AIGenerationCycle` + outputga linked bounded
  `AIDerivativeJob` + physical `AIAttempt`; har provider network call uchun
  attempt parent XOR cycle/derivative va `kind=context_embedding|generation_primary|
  generation_fallback|memory_embedding_batch`, exact state/ordinal/
  retry-of-attempt, cycle user `request_receipt` va one-to-one supply event;
- har successful cycle uchun deterministic named AI-worker `publish_receipt`;
  Message forward operation receipt unga, cycle FK esa generation cycle'ga.
  Request receipt → run/cycle va publish receipt → same output Message typed
  linkage; ikki actor scope bir rowga siqilmaydi;
- MSG1.2bdagi `AIResponseRun` provenance’ni cycle/output FKga additive backfill/
  quarantine qilib, post-cutover new `kind=ai` Message uchun successful cycle
  link constraintini enforce qilish;
- legacy `AIResponseRun` backfill provider call/costni ixtiro qilmaydi: terminal
  old rows `legacy_unattributed` compatibility marker bilan attempt/supply rowsiz,
  pending/stuck rows body-free audit+quarantine/reconciliationda. Exact
  attempt↔supply 1:1 faqat cutover epochdan keyingi physical calls uchun;
- lease expiry/reconciler/time limit;
- provider boshlanmasidan oldingi stale claim reclaim; `provider_started`dan
  keyingi crashda auto-recall0, explicit linked retry;
- generation cycle foreground boundi: memoized/batched context embedding ≤1,
  generation primary 1 + definite-failure fallback ≤1, ya'ni ≤3. Successful
  outputdan keyingi alohida derivative job bounded memory embedding batch ≤1;
  user-authorized end-to-end lineage total provider calls ≤4. Cycle terminal
  state derivative completionni kutmaydi va derivative failure outputni
  reopen qilmaydi. Post-send
  timeout/reset yoki ambiguous generation outcome → unknown, fallback0,
  explicit warned retry; supply reservation va telemetry har phase/boundda;
- `ai/providers/gemini.py` va dormant `ai/providers/digitalocean.py`dagi ichki
  generate/embedding retry/model-candidate/per-item looplarini
  bitta-network-call primitive contractiga
  ajratish; cycle orchestrator `aicontrol/supply.py` bilan har call oldidan
  attempt+supply row/reservationni atomik yaratadi. `generate()`ni bir marta
  chaqirish “bir attempt” deb taxmin qilinmaydi; paritysiz provider OFF;
- SmartForm extraction/replyni local deterministic parser yoki ayni provider
  structured envelope’iga birlashtirish; secondary extractor provider chain0,
  server form patchni schema/business rule bilan validate qiladi;
- MemoryRetriever va RAG query embeddingini bitta cycle-scoped cache/batchga
  birlashtirish; memory candidate save'ni bounded list + deferred single batchli
  `AIDerivativeJob`ga ko'chirish. Publish/cancel/revoke, account deletion va
  retention lineage bu derivative jobda ham fresh tekshiriladi;
- local deterministic safe fallback run `result_mode`i; AIAttempt state’i emas;
- AI-worker publish receipt, response Message/outbox va cycle+run terminal state
  bitta safe transaction;
- post-save signal/daemon/direct `.run()` orchestrationdan chiqarish.

**Tegiladigan joylar:** Messenger run/cycle/attempt/grant model/service/task,
`ai/providers/gemini.py`, `ai/providers/digitalocean.py`, provider base/typed
result, `aicontrol/supply.py`, `ai/memory/semantic.py`,
`ai/memory/repository.py`, `messenger/rag.py`, SmartForm extractor/schema,
web/widget/Telegram adapters, migrations, reconcilers va tests.

**Test:** same request 20 parallel, broker accepted-but-error, worker crash
before/after provider/write, lease steal boundary, cancel/late result, quota
race/failure, access revoke, har mocked network call = 1 immutable attempt =
1 supply event, grant one-to-one/immutability/expiry/access-version; cycle
terminal immutable, run reopen0, explicit retry cycle bound va regenerate yangi
run; user request replay same cycle/attempt0, worker publish replay same
Message/outbox va request/publish actor-scope swap constraint failure;
request-sent timeout → unknown/fallback0; definite primary failure → max bir
fallback; mocked `genai.Client.models.generate_content` **va** `embed_content`
counterida Gemini/DigitalOcean generation cycle bo'yicha context≤1,
generation≤2/foreground≤3; linked derivative job memory-batch≤1 va authorized
end-to-end lineage request/attempt/supply≤4; terminal cycle'dan keyin derivative
attempt parent XOR constrainti va output reopen0; Memory+RAG same query bitta
embedding, N memory candidate bitta bounded deferred batch, ichki retry/model/
per-item loop0; noncompliant provider admission0; active SmartForm ham shu bound,
replay call0; legacy terminal/pending/stuck migration count/hash, invented
attempt/cost0.

**Tugashi:** initial/regenerate operation bitta yangi logical run; explicit retry
operation open runga linked yangi immutable cycle/attemptlar; transport replay
duplicate attempt0; barcha user adapterlar bir request receipt semantikasida,
har output alohida deterministic AI-worker publish receiptida. Har phase va
total physical attempt cycle boundidan oshmaydi; unknown outcome
avtomatik provider re-call qilmaydi; orphan response/run0; stuck claim
reconcile; orphan/requestsiz publish receipt0.

**Rollback:** `messenger_ai_runs_v2` OFF new requests unavailable/read-only
history; unsafe legacy provider path qaytmaydi.

#### MSG1.6b — scoped context, true system role va citations

**Dependency:** MSG1.6a; canonical course/lesson policy.

**Ish:**

- provider system/user/context role separation;
- untrusted RAG/profile/attachment boundaries;
- active course + lesson drip/sequential access;
- teacher scope default-deny;
- persisted `EvidenceRef`: attempt/output Message FK, ordered unique ordinal,
  kind/object ID/version/content hash, safe deep-link/access-scope hash/freshness;
- memory/progress only requester private AI roomda;
- capability-driven image/PDF behavior.

**Fayllar:** `messenger/models.py` va additive migrations (grant/evidence/
constraints), AI engine/builder/providers, `messenger/rag.py`, context tools,
course access adapter, citation projection/tests.

**Test:** locked/foreign course, staff no scope, stale enrollment, prompt
injection in message/RAG/PDF/profile, EvidenceRef ordering/uniqueness/version/
retention, citation revoke/click fresh access, system-role provider parity,
supports_vision false, token/context bounds.

**Tugashi:** unauthorized context0; false capability claim0; output source
requesterga ochiladigan evidence bilan yoki citationless safe fallback.

**Rollback:** `messenger_ai_grounded_context` OFF remote generative explanation/
context claimni bloklaydi; deterministic local safe help/handoff va private
history saqlanadi. Broad flat promptga qaytish yo‘q.

#### MSG1.6c — retry/regenerate UX va adapter parity

**Dependency:** MSG1.6a–b, MSG1.3 client.

**Ish:** same-logical-request yangi linked immutable retry attempt/cycle,
explicit new-run regenerate, cancel, run/attempt status projection; web/Telegram/
widget stable external identity; error taxonomy, quota cost copy; no raw
provider exception.

**Test:** double retry/regenerate, reconnect, stale button, terminal success,
Telegram webhook replay, widget refresh/two tabs, cancel race, fallback and
quota copy.

**Tugashi:** user qaysi amal yangi quota/provider request ekanini biladi;
duplicate request0; every run/message traceable receipt.

**Rollback:** `messenger_ai_retry_controls` OFF retry/regenerate/cancel
controllerlarini yashiradi va yangi retry/regenerate provider requestni bloklaydi;
pending/result read-only. Legacy random retry key qaytmaydi.

#### MSG1.6d — A9 eval, memory deletion va staged AI rollout

**Dependency:** MSG1.6a–c; A8 green; MSG-D3/MSG-D11.

**Ish:** `8.8` eval corpus/runner, cost/latency budget, privacy cases; memory/
summary/fact/embedding/trace dependency graph va clear/delete dry-run; staff
pilot → bounded learners.

**Test/evidence:** ≥50 fixed cases, repeat variance, provider unavailable,
locked/cross-user/group privacy, poison file/RAG, quota, citations, deletion
graph, logs. Real prompt data eval artifactiga ko‘chirilmaydi.

**Tugashi:** A9 threshold/owner review documented; AI default ON faqat admission;
clear operation approved derivativesga yetadi; group AI hanuz OFF.

**Rollback:** `messenger_ai_runs_v2` OFF, history/read/delete controls qoladi;
new provider call0. Memory data owner-approved retention bo‘yicha.

### MSG1.7 — notification, ustoz ishi va moderation

#### MSG1.7a — per-user notification policy

**Dependency:** MSG1.0c containment, MSG1.2c transactional event outbox,
MSG1.2d membership; MSG-D10.

**Ish:** preference/mute/quiet/channel HTTP mutationlari operation receipt +
expected `preference_version` bilan; access/role lifecycle esa alohida
`state_version`. Message transactionida body-free event va immutable event-time
tenure/visible-sequence audience basis persist bo‘ladi; idempotent projector
candidate’larni append-only tenure’dan derive qiladi va recipient ID bo‘yicha
sorted bounded batchda preference’dan qat’i nazar required logical user-event/
Inbox-unread deliveryni yaratadi; fresh accessgina audience’ni toraytiradi.
Keyin alohida external notification projector current fresh access +
`all|non_group|none` + mute/quiet/channel preference bilan external candidate’ni
olib tashlashi mumkin, lekin keyin join qilgan userni qo‘shmaydi. Deterministic
`external_key=messenger:<message>:<recipient>` bilan
body/URLsiz typed room/message refsli `Notification.CATEGORY_MESSENGER` →
existing `TelegramOutbox`; relative deep link fresh accessdan keyin delivery
vaqtida materialize bo‘ladi; projection
fail/retry/dead-letter va fresh recipient access. So‘ng `all|non_group|none`, mute
until, quiet hours/timezone, web vs Telegram channel, generic-only privacy
preview, preference UI/no-JS POST va room-kind default matrix. Human mention
notificationi typed model yo‘qligi sabab CUT; raw `@username` parse qilinmaydi.

**Test:** message commit + projector/Notification creation fail → durable pending
delivery → retryda exactly one Notification/outbox; duplicate event; exact quiet
boundary/DST, mute expiry, AI/private/group defaults, multiple devices,
preference race, eventdan keyin join → notification0, leave-before-claim → send0,
stale `preference_version` 409/effect0 va state-version preferencega tasodifiy
increment0,
leave/rejoin absence gap → send0, stale access, outbox dedupe/429/transient/
permanent/dead; access revoke before claim → link/send0; purge/delete typed ref
projectioni; persisted URL/body0 va token/log redaction; two overlapping
100-member roomsda concurrent fanout PostgreSQL deadlock0, unique delivery rows
va bounded message-receipt latency.

**Tugashi:** recipient predictable notification oladi; bir
message-recipientga ko‘pi bilan bitta canonical Notification/outbox; projector
failure owner dead-letterda va retryable; raw private body/filename/AI output0; web
history/preferences failuredan mustaqil. Bot API delivery at-least-once: sender
remote acceptdan keyin crash qilsa duplicate bo‘lishi mumkin; UI/ops exactly-once
external delivery da’vo qilmaydi va platform receipt holatini truthful ko‘rsatadi.

**Rollback:** `messenger_notifications_v2` OFF external claimlarni pause qiladi,
outboxni saqlaydi va existing mute/level/channel suppressioni fail-closed qoladi;
generic notification yoki direct Bot API qaytmaydi.

#### MSG1.7b — teacher Inbox va contextual handoff

**Dependency:** MSG1.2a membership, MSG1.3a shell, MSG1.4a contextual handoff,
MSG-D6 response window va MSG-D12 support assignment/handoff.

**Ish:** assigned academic rooms; unread/unanswered/course filters;
last learner message → first instructor reply derived state; safe context cards;
owner support escalation; no duplicate ticket canonical state.

**Test:** instructor transfer, multiple courses, learner consecutive messages,
teacher reply, deleted/system/AI message exclusion, SLA exact boundary,
foreign course, SIT/Classbook unavailable handoff.

**Tugashi:** academic savol exact instructor queuega; unanswered metric
reproducible; ordinary staff private AI room ko‘rmaydi.

**Rollback:** teacher queue flag OFF unified scoped rooms qoladi; messages/
membership saqlanadi.

#### MSG1.7c — report/moderation va owner support

**Dependency:** MSG1.4b revisions, MSG-D7 moderation owner va MSG-D12 support
assignment. Body/transcript break-glass faqat MSG-D13 `ADMIT` bo'lsa.

**Ish:** core report category/note, duplicate guard, metadata-only moderation
queue, hide/restore/resolve/dismiss reason+audit; owner support assignment; abuse
rate/slow mode. MSG-D13 no-decision yoki `DENY`da body/transcript break-glass
route/control/service0; `ADMIT` bo'lsa exact purpose/scope/expiry/auditli optional
integration.

**Test:** reporter/author/instructor/moderator/owner matrix, foreign report,
duplicate/concurrent, hidden projection/search/reply/notification, audit failure,
appeal/restore if admitted; D13 no-decision/DENY route/control/service0, ADMITda
scope/expiry/reason/audit va foreign/bulk body0.

**Tugashi:** harmful message uchun user safe path; moderator action audited;
global body surveillance yoki hard delete default emas.

**Rollback:** new reports read-only and queue retained; hide policy safe
projection; admin direct edit qaytmaydi.

### MSG1.8 — privacy, scale va reliz

#### MSG1.8a — retention/export/anonymization

**Dependency:** MSG-D3 approved; MSG-D13 resolved (`DENY` ham valid, bunda body
export/break-glass/legal-hold body accessi scope’dan olinadi); MSG1.5a–b/1.6/1.7
data graph va faqat MSG-D8 `ADMIT` bo'lib voice slice bajarilgan bo'lsa MSG1.5c.

**Ish:** policy matrix/settings, user export scope, account unlink/anonymize,
message/attachment/revision/AI derivative/`MessengerUserEvent`/chat event delivery/
optional admitted voice object/transcript alternative/
`users.Notification`/`TelegramOutbox`/audit purge commands, legal hold va owner
preview/confirm. Shu slice `ChatOperationReceipt` full response/detailini stable
PK saqlangan in-place compact rowga o'tkazadi; dependent FK mavjud paytda base
receipt delete0. Notification/outbox content generic/body-free bo'lsa ham
recipient/delivery metadata retention graphga kiradi. Minimal body-free immutable
`PrivacyActionLedger` (subject pseudonymous ref, action/policy version/time,
result hash) har approved purge/anonymizationdan keyin restore-control sifatida
alohida durable/exported saqlanadi. Eski backup restore qilinganda service
ochilishidan oldin latest ledger/legal hold qayta import/reapply/reconcile
qilinadi; o‘chirilgan subject jim resurrect qilinmaydi.

**Test:** dry-run/apply/rerun/resume, boundary dates, legal hold, shared group
author anonymization, private export foreign0, missing object; pre-purge backupni
restore → latest ledger reapply → deleted/anonymized subject/body resurrection0
va readiness faqat reconciliationdan keyin; receipt compactionda Message FK
saqlanishi, expired/key-retired replay effect0, key-rotation golden vectors va
purged short bodyga dictionary-guess orqali HMAC match0; account delete
`MessengerActorSubject.user`ni unlink qilib opaque subject uniqueness/replay protectionni
saqlashi, stale/deleted credential replay auth0/effect0; re-identification review
checklist.

**Tugashi:** approved period va deletion/anonymization operational; count/hash
evidence; destructive target exact va recoverability documented.

**Rollback:** purge job pause; completed physical deletion faqat backup/legal
runbook darajasida. Policy rowni OFF qilib o‘chirilgan data qaytadi deyilmaydi.

#### MSG1.8b — performance, chaos va operational control

**Dependency:** barcha admitted writer/read/worker paths.

**Ish:** inbox query/index budgets, DOM window, 5k history, 100 sockets,
PostgreSQL races, Redis/channel/Celery/storage/provider/Telegram chaos;
metrics/alerts/reconcilers/Control Center cards va runbooks; all-role deploy
inventory/per-instance epoch lease, each executable prestart+claim guard,
`/healthz` liveness vs web `/readyz`, Caddy active health, event executor
required-process/lag visibility va candidate tashqarisidagi trusted deploy
controller bilan pre-fence rollback/direct-compose bypass rejection drill.

**Test:** `9.7–9.9`; SQLite local va PostgreSQL+Redis integration; separate
worker processes where needed; privacy-safe metric/log inspection; old web/
Celery/outbox replica, stale/duplicate/missing leases, process crash/expiry,
DB outage restart-loop0, incompatible web traffic0, ancillary worker stale paytda
LMS HTTP/history up + Control Center red/degraded, event pending durable; missing
manifest/image label/`SOURCE_VERSION`/wrapper va old `/readyz=200` candidate
trusted controllerda start/traffic0.

**Tugashi:** budgets evidence; no N+1 growth; outage data-loss/duplicate0;
owner stuck queue’ni body ko‘rmasdan topadi; alert/runbook drill.

**Rollback:** expensive optional projections/notifications/AI paused; canonical
human history/send safe degraded mode. Metrics removal rollback emas.

#### MSG1.8c — staged rollout va final evidence

**Dependency:** MSG1.0 through MSG1.8b admitted scope, required CI/review green,
backup.

Rollout:

1. security/invariant fixes unflagged;
2. expand schema/audit/backfill;
3. canonical writes + shadow reads internal staff;
4. `11.3` writer pause-drain/final-check/`MessengerCutoverReceipt`ni real
   cutover; membership + initial event-v2 atomik admissioni esa boundary/lease
   bilan rehearsal, receipt0;
5. one pilot cohort;
6. `11.3` bo'yicha membership + initial event-v2 route/generationni real atomik
   admission, smoke; shundan keyin V2 read/inbox client rollout;
7. attachment/notification/teacher/moderation;
8. private AI only after A8/A9;
9. bounded cohort expansion;
10. owner/native/AT sign-off;
11. production deploy alohida decision/evidence; candidate/image SHA + manifest
    hash, expected replica inventory va cutover-aware rollback artifact trusted
    external controllerda prove; direct compose/platform deploy credential0.

Har qadam metric, anomaly diff, outbox/run age, rollback readback bilan. Writer
cutover majburiy append-only `MessengerCutoverReceipt` bilan; `SystemAuditEvent`
qo‘shimcha operator audit bo‘lishi mumkin, receipt o‘rnini bosmaydi. Flag toggle
bu receiptni bekor qilib old direct writerga qaytarmaydi.

**Final evidence:** migration rehearsal/count/hash/quarantine; feature flag
ON/OFF; browser/device/AT; PostgreSQL/Redis/Celery; provider/Telegram qaysi
muhitda real/mocked; backup/restore; runbook; owner acceptance holati.

**Tugashi:** `15` DoD va `12` acceptance to‘liq. “Merged” production “ON” yoki
owner “qabul qildi” bilan aralashtirilmaydi.

**Rollback:** capability flaglari `11`dagi teskari tartibda; data/schema/history
saqlanadi. Destructive cleanup boshqa admission.

---

## 11. Feature flag, setting va rollback contracti

### 11.1 Flag emas — har doim amal qiladigan xavfsizlik

Quyidagilar renderer yoki rollout flag ortiga yashirilmaydi:

- WebSocket Origin/session validation;
- server-side schema/frame/text hard cap;
- fresh action/delivery/worker authorization;
- body/token/raw exception log redaction;
- private media authorization/no-store/nosniff;
- barcha non-AI/shared-room private-context AI OFF containment;
- teacher/RAG default-deny scope;
- backoffice least privilege;
- latest-history va GET false-read bugfixi;
- idempotency/DB constraint canonical writer yoqilgach.

Feature rollback bu invariantlarni qayta ochmaydi.

### 11.2 Rollout flaglari

| Flag | Default | ON | OFF/rollback |
|---|---:|---|---|
| existing `frontend_v1_messenger` | OFF | human V1 renderer | safe legacy renderer; backend invariant bir xil |
| existing `frontend_v1_ai_messenger` | OFF | AI V1 renderer | safe legacy AI projection; provider policy bir xil |
| `messenger_membership_route_v2` | OFF | cutovergacha canonical shadow compare/pilot renderer; access `legacy ∩ canonical-veto`, widen0 | receipt oldida legacy authority + optional canonical veto; receipt’dan keyin OFF/error = write pause/safe read-only, legacy authority emas |
| `messenger_write_cutover` | OFF | canonical message service barcha adapterlar uchun | cutover receiptgacha legacy compatibility; receipt’dan keyin OFF = writes paused, eski writer emas |
| `messenger_event_transport_v2` | OFF | **requested** outbox + v2 socket/gap capability | raw toggle route’ni o‘zgartirmaydi; actual V1/V2 authority faqat `MessengerEventTransportRoute` pause/drain/immutable transition receiptida; OFF request canonical HTTP/history + polling/V1ga controlled transition ochadi |
| `messenger_read_watermark_v2` | OFF | sequence unread/read | compatibility display; GET write qaytmaydi |
| `messenger_inbox_v2` | OFF | unified SSR/enhanced Inbox | safe old shell/redirect, canonical data/write |
| `messenger_reply_v2` | OFF | reply/deep-link/date/context | reply rows plain readable; data saqlanadi |
| `messenger_search_v2` | OFF | scoped server message search | room filter qoladi; index/data saqlanadi |
| `messenger_personal_state_v2` | OFF | pin va per-user archive canonical membership + user-stream | V2 controls/projection OFF; rows saqlanadi, existing safe pin display compatibility; mute/quiet/channel faqat notifications flag/policyda |
| `messenger_upload_v2` | OFF | upload session/progress/lifecycle | canonical compatibility upload: private storage + persisted sniffed kind + canonical send; adapter tayyor bo‘lmasa read-only; baseline direct writer/AI fallback hech qachon qaytmaydi |
| `messenger_notifications_v2` | OFF | mute + notification level/channel/quiet preferences va canonical outbox | existing mute rows saqlanadi va external-send suppressioni fail-closed qoladi; generic privacy-safe claim pause, direct sender yo‘q |
| `messenger_teacher_inbox` | OFF | unanswered/scoped teacher queue | unified scoped Inbox |
| `messenger_moderation` | OFF | report/queue/actions | existing reports read-only; unsafe admin writer yo‘q |
| `messenger_ai_runs_v2` | OFF | lease/context/receipt orchestration | new AI paused, history/human chat ishlaydi |
| `messenger_ai_grounded_context` | OFF | scoped course/lesson/RAG/memory context + evidence-backed remote explanation | remote explanation/context claim0; deterministic local safe help/handoff va history |
| `messenger_ai_retry_controls` | OFF | explicit retry/regenerate/cancel operationlari va truthful cost/state UX | controls hidden; new retry/regenerate request0, pending/result read-only |
| `messenger_ai_shared_room` | OFF | approved typed shared-room AI | barcha non-AI roomda provider call0; raw `@azure` oddiy human text |
| `messenger_ai_vision` | OFF | approved provider/eval image analysis | human image attachment only |
| `messenger_voice_notes` | OFF | admitted human voice record/playback | existing file read; new record0 |

Flaglar [registry](../../core/flags.py)da declared default bilan va runbookda.
Riskli yangi capability default OFF; DB flag read xatosi declared OFFga tushadi.
Membership/writer receipt’dan keyin bu OFF holat legacyga rollback degani emas;
authority state flag storedan mustaqil monotonic receipt bilan aniqlanadi.
Xuddi shunday event flag raw readi writer/broadcaster yo‘lini fork qilmaydi:
adapter faqat DB `MessengerEventTransportRoute` authority’sini o‘qiydi; flag
o‘zgarishi operatorga pause/drain transitionni boshlash requesti xolos.

### 11.3 Monoton membership va writer cutover

`MessengerMembershipCutoverReceipt`:

- backfill/shadow report hash, canonical policy version, actor/reason/time;
- unresolved quarantine count va accepted exceptionlar;
- old/new access matrix diff status;
- `minimum_membership_epoch` va `minimum_schema_epoch`;
- receipt immutable; cutoverdan keyin authority canonical membership.

Receipt oldidan `messenger_membership_route_v2=OFF` old projectionga qaytishi
mumkin. Receipt’dan keyin flag DB unavailable, OFF yoki config mismatch bo‘lsa
new send/membership mutation fail-closed va history safe read-only; stale
`participants`/`ChatRoomUserState` hech qachon qayta access authority bo‘lmaydi.
Reverse cutover faqat yangi owner-approved incident operation, eski flag toggle
emas.

Majburiy `MessengerCutoverReceipt` (`SystemAuditEvent` faqat qo‘shimcha log):

- canonical writer version;
- `minimum_writer_epoch` va `minimum_schema_epoch`;
- migration/backfill report hash;
- actor/reason/time;
- old/new projection diff status;
- rollback semanticasi.

Receipt yaratilmaguncha `messenger_write_cutover=OFF` legacy compatibility
writerga ruxsat berishi mumkin. Receipt’dan keyin:

- barcha renderer/adapter canonical service;
- flag OFF yangi write’ni safe pause qiladi;
- old `Message.objects.create`/signal/provider writer qayta ochilmaydi;
- read rollback compatibility projection orqali;
- receipt update/delete qilinmaydi; reverse cutover yangi audited operation va
  owner incident qarorisiz yo‘q.

Flag va receiptning o'zi eski binary'ni to'xtatmaydi. Har release repositorydagi
versionlangan static `deploy/messenger-runtime-epochs.json` manifestda format
versioni, supported membership/writer/schema/event epoch va **barcha production
executable** uchun executable→role/capability mappingni e'lon qiladi: `web`,
Celery `worker`, scheduler `beat`, `telegram_outbox`, event-v2 admitted bo'lsa
`messenger_event_outbox`, local polling ishlatilsa Messengerga yozishi mumkin
bo'lgan `runbot`/Telegram ingress. Required role/replica set capabilityga
conditional: 1.2b writer cutoverida hali mavjud bo'lmagan event executor majburiy
emas; 1.2c event-v2 admissionidan boshlab u majburiy. `beat` manifestda map
qilinadi. Har role manifestda explicit `lease_required` va
`required_when_capability` beradi: `web` hamda Messenger mutation/claim qiluvchi
worker/ingress/outbox uchun lease required; mapping-only `beat` uchun artifact/
wrapper verification shart, ammo cutover lease proof emas.

Manifest o'z commit SHA'sini hardcode qilmaydi. Root `Dockerfile` build ARG/LABEL,
immutable image digest va existing `SOURCE_VERSION` bir release SHA'ga bind
qilinadi; manifest hash ham artifact attestatsiyasiga kiradi. **Candidate
image/checkoutdan tashqaridagi**, rollback bilan almashtirilmaydigan pinned trusted
host/CI deploy controller image filesystem/label+manifest va har production
processning shared epoch wrapper argv sini process startidan oldin tekshiradi.
Missing manifest, label, `SOURCE_VERSION`, executable mapping yoki wrapper =
deploy reject. Candidate ichidagi management command, entrypoint yoki uning eski
`/readyz=200` javobi bu tashqi gate o'rnini bosa olmaydi; ular defense in depth.
Eski `docker compose up`/platform direct-release yo'li decommission qilinadi va
deploy credential faqat shu controllerga beriladi. Controller manifest epochini
DB receipt minimumiga solishtirib past rollback/deploy candidate'ni process
startidan oldin rad etadi; DB lease qatorlari expected replica inventari emas.

Har `lease_required=true` running replica alohida
`MessengerRuntimeInstanceLease` yozadi: verified release SHA + manifest hash,
role, orchestrator/process `instance_id`, supported membership/writer/schema/
event epochlar va qisqa expiry.
Uni global-name-unique `WorkerHeartbeat` bilan almashtirish mumkin emas. Expected
service/replica set manifestdagi `lease_required` + `required_when_capability` va
`docker compose config`/platform process inventorysidan olinadi; cutover faqat
shu expected candidate lease’lari fresh/mos va eski mutating release lease’lari
drained/expired bo‘lishini talab qiladi. Mapping-only process lease’i kutilmaydi.

`MessengerRuntimeEpochGuard` lifecycle’i:

1. settings, `AppConfig.ready()` va module import vaqtida DB query **0**;
   fresh/empty/pre-receipt DBda `migrate`, `collectstatic` va schema inspect
   ishlaydi;
2. trusted controller admissionidan keyin va migrationdan so'ng, traffic/
   mutation/claimdan oldin har tegishli executable
   `python manage.py check_messenger_epoch --role <role> --release <sha>
   --manifest deploy/messenger-runtime-epochs.json` gate’idan o‘tadi, keyin
   `lease_required=true` bo'lsa shared wrapper orqali lease register/renew
   qiladi. Mismatch processni fail-closed to'xtatadi. `runbot`/Telegram ingress
   canonical write qilsa ayni guard+lease'dan o'tadi; schedulerning o'zi mutation
   qilmasa artifact/wrapper mappingi tekshiriladi, lease yozmaydi;
3. `/healthz` faqat process liveness bo‘lib qoladi va Compose restart loop
   yaratmaydi. Alohida web `/readyz` shu web release/manifestning receipt/schema
   compatibilitysi va faqat traffic-critical dependencylarni tekshiradi; Caddy
   upstream active health `/readyz`dan foydalanadi. Ancillary Celery/Telegram/
   messenger-event executor lease yoki oddiy lag stale bo‘lsa butun LMSni
   yiqitmaydi: Control Center alert + durable pending/HTTP polling degraded mode,
   har workerning o‘z prestart/claim guard’i. Faqat oldindan named critical lag
   thresholdi aniq pause/flag semantikasi bilan web readinessga kirishi mumkin.
   Readinessning o‘zi fence emas: deploy/prestart gate va keyingi service-entry
   guard authority;
4. har membership decision, canonical write va worker/outbox claim service
   entry’sida epoch transaction ichida qayta assert qilinadi; DB/receipt
   unavailable bo‘lsa mutation/claim0, authorized safe read-only projection;
5. backfill tugagach imkonli `NOT NULL`/check/unique constraintlar eski direct
   Message writer’ni DBda ham fail-closed qiladi.

Shared pause/drain skeleti **ikki alohida admission** sifatida bajariladi;
membership va writer bitta singular receipt emas:

1. MSG1.2b writer admissioni: trusted controller artifactni offline verify qiladi
   → expand migrate → cutover-aware processesni compatibility/shadow mode'da
   start/lease prove qiladi → new-write admissionni pause → old writer va V1
   compatibility broadcastlarni drain qiladi → eski mutating lease0 → final
   message catch-up/count/hash/quarantine → constraints → locked transactionda
   immutable `MessengerCutoverReceipt` + minimum writer/schema epoch → compatible
   readiness/traffic → send smoke. Membership receipt hali0;
2. MSG1.2c initial membership+event admissioni: exact sequence **va** event
   boundarylari `final`, shadow diff/quarantine0 va conditional event-executor
   lease ready bo'lgach membership/event admission pause qilinadi; V1 projection
   drain bo'ladi. Bitta DB transaction membership singleton va event route'ni
   lock qilib `MessengerMembershipCutoverReceipt` hamda initial
   `MessengerEventTransportRoute` transition receipt/generation + minimum
   event/schema epochni yozadi va ikki
   authorityni birga almashtiradi. Commit oldidagi crash = receipt0/V1 shadow;
   commitdan keyingi crash = canonical membership+event-v2, admission paused va
   resume smoke'dan davom; interstitial mixed authority yo'q. Keyingi event
   transport rollback/transition membership receiptini hech qachon bekor qilmaydi.

Har admissionda receipt yozilishidan oldingi abort faqat yangi cutover-aware
compatibility adapter bilan resume qiladi; drained eski binary qayta yoqilmaydi.
Receipt'dan keyin pre-fence image/binary deploy yoki rollback taqiqlanadi;
rollback faqat trusted controller orqali receipt minimumiga teng/yuqori release
va renderer/capability flaglari bilan.

Test: empty/pre-table DB migrate/collectstatic; receipt mavjud + simulated old
web/worker/outbox/runbot; two replicas same role; stale/missing/extra lease;
capabilityga conditional required-role inventory; `/healthz` liveness va
`/readyz` 503 ajralishi; old image manifest/label/wrapper commandisiz yoki
`/readyz=200` bilan ham trusted-controller traffic0; direct old compose/platform
release credential bypass0; Caddy/deploy gate; writer va atomic membership+event
cutoverning har crash boundarysida resume/abort; unsupported runtime → traffic/
readiness/write/access/claim fail-closed, legacy participant authority va direct
writer effect0.

### 11.4 Audited settings va user preference

Flag capabilityni boshqaradi. 65 536-byte Daphne frame/message ceiling source va
deploy artifactdagi immutable security hard cap; owner UI/runtime setting uni
oshirmaydi. Attachment type/signature/parser allowlist ham pre-vetted code yoki
named reviewed profile bo‘lib, generic settings bilan almashtirilmaydi.
Quyidagilar shu hard cap/allowlist ichidagi audited runtime policy:

- domain text limiti, upload size/room quota va rate/time budgetlari;
- hard upper bound ichidagi concurrent socket cap hamda heartbeat/idle timeout;
- edit/delete window;
- unanswered response window;
- notification quiet-hour default;
- approved parser resource/size/time limitlari (type allowlist emas);
- retention/legal-hold periods;
- AI per-user attempt/queue limits.

Setting UI bo‘lsa owner-only, change reason/confirmation/audit/CAS va safe
range va immutable hard capdan yuqori qiymat reject. Secret/provider token bu
modelga yozilmaydi. Userning mute/quiet/channel tanlovi o‘z
`ChatMembership`/preference rowida; system flag emas. Telegram raw body preview
preference’i mavjud emas.

### 11.5 Rollback tartibi

Incident turiga mos, eng tor capabilitydan:

1. `messenger_ai_shared_room` / `messenger_ai_vision` / `messenger_voice_notes`;
2. `messenger_ai_retry_controls` — new retry/regenerate0, result read-only;
3. `messenger_ai_grounded_context` — remote explanation0, local safe handoff;
4. `messenger_ai_runs_v2` — AI paused, human chat qoladi;
5. `messenger_notifications_v2` — claim pause, outbox saqlanadi;
6. moderation/teacher/search/reply/upload enhancementlari;
7. `messenger_inbox_v2` — safe server/legacy renderer;
8. event transport — HTTP/history/polling;
9. read projection;
10. writes faqat data-integrity incidentda pause; old unsafe writerga qaytish yo‘q;
11. membership route faqat cutover receipt **oldidan** va shadow parity mavjud
   bo‘lsa old projectionga; receipt’dan keyin fail-closed/read-only.

Rollback candidate image avval candidate tashqarisidagi trusted deploy controller
tomonidan receipt minimum epochi, image label/`SOURCE_VERSION`, manifest hash va
process wrapperlari bo'yicha offline tekshiriladi; past binary “last known good”
bo'lsa ham ishlatilmaydi. Candidate o'zini tekshirishi yoki `/readyz=200`
qaytarishi admission dalili emas; direct eski compose/platform yo'li yo'q.

Rollback har safar DB count/readback, pending outbox/run, old/new URL, attachment
access va safe send/read smoke bilan. Migration down normal production rollback
emas.

---

## 12. Test va qabul matrixi

### 12.1 Majburiy avtomatik contractlar

**Model/DB**

- room-kind/subject, membership role/state/visibility;
- UUID, message sequence, room event cursor va nonce/operation unique;
- legacy idempotency-origin/provenance, human/AI/system sender/run/service checks;
- reply same-room, revision/version, attachment state;
- receipt/outbox/run lease, transport route va runtime instance lease unique;
- delete FK behavior va migration empty/legacy;
- SQLite parity va PostgreSQL real lock/concurrency.

**Authorization/privacy**

- anonymous, inactive, active/expired/frozen/pending learner;
- assigned/unassigned instructor, ordinary staff, support, owner;
- room list/history/search/send/edit/delete/read/upload/download/event/worker;
- join/leave/transfer/history boundaries;
- break-glass reason/expiry/audit;
- Django admin add/change/inline/search orqali body/prompt/memory bypass0;
- CSRF barcha cookie-auth HTTP mutationlarda; non-upload streaming body cap;
- log/metric/event/Telegram body/token/PII leak0.

**Idempotency/concurrency**

- same key same payload, same key different payload;
- parallel unique message sequence va event cursor;
- ACK lost, duplicate/out-of-order/event-cursor gap; hidden-audience hole +
  scanned-through watermark; history sequence gap;
- broker accepted-but-error, worker/storage/provider crash;
- Telegram webhook/update replay;
- multi-tab send/read;
- outbox/run lease expiry and reclaim.
- historical seed fanout0, V1↔V2 pause/drain/generation crash boundaries;

**AI**

- entitlement/quota/supply reservations;
- revoke before claim/provider/write;
- released/locked lesson and teacher course scope;
- barcha non-AI group/direct/support roomlarda private memory/progress0;
- system-role/untrusted injection corpus;
- selected attachment only, vision capability;
- evidence/citation/deep-link access;
- retry/regenerate/cancel/unknown;
- A9 metrics/sample gate.

**Upload/retention**

- MIME/extension/signature/dimension/page/size/parser limits;
- DB/storage partial failure, object orphan/missing/hash;
- quota, lifecycle, delete/legal hold/purge rerun;
- account anonymization/export foreign scope.

**Frontend/a11y/performance**

- no-JS read/send/pagination/validation;
- reducer duplicate/gap/unknown/multi-tab;
- query count/index and DOM bound;
- 320px/400%, 200% text, keyboard/IME/focus;
- `role=log`/status cadence;
- native AT/device evidence alohida.

### 12.2 Yakuniy browser va end-to-end ssenariylar

1. Active learner unified Inboxda barcha va faqat o‘z group/direct/AI roomsini
   ko‘radi; filter/back/draft saqlanadi; logout/account switchda boshqa userga
   draft leak0.
2. “Kurs ustozingiz” aynan `Course.instructor`ga boradi; boshqa superuser/staffga
   yo‘q.
3. Instructor faqat assigned course/cohort queue; foreign URL/search/event 404.
4. Instructor transfer MSG-D2 history siyosati va audit bilan.
5. Page/history/search GET oldin/keyin row/state count bir xil.
6. 100/101/5 000 xabar: latest, older, around va reconnect gap no duplicate/gap.
7. ACK DB commitdan keyin yo‘qoladi; refresh/reconcile ayni Message/receiptni
   topadi, resend0.
8. 20 parallel same nonce bitta message/outbox; boshqa payload 409.
9. Channel/Redis down: HTTP receipt/history saqlanadi; recovery event gapni
   to‘ldiradi. Ikki shared event orasidagi boshqa audience eventi leak/refetch
   loop bermaydi; historical seed notification/network0 va V1↔V2 cutover crashda
   bitta render yoki refreshda topiladi.
10. Hidden tab read qilmaydi; visible watermark ikki device’da monotonic; peer
   read eventi shared room streamga chiqmaydi.
11. Other-room message inbox badge/previewni reloadsiz yangilaydi.
12. Revoke/logout/password change open socket, queued send va provider gate’iga
   yetmagan delayed workerni yopadi: provider/notification0. In-flight provider
   bo‘lsa late output publish0 va physical call metered.
13. Foreign origin/malformed/oversize/rate-limit write0 va stable error;
   1–6 socket ishlaydi, 7-si rad, cache outage HTTP fallback; WebSocket hamda
   non-upload HTTP chunked/forged-length 65 537-byte body effect0.
14. Ordinary staff AI/private body/snippet/searchni ko‘rmaydi; MSG-D13 admitted
   bo‘lsa owner break-glass reason va audit bilan exact roomni ko‘radi, aks
   holda owner global body accessi ham 0.
15. Telegram duplicate/retry bitta outbox; raw body/filename/AI output0;
   mute/quiet/access respected; 429 recovered.
16. MIME spoof/slow/cancel/retry attachment bitta private ready object; foreign/
   deleted download 404.
17. Edit stale tab 409; delete tombstone/reply/search/attachment retention copy
   mos.
18. Reply/deep-link revoked sourcega leak bermaydi; course/SIT/Classbook card
   canonical object unavailable holatini aytadi.
19. Group va tutor/private/support room `@azure` provider/memory query0; oddiy
   human message saqlanadi.
20. MSG-D4 qaroriga mos entitlement: denied holatda history o‘qiladi va new
   provider/supply0; admitted private request bitta logical run/output.
21. Locked lesson, foreign course, untrusted PDF/RAG/memory injection outputga
   maxfiy context chiqarmaydi.
22. Provider crash/unknown/cancel/retry/regenerate: transport replay attempt0;
   generation cycle context embedding≤1 + primary/fallback generation≤2
   (foreground≤3), linked derivative memory batch≤1 va end-to-end lineage≤4;
   har physical call bitta attempt+supply row, parent XOR cycle/derivative;
   `provider_started` crash auto-recall0, explicit linked retry; raw exception0.
23. No-JS latest history/pagination/text POST/PRG ishlaydi.
24. 320/360/390px, 400% zoom, 200% text, virtual keyboard, long text; page
   horizontal overflow0.
25. Keyboard+IME, NVDA, VoiceOver, TalkBack transcript/send/older/unknown/dialog
   flowlari.
26. Retention dry-run count/hash → approved apply → rerun0; legal hold skip;
   backup/restore readback.
27. Flaglar `11.5` teskari OFF; new data/history/attachments o‘qiladi, old unsafe
   writer/provider/direct Telegram qaytmaydi; old release/image epoch prestart/
   service-entryda rad, ancillary worker outage esa LMSni to‘liq yiqitmaydi.

### 12.3 Test buyruqlari

Har command real kalit va `.env.local`siz:

```powershell
$env:AZURELMS_SKIP_ENV_FILE='1'
$env:APP_ENV='local'
$env:LOCAL_USE_REMOTE_SERVICES='False'
$env:GEMINI_API_KEY=''
$env:TELEGRAM_BOT_TOKEN=''

.\venv\Scripts\python.exe manage.py check
.\venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\venv\Scripts\python.exe manage.py test messenger --noinput --verbosity 1
node --test tests/frontend_v1/*.test.mjs
```

Cross-domain slice tegsa kamida:

```powershell
.\venv\Scripts\python.exe manage.py test messenger core.test_private_media core.test_upload_validation bot.test_outbox_lease bot.test_outbox_miniapp_link aicontrol.tests --noinput --verbosity 1
```

Final admitted stage:

```powershell
.\venv\Scripts\python.exe manage.py test --noinput --verbosity 1
.\venv\Scripts\python.exe manage.py system_audit --json --fail-on never
.\venv\Scripts\python.exe .tools\docs-sync\verify_docs.py
git diff --check
```

PostgreSQL + Redis/channel layer required CI `integration`da; parallel writer/
lease tests SQLite yashil bo‘lishi bilan yopilmaydi. Real Gemini/Telegram faqat
owner-approved budget/credential muhitida va bu offline commandlardan alohida
qayd etiladi. Test logidagi mocked failure matni real provider chaqiruvi deb
hisoblanmaydi.

### 12.4 Manual evidence formati

Har device/AT case:

- build SHA, flaglar, browser/OS/device/AT version;
- test account/role va synthetic data fixture;
- viewport/zoom/text spacing/theme/network;
- exact steps va expected/actual;
- screenshot/video kerak bo‘lsa PII redacted;
- console/network error va query/latency summary;
- PASS/FAIL/BLOCKED va issue link.

Ownerning “ko‘rdim”i texnik testni, automated axe esa native screen readerni
almashtirmaydi.

---

## 13. Keyingi agent uchun bajarish protokoli

### 13.1 Ishni boshlashdan oldin

1. Root `AGENTS.md`, [agent qoidalari](../rules-for-agents.md), marinebookning
   so‘nggi 3–5 yozuvi, [joriy holat](../README.md) va shu rejaning tegishli
   slice’ini to‘liq o‘qing.
2. `git status --short --branch`, `git log --oneline --decorate -8`,
   `git branch -a`. Begona uncommitted o‘zgarish bo‘lsa tegmang.
3. `main`ni fetch qilib `codex/<slice-name>` yoki agentga mos prefiks branch;
   bitta checkout, worktree yo‘q.
4. Joriy kod plan dalilidan o‘zgargan bo‘lsa avval characterization; plan
   matnini ko‘r-ko‘rona implement qilmang.
5. Bitta aniq slice tanlang. “Messenger redesign” nomli ko‘p-bosqichli PR
   ochmang.
6. Slice owner qaroriga bog‘liq bo‘lsa `14`dagi kodni tekshiring. Safe default
   yozilgan bo‘lsa ham owner qarori deb soxtalashtirmang.

### 13.2 Har slice ish tartibi

1. **Characterize:** bug/riskni yiqiladigan test yoki read-only report bilan
   isbotlang.
2. **Inventory:** barcha writer/reader/adapter call sitelarini `rg` bilan toping;
   faqat ko‘ringan bir viewni patch qilmang.
3. **Contract:** input, output, permission, state, idempotency, failure va
   rollbackni test nomlarida yozing.
4. **Expand:** migration bo‘lsa nullable/additive; drop/rename keyin.
5. **Service first:** business rule canonical policy/service’da; adapter yupqa.
6. **Concurrency:** receipt/sequence/lease uchun SQLite ham, PostgreSQL ham.
7. **Failure:** broker/cache/storage/provider/audit xatosi; no silent fallback.
8. **Privacy:** event/log/notification/search/backoffice/attachment projection.
9. **Compatibility:** legacy/V1, flag ON/OFF va existing URLs.
10. **Verify:** `12.3` safe env, targeted + affected cross-domain + Node;
    migration drift/diff check.
11. **Evidence:** count/hash/metric/browser/rollback chegarasi; real provider/
    device bajarilmagan bo‘lsa aniq ayting.
12. **Commit/PR:** logical commit, Co-Authored-By trailer, marinebook, push,
    required CI, review, manual merge va branch cleanup — agent qoidalariga ko‘ra.

### 13.3 Tavsiya etilgan PR navbati

| # | Slice | Old shart | PR chiqishi |
|---:|---|---|---|
| 1 | MSG1.0a1 | yo‘q | dedicated Origin gate + Daphne frame/message ceiling |
| 2 | MSG1.0a2 | 1 | legacy-compatible schema/text/binary boundary |
| 3 | MSG1.0a3 | 2 | rate limit + live-session revoke; persisted replay hali deferred |
| 4 | MSG1.0b | 2–3 | all AI adaptersda group/access/vision/error containment |
| 5 | MSG1.0c | 4 | direct Telegram yo‘q; delivery truthful paused, durable claim deferred |
| 6 | MSG1.0d | yo‘q; shared-file coordination | scoped backoffice/no-store; D13 bo‘lsa break-glass |
| 7 | MSG1.0e | 2 | legacy latest rooms/history va truthful status |
| 8 | MSG1.1a | 1–7 | read-only integrity report |
| 9 | MSG1.1b | 8 + D14 for AI constraint | room/membership + dual-cursor expand schema |
| 10 | MSG1.1c | 9 + D1/D2/D14 | resumable membership backfill/shadow |
| 11 | MSG1.1d | 8–9 | message/receipt/event/delivery expand |
| 12 | MSG1.2a | 9–11 + D1/D2/D12/D14 | canonical room policy + membership dual-write/shadow; receipt deferred |
| 13 | MSG1.2b | 4, 11–12 | all runtime message writers/receipt/message sequence + V1 compatibility broadcast |
| 14 | MSG1.2c | 12–13 | event cursor/outbox/protocol/gap sync + coordinated membership cutover |
| 15 | MSG1.2d | 12–14 | explicit unread/read watermark |
| 16 | MSG1.3a | 12–15 + D14 | unified SSR/no-JS Inbox |
| 17 | MSG1.3b | 14–16 | resilient reducer/reconcile/multi-tab |
| 18 | MSG1.3c | 16–17 | mobile/keyboard/AT acceptance |
| 19 | MSG1.4a | 14–18 | reply/deep-link/context/date |
| 20 | MSG1.4b | 11, 19 + D3 | revision/edit/delete/tombstone |
| 21 | MSG1.4c | 15–19 | scoped search/pin/per-user archive |
| 22 | MSG1.5a | 11, 13–17 | upload session/sniffed metadata |
| 23 | MSG1.5b | 22 + D3 | lifecycle/quota/reconciliation |
| 24 | MSG1.5c | 18, 22–23 + D3 approved/D8 ADMIT | optional human voice |
| 25 | MSG1.6a | 4, 13–14 + D4 | AI logical run/attempt/receipt/entitlement |
| 26 | MSG1.6b | 25 | context/system/evidence |
| 27 | MSG1.6c | 17, 25–26 | retry/regenerate/adapter parity |
| 28 | MSG1.6d | 25–27 + D3/D11 + A8 | A9 evalni yaratish; PASS/owner review rollout gate |
| 29 | MSG1.7a | 5, 14–15 + D10 | durable notification projector/outbox + preference |
| 30 | MSG1.7b | 12, 16, 19 + D6/D12 | teacher Inbox/handoff |
| 31 | MSG1.7c | 20 + D7/D12; body break-glass faqat D13 ADMIT | moderation/support |
| 32 | MSG1.8a | 20, 23, 28–31 + D3/D13; 24 faqat D8 ADMIT bo'lsa | retention/export/anonymize |
| 33 | MSG1.8b | barcha admitted runtime | scale/chaos/ops |
| 34 | MSG1.8c | 1–33 dispositioned; barcha admitted scope complete + CI | staged release/evidence |

MSG1.0c/d/e code-touch to‘qnashmasa mustaqil read/review qilinishi mumkin,
lekin loyiha qoidasi bo‘yicha bitta checkoutda parallel edit yo‘q. Ikki agent
bir migration, policy/service yoki shared templatega bir paytda yozmaydi.

### 13.4 Stop va eskalatsiya shartlari

Agent to‘xtab ownerga aniq dalil bilan murojaat qiladi, agar:

- wrong-tutor/private room mapping bir nechta legitim talqinga ega;
- retention/purge/legal hold qarorisiz physical delete kerak bo‘lsa;
- AI entitlement/pricing contractini o‘zgartirish kerak bo‘lsa;
- migration dry-run count/hash yoki shadow access diff tushuntirilmasa;
- security fix mavjud Classbook/other socketni buzsa va safe compatible yo‘l
  topilmasa;
- PostgreSQL race/constraint SQLite natijasidan farq qilsa;
- required CI/review failure, merge conflict, data-loss yoki secret/privacy
  anomaly bo‘lsa;
- real production/provider credential, deploy yoki destructive data operation
  talab qilinsa.

“Qiyin” yoki “ko‘p ish” stop sababi emas; owner authority yoki xavfsiz ma’no
yetishmasligi stop sababi.

### 13.5 Stage evidence hujjati

Har katta phase tugaganda `MESSENGER-01-STAGE-<N>.md`:

- scope va non-scope;
- commits/PR/CI run;
- schema/backfill/flag/settings;
- test count/command/backend/skip;
- browser/device/AT/provider/Telegram dalili;
- KPI before/after yoki `not measured`;
- rollback drill;
- remaining risk/owner decision;
- next exact slice.

Rejadagi matn bajarildi deb o‘chirib yozilmaydi; stage evidence va joriy holat
sahifasi real natijani qayd qiladi.

---

## 14. Ochiq owner qarorlari

Bu qarorlar tegishli slice oldidan olinadi. Ularning ko‘pi MSG1.0a1–a3 Origin,
transport/input/session cap, backoffice least privilege va legacy correctnessni
boshlashga blocker emas. D4 entitlement cutoverini, D13 esa optional
break-glassni bloklaydi; ular safe containmentni bloklamaydi.

| ID | Qaror | Tavsiya etilgan safe default | Bloklaydi |
|---|---|---|---|
| MSG-D1 | Academic direct room identiteti learner+coursemi, learner+cohortmi yoki globalmi? | **learner + course**; support alohida | MSG1.1c, 1.2a |
| MSG-D2 | Yangi learner/instructor oldingi group/direct tarixni qayerdan ko‘radi? | group: cohort start/join policy; direct: membership join; instructor transfer explicit owner audit | MSG1.1c, 1.2a |
| MSG-D3 | message, attachment, revision, receipt, AI raw/derivative va audit retention; edit/delete window? | qarorgacha destructive purge yo‘q; tombstone; edit uchun mahsulot taklifi 15 daqiqa, lekin owner tasdiqlaydi | MSG1.4b, 1.5b destructive part, 1.5c, 1.6d delete, 1.8a |
| MSG-D4 | Active enrollment/typed entitlement yo‘q user remote AI yubora oladimi? | history read-only, yangi remote call uchun `AI_TUTOR`; bepul tier bo‘lsa alohida entitlement/quota | MSG1.6a typed cutover; MSG1.0b faqat shadow evidence |
| MSG-D5 | 1:1/group read receipt va presence kerakmi? | self-unread; 1:1 receipt keyin; group per-user receipt/presence HOLD | receipt UI beyond MSG1.2d |
| MSG-D6 | Ustoz javob oynasi/SLA qancha va business-hours bormi? | o‘lchov avval, deadline claim keyin | MSG1.7b |
| MSG-D7 | Report/moderationni kim boshqaradi, appeal bormi? | owner named moderator; least privilege; hide+audit, hard delete emas | MSG1.7c |
| MSG-D8 | Human voice note kerakmi? | HOLD; real need + transcript/accessibility/retentiondan keyin; pronunciation AI yo‘q | MSG1.5c |
| MSG-D9 | Group `@azure` qaytadimi? | OFF; shared-room no-private-context eval + A9 + owner pilot bo‘lmaguncha yo‘q | future shared AI only |
| MSG-D10 | Telegram generic preview nomlanishi va quiet-hours/timezone defaulti? | raw body CUT; generic sender/room + deep link, raw preview opt-in yo‘q | MSG1.7a |
| MSG-D11 | AI memory yangi userda default ONmi, explicit opt-inmi; clear nimani o‘chiradi? | shared roomda doim OFF; private uchun visible control va aniq hard-delete/retention | MSG1.6d |
| MSG-D12 | Pre-enrollment/support kimga assign va qanday handoff qilinadi? | academic tutor emas; alohida owner/support queue, explicit context/consent | MSG1.2a support, 1.7b–c |
| MSG-D13 | Body export/break-glass/legal hold vakolati va review muddati? | owner-only, exact purpose/scope/expiry/audit; bulk export OFF | MSG1.0d va MSG1.7cning faqat optional break-glass qismi; MSG1.8a export/legal-hold body-access qismi |
| MSG-D14 | Learnerning AI conversation/draft/archive modeli qanday? | bir nechta boshlangan private conversation; ko‘pi bilan bitta bo‘sh draft; SmartForm alohida; archive delete emas | MSG1.1b–c, 1.2a, 1.3a |

Tavsiya safe fallback, yashirin owner qarori emas. Owner boshqa yo‘lni tanlasa
tegishli invariant/test/UX shu hujjatda va stage evidence’da yangilanadi.

---

## 15. MESSENGER-01 Definition of Done

MESSENGER-01 faqat quyidagilarning **admitted scope’i** bajarilganda yakunlangan:

- MSG1.0a1dan MSG1.8cgacha **34/34 slice dispositioned**: har `ADMIT` qilingan
  slice code/test/docsda bajarilgan, har `HOLD/CUT` slice owner qarori, non-scope
  va UI/route/model promise0 dalili bilan; `12.2` admitted scope uchun 27/27;
- WebSocket Origin/session/schema/frame/rate/connection/idle gate va non-upload
  HTTP streaming body cap; unauthorized delivery0;
- room/membership exact subject va instructor, monotonic cutover receipt;
  GET write0;
- human send persisted nonce, payload conflict, message sequence, alohida event
  cursor va outbox/delivery bilan;
  duplicate logical send0;
- dedicated `messenger_event_outbox` process/lease/lag/recovery; historical
  fanout0 va V1↔V2 transport pause/drain cutoverda duplicate/missed refresh0;
- reconnect/gap/unknown/read/unread multi-device converge;
- draft opaque user/room namespace, bounded TTL/size, logout/account-switch leak0;
- legacy/V1/no-JS bir canonical writer va safe access policyda;
- ordinary staff global private/AI bodyga kira olmaydi; D13 admitted bo‘lsa
  break-glass audited, aks holda body access0;
- Telegram direct HTTP yo‘q; preferences/fresh access/dedupe/lease/dead-letter;
- attachment sniffed kind/private lifecycle/quota/reconciliation/retention;
- AI worker fresh access/entitlement/context, true system role, selected
  attachment, lease/idempotency/evidence; non-AI shared-room private leak0;
  A8/A9 gate;
- teacher Inbox exact scope, report/moderation va typed domain handoff;
- 320px/400%, keyboard/IME, native AT/device va no-JS evidence;
- PostgreSQL/Redis/Celery chaos/concurrency va performance budgets;
- retention/export/anonymization owner-approved va rehearsed;
- flags OFF/ON/rollback, backup/restore, Control Center/runbook;
- cutover minimum runtime/schema epoch fence, verified candidate SHA+manifest
  hash, per-instance all-role deploy inventory va per-service prestart/claim
  guard; pre-cutover binary deploy0;
- required CI/review green va owner acceptance status aniq.

Quyidagilar alohida holatlar:

1. reja yozildi;
2. kod merge bo‘ldi;
3. flag muhitda ON;
4. production deploy;
5. owner usability/privacy qabuli.

Bittasi boshqasini avtomatik anglatmaydi. Voice, shared-room AI, vision,
presence yoki streaming HOLD/CUT bo‘lib qolsa, u admitted bo‘lmaganligi aniq
qayd etiladi; core DoDni soxta yopmaydi.

---

## 16. Birinchi implementatsiya task kartasi — MSG1.0a1

Owner MESSENGER-01 implementatsiyasini keyingi aniq ish qilib tanlasa, agent
quyidagi kartadan boshlaydi.

**Maqsad:** begona/missing origin cookie-auth Messenger/Classbook socketini
ocha olmasin va CLI hamda `manage.py runserver` Daphne consumerdan oldin
65 536 bytedan katta WebSocket frame/message’ni buffer qilmasin.

**Non-scope:** Messenger command parser/text cap (MSG1.0a2), rate/session revoke
(MSG1.0a3), schema migration, Inbox, nonce/sequence, Telegram, AI, retention.

**Avvalgi dalilni testga aylantirish:**

- `core/asgi.py`da Origin validator yo‘qligi;
- `core/settings.py` local `ALLOWED_HOSTS`ida `*` borligi;
- `core/settings.py`da ikkala `DAPHNE_WEBSOCKET_MAX_*` yo‘qligi sabab local
  `manage.py runserver` 1 MiB default ishlatishi;
- Dockerfile, production compose va Procfile Daphne argv’sida frame/message
  cap yo‘qligi; root README, project-context va mobile QA runbook safe hard
  ceiling/exact Origin contractini ko‘rsatmasligi.

**Minimal fayllar:**

- `core/settings.py` va `core/asgi.py`;
- `Dockerfile`, `deploy/docker-compose.prod.yml`, `Procfile`, root `README.md`,
  canonical production `deploy/README.md`,
  `nuclear-program/project-context.md`, `nuclear-program/mobile-qa-runbook.md`,
  `deploy/env.example`;
- yangi `core/test_websocket_security.py`;
- `messenger/test_socket_access_recheck.py`, `classbook/test_realtime.py` yoki
  shu routelarni global ASGI application orqali qamraydigan regressiya testlari;
- `core/test_deploy_artifacts.py` va kerakli runbook/env hujjati.

**Implementation tartibi:**

1. Characterization testsni red qiling.
2. `WEBSOCKET_ALLOWED_ORIGINS`ni alohida env-list sifatida qo‘shing. Local
   default faqat exact `http://localhost:8000` va
   `http://127.0.0.1:8000`; test `override_settings` bilan exact origin beradi;
   non-local default/required value `https://<APP_DOMAIN>`. Scheme `http|https`,
   host va optional portdan boshqa path/query/fragment/userinfo hamda `*` rad.
   LAN/device yoki ngrok ishlatilsa runbook exact
   `http://<LAN-IP>:8000`/`https://<ngrok-host>`ni `CSRF_TRUSTED_ORIGINS` bilan
   birga talab qiladi; wildcard yo‘q.
3. Channels origin matching/deny semantikasini saqlaydigan kichik
   `BodyFreeOriginValidator(AuthMiddlewareStack(URLRouter(
   websocket_urlpatterns)), settings.WEBSOCKET_ALLOWED_ORIGINS)`ni butun
   websocket branchga outer wrapper qilib qo‘ying; stock `OriginValidator`
   rejectda sabab/log bermagani uchun wrapper `missing|null|malformed|not_allowed`
   safe code’ni origin qiymati/cookie/body'siz yozadi. HTTPga tegmang.
   `AllowedHostsOriginValidator`ni bu repo local wildcardi bilan substitute
   qilmang.
4. `core/settings.py`da immutable
   `DAPHNE_WEBSOCKET_MAX_MESSAGE_SIZE=65536` va
   `DAPHNE_WEBSOCKET_MAX_FRAME_SIZE=65536`; `manage.py runserver` commandi bu
   qiymatlarni olayotganini integration/command testda isbotlang.
5. Dockerfile, compose `web.command` va Procfile `web` commandiga ikkala exact
   argvni qo‘shing:
   `--websocket-max-message-size 65536` va
   `--websocket-max-frame-size 65536`; root README manual Daphne misolini ham
   shu caplar bilan yozing.
6. Artifact test settings va uchala CLI launch source’da caplar bir martadan,
   qiymati 65536, frame ≤ message va `0` emasligini, README/project-context/
   mobile runbook hamda canonical `deploy/README.md`da safe contract borligini
   tekshirsin.
   `docker compose config`, Procfile platform process argv va
   staging process argv readbacki runbookga yozilsin. Procfile dormant deb
   chiqarilsa, uning deployment bog‘lanishi yo‘qligiga explicit dalil va
   decommission commit talab qilinadi.
7. Allowed/foreign/`null`/missing/malformed Originni global ASGI application
   bilan Messenger va Classbook routelarida test qiling; Origin rejectda
   consumer connect/DB write bo‘lmasin.
8. `12.3` safe-env check, migration drift, focused Messenger/Classbook/deploy
   tests, so‘ng affected suite; body/cookie log0.
9. Flag kerak emas; env misoli va rollback configi PRda.

**Qabul:**

- dedicated allowed origin bilan valid Messenger va Classbook current behavior;
- foreign/null/missing origin connect0;
- har origin rejectda qiymat/cookie/body'siz stable structured reason event;
- `ALLOWED_HOSTS=*` foreign originni ochmaydi;
- settings, Dockerfile, compose va Procfile ikkala 65 536 cap bilan;
  `manage.py runserver`, README/project-context/mobile/deploy runbook safe;
  deploy argv readback yozilgan;
- 65 537-byte integration probe `manage.py runserver` va staging edge/serverda
  reject (agar focused unit production Daphne processini ko‘tarmasa, staging
  evidencega explicit ochiq gate; artifact testi unit-level substitute emas);
- secret/body log0;
- check, migration drift, focused/affected/full CI green.

**Rollback:** faqat noto‘g‘ri origin/configni verified dedicated allowlistga
tuzatish. Origin guardni olib tashlash, `ALLOWED_HOSTS`ga fallback yoki Daphne
capni `0`/unlimited qilish yo‘q.

**MSG1.0a1–a3 tugamaguncha** yangi Messenger UI, reply, voice, search, streaming
yoki AI capability PR’i boshlanmaydi. Keyingi exact slice — MSG1.0a2.
