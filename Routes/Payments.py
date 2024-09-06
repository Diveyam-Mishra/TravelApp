from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Body
from fastapi.responses import FileResponse
from config import JWTBearer
from Schemas.EventSchemas import SuccessResponse
from Database.Connection import get_booking_container, get_container, get_db, \
    get_user_specific_container, get_successful_transaction_container
from Models.user_models import User
from Controllers.Auth import get_current_user
from Controllers.Payments import getUserBookingStatus, bookEventForUser, addAttendee, getBookedUsers, \
    getAttendedUsers, create_ticket_pdf, \
    send_email_with_attachment, send_ticket
from Schemas.PaymentSchemas import PaymentInformation, ticketData
from sqlalchemy.orm import Session
import os

router = APIRouter()

async def send_ticket_background(
    ticket_data: dict[str],
    ticketNo:int,
    userId:str,
    bookingContainer,
    eventContainer,
    db: Session
):  
    status_response = await getUserBookingStatus(ticket_data['eventId'], userId, bookingContainer, eventContainer)
    print(status_response)
    if not status_response.success: 
        return SuccessResponse(message="User has not booked the event", success=False) 

    status_response = status_response.dict()
    print("Yes")
    # Assuming 'data' is already a list within the dictionary
    data_list = status_response.get('data', [])
    # data_list = list(data_list)
    # print(data_list[ticketNo])
    booking_data = data_list[ticketNo]
    booking_data_dict = booking_data
    # print(status_response)
    newTicketData = ticketData(eventId=ticket_data['eventId'], userId=userId, paid_amount=booking_data_dict['data']['amount'], payment_id=booking_data_dict['transactionId'], members_details=booking_data_dict['members'])
    print("Yes")
    response = await send_ticket(newTicketData, eventContainer, db)
    # You might want to log the response or handle it in some way
    print(f"Ticket sent: {response}")

@router.get("/bookingStatus/{eventId}/", dependencies=[Depends(JWTBearer())], response_model=SuccessResponse)
async def checkUserBookingStatus(eventId: str, bookingContainer=Depends(get_booking_container),
eventContainer=Depends(get_container), current_user:User=Depends(get_current_user)):
    if current_user is None:
        raise HTTPException(status_code=401, detail="Unauthorized")

    return await getUserBookingStatus(eventId, current_user.id, bookingContainer, eventContainer)


@router.post("/bookEvent/{eventId}/", dependencies=[Depends(JWTBearer())], response_model=SuccessResponse)
async def newBooking(eventId: str, background_tasks: BackgroundTasks, merchantTransactionId: str=Body(...), members:int=Body(...), ticketNo: int = 0, bookingContainer=Depends(get_booking_container), eventContainer=Depends(get_container), current_user: User=Depends(get_current_user), userSpecificContainer=Depends(get_user_specific_container), transactionContainer=Depends(get_successful_transaction_container),db:Session=Depends(get_db)):

    if current_user is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    booking_response = await bookEventForUser(
        eventId, current_user.id, bookingContainer, eventContainer,
        merchantTransactionId, userSpecificContainer, transactionContainer, members
    )

    # if booking_response.success:
    #     newTicketData = {
    #     "eventId": eventId,
    #     "userId_O": current_user.id 
    # }
    #     # try:
    #     background_tasks.add_task(send_ticket_background, newTicketData, current_user.id,ticketNo,bookingContainer,eventContainer,db)
    # # except Exception as e:
    # #     pass

    
    # # if current_user.id != str(current_user.id):
    # #     raise HTTPException(status_code=401, detail="You are not authorized to book an event for another user")
    
    return booking_response


@router.put("/addAttendee/{eventId}/", dependencies=[Depends(JWTBearer())], response_model=SuccessResponse, tags=["Will not work"])
async def addAttendeeToEvent(eventId: str, bookingContainer=Depends(get_booking_container),
                              eventContainer=Depends(get_container), current_user: User=Depends(get_current_user)):
    if current_user is None:
        raise HTTPException(status_code=401, detail="Unauthorized")

    response = await addAttendee(eventId, current_user.id, bookingContainer, eventContainer)

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


@router.post("/tickets/send/{ticketNo}", response_model=SuccessResponse, dependencies=[Depends(JWTBearer())])
async def send_ticket_endpoint(req: ticketData, ticketNo:int=0, current_user=Depends(get_current_user), bookingContainer=Depends(get_booking_container), eventContainer=Depends(get_container), db:Session=Depends(get_db)):
    # ticket_data_dict = req.dict()
    if current_user is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    ticket_data_dict = req.dict()
    status_response = await getUserBookingStatus(ticket_data_dict['eventId'], current_user.id, bookingContainer, eventContainer)

    if not status_response.success: 
        return SuccessResponse(message="User has not booked the event", success=False) 

    status_response_dict = status_response.dict()

    # Assuming 'data' is already a list within the dictionary
    data_list = status_response_dict.get('data', [])
    # data_list = list(data_list)
    # print(data_list[ticketNo])
    booking_data = data_list[ticketNo]
    booking_data_dict = booking_data
    # print(status_response)
    newTicketData = ticketData(eventId=ticket_data_dict['eventId'], userId=current_user.id, paid_amount=booking_data_dict['data']['amount'], payment_id=booking_data_dict['transactionId'], members_details=booking_data_dict['members'])
    response = await send_ticket(newTicketData, eventContainer, db)
    return response


@router.post("/generate-ticket/{ticketNo}", dependencies=[Depends(JWTBearer())])
async def generate_ticket(ticket_data: ticketData, ticketNo:int=0, booking_container=Depends(get_booking_container), event_container=Depends(get_container), db:Session=Depends(get_db), current_user=Depends(get_current_user)):

    if current_user is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    pdf_path = "ticket.pdf"
    ticket_data_dict = ticket_data.dict()

    status_response = await getUserBookingStatus(ticket_data_dict['eventId'], current_user.id, booking_container, event_container)
    
    if not status_response.success: 
        return SuccessResponse(message="User has not booked the event", success=False) 
    status_response_dict = status_response.dict()

    # Assuming 'data' is already a list within the dictionary
    data_list = status_response_dict.get('data', [])
    # data_list = list(data_list)
    # print(data_list[ticketNo])
    booking_data = data_list[ticketNo]
    booking_data_dict = booking_data
    # print(status_response)
    newTicketData = ticketData(eventId=ticket_data_dict['eventId'], userId=current_user.id, paid_amount=booking_data_dict['data']['amount'], payment_id=booking_data_dict['transactionId'], members_details=booking_data_dict['members'])
    updated_data = await create_ticket_pdf(newTicketData, pdf_path, event_container, db)
    
    # Return the PDF file as a downloadable response
    return FileResponse(path=pdf_path, filename="ticket.pdf", media_type='application/pdf')
