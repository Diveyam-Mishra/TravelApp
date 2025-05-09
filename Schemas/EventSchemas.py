from pydantic import BaseModel,conlist, validator
from typing import List, Dict, Optional
from datetime import datetime


class GeoTag(BaseModel):
    latitude: float
    longitude: float


class Location(BaseModel):
    venue: str
    geo_tag: GeoTag
    city:str

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


class DateTimeDetails(BaseModel):
    day: int
    month: int
    year: int
    hour: int
    minute: int
    second: Optional[int] = None  # Optional field for seconds

    def to_datetime(self) -> datetime:
        """Convert the fields to a datetime object."""
        return datetime(
            year=self.year,
            month=self.month,
            day=self.day,
            hour=self.hour,
            minute=self.minute,
            second=self.second or 0  # Default to 0 if not provided
        )


class PriceDetails(BaseModel):
    standard: float
    early_bird: float
    group_rate: float


class HostDetails(BaseModel):
    id: str


class EventDetails(BaseModel):
    event_name: str
    event_description: str
    event_type: List[str]
    start_date_and_time: str  # iso
    end_date_and_time: str  # iso
    age_group: str
    family_friendly: bool
    price_fees: float 
    capacity: int
    host_information: str
    location:Location


class SuccessResponse(BaseModel):
    message: str
    success: bool
    class Config:
        extra = 'allow'


class EventDetailsupdate(BaseModel):
    event_name: Optional[str] = None
    event_description: Optional[str] = None
    event_type: Optional[List[str]] = None
    start_date_and_time: Optional[str] = None
    end_date_and_time: Optional[str] = None
    age_group: Optional[str] = None
    family_friendly: Optional[bool] = None
    price_fees: Optional[float] = None
    capacity: Optional[int] = None
    host_information: Optional[str] = None
    location:Optional[Location] = None


class EventFilter(BaseModel):
    date_preference: Optional[str] = None
    specific_date: Optional[datetime] = None
    time_preference: Optional[List[str]] = None
    location_preference: Optional[str] = None
    duration_preference: Optional[str] = None
    event_type_preference:Optional[List[str]] = None
    user_latitude: float
    user_longitude: float
    user_city: Optional[str] = None
    @validator('date_preference')
    def validate_date_preference(cls, value):
        if value is None:
            return value
        valid_strings = {"today", "tomorrow", "this week", "anytime","Today", "Tomorrow", "This week", "Anytime"}
        if value:
            if value.endswith('Z'):
                value = value[:-1]
            try:
                # Try to parse as ISO 8601 date string
                datetime.fromisoformat(value)
            except ValueError:
                # If it fails, check if it matches the allowed strings
                if value not in valid_strings:
                    raise ValueError('date_preference must be "Today", "Tomorrow","This week", "Anytime" or a valid ISO 8601 date string')
        return value

class SearchEvent(BaseModel):
    event_name: str
    event_description: str
    event_type: List[str]
    start_date_and_time: str
    end_date_and_time: str
    age_group: str
    family_friendly: bool
    price_fees: float
    capacity: int
    host_information: str
    location: Location
    id: str
    event_id: Optional[str] = None
    event_ID: Optional[str] = None
    start_date: str
    end_date: str
    duration: str
    remaining_capacity: int
    creator_id: str
    editor_access: List[str]
    
    class Config:
        extra = 'allow'


class ImageDetails(BaseModel):
    file_name: Optional[str] = None
    file_url: Optional[str] = None  # This will be base64 encoded data
    file_type: Optional[str] = None


class SearchEventResult(BaseModel):
    id:str
    name:str
    description:str
    type: List[str]
    thumbnail: Optional[ImageDetails] = None
    distance: Optional[str] = None
    location: Optional[Location] = None
    
    class Config:
        extra = 'allow'


class SearchEventResultWithCnt(BaseModel):
    cnt: int
    results: List[SearchEventResult]

class PartialName(BaseModel):
    partial_name:str


class CreatorId(BaseModel):
    creator:str

class EventIds(BaseModel):
    eventids: List[str]

class takeString(BaseModel):
    eventId:str
class strAndint(BaseModel):
    event_id:str
    image: int