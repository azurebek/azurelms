# AzureLMS Design Tokens

This file documents the reusable tokens in `assets/css/tokens.css`. Token changes are the preferred way to centralize color, spacing, radius, shadow, typography, and layout decisions.

## Color Tokens

### Ink

- `--ink-900`: `#152133`
- `--ink-850`: `#16263c`
- `--ink-800`: `#172334`
- `--ink-700`: `#18263c`
- `--ink-600`: `#24344f`
- `--ink-500`: `#6d7c92`

### Surface

- `--surface-page-public`: `#f3f5f8`
- `--surface-page-app`: `#edf1f5`
- `--surface-workspace`: `#f7f9fc`
- `--surface-base`: `#ffffff`
- `--surface-soft`: `#eef3f8`
- `--surface-dark-start`: `#13253b`
- `--surface-dark-end`: `#102033`
- `--surface-dark-gradient`: `linear-gradient(180deg, var(--surface-dark-start) 0%, var(--surface-dark-end) 100%)`
- `--surface-utility`: `var(--surface-dark-gradient)`
- `--surface-footer`: `var(--surface-dark-gradient)`

### Border

- `--border-strong`: `#cfd8e3`
- `--border-main`: `#d7dfea`
- `--border-soft`: `#d9e1ea`
- `--border-subtle`: `#dde4ee`
- `--border-light`: `#e0e7f0`

### Interactive

- `--interactive-primary`: `#16263c`
- `--interactive-link`: `#1e5ab4`
- `--interactive-brand`: `#173b73`

### Hero

- `--hero-burgundy`: `#3d102e`
- `--hero-violet`: `#2b173f`
- `--hero-navy`: `#22395f`
- `--hero-gold`: `#ffdd74`

### Signals

- `--signal-danger`: `#e83b45`
- `--signal-utility-red`: `#cf1f1f` legacy signal token, not the default public utility strip
- `--signal-success`: `#2ea84b`
- `--signal-success-deep`: `#27885e`
- `--signal-warm`: `#c96f3b`
- `--signal-warm-soft`: `#f0d7c5`

## Typography Tokens

### Font Families

- `--font-body`: `"Plus Jakarta Sans", sans-serif`
- `--font-display`: `"IBM Plex Sans", sans-serif`

### Base Scale

- `--text-xs`: `0.72rem`
- `--text-sm`: `0.8rem`
- `--text-md`: `0.9rem`
- `--text-body`: `0.92rem`
- `--text-lg`: `1.16rem`
- `--text-xl`: `1.92rem`
- `--text-hero`: `clamp(2.15rem, 3.7vw, 3.25rem)`
- `--text-auth-title`: `1.52rem`
- `--text-auth-spotlight`: `clamp(1.8rem, 2.5vw, 2.3rem)`

### Usage By Flow

- Public: `--text-hero` only for true public hero areas. Inner sections use `--text-xl` or smaller.
- App: `--text-sm` and `--text-md` dominate navigation, topbar, cards, filters, and tables.
- Auth/Billing: `--text-auth-title` for form titles; checkout avoids hero-scale type.
- Learning: compact body and title rhythm, usually `--text-sm` to `--text-lg`.
- Exam: compact and legible; no public hero scale.
- Blog Reading: article title can be larger, list cards stay compact.
- Blog Studio, Messenger, Error: operational scale, mostly `--text-sm` to `--text-lg`.

## Spacing Tokens

Use compact spacing by default:

- `--space-2`: `4px`
- `--space-4`: `8px`
- `--space-6`: `12px`
- `--space-8`: `16px`
- `--space-10`: `20px`
- `--space-12`: `24px`
- `--space-14`: `28px`
- `--space-16`: `32px`

## Radius Tokens

- `--radius-xs`: `4px`
- `--radius-sm`: `6px`
- `--radius-md`: `10px`
- `--radius-pill`: `999px`

Usage:

- App, studio, messenger, checkout, and dense cards prefer `--radius-xs` or `--radius-sm`.
- Public hero/poster surfaces may use `--radius-md`.
- Pills use `--radius-pill` only for chips, badges, and segmented controls.

## Shadow Tokens

- `--shadow-soft`: `0 10px 22px rgba(13, 24, 42, 0.05)`
- `--shadow-panel`: `0 10px 26px rgba(13, 24, 42, 0.08)`
- `--shadow-hero`: `0 18px 40px rgba(9, 17, 30, 0.24)`

Usage:

- `--shadow-soft` is safe for catalog cards and light panels.
- `--shadow-panel` is used for elevated functional panels.
- `--shadow-hero` is reserved for public hero/poster layers.

## Layout Tokens

### Shared

- `--public-wrap-max`: `1440px`
- `--content-max`: `1440px`

### Mobile Readiness

Breakpoint values stay documented in `../docs/MOBILE_FIRST_READINESS.md` because CSS custom properties cannot safely drive media queries across the current static prototype layer.

Target verification viewports:

- `360 x 800`
- `390 x 844`
- `430 x 932`
- `768 x 1024`
- `1024 x 768`
- `1440 x 900`

Mobile layout rules:

- Mobile gutters should generally resolve to `12px` to `16px`.
- Touch controls should stay close to `44px` height.
- Dense data components may use local `min-width` only inside an `overflow-x: auto` wrapper.
- Shared shell dimensions belong in tokens only after at least two flow families reuse the same value.

### Auth

- `--auth-layout-max`: `1030px`
- `--auth-aside-width`: `388px`
- `--auth-card-width`: `620px`
- `--auth-panel-padding`: `22px`
- `--auth-input-height`: `44px`
- `--auth-code-cell-height`: `56px`

### App

- `--app-sidebar-width`: `264px`
- `--app-topbar-height`: `42px`

## Token Rules

- Add new colors to `tokens.css` before using them in shell CSS.
- Prefer a token alias when two places intentionally share the same value.
- Keep shared surfaces neutral and compact.
- Avoid viewport-scaled font sizes inside app, auth, checkout, studio, messenger, and error pages.
- Use `../docs/MOBILE_FIRST_READINESS.md` for viewport targets and responsive gate rules.
- Use page CSS for layout experiments, then promote stable values to tokens only after reuse is clear.
