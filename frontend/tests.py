from django.test import TestCase
from django.urls import reverse

from .models import (
    LandingAIFeature,
    LandingExamSkill,
    LandingLevelStage,
    LandingNavItem,
    LandingPage,
    LandingProcessStep,
    Statistic,
)


class LandingPageHowItWorksTests(TestCase):
    def test_home_page_uses_dynamic_how_it_works_content(self):
        page = LandingPage.load()
        page.how_it_works_title = "Bu qanday ishlaydi?"
        page.how_it_works_subtitle = "Hammasi 4 bosqichda"
        page.save()
        LandingProcessStep.objects.all().delete()
        LandingProcessStep.objects.create(
            title="Profil oching",
            description="Bir necha soniyada ro'yxatdan o'ting",
            icon_class="bi bi-person-plus",
            order=1,
        )
        LandingProcessStep.objects.create(
            title="Natijani oling",
            description="Yakunida sertifikatni yuklab oling",
            icon_class="bi bi-patch-check",
            order=2,
        )

        response = self.client.get("/")
        content = response.content.decode("utf-8")

        self.assertContains(response, "Bu qanday ishlaydi?")
        self.assertContains(response, "Hammasi 4 bosqichda")
        self.assertContains(response, "Profil oching")
        self.assertContains(response, "Natijani oling")
        self.assertIn("Bir necha soniyada ro&#x27;yxatdan o&#x27;ting", content)
        self.assertIn("Yakunida sertifikatni yuklab oling", content)


class LandingSITLinkTests(TestCase):
    def test_home_page_links_to_study_in_turkey_portal(self):
        response = self.client.get("/")

        self.assertContains(response, f'href="{reverse("sit:home")}"')
        self.assertContains(response, "Turkiyada o'qish")


class LandingFooterContactTests(TestCase):
    def test_footer_uses_dynamic_site_settings_contact_values(self):
        from .models import SiteSettings

        settings_obj = SiteSettings.load()
        settings_obj.contact_phone = "+998 71 555 44 33"
        settings_obj.contact_email = "support@azurelms.test"
        settings_obj.save()

        response = self.client.get("/")

        self.assertContains(response, "+998 71 555 44 33")
        self.assertContains(response, "support@azurelms.test")
        self.assertContains(response, "tel:+998715554433")
        self.assertContains(response, "mailto:support@azurelms.test")


class LandingAdminControlledContentTests(TestCase):
    """Barcha asosiy landing bo'limlari admin modellaridan render bo'lishini kafolatlaydi."""

    def test_hero_and_section_text_come_from_landing_page(self):
        page = LandingPage.load()
        page.rail_tagline = "RAIL-TAGLINE-XYZ"
        page.hero_kicker_left = "HERO-KICKER-LEFT-XYZ"
        page.hero_title_start = "BOSHI"
        page.hero_title_highlight = "AJRATILGAN"
        page.hero_title_end = "OXIRI"
        page.hero_subtitle = "<p>HERO-SUBTITLE-XYZ</p>"
        page.demo_course_name = "DEMO-KURS-XYZ"
        page.demo_progress = 42
        page.ai_title = "AI-TITLE-XYZ"
        page.ai_demo_question = "AI-SAVOL-XYZ"
        page.exam_title = "EXAM-TITLE-XYZ"
        page.cert_sample_name = "CERT-ISM-XYZ"
        page.final_cta_title = "FINAL-CTA-XYZ"
        page.footer_copyright = "FOOTER-COPYRIGHT-XYZ"
        page.save()

        response = self.client.get("/")

        for needle in [
            "RAIL-TAGLINE-XYZ",
            "HERO-KICKER-LEFT-XYZ",
            "BOSHI",
            "AJRATILGAN",
            "OXIRI",
            "HERO-SUBTITLE-XYZ",
            "DEMO-KURS-XYZ",
            'data-target="42"',
            "AI-TITLE-XYZ",
            "AI-SAVOL-XYZ",
            "EXAM-TITLE-XYZ",
            "CERT-ISM-XYZ",
            "FINAL-CTA-XYZ",
            "FOOTER-COPYRIGHT-XYZ",
        ]:
            self.assertContains(response, needle)

    def test_repeatable_sections_render_from_their_models(self):
        LandingLevelStage.objects.all().delete()
        LandingAIFeature.objects.all().delete()
        LandingExamSkill.objects.all().delete()
        Statistic.objects.all().delete()

        LandingLevelStage.objects.create(
            title="BOSQICH-A", description="tavsif", level_range="A1—A2",
            lessons_count="10", duration="5 hafta", status="current",
            status_label="JORIY-XYZ", order=1,
        )
        LandingAIFeature.objects.create(text="AI-FEATURE-XYZ", order=1)
        LandingExamSkill.objects.create(name="SKILL-XYZ", meta="10 MIN", icon_class="bi bi-mic", order=1)
        Statistic.objects.create(numeric_value=1234, suffix="+", decimals=0, label="STAT-LABEL-XYZ", order=1)

        response = self.client.get("/")

        self.assertContains(response, "BOSQICH-A")
        self.assertContains(response, "JORIY-XYZ")
        self.assertContains(response, "AI-FEATURE-XYZ")
        self.assertContains(response, "SKILL-XYZ")
        self.assertContains(response, "STAT-LABEL-XYZ")
        self.assertContains(response, 'data-count="1234"')
        self.assertContains(response, 'data-suffix="+"')

    def test_hidden_items_are_not_rendered(self):
        LandingExamSkill.objects.all().delete()
        LandingExamSkill.objects.create(name="KORINADI-XYZ", meta="x", order=1, is_visible=True)
        LandingExamSkill.objects.create(name="YASHIRIN-XYZ", meta="x", order=2, is_visible=False)

        response = self.client.get("/")

        self.assertContains(response, "KORINADI-XYZ")
        self.assertNotContains(response, "YASHIRIN-XYZ")

    def test_footer_columns_render_from_nav_items(self):
        LandingNavItem.objects.filter(placement__startswith="footer").delete()
        LandingNavItem.objects.create(
            placement="footer_platform", key="custom", label="FOOTER-LINK-XYZ",
            custom_url="/xyz/", is_visible=True, order=1,
        )

        response = self.client.get("/")

        self.assertContains(response, "FOOTER-LINK-XYZ")
        self.assertContains(response, "/xyz/")
