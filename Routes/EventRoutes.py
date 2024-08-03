from fastapi import APIRouter, Depends, HTTPException
from Schemas.UserSchemas import SuccessResponse, UserId
from Schemas.EventSchemas import EventDetails, EventDetailsupdate, EventFilter
from Database.Connection import get_db
from Controllers.Events import create_event, update_event, get_filtered_events, \
    give_editor_access
from sqlalchemy.orm import Session
from Controllers.Auth import get_current_user
from Models.user_models import User
from Database.Connection import get_container
router = APIRouter()
from typing import List, Dict


@router.post("/event/create", response_model=SuccessResponse)
async def add_event(event_data: EventDetails, container=Depends(get_container), current_user: User = Depends(get_current_user)):
    if current_user is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return await create_event(event_data, current_user, container)

@router.post("/event/{eventId}/edit", response_model=SuccessResponse)
async def edit_event(eventId: str, event_data: EventDetailsupdate, container=Depends(get_container), current_user: User = Depends(get_current_user)):
    return await update_event(eventId, event_data, container, current_user)


@router.post("/events/filtered", response_model=List[Dict[str, str]])
def filter_events(filters: EventFilter, db: Session=Depends(get_db)):
    events = get_filtered_events(db, filters)
    result = [{"id": event.id, "name": event.name, "description": event.description} for event in events]
    # print(result)
    return result


@router.post("/events/{eventId}/give-edit-access", response_model=SuccessResponse)
async def add_editor(
    eventId: str,  # Add eventId as a path parameter
    userId: UserId,  # Ensure userId is of type int
    container=Depends(get_container),
    db: Session=Depends(get_db),
    current_user: User=Depends(get_current_user)
) -> SuccessResponse:
    return await give_editor_access(db, userId.userid, current_user, eventId, container)
