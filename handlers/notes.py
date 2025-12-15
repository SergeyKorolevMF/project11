import html
import math

from aiogram import Router, types, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database.models import Person, MeetingNote
from keyboards.history_kb import get_history_keyboard
from keyboards.people_kb import (
    get_cancel_keyboard,
    get_person_actions_keyboard,
)
from keyboards.note_kb import get_note_actions_keyboard
from services.llm import analyze_note

router = Router()

HISTORY_PAGE_SIZE = 5


def _truncate_one_line(text: str, max_len: int = 28) -> str:
    one_line = " ".join((text or "").split())
    if len(one_line) <= max_len:
        return one_line
    return one_line[: max_len - 1] + "…"


async def _build_history_page(
    *,
    user_id: int,
    person_id: int,
    page: int,
) -> tuple[str, types.InlineKeyboardMarkup] | tuple[str, None]:
    person = await Person.get_or_none(id=person_id)
    if not person or person.user_id != user_id:
        return "Сотрудник не найден.", None

    total = await MeetingNote.filter(person_id=person_id).count()
    if total == 0:
        return f"📭 У <b>{person.name}</b> пока нет заметок.", None

    pages = max(1, math.ceil(total / HISTORY_PAGE_SIZE))
    page = max(0, min(page, pages - 1))
    offset = page * HISTORY_PAGE_SIZE

    notes = (
        await MeetingNote.filter(person_id=person_id)
        .offset(offset)
        .limit(HISTORY_PAGE_SIZE)
    )

    note_buttons: list[tuple[str, str]] = []
    for note in notes:
        date_str = note.created_at.strftime("%d.%m")
        snippet = _truncate_one_line(note.raw_text)
        mood = note.stress_level if note.stress_level is not None else "-"
        note_buttons.append((f"📅 {date_str} ({mood}/10) {snippet}", str(note.id)))

    has_prev = page > 0
    has_next = page < pages - 1

    text = (
        f"📜 <b>История: {person.name}</b>\n"
        f"Страница {page + 1}/{pages}\n\n"
        "Выберите заметку:"
    )
    kb = get_history_keyboard(
        person_id=person_id,
        page=page,
        note_buttons=note_buttons,
        has_prev=has_prev,
        has_next=has_next,
    )
    return text, kb


class NoteState(StatesGroup):
    waiting_for_text = State()
    editing_text = State()


@router.callback_query(F.data.startswith("add_note:"))
async def callback_add_note(callback: types.CallbackQuery, state: FSMContext):
    person_id = int(callback.data.split(":")[1])

    # Сохраняем ID человека в state data
    await state.update_data(person_id=person_id)

    person = await Person.get_or_none(id=person_id)
    if not person:
        await callback.answer("Человек не найден", show_alert=True)
        return

    await callback.message.answer(
        f"Напишите заметку для <b>{person.name}</b>:",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(NoteState.waiting_for_text)
    await callback.answer()

@router.message(NoteState.waiting_for_text)
async def process_note_text(message: types.Message, state: FSMContext):
    if not message.text:
        await message.answer("Пожалуйста, введите текст заметки.")
        return

    data = await state.get_data()
    person_id = data.get("person_id")

    person = await Person.get_or_none(id=person_id)
    if not person:
        await message.answer("Ошибка: сотрудник не найден.")
        await state.clear()
        return

    # Отправляем сообщение об ожидании
    processing_msg = await message.answer("⏳ Сохраняю и анализирую заметку...")

    # Анализируем с помощью AI
    analysis = await analyze_note(message.text, custom_prompt=person.custom_prompt)

    # Сохраняем заметку
    note = await MeetingNote.create(
        person=person,
        raw_text=message.text,
        ai_summary=analysis,
        stress_level=analysis.get("mood")
    )

    # Формируем красивый ответ
    summary_text = (
        f"✅ <b>Заметка для {person.name} сохранена!</b>\n\n"
        f"🤖 <b>AI Анализ:</b>\n"
        f"Mood: {analysis.get('mood_text', 'N/A')} "
        f"({analysis.get('mood', '-')}/10)\n"
        f"Summary: {analysis.get('summary', '-')}\n"
    )

    if analysis.get('positive'):
        summary_text += f"➕ {analysis.get('positive')}\n"
    if analysis.get('negative'):
        summary_text += f"➖ {analysis.get('negative')}\n"

    todos = analysis.get('action_items', [])
    if todos:
        summary_text += "\n📋 <b>Todos:</b>\n"
        for todo in todos:
            summary_text += f"▫️ {todo}\n"

    tags = analysis.get('tags', [])
    if tags:
        summary_text += "\n" + " ".join(tags)

    # Удаляем сообщение "Анализирую..." и отправляем результат
    await processing_msg.delete()
    await message.answer(
        summary_text,
        reply_markup=get_note_actions_keyboard(
            note_id=str(note.id),
            person_id=person_id,
        ),
    )
    await state.clear()


@router.callback_query(F.data == "cancel_action")
async def callback_cancel(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.delete()
    await callback.answer("Действие отменено")


@router.callback_query(F.data.startswith("note_edit:"))
async def callback_note_edit(callback: types.CallbackQuery, state: FSMContext):
    """
    Переходим в режим правки сырого текста заметки.
    callback_data: note_edit:<note_uuid>
    """
    parts = callback.data.split(":")
    if len(parts) != 2:
        await callback.answer("Некорректная команда", show_alert=True)
        return

    note_id = parts[1]
    note = await MeetingNote.get_or_none(id=note_id).prefetch_related("person")
    if not note:
        await callback.answer("Заметка не найдена", show_alert=True)
        return

    await state.set_state(NoteState.editing_text)
    await state.update_data(note_id=str(note.id))

    await callback.message.answer(
        "✏️ Отправьте исправленный текст заметки одним сообщением.\n"
        "Я пересчитаю AI‑разбор и обновлю запись.",
        reply_markup=get_cancel_keyboard(),
    )
    await callback.answer()


@router.message(NoteState.editing_text)
async def process_note_edit(message: types.Message, state: FSMContext):
    if not message.text:
        await message.answer("Пожалуйста, отправьте текстом.")
        return

    data = await state.get_data()
    note_id = data.get("note_id")
    if not note_id:
        await message.answer("Ошибка состояния. Попробуйте ещё раз.")
        await state.clear()
        return

    note = await MeetingNote.get_or_none(id=note_id).prefetch_related("person")
    if not note:
        await message.answer("Заметка не найдена.")
        await state.clear()
        return

    processing_msg = await message.answer("⏳ Обновляю и пересчитываю AI‑разбор...")

    note.raw_text = message.text
    analysis = await analyze_note(message.text, custom_prompt=note.person.custom_prompt)
    note.ai_summary = analysis
    note.stress_level = analysis.get("mood")
    await note.save()

    summary_text = (
        f"✅ <b>Заметка для {note.person.name} обновлена!</b>\n\n"
        f"🤖 <b>AI Анализ:</b>\n"
        f"Mood: {analysis.get('mood_text', 'N/A')} "
        f"({analysis.get('mood', '-')}/10)\n"
        f"Summary: {analysis.get('summary', '-')}\n"
    )

    if analysis.get("positive"):
        summary_text += f"➕ {analysis.get('positive')}\n"
    if analysis.get("negative"):
        summary_text += f"➖ {analysis.get('negative')}\n"

    todos = analysis.get("action_items", [])
    if todos:
        summary_text += "\n📋 <b>Todos:</b>\n"
        for todo in todos:
            summary_text += f"▫️ {todo}\n"

    tags = analysis.get("tags", [])
    if tags:
        summary_text += "\n" + " ".join(tags)

    await processing_msg.delete()
    await message.answer(
        summary_text,
        reply_markup=get_note_actions_keyboard(
            note_id=str(note.id),
            person_id=note.person_id,
        ),
    )
    await state.clear()


@router.callback_query(F.data.startswith("note_reanalyze:"))
async def callback_note_reanalyze(callback: types.CallbackQuery):
    """
    Пересчитываем AI по текущему raw_text, чтобы можно было поправить промпт
    и обновить разбор без редактирования текста.
    callback_data: note_reanalyze:<note_uuid>
    """
    parts = callback.data.split(":")
    if len(parts) != 2:
        await callback.answer("Некорректная команда", show_alert=True)
        return

    note_id = parts[1]
    note = await MeetingNote.get_or_none(id=note_id).prefetch_related("person")
    if not note:
        await callback.answer("Заметка не найдена", show_alert=True)
        return

    await callback.answer("⏳ Пересчитываю…")
    analysis = await analyze_note(note.raw_text, custom_prompt=note.person.custom_prompt)
    note.ai_summary = analysis
    note.stress_level = analysis.get("mood")
    await note.save()

    summary_text = (
        f"✅ <b>AI‑разбор обновлён ({note.person.name})</b>\n\n"
        f"🤖 <b>AI Анализ:</b>\n"
        f"Mood: {analysis.get('mood_text', 'N/A')} "
        f"({analysis.get('mood', '-')}/10)\n"
        f"Summary: {analysis.get('summary', '-')}\n"
    )

    if analysis.get("positive"):
        summary_text += f"➕ {analysis.get('positive')}\n"
    if analysis.get("negative"):
        summary_text += f"➖ {analysis.get('negative')}\n"

    todos = analysis.get("action_items", [])
    if todos:
        summary_text += "\n📋 <b>Todos:</b>\n"
        for todo in todos:
            summary_text += f"▫️ {todo}\n"

    tags = analysis.get("tags", [])
    if tags:
        summary_text += "\n" + " ".join(tags)

    await callback.message.edit_text(
        summary_text,
        reply_markup=get_note_actions_keyboard(
            note_id=str(note.id),
            person_id=note.person_id,
        ),
    )


@router.callback_query(F.data.startswith("history:"))
async def callback_history(callback: types.CallbackQuery):
    person_id = int(callback.data.split(":")[1])
    text, kb = await _build_history_page(
        user_id=callback.from_user.id,
        person_id=person_id,
        page=0,
    )

    if not kb:
        await callback.message.answer(text)
        await callback.answer()
        return

    try:
        await callback.message.edit_text(text, reply_markup=kb)
    except TelegramBadRequest:
        await callback.message.answer(text, reply_markup=kb)

    await callback.answer()


@router.callback_query(F.data.startswith("history_page:"))
async def callback_history_page(callback: types.CallbackQuery):
    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer("Некорректная команда", show_alert=True)
        return

    person_id = int(parts[1])
    page = int(parts[2])

    text, kb = await _build_history_page(
        user_id=callback.from_user.id,
        person_id=person_id,
        page=page,
    )
    if not kb:
        await callback.answer("Нет заметок", show_alert=True)
        return

    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("note_view:"))
async def callback_note_view(callback: types.CallbackQuery):
    """
    Открываем конкретную заметку из истории.
    callback_data: note_view:<note_uuid>:<person_id>:<page>
    """
    parts = callback.data.split(":")
    if len(parts) != 4:
        await callback.answer("Некорректная команда", show_alert=True)
        return

    note_id = parts[1]
    person_id = int(parts[2])
    page = int(parts[3])

    person = await Person.get_or_none(id=person_id)
    if not person or person.user_id != callback.from_user.id:
        await callback.answer("Сотрудник не найден", show_alert=True)
        return

    note = await MeetingNote.get_or_none(id=note_id)
    if not note or note.person_id != person_id:
        await callback.answer("Заметка не найдена", show_alert=True)
        return

    ai = note.ai_summary or {}
    date_str = note.created_at.strftime("%d.%m.%Y %H:%M")
    raw_preview = html.escape(note.raw_text)

    text = (
        f"📝 <b>{person.name}</b>\n"
        f"📅 {date_str}\n\n"
        f"<pre>{raw_preview}</pre>\n\n"
        f"🤖 <b>AI:</b> {ai.get('summary', '-')}"
    )

    await callback.message.edit_text(
        text,
        reply_markup=get_note_actions_keyboard(
            note_id=str(note.id),
            person_id=person_id,
            back_callback_data=f"history_page:{person_id}:{page}",
        ),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("note_delete:"))
async def callback_note_delete(callback: types.CallbackQuery):
    """
    Удаление заметки целиком.
    callback_data: note_delete:<note_uuid>:<person_id>
    """
    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer("Некорректная команда", show_alert=True)
        return

    note_id = parts[1]
    person_id = int(parts[2])

    deleted = await MeetingNote.filter(id=note_id).delete()
    if deleted:
        await callback.message.edit_text("🗑️ Заметка удалена.")
    else:
        await callback.answer("Заметка не найдена", show_alert=True)
        return

    await callback.message.answer(
        "Что делаем дальше?",
        reply_markup=get_person_actions_keyboard(person_id),
    )
    await callback.answer()
