import importlib
from types import SimpleNamespace
from unittest.mock import patch

from django.apps import apps
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from django.utils import timezone

from aicontrol.models import AIPlanPolicy, SystemAuditEvent
from bot.services import list_plans
from cohorts.models import Cohort, Enrollment
from courses.models import Course
from subscriptions.catalog import purchase_plans
from subscriptions.catalog_service import save_cohort, update_plan
from subscriptions.models import Plan, PlanFeature
from users.models import CustomUser


class CatalogTests(TestCase):
    def setUp(self):
        self.owner = CustomUser.objects.create_superuser(username="catalog-owner", email="owner@example.test", password="test")
        self.student = CustomUser.objects.create_user(username="catalog-user", email="user@example.test")
        self.plan = Plan.objects.get(code="standard")
        self.course = Course.objects.create(title="Catalog", description="d", level="beginner", instructor=self.owner)

    def data(self, **changes):
        result = {
            "name": self.plan.name, "price": "270000", "description": "To'liq darslar",
            "is_popular": "on", "button_text": "Tanlash", "order": "2",
            "features_text": "Darslar\nSertifikat\n- Hali yo'q",
            "change_reason": "Owner tasdiqlagan narx", "confirm_change": "on",
        }
        result.update(changes)
        return result

    def cohort_data(self, **changes):
        result = {
            "name": "Standard guruh", "course": str(self.course.pk), "plan": str(self.plan.pk),
            "capacity": "", "start_date": timezone.localdate().isoformat(), "is_active": "on",
            "is_checkout_default": "on", "change_reason": "Guruh tayyor", "confirm_change": "on",
        }
        result.update(changes)
        return result

    def test_three_seeded_prices_policies_drafts_and_recommended_standard(self):
        for code, price, capacity, short, weekly in (
            ("economic", 89000, 60, 50000, 300000), ("standard", 259000, 8, 100000, 800000),
            ("intensive", 399000, 3, 200000, 1500000),
        ):
            plan = Plan.objects.get(code=code)
            self.assertEqual((plan.price, plan.cohort_capacity_limit), (price, capacity))
            self.assertEqual((plan.ai_policy.token_limit_5h, plan.ai_policy.token_limit_weekly), (short, weekly))
            self.assertEqual(plan.is_popular, code == "standard")
            self.assertFalse(plan.is_available_for_purchase)
            self.assertNotIn(plan.pk, purchase_plans().values_list("pk", flat=True))
            self.assertTrue(plan.features.exists())

    def test_public_web_and_bot_hide_archived_plans(self):
        hidden = {plan.pk for plan in Plan.objects.filter(is_available_for_purchase=False)}
        self.assertFalse(hidden.intersection(p["id"] for p in list_plans()))
        response = self.client.get(reverse("subscriptions:pricing"))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(hidden.intersection(p.pk for p in response.context["plans"]))

    def test_code_and_delivery_limit_do_not_change_on_rename(self):
        self.plan.name = "Yangi nom"
        self.plan.save(update_fields=["name"])
        self.assertEqual(Plan.objects.get(pk=self.plan.pk).code, "standard")
        self.plan.code = "renamed"
        with self.assertRaises(ValidationError):
            self.plan.save()
        self.plan.refresh_from_db()
        self.plan.cohort_capacity_limit = 9
        with self.assertRaises(ValidationError):
            self.plan.save()

    def test_owner_edits_price_features_with_audit_without_legacy_admin(self):
        self.client.force_login(self.owner)
        response = self.client.post(reverse("backoffice_plan_edit", args=[self.plan.pk]), self.data())
        self.assertEqual(response.status_code, 302)
        self.plan.refresh_from_db()
        self.assertEqual(self.plan.price, 270000)
        self.assertEqual(list(self.plan.features.values_list("name", "is_included")), [("Darslar", True), ("Sertifikat", True), ("Hali yo'q", False)])
        audit = SystemAuditEvent.objects.get(action="catalog.plan.update")
        self.assertEqual(audit.before["price"], "259000")
        self.assertEqual(audit.after["price"], "270000")

    def test_reason_and_confirmation_are_required_and_unknown_fields_ignored(self):
        form = update_plan(actor=self.owner, plan_id=self.plan.pk, data=self.data(confirm_change=""))
        self.assertFalse(form.is_valid())
        form = update_plan(actor=self.owner, plan_id=self.plan.pk, data=self.data(change_reason=""))
        self.assertFalse(form.is_valid())
        self.plan.refresh_from_db()
        self.assertEqual(self.plan.price, 259000)
        self.assertFalse(SystemAuditEvent.objects.filter(action="catalog.plan.update").exists())
        form = update_plan(actor=self.owner, plan_id=self.plan.pk, data=self.data(code="forged", cohort_capacity_limit="1000"))
        self.assertTrue(form.is_valid(), form.errors)
        self.plan.refresh_from_db()
        self.assertEqual((self.plan.code, self.plan.cohort_capacity_limit), ("standard", 8))

    def test_staff_student_inactive_owner_and_service_cannot_edit_catalog(self):
        staff = CustomUser.objects.create_user(username="catalog-staff", email="staff@example.test", is_staff=True)
        inactive = CustomUser.objects.create_user(username="inactive-owner", email="inactive@example.test", is_superuser=True, is_active=False)
        for actor in (staff, self.student, inactive):
            with self.assertRaises(PermissionDenied):
                update_plan(actor=actor, plan_id=self.plan.pk, data=self.data())
        for actor in (staff, self.student):
            self.client.force_login(actor)
            self.assertEqual(self.client.post(reverse("backoffice_plan_edit", args=[self.plan.pk]), self.data()).status_code, 403)
        self.plan.refresh_from_db()
        self.assertEqual(self.plan.price, 259000)

    def test_audit_failure_rolls_back_price_and_features(self):
        before = list(self.plan.features.values_list("name", "is_included", "order"))
        with patch("subscriptions.catalog_service.record_audit_event", side_effect=RuntimeError("audit offline")):
            with self.assertRaises(RuntimeError):
                update_plan(actor=self.owner, plan_id=self.plan.pk, data=self.data())
        self.plan.refresh_from_db()
        self.assertEqual(self.plan.price, 259000)
        self.assertEqual(list(self.plan.features.values_list("name", "is_included", "order")), before)

    def test_owner_must_create_matching_group_before_publishing(self):
        form = update_plan(actor=self.owner, plan_id=self.plan.pk, data=self.data(is_available_for_purchase="on"))
        self.assertFalse(form.is_valid())
        self.assertIn("is_available_for_purchase", form.errors)
        form = save_cohort(actor=self.owner, data=self.cohort_data())
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.instance.capacity, 8)
        self.assertTrue(SystemAuditEvent.objects.filter(action="catalog.cohort.save").exists())
        form = update_plan(actor=self.owner, plan_id=self.plan.pk, data=self.data(is_available_for_purchase="on"))
        self.assertTrue(form.is_valid(), form.errors)
        self.assertIn(self.plan.pk, purchase_plans().values_list("pk", flat=True))

    def test_cohort_form_reports_tier_capacity_errors_without_500(self):
        self.client.force_login(self.owner)
        response = self.client.post(reverse("backoffice_cohort_create"), self.cohort_data(capacity="9"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("capacity", response.context["form"].errors)
        self.assertFalse(Cohort.objects.filter(plan=self.plan).exists())

    def test_seed_replay_preserves_owner_changes_and_does_not_duplicate_features(self):
        seed = importlib.import_module("subscriptions.migrations.0007_seed_delivery_catalog").seed_catalog
        self.plan.price = 277000
        self.plan.save(update_fields=["price"])
        AIPlanPolicy.objects.filter(plan=self.plan).update(token_limit_weekly=456)
        count = PlanFeature.objects.count()
        seed(apps, SimpleNamespace(connection=connection))
        self.plan.refresh_from_db()
        self.assertEqual(self.plan.price, 277000)
        self.assertEqual(self.plan.ai_policy.token_limit_weekly, 456)
        self.assertEqual(PlanFeature.objects.count(), count)


class CatalogMigrationTests(TransactionTestCase):
    def test_existing_rows_and_colliding_owner_code_are_not_rewritten(self):
        executor = MigrationExecutor(connection)
        latest = executor.loader.graph.leaf_nodes()
        self.addCleanup(lambda: MigrationExecutor(connection).migrate(latest))
        previous = [node for node in latest if node[0] not in {"cohorts", "subscriptions"}] + [
            ("cohorts", "0016_payment_plan_snapshot"), ("subscriptions", "0005_plan_code"),
        ]
        executor.migrate(previous)
        old = executor.loader.project_state(previous).apps
        OldPlan = old.get_model("subscriptions", "Plan")
        # Reverse seeding is deliberately non-destructive; recreate an old
        # installation's owner-created code using historical models.
        plan, _ = OldPlan.objects.update_or_create(code="economic", defaults={"name": "Owner's old plan", "price": 12345})
        OldPolicy = old.get_model("aicontrol", "AIPlanPolicy")
        OldPolicy.objects.update_or_create(plan=plan, defaults={"token_limit_5h": 17, "token_limit_weekly": 71})
        user = old.get_model("users", "CustomUser").objects.create(username="catalog-legacy", email="legacy@example.test")
        course = old.get_model("courses", "Course").objects.create(title="Legacy", description="d", level="beginner")
        cohort = old.get_model("cohorts", "Cohort").objects.create(name="Unchanged", course=course, start_date=timezone.localdate(), is_checkout_default=True)
        enrollment = old.get_model("cohorts", "Enrollment").objects.create(student=user, cohort=cohort, plan=plan, status="active")
        receipt = old.get_model("cohorts", "PaymentReceipt").objects.create(enrollment=enrollment, plan=plan, amount=12345, is_verified=True, plan_code_snapshot="economic", plan_name_snapshot="Historic", plan_price_snapshot=12345)
        executor = MigrationExecutor(connection)
        executor.migrate(latest)
        new = executor.loader.project_state(latest).apps
        migrated = new.get_model("subscriptions", "Plan").objects.get(pk=plan.pk)
        self.assertEqual((migrated.name, migrated.price), ("Owner's old plan", 12345))
        self.assertIsNone(migrated.cohort_capacity_limit)
        self.assertTrue(migrated.is_available_for_purchase)
        self.assertEqual(new.get_model("aicontrol", "AIPlanPolicy").objects.get(plan_id=plan.pk).token_limit_5h, 17)
        group = new.get_model("cohorts", "Cohort").objects.get(pk=cohort.pk)
        self.assertIsNone(group.plan_id)
        self.assertIsNone(group.capacity)
        self.assertTrue(group.is_checkout_default)
        self.assertEqual(new.get_model("cohorts", "Enrollment").objects.get(pk=enrollment.pk).plan_id, plan.pk)
        history = new.get_model("cohorts", "PaymentReceipt").objects.get(pk=receipt.pk)
        self.assertEqual((history.plan_name_snapshot, history.amount), ("Historic", 12345))
