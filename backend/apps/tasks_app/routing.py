# backend/apps/tasks_app/routing.py

from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # Маршрут для підключення до конкретної задачі
    # ws/tasks/updates/<uuid:task_uuid>/
    re_path(
        r'ws/tasks/updates/(?P<task_uuid>[0-9a-f-]+)/$', 
        consumers.TaskProgressConsumer.as_asgi()
    ),
]