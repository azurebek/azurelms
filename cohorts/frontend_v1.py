"""Frozen checkout renderer/native form adapter; all billing rules remain canonical."""
import re

from django.core import signing
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import TemplateView

from core.flags import flag_enabled
from core.frontend_v1 import FrontendV1Mixin
from core.operational_settings import current_thresholds
from core.upload_validation import MB, PROFILES, validate_upload
from courses.models import Course
from subscriptions.catalog import purchase_plans
from subscriptions.models import Plan
from subscriptions.promo_service import (
    PromoValidationError, build_promo_quote, create_checkout_receipt_with_promo,
)
from .checkout_service import (
    CheckoutUnavailable, checkout_period, find_checkout_enrollment, resolve_checkout_enrollment,
)
from .delivery_service import lock_enrollment
from .models import PaymentReceipt, PendingReceiptExists

SALT = 'frontend-v1.checkout.quote'


class CheckoutPage(FrontendV1Mixin, TemplateView):
    # Also used for a blocked in-flight V1 request after a renderer rollback.
    frontend_v1_enabled = True
    frontend_v1_title = 'To‘lov'


def page(request, context, *, status=200, receipt=False):
    view = CheckoutPage()
    view.setup(request)
    view.frontend_v1_template = 'frontend_v1/checkout/status.html' if receipt else 'frontend_v1/checkout/form.html'
    return view.render_to_response(view.get_context_data(active_nav='subscriptions', **context), status=status)


def quote_values(user, course, cohort, plan, quote, period):
    """A confirmation of displayed values, not a new invoice/pricing calculation."""
    return dict(user=user.pk, course=course.pk, cohort=cohort.pk, plan=plan.pk,
                plan_name=plan.name, kind=quote.checkout_kind,
                base=str(quote.base_amount), discount=str(quote.discount_amount), total=str(quote.final_amount),
                promo=quote.promo_code.pk if quote.promo_code else None,
                promo_code=quote.promo_code.code if quote.promo_code else '',
                campaign=quote.campaign.pk if quote.campaign else None,
                campaign_name=quote.campaign.name if quote.campaign else '',
                period=[str(day) for day in period])


def pending_receipt(enrollment):
    return enrollment.receipts.filter(is_verified=False).order_by('-submitted_at', '-pk').first() if enrollment else None


def checkout(request, course_id):
    course = get_object_or_404(Course, pk=course_id, is_active=True)
    plans = purchase_plans(student=request.user, course=course)
    data = request.POST if request.method == 'POST' else request.GET
    raw_plan = data.get('plan_id', '')
    raw_promo = data.get('promo_code', '').strip()
    quote_minutes = current_thresholds().checkout_quote_minutes
    context = dict(course=course, plans=plans, submitted_promo_code=raw_promo,
                   quote_minutes=quote_minutes,
                   max_upload_mb=PROFILES['image']['max_bytes'] // MB)
    allowed = {'plan_id', 'promo_code'}
    if request.method == 'POST':
        allowed |= {'csrfmiddlewaretoken', 'frontend_v1_checkout', 'quote_token', 'confirm_scope'}
    if any(key not in allowed or len(data.getlist(key)) != 1 for key in data) or len(raw_promo) > 64:
        return page(request, dict(context, checkout_error='So‘rov maydonlari noto‘g‘ri. Tarif va promokodni qayta tekshiring.'), status=400)
    if request.method == 'POST' and not flag_enabled('frontend_v1_checkout'):
        return page(request, dict(context, checkout_error='To‘lov sahifasi yangilandi. Qayta oching; chek yuborilmadi.'), status=409)
    if raw_plan and (not re.fullmatch(r'[1-9][0-9]{0,17}', raw_plan) or not plans.filter(pk=raw_plan).exists()):
        return page(request, dict(context, checkout_error='Tanlangan tarif mavjud emas. Boshqa tarif avtomatik tanlanmadi.'), status=400)
    if request.method == 'POST' and not raw_plan:
        return page(request, dict(context, checkout_error='Avval tarif summasini tekshiring.'), status=400)
    if not plans.exists():
        return page(request, dict(context, checkout_error='Hozircha xarid uchun tarif mavjud emas.'))

    current = request.user.enrollments.filter(cohort__course=course).exclude(status='frozen').order_by('-joined_at', '-id').first()
    preferred = (current.pending_plan or current.active_plan()) if current else None
    plan = plans.filter(pk=raw_plan).first() if raw_plan else (preferred if preferred and plans.filter(pk=preferred.pk).exists() else plans.first())
    try:
        try:
            enrollment, cohort = find_checkout_enrollment(student=request.user, course=course, plan=plan)
        except CheckoutUnavailable:
            if raw_plan:
                raise
            for candidate in plans.exclude(pk=plan.pk):
                try:
                    enrollment, cohort = find_checkout_enrollment(student=request.user, course=course, plan=candidate)
                except CheckoutUnavailable:
                    continue
                plan = candidate
                break
            else:
                raise
        context.update(selected_plan=plan, checkout_cohort=cohort, pending_receipt=pending_receipt(enrollment))
        if request.method == 'POST' and context['pending_receipt']:
            return redirect('cohorts:checkout_pending', receipt_id=context['pending_receipt'].pk)
        quote = build_promo_quote(student=request.user, enrollment=enrollment, plan=plan, raw_code=raw_promo, cohort=cohort)
        period = checkout_period(enrollment)
        values = quote_values(request.user, course, cohort, plan, quote, period)
        context.update(promo_quote=quote, period_start=period[0], period_end=period[1],
                       quote_token=signing.dumps(values, salt=SALT, compress=True))
        if request.method == 'POST':
            try:
                confirmed = signing.loads(data.get('quote_token', ''), salt=SALT, max_age=quote_minutes * 60)
            except signing.BadSignature:
                return page(request, dict(context, checkout_error='Summa tasdig‘i eskirgan yoki noto‘g‘ri. Qayta tekshiring; chek yuborilmadi.', quote_token=''), status=409)
            if confirmed != values:
                return page(request, dict(context, checkout_error='Tarif, chegirma, guruh yoki davr o‘zgargan. Yangi summani tekshiring; chek yuborilmadi.', quote_token=''), status=409)
            if data.get('confirm_scope') != 'yes':
                raise ValidationError('Chek va summani tekshirganingizni tasdiqlang.')
            upload = request.FILES.get('receipt_image')
            if not upload or set(request.FILES) != {'receipt_image'} or len(request.FILES.getlist('receipt_image')) != 1:
                raise ValidationError('Bitta to‘lov cheki rasmini tanlang.')
            validate_upload(upload, profile='image', field_label='Chek rasmi')
            try:
                with transaction.atomic():
                    # Canonical lock order, including the re-resolution of a pending cohort.
                    course = Course.objects.select_for_update().get(pk=course.pk, is_active=True)
                    enrollment, _, cohort = resolve_checkout_enrollment(student=request.user, course=course, plan=plan)
                    enrollment = lock_enrollment(enrollment.pk)
                    existing = pending_receipt(enrollment)
                    if existing:
                        return redirect('cohorts:checkout_pending', receipt_id=existing.pk)
                    plan = Plan.objects.select_for_update().get(pk=plan.pk)
                    quote = build_promo_quote(student=request.user, enrollment=enrollment, plan=plan, raw_code=raw_promo, cohort=cohort, lock=bool(raw_promo))
                    period = checkout_period(enrollment)
                    if confirmed != quote_values(request.user, course, cohort, plan, quote, period):
                        raise StaleQuote
                    receipt, _, _ = create_checkout_receipt_with_promo(
                        enrollment=enrollment, plan=plan, receipt_image=upload,
                        period_start=period[0], period_end=period[1], raw_code=raw_promo,
                    )
            except StaleQuote:
                return page(request, dict(context, checkout_error='Hisob yuborish paytida o‘zgardi. Summani qayta tekshiring; chek yuborilmadi.', quote_token=''), status=409)
            except (Course.DoesNotExist, Plan.DoesNotExist):
                return page(request, dict(context, checkout_error='Kurs yoki tarif endi mavjud emas. Chek yuborilmadi.', quote_token=''), status=409)
            except PendingReceiptExists:
                return redirect('cohorts:checkout', course_id=course.pk)
            return redirect('cohorts:checkout_pending', receipt_id=receipt.pk)
    except (CheckoutUnavailable, PromoValidationError, ValidationError) as exc:
        message = ' '.join(exc.messages) if isinstance(exc, ValidationError) else str(exc)
        return page(request, dict(context, checkout_error=message), status=400)
    return page(request, context)


class StaleQuote(Exception):
    pass


def render_receipt(request, receipt):
    return page(request, dict(receipt=receipt, access_open=receipt.enrollment.has_active_access()), receipt=True)
