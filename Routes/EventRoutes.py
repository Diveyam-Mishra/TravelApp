from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, HTTPException, Form, Body
from Schemas.UserSchemas import SuccessResponse, UserId
from Schemas.EventSchemas import *
from Database.Connection import *
from Controllers.Events import create_event, update_event, get_filtered_events, \
    give_editor_access, get_event_by_id, advertise_event
from sqlalchemy.orm import Session
from config import JWTBearer
from Controllers.Auth import get_current_user
from Models.user_models import User
router = APIRouter()
from typing import List, Dict
from Controllers.Files import create_event_and_upload_files
import json


@router.post("/event/create/", dependencies=[Depends(JWTBearer())], response_model=SuccessResponse)
async def create_event(
    event_name: str=Form(...),
    event_description: str=Form(...),
    event_type: List[str]=Form(...),
    start_date_and_time: str=Form(...),
    end_date_and_time: str=Form(...),
    age_group: str=Form(...),
    family_friendly: bool=Form(...),
    price_fees: float=Form(...),
    capacity: int=Form(...),
    host_information: str=Form(...),
    location_venue: str=Form(...),
    location_lat: float=Form(...),
    location_long: float=Form(...),
    location_city: str=Form(...),
    files: List[UploadFile]=File(...),
    container=Depends(get_container),
    fileContainer=Depends(get_file_container),
    current_user: User=Depends(get_current_user),
    blob_client=Depends(get_blob_service_client)
):
    if current_user is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    # Parse the JSON strings into Python objects
    # start_date_and_time = DateTimeDetails(**json.loads(start_date_and_time))
    # end_date_and_time = DateTimeDetails(**json.loads(end_date_and_time))
    # price_fees = PriceDetails(**json.loads(price_fees))
    # host_information = HostDetails(**json.loads(host_information))
    location = Location(
        venue=location_venue,
        geo_tag=GeoTag(latitude=location_lat, longitude=location_long),
        city=location_city
    )
    # print(location)
    event_data = EventDetails(
        event_name=event_name,
        event_description=event_description,
        event_type=event_type,
        start_date_and_time=start_date_and_time,
        end_date_and_time=end_date_and_time,
        age_group=age_group,
        family_friendly=family_friendly,
        price_fees=price_fees,
        capacity=capacity,
        host_information=host_information,
        location=location
    )

    return await create_event_and_upload_files(event_data, files, current_user, container, fileContainer, blob_client)


@router.post("/event/{eventId}/edit/", dependencies=[Depends(JWTBearer())], response_model=SuccessResponse)
async def edit_event(
    eventId:str,
    event_name: str=Form(...),
    event_description: str=Form(...),
    event_type: List[str]=Form(...),
    start_date_and_time: str=Form(...),
    end_date_and_time: str=Form(...),
    age_group: str=Form(...),
    family_friendly: bool=Form(...),
    price_fees: float=Form(...),
    capacity: int=Form(...),
    host_information: str=Form(...),
    location_venue: str=Form(...),
    location_lat: float=Form(...),
    location_long: float=Form(...),
    location_city: str=Form(...),
    files: List[UploadFile]=File(...),
    container=Depends(get_container),
    fileContainer=Depends(get_file_container),
    current_user: User=Depends(get_current_user),
    blob_client=Depends(get_blob_service_client)):
    if current_user is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    location = Location(
        venue=location_venue,
        geo_tag=GeoTag(latitude=location_lat, longitude=location_long),
        city=location_city
    )
    event_data = EventDetails(
        event_name=event_name,
        event_description=event_description,
        event_type=event_type,
        start_date_and_time=start_date_and_time,
        end_date_and_time=end_date_and_time,
        age_group=age_group,
        family_friendly=family_friendly,
        price_fees=price_fees,
        capacity=capacity,
        host_information=host_information,
        location=location
    )
    return await update_event(eventId, event_data, files, current_user, container, fileContainer, blob_client)


@router.post("/event/filtered/", dependencies=[Depends(JWTBearer())])
async def filter_events(filters: EventFilter, event_container=Depends(get_container), current_user: User=Depends(get_current_user)):
    if(current_user is None):
        raise HTTPException(status_code=401, detail="Unauthorized")
    events = await get_filtered_events(event_container, filters, current_user=current_user)
    # print (events)
    result = [{"id": event["id"], "name": event["event_name"], "description": event["event_description"]} for event in events]
    return result


@router.get("/event/details/{eventId}", response_model=SearchEvent)
async def get_event(eventId: str, event_container=Depends(get_container), file_container=Depends(get_file_container),lat:float=0.0, long:float=0.0):
    event = await get_event_by_id(eventId, event_container, file_container, lat, long)
    if event:
        return event
    else:
        raise HTTPException(status_code=404, detail="Event not found")


@router.post("/event/{eventId}/give-edit-access/", dependencies=[Depends(JWTBearer())], response_model=SuccessResponse)
async def add_editor(
    eventId: str,  # Add eventId as a path parameter
    userId: UserId,  # Ensure userId is of type int
    container=Depends(get_container),
    db: Session=Depends(get_db),
    current_user: User=Depends(get_current_user)
) -> SuccessResponse:
    return await give_editor_access(db, userId.userid, eventId, current_user, container)


@router.post("/event/advertise/", response_model=SuccessResponse)
async def add_advertisement(eventId: takeString, container=Depends(get_container), advertised_events_container=Depends(get_advertisement_container)) -> SuccessResponse:
    print("ok")
    return await advertise_event(eventId, advertised_events_container, container)
