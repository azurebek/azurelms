# Landing Editor — backoffice'da chiroyli landing boshqaruvi (bosqichli reja)

*Yaratildi: 2026-07-27 [Claude Code]. Branch: `claude/backoffice-landing-editor`. Owner admission: Azurbek (og'zaki, shu sessiya).*

## 1. Maqsad va muammo

Hozir bosh sahifa (`templates/index.html`) to'liq admin nazoratida (2026-07-27, `main`da), lekin uni tahrirlash faqat **Jazzmin admin** (`/admin/`, `ENABLE_LEGACY_ADMIN=True`) orqali. Bu:

- Owner uchun noqulay: ~50 maydonli xom fieldset, texnik ko'rinish, sahifa strukturasiga bog'lanmagan.
- Loyiha dizayn tizimidan (app-shell/admin-shell) tashqarida — brand/control kabi silliq backoffice yuzalariga zid.
- `/admin/` prod'da odatda o'chiq (`ENABLE_LEGACY_ADMIN=False`), ya'ni asosiy boshqaruv yo'li ishonchsiz.

**Yechim:** landing boshqaruvini mavjud **backoffice** ichiga, `/backoffice/landing/` sifatida, sahifa bo'limlariga (Hero, Demo, Statistika, Daraja yo'li, AI, Imtihon, Sertifikat, Footer) mos, chiroyli va qulay UI bilan ko'chiramiz. Jazzmin admin fallback sifatida qoladi.

## 2. Feature admission (gate javoblari)

1. **Qaysi muammo:** owner workload — landing tahriri texnik admin'ga bog'liq, sekin va noqulay.
2. **Asosiy KPI:** owner Jazzmin'siz, backoffice'dan landing'ning istalgan elementini ≤2 klikda topib tahrirlay olishi.
3. **Canonical state:** yangi state YO'Q. Manba o'sha `frontend` modellari (`LandingPage`, `Statistic`, `LandingLevelStage`, `LandingAIFeature`, `LandingExamSkill`, `LandingProcessStep`, `LandingNavItem`, `Testimonial`, hero slide/portal). Editor faqat shularni o'qiydi/yozadi.
4. **Adapterlar:** backoffice UI — yangi iste'molchi adapter; landing render (`home_view`) o'zgarmaydi. Dublikat biznes-logika yo'q.
5. **Owner yuki:** kamayadi (asosiy maqsad).
6. **Flag/rollback:** additive; Jazzmin admin va joriy render tegilmaydi, shuning uchun rollback = editor route'ini olib qo'yish. Har mutation `LogEntry` audit'ga yoziladi.
7. **Faza:** post-launch owner tooling (A2 backoffice kengaytmasi doktrinasiga mos — yangi parallel admin subsystem emas).

**Doktrina moslik:** A2 ("mavjud backoffice + aicontrol kengaytmasi; yangi parallel admin subsystem yo'q") ichidagi owner control surface. Brend (`/backoffice/control/brand/`) bilan bir xil pattern.

## 3. Dizayn tamoyillari

- **Bir manba:** editor `frontend` modellarini boshqaradi; landing render bilan bir xil haqiqat.
- **Backoffice dizayn tizimi:** `app-shell.css` + `admin-shell.css`; `brand_control.html` visual patterni (kartalar, seksiyalar, form-grid).
- **Bo'lim-markazli:** admin fieldset emas, sahifadagi haqiqiy bo'limlar bo'yicha guruhlash; har bo'lim yoniga "sahifada ko'rish" anchor va live preview.
- **Mutation xavfsizligi (brand pattern):** `transaction.atomic`, o'zgargan maydon aniqlanadi, no-op yo'l (o'zgarish bo'lmasa yozmaydi), `LogEntry` audit. `change_reason` — content uchun **ixtiyoriy** (brand'da majburiy edi; bu owner qaroriga qolsin, kunlik content tahririda majburiy sabab og'ir).
- **Repeatable ro'yxatlar:** inline qo'shish/tahrir/o'chirish + drag-reorder (mavjud `admin/js/landing_nav_sort.js` reorder patterni) + ko'rinish toggle. O'chirish — tasdiq bilan.
- **Ruxsat:** `_is_backoffice_user` (staff/superuser) — content darajasi; media yoki tuzilma o'zgarishi kerak bo'lsa owner-only qism ajratiladi.
- **Churn ehtiyot:** tegiladigan `.py`/`.html` fayllar repoda mixed CRLF/LF — LF normallashtirish yoki byte-patch, xom diff kattaligini finalда aytish.

## 4. Bosqichlar

### Bosqich 0 — Poydevor va reja *(shu bosqich)*
- Branch `claude/backoffice-landing-editor` ochildi.
- Backoffice pattern auditi (view/template/CSS/nav/brand mutation) qilindi.
- Shu reja nuclear-program'ga saqlandi.
- **DoD:** reja hujjati + branch + marinebook yozuvi.

### Bosqich 1 — Landing hub + singleton editor (`LandingPage`)
- Route `/backoffice/landing/` (`_is_backoffice_user`), nav'da yangi "Sayt" guruhi yoki "Kontent" ichida "Bosh sahifa".
- `LandingPageForm` (ModelForm) — ~50 maydon **sahifa bo'limlari bo'yicha** guruhlangan: Rail, Hero, Demo dashboard, Daraja yo'li sarlavhasi, AI bo'lim, Imtihon bo'lim, Sertifikat, Pastki CTA/Footer, Portal.
- Template `backoffice/landing_editor.html` — accordion/tab seksiyalar, form-grid, saqlash + no-op + audit (brand pattern).
- Har bo'lim yoniga "↗ sahifada ko'rish" (`/#anchor`) havolasi.
- **DoD:** `python manage.py test frontend core` yashil; `check` 0; browser QA (desktop+mobile, light/dark) — saqlash ishlaydi, landing'da aks etadi, audit yoziladi.

### Bosqich 2 — Repeatable ro'yxatlar menejeri
- Inline CRUD + reorder + visibility: `LandingLevelStage`, `LandingAIFeature`, `LandingExamSkill`, `Statistic`, `LandingProcessStep`.
- Har ro'yxat: qatorlar jadvali, "qo'shish" modal/inline forma, drag-reorder (JSON reorder endpoint), o'chirish tasdiqi.
- **DoD:** har model uchun add/edit/delete/reorder testlari; browser QA; landing'da tartib/ko'rinish aks etadi.

### Bosqich 3 — Navigatsiya, footer va boy ro'yxatlar
- `LandingNavItem` (main/utility/footer) menejeri — placement bo'yicha guruh, reorder, custom URL.
- `Testimonial`, `LandingHeroSlide` + `LandingHeroSlideMetric`, `LandingPortalTab`/`LandingPortalListItem`.
- Media yuklash (hero image/video, background) — preview bilan; MIME/hajm ehtiyot (A0b bilan bog'liq).
- **DoD:** nav/footer landing'da to'g'ri; media upload preview; testlar.

### Bosqich 4 — Live preview va polish
- `/` ning iframe preview'i editor yonida yoki "Ko'rish" tugmasi; saqlagach yangilanadi.
- Bo'sh/xato holatlar, mobil responsive, dark/light, keyboard/focus, uzun matn overflow.
- **DoD:** 3 kenglik (desktop/tablet/mobil) browser evidence; console 0; overflow 0.

### Bosqich 5 — Ruxsat, audit, xavfsizlik, hujjat
- Ruxsat yakuniy: content = staff, tuzilma/media = owner (kerak bo'lsa).
- Audit paneli (so'nggi o'zgarishlar, `LogEntry`), rollback yo'li.
- Jazzmin admin taqdiri: fallback qoladimi yoki landing modellarini admin'dan yashiramizmi — owner qaroriga.
- `project-context.md` + `marinebook.md` yangilash. Feature flag/kill switch ko'rib chiqish.
- **DoD:** to'liq test suite; owner sign-off; docs yangilangan.

### Bosqich 6 — (Ixtiyoriy) boshqa public sahifalar
- Xuddi shu editor patternida: `AboutPage`/`TeamMember`, `LegalPage`, `AuthPageSettings`. Landing tugagach, alohida admission.

## 5. Har bosqich uchun umumiy DoD
- Tegishli testlar (`frontend`, `core`) yashil, aniq command bilan.
- `manage.py check` 0; model o'zgarsa `makemigrations --check`.
- Dublikat biznes-logika yo'q; render `home_view` o'zgarmaydi.
- Browser evidence (desktop+mobil, light/dark) — overflow/console 0.
- Mutation `LogEntry` audit'ga tushadi; no-op yo'l bor.
- Commit + marinebook (major bosqichlarda).

## 6. Ochiq qarorlar (owner)
1. `change_reason` content tahririda majburiymi yoki ixtiyoriy? *(taklif: ixtiyoriy)*
2. Ruxsat: content'ni butun staff tahrirlaydimi yoki faqat owner? *(taklif: staff content, owner tuzilma)*
3. Bosqich tugagach Jazzmin admin'dan landing modellari yashirinsinmi yoki fallback qolsinmi? *(taklif: fallback qolsin)*
4. Live preview iframe kerakmi yoki "yangi tabda ko'rish" yetarlimi? *(taklif: 1-bosqichda anchor havola, 4-bosqichda iframe)*
