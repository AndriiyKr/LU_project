# backend/apps/monitoring/views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from django.conf import settings # Додано
from rest_framework import generics
# Ось виправлений імпорт:
from .metrics import get_system_metrics, get_task_metrics, get_user_metrics
from apps.tasks_app.models import Task # <--- ДОДАЙТЕ ЦЕЙ ІМПОРТ
from apps.tasks_app.serializers import TaskListSerializer
from config.celery import app as celery_app

class MonitoringMetricsView(APIView):
    """
    API для панелі адміністратора (Пункт 8).
    Доступно лише для персоналу (is_staff=True).
    """
    permission_classes = [IsAdminUser]

    def get(self, request, *args, **kwargs):
        system_metrics = get_system_metrics()
        task_metrics = get_task_metrics()
        user_metrics = get_user_metrics()

        # --- ОТРИМУЄМО КІЛЬКІСТЬ ВОРКЕРІВ ---
        active_workers_count = 0
        try:
            # Спробуємо "пінганути" активні воркери
            inspector = celery_app.control.inspect()
            ping_result = inspector.ping()
            if ping_result:
                # ping() повертає словник {worker_name: {'ok': 'pong'}},
                # нам потрібна лише кількість ключів (воркерів)
                active_workers_count = len(ping_result)
        except Exception as e:
            # Можливо, Redis недоступний або немає активних воркерів
            print(f"Помилка отримання кількості воркерів Celery: {e}")
            active_workers_count = 0 # Показуємо 0 у разі помилки
        # --- КІНЕЦЬ ---

        return Response({
            "system": system_metrics,
            "tasks": task_metrics,
            "users": user_metrics,
            "workers": {
                # --- ВИКОРИСТОВУЄМО ОТРИМАНЕ ЗНАЧЕННЯ ---
                "count": active_workers_count,
                # --- КІНЕЦЬ ---
                "max_replicas": settings.MAX_WORKER_REPLICAS,
            }
        })
        
class AdminTaskListView(generics.ListAPIView):
    """
    API для адміна: повертає список ВСІХ задач в системі.
    """
    permission_classes = [IsAdminUser]
    serializer_class = TaskListSerializer
    
    def get_queryset(self):
        # Адмін бачить всі задачі, відсортовані за датою
        return Task.objects.all().order_by('-created_at')