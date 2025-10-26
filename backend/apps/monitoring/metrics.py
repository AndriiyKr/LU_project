# backend/apps/monitoring/metrics.py

import psutil
from apps.tasks_app.models import Task
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
from django.contrib.auth import get_user_model


def get_system_metrics():
    # Навантаження CPU
    cpu_percent = psutil.cpu_percent(interval=None)

    # Використання RAM
    memory = psutil.virtual_memory()
    ram_total_mb = memory.total / (1024 * 1024)
    ram_used_mb = memory.used / (1024 * 1024)
    ram_percent = memory.percent

    return {
        "cpu_percent": cpu_percent,
        "ram_total_mb": ram_total_mb,
        "ram_used_mb": ram_used_mb,
        "ram_percent": ram_percent,
    }

def get_task_metrics():
    active_tasks = Task.objects.filter(status__in=[Task.Status.RUNNING, Task.Status.QUEUED]).count()
    completed_last_24h = Task.objects.filter(
        status=Task.Status.COMPLETED,
        completed_at__gte=timezone.now() - timedelta(days=1)
    ).count()
    failed_last_24h = Task.objects.filter(
        status=Task.Status.FAILED,
        completed_at__gte=timezone.now() - timedelta(days=1)
    ).count()

    return {
        "active_tasks": active_tasks,
        "completed_last_24h": completed_last_24h,
        "failed_last_24h": failed_last_24h,
    }
    
def get_user_metrics():
    """Рахує загальну кількість користувачів."""
    User = get_user_model()
    total_users = User.objects.count()
    return {
        "total_users": total_users,
    }