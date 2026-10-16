"""Yangi akkaunt yaratishning yagona qarori (PUBLIC-01 · PUB1.0b).

`public_registration` flagini avval faqat web `RegisterView` tekshirardi.
Telegram deep-link auth va telefon-kontakt orqali ro'yxat esa noma'lum
identity uchun flagga qaramasdan `CustomUser` yaratardi — ya'ni "ro'yxat
yopiq" amalda "yangi akkaunt yo'q" degani emas edi. Har adapter o'z
tekshiruvini yozsa, keyingi kanal yana unutiladi; shuning uchun qaror shu
yerda bitta: adapter faqat `can_create_account(...)`ni chaqiradi.

Ikki qoida ataylab ajratilgan:

* **Yaratish** (`can_create_account`) — kanal ro'yxatda bo'lishi va flag
  ochiq bo'lishi shart. Ro'yxatda yo'q kanal (va Mini App) fail-closed.
* **Mavjud identity** (`existing_identity_may_continue`) — flag yopiq bo'lsa
  ham mavjud foydalanuvchi kira oladi va Telegramni ulay oladi; faqat
  faolsizlantirilgan hisob hech bir kanalda davom etmaydi. Aks holda Telegram
  deep-link `django.contrib.auth.login` orqali bloklangan xodim yoki o'quvchini
  qayta kiritardi (`login()` `is_active`ni tekshirmaydi).

Rad etish matni generik: kanal, flag nomi yoki identity mavjudligi ochilmaydi.
"""

from dataclasses import dataclass

CHANNEL_WEB = "web"
CHANNEL_TELEGRAM_DEEPLINK = "telegram_deeplink"
CHANNEL_TELEGRAM_PHONE = "telegram_phone"
CHANNEL_MINIAPP = "miniapp"

# Kanal → yangi identity yarata oladimi va sintetik email (Telegram akkaunti
# haqiqiy emailsiz yaratiladi) shu kanalda qabul qilinganmi. Yangi kanal shu
# jadvalga qo'shilmaguncha akkaunt yarata olmaydi.
CHANNEL_RULES = {
    CHANNEL_WEB: {"may_create": True, "synthetic_email": False},
    CHANNEL_TELEGRAM_DEEPLINK: {"may_create": True, "synthetic_email": True},
    CHANNEL_TELEGRAM_PHONE: {"may_create": True, "synthetic_email": True},
    # Mini App faqat mavjud, faol identityni topadi; yaratish yo'li yo'q.
    CHANNEL_MINIAPP: {"may_create": False, "synthetic_email": False},
}

REGISTRATION_CLOSED_MESSAGE = (
    "Hozircha yangi hisob ochilmaydi. Hisobingiz bo'lsa, u bilan kiring."
)
IDENTITY_INACTIVE_MESSAGE = "Bu hisob bilan hozir kirib bo'lmaydi. Yordam: /yordam"


@dataclass(frozen=True)
class RegistrationDecision:
    allowed: bool
    code: str
    message: str = ""
    synthetic_email: bool = False


def can_create_account(channel, request=None, identity=None):
    """Shu kanal hozir yangi `CustomUser` yarata oladimi.

    `request`/`identity` keyingi kesimlar (auth abuse, owner admitted
    policy) uchun shu signaturada qoladi; bugungi qaror ularga bog'liq emas.
    """
    rule = CHANNEL_RULES.get(channel)
    if rule is None or not rule["may_create"]:
        return RegistrationDecision(False, "channel_not_admitted", REGISTRATION_CLOSED_MESSAGE)

    from core.flags import flag_enabled

    if not flag_enabled("public_registration"):
        return RegistrationDecision(False, "registration_closed", REGISTRATION_CLOSED_MESSAGE)
    return RegistrationDecision(True, "allowed", synthetic_email=rule["synthetic_email"])


def existing_identity_may_continue(user):
    """Mavjud identity login/claim qila oladimi — har kanalda bir xil."""
    return bool(user is not None and user.is_active)
