import json

from django.contrib import admin
from django.http import JsonResponse
from django.urls import path
from django.utils.html import format_html

from .models import (
    LandingPage,
    Statistic,
    Testimonial,
    AboutPage,
    AboutStatistic,
    TeamMember,
    LandingNavItem,
    AuthPageSettings,
    SiteSettings,
    LegalPage,
)

@admin.register(LandingPage)
class LandingPageAdmin(admin.ModelAdmin):
    fieldsets = (
        (
            "Hero matnlari",
            {
                "fields": (
                    "hero_badge",
                    ("hero_title_start", "hero_title_highlight", "hero_title_end"),
                    "hero_subtitle",
                )
            },
        ),
        (
            "Hero foni",
            {
                "description": "Bu bo'lim bo'sh qolsa bosh sahifada default nozik gradient fon ishlatiladi.",
                "fields": ("hero_background_image", "hero_background_video"),
            },
        ),
        (
            "Hero media kartasi",
            {
                "fields": ("hero_image", "hero_video"),
            },
        ),
        (
            "\"Qanday ishlaydi?\" bo'limi",
            {
                "fields": (
                    ("how_it_works_title", "how_it_works_subtitle"),
                    ("how_it_works_background_image", "how_it_works_background_video"),
                    ("how_it_works_step_one_title", "how_it_works_step_one_description"),
                    ("how_it_works_step_two_title", "how_it_works_step_two_description"),
                    ("how_it_works_step_three_title", "how_it_works_step_three_description"),
                    ("how_it_works_step_four_title", "how_it_works_step_four_description"),
                ),
            },
        ),
        (
            "Footer foni",
            {
                "fields": ("footer_background_image", "footer_background_video"),
            },
        ),
        (
            "Bottom CTA",
            {
                "fields": ("cta_title", "cta_description"),
            },
        ),
    )

    def has_add_permission(self, request):
        # Yagona (Singleton) model uchun faqat 1 ta yozuv yaratishga ruxsat beramiz.
        return not LandingPage.objects.exists()

@admin.register(AboutPage)
class AboutPageAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        # Yagona (Singleton) model
        return not AboutPage.objects.exists()

@admin.register(Statistic)
class StatisticAdmin(admin.ModelAdmin):
    list_display = ('label', 'value', 'order')
    list_editable = ('order',)

@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ('name', 'role', 'rating', 'is_active')
    list_filter = ('is_active', 'rating')

@admin.register(AboutStatistic)
class AboutStatisticAdmin(admin.ModelAdmin):
    list_display = ('label', 'value', 'order')
    list_editable = ('order',)

@admin.register(TeamMember)
class TeamMemberAdmin(admin.ModelAdmin):
    list_display = ('name', 'role_1', 'order')
    list_editable = ('order',)


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        (
            "Asosiy kontaktlar",
            {
                "fields": (
                    "company_description",
                    ("contact_phone", "contact_email"),
                    "contact_address",
                    "support_url",
                )
            },
        ),
        (
            "Checkout to'lov rekvizitlari",
            {
                "fields": (
                    "payment_card_number",
                    "payment_card_holder",
                    "payment_provider_label",
                    "payment_instruction",
                )
            },
        ),
        (
            "Ijtimoiy tarmoqlar",
            {
                "fields": (
                    "telegram_url",
                    "instagram_url",
                    "youtube_url",
                    "facebook_url",
                )
            },
        ),
    )

    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()


@admin.register(LandingNavItem)
class LandingNavItemAdmin(admin.ModelAdmin):
    list_display = ("drag_handle", "label", "kind_label", "is_visible", "order")
    list_display_links = ("label",)
    list_editable = ("is_visible",)
    ordering = ("order", "id")
    readonly_fields = ("key_label",)
    fields = ("label", "key_label", "is_visible", "order")

    class Media:
        css = {"all": ("admin/css/landing_nav_sort.css",)}
        js = ("admin/js/landing_nav_sort.js",)

    @admin.display(description="")
    def drag_handle(self, obj):
        return format_html(
            '<span class="nav-drag-handle" data-object-id="{}" title="Tartibni sudrab o\'zgartiring">⋮⋮</span>',
            obj.pk,
        )

    @admin.display(description="Link turi", ordering="key")
    def kind_label(self, obj):
        return obj.get_key_display()

    @admin.display(description="Link turi")
    def key_label(self, obj):
        return obj.get_key_display()

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_urls(self):
        custom_urls = [
            path("reorder/", self.admin_site.admin_view(self.reorder_view), name="frontend_landingnavitem_reorder"),
        ]
        return custom_urls + super().get_urls()

    def reorder_view(self, request):
        if request.method != "POST":
            return JsonResponse({"error": "Method not allowed."}, status=405)

        try:
            payload = json.loads(request.body.decode("utf-8"))
            ordered_ids = [int(item_id) for item_id in payload.get("ordered_ids", [])]
        except (TypeError, ValueError, json.JSONDecodeError):
            return JsonResponse({"error": "Invalid payload."}, status=400)

        existing_ids = list(self.model.objects.order_by("order", "id").values_list("id", flat=True))
        if sorted(existing_ids) != sorted(ordered_ids):
            return JsonResponse({"error": "IDs mismatch."}, status=400)

        for index, item_id in enumerate(ordered_ids, start=1):
            self.model.objects.filter(pk=item_id).update(order=index)

        return JsonResponse({"ok": True})


@admin.register(AuthPageSettings)
class AuthPageSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        (
            "Umumiy matnlar",
            {
                "fields": (
                    "meta_description",
                    "topbar_back_label",
                    ("help_prompt", "help_link_label"),
                )
            },
        ),
        (
            "Login sahifasi",
            {
                "fields": (
                    "login_visual_kicker",
                    "login_visual_title",
                    "login_visual_description",
                    "login_panel_badge",
                    "login_panel_heading",
                    "login_panel_intro",
                    ("login_footer_prompt", "login_footer_link_label"),
                )
            },
        ),
        (
            "Register sahifasi",
            {
                "fields": (
                    "register_visual_kicker",
                    "register_visual_title",
                    "register_visual_description",
                    "register_panel_badge",
                    "register_panel_heading",
                    "register_panel_intro",
                    ("register_footer_prompt", "register_footer_link_label"),
                )
            },
        ),
    )

    def has_add_permission(self, request):
        return not AuthPageSettings.objects.exists()


@admin.register(LegalPage)
class LegalPageAdmin(admin.ModelAdmin):
    list_display = ("page_type", "title", "updated_at")
    readonly_fields = ("updated_at",)
