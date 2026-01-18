from django.db import models
from core.models import TimeStampedModel
from django_ckeditor_5.fields import CKEditor5Field

class PageBlock(TimeStampedModel):
    HERO = "HERO"
    FEATURES = "FEATURES"
    CURRICULUM = "CURRICULUM"
    PRICING = "PRICING"
    REVIEWS = "REVIEWS"
    COURSE_FEED = "COURSE_FEED"

    BLOCK_TYPE_CHOICES = [
        (HERO, "Hero"),
        (FEATURES, "Features"),
        (CURRICULUM, "Curriculum"),
        (PRICING, "Pricing"),
        (REVIEWS, "Reviews"),
        (COURSE_FEED, "Course Feed"),
    ]

    title = models.CharField(max_length=200)
    block_type = models.CharField(max_length=50, choices=BLOCK_TYPE_CHOICES)
    content_html = CKEditor5Field(config_name="default", blank=True)
    order = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.order}. {self.title}"


class SiteConfig(models.Model):
    site_name = models.CharField(max_length=200, default="AzureLMS")
    announcement = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return "Site Config"
