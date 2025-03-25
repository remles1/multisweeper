import json
from typing import Union

from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth.models import User

from multisweeper.game.lobby import Lobby, lobbies

MAX_PACKET_SIZE = 1024


class PlayerConsumer(AsyncWebsocketConsumer):
    player: Union[User, str]
    lobby: Lobby

    async def connect(self):
        self.player = self.scope["user"]

        if not self.player.is_authenticated:
            self.player = self.scope["session"]["username"]

        lobby_id = self.scope['url_route']['kwargs']['lobby_id']

        await self.join_lobby(lobby_id)
        await self.lobby.add_player(self)

        await self.accept()

        await self.lobby.broadcast(self.lobby.create_user_board_json())

        username = self.player.username if isinstance(self.player, User) else self.player

        await self.send(text_data=json.dumps({
            "type": "username",
            "message": f"{username}"
        }))

        await self.send(self.lobby.create_state_json())

    async def receive(self, text_data):
        if len(text_data) > MAX_PACKET_SIZE:
            await self.close(code=1009)
            return
        try:
            text_data_json = json.loads(text_data)
        except json.JSONDecodeError:
            print("Invalid JSON")
            return

        if text_data_json["type"] == "l_click":
            message = text_data_json["message"]
            split_message = message.split('-')
            y = int(split_message[0])
            x = int(split_message[1])
            await self.lobby.left_click_game(y, x, self)
            await self.lobby.broadcast_board_and_interface()
        elif text_data_json["type"] == "bomb":
            message = text_data_json["message"]
            split_message = message.split('-')
            y = int(split_message[0])
            x = int(split_message[1])
            await self.lobby.bomb_used(y, x, self)
            await self.lobby.broadcast_board_and_interface()
        elif text_data_json["type"] == "choose_seat":
            await self.lobby.choose_seat(self, text_data_json["message"])
        elif text_data_json["type"] == "promote_to_owner":
            await self.lobby.promote_to_owner(self, text_data_json["message"])
        elif text_data_json["type"] == "start_game":
            await self.lobby.start_game(self)
        elif text_data_json["type"] == "chat_message":
            await self.lobby.chat_manager.process_user_message(message=text_data_json["message"], sender=self.player)

    async def disconnect(self, close_code):
        await self.lobby.remove_player(self)
        await self.lobby.broadcast(self.lobby.create_seats_json())

    async def join_lobby(self, lobby_id):
        self.lobby = lobbies[lobby_id]

    async def send_message(self, event):
        await self.send(text_data=event['content'])
