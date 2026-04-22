from django import forms
from django.contrib import admin, messages
from django.contrib.admin.helpers import ActionForm

from .models import Plan, PlanFeature, PromoCampaign, PromoCode, PromoRedemption
from .promo_service import generate_promo_codes


class PlanFeatureInline(admin.TabularInline):
    model = PlanFeature
    extra = 3


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ("name", "price", "is_popular", "order")
    list_editable = ("price", "is_popular", "order")
    inlines = [PlanFeatureInline]


class PromoCodeInline(admin.TabularInline):
    model = PromoCode
    extra = 0
    fields = ("code", "status", "assigned_to", "max_redemptions", "valid_from", "valid_until")
    readonly_fields = ("normalized_code",)


class PromoCampaignActionForm(ActionForm):
    code_prefix = forms.CharField(required=False, label="Prefix")
    code_count = forms.IntegerField(required=False, min_value=1, label="Code count")
    single_use_codes = forms.BooleanField(required=False, label="Single-use")


@admin.register(PromoCampaign)
class PromoCampaignAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "status",
        "discount_type",
        "discount_value",
        "max_total_redemptions",
        "usage_count",
        "created_at",
    )
    list_filter = ("status", "discount_type", "allow_on_renewals", "applies_to_first_purchase_only")
    search_fields = ("name", "description", "internal_note")
    filter_horizontal = ("applicable_plans", "applicable_courses", "applicable_cohorts")
    readonly_fields = ("created_at", "updated_at", "usage_count")
    inlines = [PromoCodeInline]
    action_form = PromoCampaignActionForm
    actions = ("activate_selected", "pause_selected", "archive_selected", "generate_codes_for_campaign")
    fieldsets = (
        (
            "Asosiy ma'lumotlar",
            {
                "fields": (
                    "name",
                    "description",
                    "status",
                    ("discount_type", "discount_value"),
                    ("minimum_order_amount", "max_total_redemptions", "max_redemptions_per_user"),
                    ("applies_to_first_purchase_only", "allow_on_renewals", "allow_stacking"),
                    ("start_at", "end_at"),
                    "usage_count",
                    "internal_note",
                )
            },
        ),
        (
            "Scope",
            {
                "fields": (
                    "applicable_plans",
                    "applicable_courses",
                    "applicable_cohorts",
                )
            },
        ),
        (
            "Audit",
            {
                "fields": ("created_at", "updated_at"),
            },
        ),
    )

    @admin.display(description="Faol usage")
    def usage_count(self, obj):
        return obj.redemptions.filter(status__in=PromoRedemption.ACTIVE_USAGE_STATUSES).count()

    @admin.action(description="Campaignlarni active qilish")
    def activate_selected(self, request, queryset):
        updated = queryset.update(status=PromoCampaign.STATUS_ACTIVE)
        self.message_user(request, f"{updated} ta campaign active qilindi.", level=messages.SUCCESS)

    @admin.action(description="Campaignlarni pause qilish")
    def pause_selected(self, request, queryset):
        updated = queryset.update(status=PromoCampaign.STATUS_PAUSED)
        self.message_user(request, f"{updated} ta campaign pause qilindi.", level=messages.SUCCESS)

    @admin.action(description="Campaignlarni archive qilish")
    def archive_selected(self, request, queryset):
        updated = queryset.update(status=PromoCampaign.STATUS_ARCHIVED)
        self.message_user(request, f"{updated} ta campaign archive qilindi.", level=messages.SUCCESS)

    @admin.action(description="Tanlangan campaignlar uchun batch promo kodlar yaratish")
    def generate_codes_for_campaign(self, request, queryset):
        code_count = int(request.POST.get("code_count") or 0)
        code_prefix = (request.POST.get("code_prefix") or "").strip().upper()
        single_use = bool(request.POST.get("single_use_codes"))
        if code_count <= 0:
            self.message_user(request, "Iltimos, code count kiriting.", level=messages.ERROR)
            return

        total_created = 0
        for campaign in queryset:
            created = generate_promo_codes(
                campaign=campaign,
                count=code_count,
                prefix=code_prefix,
                single_use=single_use,
            )
            total_created += len(created)

        self.message_user(
            request,
            f"{total_created} ta yangi promo kod yaratildi.",
            level=messages.SUCCESS,
        )


@admin.register(PromoCode)
class PromoCodeAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "campaign",
        "status",
        "assigned_to",
        "max_redemptions",
        "usage_count",
        "valid_until",
    )
    list_filter = ("status", "campaign", "campaign__status")
    search_fields = ("code", "normalized_code", "campaign__name", "assigned_to__username", "assigned_to__email")
    readonly_fields = ("normalized_code", "created_at", "updated_at", "usage_count")
    actions = ("activate_selected", "disable_selected", "archive_selected")

    @admin.display(description="Faol usage")
    def usage_count(self, obj):
        return obj.redemptions.filter(status__in=PromoRedemption.ACTIVE_USAGE_STATUSES).count()

    @admin.action(description="Kodlarni active qilish")
    def activate_selected(self, request, queryset):
        updated = queryset.update(status=PromoCode.STATUS_ACTIVE)
        self.message_user(request, f"{updated} ta promo kod active qilindi.", level=messages.SUCCESS)

    @admin.action(description="Kodlarni disable qilish")
    def disable_selected(self, request, queryset):
        updated = queryset.update(status=PromoCode.STATUS_DISABLED)
        self.message_user(request, f"{updated} ta promo kod disable qilindi.", level=messages.SUCCESS)

    @admin.action(description="Kodlarni archive qilish")
    def archive_selected(self, request, queryset):
        updated = queryset.update(status=PromoCode.STATUS_ARCHIVED)
        self.message_user(request, f"{updated} ta promo kod archive qilindi.", level=messages.SUCCESS)


@admin.register(PromoRedemption)
class PromoRedemptionAdmin(admin.ModelAdmin):
    list_display = (
        "code_snapshot",
        "student",
        "campaign_name_snapshot",
        "status",
        "checkout_kind",
        "original_amount",
        "discount_amount",
        "final_amount",
        "reserved_at",
    )
    list_filter = ("status", "checkout_kind", "campaign", "promo_code")
    search_fields = ("code_snapshot", "student__username", "student__email", "campaign_name_snapshot")
    readonly_fields = (
        "promo_code",
        "campaign",
        "student",
        "enrollment",
        "payment_receipt",
        "checkout_kind",
        "original_amount",
        "discount_amount",
        "final_amount",
        "code_snapshot",
        "campaign_name_snapshot",
        "discount_type_snapshot",
        "discount_value_snapshot",
        "reserved_at",
        "applied_at",
        "released_at",
        "updated_at",
    )
    actions = ("release_selected", "reject_selected")

    @admin.action(description="Tanlangan redemptionlarni release qilish")
    def release_selected(self, request, queryset):
        count = 0
        for redemption in queryset:
            if redemption.status in PromoRedemption.ACTIVE_USAGE_STATUSES:
                redemption.release(note="Admin release action")
                count += 1
        self.message_user(request, f"{count} ta redemption release qilindi.", level=messages.SUCCESS)

    @admin.action(description="Tanlangan redemptionlarni reject qilish")
    def reject_selected(self, request, queryset):
        count = 0
        for redemption in queryset:
            if redemption.status in PromoRedemption.ACTIVE_USAGE_STATUSES:
                redemption.release(status=PromoRedemption.STATUS_REJECTED, note="Admin reject action")
                count += 1
        self.message_user(request, f"{count} ta redemption reject qilindi.", level=messages.SUCCESS)
