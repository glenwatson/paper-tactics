from dataclasses import dataclass, field
from random import randint
from typing import Final, Iterable, cast

from paper_tactics.entities.cell import Cell
from paper_tactics.entities.game_preferences import GamePreferences
from paper_tactics.entities.game_view import GameView
from paper_tactics.entities.player import Player
from paper_tactics.entities.player_view import PlayerView


@dataclass
class Game:
    id: Final[str] = ""
    preferences: Final[GamePreferences] = GamePreferences()
    turns_left: int = 0
    active_player: Player = field(default_factory=Player)
    passive_player: Player = field(default_factory=Player)
    trenches: frozenset[Cell] = frozenset()

    def init(self) -> None:
        assert self.active_player.id != self.passive_player.id
        self._init_players()
        self.trenches = frozenset(self._generate_trenches())
        self._rebuild_reachable_set(self.active_player, self.passive_player)
        self._rebuild_reachable_set(self.passive_player, self.active_player)
        self.turns_left = self.preferences.turn_count

    def get_view(self, player_id: str) -> GameView:
        assert player_id in (self.active_player.id, self.passive_player.id)
        if player_id == self.active_player.id:
            me = self.active_player
            opponent = self.passive_player
        else:
            me = self.passive_player
            opponent = self.active_player

        if self.preferences.is_visibility_applied and me.can_win and opponent.can_win:
            opponent_units = opponent.units.intersection(me.visible_opponent)
            opponent_walls = opponent.walls.intersection(me.visible_opponent)
            trenches = self.trenches.intersection(me.visible_terrain)
        else:
            opponent_units = opponent.units
            opponent_walls = opponent.walls
            trenches = self.trenches

        return GameView(
            id=self.id,
            turns_left=self.turns_left,
            my_turn=(me == self.active_player),
            me=PlayerView(
                units=cast(frozenset[Cell], me.units),
                walls=cast(frozenset[Cell], me.walls),
                reachable=cast(frozenset[Cell], me.reachable),
                view_data=me.view_data.copy(),
                is_gone=me.is_gone,
                is_defeated=me.is_defeated,
            ),
            opponent=PlayerView(
                units=cast(frozenset[Cell], opponent_units),
                walls=cast(frozenset[Cell], opponent_walls),
                reachable=frozenset(),
                view_data=opponent.view_data.copy(),
                is_gone=opponent.is_gone,
                is_defeated=opponent.is_defeated,
            ),
            trenches=trenches,
            preferences=self.preferences,
        )

    def make_turn(self, player_id: str, cell: Cell) -> None:
        if (
            player_id != self.active_player.id
            or cell not in self.active_player.reachable
            or not all(
                player.can_win for player in (self.active_player, self.passive_player)
            )
        ):
            raise IllegalTurnException(self.id, player_id, cell)

        self._make_turn(cell, self.active_player, self.passive_player)
        self._decrement_turns()

    def _decrement_turns(self) -> None:
        self.turns_left -= 1
        if not self.turns_left:
            self.turns_left = self.preferences.turn_count
            self.active_player, self.passive_player = (
                self.passive_player,
                self.active_player,
            )
            if self.preferences.is_against_bot:
                from paper_tactics.entities.game_bot import GameBot  # hack to avoid circular imports
                game_bot = GameBot()
                while self.turns_left:
                    if not self.active_player.reachable:
                        self.active_player.is_defeated = True
                        break
                    cell = game_bot.make_turn(self)
                    assert cell in self.active_player.reachable
                    self._make_turn(cell, self.active_player, self.passive_player)
                    self.turns_left -= 1
                self.turns_left = self.preferences.turn_count
                self.active_player, self.passive_player = (
                    self.passive_player,
                    self.active_player,
                )
        if not self.active_player.reachable and not self.passive_player.is_defeated:
            self.active_player.is_defeated = True

    def _make_turn(self, cell: Cell, player: Player, opponent: Player) -> None:
        if cell in opponent.units:
            opponent.units.remove(cell)
            player.walls.add(cell)
            self._rebuild_reachable_set(opponent, player)
        elif cell in self.trenches:
            player.walls.add(cell)
            opponent.reachable.discard(cell)
        else:
            player.units.add(cell)
        self._rebuild_reachable_set(player, opponent)

    def _rebuild_reachable_set(self, player: Player, opponent: Player) -> None:
        player.reachable.clear()
        if self.preferences.is_visibility_applied:
            player.visible_opponent = {
                cell
                for cell in player.visible_opponent
                if cell in opponent.units or cell in opponent.walls
            }.union(cell for cell in opponent.walls if cell not in self.trenches)
        sources = player.units.copy()
        while True:
            new_sources = set()
            for source in sources:
                for cell in self.preferences.get_adjacent_cells(source):
                    if self.preferences.is_visibility_applied:
                        player.visible_opponent.add(cell)
                        if cell in self.trenches:
                            player.visible_terrain.add(cell)
                            player.visible_terrain.add(
                                self.preferences.get_symmetric_cell(cell)
                            )
                    if cell in sources:
                        continue
                    if cell in player.walls:
                        new_sources.add(cell)
                    elif cell not in opponent.walls and cell not in player.units:
                        player.reachable.add(cell)
            if not new_sources:
                break
            sources.update(new_sources)

    def _init_players(self) -> None:
        edge = self.preferences.size
        self.active_player.units.add((1, 1))
        self.passive_player.units.add((edge, edge))
        if self.preferences.is_double_base:
            self.active_player.units.add((1, edge))
            self.passive_player.units.add((edge, 1))

    def _generate_trenches(self) -> Iterable[Cell]:
        if not self.preferences.trench_density_percent:
            return
        size = self.preferences.size
        half = (size + 1) // 2
        for x in range(size):
            for y in range(half):
                if (
                    (y < half - 1 or x < half)
                    and (x + 1, y + 1) not in self.active_player.units
                    and (x + 1, y + 1) not in self.passive_player.units
                    and randint(1, 100) <= self.preferences.trench_density_percent
                ):
                    yield x + 1, y + 1
                    yield size - x, size - y


class IllegalTurnException(Exception):
    pass
