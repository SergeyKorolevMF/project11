import html

from aiogram import F, Router, types
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database.models import Person, User
from keyboards.people_kb import (
    get_people_keyboard,
    get_person_actions_keyboard,
    get_person_prompt_keyboard,
)

router = Router()


class AddPersonState(StatesGroup):
    waiting_for_name = State()


class PersonPromptState(StatesGroup):
    waiting_for_prompt = State()


@router.message(Command("add_person"))
async def cmd_add_person(message: types.Message, state: FSMContext):
    await message.answer(
        "Введите имя сотрудника (или название регулярной встречи):"
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
            f"✅ Сотрудник <b>{name}</b> добавлен в вашу команду."
        )
    except Exception:  # Скорее всего нарушение уникальности
        await message.answer(
            f"⚠️ Сотрудник с именем <b>{name}</b> уже есть в вашем списке."
        )

    await state.clear()

@router.message(Command("my_team"))
async def cmd_my_team(message: types.Message):
    user_id = message.from_user.id
    # Получаем список людей пользователя
    people = await Person.filter(user_id=user_id).all()

    if not people:
        await message.answer(
            "В вашей команде пока никого нет. Используйте /add_person, "
            "чтобы добавить."
        )
        return

    await message.answer(
        "👥 <b>Ваша команда:</b>\nВыберите сотрудника для работы:",
        reply_markup=get_people_keyboard(people)
    )

@router.callback_query(F.data.startswith("person_select:"))
async def callback_person_select(callback: types.CallbackQuery):
    person_id = int(callback.data.split(":")[1])
    person = await Person.get_or_none(id=person_id)

    if not person:
        await callback.answer("Сотрудник не найден", show_alert=True)
        return

    try:
        await callback.message.edit_text(
            f"👤 Выбран: <b>{person.name}</b>\nЧто хотите сделать?",
            reply_markup=get_person_actions_keyboard(person_id)
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
            "👥 <b>Ваша команда:</b>\nВыберите сотрудника:",
            reply_markup=get_people_keyboard(people)
        )
    except TelegramBadRequest:
        pass

    await callback.answer()

@router.callback_query(F.data == "add_person_btn")
async def callback_add_person_btn(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "Введите имя сотрудника (или название регулярной встречи):"
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
        await callback.answer("Сотрудник не найден", show_alert=True)
        return

    if person.custom_prompt:
        prompt_preview = html.escape(person.custom_prompt)
        text = (
            f"🧠 <b>Промпт для {person.name}</b>\n\n"
            "Сейчас установлен кастомный промпт:\n"
            f"<pre>{prompt_preview}</pre>"
        )
    else:
        text = (
            f"🧠 <b>Промпт для {person.name}</b>\n\n"
            "Сейчас используется дефолтный промпт (общий для всех)."
        )

    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_person_prompt_keyboard(person_id),
        )
    except TelegramBadRequest:
        await callback.message.answer(
            text,
            reply_markup=get_person_prompt_keyboard(person_id),
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
        await callback.answer("Сотрудник не найден", show_alert=True)
        return

    await state.set_state(PersonPromptState.waiting_for_prompt)
    await state.update_data(person_id=person_id)

    await callback.message.answer(
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
    if not person_id:
        await message.answer("Ошибка состояния. Попробуйте ещё раз.")
        await state.clear()
        return

    person = await Person.get_or_none(id=person_id)
    if not person:
        await message.answer("Сотрудник не найден.")
        await state.clear()
        return

    person.custom_prompt = message.text.strip()
    await person.save()
    await state.clear()

    await message.answer(
        f"✅ Промпт для <b>{person.name}</b> обновлён.",
        reply_markup=get_person_actions_keyboard(person_id),
    )


@router.callback_query(F.data.startswith("person_prompt_reset:"))
async def callback_person_prompt_reset(callback: types.CallbackQuery):
    parts = callback.data.split(":")
    if len(parts) != 2:
        await callback.answer("Некорректная команда", show_alert=True)
        return

    person_id = int(parts[1])
    person = await Person.get_or_none(id=person_id)
    if not person:
        await callback.answer("Сотрудник не найден", show_alert=True)
        return

    person.custom_prompt = None
    await person.save()

    await callback.message.edit_text(
        f"♻️ Промпт для <b>{person.name}</b> сброшен на дефолтный.",
        reply_markup=get_person_actions_keyboard(person_id),
    )
    await callback.answer()
