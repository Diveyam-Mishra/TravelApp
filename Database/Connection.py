from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config import settings
import urllib
from azure.cosmos import CosmosClient
from sqlalchemy.engine import URL
from azure.storage.blob import BlobServiceClient
import redis

# SQLAlchemy setup
Driver = settings.Driver
Server = settings.Server
Database = settings.Database
Uid = settings.Uid
SQLPwd = settings.SQLPwd

# Cosmos DB settings
COSMOS_DB_ENDPOINT = settings.COSMOS_DB_ENDPOINT
COSMOS_DB_KEY = settings.COSMOS_DB_KEY + "=="
DATABASE_NAME = settings.DATABASE_NAME 
CONTAINER_NAME = settings.CONTAINER_NAME
FILE_CONTAINER_NAME = settings.FILE_CONTAINER_NAME
ADVERTISEMENT_CONTAINER_NAME = settings.ADVERTISEMENT_CONTAINER_NAME
BOOKING_CONTAINER_NAME = settings.BOOKING_CONTAINER_NAME
USER_SPECIFIC_CONTAINER = settings.USER_SPECIFIC_CONTAINER_NAME
SUCCESSFUL_TRANSACTION_CONTAINER = settings.SUCCESSFUL_TRANSACTION_CONTAINER

# Blob Storage settings
avatar_connection_string = settings.BLOB_AVATAR_CONNECTION_STRING
avatar_container_name = settings.BLOB_CONTAINER_AVATAR_NAME
event_files_blob_container_name = settings.BLOB_CONTAINER_EVENT_FILE_NAME

# Redis settings
redis_host = settings.REDIS_HOST
redis_port = settings.REDIS_PORT
redis_password = settings.REDIS_PASSWORD

# Create the SQLAlchemy engine with connection pooling enabled
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

connection_string = f"DRIVER={Driver};SERVER={Server};DATABASE={Database};UID={Uid};PWD={SQLPwd}"
connection_url = URL.create("mssql+pyodbc", query={"odbc_connect": connection_string})

# connection_url = "sqlite:///./test.db"

engine = create_engine(
    connection_url,
    pool_size=10,          # Minimum number of connections maintained in the pool
    max_overflow=20,       # Maximum number of connections beyond the pool_size
    pool_timeout=30,       # Timeout for acquiring a connection from the pool
    pool_recycle=1800,     # Recycle connections to avoid DB timeouts (in seconds)
    echo=False,            # Set to True if you want to see SQL queries in logs (for debugging)
)

# SQLAlchemy session setup
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Initialize Cosmos DB clients and containers
client = CosmosClient(COSMOS_DB_ENDPOINT, COSMOS_DB_KEY)
database = client.get_database_client(DATABASE_NAME)
container = database.get_container_client(CONTAINER_NAME)
file_container = database.get_container_client(FILE_CONTAINER_NAME)
advertisement_container = database.get_container_client(ADVERTISEMENT_CONTAINER_NAME)
booking_container = database.get_container_client(BOOKING_CONTAINER_NAME)
user_specific_container = database.get_container_client(USER_SPECIFIC_CONTAINER)
success_transaction_container = database.get_container_client(SUCCESSFUL_TRANSACTION_CONTAINER)

# Initialize Blob Storage client
blob_service_client = BlobServiceClient.from_connection_string(avatar_connection_string)

# Dependency injection for SQLAlchemy DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Dependency injection for Cosmos DB containers
def get_container():
    yield container

def get_file_container():
    yield file_container

def get_advertisement_container():
    yield advertisement_container

def get_booking_container():
    yield booking_container

def get_user_specific_container():
    yield user_specific_container

def get_successful_transaction_container():
    yield success_transaction_container

# Dependency injection for Blob Storage client
def get_blob_service_client():
    yield blob_service_client

# Redis client initialization (using connection pooling)
# redis_pool = redis.ConnectionPool(
#     host=redis_host,
#     port=redis_port,
#     password=redis_password,
#     decode_responses=True,
#     max_connections=20  # Max number of connections to the Redis server
# )

# async def get_redis():
#     r = redis.Redis(connection_pool=redis_pool)
#     return r
