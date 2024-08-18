from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from config import JWTBearer
from Schemas.EventSchemas import SuccessResponse
from Database.Connection import get_booking_container, get_container, get_db
from Models.user_models import User
from Controllers.Auth import get_current_user
from Controllers.Payments import getUserBookingStatus, bookEventForUser, addAttendee, getBookedUsers, \
    getAttendedUsers, create_ticket_pdf, \
    send_email_with_attachment, send_ticket
from Schemas.PaymentSchemas import PaymentInformation, ticketData
from sqlalchemy.orm import Session
import os

router = APIRouter()


@router.get("/bookingStatus/{eventId}+{userID}/", dependencies=[Depends(JWTBearer())], response_model=SuccessResponse)
async def checkUserBookingStatus(eventId: str, userID: str, bookingContainer=Depends(get_booking_container),
eventContainer=Depends(get_container), current_user:User=Depends(get_current_user)):
    if current_user is None:
        raise HTTPException(status_code=401, detail="Unauthorized")

    return await getUserBookingStatus(eventId, userID, bookingContainer, eventContainer)


@router.post("/bookEvent/{eventId}+{userID}/", dependencies=[Depends(JWTBearer())], response_model=SuccessResponse)
async def newBooking(eventId: str, userID: str, bookingDetails: PaymentInformation, bookingContainer=Depends(get_booking_container), eventContainer=Depends(get_container), current_user: User=Depends(get_current_user)):

    if current_user is None:
        raise HTTPException(status_code=401, detail="Unauthorized")

    if userID != str(current_user.id):
        raise HTTPException(status_code=401, detail="You are not authorized to book an event for another user")

    return await bookEventForUser(eventId, userID, bookingContainer, eventContainer, bookingDetails)


@router.put("/addAttendee/{eventId}+{userId}/", dependencies=[Depends(JWTBearer())], response_model=SuccessResponse)
async def addAttendeeToEvent(eventId: str, userId: str, bookingContainer=Depends(get_booking_container),
                              eventContainer=Depends(get_container), current_user: User=Depends(get_current_user)):
    if current_user is None:
        raise HTTPException(status_code=401, detail="Unauthorized")

    response = await addAttendee(eventId, userId, bookingContainer, eventContainer)

    return response


@router.get("/getBookedUsers/{eventID}/", dependencies=[Depends(JWTBearer())])
async def getBookedUsersOfEvent(eventId: str, bookingContainer=Depends(get_booking_container), current_user=Depends(get_current_user), db: Session=Depends(get_db)):
    if current_user is None:
        raise HTTPException(status_code=401, detail="Unauthorized")

    response = await getBookedUsers(eventId, bookingContainer, current_user, db)

    return response


@router.get("/getAttendedUsers/{eventID}/", dependencies=[Depends(JWTBearer())])
async def getAttendedUsersOfEvent(eventId: str, bookingContainer=Depends(get_booking_container), current_user=Depends(get_current_user), db: Session=Depends(get_db)):
    if current_user is None:
        raise HTTPException(status_code=401, detail="Unauthorized")

    response = await getAttendedUsers(eventId, bookingContainer, current_user, db)

    return response


@router.post("/tickets/send/", response_model=SuccessResponse, dependencies=[Depends(JWTBearer())])
async def send_ticket_endpoint(req: ticketData, current_user=Depends(get_current_user), bookingContainer=Depends(get_booking_container), eventContainer=Depends(get_container)):
    # ticket_data_dict = req.dict()
    if current_user is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    ticket_data_dict = req.dict()
    status_response = await getUserBookingStatus(ticket_data_dict['eventId'], ticket_data_dict['userId'], bookingContainer, eventContainer)

    if not status_response.success:  
        return SuccessResponse(message="User has not booked the event", success=False) 
    response = await send_ticket(req.email, req)
    return response


@router.post("/generate-ticket/", dependencies=[Depends(JWTBearer())])
async def generate_ticket(ticket_data: ticketData, booking_container=Depends(get_booking_container), event_container=Depends(get_container)):
    pdf_path = "ticket.pdf"
    ticket_data_dict = ticket_data.dict()
    status_response = await getUserBookingStatus(ticket_data_dict['eventId'], ticket_data_dict['userId'], booking_container, event_container)

    # print(status_response)

    if not status_response.success:  
        return SuccessResponse(message="User has not booked the event", success=False) 
    await create_ticket_pdf(ticket_data, pdf_path)
    
    # Return the PDF file as a downloadable response
    return FileResponse(path=pdf_path, filename="ticket.pdf", media_type='application/pdf')
