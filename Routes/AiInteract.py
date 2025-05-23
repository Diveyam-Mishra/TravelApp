from fastapi import APIRouter, Depends, HTTPException,BackgroundTasks
from pydantic import BaseModel
from typing import List
from Controllers.AiInteract import generate_questions, suggest_events
from Controllers.Events import get_filtered_events
# from Routes.EventRoutes import filter_events
from Controllers.Auth import get_user_specific_data
from Models.user_models import User
from Controllers.Auth import get_current_user
router = APIRouter()
from typing import Optional
from datetime import datetime
from Schemas.EventSchemas import EventFilter
from Database.Connection import get_container,get_user_specific_container
from sqlalchemy.orm import Session
from config import JWTBearer
import random
class Params(BaseModel):
    userName: str
    age: int


class Preferences(BaseModel):
    VibePreference:str
    LocationPreference: str
    EngagementLevel:str
    Budget: str
    Paragraph_Question_1_O:Optional[str]=None
    Paragraph_Question_2_O:Optional[str]=None
    date_preference_O: Optional[str] = None
    specific_date_O: Optional[datetime] = None
    time_preference_O: Optional[List[str]] = None
    distance_preference_O: Optional[str] = None
    duration_preference_O: Optional[str] = None
    event_type_preference_O:Optional[List[str]] = None
    user_latitude: float = None
    user_longitude: float = None
    user_city_O: Optional[str] = None


@router.post("/ai/get_questions/",dependencies=[Depends(JWTBearer())])
async def get_questions(params: Params, current_user: User=Depends(get_current_user)):
    if current_user is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    questions = generate_questions(f"username:{params.userName}, age:{params.age}")
    return {"Questions":questions}


@router.post("/ai/get_events/",dependencies=[Depends(JWTBearer())])
async def get_events(Preferences: Preferences, background_tasks: BackgroundTasks,event_container=Depends(get_container), current_user: User=Depends(get_current_user),user_specific_container=Depends(get_user_specific_container)):
    if current_user is None:
            raise HTTPException(status_code=400, detail="User Not Found")
    userId = current_user.id
    if not Preferences.event_type_preference_O:
        resp = await get_user_specific_data(userId, user_specific_container, event_container)
        if resp:     
            k=resp['interest_areas']
        else:
            k=[]
    filters = EventFilter(
        date_preference=Preferences.date_preference_O,
        specific_date=Preferences.specific_date_O,
        time_preference=Preferences.time_preference_O,
        location_preference=Preferences.distance_preference_O,
        event_type_preference=Preferences.event_type_preference_O if Preferences.event_type_preference_O else k,
        duration_preference=Preferences.duration_preference_O,
        user_latitude=Preferences.user_latitude,
        user_longitude=Preferences.user_longitude,
        user_city=Preferences.user_city_O
    )
    if Preferences.date_preference_O == "Today" or Preferences.date_preference_O == "Tomorrow" or Preferences.date_preference_O == "This week" or  Preferences.date_preference_O == "today" or Preferences.date_preference_O == "tomorrow" or Preferences.date_preference_O == "this week":
        filters.specific_date = None
    elif Preferences.date_preference_O=="Anytime"or Preferences.date_preference_O=="anytime":
        filters.specific_date = None
        filters.date_preference = None
    else:
        filters.specific_date = filters.date_preference
        filters.date_preference = "Specific Date"

    # print(filters)

    input_str = (f"Vibe preference: {Preferences.VibePreference}, Location Preference: {Preferences.LocationPreference}, Engagement Level: {Preferences.EngagementLevel},  Interest Areas: {Preferences.event_type_preference_O if Preferences.event_type_preference_O else k},Budget: {Preferences.Budget}")
    # update_needed = False
    # if Preferences.Paragraph_Question_1_O:
    #     resp['paragraph_question_1'] = Preferences.Paragraph_Question_1_O
    #     update_needed = True

    # if Preferences.Paragraph_Question_2_O:
    #     resp['paragraph_question_2'] = Preferences.Paragraph_Question_2_O
    #     update_needed = True

    # # Update user-specific container only if necessary
    # if update_needed:
    #     user_specific_container.replace_item(item=resp['id'], body=resp)
    background_tasks.add_task(update_user_specific_data, user_specific_container, event_container, userId, Preferences)
    list_of_filtered_events = await get_filtered_events(event_container, filters, current_user)
    result = [{"id": event["id"], "name": event["event_name"], "description": event["event_description"]} for event in list_of_filtered_events]
    # print(result)
    if len(result) > 100:
        result = result[:100]
    # print(len(result))
    events = await suggest_events(input_str, result, current_user)
    if len(events) > 0:
        return {"eventsSuggested":events}
    else:
        query = "SELECT e.event_ID FROM event_container e WHERE IS_STRING(e.start_date_and_time) AND e.start_date_and_time > @now OFFSET @random_offset LIMIT 6"
        now = datetime.now().isoformat()
        random_offset = random.randint(0, 30)
        params = [{"name": "@random_offset", "value": random_offset},{"name": "@now", "value": now}]
        items = list(event_container.query_items(query=query, parameters=params, enable_cross_partition_query=True,max_item_count=6))
        event_ids = [item["event_ID"] for item in items]
        return {"eventsSuggested":event_ids}

    

async def update_user_specific_data(user_specific_container, event_container, userId,Preferences: Preferences):
    resp = await get_user_specific_data(userId, user_specific_container, event_container)
    update_needed = False
    # print("Yes")
    if Preferences.Paragraph_Question_1_O:
        # print("Yes")
        resp['paragraph_question_1'] = Preferences.Paragraph_Question_1_O
        update_needed = True
    # print("Yes")
    if Preferences.Paragraph_Question_2_O:
        # print("Yes")
        resp['paragraph_question_2'] = Preferences.Paragraph_Question_2_O
        update_needed = True
    # print("Yes")
    # Update user-specific container only if necessary
    if update_needed:
        # print("Yes")
        user_specific_container.replace_item(item=resp['id'], body=resp)