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

    def make_turn(self, game: Game) -> [Cell]:
        # print(game)
        # print()
        # for c in self.a_star_algorithm(game, [(game.preferences.size, game.preferences.size)], (2, 1)):
        #     print(c)
        return self.negamax_move(game)[:game.turns_left]

    def _weighted_move(self, game: Game):
        weights = [self._get_weight(cell, game) for cell in game.active_player.reachable]
        return [choices(list(game.active_player.reachable), weights)[0]]

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

    def negamax_move(self, game: Game) -> [Cell]:
        # store this many number of turns
        turns_to_make = game.turns_left
        moves_to_make = []
        possible_moves = game.active_player.reachable
        best_moves = []
        best_score = float('-inf')
        for cell in possible_moves:
            simulated_game = copy.deepcopy(game)
            simulated_game.preferences.hack_set_is_not_against_bot()
            simulated_game.make_turn(simulated_game.active_player.id, cell)
            score, moves = self.negamax(simulated_game, 3, float('-inf'), float('inf'), False)
            if score > best_score:
                best_score = score
                best_moves = [[cell] + moves]
            elif score == best_score:
                best_moves.append([cell] + moves)
        print('found best moves ' + str(best_moves) + ' with score of ' + str(best_score))
        return random.choice(best_moves)

    def negamax(self, game: Game, depth: int, alpha: float, beta: float, turn: bool) -> tuple[float, [Cell]]:
        if depth == 0 or game.active_player.is_defeated or game.passive_player.is_defeated:
            return self.evaluate_game_for_active_player(game), []
        possible_moves = game.active_player.reachable
        # possible_moves = sort(possible_moves)
        value = float('-inf')
        value_move = []
        for cell in possible_moves:
            simulated_game = copy.deepcopy(game)
            simulated_game.preferences.hack_set_is_not_against_bot()
            simulated_game.make_turn(simulated_game.active_player.id, cell)
            # turns were just reset after .make_turn()
            should_change_turn = simulated_game.turns_left == 2  #  simulated_game.preferences.turn_count
            recursion_modifier = -1 if should_change_turn else 1
            simulated_game_value_move = self.negamax(
                simulated_game,
                depth - 1,
                beta * recursion_modifier,
                alpha * recursion_modifier,
                not turn if should_change_turn else turn)
            simulated_game_value = simulated_game_value_move[0] * recursion_modifier
            if value < simulated_game_value:
                value = simulated_game_value
                value_move = [cell] + simulated_game_value_move[1]
            alpha = max(alpha, value)
            if alpha >= beta:
                break
        return value, value_move

    @staticmethod
    def evaluate_game_for_active_player(game: Game) -> float:
        if game.active_player.is_defeated:
            return float('-inf')
        if game.passive_player.is_defeated:
            return float('inf')
        points = 0
        # reachable squares
        points += 1 * len(game.active_player.reachable)
        points -= 1 * len(game.passive_player.reachable)
        # num of units
        points += 2 * len(game.active_player.units)
        points -= 2 * len(game.passive_player.units)
        # num of walls
        points += 8 * len(game.active_player.walls)
        points -= 8 * len(game.passive_player.walls)
        # todo connected walls
        # units touch a wall
        active_units_touching_wall_count = GameBot.count_of_units_touching_wall(game, game.active_player)
        points += 1000 if active_units_touching_wall_count > 0 else 0
        points += 16 * active_units_touching_wall_count
        passive_units_touching_wall_count = GameBot.count_of_units_touching_wall(game, game.passive_player)
        points -= 1000 if passive_units_touching_wall_count > 0 else 0
        points -= 16 * active_units_touching_wall_count
        # dist from friendly wall
        # todo: kind of the same as active_units_touching_wall_count
        active_dist_to_friendly_walls = GameBot.dist_to_walls(game, game.active_player)
        points -= 20 * (active_dist_to_friendly_walls - 2) if active_dist_to_friendly_walls is not None else 0
        passive_dist_to_friendly_walls = GameBot.dist_to_walls(game, game.passive_player)
        points += 20 * (passive_dist_to_friendly_walls - 2) if passive_dist_to_friendly_walls is not None else 0
        # todo
        #  dist from friendly wall
        #  if you can run far away enough to not allow your opponent to remove units from adjacent walls, +10
        #  length of wall, +2 * length
        #  keep opponent.units away from your units, keep opponent.units close to your walls, and vice-versa
        return points

    @staticmethod
    def count_of_units_touching_wall(game: Game, player: Player) -> int:
        return len(GameBot.get_units_touching_wall(game, player))

    @staticmethod
    def get_units_touching_wall(game: Game, player: Player) -> set[Cell]:
        if len(player.walls) > len(player.units):  # optimization
            cells = player.walls
            adjacents = player.units
        else:
            cells = player.units
            adjacents = player.walls
        return GameBot.flat_map_set(lambda adjacent: game.preferences.get_adjacent_cells(adjacent), adjacents) \
            .intersection(cells)

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

    @staticmethod
    def dist_to_walls(game: Game, player: Player) -> float:
        path_to_walls = GameBot.a_star_algorithm(
            game,
            game.active_player if player == game.active_player else game.passive_player,
            game.active_player if player != game.active_player else game.passive_player,
            player.units,
            player.walls)
        if path_to_walls is None:
            return None
        return len(path_to_walls)

    @staticmethod
    def dist_to_closest_enemy(game: Game) -> int:
        return len(GameBot.a_star_algorithm(
            game,
            game.active_player,
            game.passive_player,
            game.active_player.units,
            game.passive_player.units.union(game.passive_player.walls)))

    @staticmethod
    def a_star_algorithm(game: Game, player: Player, opponent: Player, start_cells: [Cell], goals: [Cell]):  # -> [Cell] | None
        # TODO make goal a list of Cells
        # Initially, only the start cell is known.
        open_set = []
        # For cell c, cheapest_score[c] is the cost of the cheapest path from start to c currently known.
        cheapest_score = defaultdict(lambda: float('inf'))
        # For cell c, h_score[c] := cheapest_score[c] + h(c).
        # h_score[c] represents our current best guess as to how cheap a path could be from start to finish if it goes through c.
        h_score = defaultdict(lambda: float('inf'))
        for start_cell in start_cells:
            open_set.append((0, start_cell))
            cheapest_score[start_cell] = 0
            h_score[start_cell] = GameBot._heuristic(start_cell, goals)
        heapq.heapify(open_set)

        # For cell c, cameFrom[c] is the cell immediately preceding it on the cheapest path from the start
        # to c currently known.
        cameFrom = {}

        while open_set:
            # This operation occurs in O(Log(N)) time since open_set is a min-heap
            cost_cell = heapq.heappop(open_set)
            current = cost_cell[1]
            if current in goals:
                # todo: optimization - don't have to reconstruct the path if we only want the cost
                return GameBot._reconstruct_path(cameFrom, current)

            for cost, neighbor in GameBot._get_friendly_neighbors(game, player, opponent, current):
                # tentative_cheapest_score is the distance from start to the neighbor through current
                tentative_cheapest_score = cheapest_score[current] + cost
                if tentative_cheapest_score < cheapest_score[neighbor]:
                    # This path to neighbor is better than any previous one. Record it!
                    cameFrom[neighbor] = current
                    cheapest_score[neighbor] = tentative_cheapest_score
                    h_score[neighbor] = tentative_cheapest_score + GameBot._heuristic(neighbor, goals)
                    if neighbor not in open_set:
                        heapq.heappush(open_set, (tentative_cheapest_score, neighbor))

        # Open set is empty but goal was never reached
        return None

    @staticmethod
    def _heuristic(start: Cell, goals: [Cell]) -> float:
        return 0  # todo
        # return GameBot._heuristic_single(start, goal)

    @staticmethod
    def _heuristic_single(start: Cell, goal: Cell) -> float:
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
    def _get_friendly_neighbors(game: Game, player: Player, opponent: Player, cell: Cell) -> [(Cell, int)]:
        """
        :return: a list of friendly neighbors and their cost of getting there
        """
        # Start with exploring in each of the 8 directions
        neighbors = []
        for candidate in game.preferences.get_adjacent_cells(cell):
            if candidate in player.walls:  # check for friendly walls
                neighbors.append((0, candidate))
            elif candidate in opponent.walls:  # check for opponent walls
                pass  # skip
            elif candidate in opponent.units:  # check for opponent units
                pass  # skip
            else:  # empty cell or untaken trench
                neighbors.append((1, candidate))
        return neighbors
