import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from urllib.parse import parse_qs
import redis.asyncio as redis
from Account.models import RoomTable
from .models import GameTable
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)
logger.debug("WebSocket connected")


class WaitRoomConsumer(AsyncWebsocketConsumer):
    async def connect(self):
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

        if not status:
            if self.username == self.room_owner:
                self.gameslist = await sync_to_async(list)(GameTable.objects.values_list('gamename', flat=True))
                initial_data = {
                    "status": "waiting",
                    "gamelist": json.dumps(self.gameslist),
                    "selected_game": "",
                    "owner": self.username,
                    "players": json.dumps([self.username]),
                    "cardList": json.dumps({}),
                    "current_round": json.dumps({}),
                    "played_card_list": json.dumps([])
                }
                await self.redis.hset(self.redis_key, mapping=initial_data)
            else:
                await self.accept()
                await self.send(text_data=json.dumps({
                    "error": f"The room is closed. Please contact admin: {self.room_owner}"
                }))
                await self.close(code=4002)
                return
        else:
            players_json = await self.redis.hget(self.redis_key, "players")
            players = json.loads(players_json) if players_json else []

            if self.username not in players:
                players.append(self.username)
                await self.redis.hset(self.redis_key, "players", json.dumps(players))

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "players_update",
            }
        )

    async def disconnect_gracefully(self):
        try:
            logger.info(f"Graceful disconnect for {self.username}")
            self.room_id = self.scope['url_route']['kwargs']['room_id']
            self.redis_key = f"gamedata:{self.room_id}"

            players_json = await self.redis.hget(self.redis_key, 'players')
            if players_json:
                players = json.loads(players_json)
                if self.username in players:
                    players.remove(self.username)
                    
                    owner = await self.redis.hget(self.redis_key, 'owner')
                    if self.username == owner.decode():
                        players=[]
                        await self.redis.hset(self.redis_key, 'players', json.dumps(players))
                        await self.channel_layer.group_send(
                            self.group_name,
                            {
                                "type": "players_update",
                            }
                        )
                        await self.channel_layer.group_send(self.group_name,
                            {
                                "type": "send_error_message",
                                "message": "Room Owner left the game, game closed"
                            }
                        )
                        await self.close(code=4002)
                        await self.redis.delete(self.redis_key)
                        logger.info(f"Room {self.room_id} Owner left the room.Game closed")


                    elif players:
                        # Still some players left
                        await self.redis.hset(self.redis_key, 'players', json.dumps(players))
                        await self.channel_layer.group_send(
                            self.group_name,
                            {
                                "type": "players_update",
                            }
                        )
                    else:
                        # No players left, clean up Redis
                        await self.redis.delete(self.redis_key)
                        logger.info(f"Room {self.room_id} is now empty. Redis game data deleted.")

            await self.channel_layer.group_discard(self.group_name, self.channel_name)
            logger.info(f"User {self.username} removed and left the group.")

        except Exception as e:
            logger.error(f"Error during graceful disconnect: {e}")


    async def disconnect(self, close_code):
        await self.disconnect_gracefully()

    async def players_update(self, event):
        self.players_json = await self.redis.hget(self.redis_key, "players")
        self.players = json.loads(self.players_json.decode()) if self.players_json else []
        self.owner = (await self.redis.hget(self.redis_key, "owner")).decode() if await self.redis.hexists(self.redis_key, "owner") else None
        
        self.gamelist_json = await self.redis.hget(self.redis_key, "gamelist")
        self.gamelist = json.loads(self.gamelist_json.decode()) if self.gamelist_json else []

        await self.send(text_data=json.dumps({
            "type": "players_update",
            "players": self.players,
            "owner": self.owner,
            "gamelist":self.gamelist,
        }))

    async def receive(self, text_data):
        data = json.loads(text_data)
        msg_type = data.get("type")
        logger.info(f"recieved {msg_type}")

        if msg_type == "leave":
            logger.info(f"Received leave message from {data.get('username')}")
            await self.disconnect_gracefully()

        elif msg_type == "start_game":
            # Only owner can start the game
            redis_owner = await self.redis.hget(self.redis_key, "owner")
            if redis_owner and redis_owner.decode() == self.username:
                logger.info(f"Game started by owner: {self.username}")
                await self.redis.hset(self.redis_key, "status", "started")

                # Notify all players to start game
                await self.channel_layer.group_send(
                    self.group_name,
                    {
                        "type": "game_started",
                    }
                )
            else:
                logger.warning(f"Unauthorized game start attempt by {self.username}")
                await self.send(text_data=json.dumps({
                    "error": "Only the room owner can start the game."
                }))

        elif msg_type == "game_selected":
            self.selected_game = data.get("selected_game")
            if self.selected_game:
                logger.info(f"Game Card selected: {self.selected_game} by {self.username}")

                # Save the selected card to Redis under 'selected_game'
                await self.redis.hset(self.redis_key, "selected_game", self.selected_game)

                # Notify the group about the game selection
                await self.channel_layer.group_send(
                    self.group_name,
                    {
                        "type": "game_selected",
                    }
                )
            else:
                logger.warning("game selected message received without 'game' field.")
                await self.send(text_data=json.dumps({
                    "error": "No game provided in game_selected message."
                }))

    async def game_started(self, event):
        await self.send(text_data=json.dumps({
            "type": "game_started"
        }))

    async def game_selected(self, event):
        selected_game = await self.redis.hget(self.redis_key, "selected_game")
        selected_game = selected_game.decode() if selected_game else None

        await self.send(text_data=json.dumps({
            "type": "game_selected",
            "selected_game": selected_game,
            "selected_by": self.username
        }))

    async def send_error_message(self, event):
        await self.send(text_data=json.dumps({
            "error": event["message"]
        }))


    # Sokkatte

