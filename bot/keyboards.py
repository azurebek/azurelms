from urllib.parse import quote

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from django.conf import settings


def is_public_domain():
    """Mini App faqat public HTTPS domenda ochiladi.

    Lokalda (`localhost`, `127.*`) Telegram `web_app` tugmasini rad etadi,
    shuning uchun tugma quruvchilar `None` qaytaradi va chaqiruvchi eski
    (oddiy havolali) yo'lga tushadi.
    """
    domain = getattr(settings, "APP_DOMAIN", "") or ""
    return bool(domain) and "localhost" not in domain and not domain.startswith("127.")


def miniapp_button(text, path):
    """Mini App tugmasi (F5) — sayt sahifasini bot ichida avto-login bilan ochadi.

    `bot/routers/workspace.py` da edi; outbox worker ham shu tugmani
    yasashi kerak bo'lgani uchun neytral modulga ko'chirildi. Router
    moduli worker'ga import qilinmasligi kerak.
    """
    if not is_public_domain():
        return None
    url = f"https://{settings.APP_DOMAIN}/bot/miniapp/?next={quote(path, safe='')}"
    return InlineKeyboardButton(text=text, web_app=WebAppInfo(url=url))


def attendance_checkin_markup(session_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Darsga kirdim",
                    callback_data=f"attendance:{session_id}",
                )
            ]
        ]
    )
