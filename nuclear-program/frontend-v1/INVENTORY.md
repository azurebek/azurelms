# Frontend V1 — tayyorlik inventari va source xaritasi

Sana: 2026-09-25. Runtime source: `d0cce32eec392717e9bb6d0c1488740bc34b3831`.
[Ko‘chirish tartibi](README.md), [bajarish jurnali](PORT-LEDGER.md).

## Hisob nimani anglatadi

**95 preview manzil → 54 page template → 76 noyob real UI/alias URL nomi.**
95 — alohida tayyor production sahifalar soni emas: kurs/dars/material ID
variantlari va bir sahifaning turli namunalari ham kiradi. 76 — faqat nom
bo‘yicha source mosligi, real data/access/action pariteti yoki port PASS emas.

Real source: **120 UI/alias (118 screen + 2 alias), 76 yordamchi endpoint
(61 action + 9 media + 3 redirect + 3 technical), 1 shartli admin mount**.
44 UI/alias uchun named preview yo‘q; ularning hammasi yangi ekran emas.
403/404/500 kabi handlerlar va socket consumerlar bu URL sonining ichida
mustaqil UI leaf bo‘lib hisoblanmaydi; relevant relizda baribir tekshiriladi.

### Oilalar bo‘yicha mavjud lokal UI

| Oila | Preview manzil | Amaldagi holat / real portdagi chegara |
|---|---:|---|
| Public, blog, SIT | 15 | List/detail va umumiy sahifalar bor; haqiqiy kontent/query mapping kerak |
| Auth | 7 | Login/register/reset/onboarding lokal; real session/form/token parity kerak |
| Learner dashboard/kurs/dars | 4 | Matn/tab/material bor; real enrollment va full lesson controller kerak |
| Messenger | 4 | Canonical preview eski; B layout tasdiqlangan alohida namuna, real socket/AI yo‘q |
| Profil/settings | 5 | Lokal UI bor; real hisob/privacy/AI preferences write mapping kerak |
| Teacher | 8 | Home/release/davomat/directory/review; cohort scope va real grade audit kerak |
| Exam | 4 | Learner 3 + teacher review; real attempt/timer/audio/submit contracti kerak |
| Checkout | 4 | Bir URLning ikki holati ham sanalgan; real receipt/access tasdig‘i yo‘q |
| Records/support | 8 | Sertifikat/davomat/obuna/reyting/help/notifications; real queryset/actions kerak |
| Course/lesson/library editor | 21 | Q13 local yopiq, Q11/Q12 qisman; to‘liq real forma va file parity yo‘q |
| Classbook | 15 | Lokal teacher/live/exercise oqimi; ko‘p foydalanuvchi va transport integratsiyasi kerak |
| **Jami** | **95** | **Productionga ko‘chirilgan yangi renderer: 0** |

Prototip registrida 180 action / 843 route-state / 20 component / 50 pattern
bor. Bular ro‘yxat hajmi; barcha kombinatsiya browser yoki real qurilmada
tekshirilganligini bildirmaydi. Messenger B eksperimenti yuqoridagi 95ga
qo‘shimcha yangi production URL sifatida hisoblanmadi.

## Ko‘chirish paketlari

Quyidagi jadval fayl/URL boshlang‘ich xaritasi. `<int:...>`, `<slug:...>`
va boshqa parametrlar real recordlar bilan to‘ldiriladi, demo ID ko‘chirilmaydi.
UI bilan bir URLdagi POSTlar ham alohida action contract sifatida tekshiriladi.

| Paket | Preview manzil | Noyob source UI nomi | Natija |
|---|---:|---:|---|
| [I1](#i1) — V1 shell, login, dashboard va mening kurslarim | 3 | 3 | NOT PORTED |
| [I2](#i2) — Dars/material, ustoz bosh sahifasi va darsni ochish | 4 | 3 | NOT PORTED |
| [I3](#i3) — Topshiriq/review, ustoz ro‘yxatlari va davomat | 6 | 6 | NOT PORTED |
| [I4](#i4) — Messenger B: guruh, ustoz va AI | 4 | 4 | NOT PORTED |
| [I5](#i5) — Public, qolgan auth, profil/settings, records/support | 34 | 33 | NOT PORTED |
| [I6](#i6) — Kutubxona, kurs va dars editorlari | 21 | 9 | NOT PORTED |
| [I7](#i7) — Checkout va to‘lov holati | 4 | 3 | NOT PORTED |
| [I8](#i8) — Imtihon va ustoz review | 4 | 4 | NOT PORTED |
| [I9](#i9) — Classbook va jonli mashg‘ulot | 15 | 11 | NOT PORTED |

I3 shuningdek I2dagi darsning assignment/quiz tablarini ulaydi: yangi route
qo‘shilmagani uchun jadvalda ikkinchi marta sanalmaydi. I2da mavjud tablar
ishlamay qolsa I2 qabul qilinmaydi; legacy lesson yoki zarur I3 adapteri shart.

## I1

V1 shell, login, dashboard va mening kurslarim. Barcha qatorlar: **NOT PORTED**.

| Real URL nomi / pattern | Preview IDlari | Canonical callback | Existing template hint |
|---|---|---|---|
| `login`<br>`/users/login/` | `auth_login` | `django.contrib.auth.views.LoginView` | `registration/login.html` |
| `dashboard`<br>`/users/dashboard/` | `dashboard` | `users.views.DashboardView` | `users/dashboard.html` |
| `my_courses`<br>`/users/my-courses/` | `courses` | `users.views.MyCoursesView` | `users/my_courses.html` |

## I2

Dars/material, ustoz bosh sahifasi va darsni ochish. Barcha qatorlar: **NOT PORTED**.

| Real URL nomi / pattern | Preview IDlari | Canonical callback | Existing template hint |
|---|---|---|---|
| `teacher_release`<br>`/teacher/release/` | `teacher_release` | `core.teacher_views.teacher_release` | `teacher/release.html` |
| `teacher_dashboard`<br>`/teacher/` | `teacher_home` | `core.teacher_views.teacher_dashboard` | `teacher/dashboard.html` |
| `lesson_detail`<br>`/courses/<int:course_id>/lesson/<int:lesson_id>/` | `lesson`, `lesson_materials_81` | `courses.views.LessonDetailView` | `courses/lesson_detail.html` |

## I3

Topshiriq/review, ustoz ro‘yxatlari va davomat. Barcha qatorlar: **NOT PORTED**.

| Real URL nomi / pattern | Preview IDlari | Canonical callback | Existing template hint |
|---|---|---|---|
| `teacher_attendance`<br>`/teacher/attendance/` | `teacher_attendance` | `core.teacher_views.teacher_attendance` | `teacher/attendance.html` |
| `teacher_courses`<br>`/teacher/courses/` | `teacher_courses` | `core.teacher_views.teacher_courses_view` | `teacher/courses.html` |
| `teacher_cohorts`<br>`/teacher/cohorts/` | `teacher_cohorts` | `core.teacher_views.teacher_cohorts` | `teacher/cohorts.html` |
| `teacher_students`<br>`/teacher/students/` | `teacher_students` | `core.teacher_views.teacher_students` | `teacher/students.html` |
| `teacher_grading`<br>`/teacher/grading/` | `grading` | `core.teacher_views.teacher_grading` | `teacher/grading.html` |
| `teacher_grade_assignment`<br>`/teacher/grading/assignment/<int:submission_id>/` | `assignment_review` | `core.teacher_views.teacher_grade_assignment` | `teacher/grade_assignment.html` |

## I4

Messenger B: guruh, ustoz va AI. Barcha qatorlar: **NOT PORTED**.

| Real URL nomi / pattern | Preview IDlari | Canonical callback | Existing template hint |
|---|---|---|---|
| `messenger:ai`<br>`/messenger/ai/` | `messages_ai` | `messenger.views.MessengerAIView` | `messenger/ai.html` |
| `messenger:ai_room`<br>`/messenger/ai/<int:room_id>/` | `messages_ai_room` | `messenger.views.MessengerAIView` | `messenger/ai.html` |
| `messenger:group`<br>`/messenger/group/` | `messages_group` | `messenger.views.MessengerGroupView` | `messenger/group.html` |
| `messenger:tutor`<br>`/messenger/tutor/` | `messages_tutor` | `messenger.views.MessengerTutorView` | `messenger/tutor.html` |

## I5

Public, qolgan auth, profil/settings, records/support. Barcha qatorlar: **NOT PORTED**.

| Real URL nomi / pattern | Preview IDlari | Canonical callback | Existing template hint |
|---|---|---|---|
| `home`<br>`/` | `public_home` | `frontend.views.home_view` | `index.html` |
| `about`<br>`/about/` | `public_about` | `frontend.views.about_view` | `about.html` |
| `subscriptions:pricing`<br>`/pricing/` | `public_pricing` | `subscriptions.views.PricingView` | `subscriptions/pricing.html` |
| `courses`<br>`/courses/` | `public_catalog` | `courses.views.CourseListView` | `courses/course_list.html` |
| `course_detail`<br>`/courses/<int:pk>/` | `public_course_1`, `public_course_2` | `courses.views.CourseDetailView` | `courses/course_detail.html` |
| `privacy_policy`<br>`/privacy-policy/` | `public_privacy` | `frontend.views.legal_page_view` | `legal_page.html` |
| `terms_of_service`<br>`/terms-of-service/` | `public_terms` | `frontend.views.legal_page_view` | `legal_page.html` |
| `faq_page`<br>`/faq/` | `public_faq` | `frontend.views.legal_page_view` | `legal_page.html` |
| `blog:list`<br>`/blog/` | `public_blog` | `blog.views.BlogListView` | `blog/post_list.html` |
| `blog:detail`<br>`/blog/<slug:slug>/` | `public_blog_detail` | `blog.views.BlogDetailView` | `blog/post_detail.html` |
| `sit:home`<br>`/sit/` | `public_sit` | `sit.views.home` | `sit/home.html` |
| `sit:university_list`<br>`/sit/universities/` | `public_universities` | `sit.views.university_list` | `sit/university_list.html` |
| `sit:university_detail`<br>`/sit/universities/<slug:slug>/` | `public_university_detail` | `sit.views.university_detail` | `sit/university_detail.html` |
| `sit:knowledge_detail`<br>`/sit/guides/<slug:slug>/` | `public_guide_detail` | `sit.views.knowledge_detail` | `sit/knowledge_detail.html` |
| `certificates`<br>`/users/certificates/` | `certificates` | `users.views.CertificateListView` | `users/certificates.html` |
| `certificate_detail`<br>`/courses/certificate/<str:certificate_id>/` | `certificate_detail` | `courses.views.CertificateDetailView` | `courses/certificate.html` |
| `certificate_appendix`<br>`/courses/certificate/<str:certificate_id>/appendix/` | `certificate_appendix` | `courses.views.CertificateAppendixView` | `courses/certificate_appendix.html` |
| `attendance_calendar`<br>`/users/attendance/` | `attendance` | `users.views.AttendanceCalendarView` | `users/attendance_calendar.html` |
| `subscriptions`<br>`/users/subscriptions/` | `subscriptions` | `users.views.SubscriptionHistoryView` | `users/subscriptions.html` |
| `leaderboard`<br>`/users/leaderboard/` | `leaderboard` | `users.views.LeaderboardView` | `users/leaderboard.html` |
| `notifications`<br>`/users/notifications/` | `notifications` | `users.views.NotificationCenterView` | `users/notifications.html` |
| `help_center`<br>`/users/help/` | `help` | `users.views.HelpCenterView` | `users/help_center.html` |
| `register`<br>`/users/register/` | `auth_register` | `users.views.RegisterView` | `registration/register.html`, `registration/register_closed.html` |
| `onboarding_choice`<br>`/users/register/onboarding/` | `auth_onboarding` | `users.views.OnboardingChoiceView` | `registration/onboarding_choice.html` |
| `password_reset`<br>`/users/password-reset/` | `auth_reset` | `django.contrib.auth.views.PasswordResetView` | `registration/password_reset_email.html`, `registration/password_reset_form.html` |
| `password_reset_done`<br>`/users/password-reset/done/` | `auth_reset_done` | `django.contrib.auth.views.PasswordResetDoneView` | `registration/password_reset_done.html` |
| `password_reset_confirm`<br>`/users/password-reset-confirm/<uidb64>/<token>/` | `auth_reset_confirm` | `django.contrib.auth.views.PasswordResetConfirmView` | `registration/password_reset_confirm.html` |
| `password_reset_complete`<br>`/users/password-reset-complete/` | `auth_reset_complete` | `django.contrib.auth.views.PasswordResetCompleteView` | `registration/password_reset_complete.html` |
| `profile`<br>`/users/profile/` | `profile` | `users.views.UserProfileView` | `users/profile.html` |
| `settings_account`<br>`/users/settings/hisob/` | `settings_account` | `users.views.SettingsAccountView` | `users/settings/account.html` |
| `settings_privacy`<br>`/users/settings/maxfiylik/` | `settings_privacy` | `users.views.AIMemoryListView` | `users/settings/privacy.html` |
| `settings_billing`<br>`/users/settings/tolov/` | `settings_billing` | `users.views.SettingsBillingView` | `users/settings/billing.html` |
| `settings_capabilities`<br>`/users/settings/imkoniyatlar/` | `settings_capabilities` | `users.views.SettingsCapabilitiesView` | `users/settings/capabilities.html` |

## I6

Kutubxona, kurs va dars editorlari. Barcha qatorlar: **NOT PORTED**.

| Real URL nomi / pattern | Preview IDlari | Canonical callback | Existing template hint |
|---|---|---|---|
| `backoffice_courses`<br>`/backoffice/courses/` | `course_list` | `core.views.backoffice_courses` | `backoffice/courses.html` |
| `backoffice_course_create`<br>`/backoffice/courses/new/` | `course_new` | `core.views.backoffice_course_editor` | `backoffice/course_form.html` |
| `backoffice_course_edit`<br>`/backoffice/courses/<int:course_id>/` | `course_edit_1`, `course_edit_2`, `course_edit_3`, `course_edit_4` | `core.views.backoffice_course_editor` | `backoffice/course_form.html` |
| `backoffice_lessons`<br>`/backoffice/lessons/` | `lesson_index` | `core.views.backoffice_lesson_editor` | `backoffice/lesson_form.html` |
| `backoffice_lesson_edit`<br>`/backoffice/lessons/<int:lesson_id>/` | `lesson_edit_3`, `lesson_edit_81` | `core.views.backoffice_lesson_editor` | `backoffice/lesson_form.html` |
| `library_backoffice:resources`<br>`/backoffice/library/` | `library_index` | `library.backoffice_views.resource_list` | `backoffice/library_list.html` |
| `library_backoffice:resource_create`<br>`/backoffice/library/new/` | `library_new` | `library.backoffice_views.resource_editor` | `backoffice/library_form.html` |
| `library_backoffice:resource_edit`<br>`/backoffice/library/<int:resource_id>/` | `library_detail_41`, `library_detail_42`, `library_detail_43`, `library_detail_46`, `library_detail_47`, `library_detail_48`, `library_detail_49`, `library_detail_50` | `library.backoffice_views.resource_editor` | `backoffice/library_form.html` |
| `library_backoffice:lesson_picker`<br>`/backoffice/library/lessons/<int:lesson_id>/pick/` | `library_picker_3`, `library_picker_81` | `library.backoffice_views.lesson_picker` | `backoffice/library_picker.html` |

## I7

Checkout va to‘lov holati. Barcha qatorlar: **NOT PORTED**.

| Real URL nomi / pattern | Preview IDlari | Canonical callback | Existing template hint |
|---|---|---|---|
| `cohorts:checkout`<br>`/checkout/course/<int:course_id>/` | `checkout`, `checkout_enrollment` | `cohorts.views.checkout_view` | `cohorts/checkout.html` |
| `cohorts:checkout_pending`<br>`/checkout/receipt/<int:receipt_id>/pending/` | `payment_pending` | `cohorts.views.checkout_pending_view` | `cohorts/checkout_pending.html` |
| `cohorts:checkout_success`<br>`/checkout/receipt/<int:receipt_id>/success/` | `payment_success` | `cohorts.views.checkout_success_view` | `cohorts/checkout_success.html` |

## I8

Imtihon va ustoz review. Barcha qatorlar: **NOT PORTED**.

| Real URL nomi / pattern | Preview IDlari | Canonical callback | Existing template hint |
|---|---|---|---|
| `teacher_grade_exam`<br>`/teacher/grading/exam/<int:attempt_id>/` | `teacher_exam_review` | `core.teacher_views.teacher_grade_exam` | `teacher/grade_exam.html` |
| `exam_center`<br>`/courses/exams/` | `exam_center` | `courses.views.ExamCenterView` | `courses/exam_center.html` |
| `exam_detail`<br>`/courses/<int:course_id>/exam/<int:exam_id>/` | `exam_detail` | `courses.views.ExamDetailView` | `courses/exam_detail.html` |
| `exam_result`<br>`/courses/<int:course_id>/exam/<int:exam_id>/result/` | `exam_result` | `courses.views.ExamResultView` | `courses/exam_result.html` |

## I9

Classbook va jonli mashg‘ulot. Barcha qatorlar: **NOT PORTED**.

| Real URL nomi / pattern | Preview IDlari | Canonical callback | Existing template hint |
|---|---|---|---|
| `classbook:teacher_home`<br>`/classbook/teacher/` | `classbook_home` | `classbook.views.teacher_home` | `classbook/teacher_home.html` |
| `classbook:exercise_list`<br>`/classbook/teacher/exercises/` | `classbook_exercises` | `classbook.views.exercise_list` | `classbook/exercise_list.html` |
| `classbook:playbook_edit`<br>`/classbook/teacher/playbook/<int:cohort_id>/<int:lesson_id>/` | `classbook_playbook_3_3`, `classbook_playbook_8_81`, `classbook_playbook_9_81` | `classbook.views.playbook_edit` | `classbook/playbook_form.html` |
| `classbook:teacher_session`<br>`/classbook/teacher/session/<int:session_id>/` | `classbook_session_8`, `teacher` | `classbook.views.teacher_session` | `classbook/teacher_session.html` |
| `classbook:live_home`<br>`/classbook/live/` | `classbook_live_home` | `classbook.views.live_home` | `classbook/live_home.html` |
| `classbook:live_session`<br>`/classbook/live/<int:session_id>/` | `classbook_live_session_8`, `live` | `classbook.views.live_session` | `classbook/live_session.html` |
| `classbook:live_activity`<br>`/classbook/live/activity/<int:activity_id>/` | `classbook_live_activity` | `classbook.views.live_activity` | `classbook/live_activity.html` |
| `classbook:activity_result`<br>`/classbook/live/activity/<int:activity_id>/result/` | `classbook_live_result` | `classbook.views.activity_result` | `classbook/activity_result.html` |
| `classbook:teacher_activity_result`<br>`/classbook/teacher/activity/<int:activity_id>/results/` | `classbook_teacher_activity_result` | `classbook.views.teacher_activity_result` | `classbook/teacher_activity_result.html` |
| `classbook:exercise_create`<br>`/classbook/teacher/exercises/new/` | `classbook_exercise_new` | `classbook.views.exercise_edit` | `classbook/exercise_form.html` |
| `classbook:exercise_edit`<br>`/classbook/teacher/exercises/<int:exercise_id>/` | `classbook_exercise_edit` | `classbook.views.exercise_edit` | `classbook/exercise_form.html` |

## Birinchi oqimda UI soniga kirmaydigan zarur contractlar

| Contract | Real source / endpoint | Saqlanishi shart |
|---|---|---|
| Login/logout | `users/urls.py`, `registration/login.html`, `logout` URL | Safe next, CSRF, POST logout, role menu |
| Dashboard/kurslarim | `users.views.DashboardView`, `users.views.MyCoursesView` | Faqat joriy user enrollmentlari; ko‘p/yo‘q enrollment; canonical progress |
| Lesson GET/context | `courses.views.LessonDetailView` | Real Lesson, active enrollment/cohort, locked redirect, haqiqiy tablar |
| Teacher release POST | `core.teacher_views.teacher_release` → `set_lesson_release` | Aniq course/cohort/lesson/action; invalid context boshqa guruhga yozmaydi |
| Material GET | `library:material_file` → `library.views.material_file` | `library.services.student_can_open`: link + enrollment + lesson access; direct URL ham gate |
| Completion | `lesson_completion` → `courses.views.lesson_completion_view` | Canonical completion/XP; takror bosish yangi ball yaratmasin |
| Assignment/quiz | `assignment_submit`, `api_quiz_submit`, `submission_file` | I2da existing behavior saqlansin; I3da yangi UI bilan locked write/file regression |
| Rollback | `core/flags.py` registri + existing control | V1 flag default OFF; flag faqat renderer tanlaydi, permission emas |

Loginning actual template/class adapteri I1da source bilan yana tekshiriladi;
bu jadval live backend execution dalili emas. Private storage/public cache,
cookie/session va hashed static tekshiruvi staging release gate’ida ham bor.

## Named prototipi yo‘q 44 UI/alias

**Saqlab turiladigan legacy yuzalar**, jimgina scope’dan chiqarilmaydi.
Umumiy D23 qamrovi qoladi; D30 bilan yangi prototiplar vaqtincha pauzada.
Qxx — avvalgi prototype ish oilasi, Ixx bilan aralashtirilmaydi.

| Q oilasi | Real URL nomi | Pattern | Canonical callback |
|---|---|---|---|
| Q05 | `messenger:index` | `/messenger/` | `messenger.views.MessengerAIView` |
| Q07 | `cohorts:checkout_success_latest` | `/checkout/success/` | `cohorts.views.checkout_success_view` |
| Q08 | `attendance_manage` | `/users/attendance/manage/` | `users.views.AttendanceManageView` |
| Q14 | `backoffice_exam_edit` | `/backoffice/exams/<int:exam_id>/` | `core.views.backoffice_exam_editor` |
| Q14 | `backoffice_exams` | `/backoffice/exams/` | `core.views.backoffice_exam_editor` |
| Q15 | `backoffice_catalog` | `/backoffice/catalog/` | `subscriptions.backoffice_views.catalog` |
| Q15 | `backoffice_chats` | `/backoffice/chats/` | `core.views.backoffice_chats` |
| Q15 | `backoffice_cohort_create` | `/backoffice/catalog/cohorts/new/` | `subscriptions.backoffice_views.cohort_editor` |
| Q15 | `backoffice_cohort_edit` | `/backoffice/catalog/cohorts/<int:cohort_id>/` | `subscriptions.backoffice_views.cohort_editor` |
| Q15 | `backoffice_cohort_members` | `/backoffice/catalog/cohorts/<int:cohort_id>/members/` | `subscriptions.backoffice_views.cohort_members` |
| Q15 | `backoffice_dashboard` | `/backoffice/` | `core.views.backoffice_dashboard` |
| Q15 | `backoffice_plan_edit` | `/backoffice/catalog/plans/<int:plan_id>/` | `subscriptions.backoffice_views.plan_editor` |
| Q15 | `backoffice_receipts` | `/backoffice/receipts/` | `core.views.backoffice_receipts` |
| Q15 | `backoffice_users` | `/backoffice/users/` | `core.views.backoffice_users` |
| Q16 | `backoffice_ai_circuit_reset` | `/backoffice/control/ai-circuit-reset/` | `core.views.backoffice_ai_circuit_reset` |
| Q16 | `backoffice_ai_control` | `/backoffice/ai-control/` | `core.views.backoffice_ai_control` |
| Q16 | `backoffice_ai_cost` | `/backoffice/control/ai-cost/` | `core.views.backoffice_ai_cost` |
| Q16 | `backoffice_ai_kill_switch` | `/backoffice/control/ai-kill-switch/` | `core.views.backoffice_ai_kill_switch` |
| Q16 | `backoffice_brand` | `/backoffice/control/brand/` | `core.views.backoffice_brand` |
| Q16 | `backoffice_control` | `/backoffice/control/` | `core.views.backoffice_control` |
| Q16 | `backoffice_dead_letter` | `/backoffice/control/dead-letter/` | `core.views.backoffice_dead_letter` |
| Q16 | `backoffice_feature_flags` | `/backoffice/control/flags/` | `core.views.backoffice_feature_flags` |
| Q16 | `backoffice_landing` | `/backoffice/landing/` | `core.views.backoffice_landing` |
| Q16 | `backoffice_runtime_settings` | `/backoffice/control/runtime-settings/` | `core.views.backoffice_runtime_settings` |
| Q17 | `blog:studio` | `/blog/studio/` | `blog.views.BlogStudioView` |
| Q17 | `blog:studio_create` | `/blog/studio/new/` | `blog.views.BlogPostCreateView` |
| Q17 | `blog:studio_edit` | `/blog/studio/<slug:slug>/edit/` | `blog.views.BlogPostUpdateView` |
| Q17 | `sit_backoffice:announcement_create` | `/backoffice/sit/announcements/new/` | `sit.backoffice_views.announcement_editor` |
| Q17 | `sit_backoffice:announcement_edit` | `/backoffice/sit/announcements/<int:announcement_id>/` | `sit.backoffice_views.announcement_editor` |
| Q17 | `sit_backoffice:announcements` | `/backoffice/sit/announcements/` | `sit.backoffice_views.announcement_list` |
| Q17 | `sit_backoffice:dashboard` | `/backoffice/sit/` | `sit.backoffice_views.dashboard` |
| Q17 | `sit_backoffice:guide_create` | `/backoffice/sit/guides/new/` | `sit.backoffice_views.guide_editor` |
| Q17 | `sit_backoffice:guide_edit` | `/backoffice/sit/guides/<int:guide_id>/` | `sit.backoffice_views.guide_editor` |
| Q17 | `sit_backoffice:guides` | `/backoffice/sit/guides/` | `sit.backoffice_views.guide_list` |
| Q17 | `sit_backoffice:universities` | `/backoffice/sit/universities/` | `sit.backoffice_views.university_list` |
| Q17 | `sit_backoffice:university_create` | `/backoffice/sit/universities/new/` | `sit.backoffice_views.university_editor` |
| Q17 | `sit_backoffice:university_edit` | `/backoffice/sit/universities/<int:university_id>/` | `sit.backoffice_views.university_editor` |
| Q18 | `bot:miniapp_ai` | `/bot/miniapp/ai/` | `bot.views.miniapp_ai` |
| Q18 | `bot:miniapp_courses` | `/bot/miniapp/courses/` | `bot.views.miniapp_courses` |
| Q18 | `bot:miniapp_entry` | `/bot/miniapp/` | `bot.views.miniapp_entry` |
| Q18 | `bot:miniapp_home` | `/bot/miniapp/home/` | `bot.views.miniapp_home` |
| Q18 | `bot:miniapp_profile` | `/bot/miniapp/profile/` | `bot.views.miniapp_profile` |
| Q19 | `maintenance` | `/maintenance/` | `core.views.maintenance` |
| Q19 | `offline` | `/offline/` | `core.views.offline` |

Admin mount, xato/offline handlerlar va helper endpointlar inventarda alohida:
“named prototipi yo‘q” degani endpointni o‘chirish yoki unga 404 berish emas.
Ko‘chmagan UIga valid legacy navigatsiya saqlanadi.

## Dalil va yangilash usuli

- Lokal `playground/Eleventh Trial/prototype/contracts/registry.json`ning
  95 qatori joriy nomlari bilan qayta solishtirildi; eski Q01ning 44 preview
  crosswalk ro‘yxati tayyorlik hisobi sifatida qayta ishlatilmadi.
- Lokal `playground/Eleventh Trial/evidence/q01-runtime-map.json` 197 leaf,
  source commit bilan mos; SCREEN/SCREEN_ALIAS filtrida 120 qator.
- 95 qatorning barchasi paketga bir marta ajratildi; 76 noyob URL nomining
  har biri source UIga aniq bitta moslik berdi; 44 nom unmatched.
- Callback/template ma’lumoti source/loader hint, permission/render/browser
  PASS emas. Har paket boshlanganda tegishli actual view/form/service va
  templates qayta o‘qiladi. Runtime source o‘zgarsa xarita yangilanadi.
- Bir bo‘lak tugagach faqat unga tegishli status, adapter/read-write mapping,
  test/browser va commit/PR/release dalili `PORT-LEDGER.md`ga yoziladi.
  Qolgan bo‘laklarning statusi taxminan ko‘tarilmaydi.
