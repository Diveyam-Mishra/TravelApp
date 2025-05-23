from fastapi import APIRouter, Depends, Query
from Database.Connection import get_container, get_file_container, \
    get_db, get_user_specific_container, get_booking_container,\
    AsyncSessionLocal
from typing import List
from Schemas.EventSchemas import*
from Controllers.Filters import *
from typing import Optional, List
from config import JWTBearer
from operator import itemgetter
import json
from Models.user_models import User
from Controllers.Auth import get_current_user, add_recent_search, oauth2_scheme, \
    get_current_user_optional
from fastapi.exceptions import HTTPException
from sqlalchemy.orm import Session

router = APIRouter()


async def get_optional_current_user(
    token: Optional[str] = Depends(JWTBearer(auto_error=False)), db: AsyncSessionLocal = Depends(get_db)
) -> Optional[User]:
    if token is None:
        return None

    user = await get_current_user_optional(token.credentials, db)
    return user


# @router.get("/events/filtered/category", response_model=SearchEventResultWithCnt)
# async def filter_events_v1(
#     filters: List[str]=Query(...),
#     page: int=0,
#     event_container=Depends(get_container),
#     file_container=Depends(get_file_container)
# ):
#     unique_events = set()
#     items_per_page = 15

#     for category in filters:
        
#             category_events = await get_event_of_single_category(category, event_container, file_container)

            
        
#         for event in category_events:
#             unique_events.add(json.dumps(event))
    
#     unique_events_list = [json.loads(event) for event in unique_events]

#     start_index = page * items_per_page
#     paginated_events = unique_events_list[start_index:start_index + items_per_page]
#     # #print(paginated_events)
#     result = [
#         {
#             "id": event.get("event_id"),
#             "name": event.get("event_name"),
#             "description": event.get("event_description"),
#             "type": event.get("event_type"),
#             "thumbnail": event.get("thumbnail"),
#             "location": event.get("location")
#         } for event in paginated_events
#     ]

#     # Return the updated response
#     return {
#         "cnt": len(unique_events),
#         "results": result
#     }


@router.post("/events/filtered/category/")
async def filter_events(
    filters: List[str],
    coord: List[float],
    event_container=Depends(get_container),
    page: int=0
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
            "id": event.get("id"),
            "name": event.get("event_name"),
            "description": event.get("event_description"),
            "type": event.get("event_type"),
            "thumbnail": {
                    "file_name": event.get("thumbnail", {}).get("fileName"),
                    "file_url": event.get("thumbnail", {}).get("fileUrl"),
                    "file_type": event.get("thumbnail", {}).get("fileType"),
                } if event.get("thumbnail") else None,
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

import time

@router.post("/events/search_by_name/", response_model=SearchEventResultWithCnt)
async def search_events_by_name1(
    partial_name: PartialName,
    coord: List[float],
    event_container=Depends(get_container),
    current_user: Optional[User] = Depends(get_optional_current_user),
    user_specific_container=Depends(get_user_specific_container),
    page: int = 0
):
    start_time = time.time()  # Start the timer

    if current_user is not None:
        # Track time taken for adding recent search
        recent_search_start = time.time()
        await add_recent_search(current_user.id, partial_name.partial_name, user_specific_container)
        recent_search_time = time.time() - recent_search_start
        print(f"Time taken for add_recent_search: {recent_search_time:.6f} seconds")  # Log the time

    # Track time taken for searching events
    search_events_start = time.time()
    eventsRes = await search_events_by_name(partial_name, coord, event_container, page)
    search_events_time = time.time() - search_events_start
    print(f"Time taken for search_events_by_name: {search_events_time:.6f} seconds")  # Log the time

    total_count = eventsRes['cnt']
    events = eventsRes['results']

    # Track time taken for processing results
    processing_start = time.time()
    result = [
        {
            "id": event["id"],
            "name": event["event_name"],
            "description": event["event_description"],
            "type": event.get("event_type"),
            "thumbnail": {
                "file_name": event.get("thumbnail", {}).get("fileName") or event.get("thumbnail", {}).get("file_name"),
                "file_url": event.get("thumbnail", {}).get("fileUrl") or event.get("thumbnail", {}).get("file_url"),
                "file_type": event.get("thumbnail", {}).get("fileType") or event.get("thumbnail", {}).get("file_type"),
            } if event.get("thumbnail") else None,
            "distance": str(event["distance"]) + "km"
        } 
        for event in events
    ]
    processing_time = time.time() - processing_start
    print(f"Time taken for processing results: {processing_time:.6f} seconds")  # Log the time

    total_time = time.time() - start_time  # Total execution time
    print(f"Total time taken for search_events_by_name1: {total_time:.6f} seconds")  # Log the time

    return {
        "cnt": total_count,
        "results": result
    }


@router.post("/events/search_by_creator/" , dependencies=[Depends(JWTBearer())], response_model=SearchEventResultWithCnt)
async def search_events_by_creator1(
    creator_id: CreatorId,
    coord: List[float],
    event_container=Depends(get_container),
    current_user=Depends(get_current_user),
    page: int=0
):
    eventsRes = await search_events_by_creator(coord, event_container, page,creator_id)
    total_count = eventsRes['cnt']
    events = eventsRes['results']
    result = [{"id": event["id"], "name": event["event_name"], "description": event["event_description"], "type":event.get("event_type"), "thumbnail":event.get("thumbnail"), "distance":str(event["distance"]) + "km"} for event in events]
    return {
        "cnt": total_count,
        "results": result
    }


@router.get("/events/search_by_creator/{time}", dependencies=[Depends(JWTBearer())], response_model=SearchEventResultWithCnt)
async def search_own_event_time(
    time:str,
    current_user: User=Depends(get_current_user),
    event_container=Depends(get_container),
    bookingContainer=Depends(get_booking_container),
    db=Depends (get_db),
    page: int=0

):
    eventsRes = await search_events_by_creator_past_v1(time, db, bookingContainer, event_container, page, current_user)
    total_count = eventsRes['cnt']
    events = eventsRes['results']
    result = [
        {
            "id": event["id"],
            "name": event["event_name"],
            "description": event["event_description"],
            "type":event.get("event_type"),
            "thumbnail":event.get("thumbnail") ,
            "booked_users":event.get("booked_users"),
            "location": event.get("location"),
            "start_date_and_time": event["start_date_and_time"],
            "end_date_and_time": event["end_date_and_time"],
            "age_group": event["age_group"],
            "family_friendly":event["family_friendly"],
            "price_fees": event["price_fees"],
            "capacity": event["capacity"],
            "editor_access":event.get("editor_access"),
            "total_booking_amount": event.get("total_booking_amount") or 0
        } 
           for event in events
        ]
    return {
        "cnt": total_count,
        "results": result
    }
