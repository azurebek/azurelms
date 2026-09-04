from django import forms
from django.contrib import admin, messages
from django.contrib.admin.helpers import ActionForm
from django.urls import reverse
from django.utils.html import format_html

from .models import Attendance, Cohort, Enrollment, EnrollmentTransition, PaymentReceipt
from .transition_service import (
    EnrollmentTransitionError,
    promote_enrollment_to_cohort,
    transfer_enrollment_to_cohort,
)


# ==========================================
# 1. INLINES (O'zaro bog'langan oynalar)
# ==========================================

class EnrollmentInline(admin.TabularInline):
    # Guruhning ichida turib o'quvchilarni qo'shish uchun
    model = Enrollment
    extra = 1
    fields = (
        'student',
        'plan',
        'status',
        'completion_state',
        'last_payment_date',
        'next_payment_deadline',
    )


class ReceiptFileLinkMixin:
    # Private storage public URL bermaydi; barcha admin yuzalari gate'li
    # havoladan foydalanadi, xom FileField widgetidan emas.
    exclude = ('receipt_image',)

    @admin.display(description="Chek fayli")
    def receipt_file_link(self, obj):
        if not obj.pk or not obj.receipt_image:
            return "—"
        return format_html(
            '<a href="{}" target="_blank" rel="noopener">Chekni ochish</a>',
            reverse('cohorts:receipt_file', args=[obj.pk]),
        )


class PaymentReceiptInline(ReceiptFileLinkMixin, admin.TabularInline):
    # O'quvchi obunasining ichida uning to'lov cheklarini ko'rish uchun
    model = PaymentReceipt
    extra = 0
    readonly_fields = (*PaymentReceipt.BILLING_FIELDS, 'submitted_at', 'is_verified', 'receipt_file_link')
    can_delete = False

    def has_add_permission(self, request, obj=None):
        # Bu tarix ko'rinishi; invoice checkoutdan, qaror esa auditli
        # backoffice/bot receipt service'dan o'tadi.
        return False


class EnrollmentTransitionActionForm(ActionForm):
    target_cohort = forms.ModelChoiceField(
        queryset=Cohort.objects.select_related("course").order_by("course__title", "start_date", "name"),
        required=False,
        label="Target cohort",
    )
    transition_note = forms.CharField(
        required=False,
        label="Izoh",
        widget=forms.TextInput(attrs={"placeholder": "Qisqa izoh (ixtiyoriy)"}),
    )


# ==========================================
# 2. ASOSIY ADMIN PANEL SOZLAMALARI
# ==========================================

@admin.register(Cohort)
class CohortAdmin(admin.ModelAdmin):
    list_display = ('name', 'course', 'start_date', 'is_active', 'is_checkout_default')
    list_filter = ('course', 'is_active', 'is_checkout_default')
    search_fields = ('name',)
    actions = ("mark_as_checkout_default",)
    inlines = [EnrollmentInline]  # Guruh ochganda darhol o'quvchilarni tirkab ketamiz

    @admin.action(description="Checkout default cohort qilib belgilash")
    def mark_as_checkout_default(self, request, queryset):
        updated_courses = set()
        for cohort in queryset.select_related("course").order_by("course_id", "-start_date", "-id"):
            Cohort.objects.filter(course=cohort.course, is_checkout_default=True).exclude(pk=cohort.pk).update(
                is_checkout_default=False
            )
            if not cohort.is_checkout_default:
                cohort.is_checkout_default = True
                cohort.save(update_fields=["is_checkout_default"])
            updated_courses.add(cohort.course.title)

        if updated_courses:
            self.message_user(
                request,
                f"{len(updated_courses)} ta kurs uchun checkout default cohort yangilandi.",
                level=messages.SUCCESS,
            )


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = (
        'student',
        'cohort',
        'plan',
        'status',
        'completion_state',
        'next_payment_deadline',
        'promotion_ready_at',
    )
    list_filter = ('status', 'completion_state', 'cohort', 'plan')
    search_fields = ('student__username', 'student__first_name', 'student__last_name')
    inlines = [PaymentReceiptInline]
    action_form = EnrollmentTransitionActionForm
    actions = ("promote_selected", "transfer_selected")
    list_select_related = ("student", "cohort", "cohort__course", "plan")

    def _get_action_target_cohort(self, request):
        target_cohort_id = request.POST.get("target_cohort")
        if not target_cohort_id:
            self.message_user(request, "Iltimos, target cohort tanlang.", level=messages.ERROR)
            return None
        target_cohort = Cohort.objects.select_related("course").filter(pk=target_cohort_id).first()
        if not target_cohort:
            self.message_user(request, "Tanlangan target cohort topilmadi.", level=messages.ERROR)
            return None
        return target_cohort

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("student", "cohort", "cohort__course", "plan")
        )

    @admin.action(description="Tanlangan enrollmentlarni keyingi cohortga promote qilish")
    def promote_selected(self, request, queryset):
        target_cohort = self._get_action_target_cohort(request)
        if not target_cohort:
            return
        note = (request.POST.get("transition_note") or "").strip()
        success_count = 0

        for enrollment in queryset.select_related("student", "cohort", "cohort__course", "plan"):
            try:
                promote_enrollment_to_cohort(
                    source_enrollment=enrollment,
                    target_cohort=target_cohort,
                    created_by=request.user,
                    note=note,
                )
            except EnrollmentTransitionError as exc:
                self.message_user(
                    request,
                    f"{enrollment.student.username} uchun promotion bo'lmadi: {exc}",
                    level=messages.ERROR,
                )
            else:
                success_count += 1

        if success_count:
            self.message_user(
                request,
                f"{success_count} ta enrollment muvaffaqiyatli promote qilindi.",
                level=messages.SUCCESS,
            )

    @admin.action(description="Tanlangan enrollmentlarni boshqa cohortga transfer qilish")
    def transfer_selected(self, request, queryset):
        target_cohort = self._get_action_target_cohort(request)
        if not target_cohort:
            return
        note = (request.POST.get("transition_note") or "").strip()
        success_count = 0

        for enrollment in queryset.select_related("student", "cohort", "cohort__course", "plan"):
            try:
                transfer_enrollment_to_cohort(
                    source_enrollment=enrollment,
                    target_cohort=target_cohort,
                    created_by=request.user,
                    note=note,
                )
            except EnrollmentTransitionError as exc:
                self.message_user(
                    request,
                    f"{enrollment.student.username} uchun transfer bo'lmadi: {exc}",
                    level=messages.ERROR,
                )
            else:
                success_count += 1

        if success_count:
            self.message_user(
                request,
                f"{success_count} ta enrollment muvaffaqiyatli transfer qilindi.",
                level=messages.SUCCESS,
            )


@admin.register(PaymentReceipt)
class PaymentReceiptAdmin(ReceiptFileLinkMixin, admin.ModelAdmin):
    list_display = (
        'get_student',
        'get_plan',
        'base_amount',
        'discount_amount',
        'amount',
        'promo_code_snapshot',
        'is_verified',
        'submitted_at',
    )
    list_filter = ('is_verified', 'submitted_at', 'promo_campaign_snapshot')
    search_fields = ('enrollment__student__username', 'promo_code_snapshot', 'promo_campaign_snapshot')
    readonly_fields = (
        'base_amount', 'discount_amount', 'promo_code_snapshot',
        'promo_campaign_snapshot', 'receipt_file_link', 'is_verified',
    )
    # Tasdiqlash/rad etish canonical servisli backoffice'da. Changelist
    # checkboxi auditni chetlab o'tmasin yoki verified chekni unverify qilmasin.

    def get_student(self, obj):
        return obj.enrollment.student.username

    get_student.short_description = "O'quvchi"

    def get_plan(self, obj):
        return obj.plan_label

    def get_readonly_fields(self, request, obj=None):
        fields = super().get_readonly_fields(request, obj)
        return tuple(dict.fromkeys((*fields, *PaymentReceipt.BILLING_FIELDS))) if obj else fields

    def has_delete_permission(self, request, obj=None):
        # Qaror auditi va promo release uchun backoffice receipt service.
        return False

    get_plan.short_description = "Tarif"


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('enrollment', 'lesson', 'date', 'status', 'xp_awarded', 'marked_by', 'marked_at')
    list_filter = ('status', 'date', 'lesson')
    search_fields = ('enrollment__student__username',)


@admin.register(EnrollmentTransition)
class EnrollmentTransitionAdmin(admin.ModelAdmin):
    list_display = (
        "student",
        "kind",
        "source_cohort",
        "target_cohort",
        "progress_items_moved",
        "created_by",
        "created_at",
    )
    list_filter = ("kind", "source_cohort__course", "target_cohort__course", "created_at")
    search_fields = (
        "student__username",
        "student__email",
        "source_cohort__name",
        "target_cohort__name",
    )
    readonly_fields = (
        "student",
        "kind",
        "source_enrollment",
        "target_enrollment",
        "source_cohort",
        "target_cohort",
        "created_by",
        "note",
        "progress_items_moved",
        "created_at",
    )
    list_select_related = (
        "student",
        "source_cohort",
        "target_cohort",
        "created_by",
    )
