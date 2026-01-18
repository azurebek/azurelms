from django.contrib import admin
from adminsortable2.admin import SortableAdminMixin, SortableInlineAdminMixin
from .models import LeadCapture, MenuLink, PageBlock, SiteConfig


@admin.register(PageBlock)
class PageBlockAdmin(SortableAdminMixin, admin.ModelAdmin):
    list_display = ("order", "title", "block_type", "is_active")
    list_display_links = ("title",)   # 👈 MUHIM
    list_editable = ("order", "is_active")
    list_filter = ("block_type",)
    ordering = ("order",)


class MenuLinkInline(SortableInlineAdminMixin, admin.TabularInline):
    model = MenuLink
    extra = 0
    fields = ("label", "url", "order", "is_active")
    ordering = ("order",)


@admin.register(SiteConfig)
class SiteConfigAdmin(admin.ModelAdmin):
    inlines = [MenuLinkInline]


@admin.register(LeadCapture)
class LeadCaptureAdmin(admin.ModelAdmin):
    list_display = ("email", "source", "created_at")
    search_fields = ("email", "source")
