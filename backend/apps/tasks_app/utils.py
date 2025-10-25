# backend/apps/tasks_app/utils.py

import os
import numpy as np
import io
from django.conf import settings
from django.core.exceptions import ValidationError
from .models import Task

def parse_and_save_input_data(task_id, source_file=None, matrix_text=None) -> (str, str, int):
    """
    Парсить вхідні дані (файл або текст), 
    розділяє на матрицю A та вектор b (останній стовпець).
    Зберігає їх у тимчасові файли і повертає шляхи до них та розмір N.
    """
    try:
        task = Task.objects.get(id=task_id)
        
        if source_file:
            data = source_file
        elif matrix_text:
            data = matrix_text
        else:
            raise ValueError("Не надано ані файлу, ані тексту.")
            
        string_io = io.StringIO(data)
        
        try:
            full_matrix = np.loadtxt(string_io, dtype=np.float64, ndmin=2)
        except Exception as e:
            raise ValueError(f"Помилка читання даних. Переконайтеся, що це числа, розділені пробілами. Деталі: {e}")

        if full_matrix.ndim != 2:
            raise ValueError("Вхідні дані не є 2D матрицею.")
        
        n_rows, n_cols = full_matrix.shape
        
        if n_cols <= 1:
            raise ValueError("Матриця має мати щонайменше 2 стовпці (матриця A та вектор b).")
            
        matrix_n = n_rows
        
        if matrix_n != (n_cols - 1):
             raise ValueError(f"Матриця A має бути квадратною. Отримано {n_rows} рядків та {n_cols-1} стовпців A.")

        # Перевірка ліміту N (Пункт 1)
        if matrix_n > task.max_n:
            raise ValueError(f"Розмір матриці ({matrix_n}) перевищує дозволений ліміт ({task.max_n}).")

        # Розділяємо: A - це все, крім останнього стовпця
        A = full_matrix[:, :-1]
        # b - це останній стовпець
        b = full_matrix[:, -1]

        # Створюємо директорію для задачі
        task_dir = os.path.join(settings.MEDIA_ROOT, "tasks", str(task.uuid))
        os.makedirs(task_dir, exist_ok=True)

        matrix_path = os.path.join(task_dir, "A.txt")
        vector_path = os.path.join(task_dir, "b.txt")

        # Зберігаємо A та b як окремі файли
        np.savetxt(matrix_path, A, fmt='%.18e')
        np.savetxt(vector_path, b, fmt='%.18e')

        # Повертаємо шляхи *відносно MEDIA_ROOT*
        rel_matrix_path = os.path.relpath(matrix_path, settings.MEDIA_ROOT)
        rel_vector_path = os.path.relpath(vector_path, settings.MEDIA_ROOT)
        
        return rel_matrix_path, rel_vector_path, matrix_n

    except Exception as e:
        raise ValueError(f"Помилка парсингу вхідних даних: {str(e)}")

# Функція check_task_queue_limit видалена, оскільки її логіка була некоректною.
# Celery автоматично керує чергою (Пункт 6).