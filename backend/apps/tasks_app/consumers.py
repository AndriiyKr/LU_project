# backend/apps/tasks_app/consumers.py

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from .models import Task

class TaskProgressConsumer(AsyncWebsocketConsumer):
    
    async def connect(self):
        # Отримуємо UUID задачі з URL
        self.task_uuid = self.scope['url_route']['kwargs']['task_uuid']
        self.task_group_name = f"task_{self.task_uuid}"
        
        # Отримуємо користувача
        self.user = self.scope['user']
        
        if not self.user or not self.user.is_authenticated:
            await self.close(code=4001)
            return
            
        # Перевіряємо, чи має користувач доступ до цієї задачі
        if not await self.check_task_permission():
            await self.close(code=4003)
            return

        # Приєднуємось до групи каналу
        await self.channel_layer.group_add(
            self.task_group_name,
            self.channel_name
        )

        await self.accept()
        
        # Надсилаємо поточний стан при підключенні
        await self.send_current_state()

    async def disconnect(self, close_code):
        # Від'єднуємось від групи
        await self.channel_layer.group_discard(
            self.task_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        # Ми не очікуємо повідомлень від клієнта, лише надсилаємо
        pass

    # --- Обробники повідомлень з Channel Layer ---

    async def task_update(self, event):
        """
        Обробник повідомлення, що надсилається з Task.send_websocket_update()
        """
        # Надсилаємо повідомлення клієнту через WebSocket
        await self.send(text_data=json.dumps({
            'type': 'update',
            'task_id': event['task_id'],
            'status': event['status'],
            'stage': event.get('stage'),
            'percentage': event.get('percentage'),
            'log_message': event.get('log_message'),
            'result_message': event.get('result_message'),
        }))

    # --- Допоміжні функції ---

    @sync_to_async
    def check_task_permission(self):
        """Перевіряє, чи належить задача користувачу."""
        try:
            # Адміністратори можуть бачити всі задачі
            if self.user.is_staff:
                return Task.objects.filter(uuid=self.task_uuid).exists()
            
            # Звичайні користувачі - лише свої
            return Task.objects.filter(uuid=self.task_uuid, owner=self.user).exists()
        except Task.DoesNotExist:
            return False
            
    @sync_to_async
    def get_task_state(self):
        """Отримує поточний стан задачі з БД."""
        try:
            task = Task.objects.get(uuid=self.task_uuid)
            progress = task.get_progress()
            return {
                'status': task.status,
                'stage': progress.get('stage'),
                'percentage': progress.get('percentage'),
                'result_message': task.result_message
            }
        except Task.DoesNotExist:
            return None
            
    async def send_current_state(self):
        """Надсилає поточний стан задачі одразу після підключення."""
        state = await self.get_task_state()
        if state:
            await self.send(text_data=json.dumps({
                'type': 'initial_state',
                **state
            }))