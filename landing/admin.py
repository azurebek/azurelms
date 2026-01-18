from django.contrib import admin
from .models import PageBlock, SiteConfig

@admin.register(PageBlock)
class PageBlockAdmin(admin.ModelAdmin):
    list_display = ("order", "title", "block_type", "is_active")
    list_display_links = ("title",)   # 👈 MUHIM
    list_editable = ("order", "is_active")
    list_filter = ("block_type",)
    ordering = ("order",)

@admin.register(SiteConfig)
class SiteConfigAdmin(admin.ModelAdmin):
    pass
