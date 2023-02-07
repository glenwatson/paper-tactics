import json
from dataclasses import asdict, dataclass

from paper_tactics.entities.cell import Cell
from paper_tactics.entities.player_view import PlayerView


@dataclass(frozen=True)
class GameView:
    id: str
    turns_left: int
    my_turn: bool
    me: PlayerView
    opponent: PlayerView
    trenches: frozenset[Cell]

    def to_json(self) -> str:
        game_dict = asdict(self)
        game_dict["trenches"] = list(game_dict["trenches"])
        for player_view in game_dict["me"], game_dict["opponent"]:
            for key in player_view:
                if isinstance(player_view[key], (set, frozenset)):
                    player_view[key] = list(player_view[key])
        return json.dumps(game_dict, separators=(",", ":"))
