# Playground Readiness Gate

Bu hujjat `design-playground/` prototype qatlamining yakuniy handoff gate'i. U uchta asosiy savolga bitta joyda javob beradi va migration boshlashdan oldin tekshiriladigan checklist sifatida ishlatiladi.

## Final Decision

| Savol | Javob | Dalil |
| --- | --- | --- |
| Arxitektura va bog'lanish tizimlimi? | Ha | `design-playground/index.html` barcha prototype flowlarni oilalar bo'yicha ochadi, shell HTML sahifalar shu katalogdan topiladi |
| Butun loyiha standartlari markazlimi? | Ha | `DESIGN_STANDARDS.md`, `DESIGN_TOKENS.md`, `COMPONENT_CATALOG.md`, `MIGRATION_READINESS.md` va coverage matrix bitta source-of-truth zanjirida turadi |
| Loyiha oqimi, sahifalar, componentlar va standartlar tartibli ko'rsatilganmi? | Ha | `docs/PROTOTYPE_COVERAGE_MATRIX.md` har bir flow uchun entry, pages, CSS, components, standards va migration targetlarni ko'rsatadi |

## Verification Snapshot

| Check | Result |
| --- | --- |
| Shell playground HTML sahifalar `index.html`dan linklangan | Pass |
| Recursive HTML link va anchor check | Pass |
| Flow coverage matrix har bir prototype oilani qamrab oladi | Pass |
| Standards, tokens, components, migration va coverage docs indexdan ochiladi | Pass |
| Shared public utility/footer rang qarori tokenga chiqarilgan | Pass |
| `git diff --check` | Pass |

## Source-Of-Truth Chain

| Layer | Source |
| --- | --- |
| Flow map | `design-playground/index.html` |
| Design rules | `design-playground/DESIGN_STANDARDS.md` |
| Token rules | `design-playground/DESIGN_TOKENS.md` |
| Component rules | `design-playground/COMPONENT_CATALOG.md` |
| Mobile-first gate | `docs/MOBILE_FIRST_READINESS.md` |
| Coverage matrix | `docs/PROTOTYPE_COVERAGE_MATRIX.md` |
| Migration map | `design-playground/MIGRATION_READINESS.md` |
| Final gate | `docs/PLAYGROUND_READINESS_GATE.md` |

## Flow Gate

| Flow | Entry | Page Coverage | CSS Ownership | Component Source | Migration Map | Gate |
| --- | --- | --- | --- | --- | --- | --- |
| Public Discovery | `public/public-shell.html` | `about`, public course list/detail, pricing | Public + scoped page CSS | Public components | Public templates | Ha |
| Auth & Billing | `auth/auth-login.html` | register, recovery, verify, checkout | Auth + billing CSS | Auth & Billing components | Auth and subscription templates | Ha |
| Student App | `app/app-shell.html` | catalog, detail, attendance, leaderboard, notifications, subscriptions, profile, settings | App + scoped page CSS | App components | Dashboard/user templates | Ha |
| Learning | `learning/learning-shell.html` | learning shell and learning component reference | Learning CSS | Learning components | Lesson templates | Ha |
| Exam | `exam/exam-shell.html` | reading, writing, listening, speaking, review | Exam CSS | Exam components | Exam templates | Ha |
| Messenger | `messenger/messenger-shell.html` | full messenger and component reference | Messenger CSS | Messenger components | Messenger templates | Ha |
| Blog Reading | `blog/blog-public-shell.html` | blog list and article | Blog CSS | Blog Reading components | Blog public templates | Ha |
| Blog Studio | `blog-studio/blog-studio-shell.html` | dashboard, new post, analytics, tags, sections | Blog Studio CSS | Studio components | Blog studio templates | Ha |
| Legal Documents | `legal/legal-privacy.html` | privacy, terms, FAQ | Legal CSS | Legal components | Legal templates | Ha |
| Error | `error/error-shell.html` | 400, 401, 403, 404, 419, 429, 500, 503 | Error CSS | Error components | Error templates | Ha |
| Component Reference | `components/index.html` | buttons, navigation, cards, forms, learning, exam, messenger | Component catalog CSS | Component reference pages | Shared includes | Ha |

## Migration Kickoff Checklist

Use this checklist before moving a flow into Django:

1. Pick the flow from `design-playground/index.html`.
2. Read the matching flow row in `docs/PROTOTYPE_COVERAGE_MATRIX.md`.
3. Read the shell rule in `design-playground/DESIGN_STANDARDS.md`.
4. List components from `design-playground/COMPONENT_CATALOG.md`.
5. Use tokens from `design-playground/DESIGN_TOKENS.md`.
6. Read the mobile gate in `docs/MOBILE_FIRST_READINESS.md`.
7. Create the Django base shell for the flow.
8. Port page markup into that shell.
9. Keep CSS scoped to the shell or page wrapper.
10. Run HTML link/anchor check and Django `manage.py check`.

## Final Status

Playground prototype layer is ready as the design and migration reference.
