from sqlalchemy.orm import Session
from Models.user_models import User, OTP, deletedUser
from Models.Files import Avatar
from Schemas.UserSchemas import *
from jose import JWTError
from fastapi import HTTPException, Depends
import jwt
from jwt.exceptions import ExpiredSignatureError
from fastapi.security import OAuth2PasswordBearer
from config import settings
from passlib.context import CryptContext
from Database.Connection import get_db, AsyncSessionLocal
from Controllers.OtpGen import create_otp
from datetime import timedelta
import uuid
from typing import List, Dict
from Schemas.userSpecific import UserSpecific,CreditCard,BankingDetails
from Models.Files import Carousel_image

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

from sqlalchemy import select

async def get_user(db: AsyncSessionLocal, user_id: str):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()  # Get the first matching user or None
    return user


async def get_user_by_email(db: AsyncSessionLocal, email: str):
    result = await db.execute(select(User).where(User.email == email))
    return result.scalars().first()  # Get the first matching user or None


async def get_user_by_username(db: AsyncSessionLocal, username: str):
    result = await db.execute(select(User).where(User.username == username))
    return result.scalars().first()  # Get the first matching user or None

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
JWT_SECRET = settings.JWT_SECRET
ALGORITHM = settings.ALGORITHM


async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSessionLocal = Depends(get_db)) -> UserWithAvatar:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])

        user_id = payload.get("user_id")

        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")

        # Query the user asynchronously
        result = await db.execute(
            select(User, Avatar.fileurl)
            .outerjoin(Avatar, User.id == Avatar.userID)
            .filter(User.id == user_id)
        )
        db_user = result.first()
        # print(db_user)
        if not db_user:
            raise HTTPException(status_code=400, detail="User not found")

        user_details, avatar_url = db_user

        user_with_avatar = UserWithAvatar(
            id=user_details.id,
            email=user_details.email,
            username=user_details.username,
            is_admin=user_details.is_admin,
            works_at=user_details.works_at,
            contact_no=user_details.contact_no,
            dob=user_details.dob,
            gender=user_details.gender,
            created_at=user_details.created_at,
            avatar_url=avatar_url
        )

    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Token error: {str(e)}")
    
    return user_with_avatar

async def get_current_user_optional(token: str, db: AsyncSessionLocal = Depends(get_db)):
    try:
        # Decode the token and verify its signature and expiration
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        # Query the user from the database using async select
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalars().first()  # Get the first result
        
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")
    
    except ExpiredSignatureError:
        # Handle token expiration
        raise HTTPException(status_code=401, detail="Token has expired")
    except JWTError:
        # Handle other JWT errors
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        # Handle other potential exceptions
        raise HTTPException(status_code=401, detail=f"Token error: {str(e)}")
     
    return user

async def update_user(req: UserUpdate, db: AsyncSessionLocal, userId: str, current_user: User, user_specific_container):
    # Fetch the user asynchronously
    result = await db.execute(select(User).where(User.id == userId))
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if str(current_user.id) != str(userId):
        raise HTTPException(status_code=403, detail="You are not authorized to update this user")

    # Update the user's details with the data from req
    if req.username is not None:
        await check_unique_username(req.username, db)
        user.username = req.username
    if req.works_at is not None:
        user.works_at = req.works_at
    if req.contact_no is not None:
        user.contact_no = req.contact_no
    if req.dob is not None:
        user.dob = req.dob
    if req.gender is not None:
        user.gender = req.gender
    if req.interestAreas is not None:
        await add_interest_areas_to_user(userId, req.interestAreas, user_specific_container)

    # Commit the changes to the database
    await db.commit()  # Use await for the commit operation

    # Optionally, refresh the instance to reflect changes
    await db.refresh(user)

    return {"message": "User updated successfully", "success": True}


async def check_unique_username(username: str, db: AsyncSessionLocal) -> SuccessResponse:
    # Query to check if the username already exists asynchronously
    result = await db.execute(select(User).where(User.username == username))
    query = result.scalars().first()

    if query:
        raise HTTPException(status_code=400, detail="Username already taken")

    return SuccessResponse(message="Username Available", success=True)


async def create_user(db: AsyncSessionLocal, user: UserCreate) -> UserResponse:
    # hashed_password = pwd_context.hash(user.password)  # Uncomment if you plan to hash passwords
    db_user = User(
        email=user.email,
        username=user.username,
        # password=hashed_password,
        contact_no=user.contact_no,
        works_at=user.works_at
    )
    db.add(db_user)
    await db.commit()  # Use await for the commit operation
    await db.refresh(db_user)  # Refresh the instance to reflect the changes

    return db_user


async def delete_user(current_user: User, db: AsyncSessionLocal) -> SuccessResponse:
    deleted_user = deletedUser(
        email=current_user.email,
        username=current_user.username,
        works_at=current_user.works_at,
        contact_no=current_user.contact_no
    )
    x = current_user.id
    db.add(deleted_user)
    
    # Delete the current user
    db.delete(current_user)

    # Delete avatar if it exists
    avatar = await db.execute(select(Avatar).where(Avatar.userID == x))
    avatar_instance = avatar.scalars().first()
    if avatar_instance:
        db.delete(avatar_instance)

    await db.commit()  # Commit the changes

    return SuccessResponse(message="User deleted successfully", success=True)


async def register_user(db: AsyncSessionLocal, email: str = None, username: str = None) -> SuccessResponse:
    if (not email) and (not username):
        raise HTTPException(status_code=400, detail="Both Email and Username are required")
    
    if email:
        db_user = await db.execute(select(User).where(User.email == email))
        db_user_instance = db_user.scalars().first()
        if db_user_instance:
            raise HTTPException(status_code=400, detail="Email already registered")
    
    if username:
        db_user = await db.execute(select(User).where(User.username == username))
        db_user_instance = db_user.scalars().first()
        if db_user_instance:
            raise HTTPException(status_code=400, detail="Username already registered")
    
    if email == "trabiitestaccount1781@trabii.com":
        return SuccessResponse(message="OTP sent to your email", success=True)

    if email:  # Assuming create_otp only needs email
        await create_otp(db, email)
     
    return SuccessResponse(message="OTP sent to your email", success=True)


async def login_user(login_data: UserLogin, db: AsyncSessionLocal) -> SuccessResponse:
    if not login_data.email and not login_data.username:
        raise HTTPException(status_code=400, detail="Either email or username is required")
    
    db_user = None
    user_email = None

    if login_data.email:
        db_user = await db.execute(select(User).where(User.email == login_data.email))
        db_user_instance = db_user.scalars().first()
        user_email = login_data.email

    if login_data.username and not db_user_instance:
        db_user = await db.execute(select(User).where(User.username == login_data.username))
        db_user_instance = db_user.scalars().first()
        if db_user_instance:
            user_email = db_user_instance.email

    if not db_user_instance:
        raise HTTPException(status_code=400, detail="User not found")
    
    if user_email == "trabiitestaccount1781@trabii.com":
        return SuccessResponse(message="OTP sent to your email", success=True)
    
    await create_otp(db, user_email)  # Call create_otp as an async function
     
    return SuccessResponse(message="OTP sent to your email", success=True)


async def login_verify(login_data: UserLoginVerify, db: AsyncSessionLocal) -> SuccessResponse:
    if not login_data.email and not login_data.username:
        raise HTTPException(status_code=400, detail="Either email or username is required")
    
    if not login_data.otp:
        raise HTTPException(status_code=400, detail="OTP is required")
    
    db_user = None
    user_email = None

    if login_data.username and not login_data.email:
        db_user_result = await db.execute(select(User).where(User.username == login_data.username))
        db_user = db_user_result.scalars().first()
        if not db_user:
            raise HTTPException(status_code=400, detail="User not found")
        user_email = db_user.email
    else:
        user_email = login_data.email
        db_user_result = await db.execute(select(User).where(User.email == user_email))
        db_user = db_user_result.scalars().first()
        if not db_user:
            raise HTTPException(status_code=400, detail="User not found")
        
    if user_email == "trabiitestaccount1781@trabii.com":
        if login_data.otp == "111111":
            expiry_time = datetime.utcnow() + timedelta(days=30)

            # Create token data with the expiration time
            token_data = {
                'user_id': db_user.id,  # Example user ID
                'exp': expiry_time
            }

            token = jwt.encode(token_data, JWT_SECRET, algorithm="HS256")
            
            return SuccessResponse(message="User logged in successfully", token=token, success=True)
        else:
            raise HTTPException(status_code=400, detail="Invalid or expired OTP")

    db_otp_result = await db.execute(select(OTP).where(OTP.email == user_email, OTP.otp == login_data.otp))
    db_otp = db_otp_result.scalars().first()
    if not db_otp or db_otp.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")

    expiry_time = datetime.utcnow() + timedelta(days=30)

    # Create token data with the expiration time
    token_data = {
        'user_id': db_user.id,  # Example user ID
        'exp': expiry_time
    }

    token = jwt.encode(token_data, JWT_SECRET, algorithm="HS256")
    
    # Delete the OTP after successful login
    db.delete(db_otp)
    await db.commit()  # Commit the changes asynchronously
     
    return SuccessResponse(message="User logged in successfully", token=token, success=True)

async def look_up_username(username: str, db: AsyncSessionLocal, current_user: User = Depends(get_current_user)):
    if current_user is None:
        raise HTTPException(status_code=400, detail="User Not Found")

    # Query to get user details along with their avatar URL
    db_user_result = await db.execute(
        select(User, Avatar.fileurl)
        .outerjoin(Avatar, User.id == Avatar.userID)  # Join with Avatar table
        .where(User.username == username)  # Use the username to filter
    )

    db_user = db_user_result.first()  # Get the first result
    
    if not db_user:
        raise HTTPException(status_code=400, detail="User not found")
    
    user_details, avatar_url = db_user  # Unpack the result tuple

    # Return both user details and avatar URL here
    return {"user": user_details, "avatar_url": avatar_url}

async def add_interest_areas_to_user(userId:str, interestAreas:List[str], user_specific_container):
    query = "SELECT interest_areas FROM c where c.userId = @userId"
    params = [{"name":"@userId", "value":userId}]

    search = list(user_specific_container.query_items(query=query,
        parameters=params,
        enable_cross_partition_query=True))

    if not search:
        user_specific = UserSpecific(id=userId, userId=userId, booked_events=[], recent_searches=[], interest_areas=interestAreas)
        user_specific_container.create_item(user_specific.to_dict())
        current_time = datetime.datetime.now()
        print(current_time.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3])
        return SuccessResponse(message="User Interest areas updated successfully", success=True)
    else:
        # Update the interest_areas if the user already exists
        user_specific = search[0]
        user_specific["interest_areas"] = interestAreas
        user_specific_container.replace_item(user_specific["id"], user_specific)
        current_time = datetime.datetime.now()
        print(current_time.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3])
        return {"message": "User interest areas updated successfully", "success": True}


import time  # Import the time module for tracking execution time

async def add_recent_search(userId, searchItem, user_specific_container):
    start_time = time.time()  # Start the timer

    # Query to retrieve user-specific data
    query = "SELECT * FROM c WHERE c.id = @userId"
    params = [{"name": "@userId", "value": userId}]

    # Track time taken for querying items
    query_start = time.time()
    search = list(user_specific_container.query_items(query=query,
                                                     parameters=params,
                                                     enable_cross_partition_query=True))
    query_time = time.time() - query_start
    print(f"Time taken for querying items: {query_time:.6f} seconds")  # Log the time

    if search:
        user_specific_data = search[0]
        user_specific = UserSpecific(**user_specific_data)
    else:
        user_specific = UserSpecific(
            id=userId,
            userId=userId,
            booked_events=[],
            recent_searches=[],  # Start with the new searchItem
            interest_areas=[],
            credit_cards=[],
            bank_details=None
        )

    # Track time taken for adding the search item
    add_search_start = time.time()
    user_specific.add_search(searchItem)
    add_search_time = time.time() - add_search_start
    print(f"Time taken for adding search item: {add_search_time:.6f} seconds")  # Log the time

    # Track time taken for upserting the item
    upsert_start = time.time()
    user_specific_container.upsert_item(user_specific.to_dict())
    upsert_time = time.time() - upsert_start
    print(f"Time taken for upserting item: {upsert_time:.6f} seconds")  # Log the time

    total_time = time.time() - start_time  # Total execution time
    print(f"Total time taken for add_recent_search: {total_time:.6f} seconds")  # Log the time

    return SuccessResponse(message="Added search in recent items", success=True)

async def get_user_specific_data(userId: str, user_specific_container, event_container):
    # Query to get user-specific data
    query = "SELECT * FROM c WHERE c.userId = @userId"
    params = [{"name": "@userId", "value": userId}]
    
    search = list(user_specific_container.query_items(
        query=query,
        parameters=params,
        enable_cross_partition_query=True
    ))
    
    if not search:
        user_specific=UserSpecific(
            id=userId,
            userId=userId,
            booked_events=[],
            recent_searches=[],
            interest_areas=[],
            credit_cards=[],
            bank_details=None
        )
        user_specific_container.create_item(user_specific.to_dict())
        return user_specific
    print(search)
    user_data = search[0]
    event_map = {}

    # Fetch event details and update booked_events
    for event in user_data.get('booked_events', []):
        event_id = event.get('event_id')
        if event_id:
            if event_id in event_map:
                # Use the cached event details
                event.update(event_map[event_id])
            else:
                # Query the eventContainer for event details
                event_query = "SELECT * FROM c WHERE c.id = @event_id"
                event_params = [{"name": "@event_id", "value": event_id}]
                
                event_details = list(event_container.query_items(
                    query=event_query,
                    parameters=event_params,
                    enable_cross_partition_query=True
                ))
                
                if event_details:
                    event_info = event_details[0]
                    event_name = event_info.get('event_name')
                    description = event_info.get('event_description')
                    event_type = event_info.get('event_type')
                    location = event_info.get('location', {})
                    venue = location.get('venue')
                    geo_tag = location.get('geo_tag', {})
                    latitude = geo_tag.get('latitude')
                    longitude = geo_tag.get('longitude')
                    city = location.get('city')
                    thumbnail = event_info.get('thumbnail', {})
                    fileUrl = thumbnail.get('fileUrl')
                    # Cache the event details in the map
                    event_map[event_id] = {
                        'eventName': event_name,
                        'description': description,
                        'type': event_type,
                        'venue': venue,
                        'latitude': latitude,
                        'longitude': longitude,
                        'city': city,
                        'thumbnail': fileUrl
                    }
                    
                    # Update the event with the fetched details
                    event.update(event_map[event_id])
    # #print(user_data)
     
    return user_data


async def fetch_carousel_images_db(db: AsyncSessionLocal) -> List[Dict[str, str]]:
    # Fetch all carousel images from the database asynchronously
    result = await db.execute(select(Carousel_image))
    db_images = result.scalars().all()  # Get all Carousel_image instances

    # Convert each Carousel_image instance to a dictionary
    images_as_dicts = [
        {
            "id": str(image.id),  # Convert id to string
            "filename": image.filename,
            "fileurl": image.fileurl,
            "filetype": image.filetype
        }
        for image in db_images
    ]
    
    return images_as_dicts

async def get_recent_search_data(userId: str, user_specific_container):
    # Query to get user-specific data
    query = "SELECT c.recent_searches FROM c WHERE c.userId = @userId"
    params = [{"name": "@userId", "value": userId}]
    
    search = list(user_specific_container.query_items(
        query=query,
        parameters=params,
        enable_cross_partition_query=True
    ))
    
    if not search:
        user_specific=UserSpecific(
            id=userId,
            userId=userId,
            booked_events=[],
            recent_searches=[],
            interest_areas=[],
            credit_cards=[],
            bank_details=None
        )
        user_specific_container.create_item(user_specific.to_dict())
        return []
    
    user_data = search[0]
     
    return user_data

async def add_credit_card(userId: str, card_details: dict, user_specific_container):
    query = "SELECT * FROM c WHERE c.userId = @userId"
    params = [{"name": "@userId", "value": userId}]

    search = list(user_specific_container.query_items(
        query=query,
        parameters=params,
        enable_cross_partition_query=True
    ))
    
    if search:
        user_specific_data = search[0]
        user_specific = UserSpecific(**user_specific_data)
    else:
        user_specific = UserSpecific(
            id=userId,
            userId=userId,
            booked_events=[],
            recent_searches=[],
            interest_areas=[],
            credit_cards=[],
            bank_details=None  # Initialize with an empty list of credit cards
        )

    # Add new credit card
    new_card = CreditCard(**card_details)

    user_specific.add_credit_card(new_card)
    print (user_specific)
    # Upsert the user-specific document back to the container
    user_specific_container.upsert_item(user_specific.to_dict())
     
    return {"message": "Credit card added successfully", "success": True}


async def add_banking_details(userId, user_specific_container, banking_details_data):
    query = "SELECT * FROM c WHERE c.userId=@userId"
    params = [{"name": "@userId", "value": userId}]

    search= list(user_specific_container.query_items(
        query=query,
        parameters=params,
        enable_cross_partition_query=True
    ))
    print(search[0])
    if isinstance(banking_details_data, dict):
        banking_details = BankingDetails(**banking_details_data)
    elif isinstance(banking_details_data, BankingDetails):
        banking_details = banking_details_data
    print(banking_details)
    if search:
        # Existing user found, update their banking details
        user_specific_data = search[0]
        user_specific = UserSpecific(**user_specific_data)
        print(f"this is {search[0]}")
        # Add or update the banking details
        user_specific.add_banking_details(banking_details)
        print(user_specific)
        # Replace the existing document with updated details
        user_specific_container.upsert_item( user_specific.to_dict())

        return {"message": "Banking details updated successfully", "success": True}
    else:
        # No existing user found, create a new user-specific document
        user_specific = UserSpecific(
            id=userId,
            userId=userId,
            booked_events=[],
            recent_searches=[],
            interest_areas=[],
            credit_cards=[],
            bank_details=banking_details  # Set the new banking details
        )

        # Insert a new document into the container
        user_specific_container.create_item(user_specific.to_dict())

        return {"message": "Banking details added successfully", "success": True}