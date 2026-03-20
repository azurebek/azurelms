from django.urls import path

from . import views


app_name = "backoffice"

urlpatterns = [
    path("", views.BackofficeDashboardView.as_view(), name="dashboard"),
    path("students/", views.BackofficeStudentsView.as_view(), name="students"),
    path("users/", views.BackofficeUsersView.as_view(), name="users"),
    path("users/<int:user_id>/", views.BackofficeUserDetailView.as_view(), name="user_detail"),
    path("subscriptions/", views.BackofficeSubscriptionsView.as_view(), name="subscriptions"),
    path("subscriptions/<int:plan_id>/", views.BackofficeSubscriptionPlanDetailView.as_view(), name="subscription_plan_detail"),
    path("payments/", views.BackofficePaymentsView.as_view(), name="payments"),
    path("cohorts/", views.BackofficeCohortsView.as_view(), name="cohorts"),
    path("attendance/", views.BackofficeAttendanceView.as_view(), name="attendance"),
    path("notifications/", views.BackofficeNotificationsView.as_view(), name="notifications"),
    path("learning/assignments/", views.BackofficeLearningAssignmentsView.as_view(), name="learning_assignments"),
    path("learning/releases/", views.BackofficeLearningReleasesView.as_view(), name="learning_releases"),
    path("learning/exams/", views.BackofficeLearningExamsView.as_view(), name="learning_exams"),
    path("content/settings/", views.BackofficeContentSettingsView.as_view(), name="content_settings"),
    path("content/landing/", views.BackofficeLandingPageView.as_view(), name="content_landing_page"),
    path("content/landing/blocks/", views.BackofficeLandingBlocksView.as_view(), name="content_landing_blocks"),
    path(
        "content/landing/testimonials/<int:testimonial_id>/",
        views.BackofficeLandingTestimonialDetailView.as_view(),
        name="content_testimonial_detail",
    ),
    path("content/about/", views.BackofficeAboutPageView.as_view(), name="content_about_page"),
    path("content/about/blocks/", views.BackofficeAboutBlocksView.as_view(), name="content_about_blocks"),
    path(
        "content/about/team/<int:member_id>/",
        views.BackofficeTeamMemberDetailView.as_view(),
        name="content_team_member_detail",
    ),
    path("content/landing-nav/", views.BackofficeLandingNavItemsView.as_view(), name="content_landing_nav"),
    path("content/blog-home/", views.BackofficeBlogHomeSettingsView.as_view(), name="content_blog_home"),
    path("content/blog-tags/", views.BackofficeBlogTagsView.as_view(), name="content_blog_tags"),
    path("content/blog-signals/", views.BackofficeBlogSignalsView.as_view(), name="content_blog_signals"),
    path("content/legal/", views.BackofficeLegalPagesView.as_view(), name="legal_pages"),
    path("content/legal/<int:page_id>/", views.BackofficeLegalPageDetailView.as_view(), name="legal_page_detail"),
    path("content/blog-posts/", views.BackofficeBlogPostsView.as_view(), name="blog_posts"),
    path("content/blog-comments/", views.BackofficeBlogCommentsView.as_view(), name="blog_comments"),
]
