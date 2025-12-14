# Technical Documentation

## Стек технологий
*   **Language:** Python 3.11+
*   **Framework:** aiogram 3.x (Telegram Bot API)
*   **Database:** 
    *   **Dev:** SQLite (с эмуляцией JSON)
    *   **Prod:** PostgreSQL (драйвер `asyncpg`)
*   **ORM:** Tortoise ORM
*   **AI/NLP:** OpenAI API (`gpt-4o-mini`) для анализа заметок.
*   **Environment:** `.env` для хранения секретов (`BOT_TOKEN`, `OPENAI_API_KEY`, `DATABASE_URL`).
*   **Containerization:** Docker Compose (PostgreSQL).

## Архитектура проекта

### Структура директорий
```text
project/
├── bot.py                 # Точка входа (entry point)
├── config.py              # Конфигурация и загрузка переменных окружения
├── docker-compose.yml     # Запуск PostgreSQL
├── database/
│   ├── db.py              # Инициализация Tortoise ORM
│   └── models.py          # Модели данных (User, Person, MeetingNote)
├── handlers/              # Обработчики команд и сообщений
│   ├── __init__.py
│   ├── common.py          # Общие команды (/start, /help)
│   ├── people.py          # Управление людьми (/add_person, /my_team)
│   └── notes.py           # Добавление и просмотр заметок
├── keyboards/             # Клавиатуры (inline, reply)
│   └── people_kb.py       # Клавиатуры для работы с людьми
├── middlewares/           # Миддлвари
├── services/              # Бизнес-логика и внешние интеграции
│   └── llm.py             # Интеграция с OpenAI (analyze_note)
└── utils/                 # Вспомогательные утилиты
```

## Модели данных

### User
Пользователь бота (Менеджер).
*   `id`: BigInt (PK, Telegram ID)
*   `username`: Char
*   `full_name`: Char
*   `created_at`: Datetime

### Person (Report/Context)
Сущность, к которой привязываются встречи.
*   `id`: Int (PK)
*   `user_id`: FK -> User
*   `name`: Char
*   `custom_prompt`: Text (Optional) — Индивидуальный промпт для AI-анализа.
*   `created_at`: Datetime
*   *Unique Constraint:* (user_id, name)

### MeetingNote
Запись о встрече.
*   `id`: UUID (PK)
*   `person_id`: FK -> Person
*   `raw_text`: Text (Исходный текст)
*   `ai_summary`: JSON (Результат анализа AI)
    *   `mood`: Int
    *   `summary`: Str
    *   `action_items`: List[Str]
    *   `tags`: List[Str]
*   `stress_level`: Int (Optional, дублирует mood из JSON для быстрого доступа)
*   `created_at`: Datetime

## Потоки данных (Data Flow)

1.  **Ввод заметки:**
    User -> Handler (`notes.py`) -> LLM Service (`llm.py`) -> OpenAI API -> JSON Result -> Database -> User (Formatted Message).

2.  **Аналитика (AI):**
    Вход: Текст заметки + System Prompt (Default или Custom).
    Выход: JSON с полями mood, summary, action_items.

## Развертывание
*   Локально для разработки: `python bot.py` (использует SQLite по умолчанию).
*   С PostgreSQL: Запустить `docker-compose up -d`, раскомментировать `DATABASE_URL` в `config.py`.
