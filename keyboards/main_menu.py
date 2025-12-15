from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


MAIN_MENU_BUTTONS = (
    "➕ Заметка",
    "👥 Люди",
    "🕘 История",
    "⚙️ Настройки",
    "❓ Помощь",
)


def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
    """
    Простое reply-меню, чтобы пользователю не нужно было помнить команды.
    """
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="➕ Заметка"),
                KeyboardButton(text="👥 Люди"),
            ],
            [
                KeyboardButton(text="🕘 История"),
                KeyboardButton(text="⚙️ Настройки"),
            ],
            [KeyboardButton(text="❓ Помощь")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие…",
    )
