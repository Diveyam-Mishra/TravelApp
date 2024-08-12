from fastapi import Depends
from Models.user_models import User
from Controllers.Auth import get_current_user
from Schemas.UserSchemas import *
from Schemas.EventSchemas import *
from datetime import datetime, timedelta
import random

async def get_category_events(
    filters: List[str], 
    event_container
):
    query = "SELECT * FROM c WHERE c.event_type IN ({})".format(
    ",".join(["'{}'".format(event) for event in filters])
)
    events = list(event_container.query_items(
        query=query,
        enable_cross_partition_query=True
    ))
    print(events)
    return events
#filters Coming as Objects



async def get_sponsered_events(
    event_container, 
    limit: int = 10
):
    random_offset = random.randint(0, 100)
    query = """
    SELECT * FROM adcontainer e 
    WHERE ST_DISTANCE({
        'type': 'Point', 
        'coordinates': [@user_lon, @user_lat]
    }, e.location) <= 10000
    OFFSET @random_offset LIMIT @limit
    """

    params = [
        {"name": "@random_offset", "value": random_offset},
        {"name": "@limit", "value": limit}
    ]
    events = list(event_container.query_items(
        query=query,
        parameters=params,
        enable_cross_partition_query=True
    ))

    return events
async def search_events_by_name(
    partial_name: str, 
    event_container, 
):
    query = """
    SELECT * FROM eventcontainer e 
    WHERE STARTSWITH(e.event_name, @partial_name)
    """

    params = [
        {"name": "@partial_name", "value": partial_name}
    ]

    events = list(event_container.query_items(
        query=query,
        parameters=params,
        enable_cross_partition_query=True
    ))
    return events

async def search_events_by_creator(
    creator_id: int,
    event_container
):
    query = """
    SELECT * FROM eventcontainer e 
    WHERE e.creator_id = @creator_id
    """

    params = [
        {"name": "@creator_id", "value": creator_id}
    ]

    events = list(event_container.query_items(
        query=query,
        parameters=params,
        enable_cross_partition_query=True
    ))
    return events
