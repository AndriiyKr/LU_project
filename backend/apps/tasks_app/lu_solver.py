import numpy as np
import time
import os

def lu_decomposition(A, progress_callback):
    n = A.shape[0]
    L = np.zeros((n, n))
    U = np.zeros((n, n))
    P = np.eye(n)
    A_copy = A.copy()
    progress_callback(0)

    for k in range(n):
        pivot_row = np.argmax(np.abs(A_copy[k:n, k])) + k
        if k != pivot_row:
            A_copy[[k, pivot_row]] = A_copy[[pivot_row, k]]
            P[[k, pivot_row]] = P[[pivot_row, k]]
            L[[k, pivot_row], :k] = L[[pivot_row, k], :k] 

        L[k, k] = 1.0
        for i in range(k + 1, n):
            factor = A_copy[i, k] / A_copy[k, k]
            L[i, k] = factor
            A_copy[i, k:] -= factor * A_copy[k, k:]
        
        U[k, k:] = A_copy[k, k:]

        progress = (k + 1) / n * 100
        if k % (n // 20 or 1) == 0 or k == n - 1: 
            progress_callback(progress) 
            
    return L, U, P


def solve_lu_system(matrix_path, vector_path, progress_callback, save_matrices=False):
    try:
        progress_callback("Завантаження даних", 0)
        start_time = time.time()
        
        A = np.loadtxt(matrix_path)
        b = np.loadtxt(vector_path)
        
        n = A.shape[0]
        if A.shape != (n, n) or b.shape != (n,):
            raise ValueError("Некоректні розміри матриці A або вектора b.")

        def lu_progress_callback(percentage):
            scaled_percentage = percentage * 0.8 
            progress_callback("LU розклад", scaled_percentage)
        
        L, U, P = lu_decomposition(A, lu_progress_callback)
        progress_callback("LU розклад", 80)

        Pb = np.dot(P, b)
        y = np.linalg.solve(L, Pb)
        
        progress_callback("Розв'язання системи", 90)
        x = np.linalg.solve(U, y)
        progress_callback("Розв'язання системи", 100)
        end_time = time.time()
        progress_callback(f"Завершено за {end_time - start_time:.2f} c.", 100)

        files_to_save = {}
        if save_matrices:
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