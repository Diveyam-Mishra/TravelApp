from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel

class CreditCard(BaseModel):
    card_number: str
    card_holder_name: str
    expiry_date: str

    def to_dict(self):
        return{

            "card_number" :self.card_number,
            "card_holder_name": self.card_holder_name,
            "expiry_date": self.expiry_date
        }

class EventData(BaseModel):
    event_id: str
    payment_id: str
    paid_amount: float
    payment_date: datetime
    event_date: str  # Storing event_date as an ISO string
    ticket_id: Optional[str] = None

    class Config:
        extra = 'allow'

    def to_dict(self):
        return {
            "event_id": self.event_id,
            "payment_id": self.payment_id,
            "paid_amount": self.paid_amount,
            "payment_date": self.payment_date.isoformat(),
            "event_date": self.event_date,
            "ticket_id": self.ticket_id
        }

class BankingDetails(BaseModel):
    account_no: str
    ifsc_code: str
    PAN: str
    GST_no: str
    bank_name:str

    class Config:
        extra = 'allow'

    def to_dict(self):
        return {
            "account_no": self.account_no,
            "ifsc_code": self.ifsc_code,
            "PAN": self.PAN,
            "GST_no": self.GST_no,
            "bank_name": self.bank_name
        }
class UserSpecific(BaseModel):
    id: str
    userId: str
    booked_events: List[EventData]
    recent_searches: List[str]
    interest_areas: List[str]
    credit_cards: Optional[List[CreditCard]]=[]
    bank_details: Optional[BankingDetails]= None
    class Config:
        extra = 'allow'

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
            "interest_areas": self.interest_areas,
            "credit_cards":[credit_card.to_dict() for credit_card in self.credit_cards],
            "bank_details": self.bank_details.to_dict() if self.bank_details else None

        }
    def add_credit_card(self, card: CreditCard):
        for existing_card in self.credit_cards:
            if existing_card.card_number == card.card_number:
                raise ValueError("Card already exists")
        self.credit_cards.append(card)

    def add_banking_details(self, banking_details: BankingDetails):
        self.bank_details = banking_details