from django.views.generic import ListView
from .models import Plan

class PricingView(ListView):
    model = Plan
    template_name = 'subscriptions/pricing.html'
    context_object_name = 'plans'
    
    def get_queryset(self):
        # Using prefetch_related reduces database queries
        return Plan.objects.prefetch_related('features').all()
