import asyncio
import datetime
import json
import math
from typing import List, TYPE_CHECKING, Dict, Union

from channels.layers import get_channel_layer
from django.contrib.auth.models import User

from multisweeper.game.game_logic import GameLogic
from multisweeper.game.lobby_states import State, LobbyWaitingState, LobbyGameInProgressState, LobbyGameOverState
from multisweeper.models import PlayerProfile

if TYPE_CHECKING:
    from multisweeper.consumers import PlayerConsumer

lobbies = {}


class Lobby:
    lobby_id: str
    state: State
    owner: Union[User, str]
    max_players: int
    current_players: int = 0
    players: List[Union[User, str]]  # str is for the guest
    seats: Dict[int, Union[User, str] | None]  # key - seat number, value - player occupying the seat
    player_scores: Dict[Union[User, str], int]
    player_profiles: Dict[Union[User, str], PlayerProfile | None]
    player_connections: Dict[Union[User, str], 'PlayerConsumer']
    active_seat: int = 0
    mine_count: int
    game_instance: GameLogic

    def __init__(self, lobby_id, max_players, mine_count):
        self.lobby_id = lobby_id
        self.state = LobbyWaitingState(self)
        self.max_players = max_players
        self.players = []
        self.seats = {}
        for i in range(max_players):
            self.seats[i] = None
        self.player_profiles = {}
        self.player_connections = {}
        self.player_scores = {}
        self.mine_count = mine_count
        self.game_instance = GameLogic(difficulty='intermediate', width=16, height=16, mine_count=mine_count)
        self.lock = asyncio.Lock()

        self.channel_layer = get_channel_layer()
        self.group_name = f'lobby_{self.lobby_id}'

    async def auto_destruct(self):
        await asyncio.sleep(10)
        if self.lobby_id in lobbies and self.current_players == 0:
            del lobbies[self.lobby_id]

    async def change_state(self, state: State):
        self.state = state
        await self.broadcast(self.create_state_json())

    async def add_player(self, player_connection: 'PlayerConsumer'):
        await self.state.add_player(player_connection)

    async def remove_player(self, player_connection: 'PlayerConsumer'):
        await self.state.remove_player(player_connection)

    async def choose_seat(self, player_connection: 'PlayerConsumer', seat_number):
        await self.state.choose_seat(player_connection, seat_number)

    async def left_click_game(self, y, x, player_connection: 'PlayerConsumer'):
        async with self.lock:
            if not isinstance(self.state, LobbyGameInProgressState):
                return

            if player_connection.player != self.seats[self.active_seat] or self.game_instance.user_board[y][x] != "c":
                return
            self.game_instance.cell_left_clicked(y, x, self.active_seat)

            if self.game_instance.logic_board[y][x] != -1:
                self.active_seat = (self.active_seat + 1) % self.max_players
            else:
                self.player_scores[player_connection.player] += 1
                if self.player_scores[player_connection.player] > math.floor(self.game_instance.mine_count / 2):
                    await self.change_state(LobbyGameOverState(self))
                    await self.broadcast(self.create_game_over_json(
                        player_connection.player.username if isinstance(player_connection.player,
                                                                        User) else player_connection.player))

    async def start_game(self, player_connection: 'PlayerConsumer'):
        async with self.lock:
            if player_connection.player == self.owner and not isinstance(self.state, LobbyGameInProgressState):
                if len(self.players) == self.max_players:
                    if isinstance(self.state, LobbyGameOverState):
                        self.game_instance = GameLogic(difficulty='intermediate', width=16, height=16,
                                                       mine_count=self.mine_count)

                        self.game_rematch_cleanup()

                    await self.change_state(LobbyGameInProgressState(self))
                    await self.broadcast_board_and_interface()

    def game_rematch_cleanup(self):
        self.player_scores = dict(zip(self.players, [0] * len(self.players)))

    async def promote_to_owner(self, player_connection: 'PlayerConsumer', seat: int):
        if player_connection.player == self.owner and self.seats[seat] is not None and not isinstance(self.state, LobbyGameInProgressState):
            self.owner = self.seats[seat]
        await self.broadcast(self.create_seats_json())

    async def broadcast(self, content):
        print(datetime.datetime.now(), ' ', self.player_scores, self.state)
        print(self.owner)
        await self.channel_layer.group_send(
            self.group_name,
            {
                'type': 'send_message',
                'content': content
            }
        )

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

    def create_state_json(self):
        content = json.dumps({
            "type": "state",
            "message": f"{type(self.state).__name__}"
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

    def create_game_over_json(self, winner: str):
        content = json.dumps({
            "type": "game_over",
            "winner_username": f"{winner}"
        })
        return content
