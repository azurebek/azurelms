# Prototype Coverage Matrix

Bu hujjat `docs/FRONTEND_REBUILD_TARGETS.md` ichidagi HTML targetlarni hozirgi `design-playground/` coverage bilan solishtiradi.

## Important Modeling Rule

Bu matrixdagi `Shell` ustuni sahifaning **asosiy yoki birinchi prototype surface**ini bildiradi, lekin u har doim `faqat shu yerda bo'ladi` degani emas.

Ba'zi sahifalar bitta maqsadga ega bo'lib, ikki xil surface'da yashashi mumkin:

- `public surface`
  acquisition, trust, discovery, onboarding
- `app surface`
  current user contexti, personalized actions, operational continuity
- `document surface`
  print, certificate, appendix, receipt kabi hujjatga o'xshash ko'rinishlar

Masalan:

- `pricing` public'da marketing/acquisition ko'rinishida bo'lishi mumkin
- shu bilan birga app ichida `upgrade / renew / compare plans` ko'rinishida ham yashashi mumkin
- `course list` va `course detail` ham public discovery varianti va auth qilingan user uchun app varianti sifatida ikkita surface'ga ega bo'lishi mumkin

Shu sabab `Shell` ustunini `exclusive ownership` emas, `primary prototype family` deb o'qish kerak.

## Status Legend

- `page-ready`: shu sahifa uchun alohida prototype HTML bor
- `shell-only`: sahifa tegishli shell ichida ko'rinadi, lekin alohida page prototype hali yo'q
- `component-only`: component/reference darajasida bor, lekin yakuniy page ko'rinishi hali yo'q
- `missing`: hozircha aniq prototype yo'q
- `dual-surface`: bu page tabiatan bir nechta shell/surface varianti bilan yashashi mumkin

## Public Shell

| Target | Shell | Status | Prototype source | Notes |
|---|---|---|---|---|
| `templates/base.html` | Public | `shell-only` | `design-playground/public-shell.html` | Header, hero, portal, footer yo'nalishi bor |
| `templates/index.html` | Public | `page-ready` | `design-playground/public-shell.html` | Landing asosiy reference sifatida yetarlicha kuchli |
| `templates/about.html` | Public | `page-ready` | `design-playground/about.html` | Mission, vision, statistics va team content uchun alohida prototype tayyor |
| `templates/legal_page.html` | Public + App / Document | `page-ready` | `design-playground/legal-privacy.html`, `design-playground/legal-terms.html`, `design-playground/legal-faq.html` | Shared legal template uchun uchta page-type reference tayyor: privacy, terms va FAQ |
| `templates/subscriptions/pricing.html` | Public + App / Commerce | `dual-surface` | - | Public acquisition varianti va app ichidagi upgrade/renew varianti bo'lishi mumkin; ikkalasi ham hali yo'q |
| `templates/courses/course_list.html` | Public + App / Catalog | `dual-surface` | `design-playground/public-shell.html`, `design-playground/app-course-list.html` | Public discovery va auth user katalogi ikkisi ham kerak bo'lishi mumkin |
| `templates/courses/course_detail.html` | Public + App / Catalog | `dual-surface` | `design-playground/public-shell.html`, `design-playground/app-course-detail.html` | Public detail va app ichidagi cohort-aware detail ikkisi ham kerak bo'lishi mumkin |

## Auth Shell

| Target | Shell | Status | Prototype source | Notes |
|---|---|---|---|---|
| `templates/auth/base.html` | Auth | `page-ready` | `design-playground/auth-login.html` | Split auth shell yaxshi aniqlangan |
| `templates/registration/login.html` | Auth | `page-ready` | `design-playground/auth-login.html` | Tayyor reference bor |
| `templates/registration/register.html` | Auth | `page-ready` | `design-playground/auth-register.html` | Tayyor reference bor |
| `templates/registration/password_reset_form.html` | Auth | `shell-only` | `design-playground/auth-recovery.html` | Recovery family ichida moslashadi |
| `templates/registration/password_reset_confirm.html` | Auth | `shell-only` | `design-playground/auth-verify.html` | Verify family ichida moslashadi |
| `templates/registration/password_reset_done.html` | Auth | `shell-only` | `design-playground/auth-recovery.html` | Intermediate confirmation state kerak |
| `templates/registration/password_reset_complete.html` | Auth | `shell-only` | `design-playground/auth-recovery.html` | Final success state hali alohida chizilmagan |

## App Shell

| Target | Shell | Status | Prototype source | Notes |
|---|---|---|---|---|
| `templates/dashboard/base.html` | App | `page-ready` | `design-playground/app-shell.html` | Base shell pishgan |
| `templates/users/dashboard.html` | App | `page-ready` | `design-playground/app-shell.html` | Dashboard reference bor |
| `templates/users/leaderboard.html` | App | `missing` | - | Alohida ranking page prototype kerak |
| `templates/users/attendance_calendar.html` | App | `missing` | - | Calendar page hali yo'q |
| `templates/users/attendance_manage.html` | App | `missing` | - | Manage/operator ko'rinishi ham yo'q |
| `templates/users/notifications.html` | App | `missing` | - | Notification center page kerak |
| `templates/users/profile.html` | App | `missing` | - | Profile page prototype kerak |
| `templates/users/settings.html` | App | `missing` | - | Settings page prototype kerak |
| `templates/users/subscriptions.html` | App | `missing` | - | App ichidagi subscription center yo'q |
| `templates/users/help_center.html` | Public + App / Support | `dual-surface` | - | Public FAQ/help va auth qilingan user uchun operational help center varianti bo'lishi mumkin |
| `templates/users/certificates.html` | App / Records | `missing` | - | Certificate list/history page yo'q |

## App Catalog Variants

| Target | Shell | Status | Prototype source | Notes |
|---|---|---|---|---|
| `app course list variant` | App | `page-ready` | `design-playground/app-course-list.html` | Auth bo'lgan katalog uchun reference bor |
| `app course detail variant` | App | `page-ready` | `design-playground/app-course-detail.html` | Auth bo'lgan detail uchun reference bor |

Bu ikkalasi rebuild targetlarda alohida template sifatida turmagan bo'lsa ham, keyingi qarorlar uchun muhim reference hisoblanadi.

## Dual-Surface Candidates

Quyidagi page oilalari tabiatan `bitta sahifa = bitta shell` emas:

| Page family | Variant 1 | Variant 2 | Notes |
|---|---|---|---|
| `pricing` | Public acquisition | App upgrade / renew | Copy, CTA va context boshqacha bo'ladi |
| `legal` | Public trust / footer documents | App settings / help / compliance access | Dedicated prototype family tayyor; kontent shared bo'lishi mumkin, lekin surrounding shell va navigatsiya boshqacha bo'ladi |
| `course_list` | Public discovery catalog | App contextual catalog | App varianti current level/cohort signallarini ko'rsatadi |
| `course_detail` | Public sales/detail | App operational cohort detail | App ichida enrollment qarori continuity bilan keladi |
| `help_center` | Public FAQ/support intro | App support workspace | Auth userda issue history va contextual help bo'lishi mumkin |

## Page Ownership Buckets

Bu bo'lim prototype planning uchun eng amaliy ko'rinishni beradi: qaysi sahifa oilasi faqat public, qaysisi faqat app, qaysisi esa ikki surface'da yashashi mumkin.

### 1. Public-only

Bu sahifalar asosan trust, discovery, onboarding yoki public information vazifasini bajaradi.

- `templates/base.html`
- `templates/index.html`
- `templates/about.html`
- `templates/auth/base.html`
- `templates/registration/login.html`
- `templates/registration/register.html`
- `templates/registration/password_reset_form.html`
- `templates/registration/password_reset_confirm.html`
- `templates/registration/password_reset_done.html`
- `templates/registration/password_reset_complete.html`
- `blog/templates/blog/base.html`
- `blog/templates/blog/post_list.html`
- `blog/templates/blog/post_detail.html`

### 2. App-only

Bu sahifalar auth qilingan foydalanuvchi yoki operator kontekstiga tayanadi va public surface'da yashashi mantiqan to'g'ri emas.

- `templates/dashboard/base.html`
- `templates/users/dashboard.html`
- `templates/users/leaderboard.html`
- `templates/users/attendance_calendar.html`
- `templates/users/attendance_manage.html`
- `templates/users/notifications.html`
- `templates/users/profile.html`
- `templates/users/settings.html`
- `templates/users/subscriptions.html`
- `templates/users/certificates.html`
- `templates/courses/lesson_detail.html`
- `templates/courses/exam_detail.html`
- `templates/courses/exam_result.html`
- `templates/messenger/chat_widget.html`
- `blog/templates/blog/studio_form.html`
- `blog/templates/blog/studio_list.html`
- `templates/includes/dashboard_enrollment_card.html`
- `templates/includes/dashboard_recommended_course_card.html`

### 3. Dual-surface

Bu sahifalar bitta maqsadga ega bo'lsa ham, public va app ichida turlicha kontekstda ko'rinishi mumkin.

- `templates/subscriptions/pricing.html`
- `templates/legal_page.html`
- `templates/courses/course_list.html`
- `templates/courses/course_detail.html`
- `templates/users/help_center.html`
- `templates/includes/brand_lockup.html`
- `templates/includes/course_cover_overlay.html`
- `templates/includes/course_showcase_card.html`

### 4. Document-special

Bu oilani public/app duality ichiga tiqish noto'g'ri bo'ladi. Ular hujjat, checkout, printable yoki verification surface sifatida alohida qaralishi kerak.

- `templates/cohorts/checkout.html`
- `templates/cohorts/checkout_success.html`
- `templates/courses/certificate.html`
- `templates/courses/certificate_appendix.html`

## Planning Shortcut

Agar prototype navbatni eng amaliy ko'rinishda belgilamoqchi bo'lsak:

1. `App-only gaps`
   - notifications
   - profile
   - settings
   - subscriptions
   - attendance
   - leaderboard
   - certificates list
2. `Document-special gaps`
   - checkout
   - checkout success
   - certificate
   - certificate appendix
3. `Dual-surface gaps`
   - pricing
   - public/app course list
   - public/app course detail
   - help center

## Learning Shell

| Target | Shell | Status | Prototype source | Notes |
|---|---|---|---|---|
| `templates/courses/lesson_detail.html` | Learning | `shell-only` | `design-playground/learning-shell.html` | Asosiy lesson workspace bor, lekin text/homework/quiz/chat mode'lar hali ko'paytirilishi kerak |

## Exam Shell

| Target | Shell | Status | Prototype source | Notes |
|---|---|---|---|---|
| `templates/courses/exam_detail.html` | Exam | `page-ready` | `design-playground/exam-shell.html`, `design-playground/exam-writing.html`, `design-playground/exam-listening.html`, `design-playground/exam-speaking.html` | Family kuchli, mode-specific center stage bor |
| `templates/courses/exam_result.html` | Exam | `page-ready` | `design-playground/exam-review.html` | Student-facing review/result reference bor |

## Commerce / Document Flows

| Target | Shell | Status | Prototype source | Notes |
|---|---|---|---|---|
| `templates/cohorts/checkout.html` | Commerce / Document | `missing` | - | Juda muhim bo'shliq |
| `templates/cohorts/checkout_success.html` | Commerce / Document | `missing` | - | Checkout completion state yo'q |
| `templates/courses/certificate.html` | Document | `missing` | - | Hujjatga o'xshash alohida shell kerak |
| `templates/courses/certificate_appendix.html` | Document | `missing` | - | Academic appendix uchun alohida layout kerak |

## Messenger

| Target | Shell | Status | Prototype source | Notes |
|---|---|---|---|---|
| `templates/messenger/chat_widget.html` | App / Learning Widget | `component-only` | `design-playground/components/messenger.html` | Widget reference bor, lekin final page/context rule hali qotmagan |
| `full messenger workspace` | Messenger | `page-ready` | `design-playground/messenger-shell.html` | Albatta rebuild targetda yo'q, lekin future reference sifatida kuchli |

## Blog

| Target | Shell | Status | Prototype source | Notes |
|---|---|---|---|---|
| `blog/templates/blog/base.html` | Blog / Editorial | `shell-only` | `design-playground/blog-public-shell.html`, `design-playground/blog-article-shell.html`, `design-playground/blog-studio-shell.html` | Oilaning bazasi bor, lekin yagona base hali ajratilmagan |
| `blog/templates/blog/post_list.html` | Blog / Editorial | `page-ready` | `design-playground/blog-public-shell.html` | Public list reference tayyor |
| `blog/templates/blog/post_detail.html` | Blog / Editorial | `page-ready` | `design-playground/blog-article-shell.html` | Article page reference tayyor |
| `blog/templates/blog/studio_form.html` | Blog / Studio | `shell-only` | `design-playground/blog-studio-shell.html` | Form ichki bloklari bor, lekin final dedicated page yo'q |
| `blog/templates/blog/studio_list.html` | Blog / Studio | `shell-only` | `design-playground/blog-studio-shell.html` | Queue/list bor, lekin ajratilgan page hali yo'q |

## Shared Includes

| Target | Shell | Status | Prototype source | Notes |
|---|---|---|---|---|
| `templates/includes/brand_lockup.html` | Shared | `component-only` | `design-playground/public-shell.html`, `design-playground/app-shell.html` | Mark+copy patternlar bor |
| `templates/includes/course_cover_overlay.html` | Shared | `component-only` | `design-playground/public-shell.html`, `design-playground/app-course-detail.html` | Visual direction bor, include hali ajratilmagan |
| `templates/includes/course_showcase_card.html` | Shared | `component-only` | `design-playground/public-shell.html`, `design-playground/components/cards.html` | Card oilasi bor |
| `templates/includes/dashboard_enrollment_card.html` | Shared | `component-only` | `design-playground/app-shell.html` | Dashboard stat/enrollment ritmi bor, alohida include yo'q |
| `templates/includes/dashboard_recommended_course_card.html` | Shared | `component-only` | `design-playground/app-shell.html`, `design-playground/app-course-list.html` | App card oilasi bor |

## Biggest Prototype Gaps

Priority bo'yicha eng katta bo'shliqlar:

1. `checkout + checkout_success`
2. `certificate + certificate_appendix`
3. `notifications / profile / settings / subscriptions / help_center`
4. `attendance_calendar / attendance_manage / leaderboard / certificates list`
5. `public course_list / public course_detail / pricing / about`

## Suggested Prototype Order

1. Commerce/document oilasi:
   - checkout
   - checkout success
   - certificate
   - certificate appendix
2. App utility oilasi:
   - notifications
   - profile
   - settings
   - subscriptions
   - help center
3. Academic tracking oilasi:
   - attendance calendar
   - attendance manage
   - leaderboard
   - certificates list
4. Public informational oilasi:
   - pricing
   - public course list
   - public course detail
