from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/wait/(?P<room_id>\w+)/$', consumers.WaitRoomConsumer.as_asgi()),
]
