# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import motor.motor_asyncio
from passlib.context import CryptContext
from fastapi.middleware.cors import CORSMiddleware
from Routes.OrganizationRoutes import router as organization_router
from Routes.Auth import router as auth_router
# from Controllers.Auth import (settings, engine)
from Database.Connection import engine
from config import settings
from Routes.forgot_password import router as forgot_password
from Routes.EventRoutes import router as events
from Routes.AiInteract import router as AiInteract
from Routes.Files import router as FileRouter
from Routes.Fiters import router as FilterRouter
from Routes.Payments import router as PaymentRouter
from Routes.admin.promotionImages import router as adminImageRouter
from sqlalchemy import MetaData
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
app.include_router(adminImageRouter, tags=["Admin - File Management"])
app.include_router(auth_router, tags=["Authentication"])
app.include_router(organization_router, tags=["Organizations"])
app.include_router(forgot_password, tags=["Forgot Password"])
app.include_router(events, tags=["Events"])
app.include_router(AiInteract, tags=["AI Interaction"])
app.include_router(FileRouter, tags=["File Management"])
app.include_router(FilterRouter, tags=["Filters"])
app.include_router(PaymentRouter, tags=["Payments"])

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

    metadata = MetaData()
    metadata.reflect(bind=engine)


@app.get("/")
async def read_root():
    return {"Trabii Server!!"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
