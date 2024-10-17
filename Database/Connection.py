from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config import settings
from sqlalchemy.engine import URL
from azure.cosmos import CosmosClient
from azure.storage.blob import BlobServiceClient
import redis

# SQLAlchemy async setup
Driver = settings.Driver
Server =  settings.Server
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
BUGS_CONTAINER = settings.BLOB_CONTAINER_BUGS_NAME

# Blob Storage settings
avatar_connection_string = settings.BLOB_AVATAR_CONNECTION_STRING
avatar_container_name = settings.BLOB_CONTAINER_AVATAR_NAME
event_files_blob_container_name = settings.BLOB_CONTAINER_EVENT_FILE_NAME
bug_file_container_name = settings.BLOB_CONTAINER_BUGS_NAME

# Redis settings
redis_host = settings.REDIS_HOST
redis_port = settings.REDIS_PORT
redis_password = settings.REDIS_PASSWORD

# Create the async SQLAlchemy engine with connection pooling enabled
connection_string = f"Driver={Driver};Server={Server};Database={Database};Uid={Uid};Pwd={SQLPwd};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"
connection_url = URL.create("mssql+aioodbc", query={"odbc_connect": connection_string})

# print(connection_url)

# Use the async SQLite URL for local testing (replace with appropriate async driver for your DB)
# For example, for PostgreSQL, use `postgresql+asyncpg://...`
# connection_url = "sqlite+aiosqlite:///./test.db"  # Example for SQLite with async

# Create the async engine
engine = create_async_engine(
    connection_url,
    echo=False,  # This is optional and enables SQL query logging
    future=True  # Optional: Enables the 2.0 style API
)

# SQLAlchemy async session setup
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Prevent session from expiring objects after commit
    autocommit=False,
    autoflush=False,
)

Base = declarative_base()

# Initialize Cosmos DB clients and containers (no need to change these as CosmosClient doesn't support asyncio natively)
client = CosmosClient(COSMOS_DB_ENDPOINT, COSMOS_DB_KEY)
database = client.get_database_client(DATABASE_NAME)
container = database.get_container_client(CONTAINER_NAME)
file_container = database.get_container_client(FILE_CONTAINER_NAME)
advertisement_container = database.get_container_client(ADVERTISEMENT_CONTAINER_NAME)
booking_container = database.get_container_client(BOOKING_CONTAINER_NAME)
user_specific_container = database.get_container_client(USER_SPECIFIC_CONTAINER)
success_transaction_container = database.get_container_client(SUCCESSFUL_TRANSACTION_CONTAINER)
bugs_container = database.get_container_client(BUGS_CONTAINER)

# Initialize Blob Storage client (no change needed here)
blob_service_client = BlobServiceClient.from_connection_string(avatar_connection_string)

# Dependency injection for async SQLAlchemy DB session
async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session

# Dependency injection for Cosmos DB containers (no need to change these as CosmosClient doesn't support asyncio natively)
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

def get_bugs_container():
    yield bugs_container

# Redis client initialization (optional if using Redis)
# You can initialize a Redis async client using `aioredis` for asynchronous Redis access:
# import aioredis
# async def get_redis():
#     redis = await aioredis.create_redis_pool(
#         f"redis://{redis_host}:{redis_port}",
#         password=redis_password,
#         maxsize=20
#     )
#     return redis
