# backend/apps/tasks_app/serializers.py

from rest_framework import serializers
from .models import Task, TaskProgress, TaskLog

# -------------------------------------------------------------
# Серіалізатори для вкладених даних
# -------------------------------------------------------------
class TaskProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskProgress
        fields = ['stage', 'percentage', 'timestamp']

class TaskLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskLog
        fields = ['message', 'level', 'timestamp']

# -------------------------------------------------------------
# Серіалізатор для СТВОРЕННЯ задачі (POST)
# -------------------------------------------------------------
class TaskCreateSerializer(serializers.ModelSerializer):
    # Поля, які не зберігаються в моделі, а лише для вводу
    source_file = serializers.FileField(write_only=True, required=False, allow_null=True)
    matrix_text = serializers.CharField(write_only=True, required=False, allow_null=True, trim_whitespace=False)
    
    class Meta:
        model = Task
        fields = [
            'id', 'uuid',
            'name',
            'description',
            'source_file',      # Вхідні дані
            'matrix_text',      # Вхідні дані
            'max_n',
            'save_matrices',
        ]
        read_only_fields = ['owner']

    def validate(self, attrs):
        if not attrs.get('source_file') and not attrs.get('matrix_text'):
            raise serializers.ValidationError("Необхідно надати або файл (source_file), або текст (matrix_text).")
        
        if attrs.get('source_file') and attrs.get('matrix_text'):
            raise serializers.ValidationError("Надайте щось одне: або файл, або текст, але не обидва.")
            
        return attrs

# -------------------------------------------------------------
# Серіалізатор для СПИСКУ задач (GET)
# -------------------------------------------------------------
class TaskListSerializer(serializers.ModelSerializer):
    owner = serializers.ReadOnlyField(source='owner.username')
    last_progress = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = [
            'id', 'uuid', 'name', 'status', 'created_at', 
            'completed_at', 'owner', 'last_progress'
        ]

    def get_last_progress(self, obj):
        return obj.get_progress()

# -------------------------------------------------------------
# Серіалізатор для ДЕТАЛЕЙ задачі (GET)
# -------------------------------------------------------------
class TaskDetailSerializer(serializers.ModelSerializer):
    owner = serializers.ReadOnlyField(source='owner.username')
    progress_updates = TaskProgressSerializer(many=True, read_only=True)
    logs = TaskLogSerializer(many=True, read_only=True)
    
    # Поля для черги (Пункт 6)
    queue_position = serializers.SerializerMethodField()
    estimated_wait_time_sec = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = [
            'id', 'uuid', 'name', 'description', 'status', 'celery_task_id',
            'matrix_size', 'save_matrices', 'result_message',
            'created_at', 'started_at', 'completed_at',
            'owner', 'progress_updates', 'logs',
            'result_file', # Додаємо посилання на результат
            'queue_position',
            'estimated_wait_time_sec',
        ]

    def get_queue_position(self, obj):
        return obj.get_queue_position()
        
    def get_estimated_wait_time_sec(self, obj):
        return obj.get_estimated_wait_time()