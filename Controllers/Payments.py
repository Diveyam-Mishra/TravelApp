from Controllers.Events import get_event_by_id
from fastapi import HTTPException
from Schemas.PaymentSchemas import PaymentInformation, PaymentLists, \
    AttendedInformation, ticketData, UserBookings
from azure.cosmos import exceptions
from Schemas.EventSchemas import SuccessResponse
from Schemas.userSpecific import EventData, UserSpecific
from uuid import uuid4
from datetime import datetime
from Models.user_models import User
from Models.Files import Avatar
from email.message import EmailMessage
from pathlib import Path
from azure.communication.email import EmailClient
import pdfkit  # type: ignore
from tempfile import NamedTemporaryFile
import jinja2
from config import settings, connectionString
import os
from sqlalchemy.orm import joinedload
from Helpers.QRCode import generate_qr_code
from typing import Dict, Optional
from azure.core.exceptions import HttpResponseError
import base64
import hashlib
from Helpers.calculateAge import calculate_age

def generate_merchant_transaction_id(user_id: str, id_no: int) -> str:
    # Create a unique base string from user_id and id_no
    base_string = f"{user_id}_{id_no}"
    
    # Generate a hash of the base string
    unique_hash = hashlib.sha256(base_string.encode()).hexdigest()[:12]  # 12 characters for example
    
    return unique_hash

async def getUserBookingStatus(eventId: str, userId: str, bookingContainer, eventContainer):
    event_query = "SELECT * FROM c WHERE c.id = @eventId"
    params = [{"name": "@eventId", "value": eventId}]
    
    # Query the event container for the event with the specified event_id
    events = list(eventContainer.query_items(
        query=event_query,
        parameters=params,
        enable_cross_partition_query=True
    ))
    
    if not events:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Query the booking container for the event with the specified event_id
    booking_event_query = "SELECT * FROM c WHERE c.id = @eventId"
    params = [{"name": "@eventId", "value": eventId}]

    bookingLists = list(bookingContainer.query_items(
        query=booking_event_query,
        parameters=params,
        enable_cross_partition_query=True
    ))

    if not bookingLists:
        # Create a booking object with id field
        booking_lists = PaymentLists(
            id=eventId,  # Using eventId as the id field
            event_id=eventId,
            booked_users=[],  # Empty list
            attended_users=[]  # Empty list
        )
        # Store the booking_lists object in the container
        bookingContainer.create_item(booking_lists.to_dict())
        # Return that the user has not booked the event yet
        return SuccessResponse(message="User has not booked the event", success=False)
    
    booking_lists_data = bookingLists[0]  # Raw data from Cosmos DB

    # Convert the raw data to PaymentLists model
    try:
        # Convert raw data to PaymentLists model
        booking_lists = PaymentLists(**booking_lists_data)

        # Convert booked_users to a list of UserBookings models
        booked_users = []
        for user_booking_data in booking_lists.booked_users:
            # Convert user_booking_data to UserBookings instance
            user_bookings = UserBookings(**user_booking_data.to_dict())

            # #print(user_bookings)

            # Convert each booking in user_bookings to PaymentInformation instance
            try:
                payment_info_list = [PaymentInformation(**booking.to_dict()) for booking in user_bookings.bookings]
                user_bookings.bookings = payment_info_list
            except TypeError as e:
                raise HTTPException(status_code=500, detail=f"Error parsing bookings for user {user_bookings.user_id}: {str(e)}")

            booked_users.append(user_bookings)

        booking_lists.booked_users = booked_users

    except TypeError as e:
        raise HTTPException(status_code=500, detail=f"Error parsing booking lists: {str(e)}")

    # Debug: #print out booked_users for inspection
    # #print(f"Booked Users: {booked_users}")
    # #print(f"User ID to Check: {userId}")

    # Check if the userId exists in the booked_users list
    user_booking = next((user for user in booked_users if user.user_id == str(userId)), None)
    # #print(user_booking.bookings.to_dict())
    if not user_booking:
        return SuccessResponse(message="User has not booked the event", success=False)
    else:
        # Extract booking details
        # booking_details = {
        #     "booking_id": user_booking.booking_id,
        #     "event_id": user_booking.event_id,
        #     "user_id": user_booking.user_id,
        #     "booking_date": user_booking.booking_date,
        #     # Add other relevant details
        # }
        return SuccessResponse(
            message="User has booked the event",
            success=True,
            data=user_booking.bookings
        )


async def addBookingDataInUserSpecific(
    userId: str,
    eventId: str,
    eventContainer,
    paymentDetails: PaymentInformation,
    userSpecificContainer
):
    event_query = "SELECT * from c WHERE c.id = @eventId"
    params = [{"name": "@eventId", "value": eventId}]
    event = list(eventContainer.query_items(query=event_query, parameters=params, enable_cross_partition_query=True))
    if not event:
        return SuccessResponse(message="Event does not exist", success=False)
    
    query = "SELECT * FROM c where c.userId = @userId"
    params = [{"name": "@userId", "value": userId}]
    search = list(userSpecificContainer.query_items(query=query, parameters=params, enable_cross_partition_query=True))

    if not search:
        user_specific = UserSpecific(id=userId, userId=userId, booked_events=[], recent_searches=[], interest_areas=[])
    else:
        user_specific = UserSpecific(**search[0])

    event_time = event[0]['start_date_and_time']  # Assuming you want to use the first event found
    # #print(paymentDetails)

    newUserBookingData = EventData(
        event_id=eventId,
        payment_id=paymentDetails.transactionId,
        paid_amount=paymentDetails.data['amount'],
        payment_date=paymentDetails.paymentDate,
        event_date=event_time,
        ticket_id=paymentDetails.ticketId
    )

    user_specific.booked_events.append(newUserBookingData)

    # Convert user_specific back to dictionary format for storage
    user_specific_data = user_specific.to_dict()

    # Store the updated user-specific data in the container
    userSpecificContainer.upsert_item(user_specific_data)

    return SuccessResponse(message="Booking data added", success=True)


def generate_unique_ticket_id(user_id: str, event_id: str, merchantTransactionNo: str) -> str:
    # Create a combined string of user_id and event_id
    combined_string = f"{user_id}_{event_id}_{merchantTransactionNo}"
    
    # Generate a SHA-256 hash of the combined string
    hash_object = hashlib.sha256(combined_string.encode())
    hash_hex = hash_object.hexdigest()
    
    # Shorten the hash to a desired length for the ticket ID
    ticket_id = hash_hex[:16]  # For example, take the first 16 characters
    
    return ticket_id


async def bookEventForUser(
    eventId: str,
    userId: str,
    bookingContainer,
    eventContainer,
    id_no: int,
    userSpecificContainer,
    transactionContainer,
    members: int
):
    try:
        # Check if the event exists
        event_query = "SELECT * FROM c WHERE c.id = @eventId"
        params = [{"name": "@eventId", "value": eventId}]
        eventList = list(eventContainer.query_items(query=event_query, parameters=params, enable_cross_partition_query=True))

        if not eventList:
            return SuccessResponse(message="Event does not exist", success=False)
        
        event = eventList[0]
        
        if 'capacity' not in event or event['capacity'] < members:
            return SuccessResponse(message="Not enough capacity available for this event", success=False)
        
        # Check if the transaction exists
        transactionId = generate_merchant_transaction_id(userId, id_no)
        transaction_query = "SELECT * FROM c WHERE c.transactionId = @transactionId"
        params = [{"name": "@transactionId", "value": transactionId}]
        transactionsList = list(transactionContainer.query_items(query=transaction_query, parameters=params, enable_cross_partition_query=True))

        if not transactionsList:
            return SuccessResponse(message="Transaction does not exist", success=False)
        
        transaction = PaymentInformation(**transactionsList[0])
        transaction_dict = transaction.to_dict()

        if transaction_dict.get('added_in_event_booking', False):
            return SuccessResponse(message="User has already booked the event", success=False)

        # Check booking list for the event
        booking_event_query = "SELECT * FROM c WHERE c.id = @eventId"
        params = [{"name": "@eventId", "value": eventId}]

        bookingLists = list(bookingContainer.query_items(query=booking_event_query, parameters=params, enable_cross_partition_query=True))

        if not bookingLists:
            booking_list_item = PaymentLists(
                id=eventId,
                event_id=eventId,
                booked_users=[],
                attended_users=[]
            )
            # Store the booking_lists object in the container
            bookingContainer.create_item(booking_list_item.to_dict())
        else:
            booking_list_item = PaymentLists(**bookingLists[0])

        # Update booking list
        booking_list_item.add_new_user(userId)
        transaction_dict['members'] = members
        transaction_dict['added_in_event_booking'] = True

        transaction_dict['ticketId'] = generate_unique_ticket_id(userId, eventId, transactionId)
        transaction_dict['userId'] = userId
        ticketId = transaction_dict['ticketId']
        # Replace transaction item
        transactionContainer.replace_item(item=transaction_dict['id'], body=transaction_dict)

        # Clean up transaction data
        del transaction_dict["data"]["merchantId"]
        del transaction_dict["data"]["merchantTransactionId"]

        # #print("ok")
        # Update booking list with user details
        booking_list_item.add_booking_by_user_id(userId, PaymentInformation(**transaction_dict))

        transacationUpd = PaymentInformation(**transaction_dict)

        # #print('ok2')
        # #print(booking_list_item.id)
        bookingContainer.replace_item(item=booking_list_item.id, body=booking_list_item.to_dict())
        event['capacity'] -= members 
        eventContainer.replace_item(item=event['id'], body=event)
        
        # Add booking data in user-specific container
        await addBookingDataInUserSpecific(userId, eventId, eventContainer, transacationUpd, userSpecificContainer)
        # #print('ok4')
        return SuccessResponse(message="User booked the event", success=True, ticketId=ticketId)
    
    except Exception as e:
        # Log the exception (you can use logging or any other method)
        # print(f"An error occurred: {str(e)}")

        # Return a generic error response
        return SuccessResponse(message=f"An error occurred while booking the event, {e}", success=False)

async def saveTransactionInitInDB(userId, finalMerchantId, paymentInitContainer):
    try:
        date = datetime.now()
        newId = str(uuid4())

        newPaymentInit = {
            "id": newId,
            "userId": userId,
            "merchantId": finalMerchantId,
            "initiated_at": date.isoformat()
        }
        paymentInitContainer.create_item(newPaymentInit)
        return SuccessResponse(message="Transaction initiation data added successfully", success=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{e}")

async def updateTransactionInitInDB(merchantId, paymentInitContainer, status):
    try:
        # Query to find the transaction by merchantId
        paymentInitQuery = "SELECT * FROM c WHERE c.merchantId = @merchantId"
        params = [{"name": "@merchantId", "value": merchantId}]

        # Fetch the matching transaction(s)
        paymentLists = list(paymentInitContainer.query_items(
            query=paymentInitQuery,
            parameters=params,
            enable_cross_partition_query=True
        ))

        # If no records are found, raise an exception or handle accordingly
        if not paymentLists:
            raise Exception(f"No transaction found for merchantId: {merchantId}")

        # Update the first matched record (assuming only one record for merchantId)
        for payment in paymentLists:
            payment_id = payment.get("id")  # Retrieve the document ID
            partition_key = payment.get("merchantId")  # Assuming merchantId is the partition key

            # Update fields
            payment["status"] = status
            payment["updated_at"] = int(time.time())  # Current time in UNIX format
            # payment["created_at"] = created_at  # Preserving original created_at

            # Replace the updated document in the database
            paymentInitContainer.replace_item(
                item=payment_id,
                body=payment,
                partition_key=partition_key
            )

        print(f"Transaction for merchantId: {merchantId} updated successfully.")
        return {"status": "success", "message": "Transaction updated successfully."}

    except Exception as e:
        print(f"Error updating transaction: {e}")
        return {"status": "error", "message": str(e)}



from sqlalchemy import select

async def addAttendee(ticketId: str, userId: str, bookingContainer, eventContainer, fileContainer, db):
    # Check if the user has booked the event
    booking_records = await ticket_information(ticketId, bookingContainer, eventContainer, fileContainer)

    if not booking_records:
        return SuccessResponse(message="User has not booked the event", success=False)

    booking_record = booking_records[0]
    creator = booking_record['event_details']['creator_id']
    eventId = booking_record['event_details']['id']
    transactionId = booking_record['Transaction']['booking']['transactionId']
    members = str(booking_record['Transaction']['booking']['members'])
    user_id = booking_record['Transaction']['booking']['userId']

    # Asynchronous SQLAlchemy query for User
    query = select(User).filter(User.id == user_id)
    result = await db.execute(query)
    k = result.scalars().first()
    
    if not k:
        raise HTTPException(status_code=404, detail="User not found")
    
    username = k.username
    start_date_and_time = booking_record['event_details']['start_date_and_time']
    end_date_and_time = booking_record['event_details']['end_date_and_time']
    event_name = booking_record['event_details']['event_name']
    location = booking_record['event_details']['location']

    if creator != userId:
        raise HTTPException(status_code=401, detail="You are not the creator of the booked event")

    # Asynchronous query for booking event
    booking_event_query = "SELECT * FROM c WHERE c.id = @eventId"
    params = [{"name": "@eventId", "value": eventId}]

    bookingLists = list(bookingContainer.query_items(query=booking_event_query, parameters=params, enable_cross_partition_query=True))

    if not bookingLists:
        return SuccessResponse(message="Event Booking record not found", success=False)

    booking_list_item = PaymentLists(**bookingLists[0])

    attendedStatus = booking_list_item.is_attended_by_ticket_id(ticketId)

    if attendedStatus:
        return SuccessResponse(message="User has already attended the event", success=False)

    newAttendeeInfo = AttendedInformation(user_id=userId, transactionId=transactionId, ticketId=ticketId, members=members)

    booking_list_item.add_attendee_information(newAttendeeInfo)
    booking_list_item.mark_attended_by_ticket_id(ticketId)
    
    # Replace item asynchronously
    bookingContainer.replace_item(item=booking_list_item.id, body=booking_list_item.to_dict())

    return SuccessResponse(
        message="User successfully added to attended users",
        event_name=event_name,
        username=username,
        location=location,
        start_date_and_time=start_date_and_time,
        end_date_and_time=end_date_and_time,
        members=members,
        success=True
    )


async def getBookedUsers(eventId: str, bookingContainer, current_user, db):
    if current_user is None:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Fetch the booking details
    booking_event_query = "SELECT * FROM c WHERE c.event_id = @eventId"
    params = [{"name": "@eventId", "value": eventId}]

    bookingLists = list(bookingContainer.query_items(
        query=booking_event_query,
        parameters=params,
        enable_cross_partition_query=True
    ))

    if not bookingLists:
        raise HTTPException(status_code=404, detail="Booking record not found")

    booking_lists = bookingLists[0]

    # Convert booked_users to PaymentInformation models
    booked_users = booking_lists.get("booked_users", [])
    user_ids = [user["user_id"] for user in booked_users]

    # Query the User model to get usernames
    results = (
    db.query(User, Avatar.fileurl)
    .outerjoin(Avatar, User.id == Avatar.userID)  # Join condition
    .filter(User.id.in_(user_ids))  # Filter users based on user_ids list
    .all())
    # Return a list of usernames
    return {
        "users": [
            {
                "username": user.username,
                "gender": user.gender,
                "age": calculate_age(user.dob) ,  # Convert date to ISO format if not None
                "Avatar": avatar_url  # Corrected to fetch the avatar URL
            }
            for user, avatar_url in results  # Destructure the tuple to access user and avatar_url
        ]
    }


async def getAttendedUsers(eventId: str, bookingContainer, current_user, db):
    if current_user is None:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Fetch the booking details
    booking_event_query = "SELECT * FROM c WHERE c.event_id = @eventId"
    params = [{"name": "@eventId", "value": eventId}]

    bookingLists = list(bookingContainer.query_items(
        query=booking_event_query,
        parameters=params,
        enable_cross_partition_query=True
    ))

    if not bookingLists:
        raise HTTPException(status_code=404, detail="Booking record not found")

    booking_lists = bookingLists[0]

    # Extract attended_users from the booking record
    attended_users = booking_lists.get("attended_users", [])
    user_ids = [user["user_id"] for user in attended_users]

    # Query the User model to get usernames
    if user_ids:
        usernames = db.query(User.username).filter(User.id.in_(user_ids)).all()
    else:
        usernames = []

    # Return a list of usernames
    return {"usernames": [username for (username,) in usernames]}


TEMPLATE_DIR = Path(__file__).parent / "../Templates/Ticket"
options = {
    "enable-local-file-access": "",  # This flag should be passed without a value
    "margin-left": "0mm",  # Use hyphen and specify units
    "margin-right": "0mm",  # Use hyphen and specify units
    "margin-top":"0mm",
    "margin-bottom":"0mm",
    "page-height":"290mm",
    "page-width":"215mm",
    "dpi":"300"
}


def generate_ticket_id(user_id: str, event_id: str) -> str:
    # Create a combined string of user_id and event_id
    combined_string = f"{user_id}_{event_id}"
    
    # Generate a SHA-256 hash of the combined string
    hash_object = hashlib.sha256(combined_string.encode())
    hash_hex = hash_object.hexdigest()
    
    # Shorten the hash to a desired length for the ticket ID
    ticket_id = hash_hex[:16]  # For example, take the first 16 characters
    
    return ticket_id


async def create_ticket_pdf(ticket_data: ticketData, output_path: str, eventContainer, db, ticketId: str):
    ticket_data_dict = ticket_data.dict()
    # print(ticket_data_dict)
   
    # Ensure ticket_data is an instance of ticketData and convert it to a dictionary
    if not isinstance(ticket_data, ticketData):
        raise TypeError("ticket_data must be an instance of ticketData")
    
    # Convert ticket_data to a dictionary
    
    # Prepare QR code data
    qr_data = {
        "id": "trabii.com",
        "ticket_id": ticketId
       }
    
    event_query = """
    SELECT * FROM eventcontainer e WHERE e.id = @id
    """
    params = [{"name": "@id", "value": ticket_data_dict['eventId']}]
    items = list(eventContainer.query_items(query=event_query, parameters=params, enable_cross_partition_query=True))
    
    existing_event = items[0]
    ticket_data_dict['event_name_O'] = existing_event['event_name']

    iso_string = existing_event['start_date_and_time']
    event_datetime = datetime.fromisoformat(iso_string.replace('Z', '+00:00'))
    date_format = '%Y-%m-%d'  # Format: '2024-08-20'
    time_format = '%H:%M:%S'  # Format: '15:03:19'
    ticket_data_dict['event_date_O'] = str(event_datetime.strftime(date_format))
    ticket_data_dict['event_time_O'] = str(event_datetime.strftime(time_format))
    ticket_data_dict['event_venue_O'] = existing_event['location']['venue']

    ticket_data_dict['ticketId_O'] = ticketId

    ticket_data_dict['organizer_O'] = existing_event['host_information']

    user = db.query(User).filter(User.id == ticket_data_dict['userId_O']).first()
    if user is None:
        raise HTTPException(status_code=400, detail="User Not found")
    
    ticket_data_dict['email_O'] = user.email
    ticket_data_dict['UserName_O'] = user.username

    updated_ticket_data = ticketData(**ticket_data_dict)

    # Generate the QR code
    qr_code_path = str(Path(TEMPLATE_DIR) / "qr_code.png")
    generate_qr_code(qr_data, qr_code_path)

    # Set up the Jinja2 environment with the TEMPLATE_DIR
    template_loader = jinja2.FileSystemLoader(searchpath=str(TEMPLATE_DIR))
    template_env = jinja2.Environment(loader=template_loader)
    
    # Load and render the HTML template with the context
    template = template_env.get_template("form.html")  # Ensure this template file exists
    context = {
        'media_folder': str(TEMPLATE_DIR),
        'qr_code_path': qr_code_path,
        **ticket_data_dict
    }
    html_content = template.render(context)
    
    # Save the rendered HTML content to a temporary file
    temp_html_path = str(Path(TEMPLATE_DIR) / "temp_ticket.html")
    with open(temp_html_path, 'w') as f:
        f.write(html_content)
    
    # Convert the saved HTML file to a PDF
    pdfkit.from_file(temp_html_path, output_path, options=options)
    
    # Optionally, remove the temporary files after creating the PDF
    os.remove(temp_html_path)
    os.remove(qr_code_path)

    return updated_ticket_data


sender_email = settings.sender_email
email_client = EmailClient.from_connection_string(connectionString)


async def send_ticket(ticket_data: Dict[str, str], eventContainer, db, ticketId: str) -> SuccessResponse:

    # Generate the PDF
    with NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
        pdf_path = temp_file.name
        updated_ticket_data = await create_ticket_pdf(ticket_data, pdf_path, eventContainer, db, ticketId)

    ticket_data_dict = updated_ticket_data.dict()
    # Send the email with the PDF attachment
    # #print(ticket_data_dict)
    try:
        send_email_with_attachment(ticket_data_dict['email_O'], pdf_path)

        # Clean up: Remove the temporary file
        os.remove(pdf_path)

        return SuccessResponse(message="Ticket sent to your registered email id", success=True)

    except Exception as e:
        # print(f"Error sending email: {e}")
        os.remove(pdf_path)
        return SuccessResponse(message="Some error occured", success=False)


def send_email_with_attachment(email: str, attachment_path: str):
    subject = "Your Ticket Confirmation"

    # Read and encode the PDF attachment in Base64
    with open(attachment_path, "rb") as file:
        file_content = file.read()
        base64_content = base64.b64encode(file_content).decode('utf-8')

    # Set the file name as 'ticket.pdf'
    file_name = "ticket.pdf"

    # Define the email message
    try:
        message = {
            "senderAddress": sender_email,
            "recipients": {
                "to": [{"address": email}],
            },
            "content": {
                "subject": subject,
                "plainText": "Please find your ticket attached.",
            },
            "attachments": [
                {
                    "name": file_name,
                    "attachmentType": "pdf",  # Use "pdf" instead of "application/pdf"
                    "contentType": "application/pdf",  # Correct contentType
                    "contentInBase64": base64_content
                }
            ]
        }

        # Send the email
        poller = email_client.begin_send(message)
        result = poller.result()
        return result
    
    except HttpResponseError as e:
        # Handle the error by logging or raising an HTTP exception
        raise HTTPException(status_code=500, detail=f"Failed to send email: {e.message}")


# async def ticket_information(ticketId: str, eventBooking,event_container,file_container):
#     query = """
#     SELECT 
#         c.event_id,
#         booked_user.bookings
#     FROM 
#         c 
#     JOIN 
#         booked_user IN c.booked_users
#     WHERE 
#         ARRAY_CONTAINS(booked_user.bookings, {"ticketId": @ticketId}, true)
#     """
#     parameters = [
#         {"name": "@ticketId", "value": ticketId}
#     ]
#     try:
#         items = list(eventBooking.query_items(
#             query=query,
#             parameters=parameters,
#             enable_cross_partition_query=True 
#         ))
#         print(items)
#         results=[]
#         for x in range(len(items)):
#             try:
#                 TicketInfo=items[x]
#                 eventId=TicketInfo['event_id']
#                 event_result=await get_event_by_id(eventId,event_container,file_container,0.0,0.0)
#                 print(event_result)
#                 results.append({TicketInfo:event_result})
#             except Exception as e:
#                 print(1)
#                 pass
#         print(results)
#         return results
#     except exceptions.CosmosHttpResponseError as e:
#         return (f"Wait while we update the Ticket {str(e)}")
async def ticket_information(ticketId: str, eventBooking, event_container, file_container):
    query = """
    SELECT 
        c.event_id,
        booked_user.bookings
    FROM 
        c 
    JOIN 
        booked_user IN c.booked_users
    WHERE 
        ARRAY_CONTAINS(booked_user.bookings, {"ticketId": @ticketId}, true)
    """
    parameters = [
        {"name": "@ticketId", "value": ticketId}
    ]
    
    try:
        # Execute the query to find bookings that contain the specified ticketId
        items = list(eventBooking.query_items(
            query=query,
            parameters=parameters,
            enable_cross_partition_query=True 
        ))
        results = []
        for item in items:
            event_id = item['event_id']
            # Filter bookings to find the one with the specified ticketId
            matching_booking = next(
                (booking for booking in item['bookings'] if booking['ticketId'] == ticketId),
                None
            )
            if matching_booking:
                try:
                    event_result = await get_event_by_id(event_id, event_container, file_container, 0.0, 0.0)
                    # Remove unnecessary fields from event result
                    event_result1 = {key: value for key, value in event_result.items() if key not in ['_rid', '_self', '_etag', '_attachments', '_ts', 'distance', 'images']}
                    # Create ticket information dictionary
                    ticket_info = {
                        'ticket_id': ticketId,
                        'Transaction': {
                            'event_id': event_id,
                            'booking': matching_booking  # Only the matched booking
                        },
                        'event_details': event_result1
                    }
                    results.append(ticket_info)
                except Exception as e:
                    continue
        
        return results

    except exceptions.CosmosHttpResponseError as e:
        return (f"Wait while we update the Ticket {str(e)}")


import httpx

async def create_razorpay_order(
    userID: str, amount: float, eventId: str, randomNumber: int, paymentInitContainer
):
    key_id ="rzp_test_gQ9s0JYn7a2X5S" #"rzp_live_cYB32Z66jVvWm8"
    key_secret ="feJN6nSvJ5DPalsdh7sWcoiD" #"T7wyhhGzVKHeZzlrf6K9AJb3"

    # Prepare the API URL and headers
    url = "https://api.razorpay.com/v1/orders"
    headers = {
        "content-type": "application/json"
    }

    # Prepare the payload
    print(userID)
    payload = {
        "amount": int(amount * 100),  # Convert amount to paise (smallest currency unit)
        "currency": "INR",
        "receipt": f"receipt#{randomNumber}",  # Unique receipt using userID
        "notes": {
            "event": eventId,
            "user": userID
        },
    }

    try:
        # Perform the API call
        async with httpx.AsyncClient(auth=(key_id, key_secret)) as client:
            response = await client.post(url, json=payload, headers=headers)

        # Handle the response
        if response.status_code in {200, 201}:
            res_json = response.json()

            # Save the transaction to the database
            await saveTransactionInitInDB(
                userId=userID, finalMerchantId=res_json.get("id"), paymentInitContainer=paymentInitContainer
            )

            return res_json
        else:
            raise Exception(f"Razorpay API Error: {response.status_code} - {response.text}")

    except httpx.RequestError as e:
        # Handle network-related errors
        raise Exception(f"Network error occurred: {e}")
    except Exception as e:
        # Handle other errors
        raise Exception(f"An error occurred: {e}")

