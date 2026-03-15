from django.urls import path

from .views import (
    BlogCommentCreateView,
    BlogCommentLikeToggleView,
    BlogDetailView,
    BlogListView,
    BlogPostClapView,
    BlogPostCreateView,
    BlogPostUpdateView,
    BlogStudioView,
)

app_name = "blog"

urlpatterns = [
    path("", BlogListView.as_view(), name="list"),
    path("studio/", BlogStudioView.as_view(), name="studio"),
    path("studio/new/", BlogPostCreateView.as_view(), name="studio_create"),
    path("studio/<slug:slug>/edit/", BlogPostUpdateView.as_view(), name="studio_edit"),
    path("<slug:slug>/", BlogDetailView.as_view(), name="detail"),
    path("<slug:slug>/clap/", BlogPostClapView.as_view(), name="clap"),
    path("<slug:slug>/comment/", BlogCommentCreateView.as_view(), name="comment_create"),
    path("comments/<int:comment_id>/like/", BlogCommentLikeToggleView.as_view(), name="comment_like"),
]
