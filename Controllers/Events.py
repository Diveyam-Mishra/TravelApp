from sqlalchemy.orm import Session
from Schemas.EventSchemas import EventDetails,EventDetailsupdate
from Schemas.UserSchemas import SuccessResponse
from Controllers.Auth import pwd_context, JWT_SECRET
import jwt
from Models.event_models import Event
from Controllers.Auth import get_current_user
from Models.user_models import User
from fastapi import HTTPException, Depends
from Database.Connection import get_container
import uuid

async def create_event(event_details: EventDetails, container=Depends(get_container), current_user: User = Depends(get_current_user)) -> SuccessResponse:
    if current_user is None:
        raise HTTPException(status_code=400, detail="User Not Found")

    # Prepare the query to check if the event already exists
    query = """
    SELECT * FROM eventcontainer e WHERE e.name = @name AND e.host_id = @host_id AND e.type = @type AND e.start_date = @start_date AND e.end_date = @end_date
    """
    
    params = [
        {"name": "@name", "value": event_details.event_name},
        {"name": "@host_id", "value": event_details.host_information.id},
        {"name": "@type", "value": ','.join(event_details.event_type)},
        {"name": "@start_date", "value": event_details.date_and_time},
        {"name": "@end_date", "value": event_details.date_and_time}
    ]
    
    items = list(container.query_items(query=query, parameters=params, enable_cross_partition_query=True))

    if items:
        raise HTTPException(status_code=400, detail="Event already created")

    # Create a new event
    new_event = event_details.dict()
    new_event.update({
        "id": str(uuid.uuid4()),
        "type": ','.join(event_details.event_type),  # Convert list to comma-separated string
        "start_date": event_details.date_and_time,
        "end_date": event_details.date_and_time,
        "media_files": ','.join(event_details.media_files),  # Convert list to comma-separated string
        "remaining_capacity": event_details.capacity,
        "creator_id": current_user.id  # Use the current user's ID
    })

    container.create_item(new_event)
    return SuccessResponse(message="Event Created Successfully", success=True)


async def update_event(event_details: EventDetailsupdate, container=Depends(get_container), current_user: User = Depends(get_current_user)) -> SuccessResponse:
    if current_user is None:
        raise HTTPException(status_code=400, detail="User Not Found")
    query = """
    SELECT * FROM eventcontainer e WHERE e.id = @id
    """
    
    params = [{"name": "@id", "value": event_details.id}]
    
    items = list(container.query_items(query=query, parameters=params, enable_cross_partition_query=True))

    if not items:
        raise HTTPException(status_code=400, detail="Event not found")

    existing_event = items[0]

    if existing_event["creator_id"] != current_user.id:
        raise HTTPException(status_code=401, detail="Not Authorized")

    update_data = event_details.dict(exclude_unset=True)

    # Convert lists to comma-separated strings
    if 'event_type' in update_data:
        update_data['type'] = ','.join(update_data['event_type'])
    if 'media_files' in update_data:
        update_data['media_files'] = ','.join(update_data['media_files'])

    for key, value in update_data.items():
        existing_event[key] = value

    container.replace_item(item=existing_event['id'], body=existing_event)
    return SuccessResponse(message="Event Updated Successfully", success=True)
