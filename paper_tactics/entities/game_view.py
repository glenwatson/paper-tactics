from dataclasses import dataclass

from paper_tactics.entities.cell import Cell
from paper_tactics.entities.player_view import PlayerView
from paper_tactics.entities.game_preferences import GamePreferences


@dataclass(frozen=True)
class GameView:
    id: str
    turns_left: int
    my_turn: bool
    me: PlayerView
    opponent: PlayerView
    trenches: frozenset[Cell]
    preferences: GamePreferences

    def __str__(self) -> str:
        return self._str_wide()

    def _str_wide(self) -> str:
        ret = ''
        board_size = self.preferences.size
        for y in range(board_size):
            for x in range(board_size):
                ret += "+-"
            ret += "+\n"
            for x in range(board_size):
                current_cell = (x+1, y+1)
                ret += "|" + self._get_char(current_cell)
            ret += "|\n"
        for x in range(board_size):
            ret += "+-"
        ret += "+\n"
        return ret

    def _str_compact(self) -> str:
        ret = ''
        board_size = self.preferences.size
        for y in range(board_size):
            ret += "\n"
            for x in range(board_size):
                current_cell = (x+1, y+1)
                ret += self._get_char(current_cell)
            ret += "\n"
        ret += "\n"
        return ret

    def _get_char(self, cell: Cell) -> str:
        if cell in self.me.units:
            return "x"
        elif cell in self.active_player.walls:
            return "X"
        elif cell in self.passive_player.units:
            return "o"
        elif cell in self.passive_player.walls:
            return "0"
        elif cell in self.trenches:
            # is unclaimed trench
            return "@"
        else:
            return " "
