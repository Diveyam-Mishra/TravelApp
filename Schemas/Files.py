# schemas.py
from pydantic import BaseModel

class FileUploadRequest(BaseModel):
    userID: str
    email: str

class FileUploadResponse(BaseModel):
    message: str
    success: bool
