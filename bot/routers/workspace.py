"""Bog'langan user workspace'i (F3) — shaxsiy chat menyusi.

Buyruqlar/tugmalar: darslarim (progress), davomatim, to'lov holati.
Erkin matn AI repetitorga boradi (onboarding catch-all → telegram_ai_reply).
"""

import html
import time
from urllib.parse import quote

from aiogram import F, Router, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from asgiref.sync import sync_to_async
from django.conf import settings

from bot.services import (
    begin_course_enrollment,
    list_plans,
    list_public_courses,
    student_course_map,
    student_open_lesson,
    student_overview,
    student_payment_overview,
    student_recent_attendance,
    submit_payment_receipt,
)

router = Router(name="workspace")
router.message.filter(F.chat.type == "private")

HTML_MODE = "HTML"
TG_MESSAGE_LIMIT = 4000  # 4096 rasmiy limitdan zaxira bilan


def _is_public_domain():
    domain = getattr(settings, "APP_DOMAIN", "") or ""
    return "localhost" not in domain and not domain.startswith("127.")


def miniapp_button(text, path):
    """Mini App tugmasi (F5) — sayt sahifasini bot ichida avto-login bilan ochadi.

    Telegram web_app tugmasi faqat public HTTPS'da ishlaydi — lokalda None.
    """
    if not _is_public_domain():
        return None
    url = f"https://{settings.APP_DOMAIN}/bot/miniapp/?next={quote(path, safe='')}"
    return InlineKeyboardButton(text=text, web_app=WebAppInfo(url=url))


def student_menu_markup():
    rows = [
        [
            InlineKeyboardButton(text="📚 Darslarim", callback_data="ws:courses"),
            InlineKeyboardButton(text="✅ Davomatim", callback_data="ws:attendance"),
        ],
        [
            InlineKeyboardButton(text="💳 To'lovim", callback_data="ws:payment"),
            InlineKeyboardButton(text="🤖 AI repetitor", callback_data="ws:ai"),
        ],
        [InlineKeyboardButton(text="🎓 Kursga yozilish", callback_data="ws:enroll")],
    ]
    webapp_btn = miniapp_button("🌐 Saytni ochish (Mini App)", "/users/dashboard/")
    if webapp_btn:
        rows.append([webapp_btn])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def enroll_courses_markup(courses):
    rows = [
        [InlineKeyboardButton(text=f"🎓 {c['title']}", callback_data=f"enr:c:{c['id']}")]
        for c in courses[:10]
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows) if rows else None


def enroll_plans_markup(course_id, plans):
    rows = []
    for p in plans[:8]:
        price = f"{p['price']:,}".replace(",", " ")
        star = "⭐️ " if p.get("is_popular") else ""
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{star}{p['name']} — {price} so'm/oy",
                    callback_data=f"enr:p:{course_id}:{p['id']}",
                )
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows) if rows else None


async def send_long(message: types.Message, text: str, **kwargs):
    """4096 belgi limitidan oshgan javobni bo'lib yuboradi.

    reply_markup faqat OXIRGI bo'lakka qo'shiladi (tugmalar takrorlanmasin).
    """
    reply_markup = kwargs.pop("reply_markup", None)
    while text:
        chunk = text[:TG_MESSAGE_LIMIT]
        if len(text) > TG_MESSAGE_LIMIT:
            cut = chunk.rfind("\n")
            if cut > TG_MESSAGE_LIMIT // 2:
                chunk = chunk[:cut]
        text = text[len(chunk):].lstrip("\n")
        is_last = not text
        await message.answer(
            chunk, reply_markup=reply_markup if is_last else None, **kwargs
        )


# ---------------------------------------------------------------- rendering

def render_courses_overview(items):
    if not items:
        return "Siz hali kursga yozilmagansiz. Kurslar bilan tanishish uchun saytga kiring yoki savol yozing."
    lines = ["📚 <b>Darslarim</b>\n"]
    for it in items:
        bar_filled = round(it["progress"] / 10)
        bar = "▰" * bar_filled + "▱" * (10 - bar_filled)
        lines.append(
            f"▫️ <b>{html.escape(it['course'])}</b> · {html.escape(it['cohort'])}\n"
            f"   {bar} {it['progress']}% ({it['completed']}/{it['total']} dars) · {it['status']}"
        )
    return "\n".join(lines)


def render_attendance(items):
    if not items:
        return "Davomat yozuvlari hali yo'q."
    lines = ["✅ <b>So'nggi davomatim</b>\n"]
    for it in items:
        lines.append(f"{it['date']} — {html.escape(it['lesson'])}: {it['status']}")
    return "\n".join(lines)


def render_payment(items):
    if not items:
        return "To'lov ma'lumotlari yo'q — hali kursga yozilmagansiz."
    lines = ["💳 <b>To'lov holatim</b>\n"]
    for it in items:
        lines.append(
            f"▫️ <b>{html.escape(it['course'])}</b>\n"
            f"   Tarif: {html.escape(it['plan'])} · Holat: {it['status']}\n"
            f"   Oxirgi to'lov: {it['last_payment']} · Keyingi muddat: {it['next_deadline']}"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------- handlers

def _require_user(lms_user):
    return lms_user is not None


def _courses_overview_markup(items):
    rows = [
        [
            InlineKeyboardButton(
                text=f"📖 {it['course']} — darslar",
                callback_data=f"ls:c:{it['course_id']}",
            )
        ]
        for it in items[:8]
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows) if rows else None


@router.message(Command("darslarim"))
async def cmd_courses(message: types.Message, lms_user):
    if not _require_user(lms_user):
        await message.answer("Avval ro'yxatdan o'ting: /start")
        return
    items = await sync_to_async(student_overview)(lms_user)
    await send_long(
        message,
        render_courses_overview(items),
        parse_mode=HTML_MODE,
        reply_markup=_courses_overview_markup(items),
    )


@router.message(Command("davomatim"))
async def cmd_attendance(message: types.Message, lms_user):
    if not _require_user(lms_user):
        await message.answer("Avval ro'yxatdan o'ting: /start")
        return
    items = await sync_to_async(student_recent_attendance)(lms_user)
    await send_long(message, render_attendance(items), parse_mode=HTML_MODE)


@router.message(Command("tolov", "tolovim"))
async def cmd_payment(message: types.Message, lms_user):
    if not _require_user(lms_user):
        await message.answer("Avval ro'yxatdan o'ting: /start")
        return
    items = await sync_to_async(student_payment_overview)(lms_user)
    await send_long(message, render_payment(items), parse_mode=HTML_MODE)


@router.callback_query(F.data == "ws:courses")
async def cb_courses(callback: types.CallbackQuery, lms_user):
    await callback.answer()
    if not _require_user(lms_user):
        return
    items = await sync_to_async(student_overview)(lms_user)
    await send_long(callback.message, render_courses_overview(items), parse_mode=HTML_MODE)


@router.callback_query(F.data == "ws:attendance")
async def cb_attendance(callback: types.CallbackQuery, lms_user):
    await callback.answer()
    if not _require_user(lms_user):
        return
    items = await sync_to_async(student_recent_attendance)(lms_user)
    await send_long(callback.message, render_attendance(items), parse_mode=HTML_MODE)


@router.callback_query(F.data == "ws:payment")
async def cb_payment(callback: types.CallbackQuery, lms_user):
    await callback.answer()
    if not _require_user(lms_user):
        return
    items = await sync_to_async(student_payment_overview)(lms_user)
    await send_long(callback.message, render_payment(items), parse_mode=HTML_MODE)


@router.callback_query(F.data == "ws:ai")
async def cb_ai(callback: types.CallbackQuery, lms_user):
    await callback.answer()
    if not _require_user(lms_user):
        return
    await callback.message.answer(
        "🤖 Shunchaki savolingizni yozib yuboring — AI repetitor javob beradi.\n"
        "Suhbat saytdagi Messenger'da \"Telegram AI suhbati\" bo'lib saqlanadi, "
        "xotira va limitlar sayt bilan bir xil."
    )


# ---------------------------------------------------------------- botda o'qish (F8)

async def send_course_map(message: types.Message, lms_user, course_id):
    data = await sync_to_async(student_course_map)(lms_user, course_id)
    if not data:
        await message.answer("Kurs topilmadi yoki faol emas.")
        return
    if not data["modules"]:
        await message.answer("Bu kursda hali darslar joylanmagan.")
        return

    for module_title, lessons in data["modules"].items():
        lines = [f"📦 <b>{html.escape(module_title)}</b> · {html.escape(data['course'])}\n"]
        rows = []
        for i, lesson in enumerate(lessons, 1):
            if lesson["locked"]:
                reason = f" — <i>{html.escape(lesson['lock_reason'])}</i>" if lesson["lock_reason"] else ""
                lines.append(f"🔒 {i}. {html.escape(lesson['title'])}{reason}")
                continue
            icon = "✅" if lesson["completed"] else "▶️"
            lines.append(f"{icon} {i}. {html.escape(lesson['title'])}")
            rows.append(
                [
                    InlineKeyboardButton(
                        text=f"{icon} {i}. {lesson['title'][:40]}",
                        callback_data=f"ls:l:{lesson['id']}",
                    )
                ]
            )
        await send_long(
            message,
            "\n".join(lines),
            parse_mode=HTML_MODE,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=rows[:30]) if rows else None,
        )


async def send_lesson_view(message: types.Message, lms_user, lesson_id):
    """Darsni botda ochish — deep-link va tugmalar shu funksiyani chaqiradi."""
    result = await sync_to_async(student_open_lesson)(lms_user, lesson_id)
    if not result.ok:
        await message.answer(result.message)
        return
    lesson = result.lesson

    header = (
        f"📖 <b>{html.escape(lesson['title'])}</b>\n"
        f"{html.escape(lesson['module'])} · {html.escape(lesson['course'])}\n"
    )
    extras = []
    if lesson["assignments"]:
        extras.append(f"📝 Vazifa: {lesson['assignments']} ta (topshirish tez orada botda)")
    if lesson["quizzes"]:
        extras.append(f"❓ Quiz: {lesson['quizzes']} ta (tez orada botda)")
    footer = "\n\n" + "\n".join(extras) if extras else ""
    footer += "\n\n✅ Dars o'tildi deb belgilandi."

    rows = []
    if lesson["video_url"]:
        rows.append([InlineKeyboardButton(text="🎥 Video darsni ko'rish", url=lesson["video_url"])])
    rows.append(
        [InlineKeyboardButton(text="⬅️ Darslar ro'yxati", callback_data=f"ls:c:{lesson['course_id']}")]
    )

    body = html.escape(lesson["content"]) if lesson["content"] else (
        "Bu darsda matnli kontent yo'q — videoni ko'ring."
    )
    await send_long(
        message,
        header + "\n" + body + footer,
        parse_mode=HTML_MODE,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
    )


@router.callback_query(F.data.startswith("ls:c:"))
async def cb_course_map(callback: types.CallbackQuery, lms_user):
    await callback.answer()
    if not _require_user(lms_user):
        return
    course_id = callback.data.split(":")[2]
    if course_id.isdigit():
        await send_course_map(callback.message, lms_user, int(course_id))


@router.callback_query(F.data.startswith("ls:l:"))
async def cb_open_lesson(callback: types.CallbackQuery, lms_user):
    await callback.answer()
    if not _require_user(lms_user):
        return
    lesson_id = callback.data.split(":")[2]
    if lesson_id.isdigit():
        await send_lesson_view(callback.message, lms_user, int(lesson_id))


# ---------------------------------------------------------------- kursga yozilish (F3.5)

async def _show_enrollable_courses(message: types.Message):
    courses = await sync_to_async(list_public_courses)()
    if not courses:
        await message.answer("Hozircha qabul ochiq kurslar yo'q — tez orada e'lon qilinadi.")
        return
    lines = ["🎓 <b>Qabul davom etayotgan kurslar</b>\n"]
    for c in courses:
        lines.append(f"▫️ <b>{html.escape(c['title'])}</b> — {c['level']} · ~{c['duration']} soat")
    lines.append("\nYozilish uchun kursni tanlang 👇")
    await message.answer(
        "\n".join(lines), parse_mode=HTML_MODE, reply_markup=enroll_courses_markup(courses)
    )


@router.message(Command("yozilish", "kurslar"))
async def cmd_enroll(message: types.Message, lms_user):
    if not _require_user(lms_user):
        await message.answer("Avval ro'yxatdan o'ting: /start")
        return
    await _show_enrollable_courses(message)


@router.callback_query(F.data == "ws:enroll")
async def cb_enroll(callback: types.CallbackQuery, lms_user):
    await callback.answer()
    if not _require_user(lms_user):
        return
    await _show_enrollable_courses(callback.message)


@router.callback_query(F.data.startswith("enr:c:"))
async def cb_enroll_course(callback: types.CallbackQuery, lms_user):
    await callback.answer()
    if not _require_user(lms_user):
        return
    course_id = callback.data.split(":")[2]
    if not course_id.isdigit():
        return
    plans = await sync_to_async(list_plans)()
    if not plans:
        await callback.message.answer("Tariflar hali sozlanmagan — administratorga murojaat qiling.")
        return
    await callback.message.answer(
        "💳 Tarifni tanlang:",
        reply_markup=enroll_plans_markup(int(course_id), plans),
    )


@router.callback_query(F.data.startswith("enr:p:"))
async def cb_enroll_plan(callback: types.CallbackQuery, lms_user):
    await callback.answer()
    if not _require_user(lms_user):
        return
    parts = callback.data.split(":")
    if len(parts) != 4 or not (parts[2].isdigit() and parts[3].isdigit()):
        return
    result = await sync_to_async(begin_course_enrollment)(lms_user, int(parts[2]), int(parts[3]))
    if not result.ok:
        await callback.message.answer(result.message)
        return
    price = f"{result.amount:,}".replace(",", " ")
    card_holder = f"\nKarta egasi: <b>{html.escape(result.card_holder)}</b>" if result.card_holder else ""
    await callback.message.answer(
        f"✅ Tanlandi: <b>{html.escape(result.course_title)}</b> · "
        f"{html.escape(result.plan_name)} tarifi\n\n"
        f"💳 <b>To'lov:</b> {price} so'm\n"
        f"Karta: <code>{html.escape(result.card_number)}</code>{card_holder}\n"
        f"Davr: {result.period_start} — {result.period_end}\n\n"
        f"To'lovni amalga oshirib, <b>chek rasmini (skrinshot) shu chatga yuboring</b> 📸\n"
        f"Administrator tasdiqlagach kursga kirish ochiladi.",
        parse_mode=HTML_MODE,
    )


@router.message(F.photo)
async def photo_handler(message: types.Message, lms_user):
    if not _require_user(lms_user):
        await message.answer("Chek qabul qilish uchun avval ro'yxatdan o'ting: /start")
        return

    photo = message.photo[-1]
    file = await message.bot.get_file(photo.file_id)
    buffer = await message.bot.download_file(file.file_path)

    from django.core.files.base import ContentFile

    content = ContentFile(
        buffer.read(), name=f"tg-receipt-{lms_user.id}-{int(time.time())}.jpg"
    )
    result = await sync_to_async(submit_payment_receipt)(lms_user, content)
    if not result.ok:
        await message.answer(result.message)
        return
    price = f"{result.amount:,}".replace(",", " ")
    await message.answer(
        f"✅ Chek qabul qilindi (№{result.receipt_id}) — "
        f"<b>{html.escape(result.course_title)}</b>, {price} so'm.\n\n"
        f"Administrator tasdiqlashi bilan kursga kirish ochiladi. Holat: /tolov",
        parse_mode=HTML_MODE,
    )
