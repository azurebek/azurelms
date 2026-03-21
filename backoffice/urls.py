from django.urls import path

from . import views


app_name = "backoffice"

urlpatterns = [
    path("login/", views.BackofficeLoginView.as_view(), name="login"),
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
    path("learning/courses/", views.BackofficeCoursesCatalogView.as_view(), name="courses_catalog"),
    path("learning/courses/<int:course_id>/", views.BackofficeCourseStructureView.as_view(), name="course_structure"),
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
    path("messenger/rooms/", views.BackofficeMessengerRoomsView.as_view(), name="messenger_rooms"),
    path("messenger/rooms/<int:room_id>/", views.BackofficeMessengerRoomDetailView.as_view(), name="messenger_room_detail"),
    path("messenger/messages/", views.BackofficeMessengerMessagesView.as_view(), name="messenger_messages"),
    path("messenger/rag-chunks/", views.BackofficeMessengerRAGChunksView.as_view(), name="messenger_rag_chunks"),
    path("gamification/levels/", views.BackofficeGamificationLevelsView.as_view(), name="gamification_levels"),
    path("gamification/badges/", views.BackofficeGamificationBadgesView.as_view(), name="gamification_badges"),
    path(
        "gamification/badges/<int:badge_id>/",
        views.BackofficeGamificationBadgeDetailView.as_view(),
        name="gamification_badge_detail",
    ),
    path(
        "gamification/earned-badges/",
        views.BackofficeGamificationEarnedBadgesView.as_view(),
        name="gamification_earned_badges",
    ),
    path(
        "gamification/certificates/",
        views.BackofficeGamificationCertificatesView.as_view(),
        name="gamification_certificates",
    ),
]
