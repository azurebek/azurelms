# AzureLMS Component Catalog

This file lists reusable component patterns for the prototype layer and future Django templates. New pages should be assembled from these patterns before creating new UI.

## Component Source Order

1. Check this catalog.
2. Check the matching shell/family CSS.
3. Use tokens from `tokens.css`.
4. Add page-specific UI only when the component is local to one page.
5. Promote repeated page UI back into this catalog.

## Public Discovery Components

### Utility Strip

- Uses `--surface-utility`.
- Compact dark institutional bar.
- Holds quick links, locale, and entry actions.
- Stays secondary to the white main header.

### Public Header

- White background.
- Brand block on the left.
- Flat navigation in the center.
- Locale/account actions on the right.
- No glossy or oversized navigation treatments.

### Hero Carousel

Parts:

- visual/poster area
- copy column
- CTA row
- summary row
- dot indicators
- prev/next controls

Rules:

- Every slide keeps the same outer height.
- Slide compositions may vary: visual left, visual right, or centered text.
- Controls stay visible above overlap content.
- Gradients are slide-specific and remain within the approved public palette.

### Portal Blocks

Parts:

- media/preview card
- tabbed information card
- compact labels or tags

Rules:

- Blocks can overlap the hero slightly.
- They support institutional content, not decorative feature grids.
- Paired cards should share the same row height.

### Public Course Card

Parts:

- course mark or cover
- level/category kicker
- title
- short description
- chips
- action/meta row

Rules:

- Product-first.
- Compact.
- No empty showcase padding.

### Public Course Detail Fact Bar

Parts:

- compact metric
- rating or level
- duration
- schedule/flexibility

Rules:

- Sits near the hero.
- Gives quick confidence before deeper content.
- Must not look like a decorative dashboard.

### Public Tabs

Parts:

- About
- Outcomes
- Courses or cohorts
- FAQ/testimonials when needed

Rules:

- Simple underline or restrained active state.
- Used for course detail and long public pages.

### Pricing Plan Card

Parts:

- plan name
- price/month
- included access
- primary action
- short feature list

Rules:

- Subscription-based only.
- Do not imply per-course payment.
- Keep card hierarchy restrained.

### Public Footer

- Uses `--surface-footer`.
- Grouped links.
- Contact and legal links.
- Informational, not decorative.

## Auth & Billing Components

### Auth Mini Chrome

- back to site
- locale switch

Rules:

- Minimal.
- Not a public navbar.
- Secondary to the form task.

### Auth Split Shell

Parts:

- content pane
- visual/context pane

Rules:

- Auth is task-focused.
- Visual pane stays calm and supportive.
- No fake dashboard-heavy preview.

### Auth Form Surface

Parts:

- title
- short supporting line
- compact fields
- primary action
- secondary helper link

Rules:

- Main focal point.
- Operational and clear.
- Register avoids one long classic signup form.

### Verification Code Row

- Six input cells.
- Timer/status text.
- Resend/change contact links.

Rules:

- Secure, calm, and distraction-free.

### Checkout Payment Surface

Parts:

- subscription summary
- card-number payment instruction
- receipt upload
- submit action
- pending confirmation state

Rules:

- Auth-gated.
- Auth-like shell, not public landing shell.
- Fits without redundant hero copy.
- Payment is monthly platform access, not per-course checkout.

## Student App Components

### App Sidebar

Parts:

- brand
- grouped navigation
- nav item
- account area

Rules:

- Dark operational column.
- Strict icon and label alignment.
- Grouped sections support scanning.

### App Topbar

- current page/context on the left
- utility actions on the right

Rules:

- Thin.
- Fixed.
- Names the page, so the content area does not repeat a large title.

### App Workspace

- Light background.
- Scrolls independently below the fixed topbar.
- Uses compact spacing.

### App Filter Bar

Parts:

- search
- compact dropdown filters
- sort or mode controls

Rules:

- Filters stay collapsed or compact when cards are the focus.
- Filter changes should not push content far down the page.

### App Course Card

Parts:

- compact cover block
- status/kicker
- title
- description
- chips
- progress or seats row
- primary/secondary actions

Rules:

- Course card is the main focus of app course list.
- Signal cards above the list are avoided unless they are necessary.

### App Data Panel

- Compact header.
- Functional body.
- Direct controls or table/list.

Rules:

- Operational.
- Low decoration.
- Useful on attendance, leaderboard, subscriptions, profile, settings, notifications.

### Subscription Status Card

Parts:

- active plan
- start date
- end date
- remaining days
- payment history

Rules:

- Belongs to app shell.
- Dates must be easy to scan.

## Learning Components

### Learning Rail

- lesson context
- outline
- compact progress

Rules:

- Narrow and dense.
- Not general site navigation.

### Learning Stage

Parts:

- lesson title
- supporting descriptor
- media/material area
- notes or task panels

Rules:

- Main focus of learning shell.
- Feels like a real lesson workspace, not a public hero.

### Learning Support Panel

- AI coach
- task queue
- session info

Rules:

- Supports the lesson.
- Does not compete with the stage.

## Exam Components

### Secure Topbar

- exam identity
- timer
- question count
- autosave state

Rules:

- No global navigation.
- Communicates control and trust.

### Passage Panel

- Reading text or source material.
- Scrollable when needed.
- Visually tied to the current question.

### Question Panel

- question title
- supporting instruction
- answer options or editor

Rules:

- Compact and readable.
- No oversized decorative question blocks.

### Question Map

- numbered question grid
- current/done/review/untouched states

Rules:

- Small and legible.
- Supports navigation within the exam only.

### Exam Mode Surfaces

- Writing editor.
- Listening player.
- Speaking record stage.
- Review summary.

Rules:

- Same secure shell.
- Center task surface changes by mode.

## Messenger Components

### Messenger Rail

Parts:

- new chat action
- search
- Group chat
- Tutor threads
- AI chat session list

Rules:

- Group chat and Tutor threads stay above AI sessions.
- AI sessions list without large empty gaps.

### Conversation Topbar

- active chat name
- status/meta
- optional actions

Rules:

- Chat name is shown here.
- The message stage does not repeat the chat name as a large header.

### Message Bubble

Parts:

- sender/content
- timestamp/state
- hover actions

Rules:

- Copy, like, and feedback actions appear on hover.
- Message list scrolls.

### Composer

- input
- attach/voice/action icons
- send action

Rules:

- Compact.
- Close to the old simple structure, with refined styling.

## Blog Reading Components

### Blog List Shell

- search
- topics
- featured article
- article stream

Rules:

- Editorial and clean.
- Typography is readable without oversized headings.

### Article Shell

Parts:

- title/meta
- article body
- action rail
- table of contents
- related posts

Rules:

- Reading is the main focus.
- Support elements stay secondary.

## Blog Studio Components

### Studio Sidebar

- studio dashboard
- new post
- analytics
- tags
- sections
- public preview links

Rules:

- Studio-specific navigation only.
- Not the student dashboard sidebar.

### Studio Topbar

- current studio page
- utility actions

Rules:

- Thin and app-like.

### Post Queue

- status
- title
- author/date
- action

Rules:

- Dense editorial workflow.

### Editor Surface

- title
- body/content area
- metadata
- publish/review actions

Rules:

- Functional, not decorative.

### Taxonomy Manager

- search/filter
- list/grid of tags or sections
- editor panel

Rules:

- Top controls stay compact.
- Editor is visible without bloated top sections.

## Legal Components

### Legal Document Header

- document title
- short summary
- updated date or status

Rules:

- Calm and readable.
- No marketing hero treatment.

### Legal Content Section

- heading
- paragraphs
- structured lists

Rules:

- Long-form friendly.
- Easy to scan.

## Error Components

### Error Shell

- centered task surface
- brand context
- status code
- reason
- next actions

Rules:

- Calm and direct.
- No public hero, app sidebar, or marketing section.

### Error Action Row

- primary recovery action
- secondary support/back action

Rules:

- One obvious next step.
- Support path always visible.

## Migration Rule

Before building a Django template:

1. Pick the flow from `index.html`.
2. Pick the shell/family CSS.
3. List components from this catalog.
4. Use tokens from `tokens.css`.
5. Create new component classes only when no listed pattern fits.
6. Update this catalog when a repeated pattern becomes stable.
