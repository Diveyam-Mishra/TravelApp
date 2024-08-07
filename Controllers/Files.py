from fastapi import UploadFile, HTTPException
from sqlalchemy.orm import Session
from Database.Connection import get_db
from Models.user_models import User
from Models.Files import Avatar
import pybase64 # type: ignore
from uuid import uuid4
from Controllers.Auth import get_current_user
from typing import Dict, List
from Schemas.UserSchemas import *
from Schemas.EventSchemas import EventDetailsupdate
MAX_FILE_SIZE_MB = 5  # Maximum file size in MB
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024  # Convert MB to bytes

VALID_IMAGE_MIME_TYPES = {"image/jpeg", "image/png", "image/gif"}  # Add any other valid image MIME types here
VALID_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "gif"}  # Add any other valid image extensions here


async def avatar_upload(
    username: str,
    req: UserUpdate,
    db: Session,
    current_user: User,
    file: UploadFile
):
    # Check if file is provided
    if file:
        # Check file size
        file_data = await file.read()
        if len(file_data) > MAX_FILE_SIZE_BYTES:
            raise HTTPException(status_code=400, detail="File size exceeds 5MB limit")

        # Rewind file data for future operations
        file.file.seek(0)

        # Check if the file is an image
        file_type = file.content_type
        if file_type not in VALID_IMAGE_MIME_TYPES:
            raise HTTPException(status_code=400, detail="Invalid file type. Only image files are allowed")

        # Check file extension
        ext = file.filename.split('.')[-1].lower()
        if ext not in VALID_IMAGE_EXTENSIONS:
            raise HTTPException(status_code=400, detail="Invalid file extension. Only image files are allowed")

        # Process file details
        file_name = f"{current_user.id}_avatar.{ext}"

        # Check for existing avatar
        existing_avatar = db.query(Avatar).filter(Avatar.userID == current_user.id).first()

        if not existing_avatar:
            # Create new avatar record if none exists
            avatar = Avatar(
                filename=file_name,
                filedata=file_data,
                filetype=file_type,
                userID=current_user.id
            )
            db.add(avatar)
        else:
            # Update existing avatar record
            existing_avatar.filename = file_name
            existing_avatar.filedata = file_data
            existing_avatar.filetype = file_type

    user = db.query(User).filter(User.username==username).first()
    if user:
    # Update the user's details with the data from req
        if req.username is not None:
            user.username = req.username
        if req.works_at is not None:
            user.works_at = req.works_at
        if req.contact_no is not None:
            user.contact_no = req.contact_no
        # Commit the changes to the database
        db.commit()

        # Optionally, you might want to refresh the instance to reflect changes
        db.refresh(user)
        db.commit()
    return {"message": "Avatar Updated", "success": True}


async def get_avatar(
    userID: int,
    db: Session
) -> Dict[str, str]:
    # Fetch the avatar record from the database
    avatar = db.query(Avatar).filter(Avatar.userID == userID).first()
    
    # Handle case where no avatar is found
    if not avatar:
        raise HTTPException(status_code=404, detail="Avatar Not Found")

    # Retrieve file details
    file_name = getattr(avatar, 'filename', None)
    file_data = getattr(avatar, 'filedata', None)
    file_type = getattr(avatar, 'filetype', None)

    # Ensure that all required fields are present
    if not file_name or not file_data or not file_type:
        raise HTTPException(status_code=500, detail="Incomplete avatar data")

    try:
        # Encode file data to base64
        encoded_file_data = pybase64.b64encode(file_data).decode('utf-8')
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error encoding file data")

    # Construct response
    response = {
        "fileName": file_name,
        "fileType": file_type,
        "fileData": encoded_file_data
    }
    
    return response


async def upload_event_files(
    eventId: str,
    files: List[UploadFile],
    update_info:EventDetailsupdate,
    current_user: User,
    event_container,
    file_container
):
    # Query to find the event
    query_event = "SELECT * FROM eventcontainer e WHERE e.id = @id"
    params_event = [{"name": "@id", "value": eventId}]
    event_items = list(event_container.query_items(query=query_event, parameters=params_event, enable_cross_partition_query=True))

    if not event_items:
        raise HTTPException(status_code=404, detail="Event Not Found")
    
    existing_event = event_items[0]

    userId = current_user.id
    editor_access_list = existing_event.get("editor_access", "")
    if str(userId) not in editor_access_list:
        raise HTTPException(status_code=403, detail="User does not have editor access")
    if files:
        if len(files) > 5:
            raise HTTPException(status_code=400, detail="Maximum 5 files can be uploaded at once")
        file_columns = [
            ('fileName1', 'fileData1', 'fileType1'),
            ('fileName2', 'fileData2', 'fileType2'),
            ('fileName3', 'fileData3', 'fileType3'),
            ('fileName4', 'fileData4', 'fileType4'),
            ('fileName5', 'fileData5', 'fileType5')
        ]

        # Query to find existing record of event files
        query_files = "SELECT * FROM eventfilescontainer ef WHERE ef.eventId = @eventId"
        params_files = [{"name": "@eventId", "value": eventId}]
        file_items = list(file_container.query_items(query=query_files, parameters=params_files, enable_cross_partition_query=True))

        if file_items:
            existing_record = file_items[0]
            for i, file in enumerate(files):
                if i < len(file_columns):
                    file_column = file_columns[i]
                    fileName = f"{eventId}_{file.filename}"
                    fileType = file.content_type
                    
                    # Encode file data as base64 string
                    file_data_base64 = pybase64.b64encode(await file.read()).decode('utf-8')

                    existing_record[file_column[0]] = fileName
                    existing_record[file_column[1]] = file_data_base64
                    existing_record[file_column[2]] = fileType

            file_container.replace_item(item=existing_record['id'], body=existing_record)
        else:
            new_record = {
                "id": str(uuid4()),  # Generate a new UUID for the record
                "eventId": eventId,
            }

            for i, file in enumerate(files):
                if i < len(file_columns):
                    file_column = file_columns[i]
                    fileName = f"{eventId}_{file.filename}"
                    fileType = file.content_type
                    # Encode file data as base64 string
                    file_data_base64 = pybase64.b64encode(await file.read()).decode('utf-8')
                    new_record[file_column[0]] = fileName
                    new_record[file_column[1]] = file_data_base64
                    new_record[file_column[2]] = fileType
            file_container.create_item(new_record)
    if update_info:
        print (update_info)
        update_data = update_info.dict(exclude_unset=True)
        # Convert lists to comma-separated strings
        if 'event_type' in update_data and update_data['event_type'] is not None:
            update_data['type'] = ','.join(update_data.pop('event_type'))
        
        # Convert datetime fields to ISO format strings
        if 'start_date_and_time' in update_info and update_info.start_date_and_time is not None:
            update_data['start_date'] = update_info.start_date_and_time.to_datetime().isoformat()
        if 'end_date_and_time' in update_info and update_info.end_date_and_time is not None:
            update_data['end_date'] = update_info.end_date_and_time.to_datetime().isoformat()
            # Update existing event with new data
        for key, value in update_data.items():
            if value is not None:
                existing_event[key] = value
        event_container.replace_item(item=existing_event['id'], body=existing_event)
    return {"message": "Files Updated", "success": True}

async def fetch_event_files(
    eventId: str,
    file_container
):
    # Query to find the existing record of event files
    query = "SELECT * FROM eventfilescontainer ef WHERE ef.eventId = @eventId"
    params = [{"name": "@eventId", "value": eventId}]
    file_items = list(file_container.query_items(query=query, parameters=params, enable_cross_partition_query=True))

    if not file_items:
        raise HTTPException(status_code=404, detail="Files not found")

    existing_record = file_items[0]

    files = []

    for i in range(1, 6):
        fileName = existing_record.get(f'fileName{i}', None)
        fileData = existing_record.get(f'fileData{i}', None)
        fileType = existing_record.get(f'fileType{i}', None)
        if fileName and fileData and fileType:
            try:
                
                files.append({"fileName": fileName, "fileData": fileData, "fileType": fileType})
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Error decoding file data: {str(e)}")
    
    return files