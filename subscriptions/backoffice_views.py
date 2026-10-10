from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from cohorts.membership_service import (
    difference_between,
    release_seat,
    request_tier_difference,
    restore_seat,
    suggest_difference_amount,
    transfer_member,
)
from cohorts.models import Cohort, Enrollment, enrollment_active_access_q
from core.views import _backoffice_context, _private_support_handoff
from .catalog_forms import (
    CatalogPlanForm,
    DeliveryCohortForm,
    DifferenceRequestForm,
    MemberTransferForm,
    SeatDecisionForm,
)
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
        # `with_seat_metrics()`: shablonda `target.is_full` a'zolar sikli
        # ichida o'qiladi, ya'ni annotatsiyasiz har bir a'zo uchun har bir
        # maqsad guruhga alohida COUNT ketardi.
        Cohort.objects.with_seat_metrics()
        .filter(course_id=cohort.course_id, is_active=True)
        .exclude(pk=cohort.pk)
        .select_related("plan")
        .order_by("plan__order", "start_date", "pk")
    )


@_private_support_handoff
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
    from django.http import Http404
    from django.urls import reverse
    from urllib.parse import urlencode
    from core.flags import flag_enabled
    from courses.models import Lesson

    selected_enrollment = None
    selected_lesson = None
    support_return_url = ''
    redirect_url = reverse('backoffice_cohort_members', kwargs={'cohort_id': cohort_id})
    if 'lesson' in request.GET and 'enrollment' not in request.GET:
        raise Http404
    if 'enrollment' in request.GET:
        value = request.GET.get('enrollment', '')
        if (len(request.GET.getlist('enrollment')) != 1 or not value.isascii()
                or not value.isdecimal() or len(value) > 18 or int(value) < 1):
            raise Http404
        selected_enrollment = get_object_or_404(cohort.members.select_related('student'), pk=int(value))
        if 'lesson' in request.GET:
            lesson_value = request.GET.get('lesson', '')
            if (len(request.GET.getlist('lesson')) != 1 or not lesson_value.isascii()
                    or not lesson_value.isdecimal() or len(lesson_value) > 18 or int(lesson_value) < 1):
                raise Http404
            selected_lesson = get_object_or_404(Lesson, pk=int(lesson_value), module__course_id=cohort.course_id)
        if request.method == 'POST' and (
                len(request.POST.getlist('enrollment_id')) != 1
                or request.POST.get('enrollment_id') != str(selected_enrollment.pk)):
            raise Http404
        redirect_params = {'enrollment': selected_enrollment.pk}
        if selected_lesson is not None:
            redirect_params['lesson'] = selected_lesson.pk
        redirect_url += '?' + urlencode(redirect_params)
        if flag_enabled('backoffice_student_support'):
            support_params = {'course': cohort.course_id}
            if selected_lesson is not None:
                support_params['lesson'] = selected_lesson.pk
            support_return_url = reverse('backoffice_workspace_student', kwargs={
                'student_id': selected_enrollment.student_id,
            }) + '?' + urlencode(support_params)
    targets = _transfer_targets(cohort)
    if request.method == "POST":
        if request.POST.get("action") == "difference":
            form = DifferenceRequestForm(request.POST)
            if form.is_valid():
                decision = request_tier_difference(
                    form.cleaned_data["enrollment_id"], request.user,
                    amount=form.cleaned_data["amount"],
                    reason=form.cleaned_data["change_reason"], request=request,
                )
                (messages.success if decision.ok else messages.error)(request, decision.message)
            else:
                messages.error(request, "Summa kiriting, sabab yozing va tasdiqlang.")
            return redirect(redirect_url)

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
            return redirect(redirect_url)

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
        return redirect(redirect_url)

    member_rows = cohort.members.select_related("student", "plan")
    if selected_enrollment is not None:
        member_rows = member_rows.filter(pk=selected_enrollment.pk)
    members = list(
        member_rows.order_by("status", "next_payment_deadline", "pk")
    )
    live_ids = set(
        cohort.members.filter(enrollment_active_access_q()).values_list("pk", flat=True)
    )
    # Eski tariflar bitta so'rovda: aks holda har bir a'zo uchun alohida
    # so'rov ketardi. Yangi tarif sifatida `plan` ustuni olinadi — ko'chirish
    # uni bevosita yozadi.
    previous_plans = {}
    for frozen in (
        Enrollment.objects.filter(
            student_id__in=[member.student_id for member in members],
            cohort__course_id=cohort.course_id,
            status=Enrollment.STATUS_FROZEN,
            plan__isnull=False,
        )
        .select_related("plan")
        .order_by("id")
    ):
        previous_plans[frozen.student_id] = frozen.plan
    open_differences = set(
        cohort.members.filter(
            receipts__is_verified=False, receipts__kind="difference"
        ).values_list("pk", flat=True)
    )
    for member in members:
        member.access_is_open = member.pk in live_ids
        member.holds_a_seat = member.status in (
            Enrollment.STATUS_ACTIVE, Enrollment.STATUS_EXPIRED,
        )
        member.has_open_difference = member.pk in open_differences
        member.suggested_difference = None if member.has_open_difference else difference_between(
            new_plan=member.plan,
            previous_plan=previous_plans.get(member.student_id),
            deadline=member.next_payment_deadline,
        )
    return render(request, "subscriptions/backoffice_cohort_members.html", {
        **_backoffice_context("catalog"), "cohort": cohort, "members": members,
        "transfer_targets": targets,
        "selected_enrollment": selected_enrollment, "support_return_url": support_return_url,
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
