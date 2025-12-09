from aiogram import Router, types
from aiogram.filters import CommandStart
from database.models import User

router = Router()

@router.message(CommandStart())
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username
    full_name = message.from_user.full_name

    # Создаем или обновляем пользователя в БД
    user, created = await User.get_or_create(
        id=user_id,
        defaults={
            "username": username,
            "full_name": full_name
        }
    )

    # Если пользователь уже был, обновляем данные (например, если сменил ник)
    if not created:
        if user.username != username or user.full_name != full_name:
            user.username = username
            user.full_name = full_name
            await user.save()

    welcome_text = (
        f"Привет, {full_name}! 👋\n\n"
        "Я бот для ведения заметок со встреч. Я помогу тебе структурировать "
        "информацию о твоих 1-1 и командных синках.\n\n"
        "Я уже сохранил тебя в базе данных."
    )
    
    await message.answer(welcome_text)

