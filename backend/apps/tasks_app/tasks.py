# backend/apps/tasks_app/tasks.py

from celery import shared_task, Task as CeleryTask
from celery.exceptions import SoftTimeLimitExceeded
from django.conf import settings
from django.core.files.base import ContentFile
import numpy as np
import os
import io
import time

from .models import Task
from .lu_solver import solve_lu_system
from .utils import parse_and_save_input_data

# -------------------------------------------------------------
# Задача №1: Парсинг та підготовка
# -------------------------------------------------------------
@shared_task(bind=True)
def parse_and_prepare_task_data(self, task_id, source_file_content=None, matrix_text=None):
    task = None 
    try:
        task = Task.objects.get(id=task_id)

        # --- ВИПРАВЛЕННЯ: Оновлюємо статус на початку парсингу ---
        task.update_progress("Парсинг вхідних даних", 5)
        # --- КІНЕЦЬ ВИПРАВЛЕННЯ ---

        data_string = None # Змінна для зберігання рядка з даними

        if source_file_content:
            data_string = source_file_content 
        elif matrix_text:
            data_string = matrix_text
        else:
            raise ValueError("Не надано ані вмісту файлу, ані тексту матриці.")

        string_io = io.StringIO(data_string) 

        try:
            full_matrix = np.loadtxt(string_io, dtype=np.float64, ndmin=2) 
        except Exception as e:
            line_preview = data_string.split('\n', 1)[0][:80] 
            raise ValueError(f"Помилка читання даних... Початок: '{line_preview}...'. Деталі: {e}")

        if full_matrix.ndim != 2:
            raise ValueError("Вхідні дані не вдалося перетворити на 2D матрицю.")

        n_rows, n_cols = full_matrix.shape

        if n_cols <= 1:
            raise ValueError(f"Матриця має мати щонайменше 2 стовпці... Отримано: {n_cols}.")

        matrix_n = n_rows

        if matrix_n != (n_cols - 1):
            raise ValueError(f"Матриця A має бути квадратною... Отримано {n_rows}x{n_cols-1}.")

        if matrix_n > task.max_n:
            raise ValueError(f"Розмір матриці ({matrix_n}) перевищує ліміт ({task.max_n}).")

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

        # --- ВИПРАВЛЕННЯ: Зберігаємо результат парсингу в моделі та запускаємо наступний крок ---
        task.matrix_file.name = rel_matrix_path
        task.vector_file.name = rel_vector_path
        task.matrix_size = matrix_n
        # Оновлюємо статус на "В черзі"
        task.status = Task.Status.QUEUED
        task.save(update_fields=['matrix_file', 'vector_file', 'matrix_size', 'status'])
        
        # Надсилаємо апдейт про успішний парсинг
        task.update_progress("Додано в чергу на обчислення", 10)
        
        # Запускаємо основну задачу обчислення
        run_lu_task.delay(task.id)
        # --- КІНЕЦЬ ВИПРАВЛЕННЯ ---

        return rel_matrix_path, rel_vector_path, matrix_n

    except Exception as e:
        error_message = f"Помилка парсингу для задачі ID {task_id}: {str(e)}"
        if task:
            # --- ВИПРАВЛЕННЯ: Позначаємо задачу як FAILED ---
            task.mark_status(Task.Status.FAILED, error_message)
            task.add_log(error_message, level="ERROR")
            # --- КІНЕЦЬ ВИПРАВЛЕННЯ ---
        else:
            print(f"CRITICAL PARSING ERROR (task object unavailable): {error_message}")
        
        # Ми не кидаємо помилку (raise), бо Celery спробує повторити.
        # Ми вже позначили задачу як FAILED.
        return

# -------------------------------------------------------------
# Задача №2: Обчислення LU
# -------------------------------------------------------------

class LuSolverTask(CeleryTask):
    """Кастомний клас задачі для обробки лімітів часу та стану."""
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        # Обробка помилок, що не були перехоплені
        task_id = args[0]
        task = Task.objects.get(id=task_id)
        task.mark_status(Task.Status.FAILED, f"Непередбачувана помилка воркера: {exc}")
        task.add_log(f"Traceback: {einfo}", level="ERROR")

    def on_success(self, retval, task_id, args, kwargs):
        pass # Успіх обробляється всередині `run`

@shared_task(
    bind=True,
    base=LuSolverTask,
    # Переконуємось, що ці ліміти є
    soft_time_limit=settings.CELERY_TASK_TIME_LIMIT,
    time_limit=settings.CELERY_TASK_TIME_LIMIT + 60
)
def run_lu_task(self, task_id):
    """
    Основна задача обчислення LU-розкладу.
    """
    task = Task.objects.get(id=task_id)
    
    # Перевірка, чи задачу не скасували, поки вона була в черзі
    if task.status == Task.Status.CANCELLED:
        return "Task was cancelled before execution."
        
    # Зберігаємо ID задачі Celery для можливості скасування
    task.celery_task_id = self.request.id
    task.mark_status(Task.Status.RUNNING, "Задача прийнята воркером. Початок обчислень.")
    task.save(update_fields=['celery_task_id'])
    
    def progress_callback(stage, percentage):
        """
        Callback-функція, що викликається з lu_solver.
        Оновлює модель та надсилає прогрес через WS (Пункт 2).
        """
        task.update_progress(stage, percentage)
        task.add_log(f"Етап: {stage} ({percentage:.0f}%)")

    try:
        task.add_log("Завантаження матриці A та вектора b...")
        
        # Перевіряємо шляхи до файлів
        if not task.matrix_file or not task.vector_file:
            raise FileNotFoundError("Файли матриці або вектора відсутні.")
            
        matrix_path = task.matrix_file.path
        vector_path = task.vector_file.path

        if not os.path.exists(matrix_path) or not os.path.exists(vector_path):
            raise FileNotFoundError(f"Файл не знайдено за шляхом: {matrix_path} або {vector_path}")

        # Запускаємо важкі обчислення
        result_vector, files_to_save = solve_lu_system(
            matrix_path,
            vector_path,
            progress_callback=progress_callback,
            save_matrices=task.save_matrices
        )

        # Зберігаємо результат (вектор X)
        task.add_log("Збереження результату...")
        result_dir = os.path.dirname(matrix_path)
        result_path = os.path.join(result_dir, "result_X.txt")
        np.savetxt(result_path, result_vector, fmt='%.18e')

        # Прикріплюємо файл до моделі
        rel_result_path = os.path.relpath(result_path, settings.MEDIA_ROOT)
        task.result_file.name = rel_result_path
        
        # TODO: Зберегти L, U, P, якщо task.save_matrices == True
        # (files_to_save містить шляхи до них)

        task.mark_status(Task.Status.COMPLETED, "Обчислення успішно завершено.")
        task.add_log("Задача виконана.")
        task.save(update_fields=['result_file'])
        
        return f"Task {task_id} completed successfully."

    except SoftTimeLimitExceeded:
        task.mark_status(Task.Status.FAILED, f"Помилка: Перевищено ліміт часу виконання ({settings.CELERY_TASK_TIME_LIMIT} c).")
        task.add_log("Задача примусово зупинена через перевищення ліміту часу.", level="ERROR")
        return f"Task {task_id} failed: Time limit exceeded."
        
    except Exception as e:
        task.mark_status(Task.Status.FAILED, f"Помилка під час виконання: {str(e)}")
        task.add_log(f"Критична помилка обчислення: {str(e)}", level="ERROR")
        return f"Task {task_id} failed: {str(e)}"