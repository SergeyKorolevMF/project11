from tortoise import Tortoise
import os

async def init_db():
    # В MVP используем SQLite файл db.sqlite3
    await Tortoise.init(
        db_url='sqlite://db.sqlite3',
        modules={'models': ['database.models']}
    )
    # Генерация схемы (таблиц) при старте. 
    # В продакшене лучше использовать миграции (aerich), но для MVP так проще.
    await Tortoise.generate_schemas()

async def close_db():
    await Tortoise.close_connections()
