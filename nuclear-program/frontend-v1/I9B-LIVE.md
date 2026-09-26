# I9b — Classbook jonli dars va natijalar

ADMIT — launch-critical. Frozen V1ning qolgan 6 rendereri: teacher_session,
teacher_activity_result, live_home/session/activity/result. KPI: ustoz mashqni
ochishi → learner bir javob yuborishi → explicit reveal → natijani ko'rish.
Owner operatsion yuki oshmaydi; yangi mahsulot/baholash qoidasi yo'q.

Canonical state/service: ActivityRun, StudentResponse, TelegramLessonSession;
open_activity / submit_response / close_activity / finish_class_session.
Web shu servicelarni iste'mol qiladi. Telegram, davomat, XP, access va grading
shu domain qatlamida qoladi. Default-OFF frontend_v1_classbook_live; OFF eski
renderer, in-flight V1 write no-write. Schema migration rejalashtirilmagan.

Transport: explicit native teacher confirmation + scoped state fingerprint;
learner JSON submit/GET reconcile, bir javob unique constraint. Hech qanday
auto POST retry, avtomatik navigatsiya yoki javobni browser storagega yozish
yo'q. Unknown holatda draft DOMda qoladi, GET tekshiruv yozuv qilmaydi.
Mashq ID aliaslari serverda canonical IDga qaytadi; answer key reveal oldidan
clientga chiqmaydi. Ball clientda hisoblanmaydi.

Tekshiruv: provider-free classbook + full suites, PG race, Node state tests,
6 renderer desktop/mobile, open→submit→reveal→finish synthetic browser.
Haqiqiy AWS/Telegram/native device release alohida. Frozen prototype va
current DB o'zgarmaydi. Natijalar tekshiruvdan keyin shu yerga yoziladi.
