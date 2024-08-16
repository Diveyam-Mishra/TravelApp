from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from config import JWTBearer
from Schemas.EventSchemas import SuccessResponse
from Database.Connection import get_booking_container, get_container, get_db
from Models.user_models import User
from Controllers.Auth import get_current_user
from Controllers.Payments import getUserBookingStatus, bookEventForUser, addAttendee, getBookedUsers,\
    getAttendedUsers, create_ticket_pdf, send_ticket_email
from Schemas.PaymentSchemas import PaymentInformation, ticketData
from sqlalchemy.orm import Session

router = APIRouter()


@router.get("/bookingStatus/{eventId}+{userID}/", dependencies=[Depends(JWTBearer())], response_model=SuccessResponse)
async def checkUserBookingStatus(eventId: str, userID: int, bookingContainer=Depends(get_booking_container),
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



@router.post("/send-ticket/")
async def send_ticket(ticket_data: ticketData, background_tasks: BackgroundTasks):
    pdf_path = "ticket.pdf"
    create_ticket_pdf(ticket_data, pdf_path)
    background_tasks.add_task(send_ticket_email, ticket_data, pdf_path, ticket_data["email"])
    return {"message": "Ticket will be sent shortly."}