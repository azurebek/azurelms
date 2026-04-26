from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


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
