"""Shaxsiy chat — onboarding voronkasi (F2) + workspace kirish nuqtasi.

Mehmon (bog'lanmagan) oqimi:
    /start → tanituv + inline menyu (kurslar / narxlar / AI savol / ro'yxat)
    oddiy matn → AI demo javob (limitli, GUEST_DEMO_QUESTION_LIMIT)
    kontakt ulashish → telefon bilan ro'yxat/bog'lash

Bog'langan user: rolga mos salomlashish (to'liq workspace — F3).
"""

import html

from aiogram import F, Router, types
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from asgiref.sync import sync_to_async
from django.conf import settings

from bot.services import (
    GUEST_DEMO_QUESTION_LIMIT,
    guest_demo_answer,
    link_user_from_start_token,
    list_plans,
    list_public_courses,
    register_guest_via_phone,
    student_display_name,
)

router = Router(name="onboarding")
router.message.filter(F.chat.type == "private")

HTML_MODE = "HTML"

ROLE_LABELS = {
    "admin": "Administrator",
    "teacher": "O'qituvchi",
    "student": "Talaba",
    "linked": "Foydalanuvchi",
    "guest": "Mehmon",
}


# ---------------------------------------------------------------- keyboards

def guest_menu_markup():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📚 Kurslar", callback_data="onb:courses"),
                InlineKeyboardButton(text="💰 Narxlar", callback_data="onb:pricing"),
            ],
            [InlineKeyboardButton(text="🤖 AI'ga savol berish", callback_data="onb:ask")],
            [InlineKeyboardButton(text="📝 Ro'yxatdan o'tish", callback_data="onb:register")],
        ]
    )


def _is_public_domain():
    domain = getattr(settings, "APP_DOMAIN", "") or ""
    return "localhost" not in domain and not domain.startswith("127.")


def site_register_url():
    if _is_public_domain():
        return f"https://{settings.APP_DOMAIN}/users/register/"
    return f"http://{settings.APP_DOMAIN}:8000/users/register/"


def register_menu_markup():
    # Telegram inline tugmalarda localhost URL'ni rad etadi (Wrong HTTP URL) —
    # lokalda URL-tugma o'rniga havolani matn qilib yuboradigan callback ishlatamiz.
    if _is_public_domain():
        site_btn = InlineKeyboardButton(text="🌐 Saytda ro'yxatdan o'tish", url=site_register_url())
    else:
        site_btn = InlineKeyboardButton(text="🌐 Saytda ro'yxatdan o'tish", callback_data="onb:register_site")
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📱 Telefon raqam bilan (shu yerda)", callback_data="onb:register_phone")],
            [site_btn],
            [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="onb:menu")],
        ]
    )


def contact_request_markup():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Raqamni ulashish", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def back_to_menu_markup():
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="⬅️ Menyu", callback_data="onb:menu")]]
    )


# ---------------------------------------------------------------- rendering

def render_guest_welcome():
    return (
        "👋 <b>AzureLMS botiga xush kelibsiz!</b>\n\n"
        "Biz o'zbek tilida <b>turk tilini A1'dan C1'gacha</b> o'rgatamiz: "
        "video darslar, jonli guruh darslari, imtihonlar, sertifikat va "
        "24/7 AI repetitor.\n\n"
        "Quyidan tanlang — yoki shunchaki savolingizni yozib yuboring, "
        "AI konsultant javob beradi 👇"
    )


def render_courses(courses):
    if not courses:
        return "Hozircha faol kurslar yo'q — tez orada qo'shiladi."
    lines = ["📚 <b>Kurslarimiz</b>\n"]
    for c in courses:
        lines.append(
            f"▫️ <b>{html.escape(c['title'])}</b>\n"
            f"   Daraja: {c['level']} · ~{c['duration']} soat"
        )
        if c["description"]:
            lines.append(f"   <i>{html.escape(c['description'])}</i>")
        lines.append("")
    lines.append("O'qishni boshlash uchun ro'yxatdan o'ting 👇")
    return "\n".join(lines)


def render_plans(plans):
    if not plans:
        return "Tariflar hozircha e'lon qilinmagan."
    lines = ["💰 <b>Tariflar</b>\n"]
    for p in plans:
        badge = " ⭐️" if p["is_popular"] else ""
        price = f"{p['price']:,}".replace(",", " ")
        lines.append(f"▫️ <b>{html.escape(p['name'])}</b>{badge} — {price} so'm/oy")
        for feat in p["features"]:
            lines.append(f"   • {html.escape(feat)}")
        lines.append("")
    lines.append("Savollaringiz bo'lsa — shunchaki yozib yuboring 🤖")
    return "\n".join(lines)


def render_welcome(lms_user, lms_role):
    if lms_user is None:
        return render_guest_welcome()
    name = html.escape(student_display_name(lms_user))
    role_label = ROLE_LABELS.get(lms_role, "Foydalanuvchi")
    lines = [
        f"👋 Salom, <b>{name}</b>!",
        f"Maqomingiz: <b>{role_label}</b>",
        "",
    ]
    if lms_role in {"admin", "teacher"}:
        lines.append(
            "Guruh buyruqlari (dars guruhida):\n"
            "• <code>/dars 1</code> — davomat boshlash\n"
            "• <code>/dars tugadi</code> — yakunlash, ismli e'lon + ogohlantirishlar\n"
            "• <code>/davomat</code> — joriy holat\n"
            "• <code>/link_cohort ID</code> — guruhni kohortga ulash\n\n"
            "Shaxsiy buyruqlar: /darslarim · /davomatim · /tolov\n"
            "Savol yozsangiz — AI repetitor javob beradi 🤖"
        )
    else:
        lines.append(
            "Menyu: quyidagi tugmalar yoki buyruqlar —\n"
            "📚 /darslarim · ✅ /davomatim · 💳 /tolov\n\n"
            "🤖 Shunchaki savol yozing — AI repetitor javob beradi "
            "(turk tili, darslar, mashqlar — hammasi)."
        )
    return "\n".join(lines)


# ---------------------------------------------------------------- commands

@router.message(CommandStart())
async def cmd_start_handler(
    message: types.Message,
    command: CommandObject,
    lms_user,
    lms_role,
):
    token = command.args

    if token:
        result = await sync_to_async(link_user_from_start_token)(
            token,
            message.from_user.id,
            message.from_user.username or "",
        )
        if not result.ok:
            await message.answer(result.message)
            return
        from bot.middleware import resolve_identity

        lms_user, lms_role = await sync_to_async(resolve_identity)(message.from_user.id)
        await message.answer(
            f"✅ {result.message}\n\n" + render_welcome(lms_user, lms_role),
            parse_mode=HTML_MODE,
        )
        return

    if lms_user is None:
        await message.answer(
            render_guest_welcome(), parse_mode=HTML_MODE, reply_markup=guest_menu_markup()
        )
        return

    from bot.routers.workspace import student_menu_markup

    await message.answer(
        render_welcome(lms_user, lms_role),
        parse_mode=HTML_MODE,
        reply_markup=student_menu_markup(),
    )


@router.message(Command("yordam", "help"))
async def help_handler(message: types.Message, lms_user, lms_role):
    if lms_user is None:
        await message.answer(
            render_guest_welcome(), parse_mode=HTML_MODE, reply_markup=guest_menu_markup()
        )
        return
    from bot.routers.workspace import student_menu_markup

    await message.answer(
        render_welcome(lms_user, lms_role),
        parse_mode=HTML_MODE,
        reply_markup=student_menu_markup(),
    )


# ---------------------------------------------------------------- callbacks

@router.callback_query(F.data == "onb:menu")
async def cb_menu(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        render_guest_welcome(), parse_mode=HTML_MODE, reply_markup=guest_menu_markup()
    )


@router.callback_query(F.data == "onb:courses")
async def cb_courses(callback: types.CallbackQuery):
    await callback.answer()
    courses = await sync_to_async(list_public_courses)()
    await callback.message.edit_text(
        render_courses(courses), parse_mode=HTML_MODE, reply_markup=register_menu_markup()
    )


@router.callback_query(F.data == "onb:pricing")
async def cb_pricing(callback: types.CallbackQuery):
    await callback.answer()
    plans = await sync_to_async(list_plans)()
    await callback.message.edit_text(
        render_plans(plans), parse_mode=HTML_MODE, reply_markup=register_menu_markup()
    )


@router.callback_query(F.data == "onb:ask")
async def cb_ask(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        "🤖 Savolingizni oddiy xabar qilib yozib yuboring — AI konsultant javob "
        f"beradi (demo: {GUEST_DEMO_QUESTION_LIMIT} tagacha savol).\n\n"
        "Masalan: <i>«Kurslar qanday o'tadi?»</i>, <i>«Turk tilini necha oyda o'rganaman?»</i>",
        parse_mode=HTML_MODE,
        reply_markup=back_to_menu_markup(),
    )


@router.callback_query(F.data == "onb:register")
async def cb_register(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        "📝 <b>Ro'yxatdan o'tish</b>\n\n"
        "Qulay yo'lni tanlang: telefon raqamingiz bilan shu yerning o'zida "
        "(30 soniya), yoki saytda to'liq forma bilan.",
        parse_mode=HTML_MODE,
        reply_markup=register_menu_markup(),
    )


@router.callback_query(F.data == "onb:register_site")
async def cb_register_site(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.answer(
        f"🌐 Saytda ro'yxatdan o'tish:\n{site_register_url()}"
    )


@router.callback_query(F.data == "onb:register_phone")
async def cb_register_phone(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.answer(
        "Quyidagi tugmani bosib raqamingizni ulashing — hisob avtomatik yaratiladi. "
        "Raqamingiz faqat hisob uchun ishlatiladi.",
        reply_markup=contact_request_markup(),
    )


# ---------------------------------------------------------------- contact (ro'yxat)

@router.message(F.contact)
async def contact_handler(message: types.Message, lms_user):
    contact = message.contact
    # Xavfsizlik: faqat O'ZINING raqamini qabul qilamiz (Telegram tasdiqlagan)
    if not contact or contact.user_id != message.from_user.id:
        await message.answer(
            "Iltimos, \"Raqamni ulashish\" tugmasi orqali o'z raqamingizni yuboring.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    if lms_user is not None:
        await message.answer(
            "Siz allaqachon ro'yxatdan o'tgansiz ✅", reply_markup=ReplyKeyboardRemove()
        )
        return

    result = await sync_to_async(register_guest_via_phone)(
        telegram_id=message.from_user.id,
        telegram_username=message.from_user.username or "",
        phone=contact.phone_number,
        first_name=contact.first_name or message.from_user.first_name or "",
        last_name=contact.last_name or message.from_user.last_name or "",
    )
    if not result.ok:
        await message.answer(result.message, reply_markup=ReplyKeyboardRemove())
        return

    from bot.middleware import resolve_identity

    lms_user, lms_role = await sync_to_async(resolve_identity)(message.from_user.id)
    await message.answer(
        f"🎉 {result.message}\n\n" + render_welcome(lms_user, lms_role),
        parse_mode=HTML_MODE,
        reply_markup=ReplyKeyboardRemove(),
    )


# ---------------------------------------------------------------- guest AI demo
# MUHIM: bu catch-all handler routerning ENG OXIRIDA turishi shart —
# aks holda buyruqlarni ham yutib yuboradi.

@router.message(F.text & ~F.text.startswith("/"))
async def guest_text_handler(message: types.Message, lms_user):
    if lms_user is not None:
        # Bog'langan user — to'liq AI repetitor (messenger engine, F3)
        from bot.routers.workspace import send_long
        from bot.services import telegram_ai_reply

        await message.bot.send_chat_action(message.chat.id, "typing")
        result = await sync_to_async(telegram_ai_reply)(lms_user, message.text)
        if not result.ok:
            await message.answer(result.message)
            return
        # AI matni markdown bo'lishi mumkin — parse_mode'siz (xavfsiz) yuboramiz
        await send_long(message, result.answer)
        return

    await message.bot.send_chat_action(message.chat.id, "typing")
    result = await sync_to_async(guest_demo_answer)(
        message.from_user.id,
        message.from_user.username or "",
        message.text,
    )
    if not result.ok:
        await message.answer(result.message, reply_markup=guest_menu_markup())
        return

    tail = ""
    if result.remaining <= 1:
        tail = (
            f"\n\n<i>Demo savollar: {result.remaining} ta qoldi. Cheklovsiz AI repetitor "
            "uchun ro'yxatdan o'ting 👇</i>"
        )
    await message.answer(
        html.escape(result.answer) + tail,
        parse_mode=HTML_MODE,
        reply_markup=guest_menu_markup() if result.remaining <= 1 else None,
    )
