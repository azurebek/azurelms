"""Bog'langan user workspace'i (F3) — shaxsiy chat menyusi.

Buyruqlar/tugmalar: darslarim (progress), davomatim, to'lov holati.
Erkin matn AI repetitorga boradi (onboarding catch-all → telegram_ai_reply).
"""

import html
import time
from urllib.parse import quote

from aiogram import F, Router, types
from aiogram.filters import BaseFilter, Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from asgiref.sync import sync_to_async
from django.conf import settings

from bot.keyboards import is_public_domain, miniapp_button
from bot.services import (
    answer_quiz_question,
    begin_course_enrollment,
    clear_pending_action,
    get_pending_action,
    lesson_assignments,
    lesson_quizzes,
    list_plans,
    list_public_courses,
    start_assignment_answer,
    start_quiz,
    student_course_map,
    student_open_lesson,
    student_overview,
    student_payment_overview,
    student_recent_attendance,
    submit_assignment_answer,
    submit_payment_receipt,
)

router = Router(name="workspace")
router.message.filter(F.chat.type == "private")

HTML_MODE = "HTML"
TG_MESSAGE_LIMIT = 4000  # 4096 rasmiy limitdan zaxira bilan


class AwaitingAssignment(BaseFilter):
    """Vazifa javobi kutilayaptimi? False bo'lsa aiogram keyingi handler'ga o'tadi
    (matn → AI repetitor, rasm → to'lov cheki)."""

    async def __call__(self, event: types.Message, lms_user=None, **kwargs):
        if lms_user is None:
            return False
        from bot.models import BotPendingAction

        pending = await sync_to_async(get_pending_action)(lms_user)
        if pending is None or pending.kind != BotPendingAction.KIND_ASSIGNMENT:
            return False
        return {"pending_assignment_id": pending.target_id}


# `_is_public_domain` va `miniapp_button` `bot/keyboards.py` ga ko'chirildi:
# outbox worker ham o'sha tugmani yasashi kerak va router modulini import
# qilishi noto'g'ri bo'lardi. Nomlar shu yerda qoladi — bu modulning qolgan
# qismi va testlar ularni shu yerdan chaqiradi.
_is_public_domain = is_public_domain


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
    webapp_btn = miniapp_button("🌐 Saytni ochish (Mini App)", "/bot/miniapp/home/")
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
    footer = "\n\n✅ Dars o'tildi deb belgilandi."

    rows = []
    if lesson["video_url"]:
        rows.append([InlineKeyboardButton(text="🎥 Video darsni ko'rish", url=lesson["video_url"])])
    if lesson["assignments"]:
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"📝 Vazifa ({lesson['assignments']})",
                    callback_data=f"ls:a:{lesson['id']}",
                )
            ]
        )
    if lesson["quizzes"]:
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"❓ Quiz ({lesson['quizzes']})",
                    callback_data=f"ls:q:{lesson['id']}",
                )
            ]
        )
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


# ---------------------------------------------------------------- vazifa (F9)

@router.callback_query(F.data.startswith("ls:a:"))
async def cb_lesson_assignments(callback: types.CallbackQuery, lms_user):
    await callback.answer()
    if not _require_user(lms_user):
        return
    lesson_id = callback.data.split(":")[2]
    if not lesson_id.isdigit():
        return
    data = await sync_to_async(lesson_assignments)(lms_user, int(lesson_id))
    if not data or not data["assignments"]:
        await callback.message.answer("Bu darsda vazifa yo'q.")
        return

    lines = [f"📝 <b>Vazifalar</b> · {html.escape(data['lesson'])}\n"]
    rows = []
    for item in data["assignments"]:
        state = f" — {item['status']}" if item["status"] else ""
        lines.append(f"• <b>{html.escape(item['title'])}</b> ({item['max_xp']} XP){state}")
        if item["feedback"]:
            lines.append(f"  💬 <i>{html.escape(item['feedback'])}</i>")
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"✍️ {item['title'][:40]}",
                    callback_data=f"as:s:{item['id']}",
                )
            ]
        )
    await send_long(
        callback.message,
        "\n".join(lines),
        parse_mode=HTML_MODE,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
    )


@router.callback_query(F.data.startswith("as:s:"))
async def cb_assignment_start(callback: types.CallbackQuery, lms_user):
    await callback.answer()
    if not _require_user(lms_user):
        return
    assignment_id = callback.data.split(":")[2]
    if not assignment_id.isdigit():
        return
    result = await sync_to_async(start_assignment_answer)(lms_user, int(assignment_id))
    if not result.ok:
        await callback.message.answer(result.message)
        return
    a = result.assignment
    body = html.escape(a["description"]) if a["description"] else "Shart berilmagan."
    await send_long(
        callback.message,
        f"✍️ <b>{html.escape(a['title'])}</b> ({a['max_xp']} XP)\n\n{body}\n\n"
        f"<b>Javobingizni yuboring:</b> matn yozing yoki rasm/fayl tashlang.\n"
        f"Bekor qilish: /bekor",
        parse_mode=HTML_MODE,
    )


@router.message(Command("bekor"))
async def cmd_cancel(message: types.Message, lms_user):
    if not _require_user(lms_user):
        return
    await sync_to_async(clear_pending_action)(lms_user)
    await message.answer("Bekor qilindi.")


# ---------------------------------------------------------------- quiz (F9)

def _quiz_markup(quiz_id, question):
    rows = [
        [
            InlineKeyboardButton(
                text=choice["text"][:60],
                callback_data=f"qz:a:{quiz_id}:{question['id']}:{choice['id']}",
            )
        ]
        for choice in question["choices"]
    ]
    rows.append([InlineKeyboardButton(text="❌ To'xtatish", callback_data="qz:x")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def _send_quiz_question(message, quiz_id, result):
    q = result.question
    await message.answer(
        f"❓ <b>{html.escape(result.quiz_title)}</b> · savol {q['index'] + 1}/{q['total']}\n\n"
        f"{html.escape(q['text'])}",
        parse_mode=HTML_MODE,
        reply_markup=_quiz_markup(quiz_id, q),
    )


@router.callback_query(F.data.startswith("ls:q:"))
async def cb_lesson_quizzes(callback: types.CallbackQuery, lms_user):
    await callback.answer()
    if not _require_user(lms_user):
        return
    lesson_id = callback.data.split(":")[2]
    if not lesson_id.isdigit():
        return
    quizzes = await sync_to_async(lesson_quizzes)(lms_user, int(lesson_id))
    if not quizzes:
        await callback.message.answer("Bu darsda quiz yo'q.")
        return
    rows = [
        [
            InlineKeyboardButton(
                text=f"▶️ {q['title'][:35]} ({q['questions']} savol · {q['xp']} XP)",
                callback_data=f"qz:s:{q['id']}",
            )
        ]
        for q in quizzes
    ]
    await callback.message.answer(
        "❓ <b>Quizlar</b> — boshlash uchun tanlang:",
        parse_mode=HTML_MODE,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
    )


@router.callback_query(F.data.startswith("qz:s:"))
async def cb_quiz_start(callback: types.CallbackQuery, lms_user):
    await callback.answer()
    if not _require_user(lms_user):
        return
    quiz_id = callback.data.split(":")[2]
    if not quiz_id.isdigit():
        return
    result = await sync_to_async(start_quiz)(lms_user, int(quiz_id))
    if not result.ok:
        await callback.message.answer(result.message)
        return
    await _send_quiz_question(callback.message, int(quiz_id), result)


@router.callback_query(F.data == "qz:x")
async def cb_quiz_cancel(callback: types.CallbackQuery, lms_user):
    await callback.answer("To'xtatildi.")
    if _require_user(lms_user):
        await sync_to_async(clear_pending_action)(lms_user)
    if callback.message:
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass


@router.callback_query(F.data.startswith("qz:a:"))
async def cb_quiz_answer(callback: types.CallbackQuery, lms_user):
    await callback.answer()
    if not _require_user(lms_user):
        return
    parts = callback.data.split(":")  # qz:a:<quiz>:<question>:<choice>
    if len(parts) != 5 or not all(p.isdigit() for p in parts[2:]):
        return
    quiz_id, question_id, choice_id = int(parts[2]), int(parts[3]), int(parts[4])

    # Tanlangan javobni belgilab, tugmalarni o'chiramiz (qayta bosilmasin)
    if callback.message:
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass

    result = await sync_to_async(answer_quiz_question)(lms_user, quiz_id, question_id, choice_id)
    if not result.ok:
        await callback.message.answer(result.message)
        return
    if not result.finished:
        await _send_quiz_question(callback.message, quiz_id, result)
        return

    emoji = "🎉" if result.score >= 80 else ("👍" if result.score >= 50 else "💪")
    xp_line = f"\n+{result.xp_earned} XP" if result.xp_earned else "\n(XP avval berilgan)"
    await callback.message.answer(
        f"{emoji} <b>{html.escape(result.quiz_title)}</b> yakunlandi!\n\n"
        f"Natija: <b>{result.total_correct}/{result.total_questions}</b> · {result.score}%{xp_line}",
        parse_mode=HTML_MODE,
    )


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


async def _download_to_content_file(message, file_id, name):
    from django.core.files.base import ContentFile

    file = await message.bot.get_file(file_id)
    buffer = await message.bot.download_file(file.file_path)
    return ContentFile(buffer.read(), name=name)


# --- Vazifa javobi (matn/rasm/fayl) — pending bo'lganda BIRINCHI bo'lib ushlaydi ---

@router.message(AwaitingAssignment(), F.text & ~F.text.startswith("/"))
async def assignment_text_answer(message: types.Message, lms_user, pending_assignment_id):
    result = await sync_to_async(submit_assignment_answer)(
        lms_user, pending_assignment_id, text=message.text
    )
    await message.answer(result.message, parse_mode=HTML_MODE if result.ok else None)


@router.message(AwaitingAssignment(), F.photo | F.document)
async def assignment_file_answer(message: types.Message, lms_user, pending_assignment_id):
    if message.photo:
        file_id = message.photo[-1].file_id
        name = f"tg-assignment-{lms_user.id}-{int(time.time())}.jpg"
    else:
        file_id = message.document.file_id
        name = message.document.file_name or f"tg-assignment-{lms_user.id}-{int(time.time())}"

    content = await _download_to_content_file(message, file_id, name)
    result = await sync_to_async(submit_assignment_answer)(
        lms_user, pending_assignment_id, text=message.caption or "", attachment=content
    )
    await message.answer(result.message, parse_mode=HTML_MODE if result.ok else None)


@router.message(F.photo)
async def photo_handler(message: types.Message, lms_user):
    if not _require_user(lms_user):
        await message.answer("Chek qabul qilish uchun avval ro'yxatdan o'ting: /start")
        return

    content = await _download_to_content_file(
        message,
        message.photo[-1].file_id,
        f"tg-receipt-{lms_user.id}-{int(time.time())}.jpg",
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
