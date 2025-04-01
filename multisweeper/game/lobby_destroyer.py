import asyncio
from typing import TYPE_CHECKING

from multisweeper.game.lobbies_register import lobbies

if TYPE_CHECKING:
    from multisweeper.game.lobby import Lobby


class LobbyDestroyer:
    def __init__(self, lobby: "Lobby"):
        self.lobby = lobby
        self.running = False

    async def wait_for_players_to_join(self):
        if self.running:
            return

        self.running = True

        await asyncio.sleep(10)
        if self.lobby.lobby_id in lobbies and self.lobby.current_players == 0:
            del lobbies[self.lobby.lobby_id]
            print("destroyed")

        self.running = False
