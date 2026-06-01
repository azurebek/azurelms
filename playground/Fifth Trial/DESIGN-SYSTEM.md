# Fifth Trial — Design System

AzureLMS prototip tizimi. Asos: Coursera'dan kalibrlangan klon (jonli o'lchov).
**Yagona manba:** `style.css` (tokenlar + komponentlar), `design-system.html` (visual reference) + ushbu hujjat.
Sahifalar: `public/` (ochiq) va `auth/`. Mascot/character alohida: `brand/`.

> Qoida: yangi kod **faqat token** ishlatadi — hardcoded px/hex emas.

---

## 1. Font
`Source Sans 3` (`--font`). Vaznlar: **400** (`--fw-r`), **600** (`--fw-sb`), **700** (`--fw-b`, faqat display/logo).

## 2. Type scale
| Token | Qiymat | Ishlatilishi |
|---|---|---|
| `--fs-xs` | 12px | caption, mayda meta |
| `--fs-sm` | 14px | **HUKMRON**: meta, nav, footer, label, chip, reyting |
| `--fs-base` | 16px | asosiy matn, tugma, input |
| `--fs-md` | 18px | karta sarlavhasi, lead |
| `--fs-lg` | 20px | blok/ustun sarlavha, kurs nomi |
| `--fs-xl` | 22px | kichik sektsiya sarlavha |
| `--fs-2xl` | 24px | sektsiya sarlavha (cd-h2) |
| `--fs-3xl` | 28px | yirik sarlavha |
| `--fs-display` | 34px | display |
| `--fs-hero` | clamp(30,4vw,44) | hero sarlavha |

Line-height: `--lh-tight 1.2` (sarlavha), `--lh-base 1.6` (matn).

## 3. Spacing (4px-grid)
`--space-1…9` = 4 · 8 · 12 · 16 · 20 · 24 · 32 · 48 · 64 px.

## 4. Color
**Brend / fonlar:**
| Token | Qiymat | Ishlatilishi |
|---|---|---|
| `--blue` | #0056d2 | CTA, link, aktiv |
| `--blue-dark` | #00419e | hover |
| `--blue-deep` | #0048b0 | gradient |
| `--navy` | #08246b | to'q band (stat, CTA) |
| `--blue-soft` | #eef4ff | yumshoq ko'k fon |
| `--lilac-panel` | #eaf1fb | ochiq-ko'k band (hero/legal) |
| `--cream` | #fff4e8 | iliq promo fon |

**Ink / neytral:** `--ink #0f1114` · `--ink-2 #5b6780` · `--ink-3 #8a94a6` · `--bg #fff` · `--gray #f7f9fa` · `--line #d9dde3` · `--line-2 #eceef1` · `--dark #1f1f1f` (topbar).

> Reyting yulduzlari **to'q** (`--ink`), Coursera kabi (gold emas).

## 5. Radius / Shadow / Layout
- Radius: `--r-sm 6` · `--r-btn 8` · `--r-card 12` · `--r-banner 24` · `--r-pill 999`.
- Shadow: `--sh-sm` (kichik) · `--sh-md` (panel) · `--sh-lg` (modal).
- Layout: `--wrap 1408px` · `--pad 32px` → desktop content eni `1344px`.

---

## 6. Komponentlar inventari
**Asos:** `.btn` (`.btn-primary/.btn-white/.btn-outline`, `.btn-sm`, `.btn-block`) · `.textlink`

**Navigatsiya:** `.topbar` · `.header`+`.search` · `.nav-item` · `.crumb` (breadcrumb) · `.cd-subnav` (sticky) · `.pager`

**Hero / promo:** `.promo`(`-blue/-cream/-lilac`)+`.blob`+`.promo-person`+`.dots` (karusel) · `.jobready`+`.tabs/.tab`+`.jr-cards` (gradient) · `.wide2`(`-blue/-navy`) · `.cd-hero`+`.cd-art`

**Kartalar:** `.ccard` (kompakt gorizontal) · `.vcard` (vertikal) · `.ccourse` (katalog batafsil) · `.career-card`+`.career-fan` · `.course-list`+`.course-item`+`.course-thumb` (accordion) · `.cert-row`

**Bo'lim bloklari:** `.section`(`-gray`)+`.section-head/-link` · `.believe` (to'q ko'k band, 4 ustun) · `.tcar` (testimonial karusel) · `.biz-band` · `.outcome` · `.interstitial`+`.intent` · `.stat-band`+`.ring` · `.cd-stats` (stat-strip) · `.details-row/.detail` · `.cta-band`/`.cta-soft`

**Pill / chip:** `.logo-pill` · `.cat-pill` · `.chip` (skills) · `.fbtn/.fchip` (filter) · `.filters`

**Form (auth):** `.auth-card` · `.field`+`.inp` · `.pw`+toggle · `.icon-btn` · `.divider` · `.social`

**Yon panel:** `.side-panel` (instructor/offered) · `.learn-grid/.learn-item`+`.side-card`

**Legal:** `.legal-head` · `.legal-toc` (sticky TOC) · `.legal-content` · `.legal-keybox`

**Footer:** `.footer`+`.footer-grid/-col/-bottom`

**Reviews:** `.reviews-grid`+`.review`

## 7. Sahifalar
| Sahifa | Fayl | Holat |
|---|---|---|
| Landing | `public/index.html` | ✅ |
| About | `public/about.html` | ✅ |
| Catalog (search) | `public/catalog.html` | ✅ |
| Course detail | `public/course.html` | ✅ |
| Privacy (legal namuna) | `public/privacy.html` | ✅ |
| Login / Sign up / Forgot | `auth/*.html` | ✅ |
| Visual UI standards | `design-system.html` | ✅ |

## 8. Tuzilma
```
Fifth Trial/
├── style.css            ← tizim (tokenlar + komponentlar)
├── DESIGN-SYSTEM.md     ← shu hujjat
├── design-system.html   ← visual source of truth
├── public/              ← ochiq sahifalar
├── auth/                ← auth oqimi
├── brand/               ← mascot / character (alohida track)
└── _legacy/             ← eski (rad etilgan) tizim, arxiv
```
Sahifalar CSS'ни `../style.css` orqali ulaydi.

## 9. Qoidalar
1. Yangi kod **token** ishlatsin (`var(--fs-…)`, `var(--space-…)`, `var(--blue)` …), hardcoded emas.
2. Bitta stylesheet: `style.css`. Yangi komponent shu yerga + shu hujjatga yoziladi.
3. Kontent **placeholder** — "brandname", picsum/randomuser. Ishlab chiqarishдан oldin almashtiriladi (ayniqsa legal matn).
4. Brend rangini almashtirish: faqat `--blue` (va kerak bo'lsa `--font`) o'zgartiriladi → butun tizim ko'chadi.

## 10. Holat va ochiq ishlar
**✅ Bajarildi (tokenizatsiya + tozalash, 2026-05-31):**
- **Shrift** — 0 ta hardcoded, hammasi `--fs-*` token.
- **Rang dublikatlari** — `#eaf1fb`→`--lilac-panel`, `#eef4ff`→`--blue-soft`.
- **Radius** — asosiy (6/8/12/16/24) `--r-*` token.
- **Spacing** — on-grid `gap/padding/margin` (4/8/12/16/20/24/32/48) `--space-*` token.
- **O'lik legacy CSS** olib tashlandi (`.about-hero/.values/.story/.stat-row2/.belief-lead/.cta-band`).

**Qolgan:**
- **Off-grid spacing** (~63 ta: 5/6/10/14/18/22/26/28/36/44px va shorthand) — komponent-xos, ataylab qoldirildi (4-grid'ga majburlash layoutни siljitardi).
- **Mayda radius** (3/4/10/20px) — komponentga xos.
- **Kesh:** sahifa CSS havolalari `?v=` versiyali — o'zgarish ko'rinmasa versiya ko'tariladi yoki Ctrl+Shift+R.
- **Brend qarori:** tizim hozir Coursera-ko'k + Source Sans; brand track azure + Plus Jakarta. AzureLMS uchun `--blue`→azure, `--font`→Plus Jakarta?

*Oxirgi yangilanish: 2026-05-31 — klon Fifth Trial tizimiga birlashtirildi.*
