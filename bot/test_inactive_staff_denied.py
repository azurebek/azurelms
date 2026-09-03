from django.contrib.auth import get_user_model
from django.test import TestCase

from bot.middleware import resolve_identity
from bot.services import (
    can_manage_cohort,
    get_user_role,
    is_active_staff,
    _require_admin,
    verify_receipt,
    reject_receipt,
)


User = get_user_model()


class InactiveStaffDeniedTests(TestCase):
    """Deaktivatsiya qilingan staff bot admin huquqini yo'qotadi.

    Ilgari `is_active` hech qayerda tekshirilmasdi: bloklangan xodim
    hali ham to'lov tasdiqlashi, cohort boshqarishi va admin buyruqlari
    berishi mumkin edi.
    """

    def setUp(self):
        self.active_admin = User.objects.create_user(
            username="active-admin",
            email="active-admin@example.test",
            password="x",
            is_staff=True,
            telegram_id=101,
        )
        self.blocked_admin = User.objects.create_user(
            username="blocked-admin",
            email="blocked-admin@example.test",
            password="x",
            is_staff=True,
            is_active=False,
            telegram_id=102,
        )

    def test_is_active_staff_helper(self):
        self.assertTrue(is_active_staff(self.active_admin))
        self.assertFalse(is_active_staff(self.blocked_admin))
        self.assertFalse(is_active_staff(None))

    def test_require_admin_denies_blocked_staff(self):
        self.assertTrue(_require_admin(self.active_admin))
        self.assertFalse(_require_admin(self.blocked_admin))

    def test_role_label_is_not_admin_for_blocked_staff(self):
        self.assertEqual(get_user_role(101), "Admin")
        self.assertNotEqual(get_user_role(102), "Admin")

    def test_middleware_gives_blocked_staff_no_identity(self):
        user, role = resolve_identity(101)
        self.assertEqual(role, "admin")
        self.assertEqual(user, self.active_admin)

        user, role = resolve_identity(102)
        self.assertEqual(role, "guest")
        self.assertIsNone(user)

    def test_blocked_staff_cannot_manage_cohort(self):
        """`is_active` ni izolyatsiya qiladi: ikkalasi ham o'z kursining instructori.

        Ilgari bu yerda instructor biriktirilmagan bitta kurs bor edi va
        `active_admin` unga faqat "staff" bo'lgani uchun kira olardi. Ya'ni
        test scope qoidasini emas, o'sha paytdagi default-allow'ni yozib
        qo'ygandi. Endi yagona o'zgaruvchi — `is_active`.
        """
        from django.utils import timezone
        from courses.models import Course
        from cohorts.models import Cohort

        today = timezone.now().date()
        own_course = Course.objects.create(
            title="C1", description="d", level="beginner", instructor=self.active_admin
        )
        own_cohort = Cohort.objects.create(name="G1", course=own_course, start_date=today)
        blocked_course = Course.objects.create(
            title="C2", description="d", level="beginner", instructor=self.blocked_admin
        )
        blocked_cohort = Cohort.objects.create(
            name="G2", course=blocked_course, start_date=today
        )

        self.assertTrue(can_manage_cohort(self.active_admin, own_cohort))
        self.assertFalse(can_manage_cohort(self.blocked_admin, blocked_cohort))

    def test_blocked_staff_cannot_act_on_payment_receipts(self):
        approve = verify_receipt(receipt_id=1, actor=self.blocked_admin)
        self.assertFalse(approve.ok)
        self.assertEqual(approve.code, "forbidden")

        reject = reject_receipt(receipt_id=1, actor=self.blocked_admin)
        self.assertFalse(reject.ok)
        self.assertEqual(reject.code, "forbidden")
