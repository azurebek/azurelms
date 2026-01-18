from django.db import models
from django.utils import timezone
from core.models import TimeStampedModel
from django_ckeditor_5.fields import CKEditor5Field

class PageBlock(TimeStampedModel):
    HERO = "HERO"
    MARKETING = "MARKETING"
    FEATURES = "FEATURES"
    CURRICULUM = "CURRICULUM"
    PRICING = "PRICING"
    REVIEWS = "REVIEWS"
    LEAD_FORM = "LEAD_FORM"
    COURSE_FEED = "COURSE_FEED"
    HTML = "HTML"

    BLOCK_TYPE_CHOICES = [
        (HERO, "Hero"),
        (MARKETING, "Marketing"),
        (FEATURES, "Features"),
        (CURRICULUM, "Curriculum"),
        (PRICING, "Pricing"),
        (REVIEWS, "Reviews"),
        (LEAD_FORM, "Lead Form"),
        (COURSE_FEED, "Course Feed"),
        (HTML, "HTML"),
    ]

    title = models.CharField(max_length=200)
    block_type = models.CharField(max_length=50, choices=BLOCK_TYPE_CHOICES)
    content_html = CKEditor5Field(config_name="default", blank=True)
    image = models.ImageField(upload_to="landing/blocks/", blank=True, null=True)
    cta_label = models.CharField(max_length=120, blank=True)
    cta_url = models.URLField(blank=True)
    order = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    style_config = models.JSONField(default=dict, blank=True)
    start_date = models.DateTimeField(blank=True, null=True)
    end_date = models.DateTimeField(blank=True, null=True)
    countdown_to = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["order"]

    @property
    def bg_class(self):
        return self.style_config.get("bg_color", "bg-white")

    @property
    def container_class(self):
        return self.style_config.get("container_type", "container")

    def is_within_schedule(self):
        now = timezone.now()
        if self.start_date and self.start_date > now:
            return False
        if self.end_date and self.end_date < now:
            return False
        return True

    def __str__(self):
        return f"{self.order}. {self.title}"


class SiteConfig(models.Model):
    site_name = models.CharField(max_length=200, default="AzureLMS")
    announcement = models.CharField(max_length=255, blank=True)
    logo_light = models.ImageField(upload_to="branding/", blank=True, null=True)
    logo_dark = models.ImageField(upload_to="branding/", blank=True, null=True)

    def __str__(self):
        return "Site Config"


class MenuLink(models.Model):
    site = models.ForeignKey(SiteConfig, related_name="menu_links", on_delete=models.CASCADE)
    label = models.CharField(max_length=80)
    url = models.URLField()
    order = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.label


class LeadCapture(TimeStampedModel):
    email = models.EmailField()
    source = models.CharField(max_length=120, blank=True)

    def __str__(self):
        return self.email
