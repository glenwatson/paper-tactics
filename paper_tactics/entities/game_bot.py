import copy
import random
from dataclasses import dataclass
from random import choices
import heapq
from collections import defaultdict
from typing import List

from paper_tactics.entities.cell import Cell
from paper_tactics.entities.game import Game
from paper_tactics.entities.player import Player


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

    def make_turn(self, game: Game) -> Cell:
        # print(game)
        # print()
        # for c in self.a_star_algorithm(game, [(game.preferences.size, game.preferences.size)], (2, 1)):
        #     print(c)
        return self.negamax_move(game)

    def _weighted_move(self, game: Game):
        weights = [self._get_weight(cell, game) for cell in game.active_player.reachable]
        return choices(list(game.active_player.reachable), weights)[0]

    def _get_weight(self, cell: Cell, game: Game) -> float:
        if cell in game.passive_player.units:
            if any(
                    cell_ in game.active_player.units
                    for cell_ in game.preferences.get_adjacent_cells(cell)
            ):
                return self.neighbour_opponent_unit_weight
            return self.opponent_unit_weight

        if cell in game.trenches:
            return self.trench_weight

        if any(
                cell_ in game.passive_player.walls
                for cell_ in game.preferences.get_adjacent_cells(cell)
        ):
            return self.opponent_wall_weight

        opponent_count = sum(
            1
            for cell_ in game.preferences.get_adjacent_cells(cell)
            if cell_ in game.active_player.units
        )
        if opponent_count >= game.turns_left:
            return self.trap_weight
        if opponent_count > 0:
            return self.taunt_weight

        if not game.preferences.is_visibility_applied:
            x, y = cell
            for cell_ in ((x, y + 1), (x, y - 1), (x + 1, y), (x - 1, y)):
                if cell_ in game.active_player.walls or cell_ in game.active_player.units:
                    return self.horizontal_weight
            return self.diagonal_weight

        discoverable_count = sum(
            1
            for cell_ in game.preferences.get_adjacent_cells(cell)
            if cell_ not in game.active_player.reachable
        )
        return (discoverable_count + 1) * self.discoverable_weight

    def negamax_move(self, game: Game) -> Cell:
        possible_moves = game.active_player.reachable
        best_moves = []
        best_score = float('-inf')
        for cell in possible_moves:
            simulated_game = copy.deepcopy(game)
            simulated_game.preferences.hack_set_is_not_against_bot()
            simulated_game.make_turn(simulated_game.active_player.id, cell)
            score = self.negamax(simulated_game, 3, float('-inf'), float('inf'), False)
            if score > best_score:
                best_score = score
                best_moves = [cell]
            elif score == best_score:
                best_moves.append(cell)
        print('found best moves ' + str(best_moves) + ' with score of ' + str(best_score))
        return random.choice(best_moves)

    def negamax(self, game: Game, depth: int, alpha: float, beta: float, turn: bool) -> float:
        if depth == 0 or game.active_player.is_defeated or game.passive_player.is_defeated:
            return self.evaluate_game_for_active_player(game) * 1 if turn else -1
        possible_moves = game.active_player.reachable
        # possible_moves = sort(possible_moves)
        value = float('-inf')
        for cell in possible_moves:
            simulated_game = copy.deepcopy(game)
            simulated_game.preferences.hack_set_is_not_against_bot()
            simulated_game.make_turn(simulated_game.active_player.id, cell)
            value = max(value, -self.negamax(simulated_game, depth-1, -beta, -alpha, not turn))
            alpha = max(alpha, value)
            if alpha >= beta:
                break
        return value

    @staticmethod
    def evaluate_game_for_active_player(game: Game) -> float:
        points = 0
        points += len(game.active_player.reachable)
        points -= len(game.passive_player.reachable)
        points += len(game.active_player.units)
        points -= len(game.passive_player.units)
        points += 4 * len(game.active_player.walls)
        points -= 4 * len(game.passive_player.walls)
        # todo
        #  if you can remove opponents units from adjacent walls, +10
        #  if you can run far away enough to not allow your opponent to remove units from adjacent walls, +10
        #  length of wall, +2 * length
        return points

    def count_of_units_touching_wall(self, game: Game, player: Player) -> int:
        if len(player.walls) > len(player.units):  # optimization
            cells = player.walls
            adjacents = player.units
        else:
            cells = player.units
            adjacents = player.walls
        return len(self.flat_map_set(lambda adjacent: game.preferences.get_adjacent_cells(adjacent), adjacents)
                   .intersection(cells))

    @staticmethod
    def flat_map_list(f, collection) -> List:
        ret = []
        for item in collection:
            ret.extend(f(item))
        return ret

    @staticmethod
    def flat_map_set(f, collection) -> set:
        ret = set()
        for item in collection:
            ret.add(f(item))
        return ret


    def dist_to_closest_enemy(self, game: Game) -> int:
        pass

    def a_star_algorithm(self, game: Game, start_cells: [Cell], goal: Cell):  # -> [Cell] | None
        # TODO make goal a list of Cells
        # Initially, only the start cell is known.
        open_set = []
        # For cell c, cheapest_score[c] is the cost of the cheapest path from start to c currently known.
        cheapest_score = defaultdict(lambda: float('inf'))
        # For cell c, h_score[c] := cheapest_score[c] + h(c).
        # h_score[c] represents our current best guess as to how cheap a path could be from start to finish if it goes through c.
        h_score = defaultdict(lambda: float('inf'))
        for start_cell in start_cells:
            open_set = [(0, start_cell)]
            cheapest_score[start_cell] = 0
            h_score[start_cell] = self._heuristic(start_cell, goal)
        heapq.heapify(open_set)

        # For cell c, cameFrom[c] is the cell immediately preceding it on the cheapest path from the start
        # to c currently known.
        cameFrom = {}

        while open_set:
            # This operation occurs in O(Log(N)) time since open_set is a min-heap
            cost_cell = heapq.heappop(open_set)
            current = cost_cell[1]
            if current == goal:
                return self._reconstruct_path(cameFrom, current)

            for cost_neighbor in self._get_friendly_neighbors(game, current):
                neighbor = cost_neighbor[1]
                # tentative_cheapest_score is the distance from start to the neighbor through current
                tentative_cheapest_score = cheapest_score[current] + cost_neighbor[0]
                if tentative_cheapest_score < cheapest_score[neighbor]:
                    # This path to neighbor is better than any previous one. Record it!
                    cameFrom[neighbor] = current
                    cheapest_score[neighbor] = tentative_cheapest_score
                    h_score[neighbor] = tentative_cheapest_score + self._heuristic(neighbor, goal)
                    if neighbor not in open_set:
                        heapq.heappush(open_set, (tentative_cheapest_score, neighbor))

        # Open set is empty but goal was never reached
        return None

    @staticmethod
    def _heuristic(start: Cell, goal: Cell) -> float:
        """
        https://en.wikipedia.org/wiki/Chebyshev_distance
        This is NOT admissible due to friendly walls being present which could shorten the
        length of the path to get to the goal. (https://en.wikipedia.org/wiki/Admissible_heuristic)
        It may be impossible to be able to accurately estimate the distance to get to the goal, in
        which case we need to fall back to Dijkstra's (A* without a heuristic)
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
    def _get_friendly_neighbors(game: Game, cell: Cell) -> [(Cell, int)]:
        """
        :return: a list of friendly neighbors and their cost of getting there
        """
        # Start with exploring in each of the 8 directions
        neighbors = []
        for candidate in game.preferences.get_adjacent_cells(cell):
            if candidate in game.active_player.walls:  # check for friendly walls
                neighbors.append((0, candidate))
            elif candidate in game.passive_player.walls:  # check for opponent walls
                pass  # skip
            elif candidate in game.passive_player.units:  # check for opponent units
                pass  # skip
            else:  # empty cell or untaken trench
                neighbors.append((1, candidate))
        return neighbors
