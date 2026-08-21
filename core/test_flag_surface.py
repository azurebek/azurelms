"""Owner uchun flag boshqaruvi (A2).

Boshqa owner mutation'lari bilan bir xil qoida: majburiy sabab, majburiy
tasdiq, auditlangan yozuv va o'zgarish bo'lmasa hech narsa yozmaydigan no-op
yo'l. Registrda e'lon qilinmagan slug qabul qilinmaydi.
"""

from django.test import TestCase
from django.utils.html import escape
from django.urls import reverse

from aicontrol.models import FeatureFlag, SystemAuditEvent
from core.flags import FLAG_REGISTRY, flag_enabled
from users.models import CustomUser as User


class FlagSurfaceAccessTests(TestCase):
    def setUp(self):
        self.url = reverse("backoffice_feature_flags")

    def test_anonymous_is_redirected_to_login(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/users/login/", response.url)

    def test_student_cannot_open_it(self):
        User.objects.create_user(username="oquvchi", email="o@example.com", password="testpass123")
        self.client.login(username="oquvchi", password="testpass123")

        response = self.client.get(self.url)
        self.assertIn(response.status_code, (302, 403))

    def test_staff_without_superuser_cannot_open_it(self):
        """Control Center owner-only: staff yetarli emas."""
        User.objects.create_user(
            username="xodim", email="x@example.com", password="testpass123", is_staff=True
        )
        self.client.login(username="xodim", password="testpass123")

        response = self.client.get(self.url)
        self.assertIn(response.status_code, (302, 403))


class FlagSurfaceTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_superuser(
            username="owner", email="owner@example.com", password="testpass123"
        )
        self.client.login(username="owner", password="testpass123")
        self.url = reverse("backoffice_feature_flags")
        self.flag = FLAG_REGISTRY[0]

    def test_page_lists_every_declared_flag(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        for flag in FLAG_REGISTRY:
            # Yorliqlarda apostrof bor; sahifada u `&#x27;` bo'lib chiqadi.
            self.assertContains(response, escape(flag.label))
            self.assertContains(response, flag.slug)

    def test_owner_can_change_a_flag(self):
        response = self.client.post(self.url, {
            "slug": self.flag.slug,
            "enabled": "" if self.flag.default else "on",
            "change_reason": "demo oldidan yopamiz",
            "confirm_change": "on",
        })

        self.assertEqual(response.status_code, 302)
        self.assertEqual(flag_enabled(self.flag.slug), not self.flag.default)
        event = SystemAuditEvent.objects.filter(action="feature_flag.update").first()
        self.assertIsNotNone(event)
        self.assertIn(self.flag.slug, event.target_label)

    def test_reason_is_required(self):
        self.client.post(self.url, {
            "slug": self.flag.slug,
            "enabled": "" if self.flag.default else "on",
            "confirm_change": "on",
        })
        self.assertEqual(flag_enabled(self.flag.slug), self.flag.default)
        self.assertFalse(SystemAuditEvent.objects.filter(action="feature_flag.update").exists())

    def test_confirmation_is_required(self):
        self.client.post(self.url, {
            "slug": self.flag.slug,
            "enabled": "" if self.flag.default else "on",
            "change_reason": "tasdiqsiz",
        })
        self.assertEqual(flag_enabled(self.flag.slug), self.flag.default)

    def test_unknown_slug_is_rejected(self):
        """Forma faqat registrda bor slugni qabul qilsin."""
        self.client.post(self.url, {
            "slug": "mavjud-emas",
            "enabled": "on",
            "change_reason": "sinov",
            "confirm_change": "on",
        })
        self.assertFalse(FeatureFlag.objects.filter(slug="mavjud-emas").exists())

    def test_no_op_writes_nothing(self):
        self.client.post(self.url, {
            "slug": self.flag.slug,
            "enabled": "on" if self.flag.default else "",
            "change_reason": "o'zgarishsiz",
            "confirm_change": "on",
        })
        self.assertFalse(SystemAuditEvent.objects.filter(action="feature_flag.update").exists())

    def test_page_is_reachable_from_the_control_center(self):
        response = self.client.get(reverse("backoffice_control"))
        self.assertContains(response, self.url)
