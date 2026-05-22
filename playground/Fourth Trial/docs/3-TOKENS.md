# AzureLMS - Design Tokens

Ushbu hujjat loyihada ishlatiladigan CSS o'zgaruvchilarini (Tokens) belgilaydi. Bu kodlar `assets/css/tokens.css` faylida aks etishi kerak.

## 1. Asosiy Ranglar (Light Mode)

### Base & Surfaces
* `--bg`: `#eff2f6` (Body background)
* `--surface`: `#f7f9fb` (Slightly lighter than bg, input/card backgrounds)
* `--white`: `#ffffff` (Pure white for cards/nav)
* `--border`: `#dde4ee` (Main borders)
* `--border-soft`: `#e8eef6` (Subtle dividers)

### Typography (Ink)
* `--ink-0`: `#0d1b2a` (Headings, primary text)
* `--ink-1`: `#1e3248` (Strong body text)
* `--ink-2`: `#2f4a66` (Muted body text)
* `--ink-3`: `#4d6680` (Secondary text, descriptions)
* `--ink-4`: `#7a90a8` (Placeholders, disabled text)
* `--ink-5`: `#a8bcce` (Very faint text/icons)

### Dark Surfaces (CTA, Sidebar in App)
* `--deep`: `#0d1b2a` (Dark institutional background)
* `--on-deep`: `#eff2f6` (Text on deep background)

### Brand & Accents
* **Blue (Primary):** `--blue-mid: #2563eb`, `--blue: #1d57d8`, `--blue-soft: rgba(29,87,216,.09)`
* **Accent (Orange/Brand):** `--accent: #f26a3d`, `--accent-mid: #e05528`, `--accent-soft: rgba(242,106,61,.10)`
* **Success:** `--green-mid: #16a34a`, `--green: #15803d`, `--green-soft: rgba(21,128,61,.10)`
* **Warning:** `--amber-mid: #d97706`, `--amber: #b45309`, `--amber-soft: rgba(180,83,9,.10)`
* **Danger:** `--red: #dc2626`, `--red-soft: rgba(220,38,38,.09)`
* **Info/Pro:** `--purple: #6d28d9`, `--purple-soft: rgba(109,40,217,.09)`

## 2. Dark Mode Ranglar

`[data-theme="dark"]` selektori ostida chaqiriladi:

* `--bg`: `#0c1520`
* `--surface`: `#111d2b`
* `--white`: `#152233`
* `--border`: `#1e3450`
* `--border-soft`: `#172a40`
* `--ink-0`: `#dce9f5`
* `--ink-1`: `#b8d0e6`
* `--ink-2`: `#8aadc8`
* `--ink-3`: `#6288a4`
* `--ink-4`: `#3f607e`
* `--ink-5`: `#284259`
* `--deep`: `#070e18`
* `--on-deep`: `#dce9f5`

*(Accent va Status ranglarning dark mode variantlari ham mutanosib yorqinlashtiriladi).*

## 3. O'lchamlar va Effektlar

### Shadows (Soyalar)
* `--sh-sm`: `0 1px 3px rgba(13,27,42,.05), 0 4px 12px rgba(13,27,42,.07)` (Card normal state)
* `--sh-md`: `0 4px 12px rgba(13,27,42,.08), 0 16px 48px rgba(13,27,42,.10)` (Card hover, Modals)

### Border Radius (Qiyalik)
* `--r-sm`: `6px`
* `--r-md`: `10px` (Inputs, Buttons)
* `--r-lg`: `14px` (Cards, Panels)
* `--r-xl`: `20px` (Large surfaces)
* `--r-pill`: `999px` (Badges, rounded buttons)

### Animation & Ease
* `--ease`: `cubic-bezier(0.16, 1, 0.3, 1)` (General smooth transition)
