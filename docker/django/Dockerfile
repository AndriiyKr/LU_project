FROM python:3.11-slim as builder

WORKDIR /usr/src/app

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /usr/src/app/
RUN pip wheel --no-cache-dir --wheel-dir /usr/src/app/wheels -r requirements.txt

FROM python:3.11-slim

WORKDIR /usr/src/app

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /usr/src/app/wheels /wheels
COPY --from=builder /usr/src/app/requirements.txt .
RUN pip install --no-cache /wheels/*

RUN addgroup --system app && adduser --system --group app
RUN chown -R app:app /usr/src/app

COPY ./backend /usr/src/app/

RUN mkdir -p /usr/src/app/staticfiles && \
    mkdir -p /usr/src/app/mediafiles && \
    chown -R app:app /usr/src/app/staticfiles && \
    chown -R app:app /usr/src/app/mediafiles

USER app

EXPOSE 8000

CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "backend_project.asgi:application"]