
from sqlalchemy import Column, Integer, String, Boolean, DateTime, func,Float
from sqlalchemy.ext.declarative import declarative_base


Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, index=True)
    is_admin = Column(Boolean, default=False)
    works_at = Column(String, nullable=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, index=True, nullable=False)
    password = Column(String, nullable=False)
    avatar = Column(String, nullable=True)
    contact_no = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class OTP(Base):
    __tablename__ = "otps"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, index=True)
    otp = Column(String)
    expires_at = Column(DateTime)


class Organization(Base):
    __tablename__ = 'organizations'
    id = Column(Integer, primary_key=True, index=True)
    org_name = Column(String, nullable=False)
    venue = Column(String, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    contact_info = Column(String, nullable=False)
    bio = Column(String, nullable=True)
# Pydantic models
