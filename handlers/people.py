import html

from aiogram import F, Router, types
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database.models import Person, PromptTemplate, User
from keyboards.people_kb import (
    get_people_keyboard,
    get_person_actions_keyboard,
    get_person_prompt_keyboard,
)

router = Router()

PROMPT_DISABLED_PREFIX = "[DISABLED]\n"


def _parse_custom_prompt(custom_prompt: str | None) -> tuple[bool, str | None]:
    """
    Returns (is_enabled, prompt_text_without_marker_or_none).
    """
    if not custom_prompt:
        return True, None

    if custom_prompt.startswith(PROMPT_DISABLED_PREFIX):
        raw = custom_prompt[len(PROMPT_DISABLED_PREFIX):].strip()
        return False, (raw or None)

    return True, custom_prompt


def _format_prompt_preview(prompt_text: str | None) -> str:
    if not prompt_text:
        return "<i>(пусто)</i>"
    return f"<pre>{html.escape(prompt_text)}</pre>"


class AddPersonState(StatesGroup):
    waiting_for_name = State()


class PersonPromptState(StatesGroup):
    waiting_for_prompt = State()


class PromptTemplateState(StatesGroup):
    waiting_for_name = State()
    waiting_for_text = State()


@router.message(Command("add_person"))
async def cmd_add_person(message: types.Message, state: FSMContext):
    await message.answer(
        "Введите название встречи (или имя человека):"
    )
    await state.set_state(AddPersonState.waiting_for_name)


@router.message(AddPersonState.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    if not message.text:
        await message.answer("Пожалуйста, введите имя текстом.")
        return

    name = message.text.strip()
    user_id = message.from_user.id

    # Получаем пользователя из БД
    user = await User.get_or_none(id=user_id)
    if not user:
        # Редкий случай, если пользователь не нажимал /start
        user = await User.create(
            id=user_id,
            username=message.from_user.username,
            full_name=message.from_user.full_name,
        )

    try:
        # Пытаемся создать
        await Person.create(user=user, name=name)
        await message.answer(
            f"✅ Встреча <b>{name}</b> добавлена."
        )
    except Exception:  # Скорее всего нарушение уникальности
        await message.answer(
            f"⚠️ Встреча с именем <b>{name}</b> уже есть в вашем списке."
        )

    await state.clear()


@router.message(Command("my_team"))
async def cmd_my_team(message: types.Message):
    user_id = message.from_user.id
    # Получаем список людей пользователя
    people = await Person.filter(user_id=user_id).all()

    if not people:
        await message.answer(
            "У вас пока нет встреч. Используйте /add_person, "
            "чтобы добавить."
        )
        return

    await message.answer(
        "📅 <b>Ваши встречи:</b>\nВыберите встречу для работы:",
        reply_markup=get_people_keyboard(people),
    )


@router.callback_query(F.data.startswith("person_select:"))
async def callback_person_select(callback: types.CallbackQuery):
    person_id = int(callback.data.split(":")[1])
    person = await Person.get_or_none(id=person_id)

    if not person:
        await callback.answer("Встреча не найдена", show_alert=True)
        return

    try:
        await callback.message.edit_text(
            f"📅 Выбрано: <b>{person.name}</b>\nЧто хотите сделать?",
            reply_markup=get_person_actions_keyboard(person_id),
        )
    except TelegramBadRequest:
        pass

    await callback.answer()


@router.callback_query(F.data == "back_to_team")
async def callback_back_to_team(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    people = await Person.filter(user_id=user_id).all()

    try:
        await callback.message.edit_text(
            "📅 <b>Ваши встречи:</b>\nВыберите встречу:",
            reply_markup=get_people_keyboard(people),
        )
    except TelegramBadRequest:
        pass

    await callback.answer()


@router.callback_query(F.data == "add_person_btn")
async def callback_add_person_btn(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "Введите название встречи (или имя человека):"
    )
    await state.set_state(AddPersonState.waiting_for_name)
    await callback.answer()


@router.callback_query(F.data.startswith("person_prompt:"))
async def callback_person_prompt(callback: types.CallbackQuery):
    """
    Показываем текущий промпт (если есть) и даём кнопки изменить/сбросить.
    callback_data: person_prompt:<person_id>
    """
    parts = callback.data.split(":")
    if len(parts) != 2:
        await callback.answer("Некорректная команда", show_alert=True)
        return

    person_id = int(parts[1])
    person = await Person.get_or_none(id=person_id)
    if not person:
        await callback.answer("Встреча не найдена", show_alert=True)
        return

    is_enabled, prompt_text = _parse_custom_prompt(person.custom_prompt)
    status = (
        "✅ включён"
        if prompt_text and is_enabled
        else "⏸️ выключен"
        if prompt_text
        else "—"
    )
    text = (
        f"🧠 <b>Промпт для встречи: {person.name}</b>\n"
        f"Статус: <b>{status}</b>\n\n"
        "<b>Текущий промпт</b>:\n"
        f"{_format_prompt_preview(prompt_text)}\n\n"
        "<i>Промпт дополняет дефолтный. Его можно временно выключить "
        "для этой встречи.</i>"
    )

    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_person_prompt_keyboard(
                person_id,
                has_prompt=bool(prompt_text),
                is_disabled=bool(prompt_text) and not is_enabled,
            ),
        )
    except TelegramBadRequest:
        await callback.message.answer(
            text,
            reply_markup=get_person_prompt_keyboard(
                person_id,
                has_prompt=bool(prompt_text),
                is_disabled=bool(prompt_text) and not is_enabled,
            ),
        )

    await callback.answer()


@router.callback_query(F.data.startswith("person_prompt_set:"))
async def callback_person_prompt_set(
    callback: types.CallbackQuery,
    state: FSMContext,
):
    parts = callback.data.split(":")
    if len(parts) != 2:
        await callback.answer("Некорректная команда", show_alert=True)
        return

    person_id = int(parts[1])
    person = await Person.get_or_none(id=person_id)
    if not person:
        await callback.answer("Встреча не найдена", show_alert=True)
        return

    is_enabled, prompt_text = _parse_custom_prompt(person.custom_prompt)

    await state.set_state(PersonPromptState.waiting_for_prompt)
    await state.update_data(
        person_id=person_id,
        prompt_was_disabled=not is_enabled,
    )

    await callback.message.answer(
        "Текущий промпт:\n"
        f"{_format_prompt_preview(prompt_text)}\n\n"
        "✏️ Отправьте текст промпта одним сообщением.\n\n"
        "Подсказка: пиши дополнительные правила поверх дефолтного промпта "
        "(например: “всегда извлекай risks и blockers”).",
    )
    await callback.answer()


@router.message(PersonPromptState.waiting_for_prompt)
async def process_person_prompt(message: types.Message, state: FSMContext):
    if not message.text:
        await message.answer("Пожалуйста, отправьте текстом.")
        return

    data = await state.get_data()
    person_id = data.get("person_id")
    prompt_was_disabled = bool(data.get("prompt_was_disabled"))
    if not person_id:
        await message.answer("Ошибка состояния. Попробуйте ещё раз.")
        await state.clear()
        return

    person = await Person.get_or_none(id=person_id)
    if not person:
        await message.answer("Встреча не найдена.")
        await state.clear()
        return

    new_prompt = message.text.strip()
    if prompt_was_disabled:
        person.custom_prompt = PROMPT_DISABLED_PREFIX + new_prompt
    else:
        person.custom_prompt = new_prompt
    await person.save()
    await state.clear()

    await message.answer(
        f"✅ Промпт для <b>{person.name}</b> обновлён.",
        reply_markup=get_person_actions_keyboard(person_id),
    )


@router.callback_query(F.data.startswith("person_prompt_disable:"))
async def callback_person_prompt_disable(callback: types.CallbackQuery):
    parts = callback.data.split(":")
    if len(parts) != 2:
        await callback.answer("Некорректная команда", show_alert=True)
        return

    person_id = int(parts[1])
    person = await Person.get_or_none(id=person_id)
    if not person:
        await callback.answer("Встреча не найдена", show_alert=True)
        return

    is_enabled, prompt_text = _parse_custom_prompt(person.custom_prompt)
    if not prompt_text:
        await callback.answer("Нет кастомного промпта", show_alert=True)
        return

    if not is_enabled:
        await callback.answer("Уже выключен")
        return

    person.custom_prompt = PROMPT_DISABLED_PREFIX + prompt_text.strip()
    await person.save()
    await callback.answer("⏸️ Выключено")
    await callback_person_prompt(callback)


@router.callback_query(F.data.startswith("person_prompt_enable:"))
async def callback_person_prompt_enable(callback: types.CallbackQuery):
    parts = callback.data.split(":")
    if len(parts) != 2:
        await callback.answer("Некорректная команда", show_alert=True)
        return

    person_id = int(parts[1])
    person = await Person.get_or_none(id=person_id)
    if not person:
        await callback.answer("Встреча не найдена", show_alert=True)
        return

    is_enabled, prompt_text = _parse_custom_prompt(person.custom_prompt)
    if not prompt_text:
        await callback.answer("Нет кастомного промпта", show_alert=True)
        return

    if is_enabled:
        await callback.answer("Уже включен")
        return

    person.custom_prompt = prompt_text.strip()
    await person.save()
    await callback.answer("✅ Включено")
    await callback_person_prompt(callback)


@router.callback_query(F.data.startswith("person_prompt_reset:"))
async def callback_person_prompt_reset(callback: types.CallbackQuery):
    parts = callback.data.split(":")
    if len(parts) != 2:
        await callback.answer("Некорректная команда", show_alert=True)
        return

    person_id = int(parts[1])
    person = await Person.get_or_none(id=person_id)
    if not person:
        await callback.answer("Встреча не найдена", show_alert=True)
        return

    person.custom_prompt = None
    await person.save()

    await callback.message.edit_text(
        f"♻️ Промпт для <b>{person.name}</b> сброшен на дефолтный.",
        reply_markup=get_person_actions_keyboard(person_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("person_prompt_templates:"))
async def callback_person_prompt_templates(callback: types.CallbackQuery):
    parts = callback.data.split(":")
    if len(parts) != 2:
        await callback.answer("Некорректная команда", show_alert=True)
        return

    person_id = int(parts[1])
    person = await Person.get_or_none(id=person_id)
    if not person or person.user_id != callback.from_user.id:
        await callback.answer("Встреча не найдена", show_alert=True)
        return

    templates = await PromptTemplate.filter(user_id=callback.from_user.id).all()
    from keyboards.prompt_templates_kb import get_prompt_templates_keyboard

    text = (
        f"📚 <b>Шаблоны промптов</b>\n"
        f"Встреча: <b>{person.name}</b>\n\n"
        "Выберите шаблон, чтобы применить его к этой встрече, "
        "или создайте новый."
    )
    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_prompt_templates_keyboard(person_id, templates),
        )
    except TelegramBadRequest:
        await callback.message.answer(
            text,
            reply_markup=get_prompt_templates_keyboard(person_id, templates),
        )
    await callback.answer()


@router.callback_query(F.data.startswith("prompt_tpl_new:"))
async def callback_prompt_template_new(
    callback: types.CallbackQuery,
    state: FSMContext,
):
    parts = callback.data.split(":")
    if len(parts) != 2:
        await callback.answer("Некорректная команда", show_alert=True)
        return

    person_id = int(parts[1])
    await state.set_state(PromptTemplateState.waiting_for_name)
    await state.update_data(person_id=person_id)
    await callback.message.answer("Введите название шаблона (например: 1-1 репорт):")
    await callback.answer()


@router.message(PromptTemplateState.waiting_for_name)
async def process_prompt_template_name(message: types.Message, state: FSMContext):
    if not message.text:
        await message.answer("Пожалуйста, введите текстом.")
        return

    name = message.text.strip()
    await state.update_data(template_name=name)
    await state.set_state(PromptTemplateState.waiting_for_text)
    await message.answer("Теперь отправьте текст шаблона одним сообщением:")


@router.message(PromptTemplateState.waiting_for_text)
async def process_prompt_template_text(message: types.Message, state: FSMContext):
    if not message.text:
        await message.answer("Пожалуйста, введите текстом.")
        return

    data = await state.get_data()
    person_id = data.get("person_id")
    template_name = data.get("template_name")
    template_text = message.text.strip()

    if not person_id or not template_name:
        await message.answer("Ошибка состояния. Попробуйте ещё раз.")
        await state.clear()
        return

    try:
        await PromptTemplate.create(
            user_id=message.from_user.id,
            name=template_name,
            text=template_text,
        )
        await message.answer(f"✅ Шаблон <b>{template_name}</b> сохранён.")
    except Exception:
        await message.answer(
            "⚠️ Не удалось сохранить шаблон (возможно, имя уже занято)."
        )

    await state.clear()

    templates = await PromptTemplate.filter(user_id=message.from_user.id).all()
    from keyboards.prompt_templates_kb import get_prompt_templates_keyboard

    await message.answer(
        "📚 Шаблоны обновлены.",
        reply_markup=get_prompt_templates_keyboard(person_id, templates),
    )


@router.callback_query(F.data.startswith("prompt_tpl_apply:"))
async def callback_prompt_template_apply(callback: types.CallbackQuery):
    """
    callback_data: prompt_tpl_apply:<template_id>:<person_id>
    """
    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer("Некорректная команда", show_alert=True)
        return

    template_id = int(parts[1])
    person_id = int(parts[2])

    person = await Person.get_or_none(id=person_id)
    if not person or person.user_id != callback.from_user.id:
        await callback.answer("Встреча не найдена", show_alert=True)
        return

    tpl = await PromptTemplate.get_or_none(id=template_id)
    if not tpl or tpl.user_id != callback.from_user.id:
        await callback.answer("Шаблон не найден", show_alert=True)
        return

    person.custom_prompt = tpl.text
    await person.save()
    await callback.answer("✅ Применено")
    await callback_person_prompt(callback)


@router.callback_query(F.data.startswith("prompt_tpl_delete:"))
async def callback_prompt_template_delete(callback: types.CallbackQuery):
    """
    callback_data: prompt_tpl_delete:<template_id>:<person_id>
    """
    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer("Некорректная команда", show_alert=True)
        return

    template_id = int(parts[1])
    person_id = int(parts[2])

    deleted = await PromptTemplate.filter(
        id=template_id,
        user_id=callback.from_user.id,
    ).delete()
    if not deleted:
        await callback.answer("Шаблон не найден", show_alert=True)
        return

    templates = await PromptTemplate.filter(user_id=callback.from_user.id).all()
    from keyboards.prompt_templates_kb import get_prompt_templates_keyboard

    await callback.message.edit_reply_markup(
        reply_markup=get_prompt_templates_keyboard(person_id, templates),
    )
    await callback.answer("🗑️ Удалено")
