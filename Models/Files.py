
from sqlalchemy import Column, Integer, String, LargeBinary, DateTime, func
from Database.Connection import Base


class Avatar(Base):
    __tablename__ = 'avatar'
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=True)
    fileurl = Column(String, nullable=True) 
    filetype = Column(String, nullable=True)
    userID = Column(Integer, unique=True, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

class Carousel_image(Base):
    __tablename__ = 'carousel_images'
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=True)
    fileurl = Column(String, nullable=True)
    filetype = Column(String, nullable=True)

class EventFiles(Base):
    __tablename__ = 'event_files'

    id = Column(Integer, primary_key=True, index=True)
    fileName1 = Column(String, nullable=True)
    fileData1 = Column(LargeBinary, nullable=True)
    fileType1 = Column(String, nullable=True)  
    fileName2 = Column(String, nullable=True)
    fileData2 = Column(LargeBinary, nullable=True)
    fileType2 = Column(String, nullable=True)  
    fileName3 = Column(String, nullable=True)
    fileData3 = Column(LargeBinary, nullable=True)
    fileType3 = Column(String, nullable=True)  
    fileName4 = Column(String, nullable=True)
    fileData4 = Column(LargeBinary, nullable=True)
    fileType4 = Column(String, nullable=True)  
    fileName5 = Column(String, nullable=True)
    fileData5 = Column(LargeBinary, nullable=True)
    fileType5 = Column(String, nullable=True)  
    
    event_ID = Column(Integer, unique=True, nullable=False)
    date = Column(DateTime, default=func.now())
