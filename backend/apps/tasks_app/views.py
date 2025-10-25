# backend/apps/tasks_app/views.py

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.http import FileResponse, Http404
from celery.result import AsyncResult
from .models import Task, TaskProgress, TaskLog
from .serializers import (
    TaskCreateSerializer, TaskListSerializer, TaskDetailSerializer,
    TaskProgressSerializer, TaskLogSerializer
)
from .tasks import run_lu_task, parse_and_prepare_task_data
from config.celery import app as celery_app

# -------------------------------------------------------------
# Створення (POST) та Список (GET) задач
# -------------------------------------------------------------
class TaskListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return TaskCreateSerializer
        return TaskListSerializer

    def get_queryset(self):
        # Користувач бачить лише свої задачі
        return Task.objects.filter(owner=self.request.user).order_by('-created_at')

    def perform_create(self, serializer):
        # 1. Отримуємо дані
        source_file_obj = serializer.validated_data.pop('source_file', None) 
        matrix_text = serializer.validated_data.pop('matrix_text', None)

        # 2. Створюємо задачу
        task = serializer.save(owner=self.request.user, status=Task.Status.PENDING)
        task.update_progress("Очікування парсингу", 1)
        
        source_file_content = None
        if source_file_obj:
            try:
                source_file_content = source_file_obj.read().decode('utf-8')
            except Exception as e:
                task.mark_status(Task.Status.FAILED, f"Помилка читання файлу: {e}")
                # --- ДОДАЙТЕ ЦЕЙ РЯДОК ---
                # Негайно повертаємо помилку і НЕ запускаємо Celery
                return Response(
                    {"error": f"Не вдалося прочитати завантажений файл: {e}"},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # 4. Запускаємо парсинг у фоні
        # Передаємо task.id, source_file_content (який може бути None), matrix_text
        parse_and_prepare_task_data.delay(task.id, source_file_content, matrix_text) 

        # 5. Повертаємо відповідь
        # Переконуємось, що серіалізатор повертає id та uuid для редіректу
        return Response(TaskCreateSerializer(task).data, status=status.HTTP_201_CREATED)

# -------------------------------------------------------------
# Деталі задачі (GET)
# -------------------------------------------------------------
class TaskDetailView(generics.RetrieveAPIView):
    serializer_class = TaskDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'id'

    def get_queryset(self):
        if self.request.user.is_staff:
            return Task.objects.all()
        return Task.objects.filter(owner=self.request.user)

# -------------------------------------------------------------
# Скасування задачі (POST) (Пункт 3)
# -------------------------------------------------------------
class TaskCancelView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, id, *args, **kwargs):
        task = get_object_or_404(Task, id=id)

        # Перевіряємо, чи це власник задачі АБО адмін
        if not (task.owner == request.user or request.user.is_staff):
            return Response(
                {"error": "У вас немає дозволу на скасування цієї задачі."},
                status=status.HTTP_403_FORBIDDEN
            )

        if task.status not in [Task.Status.PENDING, Task.Status.QUEUED, Task.Status.RUNNING]:
            return Response(
                {"error": "Неможливо скасувати задачу зі статусом " + task.status},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Скасовуємо задачу в Celery
            if task.celery_task_id:
                celery_app.control.revoke(task.celery_task_id, terminate=True, signal='SIGTERM')

            # Скасовуємо, якщо вона ще на етапі парсингу (не має celery_task_id)
            task.mark_status(Task.Status.CANCELLED, "Задача скасована користувачем.")
            
            return Response({"message": "Запит на скасування задачі надіслано."}, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({"error": f"Помилка скасування: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# -------------------------------------------------------------
# Додаткові API для поллінгу (якщо WS не працює)
# -------------------------------------------------------------
class TaskProgressListView(generics.ListAPIView):
    serializer_class = TaskProgressSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        task_id = self.kwargs['id']
        task = get_object_or_404(Task, id=task_id, owner=self.request.user)
        return TaskProgress.objects.filter(task=task)

class TaskLogListView(generics.ListAPIView):
    serializer_class = TaskLogSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        task_id = self.kwargs['id']
        task = get_object_or_404(Task, id=task_id, owner=self.request.user)
        return TaskLog.objects.filter(task=task)

# -------------------------------------------------------------
# Завантаження результату (GET)
# -------------------------------------------------------------
class TaskDownloadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, id, *args, **kwargs):
        task = get_object_or_404(Task, id=id, owner=request.user)
        
        if not task.result_file or not task.result_file.storage.exists(task.result_file.name):
            raise Http404("Файл результату не знайдено.")

        # Повертаємо файл як відповідь
        response = FileResponse(task.result_file.open('rb'), as_attachment=True, filename='result_X.txt')
        return response