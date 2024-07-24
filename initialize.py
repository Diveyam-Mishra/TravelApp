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
from fastapi.middleware.cors import CORSMiddleware
from Routes.OrganizationRoutes import router as organization_router
from Routes.Auth import router as auth_router
from Routes.forgot_password import router as forgotPassword
from Controllers.Auth import (create_user, get_user, get_current_user, get_user_by_email, get_user_by_username, settings, engine, JWT_SECRET)
from Controllers.OtpGen import create_otp
from datetime import datetime
from config import settings, connectionString
from sqlalchemy import inspect
from Database.Connection import get_db
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
app.include_router(auth_router)
app.include_router(organization_router)
app.include_router(forgotPassword)

# MongoDB setup
client = motor.motor_asyncio.AsyncIOMotorClient(settings.mongoURI)
database = client.TrabiiBackendTest
collection = database.users

# Base = declarative_base()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@app.on_event("startup")
async def startup_event():
    from Database.Connection import Base
    Base.metadata.create_all(bind=engine)


@app.get("/")
async def read_root():
    return {"Trabii Server!!"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)