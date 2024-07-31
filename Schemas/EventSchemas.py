from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

# class GeoTag(BaseModel):
#     latitude: float
#     longitude: float

# class Location(BaseModel):
#     venue: str
#     geo_tag: GeoTag

# class PriceFees(BaseModel):
#     standard: float
#     early_bird: float
#     group_rate: float

# class DateTimeRange(BaseModel):
#     start: datetime
#     end: datetime

# class HostInformation(BaseModel):
#     id: Optional[str] = Field(None, alias='_id')
#     name: str
#     contact_details: str
#     bio: str

# class EventDetails(BaseModel):
#     event_name: str
#     event_description: str
#     event_type: List[str]
#     date_and_time: DateTimeRange
#     duration: str
#     age_group: str
#     family_friendly: bool
#     price_fees: PriceFees
#     capacity: int
#     host_information: HostInformation
#     media_files: Optional[List[str]] = [] 

# class EventSchema(BaseModel):
#     id: Optional[str] = Field(None, alias='_id')
#     event_ID: str
#     created_at: datetime
#     updated_at: datetime
#     title: str
#     date: datetime
#     location: Location
#     popularity: int
#     event_details: EventDetails


class EventDetails(BaseModel):
    event_name: str
    event_description: str
    event_type: List[str]
    date_and_time: str
    duration: str
    age_group: str
    family_friendly: bool
    price_fees: 'PriceDetails'
    capacity: int
    host_information: 'HostDetails'
    media_files: List[str]

class DateTimeDetails(BaseModel):
    start: datetime
    end: datetime

class PriceDetails(BaseModel):
    standard: float
    early_bird: float
    group_rate: float

class HostDetails(BaseModel):
    id: int

class SuccessResponse(BaseModel):
    message: str
    success: bool

class EventDetailsupdate(BaseModel):
    id: str
    event_name: str
    event_description: str
    event_type: List[str]
    date_and_time: str
    duration: str
    age_group: str
    family_friendly: bool
    price_fees: 'PriceDetails'
    capacity: int
    host_information: 'HostDetails'
    media_files: List[str]

class EventFilter(BaseModel):
    date_preference: Optional[str] = None
    specific_date: Optional[datetime] = None
    time_preference: Optional[List[str]] = None
    location_preference: Optional[str] = None
    duration_preference: Optional[str] = None
    user_latitude: float
    user_longitude: float
    user_city: str