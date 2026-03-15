from django.contrib import admin

from .models import BlogComment, BlogCommentLike, BlogHomeSettings, BlogPost, BlogPostClap, BlogPostRead, BlogTag


@admin.register(BlogHomeSettings)
class BlogHomeSettingsAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return not BlogHomeSettings.objects.exists()


@admin.register(BlogTag)
class BlogTagAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name",)


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "status", "featured", "published_at", "view_count", "clap_count")
    list_filter = ("status", "featured", "allow_comments", "tags")
    search_fields = ("title", "excerpt", "body", "author__username", "author__first_name", "author__last_name")
    readonly_fields = ("view_count", "clap_count", "comment_count", "reading_time_minutes", "created_at", "updated_at")
    filter_horizontal = ("tags",)


@admin.register(BlogComment)
class BlogCommentAdmin(admin.ModelAdmin):
    list_display = ("post", "user", "parent", "like_count", "created_at")
    list_filter = ("created_at",)
    search_fields = ("content", "user__username", "user__first_name", "user__last_name", "post__title")
    readonly_fields = ("like_count", "created_at", "updated_at")


@admin.register(BlogCommentLike)
class BlogCommentLikeAdmin(admin.ModelAdmin):
    list_display = ("comment", "user", "created_at")
    search_fields = ("user__username", "comment__content")


@admin.register(BlogPostRead)
class BlogPostReadAdmin(admin.ModelAdmin):
    list_display = ("post", "viewer_key", "user", "first_seen_at", "last_seen_at")
    search_fields = ("post__title", "viewer_key", "user__username")
    readonly_fields = ("first_seen_at", "last_seen_at")


@admin.register(BlogPostClap)
class BlogPostClapAdmin(admin.ModelAdmin):
    list_display = ("post", "viewer_key", "user", "clap_count", "updated_at")
    search_fields = ("post__title", "viewer_key", "user__username")
