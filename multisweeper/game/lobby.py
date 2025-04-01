import asyncio
import datetime
import json
import math
from typing import List, TYPE_CHECKING, Dict, Union

from channels.layers import get_channel_layer
from django.contrib.auth.models import User


from multisweeper.game.chat_manager import ChatManager
from multisweeper.game.game_logic import GameLogic
from multisweeper.game.lobby_destroyer import LobbyDestroyer
from multisweeper.game.lobby_player_rejoin_watcher import LobbyPlayerRejoinWatcher

from multisweeper.game.lobby_states import State, LobbyWaitingState, LobbyGameInProgressState, LobbyGameOverState, \
    LobbyPlayerQuitState
from multisweeper.models import PlayerProfile

if TYPE_CHECKING:
    from multisweeper.consumers import PlayerConsumer


class Lobby:
    lobby_id: str
    state: State
    owner: Union[User, str]
    ranked: bool
    max_players: int
    current_players: int = 0
    players: List[Union[User, str]]  # str is for the guest
    seats: Dict[int, Union[User, str] | None]  # key - seat number, value - player occupying the seat
    player_scores: Dict[Union[User, str], int]
    player_profiles: Dict[Union[User, str], PlayerProfile | None]
    player_connections: Dict[Union[User, str], 'PlayerConsumer']
    player_bomb_used: Dict[Union[User, str], bool]
    active_seat: int = 0
    mine_count: int
    game_instance: GameLogic

    def __init__(self, lobby_id, max_players, mine_count, ranked: bool):
        self.lobby_id = lobby_id
        self.state = LobbyWaitingState(self)
        self.ranked = ranked
        self.max_players = max_players
        self.players = []
        self.seats = {}
        for i in range(max_players):
            self.seats[i] = None
        self.player_profiles = {}
        self.player_connections = {}
        self.player_bomb_used = {}
        self.player_scores = {}
        self.mine_count = mine_count
        self.game_instance = GameLogic(difficulty='intermediate', width=16, height=16, mine_count=mine_count)

        self.lock = asyncio.Lock()
        self.lobby_destroyer = LobbyDestroyer(self)
        self.lobby_player_rejoin_watcher = LobbyPlayerRejoinWatcher(self)

        self.chat_manager = ChatManager(self)

        self.channel_layer = get_channel_layer()
        self.group_name = f'lobby_{self.lobby_id}'

    async def _remove_player_without_connection(self, player: Union[User, str]):
        async with self.lock:

            self.players.remove(player)
            if self.current_players == 0:
                self.owner = None
            else:
                if self.owner != self.players[0]:
                    await self.chat_manager.send_server_message(
                        f"{self.players[0]} is the owner of the lobby.")
                self.owner = self.players[0]

            self.seats = {k: (None if v is player else v) for k, v in self.seats.items()}

            if isinstance(player, User):
                del self.player_profiles[player]
            del self.player_scores[player]
            del self.player_bomb_used[player]

            if self.current_players == 0:
                asyncio.create_task(self.lobby_destroyer.wait_for_players_to_join())
                return

    async def handle_players_failed_to_rejoin(self, failed_players: List[Union[User, str]]):
        # TODO penalty for players who failed
        print(f"failed_players: {failed_players}")
        for player in failed_players:
            await self._remove_player_without_connection(player)
        await self.change_state(LobbyGameOverState(self))
        await self.broadcast(self.create_seats_json())

    async def change_state(self, state: State):
        self.state = state
        await self.broadcast(self.create_state_json())

    async def add_player(self, player_connection: 'PlayerConsumer'):
        if player_connection.lobby.ranked and not isinstance(player_connection.player, User):
            return  # TODO really think if this validation of credentials should be there and not somewhere else
        await self.state.add_player(player_connection)
        if isinstance(self.state, LobbyPlayerQuitState):
            if len(self.state.players_who_quit) == 0:
                await self.change_state(LobbyGameInProgressState(self))
        await self.chat_manager.send_server_message(f"{player_connection.player} joined.")

    async def remove_player(self, player_connection: 'PlayerConsumer'):
        if player_connection.lobby.ranked and not isinstance(player_connection.player, User):
            return  # TODO really think if this validation of credentials should be there and not somewhere else
        if isinstance(self.state, LobbyGameInProgressState):
            await self.change_state(LobbyPlayerQuitState(self))
        await self.state.remove_player(player_connection)
        await self.chat_manager.send_server_message(f"{player_connection.player} quit.")

    async def choose_seat(self, player_connection: 'PlayerConsumer', seat_number):
        await self.state.choose_seat(player_connection, seat_number)

    async def bomb_used(self, y, x, player_connection: 'PlayerConsumer'):
        async with self.lock:
            if not isinstance(self.state, LobbyGameInProgressState):
                return

            if player_connection.player != self.seats[self.active_seat]:
                return

            #  this check below returns if:
            # 1. player has already used bomb before
            # 2. player who wanted to use the bomb doesn't have the lowest score
            # 3. player who wanted to use the bomb shares the lowest score with somebody else
            if self.player_bomb_used[player_connection.player] or self.player_scores[player_connection.player] != min(
                    self.player_scores.values()) or sum(
                value == self.player_scores[player_connection.player] for value in self.player_scores.values()) != 1:
                return

            self.player_bomb_used[player_connection.player] = True
            mines_clicked_before = self.game_instance.mines_clicked

            for dy in range(y - 2, y + 3, 1):
                for dx in range(x - 2, x + 3, 1):
                    if (not (0 <= dy < self.game_instance.height)) or (not (0 <= dx < self.game_instance.width)):
                        continue
                    self.game_instance.cell_left_clicked(dy, dx, self.active_seat)

            self.player_scores[player_connection.player] += self.game_instance.mines_clicked - mines_clicked_before

            if self.player_scores[player_connection.player] > math.floor(self.game_instance.mine_count / 2):
                await self.change_state(LobbyGameOverState(self))
                await self.broadcast(self.create_game_over_json(
                    player_connection.player.username if isinstance(player_connection.player,
                                                                    User) else player_connection.player))
                await self.on_win()
            elif self.game_instance.mine_count == self.game_instance.mines_clicked:  # draw
                await self.change_state(LobbyGameOverState(self))
                await self.broadcast(self.create_game_over_json(None))
                await self.on_win()

            self.active_seat = (self.active_seat + 1) % self.max_players

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
                    await self.on_win()
                elif self.game_instance.mine_count == self.game_instance.mines_clicked:  # draw
                    await self.change_state(LobbyGameOverState(self))
                    await self.broadcast(self.create_game_over_json(None))
                    await self.on_win()

    async def on_win(self):
        if self.ranked:
            await self.calculate_elo_after_ranked_game()
        await self.chat_manager.send_server_message("Game over.")
        self.active_seat = (self.active_seat + 1) % self.max_players

    async def calculate_elo_after_ranked_game(self):
        """
                    p1: 20
                    p2: 15
                    p3: 10
                    p4: 10

                    p1 won with all,
                    p2 won with p3 and p4, lost to p1
                    p3 drew with p4, lost to p1 and p2
                    p4 same as p3
                """
        K_CONST = 32

        scores_sorted = tuple(sorted(self.player_scores.items(), key=lambda item: item[1], reverse=True))
        # converts player scores into a tuple of tuples with sorting based on decreasing score.
        # Pretty much an ordered dictionary and that's how it will be used

        delta_elo = dict(zip(self.players, [0] * len(self.players)))

        for a in scores_sorted:
            r_a = self.player_profiles[a[0]].elo_rating
            for b in scores_sorted:
                if a == b:
                    continue
                r_b = self.player_profiles[b[0]].elo_rating

                e_a = 1 / (1 + 10 ** ((r_b - r_a) / 400))

                if a[1] > b[1]:
                    s_a = 1
                elif a[1] < b[1]:
                    s_a = 0
                else:
                    s_a = 0.5

                d_elo_a = K_CONST * (s_a - e_a)
                delta_elo[a[0]] += d_elo_a

        for player, delta in delta_elo.items():
            self.player_profiles[player].elo_rating += delta
            await self.player_profiles[player].asave()

    async def start_game(self, player_connection: 'PlayerConsumer'):
        async with self.lock:
            if player_connection.player == self.owner and (
                    not isinstance(self.state, LobbyGameInProgressState) and not isinstance(self.state,
                                                                                            LobbyPlayerQuitState)):
                if len(self.players) == self.max_players and sum(
                        1 for value in self.seats.values() if value is None) == 0:
                    if isinstance(self.state, LobbyGameOverState):
                        self.game_instance = GameLogic(difficulty='intermediate', width=16, height=16,
                                                       mine_count=self.mine_count)

                        self.game_rematch_cleanup()

                    await self.change_state(LobbyGameInProgressState(self))
                    await self.broadcast_board_and_interface()
                    await self.chat_manager.send_server_message("Game started.")

    def game_rematch_cleanup(self):
        self.player_scores = dict(zip(self.players, [0] * len(self.players)))
        self.player_bomb_used = dict(zip(self.players, [False] * len(self.players)))

    async def promote_to_owner(self, player_connection: 'PlayerConsumer', seat: int):
        if player_connection.player == self.owner and self.seats[seat] is not None and (
                not isinstance(self.state, LobbyGameInProgressState) and not isinstance(self.state,
                                                                                        LobbyPlayerQuitState)):
            self.owner = self.seats[seat]
        await self.broadcast(self.create_seats_json())
        await self.chat_manager.send_server_message(f"{self.seats[seat]} is the owner of the lobby.")

    async def broadcast(self, content):

        # if isinstance(self.state, LobbyPlayerQuitState):
        #     print(datetime.datetime.now(), ' ', self.state.players_who_quit)
        # else:
        print(datetime.datetime.now(), ' ', self.players, self.player_connections, self.state)
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
        temp_scores = {}
        temp_elo = {}

        for seat, player in self.seats.items():
            if isinstance(player, User):
                temp_seats[seat] = player.username
                if player is not None:
                    temp_scores[seat] = self.player_scores[player]
                    temp_elo[seat] = int(self.player_profiles[player].elo_rating)
                else:
                    temp_elo[seat] = None
            else:
                temp_seats[seat] = player
                if player is not None:
                    temp_scores[seat] = self.player_scores[player]
                    temp_elo[seat] = '--GUEST--'
                else:
                    temp_elo[seat] = None

        content = json.dumps({
            "type": "seats",
            "owner": self.owner.username if isinstance(self.owner, User) else self.owner,
            "active_seat": self.active_seat,
            "seats": temp_seats,
            "scores": temp_scores,
            "elo_ratings": temp_elo
        })
        return content

    def create_game_over_json(self, winner: str | None):
        draw = self.game_instance.mine_count == self.game_instance.mines_clicked
        content = json.dumps({
            "type": "game_over",
            "draw": draw,
            "winner_username": f"{winner}"
        })
        return content
