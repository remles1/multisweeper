from typing import List, TYPE_CHECKING, Dict, Union

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
    players: List[User]
    player_scores: dict[Union[User, str], int]  # str is for the guest
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

    def add_player(self, player_connection: 'PlayerConsumer'):
        if self.current_players >= self.max_players:
            return
        if len(self.players) == 0:
            self.owner = player_connection.player
        self.current_players += 1
        self.players.append(player_connection.player)
        self.player_connections[player_connection.player] = player_connection

        if isinstance(player_connection.player, User):
            self.player_profiles[player_connection.player] = PlayerProfile.objects.get(user=player_connection.player)

        self.player_scores[player_connection.player] = 0

    def remove_player(self, player_connection: 'PlayerConsumer'):
        self.current_players -= 1
        self.players.remove(player_connection.player)
        del self.player_connections[player_connection.player]
        if isinstance(player_connection.player, User):
            del self.player_profiles[player_connection.player]
        del self.player_scores[player_connection.player]

    def left_click_game(self, y, x, player_connection: 'PlayerConsumer'):

        player_index = self.players.index(player_connection.player)
        if player_index != self.active_player or self.game_instance.user_board[y][x] != "c":
            return
        self.game_instance.cell_left_clicked(y, x, player_index)

        if self.game_instance.logic_board[y][x] != -1:
            self.active_player = (self.active_player + 1) % self.max_players
        else:
            self.player_scores[player_connection.player] += 1

    def broadcast(self):
        print(self.players)
        for player_connection in self.player_connections.values():
            player_connection.send_user_board()
