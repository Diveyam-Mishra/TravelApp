from sqlalchemy.orm import Session
from Schemas.EventSchemas import *
from Schemas.UserSchemas import SuccessResponse
from Controllers.Auth import get_current_user
from Models.user_models import User
from fastapi import HTTPException, Depends, UploadFile
from Database.Connection import get_container, event_files_blob_container_name,\
    AsyncSessionLocal
from uuid import uuid4
from datetime import datetime,timedelta
from Helpers.Haversine import haversine
from Controllers.Files import fetch_event_files
from azure.cosmos.exceptions import CosmosHttpResponseError

async def create_event(event_details: EventDetails, current_user: User, container=Depends(get_container)) -> SuccessResponse:
    # Prepare the query to check if the event already exists
    query = """
    SELECT e.event_name,e.host_information,e.event_type,e.start_date_and_time,e.end_date_and_time FROM eventcontainer e WHERE e.name = @name AND e.host_id = @host_id AND e.type = @type AND e.start_date = @start_date AND e.end_date = @end_date
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

from sqlalchemy import select

async def give_editor_access(
    db: AsyncSessionLocal,
    userId: str,
    event_id: str,
    current_user,
    container
) -> SuccessResponse:
    try:
        # Check if the event exists in the event container
        query = "SELECT e.id, e.editor_access, e.creator_id FROM eventcontainer e WHERE e.id = @id"
        params = [{"name": "@id", "value": event_id}]
        items = list(container.query_items(query=query, parameters=params, enable_cross_partition_query=True))

        if not items:
            raise HTTPException(status_code=404, detail="Event not found")
        
        existing_event = items[0]

        # Check if the user exists in the database asynchronously
        db_user = await db.execute(select(User).filter(User.id == userId))
        db_user = db_user.scalars().first()
        if not db_user:
            raise HTTPException(status_code=400, detail="User not found")

        # Authorization check
        if current_user.id != existing_event.get('creator_id'):
            raise HTTPException(status_code=401, detail="Not Authorized")

        # Check if the user already has editor access
        editor_access_list = existing_event.get('editor_access', [])
        if str(userId) in map(str, editor_access_list):
            raise HTTPException(status_code=400, detail="User already has editor access")

        # Add the new user ID to the editor access list
        editor_access_list.append(str(userId))
        existing_event['editor_access'] = editor_access_list

        # Replace the item in the container with the updated data
        container.replace_item(item=existing_event['id'], body=existing_event)

        # Commit the transaction to the database asynchronously
        await db.commit()
        
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

category_map = {
    # Social Events
    "Social Events": "Social Events",
    "Parties": "Social Events",
    "Meetups": "Social Events",
    "Networking Events": "Social Events",
    "Reunions": "Social Events",

    # Recreational Activities
    "Recreational Activities": "Recreational Activities",
    "Outdoor Activities": "Recreational Activities",
    "Water Activities": "Recreational Activities",
    "Adventure Sports": "Recreational Activities",

    # Weekend Getaways
    "Weekend Getaways": "Weekend Getaways",
    "Short Trips": "Weekend Getaways",
    "Staycations": "Weekend Getaways",
    "Road Trips": "Weekend Getaways",
    "Nature Retreats": "Weekend Getaways",

    # Workshops and Learning Events
    "Workshops and Learning Events": "Workshops and Learning Events",
    "Skill-building Workshops": "Workshops and Learning Events",
    "Cooking Classes": "Workshops and Learning Events",
    "Art and Craft Workshops": "Workshops and Learning Events",
    "Professional Development Seminars": "Workshops and Learning Events",

    # Cultural Events
    "Cultural Events": "Cultural Events",
    "Festivals": "Cultural Events",
    "Music Concerts": "Cultural Events",
    "Theater and Dance Performances": "Cultural Events",
    "Movie Screenings": "Cultural Events",

    # Health and Wellness
    "Health and Wellness": "Health and Wellness",
    "Yoga Retreats": "Health and Wellness",
    "Meditation Sessions": "Health and Wellness",
    "Wellness Workshops": "Health and Wellness",
    "Spa and Relaxation Events": "Health and Wellness",

    # Sports and Fitness
    "Sports and Fitness": "Sports and Fitness",
    "Marathons and Runs": "Sports and Fitness",
    "Fitness Bootcamps": "Sports and Fitness",
    "Sports Tournaments": "Sports and Fitness",
    "Group Workouts": "Sports and Fitness",

    # Food and Drink
    "Food and Drink": "Food and Drink",
    "Food Festivals": "Food and Drink",
    "Tasting Events": "Food and Drink",
    "Cooking Competitions": "Food and Drink",
    "Restaurant Pop-ups": "Food and Drink",

    # Community Events
    "Community Events": "Community Events",
    "Charity Events": "Community Events",
    "Community Gatherings": "Community Events",
    "Volunteering Opportunities": "Community Events",
    "Farmers Markets": "Community Events",

    # Family and Kids
    "Family and Kids": "Family and Kids",
    "Family Get-togethers": "Family and Kids",
    "Kids' Playdates": "Family and Kids",
    "Parenting Workshops": "Family and Kids",
    "Family-friendly Outings": "Family and Kids",

    # Business and Professional
    "Business and Professional": "Business and Professional",
    "Conferences": "Business and Professional",
    "Trade Shows": "Business and Professional",
    "Product Launches": "Business and Professional",
    "Webinars": "Business and Professional",

    # Hobbies and Special Interests
    "Hobbies and Special Interests": "Hobbies and Special Interests",
    "Book Clubs": "Hobbies and Special Interests",
    "Hobbyist Meetups": "Hobbies and Special Interests",
    "Collectors’ Fairs": "Hobbies and Special Interests",
    "Travel Enthusiast Gatherings": "Hobbies and Special Interests",

    # Holiday Celebrations
    "Holiday Celebrations": "Holiday Celebrations",
    "Christmas and New Year Parties": "Holiday Celebrations",
    "Easter Events": "Holiday Celebrations",
    "Halloween Parties": "Holiday Celebrations",
    "National Holiday Celebrations": "Holiday Celebrations",

    # Tech and Innovation
    "Tech and Innovation": "Tech and Innovation",
    "Hackathons": "Tech and Innovation",
    "Product Demos": "Tech and Innovation",
    "Tech Talks and Seminars": "Tech and Innovation",
    "Startup Pitch Events": "Tech and Innovation",

    # Spiritual and Religious
    "Spiritual and Religious": "Spiritual and Religious",
    "Religious Ceremonies": "Spiritual and Religious",
    "Spiritual Retreats": "Spiritual and Religious",
    "Meditation Gatherings": "Spiritual and Religious",
    "Devotional Music Events": "Spiritual and Religious",

    # Educational Events
    "Educational Events": "Educational Events",
    "Lectures and Talks": "Educational Events",
    "Educational Seminars": "Educational Events",
    "Study Groups": "Educational Events",
    "Science Fairs": "Educational Events"
}


async def get_filtered_events(
    event_container,
    filters: EventFilter,
    current_user: User = Depends(get_current_user)
):
    if current_user is None:
        raise HTTPException(status_code=400, detail="User Not Found")

    # Initialize the query with a base filter for valid events
    query = "SELECT * FROM event_container e WHERE IS_STRING(e.start_date_and_time)"
    now = datetime.now().isoformat()
    query += " AND e.start_date_and_time > @now"
    params = []
    params.append({"name": "@now", "value": now})

    if filters.date_preference:
        today = datetime.today().date()
        if filters.date_preference == "Today" or filters.date_preference=="today":
            query += (
                " AND STARTSWITH(e.start_date_and_time, @date)"
            )
            params.append({"name": "@date", "value": today.isoformat()})
        elif filters.date_preference == "Tomorrow" or filters.date_preference=="tomorrow":
            tomorrow = today + timedelta(days=1)
            query += (
                " AND STARTSWITH(e.start_date_and_time, @date)"
            )
            params.append({"name": "@date", "value": tomorrow.isoformat()})
        elif filters.date_preference == "This week"or filters.date_preference=="this week":
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
            if filters.specific_date.endswith('Z'):
                # Remove the 'Z' and convert the string to a datetime object
                filters.specific_date = datetime.fromisoformat(filters.specific_date[:-1])
            else:
                # Convert to datetime if it doesn't end with 'Z'
                filters.specific_date = datetime.fromisoformat(filters.specific_date)

            # Construct the query and parameters
            query += " AND STARTSWITH(e.start_date_and_time, @date)"
            params.append({"name": "@date", "value": filters.specific_date.isoformat()})

    # Apply event type filter
    if filters.event_type_preference and len(filters.event_type_preference)>0:
        print(filters.event_type_preference)
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

    # print(query)
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
    query = """
    SELECT * FROM eventcontainer e WHERE e.id = @event_id
    """
    params = [
        {"name": "@event_id", "value": event_id.eventId}
    ]
    
    items = list(container.query_items(query=query, parameters=params, enable_cross_partition_query=True))
    if not items:
        raise HTTPException(status_code=404, detail="Event not found")
    
    event_to_advertise = items[0] 
    advertised_event = event_to_advertise.copy()
    advertised_events_container.create_item(advertised_event)

    return SuccessResponse(message=f"Event with event_id: {event_id} successfully advertised", success=True)

async def batch_event(event_ids:List[str], coord:GeoTag,container):
    event_ids = event_ids[:6]
    query = "SELECT * FROM eventcontainer e WHERE e.id IN ({})".format(
    ", ".join(f"'{event_id}'" for event_id in event_ids)
)
    events = list(container.query_items(
        query=query,
        enable_cross_partition_query=True
    ))
    for item in events:
        event_lat = item['location']['geo_tag']['latitude']
        event_lon = item['location']['geo_tag']['longitude']
        user_lat = coord.latitude
        user_lon = coord.longitude
        distance = haversine(user_lat, user_lon, event_lat, event_lon)
        item['distance']=distance
        keys_to_remove = ["creator_id","host_information","duration","remaining_capacity", "creator_id", "editor_access","_rid", "_self", "_etag", "_attachments", "_ts"]
        for key in keys_to_remove:
            item.pop(key, None)

    return events