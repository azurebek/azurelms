"""Upgrade an actual old schema without inventing paid-history snapshots."""

import datetime

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from django.utils import timezone


class PaymentPlanMigrationTests(TransactionTestCase):
    def test_existing_payments_and_open_intents_survive_the_additive_migration(self):
        executor = MigrationExecutor(connection)
        latest = executor.loader.graph.leaf_nodes()
        self.addCleanup(lambda: MigrationExecutor(connection).migrate(latest))
        # Faqat cohorts ortga qaytadi; boshqa app modellari bazada qolgan
        # schema bilan bir xil holatda bo'lishi kerak (xususan CustomUser).
        previous = [node for node in latest if node[0] != "cohorts"] + [
            ("cohorts", "0015_enrollment_checkout_started_at"),
        ]
        executor.migrate(previous)
        apps = executor.loader.project_state(previous).apps
        User = apps.get_model("users", "CustomUser")
        Plan = apps.get_model("subscriptions", "Plan")
        Course = apps.get_model("courses", "Course")
        Cohort = apps.get_model("cohorts", "Cohort")
        Enrollment = apps.get_model("cohorts", "Enrollment")
        Receipt = apps.get_model("cohorts", "PaymentReceipt")
        plan = Plan.objects.create(name="Legacy now", code="legacy-now", price=499000)
        course = Course.objects.create(title="Migration", description="d", level="beginner")
        cohort = Cohort.objects.create(name="Migration group", course=course, start_date=timezone.localdate())
        now = timezone.now()
        enrollment_ids = []
        for index in range(3):
            user = User.objects.create(username=f"legacy-{index}", email=f"legacy-{index}@example.test")
            enrollment = Enrollment.objects.create(
                student=user, cohort=cohort, plan=plan, status="active",
                checkout_started_at=now - datetime.timedelta(minutes=5),
            )
            enrollment_ids.append(enrollment.pk)
        paid = Receipt.objects.create(
            enrollment_id=enrollment_ids[0], amount=89000, base_amount=99000, discount_amount=10000, is_verified=True,
        )
        pending = Receipt.objects.create(
            enrollment_id=enrollment_ids[1], amount=259000, base_amount=259000, is_verified=False,
        )
        executor = MigrationExecutor(connection)
        executor.migrate(latest)
        new_apps = executor.loader.project_state(latest).apps
        NewReceipt = new_apps.get_model("cohorts", "PaymentReceipt")
        NewEnrollment = new_apps.get_model("cohorts", "Enrollment")
        history = NewReceipt.objects.get(pk=paid.pk)
        self.assertEqual(history.amount, 89000)
        self.assertEqual(history.base_amount, 99000)
        self.assertIsNone(history.plan_id)
        self.assertEqual(history.plan_name_snapshot, "")
        self.assertEqual(history.plan_snapshot_source, "legacy")
        open_receipt = NewReceipt.objects.get(pk=pending.pk)
        self.assertEqual(open_receipt.plan_id, plan.pk)
        self.assertEqual(open_receipt.plan_price_snapshot, 259000)  # not today's 499000
        self.assertEqual(open_receipt.plan_snapshot_source, "legacy")
        completed = NewEnrollment.objects.get(pk=enrollment_ids[0])
        self.assertIsNone(completed.pending_plan_id)
        self.assertIsNone(completed.checkout_started_at)
        for pk in enrollment_ids[1:]:
            enrollment = NewEnrollment.objects.get(pk=pk)
            self.assertEqual(enrollment.plan_id, plan.pk)  # no silent paid-plan migration
            self.assertEqual(enrollment.pending_plan_id, plan.pk)
