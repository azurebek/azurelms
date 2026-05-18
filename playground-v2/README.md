# playground-v2 — AzureLMS Prototip Markazi

`design-playground` ning muqobili. Standartlashgan dizayn tizimi asosida yaratilgan.

## Tezkor Yo'llanma

| Sahifa | Havola |
|---|---|
| 📍 Bosh dashboard | `index.html` |
| 🎨 Dizayn qoidalari | `DESIGN_SYSTEM.md` |
| 🎨 CSS tokenlar | `TOKENS.md` |
| 📐 Kod qoidalari | `RULES.md` |
| 🧩 Komponentlar | `COMPONENTS.md` |

## Tayyor Sahifalar

| Bo'lim | Fayl | Holati |
|---|---|---|
| Auth | `auth/auth-login.html` | ✅ Tayyor |
| Auth | `auth/auth-register.html` | ✅ Tayyor |
| Auth | `auth/auth-recovery.html` | ✅ Tayyor |
| Public | `public/index.html` | ✅ Tayyor |

## Ish Rejasi

1. **Bosqich 1** ✅ — Asos (papkalar + MD hujjatlar + dashboard)
2. **Bosqich 2** — Auth to'liq (verify + checkout)
3. **Bosqich 3** — Public sahifalar (course-list, pricing, about...)
4. **Bosqich 4** — App dashboard
5. **Bosqich 5** — Exam & Learning
6. **Bosqich 6** — Blog & Studio
7. **Bosqich 7** — Components, Error, Legal, Messenger

## Qoidalar (Qisqacha)

- Barcha ranglar `var(--...)` token orqali
- CTA / Footer → `var(--deep)` / `var(--on-deep)` (har doim qorong'u)
- Dark mode: `[data-theme="dark"]` HTML atributi
- Font: Plus Jakarta Sans (Google Fonts)
- Icons: Bootstrap Icons CDN
