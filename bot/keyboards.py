from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_admin_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📊 Statistika"), KeyboardButton(text="📩 Xabarlar")],
            [KeyboardButton(text="⚙️ Sozlamalar")]
        ],
        resize_keyboard=True
    )

def get_student_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📚 Mening kurslarim"), KeyboardButton(text="🏆 Reyting")],
            [KeyboardButton(text="👨‍💻 Qo'llab-quvvatlash")]
        ],
        resize_keyboard=True
    )

def get_guest_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📋 Kurslar ro'yxati"), KeyboardButton(text="ℹ️ Biz haqimizda")],
            [KeyboardButton(text="🔗 Saytdan ulashish")]
        ],
        resize_keyboard=True
    )
