# AzureLMS — Launch rejasi (2026-09-20)

**Maqsad:** 20-sentyabr 2026 — loyiha taqdimoti va ishga tushirish. Bugungi kundan (11-iyul) unga **71 kun / ~10 hafta** bor.

**Model (2026-07-11 aniqlandi, Azurbek):** platforma mustaqil o'rgatuvchi EMAS — **Azurbekning jonli onlayn turk tili kursining raqamli dastagi**. Jonli darslar Telegram video chatda o'taveradi; platforma esa davomat, uyga vazifa, quiz, imtihon, reyting, yozilgan video darslar (jonli dars o'tilgach ochiladi), AI yordamchi, muloqot va reklama oqimini beradi. O'quvchilarning ~99% i — **O'zbekistonda magistraturaga kirish uchun chet tili sertifikati** (turk tilini tanlab) olayotganlar.

Bu papka launch'gacha bo'lgan strategiya, reja va taktikaning yagona manbai:

| # | Hujjat | Nima haqida |
|---|---|---|
| 01 | [Strategiya](01-strategiya.md) | Bozor (magistratura sertifikat talabi — rasmiy buyruq faktlari), segmentlar, raqobat, pozitsiyalash, **7 imzo-harakat**, narx |
| 02 | [Yo'l xaritasi](02-yol-xarita.md) | 6 faza (P0–P5), sanalar, chiqish-kriteriylar, risklar, metrikalar |
| 03 | [Mahsulot backlog](03-mahsulot-backlog.md) | QURISH / SAYQALLASH / KESISH — qabul kriteriylari bilan |
| 04 | [Kontent reja](04-kontent-reja.md) | Video darslar quvuri, milliy sertifikat mock imtihonlari, daraja testi banki, ko'priklar, blog |
| 05 | [Launch operatsiyalari](05-launch-ops.md) | Deploy, beta (=kuzgi jonli guruh), QA, 20-sentyabr demo ssenariysi, checklist, marketing |

---

## TL;DR — bir sahifada

**Biznes tezisi:** O'zbekistonda har magistratura talabgori chet tili sertifikati topshirishi **majburiy** (2024-yilgi vazirlik buyrug'i: yo'nalishga qarab B1/B2/C1). Til erkin tanlanadi — va o'zbek uchun turkcha eng qisqa yo'l (qardosh til; hatto C1 talab qilingan til-yo'nalishlarida ham qardosh tillarga B2 yetadi). Bitta UZBMB turk tili imtihonida 5200+ kishi qatnashgan — talab o'lchangan va katta. Azurbek shu oqimga yillardir jonli kurs o'tadi; **platforma bu kursni boshqa hech kimda yo'q darajaga ko'taradi**.

**Pozitsiya:** *"Jonli ustoz kursi + aqlli platforma"* — boshqa o'qituvchilar Telegram guruh + PDF bilan ishlaganda, bizda: yozilgan sifatli video darslar (jonli darsdan keyin ochiladi), avtomatik davomat, vazifa-tekshiruv, milliy sertifikat formatidagi mock imtihonlar, reyting, va **Azure AI — darslar orasida 24/7 yordamchi** (foto-vazifani o'qiydi, xatoni o'zbekcha tushuntiradi, zaif joyni eslab qoladi).

**Retention yadrosi:** jonli dars ritmi (haftalik jadval) + kunlik 5-daqiqalik ritual (SRS takror + bugungi ko'prik) + streak + Telegram xabarlar (O'zbekistonda Telegram qamrovi 76–88% — auditoriya allaqachon shu yerda, darslar ham shu yerda).

**Fazalar:**
- **P0** (11–15 iyul): poydevor — branch merge, qarorlar (kurs dasturi, narx, video-yozish jadvali)
- **P1** (16 iyul – 5 avg): farqlovchi yadro — daraja testi, SRS lug'at, AI skilllar, **o'qituvchi kun-oqimi** (dars ochish/davomat/vazifa bir tugmada), exam JS qarzi
- **P2** (6–24 avg): odat halqasi — Telegram loop, streak, **birinchi deploy**, analytics, freemium oqim
- **P3** (25 avg – 7 sen): ishonch — landing, to'lov UX, mobil audit, **1-sen: kuzgi jonli guruh platformada boshlanadi (= beta)**
- **P4** (8–16 sen): qattiqlash — fixlar, xavfsizlik, checklist, demo aktivlar
- **P5** (17–20 sen): taqdimot va ommaviy launch

**Eng katta 3 risk:** (1) video darslar yozish — Azurbek vaqtiga bog'liq eng uzun ustun, P0'da jadval kelishiladi; (2) prod deploy hali qilinmagan — P2'da erta; (3) jonli kurs + qurilish parallel yuki — scope-freeze muqaddas.

---

*Yaratilgan: 2026-07-11, Claude. 2026-07-11 kechqurun Azurbek modeli aniqlangach qayta yozildi. Har faza yakunida yangilanadi.*
