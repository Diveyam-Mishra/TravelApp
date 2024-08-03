from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey
from Database.Connection import Base
from sqlalchemy.orm import relationship



class Event(Base):
    __tablename__ = 'events'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=False)
    type = Column(String, nullable=False)  # Storing as comma-separated string
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    duration = Column(Integer, nullable=False)
    age_group = Column(String, nullable=False)
    family_friendly = Column(Boolean, default=True)
    price_standard = Column(Float, nullable=False)
    price_early = Column(Float, nullable=False)
    price_group = Column(Float, nullable=False)
    max_capacity = Column(Integer, nullable=False)
    host_id = Column(Integer, ForeignKey('organizations.id'), nullable=False)  # Linking host user to event
    
    remaining_capacity = Column(Integer, nullable=False)
    creator_id = Column(Integer, nullable=False)  # Linking creator user to event
    editor_access = Column(String, nullable=True)  # Storing as comma-separated string of user IDs

    host = relationship("Organization")
    
    def get_type_list(self):
        return self.type.split(',')

    def set_type_list(self, type_list):
        self.type = ','.join(type_list)

    def get_editor_access_list(self):
        return [int(user_id) for user_id in self.editor_access.split(',')] if self.editor_access else []

    def set_editor_access_list(self, editor_access_list):
        self.editor_access = ','.join(map(str, editor_access_list))
