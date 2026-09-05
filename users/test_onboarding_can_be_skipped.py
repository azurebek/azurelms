"""Onboardingdan halol chiqish yo'li bor.

UX auditning 9-topilmasi. Ro'yxatdan o'tgan odam darhol shu sahifaga
tushardi va uni tark etishning ochiq yo'li yo'q edi: ikkita teng karta,
ikkalasi ham «onboarding qilyapman» degan taassurot berardi.

Yomoni: birinchi karta «Tezkor anketa» deb atalardi va «An'anaviy shaklni
to'ldirib, darhol ta'limni boshlang» derdi — ammo **hech qanday anketa
yo'q edi**. U to'g'ridan-to'g'ri dashboardga eltardi. Ya'ni sahifa va'da
qilgan narsani bermasdi.

Endi bitta tavsiya etilgan yo'l (AI suhbati — profilni haqiqatan
to'ldiradigan yagona narsa) va uning ostida ochiq «hozircha o'tkazib
yuboraman» havolasi.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class ThereIsAWayOutTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="skip-user", email="s@example.test", password="x"
        )
        self.client.force_login(self.user)

    def page(self, query=""):
        return self.client.get(reverse("onboarding_choice") + query)

    def test_the_skip_link_is_on_the_page(self):
        response = self.page()

        self.assertContains(response, "data-onboarding-skip")
        self.assertContains(response, "Hozircha o'tkazib yuboraman")

    def test_the_skip_leads_into_the_app(self):
        response = self.page()

        self.assertContains(response, f'href="{reverse("dashboard")}" data-onboarding-skip')

    def test_the_skip_honours_where_the_person_was_going(self):
        response = self.page("?next=/checkout/course/7/")

        self.assertContains(response, 'href="/checkout/course/7/" data-onboarding-skip')

    def test_the_skip_refuses_an_outside_address(self):
        response = self.page("?next=https://boshqa-sayt.example/olja")

        self.assertNotContains(response, "boshqa-sayt.example")


class ThePageNoLongerPromisesAFormItDoesNotHaveTests(TestCase):
    """«Tezkor anketa» degan karta bor edi, anketa esa yo'q edi."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="anketa-user", email="a@example.test", password="x"
        )
        self.client.force_login(self.user)

    def test_no_questionnaire_is_advertised(self):
        response = self.client.get(reverse("onboarding_choice"))

        self.assertNotContains(response, "Tezkor anketa")
        self.assertNotContains(response, "An&#x27;anaviy shaklni")

    def test_the_real_path_is_still_offered(self):
        response = self.client.get(reverse("onboarding_choice"))

        self.assertContains(response, "Azure AI bilan suhbat")
        self.assertContains(response, reverse("start_smart_onboarding"))

    def test_it_does_not_promise_personalised_lessons(self):
        """Codex review (#90, P2): va'da qilingan narsa mavjud bo'lishi kerak.

        Suhbat `UserOnboarding` ga `goal` va `current_level` ni yozadi,
        xolos. Uni hozircha hech kim o'qimaydi — na katalog tartibi
        (`courses/views.py`), na dashboard tavsiyalari (`users/views.py`),
        na AI prompti. Ya'ni «darslar shunga qarab tartiblanadi» degan
        matn yolg'on bo'lardi.
        """
        response = self.client.get(reverse("onboarding_choice"))

        for promise in ("tartiblanadi", "moslab", "moslashtir"):
            self.assertNotContains(response, promise)

    def test_it_says_exactly_what_the_conversation_does(self):
        response = self.client.get(reverse("onboarding_choice"))

        self.assertContains(response, "profilingizga yozib qo'yadi")

    def test_the_page_describes_the_fields_the_form_actually_stores(self):
        """Matn va sxema bir xil ikki narsani aytadi."""
        from users.smart_forms import UserOnboardingSmartForm

        fields = set(UserOnboardingSmartForm.model_fields)

        self.assertIn("goal", fields)
        self.assertIn("level", fields)
        self.assertEqual(len(fields), 2)

    def test_what_the_page_says_about_later_is_true(self):
        """AI repetitor «Xabarlar» bo'limida rostdan ochiq."""
        response = self.client.get(reverse("onboarding_choice"))

        self.assertContains(response, "AI repetitor doim ochiq")
        self.assertEqual(self.client.get(reverse("messenger:ai")).status_code, 200)


class SkippingChangesNothingButTheDestinationTests(TestCase):
    """O'tkazib yuborish — hisobni buzmaydi, faqat sahifadan chiqaradi."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="ziyon-user", email="z@example.test", password="x"
        )
        self.client.force_login(self.user)

    def test_no_onboarding_row_is_created_by_visiting_the_page(self):
        from users.models import UserOnboarding

        self.client.get(reverse("onboarding_choice"))

        self.assertFalse(UserOnboarding.objects.filter(user=self.user).exists())

    def test_the_page_can_be_opened_again_later(self):
        """Fikridan qaytgan odam qaytib kela oladi."""
        self.client.get(reverse("onboarding_choice"))

        self.assertEqual(self.client.get(reverse("onboarding_choice")).status_code, 200)

    def test_a_guest_cannot_open_it(self):
        self.client.logout()

        self.assertNotEqual(
            self.client.get(reverse("onboarding_choice")).status_code, 200
        )
