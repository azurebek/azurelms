from django.views.generic import ListView
from .models import Plan
from .catalog import purchase_plans

class PricingView(ListView):
    model = Plan
    template_name = 'subscriptions/pricing.html'
    context_object_name = 'plans'
    
    def get_queryset(self):
        # Using prefetch_related reduces database queries
        return purchase_plans().prefetch_related('features')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_nav'] = 'pricing'
        return context
