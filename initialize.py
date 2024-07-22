# main.py

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
import motor.motor_asyncio
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session
from Models.user_models import User, OTP
from Schemas.UserSchemas import UserBase, UserCreate, UserLogin, UserResponse, DeleteUserAfterCheckingPass, SuccessResponse, NoSQLUser, OTPVerification
from passlib.context import CryptContext
import jwt

from Controllers.Auth import (create_user, get_user, get_current_user, get_user_by_email, get_user_by_username, settings, get_db, engine, JWT_SECRET)
from Controllers.OtpGen import create_otp
from datetime import datetime
from config import settings, connectionString
from sqlalchemy import inspect

# print(settings.sqlURI)

app = FastAPI(title="Backend with MongoDB and SQL")

origins = ['http://localhost:3000']

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB setup
client = motor.motor_asyncio.AsyncIOMotorClient(settings.mongoURI)
database = client.TrabiiBackendTest
collection = database.users

# Base = declarative_base()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# Initialize SQL database
def init_db():
    from Models.user_models import Base
    Base.metadata.create_all(bind=engine)

def table_exists(engine, table_name):
    inspector = inspect(engine)
    return inspector.has_table(table_name)

@app.on_event("startup")
async def startup_event():
    # Check if the users table exists
    init_db()
    print(settings.sender_email)


@app.get("/")
async def read_root():
    return {"Hello": "World"}


# @app.get("/api/user/{user_id}", response_model=UserResponse)
# def get_user_by_id(user_id: int, db: Session=Depends(get_db)):
#     db_user = get_user(db, user_id)
#     if db_user:
#         return db_user
#     raise HTTPException(404, f"User with ID {user_id} not found")


@app.post("/api/user/", response_model=UserResponse)
def add_user(user: UserCreate, db: Session=Depends(get_db)):
    db_user = create_user(db, user)
    return db_user


# Register a User
@app.post("/api/register/", response_model=SuccessResponse)
def register_user(email: str, db: Session=Depends(get_db)):
    db_user = get_user_by_email(db, email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    # db_user = get_user_by_username(db, user.username)
    # if db_user:
    #     raise HTTPException(status_code=400, detail="Username already registered")
    
    # Generate and send OTP
    create_otp(db, email)
    
    return {"message": "OTP sent to your email", "success": True}

@app.post("/api/verify-otp/", response_model=SuccessResponse)
def verify_otp(user: UserCreate, db: Session=Depends(get_db)):
    db_otp = db.query(OTP).filter(OTP.email == user.email, OTP.otp == user.otp).first()
    if not db_otp or db_otp.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")
    
    # Delete OTP after successful verification
    db.delete(db_otp)
    db.commit()

    # Hash the password
    hashed_password = pwd_context.hash(user.password)
    user.password = hashed_password
    
    # Create new user
    new_user = User(email=user.email, username=user.username, password=hashed_password, avatar=user.avatar, contact_no=user.contact_no, works_at=user.works_at)
    db.add(new_user)
    db.commit()
    
    # Generate JWT token
    token_data = {"user_id": new_user.id}
    token = jwt.encode(token_data, JWT_SECRET, algorithm="HS256")

    return {"message": "User Created Successfully", "token": token, "success": True}


# Authenticate a User
@app.post("/api/login", response_model=SuccessResponse)
def login_user(login_data: UserLogin, db: Session=Depends(get_db)):
    if login_data.email:
        user = get_user_by_email(db, login_data.email)
    elif login_data.username:
        user = get_user_by_username(db, login_data.username)
    else:
        raise HTTPException(status_code=400, detail="Email or username is required")

    if not user:
        return SuccessResponse(message="User Not Found", token="", success=False)

    if not pwd_context.verify(login_data.password, user.password):
        return SuccessResponse(message="Invalid Credentials", token="", success=False)

    # Generate JWT token
    token_data = {"user_id": user.id}
    token = jwt.encode(token_data, JWT_SECRET, algorithm="HS256")

    return SuccessResponse(message="User Authenticated", token=token, success=True)


@app.get("/api/getuser")
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


@app.post("/api/delete_user/")
def delete_user(delete_data: DeleteUserAfterCheckingPass, current_user: User=Depends(get_current_user), db: Session=Depends(get_db)):
    # Verify the provided password
    if not pwd_context.verify(delete_data.password, current_user.password):
        raise HTTPException(status_code=400, detail="Incorrect password")
    
    # Delete the user
    db.delete(current_user)
    db.commit()
    
    return SuccessResponse(message="User deleted sucessfully", token="", success=True)
