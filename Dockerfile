FROM python:3.12-alpine3.22

WORKDIR /opt/app

# Копирование файлов зависимостей
COPY requirements.txt ./main.py /opt/app/

# Установка Python зависимостей
RUN pip install --no-cache-dir -r requirements.txt && \
  adduser --disabled-password fastapi  && chown -R fastapi:fastapi /opt/app

USER fastapi

# Порт приложения
EXPOSE 8000

# Запуск приложения
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]