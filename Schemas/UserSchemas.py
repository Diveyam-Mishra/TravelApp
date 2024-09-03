from pydantic import BaseModel
from typing import Optional, List
from pydantic import BaseModel, EmailStr
from datetime import datetime , date


class UserBase(BaseModel):
    email: str
    username: str
    # password: str
    is_admin: Optional[bool] = False
    works_at: Optional[str] = None
    contact_no: Optional[str] = None


class UserResponse(BaseModel):
    email: EmailStr
    username: str
    is_admin: bool
    works_at: Optional[str]
    contact_no: Optional[str]
    created_at: datetime
    id: str

    class Config:
        orm_mode = True


class UserCreate(BaseModel):
    email: EmailStr
    username: str
    # password: str
    is_admin: Optional[bool] = False
    works_at: Optional[str] = None
    contact_no: Optional[str] = None
    otp: Optional[str] = None

class UserUpdate(BaseModel):
    username: Optional[str] = None
    works_at: Optional[str] = None
    contact_no: Optional[str] = None
    interestAreas: Optional[List[str]] = None
    gender : Optional[str] = None
    dob : Optional[date] = None

class UserLogin(BaseModel):
    email: Optional[str] = None
    username: Optional[str] = None
    # password: str

class UserName(BaseModel):
    username: str

class UserLoginVerify(BaseModel):
    email: Optional[str] = None
    username: Optional[str] = None
    otp: Optional[str] = None

class UserId(BaseModel):
    userid: str

class SuccessResponse(BaseModel):
    message: str
    token: Optional[str] = ""
    success: bool

    class Config:
        orm_mode = True


class DeleteUserAfterCheckingPass(BaseModel):
    password: str


class NoSQLUser(BaseModel):
    id: str
    personality_tags: Optional[str] = None
    cost: Optional[float] = None
    range: Optional[str] = None
    friends: List[str] = []

class UserWithAvatar(BaseModel):
    id: str
    email: str
    username: str
    is_admin: bool
    works_at: Optional[str]
    contact_no: Optional[str]
    dob: Optional[datetime]
    gender: Optional[str]
    created_at: datetime
    avatar_url: Optional[str] = None


class OTPVerification(BaseModel):
    email: str
    otp: str
    username: str
    # password: str
    contact_no: str
    works_at:str
    dob: date
    gender:str

class EmailRequest(BaseModel):
    email: Optional[str]
    username: Optional[str]


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    email: str
    otp: str
    new_password: str

class CheckUsername(BaseModel):
    username:str