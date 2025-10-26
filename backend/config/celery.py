# backend/config/celery.py

import os
from celery import Celery

# Встановлюємо модуль налаштувань Django за замовчуванням
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend_project.settings')

app = Celery('backend_project')

# Використовуємо налаштування з Django
app.config_from_object('django.conf:settings', namespace='CELERY')

# Автоматично знаходимо файли tasks.py у всіх додатках
app.autodiscover_tasks()