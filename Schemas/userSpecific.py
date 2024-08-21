from datetime import datetime
from typing import List
from pydantic import BaseModel

class EventData(BaseModel):
    event_id: str
    payment_id: str
    paid_amount: float
    payment_date: datetime


from typing import List
from pydantic import BaseModel

class UserSpecific(BaseModel):
    id: str
    userId: str
    booked_events: List[EventData]
    recent_searches: List[str]
    interest_areas: List[str]

    def add_search(self, search_term: str):
        # Remove the search term if it's already in the list (to update its position)
        if search_term in self.recent_searches:
            self.recent_searches.remove(search_term)
        
        # Add the search term to the front of the list
        self.recent_searches.insert(0, search_term)

        # Ensure the list only contains the last 10 search terms
        if len(self.recent_searches) > 10:
            self.recent_searches.pop()

    def to_dict(self):
        return {
            "id": self.id,
            "userId": self.userId,
            "booked_events": [event.to_dict() for event in self.booked_events],
            "recent_searches": self.recent_searches,
            "interest_areas": self.interest_areas
        }
