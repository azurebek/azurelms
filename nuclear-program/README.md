# AzureLMS — joriy holat va hujjatlar xaritasi

**Shu yerdan boshlang.** Bu sahifa loyihada nima tayyor, nima ochiq va
tafsilotni qayerdan topishni jamlaydi. AI agentlar avval [AGENTS.md](../AGENTS.md)
va [ish qoidalarini](rules-for-agents.md) o‘qiydi.

Oxirgi solishtirish: **2026-10-13**, kod tayanchi `main`dagi **`13a615b`**.
Bu sana va commit quyidagi holat qaydining chegarasi; keyingi ishda Git va
yangi dalillar bilan yangilanadi. Tarixiy rejadagi checkbox yoki eski test
soni o‘z-o‘zidan bugungi ishlar ro‘yxati hisoblanmaydi.

## Hozir qayerdamiz?

| Qism | Tasdiqlangan holat | Tafsilot |
|---|---|---|
| Asosiy platforma | Django LMS: kurs/dars, topshiriq/test/imtihon, o‘qituvchi tekshiruvi, guruh/to‘lov, kutubxona, Classbook, messenger, Telegram va AI qatlamlari kodda mavjud. Har birining ishlashi ruxsat, sozlama va muhitga bog‘liq. | [Arxitektura va kod xaritasi](project-context.md) |
| Backoffice islohoti | Dastlabki olti bosqich, eski muharrirlarni soddalashtirish va **B2.1–B2.6 lokal texnik ishlari bajarilgan**. B2.6 [PR #189](https://github.com/azurebek/azurelms/pull/189) orqali `62dd358`ga qo‘shilgan; [uchta majburiy CI tekshiruvi](https://github.com/azurebek/azurelms/actions/runs/38443075952) muvaffaqiyatli. | [Yagona backoffice rejasi](frontend-v1/BACKOFFICE-REFORM-PLAN.md), [B2.6 dalili](frontend-v1/BACKOFFICE-02-STAGE-6.md) |
| Keyingi backoffice bosqichi | **BACKOFFICE-03 rejalashtirildi, implementatsiya boshlanmagan.** Yetti bosqich: xavfsiz sozlamalar, exam qoralama/nashri, to‘liq exam muharriri, qayta foydalanish, ko‘rinadigan landing kontenti, qolgan dizayn consumerlari va texnik qabul/reliz paketi. Birinchi ish B3.1a; owner shaxsiy testi old shart emas. | [B3 qamrov va tugash mezonlari](frontend-v1/BACKOFFICE-REFORM-PLAN.md#backoffice-03) |
| Lokal backoffice | B2.6 yakunida `8092` serverida avval yoqilgan beshta B2 gate ON saqlangan. Registrdagi default qiymatlar OFF. Bu qayd barcha muhitda funksiyalar yoqilganini anglatmaydi. | [Lokal yoqish chegarasi](frontend-v1/BACKOFFICE-LOCAL-ROLLOUT.md), [flag registri](../core/flags.py) |
| AWS | **Oxirgi hujjatlashtirilgan reliz — 2026-09-26 R2, `8bb6b95`**, o‘sha tekshiruvda 19 ta V1 renderer flagi ON. Oktabrdagi B2 ishlarining serverga chiqarilgani shu dalildan kelib chiqmaydi. | [R2 reliz qaydi](frontend-v1/R2-READY-V1-AWS.md), [deploy yo‘riqnomasi](../deploy/README.md) |
| Dizayn prototipi va haqiqiy ilova | DESIGN-01 ustaxonasi va uning dalillari bor; haqiqiy Django backoffice dizayn oqimi alohida qurilgan. Prototip, kodga ko‘chirish, lokal test va owner qabuli turli holatlar. | [Frontend indeksi](frontend-v1/README.md), [ko‘chirish ledgeri](frontend-v1/PORT-LEDGER.md), [DC6 qabuli](frontend-v1/DESIGN-01-DC6-ACCEPTANCE.md) |

Bu hujjat yangilanishida server holati qayta kuzatilmadi, deploy bajarilmadi.

## Uch asosiy ishni qayerdan boshlash kerak?

Yoqilgan lokal backoffice va tegishli ruxsat bilan:

| Ish | Boshlanish joyi | Hozirgi imkoniyat |
|---|---|---|
| Kurs va dars tayyorlash | **Kurslar** — `/backoffice/workspace/courses/` | Kurs/modul/dars, materiallar, topshiriq va quiz tayyorlash, namuna ko‘rish; imtihon va bo‘limni tahrirlashga kontekst bilan o‘tish. |
| O‘quvchi muammosini topish | **O‘quvchilar** — `/backoffice/workspace/students/` | Kurs/darsga kirish sababini, topshiriq va e’lon qilingan natijani, xabar yetkazish holatini ko‘rish; tegishli tekshiruvdan ayni kartaga qaytish. |
| Dizaynni kodsiz sozlash | **Sayt va dizayn → Ko‘rinish** (owner) — `/backoffice/control/design/` | Ruxsat etilgan rang, shrift, o‘lcham va shakllar; qoralama/namuna, nashr qilish va oldingi nashrga qaytish. |

Ish stoli, umumiy qidiruv va yaqindagi ishlar shu oqimlar o‘rtasida yo‘lni
saqlaydi. [B2.1–B2.6 tafsilotlari](frontend-v1/BACKOFFICE-REFORM-PLAN.md#backoffice-02)
har bir imkoniyatning chegarasini ko‘rsatadi.

## Hali ochiq qolganlar

Quyidagi ishlarning agent bajaradigan keyingi qamrovi [B3 rejasida](frontend-v1/BACKOFFICE-REFORM-PLAN.md#backoffice-03)
ajratilgan. Reja yozilishi ularning bajarilganini anglatmaydi; keng versioning,
public UX va production masalalari o‘z chegaralarida qoladi.

- **Azurbekning shaxsiy foydalanish qabuli** keyinga qoldirilgan. Lokal
  texnik yakun uni bajarilgan deb belgilamaydi.
- **Haqiqiy telefon, brauzerning native zoom’i va screen reader** bilan
  qabul ochiq. Ekran kengligi va 200% render matni sinovlari ularning o‘rnini
  bosmaydi. B2 uchun production rollout ham alohida ish.
- **Barcha kontent uchun to‘liq builder va ishlatilgan kontentni keng
  versiyalash** B2 doirasida tugatilmagan. Imtihonning reading/listening savol
  tuzilmalari, SIT/Mini App dizayn qamrovi va vendor/print cheklovlari tegishli
  ledgerlarda ochiq qoladi.
- **UX, DATA va RULE masalalari** bo‘yicha [qabul muammolari ro‘yxati](frontend-v1/FINAL-ACCEPTANCE-ISSUES.md)
  saqlanadi. “B2 tugadi” ularni avtomatik yopmaydi.
- **A2 AI sozlamalari auditi**: mavjud AI settings yozish yuzalariga sabab,
  tasdiq va `SystemAuditEvent`ni qo‘shish qarzi ochiq. **A9 AI eval, latency va cost release gate**
  va boshqa launch gate’lari [launch-ops](launch-plan/05-launch-ops.md)da;
  ularning holati B2 natijasi bilan o‘zgarmaydi.

## Qaysi hujjat nima uchun?

| Kerakli ma’lumot | Asosiy manba |
|---|---|
| Joriy umumiy holat va ochiq chegaralar | **Shu sahifa** |
| Kod tuzilishi, domenlar va ish oqimlari | [project-context.md](project-context.md) |
| Agentning branch, test, commit va merge tartibi | [rules-for-agents.md](rules-for-agents.md), [AGENTS.md](../AGENTS.md) |
| Qachon nima bajarilgani, commit va test dalili | [marinebook.md](marinebook.md) — sanali tarix |
| Backoffice, dizayn va frontend tafsilotlari | [Frontend indeksi](frontend-v1/README.md), [backoffice rejasi](frontend-v1/BACKOFFICE-REFORM-PLAN.md) |
| Owner strategiyasi, admission va qolgan launch ishlari | [Launch rejasi](launch-plan/README.md) — eski jadval yangi deadline emas |
| Tarif va to‘lov shartlari | [Pricing ledgeri](pricing-packages-plan.md) |
| Telegram va landing bo‘yicha dastlabki shartlar | [Telegram rejasi](telegram-bot-plan.md), [landing rejasi](landing-editor-plan.md) — sanali qismlarni joriy kod bilan birga o‘qing |
| Serverga chiqarish va qaytarish tartibi | [Deploy yo‘riqnomasi](../deploy/README.md) |

`codex-context.md`, eski handofflar, bosqich hisobotlari va marinebookdagi
yozuvlar o‘z sanasidagi dalilni saqlaydi. Ular shu sahifaga parallel yangi
“joriy vazifalar” navbatini yaratmaydi. Owner qarorlari va domen shartlari
esa keyingi aniq qaror bilan almashtirilmaguncha o‘z kuchida qoladi.

## Tekshiruv dalilini qanday o‘qish kerak?

So‘nggi B2.6 lokal dalili: **10/10 ssenariy**, Django **1784 jami / 1735 PASS /
49 skip**, Node **172/172 PASS**. Bu butun loyihaning bugungi test soni emas;
aniq buyruqlar, skip sabablari va muhit [B2.6 hisobotida](frontend-v1/BACKOFFICE-02-STAGE-6.md).
Testlar haqiqiy Gemini/Telegram kalitlarisiz bajarilgan. Shu hujjatlarni
yangilash paytida ushbu natijalar qayta yugurtirilgan deb ko‘rsatilmaydi.

Holat o‘zgarganda shu sahifa, tegishli batafsil contract va marinebook
bir ish doirasida moslashtiriladi. Tarixiy test soni va sana qayta yozilmaydi;
yangi tekshiruv yangi sanali dalil bo‘ladi. “Kodda bor”, “muhitda yoqilgan”,
“tekshirildi”, “owner qabul qildi” va “serverga chiqarildi” alohida qayd qilinadi.
