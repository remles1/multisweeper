import asyncio
import json
from typing import List, TYPE_CHECKING, Dict, Union

from asgiref.sync import sync_to_async
from django.contrib.auth.models import User

from multisweeper.game.game_logic import GameLogic
from multisweeper.models import PlayerProfile

if TYPE_CHECKING:
    from multisweeper.consumers import PlayerConsumer

lobbies = {}


class Lobby:
    lobby_id: str
    owner: User
    game_started: bool = False
    max_players: int
    current_players: int = 0
    players: List[Union[User, str]]  # str is for the guest
    player_scores: dict[Union[User, str], int]
    player_profiles: Dict[Union[User, str], PlayerProfile | None]
    player_connections: Dict[Union[User, str], 'PlayerConsumer']
    active_player: int = 0
    game_instance: GameLogic

    def __init__(self, lobby_id, max_players=2):
        self.lobby_id = lobby_id
        self.max_players = max_players
        self.players = []
        self.player_profiles = {}
        self.player_connections = {}
        self.player_scores = {}
        self.game_instance = GameLogic(difficulty='intermediate', width=16, height=16, mine_count=20)
        self.lock = asyncio.Lock()

    async def add_player(self, player_connection: 'PlayerConsumer'):
        async with self.lock:
            if self.current_players >= self.max_players:
                return
            if len(self.players) == 0:
                self.owner = player_connection.player
            self.current_players += 1
            self.players.append(player_connection.player)
            self.player_connections[player_connection.player] = player_connection

            if isinstance(player_connection.player, User):
                self.player_profiles[player_connection.player] = await PlayerProfile.objects.aget(user=player_connection.player)

            self.player_scores[player_connection.player] = 0

    async def remove_player(self, player_connection: 'PlayerConsumer'):
        async with self.lock:
            self.current_players -= 1
            self.players.remove(player_connection.player)
            del self.player_connections[player_connection.player]
            if isinstance(player_connection.player, User):
                del self.player_profiles[player_connection.player]
            del self.player_scores[player_connection.player]

    async def left_click_game(self, y, x, player_connection: 'PlayerConsumer'):
        async with self.lock:
            player_index = self.players.index(player_connection.player)
            if player_index != self.active_player or self.game_instance.user_board[y][x] != "c":
                return
            self.game_instance.cell_left_clicked(y, x, player_index)

            if self.game_instance.logic_board[y][x] != -1:
                self.active_player = (self.active_player + 1) % self.max_players
            else:
                self.player_scores[player_connection.player] += 1

    async def broadcast(self, content):
        for player_connection in self.player_connections.values():
            await player_connection.send_json(content)

    def create_user_board_json(self):
        user_board_json = json.dumps(self.game_instance.user_board)
        content = json.dumps({
            "type": "user_board",
            "won": self.game_instance.game_won,
            "over": self.game_instance.game_over,
            "time": self.game_instance.time_spent,
            "message": user_board_json
        })
        return content
