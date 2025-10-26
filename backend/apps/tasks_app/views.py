from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.http import FileResponse, Http404
from django.db.models import Q
from django.db import transaction 
from celery.result import AsyncResult
from .models import Task, TaskProgress, TaskLog
from .serializers import (
    TaskCreateSerializer, TaskListSerializer, TaskDetailSerializer,
    TaskProgressSerializer, TaskLogSerializer
)
from .tasks import parse_and_prepare_task_data, try_run_next_task_from_queue, run_lu_task
from config.celery import app as celery_app

MAX_ACTIVE_TASKS_PER_USER = 2
MAX_ACTIVE_TASKS_GLOBAL = 4

class TaskListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return TaskCreateSerializer
        return TaskListSerializer

    def get_queryset(self):
        return Task.objects.filter(owner=self.request.user).order_by('-created_at')

    def perform_create(self, serializer):
        user = self.request.user
        active_statuses = [Task.Status.PENDING, Task.Status.QUEUED, Task.Status.RUNNING]
        user_active_tasks = Task.objects.filter(owner=user, status__in=active_statuses).count()
        global_active_tasks = Task.objects.filter(status__in=active_statuses).count()
        initial_status = Task.Status.PENDING
        queue_message = None
        if user_active_tasks >= MAX_ACTIVE_TASKS_PER_USER:
            initial_status = Task.Status.QUEUED
            queue_message = f"Ви досягли ліміту ({MAX_ACTIVE_TASKS_PER_USER}) одночасно активних задач. Ваша задача додана в чергу."
        elif global_active_tasks >= MAX_ACTIVE_TASKS_GLOBAL:
            initial_status = Task.Status.QUEUED
            queue_message = f"Система зараз завантажена (ліміт {MAX_ACTIVE_TASKS_GLOBAL} активних задач). Ваша задача додана в чергу."

        source_file_obj = serializer.validated_data.pop('source_file', None)
        matrix_text = serializer.validated_data.pop('matrix_text', None)
        task = serializer.save(owner=user, status=initial_status)
        source_file_content = None
        if source_file_obj:
            try:
                source_file_content = source_file_obj.read().decode('utf-8')
            except Exception as e:
                task.mark_status(Task.Status.FAILED, f"Помилка читання файлу: {e}")
                return Response({"error": f"Не вдалося прочитати завантажений файл: {e}"}, status=status.HTTP_400_BAD_REQUEST)
        parse_and_prepare_task_data.delay(task.id, source_file_content, matrix_text)

        if initial_status == Task.Status.QUEUED:
            task.refresh_from_db() 
            response_data = TaskDetailSerializer(task).data
            response_data['queue_message'] = queue_message
            return Response(response_data, status=status.HTTP_201_CREATED)
        else: 
            task.update_progress("Очікування парсингу", 1)
            return Response(TaskCreateSerializer(task).data, status=status.HTTP_201_CREATED)


class TaskDetailView(generics.RetrieveAPIView):
    serializer_class = TaskDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'id'
    def get_queryset(self):
        if self.request.user.is_staff: return Task.objects.all()
        return Task.objects.filter(owner=self.request.user)

class TaskCancelView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request, id, *args, **kwargs):
        task = get_object_or_404(Task, id=id)
        if not (task.owner == request.user or request.user.is_staff):
            return Response({"error": "У вас немає дозволу на скасування цієї задачі."}, status=status.HTTP_403_FORBIDDEN)
        previous_status = task.status
        if previous_status not in [Task.Status.PENDING, Task.Status.QUEUED, Task.Status.RUNNING]:
            return Response({"error": "Неможливо скасувати задачу зі статусом " + previous_status}, status=status.HTTP_400_BAD_REQUEST)
        try:
            if task.celery_task_id and previous_status == Task.Status.RUNNING:
                celery_app.control.revoke(task.celery_task_id, terminate=True, signal='SIGTERM')
                print(f"Sent revoke signal for Celery task {task.celery_task_id}")
            task.mark_status(Task.Status.CANCELLED, "Задача скасована користувачем.")
            if previous_status in [Task.Status.RUNNING, Task.Status.QUEUED, Task.Status.PENDING]:
                print(f"Task {id} cancelled from status {previous_status}. Triggering queue check.")
                try_run_next_task_from_queue.delay()
            return Response({"message": "Запит на скасування задачі виконано."}, status=status.HTTP_200_OK)

        except Exception as e:
            print(f"Error during task cancellation for {id}: {e}")
            return Response({"error": f"Помилка скасування: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class TaskProgressListView(generics.ListAPIView):
    serializer_class = TaskProgressSerializer
    permission_classes = [permissions.IsAuthenticated]
    def get_queryset(self):
        task_id = self.kwargs['id']
        if self.request.user.is_staff: task = get_object_or_404(Task, id=task_id)
        else: task = get_object_or_404(Task, id=task_id, owner=self.request.user)
        return TaskProgress.objects.filter(task=task)

class TaskLogListView(generics.ListAPIView):
    serializer_class = TaskLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    def get_queryset(self):
        task_id = self.kwargs['id']
        if self.request.user.is_staff: task = get_object_or_404(Task, id=task_id)
        else: task = get_object_or_404(Task, id=task_id, owner=self.request.user)
        return TaskLog.objects.filter(task=task)

class TaskDownloadView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request, id, *args, **kwargs):
        if request.user.is_staff: task = get_object_or_404(Task, id=id)
        else: task = get_object_or_404(Task, id=id, owner=request.user)
        if not task.result_file or not task.result_file.storage.exists(task.result_file.name):
            return Response({"detail": "Файл результату не знайдено або ще не створений."}, status=status.HTTP_404_NOT_FOUND)
        try:
            response = FileResponse(task.result_file.open('rb'), as_attachment=True, filename='result_X.txt')
            return response
        except Exception as e:
            return Response({"detail": f"Помилка при відкритті файлу результату: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)