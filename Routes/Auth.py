from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from Models.user_models import  User
from Schemas.UserSchemas import SuccessResponse, EmailRequest, UserLoginVerify,UserUpdate, UserName
from Schemas.UserSchemas import UserResponse, UserCreate, DeleteUserAfterCheckingPass, OTPVerification, UserLogin
from Controllers.Auth import get_current_user, login_verify, update_user,\
    check_unique_username, add_interest_areas_to_user, add_recent_search,\
    get_user_specific_data, fetch_carousel_images_db
from Database.Connection import get_db, get_user_specific_container
from config import JWTBearer
from Controllers.Auth import (create_user, register_user, login_user,delete_user,look_up_username)
from Controllers.OtpGen import (verify_otp)
from typing import List, Dict
from Schemas.userSpecific import UserSpecific
from Schemas.Files import CarouselImageResponse
from Database.Connection import get_redis
import json

router = APIRouter()


@router.post("/auth/create_user/", response_model=UserResponse)
def add_user(user: UserCreate, db: Session=Depends(get_db)):
    db_user = create_user(db, user)
    return db_user


@router.post("/auth/delete_user/", dependencies=[Depends(JWTBearer())],response_model=SuccessResponse)
def delete_user_endpoint(delete_data: DeleteUserAfterCheckingPass, current_user: User=Depends(get_current_user), db: Session=Depends(get_db)):
    return delete_user(delete_data, current_user, db)


@router.get("/auth/get_user/",dependencies=[Depends(JWTBearer())])
def get_user_details(current_user: User=Depends(get_current_user)):
    # The user data is already fetched by get_current_user and assigned to current_user
    # Return user details without sensitive information
    user_data = {
        "id": current_user.id,
        "email": current_user.email,
        "username": current_user.username,
        "is_admin": current_user.is_admin,
        "works_at": current_user.works_at,
        "contact_no": current_user.contact_no,
        "dob": current_user.dob,
        "gender":current_user.gender,
        "created_at": current_user.created_at
    }
    return user_data

@router.post("/auth/check-username/", response_model=SuccessResponse)
async def check_username(username: UserName, db: Session = Depends(get_db)):
    return await check_unique_username(username.username, db)

@router.post("/auth/{userId}/update_non_avatar/",dependencies=[Depends(JWTBearer())], response_model=SuccessResponse)
async def update_user_details(userId:str, req:UserUpdate, db: Session=Depends(get_db), current_user: User=Depends(get_current_user), user_specific_container=Depends(get_user_specific_container)):
    if current_user is None:
        raise HTTPException(status_code=401, detail="User is not authenticated")
    resp = await update_user(req, db, userId, current_user, user_specific_container)
    return resp

    
@router.post("/auth/send-otp/", response_model=SuccessResponse)
def register_user_endpoint(req: EmailRequest, db: Session=Depends(get_db)):
    return register_user(db, req.email, req.username)


@router.post("/auth/verify-otp/", response_model=SuccessResponse)
def verify_otp_endpoint(user: OTPVerification, db: Session=Depends(get_db)):
    return verify_otp(user, db)


@router.post("/auth/login/",response_model=SuccessResponse)
def login_user_otp(login_data: UserLogin, db: Session=Depends(get_db)):
    return login_user(login_data, db)


@router.post("/auth/verify-login-otp/", response_model=SuccessResponse)
def login_verify_otp(login_data: UserLoginVerify, db: Session=Depends(get_db)):
    return login_verify(login_data, db)

@router.post("/auth/get_user_info/",dependencies=[Depends(JWTBearer())])
def get_username_info(username: UserName,db: Session=Depends(get_db), current_user: User = Depends(get_current_user)):
    return look_up_username(username,db,current_user)

@router.post("/auth/add_interest_areas/", dependencies=[Depends(JWTBearer())],response_model=SuccessResponse)
async def add_interest_areas(interestAreas: List[str], user_specific_container=Depends(get_user_specific_container), current_user: User=Depends(get_current_user)):
    if current_user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    userId = current_user.id
    resp = await add_interest_areas_to_user(userId, interestAreas, user_specific_container)
    return resp

@router.post("/add_recent_search/", dependencies=[Depends(JWTBearer())], response_model=SuccessResponse)
async def addRecentSearch(searchItem:str=Body(...), user_specific_container=Depends(get_user_specific_container), current_user: User=Depends(get_current_user)):
    if current_user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    userId = current_user.id
    resp = await add_recent_search(userId, searchItem, user_specific_container)
    return resp

@router.get("/userSpecific/", dependencies=[Depends(JWTBearer())], response_model=UserSpecific)
async def get_user_specific_container(user_specific_container=Depends(get_user_specific_container), current_user:User=Depends(get_current_user)):
    if current_user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    userId = current_user.id
    resp = await get_user_specific_data(userId, user_specific_container)
    return resp

@router.get("/getCarouselImages", response_model=List[CarouselImageResponse])
async def fetch_carousel_images(
    db: Session = Depends(get_db),
    # redis = Depends(get_redis)
):
    # cached_images = redis.get("carousel_images")
    
    # if cached_images:
        # print("cache hit")
        # return json.loads(cached_images)
    
    images = fetch_carousel_images_db(db)
    
    # redis.set("carousel_images", json.dumps(images))
    
    return images
