from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
import datetime
from courses.models import Course
from subscriptions.models import Plan
from subscriptions.promo_service import (
    PromoValidationError,
    build_promo_quote,
    create_checkout_receipt_with_promo,
)
from .checkout_service import CheckoutUnavailable, resolve_checkout_enrollment
from .models import PaymentReceipt

@login_required
def checkout_view(request, course_id):
    course = get_object_or_404(Course, id=course_id, is_active=True)

    try:
        enrollment, enrollment_created, checkout_cohort = resolve_checkout_enrollment(
            student=request.user,
            course=course,
        )
    except CheckoutUnavailable as exc:
        messages.error(request, str(exc))
        return redirect('course_detail', pk=course.id)

    plans = Plan.objects.order_by('order', 'id')
    if not plans.exists():
        messages.error(request, "Hozircha obuna tariflari sozlanmagan. Iltimos, birozdan so'ng qayta urinib ko'ring.")
        return redirect('subscriptions:pricing')

    selected_plan = enrollment.plan if enrollment.plan_id else plans.first()
    if selected_plan and not plans.filter(id=selected_plan.id).exists():
        selected_plan = plans.first()
    submitted_promo_code = (request.POST.get("promo_code") or request.GET.get("promo_code") or "").strip()
    
    # Check if there is already a pending receipt
    has_pending_receipt = PaymentReceipt.objects.filter(
        enrollment=enrollment, 
        is_verified=False
    ).exists()
    
    # Calculate period_start and period_end for this payment
    today = timezone.localdate()
    if enrollment.status == 'active' and enrollment.next_payment_deadline and enrollment.next_payment_deadline > today:
        # Extend from current deadline
        tentative_start = enrollment.next_payment_deadline
    else:
        # Start immediately
        tentative_start = today
        
    tentative_end = tentative_start + datetime.timedelta(days=30)
    promo_quote = None
    if submitted_promo_code and selected_plan:
        try:
            promo_quote = build_promo_quote(
                student=request.user,
                enrollment=enrollment,
                plan=selected_plan,
                raw_code=submitted_promo_code,
            )
        except PromoValidationError:
            promo_quote = None
    
    if request.method == 'POST':
        selected_plan = plans.filter(id=request.POST.get('plan_id')).first()
        if not selected_plan:
            messages.error(request, "Iltimos, mavjud tariflardan birini tanlang.")
            return render(request, 'cohorts/checkout.html', {
                'course': course,
                'enrollment': enrollment,
                'checkout_cohort': checkout_cohort,
                'enrollment_created': enrollment_created,
                'plans': plans,
                'selected_plan': plans.first(),
                'submitted_promo_code': submitted_promo_code,
                'promo_quote': None,
                'has_pending_receipt': has_pending_receipt,
                'period_start': tentative_start,
                'period_end': tentative_end
            })

        if submitted_promo_code:
            try:
                promo_quote = build_promo_quote(
                    student=request.user,
                    enrollment=enrollment,
                    plan=selected_plan,
                    raw_code=submitted_promo_code,
                )
            except PromoValidationError as exc:
                messages.error(request, str(exc))
                return render(request, 'cohorts/checkout.html', {
                    'course': course,
                    'enrollment': enrollment,
                    'checkout_cohort': checkout_cohort,
                    'enrollment_created': enrollment_created,
                    'plans': plans,
                    'selected_plan': selected_plan,
                    'submitted_promo_code': submitted_promo_code,
                    'promo_quote': None,
                    'has_pending_receipt': has_pending_receipt,
                    'period_start': tentative_start,
                    'period_end': tentative_end
                })
        else:
            promo_quote = None

        if has_pending_receipt:
            messages.error(request, "Sizda allaqachon tasdiqlanmagan to'lov cheki mavjud. Iltimos, administrator tasdiqlashini kuting.")
            return redirect('cohorts:checkout', course_id=course.id)
            
        # Chekni saqlaymiz
        receipt_image = request.FILES.get('receipt_image')
        
        if not receipt_image:
            messages.error(request, "Iltimos, to'lov chek rasmini yuklang.")
            return render(request, 'cohorts/checkout.html', {
                'course': course, 
                'enrollment': enrollment,
                'checkout_cohort': checkout_cohort,
                'enrollment_created': enrollment_created,
                'plans': plans,
                'selected_plan': selected_plan,
                'submitted_promo_code': submitted_promo_code,
                'promo_quote': promo_quote,
                'has_pending_receipt': has_pending_receipt,
                'period_start': tentative_start,
                'period_end': tentative_end
            })

        if enrollment.plan_id != selected_plan.id:
            enrollment.plan = selected_plan
            enrollment.save(update_fields=['plan'])

        try:
            create_checkout_receipt_with_promo(
                enrollment=enrollment,
                plan=selected_plan,
                receipt_image=receipt_image,
                period_start=tentative_start,
                period_end=tentative_end,
                raw_code=submitted_promo_code,
            )
        except PromoValidationError as exc:
            messages.error(request, str(exc))
            return render(request, 'cohorts/checkout.html', {
                'course': course,
                'enrollment': enrollment,
                'checkout_cohort': checkout_cohort,
                'enrollment_created': enrollment_created,
                'plans': plans,
                'selected_plan': selected_plan,
                'submitted_promo_code': submitted_promo_code,
                'promo_quote': None,
                'has_pending_receipt': has_pending_receipt,
                'period_start': tentative_start,
                'period_end': tentative_end
            })
        
        return redirect('cohorts:checkout_success')

    return render(request, 'cohorts/checkout.html', {
        'course': course, 
        'enrollment': enrollment,
        'checkout_cohort': checkout_cohort,
        'enrollment_created': enrollment_created,
        'plans': plans,
        'selected_plan': selected_plan,
        'submitted_promo_code': submitted_promo_code,
        'promo_quote': promo_quote,
        'has_pending_receipt': has_pending_receipt,
        'period_start': tentative_start,
        'period_end': tentative_end
    })

@login_required
def checkout_success_view(request):
    return render(request, 'cohorts/checkout_success.html')


@login_required
def checkout_promo_preview_view(request, course_id):
    course = get_object_or_404(Course, id=course_id, is_active=True)
    try:
        enrollment, _, checkout_cohort = resolve_checkout_enrollment(
            student=request.user,
            course=course,
        )
    except CheckoutUnavailable as exc:
        return JsonResponse({"valid": False, "error": str(exc), "code": "checkout_unavailable"}, status=400)

    plan = Plan.objects.filter(id=request.GET.get("plan_id")).first()
    if not plan:
        return JsonResponse({"valid": False, "error": "Tarif topilmadi.", "code": "plan_not_found"}, status=400)

    raw_code = (request.GET.get("promo_code") or "").strip()
    try:
        quote = build_promo_quote(
            student=request.user,
            enrollment=enrollment,
            plan=plan,
            raw_code=raw_code,
        )
    except PromoValidationError as exc:
        return JsonResponse({"valid": False, "error": str(exc), "code": exc.code}, status=400)

    return JsonResponse(
        {
            "valid": True,
            "course_id": course.id,
            "cohort_id": checkout_cohort.id,
            "base_amount": str(quote.base_amount),
            "discount_amount": str(quote.discount_amount),
            "final_amount": str(quote.final_amount),
            "checkout_kind": quote.checkout_kind,
            "promo_code": quote.promo_code.code if quote.promo_code else "",
            "campaign": quote.campaign.name if quote.campaign else "",
        }
    )
