from typing import Optional
from sqlalchemy import Column, Integer, String, Float, ARRAY, DateTime, Boolean
from Database.Connection import Base



class Event(Base):
    __tablename__ = 'events'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=False)
    type = Column(String, nullable=False)  # Storing as comma-separated string
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    duration = Column(String, nullable=False)
    age_group = Column(String, nullable=False)
    family_friendly = Column(Boolean, default=True)
    price_standard = Column(Float, nullable=False)
    price_early = Column(Float, nullable=False)
    price_group = Column(Float, nullable=False)
    max_capacity = Column(Integer, nullable=False)
    host_id = Column(Integer, nullable=False)  # Linking host user to event
    media_files = Column(String, nullable=True)  # Storing as comma-separated string
    remaining_capacity = Column(Integer, nullable=False)
    creator_id = Column(Integer, nullable=False) #Linking creator user to event
    
    def get_type_list(self):
        return self.type.split(',')

    def set_type_list(self, type_list):
        self.type = ','.join(type_list)

    def get_media_files_list(self):
        return self.media_files.split(',') if self.media_files else []

    def set_media_files_list(self, media_files_list):
        self.media_files = ','.join(media_files_list)