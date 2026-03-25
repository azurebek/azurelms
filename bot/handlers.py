from aiogram import F, Router, types
from aiogram.filters import Command, CommandObject, CommandStart
from asgiref.sync import sync_to_async

from bot.keyboards import attendance_checkin_markup
from bot.services import (
    bind_chat_to_cohort,
    close_lesson_session,
    get_user_role,
    link_user_from_start_token,
    register_checkin,
    set_session_message_id,
    start_lesson_session,
)

router = Router()
GROUP_CHAT_TYPES = {"group", "supergroup"}
HTML_MODE = "HTML"
CHECKIN_CALLBACK_PREFIX = "attendance:"


def render_attendance_post(session, checkin_count, *, closed=False, summary=None):
    lines = [
        "Davomat sessiyasi yopildi." if closed else "Davomat olish boshlandi.",
        f"Cohort: <b>{session.cohort.name}</b>",
        f"Dars: <b>{session.lesson.title}</b>",
        f"Sana: <b>{session.attendance_date.isoformat()}</b>",
        f"Check-in: <b>{checkin_count}</b>",
    ]
    if closed and summary:
        lines.extend(
            [
                "",
                f"Keldi: <b>{summary.get('present', 0)}</b>",
                f"Qisman: <b>{summary.get('partial', 0)}</b>",
                f"Kelmadi: <b>{summary.get('absent', 0)}</b>",
            ]
        )
    else:
        lines.extend(["", "Quyidagi tugma orqali davomatga belgilanish mumkin."])
    return "\n".join(lines)


def is_group_chat(message):
    return message.chat.type in GROUP_CHAT_TYPES

@router.message(CommandStart())
async def cmd_start_handler(message: types.Message, command: CommandObject):
    token = command.args

    if not token:
        role = await sync_to_async(get_user_role)(message.from_user.id)
        await message.answer(
            f"Xush kelibsiz! Botdan to'liq foydalanish uchun LMS saytidagi profilingizga ulang.\n"
            f"Sizning joriy maqomingiz: <b>{role}</b>",
            parse_mode=HTML_MODE,
        )
        return

    result = await sync_to_async(link_user_from_start_token)(
        token,
        message.from_user.id,
        message.from_user.username or "",
    )
    role = await sync_to_async(get_user_role)(message.from_user.id)

    if result.ok:
        await message.answer(
            f"{result.message}\nSizning joriy maqomingiz: <b>{role}</b>",
            parse_mode=HTML_MODE,
        )
        return

    await message.answer(result.message)


@router.message(Command("link_cohort"))
async def link_cohort_handler(message: types.Message, command: CommandObject):
    if not is_group_chat(message):
        await message.answer("Bu command faqat Telegram guruh ichida ishlaydi.")
        return

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
    if not is_group_chat(message):
        await message.answer("Bu command faqat Telegram guruh ichida ishlaydi.")
        return

    result = await sync_to_async(start_lesson_session)(
        chat_id=message.chat.id,
        chat_title=message.chat.title or "",
        actor_telegram_id=message.from_user.id,
        lesson_ref=(command.args or "").strip(),
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


@router.message(Command("close_lesson"))
async def close_lesson_handler(message: types.Message):
    if not is_group_chat(message):
        await message.answer("Bu command faqat Telegram guruh ichida ishlaydi.")
        return

    result = await sync_to_async(close_lesson_session)(
        chat_id=message.chat.id,
        actor_telegram_id=message.from_user.id,
    )
    if not result.ok:
        await message.answer(result.message)
        return

    checkin_count = await sync_to_async(lambda: result.session.checkins.count())()
    if result.session and result.session.attendance_message_id:
        try:
            await message.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=result.session.attendance_message_id,
                text=render_attendance_post(
                    result.session,
                    checkin_count,
                    closed=True,
                    summary=result.summary,
                ),
                parse_mode=HTML_MODE,
                reply_markup=None,
            )
        except Exception:
            pass

    await message.answer(
        (
            "Davomat yakunlandi.\n"
            f"Keldi: {result.summary.get('present', 0)}\n"
            f"Qisman: {result.summary.get('partial', 0)}\n"
            f"Kelmadi: {result.summary.get('absent', 0)}"
        )
    )


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
