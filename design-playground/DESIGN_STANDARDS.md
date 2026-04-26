# AzureLMS Design Standards

This file is the central design standard for the prototypes in `design-playground/`.

## Source Of Truth

Use this order when deciding how a page should be built:

1. `index.html` defines the prototype family and page flow.
2. `assets/css/tokens.css` defines reusable color, spacing, radius, shadow, typography, and layout values.
3. `assets/css/foundation.css` defines base resets and generic primitives.
4. Shell or family CSS defines reusable layout for a product zone.
5. Page CSS is used only for page-specific composition that has not become a shared component.
6. `../docs/PROTOTYPE_COVERAGE_MATRIX.md` confirms flow coverage, page ownership, component sources, CSS scope, and migration status.
7. `../docs/MOBILE_FIRST_READINESS.md` defines the mobile-first conversion gate, viewport targets, and controlled overflow rules.
8. `../docs/PLAYGROUND_READINESS_GATE.md` confirms the final architecture, standards, and flow readiness gate.

No page should invent its own visual language. Every page must belong to one of the flows below.

## Prototype Families

| Flow | Pages | Primary CSS |
| --- | --- | --- |
| Public Discovery | `public/public-shell.html`, `public/about.html`, `public/public-course-list.html`, `public/public-course-detail.html`, `public/pricing.html` | `public.css`, `about.css`, `public-course-list.css`, `public-course-detail.css`, `billing.css`, `public-shell-polish.css` |
| Auth & Billing | `auth/auth-login.html`, `auth/auth-register.html`, `auth/auth-recovery.html`, `auth/auth-verify.html`, `auth/checkout.html` | `auth.css`, `billing.css` |
| Student App | `app/app-shell.html`, `app/app-course-list.html`, `app/app-course-detail.html`, `app/app-attendance.html`, `app/app-leaderboard.html`, `app/notifications.html`, `app/subscriptions.html`, `app/app-profile.html`, `app/app-settings.html` | `app.css` plus scoped app page CSS |
| Learning | `learning/learning-shell.html` | `learning.css` |
| Exam | `exam/exam-shell.html`, `exam/exam-writing.html`, `exam/exam-listening.html`, `exam/exam-speaking.html`, `exam/exam-review.html` | `exam.css` |
| Messenger | `messenger/messenger-shell.html`, `components/messenger.html` | `messenger-shell.css`, `messenger-catalog.css` |
| Blog Reading | `blog/blog-public-shell.html`, `blog/blog-article-shell.html` | `blog.css` |
| Blog Studio | `blog-studio/blog-studio-shell.html`, `blog-studio/blog-studio-new-post.html`, `blog-studio/blog-studio-analytics.html`, `blog-studio/blog-studio-tags.html`, `blog-studio/blog-studio-sections.html` | `blog-studio.css` |
| Legal Documents | `legal/legal-privacy.html`, `legal/legal-terms.html`, `legal/legal-faq.html` | `legal.css` |
| Error | `error/error-shell.html`, `error/error-400.html`, `error/error-401.html`, `error/error-403.html`, `error/error-404.html`, `error/error-419.html`, `error/error-429.html`, `error/error-500.html`, `error/error-503.html` | `error.css` |
| Component Reference | `components/*.html` | `component-catalog.css` plus domain component CSS |

## Core Direction

- The product feels institutional, compact, and operational.
- Trust, structure, and clarity are more important than decorative polish.
- Visual weight comes from hierarchy, alignment, contrast, and controlled spacing.
- Cards use small radius and purposeful content. Decorative floating card stacks are avoided.
- Typography stays compact inside tools, sidebars, dashboards, checkout, auth, and studio screens.
- Public pages can use more open rhythm, with restrained hero scale and professional contrast.

## Central Color Rules

### Shared Neutrals

- Main ink: `#18263c`
- Deep ink / dark shell: `#172334`
- Topbar dark: `#152133`
- Public page background: `#f3f5f8`
- App page background: `#edf1f5`
- Workspace background: `#f7f9fc`
- Surface base: `#ffffff`
- Main border: `#d7dfea`

### Public Utility And Footer

- Utility strip and public footer share the same dark institutional gradient.
- The gradient is centralized in `tokens.css` as `--surface-dark-gradient`, `--surface-utility`, and `--surface-footer`.
- Current values:
  - start: `#13253b`
  - end: `#102033`
- Red remains a danger/status color and is not the default utility strip color.

### Public Shell

- Main header stays white.
- Utility strip is dark and compact.
- Public CTAs are solid, flat, and close to `#16263c`.
- Public hero gradients must stay within burgundy, violet, navy, teal, and restrained blue ranges.
- Public course/detail pages must avoid oversized typography and harsh color contrast.

### App Shell

- Sidebar stays in the `#172334` / `#152133` family.
- Topbar is thin and dark.
- Workspace is light, compact, and operational.
- Bright colors are reserved for status, badges, or true signal.
- App pages do not add large repeated page headers under the topbar.

### Auth And Checkout

- Auth pages use a focused split shell or auth-like compact secure surface.
- Checkout is auth-gated and belongs to Auth & Billing, not to the public marketing shell.
- Checkout copy must be short and task-focused: payment target, receipt upload, pending confirmation.

### Learning And Exam

- Learning is focused and compact, with one dominant lesson stage.
- Exam is full-screen, controlled, and free of public/app navigation.
- Exam views allow only exam-related controls.

### Blog

- Blog Reading is editorial and calm, close to public shell language.
- Blog Studio is operational and app-like, with studio-specific navigation.
- Blog typography must stay readable without large marketing-scale headings.

### Error

- Error pages are task-focused and calm.
- Each error page shows the code, reason, primary next action, and support path.
- Error pages do not inherit public landing hero patterns.

## CSS Ownership Rules

Shared CSS files are reserved for stable, reused rules:

- `tokens.css`: shared values only.
- `foundation.css`: reset, base typography, generic layout primitives.
- `public.css`: public shell and public-family shared components.
- `app.css`: app shell and app-family shared components.
- `auth.css`, `learning.css`, `exam.css`, `blog.css`, `blog-studio.css`, `error.css`, `legal.css`: family-level standards.

Page-specific CSS is valid when the pattern is local or still being prototyped:

- `about.css`
- `public-course-list.css`
- `public-course-detail.css`
- `app-course-list.css`
- `app-attendance.css`
- `app-leaderboard.css`
- `app-notifications.css`
- `app-subscriptions.css`
- `app-account.css`
- `billing.css`
- `messenger-shell.css`
- `public-shell-polish.css`

### Promotion Rule

Move a rule from page CSS into shared CSS only when:

1. The pattern is used by at least two pages.
2. The class name describes a reusable component.
3. The affected pages are known.
4. The shared CSS diff is small and visually equivalent.

### Shared CSS Safety

Before changing `public.css`, `app.css`, or another family CSS file:

1. Identify every page that loads the file.
2. Confirm the selector is shell or component scoped.
3. Prefer token changes when the goal is centralization.
4. Verify links and visual risk after the edit.

## Shell Standards

## Mobile-First Standard

Use `../docs/MOBILE_FIRST_READINESS.md` before changing responsive behavior. Mobile work must move by flow, keep shell CSS scoped, and preserve the desktop reference while making `360`, `390`, `430`, `768`, and `1440` viewport checks pass.

Rules:

- Start with shell/family CSS before page-specific fixes.
- Keep body-level horizontal overflow at zero unless the shell intentionally owns a full-screen workspace.
- Put dense table, calendar, ranking, question map, or payment history overflow inside the component wrapper.
- Keep app, studio, messenger, checkout, exam, and error typography compact on mobile.
- Do not introduce a new breakpoint unless the mobile readiness document records the reason.

### Public Discovery

- Flow: landing -> about/pricing/course list -> course detail -> auth/register or checkout.
- The first viewport should identify AzureLMS and the page purpose quickly.
- Headers, course cards, pricing, and CTA surfaces use the same public rhythm.
- Public course detail can borrow structural ideas from Coursera-style product pages: hero, fact bar, tabs, outcomes, skills, course/cohort information, FAQ.

### Auth & Billing

- Flow: login/register/recovery/verify -> checkout.
- Public navbar and footer are not shown in auth screens.
- Forms are compact, flat, and clear.
- Checkout should fit without unnecessary scrolling on normal desktop height.

### Student App

- Flow: dashboard -> catalog/detail -> attendance/leaderboard/notifications/subscriptions/profile/settings.
- Sidebar and topbar stay fixed.
- Content scrolls inside the workspace.
- Topbar already names the page; app pages do not repeat large page titles below it.
- Filters stay compact and collapsible where they compete with core cards.

### Learning

- Flow: app course/lesson entry -> learning shell.
- Left rail is for lesson context and progression.
- Center stage is the main lesson area.
- Side panels support the lesson only.

### Exam

- Flow: exam entry -> reading/writing/listening/speaking -> review.
- No global navigation.
- Timer, autosave, question count, section state, and submit controls stay visible and calm.

### Messenger

- Flow: group chat / tutor threads / AI sessions.
- Group chat and Tutor threads sit above AI sessions.
- The active chat name appears in the topbar, not repeated inside the conversation stage.
- Messages scroll; message actions appear on hover.

### Blog Reading

- Flow: blog list -> article detail.
- Reading surface is clean and editorial.
- The shell remains related to public design without becoming a separate brand.

### Blog Studio

- Flow: studio dashboard -> new post -> analytics -> tags -> sections.
- Sidebar contains studio tasks, not dashboard navigation.
- Topbar names the current studio page.
- Content surfaces stay compact and work-focused.

### Legal

- Flow: privacy / terms / FAQ from public footer, auth, or app help/settings.
- Legal pages use readable long-form layout and calm document rhythm.

### Error

- Flow: error shell -> specific status page.
- Error pages give one clear next step and a support path.
- They stay visually related to AzureLMS without borrowing marketing hero patterns.

## Page Creation Checklist

Before adding or redesigning any page:

1. Choose the flow from `index.html`.
2. Use the matching shell or family CSS.
3. Reuse tokens from `tokens.css`.
4. Reuse known components from `COMPONENT_CATALOG.md`.
5. Add page CSS only for local layout.
6. Link the page from the correct flow section in `index.html`.
7. Check the mobile-first gate in `../docs/MOBILE_FIRST_READINESS.md`.
8. Run link and diff checks.
