from pydantic_settings import BaseSettings
from fastapi.security import HTTPBearer

class JWTBearer(HTTPBearer):
    def _init_(self, auto_error: bool = True):
        super(JWTBearer, self)._init_(auto_error=auto_error)

class Settings(BaseSettings):
    JWT_SECRET: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    ALGORITHM: str
    mongoURI: str
    Driver: str
    Server: str
    Database: str
    Uid: str
    SQLPwd: str
    endpoint: str
    accesskey:str
    sender_email: str
    COSMOS_DB_ENDPOINT: str
    COSMOS_DB_KEY : str
    DATABASE_NAME : str
    CONTAINER_NAME : str
    FILE_CONTAINER_NAME: str
    ADVERTISEMENT_CONTAINER_NAME:str
    BOOKING_CONTAINER_NAME: str
    OPENAI_API_KEY: str
    BLOB_AVATAR_CONNECTION_STRING:str
    BLOB_CONTAINER_AVATAR_NAME:str
    BLOB_CONTAINER_BUGS_NAME: str
    BLOB_CONTAINER_EVENT_FILE_NAME:str
    USER_SPECIFIC_CONTAINER_NAME:str
    SUCCESSFUL_TRANSACTION_CONTAINER:str
    REDIS_HOST:str
    REDIS_PORT:str
    REDIS_PASSWORD:str
    AZURE_OPENAI_API_KEY:str
    AZURE_OPENAI_ENDPOINT:str
    AZURE_OPENAI_DEVNAME: str
    RABBIT_MQ_URI:str
    BANKING_CONTAINER_NAME:str
    RAZORPAY_KEY:str
    RAZORPAY_SECRET:str
    
    class Config:
        env_file = ".env"

settings = Settings()
connectionString = "endpoint="+settings.endpoint+";accesskey="+settings.accesskey

