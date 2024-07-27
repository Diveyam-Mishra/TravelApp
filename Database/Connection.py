from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config import settings
import urllib
from azure.cosmos import CosmosClient, exceptions

Driver = settings.Driver
Server = settings.Server
Database = settings.Database
Uid = settings.Uid
Pwd = settings.Pwd

COSMOS_DB_ENDPOINT = settings.COSMOS_DB_ENDPOINT
COSMOS_DB_KEY = settings.COSMOS_DB_KEY+"=="
DATABASE_NAME =settings.DATABASE_NAME 
CONTAINER_NAME = settings.CONTAINER_NAME

client = CosmosClient(COSMOS_DB_ENDPOINT, COSMOS_DB_KEY)
database = client.get_database_client(DATABASE_NAME)
container = database.get_container_client(CONTAINER_NAME)
params = urllib.parse.quote_plus(
    f'Driver={Driver};'
    f'Server={Server};'
    f'Database={Database};'
    f'Uid={Uid};'
    f'Pwd={Pwd};'
    'Encrypt=yes;'
    'TrustServerCertificate=no;'
    'Connection Timeout=30;'
)

# Construct the connection string
conn_str = f'mssql+pyodbc:///?odbc_connect={params}'

engine = create_engine(conn_str, echo=True)
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