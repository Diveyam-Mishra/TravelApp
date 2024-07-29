from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    JWT_SECRET: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    ALGORITHM: str
    mongoURI: str
    Driver: str
    Server: str
    Database: str
    Uid: str
    Pwd: str
    endpoint: str
    accesskey:str
    sender_email: str
    COSMOS_DB_ENDPOINT: str
    COSMOS_DB_KEY : str
    DATABASE_NAME : str
    CONTAINER_NAME : str
    OPENAI_API_KEY: str


    class Config:
        env_file = ".env"

settings = Settings()
connectionString = "endpoint="+settings.endpoint+";accesskey="+settings.accesskey

