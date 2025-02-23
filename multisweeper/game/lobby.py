from typing import List, TYPE_CHECKING

from django.contrib.auth.models import User

from multisweeper.game.game_logic import GameLogic
from multisweeper.models import PlayerProfile

if TYPE_CHECKING:
    from multisweeper.consumers import PlayerConsumer

lobbies = {}


class Lobby:
    lobby_id: str
    max_players: int
    current_players: int = 0
    players: List[User]
    player_profiles: List[PlayerProfile]
    player_connections: List['PlayerConsumer']
    active_player: int = 0
    game_instance: GameLogic

    def __init__(self, lobby_id, max_players=2):
        self.lobby_id = lobby_id
        self.max_players = max_players
        self.players = []
        self.player_profiles = []
        self.player_connections = []
        self.game_instance = GameLogic(difficulty='intermediate', width=16, height=16, mine_count=60)

    def add_player(self, player_connection: 'PlayerConsumer'):
        self.current_players += 1
        self.player_connections.append(player_connection)
        self.players.append(player_connection.player)
        self.player_profiles.append(PlayerProfile.objects.get(user=player_connection.player))

    def remove_player(self, player_connection: 'PlayerConsumer'):
        self.current_players -= 1
        self.player_connections.remove(player_connection)
        self.players.remove(player_connection.player)
        self.player_profiles.remove(PlayerProfile.objects.get(user=player_connection.player))

    def left_click_game(self, y, x, player):

        player_index = self.player_connections.index(player)
        if player_index != self.active_player:
            return
        self.game_instance.cell_left_clicked(y, x, player_index)

        if self.game_instance.logic_board[y][x] != -1:
            self.active_player = (self.active_player + 1) % self.max_players

    def broadcast(self):
        print([p.player.username for p in self.player_connections])
        print("active player:", self.active_player)
        for player in self.player_connections:
            player.send_user_board()
