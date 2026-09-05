"""Blog va «Turkiyada o'qish» portaliga yo'l bor.

UX auditning 8-topilmasi. Owner'ning aynan so'zi: «oddiy auth qilgan bir
user uchun blog va SIT uchun yo'l yo'q, eng kamida men ko'rmayapman».

Ikkalasi ham ishlaydigan, to'ldirilgan bo'lim edi — faqat eshigi yo'q edi.
Blog public shell navigatsiyasida turardi, ilova qobig'ida esa yo'q: tizimga
kirgan odam uni ko'rmasdi. «Turkiyada o'qish» portali esa **hech qayerda**
yo'q edi — na public navigatsiyada, na ilova qobig'ida. Unga faqat to'g'ridan
to'g'ri manzil yozib kirish mumkin edi.

Avval faqat **ilova qobig'iga** eshik qo'yilgan edi: public sarlavhaga
beshinchi element sig'masdi va 760px dan pastda `.pub-nav` umuman
yo'qolar, o'rnini bosadigan menyu yo'q edi. Keyin o'sha mobil menyu
qo'shilgach (`<details>` asosida, JS'siz ham ochiladi) beshinchi element
public navigatsiyaga ham qo'yildi.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class TheAppSidebarHasADoorTests(TestCase):
    def setUp(self):
        self.student = User.objects.create_user(
            username="eshik-student", email="s@example.test", password="x"
        )
        self.client.force_login(self.student)

    def sidebar(self, response):
        """Faqat yon panel — sahifaning boshqa joyidagi havola hisoblanmaydi."""
        html = response.content.decode(response.charset)
        start = html.index('<nav class="app-nav"')
        return html[start:html.index("</nav>", start)]

    def test_the_blog_is_reachable_from_the_app(self):
        response = self.client.get(reverse("dashboard"))

        self.assertIn(reverse("blog:list"), self.sidebar(response))

    def test_the_study_in_turkey_portal_is_reachable_from_the_app(self):
        response = self.client.get(reverse("dashboard"))

        self.assertIn(reverse("sit:home"), self.sidebar(response))

    def test_they_are_named_the_way_the_pages_name_themselves(self):
        """«SIT» ichki qisqartma — o'quvchi uni tushunmaydi."""
        sidebar = self.sidebar(self.client.get(reverse("dashboard")))

        self.assertIn("Blog", sidebar)
        self.assertIn("Turkiyada o'qish", sidebar)

    def test_the_doors_are_on_every_app_page_not_just_the_dashboard(self):
        for name in ("my_courses", "leaderboard", "certificates"):
            with self.subTest(page=name):
                sidebar = self.sidebar(self.client.get(reverse(name)))
                self.assertIn(reverse("sit:home"), sidebar)


class TheGuestHasADoorTooNowTests(TestCase):
    """Mehmon uchun eshik mobil menyu bilan birga keldi.

    Bu sinf ilgari teskarisini yozib qo'ygan edi: public sarlavhaga
    beshinchi element sig'masdi (760-900px da gorizontal siljish), 760px
    dan pastda esa `.pub-nav` umuman yo'qolar va uning o'rnini bosadigan
    menyu yo'q edi. Shart bajarilgach — `<details>` asosidagi mobil menyu
    qo'shilgach — beshinchi element ham qo'yildi.
    """

    def nav(self, response):
        html = response.content.decode(response.charset)
        start = html.index('<nav class="pub-nav"')
        return html[start:html.index("</nav>", start)]

    def test_the_public_navigation_now_reaches_the_portal(self):
        self.assertIn(reverse("sit:home"), self.nav(self.client.get(reverse("courses"))))

    def test_the_blog_door_is_still_there(self):
        self.assertIn(reverse("blog:list"), self.nav(self.client.get(reverse("courses"))))

    def test_a_phone_visitor_gets_a_menu_instead_of_nothing(self):
        """Ilgari `.pub-nav` yashirilar, o'rniga hech narsa qolmasdi."""
        response = self.client.get(reverse("courses"))

        self.assertContains(response, "data-public-menu")
        self.assertContains(response, "pub-mobile-nav")

    def test_both_menus_are_fed_by_the_same_list(self):
        """Ikki nusxa bo'lsa biri eskirib qolardi."""
        from pathlib import Path

        from django.conf import settings

        shell = (Path(settings.BASE_DIR) / "templates/base_public.html").read_text(encoding="utf-8")

        self.assertEqual(shell.count('components/public_nav_links.html'), 2)

    def test_the_menu_works_without_javascript(self):
        """`<details>` brauzerning o'zida ochiladi — JS faqat qulaylik."""
        response = self.client.get(reverse("courses"))

        self.assertContains(response, "<details class=\"pub-mobile-menu\"")
        self.assertContains(response, "<summary")


class TheDoorsActuallyOpenTests(TestCase):
    """Havola bo'lishining o'zi yetmaydi — narigi tomonda sahifa turishi kerak."""

    def setUp(self):
        self.student = User.objects.create_user(
            username="ochil-student", email="o@example.test", password="x"
        )

    def test_a_signed_in_learner_can_open_the_portal(self):
        self.client.force_login(self.student)

        self.assertEqual(self.client.get(reverse("sit:home")).status_code, 200)

    def test_a_signed_in_learner_can_open_the_blog(self):
        self.client.force_login(self.student)

        self.assertEqual(self.client.get(reverse("blog:list")).status_code, 200)

    def test_a_guest_can_open_the_portal(self):
        self.assertEqual(self.client.get(reverse("sit:home")).status_code, 200)
