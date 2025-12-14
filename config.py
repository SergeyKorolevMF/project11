import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# AICODE-NOTE: Временно используем SQLite для разработки без Docker.
# Для продакшена раскомментировать Postgres URL и использовать его.
# DATABASE_URL = os.getenv("DATABASE_URL", "postgres://vibe_user:vibe_password@localhost:5432/vibe_tracker")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite://db.sqlite3")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is not set in .env")
