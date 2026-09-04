import secrets
import string
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import PromoCampaign, PromoCode, PromoRedemption


DECIMAL_CENTS = Decimal("0.01")


class PromoValidationError(Exception):
    def __init__(self, message, *, code):
        super().__init__(message)
        self.code = code


@dataclass
class PromoPricingQuote:
    base_amount: Decimal
    discount_amount: Decimal
    final_amount: Decimal
    checkout_kind: str
    promo_code: PromoCode | None = None
    campaign: PromoCampaign | None = None

    @property
    def is_discounted(self):
        return self.discount_amount > 0


def _quantize_amount(value):
    return Decimal(value).quantize(DECIMAL_CENTS, rounding=ROUND_HALF_UP)


def _current_checkout_kind(*, enrollment):
    # Enrollment hali yo'q (checkout sahifasi birinchi marta ochilgan) — bu
    # ta'rifi bo'yicha birinchi xarid. Yozuv yo'lini o'qish yo'lidan ajratgach
    # (A4) narx ko'rsatish enrollmentsiz ham ishlashi kerak.
    if enrollment is None or enrollment.pk is None:
        return PromoRedemption.KIND_INITIAL
    has_verified_payment = enrollment.receipts.filter(is_verified=True).exists()
    return PromoRedemption.KIND_RENEWAL if has_verified_payment else PromoRedemption.KIND_INITIAL


def _fetch_promo_code(*, raw_code, lock=False):
    normalized = PromoCode.normalize_code(raw_code)
    if not normalized:
        return None
    queryset = PromoCode.objects.select_related("campaign")
    if lock:
        queryset = queryset.select_for_update()
    return queryset.filter(normalized_code=normalized).first()


def _active_redemptions_qs():
    return PromoRedemption.objects.filter(status__in=PromoRedemption.ACTIVE_USAGE_STATUSES)


def _check_campaign_scopes(*, campaign, enrollment, plan, cohort=None):
    # Kurs/cohort scope'i uchun cohort kerak; u enrollmentdan yoki (enrollment
    # hali yaratilmagan bo'lsa) checkout tanlagan maqsad cohortdan keladi.
    cohort = cohort or (enrollment.cohort if enrollment is not None else None)

    if campaign.applicable_plans.exists() and not campaign.applicable_plans.filter(pk=plan.pk).exists():
        raise PromoValidationError("Bu promokod tanlangan tarif uchun mos emas.", code="plan_scope")
    if campaign.applicable_courses.exists() and not (
        cohort is not None and campaign.applicable_courses.filter(pk=cohort.course_id).exists()
    ):
        raise PromoValidationError("Bu promokod tanlangan kurs uchun mos emas.", code="course_scope")
    if campaign.applicable_cohorts.exists() and not (
        cohort is not None and campaign.applicable_cohorts.filter(pk=cohort.pk).exists()
    ):
        raise PromoValidationError("Bu promokod tanlangan cohort uchun mos emas.", code="cohort_scope")


def _validate_promo_code_instance(*, promo_code, student, enrollment, plan, base_amount, now=None, cohort=None):
    now = now or timezone.now()
    campaign = promo_code.campaign
    checkout_kind = _current_checkout_kind(enrollment=enrollment)

    if promo_code.status != PromoCode.STATUS_ACTIVE:
        raise PromoValidationError("Promokod faol emas.", code="code_inactive")
    if campaign.status != PromoCampaign.STATUS_ACTIVE:
        raise PromoValidationError("Promo campaign faol emas.", code="campaign_inactive")
    if promo_code.valid_from and now < promo_code.valid_from:
        raise PromoValidationError("Promokod hali ishga tushmagan.", code="code_not_started")
    if promo_code.valid_until and now > promo_code.valid_until:
        raise PromoValidationError("Promokod muddati tugagan.", code="code_expired")
    if campaign.start_at and now < campaign.start_at:
        raise PromoValidationError("Promo campaign hali ishga tushmagan.", code="campaign_not_started")
    if campaign.end_at and now > campaign.end_at:
        raise PromoValidationError("Promo campaign muddati tugagan.", code="campaign_expired")
    if promo_code.assigned_to_id and promo_code.assigned_to_id != student.id:
        raise PromoValidationError("Bu promokod boshqa foydalanuvchiga biriktirilgan.", code="assigned_user")
    if campaign.minimum_order_amount and base_amount < campaign.minimum_order_amount:
        raise PromoValidationError(
            "Checkout summasi ushbu promokod uchun yetarli emas.",
            code="minimum_order_amount",
        )
    if campaign.applies_to_first_purchase_only and student.enrollments.filter(receipts__is_verified=True).exists():
        raise PromoValidationError("Bu promokod faqat birinchi to'lov uchun ishlaydi.", code="first_purchase_only")
    if checkout_kind == PromoRedemption.KIND_RENEWAL and not campaign.allow_on_renewals:
        raise PromoValidationError("Bu promokod renewal to'lovlarga ishlamaydi.", code="renewal_not_allowed")

    _check_campaign_scopes(campaign=campaign, enrollment=enrollment, plan=plan, cohort=cohort)

    active_redemptions = _active_redemptions_qs()
    if campaign.max_total_redemptions is not None:
        total_usage = active_redemptions.filter(campaign=campaign).count()
        if total_usage >= campaign.max_total_redemptions:
            raise PromoValidationError("Promo campaign limiti tugagan.", code="campaign_usage_limit")
    if campaign.max_redemptions_per_user is not None:
        user_usage = active_redemptions.filter(campaign=campaign, student=student).count()
        if user_usage >= campaign.max_redemptions_per_user:
            raise PromoValidationError(
                "Siz ushbu campaign bo'yicha limitdan foydalanib bo'lgansiz.",
                code="campaign_user_limit",
            )
    if promo_code.max_redemptions is not None:
        code_usage = active_redemptions.filter(promo_code=promo_code).count()
        if code_usage >= promo_code.max_redemptions:
            raise PromoValidationError("Promokod ishlatish limiti tugagan.", code="code_usage_limit")

    return checkout_kind


def _calculate_discount(*, campaign, base_amount):
    base_amount = _quantize_amount(base_amount)
    if campaign.discount_type == PromoCampaign.DISCOUNT_PERCENT:
        discount_amount = _quantize_amount(base_amount * (campaign.discount_value / Decimal("100")))
    elif campaign.discount_type == PromoCampaign.DISCOUNT_FIXED:
        discount_amount = min(base_amount, _quantize_amount(campaign.discount_value))
    else:
        target_price = _quantize_amount(campaign.discount_value)
        discount_amount = max(base_amount - target_price, Decimal("0.00"))
    final_amount = max(base_amount - discount_amount, Decimal("0.00"))
    return _quantize_amount(discount_amount), _quantize_amount(final_amount)


def build_promo_quote(*, student, enrollment, plan, raw_code="", now=None, lock=False, cohort=None):
    base_amount = _quantize_amount(plan.price)
    now = now or timezone.now()
    if not raw_code or not raw_code.strip():
        return PromoPricingQuote(
            base_amount=base_amount,
            discount_amount=Decimal("0.00"),
            final_amount=base_amount,
            checkout_kind=_current_checkout_kind(enrollment=enrollment),
        )

    promo_code = _fetch_promo_code(raw_code=raw_code, lock=lock)
    if not promo_code:
        raise PromoValidationError("Promokod topilmadi.", code="not_found")
    if lock:
        promo_code.campaign = PromoCampaign.objects.select_for_update().get(pk=promo_code.campaign_id)

    checkout_kind = _validate_promo_code_instance(
        promo_code=promo_code,
        student=student,
        enrollment=enrollment,
        plan=plan,
        base_amount=base_amount,
        now=now,
        cohort=cohort,
    )
    discount_amount, final_amount = _calculate_discount(campaign=promo_code.campaign, base_amount=base_amount)
    return PromoPricingQuote(
        base_amount=base_amount,
        discount_amount=discount_amount,
        final_amount=final_amount,
        checkout_kind=checkout_kind,
        promo_code=promo_code,
        campaign=promo_code.campaign,
    )


def create_checkout_receipt_with_promo(
    *,
    enrollment,
    plan,
    receipt_image,
    period_start,
    period_end,
    raw_code="",
):
    from cohorts.models import Enrollment, PaymentReceipt, PendingReceiptExists
    from .models import Plan

    with transaction.atomic():
        enrollment = Enrollment.objects.select_for_update().get(pk=enrollment.pk)
        plan = Plan.objects.select_for_update().get(pk=plan.pk)
        if PaymentReceipt.objects.filter(enrollment=enrollment, is_verified=False).exists():
            raise PendingReceiptExists("Sizda allaqachon tasdiqlanmagan to'lov cheki mavjud.")
        quote = build_promo_quote(
            student=enrollment.student,
            enrollment=enrollment,
            plan=plan,
            raw_code=raw_code,
            lock=bool(raw_code and raw_code.strip()),
        )
        # `PaymentReceipt` dagi yagona unique cheklov — bitta enrollmentda
        # bitta tasdiqlanmagan chek. Uni nom bo'yicha ajratib bo'lmaydi:
        # PostgreSQL cheklov nomini xato matniga qo'shadi, SQLite esa yo'q
        # (`UNIQUE constraint failed: cohorts_paymentreceipt.enrollment_id`).
        # Shuning uchun aynan shu `create()` o'ralgan, butun blok emas.
        try:
            receipt = PaymentReceipt.objects.create(
                enrollment=enrollment,
                plan=plan,
                receipt_image=receipt_image,
                amount=quote.final_amount,
                base_amount=quote.base_amount,
                discount_amount=quote.discount_amount,
                promo_code_snapshot=quote.promo_code.code if quote.promo_code else "",
                promo_campaign_snapshot=quote.campaign.name if quote.campaign else "",
                period_start=period_start,
                period_end=period_end,
            )
        except IntegrityError as exc:
            raise PendingReceiptExists(
                "Sizda allaqachon tasdiqlanmagan to'lov cheki mavjud."
            ) from exc
        enrollment.pending_plan = plan
        enrollment.checkout_started_at = timezone.now()
        enrollment.save(update_fields=["pending_plan", "checkout_started_at"])
        redemption = None
        if quote.promo_code:
            redemption = PromoRedemption.objects.create(
                promo_code=quote.promo_code,
                campaign=quote.campaign,
                student=enrollment.student,
                enrollment=enrollment,
                payment_receipt=receipt,
                checkout_kind=quote.checkout_kind,
                status=PromoRedemption.STATUS_RESERVED,
                original_amount=quote.base_amount,
                discount_amount=quote.discount_amount,
                final_amount=quote.final_amount,
                code_snapshot=quote.promo_code.code,
                campaign_name_snapshot=quote.campaign.name,
                discount_type_snapshot=quote.campaign.discount_type,
                discount_value_snapshot=quote.campaign.discount_value,
            )
        return receipt, quote, redemption


def apply_redemption_for_verified_receipt(*, receipt):
    redemption = getattr(receipt, "promo_redemption", None)
    if redemption and redemption.status == PromoRedemption.STATUS_RESERVED:
        redemption.mark_applied(note="Receipt verified")
    return redemption


def release_redemption_for_receipt(*, receipt, reason):
    redemption = getattr(receipt, "promo_redemption", None)
    if redemption and redemption.status == PromoRedemption.STATUS_RESERVED:
        redemption.release(note=reason)
    return redemption


def generate_promo_codes(*, campaign, count, prefix="", length=8, single_use=False):
    count = max(int(count or 0), 0)
    if count == 0:
        return []
    alphabet = string.ascii_uppercase + string.digits
    created_codes = []
    existing_normalized = set(PromoCode.objects.values_list("normalized_code", flat=True))
    for _ in range(count):
        while True:
            random_part = "".join(secrets.choice(alphabet) for _ in range(max(length, 4)))
            raw_code = f"{prefix}{random_part}"
            normalized = PromoCode.normalize_code(raw_code)
            if normalized not in existing_normalized:
                existing_normalized.add(normalized)
                created_codes.append(
                    PromoCode(
                        campaign=campaign,
                        code=raw_code,
                        normalized_code=normalized,
                        max_redemptions=1 if single_use else None,
                    )
                )
                break
    PromoCode.objects.bulk_create(created_codes)
    return created_codes
