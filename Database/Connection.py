from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config import settings
import urllib

Driver = settings.Driver
Server = settings.Server
Database = settings.Database
Uid = settings.Uid
Pwd = settings.Pwd

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