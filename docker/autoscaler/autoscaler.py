# docker/autoscaler/autoscaler.py

import os
import time
import redis
import docker
from docker.errors import DockerException

# --- Налаштування з .env ---
REDIS_HOST = os.environ.get('REDIS_HOST', 'redis')
REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))
CELERY_QUEUE_NAME = os.environ.get('CELERY_QUEUE_NAME', 'celery')
SERVICE_TO_SCALE = os.environ.get('SERVICE_TO_SCALE') # Напр. 'lu-stack_celery_worker'
MIN_REPLICAS = int(os.environ.get('MIN_REPLICAS', 1))
MAX_REPLICAS = int(os.environ.get('MAX_REPLICAS', 10))
TASKS_PER_WORKER = int(os.environ.get('TASKS_PER_WORKER', 5))
SLEEP_TIME = int(os.environ.get('SLEEP_TIME', 15)) # Перевіряти кожні 15 сек

def get_queue_length(r):
    """Отримує довжину черги Celery."""
    try:
        return r.llen(CELERY_QUEUE_NAME)
    except Exception as e:
        print(f"Помилка підключення до Redis: {e}")
        return None

def get_current_replicas(client, service_name):
    """Отримує поточну кількість реплік сервісу."""
    try:
        service = client.services.get(service_name)
        replicas = service.attrs['Spec']['Mode']['Replicated']['Replicas']
        return replicas
    except docker.errors.NotFound:
        print(f"Помилка: Сервіс '{service_name}' не знайдено.")
        return None
    except Exception as e:
        print(f"Помилка отримання реплік: {e}")
        return None

def scale_service(client, service_name, new_replicas):
    """Масштабує сервіс до new_replicas."""
    try:
        service = client.services.get(service_name)
        print(f"Масштабування {service_name} до {new_replicas} реплік...")
        service.scale(new_replicas)
        return True
    except Exception as e:
        print(f"Помилка масштабування: {e}")
        return False

def main():
    if not SERVICE_TO_SCALE:
        print("Помилка: Не вказано SERVICE_TO_SCALE. Встановіть змінну середовища.")
        return

    print("--- Запуск сервісу Авто-масштабування ---")
    print(f"Ціль: {SERVICE_TO_SCALE}")
    print(f"Ліміти: {MIN_REPLICAS} (min) - {MAX_REPLICAS} (max)")
    print(f"Тригер: {TASKS_PER_WORKER} задач на 1 воркер")
    
    try:
        redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)
        redis_client.ping()
        print("Підключено до Redis.")
    except Exception as e:
        print(f"Не вдалося підключитися до Redis: {e}")
        return

    try:
        docker_client = docker.from_env()
        docker_client.ping()
        print("Підключено до Docker Socket.")
    except DockerException:
        print("Помилка: Не вдалося підключитися до Docker socket.")
        print("Переконайтеся, що /var/run/docker.sock змонтовано у контейнер.")
        return
    except Exception as e:
        print(f"Невідома помилка Docker: {e}")
        return

    while True:
        queue_len = get_queue_length(redis_client)
        if queue_len is None:
            time.sleep(SLEEP_TIME)
            continue
            
        current_replicas = get_current_replicas(docker_client, SERVICE_TO_SCALE)
        if current_replicas is None:
            time.sleep(SLEEP_TIME)
            continue

        # --- Логіка масштабування ---
        # 1. Розраховуємо, скільки воркерів нам ПОТРІБНО
        # (додаємо +1, якщо є хоча б 1 задача, щоб почати обробку)
        if queue_len == 0:
            desired_replicas = MIN_REPLICAS
        else:
            desired_replicas = (queue_len // TASKS_PER_WORKER) + 1
            
        # 2. Обмежуємо лімітами
        new_replicas = max(MIN_REPLICAS, min(desired_replicas, MAX_REPLICAS))

        print(f"Черга: {queue_len} задач. Поточні воркери: {current_replicas}. Бажані: {new_replicas}.")

        # 3. Якщо кількість не збігається - масштабуємо
        if new_replicas != current_replicas:
            scale_service(docker_client, SERVICE_TO_SCALE, new_replicas)
        
        time.sleep(SLEEP_TIME)

if __name__ == "__main__":
    main()