# Technical Documentation

## Стек технологий
*   **Language:** Python 3.11+
*   **Framework:** aiogram 3.x (Telegram Bot API)
*   **Database:** SQLite (MVP), PostgreSQL (Future)
*   **ORM:** Tortoise ORM
*   **AI/NLP:** OpenAI API (или аналог) для парсинга текста, выделения сущностей и саммари.
*   **Environment:** `.env` для хранения секретов.

## Архитектура проекта

### Структура директорий
```text
project/
├── bot.py                 # Точка входа (entry point)
├── config.py              # Конфигурация и загрузка переменных окружения
├── database/
│   ├── db.py              # Инициализация Tortoise ORM
│   └── models.py          # Модели данных (User, Person, MeetingNote, etc.)
├── handlers/              # Обработчики команд и сообщений
│   ├── __init__.py
│   ├── common.py          # Общие команды (/start, /help)
│   ├── meetings.py        # Логика добавления встреч/заметок
│   └── reports.py         # Логика управления репортами/людьми
├── keyboards/             # Клавиатуры (inline, reply)
├── middlewares/           # Миддлвари (логирование, проверка прав)
├── services/              # Бизнес-логика и внешние интеграции
│   ├── llm_service.py     # Интеграция с LLM (парсинг заметок)
│   └── todoist_service.py # Интеграция с Todoist (в будущем)
└── utils/                 # Вспомогательные утилиты
```

1.  **Ввод заметки:**
    User -> Handler -> LLM Service (Parse Structure & Todos) -> Database (Save Note & Todos) -> User (Confirmation).

2.  **Аналитика:**
    User -> Handler -> Database (Query Aggregation) -> Handler (Format Text/Graph) -> User.

