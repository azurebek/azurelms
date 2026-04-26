# Mobile-First Readiness Standard

Bu hujjat `design-playground/` prototiplarini mobile-first tamoyiliga tizimli moslash uchun birinchi gate hisoblanadi. Maqsad: har bir flow mobile viewportlarda tartibli yig'ilsin, desktop reference buzilmasin, va responsive ishlar flow-by-flow nazorat bilan bajarilsin.

## Scope

Bu bosqich CSSni ommaviy qayta yozmaydi. U quyidagilarni belgilaydi:

- target viewportlar
- shell va page darajasidagi mobile qarorlar
- controlled overflow qoidalari
- flow bo'yicha migration tartibi
- har bir responsive refactor uchun verification checklist

## Target Viewports

Har bir flow quyidagi viewportlarda tekshiriladi:

| Viewport | Purpose | Gate |
| --- | --- | --- |
| `360 x 800` | Eng tor oddiy telefon | Majburiy |
| `390 x 844` | Asosiy mobile reference | Majburiy |
| `430 x 932` | Katta telefon | Majburiy |
| `768 x 1024` | Tablet portrait | Majburiy |
| `1024 x 768` | Tablet landscape / kichik laptop | Tavsiya |
| `1440 x 900` | Desktop reference | Majburiy |

Mobile refactor desktop reference bilan solishtiriladi. Desktopdagi flow, hierarchy, CTA va content ownership saqlanishi kerak.

## Mobile Contract

Har bir sahifa quyidagi shartlarni bajarishi kerak:

1. Body yoki shell tasodifiy horizontal scroll bermaydi.
2. Agar table, calendar yoki dense ranking scroll qilsa, scroll faqat o'sha component ichida bo'ladi.
3. Header, topbar, sidebar, action row va form controls ekrandan chiqib ketmaydi.
4. Buttons va form controls kamida `44px` touch heightga yaqin bo'ladi.
5. Text containerdan chiqmaydi; uzun label wrap yoki truncate bilan nazorat qilinadi.
6. App, studio, messenger, checkout va error sahifalarda typography compact qoladi.
7. `100vh` ishlatilgan shelllarda mobile browser chrome sababli content kesilib qolmasligi tekshiriladi.
8. Page-specific fixlar avval scoped wrapper ichida yoziladi; repeated pattern keyin family CSSga ko'tariladi.

## Controlled Overflow

Quyidagi yuzalarda horizontal scroll ruxsat etiladi, lekin wrapper ichida bo'lishi shart:

- attendance calendar
- leaderboard table
- subscription/payment history table
- exam question map yoki dense answer grid
- messenger component catalog preview

Bu componentlarda wrapper quyidagilarni ta'minlaydi:

- visible border yoki surface chegarasi
- `overflow-x: auto`
- ichki `min-width`
- shell bodyda global horizontal scroll yo'qligi

## Flow Order

Responsive ishlar quyidagi tartibda bajariladi:

| Order | Flow | Reason |
| --- | --- | --- |
| 1 | Public Discovery | Eng ko'p public entry va header/hero risklari |
| 2 | Auth & Billing | Forms, checkout va secure task flowlar |
| 3 | Student App Shell | Sidebar, topbar va workspace umumiy riski |
| 4 | Student App Pages | Dense cards, filters, tables va account yuzalari |
| 5 | Learning, Exam, Messenger | Full-screen shell va scroll zone nazorati |
| 6 | Blog, Studio, Legal, Error | Lower-risk long-form va operational refinements |
| 7 | Component Reference | Component catalog parity va reusable patternlar |

## Flow Decisions

### Public Discovery

- Main header mobileda compact bo'ladi.
- Utility strip wrap qilishi mumkin, lekin asosiy CTA ko'rinishi saqlanadi.
- Hero/carousel bir ustunga tushadi; visual layer contentni bosmaydi.
- Course cards va pricing cards single-column yoki two-column tablet layoutga o'tadi.

### Auth & Billing

- Auth split shell mobileda single-column bo'ladi.
- Visual/context pane pastga ko'chadi yoki qisqa summaryga aylanadi.
- Checkout desktopdagi task orderni saqlaydi: plan -> payment instruction -> receipt upload -> pending state.
- OTP cells va upload controls ekrandan chiqmaydi.

### Student App

- Mobile shell qarori bitta shared pattern bo'ladi: collapsed sidebar, compact nav yoki drawer.
- Topbar page contextni saqlaydi; content ichida katta takroriy title qo'shilmaydi.
- Workspace scroll zone aniq bo'ladi.
- Dense data pages component-level horizontal scroll ishlatadi.

### Learning

- Lesson rail mobileda top summary yoki drawerga aylanadi.
- Main lesson stage birinchi ko'rinadi.
- Notes/support panel pastga tushadi yoki secondary tab sifatida beriladi.

### Exam

- Global navigation yo'q.
- Timer, autosave, question count va submit controls har viewportda topiladi.
- Passage/question layout mobileda stacked bo'ladi.
- Review va question map controlled overflow bilan ishlaydi.

### Messenger

- Conversation list mobileda rail yoki switcherga aylanadi.
- Active chat topbarda ko'rinadi.
- Message list va composer ekranga sig'adi; composer fixed bo'lsa contentni yopmaydi.

### Blog, Studio, Legal, Error

- Blog Reading long-form readabilityni saqlaydi.
- Blog Studio app-like compact shellni saqlaydi.
- Legal pages document rhythmni buzmaydi.
- Error pages bitta clear action va support pathni saqlaydi.

## CSS Work Rules

1. Avval shell/family CSSdagi mobile skeleton tuzatiladi.
2. Keyin scoped page CSSdagi local grid va dense components tuzatiladi.
3. Bir xil mobile pattern ikki yoki undan ko'p sahifada ishlatilsa, family CSSga ko'tariladi.
4. Breakpointlar mavjud family ritmiga mos bo'ladi: `1180`, `1080`, `960`, `820`, `760`, `720`, `640`.
5. Yangi breakpoint qo'shilsa, u shu hujjatda sabab bilan qayd qilinadi.
6. Mobile fix desktop selectorni bevosita buzmasligi kerak.

## Verification Gate

Har bir flow tugaganda quyidagilar bajariladi:

| Check | Required |
| --- | --- |
| `360`, `390`, `430`, `768`, `1440` screenshot review | Ha |
| Body horizontal overflow check | Ha |
| Header/topbar/sidebar visibility check | Ha |
| Primary CTA visible and tappable | Ha |
| Dense component controlled overflow check | Kerak bo'lsa |
| Local HTML link check | Ha |
| `git diff --check` | Ha |

## Phase 1 Status

Phase 1 status: `started`.

Bu hujjat mobile-first refactor uchun source-of-truth sifatida qo'shildi. Keyingi bosqich Public Discovery flowining shell va page CSSlarini shu gate asosida moslashdan boshlanadi.

## Implementation Log

| Date | Flow | Status | Notes |
| --- | --- | --- | --- |
| 2026-04-25 | Public Discovery | `final-mobile-pass` | Public shell, working mobile menu drawer, equal-height mobile carousel, course list/detail, about, pricing, footer, and touch targets passed the public mobile gate. Verified `360`, `390`, `430`, `768`, and `1440` with browser DOM overflow, touch, clipped text, menu interaction, carousel equal-height, local link, and diff checks. |
