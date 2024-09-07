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
    ticketId: Optional[str] = None

    def to_dict(self):
        return {
            "id":self.id,
            "transactionId": self.transactionId,
            "data": self.data,
            "payment_date": self.paymentDate,
            "members": self.members,
            "added_in_event_booking": self.addedInEventBooking,
            "ticketId": self.ticketId
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
    transactionId : str
    ticketId: str
    members: str  

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "transactionId": self.transactionId,
            "ticketId": self.ticketId,
            "members": self.members
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
        # #print('reached')
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
    
    def get_bookings_by_user_id_n_transaction_id(self, userId: str, transactionId: str) -> PaymentInformation:
        for user in self.booked_users:
            if user.user_id == userId:
                booking = user.get_bookings()
                for booking_details in booking:
                    if booking_details.transactionId == transactionId:
                        return booking_details
        return []
        

class ticketData(BaseModel):
    email_O: Optional[str] = None
    UserName_O: Optional[str] = None
    event_name_O: Optional[str] = None
    eventId:str
    userId_O:Optional[str] = None
    event_date_O: Optional[str] = None
    event_time_O: Optional[str] = None
    event_venue_O: Optional[str] = None
    ticketId_O: Optional[str] = None
    organizer_O: Optional[str] = None
    paid_amount_O: Optional[int] = None
    payment_id_O: Optional[str] = None
    members_details_O: Optional[str] = None
    


class PaymentConfirmationRedirectBody(BaseModel):
    response: str