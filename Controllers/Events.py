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
import uuid
from datetime import datetime, timedelta
from sqlalchemy import and_, or_
from sqlalchemy.sql import extract
from Models.org_models import Organization
from sqlalchemy import func


async def create_event(event_details: EventDetails, container=Depends(get_container), current_user: User=Depends(get_current_user)) -> SuccessResponse:
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


async def update_event(event_details: EventDetailsupdate, container=Depends(get_container), current_user: User=Depends(get_current_user)) -> SuccessResponse:
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


def get_filtered_events(db: Session, filters: EventFilter, limit: int = 30, current_user: User=Depends(get_current_user)):
    if current_user is None:
        raise HTTPException(status_code=400, detail="User Not Found")
    # Start building the query
    query = db.query(Event.id, Event.name, Event.description).join(Organization, Event.host_id == Organization.id)
    
    # Apply date filters
    if filters.date_preference:
        if filters.date_preference == "Today":
            today = datetime.today().date()
            query = query.filter(Event.start_date >= today, Event.start_date < today + timedelta(days=1))
        elif filters.date_preference == "Tomorrow":
            tomorrow = datetime.today().date() + timedelta(days=1)
            query = query.filter(Event.start_date >= tomorrow, Event.start_date < tomorrow + timedelta(days=1))
        elif filters.date_preference == "This week":
            today = datetime.today().date()
            end_of_week = today + timedelta(days=(6 - today.weekday()))
            query = query.filter(Event.start_date >= today, Event.start_date <= end_of_week)
        elif filters.date_preference == "Specific Date" and filters.specific_date:
            query = query.filter(Event.start_date == filters.specific_date)
    
    # Apply time filters
    if filters.time_preference:
        time_filters = []
        for time_pref in filters.time_preference:
            if time_pref == "Morning":
                time_filters.append(and_(extract('hour', Event.start_date) >= 6, extract('hour', Event.start_date) < 12))
            elif time_pref == "Afternoon":
                time_filters.append(and_(extract('hour', Event.start_date) >= 12, extract('hour', Event.start_date) < 17))
            elif time_pref == "Evening":
                time_filters.append(and_(extract('hour', Event.start_date) >= 17, extract('hour', Event.start_date) < 21))
            elif time_pref == "Night":
                time_filters.append(or_(extract('hour', Event.start_date) >= 21, extract('hour', Event.start_date) < 6))
        query = query.filter(or_(*time_filters))
    
    # # Apply location filters
    if filters.location_preference:
        if filters.location_preference == "Near me":
            user_lat, user_lon = filters.user_latitude, filters.user_longitude
            distance_filter = and_(
                func.acos(
                    func.sin(func.radians(user_lat)) * func.sin(func.radians(Organization.latitude)) + 
                    func.cos(func.radians(user_lat)) * func.cos(func.radians(Organization.latitude)) * 
                    func.cos(func.radians(Organization.longitude) - func.radians(user_lon))
                ) * 6371 <= 50
            )
            query = query.filter(distance_filter)
        elif filters.location_preference == "In the city":
            user_city = filters.user_city  
            query = query.filter(Organization.city == user_city)
        elif filters.location_preference == "Nearby town":
            user_lat, user_lon = filters.user_latitude, filters.user_longitude
            distance_filter = and_(
                func.acos(
                    func.sin(func.radians(user_lat)) * func.sin(func.radians(Organization.latitude)) + 
                    func.cos(func.radians(user_lat)) * func.cos(func.radians(Organization.latitude)) * 
                    func.cos(func.radians(Organization.longitude) - func.radians(user_lon))
                ) * 6371 <= 200
            )
            query = query.filter(distance_filter)
        elif filters.location_preference == "Open to traveling":
            pass  # No additional filter needed

    # # Apply duration filter
    if filters.duration_preference:
        query = query.filter(Event.duration == filters.duration_preference)
    
    # Limit and fetch results
    return query.limit(limit).all()
