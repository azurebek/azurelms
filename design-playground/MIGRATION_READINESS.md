# AzureLMS Migration Readiness

This file answers one question: what must be true before we start moving the redesign prototypes into real Django templates?

It also maps current prototype work to likely Django entry points so we do not start migration blindly.

## Current Status Summary

The prototype layer is now strong enough to guide implementation, but not every area is equally ready.

### Ready or nearly ready

- Public shell direction
- App shell direction
- Auth shell family
- Exam environment family
- Core visual language
- Color, spacing, and shell-level standards

### Partially ready

- Learning shell
- Messenger integration behavior
- Public content section finalization
- Component migration strategy

### Not yet migration-safe without extra decisions

- CSS coexistence strategy with legacy files
- Final responsive audit across all shells
- Real template inheritance plan for learning/exam/auth

## Migration Readiness Checklist

Use this list before touching Django templates.

### 1. Shell Freeze

Each shell must have a stable decision on:

- structure
- density
- nav behavior
- primary/secondary actions
- responsive intent

Shells:

- Public
- Auth
- App
- Learning
- Exam

### 2. Component Freeze

Every migrated page should be assembled from known pieces.

Before migration, classify each prototype component as:

- Ready to migrate
- Needs one more prototype pass
- Prototype only

Minimum ready set:

- Public header
- Public hero carousel
- Portal overlap block
- CTA strip
- Footer
- App sidebar groups
- App topbar
- Dense content card
- Auth split shell
- Auth form surface
- Auth method choice
- Auth verification row
- Learning rail
- Learning topbar
- Learning stage card
- Exam secure topbar
- Question panel
- Question map
- Messenger launcher

### 3. Responsive Confidence

Before migration, verify at least:

- auth on mobile/tablet
- public hero and overlap section
- app sidebar collapse behavior
- learning rail + main stage stacking
- exam sidepanel behavior

If a shell does not have responsive confidence, keep it in prototype until fixed.

### 4. Legacy CSS Strategy

This is a hard blocker for migration.

Current real site still loads:

- `styles.css`
- `unified-ui.css`
- `platform-rework.css`
- page-specific css files

Before migrating, choose one strategy:

#### Strategy A: parallel new shell CSS

- add new shell CSS files
- scope them tightly to new template wrappers
- avoid rewriting old global CSS immediately

Recommended first for safety.

#### Strategy B: replace global layers

- move prototype rules into the main global stack
- gradually delete old rules

Higher risk and should happen later.

Recommendation:

- Use Strategy A first
- page-by-page migration
- strong shell wrapper classes

### 5. Template Inheritance Plan

Do not migrate page-by-page without deciding inheritance first.

Needed real shells:

- public base
- auth base
- app/dashboard base
- learning base
- exam base

If these are not defined first, migration becomes repetitive and brittle.

### 6. Data / Content Fit Check

Prototype structure must still fit real dynamic content.

Check before migration:

- landing nav items
- site settings
- legal pages
- course cards
- user avatar/profile data
- notifications counts
- messenger widget context
- exam attempts / question state

## Prototype to Django File Map

This is the first-pass migration map.

## Public Shell

### Prototype sources

- `design-playground/public-shell.html`
- `design-playground/assets/css/public.css`
- `design-playground/assets/css/tokens.css`
- `design-playground/assets/css/foundation.css`

### Likely Django targets

- `templates/base.html`
- `templates/index.html`
- `templates/about.html`
- `templates/legal_page.html`
- `templates/subscriptions/pricing.html`
- `templates/courses/course_list.html`
- `templates/courses/course_detail.html`

### Related includes likely to refactor

- `templates/includes/brand_lockup.html`
- `templates/includes/course_showcase_card.html`

### Risk notes

- `base.html` currently loads several competing CSS files
- footer and navbar are content-driven in some places
- landing sections may depend on admin-managed content blocks

## Auth Shell

### Prototype sources

- `design-playground/auth-login.html`
- `design-playground/auth-register.html`
- `design-playground/auth-recovery.html`
- `design-playground/auth-verify.html`
- `design-playground/assets/css/auth.css`

### Likely Django targets

- `templates/auth/base.html`
- `templates/registration/login.html`
- `templates/registration/register.html`
- `templates/registration/password_reset_form.html`
- `templates/registration/password_reset_confirm.html`
- `templates/registration/password_reset_done.html`
- `templates/registration/password_reset_complete.html`

### Real CSS candidates

- `static/css/auth.css`
- `static/css/auth-rework.css`

### Risk notes

- There are already two auth CSS files in real static
- must decide whether to replace one or introduce a scoped new auth shell stylesheet
- register flow may later become multi-step in real product logic

## App Shell

### Prototype sources

- `design-playground/app-shell.html`
- `design-playground/assets/css/app.css`

### Likely Django targets

- `templates/dashboard/base.html`
- `templates/users/dashboard.html`
- `templates/users/leaderboard.html`
- `templates/users/attendance_calendar.html`
- `templates/users/notifications.html`
- `templates/users/profile.html`
- `templates/users/settings.html`
- `templates/users/subscriptions.html`
- `templates/users/help_center.html`
- `templates/users/certificates.html`

### Related includes likely to refactor

- `templates/includes/dashboard_enrollment_card.html`
- `templates/includes/dashboard_recommended_course_card.html`
- `templates/messenger/chat_widget.html`

### Risk notes

- dashboard base already contains a strong sidebar/topbar structure
- easiest shell migration candidate after auth
- messenger widget placement needs explicit decision

## Learning Shell

### Prototype sources

- `design-playground/learning-shell.html`
- `design-playground/assets/css/learning.css`

### Likely Django targets

- `templates/courses/lesson_detail.html`

### Risk notes

- lesson detail will carry real lesson content, notes, progression, and embedded actions
- learning modes still need one more audit before full migration

## Exam Shell

### Prototype sources

- `design-playground/exam-shell.html`
- `design-playground/exam-writing.html`
- `design-playground/exam-listening.html`
- `design-playground/exam-speaking.html`
- `design-playground/exam-review.html`
- `design-playground/assets/css/exam.css`

### Likely Django targets

- `templates/courses/exam_detail.html`
- `templates/courses/exam_result.html`

### Risk notes

- exam family is visually ready
- product-flow questions still need confirmation:
  - autosave state
  - section switching
  - review/submit behavior

## Messenger

### Prototype sources

- `design-playground/components/messenger.html`
- `design-playground/assets/css/messenger-catalog.css`
- `design-playground/assets/js/messenger-catalog.js`

### Likely Django targets

- `templates/messenger/chat_widget.html`
- any future full messenger page template
- `templates/dashboard/base.html`
- `templates/courses/lesson_detail.html`

### Risk notes

- widget behavior is concept-ready, but final placement rules need to be fixed before migration

## Suggested Migration Order

This is the safest order.

1. Auth shell
2. App shell
3. Public shell
4. Learning shell
5. Exam shell
6. Messenger integration polish

## Why This Order

### Auth first

- isolated
- low content complexity
- highly visible improvement
- easiest place to prove the new shell strategy

### App second

- strong shell value
- many pages benefit immediately
- existing `dashboard/base.html` already gives a clear integration point

### Public third

- highest content variability
- more admin-managed areas
- better to migrate after shell strategy is proven

### Learning / Exam after that

- more product-state heavy
- benefits from already-established shell/component rules

## Open Questions Before Migration

These should be explicitly answered before implementation starts.

- Which real CSS file will host the new auth shell?
- Will new shell CSS live as separate files or be merged into old global files?
- Will register stay one screen in the real app, or become real multi-step onboarding?
- Where exactly should messenger widget appear:
  - app only
  - app + learning
  - not inside exam
- Does learning need more than one real mode on day one?
- Is public landing considered final enough for migration, or does it need one last polish pass?

## Recommendation

Do not start broad migration yet.

Start with:

1. finalize this readiness document
2. decide CSS coexistence strategy
3. migrate auth shell first

That path gives the least surprise and the least cleanup pain later.
