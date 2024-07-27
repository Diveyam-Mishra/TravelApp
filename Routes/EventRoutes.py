from fastapi import APIRouter, Depends
from Schemas.UserSchemas import SuccessResponse
from Schemas.EventSchemas import EventDetails,EventDetailsupdate
from Database.Connection import get_db
from Controllers.Events import create_event, update_event
from sqlalchemy.orm import Session
from Controllers.Auth import get_current_user
from Models.user_models import User
from Database.Connection import get_container
router = APIRouter()


@router.post("/event/create", response_model=SuccessResponse)
async def add_event(event_data: EventDetails, container=Depends(get_container), current_user: User = Depends(get_current_user)):
    return await create_event(event_data, container, current_user)

@router.post("/event/edit", response_model=SuccessResponse)
async def edit_event(event_data: EventDetailsupdate, container=Depends(get_container), current_user: User = Depends(get_current_user)):
    return await update_event(event_data, container, current_user)