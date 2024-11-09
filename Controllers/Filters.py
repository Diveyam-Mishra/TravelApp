from Schemas.UserSchemas import *
from Schemas.EventSchemas import *
from Controllers.Auth import get_current_user
from Models.user_models import User
from Controllers.Payments import getBookedUsers
import random
import math
import asyncio
from fastapi import Depends
from fastapi.exceptions import HTTPException
from Models.Files import Avatar
from Helpers.calculateAge import calculate_age
from datetime import timedelta

import math

def deg2rad(deg):
    return deg * (math.pi / 180)

def event_distance(lat1, lon1, lat2, lon2):
    R = 6371  # Radius of the earth in km
    dLat = deg2rad(lat2 - lat1)  # Convert latitude difference to radians
    dLon = deg2rad(lon2 - lon1)  # Convert longitude difference to radians

    a = math.sin(dLat / 2) ** 2 + math.cos(deg2rad(lat1)) * math.cos(deg2rad(lat2)) * math.sin(dLon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))  # Use atan2 instead of asin for better accuracy

    distance = R * c  # Distance in kilometers
    return round(distance, 2)

from Controllers.Events import category_map

async def get_event_of_single_category(category: str, event_container, file_container):
    # Query to fetch events of a specific category
    query = f"SELECT * FROM c WHERE ARRAY_CONTAINS(c.event_type, '{category}')"

    events = []
    event_ids = []

    items = event_container.query_items(query=query, enable_cross_partition_query=True)

    if not items:
        raise HTTPException(status_code=400, detail="Events not found")

    #print(items)


    for event in items:
        events.append(event)
        event_ids.append(event['id'])

    if not event_ids:
        return events

    # Parallel execution of image queries
    async def fetch_image(event_id):
        image_query = f"SELECT TOP 1 c.fileName1, c.fileUrl1, c.fileType1 FROM c WHERE c.id = '{event_id}'"
        image_results = list(file_container.query_items(query=image_query, enable_cross_partition_query=True))
        return image_results[0] if image_results else None
    
    # #print(events)

    image_futures = [fetch_image(event_id) for event_id in event_ids]
    images = await asyncio.gather(*image_futures)
    
    for event, image in zip(events, images):
        if image:
            event['thumbnail'] = {
                "file_name": image.get('fileName1'),
                "file_url": image.get('fileUrl1'),
                "file_type": image.get('fileType1')
            }

    return events

async def update_events_with_thumbnails(event_container, file_container):
    # Query to fetch all events
    query = "SELECT * FROM c"

    # List to hold all event updates
    updates = []
    #print("ok")
    async def update_event(event):
        # Fetch the first image associated with the event
        image_query = f"SELECT TOP 1 c.fileName1, c.fileUrl1, c.fileType1 FROM c WHERE c.id = '{event['event_id']}'"
        image_results = list(file_container.query_items(query=image_query, enable_cross_partition_query=True))

        if image_results:
            # Add the first image's details to the event
            image = image_results[0]
            event['thumbnail'] = {
                "file_name": image.get('fileName1'),
                "file_url": image.get('fileUrl1'),
                "file_type": image.get('fileType1')
            }
            # Update the event in the database
            await event_container.replace_item(item=event['event_id'], body=event)
            #print("done")

    # Fetch and update each event
    for event in event_container.query_items(query=query, enable_cross_partition_query=True):
        updates.append(update_event(event))

    # Run all updates concurrently
    # await asyncio.gather(*updates)

    return "Events updated with thumbnails."

async def get_category_events(filters: List[str], coord: List[float], event_container, page: int):
    # Fetch all events
    query = "SELECT * FROM c"
    now = datetime.now().isoformat()
    query += " AND IS_STRING(c.start_date_and_time) AND c.start_date_and_time > @now"
    
    events = []
    for i, event_type in enumerate(filters):
        filters[i] = category_map.get(event_type)

    for event in event_container.query_items(
            query=query,
            enable_cross_partition_query=True
        ):
        # Count the number of matched types
        match_count = sum(1 for event_type in filters if event_type in event['event_type'])
        
        if match_count > 0:
            event['match_count'] = match_count
            event['distance'] = event_distance(
                event['location']['geo_tag']['latitude'],
                event['location']['geo_tag']['longitude'],
                coord[0],
                coord[1]
            )
            events.append(event)

    # Sort events based on the number of matching types
    sorted_events = sorted(events, key=lambda e: e['match_count'], reverse=True)
    total_count = len(sorted_events)
    items_per_page = 15
    start_index = page * items_per_page
    end_index = start_index + items_per_page
    paginated_events = sorted_events[start_index:end_index]

    return {
        "cnt": total_count,
        "results": paginated_events
    }

#filters Coming as Objects



async def get_sponsered_events(
    event_container, 
    limit: int = 10
):
    random_offset = random.randint(0, 100)
    query = """
    SELECT * FROM adcontainer e 
    OFFSET @random_offset LIMIT @limit
    """

    params = [
        {"name": "@random_offset", "value": random_offset},
        {"name": "@limit", "value": limit}
    ]
    events = list(event_container.query_items(
        query=query,
        parameters=params,
        enable_cross_partition_query=True
    ))

    return events

import time

async def search_events_by_name(
    partialname: PartialName,
    coord: List[float], 
    event_container,
    page: int
):
    start_time = time.time()  # Start timing the entire function

    query = """
    SELECT * FROM c 
    WHERE CONTAINS(c.event_name, @partial_name)
    """
    
    now = datetime.now().isoformat()
    query += " AND IS_STRING(c.start_date_and_time) AND c.start_date_and_time > @now"

    params = [
        {"name": "@partial_name", "value": partialname.partial_name.lower()}  # Convert the search term to lowercase
    ]
    params.append({"name": "@now", "value": now})

    # Timing the query execution
    query_start = time.time()
    events = list(event_container.query_items(
        query=query,
        parameters=params,
        enable_cross_partition_query=True
    ))
    query_time = time.time() - query_start
    print(f"Time taken for querying events: {query_time:.6f} seconds")

    # Fetch and attach the distance for each event
    distance_start = time.time()
    for event in events:
        event['distance'] = event_distance(event['location']['geo_tag']['latitude'],
                                           event['location']['geo_tag']['longitude'],
                                           coord[0], coord[1])
    distance_time = time.time() - distance_start
    print(f"Time taken for calculating distances: {distance_time:.6f} seconds")

    total_count = len(events)

    # Implement pagination
    items_per_page = 15
    start_index = page * items_per_page
    end_index = start_index + items_per_page
    paginated_events = events[start_index:end_index]

    # Total time taken for the function
    total_time = time.time() - start_time
    print(f"Total time taken for search_events_by_name: {total_time:.6f} seconds")

    return {
        "cnt": total_count,
        "results": paginated_events
    }

async def search_events_by_creator(
    coord:List[float],
    event_container,page,
    creator_id: User = Depends(get_current_user)
):
    creator_id=User.id
    query = """
    SELECT * FROM eventcontainer e 
    WHERE e.creator_id = @creator_id
    """

    params = [
        {"name": "@creator_id", "value": creator_id}
    ]

    events = list(event_container.query_items(
        query=query,
        parameters=params,
        enable_cross_partition_query=True
    ))
    for event in events:
        event['distance']=event_distance(event['location']['geo_tag']['latitude'],event['location']['geo_tag']['longitude'],coord[0],coord[1])
    
    total_count = len(events)
    items_per_page = 15
    start_index = page * items_per_page
    end_index = start_index + items_per_page
    paginated_events = events[start_index:end_index]
        
    return {
        "cnt": total_count,
        "results": paginated_events
    }

async def search_events_by_creator_past(
    time:str,
    db,bookingContainer,
    event_container,page,
    current_user: User
    
):
    current_datetime_iso = datetime.utcnow().isoformat()
    CreatorId=current_user.id
    time=time.lower()
    
    if time=="future":
        query = """
        SELECT * FROM eventcontainer e 
        WHERE e.creator_id = @current_user
        AND e.start_date_and_time > @current_datetime
        """
    else:
        query = """
        SELECT * FROM eventcontainer e 
        WHERE e.creator_id = @current_user
        AND e.start_date_and_time <= @current_datetime
        """
    params = [
        {"name": "@current_user", "value": CreatorId},
        {"name": "@current_datetime", "value": current_datetime_iso}
    ]

    events = list(event_container.query_items(
        query=query,
        parameters=params,
        enable_cross_partition_query=True
    ))
    for event in events:
        try:
            # #print(0)
            event["booked users"]=await getBookedUsers(event['id'], bookingContainer, current_user, db)
            # #print(event)
        except Exception as e:
            pass
            
    total_count = len(events)
    items_per_page = 15
    start_index = page * items_per_page
    end_index = start_index + items_per_page
    paginated_events = events[start_index:end_index]
        
    return {
        "cnt": total_count,
        "results": paginated_events
    }

async def search_events_by_creator_past_v1(
    time: str,
    db, bookingContainer,
    event_container, page,
    current_user: User
):
    utc_now = datetime.utcnow()

    # Define the IST timezone offset
    ist_offset = timedelta(hours=5, minutes=30)

    # Convert UTC time to IST time
    ist_now = utc_now + ist_offset

    # Get the IST time in ISO format
    current_datetime_ist_iso = ist_now.isoformat()
    # #print(current_datetime_ist_iso)
    CreatorId = current_user.id
    time = time.lower()

    if time == "future":
        query = """
        SELECT * FROM eventcontainer e 
        WHERE e.creator_id = @current_user
        AND e.start_date_and_time > @current_datetime
        """
    elif time=="past":
        query = """
        SELECT * FROM eventcontainer e 
        WHERE e.creator_id = @current_user
        AND e.start_date_and_time <= @current_datetime
        """
    else:
        query = """
        SELECT * FROM eventcontainer e 
        WHERE e.creator_id = @current_user"""
    # print(CreatorId)
    params = [
        {"name": "@current_user", "value": CreatorId},
        {"name": "@current_datetime", "value": current_datetime_ist_iso}
    ]

    events = list(event_container.query_items(
        query=query,
        parameters=params,
        enable_cross_partition_query=True
    ))

    event_ids = [event["id"] for event in events]
    # #print(len(event_ids))
    if event_ids:
        event_ids_str = ', '.join([f"'{event_id}'" for event_id in event_ids])
        # #print(event_ids_str)
        booked_users_query = f"""
        SELECT * FROM c WHERE c.event_id IN ({event_ids_str})
        """
        params = [{"name": "@event_ids", "value": event_ids_str}]

        bookingLists = list(bookingContainer.query_items(
            query=booked_users_query,
            enable_cross_partition_query=True
        ))
        # #print(len(bookingLists))
        # Prepare a dictionary to map event_id to booked users
        bookings_map = {
            booking["event_id"]: booking.get("booked_users", [])
            for booking in bookingLists
        }
        # #print(bookings_map)
        
        # for event in events:
        #     if bookings_map.get(event['id']) is not None:
        #         #print(bookings_map.get(event['id']), "bn")
        #         for user in bookings_map.get(event['id']):
        #             #print(user["user_id"], "bvs")

        user_ids = set()
        for booking_users in bookings_map.values():
            user_ids.update(user["user_id"] for user in booking_users)

        # #print(user_ids,'vv')

        if user_ids:
            results = (
                db.query(User, Avatar.fileurl)
                .outerjoin(Avatar, User.id == Avatar.userID)
                .filter(User.id.in_(user_ids))
                .all()
            )

            # #print(results)

            user_info = {
                user.id: {
                    "username": user.username,
                    "gender": user.gender,
                    "age": calculate_age(user.dob),
                    "Avatar": avatar_url
                }
                for user, avatar_url in results
            }

            # #print(user_info.get("abb26c0f-9227-4425-935f-fa98514495b3"), 'csc')

            # Attach booked users' info to corresponding events
            for event in events:
                booked_users = bookings_map.get(event["id"], [])
                event["booked_users"] = [
                    user_info.get(user["user_id"], {})
                    for user in booked_users
                ]
                basePrice = 0
                if event["price_fees"]:
                    basePrice = event["price_fees"]

                totalUsers = 0
                if event["booked_users"]:
                    totalUsers = len(event["booked_users"])
                event["total_booking_amount"] = basePrice * totalUsers
                # if(event["booked_users"]):
                #     #print(event)

    total_count = len(events)
    items_per_page = 15
    start_index = page * items_per_page
    end_index = start_index + items_per_page
    paginated_events = events[start_index:end_index]

    return {
        "cnt": total_count,
        "results": paginated_events
    }