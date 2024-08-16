from pydantic import BaseModel
from typing import List
from datetime import datetime

class PaymentInformation(BaseModel):
    user_id: str
    payment_id: str
    paid_amount: float  
    payment_date: datetime

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "payment_id": self.payment_id,
            "paid_amount": self.paid_amount,
            "payment_date": self.payment_date.isoformat()  # Convert datetime to ISO 8601 string
        }

class AttendedInformation(BaseModel):
    user_id: str
    attended_at: datetime  

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "attended_at": self.attended_at.isoformat()  # Convert datetime to ISO 8601 string
        }

class PaymentLists(BaseModel):
    id:str
    event_id: str
    booked_users: List[PaymentInformation]
    attended_users: List[AttendedInformation]

    def to_dict(self):
        return {
            "id": self.id,
            "event_id": self.event_id,
            "booked_users": [user.to_dict() for user in self.booked_users],
            "attended_users": [user.to_dict() for user in self.attended_users]
        }


class ticketData(BaseModel):
    username: str
    event_name: str
    event_date: str
    event_venue: str
    ticketId: str
    organizer: str
    paid_amount: str
    payment_id: str
    