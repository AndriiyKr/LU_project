from celery import shared_task, Task as CeleryTask
from celery.exceptions import SoftTimeLimitExceeded
from django.conf import settings
from django.core.files.base import ContentFile
import numpy as np
import os
import io
import time
from datetime import timedelta
from django.db import transaction 
from django.db.models import Q 
from .models import Task
from .lu_solver import solve_lu_system

@shared_task(ignore_result=True)
def try_run_next_task_from_queue():
    try:
        running_tasks_count = Task.objects.filter(status=Task.Status.RUNNING).count()

        if running_tasks_count < settings.MAX_ACTIVE_TASKS_GLOBAL:
            with transaction.atomic():
                task_to_run = Task.objects.select_for_update(skip_locked=True).filter(
                    status=Task.Status.QUEUED
                ).order_by('created_at').first()

                if task_to_run:
                    print(f"Slot available ({running_tasks_count}/{settings.MAX_ACTIVE_TASKS_GLOBAL}). Triggering run_lu_task for task {task_to_run.id}")
                    run_lu_task.delay(task_to_run.id)
    except Exception as e:
        print(f"Error in try_run_next_task_from_queue: {e}")

@shared_task(bind=True)
def parse_and_prepare_task_data(self, task_id, source_file_content=None, matrix_text=None):
    task = None
    try:
        task = Task.objects.get(id=task_id)

        if task.status == Task.Status.CANCELLED:
            print(f"Task {task_id} was cancelled before parsing started.")
            return "Task cancelled before parsing."
        task.update_progress("Парсинг вхідних даних", 5)
        data_string = None
        if source_file_content: data_string = source_file_content
        elif matrix_text: data_string = matrix_text
        else: raise ValueError("Не надано ані вмісту файлу, ані тексту матриці.")
        string_io = io.StringIO(data_string)
        try:
            full_matrix = np.loadtxt(string_io, dtype=np.float64, ndmin=2)
        except Exception as e:
            line_preview = data_string.split('\n', 1)[0][:80]
            raise ValueError(f"Помилка читання даних... Початок: '{line_preview}...'. Деталі: {e}")
        if full_matrix.ndim != 2: raise ValueError("Вхідні дані не вдалося перетворити на 2D матрицю.")
        n_rows, n_cols = full_matrix.shape
        if n_cols <= 1: raise ValueError(f"Матриця має мати щонайменше 2 стовпці... Отримано: {n_cols}.")
        matrix_n = n_rows
        if matrix_n != (n_cols - 1): raise ValueError(f"Матриця A має бути квадратною... Отримано {n_rows}x{n_cols-1}.")
        if matrix_n > task.max_n: raise ValueError(f"Розмір матриці ({matrix_n}) перевищує ліміт ({task.max_n}).")
        A = full_matrix[:, :-1]
        b = full_matrix[:, -1]
        task_dir = os.path.join(settings.MEDIA_ROOT, "tasks", str(task.uuid))
        os.makedirs(task_dir, exist_ok=True)
        matrix_path = os.path.join(task_dir, "A.txt")
        vector_path = os.path.join(task_dir, "b.txt")
        np.savetxt(matrix_path, A, fmt='%.18e')
        np.savetxt(vector_path, b, fmt='%.18e')
        rel_matrix_path = os.path.relpath(matrix_path, settings.MEDIA_ROOT)
        rel_vector_path = os.path.relpath(vector_path, settings.MEDIA_ROOT)
        task.matrix_file.name = rel_matrix_path
        task.vector_file.name = rel_vector_path
        task.matrix_size = matrix_n
        task.status = Task.Status.QUEUED
        task.save(update_fields=['matrix_file', 'vector_file', 'matrix_size', 'status'])
        task.update_progress("Готово до обчислення (в черзі)", 10)
        task.add_log("Парсинг даних успішно завершено.")
        try_run_next_task_from_queue.delay()
        return f"Parsing successful for task {task_id}"

    except Exception as e:
        error_message = f"Помилка парсингу для задачі ID {task_id}: {str(e)}"
        if task and task.status != Task.Status.CANCELLED:
                task.mark_status(Task.Status.FAILED, error_message)
                task.add_log(error_message, level="ERROR")
                try_run_next_task_from_queue.delay()
        elif not task: print(f"CRITICAL PARSING ERROR (task object unavailable): {error_message}")
        return f"Parsing failed for task {task_id}: {error_message}"

class LuSolverTask(CeleryTask):
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        task_id_from_args = args[0] if args else None
        if not task_id_from_args:
            print(f"CRITICAL ERROR: Could not get task_id from args in on_failure. Args: {args}")
            try_run_next_task_from_queue.delay()
            return
        try:
            task = Task.objects.get(id=task_id_from_args)
            if task.status not in [Task.Status.COMPLETED, Task.Status.FAILED, Task.Status.CANCELLED]:
                error_msg = f"Непередбачувана помилка воркера: {exc}"
                task.mark_status(Task.Status.FAILED, error_msg) 
                task.add_log(f"Traceback: {einfo}", level="ERROR")
            else:
                print(f"Task {task_id_from_args} already has a final status ({task.status}). Failure log: {exc}")
        except Task.DoesNotExist:
            print(f"CRITICAL ERROR: Task with id {task_id_from_args} not found in on_failure.")
        except Exception as e:
            print(f"CRITICAL ERROR: Error during on_failure for task {task_id_from_args}: {e}")
        try_run_next_task_from_queue.delay() 
    def on_success(self, retval, task_id, args, kwargs):
        try_run_next_task_from_queue.delay()

@shared_task(
    bind=True,
    base=LuSolverTask,
    soft_time_limit=settings.CELERY_TASK_TIME_LIMIT,
    time_limit=settings.CELERY_TASK_TIME_LIMIT + 60
)
def run_lu_task(self, task_id):
    task = None
    try:
        with transaction.atomic():
            task = Task.objects.select_for_update().get(id=task_id)
            if task.status == Task.Status.CANCELLED:
                print(f"Task {task_id} was cancelled before execution started.")
                return "Task was cancelled."
            if task.status != Task.Status.QUEUED:
                print(f"Task {task_id} has status {task.status} (expected QUEUED). Skipping execution.")
                return f"Task {task_id} has unexpected status {task.status}."
            running_tasks_count = Task.objects.filter(status=Task.Status.RUNNING).count()
            if running_tasks_count >= settings.MAX_ACTIVE_TASKS_GLOBAL:
                print(f"Task {task_id} hit limit just before starting ({running_tasks_count}/{settings.MAX_ACTIVE_TASKS_GLOBAL}). Re-queueing slightly.")
                self.retry(countdown=5 + np.random.randint(0, 5), max_retries=None)
                return f"Task {task_id} re-queued due to limit."
            print(f"Starting task {task_id}. Setting status to RUNNING.")
            task.celery_task_id = self.request.id
            task.mark_status(Task.Status.RUNNING, "Задача прийнята воркером. Початок обчислень.") 
            task.save(update_fields=['celery_task_id'])
        def progress_callback(stage, percentage):
            try:
                task.refresh_from_db(fields=['status'])
                if task.status == Task.Status.CANCELLED:
                    print(f"Task {task_id} cancelled during execution, stopping progress updates.")
                    raise InterruptedError("Task was cancelled") 
                task.update_progress(stage, percentage)
                if percentage == 0 or percentage == 100 or int(percentage) % 10 == 0:
                    task.add_log(f"Етап: {stage} ({percentage:.0f}%)")
            except Task.DoesNotExist:
                print(f"Warning: Task {task_id} not found during progress update callback.")
            except InterruptedError:
                raise
        task.add_log("Завантаження матриці A та вектора b...")
        if not task.matrix_file or not task.vector_file or not task.matrix_file.name or not task.vector_file.name:
            raise FileNotFoundError("Шляхи до файлів матриці або вектора не визначені в задачі.")
        matrix_path = os.path.join(settings.MEDIA_ROOT, task.matrix_file.name)
        vector_path = os.path.join(settings.MEDIA_ROOT, task.vector_file.name)
        if not os.path.exists(matrix_path) or not os.path.exists(vector_path):
            raise FileNotFoundError(f"Файл не знайдено за шляхом: {matrix_path} або {vector_path}")
        result_vector, files_to_save = solve_lu_system(
            matrix_path,
            vector_path,
            progress_callback=progress_callback,
            save_matrices=task.save_matrices
        )
        task.refresh_from_db(fields=['status'])
        if task.status == Task.Status.CANCELLED:
            print(f"Task {task_id} was cancelled before saving results.")
            try_run_next_task_from_queue.delay()
            return "Task was cancelled before saving results."
        task.add_log("Збереження результату...")
        result_dir = os.path.dirname(matrix_path)
        result_path = os.path.join(result_dir, "result_X.txt")
        np.savetxt(result_path, result_vector, fmt='%.18e')
        rel_result_path = os.path.relpath(result_path, settings.MEDIA_ROOT)
        task.result_file.name = rel_result_path
        task.mark_status(Task.Status.COMPLETED, "Обчислення успішно завершено.")
        task.add_log("Задача виконана.")
        task.save(update_fields=['result_file'])
        return f"Task {task_id} completed successfully."
    except InterruptedError:
        print(f"Task {task_id} execution interrupted due to cancellation.")
        if task and task.status != Task.Status.CANCELLED:
            task.add_log("Виконання перервано (можливо, через скасування).", level="WARNING")
        try_run_next_task_from_queue.delay()
        return "Task execution interrupted."
    except SoftTimeLimitExceeded:
        if task and task.status not in [Task.Status.COMPLETED, Task.Status.FAILED, Task.Status.CANCELLED]:
            error_msg = f"Помилка: Перевищено ліміт часу виконання ({settings.CELERY_TASK_TIME_LIMIT} c)."
            task.mark_status(Task.Status.FAILED, error_msg) 
            task.add_log("Задача примусово зупинена через перевищення ліміту часу.", level="ERROR")
        elif not task: print(f"CRITICAL ERROR: Task {task_id} not found in SoftTimeLimitExceeded handler.")
        try_run_next_task_from_queue.delay()
        return f"Task {task_id} failed: Time limit exceeded."
    except FileNotFoundError as e:
        if task and task.status not in [Task.Status.COMPLETED, Task.Status.FAILED, Task.Status.CANCELLED]:
            task.mark_status(Task.Status.FAILED, f"Помилка: Файл не знайдено - {str(e)}") 
            task.add_log(f"Критична помилка: Не знайдено вхідний файл - {str(e)}", level="ERROR")
        elif not task: print(f"CRITICAL ERROR: Task {task_id} not found in FileNotFoundError handler.")
        try_run_next_task_from_queue.delay()
        return f"Task {task_id} failed: {str(e)}"

    except Exception as e:
        current_task_id = task.id if task else task_id
        if not task:
            try: task = Task.objects.get(id=current_task_id)
            except Task.DoesNotExist: pass
        if task and task.status not in [Task.Status.COMPLETED, Task.Status.FAILED, Task.Status.CANCELLED]:
            error_msg = f"Помилка під час виконання: {str(e)}"
            task.mark_status(Task.Status.FAILED, error_msg) 
            task.add_log(f"Критична помилка обчислення: {repr(e)}", level="ERROR")
        elif task:
            print(f"Task {current_task_id} already has final status ({task.status}). Encountered error: {repr(e)}")
        else:
            print(f"CRITICAL ERROR: Task {current_task_id} not found in generic Exception handler. Error: {repr(e)}")
        try_run_next_task_from_queue.delay()
        return f"Task {current_task_id} failed: {str(e)}"