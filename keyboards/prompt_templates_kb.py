from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.models import PromptTemplate


def get_prompt_templates_keyboard(
    person_id: int,
    templates: list[PromptTemplate],
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    for tpl in templates:
        builder.button(
            text=f"✅ {tpl.name}",
            callback_data=f"prompt_tpl_apply:{tpl.id}:{person_id}",
        )
        builder.button(
            text="🗑️",
            callback_data=f"prompt_tpl_delete:{tpl.id}:{person_id}",
        )

    builder.button(
        text="➕ Новый шаблон",
        callback_data=f"prompt_tpl_new:{person_id}",
    )
    builder.button(text="🔙 Назад", callback_data=f"person_prompt:{person_id}")

    builder.adjust(2, 2, 1)
    return builder.as_markup()
