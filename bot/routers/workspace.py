"""Bog'langan user workspace'i (F3) — shaxsiy chat menyusi.

Buyruqlar/tugmalar: darslarim (progress), davomatim, to'lov holati.
Erkin matn AI repetitorga boradi (onboarding catch-all → telegram_ai_reply).
"""

import html

from aiogram import F, Router, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from asgiref.sync import sync_to_async

from bot.services import (
    student_overview,
    student_payment_overview,
    student_recent_attendance,
)

router = Router(name="workspace")
router.message.filter(F.chat.type == "private")

HTML_MODE = "HTML"
TG_MESSAGE_LIMIT = 4000  # 4096 rasmiy limitdan zaxira bilan


def student_menu_markup():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📚 Darslarim", callback_data="ws:courses"),
                InlineKeyboardButton(text="✅ Davomatim", callback_data="ws:attendance"),
            ],
            [
                InlineKeyboardButton(text="💳 To'lovim", callback_data="ws:payment"),
                InlineKeyboardButton(text="🤖 AI repetitor", callback_data="ws:ai"),
            ],
        ]
    )


async def send_long(message: types.Message, text: str, **kwargs):
    """4096 belgi limitidan oshgan javobni bo'lib yuboradi."""
    while text:
        chunk = text[:TG_MESSAGE_LIMIT]
        if len(text) > TG_MESSAGE_LIMIT:
            cut = chunk.rfind("\n")
            if cut > TG_MESSAGE_LIMIT // 2:
                chunk = chunk[:cut]
        await message.answer(chunk, **kwargs)
        text = text[len(chunk):].lstrip("\n")


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


@router.message(Command("darslarim"))
async def cmd_courses(message: types.Message, lms_user):
    if not _require_user(lms_user):
        await message.answer("Avval ro'yxatdan o'ting: /start")
        return
    items = await sync_to_async(student_overview)(lms_user)
    await send_long(message, render_courses_overview(items), parse_mode=HTML_MODE)


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
