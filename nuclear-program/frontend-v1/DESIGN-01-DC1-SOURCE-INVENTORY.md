# DESIGN-01 / DC1 — source inventari

2026-10-10; runtime `ead7698`. [Izoh, sozlama va komponent xaritasi](DESIGN-01-DC1-MAP.md).

Bu statik source snapshot. CSS qiymatlari browser computed style emas; URL resolver
registratsiyasi permission/data/parity testi emas. Preview metadata ignored lokal
registrdan o‘qildi; uning source/asset/fixture fayllari ko‘chirilmadi.

## Hisob va usul

- Runtime: **197 named URL** (admin/ckeditor mountlari chiqarilgan, default local config).
- Preview: **139 route yozuvi / 77 page template / 118 noyob source nomi**, yana **2 alias / 3 error handler**.
- Source UI/alias xaritasi: **120 nom**; registrdagi barcha nom runtime resolverda topildi.
- Qolgan **77 URL** yordamchi endpoint; quyida alohida berilgan.
- 20 registry component nomi: `button`, `icon-button`, `icon`, `badge`, `card`, `field`, `alert`, `progress`, `tabs`, `nav-item`, `dialog`, `avatar`, `empty`, `skeleton`, `step`, `choice`, `table`, `section-title`, `stat`, `week`.
- Resolver: env-file off, Gemini/Telegram kalitlari bo‘sh, local profil, DB backend `django.db.backends.dummy`; request/DB/remote provider ishlatilmadi.
- CSS usuli: declaration bloklaridan default/dark/print qiymatlar, `var(--az-...)` literal murojaatlari; commentlar consumer hisobidan chiqarilgan. Dinamik CSS-in-JS yoki hisoblangan selector exhaustive deb olinmaydi.
- Inventar Python stdlib bilan chiqarildi; `.tools/design-dc1/` lokal tekshiruv yordamchilari Git artefakti emas. Kelajakdagi qayta audit source fayllar/URL resolver/Trial registryga qarshi qilinadi.

## Source fingerprintlar

SHA256 oldidan fayl baytlaridagi CRLF (`\r\n`) LF (`\n`)ga almashtiriladi;
boshqa baytlar o'zgarmaydi. Shu sabab Windows va Linux natijasi bir xil.
CSS qiymatlari `ead7698` Git blob baytlari bilan ham solishtirildi.
Qayta hisoblash: `hashlib.sha256(Path(path).read_bytes().replace(b'\r\n', b'\n')).hexdigest()`.
Ignored lokal registry uchun ham shu normalizatsiya ishlatiladi.

| Source | SHA256 |
|---|---|
| `playground/Eleventh Trial/prototype/contracts/registry.json` | `340ea3936eb37b2fe932977585db133ba98cfde331feedef2a37733d45a21de8` |
| `static/frontend_v1/css/tokens.css` | `40edf73c50278b95e7b8e0f898b305acc907fc4c384a924c37c0efaaf9aab5db` |
| `static/css/tokens.css` | `d7450b520ae494fe7327a2d8580383c224972fed9dc3936f76aa60c2990ef699` |

## V1 tokenlarning to‘liq xaritasi

Consumer ustunidagi fayllar `static/frontend_v1/css/`ga nisbiy, boshqa manba bo‘lsa to‘liq repo yo‘li. `—` dark/printda defaultdan meros.
Sozlama ustunidagi `fixed` — hisobga olingan, ownerga mustaqil maydon ochish taklif qilinmagan.

| Token | Default | Dark | Print | Sozlama | Direct consumer fayllari |
|---|---|---|---|---|---|
| `--az-canvas` | `#f6f8fb` | `#111722` | `#ffffff` | S01 | `base.css`, `messenger.css`, `records.css`, `shell.css` |
| `--az-surface` | `#ffffff` | `#192231` | `#ffffff` | S01 | `auth.css`, `components.css`, `learning.css`, `messenger.css`, `public.css`, `shell.css`, `study.css` |
| `--az-side` | `#ffffff` | `#151d2a` | `#ffffff` | S01 | `shell.css` |
| `--az-soft` | `#eef2f7` | `#222e40` | `#eef2f7` | S01 | `components.css`, `messenger.css`, `records.css`, `shell.css`, `study.css` |
| `--az-text` | `#172235` | `#eef2f8` | `#172235` | S02 | `base.css`, `components.css`, `messenger.css`, `public.css`, `shell.css` |
| `--az-muted` | `#5d6a7e` | `#aab7ca` | `#5d6a7e` | S02 | `account.css`, `auth.css`, `certificates.css`, `components.css`, `directory.css`, `exam-attempt.css`, `exams.css`, `learning.css`, `messenger.css`, `public.css`, `records.css`, `settings.css`, `shell.css`, `study.css` |
| `--az-faint` | `#5f6c82` | `#97a6bc` | `#5f6c82` | S02 | `shell.css` |
| `--az-border` | `#e3e8ef` | `#2c394d` | `#e3e8ef` | S03 | `auth.css`, `certificates.css`, `classbook.css`, `components.css`, `directory.css`, `exam-attempt.css`, `exams.css`, `learning.css`, `library.css`, `messenger.css`, `public.css`, `records.css`, `shell.css`, `study.css` |
| `--az-action` | `#1257e6` | `#9bb8ff` | `#1257e6` | S04 | `base.css`, `certificates.css`, `components.css`, `learning.css`, `messenger.css`, `public.css`, `records.css`, `shell.css`, `study.css` |
| `--az-action-hover` | `#1048bf` | `#b2c8ff` | `#1048bf` | S04 | `components.css`, `messenger.css` |
| `--az-on-action` | `#ffffff` | `#12203c` | `#ffffff` | S04 | `base.css`, `components.css`, `messenger.css`, `shell.css` |
| `--az-action-soft` | `#edf3ff` | `#233552` | `#edf3ff` | S04 | `components.css`, `learning.css`, `messenger.css`, `public.css`, `records.css`, `shell.css` |
| `--az-action-border` | `#cfdefc` | `#3b527c` | `#cfdefc` | S03 | `components.css`, `learning.css`, `messenger.css` |
| `--az-hero` | `#edf3ff` | `#1c2b44` | `#edf3ff` | S01 | `learning.css`, `public.css` |
| `--az-success` | `#22714f` | `#93d7b4` | `#22714f` | S05 | `components.css`, `learning.css`, `records.css` |
| `--az-success-soft` | `#eaf6ef` | `#203c32` | `#eaf6ef` | S05 | `components.css`, `learning.css`, `records.css` |
| `--az-danger` | `#b43b44` | `#ffb2ba` | `#b43b44` | S05 | `account.css`, `components.css`, `learning.css`, `records.css` |
| `--az-danger-soft` | `#fceef0` | `#432b34` | `#fceef0` | S05 | `components.css`, `learning.css`, `records.css` |
| `--az-warning` | `#936410` | `#eac488` | `#936410` | S05 | `components.css`, `messenger.css`, `records.css` |
| `--az-focus` | `#1257e6` | `#b2c8ff` | `#1257e6` | S06 | `base.css`, `editors.css` |
| `--az-overlay` | `rgb(15 24 42 / 40%)` | `rgb(0 5 15 / 65%)` | — | S07 | `components.css` |
| `--az-shadow` | `0 12px 36px rgb(24 42 72 / 9%)` | `0 12px 36px rgb(0 0 0 / 20%)` | — | S07 | `components.css`, `messenger.css` |
| `--az-font` | `"Segoe UI", -apple-system, BlinkMacSystemFont, system-ui, sans-serif` | — | — | S08 | `base.css` |
| `--az-mono` | `"Cascadia Code", Consolas, monospace` | — | — | S08 | `learning.css` |
| `--az-text-xs` | `.75rem` | — | — | S09 | `account.css`, `auth.css`, `base.css`, `certificates.css`, `components.css`, `directory.css`, `learning.css`, `messenger.css`, `records.css`, `shell.css`, `study.css` |
| `--az-text-sm` | `.875rem` | — | — | S09 | `account.css`, `auth.css`, `certificates.css`, `components.css`, `directory.css`, `exam-attempt.css`, `exams.css`, `learning.css`, `messenger.css`, `public.css`, `records.css`, `settings.css`, `shell.css`, `study.css` |
| `--az-text-md` | `1rem` | — | — | S09 | `base.css`, `certificates.css`, `components.css`, `directory.css`, `learning.css`, `messenger.css`, `settings.css`, `study.css` |
| `--az-text-lg` | `1.125rem` | — | — | S09 | `account.css`, `base.css`, `exam-attempt.css`, `messenger.css`, `shell.css` |
| `--az-text-xl` | `1.375rem` | — | — | S09 | `base.css`, `certificates.css`, `learning.css`, `messenger.css`, `shell.css` |
| `--az-text-2xl` | `1.75rem` | — | — | S09 | `certificates.css`, `components.css`, `learning.css`, `public.css`, `study.css` |
| `--az-text-title` | `clamp(1.75rem, 1.35rem + 1.2vw, 2.25rem)` | — | — | S09 | `base.css`, `records.css` |
| `--az-text-display` | `clamp(2.25rem, 1.8rem + 1.3vw, 3rem)` | — | — | S09 | `certificates.css`, `exams.css`, `learning.css`, `public.css` |
| `--az-leading` | `1.6` | — | — | S10 | `base.css`, `components.css`, `exam-attempt.css`, `messenger.css` |
| `--az-leading-tight` | `1.2` | — | — | S10 | `base.css`, `certificates.css` |
| `--az-tracking` | `-.025em` | — | — | S11 | `base.css`, `learning.css`, `shell.css` |
| `--az-tracking-caps` | `.11em` | — | — | S11 | `components.css`, `learning.css`, `shell.css` |
| `--az-weight-medium` | `550` | — | — | S10 | `components.css`, `learning.css`, `public.css`, `records.css`, `shell.css`, `study.css` |
| `--az-weight-bold` | `650` | — | — | S10 | `account.css`, `base.css`, `certificates.css`, `components.css`, `exams.css`, `learning.css`, `records.css`, `settings.css`, `shell.css` |
| `--az-space-1` | `.25rem` | — | — | S19 | `account.css`, `base.css`, `certificates.css`, `components.css`, `exam-attempt.css`, `learning.css`, `library.css`, `messenger.css`, `public.css`, `records.css`, `settings.css`, `shell.css`, `study.css` |
| `--az-space-2` | `.5rem` | — | — | S19 | `auth.css`, `certificates.css`, `classbook.css`, `components.css`, `directory.css`, `exam-attempt.css`, `exams.css`, `learning.css`, `library.css`, `messenger.css`, `public.css`, `records.css`, `shell.css`, `study.css` |
| `--az-space-3` | `.75rem` | — | — | S19 | `account.css`, `auth.css`, `certificates.css`, `classbook.css`, `components.css`, `directory.css`, `exam-attempt.css`, `exams.css`, `learning.css`, `messenger.css`, `public.css`, `records.css`, `settings.css`, `shell.css`, `study.css` |
| `--az-space-4` | `1rem` | — | — | S19 | `account.css`, `auth.css`, `certificates.css`, `classbook.css`, `components.css`, `directory.css`, `editors.css`, `exam-attempt.css`, `exams.css`, `learning.css`, `library.css`, `messenger.css`, `public.css`, `records.css`, `shell.css`, `study.css` |
| `--az-space-5` | `1.25rem` | — | — | S19 | `account.css`, `auth.css`, `certificates.css`, `classbook.css`, `components.css`, `exam-attempt.css`, `exams.css`, `learning.css`, `library.css`, `messenger.css`, `public.css`, `records.css`, `settings.css`, `study.css` |
| `--az-space-6` | `1.5rem` | — | — | S19 | `account.css`, `auth.css`, `certificates.css`, `components.css`, `directory.css`, `exam-attempt.css`, `exams.css`, `learning.css`, `messenger.css`, `public.css`, `records.css`, `shell.css`, `study.css` |
| `--az-space-8` | `2rem` | — | — | S19 | `auth.css`, `certificates.css`, `components.css`, `exams.css`, `learning.css`, `messenger.css`, `public.css`, `records.css`, `shell.css`, `study.css` |
| `--az-space-10` | `2.5rem` | — | — | S19 | `shell.css` |
| `--az-space-12` | `3rem` | — | — | S19 | `components.css`, `public.css` |
| `--az-space-16` | `4rem` | — | — | S19 | `components.css`, `public.css`, `records.css` |
| `--az-radius-sm` | `.5rem` | — | — | S12–18: ajratish | `account.css`, `classbook.css`, `components.css`, `learning.css`, `messenger.css`, `public.css`, `records.css`, `shell.css`, `study.css` |
| `--az-radius` | `.875rem` | — | — | S12–18: ajratish | `components.css`, `learning.css`, `messenger.css` |
| `--az-radius-lg` | `1.125rem` | — | — | S12–18: ajratish | `components.css` |
| `--az-radius-round` | `999px` | — | — | S12–18: ajratish | `components.css` |
| `--az-icon` | `1.25rem` | — | — | fixed | `components.css`, `exam-attempt.css` |
| `--az-avatar` | `2.5rem` | — | — | S16 | `account.css`, `components.css` |
| `--az-avatar-sm` | `2rem` | — | — | S16 | `components.css`, `public.css`, `shell.css` |
| `--az-control` | `2.75rem` | — | — | S12–18: ajratish | `account.css`, `auth.css`, `components.css`, `exam-attempt.css`, `learning.css`, `library.css`, `messenger.css`, `public.css`, `records.css`, `settings.css`, `shell.css`, `study.css` |
| `--az-button-min` | `8rem` | — | — | S12–18: ajratish | `records.css`, `study.css` |
| `--az-progress` | `.375rem` | — | — | fixed | `components.css` |
| `--az-dot` | `.375rem` | — | — | fixed | `components.css`, `shell.css` |
| `--az-sidebar` | `16rem` | — | — | S17 | `shell.css` |
| `--az-header` | `4rem` | — | — | S17 | `auth.css`, `exam-attempt.css`, `public.css`, `shell.css` |
| `--az-content` | `88rem` | — | — | S19 | `public.css`, `shell.css` |
| `--az-aside` | `18.5rem` | — | — | S19 | `exam-attempt.css`, `exams.css`, `learning.css`, `messenger.css`, `records.css`, `study.css` |
| `--az-reading` | `48rem` | — | — | S19 | `certificates.css`, `components.css`, `exam-attempt.css`, `messenger.css`, `public.css` |
| `--az-dialog` | `32rem` | — | — | S15 | `auth.css`, `components.css`, `study.css` |
| `--az-drawer` | `19rem` | — | — | S15 | `components.css` |
| `--az-empty` | `32rem` | — | — | fixed | `components.css` |
| `--az-art-width` | `12rem` | — | — | fixed | `learning.css`, `records.css`, `study.css` |
| `--az-art-height` | `13rem` | — | — | fixed | `learning.css` |
| `--az-layer-sticky` | `10` | — | — | fixed | `public.css`, `shell.css` |
| `--az-layer-overlay` | `20` | — | — | fixed | `components.css`, `shell.css` |
| `--az-fast` | `100ms` | — | — | fixed | **Topilmadi** |
| `--az-motion` | `160ms` | — | — | fixed | `components.css`, `learning.css` |

Declared, ammo yuqoridagi scan doirasida direct consumer topilmagan tokenlar: `--az-fast`.
Bu tokenlarga UI sozlamasi chiqarishdan oldin haqiqiy consumer ulanadi yoki maydon ochilmaydi.

## Legacy palitra ko‘prigi — taklif

Bu aliaslar hozir kodda yo‘q. Legacy sahifalardagi literal CSS va SIT override alohida ko‘chiriladi.

| Legacy rol | V1 rolga nomzod | Chegara |
|---|---|---|
| `paper,paper-2,panel` | `canvas,soft,surface` | Body/section/field yuzalari tekshiriladi |
| `ink,ink-2,ink-3,ink-4` | `text,muted,faint` + alohida disabled | To‘rt pog‘onani uch rangga ko‘r-ko‘rona siqish yo‘q |
| `line,line-2` | `border` + subtle border | Ikkinchi border uchun mustaqil rol zarurati DC2da |
| `azure,azure-2,azure-soft,on-azure` | `action,action-hover,action-soft,on-action` | Link va tugma juftliklari birma-bir tekshiriladi |
| `green/amber/red` va `*-soft` | success/warning/danger oilasi | Warning-soft V1da hozir yo‘q |
| `violet,violet-soft` | Alohida dekorativ rol yoki cheklangan istisno | V1da to‘g‘ridan-to‘g‘ri ekvivalenti yo‘q |
| SIT `sans,mono` / legacy literal font | Body/heading/code | Asset va fallback tekshiruvi kerak |

## Named UI/alias → sahifa oilasi → source

F kodlari asosiy xaritaning §5 jadvaliga ulanadi. Preview IDlari mavjud namunalar;
real pathda demo ID ishlatilmaydi. Alias alohida yangi UI hisoblanmaydi.

| Oila | Runtime URL nomi / pattern | Canonical callback | Preview IDlari / page template |
|---|---|---|---|
| F01 | `about`<br>`/about/` | `frontend.views.about_view` | `public_about`<br>`public_about.html` |
| F01 | `blog:detail`<br>`/blog/<slug:slug>/` | `blog.views.BlogDetailView` | `public_blog_detail`<br>`public_content_detail.html` |
| F01 | `blog:list`<br>`/blog/` | `blog.views.BlogListView` | `public_blog`<br>`public_content_list.html` |
| F01 | `course_detail`<br>`/courses/<int:pk>/` | `courses.views.CourseDetailView` | `public_course_1`, `public_course_2`<br>`public_course.html` |
| F01 | `courses`<br>`/courses/` | `courses.views.CourseListView` | `public_catalog`<br>`public_catalog.html` |
| F01 | `faq_page`<br>`/faq/` | `frontend.views.legal_page_view` | `public_faq`<br>`public_legal.html` |
| F01 | `home`<br>`/` | `frontend.views.home_view` | `public_home`<br>`public_home.html` |
| F01 | `privacy_policy`<br>`/privacy-policy/` | `frontend.views.legal_page_view` | `public_privacy`<br>`public_legal.html` |
| F01 | `sit:home`<br>`/sit/` | `sit.views.home` | `public_sit`<br>`public_content_list.html` |
| F01 | `sit:knowledge_detail`<br>`/sit/guides/<slug:slug>/` | `sit.views.knowledge_detail` | `public_guide_detail`<br>`public_content_detail.html` |
| F01 | `sit:university_detail`<br>`/sit/universities/<slug:slug>/` | `sit.views.university_detail` | `public_university_detail`<br>`public_content_detail.html` |
| F01 | `sit:university_list`<br>`/sit/universities/` | `sit.views.university_list` | `public_universities`<br>`public_content_list.html` |
| F01 | `subscriptions:pricing`<br>`/pricing/` | `subscriptions.views.PricingView` | `public_pricing`<br>`public_pricing.html` |
| F01 | `terms_of_service`<br>`/terms-of-service/` | `frontend.views.legal_page_view` | `public_terms`<br>`public_legal.html` |
| F02 | `login`<br>`/users/login/` | `core.frontend_v1.FrontendLoginView` | `auth_login`<br>`auth.html` |
| F02 | `onboarding_choice`<br>`/users/register/onboarding/` | `users.views.OnboardingChoiceView` | `auth_onboarding`<br>`auth.html` |
| F02 | `password_reset`<br>`/users/password-reset/` | `users.frontend_v1_auth.PasswordResetView` | `auth_reset`<br>`auth.html` |
| F02 | `password_reset_complete`<br>`/users/password-reset-complete/` | `users.frontend_v1_auth.PasswordResetCompleteView` | `auth_reset_complete`<br>`auth.html` |
| F02 | `password_reset_confirm`<br>`/users/password-reset-confirm/<uidb64>/<token>/` | `users.frontend_v1_auth.PasswordResetConfirmView` | `auth_reset_confirm`<br>`auth.html` |
| F02 | `password_reset_done`<br>`/users/password-reset/done/` | `users.frontend_v1_auth.PasswordResetDoneView` | `auth_reset_done`<br>`auth.html` |
| F02 | `register`<br>`/users/register/` | `users.views.RegisterView` | `auth_register`<br>`auth.html` |
| F03 | `dashboard`<br>`/users/dashboard/` | `users.views.DashboardView` | `dashboard`<br>`dashboard.html` |
| F03 | `my_courses`<br>`/users/my-courses/` | `users.views.MyCoursesView` | `courses`<br>`courses.html` |
| F04 | `lesson_detail`<br>`/courses/<int:course_id>/lesson/<int:lesson_id>/` | `courses.views.LessonDetailView` | `lesson`, `lesson_materials_81`<br>`lesson.html`, `lesson_materials_81.html` |
| F05 | `messenger:group`<br>`/messenger/group/` | `messenger.views.MessengerGroupView` | `messages_group`<br>`messages.html` |
| F05 | `messenger:tutor`<br>`/messenger/tutor/` | `messenger.views.MessengerTutorView` | `messages_tutor`<br>`messages.html` |
| F06 | `messenger:ai`<br>`/messenger/ai/` | `messenger.views.MessengerAIView` | `messages_ai`<br>`messages.html` |
| F06 | `messenger:ai_room`<br>`/messenger/ai/<int:room_id>/` | `messenger.views.MessengerAIView` | `messages_ai_room`<br>`messages.html` |
| F06 | `messenger:index`<br>`/messenger/` | `messenger.views.MessengerAIView` | `alias:messages_ai`<br>`alias` |
| F07 | `profile`<br>`/users/profile/` | `users.views.UserProfileView` | `profile`<br>`profile.html` |
| F07 | `settings_account`<br>`/users/settings/hisob/` | `users.views.SettingsAccountView` | `settings_account`<br>`settings_account.html` |
| F08 | `settings_billing`<br>`/users/settings/tolov/` | `users.views.SettingsBillingView` | `settings_billing`<br>`settings_billing.html` |
| F08 | `settings_capabilities`<br>`/users/settings/imkoniyatlar/` | `users.views.SettingsCapabilitiesView` | `settings_capabilities`<br>`settings_capabilities.html` |
| F08 | `settings_privacy`<br>`/users/settings/maxfiylik/` | `users.views.AIMemoryListView` | `settings_privacy`<br>`settings_privacy.html` |
| F09 | `attendance_calendar`<br>`/users/attendance/` | `users.views.AttendanceCalendarView` | `attendance`<br>`records.html` |
| F09 | `certificates`<br>`/users/certificates/` | `users.views.CertificateListView` | `certificates`<br>`certificates.html` |
| F09 | `help_center`<br>`/users/help/` | `users.views.HelpCenterView` | `help`<br>`help.html` |
| F09 | `leaderboard`<br>`/users/leaderboard/` | `users.views.LeaderboardView` | `leaderboard`<br>`records.html` |
| F09 | `notifications`<br>`/users/notifications/` | `users.views.NotificationCenterView` | `notifications`<br>`notifications.html` |
| F09 | `subscriptions`<br>`/users/subscriptions/` | `users.views.SubscriptionHistoryView` | `subscriptions`<br>`records.html` |
| F10 | `certificate_appendix`<br>`/courses/certificate/<str:certificate_id>/appendix/` | `courses.views.CertificateAppendixView` | `certificate_appendix`<br>`certificates.html` |
| F10 | `certificate_detail`<br>`/courses/certificate/<str:certificate_id>/` | `courses.views.CertificateDetailView` | `certificate_detail`<br>`certificates.html` |
| F11 | `attendance_manage`<br>`/users/attendance/manage/` | `users.views.AttendanceManageView` | `attendance_manage`<br>`attendance_manage.html` |
| F11 | `teacher_attendance`<br>`/teacher/attendance/` | `core.teacher_views.teacher_attendance` | `teacher_attendance`<br>`teacher_attendance.html` |
| F11 | `teacher_cohorts`<br>`/teacher/cohorts/` | `core.teacher_views.teacher_cohorts` | `teacher_cohorts`<br>`teacher_directory.html` |
| F11 | `teacher_courses`<br>`/teacher/courses/` | `core.teacher_views.teacher_courses_view` | `teacher_courses`<br>`teacher_courses.html` |
| F11 | `teacher_dashboard`<br>`/teacher/` | `core.teacher_views.teacher_dashboard` | `teacher_home`<br>`teacher_home.html` |
| F11 | `teacher_grade_assignment`<br>`/teacher/grading/assignment/<int:submission_id>/` | `core.teacher_views.teacher_grade_assignment` | `assignment_review`<br>`assignment_review.html` |
| F11 | `teacher_grading`<br>`/teacher/grading/` | `core.teacher_views.teacher_grading` | `grading`<br>`grading.html` |
| F11 | `teacher_release`<br>`/teacher/release/` | `core.teacher_views.teacher_release` | `teacher_release`<br>`teacher_release.html` |
| F11 | `teacher_students`<br>`/teacher/students/` | `core.teacher_views.teacher_students` | `teacher_students`<br>`teacher_directory.html` |
| F12 | `backoffice_course_create`<br>`/backoffice/courses/new/` | `core.views.backoffice_course_editor` | `course_new`<br>`course_create.html` |
| F12 | `backoffice_course_edit`<br>`/backoffice/courses/<int:course_id>/` | `core.views.backoffice_course_editor` | `course_edit_1`, `course_edit_2`, `course_edit_3`, `course_edit_4`<br>`course_editor.html` |
| F12 | `backoffice_courses`<br>`/backoffice/courses/` | `core.views.backoffice_courses` | `course_list`<br>`course_list.html` |
| F12 | `backoffice_lesson_edit`<br>`/backoffice/lessons/<int:lesson_id>/` | `core.views.backoffice_lesson_editor` | `lesson_edit_3`, `lesson_edit_81`<br>`lesson_detail.html` |
| F12 | `backoffice_lessons`<br>`/backoffice/lessons/` | `core.views.backoffice_lesson_editor` | `lesson_index`<br>`lesson_index.html` |
| F13 | `library_backoffice:lesson_picker`<br>`/backoffice/library/lessons/<int:lesson_id>/pick/` | `library.backoffice_views.lesson_picker` | `library_picker_3`, `library_picker_81`<br>`library_list.html` |
| F13 | `library_backoffice:resource_create`<br>`/backoffice/library/new/` | `library.backoffice_views.resource_editor` | `library_new`<br>`library_new.html` |
| F13 | `library_backoffice:resource_edit`<br>`/backoffice/library/<int:resource_id>/` | `library.backoffice_views.resource_editor` | `library_detail_41`, `library_detail_42`, `library_detail_43`, `library_detail_46`, `library_detail_47`, `library_detail_48`, `library_detail_49`, `library_detail_50`<br>`library_detail.html` |
| F13 | `library_backoffice:resources`<br>`/backoffice/library/` | `library.backoffice_views.resource_list` | `library_index`<br>`library_list.html` |
| F14 | `cohorts:checkout`<br>`/checkout/course/<int:course_id>/` | `cohorts.views.checkout_view` | `checkout`, `checkout_enrollment`<br>`checkout.html`, `checkout_enrollment.html` |
| F14 | `cohorts:checkout_pending`<br>`/checkout/receipt/<int:receipt_id>/pending/` | `cohorts.views.checkout_pending_view` | `payment_pending`<br>`payment_status.html` |
| F14 | `cohorts:checkout_success`<br>`/checkout/receipt/<int:receipt_id>/success/` | `cohorts.views.checkout_success_view` | `payment_success`<br>`payment_status.html` |
| F14 | `cohorts:checkout_success_latest`<br>`/checkout/success/` | `cohorts.views.checkout_success_view` | `alias:payment_success`<br>`alias` |
| F15 | `exam_center`<br>`/courses/exams/` | `courses.views.ExamCenterView` | `exam_center`<br>`exam_center.html` |
| F15 | `exam_detail`<br>`/courses/<int:course_id>/exam/<int:exam_id>/` | `courses.views.ExamDetailView` | `exam_detail`<br>`exam_detail.html` |
| F15 | `exam_result`<br>`/courses/<int:course_id>/exam/<int:exam_id>/result/` | `courses.views.ExamResultView` | `exam_result`<br>`exam_result.html` |
| F15 | `teacher_grade_exam`<br>`/teacher/grading/exam/<int:attempt_id>/` | `core.teacher_views.teacher_grade_exam` | `teacher_exam_review`<br>`teacher_exam_review.html` |
| F16 | `classbook:exercise_create`<br>`/classbook/teacher/exercises/new/` | `classbook.views.exercise_edit` | `classbook_exercise_new`<br>`classbook_exercise_form.html` |
| F16 | `classbook:exercise_edit`<br>`/classbook/teacher/exercises/<int:exercise_id>/` | `classbook.views.exercise_edit` | `classbook_exercise_edit`<br>`classbook_exercise_form.html` |
| F16 | `classbook:exercise_list`<br>`/classbook/teacher/exercises/` | `classbook.views.exercise_list` | `classbook_exercises`<br>`classbook_exercises.html` |
| F16 | `classbook:playbook_edit`<br>`/classbook/teacher/playbook/<int:cohort_id>/<int:lesson_id>/` | `classbook.views.playbook_edit` | `classbook_playbook_3_3`, `classbook_playbook_8_81`, `classbook_playbook_9_81`<br>`classbook_playbook.html` |
| F16 | `classbook:teacher_home`<br>`/classbook/teacher/` | `classbook.views.teacher_home` | `classbook_home`<br>`classbook_home.html` |
| F17 | `classbook:activity_result`<br>`/classbook/live/activity/<int:activity_id>/result/` | `classbook.views.activity_result` | `classbook_live_result`<br>`classbook_live.html` |
| F17 | `classbook:live_activity`<br>`/classbook/live/activity/<int:activity_id>/` | `classbook.views.live_activity` | `classbook_live_activity`<br>`classbook_live.html` |
| F17 | `classbook:live_home`<br>`/classbook/live/` | `classbook.views.live_home` | `classbook_live_home`<br>`classbook_live.html` |
| F17 | `classbook:live_session`<br>`/classbook/live/<int:session_id>/` | `classbook.views.live_session` | `classbook_live_session_8`, `live`<br>`classbook_live.html`, `live.html` |
| F17 | `classbook:teacher_activity_result`<br>`/classbook/teacher/activity/<int:activity_id>/results/` | `classbook.views.teacher_activity_result` | `classbook_teacher_activity_result`<br>`classbook_teacher_result.html` |
| F17 | `classbook:teacher_session`<br>`/classbook/teacher/session/<int:session_id>/` | `classbook.views.teacher_session` | `classbook_session_8`, `teacher`<br>`classbook_session.html`, `teacher.html` |
| F18 | `backoffice_ai_circuit_reset`<br>`/backoffice/control/ai-circuit-reset/` | `core.views.backoffice_ai_circuit_reset` | `ops_circuit`<br>`operations.html` |
| F18 | `backoffice_ai_control`<br>`/backoffice/ai-control/` | `core.views.backoffice_ai_control` | `ops_ai`<br>`operations.html` |
| F18 | `backoffice_ai_cost`<br>`/backoffice/control/ai-cost/` | `core.views.backoffice_ai_cost` | `ops_cost`<br>`operations.html` |
| F18 | `backoffice_ai_kill_switch`<br>`/backoffice/control/ai-kill-switch/` | `core.views.backoffice_ai_kill_switch` | `ops_kill`<br>`operations.html` |
| F18 | `backoffice_brand`<br>`/backoffice/control/brand/` | `core.views.backoffice_brand` | `ops_brand`<br>`appearance.html` |
| F18 | `backoffice_catalog`<br>`/backoffice/catalog/` | `subscriptions.backoffice_views.catalog` | `control_catalog`<br>`control_catalog.html` |
| F18 | `backoffice_chats`<br>`/backoffice/chats/` | `core.views.backoffice_chats` | `backoffice_chats`<br>`backoffice_chats.html` |
| F18 | `backoffice_cohort_create`<br>`/backoffice/catalog/cohorts/new/` | `subscriptions.backoffice_views.cohort_editor` | `control_cohort_new`<br>`control_catalog_form.html` |
| F18 | `backoffice_cohort_edit`<br>`/backoffice/catalog/cohorts/<int:cohort_id>/` | `subscriptions.backoffice_views.cohort_editor` | `control_cohort`<br>`control_catalog_form.html` |
| F18 | `backoffice_cohort_members`<br>`/backoffice/catalog/cohorts/<int:cohort_id>/members/` | `subscriptions.backoffice_views.cohort_members` | `control_members`<br>`control_members.html` |
| F18 | `backoffice_control`<br>`/backoffice/control/` | `core.views.backoffice_control` | `ops_home`<br>`operations.html` |
| F18 | `backoffice_dashboard`<br>`/backoffice/` | `core.views.backoffice_dashboard` | `backoffice_home`<br>`backoffice_home.html` |
| F18 | `backoffice_dead_letter`<br>`/backoffice/control/dead-letter/` | `core.views.backoffice_dead_letter` | `ops_dead`<br>`operations.html` |
| F18 | `backoffice_exam_edit`<br>`/backoffice/exams/<int:exam_id>/` | `core.views.backoffice_exam_editor` | `exam_editor_101`, `exam_editor_102`, `exam_editor_201`<br>`exam_editor.html` |
| F18 | `backoffice_exams`<br>`/backoffice/exams/` | `core.views.backoffice_exam_editor` | `exam_editor_index`<br>`exam_editor_index.html` |
| F18 | `backoffice_feature_flags`<br>`/backoffice/control/flags/` | `core.views.backoffice_feature_flags` | `ops_flags`<br>`operations.html` |
| F18 | `backoffice_landing`<br>`/backoffice/landing/` | `core.views.backoffice_landing` | `ops_landing`<br>`appearance.html` |
| F18 | `backoffice_plan_edit`<br>`/backoffice/catalog/plans/<int:plan_id>/` | `subscriptions.backoffice_views.plan_editor` | `control_plan`<br>`control_catalog_form.html` |
| F18 | `backoffice_receipts`<br>`/backoffice/receipts/` | `core.views.backoffice_receipts` | `backoffice_receipts`<br>`backoffice_receipts.html` |
| F18 | `backoffice_runtime_settings`<br>`/backoffice/control/runtime-settings/` | `core.views.backoffice_runtime_settings` | `ops_runtime`<br>`operations.html` |
| F18 | `backoffice_users`<br>`/backoffice/users/` | `core.views.backoffice_users` | `backoffice_users`<br>`backoffice_users.html` |
| F18 | `blog:studio`<br>`/blog/studio/` | `blog.views.BlogStudioView` | `blog_studio`<br>`blog_studio.html` |
| F18 | `blog:studio_create`<br>`/blog/studio/new/` | `blog.views.BlogPostCreateView` | `blog_create`<br>`blog_form.html` |
| F18 | `blog:studio_edit`<br>`/blog/studio/<slug:slug>/edit/` | `blog.views.BlogPostUpdateView` | `blog_edit`<br>`blog_form.html` |
| F18 | `sit_backoffice:announcement_create`<br>`/backoffice/sit/announcements/new/` | `sit.backoffice_views.announcement_editor` | `sit_announcements_new`<br>`sit_form.html` |
| F18 | `sit_backoffice:announcement_edit`<br>`/backoffice/sit/announcements/<int:announcement_id>/` | `sit.backoffice_views.announcement_editor` | `sit_announcements_edit`<br>`sit_form.html` |
| F18 | `sit_backoffice:announcements`<br>`/backoffice/sit/announcements/` | `sit.backoffice_views.announcement_list` | `sit_announcements`<br>`sit_studio.html` |
| F18 | `sit_backoffice:dashboard`<br>`/backoffice/sit/` | `sit.backoffice_views.dashboard` | `sit_home`<br>`sit_studio.html` |
| F18 | `sit_backoffice:guide_create`<br>`/backoffice/sit/guides/new/` | `sit.backoffice_views.guide_editor` | `sit_guides_new`<br>`sit_form.html` |
| F18 | `sit_backoffice:guide_edit`<br>`/backoffice/sit/guides/<int:guide_id>/` | `sit.backoffice_views.guide_editor` | `sit_guides_edit`<br>`sit_form.html` |
| F18 | `sit_backoffice:guides`<br>`/backoffice/sit/guides/` | `sit.backoffice_views.guide_list` | `sit_guides`<br>`sit_studio.html` |
| F18 | `sit_backoffice:universities`<br>`/backoffice/sit/universities/` | `sit.backoffice_views.university_list` | `sit_universities`<br>`sit_studio.html` |
| F18 | `sit_backoffice:university_create`<br>`/backoffice/sit/universities/new/` | `sit.backoffice_views.university_editor` | `sit_universities_new`<br>`sit_form.html` |
| F18 | `sit_backoffice:university_edit`<br>`/backoffice/sit/universities/<int:university_id>/` | `sit.backoffice_views.university_editor` | `sit_universities_edit`<br>`sit_form.html` |
| F19 | `bot:miniapp_ai`<br>`/bot/miniapp/ai/` | `bot.views.miniapp_ai` | `mini_ai`<br>`mini_ai.html` |
| F19 | `bot:miniapp_courses`<br>`/bot/miniapp/courses/` | `bot.views.miniapp_courses` | `mini_courses`<br>`mini_courses.html` |
| F19 | `bot:miniapp_entry`<br>`/bot/miniapp/` | `bot.views.miniapp_entry` | `mini_entry`<br>`mini_entry.html` |
| F19 | `bot:miniapp_home`<br>`/bot/miniapp/home/` | `bot.views.miniapp_home` | `mini_home`<br>`mini_home.html` |
| F19 | `bot:miniapp_profile`<br>`/bot/miniapp/profile/` | `bot.views.miniapp_profile` | `mini_profile`<br>`mini_profile.html` |
| F21 | `maintenance`<br>`/maintenance/` | `core.views.maintenance` | `system_maintenance`<br>`system_maintenance.html` |
| F21 | `offline`<br>`/offline/` | `core.views.offline` | `system_offline`<br>`system_offline.html` |

## Error handlerlar

| Source | Real template | Trial diagnostic |
|---|---|---|
| `core.views.permission_denied` | `templates/errors/403.html` | `system_403` / `/_preview/errors/403/` |
| `core.views.page_not_found` | `templates/errors/404.html` | `system_404` / `/_preview/errors/404/` |
| `core.views.server_error` | `templates/errors/500.html` | `system_500` / `/_preview/errors/500/` |

Trial diagnostic pathlar real production URL emas. Minimal 500 DBsiz fallback sifatida F21/X08da qoladi.

## Yordamchi endpointlar — mustaqil dizayn sahifasi emas

Action natijasi, xato va media wrapperlari tegishli sahifa oilasi qabulida tekshiriladi.
JSON/file/redirect/export javobining o‘ziga palette qo‘llanmaydi.

| URL nomi | Pattern | Callback |
|---|---|---|
| `start_smart_onboarding` | `/users/register/onboarding/ai/` | `users.views.StartSmartOnboardingView` |
| `telegram_auth_init` | `/users/telegram-auth/init/` | `users.views.telegram_auth_init` |
| `telegram_auth_status` | `/users/telegram-auth/status/<str:token>/` | `users.views.telegram_auth_status` |
| `logout` | `/users/logout/` | `django.contrib.auth.views.LogoutView` |
| `settings` | `/users/settings/` | `django.views.generic.base.RedirectView` |
| `update_avatar` | `/users/settings/avatar/` | `users.views.AvatarUpdateView` |
| `update_password` | `/users/settings/password/` | `users.views.PasswordUpdateView` |
| `update_ai_tone` | `/users/settings/ai-tone/` | `users.views.AIToneUpdateView` |
| `update_ai_model` | `/users/settings/ai-model/` | `users.views.AIModelUpdateView` |
| `update_ai_skill` | `/users/settings/ai-skill/` | `users.views.AISkillUpdateView` |
| `update_ai_web_search_effort` | `/users/settings/ai-web-search/` | `users.views.AIWebSearchEffortUpdateView` |
| `ai_memory` | `/users/settings/ai-memory/` | `django.views.generic.base.RedirectView` |
| `ai_memory_toggle` | `/users/settings/ai-memory/toggle/` | `users.views.AIMemoryToggleView` |
| `ai_memory_clear` | `/users/settings/ai-memory/clear/` | `users.views.AIMemoryClearAllView` |
| `ai_memory_archive` | `/users/settings/ai-memory/<int:fact_id>/archive/` | `users.views.AIMemoryArchiveView` |
| `ai_memory_reject` | `/users/settings/ai-memory/<int:fact_id>/reject/` | `users.views.AIMemoryRejectView` |
| `notification_open` | `/users/notifications/<int:notification_id>/open/` | `users.views.NotificationOpenView` |
| `notifications_read_all` | `/users/notifications/read-all/` | `users.views.NotificationReadAllView` |
| `course_study` | `/courses/<int:course_id>/study/` | `courses.views.CourseStudyRedirectView` |
| `lesson_completion` | `/courses/<int:course_id>/lesson/<int:lesson_id>/completion/` | `courses.views.lesson_completion_view` |
| `assignment_submit` | `/courses/<int:course_id>/lesson/<int:lesson_id>/assignment/<int:assignment_id>/submit/` | `courses.views.SubmitAssignmentView` |
| `api_quiz_submit` | `/courses/<int:course_id>/lesson/<int:lesson_id>/quiz/<int:quiz_id>/submit/` | `courses.views.SubmitQuizView` |
| `api_exam_v1` | `/courses/<int:course_id>/exam/<int:exam_id>/api/v1/` | `courses.exam_attempt_v1.ExamAttemptV1View` |
| `api_exam_start` | `/courses/<int:course_id>/exam/<int:exam_id>/api/start/` | `courses.views.StartExamView` |
| `api_exam_section_state` | `/courses/<int:course_id>/exam/<int:exam_id>/api/section/<int:section_id>/state/` | `courses.views.ExamSectionStateView` |
| `api_exam_save` | `/courses/<int:course_id>/exam/<int:exam_id>/api/save/` | `courses.views.SaveExamAnswerView` |
| `api_exam_audio_upload` | `/courses/<int:course_id>/exam/<int:exam_id>/api/audio/` | `courses.views.UploadExamAudioView` |
| `api_exam_audio_play` | `/courses/<int:course_id>/exam/<int:exam_id>/api/audio-play/` | `courses.views.RegisterAudioPlayView` |
| `api_exam_review_flag` | `/courses/<int:course_id>/exam/<int:exam_id>/api/review-flag/` | `courses.views.ToggleExamReviewFlagView` |
| `api_exam_blur` | `/courses/<int:course_id>/exam/<int:exam_id>/api/blur/` | `courses.views.LogBlurWarningView` |
| `api_exam_submit` | `/courses/<int:course_id>/exam/<int:exam_id>/api/submit/` | `courses.views.SubmitExamView` |
| `submission_file` | `/courses/submission/<int:submission_id>/file/` | `core.private_media_views.submission_file` |
| `exam_answer_audio` | `/courses/exam/answer/<int:answer_id>/audio/` | `core.private_media_views.exam_answer_audio` |
| `library:material_file` | `/library/material/<int:material_id>/file/` | `library.views.material_file` |
| `blog:clap` | `/blog/<slug:slug>/clap/` | `blog.views.BlogPostClapView` |
| `blog:comment_create` | `/blog/<slug:slug>/comment/` | `blog.views.BlogCommentCreateView` |
| `blog:comment_like` | `/blog/comments/<int:comment_id>/like/` | `blog.views.BlogCommentLikeToggleView` |
| `cohorts:checkout_promo_preview` | `/checkout/course/<int:course_id>/promo-preview/` | `cohorts.views.checkout_promo_preview_view` |
| `cohorts:receipt_file` | `/checkout/receipt/<int:receipt_id>/file/` | `core.private_media_views.receipt_file` |
| `cohorts:difference_upload` | `/checkout/difference/<int:receipt_id>/upload/` | `cohorts.difference_views.upload_difference_receipt` |
| `messenger:new_ai_chat` | `/messenger/ai/new/` | `messenger.views.create_ai_chat` |
| `messenger:widget_ai_message` | `/messenger/api/widget-ai/message/` | `messenger.views.widget_ai_message` |
| `messenger:get_user_rooms` | `/messenger/api/rooms/` | `messenger.views.get_user_rooms` |
| `messenger:chat_assistant_profile` | `/messenger/api/profile/ai/` | `messenger.views.chat_assistant_profile` |
| `messenger:chat_profile` | `/messenger/api/profile/<int:user_id>/` | `messenger.views.chat_profile` |
| `messenger:toggle_room_pin` | `/messenger/api/rooms/<int:room_id>/pin/` | `messenger.views.toggle_room_pin` |
| `messenger:get_room_messages` | `/messenger/api/messages/<int:room_id>/` | `messenger.views.get_room_messages` |
| `messenger:upload_message_attachment` | `/messenger/api/messages/upload/` | `messenger.views.upload_message_attachment` |
| `messenger:edit_message` | `/messenger/api/messages/<int:message_id>/edit/` | `messenger.views.edit_message` |
| `messenger:delete_message` | `/messenger/api/messages/<int:message_id>/delete/` | `messenger.views.delete_message` |
| `messenger:submit_ai_feedback` | `/messenger/api/ai-feedback/<int:message_id>/` | `messenger.views.submit_ai_feedback` |
| `messenger:message_attachment` | `/messenger/attachment/<int:message_id>/` | `core.private_media_views.message_attachment` |
| `classbook:playbook_add_exercise` | `/classbook/teacher/playbook/<int:playbook_id>/add/` | `classbook.views.playbook_add_exercise` |
| `classbook:playbook_remove_exercise` | `/classbook/teacher/playbook/step/<int:step_id>/remove/` | `classbook.views.playbook_remove_exercise` |
| `classbook:playbook_move_exercise` | `/classbook/teacher/playbook/step/<int:step_id>/<str:direction>/` | `classbook.views.playbook_move_exercise` |
| `classbook:session_start` | `/classbook/teacher/session/start/<int:cohort_id>/<int:lesson_id>/` | `classbook.views.session_start` |
| `classbook:teacher_session_state` | `/classbook/teacher/session/<int:session_id>/state/` | `classbook.views.teacher_session_state` |
| `classbook:teacher_session_export` | `/classbook/teacher/session/<int:session_id>/export/` | `classbook.views.teacher_session_export` |
| `classbook:session_finish` | `/classbook/teacher/session/<int:session_id>/finish/` | `classbook.views.session_finish` |
| `classbook:activity_open` | `/classbook/teacher/activity/<int:activity_id>/open/` | `classbook.views.activity_open` |
| `classbook:activity_close` | `/classbook/teacher/activity/<int:activity_id>/close/` | `classbook.views.activity_close` |
| `classbook:teacher_activity_export` | `/classbook/teacher/activity/<int:activity_id>/export/` | `classbook.views.teacher_activity_export` |
| `classbook:live_session_state` | `/classbook/live/<int:session_id>/state/` | `classbook.views.live_session_state` |
| `classbook:live_activity_state` | `/classbook/live/activity/<int:activity_id>/state/` | `classbook.views.live_activity_state` |
| `classbook:live_activity_submit` | `/classbook/live/activity/<int:activity_id>/submit/` | `classbook.views.live_activity_submit` |
| `classbook:activity_media` | `/classbook/live/activity/<int:activity_id>/media/` | `classbook.views.activity_media` |
| `bot:telegram_webhook` | `/bot/webhook/` | `bot.views.telegram_webhook` |
| `bot:miniapp_auth` | `/bot/miniapp/auth/` | `bot.views.miniapp_auth` |
| `healthz` | `/healthz` | `core.health_views.healthz` |
| `readyz` | `/readyz` | `core.health_views.readyz` |
| `library_backoffice:resource_file` | `/backoffice/library/<int:resource_id>/file/` | `library.backoffice_views.resource_file` |
| `library_backoffice:resource_archive` | `/backoffice/library/<int:resource_id>/archive/` | `library.backoffice_views.resource_archive` |
| `library_backoffice:resource_delete` | `/backoffice/library/<int:resource_id>/delete/` | `library.backoffice_views.resource_delete` |
| `library_backoffice:material_attach` | `/backoffice/library/lessons/<int:lesson_id>/attach/` | `library.backoffice_views.material_attach` |
| `library_backoffice:material_reorder` | `/backoffice/library/lessons/<int:lesson_id>/reorder/` | `library.backoffice_views.material_reorder` |
| `library_backoffice:material_update` | `/backoffice/library/materials/<int:material_id>/update/` | `library.backoffice_views.material_update` |
| `library_backoffice:material_detach` | `/backoffice/library/materials/<int:material_id>/detach/` | `library.backoffice_views.material_detach` |

Shartli `/admin/` Jazzmin va `/ckeditor5/` vendor mountlari bu 197 hisobga kirmaydi (X02).
WebSocketlar `core/asgi.py`, `messenger/routing.py`, `classbook/routing.py`da; transport o‘zi X09, chat/live UI F05/F06/F17.

## Cheklovlar

- Browser computed style, responsive/native/AT, local flag DB va production server tekshirilmadi.
- Literal source inventari barcha dinamik UI holatining regression dalili emas.
- Registrydagi `skeleton` nomi V1/Trial CSS implementatsiyasi topildi degani emas; asosiy xarita C12da gap qayd etilgan.
- Bu hujjat DC1 source coverage; DC2–DC6 yoki oldingi UX qabulini yopmaydi.
