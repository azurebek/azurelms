"""Namuna kontent — katalog, dars va blog bo'sh bo'lmasin.

`core/demo_seed.py` QA uchun **skelet** yaratadi: sarlavhalari `[demo]` bilan
belgilangan, ataylab sun'iy ko'rinadigan bitta kurs. U mobil probe uchun
to'g'ri, lekin platformani birovga ko'rsatib bo'lmaydi — katalog, dars matni
va blog bo'm-bo'sh qoladi.

Bu modul o'sha bo'shliqni to'ldiradi: ikkita to'liq kurs (6 modul, 15 dars,
test va vazifalar bilan), har biriga guruh, hamda to'rtta nashr etilgan
maqola. Matn haqiqiy o'quv materiali — o'zbek tilida turk tili qoidalari.

To'rtta qoida butun modulni belgilaydi:

1. **Faqat lokal.** Buyruq `settings.IS_LOCAL` ni tekshiradi. Namuna kontent
   haqiqiy katalogga tushsa, o'quvchi qaysi kurs rost ekanini ajrata olmaydi.
2. **Sarlavhada belgi yo'q, egalik esa alohida yozib boriladi.** `demo_seed`
   dan farqi shu: `[demo]` prefiksi ekranda ko'rinadi va taqdimotni buzadi.
   Ammo ko'rsatiladigan identifikator (sarlavha, slug) **egalik dalili emas** —
   shu nomli haqiqiy kurs bazada bo'lishi mumkin. Shuning uchun seeder o'zi
   yaratgan har ildiz yozuvni `core.SeededRecord` bilan belgilaydi:
   `--wipe` faqat o'sha izni ko'rgan yozuvni oladi, boshqasiga tegmaydi.
   Nomi to'g'ri kelib qolgan begona yozuv qabul ham qilinmaydi — seeder
   `SampleContentError` bilan to'xtaydi va nima qilish kerakligini aytadi.
3. **Narx qo'yilmaydi.** `Course.price` model defaultida (0) qoladi — qaysi
   kurs qancha turishi owner qarori (`rules-for-agents.md`: pricing agentga
   o'tmaydi). Joriy shablonlarda kurs narxi ko'rsatilmaydi ham; checkout
   `subscriptions.Plan` narxidan ishlaydi.
4. **Soxta foydalanuvchi va to'lov yaratilmaydi.** Muallif/o'qituvchi sifatida
   mavjud superuser olinadi. Demo hisoblar kerak bo'lsa — `seed_demo`.

Guruhlarga ataylab bironta `CohortLessonRelease` yozilmaydi: `courses/views.py`
drip rejimini birorta release qatori borligiga qarab yoqadi, ya'ni bitta qator
yozilsa qolgan darslar **yopilib qoladi**. Qator yo'q — hamma dars ochiq.

SIT katalogi (universitet, kontrakt narxi, qabul muddati) ataylab to'ldirilmadi:
`03-mahsulot-backlog.md` S1 data gate'i public qabul/narx ma'lumotini rasmiy
`source_url` va `last_verified_on` siz nashr qilishni taqiqlaydi. To'qib
chiqarilgan universitet aynan shu qoidani buzardi.
"""

import datetime

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from blog.models import BlogPost, BlogTag
from cohorts.models import Cohort
from core.models import SeededRecord
from courses.models import (
    Assignment, Choice, Course, Lesson, Module, Question, Quiz,
)


class SampleContentError(RuntimeError):
    """Kontent yaratib bo'lmaydigan holat (masalan, muallif topilmadi)."""


# ---------------------------------------------------------------------------
# Kurslar
# ---------------------------------------------------------------------------

#: Dars matni qasddan uzun: bir qatorlik dars na o'quvchiga foyda beradi, na
#: mobil layoutni sinaydi (`core/test_seed_demo.py` dagi o'sha saboq).
COURSES = (
    {
        "title": "Turk tili A1 — noldan ishonchli boshlanish",
        "level": "beginner",
        "duration": 48,
        "gradient_preset": "sky_lilac",
        "gradient_cover_title": "Turk tili A1",
        "gradient_cover_label": "A1 · Boshlang'ich",
        "description": (
            "<p>Turk tilini mutlaqo noldan boshlaydiganlar uchun. Kurs oxirida "
            "o'zingiz haqingizda gapira olasiz, kundalik savollarga javob berasiz "
            "va oddiy matnni lug'atsiz tushunasiz.</p>"
            "<p>Har dars bitta qoidaga bag'ishlanadi: avval qoida o'zbekcha "
            "tushuntiriladi, keyin misollar beriladi, so'ng mashq bilan "
            "mustahkamlanadi. Jonli darslar Telegram guruhida o'tadi.</p>"
        ),
        "cohort": "A1 kechki guruh",
        "cohort_starts_in_days": 7,
        "modules": (
            {
                "title": "1-modul: Tovushlar va yozuv",
                "lessons": (
                    {
                        "title": "Turk alifbosi va o'zbekchada yo'q bo'lgan harflar",
                        "xp": 20,
                        "content": (
                            "<p>Turk alifbosida <b>29</b> harf bor. Ularning ko'pi lotin "
                            "yozuvidagi o'zbek alifbosiga o'xshaydi, ammo beshtasi boshqacha "
                            "o'qiladi va aynan shular birinchi haftada eng ko'p xato "
                            "keltiradi.</p>"
                            "<ul>"
                            "<li><b>ı</b> — nuqtasiz i. Til orqaga tortilib aytiladi: "
                            "<code>kız</code> (qiz), <code>yıl</code> (yil).</li>"
                            "<li><b>ö</b> va <b>ü</b> — lablar doira shaklida: "
                            "<code>göz</code> (ko'z), <code>gül</code> (gul).</li>"
                            "<li><b>ğ</b> — yumshoq g. Deyarli aytilmaydi, oldingi unlini "
                            "cho'zadi: <code>dağ</code> (tog') <i>daa</i> kabi eshitiladi.</li>"
                            "<li><b>c</b> — o'zbekcha <i>j</i>: <code>cam</code> (oyna) "
                            "<i>jam</i> deb o'qiladi. Bu eng ko'p adashtiradigan harf.</li>"
                            "<li><b>ç</b> va <b>ş</b> — o'zbekcha <i>ch</i> va <i>sh</i>: "
                            "<code>çocuk</code> (bola), <code>şehir</code> (shahar).</li>"
                            "</ul>"
                            "<p>Diqqat: turk tilida harf va tovush deyarli bir-biriga teng. "
                            "Qanday yozilsa, shunday o'qiladi — ingliz tilidagidek istisnolar "
                            "ro'yxatini yodlash shart emas. Shuning uchun o'qishni birinchi "
                            "haftadayoq boshlash mumkin.</p>"
                            "<p>Mashq: quyidagi so'zlarni ovoz chiqarib o'qing va o'zbekchasini "
                            "yozing — <code>çocuk</code>, <code>şehir</code>, "
                            "<code>öğretmen</code>, <code>yıldız</code>, <code>güneş</code>.</p>"
                        ),
                        "assignment": {
                            "title": "Alifbo — o'qish yozuvi",
                            "description": (
                                "<p>Yuqoridagi besh so'zni ovoz chiqarib o'qing va yozib oling "
                                "(telefon diktofoni yetarli). Yozuvni yuklang yoki har so'z uchun "
                                "o'zbekcha ma'nosini hamda qaysi harf qiyin kelganini yozing.</p>"
                            ),
                            "max_xp": 40,
                        },
                    },
                    {
                        "title": "Unli uyg'unligi: qalin va ingichka qator",
                        "xp": 25,
                        "content": (
                            "<p>Bu turk tilining eng muhim qoidasi. Qo'shimchaning shakli "
                            "so'zning <b>oxirgi unlisi</b>ga qarab tanlanadi — o'zbek tilida "
                            "bunga o'xshash, ammo ancha yumshoqroq hodisa bor.</p>"
                            "<p>Unlilar ikki qatorga bo'linadi:</p>"
                            "<ul>"
                            "<li><b>Qalin:</b> a, ı, o, u</li>"
                            "<li><b>Ingichka:</b> e, i, ö, ü</li>"
                            "</ul>"
                            "<p>Ko'plik qo'shimchasi <code>-lar / -ler</code> shuni ko'rsatadi: "
                            "<code>kitap → kitaplar</code> (oxirgi unli <i>a</i>, qalin), "
                            "<code>ev → evler</code> (oxirgi unli <i>e</i>, ingichka). Qoidani "
                            "bilmasangiz <i>evlar</i> deysiz va bu darhol sezilib qoladi.</p>"
                            "<p>To'rt shaklli qo'shimchalar ham bor "
                            "(<code>-ı / -i / -u / -ü</code>): u yerda lab holati ham hisobga "
                            "olinadi. Hozircha ikki shakllisini avtomatlashtiring — qolgani "
                            "keyingi modulda.</p>"
                        ),
                        "quiz": {
                            "title": "Unli uyg'unligi — tezkor test",
                            "xp": 30,
                            "questions": (
                                {
                                    "text": "<code>öğrenci</code> so'zining ko'pligi qaysi?",
                                    "choices": (
                                        ("öğrenciler", True),
                                        ("öğrencilar", False),
                                        ("öğrencier", False),
                                    ),
                                },
                                {
                                    "text": "<code>okul</code> so'zining ko'pligi qaysi?",
                                    "choices": (
                                        ("okullar", True),
                                        ("okuller", False),
                                        ("okulular", False),
                                    ),
                                },
                                {
                                    "text": "Qaysi unlilar qalin qatorga kiradi?",
                                    "choices": (
                                        ("a, ı, o, u", True),
                                        ("e, i, ö, ü", False),
                                        ("a, e, i, o", False),
                                    ),
                                },
                            ),
                        },
                    },
                    {
                        "title": "Undosh moslashuvi: p, ç, t, k qoidasi",
                        "xp": 20,
                        "content": (
                            "<p>So'z oxiridagi <b>p, ç, t, k</b> undoshlari unli bilan "
                            "boshlanadigan qo'shimcha olganda yumshaydi va mos ravishda "
                            "<b>b, c, d, g/ğ</b> ga aylanadi.</p>"
                            "<ul>"
                            "<li><code>kitap</code> + <code>-ı</code> → <code>kitabı</code></li>"
                            "<li><code>ağaç</code> + <code>-ı</code> → <code>ağacı</code></li>"
                            "<li><code>kağıt</code> + <code>-ı</code> → <code>kağıdı</code></li>"
                            "<li><code>renk</code> + <code>-i</code> → <code>rengi</code></li>"
                            "</ul>"
                            "<p>Qoida bir bo'g'inli so'zlarning ko'pchiligiga tegmaydi: "
                            "<code>at</code> (ot) → <code>atı</code>, <code>ip</code> → "
                            "<code>ipi</code>. Istisnolarni yodlashdan ko'ra, ko'p o'qib "
                            "quloqqa singdirish tezroq natija beradi.</p>"
                            "<p>Nega bu muhim: <code>kitabı</code> o'rniga <code>kitapı</code> "
                            "deyilsa, gap tushunarli qoladi, lekin yozma imtihonda bu "
                            "grammatik xato sifatida hisoblanadi.</p>"
                        ),
                    },
                ),
            },
            {
                "title": "2-modul: Birinchi suhbat",
                "lessons": (
                    {
                        "title": "Salomlashish, tanishuv va xayrlashuv",
                        "xp": 20,
                        "content": (
                            "<p>Turk tilida salomlashish kun vaqtiga qarab o'zgaradi va bu juda "
                            "qat'iy qo'llaniladi — noto'g'ri vaqtda aytilgan salom darhol "
                            "sezilib qoladi.</p>"
                            "<ul>"
                            "<li><code>Günaydın</code> — faqat ertalab (taxminan tushgacha).</li>"
                            "<li><code>İyi günler</code> — kunduzi; ham salom, ham xayrlashuv.</li>"
                            "<li><code>İyi akşamlar</code> — kechqurun.</li>"
                            "<li><code>Merhaba</code> — vaqtdan qat'i nazar, neytral.</li>"
                            "</ul>"
                            "<p>Tanishuv namunasi:</p>"
                            "<p><i>— Merhaba, benim adım Aziz. Sizin adınız ne?<br>"
                            "— Merhaba, ben Ayşe. Memnun oldum.<br>"
                            "— Ben de memnun oldum. Nerelisiniz?<br>"
                            "— Özbekistanlıyım, Semerkant'tan geliyorum.</i></p>"
                            "<p>E'tibor bering: <code>Memnun oldum</code> so'zma-so'z "
                            "\"mamnun bo'ldim\" degani. O'zbekcha \"tanishganimdan xursandman\" "
                            "ga to'g'ri keladi va o'tgan zamonda aytiladi — bu turk tiliga "
                            "xos.</p>"
                        ),
                        "assignment": {
                            "title": "O'zingiz haqingizda 5 gap",
                            "description": (
                                "<p>Yuqoridagi namunaga qarab o'zingiz haqingizda kamida besh gap "
                                "yozing: ism, shahar, kasb yoki o'qish joyi, yosh va turk tilini "
                                "nima uchun o'rganayotganingiz. Har gapda kamida bitta yangi so'z "
                                "ishlating.</p>"
                            ),
                            "max_xp": 50,
                        },
                    },
                    {
                        "title": "Shaxs olmoshlari va shaxs qo'shimchalari",
                        "xp": 25,
                        "content": (
                            "<p>Turk tilida \"men o'qituvchiman\" deyish uchun alohida "
                            "<i>bo'lmoq</i> fe'li kerak emas — qo'shimcha otning o'ziga "
                            "qo'shiladi. Bu o'zbek tiliga juda o'xshaydi.</p>"
                            "<ul>"
                            "<li><code>ben</code> (men) → <code>öğretmenim</code> — o'qituvchiman</li>"
                            "<li><code>sen</code> (sen) → <code>öğretmensin</code> — o'qituvchisan</li>"
                            "<li><code>o</code> (u) → <code>öğretmen</code> — o'qituvchi</li>"
                            "<li><code>biz</code> → <code>öğretmeniz</code></li>"
                            "<li><code>siz</code> → <code>öğretmensiniz</code></li>"
                            "<li><code>onlar</code> → <code>öğretmenler</code></li>"
                            "</ul>"
                            "<p>Uchinchi shaxsda qo'shimcha yo'q — o'zbekchadagi \"u o'qituvchi\" "
                            "bilan bir xil. Rasmiy matnda <code>-dır</code> qo'shilishi mumkin: "
                            "<code>öğretmendir</code>.</p>"
                            "<p>Qo'shimchaning unlisi yana uyg'unlik qoidasiga bo'ysunadi: "
                            "<code>doktorum</code>, <code>öğrenciyim</code>, "
                            "<code>müdürüm</code>. Ya'ni ikkita qoida birga ishlaydi — birinchi "
                            "modulda o'rganilgani shu yerda kerak bo'ladi.</p>"
                        ),
                    },
                    {
                        "title": "Var va yok — bor va yo'q",
                        "xp": 20,
                        "content": (
                            "<p><code>var</code> — bor, <code>yok</code> — yo'q. Ikkalasi ham gap "
                            "oxirida turadi va o'zbekcha tarjimasi bilan deyarli aynan mos "
                            "keladi, shuning uchun bu mavzu o'zbek o'quvchiga oson beriladi.</p>"
                            "<p><i>Masada kitap var.</i> — Stolda kitob bor.<br>"
                            "<i>Evde kimse yok.</i> — Uyda hech kim yo'q.<br>"
                            "<i>Sorunuz var mı?</i> — Savolingiz bormi?</p>"
                            "<p>Egalik bilan birga kelganda \"menda bor\" ma'nosi chiqadi: "
                            "<code>Benim arabam var</code> — mening mashinam bor. Bu yerda "
                            "<code>araba</code> ga egalik qo'shimchasi <code>-m</code> qo'shiladi, "
                            "<code>var</code> esa o'zgarmaydi.</p>"
                            "<p>Ko'p uchraydigan xato: <code>yok</code> o'rniga "
                            "<code>değil</code> ishlatish. <code>değil</code> sifat va otni inkor "
                            "qiladi (<code>Bu kitap değil</code> — bu kitob emas), "
                            "<code>yok</code> esa mavjud emasligini bildiradi.</p>"
                        ),
                        "quiz": {
                            "title": "Var / yok / değil",
                            "xp": 25,
                            "questions": (
                                {
                                    "text": "\"Uyda non yo'q\" — qaysi variant to'g'ri?",
                                    "choices": (
                                        ("Evde ekmek yok.", True),
                                        ("Evde ekmek değil.", False),
                                        ("Evde ekmek var mı.", False),
                                    ),
                                },
                                {
                                    "text": "\"Bu mening kitobim emas\" — qaysi variant to'g'ri?",
                                    "choices": (
                                        ("Bu benim kitabım değil.", True),
                                        ("Bu benim kitabım yok.", False),
                                        ("Bu kitap var değil.", False),
                                    ),
                                },
                            ),
                        },
                    },
                ),
            },
            {
                "title": "3-modul: Hozirgi zamon",
                "lessons": (
                    {
                        "title": "Hozirgi zamon: -yor qo'shimchasi",
                        "xp": 30,
                        "content": (
                            "<p>Hozirgi zamon qo'shimchasi <code>-yor</code> hozir bajarilayotgan "
                            "ish uchun ishlatiladi — o'zbekchadagi <i>-yapti</i> ga to'g'ri "
                            "keladi.</p>"
                            "<p>Yasalishi uch qadam: fe'l o'zagini oling, unli qo'shing "
                            "(uyg'unlikka qarab <code>ı, i, u, ü</code>), keyin <code>-yor</code> "
                            "va shaxs qo'shimchasi.</p>"
                            "<ul>"
                            "<li><code>gelmek</code> (kelmoq) → <code>geliyorum</code> — kelyapman</li>"
                            "<li><code>bakmak</code> (qaramoq) → <code>bakıyorum</code> — qarayapman</li>"
                            "<li><code>okumak</code> (o'qimoq) → <code>okuyorum</code> — o'qiyapman</li>"
                            "<li><code>görmek</code> (ko'rmoq) → <code>görüyorum</code> — ko'ryapman</li>"
                            "</ul>"
                            "<p>Muhim nozik joy: o'zak oxiridagi <b>a</b> yoki <b>e</b> tushib "
                            "qoladi. <code>başlamak</code> → <code>başlıyorum</code> "
                            "(<i>başlayıyorum</i> emas). Bu qoidani bilmaslik eng ko'p uchraydigan "
                            "A1 xatosi.</p>"
                            "<p>Turk tilida bu zamon o'zbekchadan kengroq ishlatiladi: "
                            "rejalashtirilgan kelasi ish uchun ham qo'llanadi — "
                            "<code>Yarın geliyorum</code> (ertaga kelyapman = ertaga kelaman).</p>"
                        ),
                        "assignment": {
                            "title": "Kuningiz — 8 gap hozirgi zamonda",
                            "description": (
                                "<p>Bugungi kuningizni sakkiz gapda yozing. Har gap hozirgi zamonda "
                                "bo'lsin va kamida uchtasida o'zagi <i>a/e</i> ga tugaydigan fe'l "
                                "ishlatilsin (<code>başlamak</code>, <code>beklemek</code>, "
                                "<code>anlamak</code>).</p>"
                            ),
                            "max_xp": 60,
                        },
                    },
                    {
                        "title": "Inkor va so'roq shakllari",
                        "xp": 30,
                        "content": (
                            "<p>Inkor uchun o'zak bilan <code>-yor</code> orasiga "
                            "<code>-mı / -mi / -mu / -mü</code> qo'yiladi:</p>"
                            "<p><code>geliyorum</code> → <code>gelmiyorum</code> (kelmayapman)<br>"
                            "<code>bakıyorum</code> → <code>bakmıyorum</code><br>"
                            "<code>okuyorum</code> → <code>okumuyorum</code></p>"
                            "<p>So'roq esa <b>alohida so'z</b> bilan yasaladi va shaxs qo'shimchasi "
                            "o'sha so'roq so'ziga ko'chadi — bu o'zbek tilida yo'q va shuning uchun "
                            "diqqat talab qiladi:</p>"
                            "<p><i>Geliyor musun?</i> — Kelyapsanmi?<br>"
                            "<i>Anlıyor musunuz?</i> — Tushunyapsizmi?<br>"
                            "<i>Çalışmıyor mu?</i> — Ishlamayaptimi?</p>"
                            "<p>Yozuvda <code>mu</code> ajratib yoziladi, lekin bir so'zdek "
                            "aytiladi. Test topshiriqlarida aynan shu ajratib yozish "
                            "tekshiriladi.</p>"
                        ),
                        "quiz": {
                            "title": "Hozirgi zamon — inkor va so'roq",
                            "xp": 35,
                            "questions": (
                                {
                                    "text": "\"Men tushunmayapman\" — to'g'ri variant qaysi?",
                                    "choices": (
                                        ("Anlamıyorum.", True),
                                        ("Anlamayorum.", False),
                                        ("Anlamıyor musun.", False),
                                    ),
                                },
                                {
                                    "text": "\"Siz ishlayapsizmi?\" — to'g'ri variant qaysi?",
                                    "choices": (
                                        ("Çalışıyor musunuz?", True),
                                        ("Çalışıyorsunuz mu?", False),
                                        ("Çalışıyormusunuz?", False),
                                    ),
                                },
                                {
                                    "text": "<code>başlamak</code> fe'lining hozirgi zamon shakli qaysi?",
                                    "choices": (
                                        ("başlıyorum", True),
                                        ("başlayıyorum", False),
                                        ("başlamaıyorum", False),
                                    ),
                                },
                            ),
                        },
                    },
                ),
            },
        ),
    },
    {
        "title": "Turk tili B1 — sertifikat imtihoniga tayyorgarlik",
        "level": "intermediate",
        "duration": 60,
        "gradient_preset": "emerald_glass",
        "gradient_cover_title": "Turk tili B1",
        "gradient_cover_label": "B1 · O'rta daraja",
        "description": (
            "<p>A2 darajasini tugatgan va til sertifikati imtihoniga tayyorlanayotganlar "
            "uchun. Diqqat markazida — o'tgan zamonlar, yozma ish tuzilishi va imtihon "
            "bo'limlari bo'yicha vaqt strategiyasi.</p>"
            "<p>Har modul oxirida mock topshiriq bor: shart imtihondagidek qo'yiladi, "
            "o'qituvchi esa har inshoga alohida izoh yozadi.</p>"
        ),
        "cohort": "B1 imtihon guruhi",
        "cohort_starts_in_days": 14,
        "modules": (
            {
                "title": "1-modul: O'tgan zamonlar",
                "lessons": (
                    {
                        "title": "-dı: o'zim ko'rgan o'tmish",
                        "xp": 30,
                        "content": (
                            "<p>Turk tilida ikkita o'tgan zamon bor va ular o'rtasidagi farq "
                            "grammatik emas — <b>ma'lumot qayerdan kelgani</b>. Bu o'zbek "
                            "tilidagi <i>-di</i> va <i>-ibdi</i> farqiga juda yaqin.</p>"
                            "<p><code>-dı / -di / -du / -dü</code> (jarangsizdan keyin "
                            "<code>-tı / -ti / -tu / -tü</code>) so'zlovchi o'zi guvoh bo'lgan, "
                            "aniq bilgan ish uchun ishlatiladi:</p>"
                            "<p><i>Dün İstanbul'a gittim.</i> — Kecha Istanbulga bordim.<br>"
                            "<i>Kitabı okudum ve çok beğendim.</i> — Kitobni o'qidim va juda "
                            "yoqdi.</p>"
                            "<p>Shaxs qo'shimchalari bu zamonda boshqacha: <code>-m, -n, -, -k, "
                            "-nız, -lar</code>. Ya'ni <code>gittim</code>, <code>gittin</code>, "
                            "<code>gitti</code>, <code>gittik</code>, <code>gittiniz</code>, "
                            "<code>gittiler</code>. Hozirgi zamondagi <code>-yorum</code> qatorini "
                            "bu yerga ko'chirish tipik xato.</p>"
                        ),
                        "quiz": {
                            "title": "-dı o'tgan zamoni",
                            "xp": 30,
                            "questions": (
                                {
                                    "text": "\"Biz kecha keldik\" — to'g'ri variant qaysi?",
                                    "choices": (
                                        ("Dün geldik.", True),
                                        ("Dün geliyorduk.", False),
                                        ("Dün gelmişiz.", False),
                                    ),
                                },
                                {
                                    "text": "<code>bakmak</code> fe'lining <i>men</i> shakli qaysi?",
                                    "choices": (
                                        ("baktım", True),
                                        ("bakdım", False),
                                        ("bakıyordum", False),
                                    ),
                                },
                            ),
                        },
                    },
                    {
                        "title": "-mış: eshitilgan yoki keyin bilingan o'tmish",
                        "xp": 30,
                        "content": (
                            "<p><code>-mış / -miş / -muş / -müş</code> so'zlovchi o'zi ko'rmagan, "
                            "boshqadan eshitgan yoki natijadan bilib olgan ish uchun ishlatiladi. "
                            "O'zbekchadagi <i>-ibdi</i> ga to'g'ri keladi.</p>"
                            "<p><i>Ali dün gelmiş.</i> — Ali kecha kelibdi (menga aytishdi).<br>"
                            "<i>Yağmur yağmış.</i> — Yomg'ir yog'ibdi (yerni ho'l ko'rdim).</p>"
                            "<p>Shuning uchun ertak, latifa va yangilik matnlari deyarli butunlay "
                            "shu zamonda yoziladi: <i>Bir varmış, bir yokmuş...</i></p>"
                            "<p>Imtihonda tuzoq shunday qo'yiladi: matnda voqea "
                            "<code>-mış</code> bilan berilib, savolda \"so'zlovchi voqeani "
                            "ko'rganmi?\" deb so'raladi. Javob — yo'q. Zamon shaklining o'zi manba "
                            "haqida ma'lumot beradi.</p>"
                        ),
                    },
                    {
                        "title": "Ikkala o'tgan zamon bitta hikoyada",
                        "xp": 25,
                        "content": (
                            "<p>Real matnda ikkala zamon aralashadi va aynan shu joyda daraja "
                            "ko'rinadi. Qoida sodda: <b>o'zim ko'rgan qismi <code>-dı</code>, "
                            "boshqadan eshitgan qismi <code>-mış</code></b>.</p>"
                            "<p><i>Dün okula gittim. Öğretmen gelmemiş, dersi iptal etmişler. "
                            "Ben de eve döndüm.</i></p>"
                            "<p>Bu matnda \"bordim\" va \"qaytdim\" — o'zim qilgan ish "
                            "(<code>-dı</code>); \"o'qituvchi kelmabdi\" va \"darsni bekor "
                            "qilishibdi\" — kimdandir eshitilgan (<code>-mış</code>). Bitta "
                            "abzatsda ikkalasini to'g'ri almashtira olish B1 belgisidir.</p>"
                        ),
                        "assignment": {
                            "title": "Hikoya: ikkala o'tgan zamon bilan",
                            "description": (
                                "<p>10-12 gaplik hikoya yozing: o'zingiz qatnashgan voqea va "
                                "boshqalardan eshitgan qismi birga bo'lsin. Har zamon shaklidan "
                                "kamida to'rt marta foydalaning va nima uchun aynan shu shaklni "
                                "tanlaganingizni qavs ichida qisqacha izohlang.</p>"
                            ),
                            "max_xp": 80,
                        },
                    },
                ),
            },
            {
                "title": "2-modul: Yozma ish",
                "lessons": (
                    {
                        "title": "Insho tuzilishi va paragraf mantiqi",
                        "xp": 35,
                        "content": (
                            "<p>Imtihon inshosi ijodiy matn emas — u <b>tuzilishi "
                            "tekshiriladigan</b> matn. Baholovchi birinchi navbatda uch narsani "
                            "qidiradi: fikr bormi, dalil bormi, xulosa savolga javob beradimi.</p>"
                            "<p>Ishlaydigan sxema:</p>"
                            "<ul>"
                            "<li><b>Kirish (2-3 gap):</b> mavzuni qayta ifodalang va o'z "
                            "pozitsiyangizni ayting.</li>"
                            "<li><b>1-dalil (4-5 gap):</b> bitta fikr va misol. Misolsiz dalil "
                            "yarim ball oladi.</li>"
                            "<li><b>2-dalil (4-5 gap):</b> boshqa tomondan.</li>"
                            "<li><b>Xulosa (2-3 gap):</b> yangi fikr kiritmang, savolga "
                            "qayting.</li>"
                            "</ul>"
                            "<p>So'z chegarasi jiddiy: kam yozsangiz ball kesiladi, ortiqcha "
                            "yozsangiz xato ehtimoli oshadi. 150-180 so'z odatda eng xavfsiz "
                            "oraliq.</p>"
                            "<p>Vaqt taqsimoti: 5 daqiqa reja, 20 daqiqa yozish, 5 daqiqa "
                            "tekshirish. Tekshirishda faqat uch narsani qidiring — zamon "
                            "izchilligi, unli uyg'unligi va takrorlangan so'zlar.</p>"
                        ),
                        "assignment": {
                            "title": "Mock insho №1",
                            "description": (
                                "<p>Mavzu: <i>\"Yosh avlod uchun chet tilini bilish shartmi?\"</i> "
                                "150-180 so'z, yuqoridagi to'rt qismli tuzilishda. Vaqt: 30 daqiqa, "
                                "lug'atsiz. Yozib bo'lgach so'z sonini o'zingiz sanab, matn oxiriga "
                                "yozib qo'ying.</p>"
                            ),
                            "max_xp": 100,
                        },
                    },
                    {
                        "title": "Bog'lovchilar: ancak, ayrıca, bu nedenle",
                        "xp": 30,
                        "content": (
                            "<p>B1 va A2 orasidagi eng ko'rinadigan farq — gaplarni bir-biriga "
                            "bog'lay olish. Quyidagi bog'lovchilar insho ballini eng tez "
                            "ko'taradiganlari:</p>"
                            "<ul>"
                            "<li><code>ancak</code> / <code>fakat</code> — lekin, ammo</li>"
                            "<li><code>ayrıca</code> — bundan tashqari</li>"
                            "<li><code>bu nedenle</code> / <code>bu yüzden</code> — shu sababli</li>"
                            "<li><code>örneğin</code> — masalan</li>"
                            "<li><code>öte yandan</code> — boshqa tomondan</li>"
                            "<li><code>sonuç olarak</code> — xulosa qilib aytganda</li>"
                            "</ul>"
                            "<p>Muhim cheklov: bitta abzatsda ikkitadan ortiq bog'lovchi "
                            "ishlatmang. Matn \"bog'lovchilar ro'yxati\" ga aylanib qolsa, "
                            "baholovchi buni yodlangan shablon deb belgilaydi va bu ball "
                            "qo'shmaydi.</p>"
                            "<p><i>Türkçe öğrenmek zor değil. <b>Ancak</b> düzenli çalışmak "
                            "gerekiyor. <b>Bu nedenle</b> her gün en az yirmi dakika "
                            "ayırıyorum.</i></p>"
                        ),
                    },
                ),
            },
            {
                "title": "3-modul: Imtihon strategiyasi",
                "lessons": (
                    {
                        "title": "O'qish bo'limi: vaqtni taqsimlash",
                        "xp": 25,
                        "content": (
                            "<p>O'qish bo'limida eng ko'p ball matnni tushunmagani uchun emas, "
                            "<b>vaqt yetmagani</b> uchun yo'qoladi. Shuning uchun strategiya "
                            "grammatikadan kam ahamiyatli emas.</p>"
                            "<p>Tartib: avval savollarni o'qing, keyin matnni. Teskarisi qilinsa, "
                            "matn ikki marta o'qiladi va vaqt ikki barobar ketadi.</p>"
                            "<p>Har matnga ajratilgan vaqtni oldindan belgilang va undan oshsangiz "
                            "javobni taxmin qilib, keyingisiga o'ting. Bitta qiyin savol uchun "
                            "keyingi matndagi to'rtta oson savolni qurbon qilish — eng qimmat "
                            "xato.</p>"
                            "<p>Noma'lum so'z uchraganda lug'at o'ylamang: gapning qolgan qismidan "
                            "ma'noni chiqaring. Imtihon matnlari shu ko'nikmani ataylab "
                            "tekshiradi.</p>"
                        ),
                    },
                    {
                        "title": "Eshitish: bir marta tinglashga tayyorgarlik",
                        "xp": 25,
                        "content": (
                            "<p>Ko'p imtihonlarda audio <b>bir marta</b> qo'yiladi. Ya'ni "
                            "tayyorgarlik ham shu shartda bo'lishi kerak — takror tinglab mashq "
                            "qilish yolg'on ishonch beradi.</p>"
                            "<p>Audio boshlanishidan oldingi 30 soniya eng qimmat vaqt: savollarni "
                            "o'qib, qanday ma'lumot kerakligini belgilab oling (raqammi, joymi, "
                            "sababmi). Quloq nimani kutayotganini bilsa, o'shani ilib oladi.</p>"
                            "<p>Tinglash paytida to'liq gap yozmang — kalit so'z va raqam yozing. "
                            "Yozayotganda keyingi gap o'tib ketadi.</p>"
                            "<p>Kundalik mashq: turk yangiliklaridan 2-3 daqiqalik parcha oling, "
                            "bir marta tinglang va eshitganingizni o'zbekcha qayta so'zlab bering. "
                            "Ikkinchi marta tinglash — faqat tekshirish uchun.</p>"
                        ),
                        "quiz": {
                            "title": "Imtihon strategiyasi",
                            "xp": 25,
                            "questions": (
                                {
                                    "text": "O'qish bo'limida qaysi tartib vaqtni tejaydi?",
                                    "choices": (
                                        ("Avval savollar, keyin matn", True),
                                        ("Avval matn, keyin savollar", False),
                                        ("Matnni ikki marta o'qish", False),
                                    ),
                                },
                                {
                                    "text": "Audio boshlanishidan oldingi 30 soniyada nima qilinadi?",
                                    "choices": (
                                        ("Savollar o'qiladi va kerakli ma'lumot turi belgilanadi", True),
                                        ("Javoblar taxmin qilib to'ldiriladi", False),
                                        ("Hech narsa, dam olinadi", False),
                                    ),
                                },
                            ),
                        },
                    },
                ),
            },
        ),
    },
)


# ---------------------------------------------------------------------------
# Blog
# ---------------------------------------------------------------------------

TAGS = ("Grammatika", "Lug'at", "Metodika", "Imtihon")

#: Maqolalar ataylab **pedagogika** haqida: qabul muddati, kontrakt narxi yoki
#: viza kabi vaqtga sezgir da'volar yo'q. S1 data gate'i bunday ma'lumotni
#: rasmiy manba va tekshiruv sanasisiz nashr qilishni taqiqlaydi va blog uni
#: chetlab o'tadigan joy emas.
ARTICLES = (
    {
        "slug": "unli-uygunligi-eng-kop-xato",
        "title": "Unli uyg'unligi — turk tilida eng ko'p xato qilinadigan qoida",
        "tags": ("Grammatika",),
        "featured": True,
        "excerpt": (
            "Bitta qoidani avtomatlashtirsangiz, gaplaringizdagi xatolarning sezilarli "
            "qismi o'z-o'zidan yo'qoladi. Nega aynan shu qoida va uni qanday mashq qilish kerak."
        ),
        "featured_quote": "Qoida murakkab emas — u shunchaki har gapda ishlaydi.",
        "body": (
            "<p>O'zbek tilida so'zlashuvchi uchun turk tili grammatikasi tanish tuyuladi: "
            "so'z tartibi bir xil, qo'shimchalar oxiriga qo'shiladi, jinsi yo'q. Aynan shu "
            "tanishlik tuzoq yaratadi — o'quvchi qoidani <i>tushunadi</i>, lekin gapirganda "
            "<i>qo'llamaydi</i>. Darsda to'g'ri javob beradi, suhbatda esa xato qiladi.</p>"
            "<h3>Qoida bir gapda</h3>"
            "<p>Qo'shimchaning unlisi so'zning oxirgi unlisiga moslashadi. Qalin qatordan "
            "keyin qalin, ingichka qatordan keyin ingichka unli keladi:</p>"
            "<ul>"
            "<li>qalin: <b>a, ı, o, u</b> → <code>kitaplar</code>, <code>okullar</code>, "
            "<code>arkadaşlar</code></li>"
            "<li>ingichka: <b>e, i, ö, ü</b> → <code>evler</code>, <code>günler</code>, "
            "<code>öğrenciler</code></li>"
            "</ul>"
            "<p>Ya'ni <code>ev</code> so'ziga <code>-lar</code> qo'shib bo'lmaydi va "
            "<code>okul</code> so'ziga <code>-ler</code> qo'shib bo'lmaydi. Ikkinchi variant "
            "grammatik jihatdan mavjud emas — mavjud bo'lmagan shakl esa quloqqa darrov "
            "uriladi.</p>"
            "<h3>Nega bu shunchalik muhim</h3>"
            "<p>Chunki qoida bitta qo'shimchaga emas, <b>deyarli hammasiga</b> tegishli: "
            "ko'plik, egalik, kelishik, zamon, shaxs. O'rtacha bir gapda u to'rt-besh marta "
            "ishlaydi. Shuning uchun uni bilmaslik bitta xato bermaydi — har gapda "
            "takrorlanadigan xato beradi.</p>"
            "<p>Buni sanab ko'rish oson. <i>Men do'stlarimga kitoblarni berdim</i> gapining "
            "turkchasi — <code>Arkadaşlarıma kitapları verdim</code>. Bitta qisqa gapda "
            "qoida yetti marta qo'llanilgan. Bitta joyda adashsangiz, gap baribir "
            "tushunarli qoladi; yozma imtihonda esa har biri alohida xato deb sanaladi.</p>"
            "<h3>Ikki shakldan to'rt shaklga</h3>"
            "<p>Yuqoridagi <code>-lar / -ler</code> — eng oson holat, chunki tanlov ikkitadan "
            "iborat. Qo'shimchalarning katta qismi esa to'rt shaklli: "
            "<code>-ı / -i / -u / -ü</code>. Bu yerda ikkinchi omil qo'shiladi — lablar "
            "holati:</p>"
            "<ul>"
            "<li>oxirgi unli <b>a</b> yoki <b>ı</b> bo'lsa → <code>ı</code>: "
            "<code>kitap → kitabı</code></li>"
            "<li>oxirgi unli <b>e</b> yoki <b>i</b> bo'lsa → <code>i</code>: "
            "<code>ev → evi</code></li>"
            "<li>oxirgi unli <b>o</b> yoki <b>u</b> bo'lsa → <code>u</code>: "
            "<code>okul → okulu</code></li>"
            "<li>oxirgi unli <b>ö</b> yoki <b>ü</b> bo'lsa → <code>ü</code>: "
            "<code>göz → gözü</code></li>"
            "</ul>"
            "<p>Ro'yxat uzun ko'rinadi, lekin mantiqi bitta: qo'shimcha oldingi unlining "
            "og'iz holatini takrorlaydi. Bir necha kunlik mashqdan keyin uni o'ylamay "
            "tanlaydigan bo'lasiz.</p>"
            "<h3>Qanday mashq qilinadi</h3>"
            "<p>Yodlash ishlamaydi, chunki gapirayotganda o'ylashga vaqt yo'q. Ishlaydigan "
            "usul — mexanik takror:</p>"
            "<ol>"
            "<li>20 ta so'zli ro'yxat tuzing (10 tasi qalin, 10 tasi ingichka oxirli).</li>"
            "<li>Har biriga ko'plik qo'shimchasini <b>ovoz chiqarib</b> qo'shing. Ichingizda "
            "aytish samarasiz: xatoni eshitmaysiz.</li>"
            "<li>Xato qilsangiz to'xtamang — davom eting va oxirida ro'yxatni qaytadan "
            "boshlang.</li>"
            "<li>Bir hafta, har kuni 3 daqiqa. Ettinchi kuni ro'yxatni almashtiring.</li>"
            "</ol>"
            "<p>Ikkinchi haftada to'rt shaklli qo'shimchalarga o'ting va shu tartibni "
            "takrorlang. Uchinchi haftada esa mashqni gap darajasiga ko'taring: tayyor "
            "so'zlar emas, o'zingiz tuzgan gaplar bilan ishlang.</p>"
            "<h3>Tez-tez uchraydigan savol</h3>"
            "<p><i>Chet so'zlar-chi?</i> — Ular ko'pincha qoidaga bo'ysunmaydi: "
            "<code>saat → saatler</code>, <code>kalp → kalpler</code>, "
            "<code>hakikat → hakikatler</code>. Bu istisnolar ro'yxati uzun emas va ular "
            "vaqt bilan quloqqa singadi. Ularni birinchi haftada yodlashga urinmang — avval "
            "asosiy qoidani avtomatlashtiring, istisnolar keyin o'z joyiga tushadi.</p>"
        ),
    },
    {
        "slug": "ozbek-tilidan-turkchaga-ettita-oxshashlik",
        "title": "O'zbek tilidan turkchaga o'tishda yordam beradigan 7 o'xshashlik",
        "tags": ("Grammatika", "Metodika"),
        "excerpt": (
            "Turk tili o'zbek tiliga yaqin va bu haqiqiy tezlik afzalligi. Qaysi joylarda "
            "o'zbekcha bilimingiz to'g'ridan-to'g'ri ishlaydi — va qayerda to'xtaydi."
        ),
        "body": (
            "<p>Turkiy tillar oilasida bo'lgani uchun o'zbek tilini biladigan odam turk tilini "
            "noldan boshlamaydi. Ingliz yoki rus tilida so'zlashuvchi bir yilda o'zlashtiradigan "
            "narsani siz bir necha oyda olishingiz mumkin — lekin faqat qayerda afzallik "
            "borligini bilsangiz. Quyidagi yetti nuqta shuni ko'rsatadi.</p>"
            "<h3>1. So'z tartibi bir xil</h3>"
            "<p>Ega — to'ldiruvchi — kesim. <i>Men kitob o'qiyman</i> = "
            "<code>Ben kitap okuyorum</code>. Ingliz tilidan farqli, gapni miyada qayta "
            "tartiblash shart emas: o'zbekcha o'ylab, so'zlarni almashtirsangiz to'g'ri "
            "turkcha gap chiqadi. Bu tezlikda eng katta afzallik.</p>"
            "<h3>2. Qo'shimchalar oxirga qo'shiladi</h3>"
            "<p>Predlog yo'q. <i>Uyda</i> = <code>evde</code>, <i>uydan</i> = "
            "<code>evden</code>, <i>uyga</i> = <code>eve</code>. Mantiq aynan bir xil, faqat "
            "qo'shimchaning shakli boshqa. Ya'ni yangi tushuncha o'rganilmaydi — tanish "
            "tushunchaning yangi shakli yodlanadi.</p>"
            "<h3>3. Jins yo'q</h3>"
            "<p>Na otda, na olmoshda. <code>O</code> — ham u (erkak), ham u (ayol), ham u "
            "(narsa). Rus tilini o'rganganlar bilishadi: jins tizimi eng ko'p vaqt oladigan "
            "qismlardan biri. Bu yerda u umuman yo'q.</p>"
            "<h3>4. Lug'atning bir qismi allaqachon tanish</h3>"
            "<p><code>kitap</code>, <code>dünya</code>, <code>insan</code>, "
            "<code>hayat</code>, <code>vakit</code>, <code>meydan</code>, "
            "<code>mektep</code> — arab va fors tilidan ikkala tilga ham kirgan so'zlar. "
            "Birinchi mingta so'zning sezilarli qismini siz allaqachon bilasiz; ularni "
            "yodlash emas, faqat talaffuzini to'g'rilash kerak.</p>"
            "<h3>5. Bor va yo'q</h3>"
            "<p><code>var</code> va <code>yok</code> aynan o'zbekchadagidek ishlaydi va gap "
            "oxirida turadi: <i>Masada kitap var</i>, <i>Evde kimse yok</i>. Ingliz tilidagi "
            "<i>there is / there are</i> konstruksiyasi bilan ovora bo'lish shart emas.</p>"
            "<h3>6. Ikki xil o'tgan zamon</h3>"
            "<p>Bu eng qiziq nuqta. O'zbekchadagi <i>-di</i> va <i>-ibdi</i> farqi turkchada "
            "<code>-dı</code> va <code>-mış</code> bo'lib takrorlanadi: birinchisi o'zim "
            "ko'rgan, ikkinchisi eshitgan voqea. <i>Ali keldi</i> va <i>Ali kelibdi</i> — "
            "<code>Ali geldi</code> va <code>Ali gelmiş</code>. Bu farqni boshqa tilda "
            "so'zlashuvchi oylab tushunmaydi, siz esa birinchi darsdayoq tushunasiz.</p>"
            "<h3>7. Unli uyg'unligi tanish tushuncha</h3>"
            "<p>O'zbek tilida ham bor, faqat ancha yumshoqroq. Ya'ni tamoyil notanish emas — "
            "turkchada u qat'iyroq va istisnosizroq qo'llanadi. Tushunish oson, "
            "avtomatlashtirish esa mashq talab qiladi.</p>"
            "<h3>Va qayerda o'xshashlik tugaydi</h3>"
            "<p>Afzallikni bilish yetarli emas — chegarasini ham bilish kerak, aks holda "
            "o'sha chegarada ishonch bilan xato qilinadi. Uch joyda ehtiyot bo'ling:</p>"
            "<ul>"
            "<li><b>Talaffuz:</b> <code>ı</code>, <code>ö</code>, <code>ü</code> tovushlari "
            "o'zbekchada yo'q, <code>c</code> harfi esa <i>j</i> deb o'qiladi.</li>"
            "<li><b>So'roq gap:</b> turkchada so'roq alohida so'z bilan yasaladi va shaxs "
            "qo'shimchasi o'sha so'zga ko'chadi — <code>Geliyor musun?</code></li>"
            "<li><b>Ma'nosi o'zgargan tanish so'zlar:</b> <code>bardak</code> — stakan, "
            "<code>durak</code> — bekat. Bular haqida alohida maqola bor.</li>"
            "</ul>"
            "<p>Xulosa: o'xshashlik sizga tezlik beradi, lekin e'tiborsizlik ham beradi. "
            "Birinchi oyda farqlar ro'yxatini alohida daftarga yozib boring — aynan o'sha "
            "ro'yxat sizni \"tushunarli gapiradigan\" darajadan \"to'g'ri gapiradigan\" "
            "darajaga olib o'tadi.</p>"
        ),
    },
    {
        "slug": "yolganchi-dostlar-turkcha-sozlar",
        "title": "\"Yolg'onchi do'stlar\": tanish ko'ringan, lekin boshqa ma'noli turkcha so'zlar",
        "tags": ("Lug'at",),
        "excerpt": (
            "Ba'zi turkcha so'zlar o'zbekchaga aynan o'xshaydi, ammo boshqa narsani "
            "anglatadi. Ular tarjimada emas, jonli suhbatda xato keltiradi."
        ),
        "featured_quote": "Eng xavfli so'z — noma'lum emas, noto'g'ri tanish so'z.",
        "body": (
            "<p>Umumiy lug'at o'zbek o'quvchisiga tezlik beradi. Lekin bir nechta so'z aynan "
            "shu tezlik tufayli tuzoqqa aylanadi: siz ularni bilaman deb o'ylaysiz va "
            "lug'atdan tekshirmaysiz. Tilshunoslikda bunday so'zlar \"yolg'onchi do'stlar\" "
            "deb ataladi.</p>"
            "<p>Noma'lum so'z xavfsiz — uni ko'rasiz, to'xtaysiz, qidirasiz. Noto'g'ri tanish "
            "so'z esa to'xtatmaydi: gapni tushundim deb o'ylaysiz va ma'no butunlay boshqa "
            "tomonga ketadi.</p>"
            "<h3>Eng ko'p uchraydiganlari</h3>"
            "<ul>"
            "<li><code>bardak</code> — <b>stakan</b>. O'zbekchadagi \"bardoq\" emas. "
            "<i>Bir bardak su</i> — bir stakan suv.</li>"
            "<li><code>durak</code> — <b>bekat</b>. <i>Otobüs durağı</i> — avtobus bekati.</li>"
            "<li><code>kabak</code> — <b>qovoq</b> (sabzavot), yuzdagi qovoq emas.</li>"
            "<li><code>oğlan</code> — <b>o'g'il bola</b>.</li>"
            "<li><code>yatak</code> — <b>karavot</b>. <code>yastık</code> esa yostiq, ya'ni "
            "bu ikkitasi o'zaro adashtiriladi.</li>"
            "<li><code>hava</code> — havo, ammo ko'pincha <b>ob-havo</b> ma'nosida: "
            "<i>Hava nasıl?</i> — Ob-havo qanday?</li>"
            "<li><code>sabah</code> — <b>ertalab</b> (sovun emas; sovun — <code>sabun</code>).</li>"
            "<li><code>bakan</code> — <b>vazir</b>. <i>Bakmak</i> (qaramoq) fe'lidan yasalgan "
            "bo'lsa-da, gazeta matnida deyarli doim vazirni bildiradi.</li>"
            "</ul>"
            "<h3>Ikkinchi guruh: ma'nosi torayganlar</h3>"
            "<p>Bu guruh yanada xavfliroq, chunki so'z ma'nosi butunlay boshqa emas — "
            "shunchaki torroq yoki rasmiyroq. <code>Mektep</code> turkchada eskirgan va "
            "kundalik nutqda <code>okul</code> ishlatiladi. <code>Vakit</code> mavjud, lekin "
            "oddiy suhbatda <code>zaman</code> tabiiyroq eshitiladi. Bunday so'zlarni "
            "ishlatsangiz xato qilmaysiz, lekin nutqingiz kitobiy va biroz g'alati "
            "chiqadi.</p>"
            "<h3>Nima qilish kerak</h3>"
            "<p>Bunday so'zlarni umumiy lug'at daftariga qo'shmang — ular uchun "
            "<b>alohida ro'yxat</b> yuriting. Sababi oddiy: ularni yodlash emas, "
            "<i>qayta yodlash</i> kerak, ya'ni miyangizdagi eski bog'lanishni almashtirish "
            "kerak. Bu boshqa turdagi ish.</p>"
            "<p>Har so'zga yakka tarjima emas, <b>gap</b> yozing. Yakka so'z esda qolmaydi, "
            "kontekst qoladi: <i>Garsondan bir bardak su istedim.</i> Keyingi safar "
            "<code>bardak</code> so'zini ko'rganingizda miyangiz stakanni emas, o'sha "
            "restoran manzarasini chaqiradi.</p>"
            "<p>Ikkinchi usul — ataylab noto'g'ri ishlatib ko'rish. Darsda bilib turib xato "
            "gap tuzing va o'qituvchi tuzatsin. Tuzatilgan xato yodlangan qoidadan ancha "
            "uzoqroq esda qoladi, chunki u hissiy iz qoldiradi.</p>"
            "<h3>Eshitish bo'limida ular ayniqsa qimmatga tushadi</h3>"
            "<p>Yozma matnda noto'g'ri tushunilgan so'zni qaytib o'qish mumkin. Audioda esa "
            "bunday imkoniyat yo'q: siz tanish so'zni eshitasiz, ma'noni o'zingizcha "
            "to'ldirasiz va keyingi gapni allaqachon noto'g'ri asosda tinglaysiz. Bitta so'z "
            "butun parchani buzadi.</p>"
            "<p>Shuning uchun imtihonga tayyorgarlik paytida bu ro'yxatni faqat o'qib "
            "chiqmang — uni <b>quloq bilan</b> mashq qiling. Har so'zni o'zingiz uchun ovoz "
            "chiqarib gapda ayting va yozib oling. Keyin bir kundan so'ng o'sha yozuvni "
            "tinglang: ma'no darhol tushunilsa, so'z o'z joyiga tushgan.</p>"
            "<h3>Ro'yxatni qanday to'ldirib borasiz</h3>"
            "<p>Tayyor ro'yxatni ko'chirib olishning foydasi kam — har kimning \"yolg'onchi "
            "do'st\"lari o'z lug'atiga bog'liq. Ishlaydigan usul: matn o'qiyotganda ma'nosi "
            "biroz g'alati tuyulgan har tanish so'zni belgilab boring, kun oxirida "
            "tekshiring. Haftada uch-to'rt so'z topilsa, bu yaxshi natija.</p>"
            "<h3>Oxirgi maslahat</h3>"
            "<p>Turk seriali yoki YouTube videosi ko'rayotganda tanish so'z eshitilib, gap "
            "ma'nosi g'alati tuyulsa — to'xtang va o'sha so'zni tekshiring. Katta ehtimol "
            "bilan siz yangi \"yolg'onchi do'st\" topdingiz. Bir oyda shunday yo'l bilan "
            "yig'ilgan 15-20 so'z sizni ko'pchilik o'quvchi tushib qoladigan tuzoqdan olib "
            "chiqadi.</p>"
        ),
    },
    {
        "slug": "har-kuni-20-daqiqa-takrorlash-jadvali",
        "title": "Har kuni 20 daqiqa: ishlaydigan takrorlash jadvali",
        "tags": ("Metodika", "Imtihon"),
        "excerpt": (
            "Haftada bir marta uch soat o'tirish — eng keng tarqalgan va eng samarasiz usul. "
            "Kunlik qisqa takror nima uchun kuchliroq ishlaydi va uni qanday tuzish kerak."
        ),
        "body": (
            "<p>Til o'rganishda eng ko'p uchraydigan xato — material tanlashda emas, vaqtni "
            "taqsimlashda. Haftada bir marta uzoq o'tirish yaxshi tuyuladi, chunki \"ko'p ish "
            "qilingandek\" his qoldiradi. Amalda esa oradagi olti kunda o'rganilgan "
            "narsaning katta qismi yo'qoladi va keyingi seansning yarmi o'shani qaytadan "
            "tiklashga ketadi.</p>"
            "<h3>Nima uchun kunlik qisqa takror kuchliroq</h3>"
            "<p>Esdan chiqarish birinchi kunlarda eng tez boradi — yangi ma'lumot bir necha "
            "kun ichida eng ko'p yo'qotiladi. Ya'ni takror aynan o'sha kunlarda kerak, bir "
            "hafta o'tgach emas.</p>"
            "<p>Hisob ham shuni ko'rsatadi: kuniga 20 daqiqa haftada 140 daqiqa beradi — bir "
            "seansdagi 180 daqiqadan <b>kam</b>, lekin natijasi ancha yuqori. Chunki bu yerda "
            "vaqt miqdori emas, uning taqsimlanishi ishlaydi.</p>"
            "<h3>20 daqiqani qanday bo'lish kerak</h3>"
            "<ul>"
            "<li><b>5 daqiqa — kechagini takrorlash.</b> Yangi material ko'rmasdan, faqat "
            "kecha o'rgangan so'z va qoidalarni tez ko'rib chiqing.</li>"
            "<li><b>10 daqiqa — yangi material.</b> Bitta qoida yoki 10-15 ta so'z. Ko'proq "
            "olsangiz, ertaga takrorlashga ulgurmaysiz va tizim buziladi.</li>"
            "<li><b>5 daqiqa — ishlab ko'rish.</b> Yangi materialdan foydalanib 5 ta gap "
            "yozing yoki ovoz chiqarib ayting.</li>"
            "</ul>"
            "<p>Oxirgi besh daqiqa eng muhimi va odatda birinchi bo'lib tashlab yuboriladi — "
            "\"vaqt tugadi, ertaga yozaman\". Aynan shu qism o'qilgan bilimni ishlatiladigan "
            "bilimga aylantiradi. O'qilgan qoida bilan qo'llanilgan qoida — ikki xil narsa: "
            "birinchisini imtihonda tanib olasiz, ikkinchisini gapirganda ishlata olasiz.</p>"
            "<h3>Haftalik tuzilma</h3>"
            "<p>Olti kun yuqoridagi tartib, yettinchi kun — faqat takror: yangi material yo'q. "
            "Shu kuni nimani unutganingiz ochiq ko'rinadi va keyingi hafta rejasi taxmin "
            "bilan emas, shu ro'yxat bilan tuziladi.</p>"
            "<p>Kun o'tkazib yuborsangiz nima bo'ladi? Hech narsa — ertasi kuni ikki "
            "barobar qilmang. \"Qarzni yopish\" urinishi 40 daqiqalik zerikarli seans beradi "
            "va odatda tizimning butunlay to'xtashi shundan boshlanadi. Shunchaki keyingi "
            "kundan odatdagidek davom eting.</p>"
            "<h3>Imtihonga tayyorgarlik oyida</h3>"
            "<p>Imtihonga bir oy qolganda tartib o'zgaradi: yangi material to'xtaydi va "
            "vaqtning yarmi mock topshiriqlarga o'tadi. Bu bosqichda yangi qoida o'rganish "
            "emas, mavjudini <b>vaqt bosimi ostida</b> qo'llay olish tekshiriladi.</p>"
            "<p>Mock topshiriqni har doim taymer bilan ishlang. Taymersiz ishlangan mashq "
            "haqiqiy imtihonni sinamaydi — u faqat bilimni tekshiradi, tezlikni emas. Ko'p "
            "o'quvchi imtihonda material bilmagani uchun emas, vaqtni noto'g'ri taqsimlagani "
            "uchun ball yo'qotadi.</p>"
            "<h3>Qanday kuzatiladi</h3>"
            "<p>Jadval faqat bajarilsa ishlaydi, bajarilishi esa ko'rinib turishi kerak. "
            "Eng oddiy usul — kalendarda har bajarilgan kunni belgilash. Uzilmagan zanjir "
            "o'zi undash kuchiga ega bo'ladi va ko'pchilik uchun bu har qanday motivatsion "
            "maslahatdan yaxshiroq ishlaydi.</p>"
        ),
    },
)

# ---------------------------------------------------------------------------
# Yaratish
# ---------------------------------------------------------------------------


def _resolve_author():
    """Kurs o'qituvchisi va maqola muallifi.

    Ataylab yangi hisob yaratmaydi: soxta foydalanuvchi katalogda o'qituvchi
    bo'lib ko'rinadi va teacher scope (`core/access.py`) unga kurs biriktiradi.
    Demo hisoblar kerak bo'lsa — `seed_demo`.
    """
    User = get_user_model()
    author = User.objects.filter(is_superuser=True, is_active=True).order_by("pk").first()
    if author is None:
        raise SampleContentError(
            "Superuser topilmadi. Avval `python manage.py createsuperuser` "
            "yugurtiring — kurs va maqolaga muallif kerak."
        )
    return author


def _seed_quiz(lesson, spec):
    quiz, _ = Quiz.objects.get_or_create(
        lesson=lesson,
        title=spec["title"],
        defaults={"xp_reward": spec["xp"]},
    )
    for question_spec in spec["questions"]:
        question, _ = Question.objects.get_or_create(
            quiz=quiz,
            text=question_spec["text"],
            defaults={"points": 5},
        )
        for choice_text, is_correct in question_spec["choices"]:
            Choice.objects.get_or_create(
                question=question,
                text=choice_text,
                defaults={"is_correct": is_correct},
            )
    return quiz


def _label(model):
    return f"{model._meta.app_label}.{model.__name__}"


def _mark_seeded(obj):
    """Yozuvni "buni seeder yaratdi" deb belgilaydi."""
    SeededRecord.objects.get_or_create(
        model_label=_label(type(obj)), object_id=obj.pk
    )


def _seeded_ids(model):
    return set(
        SeededRecord.objects.filter(model_label=_label(model)).values_list(
            "object_id", flat=True
        )
    )


def _is_seeded(obj):
    return SeededRecord.objects.filter(
        model_label=_label(type(obj)), object_id=obj.pk
    ).exists()


def _get_or_create_owned(model, lookup, defaults, what):
    """Faqat seeder yaratgan yozuvni qayta ishlatadi.

    Ko'rsatiladigan identifikator (sarlavha, slug) **egalik dalili emas**.
    Agar shu nomli yozuv bazada bor, lekin uni seeder yaratmagan bo'lsa —
    u ownerniki. Uni jimgina "namuna" deb qabul qilish ikki tomondan
    xavfli: seed unga o'z modul/darslarini qo'shib qo'yardi, `--wipe` esa
    uni cascade bilan o'chirib yuborardi.
    """
    existing = model.objects.filter(**lookup).first()
    if existing is not None:
        if not _is_seeded(existing):
            raise SampleContentError(
                f"{what}: bazada shu nom bilan seeder yaratmagan yozuv bor "
                f"(id={existing.pk}). U ownerniki deb hisoblanadi va tegilmaydi. "
                "Namuna kontentni yuklash uchun avval o'sha yozuvni qayta "
                "nomlang yoki moduldagi nomni o'zgartiring."
            )
        return existing, False

    obj = model.objects.create(**lookup, **defaults)
    _mark_seeded(obj)
    return obj, True


@transaction.atomic
def seed_sample_content():
    """Kurs, dars, test, vazifa, guruh va maqolalarni yaratadi. Idempotent."""
    author = _resolve_author()

    courses = []
    lesson_count = 0
    for course_spec in COURSES:
        course, _ = _get_or_create_owned(
            Course,
            {"title": course_spec["title"]},
            {
                "description": course_spec["description"],
                "instructor": author,
                "level": course_spec["level"],
                "duration": course_spec["duration"],
                # Rasm yuklanmagani uchun gradient cover: `cover_mode` model
                # defaulti `image`, ya'ni rasmsiz kurs katalogda bo'sh joy
                # bo'lib chiqadi.
                "cover_mode": "gradient",
                "gradient_preset": course_spec["gradient_preset"],
                "gradient_cover_title": course_spec["gradient_cover_title"],
                "gradient_cover_label": course_spec["gradient_cover_label"],
            },
            what=f"Kurs «{course_spec['title']}»",
        )
        courses.append(course)

        for module_order, module_spec in enumerate(course_spec["modules"], start=1):
            module, _ = Module.objects.get_or_create(
                course=course,
                title=module_spec["title"],
                defaults={"order": module_order},
            )
            for lesson_order, lesson_spec in enumerate(module_spec["lessons"], start=1):
                lesson, _ = Lesson.objects.get_or_create(
                    module=module,
                    title=lesson_spec["title"],
                    defaults={
                        "content": lesson_spec["content"],
                        "order": lesson_order,
                        "xp_reward": lesson_spec["xp"],
                    },
                )
                lesson_count += 1

                assignment_spec = lesson_spec.get("assignment")
                if assignment_spec:
                    Assignment.objects.get_or_create(
                        lesson=lesson,
                        title=assignment_spec["title"],
                        defaults={
                            "description": assignment_spec["description"],
                            "max_xp": assignment_spec["max_xp"],
                        },
                    )

                quiz_spec = lesson_spec.get("quiz")
                if quiz_spec:
                    _seed_quiz(lesson, quiz_spec)

        _get_or_create_owned(
            Cohort,
            {"name": course_spec["cohort"], "course": course},
            {
                "start_date": timezone.localdate()
                + datetime.timedelta(days=course_spec["cohort_starts_in_days"]),
                "is_active": True,
                # Har kursda bittadan default guruh bo'lishi mumkin
                # (`cohorts_one_checkout_default_per_course`), shuning uchun
                # bu kursdagi yagona guruh checkout defaulti bo'ladi.
                "is_checkout_default": not Cohort.objects.filter(
                    course=course, is_checkout_default=True
                ).exists(),
            },
            what=f"Guruh «{course_spec['cohort']}»",
        )

    # Teg — ataylab umumiy resurs: owner o'z maqolasida ishlatgan bo'lsa,
    # uni qayta ishlatish to'g'ri. Shuning uchun bu yerda rad etish yo'q,
    # faqat o'zimiz yaratganini belgilaymiz — `--wipe` shunga qaraydi.
    tags = {}
    for name in TAGS:
        tag, created = BlogTag.objects.get_or_create(name=name)
        if created:
            _mark_seeded(tag)
        tags[name] = tag

    posts = []
    for article in ARTICLES:
        post, created = _get_or_create_owned(
            BlogPost,
            {"slug": article["slug"]},
            {
                "title": article["title"],
                "author": author,
                "body": article["body"],
                "excerpt": article["excerpt"],
                "featured_quote": article.get("featured_quote", ""),
                "featured": article.get("featured", False),
                "status": BlogPost.STATUS_PUBLISHED,
            },
            what=f"Maqola «{article['slug']}»",
        )
        if created:
            post.tags.set([tags[name] for name in article["tags"]])
        posts.append(post)

    return {
        "courses": courses,
        "lesson_count": lesson_count,
        "posts": posts,
        "author": author,
    }


@transaction.atomic
def wipe_sample_content():
    """Faqat seeder **o'zi yaratgan** yozuvlarni oladi.

    Sarlavha yoki slug bo'yicha o'chirish xavfli edi: shu nomli haqiqiy kurs
    modul, dars va imtihoni bilan birga cascade'ga tushardi. Endi manba —
    `SeededRecord` izi.

    Tartib muhim: `Cohort.course` PROTECT bilan bog'langan, ya'ni kursni
    guruhidan oldin o'chirib bo'lmaydi.
    """
    for model in (Cohort, Course, BlogPost):
        ids = _seeded_ids(model)
        if not ids:
            continue
        model.objects.filter(pk__in=ids).delete()
        SeededRecord.objects.filter(
            model_label=_label(model), object_id__in=ids
        ).delete()

    # Teg umumiy resurs: seeder yaratgan bo'lsa ham, owner uni o'z maqolasiga
    # ilgan bo'lsa qoladi.
    tag_ids = _seeded_ids(BlogTag)
    if tag_ids:
        orphan_ids = set(
            BlogTag.objects.filter(pk__in=tag_ids, posts__isnull=True).values_list(
                "pk", flat=True
            )
        )
        BlogTag.objects.filter(pk__in=orphan_ids).delete()
        SeededRecord.objects.filter(
            model_label=_label(BlogTag), object_id__in=orphan_ids
        ).delete()
