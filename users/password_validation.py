"""Parol qoidalari o'zbekcha gapiradi.

Sayt boshdan-oyoq o'zbekcha, ammo parol xatolari ingliz tilida chiqardi:
«This password is too short. It must contain at least 8 characters.» Sabab
oddiy — bu Django'ning o'z xabarlari, `LANGUAGE_CODE` esa `en-us`.

`LANGUAGE_CODE` ni `uz` ga o'tkazish yechim emas: Django'ning `uz` tarjimasida
aynan shu to'rt validator **tarjima qilinmagan** (faqat «ikkala parol mos
kelmadi» bor), qolgan yuzlab satr esa kutilmaganda o'zgarardi.

Shuning uchun to'rttasi ham shu yerda meros olinadi va faqat **matni**
almashtiriladi. Tekshiruv mantig'iga tegilmaydi — u Django'niki bo'lib
qolaveradi, ya'ni 20 000 ta eng ko'p ishlatiladigan parol ro'yxati ham,
o'xshashlik hisobi ham o'z joyida.

Xabarlar buyruq emas, **maslahat** ohangida: nima xato ekanini va nima
qilish kerakligini bitta jumlada aytadi.
"""

from django.contrib.auth import password_validation as django_validators


class MinimumLengthValidator(django_validators.MinimumLengthValidator):
    def get_error_message(self):
        return "Parol juda qisqa — kamida %(min_length)d ta belgi bo'lsin." % {
            "min_length": self.min_length,
        }

    def get_help_text(self):
        return f"Kamida {self.min_length} ta belgi."


class CommonPasswordValidator(django_validators.CommonPasswordValidator):
    def get_error_message(self):
        return (
            "Bu parol juda ko'p ishlatiladi va birinchi urinishdayoq topiladi. "
            "Boshqasini o'ylab toping."
        )

    def get_help_text(self):
        return "Ommabop parol emas (masalan «parol123» yaramaydi)."


class NumericPasswordValidator(django_validators.NumericPasswordValidator):
    def get_error_message(self):
        return "Parol faqat raqamdan iborat bo'lmasin — harf ham qo'shing."

    def get_help_text(self):
        return "Faqat raqam emas."


class UserAttributeSimilarityValidator(
    django_validators.UserAttributeSimilarityValidator
):
    def get_error_message(self):
        # Django bu yerga `verbose_name` params'ini uzatadi, ammo u model
        # maydonining nomi — ingliz tilida («email address»). Shuning uchun
        # xabarga qo'shilmaydi: qaysi maydonga o'xshashini aytish o'rniga
        # nima qilish kerakligi aytiladi.
        return (
            "Parol ismingiz yoki emailingizga juda o'xshash. "
            "Ular bilan bog'liq bo'lmagan parol tanlang."
        )

    def get_help_text(self):
        return "Ism va emailga o'xshamasin."
