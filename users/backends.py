from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

User = get_user_model()


def find_login_user(identifier):
    """Login identifikatori bo'yicha bitta hisob: aniq username ustun, keyin yagona email.

    Ilgari `username=X OR email≈X` bitta `get()` edi: bir hisobning username'i
    boshqasining emailiga teng bo'lsa `MultipleObjectsReturned` → 500. Email
    bir nechta hisobda bo'lsa qaysi biri ekanini taxmin qilmaymiz.
    """
    user = User.objects.filter(username=identifier).first()
    if user is not None:
        return user
    matches = list(User.objects.filter(email__iexact=identifier)[:2])
    return matches[0] if len(matches) == 1 else None


class EmailOrUsernameBackend(ModelBackend):
    """
    Foydalanuvchiga ham username, ham email orqali tizimga kirish imkonini beruvchi backend.
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None
        user = find_login_user(username)
        if user is None:
            # Hisob yo'q bo'lsa ham parol bir marta xeshlanadi (Django `ModelBackend`
            # kabi): aks holda noma'lum email tezroq javob olib, qaysi email
            # ro'yxatdan o'tgani javob vaqtidan bilinardi (PUB1.4c).
            User().set_password(password)
            return None
        # Parolsiz (Telegram) hisobda ham Django `check_password` xeshni bir marta
        # ishlatadi — vaqt farqi yo'q.
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
