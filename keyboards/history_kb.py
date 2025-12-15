from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_history_keyboard(
    *,
    person_id: int,
    page: int,
    note_buttons: list[tuple[str, str]],
    has_prev: bool,
    has_next: bool,
) -> InlineKeyboardMarkup:
    """
    note_buttons: список (button_text, note_id)
    """
    builder = InlineKeyboardBuilder()

    for text, note_id in note_buttons:
        builder.row(
            InlineKeyboardButton(
                text=text,
                callback_data=f"note_view:{note_id}:{person_id}:{page}",
            )
        )

    nav_row = []
    if has_prev:
        nav_row.append(
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=f"history_page:{person_id}:{page - 1}",
            )
        )
    if has_next:
        nav_row.append(
            InlineKeyboardButton(
                text="Вперёд ➡️",
                callback_data=f"history_page:{person_id}:{page + 1}",
            )
        )

    if nav_row:
        builder.row(*nav_row)

    builder.row(
        InlineKeyboardButton(
            text="👤 К человеку",
            callback_data=f"person_select:{person_id}",
        )
    )
    return builder.as_markup()

