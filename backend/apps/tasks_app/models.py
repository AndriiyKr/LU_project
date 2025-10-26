# backend/apps/tasks_app/models.py

from datetime import timedelta
import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone
import os

def task_upload_path(instance, filename):
    # Файл буде завантажено в MEDIA_ROOT/tasks/<task_uuid>/<filename>
    return f'tasks/{instance.uuid}/{filename}'

class Task(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'В очікуванні'
        QUEUED = 'queued', 'В черзі' # Новий статус (Пункт 6)
        RUNNING = 'running', 'Виконується'
        COMPLETED = 'completed', 'Завершено'
        FAILED = 'failed', 'Помилка'
        CANCELLED = 'cancelled', 'Скасовано'

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='tasks')
    celery_task_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    
    name = models.CharField(max_length=255, default="Задача LU")
    description = models.TextField(blank=True, null=True)
    
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    
    # Вхідні дані
    matrix_file = models.FileField(upload_to=task_upload_path, blank=True, null=True, help_text="Файл з матрицею A")
    vector_file = models.FileField(upload_to=task_upload_path, blank=True, null=True, help_text="Файл з вектором b")
    matrix_size = models.IntegerField(blank=True, null=True, help_text="Розмірність матриці (N)")
    
    # Налаштування
    max_n = models.IntegerField(default=settings.MAX_MATRIX_N_SIZE, help_text="Макс. допустимий розмір N")
    save_matrices = models.BooleanField(default=False, help_text="Зберегти L, U, P матриці?")

    # Результати
    result_file = models.FileField(upload_to=task_upload_path, blank=True, null=True, help_text="Файл з результатом (вектор X)")
    result_message = models.TextField(blank=True, null=True, help_text="Повідомлення про помилку або успіх")
    
    # Час
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f'Task {self.id} ({self.status}) by {self.owner.username}'

    def mark_status(self, status, message=None):
        """Допоміжна функція для оновлення статусу та часу."""
        self.status = status
        if status == self.Status.RUNNING:
            self.started_at = timezone.now()
        elif status in [self.Status.COMPLETED, self.Status.FAILED, self.Status.CANCELLED]:
            self.completed_at = timezone.now()
        
        if message:
            self.result_message = message
        
        self.save(update_fields=['status', 'started_at', 'completed_at', 'result_message'])
        self.send_websocket_update() # Надсилаємо оновлення через WS

    def update_progress(self, stage, percentage):
        """Створює новий запис про прогрес."""
        TaskProgress.objects.create(task=self, stage=stage, percentage=percentage)
        self.send_websocket_update(stage=stage, percentage=percentage) # Надсилаємо оновлення через WS

    def get_progress(self):
        """Повертає останній прогрес."""
        last_progress = self.progress_updates.last()
        if last_progress:
            return {"stage": last_progress.stage, "percentage": last_progress.percentage}
        return {"stage": "Pending", "percentage": 0}

    def add_log(self, message, level="INFO"):
        """Додає лог до задачі."""
        TaskLog.objects.create(task=self, message=message, level=level)
        self.send_websocket_update(log_message=message) # Надсилаємо оновлення через WS

    def send_websocket_update(self, **kwargs):
        """Надсилає оновлення через WebSocket."""
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        
        channel_layer = get_channel_layer()
        group_name = f"task_{self.uuid}"
        
        progress = self.get_progress()

        data = {
            'type': 'task_update',
            'task_id': str(self.uuid),
            'status': self.status,
            'stage': kwargs.get('stage', progress.get('stage')),
            'percentage': kwargs.get('percentage', progress.get('percentage')),
            'log_message': kwargs.get('log_message'),
            'result_message': self.result_message,
        }
        
        async_to_sync(channel_layer.group_send)(group_name, data)
        
    def get_queue_position(self):
        """Отримує позицію в черзі (Пункт 6)."""
        if self.status not in [self.Status.QUEUED, self.Status.PENDING]:
            return None
        
        queued_tasks = Task.objects.filter(
            status__in=[self.Status.QUEUED, self.Status.PENDING],
            created_at__lt=self.created_at
        ).count()
        return queued_tasks + 1

    def get_estimated_wait_time(self):
        """Отримує приблизний час очікування (Пункт 6)."""
        position = self.get_queue_position()
        if position is None:
            return None
        
        # Розраховуємо середній час виконання
        avg_duration = Task.objects.filter(
            status=self.Status.COMPLETED,
            completed_at__isnull=False,
            started_at__isnull=False
        ).aggregate(
            avg_duration=models.Avg(models.F('completed_at') - models.F('started_at'))
        )['avg_duration']
        
        if not avg_duration:
            avg_duration = timedelta(minutes=5) # За замовчуванням, якщо немає даних

        # Отримуємо кількість активних воркерів (складно, беремо 1 для простоти)
        # TODO: Це можна покращити, якщо моніторинг знає кількість воркерів
        active_workers = 1 
        
        wait_time_seconds = (position / active_workers) * avg_duration.total_seconds()
        return round(wait_time_seconds)


class TaskProgress(models.Model):
    """Модель для зберігання історії прогресу (Пункт 2)."""
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='progress_updates')
    stage = models.CharField(max_length=100)
    percentage = models.FloatField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']

class TaskLog(models.Model):
    """Модель для логів виконання."""
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='logs')
    timestamp = models.DateTimeField(auto_now_add=True)
    level = models.CharField(max_length=20, default="INFO")
    message = models.TextField()

    class Meta:
        ordering = ['timestamp']