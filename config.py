from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    JWT_SECRET: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    ALGORITHM: str
    mongoURI: str
    sqlURI: str
    sender_password: str
    sender_email: str

    class Config:
        env_file = ".env"

settings = Settings()

