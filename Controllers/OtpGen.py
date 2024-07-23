import random
import string
from datetime import datetime, timedelta
from Models.user_models import OTP, User
from config import settings, connectionString
from azure.communication.email import EmailClient
import random
from Models.user_models import OTP
from Schemas.UserSchemas import OTPVerification, SuccessResponse
import jwt
from passlib.context import CryptContext
from fastapi import HTTPException
from sqlalchemy.orm import Session

JWT_SECRET = settings.JWT_SECRET
email_client = EmailClient.from_connection_string(connectionString)


sender_email = settings.sender_email
SMTP_SERVER = "smtp.gmail.com"  # For example, using Gmail's SMTP server
SMTP_PORT = 587  # Port for TLS

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def generate_otp(length=6):
    return ''.join(random.choices(string.digits, k=length))

def send_otp(email, otp):
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

    poller = email_client.begin_send(message)
    result = poller.result()
    return result



def create_otp(db, email):
    otp = generate_otp()
    expires_at = datetime.utcnow() + timedelta(minutes=5)
    db_otp = OTP(email=email, otp=otp, expires_at=expires_at)
    db.add(db_otp)
    db.commit()
    send_otp(email, otp)


def verify_otp(user: OTPVerification, db: Session) -> SuccessResponse:
    db_otp = db.query(OTP).filter(OTP.email == user.email, OTP.otp == user.otp).first()
    if not db_otp or db_otp.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")
    
    db.delete(db_otp)
    db.commit()

    hashed_password = pwd_context.hash(user.password)
    new_user = User(email=user.email, username=user.username, password=hashed_password, avatar=user.avatar, contact_no=user.contact_no, works_at=user.works_at)
    db.add(new_user)
    db.commit()
    
    token_data = {"user_id": new_user.id}
    token = jwt.encode(token_data, JWT_SECRET, algorithm="HS256")

    return SuccessResponse(message="User Created Successfully", token=token, success=True)