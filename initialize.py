# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import motor.motor_asyncio
from passlib.context import CryptContext
from fastapi.middleware.cors import CORSMiddleware
from Routes.OrganizationRoutes import router as organization_router
from Routes.Auth import router as auth_router
from Controllers.Auth import (settings, engine)
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
