from urllib.parse import quote
from core.flags import flag_enabled
from frontend.public_meta import absolute_url
from frontend.public_query import MAX_QUERY_CHARS, pagination_context
from frontend.public_v1 import PublicFrontendV1Mixin, safe_return_to

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db import IntegrityError, transaction
from django.db.models import Avg, F, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, TemplateView, UpdateView

from . import listing
from .forms import BlogCommentForm, BlogPostForm
from .models import BlogComment, BlogCommentLike, BlogHomeSettings, BlogPost, BlogPostClap, BlogPostRead
from .utils import forget_legacy_visitor_cookie, is_probable_bot, reader_key


class BlogStaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    login_url = reverse_lazy("login")

    def test_func(self):
        user = self.request.user
        return user.is_staff or user.is_superuser


def _return_to(url):
    """Toza ro'yxat manziliga qaytish havolaga qo'shilmaydi (`?return_to=/blog/` ortiqcha)."""
    return "" if url == reverse("blog:list") else url


class BlogListView(PublicFrontendV1Mixin, ListView):
    """Ochiq Blog ro'yxati: chegaralangan qidiruv, barqaror tartib, toza havolalar (PUB1.6a)."""

    template_name = "blog/post_list.html"
    context_object_name = "posts"
    paginate_by = 9

    def get_queryset(self):
        self.query = listing.BlogListQuery.from_params(self.request.GET)
        queryset = listing.list_queryset(self.query)
        self.featured_post = None
        if not self.query.is_filtered:
            self.featured_post = queryset.filter(featured=True).first()
            if self.featured_post:
                queryset = queryset.exclude(pk=self.featured_post.pk)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query, page_obj = self.query, context["page_obj"]
        tags = listing.top_tags()
        context.update(
            landing_settings=BlogHomeSettings.current(),
            featured_post=self.featured_post,
            blog_query=query,
            search_query=query.q,
            active_tag=query.tag,
            max_query_chars=MAX_QUERY_CHARS,
            top_tags=tags,
            tag_links=[
                {"name": tag.name, "slug": tag.slug, "url": query.url(tag=tag.slug), "current": tag.slug == query.tag}
                for tag in tags
            ],
            all_tags_url=query.url(tag=""),
            # Maqoladagi "Blogga qaytish" ayni qidiruv, teg va sahifaga qaytaradi.
            blog_return_to=_return_to(query.url(page=page_obj.number)),
            pages_label="Maqolalar sahifalari",
            **pagination_context(page_obj, context["is_paginated"], lambda number: query.url(page=number)),
        )
        return context


class BlogDetailView(PublicFrontendV1Mixin, DetailView):
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

    def _register_view(self, post):
        # Anonim o'qish yozilmaydi; kirgan foydalanuvchi uchun faqat (maqola,
        # foydalanuvchi) - IP xeshi va user-agent saqlanmaydi (PUB1.0g, PUB-D6).
        viewer_key = reader_key(self.request)
        user_agent = self.request.META.get("HTTP_USER_AGENT") or ""
        if viewer_key is None or self.is_preview or is_probable_bot(user_agent):
            return
        try:
            with transaction.atomic():
                _, created = BlogPostRead.objects.get_or_create(
                    post=post,
                    viewer_key=viewer_key,
                    defaults={"user": self.request.user},
                )
                if created:
                    BlogPost.objects.filter(pk=post.pk).update(view_count=F("view_count") + 1)
        except IntegrityError:
            return

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        self._register_view(self.object)

        context = self.get_context_data(object=self.object)
        response = self.render_to_response(context)
        return forget_legacy_visitor_cookie(request, response)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        post = self.object
        request = self.request
        # Ulashish havolasi sozlangan domendan: so'rovdagi `Host` uni o'zgartira olmaydi (PUB1.1b).
        share_url = absolute_url(post.get_absolute_url())
        share_text = f"{post.share_title} - {post.share_description}"
        viewer_key = reader_key(request)

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
        ) if viewer_key else 0

        context["is_preview"] = self.is_preview
        # Ro'yxatdagi filtr va sahifaga qaytish — ikkala rendererda bir xil (PUB1.6a).
        context["public_back_url"] = safe_return_to(request, reverse("blog:list"))
        context["blog_return_to"] = _return_to(context["public_back_url"])
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
        context["related_posts"] = listing.related_posts(post)
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
        context["scheduled_posts"] = posts.filter(
            status=BlogPost.STATUS_PUBLISHED,
            published_at__gt=timezone.now(),
        ).order_by("published_at")[:4]
        totals = posts.aggregate(
            total_views=Sum("view_count"),
            total_claps=Sum("clap_count"),
            comment_total=Sum("comment_count"),
            avg_reading_time=Avg("reading_time_minutes"),
        )
        context["total_views"] = totals["total_views"] or 0
        context["total_claps"] = totals["total_claps"] or 0
        context["comment_total"] = totals["comment_total"] or 0
        context["avg_reading_time"] = round(totals["avg_reading_time"] or 1, 1)
        context["now"] = timezone.now()
        return context


class BlogStudioFormCopyMixin:
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["simple_copy"] = flag_enabled("backoffice_unified_navigation")
        return kwargs


class BlogPostCreateView(BlogStudioFormCopyMixin, BlogStaffRequiredMixin, CreateView):
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


class BlogPostUpdateView(BlogStudioFormCopyMixin, BlogStaffRequiredMixin, UpdateView):
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


def _wants_json(request):
    return "application/json" in request.headers.get("Accept", "") or (
        request.headers.get("X-Requested-With") == "XMLHttpRequest"
    )


def _is_page_form(request):
    """JavaScriptsiz brauzer formasi: sahifa (`text/html`) kutadi, JSON emas."""
    return "text/html" in request.headers.get("Accept", "") and not _wants_json(request)


class BlogPostClapView(View):
    def post(self, request, slug):
        post = get_object_or_404(BlogPost.objects.published(), slug=slug)
        viewer_key = reader_key(request)
        if viewer_key is None:
            # Anonim olqish bir yillik yashirin cookie yaratardi. PUB-D6 qarorigacha
            # olqish uchun kirish kerak (izoh va izohni yoqtirish kabi) (PUB1.0g).
            login_url = f"{reverse('login')}?next={quote(post.get_absolute_url())}"
            if _wants_json(request):
                return JsonResponse({"ok": False, "error": "auth_required", "login_url": login_url}, status=403)
            return redirect(login_url)

        with transaction.atomic():
            clap, _ = BlogPostClap.objects.get_or_create(
                post=post,
                viewer_key=viewer_key,
                defaults={"user": request.user},
            )
            added = clap.add_clap()

        if _is_page_form(request):
            # JavaScriptsiz forma (legacy) xom JSON sahifaga tushmaydi: maqolaga qaytadi (PUB1.6a).
            return forget_legacy_visitor_cookie(request, redirect(f"{post.get_absolute_url()}#clap"))
        post.refresh_from_db(fields=["clap_count"])
        response = JsonResponse(
            {
                "ok": True,
                "added": added,
                "clap_count": post.clap_count,
                "my_clap_count": clap.clap_count,
            }
        )
        return forget_legacy_visitor_cookie(request, response)


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
