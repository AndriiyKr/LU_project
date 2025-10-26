from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(
        r'ws/tasks/updates/(?P<task_uuid>[0-9a-f-]+)/$', 
        consumers.TaskProgressConsumer.as_asgi()
    ),
]