# backend/backend_project/urls.py

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Адмін-панель Django
    path('admin/', admin.site.urls),

    # API для користувачів (логін, реєстрація)
    path('api/users/', include('apps.users.urls', namespace='users')),
    
    # API для задач (створення, історія, прогрес)
    path('api/tasks/', include('apps.tasks_app.urls', namespace='tasks_app')),

    # API для моніторингу (Пункт 8)
    path('api/monitoring/', include('apps.monitoring.urls', namespace='monitoring')),
]

# Додаємо обслуговування медіа-файлів (завантажені матриці) в режимі DEBUG
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)