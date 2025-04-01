import asyncio
import json
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Union

from django.contrib.auth.models import User

from multisweeper.models import PlayerProfile

if TYPE_CHECKING:
    from multisweeper.consumers import PlayerConsumer
    from multisweeper.game.lobby import Lobby


class State(ABC):
    lobby: 'Lobby'

    def __init__(self, lobby: 'Lobby') -> None:
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
            self.lobby.player_bomb_used[player_connection.player] = False

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
                if self.lobby.owner != self.lobby.players[0]:
                    await self.lobby.chat_manager.send_server_message(
                        f"{self.lobby.players[0]} is the owner of the lobby.")
                self.lobby.owner = self.lobby.players[0]

            self.lobby.seats = {k: (None if v is player_connection.player else v) for k, v in self.lobby.seats.items()}

            del self.lobby.player_connections[player_connection.player]

            if isinstance(player_connection.player, User):
                del self.lobby.player_profiles[player_connection.player]
            del self.lobby.player_scores[player_connection.player]
            del self.lobby.player_bomb_used[player_connection.player]

            await self.lobby.channel_layer.group_discard(
                self.lobby.group_name,
                player_connection.channel_name
            )
            if self.lobby.current_players == 0:
                asyncio.create_task(self.lobby.lobby_destroyer.wait_for_players_to_join())
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
        pass

    async def remove_player(self, player_connection: 'PlayerConsumer'):
        pass

    async def choose_seat(self, player_connection: 'PlayerConsumer', seat_number):
        return


class LobbyGameOverState(LobbyWaitingState):
    pass


class LobbyPlayerQuitState(State):
    def __init__(self, lobby: 'Lobby'):
        super().__init__(lobby)
        self.players_who_quit = []

    async def add_player(self, player_connection: 'PlayerConsumer'):
        async with self.lobby.lock:
            if type(self) is not type(
                    self.lobby.state):  # safeguard against race conditions if state changes mid websocket request
                return

            #  redirect is handled in the view, so I think its safe to delete that below
            if player_connection.player not in self.lobby.players:
                asyncio.create_task(player_connection.send(text_data=json.dumps({
                    "type": "game_in_progress_redirect",
                })))
                return

            if player_connection.player in self.players_who_quit:
                self.players_who_quit.remove(player_connection.player)
                self.lobby.current_players += 1

                self.lobby.player_connections[player_connection.player] = player_connection
                await self.lobby.channel_layer.group_add(
                    self.lobby.group_name,
                    player_connection.channel_name
                )

                print("bout to call player_rejoined")

                await self.lobby.lobby_player_rejoin_watcher.player_rejoined(player_connection.player)
                await self.lobby.broadcast(self.lobby.create_seats_json())

    async def remove_player(self, player_connection: 'PlayerConsumer'):
        async with self.lobby.lock:
            if type(self) is not type(
                    self.lobby.state):  # safeguard against race conditions if state changes mid websocket request
                return

            self.players_who_quit.append(player_connection.player)
            self.lobby.current_players -= 1

            del self.lobby.player_connections[player_connection.player]

            await self.lobby.channel_layer.group_discard(
                self.lobby.group_name,
                player_connection.channel_name
            )

            self.lobby.lobby_player_rejoin_watcher.add_player(player_connection.player)

    async def choose_seat(self, player_connection: 'PlayerConsumer', seat_number):
        return
