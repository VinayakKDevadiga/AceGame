import json
import logging
from urllib.parse import parse_qs

import redis.asyncio as redis
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from Account.models import RoomTable

logger = logging.getLogger(__name__)

COLOR_CODES = [
    "#e6194b", "#3cb44b", "#ffe119", "#0082c8", "#f58231", "#911eb4", "#46f0f0", "#f032e6",
    "#d2f53c", "#fabebe", "#008080", "#e6beff", "#aa6e28", "#fffac8", "#800000", "#aaffc3",
    "#808000", "#ffd8b1", "#000080", "#808080", "#FFFFFF", "#000000", "#FF6347", "#6A5ACD",
    "#20B2AA", "#7FFF00", "#DC143C", "#00CED1", "#00FA9A", "#1E90FF", "#FF1493", "#B22222",
    "#ADFF2F", "#5F9EA0", "#FF4500", "#9932CC", "#B0C4DE", "#9ACD32", "#8B0000", "#00FF7F",
    "#4682B4", "#DAA520", "#D2691E", "#2E8B57", "#F4A460", "#4B0082", "#CD5C5C", "#8FBC8F",
    "#4169E1", "#C71585"
]

class Sokkatte_consumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.group_name = f"room_{self.room_id}"
        self.redis_key = f"gamedata:{self.room_id}"

        query_string = self.scope['query_string'].decode()
        query_params = parse_qs(query_string)
        self.username = query_params.get('username', ['Anonymous'])[0]
        self.password = query_params.get('password', [''])[0]

        logger.info(f"WebSocket connect attempt: user={self.username}, room={self.room_id}")

        self.redis = redis.Redis()

        try:
            self.room = await sync_to_async(RoomTable.objects.get)(room_id=self.room_id)
        except RoomTable.DoesNotExist:
            logger.warning(f"Room not found: {self.room_id}")
            await self.close(code=4001)
            return

        players_raw = await self.redis.hget(self.redis_key, "players")
        if not players_raw:
            logger.warning(f"No players list found in Redis for room {self.room_id}")
            await self.send(text_data=json.dumps({"error": "No players defined for this room."}))
            await self.close(code=4002)
            return

        players = json.loads(players_raw.decode())
        logger.debug(f"Players in room {self.room_id}: {players}")

        if self.username not in players:
            logger.warning(f"Unauthorized connection attempt by '{self.username}' in room {self.room_id}")
            await self.send(text_data=json.dumps({
                "error": f"Unknown user '{self.username}' — not allowed in this room."
            }))
            await self.close(code=4003)
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        logger.info(f"User '{self.username}' connected successfully to room '{self.room_id}'")

        # Fetch current color mapping
        connected_raw = await self.redis.hget(self.redis_key, "players_connected_list")
        connected_dict = json.loads(connected_raw.decode()) if connected_raw else {}

        if self.username not in connected_dict:
            # Assign unused color
            assigned_colors = set(connected_dict.values())
            available_colors = [c for c in COLOR_CODES if c not in assigned_colors]

            if not available_colors:
                logger.warning("No more unique colors available.")
                await self.send(text_data=json.dumps({
                    "error": "All player slots are full — try again later."
                }))
                await self.close(code=4004)
                return

            assigned_color = available_colors[0]
            connected_dict[self.username] = assigned_color
            await self.redis.hset(self.redis_key, "players_connected_list", json.dumps(connected_dict))
            logger.info(f"Assigned color '{assigned_color}' to user '{self.username}'")

        # Optional: Broadcast connected player info
        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "user_joined",
                "connected_dict": connected_dict
            }
        )

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)
        logger.info(f"User '{self.username}' disconnected from room '{self.room_id}'")

    async def user_joined(self, event):
        await self.send(text_data=json.dumps({
            "type": "user_joined",
            "connected_dict": event["connected_dict"]
        }))
