from django.shortcuts import render
from django.db.models import Q
from django.utils import timezone
from .forms import LeadCaptureForm
from .models import LeadCapture, PageBlock, SiteConfig
from courses.models import Batch


def home_view(request):
    now = timezone.now()
    blocks = PageBlock.objects.filter(
        is_active=True,
    ).filter(
        Q(start_date__isnull=True) | Q(start_date__lte=now),
        Q(end_date__isnull=True) | Q(end_date__gte=now),
    )
    site = SiteConfig.objects.first()
    batches = Batch.objects.filter(status=Batch.ENROLLING).order_by("start_date")
    return render(request, "landing/home.html", {
        "blocks": blocks,
        "site": site,
        "batches": batches,
        "lead_form": LeadCaptureForm(),
    })


def lead_capture_view(request):
    form = LeadCaptureForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        LeadCapture.objects.create(
            email=form.cleaned_data["email"],
            source=form.cleaned_data.get("source", ""),
        )
        return render(request, "landing/partials/lead_success.html")
    return render(request, "landing/partials/lead_form.html", {"form": form})
