import json
from openai import AsyncOpenAI
from config import OPENAI_API_KEY

client = AsyncOpenAI(api_key=OPENAI_API_KEY)

DEFAULT_SYSTEM_PROMPT = """
Ты — эмпатичный ассистент менеджера. Твоя задача — анализировать заметки со встреч (1-1).
Твой анализ должен быть структурированным и полезным для менеджера.

ВХОДНЫЕ ДАННЫЕ: Текст заметки.

ВЫХОДНЫЕ ДАННЫЕ (JSON):
{
    "mood": int (Оценка настроения сотрудника от 1 до 10, где 1 - депрессия/выгорание, 10 - эйфория),
    "mood_text": "string" (Краткое описание настроения, например 'Тревожное', 'Вдохновленное'),
    "summary": "string" (Краткая выжимка встречи/заметки, 1-2 предложения),
    "action_items": ["string", "string"] (Список задач/todo, если есть. Если нет - пустой список),
    "positive": "string" (Что порадовало/Акула недели. Если нет - null),
    "negative": "string" (Что расстроило/Крыса недели/Источник стресса. Если нет - null),
    "tags": ["#tag1", "#tag2"] (Хештеги для поиска, включая имя человека если есть в контексте)
}

Отвечай ТОЛЬКО валидным JSON.
"""

async def analyze_note(text: str, custom_prompt: str = None) -> dict:
    """
    Анализирует текст заметки с помощью LLM.
    """
    system_prompt = custom_prompt if custom_prompt else DEFAULT_SYSTEM_PROMPT
    
    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ],
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content
        return json.loads(content)
    except Exception as e:
        print(f"Error in analyze_note: {e}")
        # Возвращаем заглушку в случае ошибки
        return {
            "mood": None,
            "summary": "Не удалось проанализировать заметку.",
            "action_items": [],
            "error": str(e)
        }

