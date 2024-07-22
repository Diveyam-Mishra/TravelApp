import smtplib, ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import random
import string
from datetime import datetime, timedelta
from Models.user_models import OTP
from config import settings
from azure.communication.email import EmailClient
import random
import asyncio
from config import *

email_client = EmailClient.from_connection_string(connectionString)

sender_email = settings.sender_email
SMTP_SERVER = "smtp.gmail.com"  # For example, using Gmail's SMTP server
SMTP_PORT = 587  # Port for TLS



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


