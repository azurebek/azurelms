from urllib.parse import quote

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    WebAppInfo,
)
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


# ---------------------------------------------------------------- doimiy klaviatura (T1)
#
# Botning auditoriyasi — «kompyuter ishlatmaydigan» odam (telegram-bot-plan.md
# vizyoni). Shunga qaramay undan `/davomatim` ni **eslab qolish** talab
# qilinardi: 23 ta slash buyruq bor edi, doimiy klaviatura esa yo'q.
# Bu klaviatura buyruqlarni **almashtirmaydi** (owner qarori) — u yonida turadi.
#
# Tugma matni oddiy xabar bo'lib keladi, ya'ni har biri o'sha buyruqning
# handleriga tushadi. Matn konstantasi shu yerda, chunki uni ikki tomon ham
# ishlatadi: klaviatura quruvchi va router filtri (`F.text == ...`). Ikki joyda
# qo'lda yozilsa, bittasini o'zgartirib ikkinchisini unutish tugmani jimgina
# ishlamaydigan qilardi.

BTN_COURSES = "📚 Darslarim"
BTN_ATTENDANCE = "🗓 Davomatim"
BTN_PAYMENT = "💳 To'lov"
BTN_AI = "🤖 AI repetitor"
BTN_GROUPS = "👥 Guruhlarim"
BTN_GRADING = "✍️ Baholash"
BTN_STATS = "📊 Statistika"
BTN_RECEIPTS = "🧾 Cheklar"
BTN_ENROLL = "🎓 Kursga yozilish"
BTN_HELP = "❓ Yordam"
BTN_HIDE = "⌨️ Klaviaturani yopish"

#: Rol → tugma qatorlari. Har rolda **to'rtta** amal: klaviatura ekranning
#: pastini egallaydi va uzun ro'yxat chat maydonini siqib qo'yadi.
WORKSPACE_KEYBOARDS = {
    "student": [[BTN_COURSES, BTN_ATTENDANCE], [BTN_PAYMENT, BTN_AI], [BTN_HIDE]],
    "teacher": [[BTN_GROUPS, BTN_GRADING], [BTN_AI, BTN_HELP], [BTN_HIDE]],
    "admin": [[BTN_STATS, BTN_RECEIPTS], [BTN_GROUPS, BTN_GRADING], [BTN_HIDE]],
    "linked": [[BTN_ENROLL, BTN_HELP], [BTN_HIDE]],
}


def workspace_keyboard(role):
    """Rolga mos doimiy klaviatura; noma'lum rol uchun `None`.

    **Guest uchun ataylab `None`.** Bog'lanmagan foydalanuvchi oqimida telefon
    ulashish klaviaturasi ishlatiladi (`request_contact`), va Telegramda chatda
    bir vaqtda faqat bitta reply klaviatura bo'ladi — yangisi eskisini
    almashtiradi. Guestga ish stoli klaviaturasi qo'yilsa, ro'yxatdan o'tish
    oqimi o'rtasida telefon tugmasi yo'qolib qolardi.
    """
    rows = WORKSPACE_KEYBOARDS.get(role)
    if not rows:
        return None
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=label) for label in row] for row in rows],
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Savolingizni yozing yoki tugmani tanlang",
    )


def hide_keyboard():
    """Klaviaturani olib tashlaydi — `/start` yoki `/yordam` uni qaytaradi."""
    return ReplyKeyboardRemove()


def keyboard_labels(role):
    """Rolga tegishli tugma matnlari — testlar va yordam matni uchun."""
    return [label for row in WORKSPACE_KEYBOARDS.get(role, []) for label in row]


#: Barcha tugma matnlari — hech biri handlersiz qolmasligini tekshirish uchun.
ALL_BUTTON_LABELS = sorted(
    {label for rows in WORKSPACE_KEYBOARDS.values() for row in rows for label in row}
)
