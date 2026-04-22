# AzureLMS Component Catalog

This file lists the reusable component patterns we should preserve while moving from prototype to real templates.

## Public Components

### Utility Strip

- Thin red signal bar
- Small, bold links
- Secondary to main header

### Main Header

- White background
- Brand block on the left
- Flat center navigation
- Flat right-side actions

### Hero Carousel

Parts:

- poster visual area
- copy column
- CTA row
- 3-point summary row
- dot indicators
- prev/next controls

Rules:

- every slide keeps the same outer height
- copy column uses a fixed rhythm
- controls must stay visible above overlap content

### Portal Cards

Two-column block after hero:

- left media/preview card
- right tabbed information card

Rules:

- both cards share one visual row
- the block slightly overlaps the hero
- it should feel like institutional portal content, not a marketing feature grid

### Course Card

Parts:

- cover
- kicker
- title
- description
- chips
- footer meta/action

Rules:

- compact
- product-first
- avoid oversized empty space

### Process Card

Parts:

- numbered step badge
- short title
- supporting line

Rules:

- concise
- one concept per card

### Testimonial Card

Parts:

- stars
- quote
- name
- role

Rules:

- support trust
- never overpower product sections

### CTA Strip

Parts:

- kicker
- heading
- short supporting line
- 1 to 2 actions

Rules:

- restrained
- dark and solid rather than glossy

### Footer

Parts:

- grouped links
- contact area
- bottom legal line

Rules:

- informational, not decorative

## App Components

### Sidebar Brand

- mark
- product name
- short descriptor

### Sidebar Group Toggle

Parts:

- group title
- small supporting text
- chevron

Rules:

- compact
- grouped
- supports accordion behavior

### Sidebar Nav Item

Parts:

- icon
- label
- optional badge

Rules:

- strict icon alignment
- equal row rhythm
- active state should be subtle but obvious

### User Card

- avatar
- name
- handle/meta

Rules:

- stays anchored at the bottom of the sidebar

### Topbar

- left context/term
- right utility actions

Rules:

- thin
- low-noise
- secondary to content

### Info Tile

- short title/value pair
- optional signal color

Rules:

- low height
- easy scanning
- no oversized padding

### Dense Data Card

- short header
- compact content body
- clear functional purpose

Rules:

- operational
- not showcase-oriented

## Learning Components

### Learning Rail Brand

- small mark
- product/workspace label

Rules:

- minimal
- not a marketing brand block

### Current Lesson Card

Parts:

- lesson kicker
- current lesson title
- compact meta chips

Rules:

- informative
- short
- always compact

### Lesson Outline

Parts:

- numbered step
- title
- supporting line

Rules:

- vertical rhythm must stay tight
- active state should be obvious but restrained
- should read as progression, not generic navigation

### Learning Topbar

Parts:

- session meta row
- mode chips
- optional exit action

Rules:

- thin
- operational
- used for current learning mode only

### Learning Chip

Parts:

- short label
- optional active state

Rules:

- compact
- low-noise
- active state uses restrained blue treatment

### Stage Card

Parts:

- lesson title
- supporting descriptor
- compact tool buttons
- media/player container

Rules:

- main focal area of the shell
- should feel like a real learning player container
- no poster-like oversized composition

### Tool Button

- square compact control
- icon-only

Rules:

- small
- secondary
- grouped tightly in the stage header

### Learning Panel

Parts:

- short header
- concise body

Rules:

- used below stage for notes, goals, summary, checkpoints
- should remain supportive, not dominant

### AI Coach Card

Parts:

- short status header
- one short paragraph
- primary action

Rules:

- should feel active and useful
- never oversized or chat-app-like by default

### Task Queue

Parts:

- task rows
- state labels

Rules:

- must support `done`, `current`, and `next`
- rows stay compact and easy to scan

### Session Info Mini Card

- short value
- short label

Rules:

- grouped in small grids
- used for progress, checkpoint, language, live status

## Messenger Components

### Launcher

- floating trigger button
- optional unread/status badge

Rules:

- stays in the bottom-right corner
- should feel compact and quiet
- appears in app and learning shells without becoming the main focal point

### Quick Panel

Parts:

- compact header
- mode tabs
- short message snippet area
- compact compose row
- link to full messenger

Rules:

- used for fast questions and short replies
- opens without leaving the current page
- must stay smaller and quieter than a real chat page

### Full Messenger Workspace

Parts:

- thread list
- active conversation area
- compose row
- context panel

Rules:

- used when history, long conversation, tutor flow, or group flow matters
- should behave like a real workspace, not like a popup
- shares the same compact visual language as app and learning shells

## Auth Components

### Auth Mini Chrome

- back to site
- locale switch

Rules:

- minimal
- always secondary to the form task
- should not become a real navbar
- brand block optional, not required on every screen

### Auth Split Shell

- left content pane
- right visual pane

Rules:

- auth is not a landing page
- visual pane supports mood and product context
- visual pane never overpowers the form

### Auth Form Surface

Parts:

- title
- short supporting paragraph
- compact fields
- primary action row
- secondary helper/meta row

Rules:

- main focal point
- operational, not decorative
- sits inside the left content pane, not floating in a marketing layout
- register should avoid becoming one long traditional signup form

### Auth Step Meta

- step bar
- step counter

Rules:

- used for onboarding-style register flow
- should stay secondary to the main form task
- should sit below the primary interaction, not between heading and form

### Auth Method Choice

- email option
- phone option

Rules:

- compact
- clear active state
- useful for recovery flow

### Auth Verification Code Row

- 6 input cells
- timer/status chips
- resend/change contact links

Rules:

- distraction-free
- strongly scannable
- should feel secure and deliberate

### Auth Motion Stage

- board/stage surface
- floating chips
- floating badges
- subtle line accents
- short supporting caption

Rules:

- used on the right pane
- should feel calm and premium
- should not imitate a fake dashboard
- should stay quiet, restrained, and non-cartoony

## Exam Components

### Secure Topbar

- exam identity
- timer
- question count
- autosave state

Rules:

- no global site navigation
- communicates control and trust, not distraction

### Passage Panel

- reading text or source material

Rules:

- scrollable when needed
- stays visually tied to the current question

### Question Panel

- question title
- supporting line
- answer options

Rules:

- compact and highly readable
- no oversized blocks

### Question Map

- numbered grid of questions

Rules:

- small but legible
- visually separates done, review, current, and untouched states

### Exam Footer Actions

- previous
- review
- next

Rules:

- stays close to the question flow
- only exam-related actions appear here

### Submit Card

- short checklist
- final submit action

Rules:

- positioned in the sidepanel
- visually serious, but not dramatic

### Writing Editor

- task prompt
- editor surface
- word count / autosave chips

Rules:

- should feel like a focused writing workspace
- no unnecessary decoration around the editor

### Listening Player

- audio header
- waveform/progress
- replay-aware controls

Rules:

- player is central
- transcript is not shown by default
- replay constraints should be visible

### Speaking Record Stage

- prompt
- recording status
- waveform
- record action

Rules:

- recording state is the main focal point
- device status should be clear without clutter

### Results / Review Summary

- overall score
- section scores
- review rows
- next-step actions

Rules:

- informative and calm
- feels like a formal result screen, not a celebratory landing page

## Migration Rule

Before building a new page in Django:

1. pick the shell
2. list which components from this file are needed
3. assemble the page from known components
4. only create a new component if none of the existing patterns fit
