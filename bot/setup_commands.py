"""Telegram buyruqlar menyusini ro'yxatdan o'tkazish.

Bu ro'yxat Telegram serverida saqlanadi — "/" bosilganda va Menu tugmasida
chiqadi. Scope bo'yicha: shaxsiy chat (default) va guruhlar alohida.
run_bot startup'ida chaqiriladi (idempotent).
"""

from aiogram.types import (
    BotCommand,
    BotCommandScopeAllGroupChats,
    BotCommandScopeAllPrivateChats,
)

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

GROUP_COMMANDS = [
    BotCommand(command="dars", description="Davomat: /dars 1 · /dars tugadi"),
    BotCommand(command="davomat", description="Joriy davomat holati"),
    BotCommand(command="link_cohort", description="Guruhni kohortga ulash (ID)"),
]


async def setup_bot_commands(bot):
    await bot.set_my_commands(PRIVATE_COMMANDS, scope=BotCommandScopeAllPrivateChats())
    await bot.set_my_commands(GROUP_COMMANDS, scope=BotCommandScopeAllGroupChats())
