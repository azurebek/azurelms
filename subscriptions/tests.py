import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from cohorts.models import Cohort, Enrollment
from courses.models import Course
from subscriptions.models import Plan, PromoCampaign, PromoCode, PromoRedemption
from subscriptions.promo_service import (
    PromoValidationError,
    build_promo_quote,
    generate_promo_codes,
)


User = get_user_model()


class PromoPricingServiceTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            username="promo-teacher",
            email="promo-teacher@example.com",
            password="testpass123",
            is_staff=True,
        )
        self.student = User.objects.create_user(
            username="promo-student",
            email="promo-student@example.com",
            password="testpass123",
        )
        self.course = Course.objects.create(
            title="Promo Course",
            description="Promo test",
            instructor=self.teacher,
            level="beginner",
        )
        self.cohort = Cohort.objects.create(
            name="Promo Cohort",
            course=self.course,
            start_date=datetime.date(2026, 3, 1),
        )
        self.plan = Plan.objects.create(
            name="Promo Plan",
            price=200000,
            description="Promo plan",
            order=1,
        )
        self.enrollment = Enrollment.objects.create(
            student=self.student,
            cohort=self.cohort,
            plan=self.plan,
            status=Enrollment.STATUS_PENDING,
        )
        self.campaign = PromoCampaign.objects.create(
            name="Spring Promo",
            status=PromoCampaign.STATUS_ACTIVE,
            discount_type=PromoCampaign.DISCOUNT_PERCENT,
            discount_value=15,
        )
        self.campaign.applicable_courses.add(self.course)
        self.code = PromoCode.objects.create(
            campaign=self.campaign,
            code="SPRING15",
        )

    def test_percent_discount_quote_is_calculated_correctly(self):
        quote = build_promo_quote(
            student=self.student,
            enrollment=self.enrollment,
            plan=self.plan,
            raw_code="spring15",
        )

        self.assertEqual(str(quote.base_amount), "200000.00")
        self.assertEqual(str(quote.discount_amount), "30000.00")
        self.assertEqual(str(quote.final_amount), "170000.00")
        self.assertEqual(quote.promo_code, self.code)

    def test_assigned_code_rejects_other_users(self):
        other_student = User.objects.create_user(
            username="other-promo-student",
            email="other-promo-student@example.com",
            password="testpass123",
        )
        self.code.assigned_to = other_student
        self.code.save(update_fields=["assigned_to"])

        with self.assertRaises(PromoValidationError) as exc:
            build_promo_quote(
                student=self.student,
                enrollment=self.enrollment,
                plan=self.plan,
                raw_code=self.code.code,
            )

        self.assertEqual(exc.exception.code, "assigned_user")

    def test_campaign_and_code_limits_are_enforced(self):
        self.campaign.max_total_redemptions = 1
        self.campaign.max_redemptions_per_user = 1
        self.campaign.save(update_fields=["max_total_redemptions", "max_redemptions_per_user"])
        PromoRedemption.objects.create(
            promo_code=self.code,
            campaign=self.campaign,
            student=self.student,
            enrollment=self.enrollment,
            status=PromoRedemption.STATUS_APPLIED,
            original_amount=200000,
            discount_amount=30000,
            final_amount=170000,
            code_snapshot=self.code.code,
            campaign_name_snapshot=self.campaign.name,
            discount_type_snapshot=self.campaign.discount_type,
            discount_value_snapshot=self.campaign.discount_value,
        )

        with self.assertRaises(PromoValidationError) as exc:
            build_promo_quote(
                student=self.student,
                enrollment=self.enrollment,
                plan=self.plan,
                raw_code=self.code.code,
            )

        self.assertIn(exc.exception.code, {"campaign_usage_limit", "campaign_user_limit"})

    def test_renewal_flag_is_enforced(self):
        self.campaign.allow_on_renewals = False
        self.campaign.save(update_fields=["allow_on_renewals"])
        self.enrollment.receipts.create(
            receipt_image="receipts/test.png",
            amount=200000,
            base_amount=200000,
            discount_amount=0,
            is_verified=True,
        )

        with self.assertRaises(PromoValidationError) as exc:
            build_promo_quote(
                student=self.student,
                enrollment=self.enrollment,
                plan=self.plan,
                raw_code=self.code.code,
            )

        self.assertEqual(exc.exception.code, "renewal_not_allowed")

    def test_first_purchase_only_checks_verified_payment_history(self):
        self.campaign.applies_to_first_purchase_only = True
        self.campaign.save(update_fields=["applies_to_first_purchase_only"])
        self.enrollment.receipts.create(
            receipt_image="receipts/verified.png",
            amount=200000,
            base_amount=200000,
            discount_amount=0,
            is_verified=True,
        )

        with self.assertRaises(PromoValidationError) as exc:
            build_promo_quote(
                student=self.student,
                enrollment=self.enrollment,
                plan=self.plan,
                raw_code=self.code.code,
            )

        self.assertEqual(exc.exception.code, "first_purchase_only")

    def test_generate_promo_codes_creates_unique_single_use_codes(self):
        created_codes = generate_promo_codes(
            campaign=self.campaign,
            count=5,
            prefix="SPR-",
            single_use=True,
        )

        self.assertEqual(len(created_codes), 5)
        self.assertEqual(
            PromoCode.objects.filter(campaign=self.campaign, max_redemptions=1).count(),
            5,
        )
        self.assertEqual(
            len({promo.normalized_code for promo in PromoCode.objects.filter(campaign=self.campaign)}),
            PromoCode.objects.filter(campaign=self.campaign).count(),
        )

    def test_code_and_campaign_time_windows_are_enforced(self):
        self.campaign.start_at = timezone.now() + datetime.timedelta(days=1)
        self.campaign.save(update_fields=["start_at"])
        with self.assertRaises(PromoValidationError) as exc:
            build_promo_quote(
                student=self.student,
                enrollment=self.enrollment,
                plan=self.plan,
                raw_code=self.code.code,
            )
        self.assertEqual(exc.exception.code, "campaign_not_started")

        self.campaign.start_at = None
        self.campaign.end_at = timezone.now() - datetime.timedelta(days=1)
        self.campaign.save(update_fields=["start_at", "end_at"])
        with self.assertRaises(PromoValidationError) as exc:
            build_promo_quote(
                student=self.student,
                enrollment=self.enrollment,
                plan=self.plan,
                raw_code=self.code.code,
            )
        self.assertEqual(exc.exception.code, "campaign_expired")
