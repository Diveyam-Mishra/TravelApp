from pydantic import BaseModel
from typing import Optional
from sqlalchemy import Column, Integer, String, Float
from Database.Connection import Base

class Organization(Base):
    __tablename__ = 'organizations'
    id = Column(Integer, primary_key=True, index=True)
    org_name = Column(String, nullable=False)
    venue = Column(String, nullable=False)
    city = Column(String, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    contact_info = Column(String, nullable=False)
    bio = Column(String, nullable=True)

class GeoTag(BaseModel):
    latitude: float
    longitude: float

class Location(BaseModel):
    venue: str
    city: str
    geo_tag: GeoTag

class Organization_details(BaseModel):
    org_name: str
    location:Location
    contact_info: str
    bio: Optional[str]=""
