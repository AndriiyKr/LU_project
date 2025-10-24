# backend/backend_project/asgi.py

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import apps.tasks_app.routing  # Імпортуємо наші WebSocket-маршрути

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend_project.settings')

# Отримуємо стандартний Django ASGI application
django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter({
    # Для звичайних HTTP-запитів
    "http": django_asgi_app,

    # Для WebSocket-запитів
    "websocket": AuthMiddlewareStack(  # Додаємо аутентифікацію
        URLRouter(
            apps.tasks_app.routing.websocket_urlpatterns
        )
    ),
})