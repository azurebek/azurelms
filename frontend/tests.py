from django.test import TestCase

from .models import LandingPage


class LandingPageHowItWorksTests(TestCase):
    def test_home_page_uses_dynamic_how_it_works_content(self):
        page = LandingPage.load()
        page.how_it_works_title = "Bu qanday ishlaydi?"
        page.how_it_works_subtitle = "Hammasi 4 bosqichda"
        page.how_it_works_step_one_title = "Profil oching"
        page.how_it_works_step_one_description = "Bir necha soniyada ro'yxatdan o'ting"
        page.how_it_works_step_two_title = "Yo'nalish tanlang"
        page.how_it_works_step_two_description = "Sizga mos kursni belgilang"
        page.how_it_works_step_three_title = "Darslarni ko'ring"
        page.how_it_works_step_three_description = "Video va mashqlar bilan davom eting"
        page.how_it_works_step_four_title = "Natijani oling"
        page.how_it_works_step_four_description = "Yakunida sertifikatni yuklab oling"
        page.save()

        response = self.client.get("/")
        content = response.content.decode("utf-8")

        self.assertContains(response, "Bu qanday ishlaydi?")
        self.assertContains(response, "Hammasi 4 bosqichda")
        self.assertContains(response, "Profil oching")
        self.assertContains(response, "Natijani oling")
        self.assertIn("Bir necha soniyada ro&#x27;yxatdan o&#x27;ting", content)
        self.assertIn("Yakunida sertifikatni yuklab oling", content)
