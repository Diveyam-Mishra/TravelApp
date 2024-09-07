from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Body
from fastapi.responses import FileResponse
from config import JWTBearer
from Schemas.EventSchemas import SuccessResponse
from Database.Connection import get_booking_container, get_container, get_db, \
    get_user_specific_container, get_successful_transaction_container,get_file_container
from Models.user_models import User
from Controllers.Auth import get_current_user
from Controllers.Payments import getUserBookingStatus, bookEventForUser, addAttendee, getBookedUsers, \
    getAttendedUsers, create_ticket_pdf, \
    send_email_with_attachment, send_ticket,ticket_information
from Schemas.PaymentSchemas import PaymentInformation, ticketData
from sqlalchemy.orm import Session
import os

router = APIRouter()


@router.get("/bookingStatus/{eventId}/", dependencies=[Depends(JWTBearer())], response_model=SuccessResponse)
async def checkUserBookingStatus(eventId: str, bookingContainer=Depends(get_booking_container),
eventContainer=Depends(get_container), current_user:User=Depends(get_current_user)):
    if current_user is None:
        raise HTTPException(status_code=401, detail="Unauthorized")

    return await getUserBookingStatus(eventId, current_user.id, bookingContainer, eventContainer)


@router.post("/bookEvent/{eventId}/", dependencies=[Depends(JWTBearer())], response_model=SuccessResponse)
async def newBooking(eventId: str, merchantTransactionId: str=Body(...), members:int=Body(...), bookingContainer=Depends(get_booking_container), eventContainer=Depends(get_container), current_user: User=Depends(get_current_user), userSpecificContainer=Depends(get_user_specific_container), transactionContainer=Depends(get_successful_transaction_container)):

    if current_user is None:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # if current_user.id != str(current_user.id):
    #     raise HTTPException(status_code=401, detail="You are not authorized to book an event for another user")

    return await bookEventForUser(eventId, current_user.id, bookingContainer, eventContainer, merchantTransactionId, userSpecificContainer, transactionContainer, members)


@router.put("/addAttendee/{ticketId}/", dependencies=[Depends(JWTBearer())], response_model=SuccessResponse, tags=["Will not work"])
async def addAttendeeToEvent(ticketId: str, bookingContainer=Depends(get_booking_container),
                              eventContainer=Depends(get_container), fileContainer=Depends(get_file_container), current_user: User=Depends(get_current_user)):
    if current_user is None:
        raise HTTPException(status_code=401, detail="Unauthorized")

    response = await addAttendee(ticketId, current_user.id, bookingContainer, eventContainer, fileContainer)

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


@router.post("/tickets/send/{ticketId}", response_model=SuccessResponse, dependencies=[Depends(JWTBearer())])
async def send_ticket_endpoint(req: ticketData, ticketId:str, current_user=Depends(get_current_user), bookingContainer=Depends(get_booking_container), eventContainer=Depends(get_container), db:Session=Depends(get_db)):
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
    ind = 0
    for i, tickets in enumerate(data_list):
        if tickets['ticketId'] == ticketId:
            ind = i
    booking_data = data_list[ind]
    booking_data_dict = booking_data
    # #print(status_response)
    newTicketData = ticketData(eventId=ticket_data_dict['eventId'], userId_O=current_user.id, paid_amount_O=booking_data_dict['data']['amount'], payment_id_O=booking_data_dict['data']['transactionId'], members_details_O=str(booking_data_dict['members']))
    response = await send_ticket(newTicketData, eventContainer, db)
    return response


@router.post("/generate-ticket/{ticketId}", dependencies=[Depends(JWTBearer())])
async def generate_ticket(ticket_data: ticketData, ticketId:str, booking_container=Depends(get_booking_container), event_container=Depends(get_container), db:Session=Depends(get_db), current_user=Depends(get_current_user)):

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
    # #print(data_list)
    ind = 0
    for i, tickets in enumerate(data_list):
        if tickets['ticketId'] == ticketId:
            ind = i
    booking_data = data_list[ind]
    booking_data_dict = booking_data
    # #print(status_response)
    newTicketData = ticketData(eventId=ticket_data_dict['eventId'], userId_O=current_user.id, paid_amount_O=booking_data_dict['data']['amount'], payment_id_O=booking_data_dict['data']['transactionId'], members_details_O=str(booking_data_dict['members']))

    # #print(newTicketData)

    updated_data = await create_ticket_pdf(newTicketData, pdf_path, event_container, db)
    
    # Return the PDF file as a downloadable response
    return FileResponse(path=pdf_path, filename="ticket.pdf", media_type='application/pdf')

@router.get("/Ticket_Info/{ticketID}",dependencies=[Depends(JWTBearer())])
async def Ticket_Information(ticketId:str, booking_container=Depends(get_booking_container), event_container=Depends(get_container), file_Container=Depends(get_file_container), current_user=Depends(get_current_user)):
    if current_user is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    k=await ticket_information(ticketId,booking_container,event_container,file_Container)
    return k
    if k[0]['event_details']['creator_id']==current_user.id:
        return k
    else:
        return ("You are not the Creator of this Event. Information is only For the Creator ")