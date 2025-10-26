from datetime import timedelta
import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone
import os
from django.db.models import Q

def task_upload_path(instance, filename):
    return f'tasks/{instance.uuid}/{filename}'

class Task(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'В очікуванні'
        QUEUED = 'queued', 'В черзі'
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
    matrix_file = models.FileField(upload_to=task_upload_path, blank=True, null=True, help_text="Файл з матрицею A")
    vector_file = models.FileField(upload_to=task_upload_path, blank=True, null=True, help_text="Файл з вектором b")
    matrix_size = models.IntegerField(blank=True, null=True, help_text="Розмірність матриці (N)")
    max_n = models.IntegerField(default=settings.MAX_MATRIX_N_SIZE, help_text="Макс. допустимий розмір N")
    save_matrices = models.BooleanField(default=False, help_text="Зберегти L, U, P матриці?")
    result_file = models.FileField(upload_to=task_upload_path, blank=True, null=True, help_text="Файл з результатом (вектор X)")
    result_message = models.TextField(blank=True, null=True, help_text="Повідомлення про помилку або успіх")
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    def __str__(self):
        return f'Task {self.id} ({self.status}) by {self.owner.username}'
    def mark_status(self, status, message=None):
        self.status = status
        if status == self.Status.RUNNING and not self.started_at:
            self.started_at = timezone.now()
        elif status in [self.Status.COMPLETED, self.Status.FAILED, self.Status.CANCELLED] and not self.completed_at:
            self.completed_at = timezone.now()
        if message is not None:
            self.result_message = message
        update_fields = ['status']
        if self.started_at: update_fields.append('started_at')
        if self.completed_at: update_fields.append('completed_at')
        if message is not None: update_fields.append('result_message')

        self.save(update_fields=update_fields)
        self.send_websocket_update()

    def update_progress(self, stage, percentage):
        TaskProgress.objects.create(task=self, stage=stage, percentage=percentage)
        self.send_websocket_update(stage=stage, percentage=percentage)

    def get_progress(self):
        last_progress = self.progress_updates.last()
        if last_progress:
            return {"stage": last_progress.stage, "percentage": last_progress.percentage}
        if self.status == Task.Status.PENDING: return {"stage": "Очікування парсингу", "percentage": 0}
        if self.status == Task.Status.QUEUED: return {"stage": "В черзі", "percentage": 0}
        return {"stage": "Ініціалізація", "percentage": 0}

    def add_log(self, message, level="INFO"):
        TaskLog.objects.create(task=self, message=message, level=level)
        self.send_websocket_update(log_message=message)

    def send_websocket_update(self, **kwargs):
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
            'matrix_size': self.matrix_size,
            'queue_position': self.get_queue_position() if self.status in [self.Status.QUEUED, self.Status.PENDING] else None,
            'estimated_wait_time_sec': self.get_estimated_wait_time() if self.status in [self.Status.QUEUED, self.Status.PENDING] else None,
        }
        async_to_sync(channel_layer.group_send)(group_name, data)

    def get_queue_position(self):
        if self.status not in [self.Status.QUEUED, self.Status.PENDING]:
            return None
        queued_tasks_before = Task.objects.filter(
            Q(status=Task.Status.QUEUED) | Q(status=Task.Status.PENDING),
            created_at__lt=self.created_at
        ).count()
        return queued_tasks_before + 1

    def get_estimated_wait_time(self):
        position = self.get_queue_position()
        if position is None or position <= 0:
            return 0
        avg_duration = Task.objects.filter(
            status=self.Status.COMPLETED,
            completed_at__isnull=False,
            started_at__isnull=False
        ).aggregate(
            avg_duration=models.Avg(models.F('completed_at') - models.F('started_at'))
        )['avg_duration']
        if not avg_duration or avg_duration.total_seconds() <= 0:
            avg_duration = timedelta(minutes=1)
        active_workers = max(1, settings.MAX_ACTIVE_TASKS_GLOBAL)
        wait_cycles = (position - 1) // active_workers
        wait_time_seconds = wait_cycles * avg_duration.total_seconds()
        wait_time_seconds += (avg_duration.total_seconds() / active_workers) * ((position - 1) % active_workers)
        return round(wait_time_seconds)


class TaskProgress(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='progress_updates')
    stage = models.CharField(max_length=100)
    percentage = models.FloatField()
    timestamp = models.DateTimeField(auto_now_add=True)
    class Meta: ordering = ['timestamp']

class TaskLog(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='logs')
    timestamp = models.DateTimeField(auto_now_add=True)
    level = models.CharField(max_length=20, default="INFO")
    message = models.TextField()
    class Meta: ordering = ['timestamp']