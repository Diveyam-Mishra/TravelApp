from Schemas.UserSchemas import *
from Schemas.EventSchemas import *
import random
import math
import asyncio

def event_distance(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1

    # Corrected formula for 'a'
    a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2

    c = 2 * math.asin(math.sqrt(a))
    r = 6371  
    distance = c * r
    return round(distance, 2)


async def get_event_of_single_category(category: str, event_container, file_container):
    # Query to fetch events of a specific category
    query = f"SELECT c.event_id, c.event_name, c.event_description, c.event_type, c.location FROM c WHERE ARRAY_CONTAINS(c.event_type, '{category}')"

    events = []
    event_ids = []

    for event in event_container.query_items(query=query, enable_cross_partition_query=True):
        events.append(event)
        event_ids.append(event['event_id'])

    if not event_ids:
        return events

    # Parallel execution of image queries
    async def fetch_image(event_id):
        image_query = f"SELECT TOP 1 c.fileName1, c.fileUrl1, c.fileType1 FROM c WHERE c.eventId = '{event_id}'"
        image_results = list(file_container.query_items(query=image_query, enable_cross_partition_query=True))
        return image_results[0] if image_results else None

    image_futures = [fetch_image(event_id) for event_id in event_ids]
    images = await asyncio.gather(*image_futures)

    for event, image in zip(events, images):
        if image:
            event['thumbnail'] = {
                "file_name": image.get('fileName1'),
                "file_url": image.get('fileUrl1'),
                "file_type": image.get('fileType1')
            }

    return events

async def update_events_with_thumbnails(event_container, file_container):
    # Query to fetch all events
    query = "SELECT * FROM c"

    # List to hold all event updates
    updates = []
    print("ok")
    async def update_event(event):
        # Fetch the first image associated with the event
        image_query = f"SELECT TOP 1 c.fileName1, c.fileUrl1, c.fileType1 FROM c WHERE c.eventId = '{event['event_id']}'"
        image_results = list(file_container.query_items(query=image_query, enable_cross_partition_query=True))

        if image_results:
            # Add the first image's details to the event
            image = image_results[0]
            event['thumbnail'] = {
                "file_name": image.get('fileName1'),
                "file_url": image.get('fileUrl1'),
                "file_type": image.get('fileType1')
            }
            # Update the event in the database
            await event_container.replace_item(item=event['event_id'], body=event)
            print("done")

    # Fetch and update each event
    for event in event_container.query_items(query=query, enable_cross_partition_query=True):
        updates.append(update_event(event))

    # Run all updates concurrently
    # await asyncio.gather(*updates)

    return "Events updated with thumbnails."

async def get_category_events(filters: List[str], coord: List[float], event_container, page: int):
    # Fetch all events
    query = "SELECT * FROM c"
    
    events = []
    for event in event_container.query_items(
            query=query,
            enable_cross_partition_query=True
        ):
        # Count the number of matched types
        match_count = sum(1 for event_type in filters if event_type in event['event_type'])
        
        if match_count > 0:
            event['match_count'] = match_count
            event['distance'] = event_distance(
                event['location']['geo_tag']['latitude'],
                event['location']['geo_tag']['longitude'],
                coord[0],
                coord[1]
            )
            events.append(event)

    # Sort events based on the number of matching types
    sorted_events = sorted(events, key=lambda e: e['match_count'], reverse=True)
    total_count = len(sorted_events)
    items_per_page = 15
    start_index = page * items_per_page
    end_index = start_index + items_per_page
    paginated_events = sorted_events[start_index:end_index]

    return {
        "cnt": total_count,
        "results": paginated_events
    }

#filters Coming as Objects



async def get_sponsered_events(
    event_container, 
    limit: int = 10
):
    random_offset = random.randint(0, 100)
    query = """
    SELECT * FROM adcontainer e 
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
    partialname: PartialName,
    coord:List[float], 
    event_container,
    file_container , page
):
    query = """
    SELECT * FROM c 
    WHERE CONTAINS(LOWER(c.event_name), LOWER(@partial_name))
    """

    params = [
        {"name": "@partial_name", "value": partialname.partial_name.lower()}  # Convert the search term to lowercase
    ]

    events = list(event_container.query_items(
        query=query,
        parameters=params,
        enable_cross_partition_query=True
    ))

    # Fetch and attach the thumbnail (first image file) for each event
    for event in events:
        event['distance']=event_distance(event['location']['geo_tag']['latitude'],event['location']['geo_tag']['longitude'],coord[0],coord[1])
    total_count = len(events)
    items_per_page = 15
    start_index = page * items_per_page
    end_index = start_index + items_per_page
    paginated_events = events[start_index:end_index]

    return {
        "cnt": total_count,
        "results": paginated_events
    }

async def search_events_by_creator(
    creator_id: CreatorId,
    coord:List[float],
    event_container,page
):
    query = """
    SELECT * FROM eventcontainer e 
    WHERE e.creator_id = @creator_id
    """

    params = [
        {"name": "@creator_id", "value": creator_id.creator}
    ]

    events = list(event_container.query_items(
        query=query,
        parameters=params,
        enable_cross_partition_query=True
    ))
    for event in events:
        event['distance']=event_distance(event['location']['geo_tag']['latitude'],event['location']['geo_tag']['longitude'],coord[0],coord[1])
    
    total_count = len(events)
    items_per_page = 15
    start_index = page * items_per_page
    end_index = start_index + items_per_page
    paginated_events = events[start_index:end_index]
        
    return {
        "cnt": total_count,
        "results": paginated_events
    }
