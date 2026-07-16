"""Telegram buyruqlar menyusini ro'yxatdan o'tkazish.

Bu ro'yxat Telegram serverida saqlanadi — "/" bosilganda va Menu tugmasida
chiqadi. Scope bo'yicha: shaxsiy chat (default) va guruhlar alohida.
run_bot startup'ida chaqiriladi (idempotent).
"""

from aiogram.types import (
    BotCommand,
    BotCommandScopeAllGroupChats,
    BotCommandScopeAllPrivateChats,
    BotCommandScopeChat,
)
from asgiref.sync import sync_to_async

PRIVATE_COMMANDS = [
    BotCommand(command="start", description="Boshlash / asosiy menyu"),
    BotCommand(command="darslarim", description="Kurslarim va progress"),
    BotCommand(command="davomatim", description="So'nggi davomatlarim"),
    BotCommand(command="tolov", description="To'lov holati"),
    BotCommand(command="yozilish", description="Kursga yozilish"),
    BotCommand(command="guruhlarim", description="Guruhlarim (o'qituvchi)"),
    BotCommand(command="baholash", description="Baholash navbati (o'qituvchi)"),
    BotCommand(command="yordam", description="Yordam"),
]

ADMIN_COMMANDS = PRIVATE_COMMANDS + [
    BotCommand(command="stat", description="Platforma holati"),
    BotCommand(command="cheklar", description="To'lov cheklari (tasdiqlash)"),
    BotCommand(command="qidiruv", description="Foydalanuvchi qidirish"),
    BotCommand(command="broadcast", description="E'lon yuborish (hammaga/kohortga)"),
    BotCommand(command="ai_stat", description="AI token sarfi"),
]

GROUP_COMMANDS = [
    BotCommand(command="dars", description="Davomat: /dars 1 · /dars tugadi"),
    BotCommand(command="davomat", description="Joriy davomat holati"),
    BotCommand(command="link_cohort", description="Guruhni kohortga ulash (ID)"),
]


def _admin_telegram_ids():
    from users.models import CustomUser

    return list(
        CustomUser.objects.filter(
            is_active=True, telegram_id__isnull=False
        )
        .filter(is_staff=True)
        .values_list("telegram_id", flat=True)
    )


async def setup_bot_commands(bot):
    await bot.set_my_commands(PRIVATE_COMMANDS, scope=BotCommandScopeAllPrivateChats())
    await bot.set_my_commands(GROUP_COMMANDS, scope=BotCommandScopeAllGroupChats())
    # Admin buyruqlari faqat admin shaxsiy chatlarida ko'rinadi
    for chat_id in await sync_to_async(_admin_telegram_ids)():
        try:
            await bot.set_my_commands(ADMIN_COMMANDS, scope=BotCommandScopeChat(chat_id=chat_id))
        except Exception:
            pass  # admin botni hali ochmagan bo'lishi mumkin
