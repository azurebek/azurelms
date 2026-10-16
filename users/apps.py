from django.apps import AppConfig


class UsersConfig(AppConfig):
    name = "users"

    def ready(self):
        # Smart Form registratsiyasi: @register_form dekoratorlari modul import
        # bo'lganda ishlaydi — app yuklanishida bir marta shu yerda import qilamiz.
        from users import smart_forms  # noqa: F401
        # Release tekshiruvi (`check --deploy`): parol tiklash xati yetkaziladimi.
        from users import checks  # noqa: F401
