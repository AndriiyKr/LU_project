from django.urls import path
from . import views

app_name = 'monitoring'

urlpatterns = [
    path('metrics/', views.MonitoringMetricsView.as_view(), name='metrics'),
    path('all-tasks/', views.AdminTaskListView.as_view(), name='admin-all-tasks'),
]