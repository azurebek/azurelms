# AzureLMS Migration Readiness

This file maps the current playground prototypes to future Django templates. It works with `index.html`, `DESIGN_STANDARDS.md`, `DESIGN_TOKENS.md`, `COMPONENT_CATALOG.md`, and `../docs/MOBILE_FIRST_READINESS.md`.

For flow coverage, page ownership, component source, CSS scope, and readiness status, use `../docs/PROTOTYPE_COVERAGE_MATRIX.md`.

For the final three-question readiness gate and migration kickoff checklist, use `../docs/PLAYGROUND_READINESS_GATE.md`.

## Current Status Summary

The playground has a complete prototype map for the main product flows:

- Public Discovery
- Auth & Billing
- Student App
- Learning
- Exam
- Messenger
- Blog Reading
- Blog Studio
- Legal Documents
- Error
- Component Reference

Every shell HTML prototype is linked from `index.html`, and the root catalog now presents pages by product flow.

## Migration Principles

1. Migrate by flow, not by random page.
2. Create shell templates before moving individual pages.
3. Keep new CSS scoped to shell wrappers and family CSS.
4. Use `tokens.css` values for shared colors and dimensions.
5. Keep page-specific CSS local until the pattern is reused.
6. Do not merge prototype rules into old global CSS without a scoped migration plan.
7. Use the mobile-first readiness gate before porting a flow into Django templates.

## CSS Strategy

Use a parallel scoped shell strategy first.

### Shared Prototype Sources

- `assets/css/tokens.css`
- `assets/css/foundation.css`

### Shell And Family Sources

- `assets/css/public.css`
- `assets/css/auth.css`
- `assets/css/billing.css`
- `assets/css/app.css`
- `assets/css/learning.css`
- `assets/css/exam.css`
- `assets/css/messenger-shell.css`
- `assets/css/blog.css`
- `assets/css/blog-studio.css`
- `assets/css/legal.css`
- `assets/css/error.css`

### Scoped Page Sources

- `assets/css/about.css`
- `assets/css/public-course-list.css`
- `assets/css/public-course-detail.css`
- `assets/css/public-shell-polish.css`
- `assets/css/app-course-list.css`
- `assets/css/app-attendance.css`
- `assets/css/app-leaderboard.css`
- `assets/css/app-notifications.css`
- `assets/css/app-subscriptions.css`
- `assets/css/app-account.css`
- `assets/css/component-catalog.css`
- `assets/css/messenger-catalog.css`

## Template Inheritance Targets

| Flow | Prototype Source | Likely Django Base |
| --- | --- | --- |
| Public Discovery | `public/public-shell.html`, `public/about.html`, `public/public-course-list.html`, `public/public-course-detail.html`, `public/pricing.html` | `templates/base_public.html` or revised `templates/base.html` |
| Auth & Billing | `auth/auth-login.html`, `auth/auth-register.html`, `auth/auth-recovery.html`, `auth/auth-verify.html`, `auth/checkout.html` | `templates/auth/base.html`, `templates/subscriptions/checkout.html` |
| Student App | `app/app-shell.html`, app feature pages | `templates/dashboard/base.html` |
| Learning | `learning/learning-shell.html` | `templates/courses/lesson_base.html` |
| Exam | `exam-*.html` | `templates/courses/exam_base.html` |
| Messenger | `messenger/messenger-shell.html` | `templates/messenger/base.html` |
| Blog Reading | `blog/blog-public-shell.html`, `blog/blog-article-shell.html` | `templates/blog/base_public.html` |
| Blog Studio | `blog-studio-*.html` | `templates/blog_studio/base.html` |
| Legal | `legal-*.html` | `templates/legal/base.html` or public include |
| Error | `error-*.html` | `templates/errors/base.html` |

## Flow Maps

### Public Discovery

Prototype sources:

- `design-playground/public/public-shell.html`
- `design-playground/public/about.html`
- `design-playground/public/public-course-list.html`
- `design-playground/public/public-course-detail.html`
- `design-playground/public/pricing.html`
- `design-playground/assets/css/public.css`
- `design-playground/assets/css/about.css`
- `design-playground/assets/css/public-course-list.css`
- `design-playground/assets/css/public-course-detail.css`
- `design-playground/assets/css/public-shell-polish.css`
- `design-playground/assets/css/billing.css`

Likely Django targets:

- `templates/index.html`
- `templates/about.html`
- `templates/courses/course_list.html`
- `templates/courses/course_detail.html`
- `templates/subscriptions/pricing.html`

### Auth & Billing

Prototype sources:

- `design-playground/auth/auth-login.html`
- `design-playground/auth/auth-register.html`
- `design-playground/auth/auth-recovery.html`
- `design-playground/auth/auth-verify.html`
- `design-playground/auth/checkout.html`
- `design-playground/assets/css/auth.css`
- `design-playground/assets/css/billing.css`

Likely Django targets:

- `templates/auth/base.html`
- `templates/registration/login.html`
- `templates/registration/register.html`
- `templates/registration/password_reset_form.html`
- `templates/registration/password_reset_confirm.html`
- `templates/registration/password_reset_done.html`
- `templates/registration/password_reset_complete.html`
- `templates/subscriptions/checkout.html`
- `templates/subscriptions/checkout_success.html`

Rules:

- Checkout is auth-gated.
- Payment is monthly platform access.
- Receipt upload creates a pending verification state.

### Student App

Prototype sources:

- `design-playground/app/app-shell.html`
- `design-playground/app/app-course-list.html`
- `design-playground/app/app-course-detail.html`
- `design-playground/app/app-attendance.html`
- `design-playground/app/app-leaderboard.html`
- `design-playground/app/notifications.html`
- `design-playground/app/subscriptions.html`
- `design-playground/app/app-profile.html`
- `design-playground/app/app-settings.html`
- `design-playground/assets/css/app.css`
- scoped app page CSS files

Likely Django targets:

- `templates/dashboard/base.html`
- `templates/users/dashboard.html`
- `templates/courses/app_course_list.html`
- `templates/courses/app_course_detail.html`
- `templates/users/attendance_calendar.html`
- `templates/users/leaderboard.html`
- `templates/users/notifications.html`
- `templates/users/subscriptions.html`
- `templates/users/profile.html`
- `templates/users/settings.html`

Rules:

- Sidebar and topbar are fixed.
- App content scrolls inside the workspace.
- Topbar provides page context.

### Learning

Prototype sources:

- `design-playground/learning/learning-shell.html`
- `design-playground/assets/css/learning.css`

Likely Django targets:

- `templates/courses/lesson_detail.html`
- `templates/courses/lesson_base.html`

### Exam

Prototype sources:

- `design-playground/exam/exam-shell.html`
- `design-playground/exam/exam-writing.html`
- `design-playground/exam/exam-listening.html`
- `design-playground/exam/exam-speaking.html`
- `design-playground/exam/exam-review.html`
- `design-playground/assets/css/exam.css`

Likely Django targets:

- `templates/courses/exam_detail.html`
- `templates/courses/exam_result.html`
- `templates/courses/exam_base.html`

### Messenger

Prototype sources:

- `design-playground/messenger/messenger-shell.html`
- `design-playground/components/messenger.html`
- `design-playground/assets/css/messenger-shell.css`
- `design-playground/assets/css/messenger-catalog.css`

Likely Django targets:

- `templates/messenger/base.html`
- `templates/messenger/index.html`
- `templates/messenger/chat_widget.html`

Rules:

- Group chat and Tutor threads are top-level chat entries.
- AI chat sessions are listed below them.
- Messenger widget can appear in app and learning, never in exam.

### Blog Reading

Prototype sources:

- `design-playground/blog/blog-public-shell.html`
- `design-playground/blog/blog-article-shell.html`
- `design-playground/assets/css/blog.css`

Likely Django targets:

- `templates/blog/base_public.html`
- `templates/blog/post_list.html`
- `templates/blog/post_detail.html`

### Blog Studio

Prototype sources:

- `design-playground/blog-studio/blog-studio-shell.html`
- `design-playground/blog-studio/blog-studio-new-post.html`
- `design-playground/blog-studio/blog-studio-analytics.html`
- `design-playground/blog-studio/blog-studio-tags.html`
- `design-playground/blog-studio/blog-studio-sections.html`
- `design-playground/assets/css/blog-studio.css`

Likely Django targets:

- `templates/blog_studio/base.html`
- `templates/blog_studio/dashboard.html`
- `templates/blog_studio/post_form.html`
- `templates/blog_studio/analytics.html`
- `templates/blog_studio/tags.html`
- `templates/blog_studio/sections.html`

### Legal Documents

Prototype sources:

- `design-playground/legal/legal-privacy.html`
- `design-playground/legal/legal-terms.html`
- `design-playground/legal/legal-faq.html`
- `design-playground/assets/css/legal.css`

Likely Django targets:

- `templates/legal/privacy.html`
- `templates/legal/terms.html`
- `templates/legal/faq.html`

### Error

Prototype sources:

- `design-playground/error/error-shell.html`
- `design-playground/error/error-400.html`
- `design-playground/error/error-401.html`
- `design-playground/error/error-403.html`
- `design-playground/error/error-404.html`
- `design-playground/error/error-419.html`
- `design-playground/error/error-429.html`
- `design-playground/error/error-500.html`
- `design-playground/error/error-503.html`
- `design-playground/assets/css/error.css`

Likely Django targets:

- `templates/errors/base.html`
- `templates/errors/400.html`
- `templates/errors/401.html`
- `templates/errors/403.html`
- `templates/errors/404.html`
- `templates/errors/419.html`
- `templates/errors/429.html`
- `templates/errors/500.html`
- `templates/errors/503.html`

## Suggested Migration Order

1. Auth & Billing
2. Student App
3. Public Discovery
4. Blog Reading
5. Blog Studio
6. Learning
7. Exam
8. Messenger integration
9. Legal and Error templates

## Readiness Gates

Before moving a flow into Django:

1. Shell base template exists.
2. Flow pages are mapped to Django templates.
3. CSS files are scoped under a shell wrapper.
4. Components are listed in `COMPONENT_CATALOG.md`.
5. Dynamic data fields are identified.
6. Links are checked from the playground and from Django routes.

## Final Playground Gate

| Question | Answer |
| --- | --- |
| Architecture and linking are systematic | Ha |
| Standards are centralized | Ha |
| Flow, pages, components, standards, and migration status are organized | Ha |

## Verification Commands

Recommended checks after each migration slice:

- HTML link/anchor check for the touched prototype files.
- Django `manage.py check`.
- Visual smoke test for desktop and mobile.
- Diff review for shared CSS changes.
