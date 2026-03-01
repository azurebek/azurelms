from django.contrib import admin
from .models import Plan, PlanFeature

class PlanFeatureInline(admin.TabularInline):
    model = PlanFeature
    extra = 3

@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'is_popular', 'order')
    list_editable = ('price', 'is_popular', 'order')
    inlines = [PlanFeatureInline]
