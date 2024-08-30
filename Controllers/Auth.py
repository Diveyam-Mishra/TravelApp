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
from Database.Connection import get_db
from Controllers.OtpGen import create_otp
from datetime import timedelta
import uuid
from typing import List, Dict
from Schemas.userSpecific import UserSpecific
from Models.Files import Carousel_image

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_user(db: Session, user_id: int):
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()


def get_user_by_username(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
JWT_SECRET = settings.JWT_SECRET
ALGORITHM = settings.ALGORITHM


def get_current_user(token: str=Depends(oauth2_scheme), db: Session=Depends(get_db)):
    try:
        # Decode the token and verify its signature and expiration
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        # Query the user from the database
        user = db.query(User).filter(User.id == user_id).first()
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

async def get_current_user_optional(token: str=Depends(oauth2_scheme), db: Session=Depends(get_db)):
    try:
        # Decode the token and verify its signature and expiration
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        # Query the user from the database
        user = db.query(User).filter(User.id == user_id).first()
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

async def update_user(req: UserUpdate, db: Session, userId:str, current_user:User, user_specific_container):
    user = db.query(User).filter(User.id == userId).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # print(userId, current_user.id)
    if str(current_user.id) != str(userId):
        raise HTTPException(status_code=403, detail="You are not authorized to update this user")

    # Update the user's details with the data from req
    if req.username is not None:
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
    db.commit()

    # Optionally, you might want to refresh the instance to reflect changes
    db.refresh(user)

    return {"message": "User updated successfully", "success": True}


async def check_unique_username(username: str, db: Session) -> SuccessResponse:
    # Query to check if the username already exists
    query = db.query(User).filter(User.username == username).first()
    
    if query:
        raise HTTPException(status_code=400, detail="Username already taken")
    
    return SuccessResponse(message="Username Available", success=True)


def create_user(db: Session, user: UserCreate) -> UserResponse:
    # hashed_password = pwd_context.hash(user.password)
    db_user = User(
        email=user.email,
        username=user.username,
        # password=hashed_password,
        contact_no=user.contact_no,
        works_at=user.works_at
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def delete_user(delete_data: DeleteUserAfterCheckingPass, current_user: User, db: Session) -> SuccessResponse:
    if delete_data.password == "delete":
        deleted_user = deletedUser(email=current_user.email,
                                 username=current_user.username,
                                 works_at=current_user.works_at,
                                 contact_no=current_user.contact_no)
        x=current_user.id
        db.add(deleted_user)
        db.delete(current_user)
        avatar = db.query(Avatar).filter(Avatar.user_id ==x).first()
        db.delete(avatar)
        db.commit()
        return SuccessResponse(message="User deleted successfully", success=True)
    else:
        return SuccessResponse(message="wrong", success=True)

    
def register_user(db: Session, email: str=None, username: str=None) -> SuccessResponse:
    if (not email) and (not username):
        raise HTTPException(status_code=400, detail="Both Email and Username are required")
    
    if email:
        db_user = db.query(User).filter(User.email == email).first()
        if db_user:
            raise HTTPException(status_code=400, detail="Email already registered")
    
    if username:
        db_user = db.query(User).filter(User.username == username).first()
        if db_user:
            raise HTTPException(status_code=400, detail="Username already registered")
    
    if email:  # Assuming create_otp only needs email
        create_otp(db, email)
    
    return SuccessResponse(message="OTP sent to your email", success=True)


def login_user(login_data: UserLogin, db: Session) -> SuccessResponse:
    if not login_data.email and not login_data.username:
        raise HTTPException(status_code=400, detail="Either email or username is required")
    
    db_user = None
    user_email = None

    if login_data.email:
        db_user = db.query(User).filter(User.email == login_data.email).first()
        user_email = login_data.email

    if login_data.username and not db_user:
        db_user = db.query(User).filter(User.username == login_data.username).first()
        if db_user:
            user_email = db_user.email

    if not db_user:
        raise HTTPException(status_code=400, detail="User not found")
    
    create_otp(db, user_email)
    
    return SuccessResponse(message="OTP sent to your email", success=True)


def login_verify(login_data: UserLoginVerify, db: Session) -> SuccessResponse:
    if not login_data.email and not login_data.username:
        raise HTTPException(status_code=400, detail="Either email or username is required")
    
    if not login_data.otp:
        raise HTTPException(status_code=400, detail="OTP is required")
    
    db_user = None
    user_email = None

    if login_data.username and not login_data.email:
        db_user = db.query(User).filter(User.username == login_data.username).first()
        if not db_user:
            raise HTTPException(status_code=400, detail="User not found")
        user_email = db_user.email
    else:
        user_email = login_data.email
        db_user = db.query(User).filter(User.email == user_email).first()
        if not db_user:
            raise HTTPException(status_code=400, detail="User not found")
    
    db_otp = db.query(OTP).filter(OTP.email == user_email, OTP.otp == login_data.otp).first()
    if not db_otp or db_otp.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")

    # token_data = {"user_id": db_user.id}
    expiry_time = datetime.utcnow() + timedelta(days=30)

    # Create token data with the expiration time
    token_data = {
        'user_id': db_user.id,  # Example user ID
        'exp': expiry_time
    }

    token = jwt.encode(token_data, JWT_SECRET, algorithm="HS256")
    db.delete(db_otp)
    db.commit()
    
    return SuccessResponse(message="User logged in successfully", token=token, success=True)


def look_up_username(username:str, db: Session, current_user: User=Depends(get_current_user)):
    if current_user is None:
        raise HTTPException(status_code=400, detail="User Not Found")
    db_user = db.query(User).filter(User.username == username.username).first()
    if not db_user:
            raise HTTPException(status_code=400, detail="User not found")
    return db_user


async def add_interest_areas_to_user(userId:str, interestAreas:List[str], user_specific_container):
    query = "SELECT * FROM c where c.userId = @userId"
    params = [{"name":"@userId", "value":userId}]

    search = list(user_specific_container.query_items(query=query,
        parameters=params,
        enable_cross_partition_query=True))

    if not search:
        user_specific = UserSpecific(id=userId, userId=userId, booked_events=[], recent_searches=[], interest_areas=interestAreas)
        user_specific_container.create_item(user_specific.to_dict())
        return SuccessResponse(message="User Interest areas updated successfully", success=True)
    else:
        # Update the interest_areas if the user already exists
        user_specific = search[0]
        user_specific["interest_areas"] = interestAreas
        user_specific_container.replace_item(user_specific["id"], user_specific)
        return {"message": "User interest areas updated successfully", "success": True}


async def add_recent_search(userId, searchItem, user_specific_container):
    query = "SELECT * FROM c where c.userId = @userId"
    params = [{"name":"@userId", "value":userId}]

    search = list(user_specific_container.query_items(query=query,
        parameters=params,
        enable_cross_partition_query=True))
    
    if search:
        user_specific_data = search[0]
        user_specific = UserSpecific(**user_specific_data)
    else:
        user_specific = UserSpecific(
            id=userId,
            userId=userId,
            booked_events=[],
            recent_searches=[],  # Start with the new searchItem
            interest_areas=[]
        )
    # Update recent searches
    user_specific.add_search(searchItem)
    
    # Update the user document in the container
    user_specific_container.upsert_item(user_specific.to_dict())

    return SuccessResponse(message="Added search in recent items", success=True)
    

async def get_user_specific_data(userId: str, user_specific_container):
    query = "SELECT * FROM c WHERE c.userId = @userId"
    params = [{"name": "@userId", "value": userId}]
    
    search = list(user_specific_container.query_items(
        query=query,
        parameters=params,
        enable_cross_partition_query=True
    ))
    
    if not search:
        raise HTTPException(status_code=404, detail="User-specific data not found")
    
    return search[0]


def fetch_carousel_images_db(db: Session) -> List[Dict[str, str]]:
    # Fetch all carousel images from the database
    db_images = db.query(Carousel_image).all()
    
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