# PAR-02 — AI xabar amallari: lokal prototip

2026-09-28 boshlandi, 2026-10-01 yakuniy tekshiruv. **EXPERIMENT**, canonical
runtime/DB/AWS yoki AI providerga o‘zgarish yo‘q. Owner tasdiqlagan
[I4b ixcham transcript](I4B-AI-MESSENGER.md) bilan UI pariteti.

## Natija va chegaralar

- Xabar qatorida ism, matn va44px `⋯` qoladi. Vaqt, texnik metadata,
  nusxalash va mavjud sintetik baholash native dialog ichida.
- `⋯`, o‘ng tugma, Shift+F10/ContextMenu; touch/pen550ms hold uchun
  >10px movement, scroll, release/cancel/leave, multi-touch, blur/pagehide
  cancellation. Oddiy tap hech qanday amalni bajarmaydi.
- Nusxa olish faqat exact xabar matni; clipboard promise muvaffaqiyatsiz
  bo‘lsa success yo‘q, matnni belgilab nusxalash yo‘li tushuntiriladi.
- Baholash eski exact room/message contract orqali. Unknown outcome
  saqlashni bloklaydi, reloadga chidamli; menyu tugmasi accessible nomda
  holatni bildiradi. Explicit GET reconcile yozuvni qaytarmaydi.
- Dinamik xabar modaliga shared Tab/Escape/focus-return binder bir marta
  ulanadi. Har row/dialog/statusning room/message IDsi alohida.
- Guruh/ustoz chatining vaqt, edit/delete va upload UIlari saqlandi.
  Biznes qoida, retry/send yoki model/skill capabilitysi qo‘shilmadi.
- Registry **139 named URL /77 page template /118 source name**,
  **1223 route-state /208 action**, yana3 diagnostic handler. Yangi URL yo‘q.

## Tekshiruv

- Testlar ignored `playground/Eleventh Trial` cwd; `.env` yuklanmaydi,
  `AZURELMS_SKIP_ENV_FILE=1`, `GEMINI_API_KEY=` va `TELEGRAM_BOT_TOKEN=`.
- `../../venv/Scripts/python.exe manage.py test tests --verbosity 1`:
  **834 PASS**,330.981s. Uzilishdan oldingi tugamagan run PASS deb olinmadi.
- `node --test` trialning barcha `tests/*.test.mjs` fayllari: **214 PASS**,
  shu jumladan11 yangi gesture/copy/controller testi. `manage.py check`:0;
  uchala o‘zgargan JS uchun `node --check`:PASS.
- IAB8084: Shift+F10/right-click/menu, exact copy→composer paste,
  save→reload, unknown→reload→GET reconcile, modal Tab/Escape/focus,
  dinamik sample,2000 belgili uzilmagan matn, room72 va per-room draft.
  Human edit modal cancel/focus va AI menyu yo‘qligi ham tekshirildi.
- **48 responsive case**:320/375/390/639/640/1023/1024/1440px,
  light/dark;32 closed/open menu +16 long-message checks. Document/row/
  dialog overflow0, tekshirilgan message controls≥44px. Console error/warn0.
  `evidence/PACKET-79-responsive.json` va mobile/desktop screenshots lokal.
- Browser tekshiruvida dynamic hidden feedback IDlarining takrorlanishi
  oldi olindi; DOMda duplicate ID0. Clipboard virtual reader bo‘sh chiqdi,
  shuning uchun haqiqiy UI copy→Ctrl+V orqali exact matn tekshirildi.

## Saqlash va qolgan ish

Source/assets/testlar ignored trial ichida; Gitga faqat ushbu evidence va
trackerlar kiradi. Force-add yoki prototype upload yo‘q. Packet78 arxivi
rollback uchun saqlanadi; verified Packet79 checkpoint alohida qayd etiladi.

Checkpoint: `playground/Eleventh Trial/checkpoints/packet-79-20261001-022839.zip`,
**632 fayl**, har entry SHA256 asl nusxa bilan tekshirildi.
ZIP SHA256 `65532DF709934886D23B863B373730D38983819CCE95ECB5451D9278AB43FB20`.

PAR-02ning **lokal compact-actions farqi yopildi**, native touch long-press,
screen reader va haqiqiy iPhone Chrome keyboard UX-01 **NOT TESTED/OPEN**.
Responsive desktop emulation native device qabuli emas. Real port/G2/G3
yoki AWS release PASS deyilmaydi. Final-qabul navbatida PAR-01/03/05,
UX/DATA/RULE/owner bandlari; undan keyin DESIGN-01 qoladi.
