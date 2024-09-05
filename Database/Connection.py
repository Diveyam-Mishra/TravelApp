from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config import settings
import urllib
from azure.cosmos import CosmosClient
from sqlalchemy.engine import URL
from azure.storage.blob import BlobServiceClient # type: ignore

Driver = settings.Driver
Server = settings.Server
Database = settings.Database
Uid = settings.Uid
SQLPwd = settings.SQLPwd

COSMOS_DB_ENDPOINT = settings.COSMOS_DB_ENDPOINT
COSMOS_DB_KEY = settings.COSMOS_DB_KEY + "=="
DATABASE_NAME = settings.DATABASE_NAME 
CONTAINER_NAME = settings.CONTAINER_NAME
FILE_CONTAINER_NAME = settings.FILE_CONTAINER_NAME
ADVERTISEMENT_CONTAINER_NAME=settings.ADVERTISEMENT_CONTAINER_NAME
BOOKING_CONTAINER_NAME = settings.BOOKING_CONTAINER_NAME
avatar_connection_string=settings.BLOB_AVATAR_CONNECTION_STRING
avatar_container_name=settings.BLOB_CONTAINER_AVATAR_NAME
event_files_blob_container_name=settings.BLOB_CONTAINER_EVENT_FILE_NAME
USER_SPECIFIC_CONTAINER=settings.USER_SPECIFIC_CONTAINER_NAME
SUCCESSFUL_TRANSACTION_CONTAINER=settings.SUCCESSFUL_TRANSACTION_CONTAINER

client = CosmosClient(COSMOS_DB_ENDPOINT, COSMOS_DB_KEY)
database = client.get_database_client(DATABASE_NAME)
container = database.get_container_client(CONTAINER_NAME)
file_container = database.get_container_client(FILE_CONTAINER_NAME)
advertisement_container=database.get_container_client(ADVERTISEMENT_CONTAINER_NAME)
booking_container = database.get_container_client(BOOKING_CONTAINER_NAME)
user_specific_container=database.get_container_client(USER_SPECIFIC_CONTAINER)
success_transaction_container=database.get_container_client(SUCCESSFUL_TRANSACTION_CONTAINER)

blob_service_client = BlobServiceClient.from_connection_string(avatar_connection_string)

params = urllib.parse.quote_plus(
    f'Driver={Driver};'
    f'Server={Server};'
    f'Database={Database};'
    f'Uid={Uid};'
    f'Pwd={SQLPwd};'
    'Encrypt=yes;'
    'TrustServerCertificate=no;'
    'Connection Timeout=30;'
)

# Construct the connection string
conn_str = f'mssql+pyodbc:///?odbc_connect={params}'

connection_string = f"DRIVER={Driver};SERVER={Server};DATABASE={Database};UID={Uid};PWD={SQLPwd}"
connection_url = URL.create("mssql+pyodbc", query={"odbc_connect": connection_string})

#connection_url = "sqlite:///./test.db"

engine = create_engine(connection_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_container():
    try:
        yield container
    finally:
        pass 


def get_file_container():
    try:
        yield file_container
    finally:
        pass

def get_advertisement_container():
    try:
        yield advertisement_container
    finally:
        pass
def get_booking_container():
    try:
        yield booking_container
    finally:
        pass


def get_blob_service_client():
    try:
        yield blob_service_client
    finally:
        pass

def get_user_specific_container():
    try:
        yield user_specific_container
    finally:
        pass

def get_successful_transaction_container():
    try:
        yield success_transaction_container
    finally:
        pass

import redis # type: ignore

redis_host = settings.REDIS_HOST
redis_port = settings.REDIS_PORT
redis_password = settings.REDIS_PASSWORD

async def get_redis():
    r = redis.Redis(
        host=redis_host,
        port=redis_port,
        password=redis_password,
        decode_responses=True  # Decode responses from bytes to strings
    )
    return r