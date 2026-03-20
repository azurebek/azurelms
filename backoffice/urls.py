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
    path("content/legal/", views.BackofficeLegalPagesView.as_view(), name="legal_pages"),
    path("content/legal/<int:page_id>/", views.BackofficeLegalPageDetailView.as_view(), name="legal_page_detail"),
    path("content/blog-posts/", views.BackofficeBlogPostsView.as_view(), name="blog_posts"),
    path("content/blog-comments/", views.BackofficeBlogCommentsView.as_view(), name="blog_comments"),
]
