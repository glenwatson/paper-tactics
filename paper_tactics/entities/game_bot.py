from dataclasses import dataclass
from random import choices
import heapq
from collections import defaultdict

from paper_tactics.entities.cell import Cell
from paper_tactics.entities.game_view import GameView


@dataclass(frozen=True)
class GameBot:
    # TODO not aggressive
    neighbour_opponent_unit_weight: float = 10
    opponent_unit_weight: float = 7
    trench_weight: float = 5
    opponent_wall_weight: float = 0.3
    trap_weight: float = 0.05
    taunt_weight: float = 2
    diagonal_weight: float = 1.5
    horizontal_weight: float = 1
    discoverable_weight: float = 1

    def make_turn(self, game_view: GameView) -> Cell:
        weights = [self._get_weight(cell, game_view) for cell in game_view.me.reachable]
        return choices(list(game_view.me.reachable), weights)[0]

    def _get_weight(self, cell: Cell, game_view: GameView) -> float:
        if cell in game_view.opponent.units:
            if any(
                cell_ in game_view.me.units
                for cell_ in game_view.preferences.get_adjacent_cells(cell)
            ):
                return self.neighbour_opponent_unit_weight
            return self.opponent_unit_weight

        if cell in game_view.trenches:
            return self.trench_weight

        if any(
            cell_ in game_view.opponent.walls
            for cell_ in game_view.preferences.get_adjacent_cells(cell)
        ):
            return self.opponent_wall_weight

        opponent_count = sum(
            1
            for cell_ in game_view.preferences.get_adjacent_cells(cell)
            if cell_ in game_view.opponent.units
        )
        if opponent_count >= game_view.turns_left:
            return self.trap_weight
        if opponent_count > 0:
            return self.taunt_weight

        if not game_view.preferences.is_visibility_applied:
            x, y = cell
            for cell_ in ((x, y + 1), (x, y - 1), (x + 1, y), (x - 1, y)):
                if cell_ in game_view.me.walls or cell_ in game_view.me.units:
                    return self.horizontal_weight
            return self.diagonal_weight

        discoverable_count = sum(
            1
            for cell_ in game_view.preferences.get_adjacent_cells(cell)
            if cell_ not in game_view.me.reachable
        )
        return (discoverable_count + 1) * self.discoverable_weight

    def dist_to_closest_enemy(self, game_view: GameView) -> int:
        pass

    def a_star_algorithm(self, game_view: GameView, start_cells: [Cell], goal: Cell):  # -> [Cell] | None
        # Initially, only the start cell is known.
        openSet = []
        # For cell c, gScore[c] is the cost of the cheapest path from start to c currently known.
        gScore = defaultdict(lambda: float('inf'))
        # For cell c, fScore[c] := gScore[c] + h(c).
        # fScore[c] represents our current best guess as to how cheap a path could be from start to finish if it goes through c.
        fScore = defaultdict(lambda: float('inf'))
        for start_cell in start_cells:
            openSet = [(0, start_cell)]
            gScore[start_cell] = 0
            fScore[start_cell] = self._heuristic(start_cell, goal)
        heapq.heapify(openSet)

        # For cell c, cameFrom[c] is the cell immediately preceding it on the cheapest path from the start
        # to c currently known.
        cameFrom = {}

        while openSet:
            # This operation occurs in O(Log(N)) time since openSet is a min-heap
            cost_cell = heapq.heappop(openSet)
            current = cost_cell[1]
            if current == goal:
                return self._reconstruct_path(cameFrom, current)

            for cost_neighbor in self.get_friendly_neighbors(game_view, current):
                neighbor = cost_neighbor[1]
                # tentative_gScore is the distance from start to the neighbor through current
                tentative_gScore = gScore[current] + cost_neighbor[0]
                if tentative_gScore < gScore[neighbor]:
                    # This path to neighbor is better than any previous one. Record it!
                    cameFrom[neighbor] = current
                    gScore[neighbor] = tentative_gScore
                    fScore[neighbor] = tentative_gScore + self._heuristic(neighbor, goal)
                    if neighbor not in openSet:
                        heapq.heappush(openSet, (tentative_gScore, neighbor))

        # Open set is empty but goal was never reached
        return None

    @staticmethod
    def _heuristic(start: Cell, goal: Cell) -> float:
        """
        https://en.wikipedia.org/wiki/Chebyshev_distance
        This is not admissible due to friendly walls being present which could shorten the
        length of the path to get to the goal. (https://en.wikipedia.org/wiki/Admissible_heuristic)
        It may be impossible to be able to accurately estimate the distance to get to the goal.
        Further (good) reading: https://theory.stanford.edu/~amitp/GameProgramming/Heuristics.html#speed-or-accuracy
        Idea: subtract length of longest friendly wall
        """
        return max(abs(goal[0] - start[0]), abs(goal[1] - start[1]))

    @staticmethod
    def _reconstruct_path(came_from: dict[Cell, Cell], current: Cell) -> [Cell]:
        total_path = [current]
        while current in came_from.keys():
            current = came_from[current]
            total_path.append(current)
        return total_path

    @staticmethod
    def get_friendly_neighbors(game_view: GameView, cell: Cell) -> [(Cell, int)]:
        """
        :return: a list of friendly neighbors and their cost of getting there
        """
        # Start with exploring in each of the 8 directions
        neighbors = []
        for candidate in game_view.preferences.get_adjacent_cells(cell):
            if candidate in game_view.me.walls:  # check for friendly walls
                neighbors.append((0, candidate))
            elif candidate in game_view.opponent.walls:  # check for opponent walls
                pass  # skip
            elif candidate in game_view.opponent.units:  # check for opponent units
                pass  # skip
            else:  # empty cell or untaken trench
                neighbors.append((1, candidate))
        return neighbors
