"""Typed theme safety, durable state transitions and owner isolation."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
from threading import Barrier
from unittest.mock import patch
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ValidationError
from django.db import DatabaseError, close_old_connections, connection
from django.test import SimpleTestCase, TestCase, TransactionTestCase, override_settings, skipUnlessDBFeature
from django.test.utils import CaptureQueriesContext

from aicontrol.models import SystemAuditEvent
from core.design_models import DesignDraft, DesignOperation, DesignPreset, DesignState, DesignVersion
from core.design_schema import CATALOG, FIELDS, DesignValidationError, compile_css, defaults, validate
from core.design_service import DesignError, execute, read_published, read_state
from core.flags import set_flag


class DesignSchemaTests(SimpleTestCase):
    def test_complete_catalog_defaults_are_safe_and_detached(self):
        value = defaults()
        self.assertEqual(len(FIELDS), 87)
        self.assertEqual(sum(len(value[section]) for section in ("light", "dark", "values")), 118)
        self.assertEqual(validate(value), value)
        value["light"]["surface"] = "#000000"
        self.assertEqual(defaults()["light"]["surface"], "#ffffff")

    def test_unknown_missing_and_future_schema_are_rejected(self):
        for transform in (
            lambda value: value.update(extra="ignored"),
            lambda value: value.update(version=2),
            lambda value: value.update(version=True),
            lambda value: value["values"].update(css="body{display:none}"),
            lambda value: value["dark"].pop("surface"),
        ):
            value = defaults()
            transform(value)
            with self.subTest(value=value), self.assertRaises(DesignValidationError):
                validate(value)

    def test_numbers_reject_boolean_nonfinite_offstep_oversized_and_css_values(self):
        for item in (True, False, float("nan"), float("inf"), -1, 100000, 10 ** 1000, 8.25, "8px", "url(https://example.test)"):
            value = defaults()
            value["values"]["button-radius"] = item
            with self.subTest(item=item), self.assertRaises(DesignValidationError):
                validate(value)

    def test_color_and_font_are_allowlisted_not_executable_content(self):
        for item in (None, "red", "#fff", "#000000;display:none", "</style><script>alert(1)</script>"):
            value = defaults()
            value["light"]["text"] = item
            with self.subTest(item=item), self.assertRaises(DesignValidationError):
                compile_css(value)
        value = defaults()
        value["values"]["body-font"] = "url(https://example.test/font.woff)"
        with self.assertRaises(DesignValidationError):
            validate(value)

    def test_deeply_nested_field_is_rejected_before_copying_untrusted_graph(self):
        nested = []
        for _ in range(1500):
            nested = [nested]
        value = defaults()
        value["values"]["button-radius"] = nested
        with self.assertRaises(DesignValidationError):
            validate(value)

    def test_equivalent_color_and_number_values_normalize(self):
        value = defaults()
        value["light"]["surface"] = "#FFFFFF"
        value["values"]["button-radius"] = 8.0
        normalized = validate(value)
        self.assertEqual(normalized["light"]["surface"], "#ffffff")
        self.assertIs(type(normalized["values"]["button-radius"]), int)
        self.assertEqual(value["light"]["surface"], "#FFFFFF")

    def test_contrast_checks_inherited_colors_and_both_modes(self):
        for mode in ("light", "dark"):
            value = defaults()
            value[mode]["surface"] = value[mode]["text"]
            with self.subTest(mode=mode), self.assertRaises(DesignValidationError):
                validate(value)
        value = defaults()
        value["dark"]["chat-own"] = value["dark"]["text"]
        with self.assertRaises(DesignValidationError):
            validate(value)

    def test_typography_hierarchy_and_readable_leading_are_enforced(self):
        value = defaults()
        value["values"]["text-xs"] = 16
        with self.assertRaises(DesignValidationError):
            validate(value)
        value = defaults()
        value["values"]["body-leading"] = 1.4
        with self.assertRaises(DesignValidationError):
            validate(value)

    def test_all_builtin_presets_validate_and_compile(self):
        for preset in CATALOG["presets"]:
            value = defaults()
            value["values"].update(preset["values"])
            with self.subTest(preset=preset["id"]):
                self.assertTrue(compile_css(value).startswith("@media screen{"))

    def test_compilation_has_mode_isolation_safe_units_and_optional_inheritance(self):
        value = defaults()
        value["values"].update({"text-md": 18, "button-radius": 24, "body-font": "serif", "overlay": 50})
        css = compile_css(value)
        self.assertTrue(css.startswith("@media screen{"))
        self.assertIn(':root:not([data-theme="dark"]){', css)
        self.assertIn(':root[data-theme="dark"]{', css)
        self.assertIn("--az-text-md:1.125rem;", css)
        self.assertIn("--dc-text-md:1.125rem;", css)
        self.assertIn("--dc-button-radius:24px;", css)
        self.assertIn('--az-font:Georgia, "Times New Roman", serif;', css)
        self.assertIn("--dc-overlay:rgb(0 0 0 / 50%);", css)
        self.assertNotIn("--dc-card-radius:", css)
        self.assertNotIn("--dc-text-sm:", css)
        self.assertNotIn("@import", css)


@override_settings(GEMINI_API_KEY="", TELEGRAM_BOT_TOKEN="")
class DesignServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.owner = User.objects.create_user("design-owner", "design-owner@example.test", is_staff=True, is_superuser=True)
        cls.other = User.objects.create_user("design-other", "design-other@example.test", is_staff=True, is_superuser=True)
        cls.staff = User.objects.create_user("design-staff", "design-staff@example.test", is_staff=True)
        cls.learner = User.objects.create_user("design-learner", "design-learner@example.test")

    def setUp(self):
        set_flag("backoffice_design_workspace", enabled=True, reason="Design regression")

    def value(self, radius=24):
        value = defaults()
        value["values"]["button-radius"] = radius
        return value

    def call(self, command, payload, *, actor=None, operation=None):
        return execute(actor or self.owner, command, operation or str(uuid4()), payload)

    def draft(self, *, actor=None, radius=24):
        actor = actor or self.owner
        state = read_state(actor)
        return self.call("save_draft", {"value": self.value(radius), "draft_revision": state["draft"]["revision"],
                                        "base_version": state["published"]["version"]}, actor=actor)

    def publish(self, *, actor=None, operation=None):
        actor = actor or self.owner
        state = read_state(actor)
        return self.call("publish", {"draft_revision": state["draft"]["revision"], "base_version": state["published"]["version"],
                                     "reason": "Ko‘rinish tasdiqlandi", "confirmed": True}, actor=actor, operation=operation)

    def assert_error(self, code, callback):
        with self.assertRaises(DesignError) as failure:
            callback()
        self.assertEqual(failure.exception.code, code)
        return failure.exception

    def audit_count(self):
        return SystemAuditEvent.objects.filter(action__startswith="design.").count()

    def test_empty_reads_create_no_design_rows_and_are_json_serializable(self):
        with CaptureQueriesContext(connection) as queries:
            state = read_state(self.owner)
            published = read_published()
        self.assertEqual(state["published"]["version"], 0)
        self.assertEqual(state["draft"], {"revision": 0, "base_version": 0, "value": defaults()})
        self.assertEqual(published, {"version": 0, "value": defaults()})
        self.assertEqual(state["presets"], [])
        self.assertIsNone(state["receipt"])
        json.dumps(state)
        self.assertFalse(any(query["sql"].lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE")) for query in queries))
        for model in (DesignState, DesignDraft, DesignVersion, DesignOperation, DesignPreset):
            self.assertFalse(model.objects.exists())

    def test_owner_permission_is_fresh_for_reads_and_mutations(self):
        for actor, code in ((AnonymousUser(), "anonymous"), (self.staff, "forbidden"), (self.learner, "forbidden")):
            with self.subTest(actor=actor):
                self.assert_error(code, lambda: read_state(actor))
                self.assert_error(code, lambda: self.draft(actor=actor))
        get_user_model().objects.filter(pk=self.owner.pk).update(is_superuser=False)
        self.assert_error("forbidden", lambda: read_state(self.owner))
        self.assert_error("forbidden", lambda: self.call("save_preset", {"name": "Safe", "value": defaults()}))
        get_user_model().objects.filter(pk=self.other.pk).update(is_active=False)
        self.assert_error("forbidden", lambda: read_state(self.other))
        self.assertFalse(DesignState.objects.exists())

    def test_flag_off_rejects_in_flight_mutation_and_keeps_saved_state(self):
        saved = self.draft()
        set_flag("backoffice_design_workspace", enabled=False, reason="Rollback")
        self.assert_error("disabled", lambda: self.publish())
        self.assertEqual(read_state(self.owner)["draft"], saved["state"]["draft"])
        self.assertEqual(read_published(), {"version": 0, "value": defaults()})
        self.assertFalse(DesignVersion.objects.exists())

    def test_exact_payload_fields_and_integer_revisions_are_required(self):
        valid = {"value": self.value(), "draft_revision": 0, "base_version": 0}
        cases = [("save_draft", {**valid, "actor": self.other.pk}),
                 ("save_draft", {**valid, "base_version": True}),
                 ("save_draft", {**valid, "draft_revision": -1}),
                 ("save_draft", {key: value for key, value in valid.items() if key != "base_version"}),
                 ("bad", {}), ([], {}), ("delete_preset", {"preset_id": True})]
        for command, payload in cases:
            with self.subTest(command=command, payload=payload):
                self.assert_error("invalid", lambda: self.call(command, payload))
        self.assertFalse(DesignState.objects.exists())

    def test_draft_persists_privately_without_publication(self):
        result = self.draft()
        self.assertEqual(result["result"]["kind"], "saved")
        self.assertEqual(result["state"]["draft"]["revision"], 1)
        self.assertEqual(read_state(self.owner)["draft"]["value"], self.value())
        self.assertEqual(read_state(self.other)["draft"]["value"], defaults())
        self.assertEqual(read_published()["value"], defaults())
        self.assertEqual(self.audit_count(), 1)
        self.assertEqual(DesignOperation.objects.count(), 1)
        self.assertFalse(DesignVersion.objects.exists())

    def test_stale_draft_cannot_overwrite_saved_input(self):
        self.draft()
        self.assert_error("stale", lambda: self.call("save_draft", {
            "value": self.value(12), "draft_revision": 0, "base_version": 0}))
        self.assertEqual(read_state(self.owner)["draft"]["value"], self.value())
        self.assertEqual(DesignOperation.objects.count(), 1)

    def test_equivalent_save_is_noop_but_has_durable_receipt(self):
        self.draft(radius=8)
        value = self.value(8.0)
        value["light"]["surface"] = "#FFFFFF"
        result = self.call("save_draft", {"value": value, "draft_revision": 1, "base_version": 0})
        self.assertEqual(result["result"]["kind"], "noop")
        self.assertEqual(result["state"]["draft"]["revision"], 1)
        self.assertEqual(self.audit_count(), 1)
        self.assertEqual(DesignOperation.objects.count(), 2)

    def test_publish_requires_saved_draft_reason_and_explicit_confirmation(self):
        self.assert_error("draft_required", lambda: self.publish())
        self.assertFalse(DesignState.objects.exists())
        self.draft()
        for reason, confirmation in (("", True), ("ab", True), ("x" * 241, True), ("a\nb", True), ("Valid", 1), ("Valid", False)):
            with self.subTest(reason=reason, confirmation=confirmation):
                self.assert_error("invalid", lambda: self.call("publish", {
                    "draft_revision": 1, "base_version": 0, "reason": reason, "confirmed": confirmation}))
        self.assertFalse(DesignVersion.objects.exists())

    def test_publish_atomically_records_factory_history_audit_and_receipt(self):
        draft = self.draft()["state"]["draft"]
        operation = str(uuid4())
        result = self.publish(operation=operation)
        self.assertEqual(result["result"]["kind"], "published")
        self.assertEqual(result["result"]["version"], 1)
        self.assertEqual(result["state"]["draft"], draft)
        self.assertEqual([item["version"] for item in result["state"]["history"]], [1, 0])
        self.assertEqual(DesignState.objects.get().current_version.number, 1)
        self.assertEqual(DesignVersion.objects.get(number=0).value, defaults())
        self.assertEqual(read_state(self.owner, operation=operation)["receipt"]["result"], result["result"])
        event = SystemAuditEvent.objects.get(action="design.publish")
        self.assertEqual(event.idempotency_key, operation)
        self.assertEqual(event.actor_id, self.owner.pk)
        json.dumps(result)

    def test_publishing_same_as_current_is_noop_without_history_or_audit_growth(self):
        self.call("save_draft", {"value": defaults(), "draft_revision": 0, "base_version": 0})
        audits = self.audit_count()
        result = self.publish()
        self.assertEqual(result["result"]["kind"], "noop")
        self.assertEqual(result["result"]["version"], 0)
        self.assertFalse(DesignVersion.objects.exists())
        self.assertEqual(self.audit_count(), audits)
        self.assertEqual(DesignOperation.objects.count(), 2)

    def test_published_base_conflict_requires_explicit_rebase_and_preserves_draft(self):
        saved = self.draft()["state"]["draft"]
        self.draft(actor=self.other, radius=12)
        self.publish(actor=self.other)
        self.assert_error("stale", lambda: self.publish())
        self.assert_error("stale", lambda: self.call("save_draft", {
            "value": self.value(), "draft_revision": 1, "base_version": 0}))
        self.assertEqual(read_state(self.owner)["draft"], saved)
        rebased = self.call("save_draft", {"value": self.value(), "draft_revision": 1, "base_version": 1})
        self.assertEqual(rebased["state"]["draft"]["revision"], 2)
        self.assertEqual(rebased["state"]["draft"]["base_version"], 1)
        self.assertEqual(self.publish()["result"]["version"], 2)

    def test_durable_replay_returns_original_result_before_stale_checks(self):
        self.draft()
        operation = str(uuid4())
        payload = {"draft_revision": 1, "base_version": 0, "reason": "Ko‘rinish tasdiqlandi", "confirmed": True}
        original = self.call("publish", payload, operation=operation)
        self.draft(actor=self.other, radius=12)
        self.publish(actor=self.other)
        audits, receipts = self.audit_count(), DesignOperation.objects.count()
        replay = self.call("publish", payload, operation=operation)
        self.assertEqual(replay["result"], original["result"])
        self.assertEqual(replay["state"]["published"]["version"], 2)
        self.assertEqual(self.audit_count(), audits)
        self.assertEqual(DesignOperation.objects.count(), receipts)

    def test_operation_reuse_conflicts_but_operations_and_readback_are_owner_private(self):
        operation = str(uuid4())
        payload = {"value": self.value(), "draft_revision": 0, "base_version": 0}
        first = self.call("save_draft", payload, operation=operation)
        self.assert_error("idempotency_conflict", lambda: self.call("save_draft", {
            **payload, "value": self.value(12)}, operation=operation))
        self.assertIsNone(read_state(self.other, operation=operation)["receipt"])
        second = self.call("save_draft", payload, actor=self.other, operation=operation)
        self.assertEqual(first["result"]["operation"], second["result"]["operation"])
        self.assertEqual(DesignOperation.objects.filter(operation=operation).count(), 2)

    def test_rollback_adds_version_retains_draft_and_can_be_noop(self):
        self.draft()
        self.publish()
        self.draft(radius=12)
        draft = read_state(self.owner)["draft"]
        result = self.call("rollback", {"target_version": 0, "base_version": 1,
                                        "reason": "Aslga qaytish", "confirmed": True})
        self.assertEqual(result["result"]["kind"], "rolled_back")
        self.assertEqual(result["result"]["version"], 2)
        self.assertEqual(read_published()["value"], defaults())
        self.assertEqual(result["state"]["draft"], draft)
        self.assertEqual(DesignVersion.objects.get(number=2).source_version.number, 0)
        audits = self.audit_count()
        noop = self.call("rollback", {"target_version": 0, "base_version": 2, "reason": "Aslga qaytish", "confirmed": True})
        self.assertEqual(noop["result"]["kind"], "noop")
        self.assertEqual(DesignVersion.objects.count(), 3)
        self.assertEqual(self.audit_count(), audits)

    def test_missing_and_invalid_rollback_target_never_changes_current_design(self):
        self.draft()
        self.publish()
        self.assert_error("not_found", lambda: self.call("rollback", {
            "target_version": 99, "base_version": 1, "reason": "Oldinga qaytish", "confirmed": True}))
        invalid = self.value()
        invalid["light"]["text"] = "#ffffff"
        DesignVersion.objects.create(number=99, value=invalid, kind="publish", reason="Imported invalid data")
        self.assert_error("validation", lambda: self.call("rollback", {
            "target_version": 99, "base_version": 1, "reason": "Oldinga qaytish", "confirmed": True}))
        self.assertEqual(read_published()["version"], 1)

    def test_audit_failure_rolls_back_draft_write_and_operation(self):
        with patch("core.design_service.record_audit_event", side_effect=RuntimeError("audit unavailable")):
            with self.assertRaises(RuntimeError):
                self.draft()
        for model in (DesignState, DesignDraft, DesignVersion, DesignOperation):
            self.assertFalse(model.objects.exists())

    def test_audit_failure_rolls_back_publication_pointer_and_both_versions(self):
        draft = self.draft()["state"]["draft"]
        with patch("core.design_service.record_audit_event", side_effect=RuntimeError("audit unavailable")):
            with self.assertRaises(RuntimeError):
                self.publish()
        self.assertEqual(read_state(self.owner)["draft"], draft)
        self.assertEqual(read_published()["version"], 0)
        self.assertFalse(DesignVersion.objects.exists())
        self.assertEqual(DesignOperation.objects.count(), 1)

    def test_receipt_failure_rolls_back_publication_and_audit(self):
        self.draft()
        with patch.object(DesignOperation.objects, "create", side_effect=RuntimeError("receipt unavailable")):
            with self.assertRaises(RuntimeError):
                self.publish()
        self.assertEqual(read_published()["version"], 0)
        self.assertFalse(DesignVersion.objects.exists())
        self.assertEqual(self.audit_count(), 1)

    def test_presets_are_private_and_independent_of_the_draft(self):
        self.draft(radius=12)
        result = self.call("save_preset", {"name": " My design ", "value": self.value()})
        preset = read_state(self.owner)["presets"][0]
        self.assertEqual(preset["name"], "My design")
        self.assertEqual(preset["value"], self.value())
        self.assertEqual(read_state(self.owner)["draft"]["value"], self.value(12))
        self.assertEqual(read_state(self.other)["presets"], [])
        self.assert_error("not_found", lambda: self.call("delete_preset", {
            "preset_id": result["result"]["preset_id"]}, actor=self.other))

    def test_preset_same_name_and_value_is_noop_but_different_value_conflicts(self):
        first = self.call("save_preset", {"name": "Yumshoq", "value": self.value()})
        audits = self.audit_count()
        noop = self.call("save_preset", {"name": "yumshoq", "value": self.value()})
        self.assertEqual(noop["result"]["kind"], "noop")
        self.assertEqual(first["result"]["preset_id"], noop["result"]["preset_id"])
        self.assertEqual(self.audit_count(), audits)
        self.assert_error("name_conflict", lambda: self.call("save_preset", {"name": "YUMSHOQ", "value": self.value(12)}))

    def test_preset_soft_delete_preserves_record_and_allows_reusing_its_name(self):
        first = self.call("save_preset", {"name": "Saved", "value": self.value()})
        preset_id = first["result"]["preset_id"]
        removed = self.call("delete_preset", {"preset_id": preset_id})
        self.assertEqual(removed["state"]["presets"], [])
        self.assertIsNotNone(DesignPreset.objects.get(pk=preset_id).deleted_at)
        self.assertEqual(self.call("delete_preset", {"preset_id": preset_id})["result"]["kind"], "noop")
        recreated = self.call("save_preset", {"name": "Saved", "value": self.value(12)})
        self.assertNotEqual(recreated["result"]["preset_id"], preset_id)

    def test_invalid_preset_names_and_operation_ids_are_rejected(self):
        for name in ("", " ", "x" * 61, "broken\nname", 12):
            with self.subTest(name=name):
                self.assert_error("invalid", lambda: self.call("save_preset", {"name": name, "value": defaults()}))
        for operation in ("bad", str(uuid4()).upper(), None, 12):
            with self.subTest(operation=operation):
                self.assert_error("invalid", lambda: execute(self.owner, "save_preset", operation, {"name": "Saved", "value": defaults()}))

    def test_surrogate_metadata_and_deep_nested_snapshot_fail_without_writes(self):
        self.assert_error("invalid", lambda: self.call("save_preset", {"name": "Bad\ud800", "value": defaults()}))
        self.assert_error("invalid", lambda: self.call("publish", {
            "draft_revision": 0, "base_version": 0, "reason": "Bad\udfff", "confirmed": True}))
        nested = []
        for _ in range(1500):
            nested = [nested]
        value = defaults()
        value["values"]["button-radius"] = nested
        self.assert_error("validation", lambda: self.call("save_draft", {
            "value": value, "draft_revision": 0, "base_version": 0}))
        for model in (DesignState, DesignDraft, DesignVersion, DesignOperation, DesignPreset):
            self.assertFalse(model.objects.exists())
        self.assertEqual(self.audit_count(), 0)

    def test_public_projection_excludes_private_metadata_and_fails_safely(self):
        self.draft()
        self.publish()
        self.assertEqual(set(read_published()), {"version", "value"})
        with patch.object(DesignState.objects, "select_related", side_effect=DatabaseError("DB unavailable")):
            self.assertEqual(read_published(), {"version": 0, "value": defaults()})
        with patch("core.design_service.validate", side_effect=DesignValidationError("Invalid stored schema")):
            self.assertEqual(read_published(), {"version": 0, "value": defaults()})
        set_flag("backoffice_design_workspace", enabled=False, reason="Read fallback")
        self.assertEqual(read_published(), {"version": 0, "value": defaults()})

    def test_version_and_receipt_snapshots_cannot_be_updated_or_deleted(self):
        self.draft()
        self.publish()
        for model in (DesignVersion, DesignOperation):
            item = model.objects.first()
            for mutation in (item.save, item.delete, lambda: model.objects.filter(pk=item.pk).delete(),
                             lambda: model.objects.filter(pk=item.pk).update(actor_label="rewritten")):
                with self.subTest(model=model, mutation=mutation), self.assertRaises(ValidationError):
                    mutation()

    def test_account_removal_retains_publication_attribution_and_receipts(self):
        self.draft()
        self.publish()
        self.owner.delete()
        version = DesignVersion.objects.get(number=1)
        self.assertIsNone(version.actor_id)
        self.assertEqual(version.actor_label, "design-owner")
        self.assertEqual(DesignOperation.objects.count(), 2)
        self.assertEqual(read_published()["version"], 1)


@override_settings(GEMINI_API_KEY="", TELEGRAM_BOT_TOKEN="")
class DesignConcurrencyTests(TransactionTestCase):
    def setUp(self):
        User = get_user_model()
        self.owner = User.objects.create_user("concurrent-owner", "concurrent-owner@example.test", is_staff=True, is_superuser=True)
        self.other = User.objects.create_user("concurrent-other", "concurrent-other@example.test", is_staff=True, is_superuser=True)
        set_flag("backoffice_design_workspace", enabled=True, reason="Concurrent publication")

    @skipUnlessDBFeature("has_select_for_update")
    def test_concurrent_owners_cannot_publish_over_the_same_base_version(self):
        for actor, radius in ((self.owner, 12), (self.other, 24)):
            value = defaults()
            value["values"]["button-radius"] = radius
            execute(actor, "save_draft", str(uuid4()), {"value": value, "draft_revision": 0, "base_version": 0})
        barrier = Barrier(2)

        def publish(actor):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                try:
                    return execute(actor, "publish", str(uuid4()), {
                        "draft_revision": 1, "base_version": 0, "reason": "Concurrent change", "confirmed": True})["result"]["kind"]
                except DesignError as error:
                    return error.code
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(publish, (self.owner, self.other)))
        self.assertCountEqual(results, ["published", "stale"])
        self.assertEqual(list(DesignVersion.objects.values_list("number", flat=True)), [1, 0])
        self.assertEqual(SystemAuditEvent.objects.filter(action="design.publish").count(), 1)

    @skipUnlessDBFeature("has_select_for_update")
    def test_simultaneous_same_operation_has_one_draft_receipt_and_audit(self):
        operation, barrier = str(uuid4()), Barrier(2)
        payload = {"value": defaults(), "draft_revision": 0, "base_version": 0}

        def save(_):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                return execute(self.owner, "save_draft", operation, payload)["result"]
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            first, second = list(pool.map(save, (1, 2)))
        self.assertEqual(first, second)
        self.assertEqual(DesignDraft.objects.count(), 1)
        self.assertEqual(DesignOperation.objects.count(), 1)
        self.assertEqual(SystemAuditEvent.objects.filter(action="design.save_draft").count(), 1)
