# AzureLMS Design Tokens

This file turns the current prototype direction into reusable design tokens.

## Color Tokens

### Core ink

- `ink-900`: `#152133`
- `ink-850`: `#16263c`
- `ink-800`: `#172334`
- `ink-700`: `#18263c`
- `ink-600`: `#24344f`

### Surface

- `surface-page-public`: `#f3f5f8`
- `surface-page-app`: `#edf1f5`
- `surface-workspace`: `#f7f9fc`
- `surface-base`: `#ffffff`
- `surface-soft`: `#eef3f8`

### Border

- `border-strong`: `#cfd8e3`
- `border-main`: `#d7dfea`
- `border-soft`: `#d9e1ea`
- `border-subtle`: `#dde4ee`
- `border-light`: `#e0e7f0`

### Interactive

- `interactive-primary`: `#16263c`
- `interactive-link`: `#1e5ab4`
- `interactive-brand`: `#173b73`

### Hero

- `hero-burgundy`: `#3d102e`
- `hero-violet`: `#2b173f`
- `hero-navy`: `#22395f`
- `hero-gold`: `#ffdd74`

### Signals

- `signal-danger`: `#e83b45`
- `signal-utility-red`: `#cf1f1f`
- `signal-success`: `#2ea84b`
- `signal-success-deep`: `#27885e`
- `signal-warm`: `#c96f3b`
- `signal-warm-soft`: `#f0d7c5`

## Typography Tokens

### Font families

- `font-body`: `"Plus Jakarta Sans", sans-serif`
- `font-display`: `"IBM Plex Sans", sans-serif`

### Public scale

- `public-kicker`: `0.72rem` to `0.8rem`
- `public-nav`: `0.9rem`
- `public-body`: `0.84rem` to `0.92rem`
- `public-section-title`: `1.92rem`
- `public-hero-title`: `clamp(2.15rem, 3.7vw, 3.25rem)`

### App scale

- `app-topbar`: `0.74rem`
- `app-nav`: `0.8rem`
- `app-group-meta`: `0.65rem`
- `app-supporting`: `0.68rem` to `0.74rem`

### Learning scale

- `learning-kicker`: `0.68rem`
- `learning-meta`: `0.72rem`
- `learning-body`: `0.76rem`
- `learning-supporting`: `0.66rem` to `0.7rem`
- `learning-title`: `0.92rem`

### Auth scale

- `auth-label`: `0.74rem`
- `auth-body`: `0.78rem` to `0.88rem`
- `auth-title`: about `1.52rem`
- `auth-shell-title`: `clamp(2.05rem, 4.1vw, 3rem)`

## Spacing Tokens

Use compact spacing by default.

- `space-2`: `4px`
- `space-4`: `8px`
- `space-6`: `12px`
- `space-8`: `16px`
- `space-10`: `20px`
- `space-12`: `24px`
- `space-14`: `28px`
- `space-16`: `32px`

## Radius Tokens

Current direction prefers smaller radii than the old prototype system.

- `radius-xs`: `4px`
- `radius-sm`: `6px`
- `radius-md`: `10px`
- `radius-pill`: `999px`

## Shadow Tokens

- `shadow-soft`: `0 10px 22px rgba(13, 24, 42, 0.05)`
- `shadow-panel`: `0 10px 26px rgba(13, 24, 42, 0.08)`
- `shadow-hero`: `0 18px 40px rgba(9, 17, 30, 0.24)`

## Layout Tokens

### Public

- `public-wrap-max`: `1440px`
- `hero-overlap-desktop`: about `-38px`
- `hero-overlap-tablet`: about `-28px`
- `hero-overlap-mobile`: about `-16px`

### App

- `app-sidebar-width`: `264px`
- `app-topbar-height`: `42px`
- `app-workspace-padding`: `10px 12px 16px`
- `app-info-tile-height`: about `70px`

### Learning

- `learning-rail-width`: `236px`
- `learning-topbar-height`: about `44px`
- `learning-workspace-padding`: `12px`
- `learning-panel-padding`: `12px`
- `learning-chip-height`: about `30px`
- `learning-tool-button-size`: `28px`
- `learning-video-height`: about `340px`

### Exam

- `exam-topbar-height`: about `58px`
- `exam-sidepanel-width`: `296px`
- `exam-workspace-padding`: `14px`
- `exam-panel-padding`: `14px`
- `exam-map-cell-height`: about `38px`
- `exam-option-padding`: `12px`

### Auth

- `auth-layout-width`: about `1240px`
- `auth-content-pane-ratio`: about `44%`
- `auth-preview-pane-ratio`: about `56%`
- `auth-panel-padding`: `22px` to `28px`
- `auth-form-gap`: `12px`
- `auth-input-height`: about `50px`
- `auth-code-cell-height`: `56px`
- `auth-content-max-width`: about `438px`
- `auth-surface-radius`: about `18px`
- `auth-stage-board-radius`: about `30px`
- `auth-stepbar-segment-width`: about `34px`
- `auth-choice-pill-height`: about `40px`
- `auth-action-height`: about `44px`

## Usage Rules

- Do not introduce new colors before checking this token list.
- Prefer the smallest spacing value that preserves readability.
- Use `radius-xs` and `radius-sm` more often than `radius-md`.
- Reserve strong shadows for hero/poster layers only.
- Keep app surfaces flatter than public hero surfaces.
