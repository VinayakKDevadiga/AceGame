from django.urls import re_path
# myproject/routing.py

from django.urls import re_path
from Home import consumers
from Sokkatte import sokk #sokkatte_consumers  

websocket_urlpatterns = [
re_path(r'ws/wait/(?P<room_id>[^/]+)/$', consumers.WaitRoomConsumer.as_asgi()),
re_path(r'ws/Sokkatte/(?P<room_id>[^/]+)/$', sokk.Sokkatte_consumer.as_asgi()),
]

