from fastapi import APIRouter, Depends
from Database.Connection import get_container, get_file_container
from typing import List
from Schemas.EventSchemas import*
from Controllers.Filters import *
from typing import Optional, List
from config import JWTBearer
router = APIRouter()


@router.post("/events/filtered/category/", response_model=List[SearchEventResult])
async def filter_events(filters: List[str], event_container=Depends(get_container)):
    events = await get_category_events(event_container, filters)
    result = [{"id": event["id"], "name": event["event_name"], "description": event["event_description"]} for event in events]
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

@router.get("/events/search_by_name/{partial_name}/", response_model=List[SearchEvent])
async def search_events_by_name1(
    partial_name: str, 
    event_container=Depends(get_container)
):
    return await search_events_by_name(partial_name, event_container)
    

@router.get("/events/search_by_creator/{creator_id}/",response_model=List[SearchEventResult])
async def search_events_by_creator1(
    creator_id: int,
    event_container=Depends(get_container)
):
    events = await search_events_by_creator(creator_id, event_container)
    result = [{"id": event["id"], "name": event["event_name"], "description": event["event_description"]} for event in events]
    return result
