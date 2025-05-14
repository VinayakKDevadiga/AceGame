import json
from channels.generic.websocket import AsyncWebsocketConsumer
from urllib.parse import parse_qs

class WaitRoomConsumer(AsyncWebsocketConsumer):
    # async def connect(self):
    #     self.room_id = self.scope['url_route']['kwargs']['room_id']
    #     self.group_name = f"room_{self.room_id}"

    #     await self.channel_layer.group_add(
    #         self.group_name,
    #         self.channel_name
    #     )

    #     await self.accept()

    #     # Get the username from query string or session
    #     username = self.scope["session"].get("username", "Anonymous")

    #     # Send username to group
    #     await self.channel_layer.group_send(
    #         self.group_name,
    #         {
    #             'type': 'player_joined',
    #             'username': username
    #         }
    #     )
    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.group_name = f"room_{self.room_id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        query_string = self.scope['query_string'].decode()
        username = parse_qs(query_string).get('username', ['Anonymous'])[0]

        await self.channel_layer.group_send(
            self.group_name,
            {
                'type': 'player_joined',
                'username': username
            }
        )

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    async def player_joined(self, event):
        await self.send(text_data=json.dumps({
            'username': event['username']
        }))
