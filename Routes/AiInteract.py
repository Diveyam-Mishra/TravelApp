from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List
from Controllers.AiInteract import generate_questions, suggest_events
from Controllers.Events import get_filtered_events
# from Routes.EventRoutes import filter_events
from Models.user_models import User
from Controllers.Auth import get_current_user
router = APIRouter()
from typing import Optional
from datetime import datetime
from Schemas.EventSchemas import EventFilter
from Database.Connection import get_container
from sqlalchemy.orm import Session
from config import JWTBearer

class Params(BaseModel):
    userName: str
    age: int


class Preferences(BaseModel):
    VibePreference:str
    LocationPreference: str
    EngagementLevel:str
    InterestAreas: List[str]
    Budget: str
    date_preference: Optional[str] = None
    specific_date: Optional[datetime] = None
    time_preference: Optional[List[str]] = None
    location_preference: Optional[str] = None
    duration_preference: Optional[str] = None
    event_type_preference:Optional[List[str]] = None
    user_latitude: float = None
    user_longitude: float = None
    user_city: Optional[str] = None


@router.post("/ai/get_questions/",dependencies=[Depends(JWTBearer())])
async def get_questions(params: Params, current_user: User=Depends(get_current_user)):
    if current_user is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    questions = generate_questions(f"username:{params.userName}, age:{params.age}")
    return {"Questions":questions}


@router.post("/ai/get_events/",dependencies=[Depends(JWTBearer())])
async def get_events(Preferences: Preferences, event_container=Depends(get_container), current_user: User=Depends(get_current_user)):
    if current_user is None:
            raise HTTPException(status_code=400, detail="User Not Found")
    filters = EventFilter(
        date_preference=Preferences.date_preference,
        specific_date=Preferences.specific_date,
        time_preference=Preferences.time_preference,
        location_preference=Preferences.location_preference,
        event_type_preference=Preferences.event_type_preference,
        duration_preference=Preferences.duration_preference,
        user_latitude=Preferences.user_latitude,
        user_longitude=Preferences.user_longitude,
        user_city=Preferences.user_city
    )
    input_str = (f"Vibe preference: {Preferences.VibePreference}, Location Preference: {Preferences.LocationPreference}, Engagement Level: {Preferences.EngagementLevel}, Interest Areas: {Preferences.InterestAreas}, Budget: {Preferences.Budget}")

    list_of_filtered_events = await get_filtered_events(event_container, filters, current_user)
    result = [{"id": event["event_id"], "name": event["event_name"], "description": event["event_description"]} for event in list_of_filtered_events]
    # print(result)

    events = suggest_events(input_str, result, current_user)

    return {"eventsSuggested":events}
