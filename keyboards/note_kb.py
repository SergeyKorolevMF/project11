from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_note_actions_keyboard(
    note_id: str,
    person_id: int,
    back_callback_data: str | None = None,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✏️ Исправить", callback_data=f"note_edit:{note_id}")
    builder.button(
        text="🔁 Пересчитать AI",
        callback_data=f"note_reanalyze:{note_id}",
    )
    builder.button(
        text="🗑️ Удалить",
        callback_data=f"note_delete:{note_id}:{person_id}",
    )
    if back_callback_data:
        builder.button(text="🔙 К истории", callback_data=back_callback_data)
    builder.button(
        text="👤 К человеку",
        callback_data=f"person_select:{person_id}",
    )
    if back_callback_data:
        builder.adjust(2, 2, 1)
    else:
        builder.adjust(2, 1, 1)
    return builder.as_markup()
