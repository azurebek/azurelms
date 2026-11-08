"""DASH1.0a — boshqaruv ruxsatlari: default-deny, aniq ruxsat, veb va bot bir xil.

Ilgari `is_staff` yetarli edi: biror kursga ustoz qilib qo'yilgan xodim ham
barcha o'quvchilarning shaxsiy ma'lumotini, chat matnini, tushumni va
boshqalarning chekini ko'rar, chek qarorini berar, botda esa "admin" bo'lardi.
"""
from io import StringIO
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from asgiref.sync import async_to_sync
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser, Group, Permission
from django.core.files.base import ContentFile
from django.core.management import CommandError, call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from aicontrol.models import SystemAuditEvent
from cohorts.models import Cohort, Enrollment, PaymentReceipt
from core.backoffice_capabilities import (
    CAPABILITIES,
    GLOBAL_CAPABILITIES,
    capability_required,
    has_any_global_capability,
    has_capability,
)
from core.capability_fixtures import grant_all_capabilities, grant_capabilities
from core.models import BackofficeCapability
from courses.models import Course

User = get_user_model()


def make_user(username, **flags):
    return User.objects.create_user(username, f"{username}@example.test", password="x", **flags)


class CapabilityCatalogTests(TestCase):
    def test_model_permissions_match_catalog(self):
        self.assertEqual(dict(BackofficeCapability._meta.permissions), CAPABILITIES)
        self.assertEqual(set(GLOBAL_CAPABILITIES), set(CAPABILITIES))

    def test_every_capability_exists_as_a_permission(self):
        stored = set(Permission.objects.filter(
            content_type__app_label="core", content_type__model="backofficecapability",
        ).values_list("codename", flat=True))
        self.assertEqual(stored, set(CAPABILITIES))

    def test_unknown_capability_is_a_programming_error(self):
        with self.assertRaises(ValueError):
            has_capability(make_user("cat-owner", is_staff=True, is_superuser=True), "everything")
        with self.assertRaises(ValueError):
            capability_required("everything")


class HasCapabilityMatrixTests(TestCase):
    def test_default_deny_matrix(self):
        owner = make_user("m-owner", is_staff=True, is_superuser=True)
        blocked_owner = make_user("m-blocked-owner", is_staff=True, is_superuser=True, is_active=False)
        plain_staff = make_user("m-staff", is_staff=True)
        granted_staff = grant_all_capabilities(make_user("m-granted", is_staff=True))
        blocked_granted = grant_all_capabilities(make_user("m-blocked-granted", is_staff=True, is_active=False))
        # Ruxsat berilgan, lekin xodim bo'lmagan hisob ham hech narsa olmaydi.
        granted_learner = grant_all_capabilities(make_user("m-learner"))
        Course.objects.create(title="Ustoz kursi", instructor=plain_staff)

        expected = {
            None: False, AnonymousUser(): False, owner: True, blocked_owner: False,
            plain_staff: False, granted_staff: True, blocked_granted: False, granted_learner: False,
        }
        for actor, allowed in expected.items():
            for capability in CAPABILITIES:
                with self.subTest(actor=getattr(actor, "username", actor), capability=capability):
                    self.assertIs(has_capability(actor, capability), allowed)
            with self.subTest(actor=getattr(actor, "username", actor), any_global=True):
                self.assertIs(has_any_global_capability(actor), allowed)

    def test_capabilities_are_independent(self):
        staff = grant_capabilities(make_user("m-finance", is_staff=True), "finance_receipt_review")
        self.assertTrue(has_capability(staff, "finance_receipt_review"))
        for capability in set(CAPABILITIES) - {"finance_receipt_review"}:
            with self.subTest(capability=capability):
                self.assertFalse(has_capability(staff, capability))

    def test_group_assignment_works(self):
        group = Group.objects.create(name="Moliya")
        group.permissions.add(Permission.objects.get(content_type__app_label="core", codename="finance_receipt_review"))
        staff = make_user("m-group", is_staff=True)
        staff.groups.add(group)
        staff = User.objects.get(pk=staff.pk)
        self.assertTrue(has_capability(staff, "finance_receipt_review"))
        self.assertFalse(has_capability(staff, "learner_pii_view"))


@override_settings(GEMINI_API_KEY="", TELEGRAM_BOT_TOKEN="")
class WebSurfaceContainmentTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = make_user("w-owner", is_staff=True, is_superuser=True)
        cls.teacher = make_user("w-teacher", is_staff=True)
        cls.student = make_user("w-student", telegram_id=7702)
        course = Course.objects.create(title="Veb kursi", instructor=cls.teacher)
        cohort = Cohort.objects.create(name="Veb guruhi", course=course, start_date="2026-10-01")
        cls.enrollment = Enrollment.objects.create(student=cls.student, cohort=cohort, status="pending")
        cls.receipt = PaymentReceipt.objects.create(
            enrollment=cls.enrollment, amount=100000, receipt_image=ContentFile(b"img", name="r.png"),
            period_start=timezone.localdate(), period_end=timezone.localdate(),
        )

    def get(self, name, actor):
        self.client.force_login(actor)
        return self.client.get(reverse(name))

    def test_plain_staff_and_course_teacher_are_denied_global_surfaces(self):
        for name in ("backoffice_dashboard", "backoffice_users", "backoffice_chats", "backoffice_receipts"):
            with self.subTest(name=name):
                response = self.get(name, self.teacher)
                self.assertEqual(response.status_code, 403)
                self.assertNotContains(response, self.student.email, status_code=403)

    def test_each_surface_opens_with_its_own_capability(self):
        cases = {
            "backoffice_users": ("learner_pii_view",),
            "backoffice_receipts": ("finance_receipt_review",),
            "backoffice_dashboard": ("platform_stats_view", "finance_receipt_review", "learner_pii_view"),
        }
        for name, capabilities in cases.items():
            staff = make_user(f"w-{name}", is_staff=True)
            with self.subTest(name=name, granted="partial"):
                if len(capabilities) > 1:
                    grant_capabilities(staff, *capabilities[:-1])
                    self.assertEqual(self.get(name, staff).status_code, 403)
            with self.subTest(name=name, granted="all"):
                grant_capabilities(staff, *capabilities)
                self.assertEqual(self.get(name, staff).status_code, 200)

    def test_chats_are_closed_for_everyone_including_owner(self):
        for actor in (self.owner, grant_all_capabilities(make_user("w-all", is_staff=True))):
            with self.subTest(actor=actor.username):
                self.assertEqual(self.get("backoffice_chats", actor).status_code, 403)

    def test_owner_keeps_every_surface_without_explicit_grants(self):
        for name in ("backoffice_users", "backoffice_receipts"):
            with self.subTest(name=name):
                self.assertEqual(self.get(name, self.owner).status_code, 200)

    def test_plain_staff_cannot_post_a_receipt_decision(self):
        self.client.force_login(self.teacher)
        response = self.client.post(reverse("backoffice_receipts"), {
            "receipt_id": self.receipt.pk, "action": "verify",
            "change_reason": "Synthetic", "confirm_change": "on",
        })
        self.assertEqual(response.status_code, 403)
        self.receipt.refresh_from_db()
        self.assertFalse(self.receipt.is_verified)

    def test_menus_do_not_link_plain_staff_to_denied_pages(self):
        response = self.get("backoffice_courses", self.teacher)
        self.assertEqual(response.status_code, 200)
        for name in ("backoffice_dashboard", "backoffice_users", "backoffice_chats", "backoffice_receipts"):
            with self.subTest(name=name):
                self.assertNotContains(response, 'href="' + reverse(name) + '"')
        self.assertContains(response, 'href="' + reverse("teacher_dashboard") + '"')


class ReceiptServiceAndFileTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.teacher = make_user("r-teacher", is_staff=True)
        cls.finance = grant_capabilities(make_user("r-finance", is_staff=True), "finance_receipt_review")
        cls.student = make_user("r-student")
        cls.other_student = make_user("r-other")
        course = Course.objects.create(title="Chek kursi", instructor=cls.teacher)
        cohort = Cohort.objects.create(name="Chek guruhi", course=course, start_date="2026-10-01")
        cls.enrollment = Enrollment.objects.create(student=cls.student, cohort=cohort, status="pending")
        cls.receipt = PaymentReceipt.objects.create(
            enrollment=cls.enrollment, amount=100000, receipt_image=ContentFile(b"\x89PNG\r\n\x1a\n", name="r.png"),
            period_start=timezone.localdate(), period_end=timezone.localdate(),
        )

    def test_course_teacher_cannot_decide_but_finance_can(self):
        from cohorts.receipt_service import reject_receipt, verify_receipt

        for decide in (verify_receipt, reject_receipt):
            with self.subTest(decide=decide.__name__):
                self.assertFalse(decide(self.receipt.pk, self.teacher).ok)
        self.assertTrue(PaymentReceipt.objects.filter(pk=self.receipt.pk, is_verified=False).exists())
        self.assertTrue(verify_receipt(self.receipt.pk, self.finance).ok)
        self.receipt.refresh_from_db()
        self.assertTrue(self.receipt.is_verified)

    def test_receipt_file_owner_yes_foreign_no_finance_file_yes(self):
        url = reverse("cohorts:receipt_file", args=[self.receipt.pk])
        file_reader = grant_capabilities(make_user("r-file", is_staff=True), "finance_cross_user_receipt_file_view")
        cases = ((self.student, 200), (self.other_student, 404), (self.teacher, 404),
                 (self.finance, 404), (file_reader, 200))
        for actor, status in cases:
            with self.subTest(actor=actor.username):
                self.client.force_login(actor)
                self.assertEqual(self.client.get(url).status_code, status)


class BotCapabilityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.teacher = make_user("b-teacher", is_staff=True, telegram_id=7801)
        cls.owner = make_user("b-owner", is_staff=True, is_superuser=True, telegram_id=7802)
        cls.capable = grant_all_capabilities(make_user("b-capable", is_staff=True, telegram_id=7803))
        cls.ops_only = grant_capabilities(make_user("b-ops", is_staff=True, telegram_id=7804), "ops_global_view")
        Course.objects.create(title="Bot kursi", instructor=cls.teacher)

    def test_roles_follow_capabilities_not_is_staff(self):
        from bot.middleware import resolve_identity
        from bot.services import get_user_role

        expected = {7801: ("teacher", "O'qituvchi"), 7802: ("admin", "Admin"),
                    7803: ("admin", "Admin"), 7804: ("admin", "Admin")}
        for telegram_id, (role, label) in expected.items():
            with self.subTest(telegram_id=telegram_id):
                self.assertEqual(resolve_identity(telegram_id)[1], role)
                self.assertEqual(get_user_role(telegram_id), label)

    def message(self):
        return SimpleNamespace(answer=AsyncMock(), answer_photo=AsyncMock(), answer_document=AsyncMock())

    def test_admin_role_alone_does_not_open_commands(self):
        """Eskirgan yoki noto'g'ri "admin" roli bilan ham handler o'zi tekshiradi."""
        from bot.routers import staff

        for name, service in (("cmd_stats", "admin_stats"), ("cmd_receipts", "pending_receipts")):
            for actor in (self.teacher, self.ops_only):
                with self.subTest(command=name, actor=actor.username), \
                        patch.object(staff, service) as called:
                    message = self.message()
                    async_to_sync(getattr(staff, name))(message, lms_user=actor, lms_role="admin")
                    called.assert_not_called()
                    message.answer.assert_awaited_once()

    def test_ai_commands_are_owner_only(self):
        from bot.routers import staff

        with patch.object(staff, "ai_control_overview") as overview:
            message = self.message()
            async_to_sync(staff.cmd_ai_settings)(message, lms_user=self.capable, lms_role="admin")
            overview.assert_not_called()
        with patch.object(staff, "ai_control_overview", return_value={}) as overview:
            try:
                async_to_sync(staff.cmd_ai_settings)(self.message(), lms_user=self.owner, lms_role="admin")
            except (KeyError, TypeError):
                pass  # Bo'sh soxta javob matnni qura olmaydi; muhimi — chaqirildi.
            overview.assert_called_once()

    def test_receipt_callback_is_denied_without_finance(self):
        from bot.routers import staff

        callback = SimpleNamespace(answer=AsyncMock(), data="adm:rcpt:ok:1")
        with patch.object(staff, "verify_receipt") as verify:
            async_to_sync(staff.cb_receipt_action)(callback, lms_user=self.ops_only, lms_role="admin")
            verify.assert_not_called()
        callback.answer.assert_awaited_once_with("Ruxsat yo'q.", show_alert=True)

    def test_service_guards_match_handlers(self):
        from bot.services import admin_toggle_user_active, ai_toggle_enforcement, create_broadcast_draft

        student = make_user("b-student")
        self.assertFalse(admin_toggle_user_active(student.pk, self.teacher).ok)
        self.assertFalse(admin_toggle_user_active(student.pk, self.ops_only).ok)  # PII ham kerak
        self.assertIsNone(create_broadcast_draft(self.teacher, "Yetarlicha uzun matn")[0])
        self.assertIsNotNone(create_broadcast_draft(self.ops_only, "Yetarlicha uzun matn")[0])
        self.assertFalse(ai_toggle_enforcement(self.capable).ok)


#: `/backoffice/` ostidagi har route qaysi qoida bilan himoyalangani. Yangi route
#: shu ro'yxatga tushmaguncha test qizil yonadi (unclassified=0).
OWNER = "owner"            # faqat platforma egasi (superuser)
CAPABILITY = "capability"  # aniq boshqaruv ruxsati (core.backoffice_capabilities)
CLOSED = "closed"          # hech kimga, egaga ham ochilmaydi
COURSE = "course"          # xodimning o'z kurs/guruh/material doirasi
HUB = "hub"                # faqat o'qiladigan bo'lim; kartalar ruxsatga qarab
ROUTE_POLICY = {
    **{f"sit_backoffice:{name}": OWNER for name in (
        "dashboard", "universities", "university_create", "university_edit", "announcements",
        "announcement_create", "announcement_edit", "guides", "guide_create", "guide_edit")},
    **{name: OWNER for name in (
        "backoffice_ai_kill_switch", "backoffice_ai_circuit_reset", "backoffice_feature_flags",
        "backoffice_runtime_settings", "backoffice_ai_cost", "backoffice_dead_letter", "backoffice_brand",
        "backoffice_design", "backoffice_design_state", "backoffice_design_command", "backoffice_landing",
        "backoffice_claim_evidence", "backoffice_legal_documents", "backoffice_legal_new", "backoffice_legal_edit",
        "backoffice_legal_preview", "backoffice_release_readiness", "backoffice_catalog", "backoffice_plan_edit",
        "backoffice_cohort_create", "backoffice_cohort_edit", "backoffice_cohort_members", "backoffice_control",
        "backoffice_ai_control", "backoffice_workspace_settings", "backoffice_workspace_plans")},
    "backoffice_dashboard": CAPABILITY,
    "backoffice_receipts": CAPABILITY,
    "backoffice_users": CAPABILITY,
    "backoffice_chats": CLOSED,
    "backoffice_workspace_payments": HUB,
    "backoffice_workspace_site": HUB,
    **{name: COURSE for name in (
        "backoffice_workspace_home", "backoffice_workspace_search", "backoffice_workspace_groups",
        "backoffice_workspace_students", "backoffice_workspace_student", "backoffice_workspace_courses",
        "backoffice_workspace_course_create", "backoffice_workspace_course_edit", "backoffice_workspace_course",
        "backoffice_workspace_assignment_new", "backoffice_workspace_assignment_edit",
        "backoffice_workspace_quiz_new", "backoffice_workspace_quiz_edit", "backoffice_courses",
        "backoffice_course_create", "backoffice_course_edit", "backoffice_lessons", "backoffice_lesson_edit",
        "backoffice_exams", "backoffice_exam_edit")},
    **{f"library_backoffice:{name}": COURSE for name in (
        "resources", "resource_create", "resource_edit", "resource_file", "resource_archive", "resource_delete",
        "lesson_picker", "material_attach", "material_reorder", "material_update", "material_detach")},
}


def backoffice_routes():
    from django.urls import URLPattern, URLResolver, get_resolver

    def walk(patterns, prefix="", namespace=None):
        for pattern in patterns:
            if isinstance(pattern, URLResolver):
                inner = pattern.namespace and (f"{namespace}:{pattern.namespace}" if namespace else pattern.namespace)
                yield from walk(pattern.url_patterns, prefix + str(pattern.pattern), inner or namespace)
            elif isinstance(pattern, URLPattern):
                name = pattern.name and (f"{namespace}:{pattern.name}" if namespace else pattern.name)
                yield prefix + str(pattern.pattern), name

    return [(route, name) for route, name in walk(get_resolver().url_patterns) if route.startswith("backoffice/")]


@override_settings(GEMINI_API_KEY="", TELEGRAM_BOT_TOKEN="")
class BackofficeRouteInventoryTests(TestCase):
    PII_EMAIL = "pii-marker-learner@example.test"

    @classmethod
    def setUpTestData(cls):
        from frontend.models import AuthPageSettings, LandingPage, SiteSettings

        cls.owner = make_user("inv-owner", is_staff=True, is_superuser=True)
        cls.staff = make_user("inv-staff", is_staff=True)
        other_teacher = make_user("inv-teacher", is_staff=True)
        learner = User.objects.create_user("inv-learner", cls.PII_EMAIL, password="x", phone_number="998901234567")
        course = Course.objects.create(title="Inventar kursi", instructor=other_teacher)
        cohort = Cohort.objects.create(name="Inventar guruhi", course=course, start_date="2026-10-01")
        enrollment = Enrollment.objects.create(student=learner, cohort=cohort, status="pending")
        PaymentReceipt.objects.create(enrollment=enrollment, amount=123000)
        SiteSettings.load()
        AuthPageSettings.load()
        LandingPage.load()

    def setUp(self):
        from core.flags import set_flag

        for flag in ("backoffice_unified_navigation", "backoffice_course_workspace",
                     "backoffice_student_support", "backoffice_design_workspace"):
            set_flag(flag, enabled=False, reason="Route inventory: legacy shells")

    def test_every_backoffice_route_is_classified(self):
        names = [name for _, name in backoffice_routes()]
        self.assertNotIn(None, names, "Nomsiz /backoffice/ route'ni tasniflab bo'lmaydi.")
        self.assertEqual(sorted(set(names) - set(ROUTE_POLICY)), [], "Tasniflanmagan route bor")
        self.assertEqual(sorted(set(ROUTE_POLICY) - set(names)), [], "Ro'yxatda eskirgan route bor")

    def test_plain_staff_gets_no_owner_capability_or_closed_route_and_no_foreign_pii(self):
        from core.flags import set_flag

        self.client.force_login(self.staff)
        routes = [(route, name) for route, name in backoffice_routes() if "<" not in route]
        for workspace_on in (False, True):
            for flag in ("backoffice_unified_navigation", "backoffice_course_workspace",
                         "backoffice_student_support", "backoffice_design_workspace"):
                set_flag(flag, enabled=workspace_on, reason="Route inventory")
            for route, name in routes:
                with self.subTest(name=name, workspace=workspace_on):
                    response = self.client.get("/" + route)
                    self.assertLess(response.status_code, 500)
                    self.assertNotIn(self.PII_EMAIL.encode(), response.content)
                    self.assertNotIn(b"998901234567", response.content)
                    policy = ROUTE_POLICY[name]
                    if policy in (OWNER, CAPABILITY, CLOSED):
                        self.assertNotEqual(response.status_code, 200)
                    if policy in (CAPABILITY, CLOSED) and response.status_code != 302:
                        self.assertEqual(response.status_code, 403)

    def test_owner_opens_capability_routes_but_not_closed_chats(self):
        self.client.force_login(self.owner)
        for name, policy in ROUTE_POLICY.items():
            if policy == CAPABILITY:
                with self.subTest(name=name):
                    self.assertEqual(self.client.get(reverse(name)).status_code, 200)
        self.assertEqual(self.client.get(reverse("backoffice_chats")).status_code, 403)


class CapabilityCommandTests(TestCase):
    def run_command(self, *args):
        out = StringIO()
        call_command("backoffice_capability", *args, stdout=out)
        return out.getvalue()

    def test_grant_list_revoke_with_audit(self):
        staff = make_user("c-staff", is_staff=True)
        self.run_command("grant", "c-staff", "finance_receipt_review", "--reason", "Moliya xodimi")
        self.assertTrue(has_capability(User.objects.get(pk=staff.pk), "finance_receipt_review"))
        self.assertIn("c-staff", self.run_command("list"))
        self.assertIn("finance_receipt_review", self.run_command("list", "--user", "c-staff"))
        self.run_command("revoke", "c-staff", "finance_receipt_review", "--reason", "Lavozim o'zgardi")
        self.assertFalse(has_capability(User.objects.get(pk=staff.pk), "finance_receipt_review"))
        events = SystemAuditEvent.objects.filter(target_id=str(staff.pk)).order_by("pk")
        self.assertEqual([event.action for event in events],
                         ["backoffice.capability.grant", "backoffice.capability.revoke"])
        self.assertEqual(events[0].before, {"capabilities": ""})
        self.assertEqual(events[0].after, {"capabilities": "finance_receipt_review"})
        self.assertEqual(events[1].after, {"capabilities": ""})
        self.assertEqual(events[0].source, SystemAuditEvent.SOURCE_CLI)

    def test_refuses_unknown_capability_learner_and_owner(self):
        make_user("c-learner")
        make_user("c-owner", is_staff=True, is_superuser=True)
        make_user("c-staff2", is_staff=True)
        for args in (("grant", "c-staff2", "everything", "--reason", "x"),
                     ("grant", "c-learner", "learner_pii_view", "--reason", "x"),
                     ("grant", "c-owner", "learner_pii_view", "--reason", "x"),
                     ("grant", "nobody", "learner_pii_view", "--reason", "x"),
                     ("grant", "c-staff2", "learner_pii_view", "--reason", " ")):
            with self.subTest(args=args), self.assertRaises(CommandError):
                self.run_command(*args)
        self.assertFalse(SystemAuditEvent.objects.filter(action__startswith="backoffice.capability.").exists())
