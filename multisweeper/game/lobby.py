import asyncio
import json
from typing import List, TYPE_CHECKING, Dict, Union

from asgiref.sync import sync_to_async
from channels.layers import get_channel_layer
from django.contrib.auth.models import User

from multisweeper.game.game_logic import GameLogic
from multisweeper.models import PlayerProfile

if TYPE_CHECKING:
    from multisweeper.consumers import PlayerConsumer

lobbies = {}


class Lobby:
    lobby_id: str
    owner: User | str
    game_started: bool = False
    max_players: int
    current_players: int = 0
    players: List[Union[User, str]]  # str is for the guest
    seats: Dict[int, Union[User, str] | None]  # key - seat number, value - player occupying the seat
    player_scores: Dict[Union[User, str], int]
    player_profiles: Dict[Union[User, str], PlayerProfile | None]
    player_connections: Dict[Union[User, str], 'PlayerConsumer']
    active_seat: int = 0
    game_instance: GameLogic

    def __init__(self, lobby_id, max_players=2):
        self.lobby_id = lobby_id
        self.max_players = max_players
        self.players = []
        self.seats = {}
        for i in range(max_players):
            self.seats[i] = None
        self.player_profiles = {}
        self.player_connections = {}
        self.player_scores = {}
        self.game_instance = GameLogic(difficulty='intermediate', width=16, height=16, mine_count=20)
        self.lock = asyncio.Lock()

        self.channel_layer = get_channel_layer()
        self.group_name = f'lobby_{self.lobby_id}'

    async def add_player(self, player_connection: 'PlayerConsumer'):
        """
        so far:
            updates current_players,
            appends player to self.players
            appends connection to connections
            adds a profile if is a User instance
            sets score to 0 for player

            waits for user to choose their seat.
        :param player_connection:
        :return:
        """
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

            await self.channel_layer.group_add(
                self.group_name,
                player_connection.channel_name
            )

            await self.broadcast(self.create_seats_json())

    async def choose_seat(self, player_connection: 'PlayerConsumer', seat_number):
        if self.seats[seat_number] is None:
            self.seats = {k: (None if v is player_connection.player else v) for k, v in self.seats.items()}
            self.seats[seat_number] = player_connection.player

        await self.broadcast(self.create_seats_json())

    async def remove_player(self, player_connection: 'PlayerConsumer'):
        async with self.lock:
            self.current_players -= 1
            self.players.remove(player_connection.player)
            self.seats = {k: (None if v is player_connection.player else v) for k, v in self.seats.items()}
            del self.player_connections[player_connection.player]
            if isinstance(player_connection.player, User):
                del self.player_profiles[player_connection.player]
            del self.player_scores[player_connection.player]

            await self.channel_layer.group_discard(
                self.group_name,
                player_connection.channel_name
            )

    async def left_click_game(self, y, x, player_connection: 'PlayerConsumer'):
        async with self.lock:
            if player_connection.player != self.seats[self.active_seat] or self.game_instance.user_board[y][x] != "c":
                return
            self.game_instance.cell_left_clicked(y, x, self.active_seat)

            if self.game_instance.logic_board[y][x] != -1:
                self.active_seat = (self.active_seat + 1) % self.max_players
            else:
                self.player_scores[player_connection.player] += 1

    async def broadcast(self, content):
        print(self.owner)
        await self.channel_layer.group_send(
            self.group_name,
            {
                'type': 'send_message',
                'content': content
            }
        )

    async def start_game(self, player_connection: 'PlayerConsumer'):
        if player_connection.player is self.owner:
            self.game_started = True

    async def promote_to_owner(self, player_connection: 'PlayerConsumer', seat: int):
        if player_connection.player is self.owner and self.seats[seat] is not None:
            self.owner = self.seats[seat]
        await self.broadcast(self.create_seats_json())

    async def broadcast_board_and_interface(self):
        await self.broadcast(self.create_user_board_json())
        await self.broadcast(self.create_seats_json())

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

    def create_seats_json(self):
        temp_seats = {}
        for seat, player in self.seats.items():
            if isinstance(player, User):
                temp_seats[seat] = player.username
            else:
                temp_seats[seat] = player

        content = json.dumps({
            "type": "seats",
            "owner": self.owner.username if isinstance(self.owner, User) else self.owner,
            "active_seat": self.active_seat,
            "message": temp_seats,
        })
        return content
