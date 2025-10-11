import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from urllib.parse import parse_qs
import redis.asyncio as redis
from Account.models import RoomTable
from .models import GameTable
from asgiref.sync import sync_to_async
from AceGame.game_routes import GAME_ROUTES
from django.conf import settings

logger = logging.getLogger(__name__)
logger.debug("WebSocket connected")


class WaitRoomConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        logger.info(f"Connect req came to connect consumer")

        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.group_name = f"room_{self.room_id}"
        self.redis_key = f"gamedata:{self.room_id}"

        query_string = self.scope['query_string'].decode()
        query_params = parse_qs(query_string)
        self.username = query_params.get('username', ['Anonymous'])[0]
        self.password = query_params.get('password', [''])[0]

        self.redis = redis.Redis(host="127.0.0.1", port=6379, db=0) 

        logger.info(f"connected to redis { self.username}, {self.password}")


        try:
            self.room = await sync_to_async(RoomTable.objects.get)(room_id=self.room_id)
        except RoomTable.DoesNotExist:
            await self.close(code=4001)
            return

        self.room_owner = self.room.username  # Save owner in self for later use
        logger.info(f"Querying status {self.room_owner} {self.redis_key}")

        try:
            await self.accept()
            status = await self.redis.hget(self.redis_key, "status")

        except redis.TimeoutError:
            logger.error(f"Redis hget timed out.")
            # status = None  # ← this is critical

        if status and self.username==self.room_owner:
                    duplicate_owner_login = (await self.redis.hget(self.redis_key, "duplicate_owner_login")).decode()
                    await self.redis.hset(self.redis_key, "duplicate_owner_login", (int(duplicate_owner_login)+1))

                    if status.decode()=='started':
                        await self.send(text_data=json.dumps({
                            "error": "Game Already started in other browser with your userid"
                            }))
                        await self.close(code=4002)
                        return
                    elif status.decode()=='waiting':
                        # await self.accept()
                        await self.send(text_data=json.dumps({
                            "error": "You are already in room with other device or browser, Log off there and continue"
                        }))
                        await self.close(code=4002)
                        return
        
        if not status:
            if self.username == self.room_owner :
                
                if status and (status.decode()=='waiting' or status.decode()=='started'):
                    # await self.accept()
                    await self.send(text_data=json.dumps({
                        "error": "You are already in room with other device or browser, Log off there and continue"
                    }))
                    await self.close(code=4002)
                    return
                # else
                self.gameslist = await sync_to_async(list)(GameTable.objects.values_list('gamename', flat=True))
                logger.info(f"IN Above STATUS PART and ")

                initial_data = {
                    "status": "waiting",
                    "gamelist": json.dumps(self.gameslist),
                    "selected_game": "",
                    "owner": self.username,
                    "duplicate_owner_login":0,
                    "players": json.dumps([self.username]),
                    "cardList": json.dumps({}),
                    "card_distributed_flag": 0,
                    "current_round": json.dumps({}),
                    "players_connected_list": json.dumps({}),
                    "played_card_list": json.dumps([]),
                    "game_completed_players_list":json.dumps([]),
                    "card_problem": json.dumps({"card_problem": False}),
                    "inserted_to_db":"False"
                }
                logger.info(f"IN NOT STATUS PART and {initial_data}")
                await self.redis.hset("test_key", mapping={"foo": "bar"})


                await self.redis.hset(self.redis_key, mapping=initial_data)
               
            else:
                # await self.accept()
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

            else:
                # await self.accept()
                await self.send(text_data=json.dumps({
                    "error": "You are already in room with other device or browser, Log off there and continue"
                }))
                await self.close(code=4002)
                return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        # await self.accept()

        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "players_update",
            }
        )
        logger.info(f"Accepted and group msg sent")


    async def disconnect_gracefully(self):
        try:
            logger.info(f"Graceful disconnect for {self.username}")
            self.room_id = self.scope['url_route']['kwargs']['room_id']
            self.redis_key = f"gamedata:{self.room_id}"

            players_json = await self.redis.hget(self.redis_key, 'players')
            if players_json:
                players = json.loads(players_json)
                if self.username in players:
                    owner = await self.redis.hget(self.redis_key, 'owner')

                    if self.username == owner.decode() :
                        logger.info(f"{(await self.redis.hget(self.redis_key, 'duplicate_owner_login')).decode()} duplicate_owner_login")

                        if int((await self.redis.hget(self.redis_key, "duplicate_owner_login")).decode())>0 :
                            duplicate_owner_login = (await self.redis.hget(self.redis_key, "duplicate_owner_login")).decode()
                            await self.redis.hset(self.redis_key, "duplicate_owner_login", (int(duplicate_owner_login)-1))
                        else:
                            
                            game_status = (await self.redis.hget(self.redis_key, 'status')).decode()
                            logger.info(f"Game started status {game_status}")
                            
                            logger.info(f"Came to else part of disconnect-----The stage an his here now ")
                       
                            
                            
                            # await self.channel_layer.group_send( #no need to send this update as the owner deleted the room
                            #     self.group_name,
                            #     {
                            #         "type": "players_update",
                            #     }
                            # )
                            if game_status=="started":
                                await self.channel_layer.group_send(
                                self.group_name,
                                {
                                    "type": "send_error_message",
                                    "message": "Game Started by owner",        
                                }
                            )
                            else:
                                await self.channel_layer.group_send(
                                    self.group_name,
                                    {
                                        "type": "send_error_message",
                                        "message": "Room Owner left the game, game closed",
                                        "delete":True

                                    }
                                )
                                await self.redis.delete(self.redis_key)
                                logger.info(f"Room {self.room_id} is now empty. Redis game data deleted.")

                    else:
                        game_status = (await self.redis.hget(self.redis_key, 'status')).decode()

                        if game_status=="started":
                                await self.channel_layer.group_send(
                                self.group_name,
                                {
                                    "type": "send_error_message",
                                    "message": "Game Started by owner",        
                                }
                            )
                        else:  #waiting
                            players.remove(self.username)
                            await self.redis.hset(self.redis_key, 'players', json.dumps(players))
                            await self.close(code=4002)
                            logger.info(f"Redis data deleted")

                            
                        

                        # if self.username == owner.decode():
                        #     players=[]
                        #     await self.redis.hset(self.redis_key, 'players', json.dumps(players))
                        #     await self.channel_layer.group_send(
                        #         self.group_name,
                        #         {
                        #             "type": "players_update",
                        #         }
                        #     )
                            
                            #to check whether game not started and owner left the room then, error
                            # game_status = await self.redis.hget(self.redis_key, 'status')
                            # if game_status.decode()!= 'started':
                            #     await self.channel_layer.group_send(self.group_name,
                            #         {
                            #             "type": "send_error_message",
                            #             "message": "Room Owner left the game, game closed"
                            #         }
                            #     )
                            #     await self.close(code=4002)
                            #     await self.redis.delete(self.redis_key)
                            #     logger.info(f"Room {self.room_id} Owner left the room.Game closed")
                            

                        if players:
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

        selected_game_raw = await self.redis.hget(self.redis_key, "selected_game")
        self.selected_game = selected_game_raw.decode().strip() if selected_game_raw else None

        
        if self.selected_game==None:
            self.selected_game=self.gamelist[1] if len(self.gamelist) > 1 else self.gamelist[0]
            await self.redis.hset(self.redis_key, "selected_game", self.selected_game)

        await self.send(text_data=json.dumps({
            "type": "players_update",
            "players": self.players,
            "owner": self.owner,
            "gamelist":self.gamelist,
            "selected_game":self.selected_game
        }))




    async def receive(self, text_data):
        data = json.loads(text_data)
        msg_type = data.get("type")
        logger.info(f"recieved {msg_type}")

        if msg_type == "leave":
            logger.info(f"Received leave message from {data.get('username')}")
            await self.disconnect_gracefully()

        elif msg_type == "start_game":
            #if the game is already in started state then consider this as invalid request
            status = (await self.redis.hget(self.redis_key, "status")).decode()
            if status=='started':
                await self.send(text_data=json.dumps({
                    "error": "You have already Started Game in other device, Log off there and continue here"
                }))
                await self.close(code=4002)
                return
            
            else:
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

            # to check whether selected game valid
            self.gamelist_json = await self.redis.hget(self.redis_key, "gamelist")
            self.gamelist = json.loads(self.gamelist_json.decode()) if self.gamelist_json else []

            if self.selected_game and self.selected_game in self.gamelist:
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
                logger.warning("game selected message received without 'game' field or You have modefied the game name.")
                await self.send(text_data=json.dumps({
                    "error": "No game provided in game_selected message."
                }))

    async def game_started(self, event):
        self.selected_game = await self.redis.hget(self.redis_key, "selected_game")
        selected_game = await self.redis.hget(self.redis_key, "selected_game")
        logger.info(f"selected game found: {selected_game}")

        self.selected_game = self.selected_game.decode() if self.selected_game else None
        
        self.domain = getattr(settings, "SITE_DOMAIN", "http://localhost:8000")
        self.full_url = f"{self.domain}{GAME_ROUTES[self.selected_game]['url']}"
        logger.info(f"ful_url: {self.full_url}")
        

        if not self.full_url or not GAME_ROUTES[self.selected_game].get("allowed", False):
            await self.send(text_data=json.dumps({
                "type": "send_error_message",
                "message": "The selected game is currently unavailable."
            }))
            return

        await self.send(text_data=json.dumps({
            "type": "game_started",
            "redirect_url": self.full_url
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
        
        if event.get("delete"):
            await self.send(text_data=json.dumps({
                "type": "players_update",
                "players": [],
                "owner": self.owner,
                "gamelist":[],
                "selected_game":self.selected_game
            }))
            if await self.redis.exists(self.redis_key):
                await self.redis.delete(self.redis_key)
                logger.info(f"Room {self.room_id} is now empty. Redis game data deleted.")
            else:
                logger.warning(f"Tried to delete Redis key {self.redis_key}, but it does not exist.")
        
        await self.send(text_data=json.dumps({
            "error": event["message"]
        }))


    