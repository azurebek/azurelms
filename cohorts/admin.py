from django.contrib import admin
from .models import Cohort, Enrollment, PaymentReceipt, Attendance


# ==========================================
# 1. INLINES (O'zaro bog'langan oynalar)
# ==========================================

class EnrollmentInline(admin.TabularInline):
    # Guruhning ichida turib o'quvchilarni qo'shish uchun
    model = Enrollment
    extra = 1
    fields = ('student', 'status', 'last_payment_date', 'next_payment_deadline')


class PaymentReceiptInline(admin.TabularInline):
    # O'quvchi obunasining ichida uning to'lov cheklarini ko'rish uchun
    model = PaymentReceipt
    extra = 0
    readonly_fields = ('submitted_at',)


# ==========================================
# 2. ASOSIY ADMIN PANEL SOZLAMALARI
# ==========================================

@admin.register(Cohort)
class CohortAdmin(admin.ModelAdmin):
    list_display = ('name', 'course', 'start_date', 'is_active')
    list_filter = ('course', 'is_active')
    search_fields = ('name',)
    inlines = [EnrollmentInline]  # Guruh ochganda darhol o'quvchilarni tirkab ketamiz


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'cohort', 'status', 'next_payment_deadline')
    list_filter = ('status', 'cohort')
    search_fields = ('student__username', 'student__first_name', 'student__last_name')
    inlines = [PaymentReceiptInline]


@admin.register(PaymentReceipt)
class PaymentReceiptAdmin(admin.ModelAdmin):
    list_display = ('get_student', 'amount', 'is_verified', 'submitted_at')
    list_filter = ('is_verified', 'submitted_at')
    search_fields = ('enrollment__student__username',)

    # SEHRLI QATOR: Chekni ichiga kirmasdan, ro'yxatning o'zidayoq galichka qilib tasdiqlash imkonini beradi!
    list_editable = ('is_verified',)

    def get_student(self, obj):
        return obj.enrollment.student.username

    get_student.short_description = "O'quvchi"


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('enrollment', 'lesson', 'date', 'is_present')
    list_filter = ('is_present', 'date', 'lesson')
    search_fields = ('enrollment__student__username',)