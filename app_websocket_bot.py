import json
import random
import time

from websockets.sync.client import connect
from websockets.exceptions import ConnectionClosedOK

from paper_tactics.entities.game import Game
from paper_tactics.entities.game_bot import GameBot
from paper_tactics.entities.game_preferences import GamePreferences
from paper_tactics.entities.game_view import GameView
from paper_tactics.entities.player import Player
from paper_tactics.entities.player_view import PlayerView


def start_websocket_bot():
    bot = GameBot()
    while True:  # play games forever
        print('connecting to websocket...')
        try:
            with connect("wss://az7ndrlaxk.execute-api.eu-central-1.amazonaws.com/rolling") as websocket:
                print('connected!')
                print('requesting game...')
                websocket.send('''{
                    "action": "create-game",
                    "view_data": {
                      "iconIndex": "0",
                      "timeZone": "America/New_York",
                      "os": "Linux"
                    },
                    "preferences": {
                      "size": 10,
                      "turn_count": 3,
                      "is_visibility_applied": false,
                      "is_against_bot": false,
                      "trench_density_percent": 0,
                      "is_double_base": false,
                      "code": ""
                    }
                }''')
                while True:
                    message = websocket.recv()
                    #print(f"Received: {message}")
                    event = json.loads(message)
                    if event['me']['is_defeated'] or event['me']['is_gone']:
                        print('I lose!')
                        break  # stop playing this game
                    if event['opponent']['is_defeated'] or event['opponent']['is_gone']:
                        print('I win!')
                        break  # stop playing this game
                    if event['my_turn']:
                        print('my turn!')
                        game_view = parse_game_view(event)
                        game = game_view_to_game(game_view)
                        print('thinking...')
                        moves = bot.make_turn(game)
                        print('done thinking! Decided on moves ' + str(moves))
                        for x, y in moves:
                            print('sending move ' + str(x) + ', ' + str(y))
                            websocket.send(json.dumps({
                                "action": "make-turn",
                                "gameId": game.id,
                                "cell": [
                                    x,
                                    y
                                ]
                            }))
                            time.sleep(0.5 + (random.random() * 1))  # 0.5-1.5 seconds
                        # Can't send multiple moves without the server queuing up multiple messages
                        # Have to swallow the "game updated" messages from each move we send (except for the last message)
                        for unused in range(len(moves)-1):
                            websocket.recv()
                            time.sleep(1)
                print('waiting a bit before the next game...')
                # wait a few seconds before the next game (to allow players to claim the "first player" spot
                time.sleep(5 + (random.random() * 10))  # 5-15 seconds
        except ConnectionClosedOK:
            print('!lost connection!')
            # wait a few minutes if there aren't any other players
            time.sleep(3 + (random.random() * 120))  # 3-5 minutes


def game_view_to_game(game_view: GameView) -> Game:
    game = Game(
        id=game_view.id,
        preferences=game_view.preferences,
        turns_left=game_view.turns_left,
        active_player=Player(
            id="",  # todo: this may break one day
            units=set(game_view.me.units),
            walls=set(game_view.me.walls),
            reachable=set(game_view.me.reachable),
            visible_opponent=set(game_view.opponent.units.union(game_view.opponent.walls)),
            visible_terrain=set(),  # todo
            view_data=dict(),  # todo
            is_gone=game_view.me.is_gone,
            is_defeated=game_view.me.is_defeated,

        ),
        passive_player=Player(
            id="",  # todo, this may break one day
            units=set(game_view.opponent.units),
            walls=set(game_view.opponent.walls),
            reachable=set(game_view.opponent.reachable),
            visible_opponent=set(game_view.me.units.union(game_view.me.walls)),
            visible_terrain=set(),  # todo
            view_data=dict(),  # todo
            is_gone=game_view.opponent.is_gone,
            is_defeated=game_view.opponent.is_defeated,

        ),
        trenches=game_view.trenches
    )
    # For some reason, the opponent's reachable set is always empty in the GameView
    game._rebuild_reachable_set(game.passive_player, game.active_player)
    return game


def parse_game_view(event: dict) -> GameView:
    return GameView(
        id=event['id'],
        turns_left=event['turns_left'],
        my_turn=event['my_turn'],
        me=PlayerView(
            units=frozenset([(x, y) for x, y in event['me']['units']]),
            walls=frozenset([(x, y) for x, y in event['me']['walls']]),
            reachable=frozenset([(x, y) for x, y in event['me']['reachable']]),
            view_data=event['me']['view_data'],
            is_gone=event['me']['is_gone'],
            is_defeated=event['me']['is_defeated']
        ),
        opponent=PlayerView(
            units=frozenset([(x, y) for x, y in event['opponent']['units']]),
            walls=frozenset([(x, y) for x, y in event['opponent']['walls']]),
            reachable=frozenset([(x, y) for x, y in event['opponent']['reachable']]),
            view_data=event['opponent']['view_data'],
            is_gone=event['opponent']['is_gone'],
            is_defeated=event['opponent']['is_defeated']
        ),
        trenches=frozenset([(x, y) for x, y in event['trenches']]),
        preferences=GamePreferences(
            size=event['preferences']['size'],
            turn_count=event['preferences']['turn_count'],
            is_visibility_applied=event['preferences']['is_visibility_applied'],
            is_against_bot=event['preferences']['is_against_bot'],
            trench_density_percent=event['preferences']['trench_density_percent'],
            is_double_base=event['preferences']['is_double_base'],
            code=event['preferences']['code']
        )
    )


if __name__ == "__main__":
    random.seed(10000)
    start_websocket_bot()
