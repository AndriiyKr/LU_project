from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from django.conf import settings 
from rest_framework import generics
from .metrics import get_system_metrics, get_task_metrics, get_user_metrics
from apps.tasks_app.models import Task 
from apps.tasks_app.serializers import TaskListSerializer
from config.celery import app as celery_app
import socket 

class MonitoringMetricsView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, *args, **kwargs):
        system_metrics = get_system_metrics() 
        task_metrics = get_task_metrics()
        user_metrics = get_user_metrics()
        active_workers_count = 0
        try:
            inspector = celery_app.control.inspect()
            ping_result = inspector.ping()
            if ping_result:
                active_workers_count = len(ping_result)
        except Exception as e:
            print(f"Помилка отримання кількості воркерів Celery: {e}")
            active_workers_count = 0
        return Response({
            "system": system_metrics,
            "tasks": task_metrics,
            "users": user_metrics,
            "workers": {
                "count": active_workers_count,
                "max_replicas": settings.MAX_WORKER_REPLICAS,
            }
        })

class AdminTaskListView(generics.ListAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = TaskListSerializer
    def get_queryset(self):
        return Task.objects.all().order_by('-created_at')