from django.urls import path
from . import views

app_name = 'tasks_app'

urlpatterns = [
    path("", views.TaskListCreateView.as_view(), name="task-list-create"),
    path("<int:id>/", views.TaskDetailView.as_view(), name="task-detail"),
    path("<int:id>/cancel/", views.TaskCancelView.as_view(), name="task-cancel"),
    path("<int:id>/download/", views.TaskDownloadView.as_view(), name="task-download"),
    path("<int:id>/progress/", views.TaskProgressListView.as_view(), name="task-progress"),
    path("<int:id>/logs/", views.TaskLogListView.as_view(), name="task-logs"),
]