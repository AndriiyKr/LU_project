# backend/apps/tasks_app/urls.py

from django.urls import path
from . import views

app_name = 'tasks_app'

urlpatterns = [
    # POST /api/tasks/ (створити)
    # GET  /api/tasks/ (список)
    path("", views.TaskListCreateView.as_view(), name="task-list-create"),
    
    # GET /api/tasks/<id>/ (деталі)
    path("<int:id>/", views.TaskDetailView.as_view(), name="task-detail"),
    
    # POST /api/tasks/<id>/cancel/ (скасувати)
    path("<int:id>/cancel/", views.TaskCancelView.as_view(), name="task-cancel"),
    
    # GET /api/tasks/<id>/download/ (завантажити результат)
    path("<int:id>/download/", views.TaskDownloadView.as_view(), name="task-download"),

    # Додаткові ендпоінти (для поллінгу, якщо WS не спрацює)
    path("<int:id>/progress/", views.TaskProgressListView.as_view(), name="task-progress"),
    path("<int:id>/logs/", views.TaskLogListView.as_view(), name="task-logs"),
]