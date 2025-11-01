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
logger = logging.getLogger("Sokkatte")  # must match logger name in settings
from redis.asyncio.lock import Lock
from redis.exceptions import LockError, LockNotOwnedError
import time

from Home.models import CompletedGame, PlayerStats
from asgiref.sync import sync_to_async
import json

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
        self.completed_players_raw = await self.redis.hget(self.redis_key, "game_completed_players_list")
        self.completed_players = json.loads(self.completed_players_raw.decode()) if self.completed_players_raw else []     
            
        if self.username not in players:
            # check in game completed player list: if there then allow else dont allow
            if self.username in self.completed_players:
                logger.info(f"User '{self.username}' is rejoining after game completion in room {self.room_id}")
                
            else:
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

        # If Game Completed player rejoins to spectate:
        if self.username in self.completed_players:
            await self.get_player_card()
            
            await self.get_starting_player()
            # send the current_round_cardlist if the current_round_card list is not empty
            self.connected_raw = await self.redis.hget(self.redis_key, "players_connected_list")
            self.connected_dict = json.loads(self.connected_raw.decode()) if self.connected_raw else {}
            self.current_round_raw_table_update = await self.redis.hget(self.redis_key, "current_round")
            self.current_round_table_update = json.loads(self.current_round_raw_table_update.decode()) if self.current_round_raw_table_update else {}
            
            # get the "next_player" from self.current_round_table_update
            self.next_player_table_update_raw = await self.redis.hget(self.redis_key, "current_player")
            self.next_player_table_update = self.next_player_table_update_raw.decode() if self.next_player_table_update_raw else None
            
            if self.current_round_table_update:
                # send the current_round_table_update to frontend
                logger.info("sending current_round_table_update")
                await self.send(text_data=json.dumps({
                    "type": "current_round_table_update",
                    "current_round": self.current_round_table_update,
                    "player": self.username,
                    "next_player":self.next_player_table_update , # self.winner_dict["winner"],
                    "player_color_dict": self.connected_dict
                }))
            
        else:
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

                    # send the current_round_cardlist if the current_round_card list is not empty
                    self.current_round_raw_table_update = await self.redis.hget(self.redis_key, "current_round")
                    self.current_round_table_update = json.loads(self.current_round_raw_table_update.decode()) if self.current_round_raw_table_update else {}
                    
                    # get the "next_player" from self.current_round_table_update
                    self.next_player_table_update_raw = await self.redis.hget(self.redis_key, "current_player")
                    self.next_player_table_update = self.next_player_table_update_raw.decode() if self.next_player_table_update_raw else None
                    
                    if self.current_round_table_update:
                        # send the current_round_table_update to frontend
                        logger.info("sending current_round_table_update")
                        await self.send(text_data=json.dumps({
                            "type": "current_round_table_update",
                            "current_round": self.current_round_table_update,
                            "player": self.username,
                            "next_player":self.next_player_table_update , # self.winner_dict["winner"],
                            "player_color_dict": self.connected_dict
                        }))

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
        await self.send_game_completed_msg()

    async def send_game_completed_msg(self):
        self.players_raw = await self.redis.hget(self.redis_key, "players")
        self.players = json.loads(self.players_raw.decode()) if self.players_raw else []
        # get connected_dct
        self.connected_dict_rejoin_raw = await self.redis.hget(self.redis_key, "players_connected_list")
        self.connected_dict_rejoin = json.loads(self.connected_dict_rejoin_raw.decode()) if self.connected_dict_rejoin_raw else {}
        logger.info(f"sending the game completed message after complted player rejoin{self.completed_players}")
        
        await self.send(text_data=json.dumps({
            "type": "completed_game",
            "players_still_in": self.players,
            "players_completed": self.completed_players,
            "players_completed_now": [],
            'connected_dict':self.connected_dict_rejoin ,
        }))


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
            self.connected_dict = json.loads(self.connected_raw.decode())
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
                if len(self.connected_dict)==0:
                    # if no players are connected then delete the redis key
                    await self.redis.delete(self.redis_key)
                    # mark the game as completed and save the game
                    await self.redis.hset(self.redis_key, "status", "completed")
                    await self.update_gamedata_to_db()
                    await self.redis.delete(self.redis_key)
                    logger.info(f"Deleted Redis key {self.redis_key} as no players are connected.")



    async def players_update(self, event):
        logger.info(f"connected dict: {event}")
        
        self.connected_dict = event.get("connected_dict", {})
        
        await self.send(text_data=json.dumps({
            "type": "players_update",
            "connected_dict":self.connected_dict
        }))

    async def completed_game(self, event):
        logger.info(f"connected dict: {event}")
        
        self.connected_dict = event.get("connected_dict", {})
        
        await self.send(text_data=json.dumps({
            "type": "completed_game",
            "players_still_in": event.get('players_still_in'),
            "players_completed": event.get("players_completed"),
            'connected_dict':self.connected_dict ,
            'players_completed_now': event.get("players_completed_now", []),
            
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

    async def send_group_message(self, event):
        message_type = event["message_type"]
        message = event["message"]
        await self.send(text_data=json.dumps({
            "type": "error",
            "message": message
        }))
        
    async def deck_pile_count(self, event):
        message = event["cardListLength"]
        await self.send(text_data=json.dumps({
            "type": "deck_pile_count",
            "message": message
        }))

    async def send_dynamic_group_message(self, message_type, message):
        """
        Send a message with dynamic type and content to the client.
        :param message_type: The type of the message (string)
        :param message: The actual message (string or dict)
        """
        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "send_group_message",   # this must match a handler method
                "message_type": message_type,
                "message": message
            }
        )
        
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
    async def clear_round(self, event):
        logger.info(f"Clearing round: {event.get('current_round')}")
        await self.send(text_data=json.dumps({
            "type": "clear_round",
            "card": event.get('card'),
            "current_round": event.get('current_round'),
            "current_round": event.get('current_round'),
            "next_player": event.get('next_player'),
         "player_color_dict": event.get('player_color_dict'),
        }))
    
    async def game_over(self, event):
        logger.info(f" msg sender Game over, looser is: {event.get('looser')}")
        logger.info(f"game_completed_player_list: {event.get('game_completed_player_list', [])}")
        await self.send(text_data=json.dumps({
            "type": "game_over",
            "looser": event.get("looser"),
            "game_completed_player_list": event.get("game_completed_player_list", []),
        }))
        logger.info("Updating game completion in redis")
        await self.redis.hset(self.redis_key,"status","completed")
        await self.update_gamedata_to_db()
        # empty the redis key
        await self.redis.delete(self.redis_key)
        logger.info("Deleted gamedata from Redis after game over.")
        

    async def card_problem(self, event):
        logger.info(f"Card problem detected")
        await self.send(text_data=json.dumps({
            "type": "card_problem",
            "message": event.get("message", "You both have different Suits of cards So,Game will not be finished.Please click on see opponent cards and continue the game"),
            "players": event.get("players"),
            "other_player_card_list": event.get("other_player_card_list", []),
            "connected_dict": self.connected_dict

        }))
        
    async def red_day_triggered(self, event):
        logger.info(f"Red day triggered by {event.get('from_player')} → winner {event.get('to_winner')}")
        await self.send(text_data=json.dumps({
            "type": "red_day_triggered",
            "from_player": event.get("from_player"),
            "to_winner": event.get("to_winner"),
            "card_given": event.get("card_given"),
            "current_round": event.get("current_round"),
            "next_player": event.get("next_player"),
            "player_color_dict": event.get("player_color_dict"),
            "current_round_card_list": event.get("current_round_card_list"),
            
        }))

    async def send_updated_next_player_after_round_completion(self, event):
        logger.info("Triggered send_updated_next_player_after_round_completion")
        await self.send(text_data=json.dumps({
            "type": "send_updated_next_player_after_round_completion",
            "next_player": event.get("next_player"),
            "player_color_dict": event.get("player_color_dict"),            
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
                for _ in range(2):
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
            # if current_player exists then give teh current_player
            self.start_player_rejoin_raw = await self.redis.hget(self.redis_key, "current_player")
            self.start_player_rejoin = self.start_player_rejoin_raw.decode() if self.start_player_rejoin_raw else None

            if self.start_player_rejoin:
                logger.info(f"Starting player selected start_player_rejoin: {self.start_player_rejoin}")
                await self.send(text_data=json.dumps({
                    "type": "starting_player",
                    "starting_player": self.start_player_rejoin
                }))
                return
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

            
    async def evaluate_round_winner(self):
        self.winner_dict = {
                "winner": list(self.played_cards[0].keys())[0],
                "card": list(self.played_cards[0].values())[0]
            }        
        self.RANK_TO_VALUE = {
            '2': 0, '3': 1, '4': 2, '5': 3, '6': 4, '7': 5,
            '8': 6, '9': 7, '10': 8, 'J': 9, 'Q': 10, 'K': 11, 'A': 12
        }

        def get_rank_index(card: str) -> int:
            return self.RANK_TO_VALUE[card[1:]]
        
        for playerdict in self.played_cards:
            for username, card in playerdict.items():  # iterate directly over key-value
                card_rank = get_rank_index(card)
                logger.info(f"Comparing card {card} of player {username} with current winner card {self.winner_dict['card']}")
                if card_rank > get_rank_index(self.winner_dict["card"]):
                    logger.info(f"New highest card found: {card} by player {username}")
                    self.winner_dict["winner"] = username   # directly use username
                    self.winner_dict["card"] = card

        return self.winner_dict

    async def start_next_round(self):
        # update the current player as winner player
        # store the current round in "played_card_list"
        # set the current__round as empty dictionary
        self.winner_dict=await self.evaluate_round_winner()
        await self.redis.hset(self.redis_key, "current_player", self.winner_dict['winner'])
        self.played_card_raw = await self.redis.hget(self.redis_key, "played_card_list")
        self.played_card_list = json.loads(self.played_card_raw.decode()) if self.played_card_raw else []
        self.played_card_list.append(self.current_round)
        await self.redis.hset(self.redis_key, "played_card_list", json.dumps(self.played_card_list))
        await self.redis.hset(self.redis_key, "current_round", json.dumps({}))
        self.next_player=self.winner_dict['winner']



    async def validate_round_completion(self):
        self.played_cards = self.current_round.get("played_cards", [])

        if len(self.played_cards) == len(self.players_list):
            
            logger.info("Round completed. Evaluating winner...")
            # check player_completed the game only when round
            await self.start_next_round()
            self.game_over_flag=await self.check_gamecompletion_of_players()
            if self.game_over_flag=="GAME_OVER":
                return  # stop further processing as game is over
            # send the empty current_round and clear the cards in frontend
            logger.info(f"Round winner: {self.winner_dict}")

            # ✅ Broadcast to all players last played card and  current_next player
            await self.channel_layer.group_send(
                self.group_name,
                {
                    "type": "card_played",
                    "player": self.username,
                    "card": self.card,
                    "next_player":self.next_player , # self.winner_dict["winner"],
                    "current_round": self.current_round,
                    "player_color_dict": self.connected_dict
                }
            )
            time.sleep(0.5)  # slight delay to ensure order

            # send game completion message
            if self.completed_players:
                # Broadcast to group so frontend knows
                await self.channel_layer.group_send(
                    self.group_name,
                    {
                        "type": "completed_game",
                        "players_still_in": self.players_list_updated,
                        "players_completed": self.game_completed_player_list,
                        "players_completed_now": self.completed_players,
                    }
                )
                time.sleep(0.5)  # slight delay to ensure order

            # get the player color dict            
            await self.channel_layer.group_send(
                self.group_name,
                {
                    "type": "clear_round",
                    "card":  self.winner_dict['card'],
                    "current_round": {},
                    "next_player": self.winner_dict["winner"],
                    "player_color_dict": self.connected_dict,
                }
            )
            
            return 
        else:
            logger.info(f"Waiting for {len(self.players_list) - len(self.played_cards)} more players.")

   
    async def check_gamecompletion_of_players(self):
        # Load players_card_list from Redis
        self.players_card_list_raw = await self.redis.hget(self.redis_key, "players_card_list")
        self.players_card_list = (
            json.loads(self.players_card_list_raw.decode())
            if self.players_card_list_raw
            else {}
        )
        self.cardList_raw = await self.redis.hget(self.redis_key, "cardList")
        self.cardList = json.loads(self.cardList_raw.decode()) if self.cardList_raw else []
        self.game_completed_player_list_raw = await self.redis.hget(self.redis_key, "game_completed_players_list")
        self.game_completed_player_list = json.loads(self.cardList_raw.decode()) if self.game_completed_player_list_raw else []
        self.current_round_data_raw=await self.redis.hget(self.redis_key, "current_round")
        self.current_round_data = json.loads(self.current_round_data_raw.decode()) if self.current_round_data_raw else {}

        # Collect players who have finished
        self.completed_players=[]
        for player, player_card_list in self.players_card_list.items():
            # If hand is empty (✅ you can drop `and not self.cardList` if you want completion
            # to be only when deck is also empty, keep it)
            # if the players card_in the current_round then , he is not completed the game
            player_check_in_current_round = any(
                player in entry for entry in self.current_round_data.get("played_cards", [])
            )
            if not player_card_list and not self.cardList:
                if player not in self.game_completed_player_list and not player_check_in_current_round:
                    self.completed_players.append(player)
                    self.game_completed_player_list.append(player)
                    logger.info(f"Player '{player}' has completed the game. completed_players: {self.completed_players} and game_completed_player_list: {self.game_completed_player_list}")

        # Remove completed players safely
        # for player in self.completed_players:
        #     self.players_card_list.pop(player, None)

        # Update main players list
            self.players_raw = await self.redis.hget(self.redis_key, "players")
            self.players_list = (
                json.loads(self.players_raw.decode())
                if self.players_raw
                else []
            )
            
        self.players_list_updated=self.players_list.copy()  # start with full list
        if self.completed_players:
            # Save updated players_card_list
            await self.redis.hset(
                self.redis_key, "players_card_list", json.dumps(self.players_card_list)
            )
            
            self.players_list_updated = [p for p in self.players_list if p not in self.completed_players]
            
            # check for the highest if all player finished:
            if len(self.players_list_updated)==0 and self.game_completed_player_list:
                logger.info(f"Game over. All players completed: {self.game_completed_player_list}")
                # determine looser whose card is highest in last round:
                # self.winner_dict['winner'] this is the looser
                # so remove the name from game_completed_player_list and then add it at the end of the list
                self.game_completed_player_list.remove(self.winner_dict['winner'])
                self.game_completed_player_list.append(self.winner_dict['winner'])
                logger.info(f"Looser is: {self.winner_dict['winner']} and game_completed_player_list: {self.game_completed_player_list}")

                await self.channel_layer.group_send(
                    self.group_name,
                    {
                        "type": "game_over",
                        "looser": self.winner_dict['winner'],
                        "game_completed_player_list": self.game_completed_player_list,
                    }
                )
                await self.redis.hset(self.redis_key, "players", json.dumps(self.players_list_updated))
                await self.redis.hset(self.redis_key, "game_completed_players_list", json.dumps(self.game_completed_player_list))
                return "GAME_OVER"

            if len(self.players_list_updated)==1 and self.game_completed_player_list: #if player_list_updated is 1 and the completed_player is not empty.list is n-1 then the last player is looser
                logger.info(f"Game over. Looser is: {self.players_list_updated[0]} and game_completed_player_list: {self.game_completed_player_list}")
                self.game_completed_player_list.append(self.players_list_updated[0])
                await self.channel_layer.group_send(
                    self.group_name,
                    {
                        "type": "game_over",
                        "looser": self.players_list_updated[0],
                        "game_completed_player_list": self.game_completed_player_list,
                    }
                )
                await self.redis.hset(self.redis_key, "players", json.dumps(self.players_list_updated))
                await self.redis.hset(self.redis_key, "game_completed_players_list", json.dumps(self.game_completed_player_list))
                return "GAME_OVER"
                #because only one player left , he is the looser.


            # check next_playeris in empty list if so change nextplaer to next to him who has card if next is empty then next like that
            # determine true next player:
            if self.next_player in self.game_completed_player_list:
                self.index_of_next_player=self.players_list.index(self.next_player)
                self.got_nextplayer=None
                while self.got_nextplayer==None:
                    self.index_of_next_player=(self.index_of_next_player+1)%len(self.players_list)
                    if self.players_list[self.index_of_next_player] not in self.game_completed_player_list:
                        self.got_nextplayer=self.players_list[self.index_of_next_player]
                        await self.redis.hset(self.redis_key, "current_player", self.got_nextplayer)
                        logger.info(f"Next player adjusted to: {self.got_nextplayer}")
                        self.next_player = self.got_nextplayer
                    
            
            await self.redis.hset(self.redis_key, "players", json.dumps(self.players_list_updated))
            await self.redis.hset(self.redis_key, "game_completed_players_list", json.dumps(self.game_completed_player_list))
            logger.info(f"Players who completed in last round: {self.completed_players}")
            logger.info(f"Players who completed totally: {self.game_completed_player_list}")


    async def check_card_suit_problem(self,card_dropped):
        """
        get the players, cardList, players_card_list

        """
        self.players_raw_p = await self.redis.hget(self.redis_key, "players")
        self.card_list_raw_p = await self.redis.hget(self.redis_key, "cardList")
        self.players_card_list_raw_p = await self.redis.hget(self.redis_key, "players_card_list")
        # decode each of this
        self.players_list_p = json.loads(self.players_raw_p.decode()) if self.players_raw_p else []
        self.card_list_p = json.loads(self.card_list_raw_p.decode()) if self.card_list_raw_p else []
        self.players_card_list_p = json.loads(self.players_card_list_raw_p.decode()) if self.players_card_list_raw_p else {}
        
        if len(self.players_list_p)==2 and len(self.card_list_p)==0:
            # player1_card=get all the cards from player1
            # player2_card=get all the cards from player2
            # total_number_of_cards=len(players1_card)+len(player2_card)
            self.player1_card=self.players_card_list_p[self.players_list_p[0]]
            self.player2_card=self.players_card_list_p[self.players_list_p[1]]
            total_number_of_cards=len(self.player1_card)+len(self.player2_card)
            
            
            if total_number_of_cards==3 or total_number_of_cards==4:
                self.player1_suits = {card[0] for card in self.player1_card}
                self.player2_suits = {card[0] for card in self.player2_card}
                #find the other player than current player.
                
                #get the current_player from redis
                self.current_player_raw = await self.redis.hget(self.redis_key, "current_player")
                self.current_player = self.current_player_raw.decode() if self.current_player_raw else None
                self.other_player = self.players_list_p[1] if self.current_player == self.players_list_p[0] else self.players_list_p[0]
                self.other_player_card_list=self.players_card_list_p[self.other_player]

                # if any player doe not have cards then return False
                if len(self.players_card_list_p[self.current_player])==0 or len(self.players_card_list_p[self.other_player])==0:
                    logger.info("one of the player doe not have any card")
                    return False

                # if the card_dropped suit is present in other players cards_list then return False:
                for card in self.other_player_card_list:
                    if card_dropped[0] == card[0]:
                        return False

                if len(self.other_player_card_list)==1 : #if other player has only one card then no need to check the suit problem he will smash this current_player and win
                    logger.info("other player has only one card so no suit problem")
                    return False
               
                #for 4 card scenario handle
                if (len(self.players_card_list_p[self.current_player]))==1 and len(self.players_card_list_p[self.other_player])==3:
                    #if current player has only one card and other player has 3 cards then let the other player has to trigger red day to give one card to current player.
                    return False
                
                # if len(self.players_card_list_p[self.current_player])==3 and len(self.players_card_list_p[self.other_player])==0:
                #     #if current player has only three cards and other player has no cards then let the other player has to trigger red day to give one card to other player who dropped his card player.
                #     return False
                
                if total_number_of_cards==4:
                    logger.info("total_number_of_cards is 4")
                    if (len(self.players_card_list_p[self.current_player]))==2 and len(self.players_card_list_p[self.other_player])==2:
                        #if each players have 2 cards and then if anyone has same suit 2 cards of same suit with him then he will have winning posibility so return false
                        # check for current_player
                        suit_check={"player1": {}, "player2": {}}
                        for card in self.player1_card:
                            if card[0] in suit_check["player1"]:
                                suit_check["player1"][card[0]] += 1
                                if suit_check["player1"][card[0]]==2:
                                    return False
                            else:
                                suit_check["player1"][card[0]] = 1
                        for card in self.player2_card:
                            if card[0] in suit_check["player2"]:
                                suit_check["player2"][card[0]] += 1
                                if suit_check["player2"][card[0]]==2:
                                    return False
                            else:
                                suit_check["player2"][card[0]] = 1
                            
                #for 3 card scenario handle
                #no need to handle because its a card_problem handled below by giving extra cards.

                Flag=True
                for suit in self.player1_suits:
                    if suit in self.player2_suits:
                        Flag=False
                        break
                if Flag:  #means no matching suits in both players
                    #declare as the card_problem
                    self.card_problem_dict = {
                        "card_problem": True,
                        "players": {
                            self.players_list_p[0]: {"watched_card": False, "cards": self.player1_card, "number_of_cards": len(self.player1_card)},
                            self.players_list_p[1]: {"watched_card": False, "cards": self.player2_card, "number_of_cards": len(self.player2_card)}
                        },
                        "total_number_of_cards": total_number_of_cards
                    
                    }
                    await self.redis.hset(self.redis_key, "card_problem", json.dumps(self.card_problem_dict))
                    # send message to the frontend
                    
                    await self.channel_layer.group_send(
                        self.group_name,
                        {
                            "type": "card_problem",
                            "message":"You both have different Suits of cards So,Game will not be finished.Please click on see opponent cards and continue the game",
                            "players": self.players_list_p,
                            "other_player_card_list": self.players_card_list_p
                        }
                    )
                    return True
        return False

    async def determine_next_player_for_normal_card(self):
        self.players_raw = await self.redis.hget(self.redis_key, "players")
        self.players_list = json.loads(self.players_raw.decode()) if self.players_raw else []

        self.current_player_raw = await self.redis.hget(self.redis_key, "current_player")
        self.next_player = self.current_player_raw.decode()

        if self.players_list:
            # Find the next player who is NOT in game_completed_player_list
            self.current_player_index = self.players_list.index(self.next_player)
            self.next_player=self.players_list[(self.current_player_index+1)%len(self.players_list)]
            await self.redis.hset(self.redis_key, "current_player", self.next_player)
        
    async def update_gamedata_to_db(self):
        inserted_to_db = await self.redis.hget(self.redis_key, "inserted_to_db")
        if inserted_to_db == b"True":
            logger.info("Game data already inserted to DB. Skipping duplicate insertion.")
            return

        

        async def parse_json(value):
            try:
                decoded_value = value.decode() if isinstance(value, bytes) else value
                logger.info(f"value:{decoded_value} json.loads(decoded_value){json.loads(decoded_value)}")
                return json.loads(decoded_value)
            except Exception:
                return decoded_value

        # ✅ Properly decode keys and values
        raw_data = await self.redis.hgetall(self.redis_key)
        clean_data = {k.decode(): await parse_json(v) for k, v in raw_data.items()}

        await sync_to_async(CompletedGame.objects.create)(
            room_id=self.redis_key.split(":")[1],
            selected_game=clean_data.get("selected_game", ""),
            owner=clean_data.get("owner", ""),
            players=clean_data.get("players", []),
            players_connected_list=clean_data.get("players_connected_list", {}),
            players_card_list=clean_data.get("players_card_list", {}),
            played_card_list=clean_data.get("played_card_list", []),
            game_completed_players_list=clean_data.get("game_completed_players_list", []),
            starting_player=clean_data.get("starting_player", ""),
            current_player=clean_data.get("current_player", ""),
            status=clean_data.get("status", ""),
            card_distributed_flag=bool(int(clean_data.get("card_distributed_flag", 0))),
            duplicate_owner_login=bool(int(clean_data.get("duplicate_owner_login", 0))),
            card_problem=clean_data.get("card_problem", {}),
            current_round=clean_data.get("current_round", {}),
            cardList=clean_data.get("cardList", []),
            gamelist=clean_data.get("gamelist", []),
        )

        await self.redis.hset(self.redis_key, "inserted_to_db", "True")
        logger.info(f"✅ Game data for {self.redis_key} successfully saved to DB.")
        
        # get the list of players who completed the game
        completed_players = clean_data.get("game_completed_players_list", [])
        players = clean_data.get("players", [])

        for username in completed_players:
            # Use sync_to_async to work with Django ORM in async function
            async def update_stats():
                stats, created = await sync_to_async(PlayerStats.objects.get_or_create)(username=username)
                stats.number_of_games_played += 1
                if username in players:
                    stats.number_of_games_lost += 1  # assuming the last player in completed list lost
                else:
                    stats.number_of_games_won += 1  # assuming all completed players won
                await sync_to_async(stats.save)()
                logger.info(f"Updated PlayerStats: {username} - Played: {stats.number_of_games_played}, Won: {stats.number_of_games_won}")

            await update_stats()

        logger.info("✅ PlayerStats updated for completed players.")

    async def drop_play_card_to_table(self,card):
        self.next_player=None
        self.game_over_flag="None"
        # validate user has that card
        # validate the card is valid for the crrent_round
        # if both assed then allow and update in the current round and update currentplayer to next player
        # if all the player have put one then, store the current round data in played_card_list and then clear the current card and update the net player as the highest number of card played player name
        self.RANK_ORDER = {
            "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8, "9": 9,
            "10": 10, "J": 11, "Q": 12, "K": 13, "A": 14
        }

        def card_value(card: str) -> int:
            """Return numeric value of a card like 'D9', 'HQ', 'SA'."""
            # card format: suit + rank (example: "D9", "HQ")
            rank = card[1:]  # everything except first char is rank
            return self.RANK_ORDER.get(rank, 0)

        try:
            # Fetch required data from Redis
            self.players_card_raw = await self.redis.hget(self.redis_key, "players_card_list")
            self.current_player_raw = await self.redis.hget(self.redis_key, "current_player")
            self.current_round_raw = await self.redis.hget(self.redis_key, "current_round")
            self.played_card_list_raw = await self.redis.hget(self.redis_key, "played_card_list")

            self.card=card
            if not self.players_card_raw or not self.current_player_raw:
                await self.send_dynamic_message("error", "Game state missing or corrupted")
                return

            # Decode Redis values
            self.players_card_dict = json.loads(self.players_card_raw.decode())
            self.current_player = self.current_player_raw.decode()
            self.current_round = json.loads(self.current_round_raw.decode()) if self.current_round_raw else {}
            self.played_card_list = json.loads(self.played_card_list_raw.decode()) if self.played_card_list_raw else []

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
                # if the player is the next player in round
                self.required_suit = self.current_round.get("required_suit")
                if self.required_suit and not card.startswith(self.required_suit):

                    # check whether card_list is not empty, 
                    # if not empty fail the red_daytrigger and send the error message saying please take card from deck
                    self.card_list_raw = await self.redis.hget(self.redis_key,"cardList")
                    self.card_list = json.loads(self.card_list_raw.decode()) if self.card_list_raw else []
                    if self.card_list:
                        await self.send_dynamic_message("error", "please take card from deck")
                        return

                    # After validating card and before setting next_player
                    # Add Red Day handling
                    # If required suit exists but player has no such suit (and no deckpile card),
                    # then trigger red day logic
                    logger.info("Checking for RED DAY condition...")
                    self.has_required_suit = any(c.startswith(self.required_suit) for c in self.player_cards)
                    if not self.has_required_suit:
                        # 🔴 RED DAY situation
                        logger.info(f"RED DAY triggered by {self.username}")

                        # 1. Decide winner among rest players (highest card)
                        self.rest_cards = [
                            (list(c.keys())[0], list(c.values())[0])
                            for c in self.current_round["played_cards"]
                        ]
                         # 2. Add played card as normal
                        self.current_round["played_cards"].append({self.username: self.card})
                        if self.rest_cards:
                            self.winner, winning_card = max(
                                self.rest_cards,
                                key=lambda x: card_value(x[1])   # compare based on rank order
                            )
                        else:
                            self.winner, winning_card = None, None
                        # 3. Save red_day info
                        self.current_round["red_day"] = {
                            "from": self.username,
                            "to": self.winner,
                            "cards_given": self.card,
                            "rest_cards": [c for c in self.current_round["played_cards"] if list(c.keys())[0] != self.username]
                        }

                        # 4. Next player is same user
                        # check whether smasher has card
                        # if yes set him as next player 
                        # else keep on going t find next player to right until who has card.
                        # eliminate the players from players_list who has no cards from "players"
                        # add them to "game_completed_players_list" and send the message to all
                        # send next player to all 
                        self.next_player = self.username

                        # 5. Update Redis atomically
                        pipe = self.redis.pipeline()
                        pipe.hset(self.redis_key, "current_round", json.dumps(self.current_round))
                        pipe.hset(self.redis_key, "current_player", self.next_player)
                        await pipe.execute()

                        # Add all cards from the current round to the winner + winning_card
                        if self.winner:
                            self.players_card_dict[self.winner] = (
                                self.players_card_dict.get(self.winner, []) +
                                [card for play in self.current_round["played_cards"] for card in play.values()]
                            )

                        # List of all cards in the current round except self.card to reduce duplicate self.card display in frontend
                        self.current_round_card_list = [
                            card for play in self.current_round["played_cards"] for card in play.values() if card!=self.card
                        ]

                        # add current_round data to the "played_card_list"
                        pipe = self.redis.pipeline()
                        # get the played_card_list and add the current_round and then set it again to redis
                        # remove played card from the player who smashed
                        self.hand_cards = self.players_card_dict.get(self.username, [])
                        if self.card in self.hand_cards:
                            self.hand_cards.remove(self.card)   # modifies the list that's stored in the dict
                            self.players_card_dict[self.username] = self.hand_cards
                            logger.info(f"The card has been removed from smasher{self.card}")
                        pipe = self.redis.pipeline()
                        pipe.hset(self.redis_key, "players_card_list", json.dumps(self.players_card_dict))
                        self.played_card_list.append(self.current_round)
                        pipe.hset(self.redis_key, "played_card_list", json.dumps(self.played_card_list))
                        pipe.hset(self.redis_key, "current_round", json.dumps({}))
                        await pipe.execute()

                        # check whether smashed player has card if not then next player beside him is the next round starter
                        self.game_over_flag=await self.check_gamecompletion_of_players() 
                        if self.game_over_flag=="GAME_OVER":
                            # add looser to the game_completed player
                            logger.info("Game over after RED DAY. Saving game data to DB...")
                            return  # stop further processing as game is over
                        
                        # 6. Broadcast RED DAY to all
                        logger.info(f"next player:{self.next_player}Broadcasting RED DAY: {self.username} → {self.winner} with card {self.card}")
                        await self.channel_layer.group_send(
                            self.group_name,
                            {
                                "type": "red_day_triggered",
                                "from_player": self.username,
                                "to_winner": self.winner,
                                "card_given": self.card,
                                "current_round": self.current_round,
                                "next_player": self.next_player,
                                "player_color_dict": self.players_card_dict[self.username],
                                "current_round_card_list": self.current_round_card_list,
                                
                            }
                        )
                        time.sleep(0.5)  # slight delay to ensure order
                        if self.completed_players:
                            # Broadcast to group so frontend knows
                            await self.channel_layer.group_send(
                                self.group_name,
                                {
                                    "type": "completed_game",
                                    "players_still_in": self.players_list_updated,
                                    "players_completed": self.game_completed_player_list,
                                    "connected_dict": self.connected_dict,
                                    "players_completed_now": self.completed_players,
                                }
                            )
                       
                        return  # 🚪 stop normal flow, handled separately
                         
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
            await self.determine_next_player_for_normal_card() 

            # Validate if the current player's turn is complete
            await self.validate_round_completion()
            if self.game_over_flag=="GAME_OVER":
                return  # stop further processing as game is over

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
    
    
    async def handle_extra_card_request_validation(self):
        # Get current round
        current_round_raw = await self.redis.hget(self.redis_key, "current_round")
        current_round = json.loads(current_round_raw.decode()) if current_round_raw else {}

        # Check if player already played
        played_cards_list = current_round.get("played_cards", [])
        if any(self.username in played_card for played_card in played_cards_list):
            logger.info(f"Player '{self.username}' has already played this round.")
            await self.send(text_data=json.dumps({
                "type": "error",
                "message": "You already completed the round!"
            }))
            return True  # block further processing

        # Get player's cards
        current_player_cards_raw = await self.redis.hget(self.redis_key, "players_card_list")
        current_player_cards = json.loads(current_player_cards_raw.decode()) if current_player_cards_raw else {}
        player_cards = current_player_cards.get(self.username, [])

        # Get required suit
        required_suit = current_round.get("required_suit", "")

        # Check if player has a card of the required suit
        if any(card[0] == required_suit for card in player_cards):
            logger.info(f"Player '{self.username}' has a card of the required suit '{required_suit}'. Cannot borrow.")
            await self.send(text_data=json.dumps({
                "type": "error",
                "message": "You have the card, do not borrow!"
            }))
            return True  # block further processing

        return False  # safe to allow borrowing


    async def handle_extra_card_request(self):
        """
        Handles 'get_extra_card_from_deck' request:
        1. Draws random cards from the deck until a card of required suit is found
        or deck is empty.
        2. Updates player's card list in Redis.
        3. Always returns the cards drawn so far, even if no match found.
        """
        # Get current round
        self.current_round_raw = await self.redis.hget(self.redis_key, "current_round")
        self.current_round = json.loads(self.current_round_raw.decode()) if self.current_round_raw else {}
        self.required_suits = self.current_round.get("required_suit", [])

        # Get deck and player cards
        self.card_list_raw = await self.redis.hget(self.redis_key,"cardList")
        self.card_list = json.loads(self.card_list_raw.decode()) if self.card_list_raw else []

        self.players_cards_raw = await self.redis.hget(self.redis_key, "players_card_list")
        self.players_cards = json.loads(self.players_cards_raw.decode()) if self.players_cards_raw else {}
        self.player_cards = self.players_cards.get(self.username, [])

        # Draw cards until a required suit is found or deck is empty
        self.drawn_cards = []
        while self.card_list:            
            self.card = random.choice(self.card_list)

            if not self.required_suits: 
                # represents he is the starter of the round
                # check players hand empty or not, if empty then only send card else, send proper error message you already have card
                # get only one card and break the loop
                if not self.player_cards:
                    self.drawn_cards.append(self.card)
                    self.player_cards.append(self.card)
                    self.card_list.remove(self.card)
                    logger.info("No cards in players hand, drew one card.")
                else:
                    logger.info("Player already has cards, cannot draw.")
                break
            else:
                self.drawn_cards.append(self.card)
                self.player_cards.append(self.card)
                self.card_list.remove(self.card)

                if self.card[0] in self.required_suits:
                    logger.info(f"Found required suit card: {self.card}")
                    break  # stop once a required suit is found
            

        # Update Redis
        self.players_cards[self.username] = self.player_cards
        logger.info(f"players_cards[self.username]: {self.players_cards[self.username]}")
        await self.redis.hset(self.redis_key, "players_card_list", json.dumps(self.players_cards))
        await self.redis.hset(self.redis_key, "cardList", json.dumps(self.card_list))

        # Send new card info
        await self.send(json.dumps({
            "type": "extra_card",
            "new_cards": self.drawn_cards,
            "full_cards": self.player_cards
        }))
        # add delay
        await asyncio.sleep(0.1)
        # send the cardList length
        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "deck_pile_count",
                "cardListLength": len(self.card_list),               
            }
        )
        await asyncio.sleep(0.1)

        await self.send_dynamic_group_message( "error", f"Player {self.username} got {len(self.drawn_cards)} extra cards from deck")
        
        
        return False  # continue processing if needed


    async def handle_saw_the_card(self):
        logger.info("Handling saw_the_card request")
        self.card_problem_handle_saw_raw = await self.redis.hget(self.redis_key, "card_problem")
        self.card_problem_handle_saw = json.loads(self.card_problem_handle_saw_raw.decode()) if self.card_problem_handle_saw_raw else {}
        
        if self.card_problem_handle_saw["players"][self.username]["watched_card"]:
            await self.send_dynamic_message( "watching_card_again", "Alreday resolved the card problem, no need to watch again")
            return

        if self.username in self.card_problem_handle_saw.get("players", {}):
            self.card_problem_handle_saw["players"][self.username]["watched_card"] = True
            # get the total_number_of_cards and check how many cards the user has
            # if the total card number is 4 and the username has 2 cards then get 3 extra card form the new deck which is not present in both players cards.  which is not present in both players cards.
            # if the total card number is 3 and the user has 2 cards then get 3 extra card from the new deck if the username has 1 card then give  4 extra cards which is not present in both players cards.
            total_number_of_cards=self.card_problem_handle_saw.get("total_number_of_cards",0)
            user_number_of_cards=self.card_problem_handle_saw["players"][self.username].get("number_of_cards",0)
            number_of_extra_cards_to_give=0
            if (total_number_of_cards==4 or total_number_of_cards==3) and user_number_of_cards==2:
                number_of_extra_cards_to_give=3
            elif total_number_of_cards==3 and user_number_of_cards==1:
                number_of_extra_cards_to_give=4
            
            SUITS = ['F', 'S', 'H', 'D']
            RANKS = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
            FULL_DECK = [f"{suit}{rank}" for suit in SUITS for rank in RANKS]
            existing_cards = []

            # get the cards from the both players and put it in existing_cards from played_card_list
            self.players_card_raw_handle_card_problem = await self.redis.hget(self.redis_key, "players_card_list")
            # {"User3": ["F5", "F8", "HK", "F3", "D8"], "Billabigbull": []}
            self.players_card_dict_handle = json.loads(self.players_card_raw_handle_card_problem.decode()) if self.players_card_raw_handle_card_problem else {}
            for player_info in self.players_card_dict_handle.values():
                existing_cards.extend(player_info.get("cards", []))

            # for player_info in self.card_problem_handle_saw["players"].values():
            #     existing_cards.extend(player_info.get("cards", []))
            available_cards = [card for card in FULL_DECK if card not in existing_cards]
            random.shuffle(available_cards)       

            # get the number_of_extra_cards_to_give to the username
            if number_of_extra_cards_to_give > 0:
                extra_cards = available_cards[:number_of_extra_cards_to_give]
                self.card_problem_handle_saw["players"][self.username]["extra_cards"] = extra_cards
            # update Redis
            await self.redis.hset(self.redis_key, "card_problem", json.dumps(self.card_problem_handle_saw))

            # update total cards in the layers_card_list on redis
            logger.info(f"Extra cards given to {self.username}: {self.card_problem_handle_saw['players'][self.username].get('extra_cards', [])}")
            self.players_card_raw = await self.redis.hget(self.redis_key, "players_card_list")
            self.players_card_dict = json.loads(self.players_card_raw.decode()) if self.players_card_raw else {}
            self.player_cards = self.players_card_dict.get(self.username, [])
            self.player_cards.extend(self.card_problem_handle_saw["players"][self.username].get("extra_cards", []))
            self.players_card_dict[self.username] = self.player_cards
            await self.redis.hset(self.redis_key, "players_card_list", json.dumps(self.players_card_dict))
            logger.info(f"Updated players_card_list for {self.username}: {self.players_card_dict[self.username]}")


            if all(player_info.get("watched_card") for player_info in self.card_problem_handle_saw["players"].values()):
                # Clear the card problem
                await self.redis.hset(self.redis_key, "card_problem", json.dumps({"card_problem": False}))
                logger.info("Both players have watched their cards. Card problem cleared.")

            await self.send(text_data=json.dumps({
                "type": "saw_card_ack",
                "message": "You have acknowledged seeing your card.",
                "extra_cards": self.card_problem_handle_saw["players"][self.username].get("extra_cards", []),
                "updated_player_cards": self.player_cards,
                "connected_dict": self.connected_dict
            }))
        
        else:
            await self.send(text_data=json.dumps({
                "type": "error",
                "message": "You are not part of the current card problem"
            }))



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
                if (await self.check_card_suit_problem(data.get("card"))):
                    logger.info("Card suit problem detected, aborting play_card.")
                    return  # stop further processing if card problem detected
                else:
                    await self.drop_play_card_to_table(data.get("card"))
                    logger.info("after drop_play_card_to_table")

            elif msg_type=="saw_the_card":
                logger.info("calling saw the card")
                await self.handle_saw_the_card()
           
            elif msg_type == "get_extra_card_from_deck":
                if await self.handle_extra_card_request_validation():
                    logger.info("Extra card request validation failed.")
                    self.send_dynamic_message("error", "You Aleady have card of reuired suit")
                    return  # stop further processing
                # Proceed to give extra card
                await self.handle_extra_card_request()


            else:
                logger.warning(f"Unhandled message type: {msg_type}")
        except Exception as e:
            logger.error(f"Error handling receive: {e}", exc_info=True)
            await self.send(text_data=json.dumps({"type": "error", "message": "Server error"}))
