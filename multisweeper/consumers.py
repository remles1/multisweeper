import json
from typing import Union

from channels.generic.websocket import WebsocketConsumer
from django.contrib.auth.models import User

from multisweeper.game.lobby import Lobby, lobbies


class PlayerConsumer(WebsocketConsumer):
    player: Union[User, str]
    lobby: Lobby

    def connect(self):
        self.player = self.scope["user"]
        if not self.player.is_authenticated:
            self.player = self.scope["session"]["username"]

        lobby_id = self.scope['url_route']['kwargs']['lobby_id']

        self.join_lobby(lobby_id)

        self.accept()

        self.lobby.broadcast()

    def receive(self, text_data):
        text_data_json = json.loads(text_data)

        message = text_data_json["message"]
        split_message = message.split('-')
        y = int(split_message[0])
        x = int(split_message[1])

        if text_data_json["type"] == "l_click":
            self.lobby.left_click_game(y, x, self)
        self.lobby.broadcast()

    def send_user_board(self):
        user_board_json = json.dumps(self.lobby.game_instance.user_board)
        self.send(text_data=json.dumps({
            "type": "user_board",
            "won": self.lobby.game_instance.game_won,
            "over": self.lobby.game_instance.game_over,
            "time": self.lobby.game_instance.time_spent,
            "message": user_board_json
        })
        )

    def disconnect(self, close_code):
        self.lobby.remove_player(self)

    def join_lobby(self, lobby_id):
        self.lobby = lobbies[lobby_id]
        self.lobby.add_player(player_connection=self)
