from pydantic import BaseModel
from typing import List, Optional
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
    email: Optional[str] = None
    UserName: Optional[str] = None
    event_name: Optional[str] = None
    eventId:str
    userId:str
    event_date: Optional[str] = None
    event_time: Optional[str] = None
    event_venue: Optional[str] = None
    ticketId: Optional[str] = None
    organizer: Optional[str] = None
    paid_amount: str
    payment_id: str
    members_details: str
    
