from aiogram import F, Router, types
from aiogram.filters import Command, CommandStart

from database.models import Person, User
from keyboards.main_menu import MAIN_MENU_BUTTONS, get_main_menu_keyboard

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
        f"Привет, {full_name}!\n\n"
        "Я помогу быстро сохранять заметки по 1‑1/встречам и показывать "
        "структурированный AI‑разбор.\n\n"
        "Начни с добавления встреч (если их ещё нет), затем — добавляй "
        "заметки через меню."
    )

    await message.answer(welcome_text, reply_markup=get_main_menu_keyboard())

    people_count = await Person.filter(user_id=user_id).count()
    if people_count == 0:
        await message.answer(
            "Похоже, у тебя пока нет ни одной встречи.\n"
            "Нажми **📅 Встречи** → **➕ Добавить новую** или введи команду "
            "/add_person.",
            reply_markup=get_main_menu_keyboard(),
            parse_mode="Markdown",
        )


@router.message(Command("help"))
async def cmd_help(message: types.Message):
    text = (
        "❓ <b>Помощь</b>\n\n"
        "Самое простое — пользоваться кнопками меню снизу.\n\n"
        "<b>Команды</b>:\n"
        "/start — перезапустить приветствие\n"
        "/my_team — список встреч\n"
        "/add_person — добавить встречу\n\n"
        "<b>Как добавить заметку</b>:\n"
        "📅 Встречи → выбрать встречу → 📝 Добавить заметку\n"
    )
    await message.answer(text, reply_markup=get_main_menu_keyboard())


@router.message(F.text.in_(MAIN_MENU_BUTTONS))
async def main_menu_router(message: types.Message):
    """
    Роутинг по reply-меню. Команды остаются доступными всегда.
    """
    label = (message.text or "").strip()

    if label in ("📅 Встречи", "➕ Заметка"):
        # Показываем список встреч (там же можно добавить заметку через
        # действия).
        # Дублируем логику /my_team, чтобы меню работало без знания команд.
        user_id = message.from_user.id
        people = await Person.filter(user_id=user_id).all()
        if not people:
            await message.answer(
                "У вас пока нет встреч. Нажмите /add_person или "
                "добавьте через кнопку ниже.",
                reply_markup=get_main_menu_keyboard(),
            )
            return

        # AICODE-NOTE: Локальный импорт, чтобы избежать циклических импортов.
        from keyboards.people_kb import get_people_keyboard

        await message.answer(
            "📅 <b>Ваши встречи:</b>\nВыберите встречу для работы:",
            reply_markup=get_people_keyboard(people),
        )
        return

    if label == "🕘 История":
        # Быстрый вход: показываем список встреч, далее история доступна из
        # действий.
        user_id = message.from_user.id
        people = await Person.filter(user_id=user_id).all()
        if not people:
            await message.answer(
                "Пока нет встреч и заметок. Добавь встречу через /add_person.",
                reply_markup=get_main_menu_keyboard(),
            )
            return

        # AICODE-NOTE: Локальный импорт, чтобы избежать циклических импортов.
        from keyboards.people_kb import get_people_keyboard

        await message.answer(
            "🕘 Выберите встречу, чтобы посмотреть историю заметок:",
            reply_markup=get_people_keyboard(people),
        )
        return

    if label == "⚙️ Настройки":
        await message.answer(
            "⚙️ <b>Настройки</b>\n\n"
            "Пока здесь минимум. Скоро добавим:\n"
            "- дефолтный промпт\n"
            "- интеграции (Todoist/Calendar)\n",
            reply_markup=get_main_menu_keyboard(),
        )
        return

    if label == "❓ Помощь":
        await cmd_help(message)
        return
