from fastapi import APIRouter, Depends
from Database.Connection import get_container, get_file_container
from typing import List
from Schemas.EventSchemas import*
from Controllers.Filters import *
from typing import Optional, List
from config import JWTBearer
from operator import itemgetter
router = APIRouter()


@router.post("/events/filtered/category/", response_model=List[SearchEventResult])
async def filter_events(filters: List[str], event_container=Depends(get_container), file_container=Depends(get_file_container)):
    events = await get_category_events(filters, event_container, file_container)
    
    # Sort the events based on the number of matching types
    sorted_events = sorted(events, key=itemgetter('match_count'), reverse=True)

    # print(sorted_events)
    result = [{"id": event["id"], "name": event["event_name"], "description": event["event_description"], "type":event.get("event_type"), "thumbnail":event.get("thumbnail"), "distance":"3.2km"} for event in sorted_events]
    return result

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


@router.get("/events/search_by_name/{partial_name}/", response_model=List[SearchEventResult])
async def search_events_by_name1(
    partial_name: str,
    event_container=Depends(get_container),
    file_container=Depends(get_file_container)
):
    events = await search_events_by_name(partial_name, event_container, file_container)
    
    # Create the result list with the required fields
    result = [
        {
            "id": event["id"],
            "name": event["event_name"],
            "description": event["event_description"],
            "type": event.get("event_type"),
            "thumbnail": event.get("thumbnail"), "distance":"3.2km"
        } 
        for event in events
    ]
    # print(len(result))
    return result


@router.get("/events/search_by_creator/{creator_id}/", response_model=List[SearchEventResult])
async def search_events_by_creator1(
    creator_id: int,
    event_container=Depends(get_container)
):
    events = await search_events_by_creator(creator_id, event_container)
    result = [{"id": event["id"], "name": event["event_name"], "description": event["event_description"], "type":event.get("event_type"), "thumbnail":event.get("thumbnail"), "distance":"3.2km"} for event in events]
    return result
