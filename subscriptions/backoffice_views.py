from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from cohorts.models import Cohort
from core.views import _backoffice_context
from .catalog_forms import CatalogPlanForm, DeliveryCohortForm
from .catalog_service import require_owner, save_cohort, update_plan
from .models import Plan


@login_required
def catalog(request):
    require_owner(request.user, request=request)
    return render(request, "subscriptions/backoffice_catalog.html", {
        **_backoffice_context("catalog"),
        "plans": Plan.objects.select_related("ai_policy").order_by("order", "id"),
        # Joy ko'rsatkichlari annotatsiya bilan: aks holda har bir qator
        # o'z so'rovlarini yugurtirardi va guruhlar soni ortgan sari sahifa
        # sekinlashardi.
        "cohorts": (
            Cohort.objects.with_seat_metrics()
            .select_related("course", "plan")
            .order_by("-start_date", "-pk")
        ),
    })


@login_required
def plan_editor(request, plan_id):
    require_owner(request.user, request=request)
    plan = get_object_or_404(Plan, pk=plan_id)
    form = CatalogPlanForm(instance=plan)
    if request.method == "POST":
        form = update_plan(actor=request.user, plan_id=plan_id, data=request.POST, request=request)
        if form.is_valid():
            messages.success(request, "Tarif saqlandi. Eski to'lov tarixi va sotib olingan huquqlar o'zgarmadi.")
            return redirect("backoffice_catalog")
    return render(request, "subscriptions/backoffice_catalog_form.html", {
        **_backoffice_context("catalog"), "form": form, "title": f"Tarif: {plan.name}",
        "note": f"Barqaror kod: {plan.code}. Valyuta: UZS. AI limiti AI boshqaruvida tahrirlanadi.",
    })


@login_required
def cohort_editor(request, cohort_id=None):
    require_owner(request.user, request=request)
    cohort = get_object_or_404(Cohort, pk=cohort_id) if cohort_id else Cohort()
    form = DeliveryCohortForm(instance=cohort)
    if request.method == "POST":
        form = save_cohort(actor=request.user, cohort_id=cohort_id, data=request.POST, request=request)
        if form.is_valid():
            messages.success(request, "Guruh saqlandi.")
            return redirect("backoffice_catalog")
    return render(request, "subscriptions/backoffice_catalog_form.html", {
        **_backoffice_context("catalog"), "form": form,
        "title": f"Guruh: {cohort.name}" if cohort_id else "Yangi tarif guruhi",
        "note": "O'qituvchi kursdan olinadi. A'zolari bor guruhning tarifi o'zgartirilmaydi. Joy faqat tasdiqda band bo'ladi.",
    })
