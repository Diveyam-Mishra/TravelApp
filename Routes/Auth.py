from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from Models.user_models import  User
from Schemas.UserSchemas import SuccessResponse, EmailRequest
from Schemas.UserSchemas import UserResponse, UserCreate, DeleteUserAfterCheckingPass, OTPVerification, UserLogin
from Controllers.Auth import get_current_user
from Database.Connection import get_db

from Controllers.Auth import (create_user, delete_user, register_user, login_user)
from Controllers.OtpGen import (verify_otp)

router = APIRouter()

@router.post("/auth/create_user/", response_model=UserResponse)
def add_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = create_user(db, user)
    return db_user

@router.post("/auth/delete_user/", response_model=SuccessResponse)
def delete_user_endpoint(delete_data: DeleteUserAfterCheckingPass, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return delete_user(delete_data, current_user, db)

@router.get("/auth/getuser")
def get_user_details(current_user: User=Depends(get_current_user)):
    # The user data is already fetched by get_current_user and assigned to current_user
    # Return user details without sensitive information
    user_data = {
        "id": current_user.id,
        "email": current_user.email,
        "username": current_user.username,
        "is_admin": current_user.is_admin,
        "works_at": current_user.works_at,
        "avatar": current_user.avatar,
        "contact_no": current_user.contact_no,
        "created_at": current_user.created_at
    }
    return user_data

@router.post("/auth/send-otp/", response_model=SuccessResponse)
def register_user_endpoint(req: EmailRequest, db: Session = Depends(get_db)):
    return register_user(req.email, db)

@router.post("/auth/verify-otp/", response_model=SuccessResponse)
def verify_otp_endpoint(user: OTPVerification, db: Session = Depends(get_db)):
    return verify_otp(user, db)

@router.post("/auth/login", response_model=SuccessResponse)
def login_user_endpoint(login_data: UserLogin, db: Session = Depends(get_db)):
    return login_user(login_data, db)