import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from urllib.parse import parse_qs
import redis.asyncio as redis
from Account.models import RoomTable
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)

class WaitRoomConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.group_name = f"room_{self.room_id}"
        self.redis_key = f"gamedata:{self.room_id}"

        # Extract username and password from query params
        query_string = self.scope['query_string'].decode()
        query_params = parse_qs(query_string)
        self.username = query_params.get('username', ['Anonymous'])[0]
        self.password = query_params.get('password', [''])[0]

        # Connect to Redis
        self.redis = redis.Redis()

        # Fetch room from DB
        try:
            room = await sync_to_async(RoomTable.objects.get)(room_id=self.room_id)
        except RoomTable.DoesNotExist:
            await self.close(code=4001)  # Invalid room
            return

        room_owner = room.username  # Ensure this field exists in RoomTable

        # Check if game status exists in Redis
        status = await self.redis.hget(self.redis_key, "status")

        if not status:
            if self.username == room_owner:
                # Owner joins first - create initial game data
                initial_data = {
                    "status": "waiting",
                    "owner": self.username,
                    "players": json.dumps([self.username]),
                    "cardList": json.dumps({}),
                    "current_round": json.dumps({}),
                    "played_card_list": json.dumps([])
                }
                await self.redis.hset(self.redis_key, mapping=initial_data)
            else:
                # Room not yet initialized by owner
                await self.send(text_data=json.dumps({
                    "error": "Room not yet created by the owner."
                }))
                await self.close(code=4002)
                return
        else:
            # Room already active, add player if new
            players_json = await self.redis.hget(self.redis_key, "players")
            players = json.loads(players_json) if players_json else []

            if self.username not in players:
                players.append(self.username)
                await self.redis.hset(self.redis_key, "players", json.dumps(players))

        # WebSocket group setup
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        # Notify all in room about updated players list
        # players_json = await self.redis.hget(self.redis_key, "players")
        # players = json.loads(players_json.decode()) if players_json else []

        # logger.debug(f"Current players in room {self.room_id}: {players}")

        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "players_update",
            }
        )

    async def disconnect(self, close_code):
        try:
            logger.info(f"DISCONNECT CALLED for {self.username}")
            players_json = await self.redis.hget(self.redis_key, 'players')
            if players_json:
                players = json.loads(players_json)
                if self.username in players:
                    players.remove(self.username)
                    await self.redis.hset(self.redis_key, 'players', json.dumps(players))
                    await self.channel_layer.group_send(
                        self.group_name,
                        {
                            "type": "players_update",
                        }
                    )
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
        except Exception as e:
            print(f"Error in disconnect(): {e}")


    async def players_update(self, event):
        players_json = await self.redis.hget(self.redis_key, "players")
        players = json.loads(players_json.decode()) if players_json else []
        
        await self.send(text_data=json.dumps({
            "type": "players_update",
            "players": players
        }))
