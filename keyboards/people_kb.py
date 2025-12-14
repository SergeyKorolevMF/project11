from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database.models import Person

def get_people_keyboard(people: list[Person]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for person in people:
        # callback_data: person_id:<id>
        builder.button(text=person.name, callback_data=f"person_select:{person.id}")
    
    builder.button(text="➕ Добавить нового", callback_data="add_person_btn")
    builder.adjust(2) # По 2 кнопки в ряд
    return builder.as_markup()

def get_person_actions_keyboard(person_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📝 Добавить заметку", callback_data=f"add_note:{person_id}")
    builder.button(text="📜 История (5)", callback_data=f"history:{person_id}")
    builder.button(text="🔙 Назад", callback_data="back_to_team")
    builder.adjust(1)
    return builder.as_markup()

def get_cancel_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отмена", callback_data="cancel_action")
    return builder.as_markup()

