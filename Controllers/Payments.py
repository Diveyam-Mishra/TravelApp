from Controllers.Events import get_event_by_id
from fastapi import HTTPException
from Schemas.PaymentSchemas import PaymentInformation, PaymentLists, \
    AttendedInformation, ticketData
from Schemas.EventSchemas import SuccessResponse
from uuid import uuid4
from datetime import datetime
from Models.user_models import User
from email.message import EmailMessage
from pathlib import Path
from azure.communication.email import EmailClient
import pdfkit
from tempfile import NamedTemporaryFile
import jinja2
from config import settings, connectionString
import os
from Helpers.QRCode import generate_qr_code
from typing import Dict
from azure.core.exceptions import HttpResponseError
import base64

async def getUserBookingStatus(eventId: str, userId: str, bookingContainer, eventContainer):
    event_query = "SELECT * FROM c WHERE c.event_id = @eventId"
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
    booking_event_query = "SELECT * FROM c WHERE c.event_id = @eventId"
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
    
    booking_lists = bookingLists[0]

    # Convert the booking_lists to PaymentLists model
    try:
        booked_users = [PaymentInformation(**user) for user in booking_lists.get("booked_users", [])]
    except TypeError as e:
        raise HTTPException(status_code=500, detail=f"Error parsing booked users: {str(e)}")

    # Debug: Print out booked_users for inspection
    # print(f"Booked Users: {booked_users}")
    # print(f"User ID to Check: {userId}")

    # Check if the userId exists in the booked_users list
    user_booked = any(user.user_id == str(userId) for user in booked_users)

    if not user_booked:
        return SuccessResponse(message="User has not booked the event", success=False)
    else:
        return SuccessResponse(message="User has booked the event", success=True)


async def bookEventForUser(eventId: str, userId: str, bookingContainer, eventContainer, bookingDetails: PaymentInformation):
    # Check if the user has already booked the event
    status_response = await getUserBookingStatus(eventId, userId, bookingContainer, eventContainer)
    
    if status_response.success:
        return SuccessResponse(message="User has already booked the event", success=False)
    
    # Query the booking container for the event
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

    # Convert bookingDetails to dictionary
    payment_info_dict = bookingDetails.to_dict()
    
    # Add new payment information to the booked_users list
    booked_users = booking_lists.get("booked_users", [])
    booked_users.append(payment_info_dict)
    
    # Update the booking list with the new booked_users
    booking_lists["booked_users"] = booked_users
    
    # Replace the existing item in the database with the updated one
    bookingContainer.replace_item(item=booking_lists['id'], body=booking_lists)

    return SuccessResponse(message="User successfully booked the event", success=True)


async def addAttendee(eventId: str, userId: str, bookingContainer, eventContainer):
    # Check if the user has booked the event
    status_response = await getUserBookingStatus(eventId, userId, bookingContainer, eventContainer)
    
    if not status_response.success:
        # User has not booked the event, cannot add to attended_users
        return SuccessResponse(message="User has not booked the event", success=False)

    # Fetch the current booking details
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

    # Create a new AttendedInformation instance
    attended_info = AttendedInformation(
        user_id=userId,
        attended_at=datetime.utcnow()  # Set to current UTC time
    )

    # Add the new AttendedInformation to the attended_users list
    attended_users = [AttendedInformation(**user) for user in booking_lists.get("attended_users", [])]
    
    if any(user.user_id == userId for user in attended_users):
        # User is already in the attended_users list, throw an error
        raise HTTPException(status_code=400, detail="User is already in the attended users list")

    attended_users.append(attended_info)
    
    # Update the booking list with the new attended_users
    booking_lists["attended_users"] = [user.to_dict() for user in attended_users]

    # Replace the existing item in the database with the updated one
    bookingContainer.replace_item(item=booking_lists['id'], body=booking_lists)

    return SuccessResponse(message="User successfully added to attended users", success=True)


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
    usernames = db.query(User.username).filter(User.id.in_(user_ids)).all()

    # Return a list of usernames
    return {"usernames": [username for (username,) in usernames]}


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
    "enable-local-file-access": True,
}

async def create_ticket_pdf(ticket_data: ticketData, output_path: str):
    ticket_data_dict = ticket_data.dict()
   
    # Ensure ticket_data is an instance of ticketData and convert it to a dictionary
    if not isinstance(ticket_data, ticketData):
        raise TypeError("ticket_data must be an instance of ticketData")
    
    # Convert ticket_data to a dictionary

    # Prepare QR code data
    qr_data = {
        "qr": "eventBooking",
        "event_id": ticket_data_dict['eventId'],  # Use relevant data for event_id
        "user_id": ticket_data_dict['userId']  # Use relevant data for user_id if available
    }
    
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

sender_email = settings.sender_email
email_client = EmailClient.from_connection_string(connectionString)

async def send_ticket(email: str, ticket_data: Dict[str, str]) -> SuccessResponse:
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")

    # Generate the PDF
    with NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
        pdf_path = temp_file.name
        await create_ticket_pdf(ticket_data, pdf_path)

    # Send the email with the PDF attachment
    send_email_with_attachment(email, pdf_path)

    # Clean up: Remove the temporary file
    os.remove(pdf_path)

    return SuccessResponse(message="Ticket sent to your email", success=True)

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