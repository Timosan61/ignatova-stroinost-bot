FROM python:3.12-slim

# FORCE REBUILD - WORKING VERSION: 2025-06-18-v8-FINAL
# Cache bust timestamp: 2025-06-18T17:45:00Z
ARG CACHE_BUST=2025-06-18-v8

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файл зависимостей
COPY requirements.txt .

# Обновляем pip и устанавливаем зависимости
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь проект
COPY . .

# Создаем директорию для логов
RUN mkdir -p /app/logs

# Устанавливаем переменную окружения для Python
ENV PYTHONPATH=/app

# Запускаем бота
CMD ["python", "-m", "uvicorn", "webhook:app", "--host", "0.0.0.0", "--port", "$PORT"]