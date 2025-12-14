from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database.models import Person, User

router = Router()

class AddPersonState(StatesGroup):
    waiting_for_name = State()

@router.message(Command("add_person"))
async def cmd_add_person(message: types.Message, state: FSMContext):
    await message.answer("Введите имя сотрудника (или название регулярной встречи):")
    await state.set_state(AddPersonState.waiting_for_name)

@router.message(AddPersonState.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    name = message.text.strip()
    user_id = message.from_user.id
    
    # Получаем пользователя из БД
    user = await User.get(id=user_id)
    
    try:
        # Пытаемся создать
        await Person.create(user=user, name=name)
        await message.answer(f"✅ Сотрудник <b>{name}</b> добавлен в вашу команду.")
    except Exception: # Скорее всего нарушение уникальности
        await message.answer(f"⚠️ Сотрудник с именем <b>{name}</b> уже есть в вашем списке.")
        
    await state.clear()

@router.message(Command("my_team"))
async def cmd_my_team(message: types.Message):
    user_id = message.from_user.id
    # Получаем список людей пользователя
    people = await Person.filter(user_id=user_id).all()
    
    if not people:
        await message.answer("В вашей команде пока никого нет. Используйте /add_person чтобы добавить.")
        return

    text = "👥 <b>Ваша команда:</b>\n\n"
    for person in people:
        text += f"• {person.name}\n"
        
    await message.answer(text)

