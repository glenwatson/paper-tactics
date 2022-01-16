import os

import boto3
from hypothesis import assume
from hypothesis.strategies import composite
from hypothesis.strategies import integers
from hypothesis.strategies import text

from paper_tactics.adapters.dynamodb_game_repository import DynamodbGameRepository
from paper_tactics.adapters.dynamodb_player_queue import DynamodbPlayerQueue


@composite
def dynamodb_player_queues(draw) -> DynamodbPlayerQueue:
    return DynamodbPlayerQueue(*draw(_dynamodb_tables()))


@composite
def dynamodb_game_repositories(draw) -> DynamodbGameRepository:
    return DynamodbGameRepository(*draw(_dynamodb_tables()))


@composite
def _dynamodb_tables(draw):
    table_name = draw(text(min_size=3))
    key = draw(text(min_size=1))
    ttl_key = draw(text(min_size=1))
    ttl_in_seconds = draw(integers(min_value=0, max_value=10 ** 10))

    assume(key != ttl_key)

    os.environ["AWS_DEFAULT_REGION"] = "eu-central-1"

    client = boto3.client("dynamodb")

    try:
        client.delete_table(TableName=table_name)
    except client.exceptions.ResourceNotFoundException:
        pass

    client.create_table(
        TableName=table_name,
        KeySchema=[
            {
                "AttributeName": key,
                "KeyType": "HASH",
            }
        ],
        AttributeDefinitions=[
            {
                "AttributeName": key,
                "AttributeType": "S",
            }
        ],
    )

    return table_name, key, ttl_key, ttl_in_seconds
