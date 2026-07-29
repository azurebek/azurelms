from datetime import date

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from .models import (
    Announcement,
    KnowledgeArticle,
    University,
    UniversityDocument,
    UniversityFaculty,
    UniversityProgram,
    UniversityRequirement,
)


class SITPublicFlowTests(TestCase):
    def create_university(
        self,
        *,
        name="İstanbul Teknik Üniversitesi",
        short_name="İTÜ",
        city="İstanbul",
        university_type=University.UniversityType.PUBLIC,
        admission_status=University.AdmissionStatus.OPEN,
        tuition_from=1200,
        is_published=True,
        is_featured=False,
    ):
        university = University.objects.create(
            name=name,
            short_name=short_name,
            city=city,
            university_type=university_type,
            admission_status=admission_status,
            tuition_from=tuition_from,
            is_published=is_published,
            is_featured=is_featured,
            source_url="https://example.edu.tr/international",
            last_verified_on=date(2026, 7, 28),
        )
        faculty = UniversityFaculty.objects.create(university=university, name="Muhandislik")
        return university, faculty

    def create_program(
        self,
        faculty,
        *,
        name="Kompyuter muhandisligi",
        degree_level=UniversityProgram.DegreeLevel.BACHELOR,
        language=UniversityProgram.Language.TURKISH,
        tuition_fee=1200,
    ):
        return UniversityProgram.objects.create(
            faculty=faculty,
            name=name,
            degree_level=degree_level,
            language=language,
            duration="4 yil",
            tuition_fee=tuition_fee,
        )

    def test_home_uses_only_published_content_and_real_counts(self):
        university, faculty = self.create_university(is_featured=True)
        self.create_program(faculty)
        self.create_university(
            name="Draft universitet",
            short_name="DU",
            city="Ankara",
            is_published=False,
            is_featured=True,
        )
        Announcement.objects.create(
            title="Qabul boshlandi",
            university=university,
            category=Announcement.Category.ADMISSION,
            published_on=date(2026, 7, 28),
            show_on_home=True,
            is_published=True,
        )
        Announcement.objects.create(
            title="Yashirin e'lon",
            published_on=date(2026, 7, 28),
            is_published=False,
        )
        KnowledgeArticle.objects.create(
            title="Talaba vizasi",
            category="Viza",
            body="Bosqichlar",
            is_featured=True,
            is_published=True,
            source_url="https://example.gov.tr/student-visa",
            last_verified_on=date(2026, 7, 28),
        )

        response = self.client.get(reverse("sit:home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, university.name)
        self.assertContains(response, "Qabul boshlandi")
        self.assertContains(response, "Talaba vizasi")
        self.assertNotContains(response, "Draft universitet")
        self.assertNotContains(response, "Yashirin e'lon")
        self.assertEqual(response.context["portal_stats"]["universities"], 1)
        self.assertEqual(response.context["portal_stats"]["programs"], 1)

    def test_catalog_defaults_to_open_and_supports_combined_filters(self):
        open_public, open_faculty = self.create_university()
        self.create_program(open_faculty)
        private, private_faculty = self.create_university(
            name="Bahçeşehir Üniversitesi",
            short_name="BAU",
            city="İstanbul",
            university_type=University.UniversityType.PRIVATE,
            admission_status=University.AdmissionStatus.CLOSED,
            tuition_from=6000,
        )
        self.create_program(
            private_faculty,
            name="Data Science",
            degree_level=UniversityProgram.DegreeLevel.MASTER,
            language=UniversityProgram.Language.ENGLISH,
            tuition_fee=6000,
        )

        response = self.client.get(reverse("sit:university_list"))
        self.assertContains(response, open_public.name)
        self.assertNotContains(response, private.name)

        response = self.client.get(
            reverse("sit:university_list"),
            {
                "status": "all",
                "type": "private",
                "city": "İstanbul",
                "language": "en",
                "level": "master",
                "price": "over_2000",
            },
        )
        self.assertContains(response, private.name)
        self.assertNotContains(response, open_public.name)
        self.assertEqual(response.context["result_count"], 1)

    def test_university_detail_groups_programs_and_hides_drafts(self):
        university, faculty = self.create_university()
        program = self.create_program(faculty)
        UniversityRequirement.objects.create(university=university, text="YÖS natijasi")
        UniversityDocument.objects.create(university=university, text="Xalqaro pasport")

        response = self.client.get(university.get_absolute_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, program.name)
        self.assertContains(response, "YÖS natijasi")
        self.assertContains(response, "Xalqaro pasport")
        self.assertEqual(response.context["program_sections"][0]["value"], "bachelor")

        draft, _ = self.create_university(
            name="Draft universitet",
            short_name="DU",
            is_published=False,
        )
        response = self.client.get(draft.get_absolute_url())
        self.assertEqual(response.status_code, 404)

    def test_knowledge_article_requires_publication(self):
        published = KnowledgeArticle.objects.create(
            title="TÖMER qo'llanmasi",
            category="Til",
            body="<p>Til talablari</p>",
            is_published=True,
            source_url="https://example.edu.tr/tomer",
            last_verified_on=date(2026, 7, 28),
        )
        draft = KnowledgeArticle.objects.create(
            title="Draft qo'llanma",
            category="Til",
            body="<p>Draft</p>",
            is_published=False,
        )

        response = self.client.get(published.get_absolute_url())
        self.assertContains(response, "Til talablari")
        response = self.client.get(draft.get_absolute_url())
        self.assertEqual(response.status_code, 404)

    def test_publication_requires_source_and_verification_date(self):
        with self.assertRaises(ValidationError):
            University.objects.create(
                name="Manbasiz universitet",
                short_name="MU",
                city="Ankara",
                admission_status=University.AdmissionStatus.OPEN,
                is_published=True,
            )

        with self.assertRaises(ValidationError):
            KnowledgeArticle.objects.create(
                title="Manbasiz qo'llanma",
                category="Viza",
                body="Matn",
                is_published=True,
            )
