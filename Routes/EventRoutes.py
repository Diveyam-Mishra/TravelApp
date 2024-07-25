from fastapi import APIRouter, Depends
from Schemas.UserSchemas import SuccessResponse
from Schemas.EventSchemas import EventDetails
from Database.Connection import get_db
from Controllers.Events import create_event, update_event
from sqlalchemy.orm import Session
from Controllers.Auth import get_current_user
from Models.user_models import User

router = APIRouter()


@router.post("/event/create", response_model=SuccessResponse)
def add_event(event_data: EventDetails, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    res = create_event(db, event_data, current_user)
    return res

@router.post("/event/edit", response_model=SuccessResponse)
def edit_event(event_data: EventDetails, db: Session = Depends(get_db), current_user: User=Depends(get_current_user)):
    res = update_event(db, event_data, current_user)
    return res