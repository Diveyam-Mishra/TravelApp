from fastapi import UploadFile, HTTPException
from sqlalchemy.orm import Session
from Database.Connection import get_db, avatar_container_name, event_files_blob_container_name
from Models.user_models import User
from Models.Files import Avatar
import pybase64  # type: ignore
from uuid import uuid4
from Controllers.Auth import get_current_user
from typing import Dict, List
from Schemas.UserSchemas import *
from Schemas.EventSchemas import EventDetailsupdate, EventDetails
from datetime import datetime
MAX_FILE_SIZE_MB = 5  # Maximum file size in MB
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024  # Convert MB to bytes

VALID_IMAGE_MIME_TYPES = {
    "image/jpeg",  # JPG, JPEG
    "image/png",   # PNG
    "image/gif",   # GIF
    "image/bmp",   # BMP
    "image/webp",  # WEBP
    "image/tiff",  # TIFF
    "image/x-icon",  # ICO
    "image/svg+xml",  # SVG
    "image/heif",  # HEIF
    "image/heic",  # HEIC
    "image/avif",  # AVIF
    "image/x-cmu-raster",  # RAS
    "image/x-portable-anymap",  # PNM
    "image/x-portable-bitmap",  # PBM
    "image/x-portable-graymap",  # PGM
    "image/x-portable-pixmap",  # PPM
    "image/x-xbitmap",  # XBM
    "image/x-xpixmap",  # XPM
    "image/x-xwindowdump",  # XWD
    "image/vnd.adobe.photoshop",  # PSD
    "image/vnd.microsoft.icon",  # ICO (alternative MIME type)
}

VALID_IMAGE_EXTENSIONS = {
    "jpg", "jpeg",  # JPEG
    "png",  # PNG
    "gif",  # GIF
    "bmp",  # BMP
    "webp",  # WEBP
    "tif", "tiff",  # TIFF
    "ico",  # ICO
    "svg",  # SVG
    "heif",  # HEIF
    "heic",  # HEIC
    "avif",  # AVIF
    "ras",  # RAS
    "pnm",  # PNM
    "pbm",  # PBM
    "pgm",  # PGM
    "ppm",  # PPM
    "xbm",  # XBM
    "xpm",  # XPM
    "xwd",  # XWD
    "psd",  # Photoshop
}


async def avatar_upload(
    req: UserUpdate,
    db: Session,
    current_user: User,
    file: UploadFile,
    blob_service_client
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
        
        # Upload the file to Azure Blob Storage
        blob_client = blob_service_client.get_blob_client(container=avatar_container_name, blob=file_name)
        blob_client.upload_blob(file_data, overwrite=True)

        # Generate the URL of the uploaded file
        file_url = blob_client.url

        # Check for existing avatar
        existing_avatar = db.query(Avatar).filter(Avatar.userID == current_user.id).first()

        if not existing_avatar:
            # Create new avatar record if none exists
            avatar = Avatar(
                filename=file_name,
                fileurl=file_url,  # Store URL instead of file data
                filetype=file_type,
                userID=current_user.id
            )
            db.add(avatar)
        else:
            # Update existing avatar record
            existing_avatar.filename = file_name
            existing_avatar.fileurl = file_url  # Update URL
            existing_avatar.filetype = file_type

        db.commit()
        db.refresh(existing_avatar if existing_avatar else avatar)

    # Update the user's details with the data from req
    user = db.query(User).filter(User.id == current_user.id).first()
    if user:
        if req.username is not None:
            user.username = req.username
        if req.works_at is not None:
            user.works_at = req.works_at
        if req.contact_no is not None:
            user.contact_no = req.contact_no
        if req.gender is not None:
            user.gender = req.gender
        if req.dob is not None:
            user.dob = req.dob
        
        # Commit the changes to the database
        db.commit()
        db.refresh(user)

    return {"message": "Avatar Updated", "success": True}


async def create_event_and_upload_files(
    event_data: EventDetails,
    files: List[UploadFile],
    current_user: User,
    event_container,
    file_container,
    blob_service_client , redis
) -> SuccessResponse:
    # Prepare the query to check if the event already exists
    query = """
    SELECT * FROM eventcontainer e WHERE e.name = @name AND e.host_id = @host_id AND e.type = @type AND e.start_date = @start_date AND e.end_date = @end_date
    """
    
    params = [
        {"name": "@name", "value": event_data.event_name},
        {"name": "@type", "value": ','.join(event_data.event_type)},
        {"name": "@start_date", "value": event_data.start_date_and_time},
        {"name": "@end_date", "value": event_data.end_date_and_time}
    ]

    if event_data.host_information != "0":
        params.append({"name": "@host_id", "value": event_data.host_information})
    
    items = list(event_container.query_items(query=query, parameters=params, enable_cross_partition_query=True))

    if items:
        raise HTTPException(status_code=400, detail="Event already created")

    # Calculate the duration in minutes
    start_date_and_time_str = event_data.start_date_and_time
    end_date_and_time_str = event_data.end_date_and_time

    # Parse ISO format strings to datetime objects
    start_datetime = datetime.fromisoformat(start_date_and_time_str.replace('Z', '+00:00'))
    end_datetime = datetime.fromisoformat(end_date_and_time_str.replace('Z', '+00:00'))

    # Calculate the duration in minutes
    duration_minutes = int((end_datetime - start_datetime).total_seconds() / 60)

    # Create a new event
    new_event = event_data.dict()
    newId = str(uuid4())
    new_event.update({
        "id": newId,  # Generate a new UUID for the id field
        "event_ID": newId,  # Generate a new UUID for the event_id field
        "type": ','.join(event_data.event_type),  # Convert list to comma-separated string
        "start_date": start_date_and_time_str,  # Convert datetime to ISO format string
        "end_date": end_date_and_time_str,  # Convert datetime to ISO format string
        "duration": str(duration_minutes),  # Store duration as a string
        "remaining_capacity": event_data.capacity,
        "creator_id": current_user.id,  # Use the current user's ID
        "editor_access": [str(current_user.id)],  # Set the creator as the editor
        "location": {
            "venue": event_data.location.venue,
            "geo_tag": {
                "latitude": event_data.location.geo_tag.latitude,
                "longitude": event_data.location.geo_tag.longitude
            },
            "city": event_data.location.city
        }
    })

    

    for category in event_data.event_type:
        cache_key = f"events:{category}"
        redis.delete(cache_key)

    # Handle file uploads
    if files:
        if len(files) > 5:
            raise HTTPException(status_code=400, detail="Maximum 5 files can be uploaded at once")

        # Prepare a list to store file metadata
        file_metadata = []
        
        # Upload files to Azure Blob Storage and collect file metadata
        for i, file in enumerate(files):
            if i >= 5:
                break
            
            file_extension = file.filename.split('.')[-1]
            file_name = f"{new_event['id']}_file_{i+1}.{file_extension}"
            blob_client = blob_service_client.get_blob_client(container=event_files_blob_container_name, blob=file_name)
            
            # Read file data
            file_data = await file.read()
            
            # Upload file
            blob_client.upload_blob(file_data, overwrite=True)
            
            # Generate file URL
            file_url = blob_client.url
            
            # Add file metadata to the list
            file_metadata.append({
                "fileName": file_name,
                "fileUrl": file_url,
                "fileType": file.content_type
            })

        # Create new record for files
        new_record = {
            "id": newId,  # Generate a new UUID for the record
            "event_ID": newId,
        }
        
        # Add file metadata to the new record
        for i, metadata in enumerate(file_metadata):
            if i==0:
                new_event.update({"thumbnail": {
                "file_name": metadata["fileName"],
                "file_url":  metadata["fileUrl"],
                "file_type": metadata["fileType"]}})
            if i < 5:
                new_record[f'fileName{i+1}'] = metadata["fileName"]
                new_record[f'fileUrl{i+1}'] = metadata["fileUrl"]
                new_record[f'fileType{i+1}'] = metadata["fileType"]
        
        # Insert the new record into the file container
        file_container.create_item(new_record)
        # Insert the new event into the event container
        event_container.create_item(new_event)
    
    return SuccessResponse(message=f"Event Created Successfully with event_id: {new_event['id']}", success=True)


async def get_avatar(
    userID: str,
    db: Session
) -> Dict[str, str]:
    # Fetch the avatar record from the database
    avatar = db.query(Avatar).filter(Avatar.userID == userID).first()
    
    # Handle case where no avatar is found
    if not avatar:
        raise HTTPException(status_code=404, detail="Avatar Not Found")

    # Retrieve file details
    file_name = getattr(avatar, 'filename', None)
    file_url = getattr(avatar, 'fileurl', None)
    file_type = getattr(avatar, 'filetype', None)

    # Ensure that all required fields are present
    if not file_name or not file_url or not file_type:
        raise HTTPException(status_code=500, detail="Incomplete avatar data")

    # Construct response
    response = {
        "fileName": file_name,
        "fileType": file_type,
        "fileUrl": file_url  # Return the URL of the file
    }
    
    return response


async def upload_event_files(
    eventId: str,
    files: List[UploadFile],
    update_info: BaseModel,
    current_user: User,
    event_container,
    blob_service_client,
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
    if userId not in editor_access_list:
        raise HTTPException(status_code=403, detail="User does not have editor access")
    
    if files:
        if len(files) > 5:
            raise HTTPException(status_code=400, detail="Maximum 5 files can be uploaded at once")
        
        # Prepare a list to store file metadata
        file_metadata = []
        
        # Upload files to Azure Blob Storage and collect file metadata
        for i, file in enumerate(files):
            if i >= 5:
                break
            
            file_name = f"{eventId}_file_{i+1}.{file.filename.split('.')[-1]}"  # Adjusted file name pattern
            blob_client = blob_service_client.get_blob_client(container=event_files_blob_container_name, blob=file_name)
            file_data = await file.read()
            await blob_client.upload_blob(file_data, overwrite=True)
            
            # Generate file URL
            file_url = blob_client.url
            
            # Add file metadata to the list
            file_metadata.append({
                "fileName": file_name,
                "fileUrl": file_url,
                "fileType": file.content_type
            })
        
        # Query to find existing record of event files
        query_files = "SELECT * FROM eventfilescontainer ef WHERE ef.id = @eventId"
        params_files = [{"name": "@eventId", "value": eventId}]
        file_items = list(file_container.query_items(query=query_files, parameters=params_files, enable_cross_partition_query=True))

        if file_items:
            existing_record = file_items[0]
            for i, metadata in enumerate(file_metadata):
                if i < len(existing_record):
                    existing_record[f'fileName{i+1}'] = metadata["fileName"]
                    existing_record[f'fileUrl{i+1}'] = metadata["fileUrl"]
                    existing_record[f'fileType{i+1}'] = metadata["fileType"]
            
            file_container.replace_item(item=existing_record['id'], body=existing_record)
        else:
            # Create new record
            new_record = {
                "id": eventId,  # Generate a new UUID for the record
                "event_ID": eventId
            }
            # Add file metadata to the new record
            for i, metadata in enumerate(file_metadata):
                new_record[f'fileName{i+1}'] = metadata["fileName"]
                new_record[f'fileUrl{i+1}'] = metadata["fileUrl"]
                new_record[f'fileType{i+1}'] = metadata["fileType"]
            
            file_container.create_item(new_record)
    
    if update_info:
        update_data = update_info.dict(exclude_unset=True)
        
        # Convert lists to comma-separated strings
        if 'event_type' in update_data and update_data['event_type'] is not None:
            update_data['type'] = ','.join(update_data.pop('event_type'))
        
        # Convert datetime fields to ISO format strings
        if 'start_date_and_time' in update_info and update_info.start_date_and_time is not None:
            update_data['start_date'] = update_info.start_date_and_time.isoformat()
        if 'end_date_and_time' in update_info and update_info.end_date_and_time is not None:
            update_data['end_date'] = update_info.end_date_and_time.isoformat()
        
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
    query = "SELECT * FROM eventfilescontainer ef WHERE ef.id = @eventId"
    params = [{"name": "@eventId", "value": eventId}]
    file_items = list(file_container.query_items(query=query, parameters=params, enable_cross_partition_query=True))

    if not file_items:
        raise HTTPException(status_code=404, detail="Files not found")

    existing_record = file_items[0]

    files = []

    for i in range(1, 6):
        fileName = existing_record.get(f'fileName{i}', None)
        fileUrl = existing_record.get(f'fileUrl{i}', None)
        fileType = existing_record.get(f'fileType{i}', None)

        if fileName and fileUrl and fileType:
            files.append({
                "fileName": fileName,
                "fileUrl": fileUrl,  # URL instead of binary data
                "fileType": fileType
            })
    
    return files
