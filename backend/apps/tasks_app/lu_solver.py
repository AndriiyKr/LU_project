# backend/apps/tasks_app/lu_solver.py

import numpy as np
import time
import os

def lu_decomposition(A, progress_callback):
    """
    Виконує LU розклад з частковим поворотом (PA = LU).
    Викликає progress_callback(percentage) з одним аргументом.
    """
    n = A.shape[0]
    L = np.zeros((n, n))
    U = np.zeros((n, n))
    P = np.eye(n)
    
    A_copy = A.copy()

    progress_callback(0) # <--- Викликаємо з ОДНИМ аргументом

    for k in range(n):
        # 1. Частковий поворот
        pivot_row = np.argmax(np.abs(A_copy[k:n, k])) + k
        if k != pivot_row:
            A_copy[[k, pivot_row]] = A_copy[[pivot_row, k]]
            P[[k, pivot_row]] = P[[pivot_row, k]]
            L[[k, pivot_row], :k] = L[[pivot_row, k], :k] # Важливо для L

        # 2. Обчислення L та U
        L[k, k] = 1.0
        for i in range(k + 1, n):
            factor = A_copy[i, k] / A_copy[k, k]
            L[i, k] = factor
            A_copy[i, k:] -= factor * A_copy[k, k:]
        
        U[k, k:] = A_copy[k, k:]
        
        # Оновлення прогресу
        progress = (k + 1) / n * 100
        if k % (n // 20 or 1) == 0 or k == n - 1: # Оновлюємо кожні 5%
            progress_callback(progress) # <--- Викликаємо з ОДНИМ аргументом
            
    return L, U, P

# --- Ми більше не використовуємо ці функції, бо вони були некоректні ---
# --- Але можемо їх залишити, вони не заважають ---
def forward_substitution(L, b):
    """(НЕ ВИКОРИСТОВУЄТЬСЯ) Пряма підстановка (Ly = b)."""
    n = L.shape[0]
    y = np.zeros(n)
    for i in range(n):
        y[i] = b[i] - np.dot(L[i, :i], y[:i])
    return y

def backward_substitution(U, y):
    """(НЕ ВИКОРИСТОВУЄТЬСЯ) Зворотна підстановка (Ux = y)."""
    n = U.shape[0]
    x = np.zeros(n)
    for i in range(n - 1, -1, -1):
        if U[i, i] == 0:
            raise np.linalg.LinAlgError("Матриця U є сингулярною.")
        x[i] = (y[i] - np.dot(U[i, i + 1:], x[i + 1:])) / U[i, i]
    return x

# ---------------------------------------------------------------------

def solve_lu_system(matrix_path, vector_path, progress_callback, save_matrices=False):
    """
    Головна функція для розв'язання системи Ax = b.
    ВИПРАВЛЕНА ВЕРСІЯ.
    """
    
    try:
        # --- Етап 1: Завантаження (0%) ---
        progress_callback("Завантаження даних", 0)
        start_time = time.time()
        
        A = np.loadtxt(matrix_path)
        b = np.loadtxt(vector_path)
        
        n = A.shape[0]
        if A.shape != (n, n) or b.shape != (n,):
             raise ValueError("Некоректні розміри матриці A або вектора b.")
        
        # --- Етап 2: LU Розклад (0% -> 80%) ---
        
        # lu_decomposition викликає callback з одним аргументом (percentage)
        # Ми створюємо нову функцію, яка "стискає" цей прогрес у 0-80%
        def lu_progress_callback(percentage):
            # percentage - це число від 0 до 100
            # ми перетворюємо його на число від 0 до 80
            scaled_percentage = percentage * 0.8 
            progress_callback("LU розклад", scaled_percentage)
        
        L, U, P = lu_decomposition(A, lu_progress_callback)
        
        # Гарантуємо, що ми досягли 80%
        progress_callback("LU розклад", 80)
        
        # --- Етап 3: Розв'язання (80% -> 100%) ---
        # PA = LU  =>  Ax=b  =>  PAx = Pb  =>  LUx = Pb
        
        # 1. Застосовуємо P до b
        Pb = np.dot(P, b)
        
        # 2. Розв'язуємо Ly = Pb
        # Використовуємо надійний розв'язувач numpy
        y = np.linalg.solve(L, Pb)
        
        progress_callback("Розв'язання системи", 90)

        # 3. Розв'язуємо Ux = y
        # Використовуємо надійний розв'язувач numpy
        x = np.linalg.solve(U, y)
        
        progress_callback("Розв'язання системи", 100)
        
        end_time = time.time()
        progress_callback(f"Завершено за {end_time - start_time:.2f} c.", 100)

        files_to_save = {}
        if save_matrices:
            # Логіка збереження L, U, P, якщо потрібно
            base_dir = os.path.dirname(matrix_path)
            np.savetxt(os.path.join(base_dir, "L.txt"), L)
            np.savetxt(os.path.join(base_dir, "U.txt"), U)
            np.savetxt(os.path.join(base_dir, "P.txt"), P)
            files_to_save = {"L": "L.txt", "U": "U.txt", "P": "P.txt"}

        return x, files_to_save

    except np.linalg.LinAlgError as e:
        raise Exception(f"Матриця сингулярна або вироджена. {e}")
    except Exception as e:
        raise Exception(f"Помилка під час обчислень: {e}")