# backend/backend_project/urls.py

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/users/', include('apps.users.urls', namespace='users')),
    path('api/tasks/', include('apps.tasks_app.urls', namespace='tasks_app')),
    path('api/monitoring/', include('apps.monitoring.urls', namespace='monitoring')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)