
from sqlalchemy import Column, Integer, String, Boolean, DateTime, func

from Database.Connection import Base

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, index=True)
    is_admin = Column(Boolean, default=False)
    works_at = Column(String(255), nullable=True)  # Added length constraint
    email = Column(String(255), unique=True, index=True, nullable=False)  # Added length constraint
    username = Column(String(255), index=True, nullable=False)  # Added length constraint
    # password = Column(String(255), nullable=False)  # Added length constraint
    contact_no = Column(String(20), nullable=True)  # Considered a fixed length
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class OTP(Base):
    __tablename__ = "otps"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), index=True)  # Added length constraint
    otp = Column(String(10))  # Optional: specify length for OTP
    expires_at = Column(DateTime)
# Pydantic models

class deletedUser(Base):
    __tablename__='deletedUser'
    id = Column(Integer, primary_key=True, index=True)
    works_at = Column(String(255), nullable=True)  
    email = Column(String(255), index=True, nullable=False)  
    username = Column(String(255), index=True, nullable=False)
    contact_no = Column(String(20), nullable=True)