from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from Models.user_models import  User
from Schemas.UserSchemas import SuccessResponse, EmailRequest, UserLoginVerify,UserUpdate, UserName
from Schemas.UserSchemas import UserResponse, UserCreate, DeleteUserAfterCheckingPass, OTPVerification, UserLogin
from Controllers.Auth import get_current_user, login_verify, update_user,\
    check_unique_username
from Database.Connection import get_db

from Controllers.Auth import (create_user, register_user, login_user,delete_user,look_up_username)
from Controllers.OtpGen import (verify_otp)

router = APIRouter()


@router.post("/auth/create_user/", response_model=UserResponse)
def add_user(user: UserCreate, db: Session=Depends(get_db)):
    db_user = create_user(db, user)
    return db_user


@router.post("/auth/delete_user/", response_model=SuccessResponse)
def delete_user_endpoint(delete_data: DeleteUserAfterCheckingPass, current_user: User=Depends(get_current_user), db: Session=Depends(get_db)):
    return delete_user(delete_data, current_user, db)


@router.get("/auth/get_user")
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
        "created_at": current_user.created_at
    }
    return user_data

@router.post("/auth/check-username", response_model=SuccessResponse)
async def check_username(username: UserName, db: Session = Depends(get_db)):
    return await check_unique_username(username.username, db)

@router.post("/auth/{userId}/update", response_model=SuccessResponse)
def update_user_details(userId:int, req:UserUpdate, db: Session=Depends(get_db), current_user: User=Depends(get_current_user)):
    if current_user is None:
        raise HTTPException(status_code=401, detail="User is not authenticated")
    return update_user(req, db, userId, current_user)

@router.post("/auth/send-otp/", response_model=SuccessResponse)
def register_user_endpoint(req: EmailRequest, db: Session=Depends(get_db)):
    return register_user(db, req.email, req.username)


@router.post("/auth/verify-otp/", response_model=SuccessResponse)
def verify_otp_endpoint(user: OTPVerification, db: Session=Depends(get_db)):
    return verify_otp(user, db)


@router.post("/auth/login/", response_model=SuccessResponse)
def login_user_otp(login_data: UserLogin, db: Session=Depends(get_db)):
    return login_user(login_data, db)


@router.post("/auth/verify-login-otp/", response_model=SuccessResponse)
def login_verify_otp(login_data: UserLoginVerify, db: Session=Depends(get_db)):
    return login_verify(login_data, db)
@router.post("/auth/get_user_info/")
def get_username_info(username: UserName,db: Session=Depends(get_db)):
    return look_up_username(username,db)