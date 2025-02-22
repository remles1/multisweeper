import json

from channels.generic.websocket import WebsocketConsumer

from multisweeper.game.lobby import Lobby, lobbies


class PlayerConsumer(WebsocketConsumer):
    lobby: Lobby

    def connect(self):
        lobby_id = self.scope['url_route']['kwargs']['lobby_id']
        print(lobby_id)
        self.join_lobby(lobby_id)

        self.accept()

        self.send_user_board()

    def receive(self, text_data):
        text_data_json = json.loads(text_data)

        if text_data_json["type"] == "open":
            print("open works")

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
        print(lobbies)

    def join_lobby(self, lobby_id):

        self.lobby = lobbies[lobby_id]
