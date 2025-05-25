from django.urls import re_path
from Home import consumers
# myproject/routing.py

from django.urls import re_path
from Home.consumers import WaitRoomConsumer
# from chat.consumers import ChatConsumer

# websocket_urlpatterns = [
#     re_path(r'ws/game/(?P<room_name>\w+)/$', GameConsumer.as_asgi()),
#     re_path(r'ws/chat/(?P<room_name>\w+)/$', ChatConsumer.as_asgi()),
# ]

websocket_urlpatterns = [
    re_path(r'ws/wait/(?P<room_id>\w+)/$', WaitRoomConsumer.as_asgi()),
]
