import os
from typing import List

from multisweeper.game.game_logic import GameLogic

lobbies = {}


class Lobby:
    lobby_id: str
    player_count: int
    players: List  # index is the order in which players play
    game_instance: GameLogic

    def __init__(self, player_count=2):
        self.lobby_id = os.urandom(8).hex()
        self.player_count = player_count
        self.players = []
        self.game_instance = GameLogic(difficulty='intermediate', width=16, height=16, mine_count=30)

    def add_player(self, player):
        self.players.append(player)

    def remove_player(self, player):
        self.players.remove(player)
