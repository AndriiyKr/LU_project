# backend/backend_project/wsgi.py

import os
from django.core.wsgi import get_wsgi_application

# Встановлюємо налаштування Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend_project.settings')

# Створюємо WSGI-додаток
application = get_wsgi_application()
