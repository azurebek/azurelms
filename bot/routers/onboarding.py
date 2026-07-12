"""Shaxsiy chat — onboarding va (hozircha minimal) workspace kirish nuqtasi.

F2'da to'liq landing voronkasi (tanituv, kurslar, narxlar, AI demo, ro'yxat)
shu routerga qo'shiladi. Hozir: token bilan bog'lash + rolga mos salomlashish.
"""

import html

from aiogram import F, Router, types
from aiogram.filters import Command, CommandObject, CommandStart
from asgiref.sync import sync_to_async

from bot.services import link_user_from_start_token, student_display_name

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


def render_welcome(lms_user, lms_role):
    if lms_user is None:
        return (
            "👋 <b>AzureLMS botiga xush kelibsiz!</b>\n\n"
            "Bu bot orqali turk tili kurslarida o'qish, davomat va "
            "AI repetitor bilan ishlash mumkin.\n\n"
            "Hisobingiz bormi? Saytdagi profilingiz orqali Telegram'ni ulang — "
            "shunda bot to'liq ish stolingizga aylanadi.\n"
            "Hisobingiz yo'qmi? Tez orada shu yerning o'zida ro'yxatdan o'tish "
            "imkoni qo'shiladi."
        )
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
            "• <code>/link_cohort ID</code> — guruhni kohortga ulash"
        )
    else:
        lines.append(
            "Dars guruhidagi davomat postida \"Darsga kirdim\" tugmasini bosing — "
            "davomatingiz avtomatik belgilanadi.\n\n"
            "Tez orada: darslaringiz, to'lov holati va AI repetitor shu yerda."
        )
    return "\n".join(lines)


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
        # Bog'lashdan keyin identity qayta aniqlanadi
        from bot.middleware import resolve_identity

        lms_user, lms_role = await sync_to_async(resolve_identity)(message.from_user.id)
        await message.answer(
            f"✅ {result.message}\n\n" + render_welcome(lms_user, lms_role),
            parse_mode=HTML_MODE,
        )
        return

    await message.answer(render_welcome(lms_user, lms_role), parse_mode=HTML_MODE)


@router.message(Command("yordam", "help"))
async def help_handler(message: types.Message, lms_user, lms_role):
    await message.answer(render_welcome(lms_user, lms_role), parse_mode=HTML_MODE)
