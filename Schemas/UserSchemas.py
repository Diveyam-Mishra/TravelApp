from pydantic import BaseModel
from typing import Optional, List
from pydantic import BaseModel, EmailStr
from datetime import datetime


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
    id: int

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
    userid: int

class SuccessResponse(BaseModel):
    message: str
    token: Optional[str] = ""
    success: bool

    class Config:
        orm_mode = True


class DeleteUserAfterCheckingPass(BaseModel):
    password: str


class NoSQLUser(BaseModel):
    id: int
    personality_tags: Optional[str] = None
    cost: Optional[float] = None
    range: Optional[str] = None
    friends: List[int] = []


class OTPVerification(BaseModel):
    email: str
    otp: str
    username: str
    # password: str
    contact_no: str
    works_at:str


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