import json
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from .models import Task

class TaskProgressConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.task_uuid = self.scope['url_route']['kwargs']['task_uuid']
        self.task_group_name = f"task_{self.task_uuid}"
        self.user = self.scope['user']

        if not self.user or not self.user.is_authenticated:
            await self.close(code=4001)
            return

        if not await self.check_task_permission():
            await self.close(code=4003)
            return

        await self.channel_layer.group_add(
            self.task_group_name,
            self.channel_name
        )
        await self.accept()
        await self.send_current_state()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.task_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        pass 

    async def task_update(self, event):
        await self.send(text_data=json.dumps({
            'type': 'update', 
            'task_id': event['task_id'],
            'status': event['status'],
            'stage': event.get('stage'),
            'percentage': event.get('percentage'),
            'log_message': event.get('log_message'),
            'result_message': event.get('result_message'),
            'queue_position': event.get('queue_position'),
            'estimated_wait_time_sec': event.get('estimated_wait_time_sec'),
        }))

    @sync_to_async
    def check_task_permission(self):
        try:
            if self.user.is_staff:
                return Task.objects.filter(uuid=self.task_uuid).exists()
            return Task.objects.filter(uuid=self.task_uuid, owner=self.user).exists()
        except Task.DoesNotExist:
            return False
        except Exception as e:
            print(f"Error in check_task_permission for {self.task_uuid}: {e}")
            return False

    @sync_to_async
    def get_task_state(self):
        try:
            task = Task.objects.get(uuid=self.task_uuid)
            progress = task.get_progress()
            state = {
                'status': task.status,
                'stage': progress.get('stage'),
                'percentage': progress.get('percentage'),
                'result_message': task.result_message,
                'queue_position': task.get_queue_position() if task.status in [Task.Status.QUEUED, Task.Status.PENDING] else None,
                'estimated_wait_time_sec': task.get_estimated_wait_time() if task.status in [Task.Status.QUEUED, Task.Status.PENDING] else None,
            }
            return state
        except Task.DoesNotExist:
            return None
        except Exception as e: 
            print(f"Error in get_task_state for {self.task_uuid}: {e}")
            return None

    async def send_current_state(self):
        state = await self.get_task_state()
        if state:
            await self.send(text_data=json.dumps({
                'type': 'initial_state',
                **state
            }))
        else:
            await self.close(code=4004)