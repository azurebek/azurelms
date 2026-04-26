# Prototype Coverage Matrix

Bu hujjat `design-playground/` ichidagi prototype oilalarini bitta flow matrixga yig'adi. Maqsad: qaysi flow qaysi sahifalardan, qaysi component reference'lardan, qaysi CSS qatlamlardan va qaysi migration targetlardan tuzilganini bir joyda ko'rsatish.

## Coverage Legend

- `ready`: current prototype freeze ichida ishlatishga tayyor reference.
- `shell-ready`: shell/base reference tayyor, child page shu shell ichida yig'iladi.
- `component-ready`: component reference tayyor va sahifaga ko'chirish mumkin.
- `future-scope`: current prototype freeze tashqarisidagi keyingi release yoki operator/document surface.

## Source Of Truth Chain

| Layer | Source | Vazifasi |
| --- | --- | --- |
| Playground map | `design-playground/index.html` | Barcha prototype oilalarini flow bo'yicha ochadi |
| Standards | `design-playground/DESIGN_STANDARDS.md` | Shell, CSS ownership va page creation qoidalari |
| Tokens | `design-playground/DESIGN_TOKENS.md` | Rang, typography, spacing, radius, shadow va layout tokenlari |
| Components | `design-playground/COMPONENT_CATALOG.md` | Reusable component patternlar |
| Mobile readiness | `docs/MOBILE_FIRST_READINESS.md` | Mobile-first viewport, overflow va flow gate qoidalari |
| Migration | `design-playground/MIGRATION_READINESS.md` | Prototype -> Django template mapping |
| Coverage | `docs/PROTOTYPE_COVERAGE_MATRIX.md` | Flow, page, CSS, component va status matrix |
| Final gate | `docs/PLAYGROUND_READINESS_GATE.md` | Uchta asosiy savolga yakuniy readiness javobi |

## Flow Coverage Summary

| Flow | Entry Page | Child Pages | Status |
| --- | --- | --- | --- |
| Public Discovery | `design-playground/public/public-shell.html` | `public/about.html`, `public/public-course-list.html`, `public/public-course-detail.html`, `public/pricing.html` | `ready` |
| Auth & Billing | `design-playground/auth/auth-login.html` | `auth/auth-register.html`, `auth/auth-recovery.html`, `auth/auth-verify.html`, `auth/checkout.html` | `ready` |
| Student App | `design-playground/app/app-shell.html` | `app/app-course-list.html`, `app/app-course-detail.html`, `app/app-attendance.html`, `app/app-leaderboard.html`, `app/notifications.html`, `app/subscriptions.html`, `app/app-profile.html`, `app/app-settings.html` | `ready` |
| Learning | `design-playground/learning/learning-shell.html` | `components/learning.html` | `ready` |
| Exam | `design-playground/exam/exam-shell.html` | `exam/exam-writing.html`, `exam/exam-listening.html`, `exam/exam-speaking.html`, `exam/exam-review.html` | `ready` |
| Messenger | `design-playground/messenger/messenger-shell.html` | `components/messenger.html` | `ready` |
| Blog Reading | `design-playground/blog/blog-public-shell.html` | `blog/blog-article-shell.html` | `ready` |
| Blog Studio | `design-playground/blog-studio/blog-studio-shell.html` | `blog-studio/blog-studio-new-post.html`, `blog-studio/blog-studio-analytics.html`, `blog-studio/blog-studio-tags.html`, `blog-studio/blog-studio-sections.html` | `ready` |
| Legal Documents | `design-playground/legal/legal-privacy.html` | `legal/legal-terms.html`, `legal/legal-faq.html` | `ready` |
| Error | `design-playground/error/error-shell.html` | `error/error-400.html`, `error/error-401.html`, `error/error-403.html`, `error/error-404.html`, `error/error-419.html`, `error/error-429.html`, `error/error-500.html`, `error/error-503.html` | `ready` |
| Component Reference | `design-playground/components/index.html` | `buttons.html`, `navigation.html`, `cards.html`, `forms.html`, `learning.html`, `exam.html`, `messenger.html` | `ready` |

## Flow Detail Matrix

### Public Discovery

| Item | Value |
| --- | --- |
| Purpose | Authsiz discovery, trust, course browse, course detail, subscription decision |
| Entry | `design-playground/public/public-shell.html` |
| Pages | `public/about.html`, `public/public-course-list.html`, `public/public-course-detail.html`, `public/pricing.html` |
| CSS | `tokens.css`, `foundation.css`, `public.css`, `about.css`, `public-course-list.css`, `public-course-detail.css`, `public-shell-polish.css`, `billing.css` |
| Components | Utility Strip, Public Header, Hero Carousel, Portal Blocks, Public Course Card, Public Course Detail Fact Bar, Public Tabs, Pricing Plan Card, Public Footer |
| Standards | `DESIGN_STANDARDS.md` -> Public Discovery, Central Color Rules, CSS Ownership |
| Migration Targets | `templates/index.html`, `templates/about.html`, `templates/courses/course_list.html`, `templates/courses/course_detail.html`, `templates/subscriptions/pricing.html` |
| Status | `ready` |

### Auth & Billing

| Item | Value |
| --- | --- |
| Purpose | Login, register, recovery, verification, secure checkout |
| Entry | `design-playground/auth/auth-login.html` |
| Pages | `auth/auth-register.html`, `auth/auth-recovery.html`, `auth/auth-verify.html`, `auth/checkout.html` |
| CSS | `tokens.css`, `foundation.css`, `auth.css`, `billing.css` |
| Components | Auth Mini Chrome, Auth Split Shell, Auth Form Surface, Verification Code Row, Checkout Payment Surface |
| Standards | `DESIGN_STANDARDS.md` -> Auth & Billing, Auth And Checkout |
| Migration Targets | `templates/auth/base.html`, `templates/registration/login.html`, `templates/registration/register.html`, password reset templates, `templates/subscriptions/checkout.html`, `templates/subscriptions/checkout_success.html` |
| Status | `ready` |

### Student App

| Item | Value |
| --- | --- |
| Purpose | Auth qilingan student workspace: dashboard, catalog, tracking, account |
| Entry | `design-playground/app/app-shell.html` |
| Pages | `app/app-course-list.html`, `app/app-course-detail.html`, `app/app-attendance.html`, `app/app-leaderboard.html`, `app/notifications.html`, `app/subscriptions.html`, `app/app-profile.html`, `app/app-settings.html` |
| CSS | `tokens.css`, `foundation.css`, `app.css`, `app-course-list.css`, `app-attendance.css`, `app-leaderboard.css`, `app-notifications.css`, `app-subscriptions.css`, `app-account.css` |
| Components | App Sidebar, App Topbar, App Workspace, App Filter Bar, App Course Card, App Data Panel, Subscription Status Card |
| Standards | `DESIGN_STANDARDS.md` -> Student App, App Shell, CSS Ownership |
| Migration Targets | `templates/dashboard/base.html`, `templates/users/dashboard.html`, `templates/courses/app_course_list.html`, `templates/courses/app_course_detail.html`, `templates/users/attendance_calendar.html`, `templates/users/leaderboard.html`, `templates/users/notifications.html`, `templates/users/subscriptions.html`, `templates/users/profile.html`, `templates/users/settings.html` |
| Status | `ready` |

### Learning

| Item | Value |
| --- | --- |
| Purpose | Focused lesson workspace |
| Entry | `design-playground/learning/learning-shell.html` |
| Pages | `components/learning.html` as component reference |
| CSS | `tokens.css`, `foundation.css`, `learning.css`, `component-catalog.css` |
| Components | Learning Rail, Learning Stage, Learning Support Panel |
| Standards | `DESIGN_STANDARDS.md` -> Learning |
| Migration Targets | `templates/courses/lesson_base.html`, `templates/courses/lesson_detail.html` |
| Status | `ready` |

### Exam

| Item | Value |
| --- | --- |
| Purpose | Secure assessment workspace |
| Entry | `design-playground/exam/exam-shell.html` |
| Pages | `exam/exam-writing.html`, `exam/exam-listening.html`, `exam/exam-speaking.html`, `exam/exam-review.html`, `components/exam.html` |
| CSS | `tokens.css`, `foundation.css`, `exam.css`, `component-catalog.css` |
| Components | Secure Topbar, Passage Panel, Question Panel, Question Map, Exam Mode Surfaces |
| Standards | `DESIGN_STANDARDS.md` -> Exam |
| Migration Targets | `templates/courses/exam_base.html`, `templates/courses/exam_detail.html`, `templates/courses/exam_result.html` |
| Status | `ready` |

### Messenger

| Item | Value |
| --- | --- |
| Purpose | Group chat, tutor threads, AI chat sessions |
| Entry | `design-playground/messenger/messenger-shell.html` |
| Pages | `components/messenger.html` as component reference |
| CSS | `tokens.css`, `foundation.css`, `messenger-shell.css`, `messenger-catalog.css` |
| Components | Messenger Rail, Conversation Topbar, Message Bubble, Composer |
| Standards | `DESIGN_STANDARDS.md` -> Messenger |
| Migration Targets | `templates/messenger/base.html`, `templates/messenger/index.html`, `templates/messenger/chat_widget.html` |
| Status | `ready` |

### Blog Reading

| Item | Value |
| --- | --- |
| Purpose | Public editorial reading experience |
| Entry | `design-playground/blog/blog-public-shell.html` |
| Pages | `blog/blog-article-shell.html` |
| CSS | `tokens.css`, `foundation.css`, `blog.css` |
| Components | Blog List Shell, Article Shell |
| Standards | `DESIGN_STANDARDS.md` -> Blog Reading |
| Migration Targets | `templates/blog/base_public.html`, `templates/blog/post_list.html`, `templates/blog/post_detail.html` |
| Status | `ready` |

### Blog Studio

| Item | Value |
| --- | --- |
| Purpose | Editorial operations workspace |
| Entry | `design-playground/blog-studio/blog-studio-shell.html` |
| Pages | `blog-studio/blog-studio-new-post.html`, `blog-studio/blog-studio-analytics.html`, `blog-studio/blog-studio-tags.html`, `blog-studio/blog-studio-sections.html` |
| CSS | `tokens.css`, `foundation.css`, `blog-studio.css` |
| Components | Studio Sidebar, Studio Topbar, Post Queue, Editor Surface, Taxonomy Manager |
| Standards | `DESIGN_STANDARDS.md` -> Blog Studio |
| Migration Targets | `templates/blog_studio/base.html`, `templates/blog_studio/dashboard.html`, `templates/blog_studio/post_form.html`, `templates/blog_studio/analytics.html`, `templates/blog_studio/tags.html`, `templates/blog_studio/sections.html` |
| Status | `ready` |

### Legal Documents

| Item | Value |
| --- | --- |
| Purpose | Policy, terms, FAQ document pages |
| Entry | `design-playground/legal/legal-privacy.html` |
| Pages | `legal/legal-terms.html`, `legal/legal-faq.html` |
| CSS | `tokens.css`, `foundation.css`, `legal.css` |
| Components | Legal Document Header, Legal Content Section |
| Standards | `DESIGN_STANDARDS.md` -> Legal |
| Migration Targets | `templates/legal/privacy.html`, `templates/legal/terms.html`, `templates/legal/faq.html` |
| Status | `ready` |

### Error

| Item | Value |
| --- | --- |
| Purpose | Error status pages with recovery actions |
| Entry | `design-playground/error/error-shell.html` |
| Pages | `error/error-400.html`, `error/error-401.html`, `error/error-403.html`, `error/error-404.html`, `error/error-419.html`, `error/error-429.html`, `error/error-500.html`, `error/error-503.html` |
| CSS | `tokens.css`, `foundation.css`, `error.css` |
| Components | Error Shell, Error Action Row |
| Standards | `DESIGN_STANDARDS.md` -> Error |
| Migration Targets | `templates/errors/base.html`, status templates |
| Status | `ready` |

## Component Reference Matrix

| Reference Page | Covers | Used By |
| --- | --- | --- |
| `design-playground/components/index.html` | Component catalog entry | All flows |
| `design-playground/components/buttons.html` | Buttons, action states | Public, Auth, App, Learning, Exam, Blog, Error |
| `design-playground/components/navigation.html` | Public nav, app sidebar, topbar patterns | Public, App, Blog Studio |
| `design-playground/components/cards.html` | Course cards, dashboard cards, content cards | Public, App, Blog |
| `design-playground/components/forms.html` | Inputs, selects, textarea, upload, validation | Auth, Checkout, App, Studio |
| `design-playground/components/learning.html` | Lesson cards, progress, learning widgets | Learning |
| `design-playground/components/exam.html` | Exam controls and assessment UI | Exam |
| `design-playground/components/messenger.html` | Chat widget and conversation components | Messenger, App, Learning |

## Migration Readiness Matrix

| Flow | Shell Base Needed | Page Templates | Component Source | CSS Scope | Status |
| --- | --- | --- | --- | --- | --- |
| Public Discovery | `templates/base_public.html` | landing, about, course list/detail, pricing | Public components | `public-*` wrapper | `ready` |
| Auth & Billing | `templates/auth/base.html` | login/register/recovery/verify/checkout | Auth & Billing components | `auth-*`, `checkout-*` wrapper | `ready` |
| Student App | `templates/dashboard/base.html` | dashboard, catalog, tracking, account | App components | `app-*` wrapper | `ready` |
| Learning | `templates/courses/lesson_base.html` | lesson detail | Learning components | `learning-*` wrapper | `ready` |
| Exam | `templates/courses/exam_base.html` | exam detail/result | Exam components | `exam-*` wrapper | `ready` |
| Messenger | `templates/messenger/base.html` | full messenger, widget | Messenger components | `messenger-*` wrapper | `ready` |
| Blog Reading | `templates/blog/base_public.html` | post list/detail | Blog Reading components | `blog-*` wrapper | `ready` |
| Blog Studio | `templates/blog_studio/base.html` | dashboard, post form, analytics, tags, sections | Studio components | `studio-*` wrapper | `ready` |
| Legal | `templates/legal/base.html` | privacy, terms, FAQ | Legal components | `legal-*` wrapper | `ready` |
| Error | `templates/errors/base.html` | status pages | Error components | `error-*` wrapper | `ready` |

## Future Scope Register

These are useful future surfaces outside the current prototype freeze:

| Surface | Suggested Flow | Reference To Start From |
| --- | --- | --- |
| Operator attendance manage | Student App / Admin extension | `app/app-attendance.html` |
| Certificate list/history | Student App / Records | `app/subscriptions.html`, `app/app-profile.html` density |
| Certificate document | Document surface | `legal/legal-privacy.html`, `error/error-shell.html` calm document rhythm |
| Certificate appendix | Document surface | `legal/legal-privacy.html` long-form rhythm |
| App help center | Student App / Support | `app/notifications.html`, `messenger/messenger-shell.html` support patterns |
| App upgrade/renew pricing | Student App / Billing | `public/pricing.html`, `app/subscriptions.html` |

## Completion Checklist

| Check | Status |
| --- | --- |
| All shell playground HTML files are listed from `design-playground/index.html` | `ready` |
| All current prototype flows have entry pages | `ready` |
| Every flow has child pages or component references | `ready` |
| Every flow maps to CSS ownership | `ready` |
| Every flow maps to component catalog sections | `ready` |
| Every flow maps to migration targets | `ready` |
| Standards, tokens, components, migration docs are linked from playground | `ready` |
| Final readiness gate is linked from playground | `ready` |
