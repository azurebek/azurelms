from django.contrib import admin
from .models import Level, Badge, EarnedBadge, Certificate


@admin.register(Level)
class LevelAdmin(admin.ModelAdmin):
    list_display = ('name', 'min_xp', 'badge_image')
    ordering = ('min_xp',)  # Eng kichik XP dan kattasiga qarab tizib beradi


@admin.register(Badge)
class BadgeAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)


@admin.register(EarnedBadge)
class EarnedBadgeAdmin(admin.ModelAdmin):
    list_display = ('student', 'badge', 'earned_at')
    list_filter = ('badge', 'earned_at')
    search_fields = ('student__username', 'student__first_name')


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ('student', 'course', 'certificate_id', 'issued_at')
    list_filter = ('course', 'issued_at')
    search_fields = ('student__username', 'certificate_id')

    # ID va Sana avtomat yaratilgani uchun, ularni adashib o'zgartirib yubormaslik uchun "faqat o'qishga" qilib qo'yamiz
    readonly_fields = ('certificate_id', 'issued_at')