import os
from typing import List, TYPE_CHECKING

from multisweeper.game.game_logic import GameLogic

if TYPE_CHECKING:
    from multisweeper.consumers import PlayerConsumer

lobbies = {}


class Lobby:
    lobby_id: str
    player_count: int
    players: List['PlayerConsumer']  # Use string annotation
    active_player = 0
    game_instance: GameLogic

    def __init__(self, player_count=2):
        self.lobby_id = os.urandom(8).hex()
        self.player_count = player_count
        self.players = []
        self.game_instance = GameLogic(difficulty='intermediate', width=16, height=16, mine_count=60)

    def add_player(self, player: 'PlayerConsumer'):
        self.players.append(player)

    def remove_player(self, player: 'PlayerConsumer'):
        self.players.remove(player)

    def left_click_game(self, y, x, player):

        player_index = self.players.index(player)
        if player_index != self.active_player:
            return
        self.game_instance.cell_left_clicked(y, x, player_index)

        if self.game_instance.logic_board[y][x] != -1:
            self.active_player = (self.active_player + 1) % self.player_count


    def broadcast(self):
        print([p.player.username for p in self.players])
        print("active player:",self.active_player)
        for player in self.players:
            player.send_user_board()