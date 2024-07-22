import smtplib, ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import random
import string
from datetime import datetime, timedelta
from Models.user_models import OTP
from config import settings


sender_email = settings.sender_email
password = settings.sender_password
SMTP_SERVER = "smtp.gmail.com"  # For example, using Gmail's SMTP server
SMTP_PORT = 587  # Port for TLS



def generate_otp(length=6):
    return ''.join(random.choices(string.digits, k=length))

def send_otp(email, otp):
    subject = "Your OTP Code"
    body = f"Your OTP code is {otp}. It is valid for 5 minutes."
    
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = email
    msg['Subject'] = subject
    
    msg.attach(MIMEText(body, 'plain'))
    
    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(sender_email, password)
        server.sendmail(sender_email, email, msg.as_string())
        server.close()
        
        print(f"OTP sent to {email}")
    except Exception as e:
        print(f"Failed to send OTP to {email}: {e}")



def create_otp(db, email):
    otp = generate_otp()
    expires_at = datetime.utcnow() + timedelta(minutes=5)
    db_otp = OTP(email=email, otp=otp, expires_at=expires_at)
    db.add(db_otp)
    db.commit()
    send_otp(email, otp)


