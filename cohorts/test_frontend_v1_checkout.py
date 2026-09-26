"""V1 checkout uses the real catalog, receipt writer and access lifecycle."""
from datetime import timedelta
from decimal import Decimal
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from django.template.defaultfilters import floatformat

from core.flags import flag_by_slug, set_flag
from core.models import OperationalSettings
from subscriptions.models import Plan, PromoCampaign, PromoCode, PromoRedemption
from . import frontend_v1 as v1
from .models import Enrollment, PaymentReceipt
from .receipt_service import reject_receipt, verify_receipt
from .test_checkout_side_effects import CheckoutFixtureMixin, PNG_1X1


class CheckoutV1Tests(CheckoutFixtureMixin, TestCase):
    def setUp(self):
        self.build_course_with_cohort()
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        override = override_settings(PRIVATE_MEDIA_ROOT=self.temp.name, MEDIA_ROOT=self.temp.name)
        override.enable()
        self.addCleanup(override.disable)
        set_flag('frontend_v1_checkout', enabled=True, reason='Isolated checkout tests')
        self.client.force_login(self.student)
        self.url = reverse('cohorts:checkout', args=[self.course.pk])

    def form(self, promo=''):
        response = self.client.get(self.url, dict(plan_id=self.plan.pk, promo_code=promo))
        self.assertEqual(response.status_code, 200)
        return dict(frontend_v1_checkout='1', plan_id=str(self.plan.pk), promo_code=promo,
                    confirm_scope='yes', quote_token=response.context['quote_token'])

    def upload(self):
        return SimpleUploadedFile('check.png', PNG_1X1, content_type='image/png')

    def send(self, data=None, **extra):
        data = self.form() if data is None else data
        return self.client.post(self.url, dict(data, receipt_image=self.upload(), **extra))

    def receipt(self):
        self.assertEqual(self.send().status_code, 302)
        return PaymentReceipt.objects.get()

    def promo(self):
        campaign = PromoCampaign.objects.create(name='Sinov chegirmasi', status='active', discount_type='percent', discount_value=10)
        code = PromoCode.objects.create(campaign=campaign, code='SINOV10')
        return campaign, code

    def test_flag_default_off_and_legacy(self):
        self.assertFalse(flag_by_slug('frontend_v1_checkout').default)
        set_flag('frontend_v1_checkout', enabled=False, reason='Rollback')
        self.assertTemplateUsed(self.client.get(self.url), 'cohorts/checkout.html')

    def test_get_no_billing_writes_private_real_template(self):
        response = self.client.get(self.url)
        self.assertTemplateUsed(response, 'frontend_v1/checkout/form.html')
        self.assertIn('no-store', response['Cache-Control'])
        self.assertFalse(Enrollment.objects.exists())
        self.assertFalse(PaymentReceipt.objects.exists())
        self.assertNotContains(response, '/_preview/')
        self.assertNotContains(response, 'checkout-plan.js')
        self.assertContains(response, 'Summani tekshirish')

    def test_guest_login_and_csrf(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.get(self.url).status_code, 302)
        client.force_login(self.student)
        self.assertEqual(client.post(self.url, self.form()).status_code, 403)

    def test_invalid_and_repeated_plan_do_not_fallback(self):
        for suffix in ['?plan_id=²', '?plan_id=' + '9'*40, '?plan_id=999999', '?plan_id=1&plan_id=2', '?cohort=1']:
            with self.subTest(suffix=suffix):
                response = self.client.get(self.url + suffix)
                self.assertEqual(response.status_code, 400)
                self.assertNotContains(response, 'name="receipt_image"', status_code=400)
        self.assertFalse(Enrollment.objects.exists())

    def test_explicit_other_plan_preview(self):
        other = Plan.objects.create(name='Boshqa tarif', price=145000, order=2)
        response = self.client.get(self.url, dict(plan_id=other.pk))
        self.assertEqual(response.context['selected_plan'], other)
        self.assertEqual(response.context['promo_quote'].final_amount, Decimal('145000.00'))
        self.assertFalse(Enrollment.objects.exists())

    def test_no_plan_and_closed_cohort(self):
        self.cohort.is_active = False
        self.cohort.save(update_fields=['is_active'])
        self.assertEqual(self.client.get(self.url).status_code, 400)
        self.cohort.refresh_from_db()
        self.assertFalse(self.cohort.is_active)
        Plan.objects.all().delete()
        self.assertContains(self.client.get(self.url), 'Hozircha xarid uchun tarif mavjud emas')

    def test_native_upload_prg_and_pending_does_not_grant_access(self):
        receipt = self.receipt()
        self.assertFalse(receipt.is_verified)
        self.assertFalse(receipt.enrollment.has_active_access())
        response = self.client.get(reverse('cohorts:checkout_pending', args=[receipt.pk]))
        self.assertTemplateUsed(response, 'frontend_v1/checkout/status.html')
        self.assertContains(response, 'bu hali to‘lov tasdig‘i emas')
        self.assertContains(response, reverse('cohorts:receipt_file', args=[receipt.pk]))
        self.assertNotContains(response, '/media/' + receipt.receipt_image.name)
        self.assertEqual(receipt.amount, self.plan.price)

    def test_duplicate_post_returns_existing_receipt(self):
        data = self.form()
        first = self.send(data)
        second = self.send(data)
        self.assertEqual(first.url, second.url)
        self.assertEqual(PaymentReceipt.objects.count(), 1)
        self.assertEqual(Enrollment.objects.count(), 1)

    def test_upload_required_validated_and_confirmation_required(self):
        data = self.form()
        self.assertEqual(self.client.post(self.url, data).status_code, 400)
        self.assertEqual(self.client.post(self.url, dict(data, receipt_image=SimpleUploadedFile('fake.png', b'<html>bad'))).status_code, 400)
        data['confirm_scope'] = ''
        self.assertEqual(self.send(data).status_code, 400)
        self.assertFalse(Enrollment.objects.exists())

    def test_missing_or_tampered_quote(self):
        for token in ['', 'tampered']:
            data = self.form()
            data['quote_token'] = token
            self.assertEqual(self.send(data).status_code, 409)
        self.assertFalse(Enrollment.objects.exists())

    def test_expired_quote(self):
        data = self.form()
        with patch('django.core.signing.time.time', return_value=timezone.now().timestamp() + 2000):
            self.assertEqual(self.send(data).status_code, 409)
        self.assertFalse(Enrollment.objects.exists())

    def test_owner_can_shorten_existing_quote_lifetime(self):
        data = self.form()
        OperationalSettings.objects.update_or_create(pk=1, defaults={'checkout_quote_minutes': 1})
        response = self.client.get(self.url)
        self.assertContains(response, 'Tasdiq 1 daqiqa')
        with patch('django.core.signing.time.time', return_value=timezone.now().timestamp() + 65):
            self.assertEqual(self.send(data).status_code, 409)
        self.assertFalse(PaymentReceipt.objects.exists())

    def test_owner_can_extend_quote_lifetime_without_restart(self):
        data = self.form()
        OperationalSettings.objects.update_or_create(pk=1, defaults={'checkout_quote_minutes': 60})
        self.assertContains(self.client.get(self.url), 'Tasdiq 60 daqiqa')
        with patch('django.core.signing.time.time', return_value=timezone.now().timestamp() + 2000):
            self.assertEqual(self.send(data).status_code, 302)
        self.assertEqual(PaymentReceipt.objects.count(), 1)

    def test_quote_bound_to_user(self):
        data = self.form()
        self.client.force_login(self.teacher)
        self.assertEqual(self.send(data).status_code, 409)
        self.assertFalse(Enrollment.objects.exists())

    def test_changed_price_before_post(self):
        data = self.form()
        Plan.objects.filter(pk=self.plan.pk).update(price=110000)
        response = self.send(data)
        self.assertEqual(response.status_code, 409)
        self.assertFalse(response.context['quote_token'])
        self.assertFalse(Enrollment.objects.exists())

    def test_change_during_locked_write_rolls_back_new_enrollment(self):
        data = self.form()
        original = v1.resolve_checkout_enrollment
        def changed(**kwargs):
            result = original(**kwargs)
            Plan.objects.filter(pk=self.plan.pk).update(price=120000)
            return result
        with patch.object(v1, 'resolve_checkout_enrollment', side_effect=changed):
            self.assertEqual(self.send(data).status_code, 409)
        self.assertFalse(Enrollment.objects.exists())
        self.assertFalse(PaymentReceipt.objects.exists())

    def test_promo_and_receipt_snapshots(self):
        campaign, code = self.promo()
        response = self.send(self.form(code.code))
        self.assertEqual(response.status_code, 302)
        receipt = PaymentReceipt.objects.get()
        self.assertEqual(receipt.amount, Decimal('90000'))
        self.assertEqual(receipt.discount_amount, Decimal('10000'))
        self.assertEqual(PromoRedemption.objects.get().status, 'reserved')
        Plan.objects.filter(pk=self.plan.pk).update(name='Later name', price=170000)
        response = self.client.get(response.url)
        self.assertContains(response, 'A4 Plan')
        self.assertNotContains(response, 'Later name')

    def test_fractional_discount_keeps_exact_displayed_amount(self):
        _, code = self.promo()
        Plan.objects.filter(pk=self.plan.pk).update(price=100001)
        response = self.client.get(self.url, dict(plan_id=self.plan.pk, promo_code=code.code))
        self.assertEqual(response.context['promo_quote'].final_amount, Decimal('90000.90'))
        self.assertContains(response, floatformat(Decimal('90000.90'), 2))

    def test_bad_promo_preserves_input_without_quote(self):
        response = self.client.get(self.url, dict(plan_id=self.plan.pk, promo_code='BAD'))
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, 'value="BAD"', status_code=400)
        self.assertNotContains(response, 'name="receipt_image"', status_code=400)

    def test_changed_promo_does_not_reserve(self):
        campaign, code = self.promo()
        data = self.form(code.code)
        campaign.discount_value = 20
        campaign.save()
        self.assertEqual(self.send(data).status_code, 409)
        self.assertFalse(PromoRedemption.objects.exists())
        self.assertFalse(Enrollment.objects.exists())

    def test_receipt_owner_scope_and_private_file(self):
        receipt = self.receipt()
        other = get_user_model().objects.create_user('foreign')
        self.client.force_login(other)
        for name in ['checkout_pending', 'checkout_success', 'receipt_file']:
            self.assertEqual(self.client.get(reverse('cohorts:' + name, args=[receipt.pk])).status_code, 404)

    def test_receipt_status_link_from_records_respects_flag(self):
        receipt = self.receipt()
        set_flag('frontend_v1_records', enabled=True, reason='Records link test')
        response = self.client.get(reverse('subscriptions'))
        self.assertContains(response, reverse('cohorts:checkout_pending', args=[receipt.pk]))
        set_flag('frontend_v1_checkout', enabled=False, reason='Rollback')
        self.assertNotContains(self.client.get(reverse('subscriptions')), 'natijasini ko‘rish')

    def test_status_redirects_follow_canonical_verification(self):
        receipt = self.receipt()
        pending = reverse('cohorts:checkout_pending', args=[receipt.pk])
        success = reverse('cohorts:checkout_success', args=[receipt.pk])
        self.assertRedirects(self.client.get(success), pending)
        owner = get_user_model().objects.create_superuser('test-owner', 'owner@example.test', 'testpass')
        self.assertTrue(verify_receipt(receipt.pk, owner).ok)
        self.assertRedirects(self.client.get(pending), success)
        response = self.client.get(success)
        self.assertContains(response, 'To‘lov tasdiqlandi')
        self.assertTrue(response.context['access_open'])
        self.assertTemplateUsed(self.client.get(reverse('cohorts:checkout_success_latest')), 'frontend_v1/checkout/status.html')

    def test_verified_but_frozen_is_not_claimed_open(self):
        receipt = self.receipt()
        receipt.is_verified = True
        receipt.save()
        Enrollment.objects.filter(pk=receipt.enrollment_id).update(status='frozen')
        response = self.client.get(reverse('cohorts:checkout_success', args=[receipt.pk]))
        self.assertContains(response, 'Hozir kursga kirish ruxsati faol emas')

    def test_difference_waiting_file_does_not_offer_new_period(self):
        enrollment = Enrollment.objects.create(student=self.student, cohort=self.cohort, status='pending')
        today = timezone.localdate()
        receipt = PaymentReceipt.objects.create(enrollment=enrollment, plan=self.plan, kind='difference', amount=5000, period_start=today, period_end=today+timedelta(days=30))
        response = self.client.get(reverse('cohorts:checkout_pending', args=[receipt.pk]))
        self.assertContains(response, 'Obunalarda chek yuborish')
        self.assertNotContains(response, 'Chek rasmini ochish')
        self.assertContains(self.client.get(self.url), 'Tekshiruvdagi chek mavjud')
        receipt.is_verified = True
        receipt.save()
        response = self.client.get(reverse('cohorts:checkout_success', args=[receipt.pk]))
        self.assertContains(response, 'obuna davrini alohida uzaytirmaydi')
        self.assertFalse(response.context['access_open'])

    def test_difference_upload_prg_no_replacement_or_access(self):
        enrollment = Enrollment.objects.create(student=self.student, cohort=self.cohort, status='pending')
        start, end = v1.checkout_period(enrollment)
        receipt = PaymentReceipt.objects.create(enrollment=enrollment, plan=self.plan, kind='difference', amount=5000, period_start=start, period_end=end)
        url = reverse('cohorts:difference_upload', args=[receipt.pk])
        first = self.client.post(url, dict(receipt_image=self.upload(), frontend_v1_checkout='1'))
        self.assertRedirects(first, reverse('cohorts:checkout_pending', args=[receipt.pk]))
        receipt.refresh_from_db()
        saved_name = receipt.receipt_image.name
        second = self.client.post(url, dict(receipt_image=self.upload(), frontend_v1_checkout='1'))
        self.assertEqual(first.url, second.url)
        receipt.refresh_from_db()
        self.assertEqual(receipt.receipt_image.name, saved_name)
        self.assertFalse(receipt.enrollment.has_active_access())
        self.assertEqual(receipt.amount, Decimal('5000'))
        receipt.is_verified = True
        receipt.save()
        self.assertEqual(self.client.post(url, dict(receipt_image=self.upload())).status_code, 404)

    def test_difference_image_gate_and_inflight_rollback(self):
        enrollment = Enrollment.objects.create(student=self.student, cohort=self.cohort, status='pending')
        start, end = v1.checkout_period(enrollment)
        receipt = PaymentReceipt.objects.create(enrollment=enrollment, plan=self.plan, kind='difference', amount=5000, period_start=start, period_end=end)
        url = reverse('cohorts:difference_upload', args=[receipt.pk])
        response = self.client.post(url, dict(receipt_image=SimpleUploadedFile('not-image.pdf', b'%PDF-1.4 test')))
        self.assertRedirects(response, reverse('subscriptions'))
        set_flag('frontend_v1_checkout', enabled=False, reason='Rollback')
        response = self.client.post(url, dict(receipt_image=self.upload(), frontend_v1_checkout='1'))
        self.assertRedirects(response, reverse('subscriptions'))
        receipt.refresh_from_db()
        self.assertFalse(receipt.receipt_image)

    def test_rejection_deletes_receipt_not_fake_rejected_state(self):
        receipt = self.receipt()
        owner = get_user_model().objects.create_superuser('test-owner', 'owner@example.test', 'testpass')
        self.assertTrue(reject_receipt(receipt.pk, owner, reason='Synthetic test').ok)
        self.assertEqual(self.client.get(reverse('cohorts:checkout_pending', args=[receipt.pk])).status_code, 404)
        self.assertFalse(PaymentReceipt.objects.exists())
        self.assertFalse(Enrollment.objects.get().has_active_access())

    def test_flag_off_inflight_post_no_write(self):
        data = self.form()
        set_flag('frontend_v1_checkout', enabled=False, reason='Rollback')
        self.assertEqual(self.send(data).status_code, 409)
        self.assertFalse(Enrollment.objects.exists())

    def test_post_plan_never_from_query_string(self):
        data = self.form()
        del data['plan_id']
        self.assertEqual(self.client.post(self.url + f'?plan_id={self.plan.pk}', dict(data, receipt_image=self.upload())).status_code, 400)
        self.assertFalse(Enrollment.objects.exists())
