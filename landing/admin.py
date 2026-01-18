from django.contrib import admin
# DIQQAT: 3 ta klassni ham import qilish shart!
from adminsortable2.admin import SortableAdminBase, SortableInlineAdminMixin, SortableAdminMixin
from .models import LeadCapture, MenuLink, PageBlock, SiteConfig


@admin.register(PageBlock)
class PageBlockAdmin(SortableAdminMixin, admin.ModelAdmin):
    # SortableAdminMixin yordamida bu bloklarni drag-and-drop qilish mumkin
    list_display = ("title", "block_type", "order", "is_active")
    list_display_links = ("title",)

    # Eslatma: 'order' maydonini list_editable'dan olib tashladim,
    # chunki drag-and-drop ishlatganda uni qo'lda yozish shart emas.
    # Faqat 'is_active' qoldi.
    list_editable = ("is_active",)

    list_filter = ("block_type",)
    ordering = ("order",)


class MenuLinkInline(SortableInlineAdminMixin, admin.TabularInline):
    # Bu inline menyularni SiteConfig ichida surishga imkon beradi
    model = MenuLink
    extra = 0
    fields = ("label", "url", "order", "is_active")
    ordering = ("order",)


@admin.register(SiteConfig)
class SiteConfigAdmin(SortableAdminBase, admin.ModelAdmin):
    # DIQQAT: Bu yerda 'SortableAdminMixin' emas, 'SortableAdminBase' ishlatildi.
    # Sababi: SiteConfig bitta nusxada (Singleton), uni surib bo'lmaydi,
    # lekin uning ichidagi MenuLink'larni surish uchun 'Base' kerak.
    inlines = [MenuLinkInline]


@admin.register(LeadCapture)
class LeadCaptureAdmin(admin.ModelAdmin):
    list_display = ("email", "source", "created_at")
    search_fields = ("email", "source")