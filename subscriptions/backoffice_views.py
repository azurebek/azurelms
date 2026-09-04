from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from cohorts.membership_service import release_seat, restore_seat, transfer_member
from cohorts.models import Cohort, Enrollment, enrollment_active_access_q
from core.views import _backoffice_context
from .catalog_forms import CatalogPlanForm, DeliveryCohortForm, MemberTransferForm, SeatDecisionForm
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


def _transfer_targets(cohort):
    """Shu kursning boshqa faol guruhlari — boshqa tarifdagilari ham.

    Tarif almashishi ro'yxatdan chiqarilmaydi: aynan shu ko'chirish kerak
    bo'ladi. Ammo u alohida tasdiq so'raydi, chunki pulga tegadi.
    """
    return (
        Cohort.objects.filter(course_id=cohort.course_id, is_active=True)
        .exclude(pk=cohort.pk)
        .select_related("plan")
        .order_by("plan__order", "start_date", "pk")
    )


@login_required
def cohort_members(request, cohort_id):
    """Guruh a'zolari va joy bo'yicha qaror.

    Ilgari obuna holatini odam o'zgartiradigan yagona joy o'chirilgan eski
    admin edi, ya'ni qaytmaydigan o'quvchining joyini hech kim bo'shata
    olmasdi va guruh sotuvni jimgina to'xtatardi.
    """
    require_owner(request.user, request=request)
    cohort = get_object_or_404(
        Cohort.objects.with_seat_metrics().select_related("course", "plan"), pk=cohort_id
    )
    targets = _transfer_targets(cohort)
    if request.method == "POST":
        if request.POST.get("action") == "transfer":
            form = MemberTransferForm(request.POST, targets=targets)
            if form.is_valid():
                decision = transfer_member(
                    form.cleaned_data["enrollment_id"], form.cleaned_data["target_cohort"].pk,
                    request.user, reason=form.cleaned_data["change_reason"], request=request,
                    allow_tier_change=form.cleaned_data["allow_tier_change"],
                )
                (messages.success if decision.ok else messages.error)(request, decision.message)
            else:
                messages.error(request, "Guruhni tanlang, sabab yozing va tasdiqlang.")
            return redirect("backoffice_cohort_members", cohort_id=cohort_id)

        form = SeatDecisionForm(request.POST)
        if form.is_valid():
            decide = release_seat if form.cleaned_data["action"] == SeatDecisionForm.ACTION_RELEASE else restore_seat
            decision = decide(
                form.cleaned_data["enrollment_id"], request.user,
                reason=form.cleaned_data["change_reason"], request=request,
            )
            (messages.success if decision.ok else messages.error)(request, decision.message)
        else:
            messages.error(request, "Sabab yozing va qarorni tasdiqlang.")
        return redirect("backoffice_cohort_members", cohort_id=cohort_id)

    members = list(
        cohort.members.select_related("student", "plan")
        .order_by("status", "next_payment_deadline", "pk")
    )
    live_ids = set(
        cohort.members.filter(enrollment_active_access_q()).values_list("pk", flat=True)
    )
    for member in members:
        member.access_is_open = member.pk in live_ids
        member.holds_a_seat = member.status in (
            Enrollment.STATUS_ACTIVE, Enrollment.STATUS_EXPIRED,
        )
    return render(request, "subscriptions/backoffice_cohort_members.html", {
        **_backoffice_context("catalog"), "cohort": cohort, "members": members,
        "transfer_targets": targets,
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
