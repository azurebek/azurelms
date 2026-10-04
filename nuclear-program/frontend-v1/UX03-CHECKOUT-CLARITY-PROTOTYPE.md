# UX-03 — checkout clarity, Packet84

2026-10-04. Admission: **EXPERIMENT — canonical state yozmaydi**.
Ownerning “davom et” topshirig‘i: mavjud prototip final UX navbati.
Scope: Eleventh Trial PAY-01 renewal/course1, `checkout.quote` read UX;
real runtime/DB/provider/AWS o‘zgarmaydi. Bu to‘liq UX-03 yoki G3 qabuli emas.

## Natija va shartnoma

- Hisob-kitob yagona blokda, chek/file/consent/submitdan oldinda; desktop
  va compactda bir xil DOM tartibi. Mavjud stepper/shell/tokenlar saqlanadi.
- Tarif tanlansa summa avtomatik GET orqali olinadi; sahifa ochilganda
  oldin qoralama tiklanadi, keyin aynan shu tanlov tekshiriladi.
- Promokod tahriri eski summani darhol bekor qiladi. Enter yoki button
  narxni tekshiradi, chek yubormaydi. Kechikkan javob yangi tanlovni bosmaydi.
- Xatoda summa tozalanadi, yuborish bloklanadi. Read retry ochiq; mutation
  avtomatik takrorlanmaydi. Focus/sample/consent quote update bilan qoladi.
- Pending/approved/unknown holatlari takroriy yuborishdan himoyalanadi;
  unknown→reload→GET reconciliation existing contracti saqlanadi.
- Ko‘rinish qaytishida/BFCache’da quote qayta o‘qiladi; bu native bank-app
  sinovi emas. Fixture pul matni o‘zgartirilmaydi, JS formula yaratmaydi.

KPI: summary submitdan oldinda, plan uchun qo‘shimcha click0,
avtomatik receipt POST0. Canonical pricing/receipt authority o‘zgarmaydi;
preview `payments.quote` faqat fixed fixture adapter. Owner operatsion
yuki oshmaydi. Rollback: old verified Packet83; previewni to‘xtatish bilan
experiment ajraladi. Yangi capability/flag yoki migration talab qilinmadi.

## Tekshiruv

Trial cwd; `.env` yuklanmaydi, Gemini/Telegram kalitlari bo‘sh:

- `../../venv/Scripts/python.exe manage.py test tests --verbosity 0`:
  **878 PASS**,531.084s; check0/exit0.
- Focused `tests.test_checkout_clarity tests.test_payments
  tests.test_payment_difference tests.test_journey_parity`: **40 PASS**,6.640s.
- Barcha `.test.mjs` PowerShellda kengaytirilib `node --test`: **236 PASS**;
  final rerun980.8188ms. JS syntax, Django check va Git whitespace check PASS.
- IAB localhost8088: **16 responsive case**,320/390/639/640/768/1023/1024/
  1280 × light/dark. Effective width, overflow0, summary/file/submit order,
  visible payment control≥44px tekshirildi. **18 state case**:9scenario×
  320/1280. Slow pending va fault submit-block bor.
- Bad/valid promo Enter, sample/consent preservation, rapid slow response,
  reload draft/cleared file, unknown GET→exact receipt→Back, subscriptions
  Back sinaldi. Console warning/error0; mobile/desktop screenshot ko‘rildi.
- Viewport initially selected tabga qo‘llandi, hidden new tabga emas;
  mismatch tekshirilib to‘g‘ri tabda matrix o‘tdi, override reset qilindi.
  Registry restartdan so‘ng plan/promo smoke qayta o‘tdi.

## Saqlangan nusxa

Ignored `playground/Eleventh Trial/checkpoints/packet-84-20261004-142331.zip`:
**671 fayl**, har entry SHA256 asl nusxa bilan verified.
ZIP SHA256 `8FD178DD9CD0E302442361C48C9499618F20647EB3774D6E196D547D8DC8C89C`.
Packet83 saqlandi, SHA256 mos. Source/assets/tests Gitga force-add yoki
upload qilinmadi. Bu bir diskdagi lokal checkpoint, offsite backup emas.
Dalil: local `evidence/PACKET-84-RESULTS.md` va ikki `.jpg` screenshot.

Registry0.84; 139 named routes +2 aliases /77 page /118 renderer-source
+2 alias sources /1223 states /213 actions +3 handlers; sonlar o‘zgarmadi.

## Ochiq qolganlari

**UX-03 PARTIAL.** Synthetic quote’da timed expiry yo‘q; real narx muddati,
bank ilovasidan native qaytish, haqiqiy karta/copy va source money format
release’da alohida tekshiriladi. Course2 yangi enrollment faqat entry;
ushbu paket uni to‘liq checkout deb ko‘rsatmaydi. Native telefon/AT/boshqa
engine/owner qabuli hali NOT TESTED. Qolgan UX/DATA/RULE va DESIGN-01
navbati saqlanadi. Prototype dalili productionga avtomatik ko‘chirilmaydi.
