from fastapi import APIRouter, Depends, Query
from Database.Connection import get_container, get_file_container, get_redis
from typing import List
from Schemas.EventSchemas import*
from Controllers.Filters import *
from typing import Optional, List
from config import JWTBearer
from operator import itemgetter
import json
router = APIRouter()


@router.get("/events/filtered/category", response_model=SearchEventResultWithCnt)
async def filter_events_v1(
    filters: List[str] = Query(...),
    page: int = 0,
    event_container=Depends(get_container),
    file_container=Depends(get_file_container),
    redis = Depends(get_redis)
):
    unique_events = set()
    items_per_page = 15

    for category in filters:
        cache_key = f"events:{category}"

        cached_data = redis.get(cache_key)

        if cached_data:
            category_events = json.loads(cached_data)
        else:
            category_events = await get_event_of_single_category(category, event_container, file_container)

            redis.set(cache_key, json.dumps(category_events))
        
        for event in category_events:
            unique_events.add(json.dumps(event))
    
    unique_events_list = [json.loads(event) for event in unique_events]

    start_index = page * items_per_page
    paginated_events = unique_events_list[start_index:start_index + items_per_page]
    # print(paginated_events)
    result = [
        {
            "id": event.get("event_id"),
            "name": event.get("event_name"),
            "description": event.get("event_description"),
            "type": event.get("event_type"),
            "thumbnail": event.get("thumbnail"),
            "location": event.get("location")
        } for event in paginated_events
    ]

    # Return the updated response
    return {
        "cnt": len(unique_events),
        "results": result
    }



@router.post("/events/filtered/category/", response_model=SearchEventResultWithCnt)
async def filter_events(
    filters: List[str],
    coord: List[float],
    event_container=Depends(get_container),
    page: int = 0
):
    eventsRes = await get_category_events(filters, coord, event_container, page)
    
    # Extract the total count and results from the response
    total_count = eventsRes['cnt']
    events = eventsRes['results']
    
    # Sort the events based on the number of matching types
    sorted_events = sorted(events, key=itemgetter('match_count'), reverse=True)

    # Format the results
    result = [
        {
            "id": event.get("event_id"),
            "name": event.get("event_name"),
            "description": event.get("event_description"),
            "type": event.get("event_type"),
            "thumbnail": event.get("thumbnail"),
            "distance": f"{event.get('distance')} km"
        } for event in sorted_events
    ]

    # Return the updated response
    return {
        "cnt": total_count,
        "results": result
    }

# @router.get("/events/search_by_name_and_access/", response_model=List[Dict[str, str]])
# async def search_events_by_name_with_access(
#     partial_name: str, 
#     creator_id: int,
#     editor_id: str,
#     event_container=Depends(get_container)
# ):
#     events = await search_events_by_name_with_access(partial_name, creator_id, editor_id, event_container)
#     result = [{"id": event["id"], "name": event["event_name"], "description": event["event_description"]} for event in events]
#     return result


@router.post("/events/search_by_name/", response_model=SearchEventResultWithCnt)
async def search_events_by_name1(
    partial_name: PartialName,
    coord:List[float],
    event_container=Depends(get_container),
    file_container=Depends(get_file_container),page: int = 0
):
    eventsRes = await search_events_by_name(partial_name, coord, event_container, file_container, page)
    
    total_count = eventsRes['cnt']
    events = eventsRes['results']
    # Create the result list with the required fields
    result = [
        {
            "id": event["id"],
            "name": event["event_name"],
            "description": event["event_description"],
            "type": event.get("event_type"),
            "thumbnail": event.get("thumbnail"), 
            "distance":str(event["distance"])+"km"
        } 
        for event in events
    ]
    # print(len(result))
    return {
        "cnt": total_count,
        "results": result
    }


@router.post("/events/search_by_creator/", response_model=SearchEventResultWithCnt)
async def search_events_by_creator1(
    creator_id: CreatorId,
    coord: List[float],
    event_container=Depends(get_container),
    page: int = 0
):
    eventsRes = await search_events_by_creator(creator_id,coord, event_container, page)
    total_count = eventsRes['cnt']
    events = eventsRes['results']
    result = [{"id": event["id"], "name": event["event_name"], "description": event["event_description"], "type":event.get("event_type"), "thumbnail":event.get("thumbnail"), "distance":str(event["distance"])+"km"} for event in events]
    return {
        "cnt": total_count,
        "results": result
    }
@router.post("/events/search_by_creator_past/", response_model=SearchEventResultWithCnt)
async def search_events_by_creator_past1(
    creator_id: CreatorId,
    coord: List[float],
    event_container=Depends(get_container),
    page: int = 0
):
    eventsRes = await search_events_by_creator_past(creator_id,coord, event_container, page)
    total_count = eventsRes['cnt']
    events = eventsRes['results']
    result = [{"id": event["id"], "name": event["event_name"], "description": event["event_description"], "type":event.get("event_type"), "thumbnail":event.get("thumbnail"), "distance":str(event["distance"])+"km"} for event in events]
    return {
        "cnt": total_count,
        "results": result
    }
@router.post("/events/search_by_creator/", response_model=SearchEventResultWithCnt)
async def search_events_by_creator_future1(
    creator_id: CreatorId,
    coord: List[float],
    event_container=Depends(get_container),
    page: int = 0
):
    eventsRes = await search_events_by_creator_future(creator_id,coord, event_container, page)
    total_count = eventsRes['cnt']
    events = eventsRes['results']
    result = [{"id": event["id"], "name": event["event_name"], "description": event["event_description"], "type":event.get("event_type"), "thumbnail":event.get("thumbnail"), "distance":str(event["distance"])+"km"} for event in events]
    return {
        "cnt": total_count,
        "results": result
    }
