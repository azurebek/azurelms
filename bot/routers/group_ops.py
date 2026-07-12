"""Guruh operatsiyalari — davomat oqimi (F1).

O'qituvchi oqimi:
    /dars 1        → davomat sessiyasi ochiladi, "Darsga kirdim" tugmali post
    /dars tugadi   → sessiya yopiladi: ismli keldi/kech/kelmadi e'loni,
                     kelmaganlarga DM ogohlantirish (bog'langanlarga)
    /davomat       → joriy ochiq sessiya holati

Eski buyruqlar (/start_lesson, /close_lesson) alias sifatida qoladi.
Biznes-mantiq bot/services.py da — bu fayl faqat Telegram UI adapteri.
"""

import html

from aiogram import F, Router, types
from aiogram.filters import Command, CommandObject
from asgiref.sync import sync_to_async

from bot.keyboards import attendance_checkin_markup
from bot.services import (
    bind_chat_to_cohort,
    close_lesson_session,
    get_open_session_status,
    register_checkin,
    set_session_message_id,
    start_lesson_session,
)

router = Router(name="group_ops")
GROUP_CHAT_TYPES = {"group", "supergroup"}
router.message.filter(F.chat.type.in_(GROUP_CHAT_TYPES))

HTML_MODE = "HTML"
CHECKIN_CALLBACK_PREFIX = "attendance:"
MAX_NAMES_PER_LIST = 60  # 4096 belgi limitidan himoya


# ---------------------------------------------------------------- helpers

def parse_dars_args(args):
    """'/dars <arg>' argumentini tasniflaydi.

    Qaytaradi: ("start", lesson_ref) | ("close", None) | ("usage", None)
    """
    text = (args or "").strip().lower()
    if not text:
        return ("usage", None)
    if text in {"tugadi", "tamom", "yakun", "stop"}:
        return ("close", None)
    return ("start", text)


def _mention(item):
    """Kelmagan o'quvchini iloji boricha 'chertib' eslatadigan ko'rinish."""
    name = html.escape(item["name"])
    if item.get("telegram_username"):
        return f"@{item['telegram_username']}"
    if item.get("telegram_id"):
        return f'<a href="tg://user?id={item["telegram_id"]}">{name}</a>'
    return name


def _name_list(items, mention=False):
    shown = items[:MAX_NAMES_PER_LIST]
    parts = [_mention(i) if mention else html.escape(i["name"]) for i in shown]
    text = ", ".join(parts)
    rest = len(items) - len(shown)
    if rest > 0:
        text += f" … va yana {rest} kishi"
    return text


def render_attendance_post(session, checkin_count, *, closed=False, summary=None):
    lines = [
        "Davomat sessiyasi yopildi." if closed else "📋 Davomat olish boshlandi.",
        f"Guruh: <b>{html.escape(session.cohort.name)}</b>",
        f"Dars: <b>{html.escape(session.lesson.title)}</b>",
        f"Sana: <b>{session.attendance_date.strftime('%d.%m.%Y')}</b>",
        f"Belgilandi: <b>{checkin_count}</b>",
    ]
    if closed and summary:
        lines.extend(
            [
                "",
                f"✅ Keldi: <b>{summary.get('present', 0)}</b>",
                f"🕒 Kech: <b>{summary.get('partial', 0)}</b>",
                f"❌ Kelmadi: <b>{summary.get('absent', 0)}</b>",
            ]
        )
    else:
        lines.extend(["", "Quyidagi tugmani bosib davomatga belgilaning 👇"])
    return "\n".join(lines)


def render_close_announcement(session, summary, details):
    """Yakuniy ismli e'lon (guruhga)."""
    lines = [
        "📋 <b>Davomat yakunlandi</b>",
        f"Dars: <b>{html.escape(session.lesson.title)}</b> · {session.attendance_date.strftime('%d.%m.%Y')}",
        "",
    ]
    present = details.get("present", [])
    partial = details.get("partial", [])
    absent = details.get("absent", [])
    if present:
        lines.append(f"✅ <b>Keldi ({len(present)}):</b> {_name_list(present)}")
    if partial:
        lines.append(f"🕒 <b>Kech qoldi ({len(partial)}):</b> {_name_list(partial)}")
    if absent:
        lines.append(f"❌ <b>Kelmadi ({len(absent)}):</b> {_name_list(absent, mention=True)}")
        lines.append("")
        lines.append("Kelmaganlarga eslatma yuborildi. Darsni qoldirmang! 💪")
    else:
        lines.append("")
        lines.append("Hamma darsda — ajoyib! 🎉")
    return "\n".join(lines)


def render_absent_dm(session):
    """Kelmagan o'quvchiga shaxsiy ogohlantirish matni."""
    from django.conf import settings

    lesson_url = (
        f"https://{settings.APP_DOMAIN}/courses/{session.cohort.course_id}"
        f"/lesson/{session.lesson_id}/"
    )
    return (
        f"⚠️ <b>Darsni qoldirdingiz</b>\n\n"
        f"{session.attendance_date.strftime('%d.%m.%Y')} kuni "
        f"\"{html.escape(session.lesson.title)}\" darsida davomatga belgilanmadingiz.\n\n"
        f"Mavzudan orqada qolmaslik uchun dars materialini ko'rib chiqing:\n{lesson_url}"
    )


# ---------------------------------------------------------------- handlers

@router.message(Command("dars"))
async def dars_handler(message: types.Message, command: CommandObject):
    action, lesson_ref = parse_dars_args(command.args)
    if action == "usage":
        status = await sync_to_async(get_open_session_status)(message.chat.id)
        if status.ok:
            await _answer_session_status(message, status)
        else:
            await message.answer(
                "Foydalanish:\n"
                "• <code>/dars 1</code> — 1-dars uchun davomat boshlash\n"
                "• <code>/dars tugadi</code> — davomatni yakunlash\n"
                "• <code>/davomat</code> — joriy holat",
                parse_mode=HTML_MODE,
            )
        return
    if action == "close":
        await _close_lesson(message)
        return
    await _start_lesson(message, lesson_ref)


@router.message(Command("davomat"))
async def davomat_handler(message: types.Message):
    status = await sync_to_async(get_open_session_status)(message.chat.id)
    if not status.ok:
        await message.answer(status.message)
        return
    await _answer_session_status(message, status)


async def _answer_session_status(message, status):
    names = status.checkin_names or []
    text = (
        f"📋 Ochiq davomat: <b>{html.escape(status.session.lesson.title)}</b>\n"
        f"Belgilandi: <b>{status.checkin_count}</b>"
    )
    if names:
        text += "\n" + html.escape(", ".join(names[:MAX_NAMES_PER_LIST]))
    text += "\n\nYakunlash: /dars tugadi"
    await message.answer(text, parse_mode=HTML_MODE)


# Eski nomlar — alias
@router.message(Command("link_cohort"))
async def link_cohort_handler(message: types.Message, command: CommandObject):
    cohort_arg = (command.args or "").strip()
    if not cohort_arg.isdigit():
        await message.answer("Foydalanish: /link_cohort 17")
        return

    result = await sync_to_async(bind_chat_to_cohort)(
        cohort_id=int(cohort_arg),
        chat_id=message.chat.id,
        chat_title=message.chat.title or "",
        actor_telegram_id=message.from_user.id,
    )
    await message.answer(result.message)


@router.message(Command("start_lesson"))
async def start_lesson_handler(message: types.Message, command: CommandObject):
    await _start_lesson(message, (command.args or "").strip())


@router.message(Command("close_lesson"))
async def close_lesson_handler(message: types.Message):
    await _close_lesson(message)


async def _start_lesson(message, lesson_ref):
    result = await sync_to_async(start_lesson_session)(
        chat_id=message.chat.id,
        chat_title=message.chat.title or "",
        actor_telegram_id=message.from_user.id,
        lesson_ref=lesson_ref or "",
    )
    if not result.ok:
        await message.answer(result.message)
        return

    sent_message = await message.answer(
        render_attendance_post(result.session, result.checkin_count),
        parse_mode=HTML_MODE,
        reply_markup=attendance_checkin_markup(result.session.id),
    )
    await sync_to_async(set_session_message_id)(result.session.id, sent_message.message_id)


async def _close_lesson(message):
    result = await sync_to_async(close_lesson_session)(
        chat_id=message.chat.id,
        actor_telegram_id=message.from_user.id,
    )
    if not result.ok:
        await message.answer(result.message)
        return

    # Eski davomat postidagi tugmani o'chirish
    checkin_count = await sync_to_async(lambda: result.session.checkins.count())()
    if result.session and result.session.attendance_message_id:
        try:
            await message.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=result.session.attendance_message_id,
                text=render_attendance_post(
                    result.session, checkin_count, closed=True, summary=result.summary
                ),
                parse_mode=HTML_MODE,
                reply_markup=None,
            )
        except Exception:
            pass

    # Ismli yakuniy e'lon
    await message.answer(
        render_close_announcement(result.session, result.summary, result.details or {}),
        parse_mode=HTML_MODE,
    )

    # Kelmaganlarga DM ogohlantirish (faqat botga /start bosgan bog'langan userlarga yetadi)
    absent = (result.details or {}).get("absent", [])
    dm_text = render_absent_dm(result.session)
    for item in absent:
        if not item.get("telegram_id"):
            continue
        try:
            await message.bot.send_message(item["telegram_id"], dm_text, parse_mode=HTML_MODE)
        except Exception:
            # User botni ochmagan/bloklagan bo'lishi mumkin — jim o'tkazamiz,
            # platforma-bildirishnoma baribir yozilgan (services._notify_absent_students).
            pass


@router.callback_query(F.data.startswith(CHECKIN_CALLBACK_PREFIX))
async def attendance_checkin_handler(callback: types.CallbackQuery):
    raw_session_id = callback.data.split(":", 1)[1]
    if not raw_session_id.isdigit():
        await callback.answer("Sessiya identifikatori noto'g'ri.", show_alert=True)
        return

    result = await sync_to_async(register_checkin)(
        session_id=int(raw_session_id),
        telegram_user_id=callback.from_user.id,
        telegram_username=callback.from_user.username or "",
    )
    show_alert = not result.ok or result.code in {"user_unlinked", "not_enrolled", "session_closed"}
    await callback.answer(result.message, show_alert=show_alert)

    if result.session and result.session.attendance_message_id and callback.message:
        try:
            await callback.message.edit_text(
                render_attendance_post(result.session, result.checkin_count),
                parse_mode=HTML_MODE,
                reply_markup=attendance_checkin_markup(result.session.id),
            )
        except Exception:
            pass
