from aiogram import Router, types
from aiogram.filters import CommandStart, CommandObject
from django.core.signing import Signer, BadSignature
from asgiref.sync import sync_to_async
from users.models import CustomUser
import base64
from bot.keyboards import get_admin_keyboard, get_student_keyboard, get_guest_keyboard

router = Router()

@sync_to_async
def get_user_keyboard(telegram_id):
    try:
        user = CustomUser.objects.get(telegram_id=telegram_id)
        if user.is_staff or user.is_superuser:
            return get_admin_keyboard(), "Admin"
        
        from cohorts.models import Enrollment
        is_student = Enrollment.objects.filter(student=user, status='active').exists()
        if is_student:
            return get_student_keyboard(), "Talaba"
            
        return get_guest_keyboard(), "Mehmon"
    except CustomUser.DoesNotExist:
        return get_guest_keyboard(), "Mehmon"

@router.message(CommandStart())
async def cmd_start_handler(message: types.Message, command: CommandObject):
    print(f"[DEBUG] Received start command msg: {message.text}")
    print(f"[DEBUG] Command args: {command.args}")
    token = command.args # The part after ?start=
    
    if not token:
        keyboard, role = await get_user_keyboard(message.from_user.id)
        await message.answer(
            f"Xush kelibsiz! Botdan to'liq foydalanish uchun LMS saytidagi profilingizga ulang.\n"
            f"Sizning joriy maqomingiz: <b>{role}</b>",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        return
        
    try:
        # Re-add padding if needed, then decode
        padded_token = token + "=" * ((4 - len(token) % 4) % 4)
        raw_token = base64.urlsafe_b64decode(padded_token.encode()).decode()
        
        signer = Signer()
        user_id = signer.unsign(raw_token)
        
        # We need sync_to_async for Django ORM operations
        @sync_to_async
        def get_user_and_check(uid, telegram_id):
            try:
                user = CustomUser.objects.get(id=uid)
                if user.telegram_id:
                    return user, "already_linked"
                    
                exists = CustomUser.objects.filter(telegram_id=telegram_id).exists()
                if exists:
                    return user, "telegram_used"
                    
                user.telegram_id = telegram_id
                # user.telegram_username = message.from_user.username
                user.save()
                return user, "success"
                
            except CustomUser.DoesNotExist:
                return None, "not_found"
                
        user, status = await get_user_and_check(user_id, message.from_user.id)
        keyboard, role = await get_user_keyboard(message.from_user.id)
        
        if status == "already_linked":
            await message.answer("Sizning profilingizga allaqachon Telegram hisob ulangan. O'zgartirish uchun adminga murojaat qiling.", reply_markup=keyboard)
        elif status == "telegram_used":
            await message.answer("Bu Telegram akkaunt boshqa o'quvchi profiliga ulangan!", reply_markup=keyboard)
        elif status == "success":
            await message.answer(
                f"Tabriklaymiz! Hisobingiz muvaffaqiyatli ulandi, {user.first_name or user.username}!\n"
                f"Sizning joriy maqomingiz: <b>{role}</b>",
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        elif status == "not_found":
            await message.answer("Foydalanuvchi topilmadi!", reply_markup=keyboard)


    except BadSignature:
        keyboard, role = await get_user_keyboard(message.from_user.id)
        await message.answer("Xatolik: havola yaroqsiz yoki buzilgan!", reply_markup=keyboard)
    except Exception as e:
        keyboard, role = await get_user_keyboard(message.from_user.id)
        await message.answer(f"Tizim xatoligi: {str(e)}", reply_markup=keyboard)
