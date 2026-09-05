"""Ro'yxatdan o'tish odam qayerga bormoqchi bo'lganini unutmaydi.

UX auditning 5-topilmasi. Mehmon kirishni talab qiladigan sahifaga bosadi
va `/users/login/?next=/checkout/course/7/` ga tushadi. Hisobi yo'q, shuning
uchun «Ro'yxatdan o'tish» tabiga o'tadi — va aynan **shu bosishda** `next`
yo'qolardi: tab havolasi oddiy `{% url 'register' %}` edi.

Natijada odam ro'yxatdan o'tib bo'lib dashboardga tushardi va to'lamoqchi
bo'lgan kursini qaytadan qidirishga majbur edi.

Xavfsizlik tomoni: `next` hech qachon xom holda ishlatilmaydi. Tekshiruv
`users/views.py::_safe_next` da — u faqat shu saytning ichki manzilini
qabul qiladi, aks holda istalgan odam `?next=https://...` bilan bizning
domendan boshqa saytga eltadigan havola tarqata olardi.
"""

from urllib.parse import quote

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()

WANTED = "/checkout/course/7/"


class TheRegisterLinkKeepsTheDestinationTests(TestCase):
    def test_the_login_page_passes_it_to_the_register_tab(self):
        """Aynan shu bosishda yo'qolardi."""
        response = self.client.get(f"{reverse('login')}?next={quote(WANTED)}")

        self.assertContains(
            response, f'href="{reverse("register")}?next={quote(WANTED, safe="")}"'
        )

    def test_the_register_page_passes_it_back_to_the_login_tab(self):
        response = self.client.get(f"{reverse('register')}?next={quote(WANTED)}")

        self.assertContains(
            response, f'href="{reverse("login")}?next={quote(WANTED, safe="")}"'
        )

    def test_the_register_form_carries_it_in_a_hidden_field(self):
        response = self.client.get(f"{reverse('register')}?next={quote(WANTED)}")

        self.assertContains(
            response, f'<input type="hidden" name="next" value="{WANTED}">'
        )

    def test_nothing_is_added_when_there_is_no_destination(self):
        """Bo'sh `?next=` manzilni iflos qiladi."""
        response = self.client.get(reverse("register"))

        self.assertNotContains(response, "?next=")


class AfterRegisteringYouEndUpWhereYouWantedTests(TestCase):
    def _register(self, **extra):
        data = {
            "first_name": "Ali", "email": "yol@example.test",
            "password1": "Qishloq7!tepa", "password2": "Qishloq7!tepa",
        }
        data.update(extra)
        return self.client.post(reverse("register"), data)

    def test_the_onboarding_step_receives_the_destination(self):
        response = self._register(next=WANTED)

        self.assertRedirects(
            response,
            f"{reverse('onboarding_choice')}?next={quote(WANTED, safe='')}",
            fetch_redirect_response=False,
        )

    def test_the_onboarding_card_leads_there_instead_of_the_dashboard(self):
        self._register(next=WANTED)

        response = self.client.get(
            f"{reverse('onboarding_choice')}?next={quote(WANTED)}"
        )

        self.assertContains(response, f'href="{WANTED}"')
        self.assertNotContains(response, f'href="{reverse("dashboard")}" class="choice-card"')

    def test_without_a_destination_the_dashboard_is_still_the_answer(self):
        """Oddiy ro'yxatdan o'tish o'zgarmadi."""
        response = self._register()

        self.assertRedirects(
            response, reverse("onboarding_choice"), fetch_redirect_response=False
        )
        page = self.client.get(reverse("onboarding_choice"))
        self.assertContains(page, f'href="{reverse("dashboard")}"')


class AnOutsideAddressIsRefusedTests(TestCase):
    """`next` — foydalanuvchi bergan matn, ya'ni ishonchsiz."""

    def test_registering_never_redirects_off_the_site(self):
        response = self.client.post(reverse("register"), {
            "first_name": "Ali", "email": "tashqi@example.test",
            "password1": "Qishloq7!tepa", "password2": "Qishloq7!tepa",
            "next": "https://boshqa-sayt.example/olja",
        })

        self.assertRedirects(
            response, reverse("onboarding_choice"), fetch_redirect_response=False
        )

    def test_the_register_page_does_not_echo_an_outside_address(self):
        response = self.client.get(
            f"{reverse('register')}?next=https://boshqa-sayt.example/olja"
        )

        self.assertNotContains(response, "boshqa-sayt.example")

    def test_the_onboarding_card_does_not_lead_off_the_site(self):
        User.objects.create_user(
            username="tashqi2", email="tashqi2@example.test", password="Qishloq7!tepa"
        )
        self.client.login(username="tashqi2", password="Qishloq7!tepa")

        response = self.client.get(
            f"{reverse('onboarding_choice')}?next=https://boshqa-sayt.example/olja"
        )

        self.assertNotContains(response, "boshqa-sayt.example")
        self.assertContains(response, f'href="{reverse("dashboard")}"')
