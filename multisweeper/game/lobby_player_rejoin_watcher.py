from typing import TYPE_CHECKING, Union

from django.contrib.auth.models import User

if TYPE_CHECKING:
    from multisweeper.game.lobby import Lobby

import asyncio
from typing import Set, Optional


class LobbyPlayerRejoinWatcher:
    def __init__(self, lobby: 'Lobby'):
        self.lobby = lobby
        self.players_waiting: Set[Union[User, str]] = set()
        self.waiting_task: Optional[asyncio.Task] = None
        self.lock = asyncio.Lock()

    def add_player(self, player: Union[User, str]):
        asyncio.create_task(self._async_add_player(player))

    async def _async_add_player(self, player: Union[User, str]):
        async with self.lock:
            self.players_waiting.add(player)
            if self.waiting_task is None:
                self.waiting_task = asyncio.create_task(self._wait_for_rejoins())

    async def _wait_for_rejoins(self):
        try:
            await asyncio.sleep(10)

            async with self.lock:
                if self.players_waiting:
                    await self._handle_rejoin_failure()

                self._reset()

        except asyncio.CancelledError:
            async with self.lock:
                self._reset()

    def _reset(self):
        self.players_waiting = set()
        self.waiting_task = None

    async def _handle_rejoin_failure(self):
        failed_players = list(self.players_waiting)
        self._reset()
        await self.lobby.handle_players_failed_to_rejoin(failed_players)

    async def player_rejoined(self, player: Union[User, str]):
        async with self.lock:
            if player in self.players_waiting:
                self.players_waiting.remove(player)
                print(f"self.players_waiting: {self.players_waiting}")
                # If all players have rejoined, cancel the waiting task
                if not self.players_waiting and self.waiting_task:
                    self.waiting_task.cancel()
                    self.waiting_task = None

