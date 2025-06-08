from Home.consumers import WaitRoomConsumer
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from Account.models import RoomTable
from urllib.parse import parse_qs
import redis.asyncio as redis
import json

class Sokkatte_consumer(AsyncWebsocketConsumer):

    async def connect(self):
        # Check whether the user is listed in the redis players, If so, accept the connection, else do not accept.
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.group_name = f"room_{self.room_id}"
        self.redis_key = f"gamedata:{self.room_id}"

        query_string = self.scope['query_string'].decode()
        query_params = parse_qs(query_string)
        self.username = query_params.get('username', ['Anonymous'])[0]
        self.password = query_params.get('password', [''])[0]

        self.redis = redis.Redis()
        try:
            self.room = await sync_to_async(RoomTable.objects.get)(room_id=self.room_id)
        except RoomTable.DoesNotExist:
            await self.close(code=4001)
            return

        self.room_owner = self.room.username  # Save owner in self for later use

        status = await self.redis.hget(self.redis_key, "status")
