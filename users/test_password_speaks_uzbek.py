"""Parol qoidalari o'zbekcha gapiradi va xato yozilgan joyda chiqadi.

UX auditning 4-topilmasi. Ro'yxatdan o'tishda ikkita alohida nuqson bor edi:

1. **Til.** Sayt boshdan-oyoq o'zbekcha, parol xatosi esa «This password is
   too short. It must contain at least 8 characters.» Sabab: bular
   Django'ning o'z xabarlari, `LANGUAGE_CODE` esa `en-us`.
2. **Joy.** Django parol kuchi xatosini `password2` ga — **tasdiqlash**
   maydoniga — qo'yadi. Foydalanuvchi parolni yuqoridagi maydonga yozgan,
   xato pastda chiqadi: u pastdagini tuzatib qayta yuboradi va yana o'sha
   xatoni oladi.

`LANGUAGE_CODE` ni `uz` ga o'tkazish yechim emas edi: Django'ning `uz`
tarjimasida aynan shu to'rt validator tarjima qilinmagan. Shuning uchun
`users/password_validation.py` da to'rttasi meros olinib, faqat matni
almashtirildi — tekshiruv mantig'i Django'niki bo'lib qoldi.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from users.forms import CustomUserCreationForm, UzbekSetPasswordForm

User = get_user_model()


def errors_for(**passwords):
    data = {"first_name": "Ali", "email": "parol-test@example.test"}
    data.update(passwords)
    form = CustomUserCreationForm(data=data)
    form.is_valid()
    return form.errors


class ThePasswordRulesSpeakUzbekTests(TestCase):
    def test_a_short_password_is_explained_in_uzbek(self):
        errors = errors_for(password1="Qi5!a", password2="Qi5!a")

        self.assertIn("Parol juda qisqa", " ".join(errors["password1"]))

    def test_a_common_password_is_explained_in_uzbek(self):
        errors = errors_for(password1="password123", password2="password123")

        self.assertIn("juda ko'p ishlatiladi", " ".join(errors["password1"]))

    def test_an_all_digit_password_is_explained_in_uzbek(self):
        errors = errors_for(password1="93028471625", password2="93028471625")

        self.assertIn("faqat raqamdan", " ".join(errors["password1"]))

    def test_a_password_like_the_email_is_explained_in_uzbek(self):
        errors = errors_for(
            password1="parol-test@example.test", password2="parol-test@example.test",
        )

        self.assertIn("o'xshash", " ".join(errors["password1"]))

    def test_the_mismatch_message_is_uzbek_too(self):
        errors = errors_for(password1="Qishloq7!tepa", password2="boshqa")

        self.assertIn("bir xil emas", " ".join(errors["password2"]))

    def test_nothing_english_leaks_through(self):
        """Bitta inglizcha satr ham sahifani begona qilib qo'yadi."""
        errors = errors_for(password1="12345", password2="boshqa")

        everything = " ".join(sum(errors.values(), []))
        for word in ("password", "must", "This", "characters"):
            self.assertNotIn(word, everything)


class TheErrorAppearsWhereItWasTypedTests(TestCase):
    def test_strength_errors_land_on_the_password_field(self):
        errors = errors_for(password1="12345", password2="12345")

        self.assertIn("password1", errors)
        self.assertNotIn("password2", errors)

    def test_the_mismatch_stays_on_the_confirmation_field(self):
        """Bu xato haqiqatan tasdiqlash maydoni haqida — ko'chirilmaydi."""
        errors = errors_for(password1="Qishloq7!tepa", password2="boshqa")

        self.assertIn("password2", errors)
        self.assertNotIn("password1", errors)

    def test_the_help_text_under_the_field_is_uzbek(self):
        form = CustomUserCreationForm()

        help_text = form.fields["password1"].help_text
        self.assertIn("Kamida 8 ta belgi", help_text)
        self.assertNotIn("<ul>", help_text)

    def test_the_register_page_shows_the_error_under_the_password_box(self):
        response = self.client.post(reverse("register"), {
            "first_name": "Ali", "email": "sahifa@example.test",
            "password1": "12345", "password2": "12345",
        })

        html = response.content.decode(response.charset)
        between = html[html.index('name="password1"'):html.index('name="password2"')]
        self.assertIn("Parol juda qisqa", between)

    def test_several_errors_do_not_run_into_each_other(self):
        """`|striptags` `<li>` larni yechib matnlarni yopishtirib qo'yardi.

        Natijada: «...bo'lsin.Bu parol juda ko'p...». Parol maydoni aynan
        shu holat — Django uchta qoidani birdan aytishi mumkin.
        """
        response = self.client.post(reverse("register"), {
            "first_name": "Ali", "email": "qatorlar@example.test",
            "password1": "12345", "password2": "12345",
        })

        html = response.content.decode(response.charset)
        self.assertNotIn("bo&#x27;lsin.Bu parol", html)
        self.assertIn("bo&#x27;lsin.</div>", html)


class ThePasswordResetPageSpeaksUzbekTests(TestCase):
    """Parolni tiklash sahifasida ham ayni ikki nuqson bor edi."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="tiklash", email="tiklash@example.test", password="Eski7!parol"
        )

    def _form(self, **data):
        form = UzbekSetPasswordForm(self.user, data=data)
        form.is_valid()
        return form.errors

    def test_a_weak_new_password_is_explained_in_uzbek(self):
        errors = self._form(new_password1="12345", new_password2="12345")

        self.assertIn("Parol juda qisqa", " ".join(errors["new_password1"]))

    def test_the_error_lands_on_the_field_that_was_typed_in(self):
        errors = self._form(new_password1="12345", new_password2="12345")

        self.assertIn("new_password1", errors)
        self.assertNotIn("new_password2", errors)

    def test_the_mismatch_stays_on_the_confirmation_field(self):
        errors = self._form(new_password1="Qishloq7!tepa", new_password2="boshqa")

        self.assertIn("bir xil emas", " ".join(errors["new_password2"]))
        self.assertNotIn("new_password1", errors)

    def test_a_good_password_is_accepted(self):
        """Qoida qattiqlashmadi — faqat matni o'zgardi."""
        form = UzbekSetPasswordForm(self.user, data={
            "new_password1": "Qishloq7!tepa", "new_password2": "Qishloq7!tepa",
        })

        self.assertTrue(form.is_valid(), form.errors)


class TheRulesThemselvesDidNotChangeTests(TestCase):
    """Matn almashtirildi, tekshiruv emas — Django mantig'i o'z joyida."""

    def test_a_strong_password_still_passes(self):
        form = CustomUserCreationForm(data={
            "first_name": "Ali", "email": "kuchli@example.test",
            "password1": "Qishloq7!tepa", "password2": "Qishloq7!tepa",
        })

        self.assertTrue(form.is_valid(), form.errors)

    def test_the_common_password_list_is_still_django_s(self):
        """20 000 ta ommabop parol ro'yxati o'zimizniki emas, Django'niki."""
        from users.password_validation import CommonPasswordValidator

        validator = CommonPasswordValidator()
        self.assertIn("qwerty123", validator.passwords)

    def test_the_minimum_is_still_eight(self):
        from users.password_validation import MinimumLengthValidator

        self.assertEqual(MinimumLengthValidator().min_length, 8)
