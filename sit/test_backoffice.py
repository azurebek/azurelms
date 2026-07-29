from datetime import date, timedelta

from django.contrib.admin.models import LogEntry
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import (
    Announcement,
    KnowledgeArticle,
    University,
    UniversityFaculty,
    UniversityRequirement,
)


class SITBackofficeTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.owner = User.objects.create_superuser(
            username="sit-owner",
            email="owner@example.com",
            password="test-pass-123",
        )
        self.staff = User.objects.create_user(
            username="sit-staff",
            password="test-pass-123",
            is_staff=True,
        )

    def university_payload(self, **overrides):
        payload = {
            "name": "Test universitet",
            "short_name": "TU",
            "city": "Ankara",
            "university_type": University.UniversityType.PUBLIC,
            "admission_status": University.AdmissionStatus.OPEN,
            "tuition_currency": University.Currency.USD,
            "application_help_enabled": "on",
            "application_help_fee": "5000",
            "cover_theme": University.CoverTheme.AZURE,
            "order": "0",
            "change_reason": "SIT katalog testi",
            "confirm_change": "on",
        }
        payload.update(overrides)
        return payload

    def create_university(self, **overrides):
        values = {
            "name": "Test universitet",
            "short_name": "TU",
            "city": "Ankara",
            "admission_status": University.AdmissionStatus.OPEN,
            "source_url": "https://example.com/admissions",
            "last_verified_on": timezone.localdate(),
            "is_published": False,
        }
        values.update(overrides)
        return University.objects.create(**values)

    def formset_management(self, prefix, *, total=1, initial=0):
        return {
            f"{prefix}-TOTAL_FORMS": str(total),
            f"{prefix}-INITIAL_FORMS": str(initial),
            f"{prefix}-MIN_NUM_FORMS": "0",
            f"{prefix}-MAX_NUM_FORMS": "1000",
        }

    def test_sit_backoffice_is_owner_only(self):
        url = reverse("sit_backoffice:dashboard")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

        self.client.force_login(self.staff)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

        self.client.force_login(self.owner)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Study in Turkey boshqaruvi")

    def test_dashboard_flags_stale_published_university(self):
        stale = self.create_university(
            name="Eskirgan universitet",
            short_name="EU",
            is_published=True,
            last_verified_on=timezone.localdate() - timedelta(days=120),
        )
        self.client.force_login(self.owner)

        response = self.client.get(reverse("sit_backoffice:dashboard"))

        self.assertEqual(response.context["metrics"]["stale"], 1)
        self.assertContains(response, stale.name)
        self.assertContains(response, "Tekshirish kerak")

    def test_owner_can_create_draft_university_with_audit(self):
        self.client.force_login(self.owner)

        response = self.client.post(
            reverse("sit_backoffice:university_create"),
            self.university_payload(),
        )

        university = University.objects.get(short_name="TU")
        self.assertRedirects(
            response,
            reverse(
                "sit_backoffice:university_edit",
                kwargs={"university_id": university.pk},
            ),
        )
        self.assertFalse(university.is_published)
        audit = LogEntry.objects.get(object_id=str(university.pk))
        self.assertIn("SIT katalog testi", audit.change_message)

    def test_university_publish_requires_source_and_verified_date(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("sit_backoffice:university_create"),
            self.university_payload(is_published="on"),
        )

        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"],
            "source_url",
            "Universitetni nashr qilish uchun rasmiy manba majburiy.",
        )
        self.assertFormError(
            response.context["form"],
            "last_verified_on",
            "Universitetni nashr qilishdan oldin tekshirilgan sanani kiriting.",
        )

    def test_save_draft_overrides_publish_checkbox(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("sit_backoffice:university_create"),
            self.university_payload(
                is_published="on",
                save_draft="1",
            ),
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(University.objects.get(short_name="TU").is_published)

    def test_related_university_sections_save_with_one_audit_entry(self):
        university = self.create_university()
        self.client.force_login(self.owner)
        payload = self.university_payload(
            name=university.name,
            short_name=university.short_name,
            city=university.city,
            source_url=university.source_url,
            last_verified_on=university.last_verified_on.isoformat(),
        )
        for prefix in (
            "faculties",
            "programs",
            "preparation",
            "requirements",
            "documents",
            "services",
            "media",
        ):
            payload.update(self.formset_management(prefix))
        payload.update(
            {
                "faculties-0-name": "Muhandislik",
                "faculties-0-is_active": "on",
                "faculties-0-order": "0",
                "requirements-0-text": "Diplom nusxasi",
                "requirements-0-is_active": "on",
                "requirements-0-order": "0",
            }
        )

        response = self.client.post(
            reverse(
                "sit_backoffice:university_edit",
                kwargs={"university_id": university.pk},
            ),
            payload,
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            UniversityFaculty.objects.filter(
                university=university,
                name="Muhandislik",
            ).exists()
        )
        self.assertTrue(
            UniversityRequirement.objects.filter(
                university=university,
                text="Diplom nusxasi",
            ).exists()
        )
        audit = LogEntry.objects.filter(object_id=str(university.pk)).latest(
            "action_time"
        )
        self.assertIn("Fakultet va institutlar", audit.change_message)
        self.assertIn("Qabul talablari", audit.change_message)

    def test_home_only_shows_selected_published_announcements(self):
        hidden = Announcement.objects.create(
            title="Oddiy nashr",
            category=Announcement.Category.NEWS,
            published_on=date(2026, 7, 29),
            is_published=True,
            show_on_home=False,
        )
        selected = Announcement.objects.create(
            title="Bosh sahifadagi qabul",
            category=Announcement.Category.ADMISSION,
            published_on=date(2026, 7, 29),
            is_published=True,
            show_on_home=True,
        )

        response = self.client.get(reverse("sit:home"))

        self.assertContains(response, selected.title)
        self.assertNotContains(response, hidden.title)

    def test_owner_can_publish_home_announcement_with_audit(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("sit_backoffice:announcement_create"),
            {
                "title": "Kuzgi qabul ochildi",
                "category": Announcement.Category.ADMISSION,
                "published_on": "2026-07-29",
                "show_on_home": "on",
                "is_published": "on",
                "order": "0",
                "change_reason": "Qabul e'loni qo'shildi",
                "confirm_change": "on",
            },
        )

        announcement = Announcement.objects.get(title="Kuzgi qabul ochildi")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(announcement.show_on_home)
        self.assertTrue(announcement.is_published)
        self.assertTrue(
            LogEntry.objects.filter(object_id=str(announcement.pk)).exists()
        )

    def test_owner_can_publish_verified_guide_with_audit(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("sit_backoffice:guide_create"),
            {
                "title": "Talaba vizasi qo'llanmasi",
                "category": "Viza",
                "excerpt": "Bosqichma-bosqich yo'riqnoma",
                "body": "<p>Rasmiy talablarni tekshiring.</p>",
                "published_on": "2026-07-29",
                "source_url": "https://example.gov.tr/student-visa",
                "last_verified_on": "2026-07-29",
                "is_featured": "on",
                "is_published": "on",
                "order": "0",
                "change_reason": "Rasmiy manba tekshirildi",
                "confirm_change": "on",
            },
        )

        guide = KnowledgeArticle.objects.get(title="Talaba vizasi qo'llanmasi")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(guide.is_published)
        self.assertTrue(guide.is_featured)
        self.assertTrue(LogEntry.objects.filter(object_id=str(guide.pk)).exists())

    def test_all_backoffice_surfaces_render(self):
        university = self.create_university()
        announcement = Announcement.objects.create(
            title="SIT yangiligi",
            published_on=date(2026, 7, 29),
        )
        guide = KnowledgeArticle.objects.create(
            title="SIT qo'llanmasi",
            category="Qabul",
            body="<p>Test</p>",
        )
        self.client.force_login(self.owner)
        urls = (
            reverse("sit_backoffice:dashboard"),
            reverse("sit_backoffice:universities"),
            reverse("sit_backoffice:university_create"),
            reverse(
                "sit_backoffice:university_edit",
                kwargs={"university_id": university.pk},
            ),
            reverse("sit_backoffice:announcements"),
            reverse("sit_backoffice:announcement_create"),
            reverse(
                "sit_backoffice:announcement_edit",
                kwargs={"announcement_id": announcement.pk},
            ),
            reverse("sit_backoffice:guides"),
            reverse("sit_backoffice:guide_create"),
            reverse(
                "sit_backoffice:guide_edit",
                kwargs={"guide_id": guide.pk},
            ),
        )

        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
