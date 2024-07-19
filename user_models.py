from sqlalchemy import Column, Integer, String, Boolean, DateTime 
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func #forsql
# for NOSQL
from pydantic import BaseModel 
from typing import List, Optional
Base = declarative_base()
class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, index=True)
    is_admin = Column(Boolean, default=False)
    works_at = Column(String, nullable=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=False, index=True, nullable=False)
    password = Column(String, nullable=False)
    avatar = Column(String, nullable=True)
    contact_no = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class NoSQLUser(BaseModel):
    id: int
    personality_tags: Optional[str] = None
    cost: Optional[float] = None
    range: Optional[str] = None
    friends: List[int] = []
