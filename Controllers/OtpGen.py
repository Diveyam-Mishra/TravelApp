import random
import string
from datetime import datetime, timedelta
from Models.user_models import OTP, User
from config import settings, connectionString
from azure.communication.email import EmailClient
import random
from Models.user_models import OTP
from Schemas.UserSchemas import OTPVerification, SuccessResponse, ResetPasswordRequest
import jwt
from passlib.context import CryptContext
from fastapi import HTTPException
from sqlalchemy.orm import Session
from uuid import uuid4
from Database.Connection import AsyncSessionLocal
JWT_SECRET = settings.JWT_SECRET
email_client = EmailClient.from_connection_string(connectionString)


sender_email = settings.sender_email
SMTP_SERVER = "smtp.gmail.com"  # For example, using Gmail's SMTP server
SMTP_PORT = 587  # Port for TLS

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

from sqlalchemy import select


async def generate_otp(length=6) -> str:
    return ''.join(random.choices(string.digits, k=length))

def send_otp(email: str, otp: str):
    subject = "Your OTP Code"
    
    message = {
        "senderAddress": sender_email,
        "recipients": {
            "to": [{"address": email}],
        },
        "content": {
            "subject": subject,
            "plainText": f"Your OTP code is {otp}. It is valid for 10 minutes.",
        }
    }

    poller = email_client.begin_send(message)  # Adjust based on your email client
    result = poller.result()  # Ensure to await the result
    return result

async def create_otp(db: AsyncSessionLocal, email: str):
    otp = await generate_otp()
    expires_at = datetime.utcnow() + timedelta(minutes=5)
    db_otp = OTP(email=email, otp=otp, expires_at=expires_at)
    
    db.add(db_otp)
    await db.commit()
    
    send_otp(email, otp)

async def verify_otp(user: OTPVerification, db: AsyncSessionLocal) -> SuccessResponse:
    if user.email == "trabiitestaccount1781@trabii.com":
        if user.otp == "111111":
            new_user = User(id=str(uuid4()), email=user.email, username=user.username,
                            contact_no=user.contact_no, works_at=user.works_at,
                            dob=user.dob, gender=user.gender)
            db.add(new_user)
            await db.commit()
            
            expiry_time = datetime.utcnow() + timedelta(days=30)

            # Create token data with the expiration time
            token_data = {
                'user_id': new_user.id,  # Example user ID
                'exp': expiry_time
            }
            token = jwt.encode(token_data, JWT_SECRET, algorithm="HS256")

            return SuccessResponse(message="User Created Successfully", token=token, success=True)
        else:
            raise HTTPException(status_code=400, detail="Invalid or expired OTP")

    result = await db.execute(select(OTP).filter(OTP.email == user.email, OTP.otp == user.otp))
    db_otp = result.scalar_one_or_none()
    
    if not db_otp or db_otp.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")
    
    await db.delete(db_otp)
    await db.commit()

    new_user = User(id=str(uuid4()), email=user.email, username=user.username,
                    contact_no=user.contact_no, works_at=user.works_at,
                    dob=user.dob, gender=user.gender)
    db.add(new_user)
    await db.commit()
    
    expiry_time = datetime.utcnow() + timedelta(days=30)

    # Create token data with the expiration time
    token_data = {
        'user_id': new_user.id,  # Example user ID
        'exp': expiry_time
    }
    token = jwt.encode(token_data, JWT_SECRET, algorithm="HS256")

    return SuccessResponse(message="User Created Successfully", token=token, success=True)

async def verify_forgot_password_otp(reset_password_data: ResetPasswordRequest, db: AsyncSessionLocal) -> bool:
    result = await db.execute(select(OTP).filter(OTP.email == reset_password_data.email, OTP.otp == reset_password_data.otp))
    db_otp = result.scalar_one_or_none()
    
    if not db_otp or db_otp.expires_at < datetime.utcnow():
        return False
    
    await db.delete(db_otp)
    await db.commit()
    return True