# Claude uchun topshirish xabari — 2026-09-04

Azurbek dam olishga ketdi va Codexdan joriy ishni xavfsiz checkpointgacha
yakunlab, senga rejani tushuntirib qoldirishni so'radi. Codex keyingi premium
workflow slice'ini boshlamaydi. Butun tarif rejasi tugagan emas; payment va
catalog/delivery poydevori topshirilmoqda.

## Boshlashdan oldin

1. `AGENTS.md`, `rules-for-agents.md`, marinebookning oxirgi yozuvlari va
   `pricing-packages-plan.md`ni o'qi. To'liq owner hujjati shu kompyuterda:
   `C:\Users\azizb\Downloads\writing-block.md`; asosiy contract va keyingi
   aniqlashtirilgan qarorlar repo ledgerida saqlangan.
2. `git status --short --branch`, `git log --oneline -8`, `git worktree list`,
   `git fetch origin` bilan haqiqiy holatni tekshir. User bitta checkout va
   oddiy branchlar bilan ishlashni afzal ko'radi; yangi worktree majburiy emas.
3. [PR #70](https://github.com/azurebek/azurelms/pull/70)ning yakuniy state/checklarini
   tekshir. Bu xabar merge oldidan o'sha PRga commit qilinmoqda; merge natijasi
   haqida taxmin qilma. Codex required CI va review gate'idan keyin o'zi merge
   qilib, lokal `main`ni ff-only yangilab to'xtaydi. PR hali ochiq bo'lsa,
   Codex ishini parallel takrorlama yoki uning PRini merge qilma.
4. `main` toza va #70 kirgan bo'lsa, keyingi slice uchun o'z `claude/...`
   branch'ingni yangilangan `origin/main`dan och. Begona dirty o'zgarishga tegma.

## Nima tayyor

- #67: payment foundation — pending plan niyat, invoice plan/narx/davr snapshotlari,
  atomic/idempotent review, web/bot bitta canonical checkout/receipt yo'li.
- Sening #68/#69 tuzatishlaring saqlangan: tarif o'zi to'langan davrda kuchga
  kiradi; kirishi yopiq student approvalni kutgan kunlar uchun xizmat kunini
  yo'qotmaydi. `Enrollment.active_plan()` haqiqat, denormalized `plan` ustuni
  doim bugungi haqiqat degan taxmin qilma.
- #70 (`b5c2068`): Economic/Standard/Intensive draft katalogi, AI policy,
  plan purchase availability, cohort tier/capacity, barcha write yo'llarida
  tier/sig'im guardi va owner-only `/backoffice/catalog/` boshqaruvi.
- #70 review fix (`916de52`): pending studentning eski guruhi to'lsa/yopilsa,
  GET faqat mos bo'sh guruhni ko'rsatadi. POST/bot `relocate_pending_checkout`
  orqali eski yozuvni muzlatib, yangi pending va auditli transition yaratadi.
  Qaror kutilayotgan invoice ko'chirilmaydi; owner rad etgach retry mumkin.
  Paid enrollment/history avtomatik ko'chmaydi.

## Owner qarorlari — qayta taxmin qilma

- Joy **faqat to'lov tasdiqlanganda** band. GET yoki chek upload rezerv emas.
  Oxirgi joyga ikki approvaldan bittasi o'tadi; ikkinchi chek pending qoladi.
- AI quota **eng oxirgi faol enrollmentning effective planidan**. Maximum
  yoki sum emas. Bu multi-course algoritmini o'zgartirma.
- Uch tarifda core curriculum, homework, quiz/exam, certificate va AzureAI
  mavjud. Farq content quality emas, teacher time/service intensity.
- Economic talabaga teacher ixtiyoriy chuqur feedback bera oladi. Premium
  capability kafolatlangan xizmatni bildiradi, boshqalarga yordamni taqiqlamaydi.
- Default/maksimal capacity: 60/8/3. Narxlar: 89000/259000/399000 UZS/oy;
  AI 5h/7kun: 50k/300k, 100k/800k, 200k/1.5m. Narx/quota DB/backofficeda;
  display name yoki narxga qarab ruxsat hisoblama.
- Avtomatik paid tier upgrade/downgrade va proration hali qurilmagan.
  Eski Starter/Pro/Premiumni yoki mavjud a'zoliklarni majburan almashtirma.

## Keyingi ish: service workflows, kichik tekshiriladigan slice'lar

Avval mavjud `courses.models.Assignment/AssignmentSubmission`,
`courses.submission_service.review_assignment_submission`, teacher web/bot
adapterlari, `core.entitlements` va teacher course scope'ini tekshir. Mavjud
feedback/review bor: shuni kengaytir, parallel submission yoki review engine
yozma. Yangi rule/capability uchun nuclear admission savollarini ledgerga
yozib, owner tasdiqlagan tarif rejasiga bog'la; scope tashqarisiga chiqma.

1. **Standard individual feedback.** Muhim ochiq javob/writing/speaking
   vazifalarini teacher navbatida ko'rsatish, individual feedback va zarur
   resubmissionning izchil holati. Student natijani ko'rsin. Economic'dagi
   submission, mavjud feedback va o'qituvchining ixtiyoriy yordam huquqi saqlansin.
   Birinchi maqsad: va'da qilingan review navbatda yo'qolmasin va teacherga
   ortiqcha qo'lda ro'yxat yuritish kerak bo'lmasin.
2. **Intensive personal assignment + progress review.** Faqat adresat ko'radigan
   teacher task; kuchli/zaif tomonlar, recurring mistakes va keyingi tavsiyaga
   ega teacher note/report. Mavjud progressni ishlat; dalilsiz AI tashxisini
   canonical learning statega yozma.
3. **Priority feedback/support.** Shu mavjud navbat/control plane orqali
   priority; alohida dublikat navbat emas. Teacher ownership/default-deny
   scope saqlansin. Real SLA bo'lmasa "24/7 teacher" va'da qilinmasin.
4. **Presentation + analytics.** Runtime tayyor bo'lgach uch pricing card,
   Standard highlight, feature matrix, dashboard plan/cohort/teacher/payment/AI
   allowance holati. Occupancy, haqiqiy revenue, AI usage, teacher review
   workload va renewal metrikalarini canonical yozuvlardan chiqar.

Har slice alohida test/commit/PR/marinebook bilan tugasin. Bot/web biznes
qoidalarini takrorlamasin. Barcha xizmatni bitta katta WIPga yig'ma. Mustaqil
product qaror kerak bo'lsa, mavjud admission doirasidagi boshqa xavfsiz ishni
qil yoki checkpointda to'xta; uxlayotgan owner nomidan taxminiy qaror olma.

## Rollout va tegilmaydigan ishlar

- Yangi uch paket **sotuvga yopiq**. Premium workflow/copy va mos real guruh
  tayyor bo'lmasdan ochma. Eski tariflar yangi sotuvdan ham avtomatik yopilmagan;
  rollout alohida tekshiriladi, eski paid renewal/access/history saqlanadi.
- Course detaildagi eski "Cheksiz AI repetitor" / "umrbod kirish" matni
  presentation bosqichida haqiqiy quota/to'lov contractiga moslanishi kerak.
- Gemini global supply/budget guardini bo'shatma: plan allowance provider
  throughput kafolati emas. Testda haqiqiy API/token ishlatma.
- Sening oldingi daily subscription job dedup kuzatuving bu slice'ga kiritilmadi:
  Celery va ikki management commandni birlashtirish alohida ish bo'lib qoladi.
  A6/A7/A9/A10 kabi boshqa backlog bandlariga pricing bahonasida o'tma.
- QA server va tablar yopilgan; dev server/tunnel hozir ishlayapti deb taxmin qilma.

## Test va DB dalillari

PowerShell, repo ildizi, `venv\Scripts\python.exe` (3.12). Har testdan oldin:

```powershell
$env:AZURELMS_SKIP_ENV_FILE='1'
$env:GEMINI_API_KEY=''
$env:TELEGRAM_BOT_TOKEN=''
```

- `python manage.py test --noinput`: **1123 OK, skipped=29**.
- `AZURELMS_TEST_FILE_DB=1` bilan `python manage.py test
  cohorts.test_delivery_catalog cohorts.test_payment_plan_integrity
  cohorts.test_single_pending_receipt subscriptions.test_catalog --noinput`:
  **67/67 OK**, shu jumladan haqiqiy parallel approval sinovi.
- Handoff CI eski approve/reject race testidagi kelasi davr tarifi darhol
  yoqilishi kerak degan assertionni topdi. U #68ga zid edi va `main`da ham
  bor edi. Runtime o'zgarmadi; eski expectation approve-first holatida
  deterministik yiqilishi ko'rsatilib, test bugungi old quota/plan va kelasi
  davrdagi new plan/deadline contractiga tuzatildi. Unordered race saqlanib,
  ikkala winner tartibiga alohida test qo'shildi. Bu ikki file-backed test
  in-memory suite'da mavjud platform guardi sabab skip qilinadi.
- `check --fail-level WARNING`: 0 issue; `makemigrations --check --dry-run`:
  no drift; `scan_secrets`: toza. Eng oxirgi required CI natijasi PR #70da.
- 390px/1280px, light/dark browser QA va haqiqiy plan-radio/narx/sig'im
  amallari o'tdi. Real telefon, mikrofon, Telegram, bank sign-off'i emas.
- Local additive migrations `subscriptions.0006/0007`, `cohorts.0017` qo'llangan.
  Backup: `backups/db-20260904-070703.sqlite3` (gitda emas). Old/new SQLite
  solishtiruvida 125 jadvalning eski ustun/yozuvlari bo'yicha yo'qotish/o'zgarish
  **0**; yangi uch plan draft, eski cohortlar null/null. Schema rollback bilan
  tarix ustunlarini o'chirma, backupni overwrite qilma.
- Pre-existing Windows qarzi: **butun** file-backed suite backup/restore testida
  ochiq WAL handle sabab `WinError 32` berishi mumkin. Baseline dalili ledgerda.
  Buni green deb ko'rsatma yoki yangi capacity regression deb taxmin qilma.

Handoffdan keyingi birinchi yaxshi checkpoint: Standard feedback slice'i,
permission/resubmission/adapter parity testlari, browser smoke va toza PR.
