# AzureLMS Design Standards

This file captures the current visual direction we agreed on for the redesign prototypes in `design-playground/`.

## Core Direction

- The product should feel institutional, compact, and operational.
- The goal is not "marketing SaaS polish"; the goal is trust, structure, and clarity.
- Visual weight should come from hierarchy, spacing, contrast, and layout discipline.
- Decoration is secondary to function.

## Color System

These values are based on the colors actually used in the current prototypes.

### Core neutrals

- Main ink: `#18263c`
- Deep ink / dark shell: `#172334`
- Topbar dark: `#152133`
- Supporting dark blue text: `#24344f`
- White surface: `#ffffff`
- App workspace background: `#f7f9fc`
- Public/page background: `#f3f5f8`
- Secondary app background: `#edf1f5`

### Surface and border colors

- Main border: `#d7dfea`
- Secondary border: `#dde4ee`
- Header border: `#d9e1ea`
- Light border / surface divider: `#e0e7f0`
- Soft border / line accents: `#d4dce7`, `#cfd8e3`, `#dbe3ee`
- Pale panel background: `#eef3f8`

### Primary interactive colors

- Public primary button / dark action: `#16263c`
- App brand blue on light surface: `#173b73`
- Active/tab/link blue: `#1e5ab4`
- Token brand blue: `#0f5bd8`
- Token deep brand blue: `#083a8c`

### Hero / billboard colors

- Hero burgundy: `#3d102e`
- Hero violet: `#2b173f`
- Hero navy: `#22395f`
- Hero highlight gold: `#ffdd74`
- Hero poster accents:
  - `#e56b77`
  - `#f0b546`
  - `#6bc5bc`
  - `#6eaef8`

### Utility / signal colors

- Utility strip red: `#cf1f1f`
- Notification / danger red in app: `#e83b45`
- Success green in portal preview: `#2ea84b`
- Token success green: `#27885e`
- Warm accent from tokens: `#c96f3b`
- Soft warm accent from tokens: `#f0d7c5`

### App shell color rules

- Sidebar should stay in the `#172334` / `#152133` family
- App text on dark surfaces should stay close to `#eef3f8`
- App active states should use white text or restrained blue accents
- Bright colors inside app shell should be used only for signal/status

### Public shell color rules

- Header and content surfaces should stay white or very pale neutral
- Dark CTA/button color should stay close to `#16263c`
- Hero can use the burgundy-violet-navy range:
  - `#3d102e`
  - `#2b173f`
  - `#22395f`
- Blue should be used mostly for tabs, links, and active states, not for glossy CTA treatments
- Red is acceptable for the thin utility strip, not as a dominant page color

### Avoid

- Glossy saturated blue gradients for standard buttons
- Random extra accent colors outside this palette
- Heavy decorative color use inside dense app screens

## Product Zones

The system is split into three shell types:

1. Public / landing
2. App shell
3. Learning environment

Some pages can exist in more than one shell. The shell controls presentation; the page content can still be shared.

## Public / Landing Standards

### Mood

- Institutional, portal-like, structured
- Inspired by university websites, but adapted to AzureLMS product flows
- Trust-first rather than hype-first

### What We Want

- Utility strip + main header + hero/carousel + portal blocks
- Sections that feel like a real institutional portal
- Old AzureLMS content blocks adapted into the new structure:
  - featured courses
  - how it works
  - testimonials
  - CTA
  - footer

### What We Do Not Want

- Oversized marketing hero typography
- Giant soft cards
- Glossy blue buttons
- Presentation-slide feeling
- Excessive gradients dominating the page

### Public Header Rules

- White main header
- Thin red utility strip is acceptable as a signal layer
- Navigation should be flat, clean, and understated
- Buttons should be flat and solid, not shiny or glassy

### Public Hero Rules

- Hero can be a carousel
- Slides must keep a stable outer height
- Heading length must not change overall hero height
- Left side can be visual/poster-driven
- Right side should keep a consistent text rhythm:
  - kicker
  - title
  - supporting paragraph
  - CTAs
  - 3-point summary row

### Public Portal-Block Rules

- The next section should slightly overlap the hero
- It should "touch" the hero, not cover too much of it
- Carousel controls must remain clearly visible above the overlap
- Two side-by-side portal cards should share the same visual height

### Public Content Section Rules

- Featured courses should stay product-focused
- "How it works" should be concise and structured
- Testimonials should support trust, not dominate the layout
- CTA should be strong, but still restrained and institutional

### Public Visual Language

- Compact spacing
- Sharp/controlled radii
- Neutral whites and structured dark/navy surfaces
- Accent colors should act as signals, not decoration

## Auth Shell Standards

### Mood

- Compact
- Trust-first
- Product-like, not promotional
- Minimal and calm
- Public oiladan rang qarindoshligini oladi, lekin layout bo'yicha mustaqil

### Auth Shell Rules

- Public navbar va footer ko'rinmaydi
- Auth alohida shell sifatida ishlaydi
- Shell ikki qismli bo'ladi:
  - left content pane
  - right visual pane
- Left pane ichida faqat mini auth chrome bo'ladi:
  - back to site
  - locale switch
- Brand block majburiy emas
- Form taski asosiy fokus bo'ladi
- Inputlar va buttonlar flat, sharp va professional ko'rinishi kerak

### What We Want

- Login
- Register
- Recovery
- Verification
- Hamma sahifalarda bir xil shell ritmi
- Public bilan brand continuity, lekin alohida product surface hissi
- `login / recovery / verify` uchun single-task screen
- `register` uchun step-based onboarding flow

### What We Do Not Want

- Giant centered auth cards
- Oversized illustration blocks
- Glossy CTA
- Floating SaaS-style glass panels
- Hero-level headings auth page ichida
- Long classic signup forms
- Fake dashboard previewlari
- Ortiqcha auth tab switcherlar

### Auth Content Rules

- Left pane task va forma uchun ishlaydi
- Right pane productni tushuntirish uchun emas, sokin visual context uchun ishlaydi
- `login` bitta vazifali bo'ladi:
  - identity
  - password
  - primary action
- `register` onboarding oqimida ishlaydi:
  - har ekranda bitta savol
  - bitta aniq qaror
- `recovery` contact -> code oqimiga xizmat qiladi
- Verification sahifasi ayniqsa toza va distraction-free bo'lishi kerak
- Recovery oqimi 3 bosqichga aniq ajratiladi:
  - contact
  - code
  - new access

### Auth Visual Language

- Figma usulidagi onboarding/auth soddaligi foydali
- Light content pane + muted blue motion stage yaxshi ishlaydi
- Rang oilasi product bilan qarindosh qoladi
- Form maydoni kompakt, lekin tiqilinch bo'lmasligi kerak
- Visual pane mockup emas, atmosferali motion-stage bo'lishi kerak
- Right pane:
  - floating chips
  - soft badges
  - subtle lines
  - quiet motion

## App Shell Standards

### Mood

- Dense
- Utilitarian
- Operational
- University admin panel feel, but cleaner and more modern

### What Works

- Dark sidebar
- Thin topbar
- Compact dashboard blocks
- Accordion/grouped navigation in the sidebar
- Strong vertical rhythm and alignment

### What We Do Not Want

- Big hero cards
- Oversized padding
- Soft/glassy dashboard widgets
- "Presentation dashboard" feeling

### App Shell Layout Rules

- Sidebar is a real operational navigation column
- Header is thin and secondary
- Main content should start quickly
- Cards should be short, dense, and role-specific

### Sidebar Rules

- Grouped sections are preferred
- Collapsible navigation works well
- Account/profile area should not float awkwardly away from other groups
- Icons and labels must share a strict alignment rhythm

### App Density Standards

These are the approximate prototype standards we liked:

- Sidebar width: about `264px`
- Topbar height: about `42px`
- Workspace padding: about `10px 12px 16px`
- Info tile height: about `70px`
- Card radius: about `4px`
- Navigation item padding: compact, around `7px` to `8px`
- Menu font size: about `0.8rem`
- Group supporting text: about `0.65rem`

### App Visual Language

- Signal over decoration
- Compact over airy
- Structured over playful
- Real control-panel feeling over showcase feeling

## Learning Environment Standards

### Mood

- Focused
- Task-oriented
- Quiet
- More immersive than the app shell, but still compact and structured

### What Works

- A narrow dark learning rail on the left
- A thin session/status bar at the top
- One dominant lesson stage in the center
- Smaller supporting cards on the right
- Clear progression from `video -> notes -> exercise -> chat`

### What We Do Not Want

- Oversized hero-like lesson blocks
- Airy marketing spacing
- Decorative dashboards inside the learning view
- Multiple competing focal points
- Large typography that makes the shell feel like a landing page

### Learning Shell Layout Rules

- The shell should read as a workspace, not as a portal
- Left rail is for lesson context and progression, not general navigation
- Topbar is for mode switching and session state
- Center column is the main learning stage
- Right column is for support:
  - AI coach
  - task queue
  - session info

### Learning Rail Rules

- Rail should stay narrow and dense
- Brand area should be minimal
- Current lesson card should be compact and informative
- Outline steps should be clearly numbered and vertically tight
- Mini stats in the rail should support orientation, not distract

### Learning Stage Rules

- The central lesson/video stage is the dominant visual block
- Stage header should remain short:
  - lesson title
  - one supporting descriptor line
  - compact tool buttons
- Video/stage placeholder should feel like a real player container
- The stage should not expand into poster-style composition

### Learning Sidepanel Rules

- Side cards should be stacked and compact
- AI card should feel actionable, not decorative
- Task queue should show progress state clearly:
  - done
  - current
  - next
- Session info cards should be small and scannable

### Learning Density Standards

These are the approximate prototype standards we liked:

- Left rail width: about `236px`
- Topbar min height: about `44px`
- Main workspace padding: about `12px`
- Standard panel/card padding: about `12px`
- Tool button size: about `28px`
- Chip min height: about `30px`
- Learning body/supporting text: about `0.76rem`
- Learning header/title text: about `0.92rem`
- Video placeholder height: about `340px`

### Learning Visual Language

- Dark, calm workspace surfaces
- White and pale text on dark backgrounds
- Blue is used as a restrained active-state signal
- Green is acceptable only for progress/success states
- Compact boxes beat large dramatic surfaces

## Exam Environment Standards

### Mood

- Fullscreen
- Controlled
- Focused
- Strictly task-driven

### What Works

- One secure topbar with timer and exam state
- One central question workspace
- One compact sidepanel for section status and question map
- Internal exam navigation only:
  - previous
  - next
  - review
  - submit

### What We Do Not Want

- Site navigation
- Marketing-like blocks
- Messenger, promo, or dashboard widgets inside the main exam workspace
- Oversized question cards or theatrical typography
- Multiple unrelated panels competing with the current question

### Exam Shell Layout Rules

- The exam shell should fill the full viewport
- The topbar is for trust and control:
  - secure state
  - question count
  - timer
  - autosave state
- The main column is for passage and question only
- The sidepanel is allowed only because it supports the exam itself

### Exam Mode Family

- Reading mode:
  - passage + question + map
- Writing mode:
  - prompt + editor + rubric/status
- Listening mode:
  - audio player + question + replay constraints
- Speaking mode:
  - prompt + recording stage + device/status checks
- Results/review mode:
  - score summary + section breakdown + review notes

Every mode keeps the same secure shell language. Only the center task surface changes.

### Exam Content Rules

- Question copy should stay compact and readable
- Option rows should be large enough to click, but not oversized
- Passage and question should sit in one consistent working plane
- Footer actions should always remain close to the question flow

### Exam Restriction Rules

- No links to other site areas
- No shell-level sidebar navigation
- No floating distractions
- Only exam-related actions are allowed in view

### Exam Visual Language

- Dark secure workspace
- Strong contrast
- Small and disciplined typography
- Compact cards and grids
- Warning color only for timer/review urgency

## Decision Rules

When choosing between two design options:

- Choose the one that feels more structured
- Choose the one that reduces decorative noise
- Choose the one that reads more like a real platform
- Avoid anything that starts feeling like a template marketplace demo

## Working Rule

Before redesigning a new page, first decide:

1. Which shell it belongs to
2. Whether it is shared content or shell-specific content
3. Whether the page should feel institutional, operational, or focused

Then apply the correct shell language instead of inventing a new style for that page.
