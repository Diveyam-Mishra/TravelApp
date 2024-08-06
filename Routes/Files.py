from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, Form
from Schemas.Files import FileUploadResponse
from Schemas.UserSchemas import UserUpdate
from Database.Connection import get_db, get_container, get_file_container
from sqlalchemy.orm import Session
from Models.user_models import User
from fastapi.responses import Response
from typing import List
from Controllers.Files import avatar_upload, get_avatar, upload_event_files,\
    fetch_event_files
from Controllers.Auth import get_current_user
from typing import Optional, List
router = APIRouter()


@router.post("/auth/update", response_model=FileUploadResponse)
async def upload_avatar(
    username: str = Form(...),
    updated_username:Optional[str]=Form(None),
    works_at: Optional[str] = Form(None),
    contact_no: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    file: UploadFile = File(...)
):
    if current_user is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    # Create UserUpdate instance from form data
    req = UserUpdate(username=updated_username, works_at=works_at, contact_no=contact_no)
    
    # Call the function to handle the file upload and user update
    return await avatar_upload(username, req, db, current_user, file)


@router.get("/avatar/fetch/{userID}")
async def fetch_avatar(
    userID: int,
    db: Session=Depends(get_db),
    current_user: User=Depends(get_current_user)
):
    if current_user is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return await get_avatar(userID, db)


@router.post("/event/{eventId}/files/upload",
response_model=FileUploadResponse)
async def upload_files(
    eventId: str,
    files: List[UploadFile] = File(...),
    container=Depends(get_container),
    fileContainer=Depends(get_file_container),
    current_user: User = Depends(get_current_user)
):
    if current_user is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    return await upload_event_files(eventId, files, current_user, container, fileContainer)

@router.get("/event/{eventId}/files")
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
