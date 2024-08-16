from sqlalchemy.orm import Session
from Schemas.EventSchemas import EventDetails, EventDetailsupdate, EventFilter
from Schemas.UserSchemas import SuccessResponse
from Controllers.Auth import pwd_context, JWT_SECRET
import jwt
from Models.event_models import Event
from Controllers.Auth import get_current_user
from Models.user_models import User
from fastapi import HTTPException, Depends
from Database.Connection import get_container
from uuid import uuid4
from datetime import datetime, timedelta
from sqlalchemy import and_, or_
from sqlalchemy.sql import extract
from Models.org_models import Organization
from sqlalchemy import func
from Helpers.Haversine import haversine


async def create_event(event_details: EventDetails, current_user: User, container=Depends(get_container)) -> SuccessResponse:
    # Prepare the query to check if the event already exists
    query = """
    SELECT * FROM eventcontainer e WHERE e.name = @name AND e.host_id = @host_id AND e.type = @type AND e.start_date = @start_date AND e.end_date = @end_date
    """
    
    params = [
        {"name": "@name", "value": event_details.event_name},
        {"name": "@host_id", "value": event_details.host_information.id},
        {"name": "@type", "value": ','.join(event_details.event_type)},
        {"name": "@start_date", "value": event_details.start_date_and_time.to_datetime().isoformat()},
        {"name": "@end_date", "value": event_details.end_date_and_time.to_datetime().isoformat()}
    ]
    
    items = list(container.query_items(query=query, params=params, enable_cross_partition_query=True))

    if items:
        raise HTTPException(status_code=400, detail="Event already created")

    # Calculate the duration in minutes
    start_datetime = event_details.start_date_and_time.to_datetime()
    end_datetime = event_details.end_date_and_time.to_datetime()
    duration_minutes = int((end_datetime - start_datetime).total_seconds() / 60)

    # Create a new event
    new_event = event_details.dict()
    new_event.update({
        "id": str(uuid4()),  # Generate a new UUID for the id field
        "event_id": str(uuid4()),  # Generate a new UUID for the event_id field
        "type": ','.join(event_details.event_type),  # Convert list to comma-separated string
        "start_date": start_datetime.isoformat(),  # Convert datetime to ISO format string
        "end_date": end_datetime.isoformat(),  # Convert datetime to ISO format string
        "duration": str(duration_minutes),  # Store duration as a string
        "remaining_capacity": event_details.capacity,
        "creator_id": current_user.id,  # Use the current user's ID
        "editor_access": [str(current_user.id)]  # Set the creator as the editor
    })
    new_event["location"] = {
        "venue": event_details.location.venue,
        "geo_tag": {
            "latitude": event_details.location.geo_tag.latitude,
            "longitude": event_details.location.geo_tag.longitude
        }
    }

    container.create_item(new_event)
    return SuccessResponse(message=f"Event Created Successfully with event_id: {new_event['id']}", success=True)

async def update_event(event_id: str, event_details: EventDetailsupdate, container=Depends(get_container), current_user: User = Depends(get_current_user)) -> SuccessResponse:
    if current_user is None:
        raise HTTPException(status_code=400, detail="User Not Found")
    
    # Prepare the query to find the event
    query = """
    SELECT * FROM eventcontainer e WHERE e.id = @id
    """
    
    params = [{"name": "@id", "value": event_id}]
    
    items = list(container.query_items(query=query, params=params, enable_cross_partition_query=True))

    if not items:
        raise HTTPException(status_code=400, detail="Event not found")

    existing_event = items[0]

    # Authorization check
    editor_access = existing_event.get("editor_access", [])
    if existing_event["creator_id"] != current_user.id and str(current_user.id) not in editor_access:
        raise HTTPException(status_code=401, detail="Not Authorized")

    update_data = event_details.dict(exclude_unset=True)

    # Convert lists to comma-separated strings
    if 'event_type' in update_data:
        update_data['type'] = ','.join(update_data.pop('event_type'))

    # Convert datetime fields to ISO format strings
    if 'start_date_and_time' in event_details:
        update_data['start_date'] = event_details.start_date_and_time.to_datetime().isoformat()
    if 'end_date_and_time' in event_details:
        update_data['end_date'] = event_details.end_date_and_time.to_datetime().isoformat()

    # Update existing event with new data
    for key, value in update_data.items():
        existing_event[key] = value

    container.replace_item(item=existing_event['id'], body=existing_event)
    return SuccessResponse(message="Event Updated Successfully", success=True)

async def give_editor_access(
    db: Session,
    userId: int,
    event_id: str,
    current_user: User = Depends(get_current_user),
    container=Depends(get_container)
) -> SuccessResponse:
    # Check if event exists in event container
    query = """
    SELECT * FROM eventcontainer e WHERE e.id = @id
    """
    
    params = [{"name": "@id", "value": event_id}]
    
    items = list(container.query_items(query=query, params=params, enable_cross_partition_query=True))

    if not items:
        raise HTTPException(status_code=404, detail="Event not found")
    
    existing_event = items[0]  # Assuming items is a list and taking the first element

    # Check if user exists
    db_user = db.query(User).filter(User.id == userId).first()
    if not db_user:
        raise HTTPException(status_code=400, detail="User not found")

    # Authorization check
    if current_user.id != existing_event.get('creator_id'):
        raise HTTPException(status_code=401, detail="Not Authorized")

    # Check if user already has editor access
    editor_access_list = existing_event.get('editor_access', [])
    if str(userId) in map(str, editor_access_list):
        raise HTTPException(status_code=400, detail="User already has editor access")

    # Add the new user ID to the editor access list
    editor_access_list.append(str(userId))

    # Update the event's editor access field
    existing_event['editor_access'] = editor_access_list

    # Replace the item in the container with the updated data
    container.replace_item(item=existing_event['id'], body=existing_event)

    # Commit the transaction to the database
    db.commit()

    return SuccessResponse(message=f"Editor Access Granted to user ID: {userId}", success=True)

async def get_event_by_id(event_id: str, event_container, file_container):
    # Query to find the event by its event_id
    event_query = "SELECT * FROM c WHERE c.event_id = @event_id"
    params = [{"name": "@event_id", "value": event_id}]
    
    # Query the event container for the event with the specified event_id
    events = list(event_container.query_items(
        query=event_query,
        parameters=params,
        enable_cross_partition_query=True
    ))
    
    if not events:
        raise HTTPException(status_code=404, detail="Event not found")
    
    event = events[0]  # Since event_id is unique, we get the first item

    # Query to find images associated with the event
    image_query = "SELECT * FROM c WHERE c.eventId = @event_id"
    
    image_files = list(file_container.query_items(
        query=image_query,
        parameters=params,
        enable_cross_partition_query=True
    ))

    # Include the images in the event data
    if image_files:
        event['images'] = [
            {
                "fileName": image.get("fileName1"),
                "fileType": image.get("fileType1"),
                "fileData": image.get("fileData1"),
            }
            for image in image_files
        ]

    return event

# def get_filtered_events(
#     db: Session, 
#     filters: EventFilter, 
#     limit: int = 30, 
#     current_user: User = Depends(get_current_user)
# ):
#     if current_user is None:
#         raise HTTPException(status_code=400, detail="User Not Found")
    
#     # Start building the query
#     query = db.query(Event.id, Event.name, Event.description).join(Organization, Event.host_id == Organization.id)
    
#     # Apply date filters
#     if filters.date_preference:
#         today = datetime.today().date()
#         if filters.date_preference == "Today":
#             query = query.filter(Event.start_date >= today, Event.start_date < today + timedelta(days=1))
#         elif filters.date_preference == "Tomorrow":
#             tomorrow = today + timedelta(days=1)
#             query = query.filter(Event.start_date >= tomorrow, Event.start_date < tomorrow + timedelta(days=1))
#         elif filters.date_preference == "This week":
#             end_of_week = today + timedelta(days=(6 - today.weekday()))
#             query = query.filter(Event.start_date >= today, Event.start_date <= end_of_week)
#         elif filters.date_preference == "Specific Date" and filters.specific_date:
#             query = query.filter(Event.start_date == filters.specific_date)
    
#     # Apply time filters
#     if filters.time_preference:
#         time_filters = []
#         for time_pref in filters.time_preference:
#             if time_pref == "Morning":
#                 time_filters.append(and_(extract('hour', Event.start_date) >= 6, extract('hour', Event.start_date) < 12))
#             elif time_pref == "Afternoon":
#                 time_filters.append(and_(extract('hour', Event.start_date) >= 12, extract('hour', Event.start_date) < 17))
#             elif time_pref == "Evening":
#                 time_filters.append(and_(extract('hour', Event.start_date) >= 17, extract('hour', Event.start_date) < 21))
#             elif time_pref == "Night":
#                 time_filters.append(or_(extract('hour', Event.start_date) >= 21, extract('hour', Event.start_date) < 6))
#         query = query.filter(or_(*time_filters))
    
#     # Apply location filters
#     if filters.location_preference:
#         if filters.location_preference == "Near me":
#             user_lat, user_lon = filters.user_latitude, filters.user_longitude
#             distance_filter = and_(
#                 func.acos(
#                     func.sin(func.radians(user_lat)) * func.sin(func.radians(Organization.latitude)) + 
#                     func.cos(func.radians(user_lat)) * func.cos(func.radians(Organization.latitude)) * 
#                     func.cos(func.radians(Organization.longitude) - func.radians(user_lon))
#                 ) * 6371 <= 50
#             )
#             query = query.filter(distance_filter)
#         elif filters.location_preference == "In the city":
#             user_city = filters.user_city  
#             query = query.filter(Organization.city == user_city)
#         elif filters.location_preference == "Nearby town":
#             user_lat, user_lon = filters.user_latitude, filters.user_longitude
#             distance_filter = and_(
#                 func.acos(
#                     func.sin(func.radians(user_lat)) * func.sin(func.radians(Organization.latitude)) + 
#                     func.cos(func.radians(user_lat)) * func.cos(func.radians(Organization.latitude)) * 
#                     func.cos(func.radians(Organization.longitude) - func.radians(user_lon))
#                 ) * 6371 <= 200
#             )
#             query = query.filter(distance_filter)
#         elif filters.location_preference == "Open to traveling":
#             pass  # No additional filter needed

#     # Apply duration filter
#     if filters.duration_preference:
#         query = query.filter(Event.duration == filters.duration_preference)
    
#     # Limit and fetch results
#     return query.limit(limit).all()

async def get_filtered_events(
    event_container, 
    filters: EventFilter, 
    current_user: User = Depends(get_current_user)
):
    if current_user is None:
        raise HTTPException(status_code=400, detail="User Not Found")
    
    # Initialize the query with a base filter for valid events
    query = "SELECT * FROM event_container e WHERE 1=1"
    params = []

    if filters.date_preference:
        today = datetime.today().date()
        if filters.date_preference == "Today":
            query += (
                " AND e.start_date_and_time.day = @day"
                " AND e.start_date_and_time.month = @month"
                " AND e.start_date_and_time.year = @year"
            )
            params.append({"name": "@day", "value": today.day})
            params.append({"name": "@month", "value": today.month})
            params.append({"name": "@year", "value": today.year})
        elif filters.date_preference == "Tomorrow":
            tomorrow = today + timedelta(days=1)
            query += (
                " AND e.start_date_and_time.day = @day"
                " AND e.start_date_and_time.month = @month"
                " AND e.start_date_and_time.year = @year"
            )
            params.append({"name": "@day", "value": tomorrow.day})
            params.append({"name": "@month", "value": tomorrow.month})
            params.append({"name": "@year", "value": tomorrow.year})
        elif filters.date_preference == "This week":
            start_of_week = today
            end_of_week = today + timedelta(days=(6 - today.weekday()))
            query += (
                " AND e.start_date_and_time.year = @year"
                " AND ("
                " (e.start_date_and_time.month = @start_month AND e.start_date_and_time.day >= @start_day)"
                " OR (e.start_date_and_time.month = @end_month AND e.start_date_and_time.day <= @end_day)"
                " )"
            )
            params.append({"name": "@year", "value": today.year})
            params.append({"name": "@start_day", "value": start_of_week.day})
            params.append({"name": "@start_month", "value": start_of_week.month})
            params.append({"name": "@end_day", "value": end_of_week.day})
            params.append({"name": "@end_month", "value": end_of_week.month})
        elif filters.date_preference == "Specific Date" and filters.specific_date:
            query += (
                " AND e.start_date_and_time.day = @day"
                " AND e.start_date_and_time.month = @month"
                " AND e.start_date_and_time.year = @year"
            )
            params.append({"name": "@day", "value": filters.specific_date.day})
            params.append({"name": "@month", "value": filters.specific_date.month})
            params.append({"name": "@year", "value": filters.specific_date.year})

    # Apply event type filter
    if filters.event_type_preference:
        # Build the event type filter dynamically
        type_filters = []
        for i, event_type in enumerate(filters.event_type_preference):
            type_filters.append(f"ARRAY_CONTAINS(e.event_type, @event_type{i})")
            params.append({"name": f"@event_type{i}", "value": event_type})

        # Join all filters with OR
        query += " AND (" + " OR ".join(type_filters) + ")"

    # Apply time filters
    if filters.time_preference:
        time_conditions = []
        for time_pref in filters.time_preference:
            if time_pref == "Morning":
                time_conditions.append("(e.start_date_and_time.hour >= 6 AND e.start_date_and_time.hour < 12)")
            elif time_pref == "Afternoon":
                time_conditions.append("(e.start_date_and_time.hour >= 12 AND e.start_date_and_time.hour < 17)")
            elif time_pref == "Evening":
                time_conditions.append("(e.start_date_and_time.hour >= 17 AND e.start_date_and_time.hour < 21)")
            elif time_pref == "Night":
                time_conditions.append("(e.start_date_and_time.hour >= 21 OR e.start_date_and_time.hour < 6)")
        if time_conditions:
            query += " AND (" + " OR ".join(time_conditions) + ")"

    # Apply location filters
    items = event_container.query_items(query=query, parameters=params, enable_cross_partition_query=True)

    filtered_events = []
    for item in items:
        # Apply location filter using Haversine formula
        if filters.location_preference:
            event_lat = item['location']['geo_tag']['latitude']
            event_lon = item['location']['geo_tag']['longitude']
            user_lat = filters.user_latitude
            user_lon = filters.user_longitude

            distance = haversine(user_lat, user_lon, event_lat, event_lon)

            if filters.location_preference == "Near Me" and distance <= 50:
                filtered_events.append(item)
            elif filters.location_preference == "Nearby town" and distance <= 200:
                filtered_events.append(item)
            elif filters.location_preference == "In the city" and item['location']['city'] == filters.user_city:
                filtered_events.append(item)
        else:
            filtered_events.append(item)


    return filtered_events
    