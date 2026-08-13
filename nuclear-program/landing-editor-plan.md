# Landing Editor — backoffice'da chiroyli landing boshqaruvi (bosqichli reja)

*Yaratildi: 2026-07-27 [Claude Code]. Rebaseline: 2026-08-14. Bosqich 0 va Bosqich 1 kodi/TOC main'da; Bosqich 1 authenticated visual QA kutadi. Bosqich 2–4 `HOLD/NEXT`, Bosqich 5 partial, Bosqich 6 optional; active core slice emas.*

## Joriy status

| Bosqich | Holat | Evidence / gap |
|---|---|---|
| 0 | `DONE` | plan va pattern auditi |
| 1 | `IN PROGRESS — implemented/tested` | `90d879e`: `/backoffice/landing/`, owner-only, reason+confirm, `LogEntry`, no-op; `6042702`: TOC/tab; authenticated visual QA pending |
| 2–3 | `HOLD/NEXT` | repeatable CRUD/reorder, nav/rich/media manager yo'q |
| 4 | `HOLD/NEXT` | iframe live preview va to'liq visual evidence yo'q |
| 5 | `PARTIAL` | mutation audit bor; audit history/rollback/permission finalization yo'q |
| 6 | `OPTIONAL` | alohida admission talab qiladi |

## 1. Maqsad va muammo

Historical muammo: bosh sahifa modeli bor edi, lekin tahrirlash faqat **Jazzmin admin** (`/admin/`, `ENABLE_LEGACY_ADMIN=True`) orqali edi. 2026-07-27 da Bosqich 1 bajarilib, singleton matnlar `/backoffice/landing/`ga ko'chdi. Hozirgi gap — repeatable ro'yxatlar, media va preview hali Jazzmin/fallbackga bog'liq:

- Owner uchun noqulay: ~50 maydonli xom fieldset, texnik ko'rinish, sahifa strukturasiga bog'lanmagan.
- Loyiha dizayn tizimidan (app-shell/admin-shell) tashqarida — brand/control kabi silliq backoffice yuzalariga zid.
- `/admin/` prod'da odatda o'chiq (`ENABLE_LEGACY_ADMIN=False`), ya'ni asosiy boshqaruv yo'li ishonchsiz.

**Yechim yo'nalishi:** mavjud `/backoffice/landing/`ni shu modellarning yagona owner adapteri sifatida bosqichma-bosqich kengaytirish. Jazzmin admin hozir fallback; yangi bosqichlar A8/A0b/A1a/core golden-flow ishlarini siqib chiqarmaydi.

## 2. Feature admission (gate javoblari)

1. **Qaysi muammo:** owner workload — landing tahriri texnik admin'ga bog'liq, sekin va noqulay.
2. **Asosiy KPI:** owner Jazzmin'siz, backoffice'dan landing'ning istalgan elementini ≤2 klikda topib tahrirlay olishi.
3. **Canonical state:** yangi state YO'Q. Manba o'sha `frontend` modellari (`LandingPage`, `Statistic`, `LandingLevelStage`, `LandingAIFeature`, `LandingExamSkill`, `LandingProcessStep`, `LandingNavItem`, `Testimonial`, hero slide/portal). Editor faqat shularni o'qiydi/yozadi.
4. **Adapterlar:** backoffice UI — yangi iste'molchi adapter; landing render (`home_view`) o'zgarmaydi. Dublikat biznes-logika yo'q.
5. **Owner yuki:** kamayadi (asosiy maqsad).
6. **Flag/rollback:** additive; Jazzmin admin va joriy render tegilmaydi, shuning uchun rollback = editor route'ini olib qo'yish. Har mutation `LogEntry` audit'ga yoziladi.
7. **Faza:** A8/A0b/A1a va core gate'lardan keyingi owner tooling (A2 backoffice kengaytmasi doktrinasiga mos — yangi parallel admin subsystem emas).

**Doktrina moslik:** A2 ("mavjud backoffice + aicontrol kengaytmasi; yangi parallel admin subsystem yo'q") ichidagi owner control surface. Brend (`/backoffice/control/brand/`) bilan bir xil pattern.

## 3. Dizayn tamoyillari

- **Bir manba:** editor `frontend` modellarini boshqaradi; landing render bilan bir xil haqiqat.
- **Backoffice dizayn tizimi:** `app-shell.css` + `admin-shell.css`; `brand_control.html` visual patterni (kartalar, seksiyalar, form-grid).
- **Bo'lim-markazli:** admin fieldset emas, sahifadagi haqiqiy bo'limlar bo'yicha guruhlash; har bo'lim yoniga "sahifada ko'rish" anchor va live preview.
- **Mutation xavfsizligi (brand pattern):** `transaction.atomic`, o'zgargan maydon aniqlanadi, no-op yo'l (o'zgarish bo'lmasa yozmaydi), `LogEntry` audit. Owner qaroriga ko'ra `change_reason` va explicit confirmation **majburiy**.
- **Repeatable ro'yxatlar:** inline qo'shish/tahrir/o'chirish + drag-reorder (mavjud `admin/js/landing_nav_sort.js` reorder patterni) + ko'rinish toggle. O'chirish — tasdiq bilan.
- **Ruxsat:** joriy editor `_is_control_center_owner` bilan faqat active superuserga ochiq; yangi repeatable/media mutationlar ham owner yangi qaror bermaguncha shu gate'da qoladi.
- **Churn ehtiyot:** tegiladigan `.py`/`.html` fayllar repoda mixed CRLF/LF — LF normallashtirish yoki byte-patch, xom diff kattaligini finalda aytish.

## 4. Bosqichlar

### Bosqich 0 — Poydevor va reja — `DONE`
- Branch `claude/backoffice-landing-editor` ochildi.
- Backoffice pattern auditi (view/template/CSS/nav/brand mutation) qilindi.
- Shu reja nuclear-program'ga saqlandi.
- **DoD:** reja hujjati + branch + marinebook yozuvi.

### Bosqich 1 — Landing hub + singleton editor (`LandingPage`) — `IMPLEMENTED/TESTED; VISUAL QA PENDING`
- Route `/backoffice/landing/` (`_is_control_center_owner`), nav'da "Bosh sahifa" entry'si.
- `LandingPageForm` (ModelForm) — ~50 maydon **sahifa bo'limlari bo'yicha** guruhlangan: Rail, Hero, Demo dashboard, Daraja yo'li sarlavhasi, AI bo'lim, Imtihon bo'lim, Sertifikat, Pastki CTA/Footer, Portal.
- Template `backoffice/landing_editor.html` — accordion/tab seksiyalar, form-grid, saqlash + no-op + audit (brand pattern).
- Har bo'lim yoniga "↗ sahifada ko'rish" (`/#anchor`) havolasi.
- **DoD:** `python manage.py test frontend core` yashil; `check` 0; browser QA (desktop+mobile, light/dark) — saqlash ishlaydi, landing'da aks etadi, audit yoziladi.
- **Evidence:** `90d879e` funksional editor; `6042702` bo'lim TOC/tab. Implementatsiya sessiyasida focused 12/12 va check 0. Authenticated full visual QA qayta bajarilmaguncha UI “to'liq finished” deyilmaydi.

### Bosqich 2 — Repeatable ro'yxatlar menejeri — `HOLD/NEXT`
- Inline CRUD + reorder + visibility: `LandingLevelStage`, `LandingAIFeature`, `LandingExamSkill`, `Statistic`, `LandingProcessStep`.
- Har ro'yxat: qatorlar jadvali, "qo'shish" modal/inline forma, drag-reorder (JSON reorder endpoint), o'chirish tasdiqi.
- **DoD:** har model uchun add/edit/delete/reorder testlari; browser QA; landing'da tartib/ko'rinish aks etadi.

### Bosqich 3 — Navigatsiya, footer va boy ro'yxatlar — `HOLD/NEXT`
- `LandingNavItem` (main/utility/footer) menejeri — placement bo'yicha guruh, reorder, custom URL.
- `Testimonial`, `LandingHeroSlide` + `LandingHeroSlideMetric`, `LandingPortalTab`/`LandingPortalListItem`.
- Media yuklash (hero image/video, background) — preview bilan; MIME/hajm ehtiyot (A0b bilan bog'liq).
- **DoD:** nav/footer landing'da to'g'ri; media upload preview; testlar.

### Bosqich 4 — Live preview va polish — `HOLD/NEXT`
- `/` ning iframe preview'i editor yonida yoki "Ko'rish" tugmasi; saqlagach yangilanadi.
- Bo'sh/xato holatlar, mobil responsive, dark/light, keyboard/focus, uzun matn overflow.
- **DoD:** 3 kenglik (desktop/tablet/mobil) browser evidence; console 0; overflow 0.

### Bosqich 5 — Ruxsat, audit, xavfsizlik, hujjat — `PARTIAL/HOLD`
- Ruxsat yakuniy: content = staff, tuzilma/media = owner (kerak bo'lsa).
- Audit paneli (so'nggi o'zgarishlar, `LogEntry`), rollback yo'li.
- Jazzmin admin taqdiri: fallback qoladimi yoki landing modellarini admin'dan yashiramizmi — owner qaroriga.
- `project-context.md` + `marinebook.md` yangilash. Feature flag/kill switch ko'rib chiqish.
- **DoD:** to'liq test suite; owner sign-off; docs yangilangan.

### Bosqich 6 — (Ixtiyoriy) boshqa public sahifalar — `OPTIONAL`
- Xuddi shu editor patternida: `AboutPage`/`TeamMember`, `LegalPage`, `AuthPageSettings`. Landing tugagach, alohida admission.

## 5. Har bosqich uchun umumiy DoD
- Tegishli testlar (`frontend`, `core`) yashil, aniq command bilan.
- `manage.py check` 0; model o'zgarsa `makemigrations --check`.
- Dublikat biznes-logika yo'q; render `home_view` o'zgarmaydi.
- Browser evidence (desktop+mobil, light/dark) — overflow/console 0.
- Mutation `LogEntry` audit'ga tushadi; no-op yo'l bor.
- Commit + marinebook (major bosqichlarda).

## 6. Owner qarorlari (2026-07-27 tasdiqlandi)
1. **Ruxsat:** faqat owner (active superuser) — `_is_control_center_owner`, brend paneli kabi.
2. **`change_reason`:** har saqlashda **majburiy** — brend paneli kabi to'liq audit izi.
3. **Preview:** Bosqich 1'da har bo'lim yoniga "↗ sahifada ko'rish" anchor havola; to'liq iframe live preview Bosqich 4'da.
4. **Jazzmin fallback:** hozircha qoladi (Bosqich 5'da qayta ko'riladi).

Natija: Bosqich 1 brend panel pattern'iga aynan mos — `_is_control_center_owner`, majburiy `change_reason` + `confirm`, `transaction.atomic` + `LogEntry` audit, no-op yo'l, `admin-shell.css` + dedicated `landing-control.css`.
