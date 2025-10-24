# docker/autoscaler/Dockerfile

FROM python:3.11-slim

WORKDIR /app

# Встановлюємо залежності
RUN pip install redis docker

# Копіюємо наш скрипт
COPY autoscaler.py .

# Запускаємо скрипт
CMD ["python", "autoscaler.py"]