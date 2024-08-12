from fastapi import APIRouter, Depends, HTTPException,File, UploadFile, HTTPException, Form
from Schemas.UserSchemas import SuccessResponse, UserId
from Schemas.EventSchemas import *
from Database.Connection import get_db, get_container, get_file_container
from Controllers.Events import create_event, update_event, get_filtered_events, \
    give_editor_access
from sqlalchemy.orm import Session
from config import JWTBearer
from Controllers.Auth import get_current_user
from Models.user_models import User
from Database.Connection import get_container
router = APIRouter()
from typing import List, Dict
from Controllers.Files import create_event_and_upload_files
import json

@router.post("/event/create/",dependencies=[Depends(JWTBearer())], response_model=SuccessResponse)
async def create_event(
    event_name: str = Form(...),
    event_description: str = Form(...),
    event_type: List[str] = Form(...),
    start_date_and_time: str = Form(...),
    end_date_and_time: str = Form(...),
    age_group: str = Form(...),
    family_friendly: bool = Form(...),
    price_fees: str = Form(...),
    capacity: int = Form(...),
    host_information: str = Form(...),
    location: str = Form(...),
    files: List[UploadFile] = File(...),
    container=Depends(get_container),
    fileContainer=Depends(get_file_container),
    current_user: User = Depends(get_current_user)
):
    if current_user is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    # Parse the JSON strings into Python objects
    start_date_and_time = DateTimeDetails(**json.loads(start_date_and_time))
    end_date_and_time = DateTimeDetails(**json.loads(end_date_and_time))
    price_fees = PriceDetails(**json.loads(price_fees))
    host_information = HostDetails(**json.loads(host_information))
    location = Location(**json.loads(location))
    
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

    return await create_event_and_upload_files(event_data, files, current_user, container, fileContainer)


@router.post("/event/{eventId}/edit/",dependencies=[Depends(JWTBearer())], response_model=SuccessResponse)
async def edit_event(eventId: str, event_data: EventDetailsupdate, container=Depends(get_container), current_user: User = Depends(get_current_user)):
    return await update_event(eventId, event_data, container, current_user)


@router.post("/events/filtered/", response_model=List[Dict[str, str]])
def filter_events(filters: EventFilter, db: Session=Depends(get_db)):
    events = get_filtered_events(db, filters)
    result = [{"id": event.id, "name": event.name, "description": event.description} for event in events]
    # print(result)
    return result


@router.post("/events/{eventId}/give-edit-access/", dependencies=[Depends(JWTBearer())],response_model=SuccessResponse)
async def add_editor(
    eventId: str,  # Add eventId as a path parameter
    userId: UserId,  # Ensure userId is of type int
    container=Depends(get_container),
    db: Session=Depends(get_db),
    current_user: User=Depends(get_current_user)
) -> SuccessResponse:
    return await give_editor_access(db, userId.userid, current_user, eventId, container)
