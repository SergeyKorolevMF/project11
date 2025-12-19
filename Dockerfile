# Используем официальный легкий образ Python
FROM python:3.11-slim

# Установка системных зависимостей для сборки некоторых пакетов (если нужно)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Установка рабочей директории
WORKDIR /app

# Копирование и установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование всего проекта
COPY . .

# Команда для запуска бота
CMD ["python", "bot.py"]

