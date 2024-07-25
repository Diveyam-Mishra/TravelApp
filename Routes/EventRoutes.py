from fastapi import APIRouter, Depends
from Schemas.UserSchemas import SuccessResponse
from Schemas.EventSchemas import EventDetails
from Database.Connection import get_db
from Controllers.Events import create_event
from sqlalchemy.orm import Session

router = APIRouter()


@router.post("/event/create", response_model=SuccessResponse)
def add_event(event_data: EventDetails, db: Session=Depends(get_db)):
    res = create_event(db, event_data)
    return res
