from rest_framework import serializers
from .models import Task, TaskProgress, TaskLog

class TaskProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskProgress
        fields = ['stage', 'percentage', 'timestamp']

class TaskLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskLog
        fields = ['message', 'level', 'timestamp']

class TaskCreateSerializer(serializers.ModelSerializer):
    source_file = serializers.FileField(write_only=True, required=False, allow_null=True)
    matrix_text = serializers.CharField(write_only=True, required=False, allow_null=True, trim_whitespace=False)
    status = serializers.CharField(read_only=True)
    class Meta:
        model = Task
        fields = [
            'id', 'uuid',
            'name',
            'description',
            'source_file',      
            'matrix_text',      
            'max_n',
            'save_matrices',
            'status',          
        ]
        read_only_fields = ['owner', 'uuid', 'status'] 

    def validate(self, attrs):
        if not attrs.get('source_file') and not attrs.get('matrix_text'):
            raise serializers.ValidationError("Необхідно надати або файл (source_file), або текст (matrix_text).")
        if attrs.get('source_file') and attrs.get('matrix_text'):
            raise serializers.ValidationError("Надайте щось одне: або файл, або текст, але не обидва.")
        return attrs

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

class TaskDetailSerializer(serializers.ModelSerializer):
    owner = serializers.ReadOnlyField(source='owner.username')
    progress_updates = TaskProgressSerializer(many=True, read_only=True)
    logs = TaskLogSerializer(many=True, read_only=True)
    queue_position = serializers.SerializerMethodField()
    estimated_wait_time_sec = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = [
            'id', 'uuid', 'name', 'description', 'status', 'celery_task_id',
            'matrix_size', 'save_matrices', 'result_message',
            'created_at', 'started_at', 'completed_at',
            'owner', 'progress_updates', 'logs',
            'result_file', 
            'queue_position',
            'estimated_wait_time_sec',
        ]
        read_only_fields = fields 

    def get_queue_position(self, obj):
        if obj.status in [Task.Status.QUEUED, Task.Status.PENDING]:
            return obj.get_queue_position()
        return None 

    def get_estimated_wait_time_sec(self, obj):
        if obj.status in [Task.Status.QUEUED, Task.Status.PENDING]:
            return obj.get_estimated_wait_time()
        return None 