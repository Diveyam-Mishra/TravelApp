from sqlalchemy.orm import Session
from Schemas.EventSchemas import *
from Schemas.UserSchemas import SuccessResponse
from Controllers.Auth import get_current_user
from Models.user_models import User
from fastapi import HTTPException, Depends, UploadFile
from Database.Connection import get_container, event_files_blob_container_name
from uuid import uuid4
from datetime import datetime, timedelta
from Helpers.Haversine import haversine
from Controllers.Files import fetch_event_files
from azure.cosmos.exceptions import CosmosHttpResponseError


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
    new_id = str(uuid4())
    new_event.update({
        "id": new_id,  # Generate a new UUID for the id field
        "event_ID": new_id,  # Generate a new UUID for the event_id field
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


async def update_event(
    event_id: str, 
    event_data: EventDetails,
    files: List[UploadFile],
    current_user: User,
    event_container,
    file_container,
    blob_service_client
) -> SuccessResponse:
    if current_user is None:
        raise HTTPException(status_code=400, detail="User Not Found")
    
    # Prepare the query to find the event
    query = """
    SELECT * FROM eventcontainer e WHERE e.id = @id
    """
    
    params = [{"name": "@id", "value": event_id}]
    
    items = list(event_container.query_items(query=query, parameters=params, enable_cross_partition_query=True))

    if not items:
        raise HTTPException(status_code=400, detail="Event not found")

    existing_event = items[0]

    # Authorization check
    editor_access = existing_event.get("editor_access", [])
    if existing_event["creator_id"] != current_user.id and current_user.id not in editor_access:
        raise HTTPException(status_code=401, detail="Not Authorized")

    update_data = event_data.dict(exclude_unset=True)

    # Convert lists to comma-separated strings
    if 'event_type' in update_data:
        update_data['type'] = ','.join(update_data.pop('event_type'))

    # Update existing event with new data
    for key, value in update_data.items():
        existing_event[key] = value

    event_container.replace_item(item=existing_event['id'], body=existing_event)

    if files:
        if len(files) > 5:
            raise HTTPException(status_code=400, detail="Maximum 5 files can be uploaded at once")

        # Fetch the existing files metadata from the file container
        query_files = "SELECT * FROM eventfilescontainer ef WHERE ef.id = @eventId"
        params_files = [{"name": "@eventId", "value": event_id}]
        file_items = list(file_container.query_items(query=query_files, parameters=params_files, enable_cross_partition_query=True))

        if not file_items:
            raise HTTPException(status_code=404, detail="Event files not found")

        existing_files = file_items[0]

        # Update only the specified files
        for file in files:
            # Extract the index from the file name pattern eventId_file_{i}
            file_extension = file.filename.split('.')[-1]
            file_index = int(file.filename.split('_')[-1].split('.')[0])  # Extract the index, e.g., '1' from 'eventId_file_1.jpg'

            file_name = f"{event_id}_file_{file_index}.{file_extension}"
            blob_client = blob_service_client.get_blob_client(container=event_files_blob_container_name, blob=file_name)
            
            # Read file data
            file_data = await file.read()
            
            # Upload file
            blob_client.upload_blob(file_data, overwrite=True)
            
            # Generate file URL
            file_url = blob_client.url
            
            # Update the existing file metadata
            existing_files[f'fileName{file_index}'] = file_name
            existing_files[f'fileUrl{file_index}'] = file_url
            existing_files[f'fileType{file_index}'] = file.content_type

        # Replace the existing file record with the updated metadata
        file_container.replace_item(item=existing_files['id'], body=existing_files)

    return SuccessResponse(message="Event Updated Successfully", success=True)


async def give_editor_access(
    db: Session,
    userId: str,
    event_id: str,
    current_user,
    container
) -> SuccessResponse:
    try:
        # Check if event exists in event container
        query = "SELECT * FROM eventcontainer e WHERE e.id = @id"
        params = [{"name": "@id", "value": event_id}]
        items = list(container.query_items(query=query, parameters=params, enable_cross_partition_query=True))

        if not items:
            raise HTTPException(status_code=404, detail="Event not found")
        
        existing_event = items[0]

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
        existing_event['editor_access'] = editor_access_list

        # Replace the item in the container with the updated data
        container.replace_item(item=existing_event['id'], body=existing_event)

        # Commit the transaction to the database
        db.commit()

        return SuccessResponse(message=f"Editor Access Granted to user ID: {userId}", success=True)
    
    except CosmosHttpResponseError as e:
        # Handle Cosmos DB specific errors
        raise HTTPException(status_code=500, detail=f"Cosmos DB Error: {str(e)}")
    except Exception as e:
        # Handle other exceptions
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

async def get_event_by_id(event_id: str, event_container, file_container, lat:float=0.0, long:float=0.0):
    # Query to find the event by its event_id
    event_query = "SELECT * FROM c WHERE c.id = @event_id"
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
    event_lat = event['location']['geo_tag']['latitude']
    event_lon = event['location']['geo_tag']['longitude']
    distance = haversine(lat, long, event_lat, event_lon)
    # Query to find images associated with the event
    event['distance']=distance
    try:
        image_files = await fetch_event_files(event_id, file_container)
        if image_files:
            event['images'] = image_files
    except HTTPException:
        # If fetch_event_files raises an HTTPException, skip adding images
        pass

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
    query = "SELECT * FROM event_container e WHERE IS_STRING(e.start_date_and_time)"
    params = []

    if filters.date_preference:
        today = datetime.today().date()
        if filters.date_preference == "Today":
            query += (
                " AND STARTSWITH(e.start_date_and_time, @date)"
            )
            params.append({"name": "@date", "value": today.isoformat()})
        elif filters.date_preference == "Tomorrow":
            tomorrow = today + timedelta(days=1)
            query += (
                " AND STARTSWITH(e.start_date_and_time, @date)"
            )
            params.append({"name": "@date", "value": tomorrow.isoformat()})
        elif filters.date_preference == "This week":
            start_of_week = today
            end_of_week = today + timedelta(days=(6 - today.weekday()))
            query += (
                " AND ("
                " (e.start_date_and_time >= @start_of_week AND e.start_date_and_time <= @end_of_week)"
                " )"
            )
            params.append({"name": "@start_of_week", "value": start_of_week.isoformat()})
            params.append({"name": "@end_of_week", "value": end_of_week.isoformat()})
        elif filters.date_preference == "Specific Date" and filters.specific_date:
            query += (
                " AND STARTSWITH(e.start_date_and_time, @date)"
            )
            params.append({"name": "@date", "value": filters.specific_date.isoformat()})

    # Apply event type filter
    if filters.event_type_preference:
        type_filters = []
        for i, event_type in enumerate(filters.event_type_preference):
            type_filters.append(f"ARRAY_CONTAINS(e.event_type, @event_type{i})")
            params.append({"name": f"@event_type{i}", "value": event_type})

        query += " AND (" + " OR ".join(type_filters) + ")"

    # Apply time filters
    if filters.time_preference:
        time_conditions = []
        for time_pref in filters.time_preference:
            if time_pref == "Morning":
                time_conditions.append("(e.start_date_and_time >= '06:00:00' AND e.start_date_and_time < '12:00:00')")
            elif time_pref == "Afternoon":
                time_conditions.append("(e.start_date_and_time >= '12:00:00' AND e.start_date_and_time < '17:00:00')")
            elif time_pref == "Evening":
                time_conditions.append("(e.start_date_and_time >= '17:00:00' AND e.start_date_and_time < '21:00:00')")
            elif time_pref == "Night":
                time_conditions.append("(e.start_date_and_time >= '21:00:00' OR e.start_date_and_time < '06:00:00')")
        if time_conditions:
            query += " AND (" + " OR ".join(time_conditions) + ")"

    # Query the event container
    items = event_container.query_items(query=query, parameters=params, enable_cross_partition_query=True)

    filtered_events = []
    for item in items:
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


    

async def advertise_event(event_id: takeString, advertised_events_container, container=Depends(get_container)) -> SuccessResponse:
    print("ok")
    query = """
    SELECT * FROM eventcontainer e WHERE e.id = @event_id
    """
    params = [
        {"name": "@event_id", "value": event_id.eventId}
    ]
    
    items = list(container.query_items(query=query, parameters=params, enable_cross_partition_query=True))
    print("fine")
    if not items:
        raise HTTPException(status_code=404, detail="Event not found")
    
    event_to_advertise = items[0] 
    advertised_event = event_to_advertise.copy()
    advertised_events_container.create_item(advertised_event)
    print("not ok")
    return SuccessResponse(message=f"Event with event_id: {event_id} successfully advertised", success=True)
