from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime



class PaymentInformation(BaseModel):
    transactionId: str
    # merchantId: str
    paymentDate: Optional[str] = datetime.now().isoformat()
    members: Optional[int] = None
    already_booked: Optional[bool] = False
    id:str
    status: Optional[str] = None
    amount: Optional[int]=None
    # method: Optional[str] = None
    ticketId: Optional[str] = None
    userId: Optional[str] = None
    attended: Optional[bool] = False
    def to_dict(self):
        return {
            "id":self.id,
            "transactionId": self.transactionId,
            # "merchantId": self.merchantId,
            "amount": self.amount,
            # "method": self.method,
            "payment_date": self.paymentDate,
            "members": self.members,
            "already_booked": self.already_booked,
            "status": self.status,
            "ticketId": self.ticketId,
            "userId": self.userId,
            "attended": self.attended
        }
    # class Config:
    #     allow_population_by_field_name = True  # Use field names during population
    #     case_insensitive = True  # Allow case-insensitive matching

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
        # Find the user first
        user_booking = next((user for user in self.booked_users if user.user_id == userId), None)
        
        if user_booking:
            # If the user is found, find the specific booking
            return next((booking for booking in user_booking.get_bookings() if booking.transactionId == transactionId), None)
        
        return None

    def add_attendee_information(self, attendee_info: AttendedInformation):
        # Check if the attendee already exists based on user_id
        existing_attendee = next((attendee for attendee in self.attended_users if attendee.user_id == attendee_info.user_id), None)
        
        if existing_attendee:
            # If attendee exists, update the information
            existing_attendee.transactionId = attendee_info.transactionId
            existing_attendee.ticketId = attendee_info.ticketId
            existing_attendee.members = attendee_info.members
        else:
            # If attendee does not exist, add to the list
            self.attended_users.append(attendee_info)

    def mark_attended_by_ticket_id(self, ticketId: str):
        for user in self.booked_users:
            booking = next((b for b in user.bookings if b.ticketId == ticketId), None)
            if booking:
                booking.attended = True
    
    def is_attended_by_ticket_id(self, ticketId: str) -> bool:
        for user in self.booked_users:
            booking = next((b for b in user.bookings if b.ticketId == ticketId), None)
            if booking:
                return booking.attended  # Return the status of the attended field
        return False  # Ticket ID not found, or attended is False
                

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