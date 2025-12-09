import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from config import BOT_TOKEN
from database.db import init_db, close_db
from handlers import common

# Настройка логирования
logging.basicConfig(level=logging.INFO, stream=sys.stdout)

async def main():
    # Инициализация бота
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    # Регистрация роутеров
    dp.include_router(common.router)

    # Инициализация БД
    await init_db()
    logging.info("Database initialized")

    try:
        # Запуск поллинга
        logging.info("Starting bot...")
        await dp.start_polling(bot)
    finally:
        # Закрытие соединения с БД при остановке
        await close_db()
        logging.info("Database connection closed")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped!")

