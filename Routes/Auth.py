from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from Models.user_models import  User
from Schemas.UserSchemas import SuccessResponse, EmailRequest, UserLoginVerify,UserUpdate, UserName
from Schemas.UserSchemas import UserResponse, UserCreate, DeleteUserAfterCheckingPass, OTPVerification, UserLogin
from Controllers.Auth import get_current_user, login_verify, update_user,\
    check_unique_username, add_interest_areas_to_user, add_recent_search,\
    get_user_specific_data, fetch_carousel_images_db,get_recent_search_data,add_banking_details,get_banking_details
from Database.Connection import get_db, get_user_specific_container,\
    get_container, AsyncSessionLocal,get_bank_container
from config import JWTBearer
from Controllers.Auth import (create_user, register_user, login_user,delete_user,look_up_username,add_credit_card,get_bookings)
from Controllers.OtpGen import (verify_otp)
from typing import List, Dict
from Schemas.userSpecific import UserSpecific,CreditCard
from Schemas.bankingDetails import BankingDetail
from Schemas.Files import CarouselImageResponse
import json

router = APIRouter()


@router.post("/auth/create_user/", response_model=UserResponse)
async def add_user(user: UserCreate, db: AsyncSessionLocal = Depends(get_db)):
    db_user = await create_user(db, user)  # Ensure create_user is also async
    return db_user


@router.delete("/auth/delete_user/", dependencies=[Depends(JWTBearer())],response_model=SuccessResponse)
async def delete_user_endpoint( current_user: User=Depends(get_current_user), db: AsyncSessionLocal=Depends(get_db)):
     
    return await delete_user(current_user, db)


@router.get("/auth/get_user/",dependencies=[Depends(JWTBearer())])
async def get_user_details(current_user: User=Depends(get_current_user)):
     
    # The user data is already fetched by get_current_user and assigned to current_user
    # Return user details without sensitive information
    return current_user.dict()

@router.post("/auth/check-username/", response_model=SuccessResponse)
async def check_username(username: UserName, db: AsyncSessionLocal = Depends(get_db)):
     
    return await check_unique_username(username.username, db)

@router.post("/auth/{userId}/update_non_avatar/",dependencies=[Depends(JWTBearer())], response_model=SuccessResponse)
async def update_user_details(userId:str, req:UserUpdate, db: AsyncSessionLocal=Depends(get_db), current_user: User=Depends(get_current_user), user_specific_container=Depends(get_user_specific_container)):
    if current_user is None:
        raise HTTPException(status_code=401, detail="User is not authenticated")
     
    resp = await update_user(req, db, userId, current_user, user_specific_container)
    return resp

    
@router.post("/auth/send-otp/", response_model=SuccessResponse)
async def register_user_endpoint(req: EmailRequest, db: AsyncSessionLocal=Depends(get_db)):
    return await register_user(db, req.email, req.username)


@router.post("/auth/verify-otp/", response_model=SuccessResponse)
async def verify_otp_endpoint(user: OTPVerification, db: AsyncSessionLocal=Depends(get_db)):
     
    return await verify_otp(user, db)


@router.post("/auth/login/",response_model=SuccessResponse)
async def login_user_otp(login_data: UserLogin, db: AsyncSessionLocal=Depends(get_db)):
     
    return await login_user(login_data, db)


@router.post("/auth/verify-login-otp/", response_model=SuccessResponse)
async def login_verify_otp(login_data: UserLoginVerify, db: AsyncSessionLocal=Depends(get_db)):
     
    return await login_verify(login_data, db)

@router.post("/auth/get_user_info/",dependencies=[Depends(JWTBearer())])
async def get_username_info(username: UserName,db: AsyncSessionLocal=Depends(get_db), current_user: User = Depends(get_current_user)):
     
    return await look_up_username(username,db,current_user)

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
async def get_user_specific_containers(user_specific_container=Depends(get_user_specific_container), current_user:User=Depends(get_current_user), eventContainer = Depends(get_container)):
    if current_user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    # userId = "d1b14612-db03-4311-8176-cf504d222bfb"
    userId = current_user.id
     
    resp = await get_user_specific_data(userId, user_specific_container, eventContainer)

    # #print(resp)
    return resp

@router.get("/bookings/", dependencies=[Depends(JWTBearer())])
async def get_only_bookings(user_specific_container=Depends(get_user_specific_container), current_user:User=Depends(get_current_user), eventContainer = Depends(get_container)):
    if current_user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    # userId = "d1b14612-db03-4311-8176-cf504d222bfb"
    userId = current_user.id
     
    resp = await get_bookings(userId, user_specific_container, eventContainer)

    # #print(resp)
    return resp

@router.get("/getCarouselImages", response_model=List[CarouselImageResponse])
async def fetch_carousel_images(
    db: AsyncSessionLocal = Depends(get_db),
    # redis = Depends(get_redis)
):
    # cached_images = redis.get("carousel_images")
    
    # if cached_images:
        # #print("cache hit")
        # return json.loads(cached_images)
     
    images = await fetch_carousel_images_db(db)
    
    # redis.set("carousel_images", json.dumps(images))
    
    return images
@router.get("/recent_searches/",dependencies=[Depends(JWTBearer())])
async def getRecentSearch(user_specific=Depends(get_user_specific_container), current_user:User=Depends(get_current_user)):
    if current_user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
     
    userId = current_user.id
    resp = await get_recent_search_data(userId, user_specific)
    return resp

@router.post("/add_credit_card/", dependencies=[Depends(JWTBearer())])
async def add_credit_card_route(card_details: CreditCard, user_specific=Depends(get_user_specific_container), current_user: User = Depends(get_current_user)):
    if current_user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
     
    userId = current_user.id
    resp = await add_credit_card(userId, card_details.dict(), user_specific)
    return resp

@router.post("/add_banking_details/",dependencies=[Depends(JWTBearer())])
async def banking_details(banking_details: BankingDetail, bank_container=Depends(get_bank_container),current_user:User=Depends(get_current_user)):
    if current_user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
     

    # userId = "7395e1a6-9ffd-46ff-9ef9-1068305a0b50"
    userId = current_user.id
    resp = await add_banking_details(userId, user_specific_container,banking_details)

    return resp

# @router.put("/toggle_global_state/", dependencies=[Depends(JWTBearer())])
# async def toggle_global_state(
#     bank_container=Depends(get_bank_container),
#     current_user: User = Depends(get_current_user)
# ):
#     if current_user is None:
#         raise HTTPException(status_code=401, detail="Not authenticated")
    
#     userId = current_user.id

#     resp = await toggle_global_state_controller(userId, bank_container)
#     return resp

@router.get("/get_banking_details/", dependencies=[Depends(JWTBearer())])
async def get_banking_info(
    bank_container=Depends(get_bank_container),
    current_user: User = Depends(get_current_user)
):
    if current_user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    userId = current_user.id

    resp = await get_banking_details(userId, bank_container)

    return resp