from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, Form
from Schemas.Files import FileUploadResponse
from Schemas.UserSchemas import UserUpdate
from Database.Connection import get_db, get_container, get_file_container, get_blob_service_client
from sqlalchemy.orm import Session
from Models.user_models import User
from fastapi.responses import Response
from typing import List
from Schemas.EventSchemas import *
from Controllers.Files import avatar_upload, get_avatar, upload_event_files,\
    fetch_event_files
from Controllers.Auth import get_current_user
from typing import Optional, List
from config import JWTBearer
router = APIRouter()


@router.post("/auth/update/", dependencies=[Depends(JWTBearer())],response_model=FileUploadResponse)
async def upload_avatar(
    username: str = Form(...),
    updated_username:Optional[str]=Form(None),
    works_at: Optional[str] = Form(None),
    contact_no: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    blob_client=Depends(get_blob_service_client),
    current_user: User = Depends(get_current_user),
    file: UploadFile = File(...)
):
    if current_user is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    # Create UserUpdate instance from form data
    req = UserUpdate(username=updated_username, works_at=works_at, contact_no=contact_no)
    
    # Call the function to handle the file upload and user update
    return await avatar_upload(username, req, db, current_user, file, blob_client)


@router.get("/avatar/fetch/",dependencies=[Depends(JWTBearer())])
async def fetch_avatar(
    db: Session=Depends(get_db),
    current_user: User=Depends(get_current_user)
):
    if current_user is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return await get_avatar(current_user.id, db)


@router.post("/event/{eventId}/files/upload/",dependencies=[Depends(JWTBearer())],
response_model=FileUploadResponse)
async def upload_files(
    eventId: str,
    files: List[UploadFile] = File(...),
    event_name: Optional[str] = Form(None),
    event_description: Optional[str] = Form(None),
    event_type: Optional[List[str]] = Form(None),
    start_date_and_time: Optional[DateTimeDetails] = Form(None),
    end_date_and_time: Optional[DateTimeDetails] = Form(None),
    age_group: Optional[str] = Form(None),
    family_friendly: Optional[bool] = Form(None),
    price_fees: Optional[PriceDetails] = Form(None),
    capacity: Optional[int] = Form(None),
    host_information: Optional[HostDetails] = Form(None),
    location: Optional[Location] = Form(None),
    container=Depends(get_container),
    blob_client=Depends(get_blob_service_client),
    file_container=Depends(get_file_container),
    current_user: User = Depends(get_current_user)
):
    if current_user is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    update_info=EventDetailsupdate(
    event_name=event_name,
    event_description=event_description,
    event_type=event_type,
    start_date_and_time=start_date_and_time,
    end_date_and_time=end_date_and_time,
    age_group=age_group,
    family_friendly=family_friendly,
    price_fees=price_fees,
    capacity=capacity,
    host_information=host_information,
    location=location
)
    
    return await upload_event_files(eventId, files,update_info, current_user, container, blob_client, file_container)

@router.get("/event/{eventId}/files/",dependencies=[Depends(JWTBearer())])
async def get_event_files(
    eventId: str,
    container=Depends(get_file_container),
    current_user: User = Depends(get_current_user)
):
    if current_user is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    return await fetch_event_files(eventId, container)


# @router.post("/upload", response_model=FileUploadResponse)
# async def upload_files(
#     userID: int=Form(...),
#     email: str=Form(...),
#     files: List[UploadFile]=File(...),
#     db: Session=Depends(get_db)
# ):
#     # print(f"userID: {userID}")
#     # print(f"email: {email}")
#     # print(f"files: {[file.filename for file in files]}")
    
#     if len(files) > 5:
#         raise HTTPException(status_code=400, detail="Maximum 5 files can be uploaded at once")

#     file_columns = [
#         ('fileName1', 'fileData1', 'fileType1'),
#         ('fileName2', 'fileData2', 'fileType2'),
#         ('fileName3', 'fileData3', 'fileType3'),
#         ('fileName4', 'fileData4', 'fileType4'),
#         ('fileName5', 'fileData5', 'fileType5')
#     ]

#     existing_record = db.query(IshmtFile).filter(IshmtFile.userID == userID).first()

#     if existing_record:
#         for i, file in enumerate(files):
#             if i < len(file_columns):
#                 file_column = file_columns[i]
#                 fileName = f"{email}_{file.filename}"
#                 fileType = file.content_type
                
#                 setattr(existing_record, file_column[0], fileName)
#                 setattr(existing_record, file_column[1], await file.read())
#                 setattr(existing_record, file_column[2], fileType)

#         db.commit()
#         return {"message": "Files Updated", "success": True}
#     else:
#         new_record = IshmtFile(
#             userID=userID,
#         )

#         for i, file in enumerate(files):
#             if i < len(file_columns):
#                 file_column = file_columns[i]
#                 fileName = f"{email}_{file.filename}"
#                 fileType = file.content_type
                
#                 setattr(new_record, file_column[0], fileName)
#                 setattr(new_record, file_column[1], await file.read())
#                 setattr(new_record, file_column[2], fileType)

#         db.add(new_record)
#         db.commit()
#         return {"message": "Files Uploaded", "success": True}

# @router.get("/file/{userID}")
# async def get_files(userID: int, db: Session=Depends(get_db)):
#     file_record = db.query(IshmtFile).filter(IshmtFile.userID == userID).first()
#     if not file_record:
#         raise HTTPException(status_code=404, detail="Files not found")

#     files = []
#     for i in range(1, 6):
#         fileName = getattr(file_record, f'fileName{i}')
#         fileData = getattr(file_record, f'fileData{i}')
#         fileType = getattr(file_record, f'fileType{i}')
#         if fileName and fileData and fileType:
#             encoded_file_data = pybase64.b64encode(fileData).decode('utf-8')
#             files.append({"fileName": fileName, "fileData": encoded_file_data, "fileType": fileType})
    
#     return files
