from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database.models import Person, MeetingNote
from keyboards.people_kb import get_cancel_keyboard, get_person_actions_keyboard
from services.llm import analyze_note

router = Router()

class NoteState(StatesGroup):
    waiting_for_text = State()

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
    await MeetingNote.create(
        person=person,
        raw_text=message.text,
        ai_summary=analysis,
        stress_level=analysis.get("mood")
    )
    
    # Формируем красивый ответ
    summary_text = (
        f"✅ <b>Заметка для {person.name} сохранена!</b>\n\n"
        f"🤖 <b>AI Анализ:</b>\n"
        f"Mood: {analysis.get('mood_text', 'N/A')} ({analysis.get('mood', '-')}/10)\n"
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
        reply_markup=get_person_actions_keyboard(person_id)
    )
    await state.clear()

@router.callback_query(F.data == "cancel_action")
async def callback_cancel(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.delete()
    await callback.answer("Действие отменено")

@router.callback_query(F.data.startswith("history:"))
async def callback_history(callback: types.CallbackQuery):
    person_id = int(callback.data.split(":")[1])
    person = await Person.get_or_none(id=person_id)
    
    if not person:
        await callback.answer("Сотрудник не найден", show_alert=True)
        return

    # Берем последние 5 заметок
    notes = await MeetingNote.filter(person=person).limit(5)
    
    if not notes:
        await callback.message.answer(f"📭 У <b>{person.name}</b> пока нет заметок.")
    else:
        text = f"📜 <b>Последние заметки ({person.name}):</b>\n\n"
        for note in notes:
            date_str = note.created_at.strftime("%d.%m.%Y")
            text += f"📅 <b>{date_str}</b>\n{note.raw_text}\n\n"
        
        await callback.message.answer(text)
    
    # Возвращаем меню действий
    await callback.message.answer(
        "Что делаем дальше?",
        reply_markup=get_person_actions_keyboard(person_id)
    )
    await callback.answer()

