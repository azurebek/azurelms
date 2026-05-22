# Old Turtle Manifest

`old-turtle` is a protected cleanup copy of `design-work-playground`.
The original playground is not edited here.

## Status Model

| Status | Meaning |
| --- | --- |
| draft | Free exploration. Can be messy. |
| normalizing | Shell, links, metadata, and shared CSS are being aligned. |
| candidate | Structure is stable enough for visual review. |
| ready | Passes link, metadata, theme, duplicate-id, a11y, and screenshot checks. |
| ported | Moved into Django templates or another real implementation. |

## Current Target

Current folder status: `normalizing`.

The first pass focuses on:

1. Root catalog and manifest.
2. Broken local links.
3. Consistent CSS chain: `tokens -> foundation -> components -> shell -> page`.
4. Metadata on every page.
5. Theme initialization before body rendering.
6. Duplicate IDs and obvious HTML typos.

## Stage 4 Interaction Cleanup

Current pass status: `done`.

Completed:

1. Shared delegated interaction helper added at `assets/js/prototype-ui.js`.
2. All 38 HTML pages include the helper.
3. Inline event handlers were moved to `data-ui-*` attributes.
4. Repeated hover/focus behavior was moved into shared classes in `assets/css/components.css`.

Latest checks:

1. Inline event handlers: `0`.
2. Missing local links: `0`.
3. Duplicate source IDs: `0`.

Remaining cleanup:

1. Inline style attributes still need a shell-by-shell extraction pass.
2. Top style hotspots are Blog Studio analytics, public course detail, app course detail, public home, messenger shell, and public about.

## Stage 5 Style Extraction And Smoke

Current pass status: `done`.

Completed:

1. Inline style attributes extracted into `assets/css/prototype-extracted.css`.
2. All 38 HTML pages include `prototype-extracted.css` after page CSS.
3. UTF-8 mojibake introduced during extraction was repaired in the `old-turtle` copy.
4. Desktop and mobile smoke screenshots were captured in `output/playwright/2026-05-18-stage5/`.

Latest checks:

1. Inline style attributes: `0`.
2. Inline event handlers: `0`.
3. `prototype-extracted.css` includes: `38 / 38`.
4. Missing local links: `0`.
5. `prototype-ui.js` syntax check: passed.

Visual notes:

1. `messenger/messenger-shell.html` still behaves like a desktop shell on mobile.
2. `public/index.html` still has large scroll/pinned-section whitespace that needs a dedicated layout pass.
3. `prototype-extracted.css` is transitional; replace `xstyle-*` classes with semantic utility/component classes over time.

## Flow Ownership

| Flow | Shell / entry | Pages |
| --- | --- | --- |
| Public Discovery | `public/index.html` | `about.html`, `course-list.html`, `course-detail.html`, `pricing.html` |
| Auth and Billing | `auth/auth-login.html` | `auth-register.html`, `auth-recovery.html`, `auth-verify.html`, `checkout.html` |
| Student App | `app/app-shell.html` | `app-course-list.html`, `app-course-detail.html`, `app-notifications.html`, `app-profile.html`, `app-settings.html`, `app-subscriptions.html` |
| Exam | `exam/exam-shell.html` | `exam-listening.html`, `exam-speaking.html`, `exam-writing.html`, `exam-review.html` |
| Blog Reading | `blog/blog-shell.html` | `blog-article.html`, `blog-tags.html` |
| Blog Studio | `blog-studio/blog-studio-shell.html` | `blog-studio-new-post.html`, `blog-studio-analytics.html` |
| Legal | `legal/legal-privacy.html` | `legal-terms.html`, `legal-cookies.html` |
| Error | `error/error-404.html` | `error-403.html`, `error-500.html`, `error-maintenance.html`, `error-offline.html` |
| Messenger | `messenger/messenger-shell.html` | standalone shell |

## Cleanup Gates

Before a page becomes `ready`, it must pass:

1. No missing local `href` or `src` links.
2. One meta description.
3. Theme boot script in the head.
4. No duplicate IDs.
5. No inline event handlers for core interactions.
6. No hard-coded colors outside token files or deliberate visual samples.
7. Visual smoke screenshots for desktop and mobile.
