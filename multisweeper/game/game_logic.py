# TODO wyczyscic ze zbednego kodu i pól

import random
from datetime import datetime
from typing import List

from django.utils import timezone


class GameLogic:
    difficulty: str
    width: int
    height: int
    mine_count: int
    logic_board: List[List[int]]
    user_board: List[List[str]]
    traversed_board: List[List[bool]]
    time_started: datetime.date
    time_spent: int
    time_ended: datetime.date
    game_over: bool
    game_won: bool
    mines_clicked: int = 0
    seed: str
    """
        user_board values:
    
        "c":  closed cell
        "0":  opened empty cell
        "f":  flagged cell 
        "fw": wrongly flagged cell # only used when the game is lost
        "m":  mine 
        "me": exploded mine# only used when the game is lost
        "1":  cell with 1 mines nearby
        "2":  cell with 2 mines nearby
        "3":  cell with 3 mines nearby
        "4":  cell with 4 mines nearby
        "5":  cell with 5 mines nearby
        "6":  cell with 6 mines nearby
        "7":  cell with 7 mines nearby 
        "8":  cell with 8 mines nearby 
    
        this can be used with a dict in the frontend to support theming
    """

    def __init__(self, difficulty: str, width: int, height: int, mine_count: int,
                 seed: str | None = None, calculate_boards: bool = True) -> None:
        """Creating a new board, not coming back to one

        Args:
            width:
            height:
            mine_count:
            seed:
        """
        self.difficulty = difficulty
        self.width = width
        self.height = height
        self.mine_count = mine_count
        self.time_started = None
        self.time_spent = 0
        self.time_ended = None
        self.game_over = False
        self.game_won = False
        self.seed = seed
        if calculate_boards:
            self.logic_board = self.create_logic_board()
            self.traversed_board = self.create_traversed_board()
            self.user_board = self.create_user_board()

    @classmethod
    def from_model(cls, model_instance):
        """
        Alternate constructor to create a MinesweeperGame instance from a Game model instance.

        Args:
            model_instance: An instance of the Game model.

        Returns:
            MinesweeperGame: An instance of MinesweeperGame initialized with data from the model.
        """
        obj = cls(
            difficulty=model_instance.difficulty,
            width=model_instance.width,
            height=model_instance.height,
            mine_count=model_instance.mine_count,
            seed=model_instance.seed,
            calculate_boards=False
        )
        # Set attributes directly from the model
        obj.time_started = model_instance.time_started
        obj.time_spent = model_instance.time_spent
        obj.time_ended = model_instance.time_ended
        obj.game_over = model_instance.game_over
        obj.game_won = model_instance.game_won
        obj.logic_board = model_instance.logic_board
        obj.traversed_board = model_instance.traversed_board
        obj.user_board = model_instance.user_board
        obj.mines_clicked = model_instance.mines_clicked
        return obj

    def create_logic_board(self) -> List[List[int]]:
        """Creates a 2D List that represents where the mines are located and .
            -1 - mine
            0 - free cell
            1 - in the neighborhood of 1 mine
            2 - in the neighborhood of 2 mines
            etc.

            Example:
                self.width = 3
                self.height = 2
                self.minecount = 1

                logic_board = [[0,1,-1],
                              [0,1,1]]

            Return:
                logic_board (List[List[int]]): A 2D List that represents where the mines are located

        """
        if self.seed is not None:
            random.seed(self.seed)

        logic_board = [[0] * self.width for _ in range(self.height)]

        mines_left_to_put_on_board = self.mine_count

        while mines_left_to_put_on_board > 0:
            i = random.randint(0, self.height - 1)
            j = random.randint(0, self.width - 1)

            if logic_board[i][j] == 0:
                logic_board[i][j] = -1
                mines_left_to_put_on_board -= 1

        for y in range(self.height):
            for x in range(self.width):
                if logic_board[y][x] == -1:
                    continue
                logic_board[y][x] = self.count_mines_nearby(logic_board, y, x)

        return logic_board

    def count_mines_nearby(self, logic_board: List[List[int]], center_y: int, center_x: int) -> int:
        """Counts how many mines are next to the point logic_board[center_y][center_x]

        logic_board[center_y][center_x] != -1 is assumed to be true

        Args:
            logic_board (List[List[int]]): incomplete logic_board with only mines in it at worst.
            center_y (int): the center ofa a 3x3 sub-matrix
            center_x (int): the center of a 3x3 sub-matrix

        Returns:
            mines_nearby (int): How many mines are next to the point logic_board[center_y][center_x]
        """

        mines_nearby = 0

        for y in range(center_y - 1, center_y + 1 + 1):
            if not 0 <= y < self.height:
                continue

            for x in range(center_x - 1, center_x + 1 + 1):
                if not 0 <= x < self.width:
                    continue
                if y == center_y and x == center_x:
                    continue

                if logic_board[y][x] == -1:
                    mines_nearby += 1

        return mines_nearby

    def create_traversed_board(self) -> List[List[bool]]:
        local_traversed_board = [[False] * self.width for _ in range(self.height)]
        return local_traversed_board

    def create_user_board(self) -> List[List[str]]:
        local_user_board = [["c"] * self.width for _ in range(self.height)]  # the board is closed at first
        return local_user_board

    def cell_left_clicked(self, y: int, x: int, player_number: int):
        if "f" in self.user_board[y][x]:
            return
        #  add to time spent playing the game
        if self.time_started is None:
            self.time_started = timezone.now()
        t_delta = timezone.now() - self.time_started
        self.time_spent = int(t_delta.total_seconds() * 1000)

        cell_val = self.logic_board[y][x]
        if cell_val == -1:
            self.mines_clicked += 1
            self.user_board[y][x] = f"f_{player_number}"
        elif cell_val >= 0:
            if self.user_board[y][x] == "c":
                self.open_cells_recursively(y, x)
        self.check_win()

    def open_cells_recursively(self, y, x):
        if self.traversed_board[y][x]:
            return

        if "f" in self.user_board[y][x]:  # dont touch flagged cells
            return

        self.traversed_board[y][x] = True

        if not self.logic_board[y][x] == 0:
            self.user_board[y][x] = str(self.logic_board[y][x])  # not opened numbered cell
            return
        else:
            for dy in range(y - 1, y + 1 + 1):
                if not 0 <= dy < self.height:
                    continue

                for dx in range(x - 1, x + 1 + 1):
                    if not 0 <= dx < self.width:
                        continue

                    if dy == y and dx == x:
                        self.user_board[dy][dx] = str(self.logic_board[dy][dx])
                        # print(f"this should be zero: {str(self.logic_board[dy][dx])}")

                    self.open_cells_recursively(dy, dx)

    def check_win(self):
        # print(f"_cells_opened: {self._cells_opened}")
        if self.mines_clicked == self.mine_count:
            self.on_win()

    def on_win(self):
        self.game_over = True
        self.game_won = True
        self.time_ended = timezone.now()
        # for dy in range(self.height):
        #     for dx in range(self.width):
        #         if self.logic_board[dy][dx] != -1:
        #             self.user_board[dy][dx] = f"{self.logic_board[dy][dx]}"

    def on_lose(self, y, x):
        self.game_over = True
        self.game_won = False
        self.time_ended = timezone.now()
        for dy in range(self.height):
            for dx in range(self.width):
                if self.logic_board[dy][dx] == -1:
                    if self.user_board[dy][dx] == "f":
                        continue
                    self.user_board[dy][dx] = "m"

                elif self.user_board[dy][dx] == "f":
                    if self.logic_board[dy][dx] != -1:
                        self.user_board[dy][dx] = 'fw'

        self.user_board[y][x] = "me"
