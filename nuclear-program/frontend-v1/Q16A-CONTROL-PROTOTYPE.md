# Q16a — nazorat va AI boshqaruvi prototipi

Sana: **2026-09-27**. Source bazasi `b6225bb` (Q15b main).
Branch: `codex/q16a-control-prototype`. D31, owner “davom et”.
Paket70 source/test/rasmlari ignored `playground/Eleventh Trial`da;
Gitga faqat dalil/reja kiradi. **Runtime, DB, AWS, flag va providerlar o‘zgarmadi.**

## Admission

**EXPERIMENT — canonical state yozmaydi.** Owner bitta nazorat nuqtasidan
holatni ko‘rib, ta’sir/sabab/tasdiqdan keyin aynan o‘z qarorining natijasini
o‘qiydi. Mezon: 8 canonical UI, 7 runtime panel, 24 flag va takroriy/stale/
unknown-result holatlarida no accidental double-write. Haftalik operatsion
yuk qo‘shilmaydi: bu lokal sinov, yangi monitoring servisi yoki worker emas.
Yangi product flag, migration, provider qo‘ng‘irog‘i, quota/narx/access
formulasi yo‘q. Rollback: lab reset yoki saqlangan Paket69 checkpoint.
Real adapter kelajakda quyidagi canonical view/form/servicega ulanadi;
preview receipt/revision mexanizmi backend capabilitysi deb ko‘rsatilmaydi.

## Qamrov va source chegarasi

| ID / real UI | Lokal holat |
|---|---|
| U12 `backoffice_control` | 16 capability, GREEN/AMBER/RED sintetik snapshot, vaqt/release/config, runbook va boshqaruv havolalari |
| U13 `backoffice_feature_flags` | 24 canonical flag; standart/override va ta’sir; bitta aniq flag formasi; orphan tushuntirishi |
| U14 `backoffice_runtime_settings` | 7 alohida panel; source maydon/birlik/bounds/help; saqlangan qiymat qoralamadan alohida |
| U15 `backoffice_ai_cost` | Narxlanmagan sarf nol emas; sanali append-only narx; provider/model/sana duplicate rad |
| U16 `backoffice_dead_letter` | Aniq DM/guruh xabarlari; doimiy xatoga ikkinchi tasdiq; navbatga qaytish yetkazildi degani emas |
| U17 `backoffice_ai_control` | Usage/global/tarif/reset-bonus maydonlari va action chegarasi **read-only**; A2-D01 ochiq |
| U18 `backoffice_ai_kill_switch` | Remote-call kaliti; sabab/tasdiq; circuit yoki kvota o‘zgarmaydi |
| U19 `backoffice_ai_circuit_reset` | Faqat cooldown; asosiy kalit/kvota o‘zgarmaydi; takroriy no-op |

Registry `0.70.0-control-operations`: **116 route /64 page template /
95 source nomi /1032 route-state /188 action**. 8 URL bitta qayta ishlatiladigan
page template va alohida AI boundary partial orqali chiziladi; bu 8 xil yangi
shell emas. Mavjud platform shell, tokenlar, breakpoints va asosiy menu saqlandi.
Backoffice’dan “Nazorat” lokal havolasi bor; ichki 8 bo‘lim disclosure navda.
Runtime/flag tanlovi URLda; lab holati yoki login orqali qaytishda saqlanadi.

Manbalar: `core/views.py`dagi sakkiz view; `core/flags.py`,
`core/control_center/registry.py`, `snapshot.py`; flag/runtime/cost/dead-letter/
kill-switch/circuit formalar; `core/ai_cost.py`, `bot/dead_letter.py`, tegishli
core/bot/users/library model validatorlari va `users/reminder_settings.py`.
Lokal extraction vositasi metadata/defaultlarni **AST orqali** oladi, domain
modul importi yoki env/DB o‘qishi yo‘q. Kutubxona source defaulti **50 MB**.

## Natija va himoya

- Native GET o‘zgartirmaydi. POST→303→GET; before/after/sabab va aniq receipt.
  O‘zgarmagan qiymat uchun yangi audit yozilmaydi. 64 ta natija limiti;
  oldingi natijalar evict qilinmaydi, yangi urinish429 bilan yopiladi.
- Run/revision/UUID/payload/origin va field/query allowlist. Noma’lum yoki
  takroriy parametr400; stale/reset/payload rebinding409; invalid422.
  Scope/auth/CSRF fail-closed; private store umumiy learner/teacher snapshotga
  chiqmaydi. O‘zgarish clone’da tekshiriladi; faqat muvaffaqiyatda almashtiriladi.
- Empty/locked403, expired401, offline/error503 yozmaydi. Unknown503dan
  keyin submit yopiq; exact GET natijani tiklaydi, yangi amal bajarmaydi.
- Qoralama run/URL/selection/revisionga bog‘langan. Consent, xabar tanlovi,
  CSRF/operation saqlanmaydi. Native Back’dan keyin tasdiq qayta belgilanadi.
  Eski result faqat o‘z draftini tozalaydi; boshqa panel qoralamasi qoladi.
- Runtime ordered AMBER/RED, backoff/window hamda numeric bounds tekshiriladi.
  Har panel o‘z maydonlarini yozadi. Library/file type allowlist o‘zgarmaydi.
- Narx snapshoti o‘qish hisobotini bu previewda qayta hisoblamaydi: hisobot
  oldindan yozilgan namuna ekanligi aniq. Real pul/AI kvotasi hisoblanmaydi.
- Dead-letter preview no-opni ko‘rsatish uchun shu sinovning navbatga qaytgan
  qatorlarini ham saqlaydi; source ro‘yxati esa terminal qatorlar bilan
  yangilanadi. Bu farq UI’da aytilgan, real portda canonical selection qoladi.

## A2-D01 — ochiq; Q16a UI bilan yopilmadi

Eski `save_settings` va `save_policy` sabab/tasdiq/SystemAuditEvent bermaydi.
`apply_event`ning o‘z event yozuvi ularni auditlangan qilmaydi. Prototipda
uchala actionga POST405, “saqlandi” degan soxta natija yoki kuchaytirilgan
backend kafolati yo‘q. **U17 to‘liq write-parity ochiq**. Alohida owner admission
→ canonical service/form/tests → yangi adapter contract kerak.

Q16a UI borligi production RBAC, durable audit, concurrent idempotency,
source locking, real health probes yoki AWS release qabuli emas. Owner
walkthrough, native iOS/Android/AT va umumiy G2/G3 ochiq.

## Tekshiruv

Trial cwd: `C:/Users/azizb/Desktop/project/azurelms/playground/Eleventh Trial`.
`AZURELMS_SKIP_ENV_FILE=1`, `GEMINI_API_KEY`/`TELEGRAM_BOT_TOKEN` bo‘sh,
`LOCAL_USE_REMOTE_SERVICES=0`.

```powershell
& 'C:/Users/azizb/Desktop/project/azurelms/venv/Scripts/python.exe' manage.py check
& 'C:/Users/azizb/Desktop/project/azurelms/venv/Scripts/python.exe' manage.py test tests --verbosity 1
$trialTestFiles = @(Get-ChildItem -LiteralPath tests -Filter '*.test.mjs' | ForEach-Object FullName)
node --test @trialTestFiles
```

- Check0; birinchi full686 PASS (256.664s); **yakuniy full688 PASS
  (245.802s)**. **178 Node PASS**, yangi4 draft codec testi;
  yangi JS modullarining syntax checki PASS.
- 10 ko‘rinish (8 default + runtime-delivery va flag editor) ×5 kenglik
  (320/390/640/1024/1440) ×2 tema = **100 geometriya tekshiruvi**:
  horizontal overflow0, ko‘rinadigan owned control height ≥44px.
- Native browser: runtime30→45/readback; reload draft va unchecked consent;
  boshqa panel drafti eski result→Back/reloaddan keyin saqlanadi;
  permanent missing-ack422→bound input/focus→consent→queued result;
  uncertain kill503→disabled submit→exact result; circuit change→no-op;
  flag override va append-only narx saqlash PASS.
- 320px/346-belgili sarlavha overflow0; tanlangan panel lab almashishida
  saqlanadi; mobile menu Escape’dan keyin fokus openerga qaytadi.
  Final desktop sahifa error/warn log0. Native qurilma qabuli emas.
- Dastlab 28-test run: rows checkboxning boolean validationi va tuple/JSON
  fixture solishtiruvi FAIL; tuzatildi, 28 PASS. Keyingi visual check library
  defaultini noto‘g‘ri ajratishni topdi; literal constant resolver va barcha
  7 unchanged panel valid/no-op regressiyasi qo‘shildi. Test susaytirilmadi.
- Lokal dalil: `evidence/PACKET-70-RESULTS.md`, `q16a-desktop-light.png`,
  `q16a-mobile-dark.png`. Preview `http://127.0.0.1:8074/backoffice/control/`.

## Checkpoint va navbat

Yakuniy checkpoint:
`playground/Eleventh Trial/checkpoints/packet-70-20260927-032444.zip`,
**516 fayl**, har source/archive entry SHA256 tekshirildi.
SHA256 **`C53458201C91D9CDCE9E9DD2CCC686745580B836F8F5FE17E0E20EFFBB10F338`**.
Oldingi Paket69 saqlanadi; ignored source yoki screenshotlar upload qilinmaydi.

U12–U19 lokal UI qurildi; U17 write-parity alohida ochiq. Qoldiq **23 UI +
3 handler =26 band**, **7 reja qadami**. Keyingi **Q16b — brend va landing,
2 URL**. Q14 keng authoring qarzi, real port va owner/native qabul bu
sahifa hisobidan alohida ochiq qoladi.
