import json
import logging
from urllib.parse import parse_qs
import random
# import aioredis.lock
import redis.asyncio as redis
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from Account.models import RoomTable
from redis.asyncio.lock import Lock
import asyncio
logger = logging.getLogger(__name__)
from redis.asyncio.lock import Lock
from redis.exceptions import LockError, LockNotOwnedError


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
        logger.info("Came to this connect for sokkatte websocket")
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.group_name = f"room_{self.room_id}"
        self.redis_key = f"gamedata:{self.room_id}"

        query_string = self.scope['query_string'].decode()
        query_params = parse_qs(query_string)
        self.username = query_params.get('username', ['Anonymous'])[0]
        self.password = query_params.get('password', [''])[0]

        logger.info(f"WebSocket connect attempt: user={self.username}, room={self.room_id}")
        self.redis = redis.Redis(host="127.0.0.1", port=6379, db=0)

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

        await self.accept()
        logger.info("Accepted the websocket conection")
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        logger.info(f"User '{self.username}' connected successfully to room '{self.room_id}'")


        try: 
            self.connected_raw = await self.redis.hget(self.redis_key, "players_connected_list")
            self.connected_dict = json.loads(self.connected_raw.decode()) if self.connected_raw else {}
            if self.username not in self.connected_dict:
                # check whether the card distributed player is refreshed the page or not.
                self.card_distributed_flag = await self.redis.hget(self.redis_key, "card_distributed_flag")
                if self.card_distributed_flag.decode() == "1":
                    logger.info(f"User '{self.username}' has already been connected and cards distributed.but refreshed the page")
                    
                else:
                    logger.info(f"User '{self.username}' is a new connection.")

                assigned_colors = set(self.connected_dict.values())
                available_colors = [c for c in COLOR_CODES if c not in assigned_colors]

                if not available_colors:
                    await self.send(text_data=json.dumps({
                        "error": "All player slots are full — try again later."
                    }))
                    await self.close(code=4004)
                    return

                assigned_color = available_colors[0]
                self.connected_dict[self.username] = assigned_color
                await self.redis.hset(self.redis_key, "players_connected_list", json.dumps(self.connected_dict))
                logger.info(f"User '{self.username}' connected with color {assigned_color}")   # Broadcast to all in the group
                await self.channel_layer.group_send(
                    self.group_name,
                    {
                        "type": "players_update",
                        "connected_dict": self.connected_dict
                    }
                )

                await asyncio.sleep(random.uniform(2, 5.3))  # Optional delay
                all_connected = all(player in self.connected_dict for player in players)
                if all_connected:
                    if self.card_distributed_flag.decode() == "1":
                        logger.info(f"All players connected and cards already distributed for room {self.room_id}")
                        await self.get_player_card()
                    else:
                        await self.channel_layer.group_send(
                            self.group_name,
                            {"type": "everyone_joined"}
                        )
                        await self.distribute_cards()
        except Exception as e:
            logger.error(f"Error in connection lock logic: {e}", exc_info=True)
            await self.send(text_data=json.dumps({
                "type": "send_error_message",
                "message": "Server encountered an error during setup."
            }))
            await self.close(code=1011)


    async def send_error_message(self, event):
        await self.send(text_data=json.dumps({
            "type": "error",
            "message": event.get("message", "An unknown error occurred.")
        }))
 

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)
        logger.info(f"User '{self.username}' disconnected from room '{self.room_id}'")
        
        # Remove user from Redis player-connected list
        self.connected_raw = await self.redis.hget(self.redis_key, "players_connected_list")
        if self.connected_raw:
            connected_dict = json.loads(self.connected_raw.decode())
            if self.username in self.connected_dict:
                del self.connected_dict[self.username]
                await self.redis.hset(self.redis_key, "players_connected_list", json.dumps(self.connected_dict))
                logger.info(f"Removed '{self.username}' from players_connected_list")
                # Send unified update to all players
                await self.channel_layer.group_send(
                    self.group_name,
                    {
                        "type": "players_update",
                        "connected_dict": self.connected_dict
                    }
                )


    async def players_update(self, event):
        logger.info(f"connected dict: {event}")
        
        self.connected_dict = event.get("connected_dict", {})
        
        await self.send(text_data=json.dumps({
            "type": "players_update",
            "connected_dict":self.connected_dict
        }))

    async def everyone_joined(self, event):
        logger.info(f"Cards sent{ self.username}")
        await self.send(text_data=json.dumps({
            "type": "start_card_distribution",
        }))

    async def send_starting_player_update(self, event):
        logger.info(f"Starting player sent: {self.starting_player}")
        await self.send(text_data=json.dumps({
            "type": "starting_player",
            "starting_player": self.starting_player
        }))

    async def send_dynamic_message(self, message_type, message):
        """
        Send a message with dynamic type and content to the client.
        :param message_type: The type of the message (string)
        :param message: The actual message (string or dict)
        """
        await self.send(text_data=json.dumps({
            "type": message_type,
            "message": message
        }))

    async def card_played(self, event):
        logger.info(f"Card played: {event.get('card')}, next player: {event.get('next_player')}")
        await self.send(text_data=json.dumps({
            "type": "card_played",
            "player": self.username,
            "card": event.get('card'),
            "next_player": event.get('next_player'),
            "current_round": event.get('current_round'),
            "player_color_dict": event.get('player_color_dict')
        }))

        


    # distribute cards | initialize cards
    async def initialize_deck(self):
        SUITS = ['F', 'S', 'H', 'D']
        RANKS = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
        FULL_DECK = [f"{suit}{rank}" for suit in SUITS for rank in RANKS]
        await self.redis.hset(self.redis_key, "cardList", json.dumps(FULL_DECK))


    async def distribute_cards(self):
        await self.initialize_deck()  # Ensure deck is initialized

        logger.info("Attempting to acquire lock for card distribution...")
        
        try:
            # Check if cards are already distributed
            logger.info("Card distribution flag")
            logger.info("Distributing cards now...")
            await self.redis.hset(self.redis_key, "card_distributed_flag", "1")
            # Create full deck
            SUITS = ['F', 'S', 'H', 'D']
            RANKS = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
            FULL_DECK = [f"{suit}{rank}" for suit in SUITS for rank in RANKS]
            card_list = FULL_DECK.copy()

            # Get players list from Redis
            raw_data = await self.redis.hgetall(self.redis_key)
            data = {k.decode('utf-8'): v.decode('utf-8') for k, v in raw_data.items()}

            try:
                players_connected = json.loads(data.get("players", "[]"))
                
                if not isinstance(players_connected, list):
                    raise ValueError("Invalid format for 'players'")
            except Exception as e:
                logger.error(f"Failed to decode 'players': {e}", exc_info=True)
                await self.send(text_data=json.dumps({"error": "Invalid player data"}))
                return

            # Distribute 4 cards per player
            distributed_card_dict = {}
            for player in players_connected:
                distributed_card_dict[player] = []
                for _ in range(4):
                    if not card_list:
                        break
                    card = random.choice(card_list)
                    card_list.remove(card)
                    distributed_card_dict[player].append(card)

            # Save to Redis

            #to store starting player name:
            if players_connected:
                self.starting_player = random.choice(players_connected)
                await self.redis.hset(self.redis_key, "starting_player", self.starting_player)
                logger.info(f"Starting player selected: {self.starting_player}")
                await self.redis.hset(self.redis_key, "current_player", self.starting_player)

            try:
                await self.redis.hset(self.redis_key, mapping={
                    "cardList": json.dumps(card_list),
                    "players_card_list": json.dumps(distributed_card_dict),
                })
                logger.info(f"Cards successfully distributed to players: {distributed_card_dict}")
            except Exception as e:
                logger.error(f"Error storing distributed cards: {e}", exc_info=True)

        except Exception as e:
            logger.error(f"Error in distribute_cards: {e}", exc_info=True)
            await self.send(text_data=json.dumps({"error": "Card distribution failed"}))

        

    async def get_player_card(self):
        try:
            # Add retry logic or small wait if needed
            for attempt in range(3):
                card_data = await self.redis.hget(self.redis_key, "players_card_list")
                if card_data:
                    break
                await asyncio.sleep(0.1)  # wait a bit for cards to be set
            else:
                logger.warning("Card data not available after retries")
                card_data = None

            if card_data:
                distributed_card_dict = json.loads(card_data)
                await self.send(text_data=json.dumps({
                    "type": "cards_distributed",
                    "player_cards": distributed_card_dict.get(self.username, [])
                }))
            else:
                await self.send(text_data=json.dumps({
                    "type": "cards_distributed",
                    "player_cards": []
                }))
        except Exception as e:
            logger.error(f"Failed to send cards to {self.username}: {e}", exc_info=True)
            await self.send(text_data=json.dumps({
                "type": "error",
                "message": "Failed to retrieve your cards"
            }))

    async def get_starting_player(self):
        try:
            # Add retry logic or small wait if needed
            for attempt in range(3):
                self.starting_player_data = await self.redis.hget(self.redis_key, "starting_player")
                if self.starting_player_data:
                    break
                await asyncio.sleep(0.1)  # wait a bit for cards to be set
            else:
                logger.warning("Starting player data not available after retries")
                self.starting_player_data = None

            if self.starting_player_data:
                logger.info(f"Starting player selected: {self.starting_player_data.decode()}")
                await self.send(text_data=json.dumps({
                "type": "starting_player",
                "starting_player": self.starting_player_data.decode()
            }))
            
            else:
                await self.send(text_data=json.dumps({
                    "type": "starting_player",
                    "starting_player": None
                }))
                        
        except Exception as e:
            logger.error(f"Failed to send starting player to {self.username}: {e}", exc_info=True)
            await self.send(text_data=json.dumps({
                "type": "error",
                "message": "Failed to retrieve starting player"
            }))
      
    async def drop_play_card_to_table(self,card):
        # validate user has that card
        # validate the card is valid for the crrent_round
        # if both assed then allow and update in the current round and update currentplayer to next player
        
        try:
            # Fetch required data from Redis
            self.players_card_raw = await self.redis.hget(self.redis_key, "players_card_list")
            self.current_player_raw = await self.redis.hget(self.redis_key, "current_player")
            self.current_round_raw = await self.redis.hget(self.redis_key, "current_round")
            self.played_card_raw = await self.redis.hget(self.redis_key, "played_card_list")
            self.card=card
            if not self.players_card_raw or not self.current_player_raw:
                await self.send_dynamic_message("error", "Game state missing or corrupted")
                return

            # Decode Redis values
            self.players_card_dict = json.loads(self.players_card_raw.decode())
            self.current_player = self.current_player_raw.decode()
            self.current_round = json.loads(self.current_round_raw.decode()) if self.current_round_raw else {}
            self.played_card_list = json.loads(self.played_card_raw.decode()) if self.played_card_raw else []

            # ✅ Validate: Is it this player's turn?
            if self.username != self.current_player:
                await self.send_dynamic_message("error", "It's not your turn")
                return

            # ✅ Validate: Player has the card
            self.player_cards = self.players_card_dict.get(self.username, [])
            if card not in self.player_cards:
                await self.send_dynamic_message("error", "You don't have this card")
                return

            # ✅ Validate: Check round-specific rules (e.g., suit enforcement)
            # if current_round is empty then add the required_suit of this card[0] and set it in redis
            if not self.current_round:
                # if the player is the first layer in round
                self.required_suit = self.card[0]
                self.current_round = {"required_suit": self.required_suit, "played_cards": [{self.username: self.card}]}
            else:
                # if the player is the next layer in round
                self.required_suit = self.current_round.get("required_suit")
                if self.required_suit and not card.startswith(self.required_suit):
                    await self.send_dynamic_message("error", f"Card must be of suit {self.required_suit}")
                    return
                else:
                    self.current_round["played_cards"].append({self.username: self.card})

            # ✅ Remove card from player's hand
            self.player_cards.remove(self.card)
            self.players_card_dict[self.username] = self.player_cards
            
            # ✅ Update Redis
            await self.redis.hset(self.redis_key, mapping={
                "players_card_list": json.dumps(self.players_card_dict),
                "current_round": json.dumps(self.current_round)
            })

            # ✅ Determine next player
            self.players_raw = await self.redis.hget(self.redis_key, "players")
            self.players_list = json.loads(self.players_raw.decode()) if self.players_raw else []
            self.next_player = None
            if self.players_list:
                current_index = self.players_list.index(self.username)
                next_index = (current_index + 1) % len(self.players_list)
                self.next_player = self.players_list[next_index]
                await self.redis.hset(self.redis_key, "current_player", self.next_player)
            
            self.connected_raw = await self.redis.hget(self.redis_key, "players_connected_list")
            self.connected_dict = json.loads(self.connected_raw.decode()) if self.connected_raw else {}

            # ✅ Broadcast to all players
            await self.channel_layer.group_send(
                self.group_name,
                {
                    "type": "card_played",
                    "player": self.username,
                    "card": self.card,
                    "next_player": self.next_player,
                    "current_round": self.current_round,
                    "player_color_dict": self.connected_dict
                }
            )
        except Exception as e:
            logger.error(f"Failed to drop_play_card_to_table {self.username}: {e} and card:{self.card}", exc_info=True)
            await self.send_dynamic_message("error", "Failed to drop_play_card_to_table")


    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            msg_type = data.get("type")
            logger.info(f"Received message type: {msg_type}")

            if msg_type == "get_my_cards_req":
                # Instead of distributing again, just fetch and send
                await self.get_player_card()

            elif msg_type=="get_starting_player":
                logger.info("calling get starting player")
                await self.get_starting_player()

            elif msg_type == "playing_card":
                logger.info("calling play card")
                await self.drop_play_card_to_table(data.get("card"))

            else:
                logger.warning(f"Unhandled message type: {msg_type}")
        except Exception as e:
            logger.error(f"Error handling receive: {e}", exc_info=True)
            await self.send(text_data=json.dumps({"type": "error", "message": "Server error"}))
