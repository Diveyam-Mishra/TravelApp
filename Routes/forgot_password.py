from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from Schemas.UserSchemas import SuccessResponse, ForgotPasswordRequest, ResetPasswordRequest
from Models.user_models import User
from sqlalchemy.orm import Session
from Models.user_models import User
from Schemas.UserSchemas import *
from Database.Connection import get_db
from Controllers.OtpGen import create_otp,verify_forgot_password_otp
from Controllers.Auth import pwd_context

router = APIRouter()

@router.post("/auth/forgot-password/", response_model=SuccessResponse)
def forgot_password_endpoint(forgot_password_data: ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == forgot_password_data.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="No user found with this email")
    
    create_otp(db, forgot_password_data.email)
    return SuccessResponse(message="OTP sent successfully", success=True)

@router.post("/auth/reset-password/", response_model=SuccessResponse)
def reset_password_endpoint(reset_password_data: ResetPasswordRequest, db: Session = Depends(get_db)):
    success = verify_forgot_password_otp(reset_password_data, db)
    if not success:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")
    
    user = db.query(User).filter(User.email == reset_password_data.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    hashed_password = pwd_context.hash(reset_password_data.new_password)
    user.password = hashed_password
    db.commit()
    
    return SuccessResponse(message="Password reset successfully", success=True)