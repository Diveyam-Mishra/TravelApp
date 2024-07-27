from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
from Controllers.AiInteract import generate_questions, suggest_events
router = APIRouter()


class Params(BaseModel):
    userName: str
    age: int


class Preferences(BaseModel):
    VibePreference:str
    LocationPreference: str
    EngagementLevel:str
    InterestAreas: List[str]
    Budget: str


@router.post("/ai/get_questions")
async def get_questions(params: Params):
    questions = generate_questions(f"username:{params.userName}, age:{params.age}")
    return {"Questions":questions}


@router.post("/ai/get_events")
async def get_events(Preferences: Preferences):
    events = suggest_events(f"vibe preference:{Preferences.VibePreference}, LocationPreference:{Preferences.LocationPreference}, EngagementLevel:{Preferences.EngagementLevel}, InterestAreas:{Preferences.InterestAreas}, Budget:{Preferences.Budget}")

    return {"eventsSuggested":events}
