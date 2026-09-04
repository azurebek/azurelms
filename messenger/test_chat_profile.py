"""Suhbatdoshning profil kartasi — va uning chegarasi.

Owner so'radi: guruhda profil rasmiga bosilsa Telegram'dagidek o'ngdan
ma'lumot paneli ochilsin.

Telegram'dan bitta muhim farq bor va u ataylab: Telegram — kontaktlar
ilovasi, bu esa o'quv platformasi. Guruhdagi o'quvchining telefon raqami
va emailini sinfdoshlariga ko'rsatish shaxsiy ma'lumotni tarqatish bo'lardi.
Shuning uchun aloqa ma'lumotlari faqat xodimga va odamning o'ziga ko'rinadi.

Va yagona gate: umumiy xonasi bo'lmagan odam hech narsa ko'rmaydi — aks
holda istalgan o'quvchi manzildagi id'ni almashtirib butun bazani o'qib
chiqardi.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from messenger.models import ChatRoom
from messenger.profile_service import profile_card

User = get_user_model()


class ChatProfileFixture:
    def setUp(self):
        super().setUp()
        self.teacher = User.objects.create_user(
            username="profil-teacher", email="t@example.test", password="x",
            is_staff=True, first_name="Dilshod", last_name="Rahimov",
        )
        self.student = User.objects.create_user(
            username="profil-student", email="s@example.test", password="x",
            first_name="Dilnoza", last_name="Karimova",
            phone_number="+998901112233", bio="Turk tilini o'rganyapman.",
            total_xp=1240,
        )
        self.classmate = User.objects.create_user(
            username="profil-classmate", email="c@example.test", password="x",
            first_name="Jasur", last_name="Aliyev",
        )
        self.outsider = User.objects.create_user(
            username="profil-outsider", email="o@example.test", password="x"
        )
        self.room = ChatRoom.objects.create(room_type="group", name="A1 guruh")
        self.room.participants.add(self.student, self.classmate, self.teacher)

    def url(self, user):
        return reverse("messenger:chat_profile", kwargs={"user_id": user.pk})


class WhatAClassmateSeesTests(ChatProfileFixture, TestCase):
    def test_a_classmate_sees_the_public_part(self):
        self.client.force_login(self.classmate)

        data = self.client.get(self.url(self.student)).json()["profile"]

        self.assertEqual(data["name"], "Dilnoza Karimova")
        self.assertEqual(data["role"], "O'quvchi")
        self.assertEqual(data["bio"], "Turk tilini o'rganyapman.")
        self.assertEqual(data["total_xp"], 1240)
        self.assertIn("A1 guruh", data["shared"])

    def test_a_classmate_never_sees_contact_details(self):
        """Eng muhim chegara: telefon va email sinfdoshga ko'rinmaydi."""
        self.client.force_login(self.classmate)

        response = self.client.get(self.url(self.student))

        self.assertEqual(response.json()["profile"]["contacts"], [])
        self.assertNotContains(response, "+998901112233")
        self.assertNotContains(response, "s@example.test")

    def test_a_teacher_sees_the_contact_details(self):
        """O'qituvchi buni backoffice'da ham ko'radi — yangi ruxsat emas."""
        self.client.force_login(self.teacher)

        contacts = self.client.get(self.url(self.student)).json()["profile"]["contacts"]

        values = [c["value"] for c in contacts]
        self.assertIn("+998901112233", values)
        self.assertIn("s@example.test", values)

    def test_a_person_sees_their_own_contacts(self):
        self.client.force_login(self.student)

        data = self.client.get(self.url(self.student)).json()["profile"]

        self.assertTrue(data["is_self"])
        self.assertTrue(data["contacts"])

    def test_the_teacher_is_labelled_as_a_teacher(self):
        self.client.force_login(self.student)

        self.assertEqual(
            self.client.get(self.url(self.teacher)).json()["profile"]["role"], "O'qituvchi"
        )


class WhoMayLookAtAllTests(ChatProfileFixture, TestCase):
    def test_someone_from_another_room_gets_nothing(self):
        self.client.force_login(self.outsider)

        response = self.client.get(self.url(self.student))

        self.assertEqual(response.status_code, 404)

    def test_an_anonymous_visitor_gets_nothing(self):
        response = self.client.get(self.url(self.student))

        self.assertNotEqual(response.status_code, 200)

    def test_a_missing_person_looks_the_same_as_a_hidden_one(self):
        """«Yo'q» va «sizga ko'rsatilmaydi» tashqaridan farq qilmasin."""
        self.client.force_login(self.classmate)

        missing = self.client.get(reverse("messenger:chat_profile", kwargs={"user_id": 999999}))
        hidden = self.client.get(self.url(self.outsider))

        self.assertEqual(missing.status_code, hidden.status_code)

    def test_a_deactivated_person_is_hidden(self):
        self.student.is_active = False
        self.student.save(update_fields=["is_active"])
        self.client.force_login(self.classmate)

        self.assertEqual(self.client.get(self.url(self.student)).status_code, 404)

    def test_an_ai_room_does_not_make_people_visible_to_each_other(self):
        """AI xonasi — shaxsiy, u umumiylik hisoblanmaydi."""
        ai_room = ChatRoom.objects.create(room_type="ai", name="AI")
        ai_room.participants.add(self.outsider, self.student)

        card = profile_card(self.outsider, self.student.pk)

        self.assertIsNotNone(card)  # xona umumiy — ko'rish mumkin
        self.assertEqual(card["shared"], [])  # ammo AI xonasi ro'yxatga chiqmaydi


class TheAssistantHasAProfileTooTests(ChatProfileFixture, TestCase):
    """AzureAI odam emas, shuning uchun kartasi alohida yo'ldan keladi."""

    def test_the_assistant_card_describes_what_it_actually_does(self):
        self.client.force_login(self.student)

        card = self.client.get(reverse("messenger:chat_assistant_profile")).json()["profile"]

        self.assertEqual(card["name"], "Azure AI")
        self.assertEqual(card["role"], "AI repetitor")
        self.assertTrue(card["is_assistant"])
        self.assertIn("Dars materiallaringiz", card["bio"])

    def test_it_admits_the_assistant_can_be_wrong(self):
        """Javob o'qituvchi tekshiruvi o'rniga qabul qilinmasin."""
        self.client.force_login(self.student)

        card = self.client.get(reverse("messenger:chat_assistant_profile")).json()["profile"]

        self.assertIn("adashishi mumkin", card["note"])

    def test_it_shows_the_settings_the_learner_actually_chose(self):
        self.client.force_login(self.student)

        card = self.client.get(reverse("messenger:chat_assistant_profile")).json()["profile"]

        labels = [f["label"] for f in card["facts"]]
        self.assertIn("Model", labels)
        self.assertIn("Uslub", labels)

    def test_an_anonymous_visitor_gets_nothing(self):
        response = self.client.get(reverse("messenger:chat_assistant_profile"))

        self.assertNotEqual(response.status_code, 200)


class TheChatPageOffersTheProfileTests(TestCase):
    """Panel haqiqiy guruh sahifasida bor va avatar bosiladigan."""

    def setUp(self):
        import datetime

        from django.utils import timezone

        from cohorts.models import Cohort, Enrollment
        from courses.models import Course
        from messenger.models import Message

        today = timezone.localdate()
        self.teacher = User.objects.create_user(
            username="sahifa-teacher", email="st@example.test", password="x", is_staff=True
        )
        self.student = User.objects.create_user(
            username="sahifa-student", email="ss@example.test", password="x",
            first_name="Dilnoza", last_name="Karimova",
        )
        self.classmate = User.objects.create_user(
            username="sahifa-classmate", email="sc@example.test", password="x"
        )
        course = Course.objects.create(
            title="Kurs", description="d", level="beginner", instructor=self.teacher
        )
        cohort = Cohort.objects.create(name="A1 guruh", course=course, start_date=today)
        for person in (self.student, self.classmate):
            Enrollment.objects.create(
                student=person, cohort=cohort, status=Enrollment.STATUS_ACTIVE,
                next_payment_deadline=today + datetime.timedelta(days=30),
            )
        # Guruh xonasini obuna signali o'zi yaratadi (`messenger/access.py`),
        # shuning uchun bu yerda yaratilmaydi — aks holda bitta cohortda
        # ikkita xona paydo bo'lardi.
        room = ChatRoom.objects.get(room_type="group", cohort=cohort)
        Message.objects.create(room=room, sender=self.student, text="salom")

    def test_the_group_page_carries_the_panel_and_a_clickable_avatar(self):
        self.client.force_login(self.classmate)

        response = self.client.get(reverse("messenger:group"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "data-chat-profile")
        self.assertContains(response, f'data-sender-id="{self.student.pk}"')
