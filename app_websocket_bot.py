import asyncio
import json
import time

from paper_tactics.adapters.stdout_logger import StdoutLogger
from paper_tactics.entities.game import Game
from paper_tactics.entities.game_bot import GameBot
from paper_tactics.entities.game_preferences import GamePreferences
from paper_tactics.entities.game_view import GameView
from paper_tactics.entities.player import Player
from paper_tactics.entities.player_view import PlayerView

logger = StdoutLogger()



from websockets.sync.client import connect


def hello():
    bot = GameBot()
    print('connecting to websocket...')
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
            print(f"Received: {message}")
            event = json.loads(message)
            if event['my_turn']:
                game_view = parse_game_view(event)
                game = game_view_to_game(game_view)
                print('thinking...')
                moves = bot.make_turn(game)
                print('done!')
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
                    time.sleep(1)



def game_view_to_game(game_view: GameView) -> Game:
    return Game(
        id=game_view.id,
        preferences=game_view.preferences,
        turns_left=game_view.turns_left,
        active_player=Player(
            id="",  # todo: this may break one day
            units=set(game_view.me.units),
            walls=set(game_view.me.walls),
            reachable=set(game_view.me.reachable),
            visible_opponent=set(),  # todo
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
            visible_opponent=set(),  # todo
            visible_terrain=set(),  # todo
            view_data=dict(),  # todo
            is_gone=game_view.opponent.is_gone,
            is_defeated=game_view.opponent.is_defeated,

        ),
        trenches=game_view.trenches
    )


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
    hello()
