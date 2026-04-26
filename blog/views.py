from urllib.parse import quote

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db import IntegrityError, transaction
from django.db.models import Count, F, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, TemplateView, UpdateView

from .forms import BlogCommentForm, BlogPostForm
from .models import BlogComment, BlogCommentLike, BlogHomeSettings, BlogPost, BlogPostClap, BlogPostRead, BlogTag
from .utils import build_ip_hash, ensure_visitor_token, is_probable_bot, set_visitor_cookie, viewer_key_for_request


class BlogStaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    login_url = reverse_lazy("login")

    def test_func(self):
        user = self.request.user
        return user.is_staff or user.is_superuser


class BlogListView(ListView):
    template_name = "blog/post_list.html"
    context_object_name = "posts"
    paginate_by = 9

    def get_queryset(self):
        self.base_queryset = (
            BlogPost.objects.published()
            .select_related("author")
            .prefetch_related("tags")
            .order_by("-featured", "-published_at", "-created_at")
        )
        queryset = self.base_queryset
        self.search_query = self.request.GET.get("q", "").strip()
        self.active_tag = self.request.GET.get("tag", "").strip()
        self.featured_post = None

        if self.search_query:
            queryset = queryset.filter(
                Q(title__icontains=self.search_query)
                | Q(excerpt__icontains=self.search_query)
                | Q(body__icontains=self.search_query)
                | Q(tags__name__icontains=self.search_query)
            ).distinct()

        if self.active_tag:
            queryset = queryset.filter(tags__slug=self.active_tag)

        if not self.search_query and not self.active_tag:
            self.featured_post = queryset.filter(featured=True).first()
            if self.featured_post:
                queryset = queryset.exclude(pk=self.featured_post.pk)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        published_filter = Q(posts__status=BlogPost.STATUS_PUBLISHED, posts__published_at__lte=timezone.now())
        landing_settings = BlogHomeSettings.load()
        carousel_posts = list(
            BlogPost.objects.published()
            .select_related("author")
            .prefetch_related("tags")
            .order_by("-featured", "-published_at", "-created_at")[:5]
        )

        for index, post in enumerate(carousel_posts):
            post.carousel_active = index == 0

        context["landing_settings"] = landing_settings
        context["carousel_posts"] = carousel_posts
        context["featured_post"] = self.featured_post
        context["search_query"] = self.search_query
        context["active_tag"] = self.active_tag
        context["top_tags"] = BlogTag.objects.annotate(post_total=Count("posts", filter=published_filter)).filter(
            post_total__gt=0
        )[:8]
        return context


class BlogDetailView(DetailView):
    template_name = "blog/post_detail.html"
    context_object_name = "post"

    def get_queryset(self):
        queryset = BlogPost.objects.select_related("author").prefetch_related("tags")
        if self.request.GET.get("preview") == "1" and self.request.user.is_authenticated:
            if self.request.user.is_superuser or self.request.user.is_staff:
                self.is_preview = True
                return queryset
        self.is_preview = False
        return queryset.published()

    def _register_view(self, post, viewer_key):
        user_agent = (self.request.META.get("HTTP_USER_AGENT") or "")[:255]
        if self.is_preview or is_probable_bot(user_agent):
            return

        defaults = {
            "user": self.request.user if self.request.user.is_authenticated else None,
            "ip_hash": build_ip_hash(self.request),
            "user_agent": user_agent,
        }
        try:
            with transaction.atomic():
                _, created = BlogPostRead.objects.get_or_create(
                    post=post,
                    viewer_key=viewer_key,
                    defaults=defaults,
                )
                if created:
                    BlogPost.objects.filter(pk=post.pk).update(view_count=F("view_count") + 1)
        except IntegrityError:
            return

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.visitor_token, cookie_created = ensure_visitor_token(request)
        viewer_key = viewer_key_for_request(request, self.visitor_token)
        self._register_view(self.object, viewer_key)

        context = self.get_context_data(object=self.object)
        response = self.render_to_response(context)
        if cookie_created:
            set_visitor_cookie(response, self.visitor_token)
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        post = self.object
        request = self.request
        share_url = request.build_absolute_uri(post.get_absolute_url())
        share_text = f"{post.share_title} - {post.share_description}"
        viewer_key = viewer_key_for_request(request, getattr(self, "visitor_token", request.COOKIES.get("blog_visitor", "")))

        comments = list(
            BlogComment.objects.filter(post=post, is_deleted=False)
            .select_related("user", "parent")
            .order_by("created_at")
        )
        liked_comment_ids = set()
        if request.user.is_authenticated:
            liked_comment_ids = set(
                BlogCommentLike.objects.filter(user=request.user, comment__post=post).values_list("comment_id", flat=True)
            )

        comment_map = {}
        for comment in comments:
            comment.reply_items = []
            comment.is_liked_by_user = comment.id in liked_comment_ids
            comment_map[comment.id] = comment

        root_comments = []
        for comment in comments:
            if comment.parent_id and comment.parent_id in comment_map:
                comment_map[comment.parent_id].reply_items.append(comment)
            elif not comment.parent_id:
                root_comments.append(comment)

        my_clap_count = (
            BlogPostClap.objects.filter(post=post, viewer_key=viewer_key).values_list("clap_count", flat=True).first() or 0
        )

        context["is_preview"] = self.is_preview
        context["comment_form"] = BlogCommentForm()
        context["root_comments"] = root_comments
        context["comments_total"] = len(comments)
        context["my_clap_count"] = my_clap_count
        context["share_url"] = share_url
        context["share_text"] = share_text
        context["telegram_share_url"] = (
            f"https://t.me/share/url?url={quote(share_url)}&text={quote(post.share_title)}"
        )
        context["x_share_url"] = f"https://twitter.com/intent/tweet?url={quote(share_url)}&text={quote(share_text)}"
        context["linkedin_share_url"] = f"https://www.linkedin.com/sharing/share-offsite/?url={quote(share_url)}"
        context["facebook_share_url"] = f"https://www.facebook.com/sharer/sharer.php?u={quote(share_url)}"
        context["related_posts"] = (
            BlogPost.objects.published()
            .filter(Q(tags__in=post.tags.all()) | Q(author=post.author))
            .exclude(pk=post.pk)
            .select_related("author")
            .prefetch_related("tags")
            .distinct()[:3]
        )
        return context


class BlogStudioView(BlogStaffRequiredMixin, TemplateView):
    template_name = "blog/studio_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        posts = BlogPost.objects.select_related("author").prefetch_related("tags")
        if not self.request.user.is_superuser:
            posts = posts.filter(author=self.request.user)

        context["posts"] = posts.order_by("-updated_at")
        context["draft_count"] = posts.filter(status=BlogPost.STATUS_DRAFT).count()
        context["published_count"] = posts.filter(status=BlogPost.STATUS_PUBLISHED).count()
        return context


class BlogPostCreateView(BlogStaffRequiredMixin, CreateView):
    model = BlogPost
    form_class = BlogPostForm
    template_name = "blog/studio_form.html"

    def form_valid(self, form):
        form.instance.author = self.request.user
        messages.success(self.request, "Blog posti saqlandi.")
        return super().form_valid(form)

    def get_success_url(self):
        if self.object.is_live:
            return self.object.get_absolute_url()
        return reverse("blog:studio_edit", kwargs={"slug": self.object.slug})


class BlogPostUpdateView(BlogStaffRequiredMixin, UpdateView):
    model = BlogPost
    form_class = BlogPostForm
    template_name = "blog/studio_form.html"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        queryset = BlogPost.objects.select_related("author").prefetch_related("tags")
        if self.request.user.is_superuser:
            return queryset
        return queryset.filter(author=self.request.user)

    def form_valid(self, form):
        messages.success(self.request, "Blog posti yangilandi.")
        return super().form_valid(form)

    def get_success_url(self):
        if self.object.is_live:
            return self.object.get_absolute_url()
        return reverse("blog:studio_edit", kwargs={"slug": self.object.slug})


class BlogPostClapView(View):
    def post(self, request, slug):
        post = get_object_or_404(BlogPost.objects.published(), slug=slug)
        visitor_token, cookie_created = ensure_visitor_token(request)
        viewer_key = viewer_key_for_request(request, visitor_token)

        with transaction.atomic():
            clap, _ = BlogPostClap.objects.get_or_create(
                post=post,
                viewer_key=viewer_key,
                defaults={"user": request.user if request.user.is_authenticated else None},
            )
            added = clap.add_clap()

        post.refresh_from_db(fields=["clap_count"])
        response = JsonResponse(
            {
                "ok": True,
                "added": added,
                "clap_count": post.clap_count,
                "my_clap_count": clap.clap_count,
            }
        )
        if cookie_created:
            set_visitor_cookie(response, visitor_token)
        return response


class BlogCommentCreateView(LoginRequiredMixin, View):
    login_url = reverse_lazy("login")

    def post(self, request, slug):
        post = get_object_or_404(BlogPost.objects.published(), slug=slug)
        if not post.allow_comments:
            messages.error(request, "Bu post uchun kommentlar vaqtincha yopilgan.")
            return redirect(f"{post.get_absolute_url()}#comments")

        form = BlogCommentForm(request.POST)
        if not form.is_valid():
            messages.error(request, "Kommentni yuborishda xatolik bo'ldi.")
            return redirect(f"{post.get_absolute_url()}#comments")

        parent = None
        parent_id = request.POST.get("parent_id")
        if parent_id:
            parent = get_object_or_404(BlogComment, pk=parent_id, post=post, is_deleted=False)

        comment = form.save(commit=False)
        comment.post = post
        comment.user = request.user
        comment.parent = parent
        comment.full_clean()
        comment.save()
        BlogPost.objects.filter(pk=post.pk).update(comment_count=F("comment_count") + 1)
        messages.success(request, "Komment joylandi.")
        return redirect(f"{post.get_absolute_url()}#comment-{comment.pk}")


class BlogCommentLikeToggleView(View):
    def post(self, request, comment_id):
        if not request.user.is_authenticated:
            return JsonResponse({"ok": False, "error": "auth_required", "login_url": reverse("login")}, status=403)

        comment = get_object_or_404(
            BlogComment.objects.select_related("post"),
            pk=comment_id,
            is_deleted=False,
            post__status=BlogPost.STATUS_PUBLISHED,
            post__published_at__lte=timezone.now(),
        )

        with transaction.atomic():
            like, created = BlogCommentLike.objects.get_or_create(comment=comment, user=request.user)
            if created:
                BlogComment.objects.filter(pk=comment.pk).update(like_count=F("like_count") + 1)
                liked = True
            else:
                like.delete()
                BlogComment.objects.filter(pk=comment.pk, like_count__gt=0).update(like_count=F("like_count") - 1)
                liked = False

        comment.refresh_from_db(fields=["like_count"])
        return JsonResponse({"ok": True, "liked": liked, "like_count": comment.like_count})
