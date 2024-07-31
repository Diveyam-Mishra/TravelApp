from fastapi import APIRouter, Depends
from Schemas.UserSchemas import SuccessResponse
from Schemas.EventSchemas import EventDetails,EventDetailsupdate, EventFilter
from Database.Connection import get_db
from Controllers.Events import create_event, update_event, get_filtered_events
from sqlalchemy.orm import Session
from Controllers.Auth import get_current_user
from Models.user_models import User
from Database.Connection import get_container
router = APIRouter()
from typing import List, Dict
from fastapi.responses import JSONResponse


@router.post("/event/create", response_model=SuccessResponse)
async def add_event(event_data: EventDetails, container=Depends(get_container), current_user: User = Depends(get_current_user)):
    return await create_event(event_data, container, current_user)

@router.post("/event/edit", response_model=SuccessResponse)
async def edit_event(event_data: EventDetailsupdate, container=Depends(get_container), current_user: User = Depends(get_current_user)):
    return await update_event(event_data, container, current_user)

@router.post("/events/filtered", response_model=List[Dict[str, str]])
def filter_events(filters: EventFilter, db: Session = Depends(get_db)):
    events = get_filtered_events(db, filters)
    result = [{"id": event.id, "name": event.name, "description": event.description} for event in events]
    # print(result)
    return result