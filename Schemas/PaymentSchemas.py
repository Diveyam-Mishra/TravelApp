from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime



class PaymentInformation(BaseModel):
    transactionId: str
    data: dict
    paymentDate: Optional[str] = datetime.now().isoformat()
    members: Optional[int] = None
    addedInEventBooking: Optional[bool] = False
    id:str

    def to_dict(self):
        return {
            "id":self.id,
            "transactionId": self.transactionId,
            "data": self.data,
            "payment_date": self.paymentDate,
            "members": self.members,
            "added_in_event_booking": self.addedInEventBooking
        }


class UserBookings(BaseModel):
    user_id: str
    bookings: List[PaymentInformation]

    def add_booking(self, booking_details: PaymentInformation):
        self.bookings.append(booking_details)

    def get_bookings(self):
        return self.bookings

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "bookings": [booking.to_dict() for booking in self.bookings]
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
    id: str
    event_id: str
    booked_users: List[UserBookings] = []
    attended_users: List[AttendedInformation] = []

    def to_dict(self):
        return {
            "id": self.id,
            "event_id": self.event_id,
            "booked_users": [user.to_dict() for user in self.booked_users],
            "attended_users": [user.to_dict() for user in self.attended_users]
        }

    def add_new_user(self, userId: str):
        if not any(bookings.user_id == userId for bookings in self.booked_users):
            self.booked_users.append(UserBookings(user_id=userId, bookings=[]))

    def add_booking_by_user_id(self, userId: str, booking_details: PaymentInformation):
        # Find the user booking by userId
        print('reached')
        user_booking = next((user for user in self.booked_users if user.user_id == userId), None)
        
        if user_booking:
            # User exists, add the booking to the existing user
            user_booking.add_booking(booking_details)
        else:
            # User does not exist, create a new UserBookings and add the booking
            new_user_booking = UserBookings(user_id=userId, bookings=[booking_details])
            self.booked_users.append(new_user_booking)

    
    def get_bookings_by_user_id(self, userId: str) -> List[PaymentInformation]:
        for user in self.booked_users:
            if user.user_id == userId:
                return user.get_bookings()
        return []
        

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
    paid_amount: int
    payment_id: str
    members_details: int
    


class PaymentConfirmationRedirectBody(BaseModel):
    response: str