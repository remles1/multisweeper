import asyncio
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from django.contrib.auth.models import User

from multisweeper.models import PlayerProfile

if TYPE_CHECKING:
    from multisweeper.consumers import PlayerConsumer
    from multisweeper.game.lobby import Lobby


class State(ABC):
    lobby: 'Lobby'

    def __init__(self, lobby: 'Lobby'):
        self.lobby = lobby

    @abstractmethod
    async def add_player(self, player_connection: 'PlayerConsumer'):
        pass

    @abstractmethod
    async def remove_player(self, player_connection: 'PlayerConsumer'):
        pass

    @abstractmethod
    async def choose_seat(self, player_connection: 'PlayerConsumer', seat_number):
        pass


class LobbyWaitingState(State):
    async def add_player(self, player_connection: 'PlayerConsumer'):
        async with self.lobby.lock:
            if type(self) is not type(
                    self.lobby.state):  # safeguard against race conditions if state changes mid websocket request
                return

            if self.lobby.current_players >= self.lobby.max_players:
                return
            if self.lobby.current_players == 0:
                self.lobby.owner = player_connection.player
            self.lobby.current_players += 1
            self.lobby.players.append(player_connection.player)
            self.lobby.player_connections[player_connection.player] = player_connection

            if isinstance(player_connection.player, User):
                self.lobby.player_profiles[player_connection.player] = await PlayerProfile.objects.aget(
                    user=player_connection.player
                )

            self.lobby.player_scores[player_connection.player] = 0

            await self.lobby.channel_layer.group_add(
                self.lobby.group_name,
                player_connection.channel_name
            )

            await self.lobby.broadcast(self.lobby.create_seats_json())

    async def remove_player(self, player_connection: 'PlayerConsumer'):
        async with self.lobby.lock:
            if type(self) is not type(
                    self.lobby.state):  # safeguard against race conditions if state changes mid websocket request
                return

            self.lobby.current_players -= 1
            self.lobby.players.remove(player_connection.player)
            if self.lobby.current_players == 0:
                self.lobby.owner = None
            else:
                self.lobby.owner = self.lobby.players[0]
            self.lobby.seats = {k: (None if v is player_connection.player else v) for k, v in self.lobby.seats.items()}
            del self.lobby.player_connections[player_connection.player]
            if isinstance(player_connection.player, User):
                del self.lobby.player_profiles[player_connection.player]
            del self.lobby.player_scores[player_connection.player]

            await self.lobby.channel_layer.group_discard(
                self.lobby.group_name,
                player_connection.channel_name
            )
            if self.lobby.current_players == 0:
                asyncio.create_task(self.lobby.auto_destruct())
                return

    async def choose_seat(self, player_connection: 'PlayerConsumer', seat_number):
        async with self.lobby.lock:
            if type(self) is not type(
                    self.lobby.state):  # safeguard against race conditions if state changes mid websocket request
                return

            if self.lobby.seats[seat_number] is None:
                self.lobby.seats = {k: (None if v is player_connection.player else v) for k, v in
                                    self.lobby.seats.items()}
                self.lobby.seats[seat_number] = player_connection.player

            await self.lobby.broadcast(self.lobby.create_seats_json())


class LobbyGameInProgressState(State):
    async def add_player(self, player_connection: 'PlayerConsumer'):
        async with self.lobby.lock:
            if type(self) is not type(
                    self.lobby.state):  # safeguard against race conditions if state changes mid websocket request
                return

            if player_connection.player not in self.lobby.players:
                pass
                # TODO tutaj trzeba websocketem przesłać

            self.lobby.current_players += 1

            self.lobby.player_connections[player_connection.player] = player_connection
            # TODO dodaj zawiadomienie o tym że player wyszedł (może wróci, przerwanie internetu czy coś)
            await self.lobby.channel_layer.group_add(
                self.lobby.group_name,
                player_connection.channel_name
            )

            await self.lobby.broadcast(self.lobby.create_seats_json())

    async def remove_player(self, player_connection: 'PlayerConsumer'):
        async with self.lobby.lock:
            if type(self) is not type(
                    self.lobby.state):  # safeguard against race conditions if state changes mid websocket request
                return

            self.lobby.current_players -= 1

            del self.lobby.player_connections[player_connection.player]

            await self.lobby.channel_layer.group_discard(
                self.lobby.group_name,
                player_connection.channel_name
            )

            if self.lobby.current_players == 0:
                asyncio.create_task(self.lobby.auto_destruct())
                return

    async def choose_seat(self, player_connection: 'PlayerConsumer', seat_number):
        return
