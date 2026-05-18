# AzureLMS Design System — v2

> Bu fayl playground-v2 uchun dizayn tizimining asosiy hujjatidir.
> Barcha prototiplar shu qoidalarga qat'iy rioya qiladi.

---

## 1. Falsafa

| Tamoyil | Ma'nosi |
|---|---|
| **Toza** | Ortiqcha dekoratsiya yo'q. Har bir element vazifa bajaradi. |
| **Yengil** | Sahifa og'ir emas. Minimal HTTP so'rovlar, inline CSS. |
| **Silliq** | Animatsiyalar maqsadli: `ease: cubic-bezier(0.16,1,0.3,1)`. |
| **Mukammal** | Detallar muhim — spacing, type scale, focus states. |
| **Hamma uchun** | WCAG 2.1 AA kontrast, keyboard navigatsiya, ARIA. |

---

## 2. Fayl Tuzilmasi

```
playground-v2/
├── README.md              ← navigatsiya indeksi
├── DESIGN_SYSTEM.md       ← shu fayl — qoidalar
├── TOKENS.md              ← barcha CSS o'zgaruvchilari
├── RULES.md               ← kod yozish qoidalari
├── COMPONENTS.md          ← komponent kataloği va pattern'lar
├── index.html             ← asosiy dashboard (barcha bo'limlarga yo'llanma)
│
├── auth/                  ← kirish, ro'yxatdan o'tish, parol tiklash
├── public/                ← marketing sahifalari (home, about, pricing...)
├── app/                   ← autentifikatsiya kerak bo'lgan app sahifalari
├── exam/                  ← imtihon muhiti
├── learning/              ← dars muhiti
├── blog/                  ← ommaviy blog
├── blog-studio/           ← blog boshqaruvi (admin)
├── components/            ← UI komponent kataloği
├── error/                 ← xato sahifalari (400, 401, 403, 404, 500...)
├── legal/                 ← huquqiy sahifalar (privacy, terms, faq)
├── messenger/             ← ichki xabar almashish
└── assets/
    ├── css/               ← umumiy CSS fayllar (foundation, tokens...)
    └── js/                ← umumiy JS modullari
```

---

## 3. Ranglar

Ikki qatlam: **Semantik tokenlar** (nima uchun) → **Primitiv tokenlar** (qanday qiymat).

### 3.1 Asosiy rang paleti (primitiv)

| Nom | Light | Dark |
|---|---|---|
| `--bg` | `#eff2f6` | `#0c1520` |
| `--surface` | `#f7f9fb` | `#111d2b` |
| `--white` | `#ffffff` | `#152233` |
| `--border` | `#dde4ee` | `#1e3450` |
| `--border-soft` | `#e8eef6` | `#172a40` |

### 3.2 Matn ranglari (ink scale)

| Token | Light | Dark | Ishlatish |
|---|---|---|---|
| `--ink-0` | `#0d1b2a` | `#dce9f5` | Sarlavhalar, asosiy matn |
| `--ink-1` | `#1e3248` | `#b8d0e6` | Ikkilamchi sarlavha |
| `--ink-2` | `#2f4a66` | `#8aadc8` | Muhim qo'shimcha matn |
| `--ink-3` | `#4d6680` | `#6288a4` | Yordam matni |
| `--ink-4` | `#7a90a8` | `#3f607e` | Placeholder, label |
| `--ink-5` | `#a8bcce` | `#284259` | Disabled |
| `--ink-6` | `#d1dce8` | `#1a2f44` | Divider |

### 3.3 Maxsus sirtlar (har doim qorong'u — theme-dan mustaqil)

| Token | Light | Dark | Ishlatish |
|---|---|---|---|
| `--deep` | `#0d1b2a` | `#070e18` | CTA, footer background |
| `--on-deep` | `#eff2f6` | `#dce9f5` | `--deep` ustidagi matn |

### 3.4 Aksent ranglar

| Token | Light | Dark |
|---|---|---|
| `--blue` | `#1d57d8` | `#60a5fa` |
| `--blue-mid` | `#2563eb` | `#3b82f6` |
| `--blue-soft` | `rgba(29,87,216,.09)` | `rgba(96,165,250,.12)` |
| `--green` | `#15803d` | `#4ade80` |
| `--green-mid` | `#16a34a` | `#22c55e` |
| `--green-soft` | `rgba(21,128,61,.10)` | `rgba(74,222,128,.12)` |
| `--amber` | `#b45309` | `#fbbf24` |
| `--amber-mid` | `#d97706` | `#f59e0b` |
| `--amber-soft` | `rgba(180,83,9,.10)` | `rgba(251,191,36,.12)` |
| `--purple` | `#6d28d9` | `#a78bfa` |
| `--purple-soft` | `rgba(109,40,217,.09)` | `rgba(167,139,250,.12)` |

---

## 4. Tipografiya

**Font**: `Plus Jakarta Sans` (Google Fonts) — 400, 500, 600, 700, 800.

### Type Scale

| Nom | font-size | font-weight | line-height | Ishlatish |
|---|---|---|---|---|
| `--t-hero` | `clamp(2.4rem, 6vw, 4rem)` | 800 | 1.05 | Hero sarlavha |
| `--t-h1` | `clamp(1.8rem, 4vw, 2.8rem)` | 800 | 1.1 | Sahifa sarlavhasi |
| `--t-h2` | `clamp(1.4rem, 3vw, 2rem)` | 700 | 1.15 | Bo'lim sarlavhasi |
| `--t-h3` | `clamp(1.1rem, 2vw, 1.4rem)` | 700 | 1.2 | Karta sarlavhasi |
| `--t-body` | `1rem` | 400 | 1.65 | Asosiy matn |
| `--t-sm` | `0.875rem` | 400 | 1.6 | Yordamchi matn |
| `--t-xs` | `0.75rem` | 500 | 1.5 | Label, caption |
| `--t-code` | `0.875rem` | 400 | 1.7 | Kod bloklari |

### Qoidalar
- `letter-spacing: -0.03em` — barcha sarlavhalarda
- `font-weight: 800` faqat hero/h1 uchun
- Body matnida `line-height: 1.65` dan kam bo'lmasin

---

## 5. Spacing

**Asosiy birlik**: `4px` (`--s-1 = 4px`)

| Token | Qiymat | Ishlatish |
|---|---|---|
| `--s-1` | `4px` | Icon padding |
| `--s-2` | `8px` | Inline gap |
| `--s-3` | `12px` | Kichik gap |
| `--s-4` | `16px` | Standart padding |
| `--s-5` | `20px` | Karta padding |
| `--s-6` | `24px` | Blok gap |
| `--s-8` | `32px` | Katta gap |
| `--s-10` | `40px` | Bo'lim padding |
| `--s-12` | `48px` | Bo'lim gap |
| `--s-16` | `64px` | Katta bo'lim |
| `--s-24` | `96px` | Sahifa bo'lim |

### Responsiv bo'limlar
```css
--gap: clamp(48px, 7vw, 96px);   /* bo'limlar orasidagi vertikal bo'shliq */
--wrap: min(100%, 1160px);        /* konteyner kengligi */
```

---

## 6. Border Radius

| Token | Qiymat | Ishlatish |
|---|---|---|
| `--r-sm` | `6px` | Badge, tag |
| `--r-md` | `10px` | Input, kichik karta |
| `--r-lg` | `14px` | Karta |
| `--r-xl` | `20px` | Katta karta, modal |
| `--r-pill` | `999px` | Button, chip |

---

## 7. Shadow

| Token | Qiymat | Ishlatish |
|---|---|---|
| `--sh-xs` | `0 1px 2px rgba(13,27,42,.04)` | Subtle lift |
| `--sh-sm` | `0 1px 3px rgba(13,27,42,.05), 0 4px 12px rgba(13,27,42,.07)` | Karta default |
| `--sh-md` | `0 4px 12px rgba(13,27,42,.08), 0 16px 48px rgba(13,27,42,.10)` | Karta hover |
| `--sh-lg` | `0 8px 24px rgba(13,27,42,.10), 0 32px 64px rgba(13,27,42,.12)` | Modal, dropdown |

Dark modeda `rgba(0,0,0,...)` ishlatiladi, opacity 1.5x ko'paytiriladi.

---

## 8. Animatsiya

```css
--ease: cubic-bezier(0.16, 1, 0.3, 1);   /* spring-like, asosiy ease */
--ease-in: cubic-bezier(0.4, 0, 1, 1);   /* chiqishlar uchun */
--ease-out: cubic-bezier(0, 0, 0.2, 1);  /* kirish uchun */
```

| Maqsad | duration | easing |
|---|---|---|
| Hover efektlar | `120ms` | `--ease` |
| Theme switch | `280ms` | `ease` |
| Karta kirish | `500–600ms` | `--ease` |
| Page scroll efekt | `0ms` (JS) | `linear` |
| Skeleton pulse | `1.4s` infinite | `ease-in-out` |

**Qoida**: `prefers-reduced-motion: reduce` bo'lsa barcha animatsiyalar o'chirilishi kerak.

---

## 9. Komponentlar (qisqacha)

To'liq spesifikatsiya → `COMPONENTS.md`

### Tugmalar
```
.btn           — asosiy tugma (padding: 10px 20px, r-pill)
.btn--primary  — ko'k to'liq
.btn--ghost    — shaffof, border bilan
.btn--danger   — qizil
```

### Forma elementlari
- Input height: `44px` (touch-friendly)
- Focus ring: `2px solid var(--blue-mid)`, `outline-offset: 2px`
- Error holatda: `border-color: var(--red)` + error message pastda

### Kartalar
- `border-radius: var(--r-lg)` 
- `background: var(--white)`
- `box-shadow: var(--sh-sm)`
- Hover: `transform: translateY(-2px)`, `box-shadow: var(--sh-md)`
- `transition: 200ms var(--ease)`

---

## 10. Dark Mode

### Amalga oshirish
```html
<html data-theme="light">  <!-- yoki "dark" -->
```

```javascript
// Preference saqlash va yuklash
const saved = localStorage.getItem('az-theme');
const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
applyTheme(saved ? saved === 'dark' : prefersDark);
```

### Qoidalar
- `background: var(--deep)` — har doim qorong'u sirt (theme-dan mustaqil)
- `background: var(--bg)` — tema asosiy foni
- Rang o'tishida `transition: background 280ms ease, color 280ms ease`

---

## 11. Responsivlik

| Breakpoint | Qiymat | Maqsad |
|---|---|---|
| `--bp-sm` | `480px` | Kichik mobil |
| `--bp-md` | `768px` | Planshet |
| `--bp-lg` | `1024px` | Katta planshet / noutbuk |
| `--bp-xl` | `1280px` | Desktop |

**Mobile-first** yondashuv: `min-width` media query ishlatiladi.

---

## 12. Foydalanish qoidalari

1. Har bir sahifa **self-contained** bo'lishi mumkin (yoki `assets/` ga bog'liq)
2. External dependency faqat: Google Fonts + Bootstrap Icons CDN
3. `localStorage` — faqat `az-theme` kalit uchun ruxsat
4. Inline JS `<script>` tagi — faqat sahifa oxirida
5. CSS tokenlar `<style>` tagida `:root {}` va `[data-theme="dark"] {}` blokida
