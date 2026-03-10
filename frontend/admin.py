from django.contrib import admin
from .models import (
    LandingPage,
    Statistic,
    Testimonial,
    AboutPage,
    AboutStatistic,
    TeamMember,
    SiteSettings,
    LegalPage,
)

@admin.register(LandingPage)
class LandingPageAdmin(admin.ModelAdmin):
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
    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()


@admin.register(LegalPage)
class LegalPageAdmin(admin.ModelAdmin):
    list_display = ("page_type", "title", "updated_at")
    readonly_fields = ("updated_at",)
