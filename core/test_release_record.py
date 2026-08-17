"""A2 — qaysi release ishlayapti va bazasi unga mos keladimi.

`05-launch-ops.md` §4: "Har release uchun commit SHA, migrationlar, gate
natijalari, deploy/rollback holati va owner qarori `ReleaseRecord`/system
auditda saqlanadi."

Shulardan bugun **haqiqiy** bo'lgani va eng ko'p zarar keltirgani — migration
holati. Bu sessiyaning o'zida bir marta yuz berdi: kill switch sahifasi
`OperationalError` bilan yiqildi, chunki beshta migratsiya haqiqiy bazaga
qo'llanmagan edi. Kod yangi, baza eski — va buni hech narsa ko'rsatmasdi.
Control Center o'nta capability'ni yashil deb turardi.

Bu yerdagi bo'linish ataylab: **probe jonli holatni o'qiydi va hech narsa
yozmaydi** (bugun checkout sahifasidan aynan shu naqshni olib tashladik),
`ReleaseRecord` esa faqat aniq buyruqlar bilan yoziladi.
"""

from django.contrib.auth import get_user_model
from django.db.migrations.recorder import MigrationRecorder
from django.test import TestCase

from aicontrol.models import ReleaseRecord, SystemAuditEvent
from core.control_center import build_control_center_snapshot
from core.release_service import decide_release, migration_state, record_current_release

User = get_user_model()


def forget_a_migration(app_label="aicontrol"):
    """Ilovaning eng oxirgi migratsiyasini "qo'llanmagan" holatga keltiradi.

    Mock emas: Django migratsiya holatini shu jadvaldan o'qiydi, ya'ni bu
    haqiqiy "kod yangi, baza eski" holatini yasaydi.

    Aynan **leaf** o'chiriladi, o'rtadagi migratsiya emas: `migration_plan()`
    maqsad sifatida leaf tugunlarni oladi va leaf hamon qo'llangan bo'lsa
    o'rtadagi teshikni ko'rmaydi. Amalda ham shunday — `migrate` ketma-ket
    qo'llaydi, ya'ni o'rtada teshik qoldirib leafni yozib qo'yish holati
    normal ishlashdan kelib chiqmaydi.
    """
    from django.db import connections
    from django.db.migrations.executor import MigrationExecutor

    executor = MigrationExecutor(connections["default"])
    leaves = [node for node in executor.loader.graph.leaf_nodes() if node[0] == app_label]
    if not leaves:  # pragma: no cover
        raise AssertionError(f"{app_label} uchun leaf migratsiya topilmadi")
    app, name = leaves[0]
    MigrationRecorder.Migration.objects.filter(app=app, name=name).delete()
    return f"{app}.{name}"


class MigrationStateTests(TestCase):
    def test_a_fully_migrated_database_reports_nothing_pending(self):
        applied, unapplied = migration_state()

        self.assertGreater(applied, 0)
        self.assertEqual(unapplied, [])

    def test_a_missing_migration_is_detected_by_name(self):
        forgotten = forget_a_migration()

        _applied, unapplied = migration_state()

        self.assertIn(forgotten, unapplied)


class ReleaseCapabilityTests(TestCase):
    def _release_result(self):
        snapshot = build_control_center_snapshot()
        return next(item for item in snapshot.results if item.definition.slug == "release")

    def test_a_consistent_release_is_green(self):
        self.assertEqual(self._release_result().status, "green")

    def test_unapplied_migrations_turn_the_release_red(self):
        """Asl hodisa: kod yangi, baza eski — va buni hech narsa ko'rsatmasdi."""
        forget_a_migration()

        result = self._release_result()

        self.assertEqual(result.status, "red")
        self.assertIn("migratsiya", result.summary.lower())

    def test_the_probe_writes_nothing(self):
        """Probe o'qish amali — snapshot ko'rish yozuv qoldirmasligi kerak."""
        build_control_center_snapshot()

        self.assertEqual(ReleaseRecord.objects.count(), 0)


class RecordCurrentReleaseTests(TestCase):
    def test_recording_captures_the_sha_and_migration_state(self):
        record = record_current_release(commit_sha="abc123def456")

        self.assertEqual(record.commit_sha, "abc123def456")
        self.assertGreater(record.migrations_applied, 0)
        self.assertEqual(record.unapplied_migrations, [])
        self.assertEqual(record.decision, ReleaseRecord.DECISION_PENDING)

    def test_recording_the_same_sha_twice_updates_one_row(self):
        record_current_release(commit_sha="abc123def456")
        record_current_release(commit_sha="abc123def456")

        self.assertEqual(ReleaseRecord.objects.count(), 1)

    def test_recording_a_release_with_pending_migrations_says_so(self):
        forgotten = forget_a_migration()

        record = record_current_release(commit_sha="broken000000")

        self.assertIn(forgotten, record.unapplied_migrations)
        self.assertFalse(record.is_consistent)

    def test_gate_results_are_stored_when_supplied(self):
        """CI natijalari uzatilsa saqlanadi; bugun ularni yozadigan quvur yo'q."""
        record = record_current_release(
            commit_sha="abc123def456",
            gate_results={"checks": "success", "integration": "success"},
        )

        self.assertEqual(record.gate_results["integration"], "success")


class ReleaseDecisionTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_superuser(
            username="rel-owner", email="rel-owner@example.com", password="x"
        )
        self.record = record_current_release(commit_sha="abc123def456")

    def test_the_owner_decision_is_stored(self):
        updated = decide_release(
            commit_sha="abc123def456",
            decision=ReleaseRecord.DECISION_GO,
            actor=self.owner,
            note="demo uchun ochildi",
        )

        self.assertEqual(updated.decision, ReleaseRecord.DECISION_GO)
        self.assertEqual(updated.decided_by, self.owner)
        self.assertEqual(updated.note, "demo uchun ochildi")

    def test_the_decision_is_written_to_the_audit_ledger(self):
        decide_release(
            commit_sha="abc123def456",
            decision=ReleaseRecord.DECISION_ROLLED_BACK,
            actor=self.owner,
            note="checkout yiqildi",
        )

        event = SystemAuditEvent.objects.get(action="release.decision")
        self.assertEqual(event.actor_label, "rel-owner")
        self.assertEqual(event.after["decision"], ReleaseRecord.DECISION_ROLLED_BACK)
        self.assertEqual(event.reason, "checkout yiqildi")

    def test_an_unchanged_decision_writes_no_audit_event(self):
        decide_release(
            commit_sha="abc123def456",
            decision=ReleaseRecord.DECISION_GO,
            actor=self.owner,
        )
        SystemAuditEvent.objects.all().delete()

        decide_release(
            commit_sha="abc123def456",
            decision=ReleaseRecord.DECISION_GO,
            actor=self.owner,
        )

        self.assertEqual(SystemAuditEvent.objects.count(), 0)

    def test_deciding_on_an_unknown_release_is_refused(self):
        from core.release_service import ReleaseNotRecorded

        with self.assertRaises(ReleaseNotRecorded):
            decide_release(
                commit_sha="hech-qachon-korilmagan",
                decision=ReleaseRecord.DECISION_GO,
                actor=self.owner,
            )
