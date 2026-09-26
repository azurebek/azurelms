# I6a — kutubxonani real kodga ko‘chirish

## Admission — runtime tahriridan oldin

**ADMIT — launch-critical.** Owner tasdiqlagan frozen V1: kutubxona list,
create/edit va scoped lesson picker. KPI: 4 route oilasi real private file
va canonical attach bilan, mavjud 10 form maydoni saqlangan, 320–1280
overflow0 va required CI3/3. Yangi prototip/design/provider yo‘q.

- Canonical state: LibraryResource + tags, LessonMaterial; mavjud
  LibraryResourceForm, selectors, apply_upload/sync_tags/attach_to_lesson,
  archive/restore/delete va private-file gate yagona manba bo‘lib qoladi.
- Staff uchun umumiy ombor; darslar teacher_course_queryset orqali scoped.
  Learner access, release, audience, XP yoki tarif qoidasi o‘zgarmaydi.
- Runtime adapter: default-OFF frontend_v1_library, teacher shell, explicit
  GET filter, native multipart/CSRF/PRG, bound error va dirty-exit.
  Fayl draft storage/retry/soxta upload success yo‘q.
- Existing resource edit va lifecycle POST V1da user/action/resource-bound
  snapshot + explicit scope confirmation; stale409/no-write. Archive qayta
  bosilsa inverse toggle bo‘lmaydi. Yangi create global idempotency receipt
  emas; UI duplicate guard va canonical PRG, unknown resultda tekshirish.
- Resource writerlar transaction/row lock bilan ishlaydi. ModelForm upload
  eski FieldFile’ni almashtirib yuborishi oldidan original filename olinadi;
  eski bayt faqat yangi record commitdan keyin canonical serviceda o‘chadi.
  Filesystem/DB distributed transaction yoki barcha tashqi writerlar uchun
  global revision kafolati da’vo qilinmaydi. Yangi model/migration yo‘q.
- Picker biriktirilganlarni ko‘rsatadi, scoped explicit attach va current
  query/pagega qaytish. Per-link settings/reorder/detach mavjud dars
  editorida qoladi; I6b shu editorlarni port qiladi. Butun Q13 porti yopilmaydi.
- Owner yangi haftalik operatsion vazifa olmaydi; mavjud kontent boshqaruvi
  bir xil UXda. Rollback flag OFF — eski renderer; saqlangan file/link/
  archive holati yo‘qolmaydi, eski fayl almashtirilsa qaytarish backupdan.
- Test: offline library + core editor/access + learner material regressiya,
  full Django/Node, disposable DB browser. AWS/real material/provider yo‘q.

## Holat

- [x] ~~Runtime va regressiya — `9a76fed`.~~
- [x] ~~Browser desktop/mobile/keyboard — isolated IAB8062.~~
- [ ] Required CI/review/main.
- [ ] AWS/native-device release.

I5d oldingi paket PR134 MERGED `337a73c`, CI36211060029 all3PASS,
SQLite2040 skip44, PostgreSQL2040 skip20, Node87; final local2040 skip45.
[Acceptance](https://github.com/azurebek/azurelms/pull/134#issuecomment-5842321154).

## Implementatsiya va tekshiruv

Default-OFF `frontend_v1_library` registri; teacher navda faqat ON paytida.
Canonical backoffice endpointlar o‘zgarmadi. O‘nta form maydoni saqlandi,
native upload/private file, qidiruv/pagination va audit haqiqiy DBdan.
Unknown/repeated V1 filtr aniqlansa boshqa tanlovga almashtirilmaydi.
Invalid course ID endi omborni kengaytirmaydi; file-kind DISTINCT modelning
default orderingidan tozalandi (bir xil PDF option ko‘payishi tuzatildi).

Snapshot metadata + timestamp + file/version + tags + foydalanish linklari
asosida user/action/resource/lesson bilan imzolanadi. POST guard form
validatsiyasidan oldin olinadi; invalid bound input saqlanadi, yon panel
esa qayta o‘qilgan saved holatni ko‘rsatadi. 409dan keyin Save yopiq.
JS initial selectni haqiqiy DOMdan oladi: HTMLda `selected` bo‘lmasa ham
o‘zgarmagan forma yolg‘ondan dirty emas. Bound error, textarea, checkbox,
file va filter draftlar exitda ogohlantiradi; cross-form discard confirm,
known-offline no-send, duplicate-submit guard; local storage yoki auto retry yo‘q.

Barcha Python buyruqlar `AZURELMS_SKIP_ENV_FILE=1 GEMINI_API_KEY= TELEGRAM_BOT_TOKEN=` bilan:

| Buyruq | Natija |
|---|---|
| `venv/Scripts/python.exe manage.py test library --noinput` | final 66 OK, 6.336s; 23 yangi V1 test |
| `venv/Scripts/python.exe manage.py test --noinput` | 2063 OK, skipped45, 149.846s |
| `node --test tests/frontend_v1/*.test.mjs` | 95 PASS; 8 yangi library controller test |
| `manage.py check --fail-level WARNING` | issue0 |
| `manage.py makemigrations --check --dry-run` | no changes |
| `git diff --check` | PASS |

Full run oxirgi DISTINCT/filter-option regressionidan oldin; undan keyin
library66 qayta PASS. Final HEAD SQLite/PostgreSQL required CI alohida gate.
Test fixture unique email tuzatildi; test skip qo‘shilmadi/susaytirilmadi.

IAB8062 synthetic27resource/privatePDF, owncourse/lesson: dark4routes ×
320/639/640/1023/1024/1280 = **24 responsive readback, overflow0**.
Qidiruv change → pending hint → explicit GET; attach → same query/page va
attached list; edit → success PRG; old second tab → no-write409, draft
saqlandi va Save disabled. Mobil form wrapping, Tab→description focus,
console warn/error0. Shared c-alert flex matnni ustunlarga ajratishi
library-scope block/inline bilan tuzatildi. Viewport reset qilindi.
Dalil lokal ignored `playground/frontend-v1-smoke/library-mobile.png`
va `library-desktop.png`. Real provider/AWS/user data o‘zgarmadi.

## Qolgan chegara

I6b — course/lesson editor va per-link settings/reorder/detach V1 hali ochiq.
Ular mavjud legacy yo‘li bilan ishlaydi, picker buni aniq aytadi. Butun
Q13/I6 yoki qolgan prototiplar tugadi deb hisoblanmaydi.
File upload/replacement/delete/CSRF/role/learner gate backend testlarda;
brauzerda synthetic metadata/attach tekshirildi, real file upload yoki
destructive lifecycle bosilmadi. Actual network loss/native iOS/Android
va light-theme qabuli NOT TESTED. AWS release alohida.

## PR135 CI tuzatishi

Final local HEAD full2063 OK skip45 (143.929s). Birinchi CI36213682493
PostgreSQL runida file-response testi oqimni to‘liq o‘qigach `close()`ni
ikkinchi marta chaqirgan: Django Client wrapperi allaqachon response’ni
yopgan, ortiqcha chaqiruv esa `request_finished` bilan TestCase umumiy PG
tranzaksiyasini yopgan. Natijada keyingi 5 test setupida connection-closed.
Runtime emas, test harness xatosi: ortiqcha close olib tashlandi, response
closed va DB hali ishlashiga assert qo‘shildi. Test skip qilinmadi.
Required CI qayta yashil bo‘lmaguncha merge qilinmaydi.
