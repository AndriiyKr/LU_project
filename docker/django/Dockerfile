# docker/django/Dockerfile

# --- Етап 1: Встановлення залежностей ---
FROM python:3.11-slim as builder

WORKDIR /usr/src/app

# Встановлюємо системні залежності
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Встановлюємо Poetry (кращий менеджер, ніж pip)
# RUN pip install poetry
# COPY poetry.lock pyproject.toml /usr/src/app/
# RUN poetry config virtualenvs.create false && \
#     poetry install --no-root --no-dev

# Або по-старому з requirements.txt
COPY backend/requirements.txt /usr/src/app/
RUN pip wheel --no-cache-dir --wheel-dir /usr/src/app/wheels -r requirements.txt

# --- Етап 2: Фінальний образ ---
FROM python:3.11-slim

WORKDIR /usr/src/app

# Встановлюємо системні залежності, потрібні для запуску
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Копіюємо "колеса" Python з білдера
COPY --from=builder /usr/src/app/wheels /wheels
COPY --from=builder /usr/src/app/requirements.txt .
RUN pip install --no-cache /wheels/*

# Створюємо користувача без прав root
RUN addgroup --system app && adduser --system --group app
RUN chown -R app:app /usr/src/app

# Копіюємо код нашого backend
COPY ./backend /usr/src/app/

# Налаштовуємо права на директорії, куди Django буде писати
RUN mkdir -p /usr/src/app/staticfiles && \
    mkdir -p /usr/src/app/mediafiles && \
    chown -R app:app /usr/src/app/staticfiles && \
    chown -R app:app /usr/src/app/mediafiles

USER app

# Відкриваємо порт, який буде слухати Daphne
EXPOSE 8000

# За замовчуванням запускаємо Daphne
# Команда буде перевизначена в docker-compose.prod.yml
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "backend_project.asgi:application"]