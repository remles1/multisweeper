import json
from typing import Union

from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth.models import User
from asgiref.sync import sync_to_async

from multisweeper.game.lobby import Lobby, lobbies


class PlayerConsumer(AsyncWebsocketConsumer):
    player: Union[User, str]
    lobby: Lobby

    async def connect(self):
        self.player = self.scope["user"]
        if not self.player.is_authenticated:
            self.player = self.scope["session"]["username"]

        lobby_id = self.scope['url_route']['kwargs']['lobby_id']

        await self.join_lobby(lobby_id)

        await self.accept()

        await self.lobby.broadcast(self.lobby.create_user_board_json())

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)

        message = text_data_json["message"]
        split_message = message.split('-')
        y = int(split_message[0])
        x = int(split_message[1])

        if text_data_json["type"] == "l_click":
            await self.lobby.left_click_game(y, x, self)
        await self.lobby.broadcast(self.lobby.create_user_board_json())

    async def disconnect(self, close_code):
        await self.lobby.remove_player(self)

    async def join_lobby(self, lobby_id):
        self.lobby = lobbies[lobby_id]
        await self.lobby.add_player(player_connection=self)

    async def send_message(self, event):
        await self.send(text_data=event['content'])
