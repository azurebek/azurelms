import math
import re
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F
from django.urls import reverse
from django.utils import timezone
from django.utils.html import strip_tags
from django.utils.text import slugify
from django_ckeditor_5.fields import CKEditor5Field

from core.utils import validate_file_size, validate_image_extension


def build_unique_slug(instance, source_value):
    base_slug = slugify(source_value or "")[:180] or uuid.uuid4().hex[:8]
    slug = base_slug
    suffix = 2
    model_class = type(instance)

    while model_class.objects.exclude(pk=instance.pk).filter(slug=slug).exists():
        suffix_text = f"-{suffix}"
        slug = f"{base_slug[: max(1, 180 - len(suffix_text))]}{suffix_text}"
        suffix += 1
    return slug


class SingletonModel(models.Model):
    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class BlogHomeSettings(SingletonModel):
    hero_kicker = models.CharField(max_length=80, default="Azure Journal")
    hero_title = models.CharField(
        max_length=220,
        default="Fikrlar, tajribalar va chuqur maqolalar uchun professional blog maydoni",
    )
    hero_description = models.TextField(
        default="Founder notes, product yozuvlari, til o'rganish bo'yicha kuzatuvlar va shaxsiy fikrlar uchun alohida jurnal."
    )
    search_label = models.CharField(max_length=80, default="Maqola qidirish")
    search_placeholder = models.CharField(max_length=140, default="Mavzu, tag yoki kalit so'z")
    carousel_kicker = models.CharField(max_length=80, default="Latest dispatches")
    carousel_title = models.CharField(max_length=140, default="Oxirgi postlar")
    stories_kicker = models.CharField(max_length=80, default="Stories")
    stories_title = models.CharField(max_length=140, default="Oxirgi maqolalar")
    stories_description = models.CharField(
        max_length=220,
        default="Har bir maqola cover, meta, preview va aniq o'qishga qulay kartochka bilan chiqadi.",
    )

    class Meta:
        verbose_name = "Blog bosh sahifa sozlamasi"
        verbose_name_plural = "Blog bosh sahifa sozlamalari"

    def __str__(self):
        return "Blog bosh sahifa sozlamalari"


class BlogTag(models.Model):
    name = models.CharField(max_length=60, unique=True)
    slug = models.SlugField(max_length=70, unique=True, blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Blog tegi"
        verbose_name_plural = "Blog teglari"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = build_unique_slug(self, self.name)
        super().save(*args, **kwargs)


class BlogPostQuerySet(models.QuerySet):
    def published(self):
        return self.filter(status=BlogPost.STATUS_PUBLISHED, published_at__lte=timezone.now())


class BlogPost(models.Model):
    STATUS_DRAFT = "draft"
    STATUS_PUBLISHED = "published"
    STATUS_CHOICES = (
        (STATUS_DRAFT, "Qoralama"),
        (STATUS_PUBLISHED, "Nashr etilgan"),
    )

    title = models.CharField(max_length=180)
    slug = models.SlugField(max_length=190, unique=True, blank=True)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="blog_posts",
    )
    cover_image = models.ImageField(
        upload_to="blog/covers/",
        blank=True,
        null=True,
        validators=[validate_file_size, validate_image_extension],
    )
    cover_alt_text = models.CharField(max_length=180, blank=True)
    excerpt = models.TextField(blank=True)
    featured_quote = models.CharField(max_length=220, blank=True)
    body = CKEditor5Field(config_name="default", verbose_name="Maqola matni")
    tags = models.ManyToManyField(BlogTag, blank=True, related_name="posts")
    featured = models.BooleanField(default=False)
    allow_comments = models.BooleanField(default=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    seo_title = models.CharField(max_length=180, blank=True)
    meta_description = models.CharField(max_length=320, blank=True)
    reading_time_minutes = models.PositiveSmallIntegerField(default=1, editable=False)
    view_count = models.PositiveIntegerField(default=0, editable=False)
    clap_count = models.PositiveIntegerField(default=0, editable=False)
    comment_count = models.PositiveIntegerField(default=0, editable=False)
    published_at = models.DateTimeField(blank=True, null=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = BlogPostQuerySet.as_manager()

    class Meta:
        ordering = ["-featured", "-published_at", "-created_at"]
        verbose_name = "Blog posti"
        verbose_name_plural = "Blog postlari"
        indexes = [
            models.Index(fields=["status", "published_at"]),
            models.Index(fields=["slug"]),
        ]

    def __str__(self):
        return self.title

    @property
    def plain_text(self):
        raw_text = strip_tags(self.body or "")
        return re.sub(r"\s+", " ", raw_text).strip()

    @property
    def share_title(self):
        return self.seo_title or self.title

    @property
    def share_description(self):
        return self.meta_description or self.excerpt

    @property
    def is_live(self):
        return self.status == self.STATUS_PUBLISHED and self.published_at and self.published_at <= timezone.now()

    def get_absolute_url(self):
        return reverse("blog:detail", kwargs={"slug": self.slug})

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = build_unique_slug(self, self.title)

        plain_text = self.plain_text
        if not self.excerpt:
            self.excerpt = plain_text[:280]
        if not self.meta_description:
            self.meta_description = (self.excerpt or plain_text)[:300]
        self.reading_time_minutes = max(1, math.ceil(max(1, len(plain_text.split())) / 220))

        if self.status == self.STATUS_PUBLISHED and not self.published_at:
            self.published_at = timezone.now()

        super().save(*args, **kwargs)


class BlogPostRead(models.Model):
    post = models.ForeignKey(BlogPost, on_delete=models.CASCADE, related_name="reads")
    viewer_key = models.CharField(max_length=120)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="blog_reads",
    )
    ip_hash = models.CharField(max_length=64, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    first_seen_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Blog o'qilishi"
        verbose_name_plural = "Blog o'qilishlari"
        constraints = [
            models.UniqueConstraint(fields=["post", "viewer_key"], name="unique_post_reader"),
        ]

    def __str__(self):
        return f"{self.post} | {self.viewer_key}"


class BlogPostClap(models.Model):
    post = models.ForeignKey(BlogPost, on_delete=models.CASCADE, related_name="claps")
    viewer_key = models.CharField(max_length=120)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="blog_claps",
    )
    clap_count = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Blog qarsagi"
        verbose_name_plural = "Blog qarsaklari"
        constraints = [
            models.UniqueConstraint(fields=["post", "viewer_key"], name="unique_post_clap_source"),
        ]

    def __str__(self):
        return f"{self.post} | {self.clap_count}"

    def add_clap(self, limit=50):
        if self.clap_count >= limit:
            return False

        type(self).objects.filter(pk=self.pk).update(clap_count=F("clap_count") + 1)
        BlogPost.objects.filter(pk=self.post_id).update(clap_count=F("clap_count") + 1)
        self.refresh_from_db(fields=["clap_count"])
        return True


class BlogComment(models.Model):
    post = models.ForeignKey(BlogPost, on_delete=models.CASCADE, related_name="comments")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="blog_comments")
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="replies",
    )
    content = models.TextField(max_length=2000)
    like_count = models.PositiveIntegerField(default=0, editable=False)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name = "Blog kommenti"
        verbose_name_plural = "Blog kommentlari"

    def __str__(self):
        return f"{self.user} | {self.post}"

    def clean(self):
        super().clean()
        if self.parent:
            if self.parent.post_id != self.post_id:
                raise ValidationError("Reply faqat shu post ichidagi kommentga yozilishi mumkin.")
            if self.parent.parent_id:
                raise ValidationError("Reply faqat bitta darajada qo'llab-quvvatlanadi.")


class BlogCommentLike(models.Model):
    comment = models.ForeignKey(BlogComment, on_delete=models.CASCADE, related_name="likes")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="blog_comment_likes")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Komment like"
        verbose_name_plural = "Komment likelari"
        constraints = [
            models.UniqueConstraint(fields=["comment", "user"], name="unique_comment_like"),
        ]

    def __str__(self):
        return f"{self.user} -> {self.comment_id}"
